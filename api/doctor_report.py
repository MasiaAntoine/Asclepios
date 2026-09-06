"""Dossier Markdown factuel + synthèse IA pour un médecin."""

from __future__ import annotations

import csv
import json
import re
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

from api import config
from api.doctor_agenda import events_for_doctor, suggest_period
from api.report_charts import plot_line, plot_step_dose

INCLUDE_KEYS = (
    "agenda",
    "medicaments",
    "rapports",
    "ordonnances",
    "prise_de_sang",
    "poids",
    "labs",
    "medication_series",
)

_FR = "%d/%m/%Y"
_ISO = "%Y-%m-%d"


def parse_day(value: str | None) -> date | None:
    raw = (value or "").strip()[:10]
    if not raw:
        return None
    for fmt in (_ISO, _FR):
        try:
            return datetime.strptime(raw.replace(".", "/"), fmt).date()
        except ValueError:
            continue
    m = re.match(r"^(\d{2})/(\d{2})/(\d{4})$", raw)
    if m:
        try:
            return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
        except ValueError:
            return None
    return None


def _in_period(day: date | None, start: date, end: date) -> bool:
    return day is not None and start <= day <= end


def _fmt(day: date | None) -> str:
    return day.strftime(_FR) if day else "—"


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def load_doctors() -> list[dict]:
    data = _read_json(config.DOCTORS_PATH) or {}
    return list(data.get("medecins") or [])


def find_doctor(doctor_id: str) -> dict | None:
    for doctor in load_doctors():
        if doctor.get("id") == doctor_id:
            return doctor
    return None


def doctor_full_name(doctor: dict) -> str:
    return " ".join(
        str(p) for p in (doctor.get("titre"), doctor.get("prenom"), doctor.get("nom")) if p
    )


def _md_table(headers: list[str], rows: list[list[str]]) -> str:
    if not rows:
        return "_Aucune donnée sur la période._\n"
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        cells = (row + [""] * len(headers))[: len(headers)]
        lines.append("| " + " | ".join(c.replace("|", "/") for c in cells) + " |")
    return "\n".join(lines) + "\n"


def _event_day(event: dict) -> date | None:
    return parse_day(str(event.get("start") or "")[:10])


def _load_agenda_events() -> list[dict]:
    from api.agenda import get_events, read_snapshot

    start = (date.today().replace(year=date.today().year - 1)).isoformat()
    end = (date.today().replace(year=date.today().year + 1)).isoformat()
    try:
        payload = get_events(config.VAULT_DIR, start=start, end=end, force=False)
        events = payload.get("events") or []
        if events:
            return list(events)
    except Exception:
        pass
    snap = read_snapshot(config.VAULT_DIR) or {}
    return list(snap.get("events") or [])


def matched_events(doctor: dict) -> list[dict]:
    return events_for_doctor(_load_agenda_events(), doctor, load_doctors())


def labs_config() -> dict:
    return _read_json(config.LABS_CONFIG_PATH) or {}


def medication_config() -> dict:
    return _read_json(config.MEDICATION_CONFIG_PATH) or {}


def _count_poids(start: date, end: date) -> int:
    path = config.POIDS_CSV
    if not path.exists():
        return 0
    n = 0
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if _in_period(parse_day(row.get("date")), start, end):
                n += 1
    return n


def _count_labs_points(start: date, end: date, analyte: str) -> int:
    path = config.LABS_CSV
    if not path.exists() or not analyte:
        return 0
    n = 0
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row.get("analyte") or "").strip().upper() != analyte.upper():
                continue
            if _in_period(parse_day(row.get("date")), start, end):
                n += 1
    return n


def _count_rapports(start: date, end: date) -> int:
    n = 0
    if not config.RAPPORTS_DIR.exists():
        return 0
    for path in config.RAPPORTS_DIR.glob("*.md"):
        if path.name.lower() == "readme.md":
            continue
        day = parse_day(path.name[:10])
        if _in_period(day, start, end):
            n += 1
    return n


def _list_pdfs(kind: str) -> list[dict]:
    try:
        if kind == "labs":
            from api.deps import load_parse_lab

            return load_parse_lab().list_lab_pdfs(config.PDS_DIR)
        from api.deps import load_parse_ordonnance

        return load_parse_ordonnance().list_ordonnance_pdfs(config.ORDONNANCES_DIR)
    except Exception:
        return []


def include_options(doctor: dict, date_from: date, date_to: date) -> list[dict]:
    events = [
        e
        for e in matched_events(doctor)
        if _in_period(_event_day(e), date_from, date_to)
    ]
    traitements = (_read_json(config.TRAITEMENTS_PATH) or {}).get("traitements") or []
    labs_cfg = labs_config()
    med_cfg = medication_config()
    ords = [
        i
        for i in _list_pdfs("ord")
        if _in_period(parse_day(str(i.get("date") or "")[:10]), date_from, date_to)
    ]
    pds = [
        i
        for i in _list_pdfs("labs")
        if _in_period(parse_day(str(i.get("date") or "")[:10]), date_from, date_to)
    ]
    return [
        {
            "id": "agenda",
            "label": "Rendez-vous",
            "hint": f"{len(events)} sur la période",
            "default": True,
        },
        {
            "id": "medicaments",
            "label": "Médicaments",
            "hint": f"{len(traitements)} traitement(s) au dossier",
            "default": True,
        },
        {
            "id": "rapports",
            "label": "Rapports",
            "hint": f"{_count_rapports(date_from, date_to)} sur la période",
            "default": True,
        },
        {
            "id": "ordonnances",
            "label": "Ordonnances",
            "hint": f"{len(ords)} sur la période",
            "default": True,
        },
        {
            "id": "prise_de_sang",
            "label": "Prises de sang",
            "hint": f"{len(pds)} sur la période",
            "default": True,
        },
        {
            "id": "poids",
            "label": "Poids",
            "hint": f"{_count_poids(date_from, date_to)} mesure(s)",
            "default": True,
        },
        {
            "id": "labs",
            "label": str(labs_cfg.get("title") or "Suivi biologique"),
            "hint": f"{_count_labs_points(date_from, date_to, str(labs_cfg.get('primaryAnalyte') or ''))} point(s)",
            "default": True,
        },
        {
            "id": "medication_series",
            "label": str(med_cfg.get("title") or "Suivi de posologie"),
            "hint": str(med_cfg.get("subtitle") or "Courbe de dose"),
            "default": True,
        },
    ]


def doctor_context(doctor_id: str, date_from: str | None, date_to: str | None) -> dict:
    doctor = find_doctor(doctor_id)
    if not doctor:
        raise KeyError(doctor_id)
    events = matched_events(doctor)
    suggestion = suggest_period(events)
    start = parse_day(date_from) or parse_day(suggestion["date_from"]) or date.today()
    end = parse_day(date_to) or parse_day(suggestion["date_to"]) or date.today()
    if end < start:
        start, end = end, start
    return {
        "doctor": {
            "id": doctor.get("id"),
            "name": doctor_full_name(doctor),
            "specialite": doctor.get("specialite"),
        },
        "events": events,
        "suggestion": suggestion,
        "date_from": start.isoformat(),
        "date_to": end.isoformat(),
        "include_options": include_options(doctor, start, end),
    }


def _filter_events(events: Iterable[dict], start: date, end: date) -> list[dict]:
    return [e for e in events if _in_period(_event_day(e), start, end)]


def _section_agenda(events: list[dict]) -> str:
    rows = []
    for ev in events:
        day = _fmt(_event_day(ev))
        title = str(ev.get("title") or "")
        loc = str(ev.get("location") or "")
        rows.append([day, title, loc or "—"])
    return "### Rendez-vous\n\n" + _md_table(["Date", "Titre", "Lieu"], rows)


def _section_poids(start: date, end: date, fig_rel: str | None) -> str:
    path = config.POIDS_CSV
    rows: list[list[str]] = []
    if path.exists():
        with path.open(encoding="utf-8") as f:
            for row in csv.DictReader(f):
                day = parse_day(row.get("date"))
                if not _in_period(day, start, end):
                    continue
                rows.append([_fmt(day), str(row.get("poids_kg") or "")])
    body = "### Poids\n\n" + _md_table(["Date", "kg"], rows)
    if fig_rel:
        body += f"\n![Évolution du poids]({fig_rel})\n"
    return body


def _section_treatments(start: date, end: date, compact: bool) -> str:
    data = _read_json(config.TRAITEMENTS_PATH) or {}
    items = data.get("traitements") or []
    rows: list[list[str]] = []
    for t in items:
        hist = t.get("historique") or []
        last = hist[-1] if hist else {}
        in_window = any(_in_period(parse_day(h.get("date")), start, end) for h in hist)
        if not in_window and not hist:
            continue
        if compact:
            rows.append(
                [
                    str(t.get("nom") or ""),
                    str(last.get("dose") or ""),
                    str(last.get("evenement") or ""),
                    _fmt(parse_day(last.get("date"))),
                ]
            )
        else:
            for h in hist:
                if not _in_period(parse_day(h.get("date")), start, end):
                    continue
                rows.append(
                    [
                        str(t.get("nom") or ""),
                        _fmt(parse_day(h.get("date"))),
                        str(h.get("dose") or ""),
                        str(h.get("evenement") or ""),
                        str(h.get("note") or ""),
                    ]
                )
    if compact:
        return "### Médicaments\n\n" + _md_table(
            ["Traitement", "Dose actuelle", "Statut", "Dernière date"],
            rows,
        )
    return "### Médicaments — historique sur la période\n\n" + _md_table(
        ["Traitement", "Date", "Dose", "Événement", "Note"],
        rows,
    )


def _section_rapports(start: date, end: date, compact: bool) -> str:
    rows: list[list[str]] = []
    extras: list[str] = []
    if config.RAPPORTS_DIR.exists():
        files = sorted(
            (p for p in config.RAPPORTS_DIR.glob("*.md") if p.name.lower() != "readme.md"),
            reverse=True,
        )
        for path in files:
            day = parse_day(path.name[:10])
            if not _in_period(day, start, end):
                continue
            raw = _read_text(path)
            title = path.stem
            m = re.search(r"^#\s+(.+)", raw, re.MULTILINE)
            if m:
                title = m.group(1).strip()
            rows.append([_fmt(day), title, f"`{path.name}`"])
            if not compact:
                excerpt = []
                for line in raw.splitlines():
                    t = line.strip()
                    if t.startswith(">") and len(t) > 3:
                        excerpt.append(t.lstrip("> ").strip())
                        break
                if excerpt:
                    extras.append(f"- **{title}** : {excerpt[0]}")
    body = "### Rapports personnels\n\n" + _md_table(["Date", "Titre", "Fichier"], rows)
    if extras:
        body += "\n" + "\n".join(extras[:12]) + "\n"
    return body


def _section_pdfs(kind: str, start: date, end: date) -> str:
    items = _list_pdfs(kind)
    rows = []
    for item in items:
        day = parse_day(str(item.get("date") or "")[:10])
        if not _in_period(day, start, end):
            continue
        if kind == "labs":
            rows.append([_fmt(day), str(item.get("lab") or ""), str(item.get("filename") or "")])
        else:
            rows.append(
                [
                    _fmt(day),
                    str(item.get("prescriber") or ""),
                    str(item.get("kind") or ""),
                    str(item.get("filename") or ""),
                ]
            )
    if kind == "labs":
        return "### Prises de sang\n\n" + _md_table(["Date", "Laboratoire", "Fichier"], rows)
    return "### Ordonnances\n\n" + _md_table(["Date", "Prescripteur", "Type", "Fichier"], rows)


def _csv_points(
    path: Path,
    date_key: str,
    value_key: str,
    start: date,
    end: date,
    *,
    analyte: str | None = None,
) -> list[tuple[datetime, float, str]]:
    if not path.exists():
        return []
    out: list[tuple[datetime, float, str]] = []
    with path.open(encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if analyte and (row.get("analyte") or "").strip().upper() != analyte.upper():
                continue
            day = parse_day(row.get(date_key))
            if not _in_period(day, start, end):
                continue
            try:
                value = float(str(row.get(value_key) or "").replace(",", "."))
            except ValueError:
                continue
            out.append((datetime(day.year, day.month, day.day), value, _fmt(day)))
    out.sort(key=lambda p: p[0])
    return out


def _section_labs(start: date, end: date, fig_rel: str | None) -> str:
    cfg = labs_config()
    analyte = str(cfg.get("primaryAnalyte") or "")
    title = str(cfg.get("title") or "Suivi biologique")
    unit = str(cfg.get("markerUnit") or "")
    points = _csv_points(config.LABS_CSV, "date", "value", start, end, analyte=analyte)
    rows = [[p[2], f"{p[1]} {unit}".strip(), analyte] for p in points]
    body = f"### {title}\n\n" + _md_table(["Date", "Valeur", "Marqueur"], rows)
    if fig_rel:
        body += f"\n![{title}]({fig_rel})\n"
    return body


def _treatment_dose_points(needle: str, start: date, end: date) -> list[tuple[datetime, float, str]]:
    data = _read_json(config.TRAITEMENTS_PATH) or {}
    needle_l = needle.lower()
    out: list[tuple[datetime, float, str]] = []
    for t in data.get("traitements") or []:
        if needle_l and needle_l not in str(t.get("nom") or "").lower():
            continue
        for h in t.get("historique") or []:
            day = parse_day(h.get("date"))
            if not _in_period(day, start, end):
                continue
            m = re.search(r"[\d.,]+", str(h.get("dose") or ""))
            if not m:
                continue
            try:
                value = float(m.group(0).replace(",", "."))
            except ValueError:
                continue
            out.append((datetime(day.year, day.month, day.day), value, _fmt(day)))
    out.sort(key=lambda p: p[0])
    return out


def _section_med_series(start: date, end: date, fig_rel: str | None) -> str:
    cfg = medication_config()
    title = str(cfg.get("title") or "Suivi de posologie")
    unit = str(cfg.get("doseUnit") or "")
    needle = str(cfg.get("treatmentNameIncludes") or "")
    points = _treatment_dose_points(needle, start, end)
    rows = [[p[2], f"{p[1]} {unit}".strip()] for p in points]
    body = f"### {title}\n\n" + _md_table(["Date", "Dose"], rows)
    if fig_rel:
        body += f"\n![{title}]({fig_rel})\n"
    return body


def build_charts(
    include: set[str],
    start: date,
    end: date,
    fig_dir: Path,
) -> dict[str, str]:
    rels: dict[str, str] = {}
    stem = fig_dir.name
    if "poids" in include:
        pts = [(d, v) for d, v, _ in _csv_points(config.POIDS_CSV, "date", "poids_kg", start, end)]
        path = plot_line(pts, fig_dir / "poids.png", title="Poids", ylabel="kg")
        if path:
            rels["poids"] = f"figures/{stem}/poids.png"
    if "labs" in include:
        cfg = labs_config()
        analyte = str(cfg.get("primaryAnalyte") or "")
        pts = [
            (d, v)
            for d, v, _ in _csv_points(config.LABS_CSV, "date", "value", start, end, analyte=analyte)
        ]
        ref_low = cfg.get("refLow")
        ref_high = cfg.get("refHigh")
        path = plot_line(
            pts,
            fig_dir / "labs.png",
            title=str(cfg.get("title") or "Suivi biologique"),
            ylabel=str(cfg.get("markerUnit") or ""),
            color="#3B82F6",
            ref_low=float(ref_low) if ref_low is not None else None,
            ref_high=float(ref_high) if ref_high is not None else None,
        )
        if path:
            rels["labs"] = f"figures/{stem}/labs.png"
    if "medication_series" in include:
        cfg = medication_config()
        pts = [
            (d, v)
            for d, v, _ in _treatment_dose_points(
                str(cfg.get("treatmentNameIncludes") or ""), start, end
            )
        ]
        path = plot_step_dose(
            pts,
            fig_dir / "posologie.png",
            title=str(cfg.get("title") or "Posologie"),
            ylabel=str(cfg.get("doseUnit") or ""),
        )
        if path:
            rels["medication_series"] = f"figures/{stem}/posologie.png"
    return rels


def build_factual(
    doctor: dict,
    include: set[str],
    start: date,
    end: date,
    size: str,
    figures: dict[str, str],
) -> str:
    compact = size == "petit"
    parts: list[str] = []
    if "agenda" in include:
        parts.append(_section_agenda(_filter_events(matched_events(doctor), start, end)))
    if "medicaments" in include:
        parts.append(_section_treatments(start, end, compact))
    if "rapports" in include:
        parts.append(_section_rapports(start, end, compact))
    if "ordonnances" in include:
        parts.append(_section_pdfs("ord", start, end))
    if "prise_de_sang" in include:
        parts.append(_section_pdfs("labs", start, end))
    if "poids" in include:
        parts.append(_section_poids(start, end, figures.get("poids")))
    if "labs" in include:
        parts.append(_section_labs(start, end, figures.get("labs")))
    if "medication_series" in include:
        parts.append(_section_med_series(start, end, figures.get("medication_series")))
    return "\n\n".join(p for p in parts if p.strip())


def fallback_narrative(doctor: dict, start: date, end: date, size: str) -> str:
    name = doctor_full_name(doctor)
    spec = str(doctor.get("specialite") or "")
    title = f"Dossier de suivi — {name}"
    tag = f"généré pour {name}"
    resume = (
        f"Synthèse de suivi destinée à {name} ({spec}), "
        f"couvrant la période du {_fmt(start)} au {_fmt(end)}."
    )
    points = (
        "- Reprendre les données chiffrées de la section suivante.\n"
        "- Croiser avec l’examen clinique du jour."
        if size == "petit"
        else (
            "- Reprendre l’évolution des traitements et des mesures sur la période.\n"
            "- Pointer les écarts de dates entre rendez-vous et examens.\n"
            "- Conserver ce dossier comme base de discussion, pas comme avis médical."
        )
    )
    return (
        f"# {title}\n\n"
        "| | |\n|---|---|\n"
        f"| **Date de rédaction** | {date.today().strftime(_FR)} |\n"
        f"| **Période concernée** | {_fmt(start)} → {_fmt(end)} |\n"
        f"| **Destinataires** | {name} ({spec}) |\n"
        f"| **Thèmes** | {tag} |\n"
        "| **Lien diagnostic** | *À préciser avec le clinicien* |\n\n"
        f"> {resume}\n\n"
        "---\n\n"
        "## Objectif\n\n"
        f"Préparer la consultation avec {name} à partir des données du dossier personnel.\n\n"
        "## Points utiles pour le suivi\n\n"
        f"{points}\n"
    )


async def write_doctor_report(
    *,
    doctor_id: str,
    size: str,
    date_from: str,
    date_to: str,
    include: list[str],
) -> tuple[str, str]:
    """Retourne (markdown, filename sans .md)."""
    from api.routers.reports import call_ai

    doctor = find_doctor(doctor_id)
    if not doctor:
        raise KeyError(doctor_id)
    start = parse_day(date_from)
    end = parse_day(date_to)
    if not start or not end:
        raise ValueError("Période invalide")
    if end < start:
        start, end = end, start
    size = "grand" if size == "grand" else "petit"
    chosen = {k for k in include if k in INCLUDE_KEYS} or set(INCLUDE_KEYS)

    name = doctor_full_name(doctor)
    spec = str(doctor.get("specialite") or "")
    tag = f"généré pour {name}"
    from api.deps import slugify

    stem = f"{date.today().isoformat()}-dossier-{slugify(name) or 'praticien'}"
    fig_dir = config.RAPPORTS_DIR / "figures" / stem
    figures = build_charts(chosen, start, end, fig_dir)
    factual = build_factual(doctor, chosen, start, end, size, figures)

    source = (
        f"Destinataire : {name} ({spec})\n"
        f"Tag obligatoire dans Thèmes : {tag}\n"
        f"Taille : {size}\n"
        f"Période : {_fmt(start)} → {_fmt(end)}\n\n"
        f"{factual}"
    )
    length_rule = (
        "Rapport COURT : résumé de 6–12 lignes, objectif en 1 paragraphe, "
        "5 points utiles maximum. Pas de tableaux (ils seront ajoutés après)."
        if size == "petit"
        else "Rapport COMPLET : objectif, description, chronologie, contexte, "
        "impact, points utiles. Pas de tableaux bruts (ils seront ajoutés après)."
    )
    try:
        narrative = await call_ai(
            "Rédige un dossier de synthèse pour un clinicien à partir des données ci-dessous.\n"
            f"{length_rule}\n"
            f"- Destinataires = {name} ({spec})\n"
            f"- Thèmes DOIT contenir exactement « {tag} » (tu peux ajouter d'autres thèmes).\n"
            "- Ne pas inventer de valeurs absentes des données.\n"
            "- Première personne du patient si tu décris le vécu.\n\n"
            f"{source}"
        )
    except Exception:
        narrative = ""

    if not (narrative or "").strip().startswith("#"):
        narrative = fallback_narrative(doctor, start, end, size)

    markdown = narrative.strip() + "\n\n---\n\n## Données de la période\n\n" + factual
    filename = f"{stem}.md"
    dest = config.RAPPORTS_DIR / filename
    dest.write_text(markdown, encoding="utf-8")
    return markdown, stem
