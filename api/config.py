"""Configuration et chemins du vault Asclepios."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent

# Fichier d'env : .env (dev) ou .env.prod (prod). Surchargeable avant import.
ASCLEPIOS_ENV_FILE = os.getenv("ASCLEPIOS_ENV_FILE", ".env").strip() or ".env"
load_dotenv(dotenv_path=ROOT / ASCLEPIOS_ENV_FILE)

VAULT_DIR = ROOT / os.getenv("LOCAL_DATA_DIR", "vault")
SCRIPTS_DIR = VAULT_DIR / "scripts"
PROJECT_SCRIPTS_DIR = ROOT / "scripts"

_VENV_PYTHON = ROOT / ".venv" / "bin" / "python"
PYTHON = str(_VENV_PYTHON) if _VENV_PYTHON.exists() else sys.executable

SCRIPT_DOCS = SCRIPTS_DIR / "rapport_personnels.py"
SCRIPT_WEIGHT = SCRIPTS_DIR / "rapport_poids.py"
SCRIPT_BIO = SCRIPTS_DIR / "rapport_biologie.py"
SCRIPT_BIO2 = SCRIPTS_DIR / "rapport_biologie_dose.py"
SCRIPT_RX = SCRIPTS_DIR / "rapport_medicaments.py"
SCRIPT_SYNC = PROJECT_SCRIPTS_DIR / "sync.py"
SCRIPT_PARSE_LAB = SCRIPTS_DIR / "parse_lab_pdf.py"
SCRIPT_PARSE_ORD = SCRIPTS_DIR / "parse_ordonnance_pdf.py"

IDENTITE_DIR = VAULT_DIR / "identite"
PROFIL_PATH = IDENTITE_DIR / "profil.json"
PHOTO_PATH = IDENTITE_DIR / "profil.png"
SIGNATURE_PATH = IDENTITE_DIR / "signature.png"

MUTUELLE_DIR = VAULT_DIR / "mutuelle"
ASSISTANT_DIR = VAULT_DIR / "assistant"
PERSONALITY_PATH = ASSISTANT_DIR / "personality.md"
RAPPORT_TEMPLATE_PATH = ASSISTANT_DIR / "rapport-template.md"

SUIVI_DIR = VAULT_DIR / "suivi"
POIDS_CSV = SUIVI_DIR / "poids.csv"
LABS_CSV = SUIVI_DIR / "labs.csv"
TRAITEMENTS_PATH = SUIVI_DIR / "traitements.json"
LABS_CONFIG_PATH = SUIVI_DIR / "labs-config.json"
MEDICATION_CONFIG_PATH = SUIVI_DIR / "medication-config.json"

MEDECINS_DIR = VAULT_DIR / "humains" / "medecins"
DOCTORS_PATH = MEDECINS_DIR / "doctors.json"
PHOTOS_DIR = VAULT_DIR / "humains" / "photos"
MEDECINS_PHOTOS_DIR = PHOTOS_DIR

MEDICAMENTS_DIR = VAULT_DIR / "medicaments"
ORDONNANCES_DIR = VAULT_DIR / "ordonnances"
HUMAINS_DIR = VAULT_DIR / "humains"
PERSONNES_DIR = HUMAINS_DIR / "personnes"
RELATIONS_DIR = HUMAINS_DIR / "relations"
RAPPORTS_DIR = VAULT_DIR / "rapports"
RECITS_DIR = VAULT_DIR / "recits"
PDS_DIR = VAULT_DIR / "prise-de-sang"
CHATS_DIR = ASSISTANT_DIR / "chats"
FONTS_DIR = VAULT_DIR / "fonts"
CACHE_DIR = VAULT_DIR / "cache"
AGENDA_CACHE_PATH = CACHE_DIR / "agenda.json"

SSE_HEADERS = {"Cache-Control": "no-cache", "X-Accel-Buffering": "no"}
APP_VERSION = "0.1.0"
AI_MODEL = "gemini-3.7-flash"

# Auth mono-utilisateur + TOTP
ASCLEPIOS_ENV = os.getenv("ASCLEPIOS_ENV", "development").strip().lower()
AUTH_PASSWORD_HASH = os.getenv("AUTH_PASSWORD_HASH", "").strip().strip("'").strip('"')
AUTH_TOTP_SECRET = os.getenv("AUTH_TOTP_SECRET", "").strip().strip("'").strip('"')
AUTH_TOTP_ISSUER = os.getenv("AUTH_TOTP_ISSUER", "Asclepios").strip() or "Asclepios"
SESSION_SECRET = os.getenv("SESSION_SECRET", "").strip().strip("'").strip('"')
SESSION_MAX_AGE = int(os.getenv("SESSION_MAX_AGE", str(60 * 60 * 24 * 14)))  # 14 jours
PREAUTH_MAX_AGE = int(os.getenv("PREAUTH_MAX_AGE", "300"))  # 5 min
CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if o.strip()
]


def totp_account_name() -> str:
    label = "Prod" if ASCLEPIOS_ENV == "production" else "Dev"
    return f"{AUTH_TOTP_ISSUER} {label}"


def auth_is_configured() -> bool:
    return bool(AUTH_PASSWORD_HASH and AUTH_TOTP_SECRET and SESSION_SECRET)
