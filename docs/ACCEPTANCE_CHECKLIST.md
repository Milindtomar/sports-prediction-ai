# Acceptance checklist (honest status)

Legend: **Verified** = run in this build environment (Linux, Python 3.11, Node 20, headless Chromium). **Written, not run** = exists but could not be exercised here. **Not done** = absent.

## Automated checks (last run)

| Check | Command | Result |
|---|---|---|
| Backend tests | `cd backend && python -m pytest -q` | 49 passed |
| Backend lint | `cd backend && ruff check .` | all checks passed (rules E, F, W, B, I; see `ruff.toml`) |
| Frontend tests | `cd frontend && npm test` | 6 passed |
| Frontend types | `cd frontend && npm run typecheck` | clean |
| Frontend build | `cd frontend && npm run build` | built |
| Route smoke test (Playwright, desktop 1366 and mobile 390, 12 routes) | ad-hoc script | no console errors, no horizontal overflow |
| HCI end-to-end (consent → 5 tasks → SUS + trust → results) | ad-hoc script on a temporary DB | works |
| Accessibility (axe-core, WCAG 2 A/AA rules, 10 routes) | ad-hoc script | 0 violations after fixes (automated check only; no manual screen-reader test) |
| API fuzz (~1,000 calls across matches, steps, events, coach, players) | ad-hoc script | 0 server errors |

## Requirements

| Area | Status |
|---|---|
| Cricket, football, basketball adapters, one API | Verified |
| Win probability, calibrated, chronological match-grouped evaluation, no label leakage (tests) | Verified |
| Model Insights: metrics, calibration, importance, **confusion matrix**, version + seed, "not available" fallbacks | Verified |
| Explainability (simple + technical, additive), momentum, simulation, recommendation | Verified |
| Player models with ranges; PREDICTION vs ACTUAL labels | Verified |
| Landing: Enter Analytics CTA, animated visual from real model output | Verified |
| Match Center → Simulation link; persistent SYNTHETIC badge | Verified |
| Graceful missing/corrupt model artifact (503 + degraded health + recovery) | Verified (test) |
| Input validation + edge cases + structured errors incl. 429 | Verified |
| HCI: consent, anonymous code, A/B, rotation, SUS, 4 trust items (not validated), feedback, CSV + JSON export, formula-injection guard | Verified |
| `scripts/analyze_hci.py` refuses statistics on empty/small data | Verified |
| `data/synthetic/` CSVs + MANIFEST (hashes match training) | Verified |
| `research/`: paper.md/.docx, protocol, poster brief/content/prompt, references notes, figures, tables | Done (see caveats) |
| Docs: README, ARCHITECTURE, API, ML, HCI, DEMO_SCRIPT, this checklist | Done |
| Windows `setup.bat/ps1`, `start.bat/ps1` | **Written, not run** (no Windows/PowerShell here) |
| `start.sh` | Written; syntax only, not run end to end |
| PostgreSQL, Docker image, Render, Vercel | **Written, not run** |
| Frontend ESLint | **Not done** (TypeScript strict type check only) |
| Frontend tests for navigation and API-failure states | **Not done** (covered by the Playwright smoke script, which is not part of the repo test suite) |

## Caveats that must not be dropped

1. All data are synthetic; metrics are synthetic benchmark results.
2. **No human-participant results exist.** No ethics approval is claimed.
3. Citations 6, 7, 8, 11, 14 are partially verified (`research/REFERENCES_NOTES.md`); the author block, institution and contact in the paper are placeholders.
4. Linear models win selection because the simulators are near log-linear.
5. Player count targets (wickets, assists, 50+) are barely better than baseline.
