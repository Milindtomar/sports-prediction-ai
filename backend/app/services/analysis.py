"""Prediction + explanation + momentum + insights for one match state."""
from __future__ import annotations

from functools import lru_cache

from app.ml.predictor import get_win_predictor, load_metrics
from app.sports.registry import get_adapter

DISCLAIMER = ("MODEL PREDICTION - an estimate from a model trained on synthetic data, not a guaranteed outcome. "
              "Probabilities describe uncertainty; the band shows model (bootstrap) disagreement.")


@lru_cache(maxsize=1)
def metrics() -> dict:
    return load_metrics()


def model_card(sport: str) -> dict:
    r = metrics()["sports"][sport]
    t = r["final"]["test"]
    return dict(name=r["chosen_display"], accuracy=t["accuracy"], f1=t["f1"], roc_auc=t["roc_auc"], brier=t["brier"],
                log_loss=t["log_loss"], ece=t["ece"], calibrated=r["calibrated"], classes=r["classes"],
                dataset=r["dataset"], data_source=metrics()["meta"]["data_source"])


def _fmt(adapter, feat: str, v: float) -> str:
    m = adapter.feature_meta.get(feat)
    return (m.fmt if m else "{:.2f}").format(v) + (f" {m.unit}" if m and m.unit and "%" not in m.fmt else "")


def predict_state(sport: str, state: dict, band: bool = True) -> dict:
    """Probabilities only (fast path used by sweeps/coach/timelines)."""
    a = get_adapter(sport)
    term = a.terminal(state)
    if term is not None:
        return dict(probs=term, lo=term, hi=term, terminal=True)
    pr = get_win_predictor(sport)
    f = a.features(state)
    if band:
        p, lo, hi = pr.proba_band([f])
        return dict(probs=p[0].tolist(), lo=lo[0].tolist(), hi=hi[0].tolist(), terminal=False)
    p = pr.proba([f])
    return dict(probs=p[0].tolist(), lo=p[0].tolist(), hi=p[0].tolist(), terminal=False)


def build_explanation(sport: str, state: dict, feats: dict, cls: int, probs: list[float]) -> dict:
    a = get_adapter(sport)
    pr = get_win_predictor(sport)
    ex = pr.explain(feats, cls)
    labels = a.outcome_labels(state)
    rows = []
    for f, c in ex["contributions"].items():
        pp = c * 100.0
        rows.append(dict(feature=f, label=a.feature_meta[f].label if f in a.feature_meta else f, value=feats[f],
                         value_text=_fmt(a, f, feats[f]), contribution_pp=round(pp, 2),
                         direction="positive" if pp > 0.15 else ("negative" if pp < -0.15 else "neutral"),
                         text=a.describe(f, feats[f], pp, feats, cls),
                         reference=pr.b["feature_means"].get(f)))
    rows.sort(key=lambda r: -abs(r["contribution_pp"]))
    pos = [r for r in rows if r["contribution_pp"] > 0.4][:3]
    neg = [r for r in rows if r["contribution_pp"] < -0.4][:3]
    sm = metrics()["sports"][sport]
    return dict(
        target_class=cls, target_label=labels[cls], probability=probs[cls], base_value=ex["base_value"],
        simple=dict(headline=f"{labels[cls]}: {probs[cls] * 100:.0f}%",
                    baseline_text=f"A typical match state scores {ex['base_value'] * 100:.0f}%; these factors move it.",
                    positives=[dict(text=r["text"], pp=r["contribution_pp"]) for r in pos],
                    negatives=[dict(text=r["text"], pp=r["contribution_pp"]) for r in neg]),
        technical=dict(
            method=f"Permutation-sampled Shapley values on the probability scale ({ex['n_permutations']} permutations x "
                   f"{ex['background_size']} background states from the training set). Contributions are additive: "
                   "baseline + sum = prediction.",
            model=sm["chosen_display"], additivity_gap_pp=round((ex["base_value"] + sum(r["contribution_pp"] for r in rows) / 100 - probs[cls]) * 100, 3),
            global_importance=list(sm["feature_importance"].items())[:8], table=rows),
        contributions=rows,
    )


def analyze(sport: str, raw_state: dict, explain: bool = True, target_class: int | None = None) -> dict:
    a = get_adapter(sport)
    state = a.validate(raw_state)
    feats = a.features(state)
    pred = predict_state(sport, state)
    labels = a.outcome_labels(state)
    outcomes = [dict(label=labels[i], prob=pred["probs"][i], lo=pred["lo"][i], hi=pred["hi"][i], cls=i)
                for i in range(len(labels))]
    mom = a.momentum(state)
    cls = a.focus_class if target_class is None else target_class
    explanation = None
    if explain and not pred["terminal"]:
        explanation = build_explanation(sport, state, feats, cls, pred["probs"])
    return dict(
        sport=sport, state=state, scoreboard=a.scoreboard(state), focus=dict(name=a.focus_name(state), cls=a.focus_class),
        outcomes=outcomes, headline=outcomes[a.focus_class], terminal=pred["terminal"], momentum=mom,
        explanation=explanation, insights=a.insights(state, feats, pred["probs"], mom), features=feats,
        model=model_card(sport), disclaimer=DISCLAIMER)
