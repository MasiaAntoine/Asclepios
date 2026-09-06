"""Agenda médical (lecture seule)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api import agenda, config

router = APIRouter(prefix="/api/agenda", tags=["agenda"])


@router.get("/status")
def agenda_status() -> dict:
    return agenda.status(config.VAULT_DIR)


@router.get("/events")
def agenda_events(
    start: str | None = Query(default=None, description="Borne basse ISO (incluse)"),
    end: str | None = Query(default=None, description="Borne haute ISO (incluse)"),
    refresh: bool = Query(default=False, description="Ignore le cache et refetch"),
) -> dict:
    try:
        return agenda.get_events(config.VAULT_DIR, start=start, end=end, force=refresh)
    except agenda.AgendaError as exc:
        status_code = 503 if agenda.is_configured() else 501
        raise HTTPException(status_code=status_code, detail=str(exc)) from exc
