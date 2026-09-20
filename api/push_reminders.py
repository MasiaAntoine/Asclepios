"""Rappels agenda par Web Push (1 h avant un rendez-vous)."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from api import config
from api.deps import dump_json

PARIS = ZoneInfo("Europe/Paris")
_POLL_SECONDS = 60
_WINDOW_MIN = 50
_WINDOW_MAX = 70
_KEEP_DAYS = 14


def _parse_start(iso: str) -> datetime | None:
    raw = (iso or "").strip()
    if not raw:
        return None
    if len(raw) == 10:
        return None
    try:
        dt = datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARIS)
    return dt.astimezone(PARIS)


def _load_sent() -> dict[str, str]:
    path = config.PUSH_SENT_PATH
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _save_sent(data: dict[str, str]) -> None:
    cutoff = datetime.now(timezone.utc) - timedelta(days=_KEEP_DAYS)
    cleaned: dict[str, str] = {}
    for key, stamp in data.items():
        try:
            when = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        except ValueError:
            continue
        if when.tzinfo is None:
            when = when.replace(tzinfo=timezone.utc)
        if when >= cutoff:
            cleaned[key] = stamp
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dump_json(config.PUSH_SENT_PATH, cleaned)


def _format_time(dt: datetime) -> str:
    return dt.strftime("%H:%M").replace(":", "h")


def check_agenda_reminders() -> dict[str, int]:
    from api.agenda import AgendaError, get_events, is_configured
    from api.push_service import send_push, subscription_count

    if not config.vapid_is_configured() or not is_configured():
        return {"reminders": 0}
    if subscription_count() == 0:
        return {"reminders": 0}

    now = datetime.now(PARIS)
    window_end = now + timedelta(hours=3)
    try:
        payload = get_events(
            config.VAULT_DIR,
            start=now.date().isoformat(),
            end=window_end.date().isoformat(),
            force=False,
        )
    except AgendaError:
        return {"reminders": 0}

    events = payload.get("events") if isinstance(payload, dict) else None
    if not isinstance(events, list):
        return {"reminders": 0}

    sent_map = _load_sent()
    n = 0
    for event in events:
        if not isinstance(event, dict) or event.get("all_day"):
            continue
        start = _parse_start(str(event.get("start") or ""))
        if start is None:
            continue
        minutes = (start - now).total_seconds() / 60
        if minutes < _WINDOW_MIN or minutes > _WINDOW_MAX:
            continue
        uid = str(event.get("uid") or start.isoformat())
        key = f"{uid}|{start.isoformat()}|1h"
        if key in sent_map:
            continue
        title = str(event.get("title") or "Rendez-vous")
        location = str(event.get("location") or "").strip()
        body = f"{title} à {_format_time(start)}"
        if location:
            body = f"{body} · {location}"
        result = send_push(
            {
                "title": "Rendez-vous dans 1 h",
                "body": body,
                "url": "/agenda",
                "tag": "asclepios-agenda",
            },
            ttl=6 * 3600,
        )
        if result.get("sent", 0) > 0:
            sent_map[key] = datetime.now(timezone.utc).isoformat()
            n += 1

    if n:
        _save_sent(sent_map)
    return {"reminders": n}


def check_daily_mood() -> dict[str, int]:
    from api.push_service import send_push, subscription_count
    from api.routers.suivi import mood_logged_on

    if not config.vapid_is_configured():
        return {"mood": 0}
    if subscription_count() == 0:
        return {"mood": 0}

    now = datetime.now(PARIS)
    if now.hour < 20:
        return {"mood": 0}

    day = now.date().isoformat()
    if mood_logged_on(day):
        return {"mood": 0}

    sent_map = _load_sent()
    key = f"mood|{day}"
    if key in sent_map:
        return {"mood": 0}

    result = send_push(
        {
            "title": "Comment tu te sens aujourd’hui ?",
            "body": "Note ton humeur de 0 (au plus bas) à 10 (super bien).",
            "url": f"/humeur?date={day}",
            "tag": "asclepios-mood",
        },
        ttl=16 * 3600,
    )
    sent_map[key] = datetime.now(timezone.utc).isoformat()
    _save_sent(sent_map)
    return {"mood": 1 if result.get("sent", 0) > 0 else 0}


async def reminder_loop() -> None:
    await asyncio.sleep(8)
    while True:
        try:
            await asyncio.to_thread(check_agenda_reminders)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        try:
            await asyncio.to_thread(check_daily_mood)
        except asyncio.CancelledError:
            raise
        except Exception:
            pass
        await asyncio.sleep(_POLL_SECONDS)
