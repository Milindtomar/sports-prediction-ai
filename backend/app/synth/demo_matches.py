"""Detailed demo-match builders (ball-by-ball / shot-by-shot / possession-by-possession).

These matches are generated with seeds disjoint from the training seasons, so the trained
models have never seen them. Shot/shot-zone coordinates, wagon-wheel angles and pitch-map
lengths are *illustrative decoration generated conditionally on the simulated outcome*;
they are not predicted by any ML model (documented in the UI and docs).
"""
from __future__ import annotations

import math
from collections import deque

import numpy as np

from app.synth import basketball as bsim
from app.synth import cricket as csim
from app.synth import football as fsim

# ------------------------------------------------------------------------------------ cricket


def build_cricket_match(seed: int, team_a: str, team_b: str, venue: str, elo_a: float, elo_b: float,
                        roster_a: list[dict], roster_b: list[dict]) -> dict:
    """roster_*: list of dicts {name, role, slot}. Team A bats first."""
    rng = np.random.default_rng(seed)
    vf, par = csim.VENUES[venue]
    sk_a, sk_b = (elo_a - 1500) / 100 + rng.normal(0, 0.25), (elo_b - 1500) / 100 + rng.normal(0, 0.25)
    timeline, balls = [], []

    def run_innings(innings, bat_team, bowl_team, bat_roster, bowl_roster, d, target, bat_elo, bowl_elo):
        st = csim.new_innings_state(innings, target)
        hist: deque = deque(maxlen=12)
        order = sorted(bat_roster, key=lambda p: p["slot"])
        bowlers = [p for p in bowl_roster if p["role"] in ("bowl", "all")][:5]
        s_idx, ns_idx, nxt = 0, 1, 2
        base = dict(innings=innings, batting_team=bat_team, bowling_team=bowl_team, venue=venue, venue_par=par,
                    batting_elo=bat_elo, bowling_elo=bowl_elo)

        def snap():
            d_ = {k: st[k] for k in ("runs", "wickets", "balls_bowled", "target", "partnership_runs", "partnership_balls",
                                     "recent_runs", "recent_wickets", "recent_boundaries")}
            d_.update(base)
            if timeline and all(timeline[-1].get(k) == d_[k] for k in ("innings", "runs", "wickets", "balls_bowled")):
                return
            d_["step_label"] = f"Inn {innings} · Over {st['balls_bowled'] // 6}.{st['balls_bowled'] % 6}"
            timeline.append(d_)

        snap()
        while st["balls_bowled"] < 120 and st["wickets"] < 10 and not (target and st["runs"] >= target):
            log: list = []
            csim.advance(st, rng, 1, d, vf, hist=hist, log=log)
            ev = log[0]
            over, b_in = (ev["ball"] - 1) // 6, (ev["ball"] - 1) % 6
            striker = order[s_idx]["name"] if s_idx < len(order) else "Tail-ender"
            bowler = bowlers[over % len(bowlers)]["name"]
            r, w = ev["runs"], ev["wicket"]
            if w:
                shot_angle, dist = None, None
            else:
                spread = 360 if r >= 4 else 300
                shot_angle = float((rng.normal(0, 1) * (110 if r < 4 else 90) + (rng.choice([-1, 1]) * 40) + 360) % 360)
                dist = {0: 0.0, 1: float(rng.uniform(.25, .5)), 2: float(rng.uniform(.5, .7)), 3: float(rng.uniform(.6, .85)),
                        4: 1.0, 6: float(rng.uniform(1.06, 1.25))}[r]
                _ = spread
            length = float(np.clip(rng.normal(0.42 if not w else 0.5, 0.22), 0.02, 0.98))   # 0 yorker .. 1 short
            line = float(np.clip(rng.normal(0.0, 0.5 if not w else 0.3), -1.2, 1.2))
            balls.append(dict(inn=innings, over=over, ball=b_in, striker=striker, bowler=bowler, runs=r, wicket=w,
                              angle=shot_angle, dist=dist, length=round(length, 2), line=round(line, 2)))
            if w:
                s_idx, nxt = nxt, nxt + 1
            elif r % 2 == 1:
                s_idx, ns_idx = ns_idx, s_idx
            if ev["ball"] % 6 == 0:
                s_idx, ns_idx = ns_idx, s_idx
            if ev["ball"] % 6 == 0 and ev["ball"] < 120:
                snap()
        snap()  # final state of the innings
        return st["runs"], st["wickets"]

    d1 = csim.D_PER_ELO100 * (sk_a - sk_b)
    s1, w1 = run_innings(1, team_a, team_b, roster_a, roster_b, d1, None, elo_a, elo_b)
    d2 = csim.D_PER_ELO100 * (sk_b - sk_a)
    s2, w2 = run_innings(2, team_b, team_a, roster_b, roster_a, d2, s1 + 1, elo_b, elo_a)
    if s2 >= s1 + 1:
        result = f"{team_b} won by {10 - w2} wickets"
    elif s2 == s1:
        result = "Match tied"
    else:
        result = f"{team_a} won by {s1 - s2} runs"
    return dict(title=f"{team_a} vs {team_b}", home=team_a, away=team_b, venue=venue, timeline=timeline, events=balls,
                meta=dict(result=result, first_innings=[s1, w1], second_innings=[s2, w2], par=par,
                          rosters={team_a: roster_a, team_b: roster_b}, format="T20",
                          viz_note="Wagon-wheel angles and pitch-map lengths are illustrative (generated from the ball outcome), not ML output."))


# ------------------------------------------------------------------------------------ football


def build_football_match(seed: int, home: str, away: str, elo_h: float, elo_a: float, h_lineup: float, a_lineup: float,
                         roster_h: list[dict], roster_a: list[dict]) -> dict:
    rng = np.random.default_rng(seed)
    D = (elo_h - elo_a) / 100 + rng.normal(0, 0.25)
    st = fsim.new_state(elo_h, elo_a, h_lineup, a_lineup)
    hist: deque = deque(maxlen=fsim.WINDOW)
    timeline, events = [], []

    def weights(roster):
        w = np.array([{"FWD": 3.0, "MID": 1.4, "DEF": 0.45}[p["role"]] for p in roster])
        return w / w.sum()

    wh, wa = weights(roster_h), weights(roster_a)

    def snap(final=False):
        d_ = dict(st)
        d_.update(home_team=home, away_team=away, step_label="Full time" if final else f"{st['minute']}'")
        timeline.append(d_)

    snap()
    prev = dict(st)
    for _ in range(90):
        log: list = []
        fsim.advance(st, rng, 1, D, hist=hist, log=log)
        for e in log:
            side, roster, w = (home, roster_h, wh) if e["side"] == "home" else (away, roster_a, wa)
            shooter = roster[rng.choice(len(roster), p=w)]["name"]
            dist = 7 + 24 * (1 - min(e["xg"], 0.5) / 0.5) ** 1.3 + rng.uniform(0, 3)
            lat = rng.normal(0, 3 + dist * 0.18)
            x = 105 - dist if e["side"] == "home" else dist
            y = float(np.clip(34 + lat, 6, 62))
            assister = None
            if e["goal"] and rng.random() < 0.72:
                mids = [p["name"] for p in roster if p["role"] in ("MID", "FWD") and p["name"] != shooter]
                assister = mids[rng.integers(len(mids))]
            events.append(dict(type="shot", minute=e["minute"], side=e["side"], team=side, player=shooter, xg=e["xg"],
                               goal=e["goal"], sot=e["sot"], x=round(float(x), 1), y=round(y, 1), assist=assister))
        for side, team in (("home", home), ("away", away)):
            for kind in ("yellow", "red"):
                if st[f"{side}_{kind}"] > prev[f"{side}_{kind}"]:
                    roster = roster_h if side == "home" else roster_a
                    events.append(dict(type=kind, minute=st["minute"], side=side, team=team,
                                       player=roster[rng.integers(len(roster))]["name"]))
        prev = dict(st)
        if st["minute"] % 5 == 0 and st["minute"] < 90:
            snap()
    snap(final=True)
    res = ("draw" if st["home_goals"] == st["away_goals"] else (home if st["home_goals"] > st["away_goals"] else away))
    result = "Draw" if res == "draw" else f"{res} won {max(st['home_goals'], st['away_goals'])}–{min(st['home_goals'], st['away_goals'])}"
    return dict(title=f"{home} vs {away}", home=home, away=away, venue=f"{home} home ground", timeline=timeline, events=events,
                meta=dict(result=result, final=[st["home_goals"], st["away_goals"]], rosters={home: roster_h, away: roster_a},
                          viz_note="Shot positions are illustrative (generated from each shot's xG), not ML output."))


# ------------------------------------------------------------------------------------ basketball


def build_basketball_match(seed: int, home: str, away: str, elo_h: float, elo_a: float, h_lineup: float, a_lineup: float,
                           roster_h: list[dict], roster_a: list[dict]) -> dict:
    rng = np.random.default_rng(seed)
    D = (elo_h - elo_a) / 100 + rng.normal(0, 0.25)
    st = bsim.new_state(elo_h, elo_a, h_lineup, a_lineup, possession=int(rng.integers(2)))
    hist: list = []
    timeline, events = [], []

    def snap(final=False):
        d_ = dict(st)
        d_.update(home_team=home, away_team=away)
        q = min(4, st["elapsed_sec"] // 720 + 1)
        left = max(q * 720 - st["elapsed_sec"], 0) if not final else 0
        d_["step_label"] = "Final" if final else f"Q{q} {left // 60}:{left % 60:02d}"
        timeline.append(d_)

    def pick(roster, key="usage"):
        w = np.array([p.get(key, 1.0) for p in roster], float)
        return roster[rng.choice(len(roster), p=w / w.sum())]

    snap()
    while st["elapsed_sec"] < bsim.GAME_SEC:
        log: list = []
        bsim.advance(st, rng, 120, D, hist=hist, log=log)
        for e in log:
            side = e["side"]
            team, roster = (home, roster_h) if side == "home" else (away, roster_a)
            opp_roster = roster_a if side == "home" else roster_h
            ev = dict(type=e["kind"], t=e["t"], side=side, team=team, pts=e["pts"])
            if e["kind"] == "shot":
                shooter = pick(roster)
                ev.update(player=shooter["name"], three=e["three"], made=e["made"])
                if e["three"]:
                    ang = rng.uniform(0.15, math.pi - 0.15)
                    r = 23.75 + rng.uniform(0, 1.5)
                    ev.update(x=round(25 + r * math.cos(ang), 1), y=round(5.25 + r * math.sin(ang), 1))
                else:
                    r = abs(rng.normal(0, 8)) + 1.5
                    ang = rng.uniform(0.1, math.pi - 0.1)
                    ev.update(x=round(25 + min(r, 22) * math.cos(ang), 1), y=round(5.25 + min(r, 22) * math.sin(ang), 1))
                if e["made"] and e["assisted"]:
                    ev["assist"] = pick([p for p in roster if p["name"] != shooter["name"]])["name"]
                if not e["made"]:
                    if e["rebound"] == "off":
                        ev["rebound"] = pick(roster, "reb")["name"]
                        ev["rebound_side"] = side
                    else:
                        ev["rebound"] = pick(opp_roster, "reb")["name"]
                        ev["rebound_side"] = "away" if side == "home" else "home"
            elif e["kind"] == "ft":
                ev.update(player=pick(roster)["name"], made=e["made"])
            else:
                ev.update(player=pick(roster)["name"])
            events.append(ev)
        if st["elapsed_sec"] < bsim.GAME_SEC:
            snap()
    snap(final=True)
    result = f"{home if st['home_score'] > st['away_score'] else away} won {max(st['home_score'], st['away_score'])}–{min(st['home_score'], st['away_score'])}"
    return dict(title=f"{home} vs {away}", home=home, away=away, venue=f"{home} arena", timeline=timeline, events=events,
                meta=dict(result=result, final=[st["home_score"], st["away_score"]], rosters={home: roster_h, away: roster_a},
                          viz_note="Shot-chart coordinates are illustrative (generated from shot type and outcome), not ML output."))
