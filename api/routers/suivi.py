"""Poids, traitements, profil."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any, AsyncGenerator
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
    score: int
    at: str | None = None
    replace_at: str | None = None


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
    sport_notify_at: str | None = None


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
_HUMEUR_HEADER = "at,score"


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


def _parse_mood_at(raw: str) -> datetime | None:
    from api.mood_slots import PARIS

    value = (raw or "").strip()
    if not value:
        return None
    if _DATE_RE.match(value):
        try:
            day = date.fromisoformat(value)
        except ValueError:
            return None
        return datetime(day.year, day.month, day.day, 20, 30, tzinfo=PARIS)
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=PARIS)
    return dt.astimezone(PARIS)


def _fmt_mood_at(dt: datetime) -> str:
    return dt.isoformat(timespec="minutes")


def load_mood_entries() -> list[dict[str, Any]]:
    path = config.HUMEUR_CSV
    if not path.exists():
        return []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    out: list[dict[str, Any]] = []
    for line in lines:
        raw = line.strip()
        if not raw or raw.lower().startswith("date") or raw.lower().startswith("at"):
            continue
        parts = [p.strip() for p in raw.split(",")]
        if len(parts) < 2:
            continue
        dt = _parse_mood_at(parts[0])
        try:
            score = int(parts[1])
        except ValueError:
            continue
        if dt is None or score < 0 or score > 10:
            continue
        out.append({"at": _fmt_mood_at(dt), "score": score, "dt": dt})
    out.sort(key=lambda row: row["dt"])
    return out


def _save_moods(rows: list[dict[str, Any]]) -> None:
    config.SUIVI_DIR.mkdir(parents=True, exist_ok=True)
    lines = [_HUMEUR_HEADER]
    for row in sorted(rows, key=lambda r: r["dt"]):
        lines.append(f"{_fmt_mood_at(row['dt'])},{row['score']}")
    config.HUMEUR_CSV.write_text("\n".join(lines) + "\n", encoding="utf-8")


def mood_slot_filled(day: str, slot_id: str) -> bool:
    from api.mood_slots import slot_at

    for row in load_mood_entries():
        dt: datetime = row["dt"]
        if dt.date().isoformat() != day:
            continue
        if slot_at(dt) == slot_id:
            return True
    return False


def last_mood_at() -> datetime | None:
    rows = load_mood_entries()
    if not rows:
        return None
    return rows[-1]["dt"]


@router.put("/mood")
def upsert_mood(body: MoodUpsertRequest, background_tasks: BackgroundTasks):
    from api.mood_slots import PARIS

    if body.score < 0 or body.score > 10:
        raise HTTPException(status_code=400, detail="Score entre 0 et 10")

    now = datetime.now(PARIS)
    dt = _parse_mood_at(body.at) if body.at else now
    if dt is None:
        raise HTTPException(status_code=400, detail="Horodatage invalide")
    if dt > now + timedelta(minutes=5):
        raise HTTPException(status_code=400, detail="Impossible de noter un horaire futur")

    rows = load_mood_entries()
    replace_dt = _parse_mood_at(body.replace_at) if body.replace_at else None
    if body.replace_at and replace_dt is None:
        raise HTTPException(status_code=400, detail="Note à modifier introuvable")
    replace_key = _fmt_mood_at(replace_dt) if replace_dt else None

    if replace_key:
        kept = [row for row in rows if row["at"] != replace_key]
        if len(kept) == len(rows):
            raise HTTPException(status_code=404, detail="Note à modifier introuvable")
        rows = kept

    new_at = _fmt_mood_at(dt)
    rows = [row for row in rows if row["at"] != new_at]
    rows.append({"at": new_at, "score": body.score, "dt": dt})
    _save_moods(rows)
    background_tasks.add_task(_push_vault)
    return {"at": new_at, "score": body.score}


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
            if body.sport_notify_at is not None:
                from api.sport import parse_notify_at

                raw = body.sport_notify_at.strip()
                parsed = parse_notify_at(raw)
                if raw and parsed is None:
                    yield "data: \u2717 Horaire sport invalide (HH:MM)\n\n".encode()
                    yield b"data: [ERROR]\n\n"
                    return
                if parsed:
                    data["sport_notify_at"] = parsed
                else:
                    data.pop("sport_notify_at", None)
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
