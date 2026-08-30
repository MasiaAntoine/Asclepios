#!/usr/bin/env python3
"""Asclepios API — génération PDF, synchronisation et génération IA (streaming SSE)."""

from __future__ import annotations

import asyncio
import io
import json as _json
import os
import re
import sys
import tempfile
import unicodedata
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
import uuid
from urllib.parse import quote

from dotenv import load_dotenv
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response, StreamingResponse
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

# ── Scripts de génération ───────────────────────────────────────────────────

_SCRIPT_DOCS   = SCRIPTS_DIR / "rapport_personnels.py"
_SCRIPT_WEIGHT = SCRIPTS_DIR / "rapport_poids.py"
_SCRIPT_BIO    = SCRIPTS_DIR / "rapport_thyroide.py"
_SCRIPT_BIO2   = SCRIPTS_DIR / "rapport_thyroide_levothyrox.py"
_SCRIPT_RX     = SCRIPTS_DIR / "rapport_traitements.py"
_SCRIPT_SYNC   = PROJECT_SCRIPTS_DIR / "sync.py"
_SCRIPT_PARSE_LAB = SCRIPTS_DIR / "parse_lab_pdf.py"
_SCRIPT_PARSE_ORD = SCRIPTS_DIR / "parse_ordonnance_pdf.py"
_PDS_DIR = DATA_DIR / "prise-de-sang"
_ORD_DIR = DATA_DIR / "ordonnances"

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


async def _run_cmd(cmd: list[str]) -> None:
    """Exécute une commande ; lève HTTP 500 si échec."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(ROOT),
    )
    assert proc.stdout is not None
    logs: list[str] = []
    async for raw in proc.stdout:
        line = raw.decode("utf-8", errors="replace").rstrip()
        if line:
            logs.append(line)
    rc = (await proc.wait()) or 0
    if rc != 0:
        detail = "\n".join(logs[-20:]) or f"Code {rc}"
        raise HTTPException(status_code=500, detail=f"Génération PDF échouée : {detail}")


def _attachment_response(data: bytes, filename: str, media_type: str) -> Response:
    ascii_name = re.sub(r"[^A-Za-z0-9._-]", "_", filename) or "download"
    return Response(
        content=data,
        media_type=media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{ascii_name}"; '
                f"filename*=UTF-8''{quote(filename)}"
            ),
            "Cache-Control": "no-store",
        },
    )


def _zip_bytes(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    return buf.getvalue()


def _safe_filename(name: str, *, allow_ext: str = ".md") -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-.]", "", name)
    if not safe.endswith(allow_ext):
        raise ValueError(f"Nom de fichier invalide : {name!r}")
    return safe


def _resolve_md_doc(report_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", report_id.removesuffix(".md"))
    if not safe_id:
        raise HTTPException(status_code=400, detail="Identifiant invalide")
    path_a = _DIR_A / f"{safe_id}.md"
    path_b = _DIR_B / f"{safe_id}.md"
    if path_a.exists():
        return path_a
    if path_b.exists():
        return path_b
    raise HTTPException(status_code=404, detail="Document introuvable")


# ── Endpoints PDF (génération à la volée) ───────────────────────────────────


def _pdf_period_args(
    date_from: str | None,
    date_to: str | None,
) -> list[str]:
    args: list[str] = []
    if date_from:
        args.extend(["--from", date_from])
    if date_to:
        args.extend(["--to", date_to])
    return args


def _period_name_suffix(date_from: str | None, date_to: str | None) -> str:
    """Suffixe de fichier : `_2026-02-28_au_2026-08-30` ou `_tout`."""
    if date_from and date_to:
        return f"_{date_from}_au_{date_to}"
    if date_from:
        return f"_depuis_{date_from}"
    if date_to:
        return f"_jusquau_{date_to}"
    return "_tout"


def _with_period_stem(name: str, date_from: str | None, date_to: str | None) -> str:
    """Insère le suffixe période avant l’extension (pdf/zip)."""
    path = Path(name)
    suffix = _period_name_suffix(date_from, date_to)
    return f"{path.stem}{suffix}{path.suffix}"


@app.get("/api/pdf/download/report/{report_id}")
async def download_report_pdf(report_id: str):
    """Génère le PDF d'un rapport/trauma et le renvoie en téléchargement."""
    md_path = _resolve_md_doc(report_id)
    safe_id = md_path.stem
    with tempfile.TemporaryDirectory(prefix="asclepios-pdf-") as td:
        out = Path(td) / f"{safe_id}.pdf"
        await _run_cmd(
            [PYTHON, str(_SCRIPT_DOCS), str(md_path), "--output", str(out), "--no-push"]
        )
        if not out.exists():
            raise HTTPException(status_code=500, detail="PDF non généré")
        return _attachment_response(out.read_bytes(), f"{safe_id}.pdf", "application/pdf")


@app.get("/api/pdf/download/poids")
async def download_poids_pdf(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """Génère le compte-rendu poids (période optionnelle) et le renvoie."""
    download_name = _with_period_stem(
        "compte_rendu_poids.pdf", date_from, date_to
    )
    with tempfile.TemporaryDirectory(prefix="asclepios-pdf-") as td:
        out = Path(td) / download_name
        cmd = [
            PYTHON,
            str(_SCRIPT_WEIGHT),
            "--output",
            str(out),
            "--no-push",
            *_pdf_period_args(date_from, date_to),
        ]
        if not date_from and not date_to:
            cmd.extend(["--periode", "tout"])
        await _run_cmd(cmd)
        if not out.exists():
            raise HTTPException(status_code=500, detail="PDF non généré")
        return _attachment_response(
            out.read_bytes(), download_name, "application/pdf"
        )


@app.get("/api/pdf/download/labs")
async def download_labs_pdf(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """Génère les PDF labos (thyroïde + comparaison) et renvoie un ZIP."""
    period = _pdf_period_args(date_from, date_to)
    with tempfile.TemporaryDirectory(prefix="asclepios-pdf-") as td:
        tdir = Path(td)
        out1 = tdir / "compte_rendu_thyroide.pdf"
        out2 = tdir / "comparaison_tsh_levothyrox.pdf"
        await _run_cmd(
            [PYTHON, str(_SCRIPT_BIO), "--output", str(out1), "--no-push", *period]
        )
        await _run_cmd(
            [PYTHON, str(_SCRIPT_BIO2), "--output", str(out2), "--no-push", *period]
        )
        files: list[tuple[str, bytes]] = []
        for path in (out1, out2):
            if path.exists():
                files.append(
                    (
                        _with_period_stem(path.name, date_from, date_to),
                        path.read_bytes(),
                    )
                )
        if not files:
            raise HTTPException(status_code=500, detail="PDF non générés")
        if len(files) == 1:
            name, data = files[0]
            return _attachment_response(data, name, "application/pdf")
        zip_name = _with_period_stem(
            "comptes_rendus_labs.zip", date_from, date_to
        )
        return _attachment_response(
            _zip_bytes(files), zip_name, "application/zip"
        )


@app.get("/api/pdf/download/traitements")
async def download_traitements_pdf(
    filtre: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    """Génère le(s) PDF traitement(s) ; un PDF ou un ZIP selon le nombre."""
    with tempfile.TemporaryDirectory(prefix="asclepios-pdf-") as td:
        outdir = Path(td)
        cmd = [
            PYTHON,
            str(_SCRIPT_RX),
            "--outdir",
            str(outdir),
            "--no-push",
            *_pdf_period_args(date_from, date_to),
        ]
        if filtre:
            cmd.append(filtre)
        await _run_cmd(cmd)
        pdfs = sorted(outdir.glob("*.pdf"))
        if not pdfs:
            raise HTTPException(status_code=500, detail="PDF non générés")
        if len(pdfs) == 1:
            p = pdfs[0]
            name = _with_period_stem(p.name, date_from, date_to)
            return _attachment_response(p.read_bytes(), name, "application/pdf")
        zip_base = (
            f"traitement_{filtre}.zip" if filtre else "traitements.pdf.zip"
        )
        return _attachment_response(
            _zip_bytes(
                [
                    (_with_period_stem(p.name, date_from, date_to), p.read_bytes())
                    for p in pdfs
                ]
            ),
            _with_period_stem(zip_base, date_from, date_to),
            "application/zip",
        )


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


def _load_parse_lab():
    """Charge le module parse_lab_pdf depuis data/scripts."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("parse_lab_pdf", _SCRIPT_PARSE_LAB)
    if spec is None or spec.loader is None:
        raise RuntimeError("parse_lab_pdf.py introuvable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _load_parse_ordonnance():
    """Charge le module parse_ordonnance_pdf depuis data/scripts."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "parse_ordonnance_pdf", _SCRIPT_PARSE_ORD
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("parse_ordonnance_pdf.py introuvable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@app.get("/api/labs/pdfs")
def list_lab_pdfs() -> dict:
    """Liste les PDF de prise de sang."""
    try:
        mod = _load_parse_lab()
        items = mod.list_lab_pdfs(_PDS_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"items": items}


@app.get("/api/labs/pdfs/{pdf_id}")
def get_lab_pdf_detail(pdf_id: str, force: bool = False) -> dict:
    """Détail parsé d'un PDF de prise de sang (cache JSON)."""
    try:
        mod = _load_parse_lab()
        path = mod.resolve_pdf(pdf_id, _PDS_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        data = mod.parse_with_cache(path, force=force)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parsing impossible : {exc}") from exc

    # Navigation prev/next
    items = mod.list_lab_pdfs(_PDS_DIR)
    ids = [i["id"] for i in items]
    idx = ids.index(path.stem) if path.stem in ids else -1
    data["navigation"] = {
        "prev_id": ids[idx + 1] if 0 <= idx < len(ids) - 1 else None,  # older (list is desc)
        "next_id": ids[idx - 1] if idx > 0 else None,  # newer
        "index": idx,
        "total": len(ids),
    }
    data["id"] = path.stem
    return data


@app.get("/api/labs/pdfs/{pdf_id}/file")
def download_lab_pdf_file(pdf_id: str):
    """Télécharge le PDF source."""
    try:
        mod = _load_parse_lab()
        path = mod.resolve_pdf(pdf_id, _PDS_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/labs/pdfs/upload")
async def upload_lab_pdf(file: UploadFile = File(...)):
    """Enregistre un PDF de prise de sang, le normalise, puis push OVH."""
    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    raw = await file.read()
    if not raw or len(raw) < 100:
        raise HTTPException(status_code=400, detail="Fichier PDF vide ou invalide")
    if len(raw) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF trop volumineux (max 40 Mo)")

    try:
        mod = _load_parse_lab()
        final_path = mod.save_uploaded_pdf(raw, filename, _PDS_DIR)
        final_id = final_path.stem
        try:
            mod.parse_with_cache(final_path, force=True)
        except Exception:
            pass
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Enregistrement impossible : {exc}") from exc

    async def stream() -> AsyncGenerator[bytes, None]:
        yield f"data: \u2713 PDF enregistré : {final_path.name}\n\n".encode()
        yield f"data: ID:{final_id}\n\n".encode()
        yield "data: Push OVH (nouveaux / modifiés uniquement)…\n\n".encode()
        async for chunk in _push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── Ordonnances PDF ───────────────────────────────────────────────────────────


@app.get("/api/ordonnances/pdfs")
def list_ordonnance_pdfs() -> dict:
    """Liste les PDF d'ordonnances."""
    try:
        mod = _load_parse_ordonnance()
        items = mod.list_ordonnance_pdfs(_ORD_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"items": items}


@app.get("/api/ordonnances/pdfs/{pdf_id}")
def get_ordonnance_pdf_detail(pdf_id: str, force: bool = False) -> dict:
    """Détail parsé d'une ordonnance PDF (cache JSON)."""
    try:
        mod = _load_parse_ordonnance()
        path = mod.resolve_pdf(pdf_id, _ORD_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        data = mod.parse_with_cache(path, force=force)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parsing impossible : {exc}") from exc

    items = mod.list_ordonnance_pdfs(_ORD_DIR)
    ids = [i["id"] for i in items]
    idx = ids.index(path.stem) if path.stem in ids else -1
    data["navigation"] = {
        "prev_id": ids[idx + 1] if 0 <= idx < len(ids) - 1 else None,
        "next_id": ids[idx - 1] if idx > 0 else None,
        "index": idx,
        "total": len(ids),
    }
    data["id"] = path.stem
    return data


@app.get("/api/ordonnances/pdfs/{pdf_id}/file")
def download_ordonnance_pdf_file(pdf_id: str):
    """Télécharge le PDF source d'ordonnance."""
    try:
        mod = _load_parse_ordonnance()
        path = mod.resolve_pdf(pdf_id, _ORD_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )


@app.post("/api/ordonnances/pdfs/upload")
async def upload_ordonnance_pdf(file: UploadFile = File(...)):
    """Enregistre un PDF d'ordonnance, le parse, puis push OVH."""
    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    raw = await file.read()
    if not raw or len(raw) < 100:
        raise HTTPException(status_code=400, detail="Fichier PDF vide ou invalide")
    if len(raw) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF trop volumineux (max 40 Mo)")

    mod = _load_parse_ordonnance()
    try:
        final_path = mod.save_uploaded_pdf(raw, filename, _ORD_DIR)
        final_id = final_path.stem
        try:
            mod.parse_with_cache(final_path, force=True)
        except Exception:
            pass
    except mod.DuplicateOrdonnanceError as exc:
        raise HTTPException(
            status_code=409,
            detail=f"Déjà importé : {exc.existing.name}",
        ) from None
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Enregistrement impossible : {exc}") from exc

    async def stream() -> AsyncGenerator[bytes, None]:
        yield f"data: \u2713 PDF enregistré : {final_path.name}\n\n".encode()
        yield f"data: ID:{final_id}\n\n".encode()
        yield "data: Push OVH (nouveaux / modifiés uniquement)…\n\n".encode()
        async for chunk in _push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


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


# ── Édition UI : poids, profil, médecins ─────────────────────────────────────


class PoidsAddRequest(BaseModel):
    date: str
    poids_kg: float


class ProfilUpdateRequest(BaseModel):
    prenom: str
    nom: str
    date_naissance: str
    sexe: str
    taille_cm: float
    tabac_type: str = ""
    tabac_debut: str = ""
    tabac_nicotine_mg_ml: float | None = None
    tabac_note: str = ""


class DoctorUpsertRequest(BaseModel):
    id: str | None = None
    titre: str = "Dr"
    prenom: str
    nom: str
    specialite: str
    role: str = ""
    telephone: str = ""
    doctolib: str = ""
    voie: str = ""
    code_postal: str = ""
    ville: str = ""
    presentation: str = ""
    notes: str = ""


def _push_stream() -> AsyncGenerator[bytes, None]:
    return _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"])


@app.post("/api/poids/add")
async def add_poids_entry(body: PoidsAddRequest):
    """Ajoute une mesure dans poids.csv et synchronise."""
    path = DATA_DIR / "poids.csv"
    if not path.exists():
        raise HTTPException(status_code=404, detail="poids.csv introuvable")
    if body.poids_kg <= 0 or body.poids_kg > 400:
        raise HTTPException(status_code=400, detail="Poids invalide")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.rstrip("\n").splitlines()
            new_row = f"{body.date},{body.poids_kg}"
            # Remplacer si même date déjà présente
            date_prefix = body.date + ","
            replaced = False
            for i, line in enumerate(lines):
                if i == 0:
                    continue
                if line.startswith(date_prefix):
                    lines[i] = new_row
                    replaced = True
                    break
            if not replaced:
                lines.append(new_row)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            yield (
                "data: \u2713 Mesure "
                + ("mise à jour" if replaced else "ajoutée")
                + "\n\n"
            ).encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/profil/update")
async def update_profil(body: ProfilUpdateRequest):
    """Met à jour les champs principaux de profil.json et synchronise."""
    path = DATA_DIR / "profil.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="profil.json introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
            data["prenom"] = body.prenom.strip()
            data["nom"] = body.nom.strip()
            data["date_naissance"] = body.date_naissance.strip()
            data["sexe"] = body.sexe.strip()
            data["taille_cm"] = body.taille_cm
            tabac = data.get("tabac") or {}
            tabac["type"] = body.tabac_type.strip()
            tabac["debut"] = body.tabac_debut.strip()
            if body.tabac_nicotine_mg_ml is not None:
                tabac["nicotine_mg_ml"] = body.tabac_nicotine_mg_ml
            elif "nicotine_mg_ml" in tabac and body.tabac_nicotine_mg_ml is None:
                pass
            if body.tabac_note.strip():
                tabac["note"] = body.tabac_note.strip()
            data["tabac"] = tabac
            path.write_text(_json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            yield "data: \u2713 Profil mis à jour\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


def _doctors_path() -> Path:
    return DATA_DIR / "doctors.json"


def _load_doctors() -> dict:
    path = _doctors_path()
    if not path.exists():
        return {"medecins": []}
    return _json.loads(path.read_text(encoding="utf-8"))


def _save_doctors(data: dict) -> None:
    _doctors_path().write_text(
        _json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _doctor_from_body(body: DoctorUpsertRequest, existing: dict | None = None) -> dict:
    doc = dict(existing) if existing else {}
    doc_id = body.id or _slugify(f"{body.prenom}-{body.nom}")
    doc["id"] = doc_id
    doc["titre"] = body.titre.strip()
    doc["prenom"] = body.prenom.strip()
    doc["nom"] = body.nom.strip()
    doc["specialite"] = body.specialite.strip()
    if body.role.strip():
        doc["role"] = body.role.strip()
    elif "role" in doc and not body.role.strip():
        doc.pop("role", None)
    doc["telephone"] = body.telephone.strip() or doc.get("telephone")
    if body.doctolib.strip():
        doc["doctolib"] = body.doctolib.strip()
    if body.voie or body.code_postal or body.ville:
        addr = doc.get("adresse") or {}
        if body.voie:
            addr["voie"] = body.voie.strip()
        if body.code_postal:
            addr["code_postal"] = body.code_postal.strip()
        if body.ville:
            addr["ville"] = body.ville.strip()
        doc["adresse"] = addr
    if body.presentation.strip():
        doc["presentation"] = body.presentation.strip()
    doc["notes"] = body.notes
    if "photo" not in doc:
        doc["photo"] = None
    if "langues" not in doc:
        doc["langues"] = ["Français"]
    return doc


@app.post("/api/doctors")
async def create_doctor(body: DoctorUpsertRequest):
    """Ajoute un médecin dans doctors.json et synchronise."""
    if not body.prenom.strip() or not body.nom.strip() or not body.specialite.strip():
        raise HTTPException(status_code=400, detail="Champs obligatoires manquants")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            data = _load_doctors()
            doc = _doctor_from_body(body)
            if any(d.get("id") == doc["id"] for d in data.get("medecins", [])):
                yield f"data: \u2717 ID déjà utilisé : {doc['id']}\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            data.setdefault("medecins", []).append(doc)
            _save_doctors(data)
            yield f"data: \u2713 Médecin ajouté ({doc['id']})\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/doctors/{doctor_id}/update")
async def update_doctor(doctor_id: str, body: DoctorUpsertRequest):
    """Met à jour un médecin et synchronise."""
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", doctor_id)
    if not safe_id:
        raise HTTPException(status_code=400, detail="ID invalide")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            data = _load_doctors()
            idx = next(
                (i for i, d in enumerate(data.get("medecins", [])) if d.get("id") == safe_id),
                None,
            )
            if idx is None:
                yield f"data: \u2717 Médecin introuvable : {safe_id}\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            body.id = safe_id
            data["medecins"][idx] = _doctor_from_body(body, data["medecins"][idx])
            _save_doctors(data)
            yield "data: \u2713 Médecin mis à jour\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/doctors/{doctor_id}/delete")
async def delete_doctor(doctor_id: str):
    """Supprime un médecin et synchronise."""
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", doctor_id)
    if not safe_id:
        raise HTTPException(status_code=400, detail="ID invalide")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            data = _load_doctors()
            before = len(data.get("medecins", []))
            data["medecins"] = [d for d in data.get("medecins", []) if d.get("id") != safe_id]
            if len(data["medecins"]) == before:
                yield f"data: \u2717 Médecin introuvable : {safe_id}\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            _save_doctors(data)
            yield "data: \u2713 Médecin supprimé\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── Paramètres / sync ────────────────────────────────────────────────────────


@app.get("/api/settings/status")
def settings_status() -> dict:
    """Statut non sensible (pas de secrets)."""
    state_path = ROOT / ".sync_state.json"
    files_tracked = 0
    state_mtime: str | None = None
    if state_path.exists():
        try:
            state = _json.loads(state_path.read_text(encoding="utf-8"))
            files_tracked = len(state) if isinstance(state, dict) else 0
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
        "ai_model": "gemini-3.7-flash",
        "app_version": "0.1.0",
    }


@app.post("/api/sync/push")
async def sync_push():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in _stream_cmd("Push OVH", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/sync/pull")
async def sync_pull():
    async def stream() -> AsyncGenerator[bytes, None]:
        async for chunk in _stream_cmd("Pull OVH", [PYTHON, str(_SCRIPT_SYNC), "pull"]):
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

        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk

        yield f"data: GENERATED:{filename[:-3]}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


# ── Édition de fichiers data (avec validation utilisateur) ──────────────────


class DataEditRequest(BaseModel):
    path: str
    old_string: str
    new_string: str


@app.post("/api/data/apply-edit")
async def apply_data_edit(body: DataEditRequest):
    """Applique une modification à un fichier dans data/ et synchronise."""
    # Sécurité : whitelist des répertoires autorisés
    ALLOWED_DIRS = ("relations", "personnes", "rapports", "traumas")
    
    # Parse le path et valide
    parts = Path(body.path).parts
    if not parts or parts[0] not in ALLOWED_DIRS:
        raise HTTPException(
            status_code=403,
            detail=f"Répertoire non autorisé. Autorisés : {', '.join(ALLOWED_DIRS)}",
        )
    
    file_path = DATA_DIR / body.path
    
    # Empêcher les path traversal
    try:
        file_path = file_path.resolve()
        if not str(file_path).startswith(str(DATA_DIR)):
            raise HTTPException(status_code=403, detail="Accès refusé")
    except Exception:
        raise HTTPException(status_code=400, detail="Chemin invalide")
    
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Fichier introuvable")
    
    if not file_path.suffix in (".md", ".json"):
        raise HTTPException(status_code=403, detail="Seuls .md et .json sont autorisés")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Vérifier que old_string existe et est unique
            if body.old_string not in content:
                yield "data: ✗ Texte introuvable dans le fichier\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            
            if content.count(body.old_string) > 1:
                yield "data: ✗ Texte non unique (trouvé plusieurs fois)\n\n".encode()
                yield b"data: [ERROR]\n\n"
                return
            
            # Appliquer la modification
            updated = content.replace(body.old_string, body.new_string, 1)
            file_path.write_text(updated, encoding="utf-8")
            yield f"data: ✓ Fichier modifié : {body.path}\n\n".encode()
        except Exception as exc:
            yield f"data: ✗ Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        
        # Sync OVH
        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


class UpdateEditProposalStatusRequest(BaseModel):
    conversation_id: str
    message_id: str
    proposal_index: int
    status: str  # "applied", "rejected", "pending"


@app.post("/api/data/update-edit-status")
async def update_edit_proposal_status(body: UpdateEditProposalStatusRequest):
    """Met à jour le statut d'une proposition d'édition dans l'historique du chat."""
    if body.status not in ("applied", "rejected", "pending"):
        raise HTTPException(status_code=400, detail="Statut invalide")
    
    try:
        chat = _load_chat(body.conversation_id)
    except HTTPException:
        raise
    
    # Trouver le message
    msg = next((m for m in chat.get("messages", []) if m.get("id") == body.message_id), None)
    if not msg:
        raise HTTPException(status_code=404, detail="Message introuvable")
    
    # Vérifier que le message a des edit_proposals
    proposals = msg.get("edit_proposals", [])
    if body.proposal_index < 0 or body.proposal_index >= len(proposals):
        raise HTTPException(status_code=404, detail="Proposition introuvable")
    
    # Mettre à jour le statut
    proposals[body.proposal_index]["status"] = body.status
    proposals[body.proposal_index]["updated_at"] = _now_iso()
    
    # Sauvegarder
    _save_chat(chat)
    
    return {"ok": True, "status": body.status}


# ── Chat Asclepios (conversations persistées dans data/chats/) ───────────────

_CHATS_DIR = DATA_DIR / "chats"

_CHAT_SYSTEM = """Tu es Asclepios, l'assistant IA du dossier médical personnel de l'utilisateur.
Tu as accès au contexte complet fourni (profil, poids, analyses, traitements, médicaments, médecins, rapports)
ET à l'historique COMPLET de cette conversation.

RÈGLES :
- Réponds en français, de façon claire, empathique et structurée (Markdown si utile).
- Cette conversation est continue : tu DOIS te souvenir de tout ce qui a déjà été dit dans l'HISTORIQUE (questions, réponses, précisions).
- Base-toi sur le contexte médical + l'historique. Ne contredis pas ce que tu as déjà affirmé sauf si les données du dossier le corrigent.
- Si une info manque, dis-le clairement plutôt qu'inventer.
- Tu n'es PAS un médecin : pas de diagnostic définitif ni d'ordonnance. Tu aides à comprendre, préparer une consultation, croiser les données.
- Sois discret et respectueux (données très sensibles).
- Si on te demande une synthèse, cite les dates et valeurs concrètes du contexte.

ÉDITION DE FICHIERS :
- Tu peux PROPOSER des modifications aux fichiers dans data/ (dossiers relations, rapports, profil, etc.).
- Utilise UNIQUEMENT ce format JSON pour proposer une modification :
  ```json:edit
  {
    "path": "relations/nom-fichier.md",
    "description": "Ajout détail trauma",
    "old_string": "texte exact existant (minimum 50 chars pour unicité)",
    "new_string": "texte modifié"
  }
  ```
- L'utilisateur verra un diff et pourra valider ou refuser.
- N'édite QUE si l'utilisateur te le demande explicitement (ex: "mets à jour le dossier de X").
- IMPORTANT : old_string doit être EXACT et assez long pour être unique dans le fichier.
"""


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    conversation_id: str | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _ensure_chats_dir() -> Path:
    _CHATS_DIR.mkdir(parents=True, exist_ok=True)
    return _CHATS_DIR


def _safe_chat_id(chat_id: str) -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-]", "", chat_id)
    if not safe or len(safe) > 80:
        raise HTTPException(status_code=400, detail="ID de conversation invalide")
    return safe


def _chat_path(chat_id: str) -> Path:
    return _ensure_chats_dir() / f"{_safe_chat_id(chat_id)}.json"


def _load_chat(chat_id: str) -> dict:
    path = _chat_path(chat_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return _json.loads(path.read_text(encoding="utf-8"))


def _save_chat(data: dict) -> None:
    path = _chat_path(data["id"])
    path.write_text(_json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _title_from_message(text: str) -> str:
    clean = re.sub(r"\s+", " ", text.strip())
    if len(clean) <= 48:
        return clean or "Nouvelle conversation"
    return clean[:45].rstrip() + "…"


# Budget caractères pour l'historique injecté dans le prompt
_HISTORY_BUDGET = 100_000


def _format_history_block(history: list[dict]) -> str:
    """Inclut toute la conversation ; si trop long, garde le début + la fin."""
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

    return (
        f"{_CHAT_SYSTEM}\n\n"
        f"===== CONTEXTE MÉDICAL =====\n{context}\n"
        f"===== FIN CONTEXTE =====\n\n"
        f"===== HISTORIQUE COMPLET DE CETTE CONVERSATION =====\n"
        f"{history_block}\n"
        f"===== FIN HISTORIQUE =====\n\n"
        f"Nouvelle question de l'utilisateur (à traiter en continuité avec l'historique ci-dessus) :\n"
        f"{message.strip()}\n\n"
        "Réponds maintenant en tant qu'Asclepios (sans préfixe « Asclepios: »), "
        "en tenant compte de TOUT l'historique de cette conversation."
    )


def _extract_edit_proposals(text: str) -> tuple[str, list[dict]]:
    """Extrait les blocs ```json:edit``` du texte et retourne (texte nettoyé, propositions)."""
    proposals: list[dict] = []
    pattern = re.compile(
        r'```json:edit\s*\n(.*?)\n```',
        re.DOTALL | re.MULTILINE
    )
    
    def replace_match(m: re.Match) -> str:
        try:
            proposal = _json.loads(m.group(1))
            # Validation basique
            if all(k in proposal for k in ("path", "description", "old_string", "new_string")):
                proposals.append(proposal)
                # Supprimer complètement le bloc du texte
                return ""
        except Exception:
            pass
        return m.group(0)  # Garder tel quel si invalide
    
    cleaned = pattern.sub(replace_match, text).strip()
    # Nettoyer les lignes vides multiples
    cleaned = re.sub(r'\n\n\n+', '\n\n', cleaned)
    return cleaned, proposals


async def _chat_ai(prompt: str) -> str:
    try:
        from cursor_sdk import Agent, AgentOptions, LocalAgentOptions  # type: ignore
    except ImportError as exc:
        raise RuntimeError("cursor-sdk non installé") from exc

    api_key = os.environ.get("CURSOR_API_KEY", "").strip()
    if not api_key:
        raise ValueError("CURSOR_API_KEY non défini dans .env")

    result = await asyncio.to_thread(
        Agent.prompt,
        prompt,
        AgentOptions(
            api_key=api_key,
            model="gemini-3.7-flash",
            local=LocalAgentOptions(cwd=str(DATA_DIR)),
        ),
    )
    return (result.result or "").strip()


@app.get("/api/chats")
def list_chats() -> dict:
    """Liste les conversations (métadonnées)."""
    _ensure_chats_dir()
    items: list[dict] = []
    for path in _CHATS_DIR.glob("*.json"):
        try:
            data = _json.loads(path.read_text(encoding="utf-8"))
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


@app.post("/api/chats")
def create_chat() -> dict:
    """Crée une conversation vide dans le vault."""
    chat_id = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S") + "-" + uuid.uuid4().hex[:8]
    now = _now_iso()
    data = {
        "id": chat_id,
        "title": "Nouvelle conversation",
        "created_at": now,
        "updated_at": now,
        "messages": [],
        "report_id": None,
    }
    _save_chat(data)
    return data


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str) -> dict:
    return _load_chat(chat_id)


@app.post("/api/chats/{chat_id}/delete")
async def delete_chat(chat_id: str):
    """Supprime une conversation (interdit si liée à un rapport), puis sync OVH."""
    path = _chat_path(chat_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    chat = _load_chat(chat_id)
    if chat.get("report_id"):
        raise HTTPException(
            status_code=403,
            detail="Conversation liée à un rapport : suppression impossible",
        )

    path.unlink()

    # Sync en arrière-plan pour répondre immédiatement à l'UI
    async def _sync_later() -> None:
        try:
            async for _ in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
                pass
        except Exception:
            pass

    asyncio.create_task(_sync_later())
    return {"ok": True, "id": chat_id}


def _conversation_as_source(chat: dict) -> str:
    """Transforme toute la conversation en texte source pour génération de rapport."""
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


@app.post("/api/chats/{chat_id}/generate-report")
async def generate_report_from_chat(chat_id: str):
    """Génère (ou régénère) un rapport MD depuis toute la conversation, lie chat↔rapport."""
    chat = _load_chat(chat_id)
    msgs = [
        m
        for m in (chat.get("messages") or [])
        if m.get("role") in ("user", "assistant") and (m.get("content") or "").strip()
    ]
    if len(msgs) < 1:
        raise HTTPException(status_code=400, detail="Conversation vide")

    async def stream() -> AsyncGenerator[bytes, None]:
        existing_id = chat.get("report_id")
        regenerating = bool(existing_id)

        yield (
            "data: "
            + ("Régénération du rapport lié…" if regenerating else "Génération du rapport depuis la conversation…")
            + "\n\n"
        ).encode()

        source = _conversation_as_source(chat)
        try:
            markdown = await _call_ai(source)
        except Exception as exc:
            yield f"data: Erreur IA : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        if not markdown.strip():
            yield "data: Erreur : réponse vide.\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        # Même fichier si déjà lié ; sinon nouveau
        if regenerating and existing_id:
            report_id = re.sub(r"[^a-zA-Z0-9_\-]", "", existing_id)
            filename = f"{report_id}.md"
            filepath = _DIR_A / filename
        else:
            m = re.search(r"^#\s+(.+)", markdown, re.MULTILINE)
            title = m.group(1).strip() if m else (chat.get("title") or "conversation")
            filename = f"{date.today().strftime('%Y-%m-%d')}-{_slugify(title)}.md"
            filepath = _DIR_A / filename
            # Éviter collision accidentelle
            if filepath.exists():
                stem = filename[:-3]
                filename = f"{stem}-{uuid.uuid4().hex[:4]}.md"
                filepath = _DIR_A / filename
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

        # Lier conversation ↔ rapport
        chat["report_id"] = report_id
        chat["updated_at"] = _now_iso()
        try:
            _save_chat(chat)
            yield "data: \u2713 Conversation liée au rapport (suppression désactivée)\n\n".encode()
        except Exception as exc:
            yield f"data: Erreur liaison : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk

        yield f"data: REPORT:{report_id}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


@app.post("/api/chat")
async def chat_with_asclepios(body: ChatRequest):
    """Envoie un message, persiste dans le vault, génère la réponse IA, sync OVH."""
    if not body.message or not body.message.strip():
        raise HTTPException(status_code=400, detail="Message vide")

    async def stream() -> AsyncGenerator[bytes, None]:
        # Créer ou charger la conversation
        try:
            if body.conversation_id:
                chat = _load_chat(body.conversation_id)
            else:
                chat_id = (
                    datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
                    + "-"
                    + uuid.uuid4().hex[:8]
                )
                now = _now_iso()
                chat = {
                    "id": chat_id,
                    "title": "Nouvelle conversation",
                    "created_at": now,
                    "updated_at": now,
                    "messages": [],
                    "report_id": None,
                }
                _save_chat(chat)
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

        # Historique avant le nouveau message
        history = list(chat.get("messages") or [])

        # Append message utilisateur
        user_msg = {
            "id": f"u-{uuid.uuid4().hex[:12]}",
            "role": "user",
            "content": body.message.strip(),
            "created_at": _now_iso(),
        }
        chat["messages"] = history + [user_msg]
        if chat.get("title") in (None, "", "Nouvelle conversation"):
            chat["title"] = _title_from_message(body.message)
        chat["updated_at"] = _now_iso()
        if "report_id" not in chat:
            chat["report_id"] = None
        try:
            _save_chat(chat)
            yield "data: Message utilisateur enregistré\n\n".encode()
        except Exception as exc:
            yield f"data: Erreur sauvegarde : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk

        # Appel IA
        yield "data: Chargement du dossier médical…\n\n".encode()
        try:
            from api.medical_context import build_medical_context

            context = await asyncio.to_thread(build_medical_context, DATA_DIR)
            yield f"data: Contexte prêt ({len(context)} caractères)\n\n".encode()
            yield "data: Appel au modèle IA…\n\n".encode()
            prompt = _build_chat_prompt(body.message, history, context)
            raw_answer = await _chat_ai(prompt)
        except Exception as exc:
            yield f"data: Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        if not raw_answer:
            yield "data: Erreur : réponse vide.\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        # Extraire les propositions d'edit
        answer, edit_proposals = _extract_edit_proposals(raw_answer)

        # Envoyer les propositions d'edit (ajouter le statut initial)
        for idx, proposal in enumerate(edit_proposals):
            proposal["status"] = "pending"
            proposal["created_at"] = _now_iso()
            proposal_json = _json.dumps(proposal, ensure_ascii=False)
            yield f"data: EDIT_PROPOSAL:{proposal_json}\n\n".encode()

        yield b"data: [ANSWER_START]\n\n"
        chunk_size = 80
        for i in range(0, len(answer), chunk_size):
            piece = answer[i : i + chunk_size]
            safe = piece.replace("\n", "\\n")
            yield f"data: {safe}\n\n".encode()
            await asyncio.sleep(0)
        yield b"data: [ANSWER_END]\n\n"

        # Append réponse assistant + sync
        assistant_msg = {
            "id": f"a-{uuid.uuid4().hex[:12]}",
            "role": "assistant",
            "content": answer,
            "created_at": _now_iso(),
        }
        # Sauvegarder les propositions d'édition dans l'historique
        if edit_proposals:
            assistant_msg["edit_proposals"] = edit_proposals
        chat["messages"].append(assistant_msg)
        chat["updated_at"] = _now_iso()
        try:
            _save_chat(chat)
            yield "data: Réponse enregistrée dans le vault\n\n".encode()
            yield f"data: TITLE:{chat['title']}\n\n".encode()
        except Exception as exc:
            yield f"data: Erreur sauvegarde réponse : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)
