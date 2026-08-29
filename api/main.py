#!/usr/bin/env python3
"""Asclepios API — génération PDF, synchronisation et génération IA (streaming SSE)."""

from __future__ import annotations

import asyncio
import json as _json
import os
import re
import sys
import unicodedata
from datetime import date
from pathlib import Path
from typing import AsyncGenerator

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent / ".env")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
SCRIPTS_DIR = DATA_DIR / "scripts"
PROJECT_SCRIPTS_DIR = ROOT / "scripts"

_VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
PYTHON = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

# ── Répertoires de données ──────────────────────────────────────────────────

_DIR_A = DATA_DIR / "rapports"
_DIR_B = DATA_DIR / "traumas"
_DIR_C = DATA_DIR / "medicaments"
_DIR_PDF_A = DATA_DIR / "pdf-generes" / "rapport"
_DIR_PDF_B = DATA_DIR / "pdf-generes" / "trauma"

# ── Scripts de génération ───────────────────────────────────────────────────

_SCRIPT_DOCS   = SCRIPTS_DIR / "rapport_personnels.py"
_SCRIPT_WEIGHT = SCRIPTS_DIR / "rapport_poids.py"
_SCRIPT_BIO    = SCRIPTS_DIR / "rapport_thyroide.py"
_SCRIPT_BIO2   = SCRIPTS_DIR / "rapport_thyroide_levothyrox.py"
_SCRIPT_RX     = SCRIPTS_DIR / "rapport_traitements.py"
_SCRIPT_SYNC   = PROJECT_SCRIPTS_DIR / "sync.py"

# ── Fichier template IA (chargé une fois au démarrage) ──────────────────────

_TEMPLATE_PATH = DATA_DIR / "rapport-template.md"
_RAPPORT_TEMPLATE: str | None = None


def _get_template() -> str:
    global _RAPPORT_TEMPLATE
    if _RAPPORT_TEMPLATE is None:
        if _TEMPLATE_PATH.exists():
            _RAPPORT_TEMPLATE = _TEMPLATE_PATH.read_text(encoding="utf-8")
        else:
            _RAPPORT_TEMPLATE = ""
    return _RAPPORT_TEMPLATE


# ── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(title="Asclepios API", version="0.1.0", docs_url=None, redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}

# ── Helpers ─────────────────────────────────────────────────────────────────


def _list_category(category: str) -> list[str]:
    d = DATA_DIR / "pdf-generes" / category
    if not d.exists():
        return []
    return sorted(p.name for p in d.glob("*.pdf"))


async def _stream_cmd(label: str, cmd: list[str]) -> AsyncGenerator[bytes, None]:
    yield f"data: ▶  {label}\n\n".encode()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(ROOT),
        )
        assert proc.stdout is not None
        async for raw in proc.stdout:
            line = raw.decode("utf-8", errors="replace").rstrip()
            if line:
                yield f"data: {line}\n\n".encode()
        rc = (await proc.wait()) or 0
        yield f"data: {'✓ OK' if rc == 0 else f'✗ Code {rc}'}\n\n".encode()
    except Exception as exc:
        yield f"data: ✗ Exception: {exc}\n\n".encode()


def _safe_filename(name: str, *, allow_ext: str = ".md") -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-.]", "", name)
    if not safe.endswith(allow_ext):
        raise ValueError(f"Nom de fichier invalide : {name!r}")
    return safe


# ── Pipeline complet ─────────────────────────────────────────────────────────

_PIPELINE: list[tuple[str, list[str]]] = [
    ("Étape 1/5", [PYTHON, str(_SCRIPT_DOCS),   "--no-push"]),
    ("Étape 2/5", [PYTHON, str(_SCRIPT_WEIGHT), "--periode", "tout", "--no-push"]),
    ("Étape 3/5", [PYTHON, str(_SCRIPT_BIO),    "--no-push"]),
    ("Étape 4/5", [PYTHON, str(_SCRIPT_BIO2),   "--no-push"]),
    ("Étape 5/5", [PYTHON, str(_SCRIPT_RX),     "--no-push"]),
    ("Sync",      [PYTHON, str(_SCRIPT_SYNC),   "push"]),
]


# ── Endpoints ───────────────────────────────────────────────────────────────


@app.get("/api/pdf/list")
def list_pdfs() -> dict[str, list[str]]:
    return {cat: _list_category(cat) for cat in ["rapport", "trauma", "compte-rendu", "traitement"]}


@app.post("/api/pipeline/run")
async def run_pipeline():
    async def stream() -> AsyncGenerator[bytes, None]:
        yield "data: Démarrage...\n\n".encode()
        for label, cmd in _PIPELINE:
            async for chunk in _stream_cmd(label, cmd):
                yield chunk
        yield b"data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/pdf/generate/reports")
async def generate_reports():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in _stream_cmd("Génération documents", [PYTHON, str(_SCRIPT_DOCS), "--no-push"]):
            yield chunk
        yield b"data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/pdf/generate/report/{report_id}")
async def generate_single_report(report_id: str):
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", report_id.removesuffix(".md"))
    if not safe_id:
        raise HTTPException(status_code=400, detail="Identifiant invalide")
    path_a = _DIR_A / f"{safe_id}.md"
    path_b = _DIR_B / f"{safe_id}.md"
    if path_a.exists():
        md_path = path_a
    elif path_b.exists():
        md_path = path_b
    else:
        raise HTTPException(status_code=404, detail="Document introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in _stream_cmd(
            "Génération PDF",
            [PYTHON, str(_SCRIPT_DOCS), str(md_path), "--no-push"],
        ):
            yield chunk
        yield b"data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/pdf/generate/poids")
async def generate_poids():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in _stream_cmd("Génération PDF", [PYTHON, str(_SCRIPT_WEIGHT), "--periode", "tout", "--no-push"]):
            yield chunk
        yield b"data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/pdf/generate/labs")
async def generate_labs():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in _stream_cmd("Génération PDF (1/2)", [PYTHON, str(_SCRIPT_BIO),  "--no-push"]):
            yield chunk
        async for chunk in _stream_cmd("Génération PDF (2/2)", [PYTHON, str(_SCRIPT_BIO2), "--no-push"]):
            yield chunk
        yield b"data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/pdf/generate/traitements")
async def generate_traitements():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in _stream_cmd("Génération PDF", [PYTHON, str(_SCRIPT_RX), "--no-push"]):
            yield chunk
        yield b"data: [DONE]\n\n"
    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── Médicaments ──────────────────────────────────────────────────────────────


def _parse_med_md(content: str) -> dict:
    result: dict = {}
    m = re.search(r'\|\s*\*\*Posologie actuelle\*\*\s*\|\s*([^\|]+)\|', content)
    if m:
        result["posologie"] = m.group(1).strip()
    m = re.search(r'\|\s*\*\*Arr[êe]t temporaire\*\*\s*\|\s*([^\|]+)\|', content)
    if m:
        result["arret_temporaire"] = m.group(1).strip()
    m = re.search(r'## Notes personnelles\n(.*?)(?=\n##|\Z)', content, re.DOTALL)
    if m:
        raw = re.sub(r'<!--.*?-->', '', m.group(1), flags=re.DOTALL).strip()
        raw = re.sub(r'^-\s*$', '', raw, flags=re.MULTILINE).strip()
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
            r'(\|\s*\*\*Posologie actuelle\*\*\s*\|)\s*[^\|]+(\|)',
            lambda m: f"{m.group(1)} {posologie} {m.group(2)}",
            content,
        )
    if arret_temporaire is not None:
        content = re.sub(
            r'(\|\s*\*\*Arr[êe]t temporaire\*\*\s*\|)\s*[^\|]+(\|)',
            lambda m: f"{m.group(1)} {arret_temporaire} {m.group(2)}",
            content,
        )
    if notes is not None:
        cb = re.search(r'(## Notes personnelles\n)(<!--.*?-->\n\n?)', content, re.DOTALL)
        if cb:
            prefix = cb.group(1) + cb.group(2)
            content = re.sub(
                r'## Notes personnelles\n<!--.*?-->\n\n?.*?(?=\n##|\Z)',
                prefix + notes + "\n",
                content, flags=re.DOTALL,
            )
        else:
            content = re.sub(
                r'(## Notes personnelles\n).*?(?=\n##|\Z)',
                r'\g<1>' + notes + "\n",
                content, flags=re.DOTALL,
            )
    return content


@app.get("/api/medication/{fichier}")
async def get_medication(fichier: str) -> dict:
    try:
        safe = _safe_filename(fichier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nom invalide")
    path = _DIR_C / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    return _parse_med_md(path.read_text(encoding="utf-8"))


class MedUpdateRequest(BaseModel):
    fichier: str
    posologie: str | None = None
    arret_temporaire: str | None = None
    notes: str | None = None


@app.post("/api/medication/update")
async def update_medication(body: MedUpdateRequest):
    try:
        safe = _safe_filename(body.fichier)
    except ValueError:
        raise HTTPException(status_code=400, detail="Nom invalide")
    path = _DIR_C / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            updated = _apply_med_update(
                path.read_text(encoding="utf-8"),
                body.posologie, body.arret_temporaire, body.notes,
            )
            path.write_text(updated, encoding="utf-8")
            yield "data: \u2713 Fichier sauvegardé\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── Suivi : ajout d'entrées dans labs.csv et traitements.json ───────────────


class LabAddRequest(BaseModel):
    csv: str
    date: str
    analyte: str
    value: float
    unit: str
    ref_low: float | None = None
    ref_high: float | None = None
    out_of_range: bool | None = None
    lab: str
    source: str = ""


class TreatmentEntryRequest(BaseModel):
    treatment_name_includes: str
    date: str
    dose: str
    posologie: str
    evenement: str
    note: str = ""


@app.post("/api/labs/add")
async def add_lab_entry(body: LabAddRequest):
    """Ajoute une ligne à labs.csv et synchronise."""
    safe = re.sub(r"[^a-zA-Z0-9_\-.]", "", body.csv)
    if not safe.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Fichier CSV invalide")
    path = DATA_DIR / safe
    if not path.exists():
        raise HTTPException(status_code=404, detail="CSV introuvable")

    oor = body.out_of_range
    if oor is None and body.ref_low is not None and body.ref_high is not None:
        oor = not (body.ref_low <= body.value <= body.ref_high)

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.rstrip("\n").splitlines()
            ref_l = "" if body.ref_low is None else str(body.ref_low)
            ref_h = "" if body.ref_high is None else str(body.ref_high)
            new_row = f"{body.date},{body.analyte},{body.value},{body.unit},{ref_l},{ref_h},{oor},{body.lab},{body.source}"
            lines.append(new_row)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            yield "data: \u2713 Ligne ajoutée dans le CSV\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/treatment/add-entry")
async def add_treatment_entry(body: TreatmentEntryRequest):
    """Ajoute une entrée d'historique dans traitements.json et synchronise."""
    path = DATA_DIR / "traitements.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="traitements.json introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
            needle = body.treatment_name_includes.lower()
            treatment = next(
                (t for t in data["traitements"] if needle in t["nom"].lower()),
                None,
            )
            if not treatment:
                yield f"data: \u2717 Traitement introuvable : {body.treatment_name_includes}\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            treatment["historique"].append({
                "date": body.date,
                "dose": body.dose,
                "posologie": body.posologie,
                "evenement": body.evenement,
                "note": body.note,
            })
            data["mis_a_jour"] = date.today().strftime("%d/%m/%Y")
            path.write_text(_json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            yield "data: \u2713 Entrée ajoutée dans l'historique\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── Génération IA ────────────────────────────────────────────────────────────


def _slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.strip("-")[:60]


async def _call_ai(text: str) -> str:
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions  # type: ignore
    except ImportError as exc:
        raise RuntimeError("cursor-sdk non installé") from exc

    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise ValueError("CURSOR_API_KEY non défini dans .env")

    template = _get_template()
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
            model="gemini-3.7-flash",
            local=LocalAgentOptions(cwd=str(_DIR_A)),
        ),
    )
    return result.result or ""


class GenerateRequest(BaseModel):
    text: str


@app.post("/api/reports/generate")
async def generate_with_ai(body: GenerateRequest):
    async def stream() -> AsyncGenerator[bytes, None]:
        yield "data: Appel au modèle IA...\n\n".encode()
        try:
            markdown = await _call_ai(body.text)
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
        filename = f"{date.today().strftime('%Y-%m-%d')}-{_slugify(title)}.md"
        filepath = _DIR_A / filename
        filepath.write_text(markdown, encoding="utf-8")
        yield f"data: Document sauvegardé\n\n".encode()

        async for chunk in _stream_cmd("Génération PDF", [PYTHON, str(_SCRIPT_DOCS), str(filepath), "--no-push"]):
            yield chunk

        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk

        yield f"data: GENERATED:{filename[:-3]}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)
