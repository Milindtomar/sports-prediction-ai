"""SPORTS AI - FastAPI application entry point."""
from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.config import settings
from app.db import init_db
from app.limiter import limiter
from app.ml.predictor import ArtifactMissing
from app.routers import core, hci, matches, players
from app.sports.registry import UnknownSport

log = logging.getLogger("sportsai")


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    if settings.auto_seed:
        from app.seed import seed
        res = seed()
        log.info("seed: %s", res)
    yield


app = FastAPI(title="SPORTS AI API", version="1.0.0", lifespan=lifespan,
              description="Intelligent Sports Analytics & Decision System - cricket, football, basketball.")
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins, allow_credentials=False,
                   allow_methods=["GET", "POST", "OPTIONS"], allow_headers=["Content-Type"])


def _err(status: int, code: str, message: str, detail=None):
    return JSONResponse(status_code=status, content=dict(error=dict(code=code, message=message, detail=detail)))


@app.exception_handler(RateLimitExceeded)
async def _rate_limited(request: Request, exc: RateLimitExceeded):
    resp = _err(429, "rate_limited", "Too many requests. Wait a moment and try again.", str(exc.detail))
    resp.headers["Retry-After"] = "60"
    return resp


@app.exception_handler(UnknownSport)
async def _unknown_sport(request: Request, exc: UnknownSport):
    return _err(404, "unknown_sport", f"Unsupported sport '{exc.args[0]}'. Use cricket, football or basketball.")


@app.exception_handler(ArtifactMissing)
async def _artifact_missing(request: Request, exc: ArtifactMissing):
    return _err(503, "prediction_unavailable", "Prediction models are not available on the server.", str(exc))


@app.exception_handler(ValidationError)
async def _pyd_validation(request: Request, exc: ValidationError):
    return _err(422, "invalid_state", "The match state is invalid.", [dict(loc=list(e["loc"]), msg=e["msg"]) for e in exc.errors(include_url=False, include_context=False)])


@app.exception_handler(RequestValidationError)
async def _req_validation(request: Request, exc: RequestValidationError):
    return _err(422, "invalid_request", "The request body is invalid.", [dict(loc=list(e["loc"]), msg=e["msg"]) for e in exc.errors()])


@app.exception_handler(KeyError)
async def _key_error(request: Request, exc: KeyError):
    return _err(404, "not_found", f"Unknown identifier: {exc.args[0]}")


@app.exception_handler(Exception)
async def _unhandled(request: Request, exc: Exception):
    log.exception("unhandled error on %s", request.url.path)
    return _err(500, "internal_error", "Something went wrong on the server. Please try again.")


@app.middleware("http")
async def _timing(request: Request, call_next):
    t0 = time.perf_counter()
    resp = await call_next(request)
    resp.headers["X-Process-Time-ms"] = f"{(time.perf_counter() - t0) * 1000:.1f}"
    return resp


for r in (core.router, matches.router, players.router, hci.router):
    app.include_router(r)
