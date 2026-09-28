"""Programme sport et journal des séances (vault)."""

from __future__ import annotations

import json
import re
import unicodedata
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from api import config
from api.deps import dump_json

PARIS = ZoneInfo("Europe/Paris")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")
_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def parse_notify_at(raw: str | None) -> str | None:
    value = (raw or "").strip()
    if not value:
        return None
    if not _TIME_RE.match(value):
        return None
    return value


def sport_notify_at() -> str | None:
    path = config.PROFIL_PATH
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return parse_notify_at(str(data.get("sport_notify_at") or ""))


def set_sport_notify_at(value: str | None) -> str | None:
    path = config.PROFIL_PATH
    if not path.exists():
        raise FileNotFoundError("profil.json introuvable")
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        data = {}
    parsed = parse_notify_at(value)
    if parsed:
        data["sport_notify_at"] = parsed
    else:
        data.pop("sport_notify_at", None)
    dump_json(path, data)
    return parsed


def _slug(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_name.lower()).strip("-")
    return slug or "exo"


def load_program() -> dict[str, Any]:
    path = config.SPORT_PATH
    if not path.exists():
        return {"exercises": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"exercises": []}
    if not isinstance(data, dict):
        return {"exercises": []}
    raw = data.get("exercises")
    if not isinstance(raw, list):
        return {"exercises": []}
    exercises = [_normalize_exercise(item, i) for i, item in enumerate(raw)]
    return {"exercises": [e for e in exercises if e]}


def save_program(exercises: list[dict[str, Any]]) -> dict[str, Any]:
    used: set[str] = set()
    cleaned: list[dict[str, Any]] = []
    for i, item in enumerate(exercises):
        row = _normalize_exercise(item, i)
        if not row:
            continue
        base = row["id"]
        candidate = base
        n = 2
        while candidate in used:
            candidate = f"{base}-{n}"
            n += 1
        row["id"] = candidate
        used.add(candidate)
        cleaned.append(row)
    payload = {"exercises": cleaned}
    config.SUIVI_DIR.mkdir(parents=True, exist_ok=True)
    dump_json(config.SPORT_PATH, payload)
    return payload


def _normalize_exercise(item: Any, index: int) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    name = str(item.get("name") or "").strip()
    if not name:
        return None
    raw_id = str(item.get("id") or "").strip()
    exo_id = raw_id if re.match(r"^[a-z0-9-]{1,40}$", raw_id) else _slug(name)
    try:
        sets = int(item.get("sets") or 1)
    except (TypeError, ValueError):
        sets = 1
    sets = max(1, min(20, sets))
    reps = _opt_int(item.get("reps"), 1, 200)
    seconds = _opt_int(item.get("seconds"), 5, 600)
    if reps is None and seconds is None:
        reps = 10
    note = str(item.get("note") or "").strip()[:200]
    return {
        "id": exo_id or f"exo-{index + 1}",
        "name": name[:80],
        "sets": sets,
        "reps": reps,
        "seconds": seconds,
        "note": note,
    }


def _opt_int(value: Any, lo: int, hi: int) -> int | None:
    if value is None or value == "":
        return None
    try:
        n = int(value)
    except (TypeError, ValueError):
        return None
    if n <= 0:
        return None
    return max(lo, min(hi, n))


def load_log() -> dict[str, Any]:
    path = config.SPORT_LOG_PATH
    if not path.exists():
        return {"sessions": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"sessions": []}
    if not isinstance(data, dict):
        return {"sessions": []}
    raw = data.get("sessions")
    if not isinstance(raw, list):
        return {"sessions": []}
    sessions = [_normalize_session(item) for item in raw]
    out = [s for s in sessions if s]
    out.sort(key=lambda s: s["date"])
    return {"sessions": out}


def session_for(day: str) -> dict[str, Any] | None:
    for session in load_log()["sessions"]:
        if session["date"] == day:
            return session
    return None


def today_complete(now: datetime | None = None) -> bool:
    local = now.astimezone(PARIS) if now and now.tzinfo else datetime.now(PARIS)
    day = local.date().isoformat()
    program = load_program()["exercises"]
    if not program:
        return True
    session = session_for(day)
    if not session:
        return False
    answered = {item["exercise_id"] for item in session["items"]}
    return all(exo["id"] in answered for exo in program)


def upsert_session(day: str, items: list[dict[str, Any]], at: datetime | None = None) -> dict[str, Any]:
    if not _DATE_RE.match(day):
        raise ValueError("Date invalide")
    now = at.astimezone(PARIS) if at and at.tzinfo else datetime.now(PARIS)
    if day > now.date().isoformat():
        raise ValueError("Impossible de noter un jour futur")

    cleaned_items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, dict):
            continue
        exo_id = str(item.get("exercise_id") or "").strip()
        if not exo_id or exo_id in seen:
            continue
        if "done" not in item:
            continue
        seen.add(exo_id)
        cleaned_items.append(
            {
                "exercise_id": exo_id[:40],
                "done": bool(item.get("done")),
            }
        )

    stamp = now.isoformat(timespec="minutes")
    log = load_log()
    sessions = [s for s in log["sessions"] if s["date"] != day]
    session = {"date": day, "at": stamp, "items": cleaned_items}
    sessions.append(session)
    sessions.sort(key=lambda s: s["date"])
    payload = {"sessions": sessions}
    config.SUIVI_DIR.mkdir(parents=True, exist_ok=True)
    dump_json(config.SPORT_LOG_PATH, payload)
    return session


def _normalize_session(item: Any) -> dict[str, Any] | None:
    if not isinstance(item, dict):
        return None
    day = str(item.get("date") or "").strip()
    if not _DATE_RE.match(day):
        return None
    raw_items = item.get("items")
    if not isinstance(raw_items, list):
        return None
    items: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in raw_items:
        if not isinstance(row, dict):
            continue
        exo_id = str(row.get("exercise_id") or "").strip()
        if not exo_id or exo_id in seen or "done" not in row:
            continue
        seen.add(exo_id)
        items.append({"exercise_id": exo_id, "done": bool(row.get("done"))})
    at = str(item.get("at") or "").strip()
    return {"date": day, "at": at, "items": items}
