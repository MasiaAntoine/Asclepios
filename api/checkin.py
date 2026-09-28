"""Check-in spontané : notif un peu aléatoire, sans spam."""

from __future__ import annotations

import hashlib
import json
from datetime import date, datetime, time, timedelta, timezone
from zoneinfo import ZoneInfo

from api import config

PARIS = ZoneInfo("Europe/Paris")

# Fenêtre vivante, hors créneaux humeur 8h30 / 12h30 / 16h30 / 20h30.
_WINDOW_START = 10 * 60 + 20  # 10h20
_WINDOW_END = 20 * 60 + 10  # 20h10
_MOOD_MINUTES = (8 * 60 + 30, 12 * 60 + 30, 16 * 60 + 30, 20 * 60 + 30)
_CLASH_MOOD = 50
_CLASH_SPORT = 40
_RECENT_CHAT_MIN = 150

TITLES = (
    "Hey, t’es là ?",
    "Comment ça va, là, maintenant ?",
    "Petit check, sans pression",
    "J’ai une minute pour toi",
    "Dis-moi où t’en es",
    "On prend le pouls ?",
)

BODIES = (
    "Ouvre le chat — je te pose deux-trois questions précises.",
    "On fait le point sur l’instant, pas sur toute ta vie.",
    "Réponds comme ça vient, j’écoute.",
    "Un check-in rapide, pour voir comment t’es vraiment.",
)


def _digest(seed: str) -> bytes:
    return hashlib.sha256(f"asclepios-checkin|{seed}".encode()).digest()


def _sport_minutes() -> int | None:
    try:
        from api.sport import sport_notify_at

        raw = sport_notify_at()
    except Exception:
        return None
    if not raw:
        return None
    hour, minute = (int(p) for p in raw.split(":"))
    return hour * 60 + minute


def _clashes(total_min: int) -> bool:
    for mood in _MOOD_MINUTES:
        if abs(total_min - mood) < _CLASH_MOOD:
            return True
    sport = _sport_minutes()
    if sport is not None and abs(total_min - sport) < _CLASH_SPORT:
        return True
    return False


def planned_at(day: date | None = None) -> datetime | None:
    """Heure du check-in du jour, ou None (jour « silencieux »)."""
    day = day or datetime.now(PARIS).date()
    digest = _digest(day.isoformat())
    # ~1 jour sur 4 : pas de notif, pour que ça reste vivant et pas mécanique.
    if digest[0] < 64:
        return None
    span = _WINDOW_END - _WINDOW_START
    total = _WINDOW_START + int.from_bytes(digest[1:3], "big") % span
    for _ in range(10):
        if not _clashes(total):
            break
        total = _WINDOW_START + (total - _WINDOW_START + 77) % span
    hour, minute = divmod(total, 60)
    return datetime.combine(day, time(hour, minute), tzinfo=PARIS)


def notification_copy(day: date | None = None) -> tuple[str, str]:
    day = day or datetime.now(PARIS).date()
    digest = _digest(f"copy|{day.isoformat()}")
    title = TITLES[digest[0] % len(TITLES)]
    body = BODIES[digest[1] % len(BODIES)]
    return title, body


def _parse_iso(raw: str) -> datetime | None:
    value = (raw or "").strip()
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def recent_user_chat(within_minutes: int = _RECENT_CHAT_MIN) -> bool:
    """True si l’utilisateur a écrit dans le chat récemment (pas la peine de pinger)."""
    if not config.CHATS_DIR.exists():
        return False
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=within_minutes)
    for path in config.CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict):
            continue
        for msg in reversed(data.get("messages") or []):
            if not isinstance(msg, dict) or msg.get("role") != "user":
                continue
            dt = _parse_iso(str(msg.get("created_at") or data.get("updated_at") or ""))
            if dt is not None and dt >= cutoff:
                return True
            break
    return False


def today_checkin_engaged() -> bool:
    """True s’il y a déjà un check-in aujourd’hui avec au moins une réponse."""
    chat = find_today_checkin()
    if not chat:
        return False
    return any(
        isinstance(m, dict) and m.get("role") == "user" and str(m.get("content") or "").strip()
        for m in (chat.get("messages") or [])
    )


def find_today_checkin() -> dict | None:
    if not config.CHATS_DIR.exists():
        return None
    today = datetime.now(PARIS).date().isoformat()
    latest: dict | None = None
    for path in config.CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        if not isinstance(data, dict) or data.get("kind") != "checkin":
            continue
        dt = _parse_iso(str(data.get("created_at") or ""))
        if dt is None:
            continue
        if dt.astimezone(PARIS).date().isoformat() != today:
            continue
        if latest is None or str(data.get("updated_at") or "") > str(latest.get("updated_at") or ""):
            latest = data
    return latest
