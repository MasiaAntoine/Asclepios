"""Prises de sang PDF + ajout d'une ligne labs.csv."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from api import config
from api.deps import load_parse_lab, push_stream, resolve_suivi_csv, sse

router = APIRouter(prefix="/api/labs", tags=["labs"])


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


@router.get("/pdfs")
def list_lab_pdfs() -> dict:
    try:
        mod = load_parse_lab()
        items = mod.list_lab_pdfs(config.PDS_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"items": items}


@router.get("/pdfs/{pdf_id}")
def get_lab_pdf_detail(pdf_id: str, force: bool = False) -> dict:
    try:
        mod = load_parse_lab()
        path = mod.resolve_pdf(pdf_id, config.PDS_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        data = mod.parse_with_cache(path, force=force)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parsing impossible : {exc}") from exc

    items = mod.list_lab_pdfs(config.PDS_DIR)
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


@router.get("/pdfs/{pdf_id}/file")
def download_lab_pdf_file(pdf_id: str):
    try:
        mod = load_parse_lab()
        path = mod.resolve_pdf(pdf_id, config.PDS_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/pdfs/upload")
async def upload_lab_pdf(file: UploadFile = File(...)):
    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    raw = await file.read()
    if not raw or len(raw) < 100:
        raise HTTPException(status_code=400, detail="Fichier PDF vide ou invalide")
    if len(raw) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF trop volumineux (max 40 Mo)")

    try:
        mod = load_parse_lab()
        final_path = mod.save_uploaded_pdf(raw, filename, config.PDS_DIR)
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
        try:
            from api.labs_sync import sync_labs_csv_from_pdfs

            summary = sync_labs_csv_from_pdfs()
            if summary.get("changed"):
                yield (
                    "data: \u2713 labs.csv mis à jour "
                    f"(+{summary.get('added', 0)} / ~{summary.get('updated', 0)})\n\n"
                ).encode()
            else:
                yield "data: labs.csv déjà à jour\n\n".encode()
        except Exception as sync_exc:
            yield f"data: Sync labs.csv ignorée : {sync_exc}\n\n".encode()
        yield "data: Push OVH (nouveaux / modifiés uniquement)…\n\n".encode()
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())


@router.post("/sync-from-pdfs")
def sync_labs_from_pdfs() -> dict:
    """Met à jour labs.csv depuis les PDF de prise de sang (merge idempotent)."""
    from api.labs_sync import sync_labs_csv_from_pdfs

    try:
        return sync_labs_csv_from_pdfs()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/add")
async def add_lab_entry(body: LabAddRequest):
    path = resolve_suivi_csv(body.csv)

    oor = body.out_of_range
    if oor is None and body.ref_low is not None and body.ref_high is not None:
        oor = not (body.ref_low <= body.value <= body.ref_high)

    async def stream() -> AsyncGenerator[bytes, None]:
        try:
            content = path.read_text(encoding="utf-8")
            lines = content.rstrip("\n").splitlines()
            ref_l = "" if body.ref_low is None else str(body.ref_low)
            ref_h = "" if body.ref_high is None else str(body.ref_high)
            new_row = (
                f"{body.date},{body.analyte},{body.value},{body.unit},"
                f"{ref_l},{ref_h},{oor},{body.lab},{body.source}"
            )
            lines.append(new_row)
            path.write_text("\n".join(lines) + "\n", encoding="utf-8")
            yield "data: \u2713 Ligne ajoutée dans le CSV\n\n".encode()
        except Exception as exc:
            yield f"data: \u2717 Erreur : {exc}\n\n".encode()
            yield b"data: [ERROR]\n\n"
            return
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())
