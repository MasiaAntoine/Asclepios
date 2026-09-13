"""Sert les fichiers du vault derrière l'auth (remplace le middleware Vite)."""

from __future__ import annotations

import json
import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from api import config

router = APIRouter(tags=["vault-files"])

_MIME_EXTRA = {
    ".md": "text/markdown; charset=utf-8",
    ".csv": "text/csv; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
}


def _safe_vault_path(rel: str) -> Path:
    clean = (rel or "").replace("\\", "/").lstrip("/")
    if not clean or ".." in clean.split("/"):
        raise HTTPException(status_code=400, detail="Chemin invalide")
    root = config.VAULT_DIR.resolve()
    target = (root / clean).resolve()
    if not str(target).startswith(str(root)):
        raise HTTPException(status_code=400, detail="Chemin invalide")
    return target


def _rapports_index() -> bytes:
    directory = config.RAPPORTS_DIR
    if not directory.is_dir():
        return b"[]"
    files = sorted(
        p.name
        for p in directory.iterdir()
        if p.is_file() and p.suffix.lower() == ".md" and p.name.lower() != "readme.md"
    )
    payload = [{"id": name[:-3], "file": name} for name in files]
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


@router.get("/vault/{file_path:path}")
async def get_vault_file(file_path: str):
    # Index virtuel (comme l'ancien plugin Vite)
    if file_path.rstrip("/") == "rapports/index.json":
        return Response(
            content=_rapports_index(),
            media_type="application/json; charset=utf-8",
            headers={"Cache-Control": "no-store"},
        )

    path = _safe_vault_path(file_path)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    ext = path.suffix.lower()
    media = _MIME_EXTRA.get(ext) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    return FileResponse(
        path,
        media_type=media,
        headers={"Cache-Control": "no-store"},
    )
