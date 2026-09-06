"""Persistance des conversations dans vault/assistant/chats/."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

from fastapi import HTTPException

from api import config


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def ensure_chats_dir() -> Path:
    config.CHATS_DIR.mkdir(parents=True, exist_ok=True)
    return config.CHATS_DIR


def safe_chat_id(chat_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", chat_id)
    if not safe or len(safe) > 80:
        raise HTTPException(status_code=400, detail="ID de conversation invalide")
    return safe


def chat_path(chat_id: str) -> Path:
    return ensure_chats_dir() / f"{safe_chat_id(chat_id)}.json"


def load_chat(chat_id: str) -> dict:
    path = chat_path(chat_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return json.loads(path.read_text(encoding="utf-8"))


def save_chat(data: dict) -> None:
    path = chat_path(data["id"])
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
