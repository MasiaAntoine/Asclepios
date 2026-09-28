"""Programme sport, journal des séances, heure de rappel."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field

from api.routers.suivi import _push_vault

router = APIRouter(prefix="/api", tags=["sport"])


class SportExerciseIn(BaseModel):
    id: str | None = None
    name: str
    sets: int = 3
    reps: int | None = None
    seconds: int | None = None
    note: str = ""


class SportProgramRequest(BaseModel):
    exercises: list[SportExerciseIn] = Field(default_factory=list)


class SportLogItemIn(BaseModel):
    exercise_id: str
    done: bool


class SportLogRequest(BaseModel):
    date: str | None = None
    items: list[SportLogItemIn]


class SportNotifyRequest(BaseModel):
    notify_at: str | None = None


@router.put("/sport/program")
def save_sport_program(body: SportProgramRequest, background_tasks: BackgroundTasks):
    from api.sport import save_program

    payload = save_program([item.model_dump() for item in body.exercises])
    background_tasks.add_task(_push_vault)
    return payload


@router.put("/sport/log")
def save_sport_log(body: SportLogRequest, background_tasks: BackgroundTasks):
    from api.sport import PARIS, upsert_session

    day = (body.date or "").strip() or datetime.now(PARIS).date().isoformat()
    try:
        session = upsert_session(
            day,
            [item.model_dump() for item in body.items],
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    background_tasks.add_task(_push_vault)
    return session


@router.put("/sport/notify-at")
def save_sport_notify(body: SportNotifyRequest, background_tasks: BackgroundTasks):
    from api.sport import parse_notify_at, set_sport_notify_at

    raw = body.notify_at
    if raw and parse_notify_at(raw) is None:
        raise HTTPException(status_code=400, detail="Horaire invalide (HH:MM)")
    try:
        saved = set_sport_notify_at(raw)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    background_tasks.add_task(_push_vault)
    return {"sport_notify_at": saved}
