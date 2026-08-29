#!/usr/bin/env python3
"""Asclepios API — génération PDF, synchronisation et génération IA (streaming SSE)."""

from __future__ import annotations

import asyncio
import json as _json
import os
import re
import sys
import unicodedata
from datetime import date, datetime, timezone
from pathlib import Path
from typing import AsyncGenerator
import uuid

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

        async for chunk in _stream_cmd("Génération PDF", [PYTHON, str(_SCRIPT_DOCS), str(filepath), "--no-push"]):
            yield chunk

        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk

        yield f"data: GENERATED:{filename[:-3]}\n\n".encode()
        yield b"data: [DONE]\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers=SSE_HEADERS)


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
    }
    _save_chat(data)
    return data


@app.get("/api/chats/{chat_id}")
def get_chat(chat_id: str) -> dict:
    return _load_chat(chat_id)


@app.post("/api/chats/{chat_id}/delete")
async def delete_chat(chat_id: str):
    """Supprime une conversation et synchronise OVH."""
    path = _chat_path(chat_id)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Conversation introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            path.unlink()
            yield "data: \u2713 Conversation supprimée\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in _stream_cmd("Sync", [PYTHON, str(_SCRIPT_SYNC), "push"]):
            yield chunk
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
            answer = await _chat_ai(prompt)
        except Exception as exc:
            yield f"data: Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

        if not answer:
            yield "data: Erreur : réponse vide.\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return

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
