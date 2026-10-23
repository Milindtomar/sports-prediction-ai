"""Pure feature-engineering functions: raw match state (dict) -> model features.

These are the ONLY place features are computed, for both offline training and the
online API, so there is no train/serve skew. Every feature uses information available
at the snapshot instant (no final score / result / future events) - see the leakage
section of ML_DOCUMENTATION.md.
"""
from __future__ import annotations

import math

BALLS = 120


# ------------------------------------------------------------------ cricket
def cricket_target(s: dict) -> int:
    """Effective target: the real target in innings 2, venue-par + 1 in innings 1."""
    if s["innings"] == 2 and s.get("target"):
        return int(s["target"])
    return int(s["venue_par"]) + 1


CRICKET_FEATURES = ["innings", "runs", "wickets_remaining", "balls_remaining", "crr", "runs_required", "rrr",
                    "rr_diff", "recent_rr", "recent_wickets", "partnership_runs", "resources", "elo_diff",
                    "venue_par", "phase"]


def cricket_features(s: dict) -> dict:
    bb, wk = int(s["balls_bowled"]), int(s["wickets"])
    rem = BALLS - bb
    target = cricket_target(s)
    req = target - s["runs"]
    crr = s["runs"] * 6.0 / bb if bb > 0 else s["venue_par"] / 20.0
    rrr = min(req * 6.0 / rem, 36.0) if rem > 0 else (36.0 if req > 0 else 0.0)
    rrr = max(rrr, 0.0)
    recent_rr = s["recent_runs"] * 6.0 / min(bb, 12) if bb > 0 else crr
    return dict(
        innings=float(s["innings"]), runs=float(s["runs"]), wickets_remaining=float(10 - wk),
        balls_remaining=float(rem), crr=crr, runs_required=float(req), rrr=rrr, rr_diff=crr - rrr,
        recent_rr=recent_rr, recent_wickets=float(s["recent_wickets"]), partnership_runs=float(s["partnership_runs"]),
        resources=(rem / BALLS) ** 0.85 * (1 - (wk / 10.0) ** 1.6),
        elo_diff=(s["batting_elo"] - s["bowling_elo"]) / 100.0, venue_par=float(s["venue_par"]),
        phase=float(0 if bb < 36 else (1 if bb < 96 else 2)),
    )


# ------------------------------------------------------------------ football
FOOTBALL_FEATURES = ["minute", "minutes_remaining", "goal_diff", "home_goals", "away_goals", "lead_security",
                     "shots_diff", "sot_diff", "xg_diff", "home_possession", "corners_diff", "fouls_diff",
                     "yellow_diff", "red_diff", "pass_acc_diff", "elo_diff", "lineup_diff"]


def football_features(s: dict) -> dict:
    rem = max(90 - s["minute"], 0)
    gd = s["home_goals"] - s["away_goals"]
    return dict(
        minute=float(s["minute"]), minutes_remaining=float(rem), goal_diff=float(gd),
        home_goals=float(s["home_goals"]), away_goals=float(s["away_goals"]),
        lead_security=gd / math.sqrt(max(rem, 1) / 90.0),
        shots_diff=float(s["home_shots"] - s["away_shots"]), sot_diff=float(s["home_sot"] - s["away_sot"]),
        xg_diff=float(s["home_xg"] - s["away_xg"]), home_possession=float(s["home_possession"]),
        corners_diff=float(s["home_corners"] - s["away_corners"]), fouls_diff=float(s["home_fouls"] - s["away_fouls"]),
        yellow_diff=float(s["home_yellow"] - s["away_yellow"]), red_diff=float(s["home_red"] - s["away_red"]),
        pass_acc_diff=float(s["home_pass_acc"] - s["away_pass_acc"]),
        elo_diff=(s["home_elo"] - s["away_elo"]) / 100.0, lineup_diff=float(s["home_lineup"] - s["away_lineup"]),
    )


# ------------------------------------------------------------------ basketball
BASKETBALL_FEATURES = ["time_remaining", "quarter", "score_diff", "lead_security", "fg_pct_diff", "tp_pct_diff",
                       "ft_pct_diff", "reb_diff", "ast_diff", "tov_diff", "foul_diff", "possession", "eff_diff",
                       "elo_diff", "lineup_diff"]
GAME_SEC = 2880


def _pct(m, a, prior, k):
    return (m + prior * k) / (a + k)


def _eff(s, side):
    poss = s[f"{side}_fga"] + 0.44 * s[f"{side}_fta"] + s[f"{side}_tov"]
    return (s[f"{side}_score"] + 1.0 * 10) / (poss + 10)


def basketball_features(s: dict) -> dict:
    rem = max(GAME_SEC - s["elapsed_sec"], 0)
    diff = s["home_score"] - s["away_score"]
    h, a = "home", "away"
    return dict(
        time_remaining=float(rem), quarter=float(min(4, s["elapsed_sec"] // 720 + 1)), score_diff=float(diff),
        lead_security=diff / math.sqrt(max(rem, 30) / 60.0),
        fg_pct_diff=_pct(s["home_fgm"], s["home_fga"], .45, 6) - _pct(s["away_fgm"], s["away_fga"], .45, 6),
        tp_pct_diff=_pct(s["home_3pm"], s["home_3pa"], .35, 4) - _pct(s["away_3pm"], s["away_3pa"], .35, 4),
        ft_pct_diff=_pct(s["home_ftm"], s["home_fta"], .77, 4) - _pct(s["away_ftm"], s["away_fta"], .77, 4),
        reb_diff=float(s["home_reb"] - s["away_reb"]), ast_diff=float(s["home_ast"] - s["away_ast"]),
        tov_diff=float(s["home_tov"] - s["away_tov"]), foul_diff=float(s["home_fouls"] - s["away_fouls"]),
        possession=1.0 if s["possession"] == 0 else -1.0, eff_diff=_eff(s, h) - _eff(s, a),
        elo_diff=(s["home_elo"] - s["away_elo"]) / 100.0, lineup_diff=float(s["home_lineup"] - s["away_lineup"]),
    )


FEATURE_FUNCS = {"cricket": (cricket_features, CRICKET_FEATURES), "football": (football_features, FOOTBALL_FEATURES),
                 "basketball": (basketball_features, BASKETBALL_FEATURES)}
