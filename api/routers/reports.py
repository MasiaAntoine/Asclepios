"""Génération de rapports Markdown via l'IA."""

from __future__ import annotations

import os
import re
from datetime import date
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import config
from api.deps import get_rapport_template, slugify, sse, stream_cmd

router = APIRouter(prefix="/api/reports", tags=["reports"])


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
