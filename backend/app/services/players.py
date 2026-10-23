"""Player Lab: predictions vs actuals, strengths/weaknesses and comparison.

Feature construction is shared with training (`app.synth.players`), so serving matches the
training pipeline. Walk-forward predictions use ONLY games before the one being predicted.
"""
from __future__ import annotations

import numpy as np
from sqlmodel import Session, select

from app.ml.predictor import PlayerModels, _load
from app.models_db import Player, PlayerGame
from app.synth import players as pl

DISCLAIMER = "MODEL PREDICTION for the next game - ranges are the 10th-90th percentile of past test errors, not guarantees."


# --------------------------------------------------------------------------------- history helpers
def games(session: Session, pid: int, kind: str) -> list[dict]:
    rows = session.exec(select(PlayerGame).where(PlayerGame.player_id == pid, PlayerGame.kind == kind)
                        .order_by(PlayerGame.game_idx)).all()
    return [r.stats for r in rows]


def _ctx_default(sport: str, p: Player, kind: str, overrides: dict | None) -> dict:
    o = overrides or {}
    if sport == "cricket":
        c = dict(slot=p.attrs.get("slot", 4), opp_strength=0.0, venue_par=158)
    elif sport == "football":
        c = dict(pos=p.role, opp_strength=0.0, team_strength=0.0, home=1)
    else:
        c = dict(pos=p.role, opp_strength=0.0, home=1, b2b=0)
    c.update({k: v for k, v in o.items() if k in c})
    return c


def _feat(sport, kind, hist, ctx):
    if sport == "cricket":
        return pl.bat_features(hist, ctx) if kind == "bat" else pl.bowl_features(hist, ctx)
    return pl.fb_features(hist, ctx) if sport == "football" else pl.bb_features(hist, ctx)


def _kinds(sport: str, p: Player) -> list[str]:
    if sport == "cricket":
        return ["bat"] + (["bowl"] if p.role in ("bowl", "all") else [])
    return ["main"]


TARGETS = {("cricket", "bat"): ["runs", "p50"], ("cricket", "bowl"): ["wickets", "economy"],
           ("football", "main"): ["goals", "assists", "shots"], ("basketball", "main"): ["points", "rebounds", "assists"]}


def _predict_targets(sport: str, kind: str, feats: dict) -> dict:
    out = {}
    for t in TARGETS[(sport, kind)]:
        key = t
        val = PlayerModels.predict(sport, key, feats)
        lo = hi = None
        if t != "p50":
            b = _load(f"player_{sport}_{t}")
            lo, hi = max(val + b["resid_q"][0], 0.0), max(val + b["resid_q"][1], 0.0)
        out[t] = dict(value=round(val, 3), lo=None if lo is None else round(lo, 3), hi=None if hi is None else round(hi, 3))
    return out


def performance_score(sport: str, kind: str, role: str, pred: dict) -> float:
    c = lambda v: float(np.clip(v, 0.0, 1.0))
    v = {k: x["value"] for k, x in pred.items()}
    if sport == "cricket" and kind == "bat":
        s = 0.6 * c(v["runs"] / 45) + 0.4 * c(v["p50"] / 0.35)
    elif sport == "cricket":
        s = 0.55 * c(v["wickets"] / 1.6) + 0.45 * c((10.5 - v["economy"]) / 4.5)
    elif sport == "football":
        w = {"FWD": (0.6 / 0.8, 0.2 / 0.4, 0.2 / 4), "MID": (0.3 / 0.35, 0.4 / 0.4, 0.3 / 2.5), "DEF": (0.3 / 0.15, 0.3 / 0.2, 0.4 / 1.5)}[role]
        s = c(w[0] * v["goals"] + w[1] * v["assists"] + w[2] * v["shots"])
    else:
        s = 0.5 * c(v["points"] / 28) + 0.25 * c(v["rebounds"] / 11) + 0.25 * c(v["assists"] / 8)
    return round(100 * s, 1)


def player_row(p: Player) -> dict:
    return dict(id=p.id, name=p.name, team=p.team, role=p.role, sport=p.sport, attrs=p.attrs)


# --------------------------------------------------------------------------------- public API
def predict_next(session: Session, p: Player, overrides: dict | None = None) -> dict:
    out = {}
    for kind in _kinds(p.sport, p):
        hist = games(session, p.id, kind)
        ctx = _ctx_default(p.sport, p, kind, overrides)
        feats = _feat(p.sport, kind, hist, ctx)
        pred = _predict_targets(p.sport, kind, feats)
        out[kind] = dict(predictions=pred, performance_score=performance_score(p.sport, kind, p.role, pred),
                         context=ctx, features={k: round(v, 3) for k, v in feats.items()}, n_games=len(hist))
    return dict(player=player_row(p), label="MODEL PREDICTION", disclaimer=DISCLAIMER, kinds=out)


def history(session: Session, p: Player) -> dict:
    """Walk-forward MODEL PREDICTION vs ACTUAL RESULT for each past game."""
    out = {}
    for kind in _kinds(p.sport, p):
        hist = games(session, p.id, kind)
        rows = []
        for i in range(3, len(hist)):
            g = hist[i]
            if p.sport == "cricket":
                ctx = dict(slot=g.get("slot", p.attrs.get("slot", 4)), opp_strength=g["opp_strength"], venue_par=g["venue_par"])
            elif p.sport == "football":
                ctx = dict(pos=p.role, opp_strength=g["opp_strength"], team_strength=g["team_strength"], home=g["home"])
            else:
                ctx = dict(pos=p.role, opp_strength=g["opp_strength"], home=g["home"], b2b=g["b2b"])
            pred = _predict_targets(p.sport, kind, _feat(p.sport, kind, hist[:i], ctx))
            actual = {t: g[t] for t in TARGETS[(p.sport, kind)] if t != "p50"}
            if p.sport == "cricket" and kind == "bat":
                actual["p50"] = int(g["runs"] >= 50)
            rows.append(dict(game=i, predicted={k: v["value"] for k, v in pred.items()}, actual=actual,
                             context={k: v for k, v in g.items() if k in ("venue", "opp_strength", "home", "minutes", "overs")}))
        out[kind] = rows
    return dict(player=player_row(p), kinds=out, label_pred="MODEL PREDICTION", label_actual="ACTUAL RESULT")


# --------------------------------------------------------------------------------- strengths / weaknesses
METRICS = {  # (sport, kind) -> list of (feature, label, higher_is_better)
    ("cricket", "bat"): [("bat_avg", "Batting average", True), ("bat_sr", "Strike rate", True), ("bat_form", "Recent form (runs)", True)],
    ("cricket", "bowl"): [("bowl_wpo", "Wickets per over", True), ("bowl_econ", "Economy", False), ("bowl_form_econ", "Recent economy", False)],
    ("football", "main"): [("fb_shots90", "Shots / 90", True), ("fb_goals90", "Goals / 90", True), ("fb_ast90", "Assists / 90", True),
                           ("fb_form_shots90", "Recent shot volume", True)],
    ("basketball", "main"): [("bb_pts_pm", "Scoring rate", True), ("bb_reb_pm", "Rebounding rate", True), ("bb_ast_pm", "Playmaking rate", True),
                             ("bb_form_pts_pm", "Recent scoring form", True)],
}


def _profile(session: Session, p: Player, kind: str) -> dict:
    hist = games(session, p.id, kind)
    return _feat(p.sport, kind, hist, _ctx_default(p.sport, p, kind, None))


def _peers(session: Session, p: Player, kind: str) -> list[Player]:
    q = select(Player).where(Player.sport == p.sport)
    ps = session.exec(q).all()
    if p.sport in ("football", "basketball"):
        ps = [x for x in ps if x.role == p.role]
    elif kind == "bowl":
        ps = [x for x in ps if x.role in ("bowl", "all")]
    else:
        ps = [x for x in ps if x.role in ("bat", "all", "bowl")]
    return ps


def percentiles(session: Session, p: Player, kind: str) -> list[dict]:
    peers = _peers(session, p, kind)
    profiles = {x.id: _profile(session, x, kind) for x in peers}
    me = profiles.get(p.id) or _profile(session, p, kind)
    out = []
    for feat, label, hib in METRICS[(p.sport, kind)]:
        vals = np.array([pr[feat] for pr in profiles.values()])
        mu, sd = vals.mean(), vals.std() or 1.0
        z = (me[feat] - mu) / sd * (1 if hib else -1)
        pct = float((vals <= me[feat]).mean() * 100) if hib else float((vals >= me[feat]).mean() * 100)
        out.append(dict(feature=feat, label=label, value=round(float(me[feat]), 3), peer_mean=round(float(mu), 3),
                        z=round(float(z), 2), percentile=round(pct, 0)))
    return out


def strengths_weaknesses(session: Session, p: Player) -> dict:
    res = {}
    for kind in _kinds(p.sport, p):
        rows = percentiles(session, p, kind)
        strengths = [r for r in rows if r["z"] >= 0.5]
        weaknesses = [r for r in rows if r["z"] <= -0.5]
        notes = []
        # form-vs-career drop: a simple, transparent weakness-detection rule
        if p.sport == "cricket" and kind == "bat":
            a, f = next(r for r in rows if r["feature"] == "bat_avg"), next(r for r in rows if r["feature"] == "bat_form")
            if f["value"] < 0.75 * a["value"]:
                notes.append(f"Recent form ({f['value']:.0f}) is well below career average ({a['value']:.0f}).")
            elif f["value"] > 1.25 * a["value"]:
                notes.append(f"Recent form ({f['value']:.0f}) is running above career average ({a['value']:.0f}).")
        res[kind] = dict(metrics=rows, strengths=strengths, weaknesses=weaknesses, notes=notes,
                         method="z-score of the player's shrunk career/form statistics against role peers in the database "
                                "(|z| ≥ 0.5 flagged). Weaker-is-better metrics (economy) are sign-flipped.")
    return dict(player=player_row(p), kinds=res)


def compare(session: Session, a: Player, b: Player) -> dict:
    if a.sport != b.sport:
        raise ValueError("Players must be from the same sport")
    kind = "bat" if a.sport == "cricket" else "main"
    if a.sport == "cricket" and (a.role == "bowl" and b.role == "bowl"):
        kind = "bowl"
    out = {}
    for p in (a, b):
        k = kind if kind in _kinds(p.sport, p) else _kinds(p.sport, p)[0]
        out[p.id] = dict(player=player_row(p), kind=k, percentiles=percentiles(session, p, k),
                         next=predict_next(session, p)["kinds"].get(k))
    return dict(sport=a.sport, kind=kind, a=out[a.id], b=out[b.id])
