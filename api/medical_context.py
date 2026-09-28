"""Construit un contexte textuel à partir du vault médical local (vault/)."""

from __future__ import annotations

import json
import re
from pathlib import Path

# Budget total approximatif pour le prompt (caractères)
_MAX_TOTAL = 140_000
_MAX_PER_REPORT = 6_000

EMOTION_LABELS = {
    "joie": "joie",
    "tristesse": "tristesse",
    "anxiete": "anxiété",
    "colere": "colère",
    "calme": "calme",
    "espoir": "espoir",
    "fatigue": "fatigue",
    "soulagement": "soulagement",
}


def _read_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def _read_json(path: Path):
    raw = _read_text(path)
    if not raw.strip():
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def _section(title: str, body: str) -> str:
    body = body.strip()
    if not body:
        return ""
    return f"\n## {title}\n\n{body}\n"


def _truncate(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[: limit - 40].rstrip() + "\n\n[… truncature …]"


def format_humeur(data_dir: Path) -> str:
    raw = _read_text(data_dir / "suivi" / "humeur.csv")
    if not raw.strip():
        return ""
    return (
        "Échelle 0 (au plus bas) à 10 (super bien). "
        "Plusieurs notes possibles par jour, horodatées Europe/Paris.\n\n"
        + raw.strip()
    )


def format_sport(data_dir: Path) -> str:
    blocks: list[str] = []
    program = _read_json(data_dir / "suivi" / "sport.json")
    exercises = program.get("exercises") if isinstance(program, dict) else None
    if exercises:
        blocks.append(
            "Programme :\n" + json.dumps(program, ensure_ascii=False, indent=2)
        )
    log = _read_json(data_dir / "suivi" / "sport-log.json")
    sessions = log.get("sessions") if isinstance(log, dict) else None
    if sessions:
        blocks.append(
            "Séances (fait / pas fait) :\n"
            + json.dumps(log, ensure_ascii=False, indent=2)
        )
    return "\n\n".join(blocks)


def format_report_emotions(data_dir: Path) -> str:
    data = _read_json(data_dir / "rapports" / "emotions.json")
    if not isinstance(data, dict) or not data:
        return ""
    lines: list[str] = [
        "Ressenti associé à chaque rapport personnel "
        "(choisi par l'utilisateur après lecture, pas un diagnostic) :"
    ]
    for report_id, ids in data.items():
        if not isinstance(report_id, str):
            continue
        raw_ids = ids
        if isinstance(ids, dict):
            raw_ids = ids.get("emotions") or ids.get("ids")
        if not isinstance(raw_ids, list):
            continue
        labels = [
            EMOTION_LABELS.get(str(e), str(e))
            for e in raw_ids
            if str(e) in EMOTION_LABELS
        ]
        if not labels:
            continue
        title = report_id
        md = data_dir / "rapports" / f"{report_id}.md"
        if md.is_file():
            m = re.search(r"^#\s+(.+)", _read_text(md), re.MULTILINE)
            if m:
                title = m.group(1).strip()
        day = report_id[:10] if re.match(r"^\d{4}-\d{2}-\d{2}", report_id) else ""
        prefix = f"{day} — " if day else ""
        lines.append(f"- {prefix}{title} : {', '.join(labels)}")
    if len(lines) < 2:
        return ""
    return "\n".join(lines)


def build_suivi_context(data_dir: Path) -> str:
    """Humeur, sport et émotions des rapports — bloc compact pour l'IA."""
    parts: list[str] = []
    humeur = format_humeur(data_dir)
    if humeur:
        parts.append(_section("Humeur (0–10, horodatée)", humeur))
    sport = format_sport(data_dir)
    if sport:
        parts.append(_section("Sport (programme et séances)", sport))
    emotions = format_report_emotions(data_dir)
    if emotions:
        parts.append(_section("Émotions des rapports", emotions))
    return "".join(parts)


def build_medical_context(data_dir: Path) -> str:
    """Agrège profil, poids, humeur, sport, labs, traitements, médecins, fiches et rapports."""
    parts: list[str] = []
    budget = _MAX_TOTAL

    def add(title: str, body: str) -> None:
        nonlocal budget
        if budget <= 0 or not body.strip():
            return
        chunk = _section(title, body)
        if len(chunk) > budget:
            chunk = _section(title, _truncate(body, max(200, budget - 80)))
        parts.append(chunk)
        budget -= len(chunk)

    # Profil
    profil = _read_json(data_dir / "identite" / "profil.json")
    if profil:
        add(
            "Profil patient",
            json.dumps(profil, ensure_ascii=False, indent=2),
        )

    # Notice mutuelle (garanties)
    notice_name = ""
    if isinstance(profil, dict):
        mut = profil.get("mutuelle") or {}
        if isinstance(mut, dict):
            notice_name = str(mut.get("notice_md") or "").strip()
    notice_path = data_dir / (
        notice_name or "mutuelle/henner-notice-complementaire-sante.md"
    )
    notice = _read_text(notice_path)
    if notice.strip():
        add("Notice mutuelle (garanties)", _truncate(notice, 25_000))

    # Poids
    poids = _read_text(data_dir / "suivi" / "poids.csv")
    if poids.strip():
        add("Poids (CSV)", poids)

    suivi = build_suivi_context(data_dir)
    if suivi.strip() and budget > 0:
        chunk = suivi if len(suivi) <= budget else suivi[: max(200, budget - 40)] + "\n\n[… truncature …]\n"
        parts.append(chunk)
        budget -= len(chunk)

    # Labs
    labs_cfg = _read_json(data_dir / "suivi" / "labs-config.json")
    if labs_cfg:
        add("Config analyses", json.dumps(labs_cfg, ensure_ascii=False, indent=2))
    labs = _read_text(data_dir / "suivi" / "labs.csv")
    if labs.strip():
        add("Analyses labo (CSV)", labs)

    # Traitements
    med_cfg = _read_json(data_dir / "suivi" / "medication-config.json")
    if med_cfg:
        add("Config posologie suivie", json.dumps(med_cfg, ensure_ascii=False, indent=2))
    traitements = _read_json(data_dir / "suivi" / "traitements.json")
    if traitements:
        add("Traitements & historique de doses", json.dumps(traitements, ensure_ascii=False, indent=2))

    # Fiches médicaments
    meds_dir = data_dir / "medicaments"
    if meds_dir.is_dir():
        med_blocks = []
        for path in sorted(meds_dir.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            med_blocks.append(f"### {path.stem}\n\n{_truncate(_read_text(path), 4_000)}")
        if med_blocks:
            add("Fiches médicaments", "\n\n".join(med_blocks))

    # Médecins
    doctors = _read_json(data_dir / "humains" / "medecins" / "doctors.json")
    if doctors:
        add("Médecins", json.dumps(doctors, ensure_ascii=False, indent=2))

    # Agenda médical (snapshot du flux iCal — pas d'appel réseau ici)
    try:
        try:
            from api.agenda import format_for_ai
        except ModuleNotFoundError:
            from agenda import format_for_ai

        agenda_text = format_for_ai(data_dir)
        if agenda_text.strip():
            add("Agenda médical (rendez-vous)", _truncate(agenda_text, 8_000))
    except Exception:
        pass  # l'agenda est facultatif : ne jamais casser le contexte

    # Dossiers relations passées (contexte affectif / patterns)
    rel_dir = data_dir / "humains" / "relations"
    if rel_dir.is_dir():
        rel_blocks = []
        for path in sorted(rel_dir.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            raw = _read_text(path)
            if not raw.strip():
                continue
            rel_blocks.append(f"### {path.stem}\n\n{_truncate(raw, 5_000)}")
        if rel_blocks:
            add("Dossiers relations passées", "\n\n---\n\n".join(rel_blocks))

    # Dossiers famille, entourage & animaux
    personnes_dir = data_dir / "humains" / "personnes"
    photos_dir = data_dir / "humains" / "photos"
    if personnes_dir.is_dir() or photos_dir.is_dir():
        photo_lines: list[str] = []
        if photos_dir.is_dir():
            for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
                for path in sorted(photos_dir.glob(ext)):
                    photo_lines.append(
                        f"- `{path.relative_to(data_dir).as_posix()}` "
                        f"(ouvrir ce fichier pour voir / confirmer l'apparence)"
                    )
        if photo_lines:
            add(
                "Photos famille / entourage / animaux / médecins",
                "Fichiers images disponibles dans vault/humains/photos/. "
                "Les descriptions physiques sont aussi dans la section « Apparence » "
                "de chaque dossier .md ci-dessous.\n\n"
                + "\n".join(photo_lines),
            )

        personnes_blocks = []
        if personnes_dir.is_dir():
            for path in sorted(personnes_dir.glob("*.md")):
                if path.name.lower() == "readme.md":
                    continue
                raw = _read_text(path)
                if not raw.strip():
                    continue
                personnes_blocks.append(f"### {path.stem}\n\n{_truncate(raw, 5_000)}")
        if personnes_blocks:
            add("Dossiers famille, entourage & animaux", "\n\n---\n\n".join(personnes_blocks))

    # Rapports + récits (plus récents d'abord)
    doc_blocks: list[str] = []
    for folder in ("rapports", "recits"):
        d = data_dir / folder
        if not d.is_dir():
            continue
        files = sorted(
            (p for p in d.glob("*.md") if p.name.lower() != "readme.md"),
            key=lambda p: p.name,
            reverse=True,
        )
        for path in files:
            raw = _read_text(path)
            if not raw.strip():
                continue
            doc_blocks.append(
                f"### [{folder}] {path.name}\n\n{_truncate(raw, _MAX_PER_REPORT)}"
            )

    if doc_blocks:
        # Remplir jusqu'au budget restant
        packed: list[str] = []
        used = 0
        for block in doc_blocks:
            if used + len(block) + 4 > budget:
                # Essayer une version plus courte
                short = _truncate(block, max(300, budget - used - 40))
                if len(short) < 80:
                    break
                packed.append(short)
                used += len(short)
                break
            packed.append(block)
            used += len(block) + 4
        add("Rapports et notes", "\n\n---\n\n".join(packed))

    header = (
        "CONTEXTE DOSSIER MÉDICAL PERSONNEL ASCLEPIOS\n"
        "Les données ci-dessous sont la source de vérité. "
        "Base toujours tes réponses sur ce contexte.\n"
    )
    return header + "".join(parts)
