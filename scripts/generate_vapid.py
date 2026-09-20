#!/usr/bin/env python3
"""Génère une paire de clés VAPID pour le Web Push.

Usage :
  docker compose exec -it api python scripts/generate_vapid.py

Ne régénère pas si des appareils sont déjà abonnés : tous les anciens
abonnements mourraient.
"""

from __future__ import annotations

import base64
import sys

from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat


def b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def main() -> None:
    private_key = ec.generate_private_key(ec.SECP256R1())
    priv_raw = private_key.private_numbers().private_value.to_bytes(32, "big")
    pub_raw = private_key.public_key().public_bytes(
        encoding=Encoding.X962,
        format=PublicFormat.UncompressedPoint,
    )
    print("Ajoute ces lignes dans .env (et .env.prod) :", file=sys.stderr)
    print()
    print(f"VAPID_PUBLIC_KEY={b64url(pub_raw)}")
    print(f"VAPID_PRIVATE_KEY={b64url(priv_raw)}")
    print("VAPID_SUBJECT=https://asclepios.masia-antoine.fr")
    print()
    print(
        "Sujet RFC-valide obligatoire pour iOS "
        "(https://… ou mailto:contact@domaine.fr, jamais @local).",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
