# SPORTS AI

A multi-sport analytics platform for **cricket, football and basketball**: win probability, explainable momentum, player-performance prediction, an Explainable-AI layer, a what-if Simulation Lab that re-runs the real prediction pipeline, an "AI-assisted recommendation" coach, and a built-in HCI study (Interface A vs B).

> **Data disclosure.** Every match, player and statistic in this repository is **synthetic**, produced by reproducible simulators in `backend/app/synth`, and every team/player name is fictional. Accuracy figures therefore describe how well models learn the *simulators*, not how well they would predict real sport. The UI labels all model output as "MODEL PREDICTION" and all replay data as simulated. See `docs/ML_DOCUMENTATION.md` for the plan to move to real open datasets.

## What is implemented

| Area | Status |
|---|---|
| Sport Adapter architecture (cricket / football / basketball) | Done |
| Win probability (+ bootstrap uncertainty band), chronological match-grouped evaluation | Done |
| Momentum 0–100 with factor breakdown | Done |
| Player models (cricket runs / 50+ / wickets / economy, football goals / assists / shots, basketball points / rebounds / assists), walk-forward prediction vs actual | Done |
| XAI: simple + technical explanations (sampled Shapley, additive) | Done |
| What-if simulation (state change → features → model → attribution), full event sweep | Done |
| AI Coach (Monte-Carlo rollouts scored by the model, worded as AI-assisted recommendation) | Done |
| HCI study (consent, 5 tasks, SUS + 4 study-specific trust items, rotation, Welch / Fisher tests, CSV + JSON export, `scripts/analyze_hci.py`) | Done; contains **no participant data** until you collect some |
| Frontend pages: Landing, Sport Selection, Match Center, AI Analytics, Simulation Lab, Player Lab, Model Insights, HCI Study | Done |
| Docs, research paper (md + docx), poster brief/content/prompt, figures, tables | Done (`docs/`, `research/`) |
| Postgres, Docker, Render, Vercel configuration; Windows `.bat/.ps1` launchers | Written, **not run** (no live services or Windows here) |

## Screenshots

Captured from the running app (`docs/screenshots/`): landing, Match Center (desktop and 390 px mobile), Simulation Lab, football Match Center, Model Insights, HCI Study.

## Prerequisites

Python 3.11+, Node 20+ (npm), ~1 GB free disk. pandoc is only needed to rebuild the Word paper.

## Quick start

| OS | Command |
|---|---|
| Windows | `setup.bat` once, then `start.bat` (or the `.ps1` versions) — **unverified: written without access to Windows** |
| Linux / macOS | `./start.sh` (creates a venv, installs, starts both servers) |

Manual start:

```bash
cd backend && python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --port 8000        # models are pre-trained in backend/artifacts; seeds demo DB on first start
cd ../frontend && npm install && npm run dev   # http://localhost:5173
```

Open <http://localhost:5173>; API docs at <http://localhost:8000/docs>. Retrain (≈2 min): `cd backend && python -m app.ml.train_all`.

## Demo flow

Landing → Enter Analytics → Cricket → Match Center (Why?) → Simulation Lab → Model Insights → HCI Study. Full script: `docs/DEMO_SCRIPT.md`.

## Tests and checks

```bash
cd backend  && pip install -r requirements-dev.txt && python -m pytest -q && ruff check .   # 49 tests
cd frontend && npm test && npm run typecheck && npm run build                                # 6 tests
```
Honest status of every requirement: `docs/ACCEPTANCE_CHECKLIST.md`.

## Research outputs

`research/paper.md` / `paper.docx` (built by `python scripts/build_paper.py` from `paper_src.md` and `backend/artifacts/metrics.json`), `hci_protocol.md`, `poster_brief.md`, `poster_content.md`, `poster_generation_prompt.md`, `REFERENCES_NOTES.md`, `figures/`, `tables/`, `poster_assets/`. Regenerate figures with `python scripts/make_figures.py`; data CSVs with `python scripts/generate_data.py`; HCI analysis with `python scripts/analyze_hci.py export.csv`. **The paper contains no human-participant results.**

## Troubleshooting

| Symptom | Fix |
|---|---|
| UI shows "could not reach the API" | Start the backend on :8000; check `curl localhost:8000/api/health` |
| Health says `degraded` / 503 `artifact_missing` | Run `python -m app.ml.train_all` in `backend/` |
| `429` errors while scripting | Raise `RATE_LIMIT` / `HEAVY_RATE_LIMIT` in `backend/.env` |
| CORS error on a deployed frontend | Add its origin to `CORS_ORIGINS` |
| Port in use | Stop the old process or pass another `--port` (and set `VITE_API_URL`) |

## Repository layout

```
backend/app/synth/      reproducible simulators + fictional player generator
backend/app/sports/     SportAdapter base + cricket / football / basketball + feature builders
backend/app/ml/         model zoo, selection, calibration, training CLI, predictor
backend/app/services/   analysis, simulation, coach, matches, players, hci
backend/app/routers/    FastAPI routers
backend/artifacts/      trained models + metrics.json (the source of every number shown in the app)
frontend/src/           React + TS + Tailwind app
docs/                   ARCHITECTURE, ML_DOCUMENTATION, HCI_DOCUMENTATION, API_DOCUMENTATION
research/               paper, HCI protocol, poster files, figures, tables
scripts/                generate_data, train_models, make_figures, build_paper, analyze_hci
data/synthetic/         exported training CSVs + MANIFEST.json
```

## Deployment (untested)

* **Backend → Render**: `render.yaml` + `backend/Dockerfile`. Set `CORS_ORIGINS` to the frontend URL; `DATABASE_URL` is injected from the Render Postgres instance.
* **Frontend → Vercel**: root `frontend/`; edit the API rewrite in `frontend/vercel.json`, or set `VITE_API_URL`.
* Local default is SQLite. Postgres support goes through SQLModel/SQLAlchemy and `psycopg2`, but has not been exercised here.

## Known limitations

See "Limitations" in `docs/ML_DOCUMENTATION.md` and `research/paper.md`. In short: synthetic data only; linear models won selection on all three win-probability tasks (the simulators are close to log-linear in the engineered features); several player count targets have R² near zero; shot/wagon-wheel coordinates are illustrative decoration; no real HCI results exist yet.
