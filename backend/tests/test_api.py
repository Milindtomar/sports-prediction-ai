"""HTTP API: normal flows, validation failures and edge cases."""
import pytest

from tests.conftest import CRICKET


def test_health_and_sports(client):
    r = client.get("/api/health")
    assert r.status_code == 200 and r.json()["models_loaded"] is True
    s = client.get("/api/sports").json()
    assert [x["key"] for x in s] == ["cricket", "football", "basketball"]
    assert all(x["model"]["accuracy"] > 0.5 for x in s)


@pytest.mark.parametrize("sport", ["cricket", "football", "basketball"])
def test_meta_default_state_and_predict(client, sport):
    meta = client.get(f"/api/sports/{sport}/meta").json()
    assert meta["events"] and meta["actions"] and meta["features"]
    st = client.get(f"/api/sports/{sport}/default-state").json()
    r = client.post(f"/api/{sport}/predict", json={"state": st})
    assert r.status_code == 200, r.text
    body = r.json()
    assert abs(sum(o["prob"] for o in body["outcomes"]) - 1) < 1e-6
    assert body["momentum"]["factors"] and body["disclaimer"].startswith("MODEL PREDICTION")
    assert body["explanation"]["simple"]["headline"] and body["explanation"]["technical"]["table"]


def test_predict_validation_errors(client):
    bad = [
        ("cricket", {**CRICKET, "wickets": 11}),
        ("cricket", {k: v for k, v in CRICKET.items() if k != "target"}),
        ("cricket", {**CRICKET, "balls_bowled": 121}),
        ("cricket", {**CRICKET, "unknown_field": 1}),
        ("basketball", {"home_fgm": 10, "home_fga": 5}),
        ("football", {"home_goals": 3, "home_sot": 1, "home_shots": 4}),
        ("football", {"minute": -1}),
    ]
    for sport, st in bad:
        r = client.post(f"/api/{sport}/predict", json={"state": st})
        assert r.status_code == 422, (sport, st, r.text)
        assert r.json()["error"]["code"] in ("invalid_state", "invalid_request")


def test_unknown_sport_and_malformed_body(client):
    assert client.post("/api/tennis/predict", json={"state": {}}).status_code == 404
    assert client.post("/api/cricket/predict", json={}).status_code == 422
    assert client.post("/api/cricket/predict", content="not json", headers={"Content-Type": "application/json"}).status_code == 422
    assert client.get("/api/matches/99999").status_code == 404


def test_simulate_and_sweep_and_audit_log(client):
    r = client.post("/api/cricket/simulate", json={"state": CRICKET, "events": [{"id": "six"}]})
    assert r.status_code == 200, r.text
    b = r.json()
    assert b["deltas"][1]["delta_pp"] > 0 and b["narrative"] and b["attribution"]["rows"]
    assert b["pipeline"][2].startswith("model.predict_proba")
    assert client.post("/api/cricket/simulate", json={"state": CRICKET, "events": [{"id": "nope"}]}).status_code == 404
    assert client.post("/api/cricket/simulate", json={"state": CRICKET, "events": []}).status_code == 422
    # overrides are validated too
    assert client.post("/api/cricket/simulate", json={"state": CRICKET, "events": [{"id": "six"}], "overrides": {"wickets": 99}}).status_code == 422
    sw = client.post("/api/cricket/simulate/sweep", json={"state": CRICKET}).json()
    assert len(sw["impacts"]) == 10 and sw["impacts"] == sorted(sw["impacts"], key=lambda r: -r["delta_pp"])
    rec = client.get("/api/simulations/recent").json()
    assert rec and rec[0]["sport"] == "cricket"                       # DB write verified


def test_simulate_edge_case_chase_completes(client):
    st = {**CRICKET, "runs": 168}
    r = client.post("/api/cricket/simulate", json={"state": st, "events": [{"id": "six"}]})
    assert r.status_code == 200 and r.json()["after"]["terminal"] is True and r.json()["after"]["headline"]["prob"] == 1.0


def test_coach_endpoint(client):
    r = client.post("/api/cricket/coach", json={"state": CRICKET})
    assert r.status_code == 200 and r.json()["recommendation"]
    f = client.post("/api/football/coach", json={"state": {"minute": 60, "home_goals": 0, "away_goals": 1, "away_shots": 3, "away_sot": 1}, "side": "home"})
    assert f.status_code == 200 and f.json()["metric"] == "expected points"
    assert client.post("/api/football/coach", json={"state": {}, "side": "bogus"}).status_code == 422


def test_matches_flow(client):
    ms = client.get("/api/matches").json()
    assert {m["sport"] for m in ms} == {"cricket", "football", "basketball"} and len(ms) == 6
    for m in ms:
        d = client.get(f"/api/matches/{m['id']}").json()
        assert d["timeline"] and d["events"] and d["meta"]["result"]
        ser = client.get(f"/api/matches/{m['id']}/series").json()
        assert len(ser["steps"]) == len(d["timeline"])
        assert all(abs(sum(s["probs"]) - 1) < 1e-6 for s in ser["steps"])
        last = len(d["timeline"]) - 1
        st = client.get(f"/api/matches/{m['id']}/steps/{last}").json()
        assert st["key_players"] is not None and st["scoreboard"]["teams"]
        mid = client.get(f"/api/matches/{m['id']}/steps/{last // 2}").json()
        assert mid["explanation"] or mid["terminal"]
    assert client.get(f"/api/matches/{ms[0]['id']}/steps/9999").status_code == 404
    assert len(client.get("/api/matches?sport=cricket").json()) == 2


def test_players_flow(client):
    for sport in ("cricket", "football", "basketball"):
        ps = client.get(f"/api/players?sport={sport}").json()
        assert len(ps) >= 30
        d = client.get(f"/api/players/{ps[0]['id']}").json()
        assert d["next_game"]["label"] == "MODEL PREDICTION" and d["history"]["label_actual"] == "ACTUAL RESULT"
        first_kind = next(iter(d["history"]["kinds"].values()))
        assert first_kind and "predicted" in first_kind[0] and "actual" in first_kind[0]
        assert d["profile"]["kinds"]
    cr = client.get("/api/players?sport=cricket").json()
    c = client.post("/api/players/compare", json={"a": cr[0]["id"], "b": cr[1]["id"]})
    assert c.status_code == 200 and c.json()["a"]["percentiles"]
    fb = client.get("/api/players?sport=football").json()
    assert client.post("/api/players/compare", json={"a": cr[0]["id"], "b": fb[0]["id"]}).status_code == 422
    assert client.post(f"/api/players/{cr[0]['id']}/predict", json={"opp_strength": 5}).status_code == 422
    assert client.get("/api/players/999999").status_code == 404
    p = client.post(f"/api/players/{cr[0]['id']}/predict", json={"opp_strength": -1.0, "venue_par": 175}).json()
    assert "bat" in p["kinds"]


def test_hci_flow_and_sus(client):
    t = client.get("/api/hci/tasks").json()
    assert len(t["tasks"]) == 5 and len(t["sus_items"]) == 10
    empty = client.get("/api/hci/results").json()
    assert empty["groups"]["A"]["participants"] == 0 and "No participant data" in empty["note"]
    sids = []
    for name in ("p1", "p2", "p3", "p4"):
        s = client.post("/api/hci/sessions", json={"participant": name, "consent": True}).json()
        sids.append(s)
    assert [s["condition"] for s in sids] == ["A", "B", "A", "B"]       # counter-balanced assignment
    for s in sids:
        for task in t["tasks"]:
            ans = task["options"][0]["id"]
            r = client.post(f"/api/hci/sessions/{s['id']}/results", json=dict(task_id=task["id"], answer=ans, time_ms=5000 + 1000 * s["id"],
                                                                                confidence=5, trust=4, interactions=0 if s["condition"] == "A" else 3))
            assert r.status_code == 200 and isinstance(r.json()["correct"], bool)
        assert client.post(f"/api/hci/sessions/{s['id']}/sus", json={"answers": [4, 2, 4, 2, 4, 2, 4, 2, 4, 2]}).json()["sus_score"] == 75.0
    dup = client.post(f"/api/hci/sessions/{sids[0]['id']}/results", json=dict(task_id="T1", answer=t["tasks"][0]["options"][0]["id"], time_ms=1, confidence=1, trust=1))
    assert dup.status_code == 409
    assert client.post(f"/api/hci/sessions/{sids[0]['id']}/sus", json={"answers": [1] * 9}).status_code == 422
    assert client.post(f"/api/hci/sessions/{sids[0]['id']}/sus", json={"answers": [6] * 10}).status_code == 422
    assert client.post(f"/api/hci/sessions/{sids[0]['id']}/results", json=dict(task_id="T9", answer="x", time_ms=1, confidence=1, trust=1)).status_code in (409, 422)
    res = client.get("/api/hci/results").json()
    assert res["groups"]["A"]["participants"] == 2 and res["groups"]["B"]["interactions"]["mean"] == 3
    assert res["groups"]["A"]["sus"]["mean"] == 75.0 and res["tests"]["sus"] is None   # zero variance -> undefined, not NaN
    csv = client.get("/api/hci/export.csv").text
    assert csv.splitlines()[0].startswith("session_id") and len(csv.splitlines()) == 1 + 4 * 5
    assert client.post("/api/hci/sessions/9999/results", json=dict(task_id="T1", answer="focus", time_ms=1, confidence=1, trust=1)).status_code == 404


def test_sus_scoring_unit():
    from app.services.hci import sus_score
    assert sus_score([3] * 10) == 50.0
    assert sus_score([5, 1] * 5) == 100.0
    assert sus_score([1, 5] * 5) == 0.0


def test_cors_headers(client):
    ok = client.options("/api/health", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"})
    assert ok.headers.get("access-control-allow-origin") == "http://localhost:5173"
    bad = client.options("/api/health", headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"})
    assert "access-control-allow-origin" not in bad.headers


def test_hci_ground_truth_is_objective():
    from app.services import hci
    for t in hci.TASKS:
        opts, truth = hci._options_and_truth(t)
        assert truth in [o["id"] for o in opts]
