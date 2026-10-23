"""Train every model and write backend/artifacts (models + metrics.json). Thin wrapper over app.ml.train_all.

    python scripts/train_models.py            # full run (~2 minutes)
    python scripts/train_models.py --quick    # small smoke run
    python scripts/train_models.py --sport cricket
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app.ml.train_all import main  # noqa: E402

if __name__ == "__main__":
    main()
