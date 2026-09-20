"""Génération de rapports Markdown via l'IA."""

from __future__ import annotations

import os
import re
import subprocess
from datetime import date
from typing import AsyncGenerator

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api import config
from api.deps import dump_json, get_rapport_template, load_json, slugify, sse, stream_cmd

router = APIRouter(prefix="/api/reports", tags=["reports"])

ALLOWED_EMOTIONS = (
    "joie",
    "tristesse",
    "anxiete",
    "colere",
    "calme",
    "espoir",
    "fatigue",
    "soulagement",
)


class ReportEmotionsBody(BaseModel):
    emotions: list[str]


def _safe_report_id(report_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", report_id)
    if not safe:
        raise HTTPException(status_code=400, detail="Identifiant invalide")
    return safe


def _load_emotions() -> dict[str, list[str]]:
    path = config.RAPPORTS_EMOTIONS_PATH
    if not path.exists():
        return {}
    try:
        data = load_json(path)
    except Exception:
        return {}
    if not isinstance(data, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, value in data.items():
        if not isinstance(key, str):
            continue
        ids = value
        if isinstance(value, dict):
            ids = value.get("emotions") or value.get("ids")
        if not isinstance(ids, list):
            continue
        out[key] = [e for e in ALLOWED_EMOTIONS if e in ids]
    return out


def _normalize_emotions(ids: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for emotion in ALLOWED_EMOTIONS:
        if emotion in ids and emotion not in seen:
            seen.add(emotion)
            out.append(emotion)
    return out


def _push_vault() -> None:
    try:
        subprocess.run(
            [config.PYTHON, str(config.SCRIPT_SYNC), "push"],
            cwd=str(config.ROOT),
            check=False,
            capture_output=True,
        )
    except Exception:
        pass


@router.get("/emotions")
def get_emotions():
    return _load_emotions()


@router.put("/{report_id}/emotions")
def put_report_emotions(
    report_id: str,
    body: ReportEmotionsBody,
    background_tasks: BackgroundTasks,
):
    safe = _safe_report_id(report_id)
    md = config.RAPPORTS_DIR / f"{safe}.md"
    if not md.is_file():
        raise HTTPException(status_code=404, detail="Rapport introuvable")
    emotions = _normalize_emotions(body.emotions)
    data = _load_emotions()
    if emotions:
        data[safe] = emotions
    else:
        data.pop(safe, None)
    config.RAPPORTS_DIR.mkdir(parents=True, exist_ok=True)
    dump_json(config.RAPPORTS_EMOTIONS_PATH, data)
    background_tasks.add_task(_push_vault)
    return {"id": safe, "emotions": emotions}


async def call_ai(text: str) -> str:
    import asyncio

    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions  # type: ignore
    except ImportError as exc:
        raise RuntimeError("cursor-sdk non installé") from exc

    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise ValueError("CURSOR_API_KEY non défini dans .env")

    template = get_rapport_template()
    prompt = (
        "Tu es un assistant médical personnel. "
        "À partir du texte fourni, génère un rapport médical structuré en Markdown.\n\n"
        "RÈGLES :\n"
        "- Réponds UNIQUEMENT avec le Markdown. Commence par `# `.\n"
        "- Pas d'introduction ni d'explication autour.\n"
        "- Conserve la première personne si le texte source l'utilise.\n"
        f"- Date de rédaction : {date.today().strftime('%d/%m/%Y')}\n\n"
        f"FORMAT REQUIS :\n{template}\n\n"
        f"TEXTE SOURCE :\n\n{text}"
    )

    result = await asyncio.to_thread(
        Agent.prompt,
        prompt,
        AgentOptions(
            api_key=api_key,
            model=config.AI_MODEL,
            local=LocalAgentOptions(cwd=str(config.RAPPORTS_DIR)),
        ),
    )
    return result.result or ""


class GenerateRequest(BaseModel):
    text: str


class GenerateForDoctorRequest(BaseModel):
    doctor_id: str
    size: str = "petit"
    date_from: str
    date_to: str
    include: list[str] = []


@router.get("/doctor-context")
def doctor_report_context(
    doctor_id: str,
    date_from: str | None = None,
    date_to: str | None = None,
):
    from api import doctor_report

    try:
        return doctor_report.doctor_context(doctor_id, date_from, date_to)
    except KeyError:
        raise HTTPException(status_code=404, detail="Médecin introuvable") from None


@router.post("/generate-for-doctor")
async def generate_for_doctor(body: GenerateForDoctorRequest):
    from api import doctor_report

    async def stream() -> AsyncGenerator[bytes, None]:
        yield "data: Préparation du dossier…\n\n".encode()
        try:
            yield "data: Collecte des données et courbes…\n\n".encode()
            _md, stem = await doctor_report.write_doctor_report(
                doctor_id=body.doctor_id,
                size=body.size,
                date_from=body.date_from,
                date_to=body.date_to,
                include=body.include,
            )
        except KeyError:
            yield "data: Médecin introuvable\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        except Exception as exc:
            yield f"data: Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        yield "data: Document sauvegardé\n\n".encode()
        async for chunk in stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
            yield chunk
        yield f"data: GENERATED:{stem}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/generate")
async def generate_with_ai(body: GenerateRequest):
    async def stream() -> AsyncGenerator[bytes, None]:
        yield "data: Appel au modèle IA...\n\n".encode()
        try:
            markdown = await call_ai(body.text)
        except Exception as exc:
            yield f"data: Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        if not markdown.strip():
            yield "data: Erreur : réponse vide.\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        m = re.search(r"^#\s+(.+)", markdown, re.MULTILINE)
        title = m.group(1).strip() if m else "document"
        filename = f"{date.today().strftime('%Y-%m-%d')}-{slugify(title)}.md"
        filepath = config.RAPPORTS_DIR / filename
        filepath.write_text(markdown, encoding="utf-8")
        yield "data: Document sauvegardé\n\n".encode()

        async for chunk in stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"]):
            yield chunk

        yield f"data: GENERATED:{filename[:-3]}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return sse(stream())
