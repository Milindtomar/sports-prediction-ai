from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import PlainTextResponse
from sqlmodel import Session, select

from app.db import get_session
from app.models_db import HciSession, HciTaskResult
from app.schemas import HciResultIn, HciSessionIn, SusIn
from app.services import hci

router = APIRouter(prefix="/api/hci")


@router.get("/tasks")
def tasks():
    return dict(tasks=hci.public_tasks(), sus_items=hci.SUS_ITEMS, trust_items=hci.TRUST_ITEMS, consent_text=hci.CONSENT_TEXT,
                conditions={"A": "Simple prediction (probability only)", "B": "Interactive explainable prediction (Why? + Simulate)"})


@router.post("/sessions")
def create_session(body: HciSessionIn, session: Session = Depends(get_session)):
    cond = body.condition or hci.next_condition(session)
    s = HciSession(participant=body.participant.strip(), condition=cond, experience=body.experience, consented=True)
    session.add(s)
    session.commit()
    session.refresh(s)
    return dict(id=s.id, condition=s.condition, participant=s.participant)


@router.post("/sessions/{sid}/results")
def add_result(sid: int, body: HciResultIn, session: Session = Depends(get_session)):
    s = session.get(HciSession, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    if body.task_id not in hci.TASK_IDS:
        raise HTTPException(422, "Unknown task")
    if session.exec(select(HciTaskResult).where(HciTaskResult.session_id == sid, HciTaskResult.task_id == body.task_id)).first():
        raise HTTPException(409, "Task already submitted for this session")
    offered, correct = hci.grade(body.task_id, body.answer)
    if not offered:
        raise HTTPException(422, "Answer is not one of the options offered for this task")
    r = HciTaskResult(session_id=sid, correct=correct, **body.model_dump())
    session.add(r)
    session.commit()
    return dict(task_id=body.task_id, correct=correct)


@router.post("/sessions/{sid}/sus")
def add_sus(sid: int, body: SusIn, session: Session = Depends(get_session)):
    s = session.get(HciSession, sid)
    if not s:
        raise HTTPException(404, "Session not found")
    try:
        score = hci.sus_score(body.answers)
    except ValueError as e:
        raise HTTPException(422, str(e)) from None
    s.sus_score, s.sus_answers, s.completed = score, body.answers, True
    s.trust_answers, s.feedback = (body.trust_items or []), body.feedback.strip()
    session.add(s)
    session.commit()
    return dict(sus_score=score)


@router.get("/results")
def results(session: Session = Depends(get_session)):
    return hci.results(session)


@router.get("/export.json")
def export_json(session: Session = Depends(get_session)):
    return hci.export_json(session)


@router.get("/export.csv", response_class=PlainTextResponse)
def export(session: Session = Depends(get_session)):
    return PlainTextResponse(hci.export_csv(session), media_type="text/csv")
