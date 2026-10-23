"""ML behaviour, explanations, simulation pipeline and coach."""
import pytest

from app.ml.predictor import get_win_predictor
from app.services import analysis, simulation
from app.services import coach as coach_svc
from app.sports.registry import ADAPTERS, get_adapter
from tests.conftest import CRICKET


def test_model_quality_beats_baselines():
    m = analysis.metrics()
    for sport, r in m["sports"].items():
        t = r["final"]["test"]
        assert t["accuracy"] > r["baseline"]["majority_accuracy"] + 0.05, sport
        assert t["log_loss"] < r["baseline"]["prior_log_loss"], sport
        assert t["roc_auc"] > 0.7, sport
        assert 0 <= t["brier"] <= 1 and t["ece"] < 0.15, sport


@pytest.mark.parametrize("sport", ["cricket", "football", "basketball"])
def test_probabilities_are_valid(sport):
    a = get_adapter(sport)
    res = analysis.analyze(sport, a.default_state() if sport != "cricket" else CRICKET, explain=False)
    ps = [o["prob"] for o in res["outcomes"]]
    assert abs(sum(ps) - 1) < 1e-6 and all(0 <= p <= 1 for p in ps)
    for o in res["outcomes"]:
        assert o["lo"] <= o["prob"] + 1e-9 <= o["hi"] + 2e-9


def test_cricket_monotonic_sanity():
    base = analysis.analyze("cricket", CRICKET, explain=False)["headline"]["prob"]
    harder = analysis.analyze("cricket", {**CRICKET, "target": 200}, explain=False)["headline"]["prob"]
    fewer_wkts = analysis.analyze("cricket", {**CRICKET, "wickets": 8}, explain=False)["headline"]["prob"]
    assert harder < base and fewer_wkts < base


def test_shapley_additivity():
    res = analysis.analyze("cricket", CRICKET, explain=True)
    ex = res["explanation"]
    total = ex["base_value"] + sum(r["contribution_pp"] for r in ex["contributions"]) / 100
    assert abs(total - ex["probability"]) < 5e-3
    assert abs(ex["technical"]["additivity_gap_pp"]) < 0.5
    assert ex["simple"]["positives"] or ex["simple"]["negatives"]


def test_explanation_is_deterministic():
    a = analysis.analyze("cricket", CRICKET)["explanation"]["contributions"][0]
    b = analysis.analyze("cricket", CRICKET)["explanation"]["contributions"][0]
    assert a == b


def test_simulation_goes_through_the_model():
    """The 'after' probability must equal an independent model evaluation of the post-event state."""
    res = simulation.simulate("cricket", CRICKET, [{"id": "six", "count": 1}])
    a = get_adapter("cricket")
    after_state = a.validate(a.apply_event(a.validate(CRICKET), "six"))
    direct = get_win_predictor("cricket").proba([a.features(after_state)])[0][1]
    assert abs(res["after"]["headline"]["prob"] - direct) < 1e-9
    assert res["after"]["headline"]["prob"] != res["before"]["headline"]["prob"]
    assert res["attribution"]["rows"]


def test_event_directions():
    c = simulation.sweep("cricket", CRICKET)["impacts"]
    d = {r["id"]: r["delta_pp"] for r in c}
    assert d["six"] > d["four"] > 0 > d["wicket"] and d["two_wickets"] < d["wicket"]
    fb = get_adapter("football").default_state()
    fb.update(minute=60, home_elo=1500, away_elo=1500)
    d = {r["id"]: r["delta_pp"] for r in simulation.sweep("football", fb)["impacts"]}
    assert d["home_goal"] > 0 > d["away_goal"] and d["home_red"] < 0 < d["away_red"]
    bb = get_adapter("basketball").default_state()
    bb.update(elapsed_sec=1500)
    d = {r["id"]: r["delta_pp"] for r in simulation.sweep("basketball", bb)["impacts"]}
    assert d["home_three"] > 0 > d["away_three"]


@pytest.mark.parametrize("sport", ["cricket", "football", "basketball"])
def test_coach_output(sport):
    a = get_adapter(sport)
    st = CRICKET if sport == "cricket" else {**a.default_state(), **({"minute": 55} if sport == "football" else {"elapsed_sec": 1500})}
    out = coach_svc.coach(sport, st)
    assert out["available"] and len(out["options"]) == 3 and sum(o["best"] for o in out["options"]) == 1
    assert 0.5 <= out["confidence"] <= 0.99 and "not a guaranteed" in out["framing"]
    assert coach_svc.coach(sport, st)["recommendation"] == out["recommendation"]      # deterministic for the same state


def test_terminal_states():
    won = analysis.analyze("cricket", {**CRICKET, "runs": 172}, explain=True)
    assert won["terminal"] and won["headline"]["prob"] == 1.0 and won["explanation"] is None
    lost = analysis.analyze("cricket", {**CRICKET, "wickets": 10}, explain=False)
    assert lost["terminal"] and lost["headline"]["prob"] == 0.0
    assert coach_svc.coach("cricket", {**CRICKET, "runs": 172})["available"] is False


def test_momentum_bounds_and_explainability():
    for sport, a in ADAPTERS.items():
        m = a.momentum(a.validate(CRICKET if sport == "cricket" else a.default_state()))
        assert 0 <= m["score"] <= 100 and m["factors"] and m["formula"]
        assert abs(sum(f["points"] for f in m["factors"]) - (m["score"] - 50)) < 0.5
    hot = ADAPTERS["cricket"].momentum(ADAPTERS["cricket"].validate({**CRICKET, "recent_runs": 40, "recent_boundaries": 6, "partnership_runs": 50}))
    cold = ADAPTERS["cricket"].momentum(ADAPTERS["cricket"].validate({**CRICKET, "recent_runs": 4, "recent_wickets": 3, "partnership_runs": 0}))
    assert hot["score"] > 70 > 30 > cold["score"] or (hot["score"] > cold["score"] + 40)
