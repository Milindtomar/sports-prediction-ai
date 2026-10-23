"""AI Coach: Monte-Carlo roll-outs of candidate actions scored by the trained model.

For each action we simulate the next few minutes/overs many times with the same
generative dynamics used to create the training data, push every resulting state
through the prediction pipeline, and compare the mean objective (win probability, or
expected points in football). Confidence is the probability that the best action
truly beats the runner-up *under this simulation model*; it is not a guarantee.
"""
from __future__ import annotations

import json
import math
import zlib

import numpy as np

from app.ml.predictor import get_win_predictor
from app.sports.registry import get_adapter

FRAMING = "AI-assisted recommendation based on simulated roll-outs - not a guaranteed correct strategy."


def _phi(z: float) -> float:
    return 0.5 * (1 + math.erf(z / math.sqrt(2)))


def coach(sport: str, raw_state: dict, side: str | None = None, n: int = 60) -> dict:
    from app.services.analysis import analyze  # local import avoids a cycle at module load

    a = get_adapter(sport)
    state = a.validate(raw_state)
    sides = a.coach_sides(state)
    side = side if side in sides else sides[0]
    if a.terminal(state) is not None:
        return dict(sport=sport, available=False, reason="The match is already decided.", framing=FRAMING)
    seed = zlib.crc32(json.dumps([state, side], sort_keys=True, default=str).encode())
    rng = np.random.default_rng(seed)
    pr = get_win_predictor(sport)
    cur = analyze(sport, state, explain=False)
    mom = cur["momentum"]
    base_val = a.coach_value(np.array([o["prob"] for o in cur["outcomes"]]), side)
    results = []
    for act in a.actions:
        rolled = a.rollout(state, act.id, rng, n, side)
        live_idx = [i for i, s in enumerate(rolled) if a.terminal(s) is None]
        vals = np.zeros(len(rolled))
        if live_idx:
            P = pr.proba([a.features(rolled[i]) for i in live_idx])
            for j, i in enumerate(live_idx):
                vals[i] = a.coach_value(P[j], side)
        for i, s in enumerate(rolled):
            t = a.terminal(s)
            if t is not None:
                vals[i] = a.coach_value(np.array(t), side)
        results.append(dict(action=act, mean=float(vals.mean()), se=float(vals.std(ddof=1) / math.sqrt(len(vals))),
                            p10=float(np.percentile(vals, 10)), p90=float(np.percentile(vals, 90)),
                            stats=a.rollout_stats(state, rolled, side)))
    order = sorted(results, key=lambda r: -r["mean"])
    best, second = order[0], order[1]
    z = (best["mean"] - second["mean"]) / math.sqrt(best["se"] ** 2 + second["se"] ** 2 + 1e-12)
    confidence = float(min(0.99, max(0.5, _phi(z))))
    txt = a.coach_text(state, best["action"], {r["action"].id: r["mean"] for r in results}, side, mom)
    metric = a.coach_metric
    fmt = (lambda v: f"{v:.2f} pts") if metric == "expected points" else (lambda v: f"{v * 100:.1f}%")
    close = best["mean"] - second["mean"] < 0.01 * (3 if metric == "expected points" else 1)
    reason = (f"Over {n} simulated roll-outs of the {a.coach_horizon}, '{best['action'].label}' gives an expected {metric} of "
              f"{fmt(best['mean'])} versus {fmt(second['mean'])} for '{second['action'].label}'.")
    if best["stats"]:
        reason += " Typical outcome of the recommended option: " + ", ".join(f"{k} {v:+.1f}" for k, v in best["stats"].items()) + "."
    if close:
        reason += " The options are very close, so treat this as a marginal preference."
    return dict(
        sport=sport, available=True, side=txt["side"], situation=txt["situation"], recommendation=best["action"].label,
        recommendation_id=best["action"].id, reason=reason, confidence=round(confidence, 3), metric=metric,
        current_value=base_val, horizon=a.coach_horizon, n_rollouts=n, framing=FRAMING,
        options=[dict(id=r["action"].id, label=r["action"].label, description=r["action"].description,
                      value=r["mean"], se=r["se"], p10=r["p10"], p90=r["p90"], stats=r["stats"],
                      delta_vs_now=r["mean"] - base_val, best=(r is best)) for r in results],
        confidence_note="Probability that the recommended option beats the runner-up under the simulation model (z-test on roll-out means).",
    )
