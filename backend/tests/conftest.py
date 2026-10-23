import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
_tmp = tempfile.mkdtemp(prefix="sportsai-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["AUTO_SEED"] = "1"
os.environ["HEAVY_RATE_LIMIT"] = "100000/minute"
os.environ["RATE_LIMIT"] = "100000/minute"


def pytest_sessionstart(session):
    """Train quick artifacts into a temp dir if the real artifacts are missing (CI-friendly)."""
    art = BACKEND / "artifacts"
    if (art / "metrics.json").exists() and (art / "cricket_win.joblib").exists():
        os.environ["ARTIFACT_DIR"] = str(art)
    else:
        qdir = Path(_tmp) / "artifacts"
        os.environ["ARTIFACT_DIR"] = str(qdir)
        subprocess.run([sys.executable, "-m", "app.ml.train_all", "--quick"], cwd=BACKEND, check=True,
                       env={**os.environ, "PYTHONPATH": str(BACKEND)})
        # train_all writes to backend/artifacts; move on if it did
        if (art / "metrics.json").exists():
            os.environ["ARTIFACT_DIR"] = str(art)


@pytest.fixture(scope="session")
def client():
    from fastapi.testclient import TestClient

    from app.main import app
    with TestClient(app) as c:
        yield c


CRICKET = dict(innings=2, target=172, runs=118, wickets=4, balls_bowled=90, partnership_runs=32, partnership_balls=22,
               recent_runs=17, recent_wickets=0, recent_boundaries=2)
