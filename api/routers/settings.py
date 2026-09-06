"""Statut app + sync OVH."""

from __future__ import annotations

import json
import os
from datetime import date
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter

from api import config
from api.deps import sse, stream_cmd

router = APIRouter(tags=["settings"])

# Aligné sur scripts/sync.py (fichiers exclus du push OVH).
_SKIP_NAMES = {
    ".DS_Store",
    ".vault_structure.json",
    "__pycache__",
    "agenda-cache.json",
    ".ovhdir",
}

# OVH Object Storage Standard Multi-Zone (Paris 3-AZ), palier < 50 Tio.
# HT / Gio / heure — https://www.ovhcloud.com/fr/public-cloud/prices/
_OVH_EUR_HT_PER_GIB_HOUR = 0.00001917
_OVH_HOURS_PER_MONTH = 730
_OVH_VAT = 0.20
_OVH_STORAGE_CLASS = "Standard Multi-Zone"
_OVH_STORAGE_REGION = "Paris 3-AZ"


def _is_skipped(path: Path) -> bool:
    if path.name in _SKIP_NAMES:
        return True
    return any(part in _SKIP_NAMES or part == "__pycache__" for part in path.parts)


def _estimate_encrypted_size(file_size: int, relative: str) -> int:
    """Taille du blob OVH : marqueur MEDENC2 + jeton Fernet (base64)."""
    payload = 4 + len(relative.encode()) + file_size
    padded = payload + (16 - (payload % 16))
    fernet_raw = 1 + 8 + 16 + padded + 32
    b64 = ((fernet_raw + 2) // 3) * 4
    return 8 + b64


def vault_storage() -> dict:
    """Volume local du vault + estimation du coût OVH mensuel."""
    root = config.VAULT_DIR
    files = 0
    local_bytes = 0
    remote_bytes = 0
    if root.exists():
        for path in root.rglob("*"):
            if not path.is_file() or _is_skipped(path):
                continue
            size = path.stat().st_size
            relative = path.relative_to(root).as_posix()
            files += 1
            local_bytes += size
            remote_bytes += _estimate_encrypted_size(size, relative)

    gib = remote_bytes / (1024 ** 3)
    eur_ht = gib * _OVH_HOURS_PER_MONTH * _OVH_EUR_HT_PER_GIB_HOUR
    return {
        "vault_files": files,
        "vault_bytes": local_bytes,
        "ovh_bytes_estimated": remote_bytes,
        "storage_class": _OVH_STORAGE_CLASS,
        "storage_region": _OVH_STORAGE_REGION,
        "storage_eur_ht_per_gib_month": round(
            _OVH_HOURS_PER_MONTH * _OVH_EUR_HT_PER_GIB_HOUR, 7
        ),
        "storage_eur_ht_per_month": round(eur_ht, 6),
        "storage_eur_ttc_per_month": round(eur_ht * (1 + _OVH_VAT), 6),
    }


@router.get("/api/settings/status")
def settings_status() -> dict:
    state_path = config.ROOT / ".sync_state.json"
    files_tracked = 0
    state_mtime: str | None = None
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8"))
            files = state.get("files", state) if isinstance(state, dict) else {}
            files_tracked = len(files) if isinstance(files, dict) else 0
            state_mtime = date.fromtimestamp(state_path.stat().st_mtime).isoformat()
        except Exception:
            files_tracked = 0

    ovh_ok = all(
        os.getenv(k, "").strip()
        for k in (
            "OVH_ACCESS_KEY",
            "OVH_SECRET_KEY",
            "OVH_BUCKET",
            "OVH_ENDPOINT",
            "OVH_REGION",
            "ENCRYPTION_KEY",
        )
    )
    return {
        "cursor_api_configured": bool(os.getenv("CURSOR_API_KEY", "").strip()),
        "ovh_configured": ovh_ok,
        "sync_files_tracked": files_tracked,
        "sync_state_date": state_mtime,
        "ai_model": config.AI_MODEL,
        "app_version": config.APP_VERSION,
        **vault_storage(),
    }


@router.post("/api/sync/push")
async def sync_push():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in stream_cmd("Push OVH", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/api/sync/pull")
async def sync_pull():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in stream_cmd("Pull OVH", [config.PYTHON, str(config.SCRIPT_SYNC), "pull"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())
