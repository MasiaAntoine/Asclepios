"""Association heuristique rendez-vous agenda ↔ médecin du vault."""

from __future__ import annotations

import unicodedata
from datetime import date, timedelta
from typing import Any

_TYPOS = (
    ("psyciatre", "psychiatre"),
    ("endrocrinologue", "endocrinologue"),
    ("endrocrino", "endocrino"),
)


def _fold(value: str) -> str:
    text = unicodedata.normalize("NFKD", value or "")
    text = "".join(c for c in text if not unicodedata.combining(c))
    return text.lower()


def normalize(value: str) -> str:
    text = _fold(value)
    for src, dst in _TYPOS:
        text = text.replace(src, dst)
    return text


def _is_former(doctor: dict) -> bool:
    role = normalize(str(doctor.get("role") or ""))
    return "ancien" in role


def specialty_keys(specialite: str) -> list[str]:
    n = normalize(specialite)
    keys: list[str] = []
    if "psychiatr" in n:
        keys.append("psychiatr")
    if "psycholog" in n:
        keys.append("psycholog")
    if "endocrin" in n:
        keys.append("endocrin")
    if "generaliste" in n or n.startswith("medecin general"):
        keys.extend(["generaliste", "medecin traitant"])
    if "hypno" in n or "psychopratic" in n:
        keys.extend(["hypno", "psychopratic"])
    return keys


def _haystack(event: dict) -> str:
    return normalize(
        " ".join(
            str(event.get(k) or "")
            for k in ("title", "location", "description")
        )
    )


def name_or_address_match(event: dict, doctor: dict) -> bool:
    hay = _haystack(event)
    nom = normalize(str(doctor.get("nom") or ""))
    prenom = normalize(str(doctor.get("prenom") or ""))
    if len(nom) >= 3 and nom in hay:
        return True
    if len(prenom) >= 4 and prenom in hay and nom and nom in hay:
        return True
    adresse = doctor.get("adresse") or {}
    voie = normalize(str(adresse.get("voie") or ""))
    voie = " ".join(voie.split()[1:]) if voie[:1].isdigit() else voie
    if len(voie) >= 10 and voie[:18] in hay:
        return True
    return False


def event_matches_doctor(event: dict, doctor: dict) -> bool:
    if name_or_address_match(event, doctor):
        return True
    hay = _haystack(event)
    return any(key in hay for key in specialty_keys(str(doctor.get("specialite") or "")))


def events_for_doctor(
    events: list[dict],
    doctor: dict,
    all_doctors: list[dict],
) -> list[dict]:
    peers = [
        d
        for d in all_doctors
        if d.get("id") != doctor.get("id")
        and set(specialty_keys(str(d.get("specialite") or "")))
        & set(specialty_keys(str(doctor.get("specialite") or "")))
    ]
    out: list[dict] = []
    for event in events:
        if not event_matches_doctor(event, doctor):
            continue
        stolen = any(
            name_or_address_match(event, peer) and not name_or_address_match(event, doctor)
            for peer in peers
        )
        if stolen:
            continue
        if _is_former(doctor) and not name_or_address_match(event, doctor):
            continue
        out.append(event)
    out.sort(key=lambda e: str(e.get("start") or ""))
    return out


def suggest_period(events: list[dict], today: date | None = None) -> dict[str, Any]:
    """Propose la tranche dernier RDV → prochain RDV (modifiable ensuite)."""
    today = today or date.today()
    today_key = today.isoformat()

    def day(ev: dict) -> str:
        return str(ev.get("start") or "")[:10]

    past = [e for e in events if day(e) and day(e) < today_key]
    future = [e for e in events if day(e) and day(e) >= today_key]
    last_visit = past[-1] if past else None
    next_visit = future[0] if future else None

    three_months = (today - timedelta(days=90)).isoformat()
    reason = "Aucun rendez-vous identifié : 3 derniers mois."
    date_from = three_months
    date_to = today_key

    if last_visit and next_visit:
        date_from = day(last_visit)
        date_to = day(next_visit)
        reason = "Dernier rendez-vous → prochain rendez-vous."
    elif last_visit:
        date_from = day(last_visit)
        date_to = today_key
        reason = "Depuis le dernier rendez-vous jusqu’à aujourd’hui."
    elif next_visit:
        date_from = three_months
        date_to = day(next_visit)
        reason = "3 derniers mois jusqu’au prochain rendez-vous."

    return {
        "date_from": date_from,
        "date_to": date_to,
        "last_visit": last_visit,
        "next_visit": next_visit,
        "reason": reason,
    }
