"""Helpers partagés (SSE, fichiers, PDF, parseurs)."""

from __future__ import annotations

import asyncio
import importlib.util
import io
import json
import re
import tempfile
import unicodedata
import zipfile
from pathlib import Path
from typing import AsyncGenerator
from urllib.parse import quote

from fastapi import HTTPException
from fastapi.responses import Response, StreamingResponse

from api import config

SSE_HEADERS = config.SSE_HEADERS


async def stream_cmd(label: str, cmd: list[str]) -> AsyncGenerator[bytes, None]:
    yield f"data: ▶  {label}\n\n".encode()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            cwd=str(config.ROOT),
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


async def run_cmd(cmd: list[str]) -> None:
    """Exécute une commande ; lève HTTP 500 si échec."""
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=str(config.ROOT),
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


def push_stream() -> AsyncGenerator[bytes, None]:
    return stream_cmd("Sync", [config.PYTHON, str(config.SCRIPT_SYNC), "push"])


def sse(stream: AsyncGenerator[bytes, None]) -> StreamingResponse:
    return StreamingResponse(stream, media_type="text/event-stream", headers=SSE_HEADERS)


def attachment_response(data: bytes, filename: str, media_type: str) -> Response:
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


def zip_bytes(files: list[tuple[str, bytes]]) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            zf.writestr(name, data)
    return buf.getvalue()


def safe_filename(name: str, *, allow_ext: str = ".md") -> str:
    safe = re.sub(r"[^a-zA-Z0-9_\-.]", "", name)
    if not safe.endswith(allow_ext):
        raise ValueError(f"Nom de fichier invalide : {name!r}")
    return safe


def resolve_md_doc(report_id: str) -> Path:
    safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "", report_id.removesuffix(".md"))
    if not safe_id:
        raise HTTPException(status_code=400, detail="Identifiant invalide")
    path_a = config.RAPPORTS_DIR / f"{safe_id}.md"
    path_b = config.RECITS_DIR / f"{safe_id}.md"
    if path_a.exists():
        return path_a
    if path_b.exists():
        return path_b
    raise HTTPException(status_code=404, detail="Document introuvable")


def pdf_period_args(date_from: str | None, date_to: str | None) -> list[str]:
    args: list[str] = []
    if date_from:
        args.extend(["--from", date_from])
    if date_to:
        args.extend(["--to", date_to])
    return args


def period_name_suffix(date_from: str | None, date_to: str | None) -> str:
    if date_from and date_to:
        return f"_{date_from}_au_{date_to}"
    if date_from:
        return f"_depuis_{date_from}"
    if date_to:
        return f"_jusquau_{date_to}"
    return "_tout"


def with_period_stem(name: str, date_from: str | None, date_to: str | None) -> str:
    path = Path(name)
    suffix = period_name_suffix(date_from, date_to)
    return f"{path.stem}{suffix}{path.suffix}"


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", "-", text.lower())
    return text.strip("-")[:60]


def resolve_suivi_csv(name: str) -> Path:
    fname = Path(name.replace("\\", "/")).name
    if not re.fullmatch(r"[A-Za-z0-9_\-]+\.csv", fname):
        raise HTTPException(status_code=400, detail="Fichier CSV invalide")
    path = config.SUIVI_DIR / fname
    if not path.exists():
        raise HTTPException(status_code=404, detail="CSV introuvable")
    return path


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def dump_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_parse_lab():
    spec = importlib.util.spec_from_file_location("parse_lab_pdf", config.SCRIPT_PARSE_LAB)
    if spec is None or spec.loader is None:
        raise RuntimeError("parse_lab_pdf.py introuvable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load_parse_ordonnance():
    spec = importlib.util.spec_from_file_location(
        "parse_ordonnance_pdf", config.SCRIPT_PARSE_ORD
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("parse_ordonnance_pdf.py introuvable")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def get_rapport_template() -> str:
    if config.RAPPORT_TEMPLATE_PATH.exists():
        return config.RAPPORT_TEMPLATE_PATH.read_text(encoding="utf-8")
    return ""


class TempDir:
    def __enter__(self) -> Path:
        self._ctx = tempfile.TemporaryDirectory(prefix="asclepios-pdf-")
        return Path(self._ctx.__enter__())

    def __exit__(self, *args) -> None:
        self._ctx.__exit__(*args)
