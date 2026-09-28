"""Créneaux d’humeur (Europe/Paris) — notifs + saisie in-app."""

from __future__ import annotations

from datetime import datetime, time
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")

# 4 points dans la journée, ~4 h d’écart : assez pour un suivi, pas du spam.
SLOTS: tuple[tuple[str, time, str], ...] = (
    ("matin", time(8, 30), "ce matin"),
    ("midi", time(12, 30), "en ce moment"),
    ("apres-midi", time(16, 30), "cet après-midi"),
    ("soir", time(20, 30), "ce soir"),
)

SLOT_LABELS = {sid: label for sid, _t, label in SLOTS}

# Pas de notif si une note a déjà été posée récemment (même créneau ou pas).
MIN_GAP_MINUTES = 120


def slot_at(dt: datetime) -> str | None:
    """Créneau en cours à `dt`, ou None avant le premier (pas de demande)."""
    local = dt.astimezone(PARIS) if dt.tzinfo else dt.replace(tzinfo=PARIS)
    clock = local.timetz().replace(tzinfo=None)
    current: str | None = None
    for sid, start, _label in SLOTS:
        if clock >= start:
            current = sid
        else:
            break
    return current


def slot_start_today(slot_id: str, day: datetime) -> datetime | None:
    local = day.astimezone(PARIS) if day.tzinfo else day.replace(tzinfo=PARIS)
    for sid, start, _label in SLOTS:
        if sid == slot_id:
            return datetime.combine(local.date(), start, tzinfo=PARIS)
    return None


def due_slots(now: datetime) -> list[str]:
    """Créneaux dont l’heure de début est déjà passée aujourd’hui."""
    current = slot_at(now)
    if current is None:
        return []
    ids = [sid for sid, _t, _l in SLOTS]
    return ids[: ids.index(current) + 1]
