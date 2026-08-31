"""Construit un contexte textuel à partir du dossier médical local (data/)."""

from __future__ import annotations

import json
from pathlib import Path

# Budget total approximatif pour le prompt (caractères)
_MAX_TOTAL = 140_000
_MAX_PER_REPORT = 6_000


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


def build_medical_context(data_dir: Path) -> str:
    """Agrège profil, poids, labs, traitements, médecins, fiches et rapports."""
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
    profil = _read_json(data_dir / "profil.json")
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
    notice_path = data_dir / (notice_name or "henner-notice-complementaire-sante.md")
    notice = _read_text(notice_path)
    if notice.strip():
        add("Notice mutuelle (garanties)", _truncate(notice, 25_000))

    # Poids
    poids = _read_text(data_dir / "poids.csv")
    if poids.strip():
        add("Poids (CSV)", poids)

    # Labs
    labs_cfg = _read_json(data_dir / "labs-config.json")
    if labs_cfg:
        add("Config analyses", json.dumps(labs_cfg, ensure_ascii=False, indent=2))
    labs = _read_text(data_dir / "labs.csv")
    if labs.strip():
        add("Analyses labo (CSV)", labs)

    # Traitements
    med_cfg = _read_json(data_dir / "medication-config.json")
    if med_cfg:
        add("Config posologie suivie", json.dumps(med_cfg, ensure_ascii=False, indent=2))
    traitements = _read_json(data_dir / "traitements.json")
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
    doctors = _read_json(data_dir / "doctors.json")
    if doctors:
        add("Médecins", json.dumps(doctors, ensure_ascii=False, indent=2))

    # Dossiers relations passées (contexte affectif / patterns)
    rel_dir = data_dir / "relations"
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
    personnes_dir = data_dir / "personnes"
    if personnes_dir.is_dir():
        # Inventaire des photos (pour que l'IA sache qu'elles existent et où)
        photo_lines: list[str] = []
        for ext in ("*.jpg", "*.jpeg", "*.png", "*.webp"):
            for path in sorted(personnes_dir.glob(ext)):
                photo_lines.append(
                    f"- `{path.relative_to(data_dir).as_posix()}` "
                    f"(ouvrir ce fichier pour voir / confirmer l'apparence)"
                )
        if photo_lines:
            add(
                "Photos famille / entourage / animaux",
                "Fichiers images disponibles dans data/personnes/. "
                "Les descriptions physiques sont aussi dans la section « Apparence » "
                "de chaque dossier .md ci-dessous.\n\n"
                + "\n".join(photo_lines),
            )

        personnes_blocks = []
        for path in sorted(personnes_dir.glob("*.md")):
            if path.name.lower() == "readme.md":
                continue
            raw = _read_text(path)
            if not raw.strip():
                continue
            personnes_blocks.append(f"### {path.stem}\n\n{_truncate(raw, 5_000)}")
        if personnes_blocks:
            add("Dossiers famille, entourage & animaux", "\n\n---\n\n".join(personnes_blocks))

    # Rapports + traumas (plus récents d'abord)
    doc_blocks: list[str] = []
    for folder in ("rapports", "traumas"):
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
