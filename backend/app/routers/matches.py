from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models_db import Match
from app.services import matches as svc

router = APIRouter(prefix="/api")


def _get(session: Session, match_id: int) -> Match:
    m = session.get(Match, match_id)
    if not m:
        raise HTTPException(404, "Match not found")
    return m


@router.get("/matches")
def list_matches(sport: Optional[str] = Query(None, max_length=20), session: Session = Depends(get_session)):
    q = select(Match)
    if sport:
        q = q.where(Match.sport == sport)
    return [svc.match_card(m) for m in session.exec(q.order_by(Match.id)).all()]


@router.get("/matches/{match_id}")
def match_detail(match_id: int, session: Session = Depends(get_session)):
    m = _get(session, match_id)
    return dict(**svc.match_card(m), meta=m.meta, timeline=m.timeline, events=m.events)


@router.get("/matches/{match_id}/series")
def match_series(match_id: int, session: Session = Depends(get_session)):
    return svc.match_series(_get(session, match_id))


@router.get("/matches/{match_id}/steps/{k}")
def match_step(match_id: int, k: int, target_class: Optional[int] = Query(None, ge=0, le=2), session: Session = Depends(get_session)):
    m = _get(session, match_id)
    try:
        return svc.step_analysis(m, k, target_class)
    except IndexError:
        raise HTTPException(404, "Step out of range") from None
