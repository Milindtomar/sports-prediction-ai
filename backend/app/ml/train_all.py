"""Offline training entry point:  python -m app.ml.train_all [--quick] [--sport cricket]

Generates the reproducible synthetic datasets, trains/compares/calibrates all models and
writes artifacts + metrics.json into backend/artifacts. Never runs inside a web request.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import time
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
import xgboost

from app.ml.common import _clean, train_binary_player, train_regression, train_win_model
from app.sports.features import FEATURE_FUNCS
from app.synth import basketball as bb
from app.synth import cricket as ck
from app.synth import football as fb
from app.synth import players as pl
from app.synth.common import chrono_split

ART = Path(__file__).resolve().parents[2] / "artifacts"
DATA_DIR = Path(__file__).resolve().parents[3] / "data" / "synthetic"   # <repo>/data/synthetic
MODEL_VERSION = "1.1.0"
DATASET_VERSION = "synthetic-v1"
EXPORT_SAMPLE_MATCHES = 300      # CSV samples stay small; pass --export-full for every snapshot
SEEDS = dict(cricket=7, football=11, basketball=13, players=21)
SIZES = dict(cricket=3200, football=3200, basketball=2600, players=420)
QUICK = dict(cricket=500, football=500, basketball=400, players=120)


def build_frame(rows: list[dict], sport: str) -> pd.DataFrame:
    fn, names = FEATURE_FUNCS[sport]
    feats = pd.DataFrame([fn(r) for r in rows])[names]
    feats["label"] = [r["label"] for r in rows]
    feats["match_id"] = [r["match_id"] for r in rows]
    return feats


def dataset_card(df: pd.DataFrame, n_classes: int, extra: dict) -> dict:
    h = hashlib.sha256(pd.util.hash_pandas_object(df, index=False).values.tobytes()).hexdigest()[:16]
    return dict(rows=int(len(df)), matches=int(df["match_id"].nunique()),
                class_balance={int(k): round(float(v), 4) for k, v in df["label"].value_counts(normalize=True).sort_index().items()},
                n_features=int(df.shape[1] - 2), data_hash=h, **extra)


def export_dataset(df: pd.DataFrame, sport: str, card: dict, full: bool) -> None:
    """Write the generated snapshot table (a match-grouped sample unless full=True) + a manifest entry."""
    try:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        keep = df if full else df[df["match_id"] < EXPORT_SAMPLE_MATCHES]
        keep.to_csv(DATA_DIR / f"{sport}_snapshots.csv", index=False)
        mf = DATA_DIR / "MANIFEST.json"
        manifest = json.loads(mf.read_text()) if mf.exists() else {}
        manifest[sport] = dict(file=f"{sport}_snapshots.csv", rows_in_file=int(len(keep)), rows_generated=card["rows"],
                               matches_generated=card["matches"], full_export=bool(full), data_hash=card["data_hash"],
                               seed=SEEDS[sport], dataset_version=DATASET_VERSION, label_column="label",
                               leakage_note="'label' and 'match_id' are NOT model inputs; every other column is a feature")
        mf.write_text(json.dumps(manifest, indent=1))
    except OSError as e:     # read-only deploy images: training still succeeds
        print(f"  (dataset CSV not written: {e})")


def train_sport_win(sport: str, n: int, log, export_full: bool = False) -> tuple[dict, dict]:
    t0 = time.time()
    if sport == "cricket":
        ms, _ = ck.simulate_season(n, SEEDS["cricket"])
        rows = ck.season_to_rows(ms)
        classes, k = ["Bowling side wins", "Batting side wins"], 2
        extra = dict(generator="ball-by-ball T20 simulator", target="current batting side wins the match",
                     snapshot="after every completed over (both innings)")
    elif sport == "football":
        ms, _ = fb.simulate_season(n, SEEDS["football"])
        rows = fb.season_to_rows(ms)
        classes, k = ["Home win", "Draw", "Away win"], 3
        extra = dict(generator="minute-by-minute shot/xG process", target="full-time result (H/D/A)",
                     snapshot="every 5 minutes, minute 0-85")
    else:
        gs, _ = bb.simulate_season(n, SEEDS["basketball"])
        rows = bb.season_to_rows(gs)
        classes, k = ["Away win", "Home win"], 2
        extra = dict(generator="possession-by-possession simulator", target="home team wins (OT resolved)",
                     snapshot="every 2 minutes of game clock")
    df = build_frame(rows, sport)
    names = FEATURE_FUNCS[sport][1]
    split = chrono_split(df["match_id"].values)
    log(f"[{sport}] {len(df)} snapshots / {df['match_id'].nunique()} matches  ({time.time()-t0:.0f}s to generate)")
    bundle, report = train_win_model(df, names, k, split, classes, seed=SEEDS[sport], log=log)
    report["dataset"] = dataset_card(df, k, extra)
    export_dataset(df, sport, report["dataset"], export_full)
    return bundle, report


# --------------------------------------------------------------------------- players
def _split_by_game(df: pd.DataFrame, n_games: int):
    g = df["game"].values
    a, b = int(n_games * 0.7), int(n_games * 0.85)
    return g < a, (g >= a) & (g < b), g >= b


def build_player_frames(n_players: int, seed: int):
    rng = np.random.default_rng(seed)
    used: set[str] = set()
    bat_rows, bowl_rows, fb_rows, bb_rows = [], [], [], []
    N = 36
    for pi in range(n_players):
        p = pl.gen_cricket_player(rng, used, n_games=N)
        bat, bowl = pl.simulate_cricket_career(p, rng)
        for i in range(3, len(bat)):
            g = bat[i]
            f = pl.bat_features(bat[:i], dict(slot=g["slot"], opp_strength=g["opp_strength"], venue_par=g["venue_par"]))
            bat_rows.append(dict(f, game=i, runs=g["runs"], p50=int(g["runs"] >= 50), pid=pi))
        for i in range(3, len(bowl)):
            g = bowl[i]
            f = pl.bowl_features(bowl[:i], dict(opp_strength=g["opp_strength"], venue_par=g["venue_par"]))
            bowl_rows.append(dict(f, game=i, wickets=g["wickets"], economy=g["economy"], pid=pi))
        pf = pl.gen_football_player(rng, used, n_games=N)
        fcar = pl.simulate_football_career(pf, rng)
        for i in range(3, len(fcar)):
            g = fcar[i]
            f = pl.fb_features(fcar[:i], dict(pos=g["pos"], opp_strength=g["opp_strength"],
                                              team_strength=g["team_strength"], home=g["home"]))
            fb_rows.append(dict(f, game=i, goals=g["goals"], assists=g["assists"], shots=g["shots"], pid=pi))
        pb = pl.gen_basketball_player(rng, used, n_games=N)
        bcar = pl.simulate_basketball_career(pb, rng)
        for i in range(3, len(bcar)):
            g = bcar[i]
            f = pl.bb_features(bcar[:i], dict(pos=g["pos"], opp_strength=g["opp_strength"], home=g["home"], b2b=g["b2b"]))
            bb_rows.append(dict(f, game=i, points=g["points"], rebounds=g["rebounds"], assists=g["assists"], pid=pi))
    return [pd.DataFrame(x) for x in (bat_rows, bowl_rows, fb_rows, bb_rows)], N


def train_players(n_players: int, log) -> tuple[dict, dict]:
    (bat, bowl, fbd, bbd), N = build_player_frames(n_players, SEEDS["players"])
    bundles, reports = {}, {}
    specs = [
        ("cricket", "runs", bat, pl.BAT_FEATURES, False), ("cricket", "wickets", bowl, pl.BOWL_FEATURES, True),
        ("cricket", "economy", bowl, pl.BOWL_FEATURES, False), ("football", "goals", fbd, pl.FB_FEATURES, True),
        ("football", "assists", fbd, pl.FB_FEATURES, True), ("football", "shots", fbd, pl.FB_FEATURES, True),
        ("basketball", "points", bbd, pl.BB_FEATURES, False), ("basketball", "rebounds", bbd, pl.BB_FEATURES, False),
        ("basketball", "assists", bbd, pl.BB_FEATURES, False),
    ]
    for sport, target, df, feats, count in specs:
        split = _split_by_game(df, N)
        b, r = train_regression(df, feats, target, split, count, seed=SEEDS["players"], log=log)
        r["dataset"] = dict(rows=int(len(df)), players=int(df["pid"].nunique()), split="chronological by game index 70/15/15")
        bundles[f"{sport}_{target}"], reports[f"{sport}_{target}"] = b, r
    split = _split_by_game(bat, N)
    b, r = train_binary_player(bat, pl.BAT_FEATURES, "p50", split, seed=SEEDS["players"], log=log)
    r["dataset"] = dict(rows=int(len(bat)), positive_rate=round(float(bat["p50"].mean()), 4))
    bundles["cricket_p50"], reports["cricket_p50"] = b, r
    return bundles, reports


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true", help="small datasets for CI / smoke tests")
    ap.add_argument("--export-full", action="store_true", help="write every generated snapshot row to data/synthetic (large)")
    ap.add_argument("--sport", choices=["cricket", "football", "basketball", "players"], default=None)
    a = ap.parse_args()
    sizes = QUICK if a.quick else SIZES
    ART.mkdir(exist_ok=True)
    mpath = ART / "metrics.json"
    metrics = json.loads(mpath.read_text()) if mpath.exists() and a.sport else {"sports": {}, "players": {}}
    t0 = time.time()
    todo = [a.sport] if a.sport else ["cricket", "football", "basketball", "players"]
    for s in todo:
        print(f"== {s}")
        if s == "players":
            bundles, reports = train_players(sizes["players"], print)
            for k, b in bundles.items():
                joblib.dump(b, ART / f"player_{k}.joblib", compress=3)
            metrics["players"] = reports
        else:
            b, r = train_sport_win(s, sizes[s], print, a.export_full)
            joblib.dump(b, ART / f"{s}_win.joblib", compress=3)
            metrics["sports"][s] = r
    metrics["meta"] = dict(seeds=SEEDS, sizes=sizes, quick=a.quick, python=platform.python_version(),
                           sklearn=sklearn.__version__, xgboost=xgboost.__version__, numpy=np.__version__,
                           pandas=pd.__version__, data_source="SYNTHETIC (reproducible simulators in app/synth)",
                           model_version=MODEL_VERSION, dataset_version=DATASET_VERSION,
                           train_seconds=round(time.time() - t0, 1))
    mpath.write_text(json.dumps(_clean(metrics), indent=1))
    print(f"done in {time.time()-t0:.0f}s -> {mpath}")


if __name__ == "__main__":
    main()
