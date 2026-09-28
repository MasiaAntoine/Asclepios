"""Rappel de pesée hebdomadaire (vault / profil)."""

from __future__ import annotations

import json
from datetime import date
from typing import Any

from api import config
from api.deps import dump_json
from api.sport import parse_notify_at
WEEKDAYS_FR = (
    "lundi",
    "mardi",
    "mercredi",
    "jeudi",
    "vendredi",
    "samedi",
    "dimanche",
)


def parse_weekday(raw: Any) -> int | None:
    if raw is None or raw == "":
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    if 0 <= value <= 6:
        return value
    return None


def _profil() -> dict[str, Any] | None:
    path = config.PROFIL_PATH
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def poids_notify() -> tuple[int | None, str | None]:
    data = _profil()
    if not data:
        return None, None
    at = parse_notify_at(str(data.get("poids_notify_at") or ""))
    if not at:
        return None, None
    weekday = parse_weekday(data.get("poids_notify_weekday"))
    if weekday is None:
        weekday = 0
    return weekday, at


def set_poids_notify(weekday: int | None, notify_at: str | None) -> tuple[int | None, str | None]:
    path = config.PROFIL_PATH
    if not path.exists():
        raise FileNotFoundError("profil.json introuvable")
    data = _profil() or {}
    parsed_at = parse_notify_at(notify_at)
    parsed_day = parse_weekday(weekday)
    if parsed_at:
        data["poids_notify_at"] = parsed_at
        data["poids_notify_weekday"] = 0 if parsed_day is None else parsed_day
    else:
        data.pop("poids_notify_at", None)
        data.pop("poids_notify_weekday", None)
    dump_json(path, data)
    if parsed_at:
        return (0 if parsed_day is None else parsed_day), parsed_at
    return None, None


def _parse_fr_date(raw: str) -> date | None:
    parts = (raw or "").strip().split("/")
    if len(parts) != 3:
        return None
    try:
        day, month, year = (int(p) for p in parts)
        return date(year, month, day)
    except ValueError:
        return None


def poids_dates() -> list[date]:
    path = config.POIDS_CSV
    if not path.exists():
        return []
    out: list[date] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    for i, line in enumerate(lines):
        if i == 0 or not line.strip():
            continue
        parsed = _parse_fr_date(line.split(",")[0])
        if parsed:
            out.append(parsed)
    return out


def has_poids_in_iso_week(year: int, week: int) -> bool:
    for day in poids_dates():
        cal = day.isocalendar()
        if int(cal.year) == year and int(cal.week) == week:
            return True
    return False


def weekday_label(weekday: int) -> str:
    if 0 <= weekday < len(WEEKDAYS_FR):
        return WEEKDAYS_FR[weekday]
    return "cette semaine"
