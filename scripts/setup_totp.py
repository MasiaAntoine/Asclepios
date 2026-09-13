#!/usr/bin/env python3
"""Génère AUTH_TOTP_SECRET + QR pour Google Authenticator.

Usage :
  docker compose exec -it api python scripts/setup_totp.py --env development
  docker compose exec -it api python scripts/setup_totp.py --env production
"""

from __future__ import annotations

import argparse
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Setup TOTP Asclepios (Google Authenticator)")
    parser.add_argument(
        "--env",
        choices=("development", "production"),
        default="development",
        help="Label Authenticator : Asclepios Dev ou Asclepios Prod",
    )
    parser.add_argument(
        "--issuer",
        default="Asclepios",
        help="Nom de l'émetteur dans Authenticator",
    )
    args = parser.parse_args()

    try:
        import pyotp
        import qrcode
    except ImportError:
        sys.exit(
            "Modules manquants (pyotp, qrcode).\n"
            "  → docker compose exec -it api python scripts/setup_totp.py --env development\n"
            "  → ou : pip install pyotp qrcode"
        )

    secret = pyotp.random_base32()
    label = "Prod" if args.env == "production" else "Dev"
    account = f"{args.issuer} {label}"
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=account, issuer_name=args.issuer)

    qr = qrcode.QRCode(border=1)
    qr.add_data(uri)
    qr.make(fit=True)

    print()
    print(f"Compte Authenticator : {account}")
    print()
    print("Scanne ce QR avec Google Authenticator :")
    print()
    qr.print_ascii(invert=True)
    print()
    print("URI (si le QR ne s'affiche pas) :")
    print(uri)
    print()
    target = ".env.prod" if args.env == "production" else ".env"
    print(f"Colle dans ton {target} :")
    print()
    print(f"ASCLEPIOS_ENV={'production' if args.env == 'production' else 'development'}")
    print(f"AUTH_TOTP_SECRET={secret}")
    print(f"AUTH_TOTP_ISSUER={args.issuer}")
    print()
    print("Puis : docker compose restart api")
    print()


if __name__ == "__main__":
    main()
