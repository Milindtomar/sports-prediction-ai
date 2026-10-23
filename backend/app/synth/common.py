"""Shared helpers for the synthetic data generators.

Everything here is deterministic given a seed. The generators intentionally
expose only information that would be available at prediction time; the
pre-match team rating is an Elo value computed *chronologically* from earlier
matches, never from the match being predicted (see ML_DOCUMENTATION.md).
"""
from __future__ import annotations

import numpy as np

ELO_INIT = 1500.0


def elo_expected(diff: float) -> float:
    """Expected score for the side with rating advantage `diff` (400-point scale)."""
    return 1.0 / (1.0 + 10.0 ** (-diff / 400.0))


class EloTable:
    """Minimal Elo rating table updated strictly after each match."""

    def __init__(self, n_teams: int, k: float = 16.0):
        self.r = np.full(n_teams, ELO_INIT, dtype=float)
        self.k = k

    def rating(self, i: int) -> float:
        return float(self.r[i])

    def update(self, i: int, j: int, score_i: float, margin: float = 1.0, adv_i: float = 0.0) -> None:
        exp_i = elo_expected(self.r[i] - self.r[j] + adv_i)
        delta = self.k * margin * (score_i - exp_i)
        self.r[i] += delta
        self.r[j] -= delta


def chrono_split(match_ids: np.ndarray, train: float = 0.70, val: float = 0.15):
    """Chronological split by match id (ids increase with time).

    Returns boolean masks (train, val, test). Whole matches stay in one fold, so
    snapshots of the same match never straddle the boundary.
    """
    ids = np.unique(match_ids)
    n = len(ids)
    t_end = ids[int(n * train) - 1]
    v_end = ids[int(n * (train + val)) - 1]
    return match_ids <= t_end, (match_ids > t_end) & (match_ids <= v_end), match_ids > v_end


FIRST = ["Aarav", "Liam", "Mateo", "Kofi", "Noah", "Ravi", "Lucas", "Omar", "Diego", "Yuki", "Elias", "Tariq",
         "Mason", "Arjun", "Felix", "Idris", "Kai", "Luca", "Nico", "Zane", "Rohan", "Dario", "Emil", "Hugo"]
LAST = ["Verma", "Okafor", "Silva", "Novak", "Hart", "Mehta", "Duarte", "Kovac", "Reyes", "Tanaka", "Brandt",
        "Haddad", "Mercer", "Iyer", "Lund", "Mbeki", "Sato", "Ferrari", "Quinn", "Bose", "Petrov", "Vale", "Ortiz", "Khan"]


def player_name(rng: np.random.Generator, used: set[str]) -> str:
    """Fictional player names (no real athletes are depicted anywhere)."""
    for _ in range(200):
        n = f"{FIRST[rng.integers(len(FIRST))]} {LAST[rng.integers(len(LAST))]}"
        if n not in used:
            used.add(n)
            return n
    n = f"Player {len(used)}"
    used.add(n)
    return n
