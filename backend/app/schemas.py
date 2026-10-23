"""Request schemas (strict validation at the API boundary)."""
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, model_validator


class StateIn(BaseModel):
    """A raw match state; the sport adapter performs the sport-specific validation."""
    model_config = ConfigDict(extra="forbid")
    state: dict[str, Any]
    target_class: Optional[int] = Field(None, ge=0, le=2, description="Which outcome to explain (football: 0=home,1=draw,2=away)")


class EventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(..., max_length=40)
    count: int = Field(1, ge=1, le=6)


class SimulateIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: dict[str, Any]
    events: list[EventIn] = Field(..., min_length=1, max_length=8)
    overrides: dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[int] = None


class SweepIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: dict[str, Any]


class CoachIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    state: dict[str, Any]
    side: Optional[str] = Field(None, pattern="^(home|away|focus)$")


class PlayerPredictIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    opp_strength: Optional[float] = Field(None, ge=-3, le=3)
    venue_par: Optional[int] = Field(None, ge=100, le=220)
    team_strength: Optional[float] = Field(None, ge=-3, le=3)
    home: Optional[int] = Field(None, ge=0, le=1)
    b2b: Optional[int] = Field(None, ge=0, le=1)
    slot: Optional[int] = Field(None, ge=1, le=11)


class CompareIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    a: int
    b: int

    @model_validator(mode="after")
    def _distinct(self):
        if self.a == self.b:
            raise ValueError("choose two different players")
        return self


class HciSessionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    participant: str = Field(..., min_length=1, max_length=60, pattern=r"^[A-Za-z0-9 _.\-]+$",
                             description="Anonymous participant code, e.g. P07. Do not enter a real name.")
    experience: str = Field("", max_length=40)
    condition: Optional[str] = Field(None, pattern="^[AB]$")
    consent: bool = Field(..., description="Participant has read the consent text and agrees to take part.")

    @model_validator(mode="after")
    def _needs_consent(self):
        if not self.consent:
            raise ValueError("consent is required before a session can start")
        return self


class HciResultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task_id: str = Field(..., max_length=8)
    answer: str = Field(..., min_length=1, max_length=60)
    position: Optional[int] = Field(None, ge=1, le=20, description="1-based position of this task in the participant's order")
    time_ms: int = Field(..., ge=0, le=3_600_000)
    confidence: int = Field(..., ge=1, le=7)
    trust: int = Field(..., ge=1, le=7)
    interactions: int = Field(0, ge=0, le=500)


class SusIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    answers: list[int] = Field(..., min_length=10, max_length=10)
    trust_items: Optional[list[int]] = Field(None, min_length=4, max_length=4, description="Study-specific trust items (1-7). NOT a validated scale.")
    feedback: str = Field("", max_length=500)
