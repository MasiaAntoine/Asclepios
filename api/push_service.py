"""Web Push : abonnements locaux + envoi VAPID (pywebpush)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from api import config
from api.deps import dump_json

DEAD_STATUS = {404, 410, 403}


def _empty() -> list[dict[str, Any]]:
    return []


def load_subscriptions() -> list[dict[str, Any]]:
    path = config.PUSH_SUBSCRIPTIONS_PATH
    if not path.exists():
        return _empty()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _empty()
    if not isinstance(data, list):
        return _empty()
    out: list[dict[str, Any]] = []
    for item in data:
        if not isinstance(item, dict):
            continue
        endpoint = str(item.get("endpoint") or "").strip()
        keys = item.get("keys") if isinstance(item.get("keys"), dict) else {}
        p256dh = str(keys.get("p256dh") or "").strip()
        auth = str(keys.get("auth") or "").strip()
        if endpoint and p256dh and auth:
            out.append(
                {
                    "endpoint": endpoint,
                    "keys": {"p256dh": p256dh, "auth": auth},
                    "created_at": item.get("created_at") or "",
                }
            )
    return out


def _save(items: list[dict[str, Any]]) -> None:
    config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dump_json(config.PUSH_SUBSCRIPTIONS_PATH, items)


def upsert_subscription(endpoint: str, p256dh: str, auth: str) -> dict[str, Any]:
    items = load_subscriptions()
    now = datetime.now(timezone.utc).isoformat()
    record = {
        "endpoint": endpoint,
        "keys": {"p256dh": p256dh, "auth": auth},
        "created_at": now,
    }
    updated = False
    for i, item in enumerate(items):
        if item.get("endpoint") == endpoint:
            record["created_at"] = item.get("created_at") or now
            items[i] = record
            updated = True
            break
    if not updated:
        items.append(record)
    _save(items)
    return record


def remove_subscription(endpoint: str) -> None:
    items = [i for i in load_subscriptions() if i.get("endpoint") != endpoint]
    _save(items)


def subscription_count() -> int:
    return len(load_subscriptions())


def send_push(payload: dict[str, Any], *, ttl: int = 86400) -> dict[str, int]:
    """Envoie le payload à tous les appareils. Nettoie les abonnements morts."""
    if not config.vapid_is_configured():
        return {"sent": 0, "failed": 0, "removed": 0}

    from pywebpush import WebPushException, webpush

    body = json.dumps(payload, ensure_ascii=False)
    items = load_subscriptions()
    sent = 0
    failed = 0
    dead: list[str] = []

    for item in items:
        try:
            webpush(
                subscription_info={
                    "endpoint": item["endpoint"],
                    "keys": item["keys"],
                },
                data=body,
                vapid_private_key=config.VAPID_PRIVATE_KEY,
                vapid_claims={"sub": config.VAPID_SUBJECT},
                ttl=ttl,
            )
            sent += 1
        except WebPushException as exc:
            status = getattr(getattr(exc, "response", None), "status_code", None)
            if status in DEAD_STATUS:
                dead.append(item["endpoint"])
            else:
                failed += 1
        except Exception:
            failed += 1

    if dead:
        remaining = [i for i in items if i.get("endpoint") not in set(dead)]
        _save(remaining)

    return {"sent": sent, "failed": failed, "removed": len(dead)}
