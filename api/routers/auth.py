"""Endpoints login / totp / logout / me."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from api import auth, config

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class TotpRequest(BaseModel):
    code: str = Field(min_length=6, max_length=16)


@router.post("/login")
async def login(body: LoginRequest, request: Request, response: Response) -> dict:
    if not config.auth_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Auth non configurée. Définis AUTH_PASSWORD_HASH, AUTH_TOTP_SECRET et SESSION_SECRET.",
        )

    ip = auth.client_ip(request)
    if auth.is_rate_limited(ip):
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives. Réessaie dans quelques minutes.",
        )

    if not auth.check_password(body.password):
        auth.record_failed_login(ip)
        raise HTTPException(status_code=401, detail="Mot de passe incorrect")

    # Mot de passe OK → preauth seulement (pas de session)
    auth.clear_session_cookie(response)
    token = auth.create_preauth_token()
    auth.set_preauth_cookie(response, token)
    return {"ok": True, "next": "totp"}


@router.post("/totp")
async def verify_totp(body: TotpRequest, request: Request, response: Response) -> dict:
    if not config.auth_is_configured():
        raise HTTPException(
            status_code=503,
            detail="Auth non configurée. Définis AUTH_PASSWORD_HASH, AUTH_TOTP_SECRET et SESSION_SECRET.",
        )

    ip = auth.client_ip(request)
    if auth.is_rate_limited(ip):
        raise HTTPException(
            status_code=429,
            detail="Trop de tentatives. Réessaie dans quelques minutes.",
        )

    if auth.preauth_from_request(request) is None:
        raise HTTPException(
            status_code=401,
            detail="Session intermédiaire expirée. Recommence avec le mot de passe.",
        )

    if not auth.verify_totp(body.code):
        auth.record_failed_login(ip)
        raise HTTPException(status_code=401, detail="Code incorrect")

    auth.clear_failed_logins(ip)
    auth.clear_preauth_cookie(response)
    session = auth.create_session_token()
    auth.set_session_cookie(response, session)
    return {"ok": True, "user": "owner"}


@router.post("/logout")
async def logout(response: Response) -> dict:
    auth.clear_session_cookie(response)
    auth.clear_preauth_cookie(response)
    return {"ok": True}


@router.get("/me")
async def me(request: Request) -> dict:
    session = auth.session_from_request(request)
    if session is None:
        raise HTTPException(status_code=401, detail="Non authentifié")
    return {"ok": True, "user": "owner"}
