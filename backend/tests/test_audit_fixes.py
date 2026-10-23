"""Regression tests for bugs found in the Master-Prompt audit."""
import csv
import io

import pytest

from tests.conftest import CRICKET


def _task_options(client):
    return {t["id"]: [o["id"] for o in t["options"]] for t in client.get("/api/hci/tasks").json()["tasks"]}


def test_hci_requires_consent_and_anonymous_code(client):
    assert client.post("/api/hci/sessions", json={"participant": "c1"}).status_code == 422             # consent missing
    assert client.post("/api/hci/sessions", json={"participant": "c1", "consent": False}).status_code == 422
    assert client.post("/api/hci/sessions", json={"participant": "Jane Doe <jane@x.com>", "consent": True}).status_code == 422
    assert client.post("/api/hci/sessions", json={"participant": "P-01", "consent": True}).status_code == 200


def test_hci_rejects_blank_and_unoffered_answers_without_locking_the_task(client):
    sid = client.post("/api/hci/sessions", json={"participant": "blank-test", "consent": True}).json()["id"]
    base = dict(task_id="T1", time_ms=900, confidence=4, trust=4, interactions=0)
    assert client.post(f"/api/hci/sessions/{sid}/results", json={**base, "answer": ""}).status_code == 422
    assert client.post(f"/api/hci/sessions/{sid}/results", json={**base, "answer": "not-an-option"}).status_code == 422
    ok = client.post(f"/api/hci/sessions/{sid}/results", json={**base, "answer": _task_options(client)["T1"][0], "position": 1})
    assert ok.status_code == 200          # earlier rejected attempts must not have consumed T1


def test_hci_trust_items_feedback_and_json_export(client):
    sid = client.post("/api/hci/sessions", json={"participant": "extras", "consent": True}).json()["id"]
    r = client.post(f"/api/hci/sessions/{sid}/results", json=dict(task_id="T2", answer=_task_options(client)["T2"][0], time_ms=1000,
                                                                  confidence=3, trust=3, interactions=1, position=2))
    assert r.status_code == 200
    assert client.post(f"/api/hci/sessions/{sid}/sus", json={"answers": [3] * 10, "trust_items": [5, 6, 4, 5], "feedback": "Clear."}).status_code == 200
    assert client.post(f"/api/hci/sessions/{sid}/sus", json={"answers": [3] * 10, "trust_items": [5, 6, 4]}).status_code == 422
    data = client.get("/api/hci/export.json").json()
    row = next(x for x in data["rows"] if x["participant"] == "extras")
    assert set(data["schema"]) == set(row) and row["trust_item_mean"] == 5.0 and row["feedback"] == "Clear." and row["position"] == 2
    assert row["consented"] == 1 and row["data_origin"] == "participant"


def test_csv_export_neutralises_formula_injection(client):
    # participant codes are restricted, but feedback is free text and must never execute in a spreadsheet
    sid = client.post("/api/hci/sessions", json={"participant": "csv-test", "consent": True}).json()["id"]
    client.post(f"/api/hci/sessions/{sid}/results", json=dict(task_id="T3", answer=_task_options(client)["T3"][0], time_ms=10, confidence=2, trust=2))
    client.post(f"/api/hci/sessions/{sid}/sus", json={"answers": [3] * 10, "feedback": "=HYPERLINK(\"http://evil\",\"x\")"})
    rows = list(csv.DictReader(io.StringIO(client.get("/api/hci/export.csv").text)))
    fb = next(r["feedback"] for r in rows if r["participant"] == "csv-test")
    assert fb.startswith("'=")


def test_compare_same_player_rejected(client):
    pid = client.get("/api/players?sport=cricket").json()[0]["id"]
    assert client.post("/api/players/compare", json={"a": pid, "b": pid}).status_code == 422


@pytest.mark.parametrize("mut", [
    dict(bowling_team="Harbor Kings"),            # same team on both sides
    dict(venue="Mars Dome"),                      # unknown venue
    dict(partnership_runs=500),
    dict(recent_wickets=9, wickets=4),
])
def test_cricket_rejects_inconsistent_states(client, mut):
    st = {**CRICKET, **mut}
    assert client.post("/api/cricket/predict", json={"state": st}).status_code == 422


def test_football_red_card_cap(client):
    st = client.get("/api/sports/football/default-state").json()
    st["home_red"] = 5
    assert client.post("/api/football/predict", json={"state": st}).status_code == 422


def test_rate_limit_error_has_standard_shape():
    """429 must use the same {error: {code, message}} envelope as every other error."""
    import asyncio

    from fastapi import Request
    from limits import parse
    from slowapi.errors import RateLimitExceeded

    from app.main import _rate_limited
    exc = RateLimitExceeded(type("L", (), {"limit": parse("1/minute"), "error_message": None})())
    resp = asyncio.run(_rate_limited(Request({"type": "http", "headers": [], "method": "GET", "path": "/"}), exc))
    import json
    body = json.loads(resp.body)
    assert resp.status_code == 429 and body["error"]["code"] == "rate_limited" and resp.headers["retry-after"]


def test_missing_or_corrupt_model_artifact_is_a_clean_503(monkeypatch, client, tmp_path):
    """Graceful behaviour when artifacts are missing or unreadable; /health must reflect it."""
    from app.config import settings
    from app.ml import predictor
    st = client.get("/api/sports/cricket/default-state").json()
    good = client.post("/api/cricket/predict", json={"state": st})
    assert good.status_code == 200 and client.get("/api/health").json()["status"] == "ok"

    monkeypatch.setattr(settings, "artifact_dir", str(tmp_path))
    predictor.clear_caches()
    try:
        r = client.post("/api/cricket/predict", json={"state": st})
        assert r.status_code == 503 and r.json()["error"]["code"] == "prediction_unavailable"
        h = client.get("/api/health").json()
        assert h["status"] == "degraded" and h["models_loaded"] is False and h["components"]["cricket"] == "unavailable"

        (tmp_path / "cricket_win.joblib").write_bytes(b"corrupt")
        predictor.clear_caches()
        r = client.post("/api/cricket/predict", json={"state": st})
        assert r.status_code == 503 and "could not be read" in r.json()["error"]["detail"]
    finally:
        monkeypatch.undo()
        predictor.clear_caches()
    assert client.post("/api/cricket/predict", json={"state": st}).status_code == 200      # recovers once artifacts are back


def test_empty_player_selection_is_handled(client):
    assert client.get("/api/players?sport=cricket&team=NoSuchTeam").json() == []
    assert client.post("/api/players/compare", json={"a": 0, "b": 1}).status_code in (404, 422)
