"""Édition assistée de fichiers du vault (validation utilisateur)."""

from __future__ import annotations

from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import config
from api.chat_store import load_chat, now_iso, save_chat
from api.deps import push_stream, sse

router = APIRouter(prefix="/api/vault", tags=["vault"])

ALLOWED_DIRS = ("humains", "rapports", "recits", "assistant")
ALLOWED_ROOT_FILES: tuple[str, ...] = ()


class VaultEditRequest(BaseModel):
    path: str
    old_string: str
    new_string: str


class UpdateEditProposalStatusRequest(BaseModel):
    conversation_id: str
    message_id: str
    proposal_index: int
    status: str


@router.post("/apply-edit")
async def apply_vault_edit(body: VaultEditRequest):
    parts = Path(body.path).parts
    is_root_file = len(parts) == 1 and parts[0] in ALLOWED_ROOT_FILES
    is_allowed_dir = bool(parts) and parts[0] in ALLOWED_DIRS
    if len(parts) >= 2 and parts[0] == "assistant" and parts[1] == "chats":
        raise HTTPException(
            status_code=403,
            detail="Les conversations (assistant/chats) ne sont pas éditables ainsi.",
        )
    if not (is_root_file or is_allowed_dir):
        raise HTTPException(
            status_code=403,
            detail=(
                f"Emplacement non autorisé. Répertoires : {', '.join(ALLOWED_DIRS)}."
            ),
        )

    file_path = (config.VAULT_DIR / body.path).resolve()
    try:
        if not str(file_path).startswith(str(config.VAULT_DIR.resolve())):
            raise HTTPException(status_code=403, detail="Accès refusé")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail="Chemin invalide")

    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    if file_path.suffix not in (".md", ".json"):
        raise HTTPException(status_code=403, detail="Seuls .md et .json sont autorisés")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            content = file_path.read_text(encoding="utf-8")
            if body.old_string not in content:
                yield "data: ✗ Texte introuvable dans le fichier\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            if content.count(body.old_string) > 1:
                yield "data: ✗ Texte non unique (trouvé plusieurs fois)\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            updated = content.replace(body.old_string, body.new_string, 1)
            file_path.write_text(updated, encoding="utf-8")
            yield f"data: ✓ Fichier modifié : {body.path}\n\n".encode()
        except Exception as exc:
            yield f"data: ✗ Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/update-edit-status")
async def update_edit_proposal_status(body: UpdateEditProposalStatusRequest):
    if body.status not in ("applied", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Statut invalide")

    chat = load_chat(body.conversation_id)
    msg = next((m for m in chat.get("messages", []) if m.get("id") == body.message_id), None)
    if not msg:
        raise HTTPException(status_code=404, detail="Message introuvable")

    proposals = msg.get("edit_proposals", [])
    if body.proposal_index < 0 or body.proposal_index >= len(proposals):
        raise HTTPException(status_code=404, detail="Proposition introuvable")

    proposals[body.proposal_index]["status"] = body.status
    proposals[body.proposal_index]["updated_at"] = now_iso()
    save_chat(chat)
    return {"ok": True, "status": body.status}
