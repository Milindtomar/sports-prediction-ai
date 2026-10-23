"""Synthetic football generator (minute-by-minute shot process).

Goals come from shots: each shot gets an xG drawn from a Beta distribution whose
mean grows with team strength; a goal is a Bernoulli(xG) draw. Therefore xG is a
*legitimate* leading indicator of goals in this dataset (as in real football),
and the models can be audited against a known generative process.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

from .common import EloTable

TEAMS = ["North Quay", "Red Harbour", "Ashford Rovers", "Kingsmead", "Stoneford", "Lakeside United",
         "Westbridge", "Calder Park", "Falcon Town", "Marlow City", "Eastgate", "Highmoor", "Brightwater",
         "Oakhill", "Redcliffe", "Thornbury", "Southvale", "Greyfriars", "Linwood", "Penhurst"]
SHOT_BASE = 11.5 / 90.0
C_STR = 0.35          # log-rate sensitivity per 100 Elo-equivalent strength gap
HOME_ADV = 0.12
WINDOW = 15


def new_state(home_elo: float, away_elo: float, home_lineup: float = 0.0, away_lineup: float = 0.0) -> dict:
    return dict(minute=0, home_goals=0, away_goals=0, home_shots=0, away_shots=0, home_sot=0, away_sot=0,
                home_xg=0.0, away_xg=0.0, home_possession=50.0, home_corners=0, away_corners=0,
                home_fouls=0, away_fouls=0, home_yellow=0, away_yellow=0, home_red=0, away_red=0,
                home_pass_acc=80.0, away_pass_acc=80.0, home_elo=home_elo, away_elo=away_elo,
                home_lineup=home_lineup, away_lineup=away_lineup,
                recent_shots_home=0, recent_shots_away=0, recent_xg_home=0.0, recent_xg_away=0.0,
                recent_goals_home=0, recent_goals_away=0)


def advance(st: dict, rng, n_min: int, D: float, tac_h: float = 0.0, tac_a: float = 0.0,
            hist: deque | None = None, log: list | None = None) -> dict:
    """Advance `st` by `n_min` minutes. D = true (or estimated) strength gap in 100-Elo units."""
    minute0 = st["minute"]
    acc = np.zeros(6)  # roll-out accumulator of recent-window totals (when no hist)
    for _ in range(n_min):
        if st["minute"] >= 90:
            break
        m = st["minute"]
        gd = st["home_goals"] - st["away_goals"]
        score_h = math.exp(0.12 * float(np.clip(-gd, -2, 2)))
        score_a = math.exp(0.12 * float(np.clip(gd, -2, 2)))
        time_f = 1.0 + 0.15 * (m / 90.0)
        red_h = math.exp(-0.45 * st["home_red"] + 0.25 * st["away_red"])
        red_a = math.exp(-0.45 * st["away_red"] + 0.25 * st["home_red"])
        lin_h = math.exp(st["home_lineup"] - 0.4 * st["away_lineup"])
        lin_a = math.exp(st["away_lineup"] - 0.4 * st["home_lineup"])
        strength_h = math.exp(0.5 * C_STR * D + HOME_ADV)
        strength_a = math.exp(-0.5 * C_STR * D)
        rate_h = SHOT_BASE * strength_h * score_h * time_f * red_h * lin_h * math.exp(tac_h + 0.55 * tac_a)
        rate_a = SHOT_BASE * strength_a * score_a * time_f * red_a * lin_a * math.exp(tac_a + 0.55 * tac_h)
        sh, sa = rng.poisson(rate_h), rng.poisson(rate_a)
        xg_h = xg_a = 0.0
        goals_h = goals_a = 0
        for side, ns, strength in (("home", sh, strength_h), ("away", sa, strength_a)):
            for _s in range(ns):
                mean = min(0.098 * strength ** 0.9, 0.3)
                a = 1.2
                x = float(rng.beta(a, a * (1 - mean) / mean))
                goal = rng.random() < x
                sot_flag = goal or rng.random() < 0.28
                if log is not None:
                    log.append(dict(minute=m + 1, side=side, xg=round(x, 3), goal=bool(goal), sot=bool(sot_flag)))
                st[f"{side}_shots"] += 1
                if side == "home":
                    xg_h += x
                else:
                    xg_a += x
                if sot_flag:
                    st[f"{side}_sot"] += 1
                if goal:
                    st[f"{side}_goals"] += 1
                    if side == "home":
                        goals_h += 1
                    else:
                        goals_a += 1
                if rng.random() < 0.22:
                    st[f"{side}_corners"] += 1
        st["home_xg"] += xg_h
        st["away_xg"] += xg_a
        # discipline
        for side, tf in (("home", 1.0), ("away", 1.0)):
            if rng.random() < 0.115 * tf:
                st[f"{side}_fouls"] += 1
                if rng.random() < 0.14:
                    st[f"{side}_yellow"] += 1
            if rng.random() < 0.0009:
                st[f"{side}_red"] += 1
        # random in-match injury / key-player change
        for side in ("home", "away"):
            if st[f"{side}_lineup"] > -0.2 and rng.random() < 0.0015:
                st[f"{side}_lineup"] -= 0.22
        # possession and passing quality drift toward strength-driven targets
        target_p = 50 + 8.0 * math.tanh(0.5 * D) + 2.5 + 2.0 * float(np.clip(-gd, -2, 2)) * 0.5
        p_min = float(np.clip(target_p + rng.normal(0, 3.0), 30, 70))
        st["home_possession"] = (st["home_possession"] * m + p_min) / (m + 1) if m else p_min
        pa_h = 80 + 4.0 * math.tanh(0.5 * D) + rng.normal(0, 3.0)
        pa_a = 80 - 4.0 * math.tanh(0.5 * D) + rng.normal(0, 3.0)
        st["home_pass_acc"] = (st["home_pass_acc"] * m + pa_h) / (m + 1) if m else pa_h
        st["away_pass_acc"] = (st["away_pass_acc"] * m + pa_a) / (m + 1) if m else pa_a
        st["minute"] += 1
        tup = (sh, sa, xg_h, xg_a, goals_h, goals_a)
        if hist is not None:
            hist.append(tup)
        else:
            acc += tup
    if hist is not None:
        w = np.array(list(hist)).sum(axis=0) if hist else np.zeros(6)
        _set_recent(st, w)
    else:
        n = st["minute"] - minute0
        keep = max(0.0, (WINDOW - n) / WINDOW)
        old = np.array([st["recent_shots_home"], st["recent_shots_away"], st["recent_xg_home"],
                        st["recent_xg_away"], st["recent_goals_home"], st["recent_goals_away"]], float)
        _set_recent(st, old * keep + acc)
    for k in ("home_possession", "home_pass_acc", "away_pass_acc", "home_xg", "away_xg"):
        st[k] = round(float(st[k]), 3)
    return st


def _set_recent(st: dict, w) -> None:
    st["recent_shots_home"], st["recent_shots_away"] = int(round(w[0])), int(round(w[1]))
    st["recent_xg_home"], st["recent_xg_away"] = round(float(w[2]), 3), round(float(w[3]), 3)
    st["recent_goals_home"], st["recent_goals_away"] = int(round(w[4])), int(round(w[5]))


@dataclass
class FootballMatch:
    match_id: int
    home: int
    away: int
    snaps: list
    final: dict
    result: int  # 0 home, 1 draw, 2 away


def simulate_season(n_matches: int, seed: int = 11, step: int = 5):
    rng = np.random.default_rng(seed)
    nt = len(TEAMS)
    q = rng.normal(0, 0.7, nt)
    elo = EloTable(nt, k=18.0)
    out = []
    for mid in range(n_matches):
        h, a = rng.choice(nt, 2, replace=False)
        D = q[h] - q[a]
        h_lin = -0.2 if rng.random() < 0.18 else 0.0
        a_lin = -0.2 if rng.random() < 0.18 else 0.0
        st = new_state(elo.rating(h), elo.rating(a), h_lin, a_lin)
        hist: deque = deque(maxlen=WINDOW)
        snaps = [dict(st)]
        for _ in range(0, 90, step):
            advance(st, rng, step, D, hist=hist)
            if st["minute"] < 90:
                snaps.append(dict(st))
        res = 0 if st["home_goals"] > st["away_goals"] else (2 if st["home_goals"] < st["away_goals"] else 1)
        for s in snaps:
            s["label"] = res
        out.append(FootballMatch(mid, int(h), int(a), snaps, dict(st), res))
        gd = abs(st["home_goals"] - st["away_goals"])
        score = 1.0 if res == 0 else (0.5 if res == 1 else 0.0)
        elo.update(int(h), int(a), score, margin=1 + 0.4 * min(gd, 3), adv_i=55)
    return out, q


def season_to_rows(matches):
    rows = []
    for m in matches:
        for s in m.snaps:
            r = dict(s)
            r["match_id"] = m.match_id
            rows.append(r)
    return rows
