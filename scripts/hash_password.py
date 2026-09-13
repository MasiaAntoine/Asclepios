#!/usr/bin/env python3
"""Hash un mot de passe pour AUTH_PASSWORD_HASH dans .env.

Usage :
  docker compose exec -it api python scripts/hash_password.py
  # ou, en local (pip install argon2-cffi) :
  python scripts/hash_password.py
  python scripts/hash_password.py --password 'mon-mot-de-passe'
"""

from __future__ import annotations

import argparse
import secrets
import sys
from getpass import getpass


def main() -> None:
    parser = argparse.ArgumentParser(description="Hash mot de passe Asclepios (Argon2id)")
    parser.add_argument("--password", help="Mot de passe (sinon saisie interactive)")
    args = parser.parse_args()

    password = args.password or getpass("Mot de passe Asclepios : ")
    if not password:
        sys.exit("Mot de passe vide")
    if not args.password:
        confirm = getpass("Confirmer : ")
        if password != confirm:
            sys.exit("Les mots de passe ne correspondent pas")

    try:
        from argon2 import PasswordHasher
    except ImportError:
        sys.exit(
            "Module argon2 manquant.\n"
            "  → docker compose exec -it api python scripts/hash_password.py\n"
            "  → ou : pip install argon2-cffi"
        )

    password_hash = PasswordHasher().hash(password)
    session_secret = secrets.token_urlsafe(48)

    print()
    print("Colle dans ton .env :")
    print()
    print(f"AUTH_PASSWORD_HASH='{password_hash}'")
    print(f"SESSION_SECRET={session_secret}")
    print()
    print("Puis : docker compose restart api")
    print()


if __name__ == "__main__":
    main()
