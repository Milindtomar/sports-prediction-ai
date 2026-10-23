"""Synthetic player careers + the *shared* pre-match feature builders.

`*_features(history, ctx)` is used by BOTH the offline dataset builder and the
serving API, which prevents train/serve skew. A feature may only read games
strictly before the one being predicted (`history` is the prior games list).
All names are fictional.
"""
from __future__ import annotations

import math

import numpy as np

from .common import player_name
from .cricket import VENUE_NAMES, VENUES

K_SMOOTH = 5.0  # pseudo-games for empirical-Bayes shrinkage of rolling averages


def _shrunk_mean(vals: list[float], prior: float, k: float = K_SMOOTH) -> float:
    return (sum(vals) + prior * k) / (len(vals) + k)


def _form(vals: list[float], prior: float, n: int = 5) -> float:
    return _shrunk_mean(vals[-n:], prior, 2.0)


# ---------------------------------------------------------------- cricket batting
BAT_PRIOR_RUNS, BAT_PRIOR_SR = 22.0, 128.0
SLOT_F = {1: 1.12, 2: 1.08, 3: 1.06, 4: 1.0, 5: 0.9, 6: 0.78, 7: 0.62}


def bat_features(hist: list[dict], ctx: dict) -> dict:
    runs = [g["runs"] for g in hist]
    balls = [g["balls"] for g in hist]
    sr_vals = [100.0 * r / max(b, 1) for r, b in zip(runs, balls)]
    return dict(
        bat_avg=_shrunk_mean(runs, BAT_PRIOR_RUNS),
        bat_sr=_shrunk_mean(sr_vals, BAT_PRIOR_SR),
        bat_form=_form(runs, BAT_PRIOR_RUNS),
        bat_innings=float(len(hist)),
        bat_slot=float(ctx["slot"]),
        opp_bowling=float(ctx["opp_strength"]),
        venue_par=float(ctx["venue_par"]),
    )


BAT_FEATURES = ["bat_avg", "bat_sr", "bat_form", "bat_innings", "bat_slot", "opp_bowling", "venue_par"]

# ---------------------------------------------------------------- cricket bowling
BOWL_PRIOR_WPO, BOWL_PRIOR_ECON = 0.28, 8.4


def bowl_features(hist: list[dict], ctx: dict) -> dict:
    ov = [g["overs"] for g in hist]
    wpo = [g["wickets"] / max(g["overs"], 1) for g in hist]
    econ = [g["economy"] for g in hist]
    return dict(
        bowl_wpo=_shrunk_mean(wpo, BOWL_PRIOR_WPO),
        bowl_econ=_shrunk_mean(econ, BOWL_PRIOR_ECON),
        bowl_form_econ=_form(econ, BOWL_PRIOR_ECON),
        bowl_form_wpo=_form(wpo, BOWL_PRIOR_WPO),
        bowl_overs=_shrunk_mean(ov, 3.6),
        opp_batting=float(ctx["opp_strength"]),
        venue_par=float(ctx["venue_par"]),
    )


BOWL_FEATURES = ["bowl_wpo", "bowl_econ", "bowl_form_econ", "bowl_form_wpo", "bowl_overs", "opp_batting", "venue_par"]

# ---------------------------------------------------------------- football
FB_POS = {"FWD": 0, "MID": 1, "DEF": 2}
FB_PRIORS = {"FWD": (3.0, 0.40, 0.10), "MID": (1.5, 0.12, 0.17), "DEF": (0.7, 0.04, 0.05)}  # shots90, goals90, ast90


def fb_features(hist: list[dict], ctx: dict) -> dict:
    pos = ctx["pos"]
    p_s, p_g, p_a = FB_PRIORS[pos]
    mins = [g["minutes"] for g in hist]
    tot_min = max(sum(mins), 1)
    def per90(key, prior):
        return (sum(g[key] for g in hist) + prior * 90.0 * K_SMOOTH / 90.0 * 1.0) / ((tot_min / 90.0) + K_SMOOTH)
    shots90, goals90, ast90 = per90("shots", p_s), per90("goals", p_g), per90("assists", p_a)
    last = hist[-5:]
    lm = max(sum(g["minutes"] for g in last), 1)
    form_shots90 = (sum(g["shots"] for g in last) + p_s * 2) / (lm / 90.0 + 2)
    return dict(
        fb_pos=float(FB_POS[pos]), fb_shots90=shots90, fb_goals90=goals90, fb_ast90=ast90,
        fb_form_shots90=form_shots90, fb_exp_minutes=_shrunk_mean(mins, 78.0, 3.0),
        fb_opp_def=float(ctx["opp_strength"]), fb_team_att=float(ctx["team_strength"]), fb_home=float(ctx["home"]),
    )


FB_FEATURES = ["fb_pos", "fb_shots90", "fb_goals90", "fb_ast90", "fb_form_shots90", "fb_exp_minutes",
               "fb_opp_def", "fb_team_att", "fb_home"]

# ---------------------------------------------------------------- basketball
BB_POS = {"G": 0, "F": 1, "C": 2}
BB_PRIORS = {"G": (0.52, 0.12, 0.17), "F": (0.50, 0.19, 0.10), "C": (0.48, 0.28, 0.07)}  # pts, reb, ast per minute


def bb_features(hist: list[dict], ctx: dict) -> dict:
    pos = ctx["pos"]
    pp, pr, pa = BB_PRIORS[pos]
    tot_min = max(sum(g["minutes"] for g in hist), 1.0)
    def pm(key, prior):
        return (sum(g[key] for g in hist) + prior * 36.0 * 3) / (tot_min + 36.0 * 3)
    last = hist[-5:]
    lm = max(sum(g["minutes"] for g in last), 1.0)
    return dict(
        bb_pos=float(BB_POS[pos]), bb_pts_pm=pm("points", pp), bb_reb_pm=pm("rebounds", pr), bb_ast_pm=pm("assists", pa),
        bb_form_pts_pm=(sum(g["points"] for g in last) + pp * 36) / (lm + 36),
        bb_exp_minutes=_shrunk_mean([g["minutes"] for g in hist], 30.0, 3.0),
        bb_opp_def=float(ctx["opp_strength"]), bb_home=float(ctx["home"]), bb_b2b=float(ctx.get("b2b", 0)),
    )


BB_FEATURES = ["bb_pos", "bb_pts_pm", "bb_reb_pm", "bb_ast_pm", "bb_form_pts_pm", "bb_exp_minutes",
               "bb_opp_def", "bb_home", "bb_b2b"]


# ================================================================ generators
def _nb(rng, mean: float, shape: float = 0.8) -> int:
    mean = max(mean, 0.05)
    p = shape / (shape + mean)
    return int(rng.negative_binomial(shape, p))


def gen_cricket_player(rng, used: set, role: str | None = None, n_games: int = 36) -> dict:
    role = role or rng.choice(["bat", "bat", "all", "bowl"])
    mu0 = float(np.clip(rng.lognormal(math.log(24 if role != "bowl" else 11), 0.33), 6, 55))
    sr0 = float(np.clip(rng.normal(132, 14), 95, 180))
    slot = int(rng.choice([1, 2, 3, 4, 5, 6, 7], p=[.16, .16, .15, .15, .14, .12, .12])) if role != "bowl" else int(rng.choice([7, 8], p=[.5, .5]))
    slot = min(slot, 7)
    wpo0 = float(np.clip(rng.normal(0.30, 0.07), 0.12, 0.55)) if role in ("bowl", "all") else 0.0
    econ0 = float(np.clip(rng.normal(8.3, 0.7), 6.2, 10.5)) if role in ("bowl", "all") else 0.0
    return dict(name=player_name(rng, used), role=role, mu0=mu0, sr0=sr0, slot=slot, wpo0=wpo0, econ0=econ0,
                form_sd=0.12, n_games=n_games)


def simulate_cricket_career(p: dict, rng) -> tuple[list[dict], list[dict]]:
    """Returns (bat_games, bowl_games). Each includes context for later feature building."""
    bat, bowl = [], []
    form = 0.0
    for gi in range(p["n_games"]):
        form = 0.8 * form + rng.normal(0, p["form_sd"])
        venue = VENUE_NAMES[rng.integers(len(VENUE_NAMES))]
        par = VENUES[venue][1]
        opp = float(rng.normal(0, 0.8))
        if p["role"] != "bowl" or p["slot"] <= 7:
            sf = SLOT_F.get(p["slot"], 0.5)
            mean = p["mu0"] * sf * math.exp(-0.15 * opp + form) * (par / 158.0) ** 1.2
            if p["role"] == "bowl":
                mean *= 0.6
            runs = _nb(rng, mean, 0.8)
            sr = p["sr0"] * math.exp(rng.normal(0, 0.15)) * (par / 158.0) ** 0.5
            balls = max(1, int(round(runs / (sr / 100.0)))) if runs > 0 else int(rng.integers(1, 4))
            bat.append(dict(game=gi, runs=runs, balls=balls, slot=p["slot"], opp_strength=opp, venue_par=par,
                            venue=venue))
        if p["role"] in ("bowl", "all"):
            overs = int(rng.choice([4, 4, 4, 3, 2])) if p["role"] == "bowl" else int(rng.choice([2, 3, 4], p=[.3, .4, .3]))
            lam = overs * p["wpo0"] * math.exp(0.12 * (-opp) + 0.5 * form)
            wk = int(rng.poisson(lam))
            econ = p["econ0"] + 0.9 * (par - 158) / 20.0 + 0.3 * (-opp) + rng.normal(0, 1.6 / math.sqrt(overs)) - 1.2 * form
            econ = float(np.clip(econ, 3.0, 16.0))
            bowl.append(dict(game=gi, overs=overs, wickets=wk, economy=round(econ, 2), opp_strength=-opp,
                             venue_par=par, venue=venue))
    return bat, bowl


def gen_football_player(rng, used: set, pos: str | None = None, n_games: int = 36) -> dict:
    pos = pos or rng.choice(["FWD", "MID", "MID", "DEF", "DEF"])
    s90, g90, a90 = FB_PRIORS[pos]
    skill = float(np.clip(rng.lognormal(0, 0.3), 0.5, 2.0))
    return dict(name=player_name(rng, used), pos=pos, shots90=s90 * skill ** 0.7, conv=(g90 / s90) * skill ** 0.5,
                ast90=a90 * skill ** 0.8, starter=float(rng.uniform(0.6, 0.97)), n_games=n_games, skill=skill)


def simulate_football_career(p: dict, rng) -> list[dict]:
    out, form = [], 0.0
    for gi in range(p["n_games"]):
        form = 0.7 * form + rng.normal(0, 0.1)
        opp = float(rng.normal(0, 0.7))     # opponent defensive strength (higher = tougher)
        team = float(rng.normal(0, 0.7))    # own team attacking strength
        home = int(rng.random() < 0.5)
        minutes = 90 if rng.random() < p["starter"] else int(rng.choice([0, 20, 35, 55, 70, 80]))
        if rng.random() < 0.03:
            minutes = 0
        f = (minutes / 90.0) * math.exp(0.35 * 0.5 * (team - opp) + 0.08 * home + form)
        shots = int(rng.poisson(p["shots90"] * f))
        goals = int(rng.binomial(shots, min(p["conv"] * math.exp(-0.1 * opp), 0.6))) if shots else 0
        assists = int(rng.poisson(p["ast90"] * f))
        out.append(dict(game=gi, minutes=minutes, shots=shots, goals=goals, assists=assists, opp_strength=opp,
                        team_strength=team, home=home, pos=p["pos"]))
    return out


def gen_basketball_player(rng, used: set, pos: str | None = None, n_games: int = 36) -> dict:
    pos = pos or rng.choice(["G", "G", "F", "F", "C"])
    pp, pr, pa = BB_PRIORS[pos]
    skill = float(np.clip(rng.lognormal(0, 0.28), 0.55, 1.9))
    return dict(name=player_name(rng, used), pos=pos, pts_pm=pp * skill, reb_pm=pr * skill ** 0.8,
                ast_pm=pa * skill ** 0.8, minutes0=float(np.clip(18 + 14 * (skill - 0.6), 12, 38)),
                n_games=n_games, skill=skill)


def simulate_basketball_career(p: dict, rng) -> list[dict]:
    out, form = [], 0.0
    for gi in range(p["n_games"]):
        form = 0.7 * form + rng.normal(0, 0.1)
        opp = float(rng.normal(0, 0.7))
        home = int(rng.random() < 0.5)
        b2b = int(rng.random() < 0.15)
        minutes = float(np.clip(rng.normal(p["minutes0"] - 2.5 * b2b, 4.5), 4, 42))
        f = math.exp(-0.06 * opp + 0.03 * home + form - 0.04 * b2b)
        points = int(rng.poisson(max(p["pts_pm"] * minutes * f, 0.1)))
        rebs = int(rng.poisson(max(p["reb_pm"] * minutes * math.exp(0.5 * form), 0.1)))
        asts = int(rng.poisson(max(p["ast_pm"] * minutes * math.exp(0.5 * form), 0.1)))
        out.append(dict(game=gi, minutes=round(minutes, 1), points=points, rebounds=rebs, assists=asts,
                        opp_strength=opp, home=home, b2b=b2b, pos=p["pos"]))
    return out
