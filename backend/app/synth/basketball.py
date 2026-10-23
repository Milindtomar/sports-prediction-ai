"""Synthetic basketball generator (possession-by-possession).

Each possession ends in: turnover, foul trip (2 FT), made/missed 2 or 3, with
offensive-rebound continuation. Efficiency depends on the strength gap `D`
(100-Elo units), home court and a lineup adjustment (injured / rested key
player). Quarter structure: 4 x 12 min; ties after 48 min are resolved by a
strength-weighted overtime draw (the label is "home team wins").
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .common import EloTable

TEAMS = ["Harbor Hornets", "Summit Stags", "Neon Nighthawks", "Iron Wolves", "Riverton Rockets",
         "Cobalt Comets", "Sable Sentinels", "Amber Aces", "Glacier Giants", "Copper Cranes",
         "Velvet Vipers", "Jade Jaguars", "Mesa Mustangs", "Tidal Titans", "Granite Grizzlies",
         "Aurora Arrows"]
GAME_SEC = 2880
WINDOW_SEC = 300


def new_state(home_elo: float, away_elo: float, home_lineup: float = 0.0, away_lineup: float = 0.0,
              possession: int = 0) -> dict:
    z = dict(home_fgm=0, home_fga=0, away_fgm=0, away_fga=0, home_3pm=0, home_3pa=0, away_3pm=0, away_3pa=0,
             home_ftm=0, home_fta=0, away_ftm=0, away_fta=0, home_reb=0, away_reb=0, home_ast=0, away_ast=0,
             home_tov=0, away_tov=0, home_fouls=0, away_fouls=0)
    return dict(elapsed_sec=0, home_score=0, away_score=0, possession=possession, home_elo=home_elo,
                away_elo=away_elo, home_lineup=home_lineup, away_lineup=away_lineup,
                recent_points_home=0, recent_points_away=0, current_run=0, **z)


def advance(st: dict, rng, seconds: float, D: float, pace: float = 0.0, three: float = 0.0,
            tac_side: str | None = None, hist: list | None = None, log: list | None = None) -> dict:
    """Advance by `seconds` of game clock. `pace`/`three` are tactical shifts applied to
    `tac_side` ('home'|'away'|None=both unchanged). Mutates and returns `st`."""
    t_start = st["elapsed_sec"]
    t_end = min(GAME_SEC, t_start + seconds)
    added_h = added_a = 0
    while st["elapsed_sec"] < t_end:
        off = "home" if st["possession"] == 0 else "away"
        dfn = "away" if off == "home" else "home"
        sgn = 1.0 if off == "home" else -1.0
        tac = (tac_side == off)
        pace_o = pace if tac else 0.0
        three_o = three if tac else 0.0
        dt = rng.uniform(8, 21) * math.exp(-pace_o)
        dt = min(dt, GAME_SEC - st["elapsed_sec"])
        lin_o, lin_d = st[f"{off}_lineup"], st[f"{dfn}_lineup"]
        eff = (1 + 0.12 * lin_o) * (1 - 0.06 * lin_d) * math.exp(0.03 * sgn * D) + (0.012 if off == "home" else 0.0)
        p_tov = float(np.clip(0.135 - 0.010 * sgn * D + 0.01 * pace_o, 0.07, 0.22))
        pts = 0
        keep = False
        ev = None
        if rng.random() < p_tov:
            st[f"{off}_tov"] += 1
            ev = dict(kind="tov")
        elif rng.random() < 0.11:
            st[f"{dfn}_fouls"] += 1
            ev = dict(kind="ft", made=0)
            for _ in range(2):
                st[f"{off}_fta"] += 1
                if rng.random() < 0.77 * min(eff, 1.2) ** 0.5:
                    st[f"{off}_ftm"] += 1
                    pts += 1
                    ev["made"] += 1
        else:
            is3 = rng.random() < float(np.clip(0.38 + three_o, 0.15, 0.7))
            p_make = (0.355 if is3 else 0.52) * eff
            st[f"{off}_fga"] += 1
            if is3:
                st[f"{off}_3pa"] += 1
            ev = dict(kind="shot", three=bool(is3), made=False, assisted=False)
            if rng.random() < p_make:
                ev["made"] = True
                st[f"{off}_fgm"] += 1
                pts += 3 if is3 else 2
                if is3:
                    st[f"{off}_3pm"] += 1
                if rng.random() < 0.6:
                    ev["assisted"] = True
                    st[f"{off}_ast"] += 1
            else:
                if rng.random() < 0.26:
                    st[f"{off}_reb"] += 1
                    keep = True
                else:
                    st[f"{dfn}_reb"] += 1
        st["elapsed_sec"] = int(round(st["elapsed_sec"] + dt))
        if log is not None and ev is not None:
            ev.update(t=st["elapsed_sec"], side=off, pts=pts, rebound=("off" if keep else None))
            log.append(ev)
        if pts:
            st[f"{off}_score"] += pts
            if off == "home":
                added_h += pts
                st["current_run"] = st["current_run"] + pts if st["current_run"] > 0 else pts
            else:
                added_a += pts
                st["current_run"] = st["current_run"] - pts if st["current_run"] < 0 else -pts
        if hist is not None and pts:
            hist.append((st["elapsed_sec"], pts if off == "home" else 0, pts if off == "away" else 0))
        if not keep:
            st["possession"] = 1 - st["possession"]
    if hist is not None:
        lo = st["elapsed_sec"] - WINDOW_SEC
        st["recent_points_home"] = sum(h[1] for h in hist if h[0] > lo)
        st["recent_points_away"] = sum(h[2] for h in hist if h[0] > lo)
    else:
        n = st["elapsed_sec"] - t_start
        keep_f = max(0.0, (WINDOW_SEC - n) / WINDOW_SEC)
        st["recent_points_home"] = int(round(st["recent_points_home"] * keep_f + added_h))
        st["recent_points_away"] = int(round(st["recent_points_away"] * keep_f + added_a))
    return st


@dataclass
class BasketballGame:
    match_id: int
    home: int
    away: int
    snaps: list
    final: dict
    home_win: int


def simulate_season(n_games: int, seed: int = 13, step_sec: int = 120):
    rng = np.random.default_rng(seed)
    nt = len(TEAMS)
    q = rng.normal(0, 0.8, nt)
    elo = EloTable(nt, k=20.0)
    out = []
    for gid in range(n_games):
        h, a = rng.choice(nt, 2, replace=False)
        D = q[h] - q[a]
        hl = -0.25 if rng.random() < 0.15 else 0.0
        al = -0.25 if rng.random() < 0.15 else 0.0
        st = new_state(elo.rating(h), elo.rating(a), hl, al, possession=int(rng.integers(2)))
        hist: list = []
        snaps = [dict(st)]
        while st["elapsed_sec"] < GAME_SEC:
            advance(st, rng, step_sec, D, hist=hist)
            if st["elapsed_sec"] < GAME_SEC:
                snaps.append(dict(st))
        if st["home_score"] == st["away_score"]:
            p = 1 / (1 + math.exp(-(0.3 * D + 0.1)))
            win = int(rng.random() < p)
            st["ot"] = 1
        else:
            win = int(st["home_score"] > st["away_score"])
        for s in snaps:
            s["label"] = win
        out.append(BasketballGame(gid, int(h), int(a), snaps, dict(st), win))
        margin = 1 + min(abs(st["home_score"] - st["away_score"]) / 12, 1.5)
        elo.update(int(h), int(a), float(win), margin=margin, adv_i=45)
    return out, q


def season_to_rows(games):
    rows = []
    for g in games:
        for s in g.snaps:
            r = dict(s)
            r["match_id"] = g.match_id
            rows.append(r)
    return rows
