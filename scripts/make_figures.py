"""Regenerate every paper/poster figure and results table from backend/artifacts/metrics.json.

    python scripts/make_figures.py

Outputs: research/figures/*.png (+ .svg for diagrams), research/tables/*.md|csv, research/poster_assets/ (copies).
Nothing here is typed in by hand: all numbers are read from metrics.json (produced by the training run).
"""
from __future__ import annotations

import csv
import json
import shutil
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
M = json.loads((ROOT / "backend" / "artifacts" / "metrics.json").read_text())
FIG, TAB, POSTER = ROOT / "research" / "figures", ROOT / "research" / "tables", ROOT / "research" / "poster_assets"
for d in (FIG, TAB, POSTER):
    d.mkdir(parents=True, exist_ok=True)

INK, MUTE, RULE, ACC = "#1B2733", "#66737F", "#C9D1D9", "#2F7D4F"
SPORT_COL = {"cricket": "#2F7D4F", "football": "#1F7A99", "basketball": "#B7691B"}
ALGO = {"logistic_regression": "Logistic regression", "random_forest": "Random forest",
        "gradient_boosting": "Gradient boosting", "xgboost": "XGBoost"}
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.edgecolor": MUTE, "axes.labelcolor": INK,
                     "xtick.color": INK, "ytick.color": INK, "text.color": INK, "axes.spines.top": False,
                     "axes.spines.right": False, "figure.dpi": 150, "savefig.dpi": 200, "savefig.bbox": "tight"})
SPORTS = ["cricket", "football", "basketball"]


def save(fig, name, svg=False):
    fig.savefig(FIG / f"{name}.png", facecolor="white")
    if svg:
        fig.savefig(FIG / f"{name}.svg", facecolor="white")
    plt.close(fig)
    print("figure", name)


# ------------------------------------------------------------------ tables (markdown + csv)
def md_table(header, rows):
    return "\n".join(["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"] +
                     ["| " + " | ".join(str(c) for c in r) + " |" for r in rows]) + "\n"


def write_table(name, header, rows):
    (TAB / f"{name}.md").write_text(md_table(header, rows))
    with open(TAB / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print("table", name)


def tables():
    rows = []
    for s in SPORTS:
        r = M["sports"][s]; t = r["final"]["test"]; b = r["baseline"]
        rows.append([s.capitalize(), r["chosen_display"], f"{t['accuracy']:.3f}", f"{t['precision']:.3f}", f"{t['recall']:.3f}",
                     f"{t['f1']:.3f}", f"{t['roc_auc']:.3f}", f"{t['brier']:.3f}", f"{t['log_loss']:.3f}", f"{t['ece']:.3f}",
                     f"{b['majority_accuracy']:.3f}", f"{b['prior_log_loss']:.3f}"])
    write_table("win_probability_test", ["Sport", "Selected model", "Accuracy", "Precision", "Recall", "F1", "ROC-AUC", "Brier",
                                         "Log-loss", "ECE", "Majority acc.", "Prior log-loss"], rows)
    rows = []
    for s in SPORTS:
        r = M["sports"][s]
        for a, c in r["comparison"].items():
            rows.append([s.capitalize(), ALGO[a], f"{c['validation']['log_loss']:.4f}", f"{c['test']['log_loss']:.4f}",
                         f"{c['test']['accuracy']:.3f}", f"{c['test']['roc_auc']:.3f}", "selected" if a == r["chosen"] else ""])
    write_table("algorithm_comparison", ["Sport", "Algorithm", "Val. log-loss", "Test log-loss", "Test acc.", "Test AUC", ""], rows)
    rows = []
    for s in SPORTS:
        d = M["sports"][s]["dataset"]; sp = M["sports"][s]["split"]
        bal = " / ".join(f"{v:.3f}" for v in d["class_balance"].values())
        rows.append([s.capitalize(), f"{d['matches']:,}", f"{d['rows']:,}", d["n_features"], bal,
                     f"{sp['matches']['train']} / {sp['matches']['validation']} / {sp['matches']['test']}", d["data_hash"], M["meta"]["seeds"][s]])
    write_table("datasets", ["Sport", "Matches", "Snapshot rows", "Features", "Class balance", "Train/val/test matches", "Data hash", "Seed"], rows)
    rows = []
    for k, p in M["players"].items():
        t = p["final"]["test"]
        if p["task"].startswith("binary"):
            rows.append([k, p["chosen_display"], "-", "-", "-", f"AUC {t['roc_auc']:.3f}; acc {t['accuracy']:.3f} vs majority {p['baseline']['majority_accuracy']:.3f}"])
        else:
            rows.append([k, p["chosen_display"], f"{t['mae']:.3f}", f"{t['rmse']:.3f}", f"{t['r2']:.3f}", f"baseline-mean MAE {p['baseline_mean_predictor']['mae']:.3f}"])
    write_table("player_models_test", ["Target", "Selected model", "MAE", "RMSE", "R2", "Note"], rows)


# ------------------------------------------------------------------ result figures
def fig_comparison():
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.2))
    for ax, s in zip(axes, SPORTS):
        c = M["sports"][s]["comparison"]; names = list(c)
        vals = [c[n]["test"]["log_loss"] for n in names]
        colors = [SPORT_COL[s] if n == M["sports"][s]["chosen"] else RULE for n in names]
        ax.bar(range(len(names)), vals, color=colors)
        ax.axhline(M["sports"][s]["baseline"]["prior_log_loss"], color=MUTE, ls="--", lw=1)
        ax.text(len(names) - 0.5, M["sports"][s]["baseline"]["prior_log_loss"], " prior", va="bottom", ha="right", fontsize=8, color=MUTE)
        ax.set_xticks(range(len(names))); ax.set_xticklabels(["LR", "RF", "GB", "XGB"])
        ax.set_title(s.capitalize(), loc="left", fontsize=10); ax.set_ylim(min(vals) * 0.9, M["sports"][s]["baseline"]["prior_log_loss"] * 1.04)
        for i, v in enumerate(vals):
            ax.text(i, v, f"{v:.3f}", ha="center", va="bottom", fontsize=8)
    axes[0].set_ylabel("Test log-loss (lower is better)")
    fig.suptitle("Model comparison on held-out synthetic matches (selected model coloured)", x=0.01, ha="left", fontsize=10)
    save(fig, "fig_model_comparison")


def fig_calibration():
    fig, axes = plt.subplots(1, 3, figsize=(10, 3.4))
    for ax, s in zip(axes, SPORTS):
        rel = M["sports"][s]["final"]["test"]["reliability"]
        x = [100 * b["mean_pred"] for b in rel if b["n"]]; y = [100 * b["frac_pos"] for b in rel if b["n"]]
        ax.plot([0, 100], [0, 100], color=MUTE, ls="--", lw=1); ax.plot(x, y, "-o", color=SPORT_COL[s], ms=4)
        ax.set_title(f"{s.capitalize()}  ECE {M['sports'][s]['final']['test']['ece']:.3f}", loc="left", fontsize=10)
        ax.set_xlabel("Predicted probability (%)" if s != "football" else "Top-class confidence (%)")
        ax.set_xlim(0, 100); ax.set_ylim(0, 100); ax.set_aspect("equal")
    axes[0].set_ylabel("Observed frequency (%)")
    save(fig, "fig_calibration")


def fig_importance():
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.4))
    for ax, s in zip(axes, SPORTS):
        imp = list(M["sports"][s]["feature_importance"].items())[:7][::-1]
        ax.barh([k for k, _ in imp], [v for _, v in imp], color=SPORT_COL[s])
        ax.set_title(s.capitalize(), loc="left", fontsize=10); ax.tick_params(axis="y", labelsize=8)
        ax.set_xlabel("Log-loss increase when shuffled")
    fig.suptitle("Global permutation importance (a property of the model, not a causal effect)", x=0.01, ha="left", fontsize=10)
    save(fig, "fig_feature_importance")


def fig_confusion():
    fig, axes = plt.subplots(1, 3, figsize=(10.5, 3.3))
    for ax, s in zip(axes, SPORTS):
        r = M["sports"][s]; cm = r["final"]["test"]["confusion_matrix"]; n = len(cm)
        short = [c.replace(" side wins", "").replace(" win", "") for c in r["classes"]]
        rowsum = [sum(row) or 1 for row in cm]
        ax.imshow([[v / rowsum[i] for v in row] for i, row in enumerate(cm)], cmap="Greens", vmin=0, vmax=1)
        for i in range(n):
            for j in range(n):
                ax.text(j, i, f"{cm[i][j]:,}\n{cm[i][j] / rowsum[i]:.0%}", ha="center", va="center", fontsize=8,
                        color="white" if cm[i][j] / rowsum[i] > 0.55 else INK)
        ax.set_xticks(range(n)); ax.set_yticks(range(n)); ax.set_xticklabels(short, fontsize=8); ax.set_yticklabels(short, fontsize=8)
        ax.set_title(s.capitalize(), loc="left", fontsize=10); ax.set_xlabel("Predicted"); ax.spines[:].set_visible(False)
    axes[0].set_ylabel("Actual")
    save(fig, "fig_confusion_matrices")


# ------------------------------------------------------------------ diagrams
def box(ax, x, y, w, h, text, fc="white", ec=INK, fs=8.5, bold=False):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.01,rounding_size=0.012", fc=fc, ec=ec, lw=0.9))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fs, fontweight="bold" if bold else "normal", wrap=True)


def arrow(ax, x1, y1, x2, y2, label=None):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=9, lw=0.9, color=MUTE))
    if label:
        ax.text((x1 + x2) / 2, (y1 + y2) / 2 + 0.025, label, ha="center", fontsize=7, color=MUTE)


def canvas(w=10, h=4.2):
    fig, ax = plt.subplots(figsize=(w, h)); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); return fig, ax


def fig_architecture():
    fig, ax = canvas(10.5, 4.8); ax.set_ylim(-0.12, 1)
    box(ax, 0.01, 0.36, 0.19, 0.28, "React + TypeScript\nsingle-page app\ntyped API client", bold=True, fs=8)
    box(ax, 0.26, 0.36, 0.19, 0.28, "FastAPI\nrouters, Pydantic\nvalidation, rate limits", bold=True, fs=8)
    box(ax, 0.52, 0.72, 0.21, 0.22, "Services\nanalysis, simulation,\ncoach, HCI study", fs=8)
    box(ax, 0.52, 0.36, 0.21, 0.28, "Sport Adapter\ncricket, football,\nbasketball: state,\nfeatures, events", fs=8)
    box(ax, 0.52, 0.06, 0.21, 0.22, "Predictor\nsaved sklearn models,\nbootstrap band, Shapley", fs=8)
    box(ax, 0.80, 0.36, 0.19, 0.28, "SQLite / PostgreSQL\nmatches, players,\nsimulation runs,\nHCI data", fs=8)
    box(ax, 0.80, 0.06, 0.19, 0.22, "Offline training\ntrain_all.py writes\nmodels + metrics.json", fs=8)
    box(ax, 0.26, 0.06, 0.19, 0.22, "Synthetic simulators\nseeded, reproducible", fs=8)
    arrow(ax, 0.20, 0.50, 0.26, 0.50); ax.text(0.23, 0.53, "JSON", ha="center", fontsize=7, color=MUTE)
    arrow(ax, 0.45, 0.58, 0.52, 0.80); arrow(ax, 0.45, 0.50, 0.52, 0.50)
    arrow(ax, 0.625, 0.72, 0.625, 0.64); arrow(ax, 0.625, 0.36, 0.625, 0.28)
    arrow(ax, 0.73, 0.50, 0.80, 0.50); arrow(ax, 0.73, 0.82, 0.86, 0.64)
    arrow(ax, 0.80, 0.17, 0.73, 0.17, "loads"); 
    ax.add_patch(FancyArrowPatch((0.355, 0.06), (0.895, 0.06), arrowstyle="-|>", mutation_scale=9, lw=0.9, color=MUTE, connectionstyle="arc3,rad=0.12"))
    ax.text(0.62, -0.075, "generates training data", ha="center", fontsize=7, color=MUTE)
    ax.set_title("System architecture", loc="left", fontsize=10)
    save(fig, "fig_architecture", svg=True)


def fig_pipeline():
    fig, ax = canvas(10.5, 2.9)
    steps = ["Seeded simulator\n(ball, minute or\npossession)", "Snapshot table\nfeatures + label\n(+ match_id)", "Chronological,\nmatch-grouped\nsplit 70/15/15",
             "Fit four models\non the train\nsplit only", "Select by validation\nlog-loss (simplest\nwithin 1%)", "Calibrate only if\nit helps; evaluate\nonce on test"]
    w, gap = 0.13, 0.034
    xs = [0.01 + i * (w + gap) for i in range(len(steps))]
    for t, x in zip(steps, xs):
        box(ax, x, 0.30, w, 0.40, t, fs=8)
    for x1, x2 in zip(xs, xs[1:]):
        arrow(ax, x1 + w + 0.004, 0.50, x2 - 0.004, 0.50)
    ax.text(0.01, 0.10, "Leakage controls: features use only state known at the snapshot; Elo is updated after each match; scaler fitted on train only; labels never enter features.",
            fontsize=8, color=MUTE)
    ax.set_title("End-to-end ML pipeline", loc="left", fontsize=10)
    save(fig, "fig_ml_pipeline", svg=True)


def fig_hci_conditions():
    fig, ax = canvas(10, 3.6)
    box(ax, 0.02, 0.10, 0.44, 0.78, "", fc="white")
    box(ax, 0.54, 0.10, 0.44, 0.78, "", fc="white")
    ax.text(0.04, 0.82, "Interface A: prediction only", fontsize=10, fontweight="bold")
    ax.text(0.56, 0.82, "Interface B: interactive + explainable", fontsize=10, fontweight="bold")
    box(ax, 0.05, 0.60, 0.38, 0.14, "Scoreboard and match status", fs=8.5)
    box(ax, 0.05, 0.38, 0.38, 0.16, "Win probability (single number\nor win / draw / loss)", fs=8.5, ec=ACC)
    ax.text(0.05, 0.22, "No reasons, no uncertainty detail,\nno what-if controls", fontsize=8.5, color=MUTE)
    box(ax, 0.57, 0.60, 0.38, 0.14, "Scoreboard and match status", fs=8.5)
    box(ax, 0.57, 0.405, 0.38, 0.13, "Win probability (same model)", fs=8.5, ec=ACC)
    box(ax, 0.57, 0.265, 0.38, 0.10, "\"Why?\" helping / hurting factors", fs=8.5)
    box(ax, 0.57, 0.135, 0.38, 0.10, "\"Simulate\": run an event, see the change", fs=8.5)
    ax.set_title("Between-subjects conditions (same model, same scenarios)", loc="left", fontsize=10)
    save(fig, "fig_hci_conditions", svg=True)


def fig_study_flow():
    fig, ax = canvas(10, 2.6)
    steps = ["Consent +\nanonymous code", "Assigned to A or B\n(alternating)", "5 tasks\n(order rotated)", "Per task: answer,\nconfidence, trust,\ntime, interactions", "SUS (10) +\ntrust items (4) +\noptional comment", "Export\nCSV / JSON"]
    for i, t in enumerate(steps):
        x = 0.01 + i * 0.165
        box(ax, x, 0.28, 0.14, 0.44, t, fs=8)
        if i:
            arrow(ax, x - 0.025, 0.50, x, 0.50)
    ax.set_title("Study procedure", loc="left", fontsize=10)
    save(fig, "fig_study_flow", svg=True)


def main():
    tables()
    for f in (fig_comparison, fig_calibration, fig_importance, fig_confusion, fig_architecture, fig_pipeline, fig_hci_conditions, fig_study_flow):
        f()
    shots = ROOT / "docs" / "screenshots"
    for p in list(FIG.glob("*.png")) + list(FIG.glob("*.svg")) + list(shots.glob("*.png")):
        shutil.copy(p, POSTER / p.name)
    print("poster_assets:", len(list(POSTER.iterdir())), "files")


if __name__ == "__main__":
    main()
