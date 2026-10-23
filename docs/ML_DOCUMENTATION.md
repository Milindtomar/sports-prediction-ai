# ML documentation

All numbers below are read from `backend/artifacts/metrics.json` (full training run: 106.7 s, sklearn 1.9.1, xgboost 3.4.1). They are the source for the Model Insights page and the paper.

## 1. Data

**All data is synthetic.** Real datasets were not reachable from the build environment, so each sport has a reproducible simulator (`backend/app/synth`):

| Sport | Generator | Training table | Label | Snapshots |
|---|---|---|---|---|
| Cricket (T20) | ball-by-ball, venue par, chase aggression | 3,200 matches / 124,221 rows | current batting side wins | after every over, both innings |
| Football | minute-by-minute shot / xG process | 3,200 / 57,600 | full-time H / D / A | minutes 0–85 every 5 |
| Basketball | possession-by-possession | 2,600 / 59,858 | home win (OT resolved) | every 2 game minutes |
| Players | career simulators, 420 players | per-game rows | next-game stats | walk-forward |

Seeds are in `metrics.json → meta.seeds`; each table has a recorded content hash. Demo matches shown in the UI use seeds disjoint from training. Team strength is an Elo rating that is **updated only after a match finishes**, so a match never sees its own result.

### Moving to real data (plan, not done)

| Sport | Candidate open source | Licence note |
|---|---|---|
| Cricket | Cricsheet ball-by-ball (T20) | Open Data Commons Attribution — attribute Cricsheet |
| Football | football-data.co.uk results/odds; StatsBomb Open Data for events/xG | StatsBomb open data has its own attribution terms; check before publishing |
| Basketball | Public box scores / play-by-play where terms allow | Check each source's terms; many forbid redistribution |

Steps: write loaders that output the same snapshot schema as `synth`, keep the chronological match-grouped split, rebuild Elo from past matches only, retrain with `python -m app.ml.train_all`, and re-check calibration. The adapters and API need no changes.

## 2. Leakage prevention

* **Chronological split, grouped by match** (70/15/15 by match date order). No match appears in more than one split. Row counts per split are in `metrics.json`.
* **Elo and form features** use only matches completed before the match's start.
* Features describe the state at the snapshot time only (score, balls/minutes left, recent window, resources). No end-of-match totals.
* Cricket innings 1 and 2 share one model; innings-1 "target" is the venue par + 1, not the realised score.
* Preprocessing (scaling) is fit on the training split only.
* Player features come from games **before** the one being predicted; the Player Lab's history view is walk-forward.
* Calibration is decided on the validation split; the test split is used once for reporting.

## 3. Models and selection

Candidates: Logistic Regression, Random Forest, Hist-Gradient Boosting, XGBoost (regressors: Ridge / Poisson GLM, RF, GB, XGB). **Rule:** lowest validation log-loss; if a simpler model is within 1% of the best, take the simpler one. Isotonic calibration is applied only if it improves validation log-loss (it did not for any sport). Uncertainty band: 12-member match-cluster bootstrap ensemble — it shows model disagreement, not outcome uncertainty.

### Win probability (test split)

| Sport | Chosen | Accuracy | ROC-AUC | Log-loss | Brier | ECE | Majority baseline acc. / prior log-loss |
|---|---|---|---|---|---|---|---|
| Cricket | Logistic Regression | 0.696 | 0.774 | 0.564 | 0.193 | 0.019 | 0.502 / 0.693 |
| Football (H/D/A) | Logistic Regression | 0.633 | 0.802 | 0.790 | 0.465 | 0.018 | 0.425 / 1.079 |
| Basketball | Logistic Regression | 0.787 | 0.882 | 0.416 | 0.139 | 0.021 | 0.562 / 0.691 |

Comparison (test log-loss): cricket LR 0.5645 · RF 0.5574 · GB 0.5561 · XGB 0.5531; football LR 0.790 · RF 0.788 · GB 0.827 · XGB 0.800; basketball LR 0.416 · RF 0.420 · GB 0.427 · XGB 0.423. XGBoost is slightly better on cricket test, but the validation gap was < 1%, so the rule picked the simpler model. Football AUC is one-vs-rest macro.

**Honest reading:** the simulators are close to log-linear in the engineered features, so linear models are expected to be competitive. These results do not show that LR beats boosting on real sport.

Largest permutation importances: cricket `runs_required` (0.96), `resources`, `balls_remaining`; football and basketball `lead_security` (1.22 / 0.90) then `elo_diff`.

### Player models (test split)

| Target | Chosen | MAE | R² | Mean-predictor R² |
|---|---|---|---|---|
| Cricket runs | Ridge | 16.4 | 0.146 | 0.000 |
| Cricket wickets | Poisson GLM | 0.83 | 0.034 | −0.001 |
| Cricket economy | Ridge | 0.745 | 0.452 | 0.000 |
| Cricket 50+ (binary) | Logistic | acc 0.906 (majority 0.905), AUC 0.779 | – | – |
| Football goals | Poisson GLM | 0.230 | 0.116 | 0.000 |
| Football assists | Poisson GLM | 0.174 | 0.006 | −0.003 |
| Football shots | Poisson GLM | 1.05 | 0.290 | 0.000 |
| Basketball points / rebounds / assists | RF / Ridge / Ridge | 3.68 / 1.82 / 1.43 | 0.597 / 0.468 / 0.417 | 0.000 |

Single-game counts are mostly noise, so R² is low for wickets, assists, goals and 50+ (which has near-zero recall at a 0.5 threshold). The UI shows an empirical 10th–90th percentile range of test residuals next to each point prediction and labels it **MODEL PREDICTION** versus **ACTUAL RESULT**.

## 4. Explainability

* **Shapley values** by permutation sampling (16 permutations × 6 background rows, seeded → deterministic), computed on the **probability scale**, so contributions are additive: base probability + Σ contributions = prediction.
* **Simple view** converts the top contributions to plain sentences ("+4.1 pp — required rate is below the current rate"); **technical view** shows feature values, base value and contributions.
* **Change attribution** (`attribute_change`) attributes a before→after probability change to the features the event changed.
* Momentum is *not* a learned model: `50 + 50·tanh(Σ wᵢ zᵢ)` of standardised, interpretable factors; the factor points are the proportional split of (M − 50). Weights are hand-set and documented in the adapters.

## 5. Calibration

Reliability tables (10 bins) are stored per model and plotted in Model Insights. Test ECE is 0.018–0.021 for all three win models. Isotonic calibration was tested and rejected (validation log-loss worsened or tied).

## 6. Limitations

1. Synthetic data only; metrics say nothing about real-world accuracy.
2. Linear models winning is a property of the simulators.
3. Football assist residual interval is asymmetric and sits below zero (zero-inflated counts); the service clips lower bounds at 0.
4. The bootstrap band reflects model-training variance only.
5. Coach recommendations come from rollouts of the same simplified simulators, so they are only as realistic as those simulators.
6. Wagon-wheel angles, pitch-map lengths, shot positions and shot-chart coordinates are illustrative decoration generated from each outcome; no model predicts them.
7. Momentum weights are hand-set, not fitted.

## 7. Versions, data files and confusion matrices

* `MODEL_VERSION = 1.1.0`, `DATASET_VERSION = synthetic-v1`, both recorded in `metrics.json → meta` and shown on the Model Insights page together with the seeds.
* `metrics.json` includes a test-split **confusion matrix** per sport (binary and 3-class). Model Insights renders it, or "Not available" with the reason when an older `metrics.json` lacks it.
* Training tables are exported to `data/synthetic/*.csv` with `MANIFEST.json` (row counts, seeds, content hashes that match `metrics.json`). By default a 300-match sample is written; `python scripts/generate_data.py --full` writes everything.
* Figures and tables for the paper come from `python scripts/make_figures.py` (reads only `metrics.json`).

## 8. Reproduce

```bash
cd backend
python -m app.ml.train_all            # full run; `--export-full` also writes the complete CSVs (add --quick for a smoke run, --sport cricket for one sport)
python -m pytest -q
```
A retrain regenerates the generators' data from the same seeds; small numeric differences versus the table above are possible across library versions.
