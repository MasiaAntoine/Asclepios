"""Authentification mono-utilisateur (mot de passe + TOTP + cookie de session)."""

from __future__ import annotations

import os
import secrets
import time
from collections import defaultdict
from threading import Lock
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from api import config

COOKIE_NAME = "asclepios_session"
PREAUTH_COOKIE_NAME = "asclepios_preauth"
SESSION_SUBJECT = "owner"
PREAUTH_STAGE = "totp"

# Anti-bruteforce (mémoire processus) — login + totp
_MAX_ATTEMPTS = 5
_WINDOW_SECONDS = 300
_attempts: dict[str, list[float]] = defaultdict(list)
_attempts_lock = Lock()


def _serializer(salt: str) -> URLSafeTimedSerializer:
    secret = config.SESSION_SECRET
    if not secret:
        raise RuntimeError("SESSION_SECRET manquant dans .env")
    return URLSafeTimedSerializer(secret, salt=salt)


def verify_password(password: str, password_hash: str) -> bool:
    from argon2 import PasswordHasher
    from argon2.exceptions import VerifyMismatchError

    if not password_hash:
        return False
    try:
        return PasswordHasher().verify(password_hash, password)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def check_password(password: str) -> bool:
    return verify_password(password, config.AUTH_PASSWORD_HASH)


def verify_totp(code: str) -> bool:
    import pyotp

    secret = config.AUTH_TOTP_SECRET
    if not secret:
        return False
    cleaned = "".join(c for c in (code or "") if c.isdigit())
    if len(cleaned) != 6:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(cleaned, valid_window=1))


def client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded:
        return forwarded
    if request.client:
        return request.client.host
    return "unknown"


def is_rate_limited(ip: str) -> bool:
    now = time.time()
    with _attempts_lock:
        recent = [t for t in _attempts[ip] if now - t < _WINDOW_SECONDS]
        _attempts[ip] = recent
        return len(recent) >= _MAX_ATTEMPTS


def record_failed_login(ip: str) -> None:
    with _attempts_lock:
        _attempts[ip].append(time.time())


def clear_failed_logins(ip: str) -> None:
    with _attempts_lock:
        _attempts.pop(ip, None)


def create_session_token() -> str:
    return _serializer("asclepios-auth-v1").dumps(
        {"sub": SESSION_SUBJECT, "nonce": secrets.token_hex(8)}
    )


def create_preauth_token() -> str:
    return _serializer("asclepios-preauth-v1").dumps(
        {
            "sub": SESSION_SUBJECT,
            "stage": PREAUTH_STAGE,
            "nonce": secrets.token_hex(8),
        }
    )


def read_session_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        data = _serializer("asclepios-auth-v1").loads(token, max_age=config.SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired, Exception):
        return None
    if not isinstance(data, dict) or data.get("sub") != SESSION_SUBJECT:
        return None
    return data


def read_preauth_token(token: str | None) -> dict[str, Any] | None:
    if not token:
        return None
    try:
        data = _serializer("asclepios-preauth-v1").loads(
            token, max_age=config.PREAUTH_MAX_AGE
        )
    except (BadSignature, SignatureExpired, Exception):
        return None
    if (
        not isinstance(data, dict)
        or data.get("sub") != SESSION_SUBJECT
        or data.get("stage") != PREAUTH_STAGE
    ):
        return None
    return data


def cookie_secure() -> bool:
    if os.getenv("AUTH_COOKIE_SECURE", "").lower() in {"1", "true", "yes"}:
        return True
    return config.ASCLEPIOS_ENV == "production"


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        max_age=config.SESSION_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )


def set_preauth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=PREAUTH_COOKIE_NAME,
        value=token,
        max_age=config.PREAUTH_MAX_AGE,
        httponly=True,
        samesite="lax",
        secure=cookie_secure(),
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")


def clear_preauth_cookie(response: Response) -> None:
    response.delete_cookie(key=PREAUTH_COOKIE_NAME, path="/")


def session_from_request(request: Request) -> dict[str, Any] | None:
    return read_session_token(request.cookies.get(COOKIE_NAME))


def preauth_from_request(request: Request) -> dict[str, Any] | None:
    return read_preauth_token(request.cookies.get(PREAUTH_COOKIE_NAME))


def is_public_path(path: str, method: str) -> bool:
    if method == "OPTIONS":
        return True
    if path == "/api/auth/login" and method == "POST":
        return True
    if path == "/api/auth/totp" and method == "POST":
        return True
    if path == "/api/auth/logout" and method == "POST":
        return True
    return False


async def auth_middleware(request: Request, call_next):
    path = request.url.path
    if is_public_path(path, request.method):
        return await call_next(request)

    if not (path.startswith("/api") or path.startswith("/vault")):
        return await call_next(request)

    if not config.auth_is_configured():
        return JSONResponse(
            {
                "detail": "Auth non configurée (AUTH_PASSWORD_HASH + AUTH_TOTP_SECRET + SESSION_SECRET)",
            },
            status_code=503,
        )

    # Le cookie preauth ne donne aucun accès aux routes protégées
    if session_from_request(request) is None:
        return JSONResponse({"detail": "Non authentifié"}, status_code=401)

    return await call_next(request)
