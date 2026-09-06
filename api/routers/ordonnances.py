"""Ordonnances PDF."""

from __future__ import annotations

from typing import AsyncGenerator

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import FileResponse

from api import config
from api.deps import load_parse_ordonnance, push_stream, sse

router = APIRouter(prefix="/api/ordonnances", tags=["ordonnances"])


@router.get("/pdfs")
def list_ordonnance_pdfs() -> dict:
    try:
        mod = load_parse_ordonnance()
        items = mod.list_ordonnance_pdfs(config.ORDONNANCES_DIR)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"items": items}


@router.get("/pdfs/{pdf_id}")
def get_ordonnance_pdf_detail(pdf_id: str, force: bool = False) -> dict:
    try:
        mod = load_parse_ordonnance()
        path = mod.resolve_pdf(pdf_id, config.ORDONNANCES_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        data = mod.parse_with_cache(path, force=force)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Parsing impossible : {exc}") from exc

    items = mod.list_ordonnance_pdfs(config.ORDONNANCES_DIR)
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
def download_ordonnance_pdf_file(pdf_id: str):
    try:
        mod = load_parse_ordonnance()
        path = mod.resolve_pdf(pdf_id, config.ORDONNANCES_DIR)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="PDF introuvable") from None
    return FileResponse(
        path,
        media_type="application/pdf",
        filename=path.name,
        headers={"Cache-Control": "no-store"},
    )


@router.post("/pdfs/upload")
async def upload_ordonnance_pdf(file: UploadFile = File(...)):
    filename = file.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF sont acceptés")

    raw = await file.read()
    if not raw or len(raw) < 100:
        raise HTTPException(status_code=400, detail="Fichier PDF vide ou invalide")
    if len(raw) > 40 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="PDF trop volumineux (max 40 Mo)")

    mod = load_parse_ordonnance()
    try:
        final_path = mod.save_uploaded_pdf(raw, filename, config.ORDONNANCES_DIR)
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
        async for chunk in push_stream():
            yield chunk
        yield b"data: [DONE]\n\n"

    return sse(stream())
