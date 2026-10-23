"""Data generation, leakage prevention and feature engineering."""
import numpy as np

from app.sports.features import CRICKET_FEATURES, basketball_features, cricket_features, football_features
from app.synth import basketball as bsim
from app.synth import cricket as csim
from app.synth import football as fsim
from app.synth.common import chrono_split


def test_generators_are_deterministic():
    a, _ = csim.simulate_season(20, seed=3)
    b, _ = csim.simulate_season(20, seed=3)
    assert [m.score1 for m in a] == [m.score1 for m in b]
    f1, _ = fsim.simulate_season(10, seed=3)
    f2, _ = fsim.simulate_season(10, seed=3)
    assert [m.final["home_goals"] for m in f1] == [m.final["home_goals"] for m in f2]
    g1, _ = bsim.simulate_season(5, seed=3)
    g2, _ = bsim.simulate_season(5, seed=3)
    assert [g.final["home_score"] for g in g1] == [g.final["home_score"] for g in g2]


def test_pre_match_elo_is_leakage_free():
    ms, _ = csim.simulate_season(30, seed=5)
    assert ms[0].inn1[0]["batting_elo"] == 1500.0 and ms[0].inn1[0]["bowling_elo"] == 1500.0   # nothing learned yet
    for m in ms:   # constant within a match: updated only AFTER the match
        assert len({s["batting_elo"] for s in m.inn1}) == 1


def test_snapshots_never_contain_final_state():
    ms, _ = csim.simulate_season(30, seed=5)
    for m in ms:
        assert all(s["balls_bowled"] < 120 or s["wickets"] >= 10 or s["balls_bowled"] == 120 for s in m.inn1)
        assert max(s["runs"] for s in m.inn1) <= m.score1
    fs, _ = fsim.simulate_season(20, seed=5)
    assert all(max(s["minute"] for s in m.snaps) <= 85 for m in fs)       # full-time state is not a training row
    gs, _ = bsim.simulate_season(10, seed=5)
    assert all(max(s["elapsed_sec"] for s in g.snaps) < bsim.GAME_SEC for g in gs)


def test_chronological_split_has_no_overlap():
    ids = np.repeat(np.arange(100), 5)
    tr, va, te = chrono_split(ids)
    assert ids[tr].max() < ids[va].min() and ids[va].max() < ids[te].min()
    assert tr.sum() + va.sum() + te.sum() == len(ids)


def test_cricket_features_known_values():
    s = dict(innings=2, target=172, runs=118, wickets=4, balls_bowled=90, partnership_runs=32, recent_runs=17,
             recent_wickets=0, batting_elo=1500, bowling_elo=1500, venue_par=158)
    f = cricket_features(s)
    assert f["runs_required"] == 54 and f["balls_remaining"] == 30
    assert abs(f["crr"] - 7.8667) < 1e-3 and abs(f["rrr"] - 10.8) < 1e-9
    assert abs(f["rr_diff"] - (7.8667 - 10.8)) < 1e-3
    assert list(f) == CRICKET_FEATURES


def test_cricket_features_edge_cases():
    s0 = dict(innings=1, target=None, runs=0, wickets=0, balls_bowled=0, partnership_runs=0, recent_runs=0,
              recent_wickets=0, batting_elo=1500, bowling_elo=1500, venue_par=160)
    f = cricket_features(s0)
    assert f["crr"] == 8.0 and f["resources"] == 1.0           # pre-match: par rate, full resources
    s1 = dict(s0, innings=2, target=150, wickets=10, balls_bowled=60, runs=80)
    f1 = cricket_features(s1)
    assert f1["resources"] == 0.0 and np.isfinite(list(f1.values())).all()
    s2 = dict(s0, innings=2, target=150, balls_bowled=119, runs=100)
    assert cricket_features(s2)["rrr"] <= 36.0


def test_football_and_basketball_features_finite():
    fs, _ = fsim.simulate_season(3, seed=1)
    assert np.isfinite(list(football_features(fs[0].snaps[-1]).values())).all()
    gs, _ = bsim.simulate_season(2, seed=1)
    assert np.isfinite(list(basketball_features(gs[0].snaps[-1]).values())).all()
    assert np.isfinite(list(basketball_features(gs[0].snaps[0]).values())).all()   # 0/0 shooting percentages handled
