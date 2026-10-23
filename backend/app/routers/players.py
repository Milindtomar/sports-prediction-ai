from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.db import get_session
from app.models_db import Player
from app.schemas import CompareIn, PlayerPredictIn
from app.services import players as svc

router = APIRouter(prefix="/api")


def _p(session: Session, pid: int) -> Player:
    p = session.get(Player, pid)
    if not p:
        raise HTTPException(404, "Player not found")
    return p


@router.get("/players")
def list_players(sport: str = Query(..., max_length=20), team: Optional[str] = Query(None, max_length=60),
                 session: Session = Depends(get_session)):
    q = select(Player).where(Player.sport == sport)
    if team:
        q = q.where(Player.team == team)
    return [svc.player_row(p) for p in session.exec(q.order_by(Player.team, Player.id)).all()]


@router.get("/players/{pid}")
def player_detail(pid: int, session: Session = Depends(get_session)):
    p = _p(session, pid)
    return dict(player=svc.player_row(p), next_game=svc.predict_next(session, p), profile=svc.strengths_weaknesses(session, p),
                history=svc.history(session, p))


@router.post("/players/{pid}/predict")
def player_predict(pid: int, body: PlayerPredictIn, session: Session = Depends(get_session)):
    p = _p(session, pid)
    return svc.predict_next(session, p, {k: v for k, v in body.model_dump().items() if v is not None})


@router.post("/players/compare")
def players_compare(body: CompareIn, session: Session = Depends(get_session)):
    a, b = _p(session, body.a), _p(session, body.b)
    try:
        return svc.compare(session, a, b)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
