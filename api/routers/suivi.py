"""Poids, traitements, profil."""

from __future__ import annotations

from datetime import date
from typing import AsyncGenerator
import re
import subprocess

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from api import config
from api.deps import dump_json, load_json, push_stream, sse

router = APIRouter(prefix="/api", tags=["suivi"])


class TreatmentEntryRequest(BaseModel):
    treatment_name_includes: str
    date: str
    dose: str
    posologie: str
    evenement: str
    note: str = ""


class PoidsAddRequest(BaseModel):
    date: str
    poids_kg: float


class MoodUpsertRequest(BaseModel):
    date: str
    score: int


class ProfilUpdateRequest(BaseModel):
    prenom: str
    nom: str
    date_naissance: str
    sexe: str
    taille_cm: float
    habitude_type: str = ""
    habitude_debut: str = ""
    habitude_dose: float | None = None
    habitude_note: str = ""


@router.post("/treatment/add-entry")
async def add_treatment_entry(body: TreatmentEntryRequest):
    path = config.TRAITEMENTS_PATH
    if not path.exists():
        raise HTTPException(status_code=404, detail="traitements.json introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            data = load_json(path)
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
            dump_json(path, data)
            yield "data: \u2713 Entrée ajoutée dans l'historique\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/poids/add")
async def add_poids_entry(body: PoidsAddRequest):
    path = config.POIDS_CSV
    if not path.exists():
        raise HTTPException(status_code=404, detail="poids.csv introuvable")
    if body.poids_kg <= 0 or body.poids_kg > 400:
        raise HTTPException(status_code=400, detail="Poids invalide")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.rstrip("\n").splitlines()
            new_row = f"{body.date},{body.poids_kg}"
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
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())


_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_HUMEUR_HEADER = "date,score"


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


def _load_moods() -> dict[str, int]:
    path = config.HUMEUR_CSV
    if not path.exists():
        return {}
    rows: dict[str, int] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return {}
    for line in lines:
        raw = line.strip()
        if not raw or raw.lower().startswith("date"):
            continue
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 2:
            continue
        day, score_s = parts[0], parts[1]
        if not _DATE_RE.match(day):
            continue
        try:
            score = int(score_s)
        except ValueError:
            continue
        if 0 <= score <= 10:
            rows[day] = score
    return rows


def _save_moods(rows: dict[str, int]) -> None:
    config.SUIVI_DIR.mkdir(parents=True, exist_ok=True)
    lines = [_HUMEUR_HEADER]
    for day in sorted(rows):
        lines.append(f"{day},{rows[day]}")
    config.HUMEUR_CSV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mood_logged_on(day: str) -> bool:
    return day in _load_moods()


@router.put("/mood")
def upsert_mood(body: MoodUpsertRequest, background_tasks: BackgroundTasks):
    if not _DATE_RE.match(body.date):
        raise HTTPException(status_code=400, detail="Date invalide")
    try:
        day = date.fromisoformat(body.date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Date invalide") from None
    if day > date.today():
        raise HTTPException(status_code=400, detail="Impossible de noter un jour futur")
    if body.score < 0 or body.score > 10:
        raise HTTPException(status_code=400, detail="Score entre 0 et 10")
    rows = _load_moods()
    updated = body.date in rows
    rows[body.date] = body.score
    _save_moods(rows)
    background_tasks.add_task(_push_vault)
    return {"date": body.date, "score": body.score, "updated": updated}


@router.post("/profil/update")
async def update_profil(body: ProfilUpdateRequest):
    path = config.PROFIL_PATH
    if not path.exists():
        raise HTTPException(status_code=404, detail="profil.json introuvable")

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            data = load_json(path)
            data["prenom"] = body.prenom.strip()
            data["nom"] = body.nom.strip()
            data["date_naissance"] = body.date_naissance.strip()
            data["sexe"] = body.sexe.strip()
            data["taille_cm"] = body.taille_cm
            habitude = data.get("habitude") or {}
            habitude["type"] = body.habitude_type.strip()
            habitude["debut"] = body.habitude_debut.strip()
            if body.habitude_dose is not None:
                habitude["dose"] = body.habitude_dose
            if body.habitude_note.strip():
                habitude["note"] = body.habitude_note.strip()
            data["habitude"] = habitude
            dump_json(path, data)
            yield "data: \u2713 Profil mis à jour\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())
