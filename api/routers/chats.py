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
from api.chat_jobs import (
    begin_job,
    emit,
    finish_job,
    get_job,
    notify_chat_ready,
    stream_job,
)
from api.chat_store import chat_path, ensure_chats_dir, load_chat, now_iso, save_chat
from api.conversation_behavior import ConversationBehaviorProfile
from api.deps import slugify, sse, stream_cmd
from api.routers.reports import call_ai

router = APIRouter(tags=["chats"])

_BEHAVIOR_PROFILE = ConversationBehaviorProfile(config.VAULT_DIR)

_MEDICAL_SYSTEM = """Tu es Asclepios, l'assistant IA du dossier médical personnel de l'utilisateur.
Tu as accès au contexte fourni (profil, poids, humeur 0–10 horodatée, programme sport et séances, émotions associées aux rapports, analyses, traitements, médicaments, médecins, rapports, dossiers personnes/relations, agenda médical)
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

_CHECKIN_SYSTEM = """
CHECK-IN DANS LE MOMENT :
- Cette conversation est un check-in spontané, pas une revue de dossier.
- Objectif : évaluer précisément l'état actuel (corps, énergie, humeur, rumination, ce qui se passe autour).
- Pose des questions concrètes, ancrées dans l'instant — pas « comment s'est passée ta semaine ».
- 1 à 3 questions max par message. Pas de liste à puces d'interrogatoire.
- Appuie-toi sur le contexte (humeur récente, sport, traitements, heure) pour personnaliser, sans le réciter.
- Ton : vivant, direct, allié qui débarque. Tu tutoies.
- Pas de diagnostic, pas de leçon, pas de « je suis une notification ».
- Quand tu as assez d'éléments : un court miroir de ce que tu perçois, puis une question suivante.
- Si l'utilisateur élude, recentre doucement sur le ressenti présent.
"""

_HISTORY_BUDGET = 100_000

_VISION_HINTS = (
    "visage", "photo", "photos", "apparence", "physique", "physiquement",
    "decris", "décris", "decrire", "décrire", "description", "ressemble",
    "look", "voir", "vois", "montre", "image", "portrait", "cheveux", "barbe", "yeux",
)


class ChatRequest(BaseModel):
    message: str = ""
    conversation_id: str | None = None
    checkin: bool = False


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


def _build_chat_prompt(
    message: str,
    history: list[dict],
    context: str,
    *,
    kind: str | None = None,
    opening: bool = False,
) -> str:
    history_block = _format_history_block(history)
    behavior = _BEHAVIOR_PROFILE.build(message or "check-in")
    profile_section = f"{behavior.profile_block}\n\n" if behavior.profile_block else ""
    checkin_block = f"{_CHECKIN_SYSTEM}\n" if kind == "checkin" or opening else ""
    if opening:
        user_part = (
            "L'utilisateur vient d'ouvrir le chat depuis une notification. "
            "Il n'a encore rien écrit.\n\n"
            "Ouvre TOI-MÊME le check-in : 2 à 4 phrases maximum, puis 2 questions "
            "précises sur l'instant (corps, clarté mentale, ce qu'il était en train "
            "de faire, tension, énergie). Adapte à l'heure et au contexte récent. "
            "Ne mentionne pas la notification. Ne commence pas par un résumé médical."
        )
    else:
        user_part = (
            "Nouvelle question de l'utilisateur (à traiter en continuité avec l'historique ci-dessus) :\n"
            f"{message.strip()}\n\n"
            "Réponds maintenant en tant qu'Asclepios (sans préfixe « Asclepios: »). "
            f"{behavior.reminder_line}"
        )
    return (
        f"{profile_section}"
        f"{_MEDICAL_SYSTEM}\n\n"
        f"{checkin_block}"
        f"{behavior.hint_block}\n\n"
        f"===== CONTEXTE MÉDICAL =====\n{context}\n"
        f"===== FIN CONTEXTE =====\n\n"
        f"===== HISTORIQUE COMPLET DE CETTE CONVERSATION =====\n"
        f"{history_block}\n"
        f"===== FIN HISTORIQUE =====\n\n"
        f"{user_part}"
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


def get_or_create_today_checkin() -> dict:
    from api.checkin import find_today_checkin

    existing = find_today_checkin()
    if existing:
        return existing
    now = now_iso()
    data = {
        "id": _new_chat_id(),
        "title": "Comment ça va ?",
        "kind": "checkin",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "report_id": None,
    }
    save_chat(data)
    return data


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
        if m.get("status") == "generating":
            continue
        label = "Patient" if role == "user" else "Asclepios"
        when = m.get("created_at") or ""
        prefix = f"[{when}] " if when else ""
        lines.append(f"{prefix}{label} :\n{content}\n")
    return "\n".join(lines)


def _set_pending(chat: dict, kind: str, assistant_id: str | None = None) -> None:
    pending: dict = {"kind": kind, "started_at": now_iso()}
    if assistant_id:
        pending["assistant_id"] = assistant_id
    chat["pending"] = pending


def _clear_pending(chat: dict) -> None:
    chat.pop("pending", None)


def _history_for_prompt(messages: list, *, skip_ids: set[str] | None = None) -> list[dict]:
    skip = skip_ids or set()
    out: list[dict] = []
    for turn in messages:
        if turn.get("id") in skip:
            continue
        if turn.get("status") == "generating":
            continue
        out.append(turn)
    return out


async def _push_vault_quiet() -> None:
    try:
        async for _ in stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
            pass
    except Exception:
        pass


async def _run_reply_job(
    job,
    *,
    chat_id: str,
    message: str,
    opening: bool,
    kind: str | None,
    assistant_id: str,
) -> None:
    try:
        chat = load_chat(chat_id)
        await emit(job, f"CONVERSATION:{chat_id}")
        if chat.get("report_id"):
            await emit(job, f"REPORT:{chat['report_id']}")
        await emit(job, f"ASSISTANT:{assistant_id}")
        await emit(job, "Chargement du dossier médical…")
        from api.medical_context import build_medical_context

        context = await asyncio.to_thread(build_medical_context, config.VAULT_DIR)
        await emit(job, f"Contexte prêt ({len(context)} caractères)")

        vision_images = _resolve_vision_images(message or "")
        if vision_images:
            names = ", ".join(p.name for p in vision_images)
            await emit(job, f"Vision : {len(vision_images)} photo(s) ouverte(s) — {names}")

        await emit(job, "Appel au modèle IA…")
        history = _history_for_prompt(
            list(chat.get("messages") or []),
            skip_ids={assistant_id},
        )
        if not opening:
            user_ids = [
                m.get("id")
                for m in reversed(history)
                if m.get("role") == "user"
            ]
            if user_ids:
                history = [m for m in history if m.get("id") != user_ids[0]]

        prompt = _build_chat_prompt(
            message,
            history,
            context,
            kind=kind,
            opening=opening,
        )
        raw_answer = await _chat_ai(prompt, vision_images)
        if not raw_answer:
            raise RuntimeError("réponse vide")

        answer, edit_proposals = _extract_edit_proposals(raw_answer)
        for proposal in edit_proposals:
            proposal["status"] = "pending"
            proposal["created_at"] = now_iso()
            await emit(job, "EDIT_PROPOSAL:" + json.dumps(proposal, ensure_ascii=False))

        await emit(job, "[ANSWER_START]")
        for i in range(0, len(answer), 80):
            piece = answer[i : i + 80].replace("\n", "\\n")
            await emit(job, piece)
            await asyncio.sleep(0)
        await emit(job, "[ANSWER_END]")

        chat = load_chat(chat_id)
        found = False
        for msg in chat.get("messages") or []:
            if msg.get("id") == assistant_id:
                msg["content"] = answer
                msg["created_at"] = now_iso()
                msg.pop("status", None)
                if edit_proposals:
                    msg["edit_proposals"] = edit_proposals
                found = True
                break
        if not found:
            assistant_msg = {
                "id": assistant_id,
                "role": "assistant",
                "content": answer,
                "created_at": now_iso(),
            }
            if edit_proposals:
                assistant_msg["edit_proposals"] = edit_proposals
            chat.setdefault("messages", []).append(assistant_msg)
        _clear_pending(chat)
        chat["updated_at"] = now_iso()
        save_chat(chat)
        await emit(job, "Réponse enregistrée dans le vault")
        await emit(job, f"TITLE:{chat.get('title') or 'Conversation'}")
        asyncio.create_task(_push_vault_quiet())
        await emit(job, "[DONE]")
        notify_chat_ready(
            chat_id,
            title="Asclepios a répondu",
            body=answer,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        try:
            await emit(job, f"Erreur : {exc}")
            await emit(job, "[ERROR]")
            chat = load_chat(chat_id)
            for msg in chat.get("messages") or []:
                if msg.get("id") == assistant_id:
                    msg["content"] = f"Désolé — {exc}"
                    msg["status"] = "error"
                    msg["created_at"] = now_iso()
                    break
            _clear_pending(chat)
            chat["updated_at"] = now_iso()
            save_chat(chat)
        except Exception:
            pass
    finally:
        await finish_job(job)


async def _run_report_job(job, *, chat_id: str) -> None:
    from datetime import date

    try:
        chat = load_chat(chat_id)
        existing_id = chat.get("report_id")
        regenerating = bool(existing_id)
        await emit(
            job,
            "Régénération du rapport lié…" if regenerating else "Génération du rapport depuis la conversation…",
        )
        source = _conversation_as_source(chat)
        markdown = await call_ai(source)
        if not markdown.strip():
            raise RuntimeError("réponse vide")

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

        filepath.write_text(markdown, encoding="utf-8")
        from api.routers.reports import save_emotions_if_empty

        save_emotions_if_empty(report_id, markdown)
        await emit(
            job,
            "\u2713 Rapport " + ("écrasé" if regenerating else "créé") + f" : {filename}",
        )

        chat = load_chat(chat_id)
        chat["report_id"] = report_id
        chat["updated_at"] = now_iso()
        _clear_pending(chat)
        save_chat(chat)
        await emit(job, "\u2713 Conversation liée au rapport (suppression désactivée)")
        asyncio.create_task(_push_vault_quiet())
        await emit(job, f"REPORT:{report_id}")
        await emit(job, "[DONE]")
        notify_chat_ready(
            chat_id,
            title="Ton rapport est prêt",
            body=chat.get("title") or filename,
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        try:
            await emit(job, f"Erreur IA : {exc}")
            await emit(job, "[ERROR]")
            chat = load_chat(chat_id)
            _clear_pending(chat)
            save_chat(chat)
        except Exception:
            pass
    finally:
        await finish_job(job)


def _resume_or_restart_reply(chat: dict):
    chat_id = chat["id"]
    live = get_job(chat_id, "reply")
    if live and not live.done:
        return live
    pending = chat.get("pending") if isinstance(chat.get("pending"), dict) else None
    if not pending or pending.get("kind") != "reply":
        return None
    assistant_id = str(pending.get("assistant_id") or "")
    asst = next(
        (m for m in (chat.get("messages") or []) if m.get("id") == assistant_id),
        None,
    )
    if asst and (asst.get("content") or "").strip() and asst.get("status") != "generating":
        _clear_pending(chat)
        save_chat(chat)
        return None
    if not assistant_id:
        assistant_id = f"a-{uuid.uuid4().hex[:12]}"
    last_user = next(
        (
            m
            for m in reversed(chat.get("messages") or [])
            if m.get("role") == "user"
        ),
        None,
    )
    opening = chat.get("kind") == "checkin" and not last_user
    job = begin_job(chat_id, "reply", assistant_id=assistant_id)
    asyncio.create_task(
        _run_reply_job(
            job,
            chat_id=chat_id,
            message=str((last_user or {}).get("content") or ""),
            opening=opening,
            kind=str(chat.get("kind") or "") or None,
            assistant_id=assistant_id,
        )
    )
    return job


def _resume_or_restart_report(chat: dict):
    chat_id = chat["id"]
    live = get_job(chat_id, "report")
    if live and not live.done:
        return live
    pending = chat.get("pending") if isinstance(chat.get("pending"), dict) else None
    if not pending or pending.get("kind") != "report":
        return None
    if chat.get("report_id") and pending.get("started_at"):
        # If a report already exists and job died after write, just clear.
        pass
    job = begin_job(chat_id, "report")
    asyncio.create_task(_run_report_job(job, chat_id=chat_id))
    return job


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
        pending = data.get("pending") if isinstance(data.get("pending"), dict) else None
        items.append({
            "id": data.get("id", path.stem),
            "title": data.get("title") or "Sans titre",
            "created_at": data.get("created_at"),
            "updated_at": data.get("updated_at"),
            "message_count": len(msgs),
            "preview": preview,
            "report_id": data.get("report_id"),
            "kind": data.get("kind"),
            "pending": (pending or {}).get("kind"),
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


@router.post("/api/chats/checkin")
def get_or_create_checkin() -> dict:
    return get_or_create_today_checkin()


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
        if m.get("role") in ("user", "assistant")
        and (m.get("content") or "").strip()
        and m.get("status") != "generating"
    ]
    if len(msgs) < 1:
        raise HTTPException(status_code=400, detail="Conversation vide")

    live = get_job(chat_id, "report")
    if live and not live.done:
        return sse(stream_job(live))

    _set_pending(chat, "report")
    chat["updated_at"] = now_iso()
    save_chat(chat)
    job = begin_job(chat_id, "report")
    asyncio.create_task(_run_report_job(job, chat_id=chat_id))
    return sse(stream_job(job))


@router.get("/api/chats/{chat_id}/events")
async def chat_events(chat_id: str, kind: str = "reply"):
    if kind not in ("reply", "report"):
        raise HTTPException(status_code=400, detail="kind invalide")
    chat = load_chat(chat_id)
    live = get_job(chat_id, kind)
    if live:
        return sse(stream_job(live))
    if kind == "reply":
        job = _resume_or_restart_reply(chat)
        if job:
            return sse(stream_job(job))
    else:
        job = _resume_or_restart_report(chat)
        if job:
            return sse(stream_job(job))

    async def snapshot() -> AsyncGenerator[bytes, None]:
        yield f"data: CONVERSATION:{chat_id}\n\n".encode()
        if chat.get("report_id"):
            yield f"data: REPORT:{chat['report_id']}\n\n".encode()
        if kind == "reply":
            last = None
            for m in chat.get("messages") or []:
                if m.get("role") == "assistant" and (m.get("content") or "").strip():
                    last = m
            if last:
                yield f"data: ASSISTANT:{last.get('id')}\n\n".encode()
                yield b"data: [ANSWER_START]\n\n"
                text = (last.get("content") or "").replace("\n", "\\n")
                yield f"data: {text}\n\n".encode()
                yield b"data: [ANSWER_END]\n\n"
            yield f"data: TITLE:{chat.get('title') or 'Conversation'}\n\n".encode()
        elif chat.get("report_id"):
            yield f"data: REPORT:{chat['report_id']}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return sse(snapshot())


@router.post("/api/chat")
async def chat_with_asclepios(body: ChatRequest):
    opening = bool(body.checkin)
    if not opening and not (body.message or "").strip():
        raise HTTPException(status_code=400, detail="Message vide")

    try:
        if opening:
            if body.conversation_id:
                chat = load_chat(body.conversation_id)
                if chat.get("kind") != "checkin":
                    chat["kind"] = "checkin"
                    if not chat.get("title") or chat.get("title") == "Nouvelle conversation":
                        chat["title"] = "Comment ça va ?"
                    save_chat(chat)
            else:
                chat = get_or_create_today_checkin()
        elif body.conversation_id:
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
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    live = get_job(chat["id"], "reply")
    if live and not live.done:
        return sse(stream_job(live))
    pending = chat.get("pending") if isinstance(chat.get("pending"), dict) else None
    if pending and pending.get("kind") == "reply":
        job = _resume_or_restart_reply(chat)
        if job:
            return sse(stream_job(job))

    history = list(chat.get("messages") or [])
    if opening:
        existing = next(
            (
                m
                for m in reversed(history)
                if m.get("role") == "assistant"
                and (m.get("content") or "").strip()
                and m.get("status") != "generating"
            ),
            None,
        )
        if existing:
            async def replay() -> AsyncGenerator[bytes, None]:
                yield f"data: CONVERSATION:{chat['id']}\n\n".encode()
                yield f"data: ASSISTANT:{existing.get('id')}\n\n".encode()
                yield b"data: [ANSWER_START]\n\n"
                text = (existing.get("content") or "").replace("\n", "\\n")
                yield f"data: {text}\n\n".encode()
                yield b"data: [ANSWER_END]\n\n"
                yield f"data: TITLE:{chat.get('title') or 'Comment ça va ?'}\n\n".encode()
                yield b"data: [DONE]\n\n"

            return sse(replay())

        generating = next(
            (m for m in reversed(history) if m.get("status") == "generating"),
            None,
        )
        if generating:
            job = _resume_or_restart_reply(chat)
            if job:
                return sse(stream_job(job))

    assistant_id = f"a-{uuid.uuid4().hex[:12]}"
    if not opening:
        user_msg = {
            "id": f"u-{uuid.uuid4().hex[:12]}",
            "role": "user",
            "content": body.message.strip(),
            "created_at": now_iso(),
        }
        chat["messages"] = history + [user_msg]
        if chat.get("title") in (None, "", "Nouvelle conversation"):
            chat["title"] = _title_from_message(body.message)
    chat["messages"] = list(chat.get("messages") or [])
    chat["messages"].append(
        {
            "id": assistant_id,
            "role": "assistant",
            "content": "",
            "status": "generating",
            "created_at": now_iso(),
        }
    )
    chat["updated_at"] = now_iso()
    if "report_id" not in chat:
        chat["report_id"] = None
    _set_pending(chat, "reply", assistant_id)
    save_chat(chat)
    asyncio.create_task(_push_vault_quiet())

    job = begin_job(chat["id"], "reply", assistant_id=assistant_id)
    asyncio.create_task(
        _run_reply_job(
            job,
            chat_id=chat["id"],
            message=body.message,
            opening=opening,
            kind=str(chat.get("kind") or "") or None,
            assistant_id=assistant_id,
        )
    )
    return sse(stream_job(job))
