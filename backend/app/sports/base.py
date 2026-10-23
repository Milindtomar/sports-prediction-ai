"""Sport adapter contract.

A new sport is added by (1) a synthetic/real data pipeline + trained artifact,
(2) one subclass of `SportAdapter` registered in `registry.py`. Nothing else in the
API or frontend engine changes (the UI renders adapter-provided metadata).
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel


@dataclass
class FeatureMeta:
    label: str
    good: int = 0            # +1: higher is better for the focus side, -1: lower is better, 0: context only
    fmt: str = "{:.1f}"
    unit: str = ""


@dataclass
class EventDef:
    id: str
    label: str
    group: str
    description: str = ""


@dataclass
class ActionDef:
    id: str
    label: str
    description: str


@dataclass
class MomentumPart:
    label: str
    weight: float
    z: float
    detail: str


def momentum_from_parts(parts: list[MomentumPart], side: str, formula: str) -> dict:
    """Momentum = 50 + 50*tanh(sum_i w_i z_i); factor points are the proportional split of (M-50)."""
    s = sum(p.weight * max(-2.0, min(2.0, p.z)) for p in parts)
    score = 50 + 50 * math.tanh(s)
    factors = []
    for p in parts:
        z = max(-2.0, min(2.0, p.z))
        share = (p.weight * z / s) if abs(s) > 1e-9 else 0.0
        factors.append(dict(label=p.label, points=round((score - 50) * share, 1), detail=p.detail,
                            direction="positive" if p.weight * z > 0.02 else ("negative" if p.weight * z < -0.02 else "neutral")))
    factors.sort(key=lambda f: -abs(f["points"]))
    if score >= 75:
        label, tone = "Strong positive momentum", "hot"
    elif score >= 60:
        label, tone = "Building momentum", "warm"
    elif score > 40:
        label, tone = "Balanced", "neutral"
    elif score > 25:
        label, tone = "Losing momentum", "cool"
    else:
        label, tone = "Strong negative momentum", "cold"
    return dict(score=round(score, 1), label=label, tone=tone, side=side, factors=factors, formula=formula)


class SportAdapter:
    key: str = ""
    name: str = ""
    tagline: str = ""
    classes: list[str] = []          # model class names, in model output order
    focus_class: int = 1             # class whose probability is the headline (for binary sports)
    state_model: type[BaseModel]
    feature_meta: dict[str, FeatureMeta] = {}
    phrases: dict[str, tuple[str, str]] = {}    # feature -> (supports focus side, hurts focus side)
    events: list[EventDef] = []
    actions: list[ActionDef] = []
    analytics: list[str] = []
    coach_horizon: str = ""

    # ---------------------------------------------------------------- state
    def validate(self, raw: dict) -> dict:
        return self.state_model.model_validate(raw).model_dump()

    def default_state(self) -> dict:
        return self.state_model().model_dump()

    def features(self, state: dict) -> dict:
        raise NotImplementedError

    def terminal(self, state: dict) -> list[float] | None:
        return None

    def focus_name(self, state: dict) -> str:
        raise NotImplementedError

    def outcome_labels(self, state: dict) -> list[str]:
        """Display label per model class."""
        return list(self.classes)

    def scoreboard(self, state: dict) -> dict:
        raise NotImplementedError

    def momentum(self, state: dict) -> dict:
        raise NotImplementedError

    def insights(self, state: dict, feats: dict, probs: list[float], mom: dict) -> list[str]:
        return []

    # ---------------------------------------------------------------- simulation / coaching
    def apply_event(self, state: dict, event_id: str) -> dict:
        raise NotImplementedError

    def rollout(self, state: dict, action_id: str, rng, n: int, side: str) -> list[dict]:
        raise NotImplementedError

    def coach_value(self, probs, side: str) -> Any:
        """Scalar objective from one probability row (win prob, or expected points in football)."""
        return float(probs[self.focus_class])

    def coach_sides(self, state: dict) -> list[str]:
        return ["focus"]

    coach_metric: str = "win probability"

    def rollout_stats(self, state: dict, rolled: list[dict], side: str) -> dict:
        """Mean simulated change of interpretable quantities over the horizon (for the reasoning text)."""
        return {}

    def coach_text(self, state: dict, best: ActionDef, values: dict, side: str, mom: dict) -> dict:
        raise NotImplementedError

    # ---------------------------------------------------------------- explanation text
    def describe(self, feature: str, value: float, contribution_pp: float, feats: dict, cls: int) -> str:
        meta = self.feature_meta.get(feature)
        label = meta.label if meta else feature
        val = (meta.fmt if meta else "{:.2f}").format(value)
        if cls == self.focus_class and feature in self.phrases:
            pos, neg = self.phrases[feature]
            tpl = pos if contribution_pp >= 0 else neg
            try:
                return tpl.format(v=value, **feats)
            except Exception:  # pragma: no cover - defensive
                pass
        verb = "raises" if contribution_pp >= 0 else "lowers"
        return f"{label} ({val}) {verb} this outcome"

    def meta_dict(self) -> dict:
        return dict(
            key=self.key, name=self.name, tagline=self.tagline, classes=self.classes, focus_class=self.focus_class,
            analytics=self.analytics, coach_horizon=self.coach_horizon,
            events=[e.__dict__ for e in self.events], actions=[a.__dict__ for a in self.actions],
            features={k: dict(label=v.label, good=v.good, unit=v.unit) for k, v in self.feature_meta.items()},
        )
