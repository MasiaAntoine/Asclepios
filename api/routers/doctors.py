"""Annuaire médecins."""

from __future__ import annotations

import re
from typing import AsyncGenerator

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from api import config
from api.deps import dump_json, load_json, push_stream, slugify, sse

router = APIRouter(tags=["doctors"])


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


def _load_doctors() -> dict:
    path = config.DOCTORS_PATH
    if not path.exists():
        return {"medecins": []}
    return load_json(path)


def _save_doctors(data: dict) -> None:
    dump_json(config.DOCTORS_PATH, data)


def _doctor_from_body(body: DoctorUpsertRequest, existing: dict | None = None) -> dict:
    doc = dict(existing) if existing else {}
    doc_id = body.id or slugify(f"{body.prenom}-{body.nom}")
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


@router.post("/api/doctors")
async def create_doctor(body: DoctorUpsertRequest):
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
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/api/doctors/{doctor_id}/update")
async def update_doctor(doctor_id: str, body: DoctorUpsertRequest):
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
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/api/doctors/{doctor_id}/delete")
async def delete_doctor(doctor_id: str):
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
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())
