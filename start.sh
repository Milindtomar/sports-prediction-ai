#!/usr/bin/env bash
# Linux/macOS: ./start.sh  (backend :8000, frontend :5173; Ctrl+C stops both)
set -euo pipefail
cd "$(dirname "$0")"
command -v python3 >/dev/null || { echo "python3 (3.11+) is required"; exit 1; }
command -v npm >/dev/null || { echo "Node.js 20+ (npm) is required"; exit 1; }
if [ ! -d backend/.venv ]; then python3 -m venv backend/.venv; fi
# shellcheck disable=SC1091
source backend/.venv/bin/activate
python -c "import fastapi, sqlmodel, sklearn" 2>/dev/null || pip install -r backend/requirements.txt
[ -d frontend/node_modules ] || (cd frontend && npm install)
[ -f backend/artifacts/metrics.json ] || (cd backend && python -m app.ml.train_all)
[ -f backend/.env ] || cp backend/.env.example backend/.env
(cd backend && uvicorn app.main:app --port 8000) & API=$!
trap 'kill $API 2>/dev/null' EXIT
(cd frontend && npm run dev -- --port 5173)
