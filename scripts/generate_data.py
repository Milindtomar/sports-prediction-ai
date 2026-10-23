"""Regenerate the synthetic datasets and write them as CSV to data/synthetic/.

    python scripts/generate_data.py                 # 300-match sample per sport (small files)
    python scripts/generate_data.py --full          # every generated snapshot (large: ~25 MB for cricket)
    python scripts/generate_data.py --matches 800   # change how many matches are simulated (default: training sizes)

Deterministic: the seeds are fixed in backend/app/ml/train_all.py (SEEDS) and recorded in data/synthetic/MANIFEST.json.
Columns: model features + 'label' (the outcome) + 'match_id'. 'label' and 'match_id' are never model inputs.
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.ml import train_all as T  # noqa: E402
from app.synth import basketball as bb, cricket as ck, football as fb  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--full", action="store_true", help="write every snapshot row instead of a sample")
    ap.add_argument("--matches", type=int, default=None, help="matches to simulate per sport (default: training sizes)")
    a = ap.parse_args()
    sim = {
        "cricket": lambda n: ck.season_to_rows(ck.simulate_season(n, T.SEEDS["cricket"])[0]),
        "football": lambda n: fb.season_to_rows(fb.simulate_season(n, T.SEEDS["football"])[0]),
        "basketball": lambda n: bb.season_to_rows(bb.simulate_season(n, T.SEEDS["basketball"])[0]),
    }
    for sport, fn in sim.items():
        n = a.matches or T.SIZES[sport]
        df = T.build_frame(fn(n), sport)
        k = 3 if sport == "football" else 2
        card = T.dataset_card(df, k, {})
        T.export_dataset(df, sport, card, a.full)
        print(f"{sport:11s} {card['rows']:>7,} snapshots / {card['matches']:>5,} matches  class balance {card['class_balance']}  hash {card['data_hash']}")
    print(f"written to {T.DATA_DIR}")


if __name__ == "__main__":
    main()
