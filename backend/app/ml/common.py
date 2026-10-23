"""Model zoo, evaluation metrics, calibration and the shared training routine.

Design rules (see ML_DOCUMENTATION.md):
* chronological, match-grouped train / validation / test split;
* model selection on VALIDATION log-loss only, simplest model within 1% of the best
  (we do not blindly pick the most complex model);
* the test split is touched once, for the final report;
* probabilities are optionally isotonic-calibrated (kept only if it helps on held-out validation);
* a match-level bootstrap ensemble of the selected family provides an epistemic
  uncertainty band at inference time.
"""
from __future__ import annotations

import time
import warnings

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingClassifier, HistGradientBoostingRegressor, RandomForestClassifier, RandomForestRegressor
from sklearn.isotonic import IsotonicRegression
from sklearn.linear_model import LogisticRegression, PoissonRegressor, Ridge
from sklearn.metrics import (
    accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    log_loss,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier, XGBRegressor

warnings.filterwarnings("ignore", category=UserWarning)
EPS = 1e-6
COMPLEXITY = ["logistic_regression", "ridge", "poisson_glm", "random_forest", "gradient_boosting", "xgboost"]
DISPLAY = {"logistic_regression": "Logistic Regression", "ridge": "Ridge Regression", "poisson_glm": "Poisson GLM",
           "random_forest": "Random Forest", "gradient_boosting": "Gradient Boosting (Hist)", "xgboost": "XGBoost"}


# ----------------------------------------------------------------------------- model factories
def make_classifier(name: str, light: bool = False, seed: int = 0):
    if name == "logistic_regression":
        return make_pipeline(StandardScaler(), LogisticRegression(C=1.0, max_iter=3000))
    if name == "random_forest":
        return RandomForestClassifier(n_estimators=50 if light else 140, max_depth=12, min_samples_leaf=40,
                                      max_samples=0.5, n_jobs=2, random_state=seed)
    if name == "gradient_boosting":
        return HistGradientBoostingClassifier(max_depth=4, learning_rate=0.06, max_iter=120 if light else 220,
                                              l2_regularization=1.0, random_state=seed)
    if name == "xgboost":
        return XGBClassifier(n_estimators=120 if light else 240, max_depth=4, learning_rate=0.06, subsample=0.8,
                             colsample_bytree=0.8, min_child_weight=10, reg_lambda=2.0, n_jobs=2,
                             tree_method="hist", random_state=seed, verbosity=0)
    raise ValueError(name)


def make_regressor(name: str, count: bool, light: bool = False, seed: int = 0):
    if name == "ridge":
        return make_pipeline(StandardScaler(), Ridge(alpha=3.0))
    if name == "poisson_glm":
        return make_pipeline(StandardScaler(), PoissonRegressor(alpha=1e-3, max_iter=1000))
    if name == "random_forest":
        return RandomForestRegressor(n_estimators=50 if light else 140, max_depth=10, min_samples_leaf=30,
                                     max_samples=0.6, n_jobs=2, random_state=seed)
    if name == "gradient_boosting":
        return HistGradientBoostingRegressor(loss="poisson" if count else "squared_error", max_depth=3,
                                             learning_rate=0.05, max_iter=100 if light else 200,
                                             l2_regularization=2.0, random_state=seed)
    if name == "xgboost":
        return XGBRegressor(n_estimators=100 if light else 220, max_depth=3, learning_rate=0.05, subsample=0.8,
                            colsample_bytree=0.8, min_child_weight=10, reg_lambda=3.0, n_jobs=2, tree_method="hist",
                            objective="count:poisson" if count else "reg:squarederror", random_state=seed,
                            verbosity=0)
    raise ValueError(name)


CLASSIFIERS = ["logistic_regression", "random_forest", "gradient_boosting", "xgboost"]


def regressor_names(count: bool):
    return ["poisson_glm" if count else "ridge", "random_forest", "gradient_boosting", "xgboost"]


# ----------------------------------------------------------------------------- calibration wrapper
class CalibratedModel:
    """Wraps a fitted classifier and (optionally) per-class isotonic calibrators."""

    def __init__(self, base, calibrators=None, n_classes: int = 2):
        self.base, self.calibrators, self.n_classes = base, calibrators, n_classes

    def with_base(self, base) -> "CalibratedModel":
        return CalibratedModel(base, self.calibrators, self.n_classes)

    def predict_proba(self, X) -> np.ndarray:
        p = np.asarray(self.base.predict_proba(X), dtype=float)
        if self.calibrators is not None:
            q = np.column_stack([self.calibrators[k].predict(p[:, k]) for k in range(self.n_classes)])
            q = np.clip(q, EPS, 1 - EPS)
            p = q / q.sum(axis=1, keepdims=True)
        return np.clip(p, EPS, 1 - EPS)


def fit_calibrators(p: np.ndarray, y: np.ndarray, n_classes: int):
    cals = []
    for k in range(n_classes):
        iso = IsotonicRegression(out_of_bounds="clip", y_min=EPS, y_max=1 - EPS)
        iso.fit(p[:, k], (y == k).astype(float))
        cals.append(iso)
    return cals


# ----------------------------------------------------------------------------- metrics
def reliability(p_pos: np.ndarray, y_pos: np.ndarray, bins: int = 10):
    edges = np.linspace(0, 1, bins + 1)
    out, ece = [], 0.0
    for i in range(bins):
        m = (p_pos >= edges[i]) & ((p_pos < edges[i + 1]) if i < bins - 1 else (p_pos <= 1))
        n = int(m.sum())
        if n:
            mp, fp = float(p_pos[m].mean()), float(y_pos[m].mean())
            ece += n / len(p_pos) * abs(mp - fp)
            out.append(dict(lo=float(edges[i]), hi=float(edges[i + 1]), n=n, mean_pred=mp, frac_pos=fp))
    return out, float(ece)


def classification_metrics(y: np.ndarray, proba: np.ndarray) -> dict:
    k = proba.shape[1]
    pred = proba.argmax(1)
    if k == 2:
        p1 = proba[:, 1]
        rel, ece = reliability(p1, y.astype(float))
        return dict(accuracy=accuracy_score(y, pred), precision=precision_score(y, pred, zero_division=0),
                    recall=recall_score(y, pred, zero_division=0), f1=f1_score(y, pred, zero_division=0),
                    roc_auc=roc_auc_score(y, p1), brier=brier_score_loss(y, p1), log_loss=log_loss(y, proba),
                    ece=ece, reliability=rel, confusion_matrix=confusion_matrix(y, pred, labels=[0, 1]).tolist())
    onehot = np.eye(k)[y]
    conf = proba.max(1)
    rel, ece = reliability(conf, (pred == y).astype(float))
    return dict(accuracy=accuracy_score(y, pred),
                precision=precision_score(y, pred, average="macro", zero_division=0),
                recall=recall_score(y, pred, average="macro", zero_division=0),
                f1=f1_score(y, pred, average="macro", zero_division=0),
                roc_auc=roc_auc_score(y, proba, multi_class="ovr", average="macro"),
                brier=float(((proba - onehot) ** 2).sum(1).mean()), log_loss=log_loss(y, proba, labels=list(range(k))),
                ece=ece, reliability=rel, confusion_matrix=confusion_matrix(y, pred, labels=list(range(k))).tolist())


def regression_metrics(y, pred) -> dict:
    return dict(mae=float(mean_absolute_error(y, pred)), rmse=float(np.sqrt(mean_squared_error(y, pred))),
                r2=float(r2_score(y, pred)))


def _clean(d):
    if isinstance(d, dict):
        return {k: _clean(v) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        return [_clean(v) for v in d]
    if isinstance(d, (np.floating, float)):
        return round(float(d), 5)
    if isinstance(d, (np.integer,)):
        return int(d)
    return d


# ----------------------------------------------------------------------------- permutation importance
def permutation_importance_ll(model, X: pd.DataFrame, y: np.ndarray, n: int = 6000, repeats: int = 2, seed: int = 0):
    rng = np.random.default_rng(seed)
    idx = rng.choice(len(X), min(n, len(X)), replace=False)
    Xs, ys = X.iloc[idx].reset_index(drop=True), y[idx]
    base = log_loss(ys, model.predict_proba(Xs), labels=list(range(model.n_classes)))
    out = {}
    for c in X.columns:
        deltas = []
        for _ in range(repeats):
            Xp = Xs.copy()
            Xp[c] = rng.permutation(Xp[c].values)
            deltas.append(log_loss(ys, model.predict_proba(Xp), labels=list(range(model.n_classes))) - base)
        out[c] = float(np.mean(deltas))
    return out


# ----------------------------------------------------------------------------- win-probability training
def pick_simplest_within(scores: dict[str, float], tol: float = 0.01) -> str:
    best = min(scores.values())
    ok = [m for m in COMPLEXITY if m in scores and scores[m] <= best * (1 + tol)]
    return ok[0]


def train_win_model(df: pd.DataFrame, features: list[str], n_classes: int, split, class_names: list[str],
                    seed: int = 0, n_boot: int = 12, log=print) -> tuple[dict, dict]:
    """Train/compare/calibrate/bootstrap. Returns (bundle_for_joblib, report_for_json)."""
    tr, va, te = split
    X, y, mid = df[features], df["label"].values.astype(int), df["match_id"].values
    Xtr, ytr, Xva, yva, Xte, yte = X[tr], y[tr], X[va], y[va], X[te], y[te]
    base_rate = np.bincount(ytr, minlength=n_classes) / len(ytr)
    baseline = dict(majority_accuracy=float((yte == base_rate.argmax()).mean()),
                    prior_log_loss=float(log_loss(yte, np.tile(base_rate, (len(yte), 1)), labels=list(range(n_classes)))))
    comparison, fitted, times = {}, {}, {}
    for name in CLASSIFIERS:
        t0 = time.time()
        m = make_classifier(name, seed=seed).fit(Xtr, ytr)
        times[name] = round(time.time() - t0, 1)
        fitted[name] = m
        comparison[name] = dict(
            validation=classification_metrics(yva, m.predict_proba(Xva)),
            test=classification_metrics(yte, m.predict_proba(Xte)), train_seconds=times[name])
        log(f"  {name:20s} val logloss={comparison[name]['validation']['log_loss']:.4f} "
            f"test acc={comparison[name]['test']['accuracy']:.3f} auc={comparison[name]['test']['roc_auc']:.3f} "
            f"({times[name]}s)")
    val_ll = {n: comparison[n]["validation"]["log_loss"] for n in CLASSIFIERS}
    chosen = pick_simplest_within(val_ll, 0.01)
    log(f"  selected: {chosen}")
    base = fitted[chosen]

    # calibration decision on a held-out half of validation (chronological halves)
    vmid = mid[va]
    half = np.unique(vmid)[len(np.unique(vmid)) // 2]
    a, b = vmid < half, vmid >= half
    pva = base.predict_proba(Xva)
    cals_a = fit_calibrators(pva[a], yva[a], n_classes)
    cm_try = CalibratedModel(base, cals_a, n_classes)
    ll_raw = log_loss(yva[b], np.clip(pva[b], EPS, 1 - EPS), labels=list(range(n_classes)))
    ll_cal = log_loss(yva[b], cm_try.predict_proba(Xva[b]), labels=list(range(n_classes)))
    use_cal = ll_cal < ll_raw
    cals = fit_calibrators(pva, yva, n_classes) if use_cal else None
    final = CalibratedModel(base, cals, n_classes)
    log(f"  calibration: raw={ll_raw:.4f} calibrated={ll_cal:.4f} -> {'use' if use_cal else 'skip'}")
    final_test = classification_metrics(yte, final.predict_proba(Xte))
    final_val = classification_metrics(yva, final.predict_proba(Xva))

    # bootstrap ensemble (cluster bootstrap over matches) for epistemic uncertainty
    rng = np.random.default_rng(seed + 99)
    ids = np.unique(mid[tr])
    groups = {i: np.where(mid[tr] == i)[0] for i in ids}
    members = []
    for _ in range(n_boot):
        pick = rng.choice(ids, len(ids), replace=True)
        rows = np.concatenate([groups[i] for i in pick])
        members.append(make_classifier(chosen, light=True, seed=int(rng.integers(1e6))).fit(Xtr.iloc[rows], ytr[rows]))
    imp = permutation_importance_ll(final, Xte.reset_index(drop=True), yte, seed=seed)
    bg = Xtr.sample(60, random_state=seed).reset_index(drop=True)
    bundle = dict(kind="win", features=features, n_classes=n_classes, class_names=class_names, model=final,
                  members=members, background=bg, feature_means=Xtr.mean().to_dict(),
                  feature_std=Xtr.std().replace(0, 1).to_dict(), chosen=chosen)
    sizes = {k: int(m.sum()) for k, m in zip(["train", "validation", "test"], split)}
    matches = {k: int(len(np.unique(mid[m]))) for k, m in zip(["train", "validation", "test"], split)}
    report = dict(task="win_probability", chosen=chosen, chosen_display=DISPLAY[chosen], classes=class_names,
                  features=features, comparison=comparison, selection_rule="lowest validation log-loss; simplest "
                  "model within 1% of the best", calibrated=bool(use_cal), calibration_check=dict(raw_val_ll=ll_raw,
                  calibrated_val_ll=ll_cal), final=dict(validation=final_val, test=final_test), baseline=baseline,
                  feature_importance=dict(sorted(imp.items(), key=lambda kv: -kv[1])),
                  split=dict(rows=sizes, matches=matches, scheme="chronological, match-grouped 70/15/15"),
                  bootstrap_members=n_boot)
    return bundle, _clean(report)


# ----------------------------------------------------------------------------- regression / player training
def train_regression(df: pd.DataFrame, features: list[str], target: str, split, count: bool, seed: int = 0,
                     log=print) -> tuple[dict, dict]:
    tr, va, te = split
    X, y = df[features], df[target].values.astype(float)
    mean_pred = float(y[tr].mean())
    baseline = regression_metrics(y[te], np.full(te.sum(), mean_pred))
    comparison, fitted = {}, {}
    for name in regressor_names(count):
        m = make_regressor(name, count, seed=seed).fit(X[tr], y[tr])
        fitted[name] = m
        comparison[name] = dict(validation=regression_metrics(y[va], m.predict(X[va])),
                                test=regression_metrics(y[te], m.predict(X[te])))
    val_rmse = {n: comparison[n]["validation"]["rmse"] for n in comparison}
    chosen = pick_simplest_within(val_rmse, 0.01)
    model = fitted[chosen]
    log(f"  {target:12s} -> {chosen:18s} test MAE={comparison[chosen]['test']['mae']:.3f} "
        f"RMSE={comparison[chosen]['test']['rmse']:.3f} R2={comparison[chosen]['test']['r2']:.3f} "
        f"(baseline MAE={baseline['mae']:.3f})")
    # permutation importance (MAE)
    rng = np.random.default_rng(seed)
    Xt, yt = X[te].reset_index(drop=True), y[te]
    b0 = mean_absolute_error(yt, model.predict(Xt))
    imp = {}
    for c in features:
        Xp = Xt.copy()
        Xp[c] = rng.permutation(Xp[c].values)
        imp[c] = float(mean_absolute_error(yt, model.predict(Xp)) - b0)
    resid = yt - model.predict(Xt)
    q = [float(np.percentile(resid, 10)), float(np.percentile(resid, 90))]
    bundle = dict(kind="regression", features=features, target=target, model=model, chosen=chosen,
                  count=count, train_mean=mean_pred, resid_q=q)
    report = dict(task=f"regression:{target}", chosen=chosen, chosen_display=DISPLAY[chosen], comparison=comparison,
                  baseline_mean_predictor=baseline, final=dict(test=comparison[chosen]["test"]),
                  residual_interval80=q,
                  feature_importance=dict(sorted(imp.items(), key=lambda kv: -kv[1])),
                  rows={k: int(m.sum()) for k, m in zip(["train", "validation", "test"], split)})
    return bundle, _clean(report)


def train_binary_player(df: pd.DataFrame, features: list[str], target: str, split, seed: int = 0, log=print):
    """Binary classifier for events such as '50+ runs' (game-level chronological split)."""
    tr, va, te = split
    d = df.copy()
    d["label"] = d[target].astype(int)
    d["match_id"] = d["game"].values
    bundle, rep = train_win_model(d, features, 2, split, ["no", "yes"], seed=seed, n_boot=0, log=log)
    bundle["kind"] = "binary"
    rep["task"] = f"binary:{target}"
    return bundle, rep


def metrics_frame_summary(report: dict) -> str:
    return f"{report['task']}: {report['chosen_display']}"
