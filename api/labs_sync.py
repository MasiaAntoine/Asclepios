"""Fusionne les analytes thyroïdiens des PDF de prise de sang vers labs.csv."""

from __future__ import annotations

import csv
import re
import unicodedata
from datetime import datetime
from pathlib import Path
from typing import Any

from api import config
from api.deps import load_parse_lab

CSV_HEADERS = [
    "date",
    "analyte",
    "value",
    "unit",
    "ref_low",
    "ref_high",
    "out_of_range",
    "lab",
    "source",
]

# Noms PDF (normalisés) → code CSV
_ANALYTE_MAP = {
    "t.s.h. ultra-sensible": "TSH",
    "t.s.h ultra-sensible": "TSH",
    "t.s.h.": "TSH",
    "t.s.h": "TSH",
    "tsh": "TSH",
    "tsh ultrasensible": "TSH",
    "thyroxine libre (t4l)": "T4L",
    "thyroxine libre": "T4L",
    "t4l": "T4L",
    "triiodothyronine libre (t3l)": "T3L",
    "triiodothyronine libre": "T3L",
    "t3l": "T3L",
    "anticorps anti-thyroperoxydase": "ANTI_TPO",
    "anticorps anti thyroperoxydase": "ANTI_TPO",
    "anticorps anti-tpo": "ANTI_TPO",
    "anti-tpo": "ANTI_TPO",
    "anticorps anti recepteur de la tsh": "ANTI_RTSH",
    "anticorps anti-recepteur de la tsh": "ANTI_RTSH",
    "anti-rtsh": "ANTI_RTSH",
}


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.lower().strip()
    text = re.sub(r"\s+", " ", text)
    return text


def map_analyte(name: str) -> str | None:
    n = _fold(name)
    if n in _ANALYTE_MAP:
        return _ANALYTE_MAP[n]
    for key, code in _ANALYTE_MAP.items():
        if key in n or n in key:
            return code
    return None


def _iso_to_fr(iso: str | None) -> str | None:
    raw = (iso or "").strip()[:10]
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").strftime("%d/%m/%Y")
    except ValueError:
        return None


def _fmt_num(value: float | None) -> str:
    if value is None:
        return ""
    text = f"{value:.4f}".rstrip("0").rstrip(".")
    return text or "0"


def _norm_unit(unit: str | None) -> str:
    if not unit:
        return ""
    u = unit.strip()
    # Harmonise la casse courante des unités labo
    replacements = {
        "mui/l": "mUI/L",
        "ui/ml": "UI/mL",
        "ui/l": "UI/L",
        "ng/l": "ng/L",
        "pg/ml": "pg/mL",
        "ng/dl": "ng/dL",
    }
    return replacements.get(u.lower(), u)


def _row_key(date_fr: str, analyte: str) -> tuple[str, str]:
    return (date_fr, analyte.upper())


def _parse_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for row in reader:
            if not row.get("date") or not row.get("analyte"):
                continue
            rows.append({h: (row.get(h) or "").strip() for h in CSV_HEADERS})
        return rows


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    def sort_key(r: dict[str, str]) -> tuple:
        try:
            d = datetime.strptime(r["date"], "%d/%m/%Y")
        except ValueError:
            d = datetime.min
        return (d, r.get("analyte", ""))

    ordered = sorted(rows, key=sort_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for row in ordered:
            writer.writerow({h: row.get(h, "") for h in CSV_HEADERS})


def _extract_from_pdf(data: dict[str, Any], filename: str) -> list[dict[str, str]]:
    meta = data.get("meta") or {}
    date_fr = _iso_to_fr(str(meta.get("date") or ""))
    if not date_fr:
        # fallback filename YYYY-MM-DD_...
        m = re.match(r"^(\d{4}-\d{2}-\d{2})", filename)
        date_fr = _iso_to_fr(m.group(1) if m else None)
    if not date_fr:
        return []

    lab = str(meta.get("lab") or "").strip() or "Laboratoire"
    source = str(meta.get("filename") or filename).strip() or filename
    out: list[dict[str, str]] = []

    for section in data.get("sections") or []:
        for item in section.get("items") or []:
            if not isinstance(item, dict):
                continue
            value = item.get("value")
            if value is None:
                continue
            try:
                num = float(value)
            except (TypeError, ValueError):
                continue
            code = map_analyte(str(item.get("name") or ""))
            if not code:
                continue
            ref_low = item.get("ref_low")
            ref_high = item.get("ref_high")
            oor = item.get("out_of_range")
            if oor is None and ref_low is not None and ref_high is not None:
                try:
                    oor = not (float(ref_low) <= num <= float(ref_high))
                except (TypeError, ValueError):
                    oor = False
            out.append(
                {
                    "date": date_fr,
                    "analyte": code,
                    "value": _fmt_num(num),
                    "unit": _norm_unit(item.get("unit")),
                    "ref_low": _fmt_num(float(ref_low) if ref_low is not None else None),
                    "ref_high": _fmt_num(float(ref_high) if ref_high is not None else None),
                    "out_of_range": "True" if oor else "False",
                    "lab": lab,
                    "source": source,
                }
            )
    return out


def sync_labs_csv_from_pdfs(
    *,
    csv_path: Path | None = None,
    pdf_dir: Path | None = None,
) -> dict[str, Any]:
    """Merge idempotent : clé (date, analyte). Les valeurs PDF écrasent l'existant."""
    csv_path = csv_path or config.LABS_CSV
    pdf_dir = pdf_dir or config.PDS_DIR
    mod = load_parse_lab()

    existing = _parse_csv(csv_path)
    by_key: dict[tuple[str, str], dict[str, str]] = {
        _row_key(r["date"], r["analyte"]): dict(r) for r in existing
    }

    added = 0
    updated = 0
    scanned = 0
    extracted = 0
    errors: list[str] = []

    items = mod.list_lab_pdfs(pdf_dir)
    for info in items:
        scanned += 1
        pdf_id = info.get("id") or ""
        filename = info.get("filename") or f"{pdf_id}.pdf"
        try:
            path = mod.resolve_pdf(pdf_id, pdf_dir)
            data = mod.parse_with_cache(path, force=False)
            rows = _extract_from_pdf(data, filename)
        except Exception as exc:
            errors.append(f"{filename}: {exc}")
            continue

        for row in rows:
            extracted += 1
            key = _row_key(row["date"], row["analyte"])
            prev = by_key.get(key)
            if prev is None:
                by_key[key] = row
                added += 1
            elif any(prev.get(h) != row.get(h) for h in CSV_HEADERS):
                by_key[key] = row
                updated += 1

    changed = added > 0 or updated > 0
    if changed:
        _write_csv(csv_path, list(by_key.values()))

    return {
        "scanned_pdfs": scanned,
        "extracted": extracted,
        "added": added,
        "updated": updated,
        "unchanged": extracted - added - updated,
        "changed": changed,
        "errors": errors,
    }
