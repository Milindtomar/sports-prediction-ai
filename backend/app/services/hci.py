"""HCI study module: Interface A (probability only) vs Interface B (explainable + interactive).

Tasks have server-side ground truth derived from the real prediction pipeline (Shapley
attribution, event sweep), so "decision accuracy" is objective. Results are never
fabricated: until participants complete tasks the aggregates are empty.
"""
from __future__ import annotations

import csv
import io
import math

import numpy as np
from scipy import stats as st
from sqlmodel import Session, select

from app.models_db import HciSession, HciTaskResult
from app.services.analysis import analyze
from app.services.simulation import sweep
from app.sports.registry import get_adapter

CRICKET = dict(innings=2, target=172, runs=118, wickets=4, balls_bowled=90, partnership_runs=32, partnership_balls=22,
               recent_runs=17, recent_wickets=0, recent_boundaries=2, venue="Harbour Oval",
               batting_team="Harbor Kings", bowling_team="Crimson Falcons", batting_elo=1510, bowling_elo=1500)
BASKETBALL = dict(elapsed_sec=1800, home_score=71, away_score=66, possession=0, home_fgm=26, home_fga=56, away_fgm=24, away_fga=55,
                  home_3pm=7, home_3pa=18, away_3pm=5, away_3pa=17, home_ftm=12, home_fta=15, away_ftm=13, away_fta=17,
                  home_reb=22, away_reb=24, home_ast=15, away_ast=12, home_tov=8, away_tov=10, home_fouls=12, away_fouls=14,
                  home_elo=1540, away_elo=1500, recent_points_home=11, recent_points_away=8, current_run=0)
FOOTBALL = dict(minute=55, home_goals=1, away_goals=1, home_shots=11, away_shots=6, home_sot=5, away_sot=2, home_xg=1.4, away_xg=0.6,
                home_possession=56, home_corners=5, away_corners=2, home_fouls=8, away_fouls=10, home_yellow=1, away_yellow=2,
                home_pass_acc=84, away_pass_acc=79, home_elo=1560, away_elo=1500, recent_shots_home=4, recent_shots_away=1,
                recent_xg_home=0.5, recent_xg_away=0.1)

TASKS = [
    dict(id="T1", sport="cricket", kind="read", title="Reading the prediction", state=CRICKET,
         prompt="Looking at the current situation, which side is favoured to win?"),
    dict(id="T2", sport="cricket", kind="why", title="Understanding the prediction", state=CRICKET,
         prompt="Which factor has the LARGEST influence on the model's current win probability?"),
    dict(id="T3", sport="cricket", kind="whatif", title="What-if reasoning", state=CRICKET, direction="max",
         events=["six", "flat_pitch", "big_over", "four"], who="the batting side",
         prompt="Which ONE of these events would INCREASE the batting side's win probability the most?"),
    dict(id="T4", sport="basketball", kind="whatif", title="Decision under uncertainty", state=BASKETBALL, direction="min",
         events=["away_three", "away_run", "home_star_out", "home_turnover"], who="the home team",
         prompt="Which ONE of these events would REDUCE the home team's win probability the most?"),
    dict(id="T5", sport="football", kind="why", title="Explaining a prediction", state=FOOTBALL,
         prompt="Which factor is the main driver of the current HOME-win probability?"),
]
TASK_IDS = [t["id"] for t in TASKS]


def _label(sport: str, feat: str) -> str:
    m = get_adapter(sport).feature_meta.get(feat)
    return m.label if m else feat


def _options_and_truth(t: dict) -> tuple[list[dict], str]:
    a = get_adapter(t["sport"])
    state = a.validate(t["state"])
    if t["kind"] == "read":
        res = analyze(t["sport"], state, explain=False)
        p = res["headline"]["prob"]
        opts = [dict(id="focus", label=state["batting_team"]), dict(id="other", label=state["bowling_team"]),
                dict(id="close", label="Too close to call (45–55%)")]
        truth = "close" if 0.45 <= p <= 0.55 else ("focus" if p > 0.55 else "other")
        return opts, truth
    if t["kind"] == "why":
        res = analyze(t["sport"], state, explain=True)
        rows = res["explanation"]["contributions"]
        top = rows[0]["feature"]
        distract = [r["feature"] for r in rows[3:] if r["feature"] != top][:3]
        fs = [top] + distract
        # deterministic shuffle so the correct answer is not always first
        order = sorted(fs, key=lambda f: (hash_str(t["id"] + f)))
        return [dict(id=f, label=_label(t["sport"], f)) for f in order], top
    sw = sweep(t["sport"], state)
    by = {r["id"]: r for r in sw["impacts"]}
    ids = t["events"]
    best = max(ids, key=lambda i: by[i]["delta_pp"]) if t["direction"] == "max" else min(ids, key=lambda i: by[i]["delta_pp"])
    labels = {e.id: e.label for e in a.events}
    return [dict(id=i, label=labels[i]) for i in ids], best


def hash_str(s: str) -> int:
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) % 1_000_003
    return h


def public_tasks() -> list[dict]:
    out = []
    for t in TASKS:
        opts, _ = _options_and_truth(t)
        out.append(dict(id=t["id"], sport=t["sport"], kind=t["kind"], title=t["title"], prompt=t["prompt"],
                        state=get_adapter(t["sport"]).validate(t["state"]), options=opts))
    return out


def check_answer(task_id: str, answer: str) -> bool:
    t = next(x for x in TASKS if x["id"] == task_id)
    return _options_and_truth(t)[1] == answer


def grade(task_id: str, answer: str) -> tuple[bool, bool]:
    """-> (answer_is_one_of_the_offered_options, answer_matches_ground_truth)."""
    t = next(x for x in TASKS if x["id"] == task_id)
    opts, truth = _options_and_truth(t)
    return answer in {o["id"] for o in opts}, answer == truth


def sus_score(answers: list[int]) -> float:
    if len(answers) != 10 or any(a < 1 or a > 5 for a in answers):
        raise ValueError("SUS needs 10 answers between 1 and 5")
    total = sum((a - 1) if i % 2 == 0 else (5 - a) for i, a in enumerate(answers))
    return total * 2.5


SUS_ITEMS = [
    "I think that I would like to use this system frequently.", "I found the system unnecessarily complex.",
    "I thought the system was easy to use.", "I think that I would need the support of a technical person to be able to use this system.",
    "I found the various functions in this system were well integrated.", "I thought there was too much inconsistency in this system.",
    "I would imagine that most people would learn to use this system very quickly.", "I found the system very cumbersome to use.",
    "I felt very confident using the system.", "I needed to learn a lot of things before I could get going with this system.",
]


# Study-specific trust items (1 = strongly disagree ... 7 = strongly agree). NOT a validated instrument.
TRUST_ITEMS = [
    "I understood why the system gave the prediction it showed.",
    "I would rely on this prediction when making a decision about this match.",
    "I could tell when the prediction might be wrong or uncertain.",
    "I felt the prediction was trustworthy.",
]

CONSENT_TEXT = (
    "This is a short, voluntary study about how people read sports predictions. You will complete five tasks and two short "
    "questionnaires (about 8-10 minutes). We record an anonymous participant code, which interface you saw, your answers, "
    "how long each task took, your ratings and optional free-text feedback. We do not record your name, email, ID or location. "
    "You may stop at any time without giving a reason; ask the researcher to delete your session if you withdraw. All matches "
    "and predictions are synthetic demonstration data. If this is a real study, it must follow your course or institution's "
    "ethics and consent requirements; this application does not itself provide ethics approval."
)


def next_condition(session: Session) -> str:
    n = len(session.exec(select(HciSession)).all())
    return "A" if n % 2 == 0 else "B"   # alternating assignment keeps groups balanced


def _desc(x):
    x = np.asarray(x, float)
    return dict(n=int(len(x)), mean=float(x.mean()) if len(x) else None, sd=float(x.std(ddof=1)) if len(x) > 1 else None)


def _cohen_d(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if len(a) < 2 or len(b) < 2:
        return None
    sp = math.sqrt(((len(a) - 1) * a.var(ddof=1) + (len(b) - 1) * b.var(ddof=1)) / (len(a) + len(b) - 2))
    return float((b.mean() - a.mean()) / sp) if sp > 0 else None


def _welch(a, b):
    if len(a) < 2 or len(b) < 2:
        return None
    if np.std(a) == 0 and np.std(b) == 0:      # no variance in either group: the test is undefined
        return None
    t = st.ttest_ind(b, a, equal_var=False)
    if not (math.isfinite(t.statistic) and math.isfinite(t.pvalue)):
        return None
    return dict(t=float(t.statistic), p=float(t.pvalue), cohen_d=_cohen_d(a, b))


def results(session: Session) -> dict:
    sessions = session.exec(select(HciSession)).all()
    res = session.exec(select(HciTaskResult)).all()
    by_sess = {s.id: s for s in sessions}
    groups = {"A": dict(time=[], correct=[], conf=[], trust=[], inter=[], sus=[], participants=set()),
              "B": dict(time=[], correct=[], conf=[], trust=[], inter=[], sus=[], participants=set())}
    per_task = {tid: {"A": dict(n=0, correct=0, time=[]), "B": dict(n=0, correct=0, time=[])} for tid in TASK_IDS}
    for r in res:
        s = by_sess.get(r.session_id)
        if not s:
            continue
        g = groups[s.condition]
        g["participants"].add(s.id)
        g["time"].append(r.time_ms / 1000)
        g["correct"].append(int(r.correct))
        g["conf"].append(r.confidence)
        g["trust"].append(r.trust)
        g["inter"].append(r.interactions)
        pt = per_task[r.task_id][s.condition]
        pt["n"] += 1
        pt["correct"] += int(r.correct)
        pt["time"].append(r.time_ms / 1000)
    for s in sessions:
        if s.sus_score is not None:
            groups[s.condition]["sus"].append(s.sus_score)
    trust_scale = {c: [float(np.mean(s.trust_answers)) for s in sessions if s.condition == c and s.trust_answers] for c in ("A", "B")}
    summary = {}
    for c, g in groups.items():
        summary[c] = dict(participants=len(g["participants"]), tasks=len(g["time"]), time_s=_desc(g["time"]),
                          accuracy=float(np.mean(g["correct"])) if g["correct"] else None, confidence=_desc(g["conf"]),
                          trust=_desc(g["trust"]), interactions=_desc(g["inter"]), sus=_desc(g["sus"]),
                          trust_scale=_desc(trust_scale[c]))
    tests = {}
    a, b = groups["A"], groups["B"]
    tests["time"] = _welch(a["time"], b["time"])
    tests["confidence"] = _welch(a["conf"], b["conf"])
    tests["trust"] = _welch(a["trust"], b["trust"])
    tests["sus"] = _welch(a["sus"], b["sus"])
    tests["trust_scale"] = _welch(trust_scale["A"], trust_scale["B"])
    if a["correct"] and b["correct"]:
        table = [[sum(a["correct"]), len(a["correct"]) - sum(a["correct"])], [sum(b["correct"]), len(b["correct"]) - sum(b["correct"])]]
        _, p = st.fisher_exact(table)
        tests["accuracy"] = dict(p=float(p), test="Fisher exact (task-level)")
    else:
        tests["accuracy"] = None
    tasks = []
    for tid in TASK_IDS:
        row = {"id": tid}
        for c in ("A", "B"):
            d = per_task[tid][c]
            row[c] = dict(n=d["n"], accuracy=(d["correct"] / d["n"]) if d["n"] else None,
                          time_s=float(np.mean(d["time"])) if d["time"] else None)
        tasks.append(row)
    total = len(sessions)
    return dict(n_sessions=total, completed=sum(1 for s in sessions if s.completed), groups=summary, tests=tests, per_task=tasks,
                note=("No participant data yet - run the study to populate this view." if not res else
                      "Small samples: treat p-values as descriptive. Task-level accuracy pools tasks within participants, "
                      "which violates independence; use the participant-level export for formal analysis."))


EXPORT_COLUMNS = ["session_id", "participant", "condition", "experience", "consented", "task_id", "position", "answer", "correct",
                  "time_ms", "confidence", "trust", "interactions", "sus_score", "trust_item_mean", "feedback", "data_origin"]


def _safe(v):
    """Neutralise spreadsheet formula injection (cells starting with = + - @ are executed by Excel/Sheets)."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + v
    return v


def export_rows(session: Session) -> list[dict]:
    rows = session.exec(select(HciTaskResult, HciSession).where(HciTaskResult.session_id == HciSession.id)
                        .order_by(HciSession.id, HciTaskResult.id)).all()
    out = []
    for r, s in rows:
        out.append(dict(session_id=s.id, participant=s.participant, condition=s.condition, experience=s.experience,
                        consented=int(bool(s.consented)), task_id=r.task_id, position=r.position, answer=r.answer,
                        correct=int(r.correct), time_ms=r.time_ms, confidence=r.confidence, trust=r.trust,
                        interactions=r.interactions, sus_score=s.sus_score,
                        trust_item_mean=(round(float(np.mean(s.trust_answers)), 3) if s.trust_answers else None),
                        feedback=s.feedback or "", data_origin="participant"))
    return out


def export_csv(session: Session) -> str:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=EXPORT_COLUMNS)
    w.writeheader()
    for row in export_rows(session):
        w.writerow({k: ("" if v is None else _safe(v)) for k, v in row.items()})
    return buf.getvalue()


def export_json(session: Session) -> dict:
    return dict(schema=EXPORT_COLUMNS, rows=export_rows(session),
                note="One row per participant x task. sus_score, trust_item_mean and feedback repeat per participant. "
                     "trust_item_mean is a study-specific 4-item measure, not a validated scale.")
