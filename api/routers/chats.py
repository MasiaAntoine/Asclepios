"""Chat Asclepios — conversations persistées dans vault/assistant/chats/."""

from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import config
from api.chat_store import chat_path, ensure_chats_dir, load_chat, now_iso, save_chat
from api.conversation_behavior import ConversationBehaviorProfile
from api.deps import slugify, sse, stream_cmd
from api.routers.reports import call_ai

router = APIRouter(tags=["chats"])

_BEHAVIOR_PROFILE = ConversationBehaviorProfile(config.VAULT_DIR)

_MEDICAL_SYSTEM = """Tu es Asclepios, l'assistant IA du dossier médical personnel de l'utilisateur.
Tu as accès au contexte fourni (profil, poids, analyses, traitements, médicaments, médecins, rapports, dossiers personnes/relations, agenda médical)
ET à l'historique COMPLET de cette conversation.
Tu travailles avec le répertoire vault/ comme répertoire de travail : tu PEUX ouvrir les fichiers images (jpg/png) listés dans le contexte.

CADRE MÉDICAL :
- Réponds en français.
- Cette conversation est continue : tiens compte de TOUT l'HISTORIQUE (questions, réponses, précisions).
- Base-toi sur le contexte médical + l'historique. Ne te contredis pas sauf si les données du dossier le corrigent.
- Si une info manque, dis-le clairement plutôt qu'inventer.
- Tu n'es PAS un médecin : pas de diagnostic définitif ni d'ordonnance. Tu aides à comprendre, préparer une consultation, croiser les données.
- Sois discret et respectueux (données très sensibles).
- Pour une synthèse, cite les dates et valeurs concrètes du contexte.

AGENDA MÉDICAL :
- La section « Agenda médical (rendez-vous) » du contexte vient du Google Agenda de l'utilisateur (lecture seule).
- Tu peux donc répondre sur ses prochains rendez-vous, préparer une consultation à venir, ou relier un RDV à un traitement / une analyse.
- Tu ne peux PAS créer, modifier ou supprimer un rendez-vous : si on te le demande, dis-le et renvoie vers Google Agenda.
- Si la section est absente, c'est que l'agenda n'est pas configuré ou pas encore synchronisé : ne suppose aucun rendez-vous.

PHOTOS / APPARENCE :
- Les photos (famille, entourage, animaux, médecins) sont dans vault/humains/photos/.
- Quand c'est pertinent, les images sont ATTACHÉES à ton message (vision multimodale) : tu les VOIS réellement.
- Chaque dossier humains/personnes/*.md a aussi une section « Apparence » utile en complément.
- Si on te demande de décrire un visage et que des images sont jointes : base-toi d'abord sur ce que tu VOIS.
- Ne dis JAMAIS que tu « ne peux pas voir » les photos quand des images sont jointes au message.

ÉDITION DE FICHIERS :
- Tu peux PROPOSER des modifications aux fichiers dans vault/ (humains/personnes, humains/relations, rapports, assistant, etc.).
- Utilise UNIQUEMENT ce format JSON pour proposer une modification :
  ```json:edit
  {
    "path": "humains/personnes/prenom-nom.md",
    "description": "Ajout détail apparence",
    "old_string": "texte exact existant (minimum 50 chars pour unicité)",
    "new_string": "texte modifié"
  }
  ```
- L'utilisateur verra un diff et pourra valider ou refuser.
- N'édite QUE si l'utilisateur te le demande explicitement.
- IMPORTANT : old_string doit être EXACT et assez long pour être unique dans le fichier.

STYLE :
- Le bloc PROFIL COMPORTEMENTAL (au-dessus) décrit TA façon de parler, à appliquer
  systématiquement, tout le temps, à chaque réponse. Ce n'est pas optionnel.
- En cas de conflit entre les règles médicales de ce bloc et le PROFIL COMPORTEMENTAL,
  seule la sécurité médicale et psychologique peut le surclasser, et uniquement pour
  la partie concernée. Le reste du profil reste actif.
"""

_HISTORY_BUDGET = 100_000

_VISION_HINTS = (
    "visage", "photo", "photos", "apparence", "physique", "physiquement",
    "decris", "décris", "decrire", "décrire", "description", "ressemble",
    "look", "voir", "vois", "montre", "image", "portrait", "cheveux", "barbe", "yeux",
)


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def _title_from_message(text: str) -> str:
    clean = re.sub(r"\s+", " ", text.strip())
    if len(clean) <= 48:
        return clean or "Nouvelle conversation"
    return clean[:45].rstrip() + "…"


def _format_history_block(history: list[dict]) -> str:
    turns: list[str] = []
    for turn in history:
        role = turn.get("role")
        content = (turn.get("content") or "").strip()
        if not content or role not in ("user", "assistant"):
            continue
        label = "Utilisateur" if role == "user" else "Asclepios"
        turns.append(f"{label}: {content}")

    if not turns:
        return "(aucun — premier message de la conversation)"

    full = "\n\n".join(turns)
    if len(full) <= _HISTORY_BUDGET:
        return full

    head: list[str] = []
    tail: list[str] = []
    budget_head = _HISTORY_BUDGET // 3
    budget_tail = _HISTORY_BUDGET - budget_head - 80
    used_h = 0
    for t in turns:
        if used_h + len(t) + 2 > budget_head:
            break
        head.append(t)
        used_h += len(t) + 2
    used_t = 0
    for t in reversed(turns):
        if t in head:
            break
        if used_t + len(t) + 2 > budget_tail:
            break
        tail.append(t)
        used_t += len(t) + 2
    tail.reverse()
    omitted = len(turns) - len(head) - len(tail)
    note = f"\n\n[… {omitted} message(s) intermédiaire(s) omis pour la taille …]\n\n"
    return "\n\n".join(head) + note + "\n\n".join(tail)


def _build_chat_prompt(message: str, history: list[dict], context: str) -> str:
    history_block = _format_history_block(history)
    behavior = _BEHAVIOR_PROFILE.build(message)
    profile_section = f"{behavior.profile_block}\n\n" if behavior.profile_block else ""
    return (
        f"{profile_section}"
        f"{_MEDICAL_SYSTEM}\n\n"
        f"{behavior.hint_block}\n\n"
        f"===== CONTEXTE MÉDICAL =====\n{context}\n"
        f"===== FIN CONTEXTE =====\n\n"
        f"===== HISTORIQUE COMPLET DE CETTE CONVERSATION =====\n"
        f"{history_block}\n"
        f"===== FIN HISTORIQUE =====\n\n"
        f"Nouvelle question de l'utilisateur (à traiter en continuité avec l'historique ci-dessus) :\n"
        f"{message.strip()}\n\n"
        "Réponds maintenant en tant qu'Asclepios (sans préfixe « Asclepios: »). "
        f"{behavior.reminder_line}"
    )


def _extract_edit_proposals(text: str) -> tuple[str, list[dict]]:
    proposals: list[dict] = []
    pattern = re.compile(r"```json:edit\s*\n(.*?)\n```", re.DOTALL | re.MULTILINE)

    def replace_match(m: re.Match) -> str:
        try:
            proposal = json.loads(m.group(1))
            if all(k in proposal for k in ("path", "description", "old_string", "new_string")):
                proposals.append(proposal)
                return ""
        except Exception:
            pass
        return m.group(0)

    cleaned = pattern.sub(replace_match, text).strip()
    cleaned = re.sub(r"\n\n\n+", "\n\n", cleaned)
    return cleaned, proposals


def _normalize_for_match(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def _person_photo_catalog() -> list[tuple[list[str], Path]]:
    profil_path = config.PROFIL_PATH
    entries: list[tuple[list[str], Path]] = []
    if not profil_path.exists():
        return entries
    try:
        profil = json.loads(profil_path.read_text(encoding="utf-8"))
    except Exception:
        return entries

    def add_person(aliases: list[str], photo: str | None) -> None:
        if not photo:
            return
        path = config.VAULT_DIR / photo
        if path.is_file():
            entries.append((aliases, path))

    parents = profil.get("parents") or {}
    for role, person in (("pere", parents.get("pere")), ("mere", parents.get("mere"))):
        if not isinstance(person, dict):
            continue
        prenom = (person.get("prenom") or "").strip()
        nom = (person.get("nom") or "").strip()
        aliases = [a for a in (prenom, nom, f"{prenom} {nom}".strip(), role) if a]
        if role == "pere":
            aliases.extend(["papa", "père", "pere"])
        if role == "mere":
            aliases.extend(["maman", "mère", "mere"])
        add_person(aliases, person.get("photo"))

    for s in profil.get("fratrie") or []:
        if not isinstance(s, dict):
            continue
        prenom = (s.get("prenom") or "").strip()
        nom = (s.get("nom") or "").strip()
        aliases = [a for a in (prenom, f"{prenom} {nom}".strip()) if a]
        lien = (s.get("lien") or "").lower()
        if "frère" in lien or "frere" in lien:
            aliases.extend(["frère", "frere", "petit frère", "petit frere"])
        if "sœur" in lien or "soeur" in lien:
            aliases.extend(["sœur", "soeur", "petite sœur", "petite soeur"])
        add_person(aliases, s.get("photo"))

    for e in profil.get("entourage") or []:
        if not isinstance(e, dict):
            continue
        prenom = (e.get("prenom") or "").strip()
        nom = (e.get("nom") or "").strip()
        aliases = [a for a in (prenom, nom, f"{prenom} {nom}".strip()) if a]
        add_person(aliases, e.get("photo"))

    for a in profil.get("animaux") or []:
        if not isinstance(a, dict):
            continue
        nom = (a.get("nom") or "").strip()
        aliases = [x for x in (nom, "chien", "dog", "golden") if x]
        add_person(aliases, a.get("photo"))

    return entries


def _resolve_vision_images(message: str, *, max_images: int = 5) -> list[Path]:
    catalog = _person_photo_catalog()
    if not catalog:
        return []

    msg_norm = _normalize_for_match(message)
    wants_vision = any(h in msg_norm for h in _VISION_HINTS)
    wants_all = any(
        k in msg_norm
        for k in (
            "entourage", "famille", "animaux", "tout le monde",
            "tous", "toutes", "chacun", "chaque personne",
        )
    )

    matched: list[Path] = []
    seen: set[Path] = set()
    for aliases, path in catalog:
        for alias in aliases:
            alias_n = _normalize_for_match(alias)
            if len(alias_n) < 3:
                continue
            if alias_n in msg_norm:
                if path not in seen:
                    matched.append(path)
                    seen.add(path)
                break

    if matched:
        return matched[:max_images]
    if wants_vision and wants_all:
        return [p for _, p in catalog][:max_images]
    if wants_vision:
        return [p for _, p in catalog][:max_images]
    return []


async def _chat_ai(prompt: str, image_paths: list[Path] | None = None) -> str:
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions  # type: ignore
    except ImportError as exc:
        raise RuntimeError("cursor-sdk non installé") from exc

    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise ValueError("CURSOR_API_KEY non défini dans .env")

    message: object = prompt
    paths = [p for p in (image_paths or []) if p.is_file()]

    if paths:
        try:
            from cursor_sdk import SDKImage, UserMessage  # type: ignore

            images: list = []
            for path in paths:
                try:
                    images.append(SDKImage.from_file(str(path)))
                except Exception:
                    import base64

                    raw = path.read_bytes()
                    if len(raw) > 900_000:
                        continue
                    suffix = path.suffix.lower()
                    mime = {
                        ".jpg": "image/jpeg",
                        ".jpeg": "image/jpeg",
                        ".png": "image/png",
                        ".webp": "image/webp",
                        ".gif": "image/gif",
                    }.get(suffix, "image/jpeg")
                    images.append({"data": base64.b64encode(raw).decode("ascii"), "mime_type": mime})
            if images:
                labels = ", ".join(p.name for p in paths)
                message = UserMessage(
                    text=(
                        f"{prompt}\n\n"
                        f"[VISION] {len(images)} image(s) jointe(s) : {labels}. "
                        "Tu VOIS ces photos — décris-les à partir de ce que tu observes."
                    ),
                    images=images,
                )
        except ImportError:
            message = prompt

    result = await asyncio.to_thread(
        Agent.prompt,
        message,
        AgentOptions(
            api_key=api_key,
            model=config.AI_MODEL,
            local=LocalAgentOptions(cwd=str(config.VAULT_DIR)),
        ),
    )
    return (result.result or "").strip()


def _new_chat_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]


def _conversation_as_source(chat: dict) -> str:
    lines = [
        f"Titre de la conversation : {chat.get('title') or 'Sans titre'}",
        f"ID conversation : {chat.get('id')}",
        "",
        "=== Transcript complet ===",
        "",
    ]
    for m in chat.get("messages") or []:
        role = m.get("role")
        content = (m.get("content") or "").strip()
        if not content or role not in ("user", "assistant"):
            continue
        label = "Patient" if role == "user" else "Asclepios"
        when = m.get("created_at") or ""
        prefix = f"[{when}] " if when else ""
        lines.append(f"{prefix}{label} :\n{content}\n")
    return "\n".join(lines)


@router.get("/api/chats")
def list_chats() -> dict:
    ensure_chats_dir()
    items: list[dict] = []
    for path in config.CHATS_DIR.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            continue
        msgs = data.get("messages") or []
        preview = ""
        for m in reversed(msgs):
            if m.get("role") == "user" and (m.get("content") or "").strip():
                preview = (m["content"] or "").strip()[:80]
                break
        items.append({
            "id": data.get("id", path.stem),
            "title": data.get("title") or "Sans titre",
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "message_count": len(msgs),
            "preview": preview,
            "report_id": data.get("report_id"),
        })
    items.sort(key=lambda x: x.get("updated_at") or "", reverse=True)
    return {"conversations": items}


@router.post("/api/chats")
def create_chat() -> dict:
    chat_id = _new_chat_id()
    now = now_iso()
    data = {
        "id": chat_id,
        "title": "Nouvelle conversation",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "report_id": None,
    }
    save_chat(data)
    return data


@router.get("/api/chats/{chat_id}")
def get_chat(chat_id: str) -> dict:
    return load_chat(chat_id)


@router.post("/api/chats/{chat_id}/delete")
async def delete_chat(chat_id: str):
    path = chat_path(chat_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    chat = load_chat(chat_id)
    if chat.get("report_id"):
        raise HTTPException(
            status_code=403,
            detail="Conversation liée à un rapport : suppression impossible",
        )

    path.unlink()

    async def _sync_later() -> None:
        try:
            async for _ in stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
                pass
        except Exception:
            pass

    asyncio.create_task(_sync_later())
    return {"ok": True, "id": chat_id}


@router.post("/api/chats/{chat_id}/generate-report")
async def generate_report_from_chat(chat_id: str):
    chat = load_chat(chat_id)
    msgs = [
        m
        for m in (chat.get("messages") or [])
        if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()
    ]
    if len(msgs) < 1:
        raise HTTPException(status_code=400, detail="Conversation vide")

    async def stream() -> AsyncGenerator[bytes, None]:
        from datetime import date

        existing_id = chat.get("report_id")
        regenerating = bool(existing_id)
        yield (
            "data: "
            + ("Régénération du rapport lié…" if regenerating else "Génération du rapport depuis la conversation…")
            + "\n\n"
        ).encode()

        source = _conversation_as_source(chat)
        try:
            markdown = await call_ai(source)
        except Exception as exc:
            yield f"data: Erreur IA : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        if not markdown.strip():
            yield "data: Erreur : réponse vide.\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        if regenerating and existing_id:
            report_id = re.sub(r"[^a-zA-Z0-9_\-]", "", existing_id)
            filename = f"{report_id}.md"
            filepath = config.RAPPORTS_DIR / filename
        else:
            m = re.search(r"^#\s+(.+)", markdown, re.MULTILINE)
            title = m.group(1).strip() if m else (chat.get("title") or "conversation")
            filename = f"{date.today().strftime('%Y-%m-%d')}-{slugify(title)}.md"
            filepath = config.RAPPORTS_DIR / filename
            if filepath.exists():
                stem = filename[:-3]
                filename = f"{stem}-{uuid.uuid4().hex[:4]}.md"
                filepath = config.RAPPORTS_DIR / filename
            report_id = filename[:-3]

        try:
            filepath.write_text(markdown, encoding="utf-8")
            yield (
                "data: \u2713 Rapport "
                + ("écrasé" if regenerating else "créé")
                + f" : {filename}\n\n"
            ).encode()
        except Exception as exc:
            yield f"data: Erreur écriture : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        chat["report_id"] = report_id
        chat["updated_at"] = now_iso()
        try:
            save_chat(chat)
            yield "data: \u2713 Conversation liée au rapport (suppression désactivée)\n\n".encode()
        except Exception as exc:
            yield f"data: Erreur liaison : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        async for chunk in stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
            yield chunk

        yield f"data: REPORT:{report_id}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/api/chat")
async def chat_with_asclepios(body: ChatRequest):
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message vide")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            if body.conversation_id:
                chat = load_chat(body.conversation_id)
            else:
                now = now_iso()
                chat = {
                    "id": _new_chat_id(),
                    "title": "Nouvelle conversation",
                    "created_at": now,
                    "updated_at": now,
                    "messages": [],
                    "report_id": None,
                }
                save_chat(chat)
        except HTTPException:
            yield "data: Erreur : conversation introuvable\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        except Exception as exc:
            yield f"data: Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        yield f"data: CONVERSATION:{chat['id']}\n\n".encode()
        if chat.get("report_id"):
            yield f"data: REPORT:{chat['report_id']}\n\n".encode()

        history = list(chat.get("messages") or [])
        user_msg = {
            "id": f"u-{uuid.uuid4().hex[:12]}",
            "role": "user",
            "content": body.message.strip(),
            "created_at": now_iso(),
        }
        chat["messages"] = history + [user_msg]
        if chat.get("title") in (None, "", "Nouvelle conversation"):
            chat["title"] = _title_from_message(body.message)
        chat["updated_at"] = now_iso()
        if "report_id" not in chat:
            chat["report_id"] = None
        try:
            save_chat(chat)
            yield "data: Message utilisateur enregistré\n\n".encode()
        except Exception as exc:
            yield f"data: Erreur sauvegarde : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        async for chunk in stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
            yield chunk

        yield "data: Chargement du dossier médical…\n\n".encode()
        try:
            from api.medical_context import build_medical_context

            context = await asyncio.to_thread(build_medical_context, config.VAULT_DIR)
            yield f"data: Contexte prêt ({len(context)} caractères)\n\n".encode()

            vision_images = _resolve_vision_images(body.message)
            if vision_images:
                names = ", ".join(p.name for p in vision_images)
                yield f"data: Vision : {len(vision_images)} photo(s) ouverte(s) — {names}\n\n".encode()

            yield "data: Appel au modèle IA…\n\n".encode()
            prompt = _build_chat_prompt(body.message, history, context)
            raw_answer = await _chat_ai(prompt, vision_images)
        except Exception as exc:
            yield f"data: Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        if not raw_answer:
            yield "data: Erreur : réponse vide.\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        answer, edit_proposals = _extract_edit_proposals(raw_answer)
        for proposal in edit_proposals:
            proposal["status"] = "pending"
            proposal["created_at"] = now_iso()
            proposal_json = json.dumps(proposal, ensure_ascii=False)
            yield f"data: EDIT_PROPOSAL:{proposal_json}\n\n".encode()

        yield b"data: [ANSWER_START]\n\n"
        chunk_size = 80
        for i in range(0, len(answer), chunk_size):
            piece = answer[i : i + chunk_size]
            safe = piece.replace("\n", "\\n")
            yield f"data: {safe}\n\n".encode()
            await asyncio.sleep(0)
        yield b"data: [ANSWER_END]\n\n"

        assistant_msg = {
            "id": f"a-{uuid.uuid4().hex[:12]}",
            "role": "assistant",
            "content": answer,
            "created_at": now_iso(),
        }
        if edit_proposals:
            assistant_msg["edit_proposals"] = edit_proposals
        chat["messages"].append(assistant_msg)
        chat["updated_at"] = now_iso()
        try:
            save_chat(chat)
            yield "data: Réponse enregistrée dans le vault\n\n".encode()
            yield f"data: TITLE:{chat['title']}\n\n".encode()
        except Exception as exc:
            yield f"data: Erreur sauvegarde réponse : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        async for chunk in stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())
