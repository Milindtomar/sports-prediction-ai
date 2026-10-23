"""Analyse an exported HCI study file (CSV from /api/hci/export.csv or JSON from /api/hci/export.json).

    python scripts/analyze_hci.py study_export.csv
    python scripts/analyze_hci.py study_export.json --min-per-group 8
    python scripts/analyze_hci.py --demo          # runs on SIMULATED rows to show the script works. Never use for findings.

Design analysed: BETWEEN-subjects (each participant sees interface A or B). The unit of analysis is the PARTICIPANT
(task-level rows are averaged within participant), so tests do not pool non-independent rows.

Per measure: descriptives, Welch t-test, Mann-Whitney U (robust to non-normality), Cohen's d with a seeded bootstrap 95% CI.
Missing data: participants with fewer than 5 task rows are excluded (reported); SUS / trust items are analysed for those who
completed them. Inferential statistics are NOT computed when a group has fewer than --min-per-group participants (default 5):
the script prints descriptives and says so instead of reporting p-values from tiny or empty samples.
Assumptions (stated, not tested away): independent participants, ordinal Likert items treated as interval for the t-test
(hence the Mann-Whitney check), no multiple-comparison correction (7 measures: treat any single p as exploratory).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

N_TASKS = 5
MEASURES = [("time_s", "Task time (s, mean per task)"), ("accuracy", "Decision accuracy (share correct)"),
            ("confidence", "Confidence (1-7)"), ("trust", "Trust, single rating (1-7)"), ("interactions", "Interactions (total)"),
            ("sus_score", "SUS (0-100)"), ("trust_item_mean", "Trust items, mean of 4 (1-7, study-specific)")]


def load(path: Path) -> pd.DataFrame:
    if path.suffix.lower() == ".json":
        return pd.DataFrame(json.loads(path.read_text())["rows"])
    return pd.read_csv(path)


def participant_table(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    g = df.groupby("session_id")
    p = g.agg(condition=("condition", "first"), n_tasks=("task_id", "nunique"), time_s=("time_ms", lambda x: x.mean() / 1000),
              accuracy=("correct", "mean"), confidence=("confidence", "mean"), trust=("trust", "mean"),
              interactions=("interactions", "sum"), sus_score=("sus_score", "first"),
              trust_item_mean=("trust_item_mean", "first")).reset_index()
    full = p[p["n_tasks"] >= N_TASKS]
    return full, len(p) - len(full)


def boot_d_ci(a: np.ndarray, b: np.ndarray, reps: int = 2000, seed: int = 0):
    rng = np.random.default_rng(seed)
    def d(x, y):
        sp = np.sqrt(((len(x) - 1) * x.var(ddof=1) + (len(y) - 1) * y.var(ddof=1)) / (len(x) + len(y) - 2))
        return (y.mean() - x.mean()) / sp if sp > 0 else np.nan
    vals = [d(rng.choice(a, len(a)), rng.choice(b, len(b))) for _ in range(reps)]
    vals = np.array([v for v in vals if np.isfinite(v)])
    return (float(np.percentile(vals, 2.5)), float(np.percentile(vals, 97.5))) if len(vals) > reps // 2 else (None, None)


def compare(a: np.ndarray, b: np.ndarray) -> dict:
    out = dict(t=None, p_welch=None, u=None, p_mwu=None, d=None, d_ci=(None, None))
    if a.std() == 0 and b.std() == 0:
        return out
    t = stats.ttest_ind(b, a, equal_var=False)
    u = stats.mannwhitneyu(b, a, alternative="two-sided")
    sp = np.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    out.update(t=float(t.statistic), p_welch=float(t.pvalue), u=float(u.statistic), p_mwu=float(u.pvalue),
               d=float((b.mean() - a.mean()) / sp) if sp > 0 else None, d_ci=boot_d_ci(a, b))
    return out


def fmt(x, dp=2):
    return "-" if x is None or (isinstance(x, float) and not np.isfinite(x)) else f"{x:.{dp}f}"


def demo_frame(seed: int = 4) -> pd.DataFrame:
    """SIMULATED participants for demonstrating the script. These are not people. Do not report them as results.
    By construction only accuracy, task time and interactions differ between A and B; every other measure is drawn from the same distribution."""
    rng = np.random.default_rng(seed)
    rows = []
    for sid in range(1, 21):
        cond = "A" if sid % 2 else "B"
        sus = float(np.clip(rng.normal(68 if cond == "A" else 74, 9), 0, 100))
        tm = float(np.clip(rng.normal(3.7, 0.6), 1, 7))
        for k in range(N_TASKS):
            rows.append(dict(session_id=sid, participant=f"SIM{sid:02d}", condition=cond, experience="simulated", consented=1,
                             task_id=f"T{k + 1}", position=k + 1, answer="sim", correct=int(rng.random() < (0.55 if cond == "A" else 0.72)),
                             time_ms=int(rng.normal(30000 if cond == "A" else 38000, 6000)), confidence=int(np.clip(rng.normal(4.6, 1.1), 1, 7)),
                             trust=int(np.clip(rng.normal(4.4, 1.1), 1, 7)), interactions=0 if cond == "A" else int(rng.poisson(2)),
                             sus_score=sus, trust_item_mean=tm, feedback="", data_origin="SIMULATED_DEMO"))
    return pd.DataFrame(rows)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("file", nargs="?", type=Path)
    ap.add_argument("--min-per-group", type=int, default=5)
    ap.add_argument("--demo", action="store_true", help="use SIMULATED rows (for demonstrating the script only)")
    a = ap.parse_args()
    if a.demo:
        df = demo_frame()
        print("*" * 78 + "\n*  SIMULATED DEMO DATA. These rows are not participants. Not research findings.  *\n" + "*" * 78)
    elif a.file:
        df = load(a.file)
    else:
        ap.error("give an export file or --demo")
    if df.empty:
        print("No study records in this file: nothing to analyse. Collect participant data first (no statistics are reported on empty data).")
        return 0
    if "data_origin" in df and (df["data_origin"] != "participant").any() and not a.demo:
        print("WARNING: file contains rows whose data_origin is not 'participant':", sorted(df["data_origin"].unique()))
    p, dropped = participant_table(df)
    nA, nB = int((p.condition == "A").sum()), int((p.condition == "B").sum())
    print(f"Participants with all {N_TASKS} tasks: A={nA}, B={nB}; excluded as incomplete: {dropped}")
    enough = min(nA, nB) >= a.min_per_group
    if not enough:
        print(f"Inferential statistics are NOT reported: need at least {a.min_per_group} participants per group (have A={nA}, B={nB}).")
    print(f"\n{'Measure':46s} {'A mean (sd)':>14s} {'B mean (sd)':>14s}" + (f" {'Welch p':>8s} {'MWU p':>7s} {'d [95% CI]':>22s}" if enough else ""))
    for col, label in MEASURES:
        A, B = p.loc[p.condition == "A", col].dropna().to_numpy(float), p.loc[p.condition == "B", col].dropna().to_numpy(float)
        sd = lambda x: x.std(ddof=1) if len(x) > 1 else None
        line = f"{label:46s} {fmt(A.mean() if len(A) else None):>6s} ({fmt(sd(A))}) {fmt(B.mean() if len(B) else None):>6s} ({fmt(sd(B))})"
        if enough and len(A) >= 2 and len(B) >= 2:
            r = compare(A, B); lo, hi = r["d_ci"]
            line += f" {fmt(r['p_welch'], 3):>8s} {fmt(r['p_mwu'], 3):>7s} {fmt(r['d']):>7s} [{fmt(lo)}, {fmt(hi)}]"
        print(line)
    print("\nAccuracy by task (share correct):")
    t = df.assign(correct=df["correct"].astype(float)).groupby(["task_id", "condition"])["correct"].agg(["mean", "count"]).unstack()
    print(t.round(2).to_string())
    return 0


if __name__ == "__main__":
    sys.exit(main())
