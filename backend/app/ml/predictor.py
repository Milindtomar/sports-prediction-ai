"""Inference-time model access (artifacts are trained offline, loaded once).

Provides:
* calibrated probabilities + bootstrap-ensemble uncertainty band,
* permutation-sampled Shapley attributions (model-agnostic, additive in probability space),
* attribution of a *change* between two states (used by the simulation "why did it move?").
"""
from __future__ import annotations

import json
import threading
from functools import lru_cache
from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from app.config import settings
from app.ml import common  # noqa: F401  (needed so joblib can unpickle CalibratedModel)


class ArtifactMissing(RuntimeError):
    pass


_lock = threading.Lock()


@lru_cache(maxsize=None)
def _load(name: str):
    path = Path(settings.artifact_dir) / f"{name}.joblib"
    if not path.exists():
        raise ArtifactMissing(f"Model artifact '{name}' not found. Run: python -m app.ml.train_all")
    try:
        return joblib.load(path)
    except Exception as e:   # corrupt / truncated / incompatible pickle
        raise ArtifactMissing(f"Model artifact '{name}' could not be read ({type(e).__name__}). Re-run: python -m app.ml.train_all") from e


def clear_caches() -> None:
    """Forget loaded models (used after retraining and in tests)."""
    _load.cache_clear()
    get_win_predictor.cache_clear()
    from app.services import analysis
    analysis.metrics.cache_clear()


def readiness() -> dict:
    """Per-sport readiness: can the win-probability artifact actually be loaded? -> {sport: 'ready' | reason}."""
    out = {}
    for sport in ("cricket", "football", "basketball"):
        try:
            _load(f"{sport}_win")
            out[sport] = "ready"
        except ArtifactMissing as e:
            out[sport] = str(e)
    try:
        load_metrics()
        out["metrics"] = "ready"
    except ArtifactMissing as e:
        out["metrics"] = str(e)
    return out


def load_metrics() -> dict:
    p = Path(settings.artifact_dir) / "metrics.json"
    if not p.exists():
        raise ArtifactMissing("metrics.json not found. Run: python -m app.ml.train_all")
    return json.loads(p.read_text())


class WinPredictor:
    """Wraps one sport's win-probability bundle."""

    def __init__(self, sport: str):
        self.sport = sport
        self.b = _load(f"{sport}_win")
        self.features: list[str] = self.b["features"]
        self.k: int = self.b["n_classes"]
        self.model = self.b["model"]
        self.members = [self.model.with_base(m) for m in self.b["members"]]

    # ------------------------------------------------------------------ probabilities
    def _frame(self, rows: list[dict]) -> pd.DataFrame:
        return pd.DataFrame([[r[f] for f in self.features] for r in rows], columns=self.features)

    def proba(self, rows: list[dict]) -> np.ndarray:
        return self.model.predict_proba(self._frame(rows))

    def proba_band(self, rows: list[dict], lo_q: float = 10, hi_q: float = 90):
        """Returns (p, lo, hi) arrays of shape (n, k). Band = bootstrap-ensemble spread (epistemic)."""
        X = self._frame(rows)
        p = self.model.predict_proba(X)
        if not self.members:
            return p, p, p
        mem = np.stack([m.predict_proba(X) for m in self.members])
        lo = np.minimum(np.percentile(mem, lo_q, axis=0), p)
        hi = np.maximum(np.percentile(mem, hi_q, axis=0), p)
        return p, lo, hi

    # ------------------------------------------------------------------ explanations
    def _shapley(self, x: np.ndarray, bg: np.ndarray, cls: int, idx: list[int], n_perm: int, seed: int,
                 base_row: np.ndarray | None = None):
        """Sampled Shapley values over the feature subset `idx`, other features fixed to `base_row`
        (or to each background row when base_row is None). Returns (phi over idx, baseline, f(x))."""
        rng = np.random.default_rng(seed)
        d = len(idx)
        rows, perms = [], []
        for _ in range(n_perm):
            perm = rng.permutation(d)
            perms.append(perm)
            for b in bg:
                cur = b.copy() if base_row is None else base_row.copy()
                rows.append(cur.copy())
                for j in perm:
                    cur[idx[j]] = x[idx[j]]
                    rows.append(cur.copy())
        P = self.model.predict_proba(pd.DataFrame(rows, columns=self.features))[:, cls]
        P = P.reshape(n_perm, len(bg), d + 1)
        diffs = P[:, :, 1:] - P[:, :, :-1]
        phi = np.zeros(d)
        for pi, perm in enumerate(perms):
            m = diffs[pi].mean(axis=0)  # mean over backgrounds, length d, ordered by perm step
            np.add.at(phi, perm, m)
        phi /= n_perm
        return phi, float(P[:, :, 0].mean()), float(P[:, :, -1].mean())

    def explain(self, feats: dict, cls: int, n_perm: int = 16, n_bg: int = 6, seed: int = 0) -> dict:
        x = np.array([feats[f] for f in self.features], dtype=float)
        bgdf = self.b["background"]
        rs = np.random.default_rng(seed)
        bg = bgdf.values[rs.choice(len(bgdf), min(n_bg, len(bgdf)), replace=False)].astype(float)
        phi, base, fx = self._shapley(x, bg, cls, list(range(len(self.features))), n_perm, seed)
        return dict(base_value=base, prediction=fx,
                    contributions={f: float(p) for f, p in zip(self.features, phi)},
                    background_size=len(bg), n_permutations=n_perm)

    def attribute_change(self, before: dict, after: dict, cls: int, n_perm: int = 24, seed: int = 0) -> dict:
        """Which *changed* features explain the move in P(class)? Baseline = the before-state."""
        xb = np.array([before[f] for f in self.features], dtype=float)
        xa = np.array([after[f] for f in self.features], dtype=float)
        idx = [i for i in range(len(xb)) if abs(xa[i] - xb[i]) > 1e-9]
        if not idx:
            return dict(contributions={}, delta=0.0)
        phi, p0, p1 = self._shapley(xa, xb[None, :], cls, idx, n_perm if len(idx) > 1 else 1, seed, base_row=xb)
        return dict(contributions={self.features[i]: float(v) for i, v in zip(idx, phi)}, delta=p1 - p0)


@lru_cache(maxsize=None)
def get_win_predictor(sport: str) -> WinPredictor:
    with _lock:
        return WinPredictor(sport)


class PlayerModels:
    """Per-sport player prediction models (regressors + the cricket 50+ classifier)."""

    TARGETS = {
        "cricket_bat": ["runs", "p50"], "cricket_bowl": ["wickets", "economy"],
        "football": ["goals", "assists", "shots"], "basketball": ["points", "rebounds", "assists"],
    }

    @staticmethod
    def predict(sport: str, target: str, feats: dict) -> float:
        key = f"player_{sport}_{target}" if sport != "cricket" else f"player_cricket_{target}"
        b = _load(key)
        X = pd.DataFrame([[feats[f] for f in b["features"]]], columns=b["features"])
        if b["kind"] in ("binary",):
            return float(b["model"].predict_proba(X)[0, 1])
        return float(max(b["model"].predict(X)[0], 0.0))
