"""Génération PDF à la volée."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from api import config
from api.deps import (
    TempDir,
    attachment_response,
    pdf_period_args,
    resolve_md_doc,
    run_cmd,
    with_period_stem,
    zip_bytes,
)

router = APIRouter(prefix="/api/pdf", tags=["pdf"])


@router.get("/download/report/{report_id}")
async def download_report_pdf(report_id: str):
    """Génère le PDF d'un rapport et le renvoie en téléchargement."""
    md_path = resolve_md_doc(report_id)
    safe_id = md_path.stem
    with TempDir() as tdir:
        out = tdir / f"{safe_id}.pdf"
        await run_cmd(
            [
                config.PYTHON,
                str(config.SCRIPT_DOCS),
                str(md_path),
                "--output",
                str(out),
                "--no-push",
            ]
        )
        if not out.exists():
            raise HTTPException(status_code=500, detail="PDF non généré")
        return attachment_response(out.read_bytes(), f"{safe_id}.pdf", "application/pdf")


@router.get("/download/poids")
async def download_poids_pdf(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    download_name = with_period_stem("compte_rendu_poids.pdf", date_from, date_to)
    with TempDir() as tdir:
        out = tdir / download_name
        cmd = [
            config.PYTHON,
            str(config.SCRIPT_WEIGHT),
            "--output",
            str(out),
            "--no-push",
            *pdf_period_args(date_from, date_to),
        ]
        if not date_from and not date_to:
            cmd.extend(["--periode", "tout"])
        await run_cmd(cmd)
        if not out.exists():
            raise HTTPException(status_code=500, detail="PDF non généré")
        return attachment_response(out.read_bytes(), download_name, "application/pdf")


@router.get("/download/labs")
async def download_labs_pdf(
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    period = pdf_period_args(date_from, date_to)
    with TempDir() as tdir:
        out1 = tdir / "compte_rendu_biologie.pdf"
        out2 = tdir / "comparaison_marqueur_dose.pdf"
        await run_cmd(
            [config.PYTHON, str(config.SCRIPT_BIO), "--output", str(out1), "--no-push", *period]
        )
        await run_cmd(
            [config.PYTHON, str(config.SCRIPT_BIO2), "--output", str(out2), "--no-push", *period]
        )
        files: list[tuple[str, bytes]] = []
        for path in (out1, out2):
            if path.exists():
                files.append((with_period_stem(path.name, date_from, date_to), path.read_bytes()))
        if not files:
            raise HTTPException(status_code=500, detail="PDF non générés")
        if len(files) == 1:
            name, data = files[0]
            return attachment_response(data, name, "application/pdf")
        zip_name = with_period_stem("comptes_rendus_labs.zip", date_from, date_to)
        return attachment_response(zip_bytes(files), zip_name, "application/zip")


@router.get("/download/traitements")
async def download_traitements_pdf(
    filtre: str | None = Query(default=None),
    date_from: str | None = Query(default=None),
    date_to: str | None = Query(default=None),
):
    with TempDir() as tdir:
        cmd = [
            config.PYTHON,
            str(config.SCRIPT_RX),
            "--outdir",
            str(tdir),
            "--no-push",
            *pdf_period_args(date_from, date_to),
        ]
        if filtre:
            cmd.append(filtre)
        await run_cmd(cmd)
        pdfs = sorted(tdir.glob("*.pdf"))
        if not pdfs:
            raise HTTPException(status_code=500, detail="PDF non générés")
        if len(pdfs) == 1:
            p = pdfs[0]
            name = with_period_stem(p.name, date_from, date_to)
            return attachment_response(p.read_bytes(), name, "application/pdf")
        zip_base = f"traitement_{filtre}.zip" if filtre else "traitements.pdf.zip"
        return attachment_response(
            zip_bytes(
                [(with_period_stem(p.name, date_from, date_to), p.read_bytes()) for p in pdfs]
            ),
            with_period_stem(zip_base, date_from, date_to),
            "application/zip",
        )
