"""Agenda médical — lecture seule d'un flux iCal (Google Agenda).

Aucune écriture, aucune création d'événement : on lit l'**adresse secrète iCal**
du calendrier « Médical » et on expose les rendez-vous normalisés.

Pourquoi l'adresse secrète plutôt qu'une URL publique : elle fonctionne sur un
calendrier **privé**, donc les rendez-vous médicaux ne sont jamais exposés
publiquement. En contrepartie l'URL est un jeton d'accès : elle reste
exclusivement côté serveur (env `MEDICAL_ICAL_URL`), le frontend passe par
`/api/agenda/*`.
"""

from __future__ import annotations

import json
import os
import re
import threading
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any

import httpx

# ── Configuration ───────────────────────────────────────────────────────────

_ENV_URL = "MEDICAL_ICAL_URL"

# Le flux Google n'est pas temps réel (propagation de quelques minutes) :
# un TTL court évite de le marteler sans rien perdre de frais.
_CACHE_TTL_SECONDS = 600

_HTTP_TIMEOUT = 15.0
_MAX_ICS_BYTES = 8 * 1024 * 1024

# Fenêtre par défaut si l'appelant n'en fournit pas.
_DEFAULT_PAST_DAYS = 60
_DEFAULT_FUTURE_DAYS = 365

# Snapshot disque : permet à l'IA de lire l'agenda sans appel réseau bloquant,
# et sert de repli si Google est injoignable.
_SNAPSHOT_NAME = "agenda-cache.json"


class AgendaError(RuntimeError):
    """Erreur récupérable côté agenda (réseau, parsing, config)."""


# ── État en mémoire ─────────────────────────────────────────────────────────

_lock = threading.Lock()
_cache: dict[str, Any] = {"ics": None, "fetched_at": None}


def ical_url() -> str:
    return os.getenv(_ENV_URL, "").strip()


def is_configured() -> bool:
    return bool(ical_url())


# ── Récupération du flux ────────────────────────────────────────────────────


def _fetch_ics(url: str) -> str:
    try:
        with httpx.Client(timeout=_HTTP_TIMEOUT, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            raw = resp.content[:_MAX_ICS_BYTES]
    except httpx.HTTPStatusError as exc:
        code = exc.response.status_code
        if code in (401, 403, 404):
            raise AgendaError(
                f"Flux iCal refusé (HTTP {code}). L'adresse secrète a peut-être été "
                "régénérée dans Google Agenda."
            ) from exc
        raise AgendaError(f"Flux iCal indisponible (HTTP {code}).") from exc
    except httpx.HTTPError as exc:
        raise AgendaError(f"Impossible de joindre le flux iCal : {exc}") from exc

    text = raw.decode("utf-8", errors="replace")
    if "BEGIN:VCALENDAR" not in text:
        raise AgendaError(
            "La réponse n'est pas un flux iCal valide. Vérifie que l'URL est bien "
            "l'adresse secrète au format iCal (elle finit par « /basic.ics »)."
        )
    return text


def _cached_ics(force: bool = False) -> str:
    url = ical_url()
    if not url:
        raise AgendaError(
            f"Agenda non configuré : ajoute {_ENV_URL} dans le fichier .env "
            "(adresse secrète au format iCal de ton Google Agenda « Médical »)."
        )

    with _lock:
        ics = _cache.get("ics")
        fetched_at = _cache.get("fetched_at")
        fresh = (
            ics
            and isinstance(fetched_at, datetime)
            and (datetime.now(timezone.utc) - fetched_at).total_seconds() < _CACHE_TTL_SECONDS
        )
        if fresh and not force:
            return ics  # type: ignore[return-value]

    fetched = _fetch_ics(url)
    with _lock:
        _cache["ics"] = fetched
        _cache["fetched_at"] = datetime.now(timezone.utc)
    return fetched


# ── Parsing ─────────────────────────────────────────────────────────────────


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _normalize(component: Any, *, recurring: bool) -> dict[str, Any] | None:
    """Convertit un VEVENT icalendar en dict JSON-safe."""
    raw_start = component.get("DTSTART")
    if raw_start is None:
        return None
    start_val = raw_start.dt

    raw_end = component.get("DTEND")
    end_val = raw_end.dt if raw_end is not None else None

    all_day = isinstance(start_val, date) and not isinstance(start_val, datetime)

    if all_day:
        if end_val is None:
            end_val = start_val + timedelta(days=1)
        # DTEND est exclusif en iCal pour les journées entières : on le rend
        # inclusif pour que le frontend n'affiche pas un jour de trop.
        display_end = end_val - timedelta(days=1)
        start_iso = start_val.isoformat()
        end_iso = max(display_end, start_val).isoformat()
    else:
        if end_val is None:
            end_val = start_val + timedelta(hours=1)
        start_iso = start_val.isoformat()
        end_iso = end_val.isoformat()

    def text(key: str) -> str:
        value = component.get(key)
        if value is None:
            return ""
        return str(value).strip()

    return {
        "uid": text("UID") or f"{start_iso}-{text('SUMMARY')}",
        "title": text("SUMMARY") or "(sans titre)",
        "start": start_iso,
        "end": end_iso,
        "all_day": all_day,
        "location": text("LOCATION"),
        "description": text("DESCRIPTION"),
        "status": text("STATUS"),
        "recurring": recurring,
    }


def _parse_with_icalendar(ics: str, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
    from icalendar import Calendar

    calendar = Calendar.from_ical(ics)

    # Expansion des récurrences (kiné hebdo, contrôle mensuel…) si la lib est là.
    try:
        import recurring_ical_events

        # Les UID porteurs d'une RRULE dans le flux source : l'expansion produit
        # des occurrences sans RRULE, on ne pourrait donc plus les reconnaître.
        recurring_uids = {
            str(comp.get("UID", "")).strip()
            for comp in calendar.walk("VEVENT")
            if comp.get("RRULE")
        }
        recurring_uids.discard("")

        occurrences = recurring_ical_events.of(calendar).between(window_start, window_end)
        events = []
        for comp in occurrences:
            uid = str(comp.get("UID", "")).strip()
            item = _normalize(comp, recurring=bool(comp.get("RRULE")) or uid in recurring_uids)
            if item:
                events.append(item)
        return events
    except ImportError:
        pass

    # Repli : VEVENT bruts, sans expansion des récurrences.
    events = []
    for comp in calendar.walk("VEVENT"):
        item = _normalize(comp, recurring=bool(comp.get("RRULE")))
        if item:
            events.append(item)
    return events


# ── Repli sans dépendance : parser iCal minimal ─────────────────────────────

_DT_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})(?:T(\d{2})(\d{2})(\d{2})(Z)?)?$")


def _unfold(ics: str) -> list[str]:
    """Recolle les lignes pliées (RFC 5545 : continuation = espace/tab initial)."""
    lines: list[str] = []
    for raw in ics.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if raw[:1] in (" ", "\t") and lines:
            lines[-1] += raw[1:]
        else:
            lines.append(raw)
    return lines


def _unescape(value: str) -> str:
    return (
        value.replace("\\n", "\n")
        .replace("\\N", "\n")
        .replace("\\,", ",")
        .replace("\\;", ";")
        .replace("\\\\", "\\")
    )


def _parse_dt(value: str) -> date | datetime | None:
    match = _DT_RE.match(value.strip())
    if not match:
        return None
    y, mo, d, hh, mm, ss, zulu = match.groups()
    if hh is None:
        return date(int(y), int(mo), int(d))
    naive = datetime(int(y), int(mo), int(d), int(hh), int(mm), int(ss))
    # Sans TZID exploitable ici, on suppose UTC pour les valeurs en Z et on
    # laisse les autres naïves (le frontend les affiche telles quelles).
    return naive.replace(tzinfo=timezone.utc) if zulu else naive


def _parse_minimal(ics: str) -> list[dict[str, Any]]:
    """Parser de secours si `icalendar` n'est pas installé.

    Gère les VEVENT simples : pas d'expansion des récurrences.
    """
    events: list[dict[str, Any]] = []
    current: dict[str, str] | None = None

    for line in _unfold(ics):
        stripped = line.strip()
        if stripped == "BEGIN:VEVENT":
            current = {}
            continue
        if stripped == "END:VEVENT":
            if current is not None:
                built = _build_minimal_event(current)
                if built:
                    events.append(built)
            current = None
            continue
        if current is None or ":" not in stripped:
            continue

        name_part, _, value = stripped.partition(":")
        key = name_part.split(";", 1)[0].upper()
        if key in ("DTSTART", "DTEND", "SUMMARY", "LOCATION", "DESCRIPTION", "UID", "STATUS", "RRULE"):
            current[key] = value

    return events


def _build_minimal_event(fields: dict[str, str]) -> dict[str, Any] | None:
    start_val = _parse_dt(fields.get("DTSTART", ""))
    if start_val is None:
        return None
    end_val = _parse_dt(fields.get("DTEND", ""))

    all_day = isinstance(start_val, date) and not isinstance(start_val, datetime)
    if all_day:
        end_date = end_val if isinstance(end_val, date) else start_val + timedelta(days=1)
        display_end = end_date - timedelta(days=1)  # DTEND exclusif
        start_iso = start_val.isoformat()
        end_iso = max(display_end, start_val).isoformat()
    else:
        if not isinstance(end_val, datetime):
            end_val = start_val + timedelta(hours=1)
        start_iso = start_val.isoformat()
        end_iso = end_val.isoformat()

    return {
        "uid": _unescape(fields.get("UID", "")) or f"{start_iso}-{fields.get('SUMMARY', '')}",
        "title": _unescape(fields.get("SUMMARY", "")) or "(sans titre)",
        "start": start_iso,
        "end": end_iso,
        "all_day": all_day,
        "location": _unescape(fields.get("LOCATION", "")),
        "description": _unescape(fields.get("DESCRIPTION", "")),
        "status": fields.get("STATUS", "").strip(),
        "recurring": "RRULE" in fields,
    }


def parse_events(ics: str, window_start: datetime, window_end: datetime) -> list[dict[str, Any]]:
    try:
        events = _parse_with_icalendar(ics, window_start, window_end)
    except ImportError:
        events = _parse_minimal(ics)

    events.sort(key=lambda e: (e["start"], e["title"]))
    return events


# ── Snapshot disque (contexte IA + repli hors ligne) ────────────────────────


def snapshot_path(data_dir: Path) -> Path:
    return data_dir / _SNAPSHOT_NAME


def write_snapshot(data_dir: Path, payload: dict[str, Any]) -> None:
    try:
        data_dir.mkdir(parents=True, exist_ok=True)
        snapshot_path(data_dir).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    except OSError:
        pass  # le snapshot est un confort, pas une exigence


def read_snapshot(data_dir: Path) -> dict[str, Any] | None:
    try:
        raw = snapshot_path(data_dir).read_text(encoding="utf-8")
    except OSError:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


# ── API publique du module ──────────────────────────────────────────────────


def _window(start: str | None, end: str | None) -> tuple[datetime, datetime]:
    def parse(value: str | None) -> datetime | None:
        if not value:
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    today = datetime.combine(date.today(), time.min, tzinfo=timezone.utc)
    window_start = parse(start) or today - timedelta(days=_DEFAULT_PAST_DAYS)
    window_end = parse(end) or today + timedelta(days=_DEFAULT_FUTURE_DAYS)
    if window_end <= window_start:
        window_end = window_start + timedelta(days=_DEFAULT_FUTURE_DAYS)
    return window_start, window_end


def get_events(
    data_dir: Path,
    start: str | None = None,
    end: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Retourne les événements de la fenêtre demandée.

    En cas d'échec réseau, retombe sur le dernier snapshot connu plutôt que de
    laisser la page vide.
    """
    window_start, window_end = _window(start, end)

    try:
        ics = _cached_ics(force=force)
    except AgendaError as exc:
        fallback = read_snapshot(data_dir)
        if fallback and fallback.get("events"):
            return {
                **fallback,
                "stale": True,
                "error": str(exc),
            }
        raise

    events = parse_events(ics, window_start, window_end)

    # Filtrage final : `_parse_minimal` et le repli sans expansion ne bornent pas.
    start_key = window_start.date().isoformat()
    end_key = window_end.date().isoformat()
    events = [e for e in events if start_key <= e["start"][:10] <= end_key]

    payload = {
        "events": events,
        "count": len(events),
        "window": {"start": window_start.isoformat(), "end": window_end.isoformat()},
        "fetched_at": (_cache.get("fetched_at") or datetime.now(timezone.utc)).isoformat(),
        "stale": False,
        "error": None,
    }
    write_snapshot(data_dir, payload)
    return payload


def format_for_ai(data_dir: Path, max_past: int = 10, max_future: int = 30) -> str:
    """Résumé texte des rendez-vous pour le contexte de l'assistant.

    Lit le snapshot disque : jamais d'appel réseau bloquant dans la construction
    du contexte médical.
    """
    snapshot = read_snapshot(data_dir)
    if not snapshot:
        return ""
    events = snapshot.get("events")
    if not isinstance(events, list) or not events:
        return ""

    today = date.today().isoformat()
    past = [e for e in events if e.get("start", "")[:10] < today]
    upcoming = [e for e in events if e.get("start", "")[:10] >= today]

    def line(event: dict[str, Any]) -> str:
        start = str(event.get("start", ""))
        day = start[:10]
        if event.get("all_day"):
            when = f"{day} (journée)"
        else:
            when = f"{day} à {start[11:16]}" if len(start) >= 16 else day
        bits = [f"- {when} — {event.get('title') or '(sans titre)'}"]
        if event.get("location"):
            bits.append(f"lieu : {event['location']}")
        if event.get("recurring"):
            bits.append("récurrent")
        return " · ".join(bits)

    blocks: list[str] = []
    if upcoming:
        blocks.append(
            "### Rendez-vous à venir\n\n"
            + "\n".join(line(e) for e in upcoming[:max_future])
        )
    if past:
        blocks.append(
            "### Rendez-vous passés (récents)\n\n"
            + "\n".join(line(e) for e in past[-max_past:])
        )

    fetched = snapshot.get("fetched_at")
    if fetched:
        blocks.append(f"_Agenda synchronisé le {str(fetched)[:16].replace('T', ' ')} (UTC)._")

    return "\n\n".join(blocks)


def status(data_dir: Path) -> dict[str, Any]:
    snapshot = read_snapshot(data_dir)
    return {
        "configured": is_configured(),
        "env_var": _ENV_URL,
        "cache_ttl_seconds": _CACHE_TTL_SECONDS,
        "last_sync": (snapshot or {}).get("fetched_at"),
        "cached_events": len((snapshot or {}).get("events") or []),
    }
