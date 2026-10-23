# API documentation

Base URL `http://localhost:8000`. Interactive docs at `/docs` (Swagger) and `/openapi.json`. `{sport}` ∈ `cricket | football | basketball`.

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Readiness: `status` ok/degraded, `models_loaded`, per-sport `components`, `detail` |
| GET | `/api/sports` | Sport cards with the selected model and its test accuracy / AUC |
| GET | `/api/sports/{sport}/meta` | Events, actions, state fields, feature labels |
| GET | `/api/sports/{sport}/default-state` | A valid example state |
| GET | `/api/models` | Full `metrics.json` (dataset, comparison, calibration, importance) |
| POST | `/api/{sport}/predict` | Probabilities, band, momentum, explanation, insights |
| POST | `/api/{sport}/simulate` | What-if: apply events, re-predict, attribute the change |
| POST | `/api/{sport}/simulate/sweep` | Impact of every event on the focus outcome |
| POST | `/api/{sport}/coach` | Rollout-based AI-assisted recommendation |
| GET | `/api/simulations/recent` | Last 20 simulation runs |
| GET | `/api/matches?sport=` | Demo matches |
| GET | `/api/matches/{id}` / `/series` / `/steps/{k}` | Timeline, per-step probabilities, step analysis |
| GET | `/api/players?sport=&team=` · `/api/players/{id}` | Roster and player detail (history, strengths/weaknesses) |
| POST | `/api/players/{id}/predict` · `/api/players/compare` | Next-game prediction with ranges; comparison |
| GET | `/api/hci/tasks` | Task definitions (ground truth is never sent) and SUS items |
| POST | `/api/hci/sessions` · `/{sid}/results` · `/{sid}/sus` | Run a session. Session creation requires `consent: true` and an anonymous code (`^[A-Za-z0-9 _.\-]+$`). Answers must be one of the offered options. `/sus` takes `answers` (10) plus optional `trust_items` (4 × 1–7) and `feedback` (≤ 500 chars) |
| GET | `/api/hci/results` · `/api/hci/export.csv` · `/api/hci/export.json` | Aggregates, tests, raw export (formula-injection neutralised) |

## Examples

```bash
S=$(curl -s localhost:8000/api/sports/cricket/default-state)

curl -s -X POST localhost:8000/api/cricket/predict \
  -H 'Content-Type: application/json' -d "{\"state\": $S}"
```
Response keys: `sport, state, scoreboard, focus, outcomes, headline, terminal, momentum, explanation, insights, features, model, disclaimer`. `headline` = `{label, prob, lo, hi, cls}`; `momentum` = `{score 0-100, label, side, factors[{label, points, detail}]}`.

```bash
curl -s -X POST localhost:8000/api/cricket/simulate \
  -H 'Content-Type: application/json' \
  -d "{\"state\": $S, \"events\": [{\"id\": \"six\"}]}"
```
Response keys: `applied, before, after, deltas[{label, before, after, delta_pp}], focus_class, attribution{rows[{feature, label, before_text, after_text, contribution_pp}], total_pp}, narrative, pipeline`. The `contribution_pp` values sum to `total_pp`.

## Errors

JSON of the form `{"error": {"code": "...", "message": "...", "detail": ...}}` with status 404 (unknown id/sport), 422 (invalid state or request, with the failing field), 429 (rate limited, with a `Retry-After` header) and 503 `artifact_missing` when a model file is absent or unreadable (`/api/health` then reports `degraded`). Domain validation includes: partnership/recent runs ≤ runs, batting ≠ bowling team, known venue, at most 4 red cards per side, and `players/compare` with two different players of the same sport.

## Configuration

`DATABASE_URL`, `CORS_ORIGINS`, `RATE_LIMIT`, `HEAVY_RATE_LIMIT`, `APP_ENV`, `AUTO_SEED` — see `backend/.env.example`.
