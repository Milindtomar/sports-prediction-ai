"""Relational schema (see ARCHITECTURE.md for the ER diagram)."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Match(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sport: str = Field(index=True)
    slug: str = Field(index=True, unique=True)
    title: str
    home: str                      # cricket: team A / football+basketball: home team
    away: str
    venue: str = ""
    status: str = "Simulated replay"
    meta: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))       # sport-specific setup
    timeline: list[Any] = Field(default_factory=list, sa_column=Column(JSON))        # raw states per step
    events: list[Any] = Field(default_factory=list, sa_column=Column(JSON))          # ball / shot / possession log
    created_at: datetime = Field(default_factory=_now)


class Player(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    sport: str = Field(index=True)
    team: str = Field(index=True)
    name: str
    role: str                      # cricket: bat/bowl/all, football: FWD/MID/DEF, basketball: G/F/C
    attrs: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))      # slot, etc.


class PlayerGame(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    player_id: int = Field(foreign_key="player.id", index=True)
    game_idx: int
    kind: str = "main"             # cricket: "bat" | "bowl"
    stats: dict[str, Any] = Field(default_factory=dict, sa_column=Column(JSON))


class SimulationRun(SQLModel, table=True):
    """Audit log of what-if runs (verifies DB writes; used in the HCI analysis)."""
    id: Optional[int] = Field(default=None, primary_key=True)
    sport: str = Field(index=True)
    created_at: datetime = Field(default_factory=_now)
    events: list[Any] = Field(default_factory=list, sa_column=Column(JSON))
    before: list[Any] = Field(default_factory=list, sa_column=Column(JSON))
    after: list[Any] = Field(default_factory=list, sa_column=Column(JSON))
    session_id: Optional[int] = Field(default=None, index=True)


class HciSession(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    participant: str = Field(index=True)
    condition: str                 # "A" (simple) | "B" (interactive explainable)
    experience: str = ""
    started_at: datetime = Field(default_factory=_now)
    completed: bool = False
    sus_score: Optional[float] = None
    sus_answers: list[Any] = Field(default_factory=list, sa_column=Column(JSON))
    consented: bool = False
    trust_answers: list[Any] = Field(default_factory=list, sa_column=Column(JSON))   # study-specific, not a validated scale
    feedback: str = ""


class HciTaskResult(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="hcisession.id", index=True)
    task_id: str
    answer: str
    correct: bool
    time_ms: int
    confidence: int                # 1-7
    trust: int                     # 1-7
    interactions: int
    position: Optional[int] = None  # order in which this participant saw the task
    created_at: datetime = Field(default_factory=_now)
