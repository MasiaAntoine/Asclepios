"""Fiches médicaments Markdown."""

from __future__ import annotations

import re
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import config
from api.deps import push_stream, safe_filename, sse

router = APIRouter(prefix="/api/medication", tags=["medications"])


def _parse_med_md(content: str) -> dict:
    result: dict = {}
    m = re.search(r"\|\s*\*\*Posologie actuelle\*\*\s*\|\s*([^\|]+)\|", content)
    if m:
        result["posologie"] = m.group(1).strip()
    m = re.search(r"\|\s*\*\*Arr[êe]t temporaire\*\*\s*\|\s*([^\|]+)\|", content)
    if m:
        result["arret_temporaire"] = m.group(1).strip()
    m = re.search(r"## Notes personnelles\n(.*?)(?=\n##|\Z)", content, re.DOTALL)
    if m:
        raw = re.sub(r"<!--.*?-->", "", m.group(1), flags=re.DOTALL).strip()
        raw = re.sub(r"^-\s*$", "", raw, flags=re.MULTILINE).strip()
        result["notes"] = raw
    return result


def _apply_med_update(
    content: str,
    posologie: str | None,
    arret_temporaire: str | None,
    notes: str | None,
) -> str:
    if posologie is not None:
        content = re.sub(
            r"(\|\s*\*\*Posologie actuelle\*\*\s*\|)\s*[^\|]+(\|)",
            lambda m: f"{m.group(1)} {posologie} {m.group(2)}",
            content,
        )
    if arret_temporaire is not None:
        content = re.sub(
            r"(\|\s*\*\*Arr[êe]t temporaire\*\*\s*\|)\s*[^\|]+(\|)",
            lambda m: f"{m.group(1)} {arret_temporaire} {m.group(2)}",
            content,
        )
    if notes is not None:
        cb = re.search(r"(## Notes personnelles\n)(<!--.*?-->\n\n?)", content, re.DOTALL)
        if cb:
            prefix = cb.group(1) + cb.group(2)
            content = re.sub(
                r"## Notes personnelles\n<!--.*?-->\n\n?.*?(?=\n##|\Z)",
                prefix + notes + "\n",
                content,
                flags=re.DOTALL,
            )
        else:
            content = re.sub(
                r"(## Notes personnelles\n).*?(?=\n##|\Z)",
                r"\g<1>" + notes + "\n",
                content,
                flags=re.DOTALL,
            )
    return content


@router.get("/{fichier}")
async def get_medication(fichier: str) -> dict:
    try:
        safe = safe_filename(fichier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nom invalide")
    path = config.MEDICAMENTS_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return _parse_med_md(path.read_text(encoding="utf-8"))


class MedUpdateRequest(BaseModel):
    fichier: str
    posologie: str | None = None
    arret_temporaire: str | None = None
    notes: str | None = None


@router.post("/update")
async def update_medication(body: MedUpdateRequest):
    try:
        safe = safe_filename(body.fichier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nom invalide")
    path = config.MEDICAMENTS_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            updated = _apply_med_update(
                path.read_text(encoding="utf-8"),
                body.posologie,
                body.arret_temporaire,
                body.notes,
            )
            path.write_text(updated, encoding="utf-8")
            yield "data: \u2713 Fichier sauvegardé\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())
