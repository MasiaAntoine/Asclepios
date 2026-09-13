"""Factory FastAPI Asclepios."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from api import auth, config
from api.routers import (
    agenda,
    chats,
    doctors,
    labs,
    medications,
    ordonnances,
    pdf,
    reports,
    settings,
    suivi,
    vault_edits,
    vault_files,
)
from api.routers import auth as auth_router


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await auth.auth_middleware(request, call_next)


def create_app() -> FastAPI:
    openapi_url = None if config.ASCLEPIOS_ENV == "production" else "/openapi.json"
    app = FastAPI(
        title="Asclepios API",
        version=config.APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=openapi_url,
    )
    # Ordre d'ajout : le dernier est le plus externe (s'exécute en premier).
    app.add_middleware(AuthMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["*"],
    )

    for module in (
        auth_router,
        vault_files,
        pdf,
        medications,
        labs,
        ordonnances,
        suivi,
        doctors,
        settings,
        agenda,
        reports,
        vault_edits,
        chats,
    ):
        app.include_router(module.router)
    return app
