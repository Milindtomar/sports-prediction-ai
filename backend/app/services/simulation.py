"""What-if simulation: every scenario is pushed back through the real prediction pipeline.

1. apply deterministic event transitions to the raw match state (adapter.apply_event),
2. recompute features with the same code used in training,
3. predict with the trained model (+ ensemble band),
4. attribute the change in probability to the features that changed (Shapley, baseline = before-state).
"""
from __future__ import annotations

from app.ml.predictor import get_win_predictor
from app.services.analysis import analyze, predict_state
from app.sports.registry import get_adapter


def _summ(res: dict) -> dict:
    return dict(outcomes=res["outcomes"], headline=res["headline"], scoreboard=res["scoreboard"],
                momentum=res["momentum"], terminal=res["terminal"], state=res["state"])


def apply_events(sport: str, state: dict, events: list[dict]) -> tuple[dict, list[dict]]:
    a = get_adapter(sport)
    labels = {e.id: e.label for e in a.events}
    st, applied = state, []
    for ev in events:
        if ev["id"] not in labels:
            raise KeyError(ev["id"])
        for _ in range(ev.get("count", 1)):
            st = a.validate(a.apply_event(st, ev["id"]))
        applied.append(dict(id=ev["id"], label=labels[ev["id"]], count=ev.get("count", 1)))
    return st, applied


def simulate(sport: str, raw_state: dict, events: list[dict], overrides: dict | None = None) -> dict:
    a = get_adapter(sport)
    base = a.validate({**raw_state, **(overrides or {})})
    before = analyze(sport, base)
    after_state, applied = apply_events(sport, base, events)
    after = analyze(sport, after_state)
    cls = a.focus_class
    deltas = [dict(label=o["label"], before=b["prob"], after=o["prob"], delta_pp=round((o["prob"] - b["prob"]) * 100, 2))
              for o, b in zip(after["outcomes"], before["outcomes"])]
    attribution, narrative = None, None
    if not before["terminal"] and not after["terminal"]:
        pr = get_win_predictor(sport)
        att = pr.attribute_change(before["features"], after["features"], cls)
        rows = []
        for f, v in att["contributions"].items():
            m = a.feature_meta.get(f)
            fm = (m.fmt if m else "{:.2f}")
            rows.append(dict(feature=f, label=m.label if m else f, before=before["features"][f], after=after["features"][f],
                             before_text=fm.format(before["features"][f]), after_text=fm.format(after["features"][f]),
                             contribution_pp=round(v * 100, 2)))
        rows.sort(key=lambda r: -abs(r["contribution_pp"]))
        attribution = dict(rows=rows, total_pp=round(att["delta"] * 100, 2),
                           method="Shapley attribution over the features that changed; baseline = the before-state.")
        top = [r for r in rows if abs(r["contribution_pp"]) >= 0.3][:3]
        d = deltas[cls]
        if top:
            narrative = (f"{d['label']} {d['before'] * 100:.0f}% → {d['after'] * 100:.0f}% ({d['delta_pp']:+.1f} pp). Main drivers: "
                         + "; ".join(f"{r['label'].lower()} {r['before_text']} → {r['after_text']} ({r['contribution_pp']:+.1f} pp)" for r in top) + ".")
    if narrative is None:
        d = deltas[cls]
        narrative = (f"{d['label']} {d['before'] * 100:.0f}% → {d['after'] * 100:.0f}% ({d['delta_pp']:+.1f} pp)."
                     + (" The match is decided in the resulting state." if after["terminal"] else ""))
    return dict(sport=sport, applied=applied, before=_summ(before), after=_summ(after), deltas=deltas,
                focus_class=cls, attribution=attribution, narrative=narrative,
                pipeline=["apply event transition", "recompute features", "model.predict_proba (+ bootstrap band)",
                          "Shapley attribution of the change"])


def sweep(sport: str, raw_state: dict) -> dict:
    """Impact of every catalogued single event on the headline probability (one batched model call)."""
    a = get_adapter(sport)
    base = a.validate(raw_state)
    pr = get_win_predictor(sport)
    b = predict_state(sport, base, band=False)
    rows, states = [], []
    for e in a.events:
        try:
            states.append((e, a.validate(a.apply_event(base, e.id))))
        except Exception:  # an event can be illegal in some states (e.g. lineup at its minimum)
            continue
    live = [(e, s) for e, s in states if a.terminal(s) is None]
    probs = pr.proba([a.features(s) for _, s in live]) if live else []
    pm = {e.id: p.tolist() for (e, _), p in zip(live, probs)}
    for e, s in states:
        p = pm.get(e.id) or a.terminal(s)
        rows.append(dict(id=e.id, label=e.label, group=e.group,
                         prob=p[a.focus_class], delta_pp=round((p[a.focus_class] - b["probs"][a.focus_class]) * 100, 2)))
    rows.sort(key=lambda r: -r["delta_pp"])
    return dict(sport=sport, baseline=b["probs"][a.focus_class], focus_label=a.outcome_labels(base)[a.focus_class], impacts=rows)
