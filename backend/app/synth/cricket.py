"""Synthetic T20 cricket generator (ball-by-ball) + in-play state advance.

Generative story (documented in ML_DOCUMENTATION.md):
* each team has a latent strength (in units of 100 Elo points);
* per-ball outcome probabilities depend on batting-minus-bowling strength `d`,
  venue scoring factor, match phase, wickets lost and batting aggression;
* chasing sides adapt aggression to the required rate, batting-first sides stay
  near par - this produces the realistic "required rate up => wickets up" loop.

The same `advance()` routine drives dataset generation, coach roll-outs and
what-if events, so training and serving share one dynamics model.
"""
from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass

import numpy as np

from .common import EloTable

TEAMS = ["Harbor Kings", "Crimson Falcons", "Indigo Titans", "Emerald Rhinos", "Golden Panthers",
         "Silver Wolves", "Midnight Hawks", "Saffron Stallions", "Coral Sharks", "Onyx Vipers"]
# name -> (scoring factor, par first-innings score)
VENUES = {
    "Harbour Oval": (1.00, 158), "Granite Park": (0.91, 144), "Skyline Ground": (1.10, 174),
    "Riverside Arena": (1.04, 164), "Dune Stadium": (0.95, 150), "Old Mill Ground": (0.88, 139),
    "Summit Park": (1.07, 169), "Lagoon Oval": (0.98, 155),
}
VENUE_NAMES = list(VENUES)
RUNS = np.array([0, 1, 2, 3, 4, 6])
BASE_W = np.array([0.40, 0.34, 0.07, 0.01, 0.11, 0.07])
PHASE_BOUND = (1.15, 0.92, 1.25)
PHASE_WKT = (0.85, 0.95, 1.25)
BALLS = 120
D_PER_ELO100 = 0.8  # maps estimated Elo gap (100s) -> ball-level skill gap


def phase_of(balls_bowled: int) -> int:
    return 0 if balls_bowled < 36 else (1 if balls_bowled < 96 else 2)


def ball_dist(d: float, venue_f: float, phase: int, wkts: int, aggr: float):
    """Return (p_wicket, run probabilities over RUNS) for the next legal ball."""
    bm = math.exp(0.10 * d) * venue_f * PHASE_BOUND[phase] * aggr
    w = BASE_W.copy()
    w[4] *= bm
    w[5] *= bm * 1.1
    w[0] *= 1.0 / (aggr ** 0.8) / math.exp(0.05 * d)
    tail = 1 - 0.04 * max(0, wkts - 5)
    w[4:] *= tail
    w = w / w.sum()
    p_w = 0.048 * math.exp(-0.22 * d) * PHASE_WKT[phase] * aggr ** 1.2 * (1 + 0.06 * max(0, wkts - 5))
    return min(p_w, 0.35), w


def chase_aggression(runs: int, balls_bowled: int, target: int | None, rng) -> float:
    """Behavioural model of batting intent."""
    if target is None:  # batting first: slightly more intent at the death
        base = 1.0 + (0.12 if balls_bowled >= 96 else 0.0)
    else:
        left = max(BALLS - balls_bowled, 1)
        need_rate = (target - runs) / left * 6.0
        base = float(np.clip((max(need_rate, 1.0) / 8.0) ** 0.6, 0.8, 1.5))
    return float(np.clip(base * math.exp(rng.normal(0, 0.08)), 0.7, 1.7))


def new_innings_state(innings: int, target: int | None = None) -> dict:
    return dict(innings=innings, runs=0, wickets=0, balls_bowled=0, target=target,
                partnership_runs=0, partnership_balls=0, recent_runs=0, recent_wickets=0,
                recent_boundaries=0)


def advance(st: dict, rng, n_balls: int, d: float, venue_f: float, aggr: float | None = None,
            hist: deque | None = None, log: list | None = None, aggr_mult: float = 1.0) -> dict:
    """Advance a state dict by up to `n_balls` legal balls. Mutates and returns `st`.

    `hist` (deque, maxlen=12) gives exact recent-window stats during dataset
    generation. When absent (API roll-outs) the window is updated by
    exponential-decay approximation, exact when n_balls >= 12.
    """
    t = st.get("target")
    for _ in range(n_balls):
        if st["balls_bowled"] >= BALLS or st["wickets"] >= 10:
            break
        if t is not None and st["runs"] >= t:
            break
        a = (aggr if aggr is not None else chase_aggression(st["runs"], st["balls_bowled"], t, rng)) * aggr_mult
        p_w, w = ball_dist(d, venue_f, phase_of(st["balls_bowled"]), st["wickets"], a)
        u = rng.random()
        if u < p_w:
            runs, wk = 0, 1
        else:
            runs, wk = int(RUNS[np.searchsorted(np.cumsum(w), rng.random(), side="right").clip(0, 5)]), 0
        st["balls_bowled"] += 1
        st["runs"] += runs
        st["wickets"] += wk
        if wk:
            st["partnership_runs"] = 0
            st["partnership_balls"] = 0
        else:
            st["partnership_runs"] += runs
            st["partnership_balls"] += 1
        boundary = 1 if runs >= 4 else 0
        if log is not None:
            log.append(dict(ball=st["balls_bowled"], runs=runs, wicket=wk))
        if hist is not None:
            hist.append((runs, wk, boundary))
            st["recent_runs"] = sum(h[0] for h in hist)
            st["recent_wickets"] = sum(h[1] for h in hist)
            st["recent_boundaries"] = sum(h[2] for h in hist)
        else:
            st["recent_runs"] = int(round(st["recent_runs"] * 11 / 12 + runs))
            st["recent_wickets"] = int(round(st["recent_wickets"] * 11 / 12 + wk))
            st["recent_boundaries"] = int(round(st["recent_boundaries"] * 11 / 12 + boundary))
    return st


@dataclass
class CricketMatch:
    match_id: int
    team_a: int
    team_b: int
    venue: str
    first_batting: int
    elo_a: float
    elo_b: float
    inn1: list  # snapshots (dict)
    inn2: list
    score1: int
    score2: int
    wkts1: int
    wkts2: int
    batting_first_won: bool


def simulate_season(n_matches: int, seed: int = 7):
    """Simulate a chronological season. Returns (list[CricketMatch], true_skill)."""
    rng = np.random.default_rng(seed)
    n_t = len(TEAMS)
    skill = rng.normal(0, 0.6, n_t)  # latent, unobserved by the models
    elo = EloTable(n_t, k=14.0)
    out: list[CricketMatch] = []
    for mid in range(n_matches):
        a, b = rng.choice(n_t, 2, replace=False)
        venue = VENUE_NAMES[rng.integers(len(VENUE_NAMES))]
        vf, par = VENUES[venue]
        bf, bs = (a, b) if rng.random() < 0.5 else (b, a)
        ea, eb = elo.rating(a), elo.rating(b)
        # innings 1
        d1 = D_PER_ELO100 * (skill[bf] - skill[bs])
        st = new_innings_state(1)
        hist: deque = deque(maxlen=12)
        s1 = [dict(st)]
        for _ in range(0, BALLS, 6):
            advance(st, rng, 6, d1, vf, hist=hist)
            if st["balls_bowled"] % 6 == 0 and st["balls_bowled"] < BALLS and st["wickets"] < 10:
                s1.append(dict(st))
            if st["balls_bowled"] >= BALLS or st["wickets"] >= 10:
                break
        score1, w1 = st["runs"], st["wickets"]
        # innings 2
        target = score1 + 1
        d2 = D_PER_ELO100 * (skill[bs] - skill[bf])
        st2 = new_innings_state(2, target)
        hist2: deque = deque(maxlen=12)
        s2 = [dict(st2)]
        for _ in range(0, BALLS, 6):
            advance(st2, rng, 6, d2, vf, hist=hist2)
            done = st2["balls_bowled"] >= BALLS or st2["wickets"] >= 10 or st2["runs"] >= target
            if not done and st2["balls_bowled"] % 6 == 0:
                s2.append(dict(st2))
            if done:
                break
        score2, w2 = st2["runs"], st2["wickets"]
        chase_won = score2 >= target
        # label bookkeeping (label = does the CURRENT batting side win?)
        for s in s1:
            s.update(batting_elo=elo.rating(bf), bowling_elo=elo.rating(bs), venue=venue, venue_par=par,
                     label=int(not chase_won))
        for s in s2:
            s.update(batting_elo=elo.rating(bs), bowling_elo=elo.rating(bf), venue=venue, venue_par=par,
                     label=int(chase_won))
        out.append(CricketMatch(mid, int(a), int(b), venue, int(bf), ea, eb, s1, s2, score1, score2, w1, w2,
                                not chase_won))
        # Elo is updated AFTER the match - no leakage into its own snapshots
        elo.update(int(bf), int(bs), 0.0 if chase_won else 1.0)
    return out, skill


def season_to_rows(matches: list[CricketMatch]) -> list[dict]:
    rows = []
    for m in matches:
        for s in m.inn1 + m.inn2:
            r = dict(s)
            r["match_id"] = m.match_id
            rows.append(r)
    return rows
