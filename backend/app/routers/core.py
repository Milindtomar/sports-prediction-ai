"""Health, sport catalogue, model metrics, prediction / explanation / simulation / coach."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlmodel import Session

from app.config import settings
from app.db import get_session
from app.limiter import limiter
from app.ml.predictor import readiness
from app.models_db import SimulationRun
from app.schemas import CoachIn, SimulateIn, StateIn, SweepIn
from app.services import analysis, simulation
from app.services import coach as coach_svc
from app.sports.registry import ADAPTERS, get_adapter

router = APIRouter(prefix="/api")


@router.get("/health")
def health():
    parts = readiness()
    ok = all(v == "ready" for v in parts.values())
    return dict(status="ok" if ok else "degraded", models_loaded=ok, env=settings.env,
                components={k: ("ready" if v == "ready" else "unavailable") for k, v in parts.items()},
                detail={k: v for k, v in parts.items() if v != "ready"} or None)


@router.get("/sports")
def sports():
    out = []
    for a in ADAPTERS.values():
        try:
            card = analysis.model_card(a.key)
        except Exception:
            card = None
        out.append(dict(key=a.key, name=a.name, tagline=a.tagline, status="Live demo (simulated replay)", analytics=a.analytics,
                        model=card and dict(name=card["name"], accuracy=card["accuracy"], roc_auc=card["roc_auc"])))
    return out


@router.get("/sports/{sport}/meta")
def sport_meta(sport: str):
    return get_adapter(sport).meta_dict()


@router.get("/sports/{sport}/default-state")
def default_state(sport: str):
    return get_adapter(sport).default_state()


@router.get("/models")
def models():
    m = analysis.metrics()
    return dict(meta=m["meta"], sports=m["sports"], players=m["players"])


@router.post("/{sport}/predict")
@limiter.limit(settings.heavy_rate_limit)
def predict(request: Request, sport: str, body: StateIn):
    return analysis.analyze(sport, body.state, explain=True, target_class=body.target_class)


@router.post("/{sport}/simulate")
@limiter.limit(settings.heavy_rate_limit)
def simulate(request: Request, sport: str, body: SimulateIn, session: Session = Depends(get_session)):
    res = simulation.simulate(sport, body.state, [e.model_dump() for e in body.events], body.overrides)
    session.add(SimulationRun(sport=sport, events=res["applied"], before=[o["prob"] for o in res["before"]["outcomes"]],
                              after=[o["prob"] for o in res["after"]["outcomes"]], session_id=body.session_id))
    session.commit()
    return res


@router.post("/{sport}/simulate/sweep")
@limiter.limit(settings.heavy_rate_limit)
def simulate_sweep(request: Request, sport: str, body: SweepIn):
    return simulation.sweep(sport, body.state)


@router.post("/{sport}/coach")
@limiter.limit(settings.heavy_rate_limit)
def coach(request: Request, sport: str, body: CoachIn):
    return coach_svc.coach(sport, body.state, body.side)


@router.get("/simulations/recent")
def recent_simulations(session: Session = Depends(get_session)):
    from sqlmodel import select
    rows = session.exec(select(SimulationRun).order_by(SimulationRun.id.desc()).limit(20)).all()
    return [dict(id=r.id, sport=r.sport, events=r.events, before=r.before, after=r.after, at=r.created_at.isoformat()) for r in rows]
