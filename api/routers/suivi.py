"""Poids, traitements, profil."""

from __future__ import annotations

from datetime import date
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
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
