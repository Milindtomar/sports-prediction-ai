"""Seed the database with fictional rosters, player histories and demo matches.

    python -m app.seed [--force]

Deterministic: same seeds -> same rows. Demo matches use seeds outside the training seasons.
"""
from __future__ import annotations

import argparse
import re

import numpy as np
from sqlmodel import Session, delete, select

from app.db import engine, init_db
from app.models_db import HciSession, HciTaskResult, Match, Player, PlayerGame, SimulationRun
from app.synth import basketball as bsim
from app.synth import cricket as csim
from app.synth import football as fsim
from app.synth import players as pl
from app.synth.demo_matches import build_basketball_match, build_cricket_match, build_football_match

N_HISTORY = 36


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


# ------------------------------------------------------------------------------ rosters
def make_cricket_roster(rng, used, team):
    roles = ["bat"] * 4 + ["all"] * 2 + ["bowl"] * 5
    out = []
    for i, role in enumerate(roles):
        p = pl.gen_cricket_player(rng, used, role=role, n_games=N_HISTORY)
        p["slot"] = i + 1 if role == "bat" else (5 + (i - 4) if role == "all" else 7)
        bat, bowl = pl.simulate_cricket_career(p, rng)
        out.append((dict(team=team, name=p["name"], role=role, attrs=dict(slot=p["slot"])), dict(bat=bat, bowl=bowl)))
    return out


def make_football_roster(rng, used, team):
    roles = ["FWD"] * 3 + ["MID"] * 4 + ["DEF"] * 4
    out = []
    for role in roles:
        p = pl.gen_football_player(rng, used, pos=role, n_games=N_HISTORY)
        out.append((dict(team=team, name=p["name"], role=role, attrs={}), dict(main=pl.simulate_football_career(p, rng))))
    return out


def make_basketball_roster(rng, used, team):
    roles = ["G", "G", "G", "F", "F", "F", "C", "C"]
    out = []
    for role in roles:
        p = pl.gen_basketball_player(rng, used, pos=role, n_games=N_HISTORY)
        usage = float(np.clip(p["skill"] ** 1.5, 0.4, 3))
        reb = {"G": 0.6, "F": 1.0, "C": 1.8}[role]
        out.append((dict(team=team, name=p["name"], role=role, attrs=dict(usage=usage, reb=reb)),
                    dict(main=pl.simulate_basketball_career(p, rng))))
    return out


def roster_for_match(rows):
    return [dict(name=a["name"], role=a["role"], **a["attrs"]) for a, _ in rows]


# ------------------------------------------------------------------------------ seed
def seed(force: bool = False) -> dict:
    init_db()
    with Session(engine) as s:
        if s.exec(select(Match)).first() and not force:
            return dict(seeded=False)
        for model in (HciTaskResult, HciSession, SimulationRun, PlayerGame, Player, Match):
            s.exec(delete(model))
        s.commit()
        summary = {}

        def add_roster(sport, rows):
            for attrs, career in rows:
                p = Player(sport=sport, **attrs)
                s.add(p)
                s.flush()
                for kind, games in career.items():
                    for i, g in enumerate(games):
                        s.add(PlayerGame(player_id=p.id, game_idx=i, kind=kind, stats=g))

        def add_match(sport, d):
            slug = f"{sport}-{slugify(d['title'])}"
            s.add(Match(sport=sport, slug=slug, title=d["title"], home=d["home"], away=d["away"], venue=d["venue"],
                        meta=d["meta"], timeline=d["timeline"], events=d["events"]))

        # ---------------- cricket
        rng = np.random.default_rng(2024)
        used: set[str] = set()
        teams = csim.TEAMS[:4]
        rosters = {t: make_cricket_roster(rng, used, t) for t in teams}
        for t in teams:
            add_roster("cricket", rosters[t])
        picked = []
        for pair in ((0, 1), (2, 3)):
            ta, tb = teams[pair[0]], teams[pair[1]]
            for seed_ in range(5000 + pair[0] * 100, 5000 + pair[0] * 100 + 150):
                r2 = np.random.default_rng(seed_)
                venue = csim.VENUE_NAMES[seed_ % len(csim.VENUE_NAMES)]
                ea, eb = 1500 + r2.normal(0, 45), 1500 + r2.normal(0, 45)
                m = build_cricket_match(seed_, ta, tb, venue, ea, eb, roster_for_match(rosters[ta]), roster_for_match(rosters[tb]))
                (s1, _), (s2, _w2) = m["meta"]["first_innings"], m["meta"]["second_innings"]
                last = m["timeline"][-1]
                close_chase = s2 > s1 and last["balls_bowled"] >= 108
                close_def = s2 <= s1 and s1 - s2 <= 12 and last["balls_bowled"] >= 108
                want_chase = (pair[0] == 0)
                if (close_chase and want_chase) or (close_def and not want_chase):
                    if len(m["timeline"]) > 30:
                        picked.append(m)
                        break
        for m in picked:
            add_match("cricket", m)
        summary["cricket_matches"] = len(picked)

        # ---------------- football
        rng = np.random.default_rng(2025)
        used = set()
        fteams = fsim.TEAMS[:4]
        frost = {t: make_football_roster(rng, used, t) for t in fteams}
        for t in fteams:
            add_roster("football", frost[t])
        fpicked = []
        for pair, (hl, al) in (((0, 1), (0.0, -0.2)), ((2, 3), (0.0, 0.0))):
            th, ta = fteams[pair[0]], fteams[pair[1]]
            for seed_ in range(7000 + pair[0] * 100, 7000 + pair[0] * 100 + 200):
                r2 = np.random.default_rng(seed_)
                m = build_football_match(seed_, th, ta, 1500 + r2.normal(0, 60), 1500 + r2.normal(0, 60), hl, al,
                                         roster_for_match(frost[th]), roster_for_match(frost[ta]))
                h, a = m["meta"]["final"]
                goals = [e for e in m["events"] if e["type"] == "shot" and e["goal"]]
                late = any(e["minute"] >= 75 for e in goals)
                ok = (h + a >= 4 and h > 0 and a > 0) if pair[0] == 0 else (h + a >= 3 and late and h != a)
                if ok:
                    fpicked.append(m)
                    break
        for m in fpicked:
            add_match("football", m)
        summary["football_matches"] = len(fpicked)

        # ---------------- basketball
        rng = np.random.default_rng(2026)
        used = set()
        bteams = bsim.TEAMS[:4]
        brost = {t: make_basketball_roster(rng, used, t) for t in bteams}
        for t in bteams:
            add_roster("basketball", brost[t])
        bpicked = []
        for pair, mode in (((0, 1), "close"), ((2, 3), "comeback")):
            th, ta = bteams[pair[0]], bteams[pair[1]]
            for seed_ in range(9000 + pair[0] * 100, 9000 + pair[0] * 100 + 250):
                r2 = np.random.default_rng(seed_)
                m = build_basketball_match(seed_, th, ta, 1500 + r2.normal(0, 60), 1500 + r2.normal(0, 60),
                                           0.0, -0.25 if pair[0] == 0 else 0.0, roster_for_match(brost[th]), roster_for_match(brost[ta]))
                h, a = m["meta"]["final"]
                margins = [t["home_score"] - t["away_score"] for t in m["timeline"]]
                changes = sum(1 for x, y in zip(margins, margins[1:]) if x * y < 0)
                if mode == "close" and abs(h - a) <= 5 and changes >= 3:
                    ok = True
                elif mode == "comeback" and ((h > a and min(margins) <= -10) or (a > h and max(margins) >= 10)) and abs(h - a) <= 12:
                    ok = True
                else:
                    ok = False
                if ok:
                    bpicked.append(m)
                    break
        for m in bpicked:
            add_match("basketball", m)
        summary["basketball_matches"] = len(bpicked)
        s.commit()
        summary["players"] = len(s.exec(select(Player)).all())
        summary["seeded"] = True
        return summary


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true")
    print(seed(ap.parse_args().force))
