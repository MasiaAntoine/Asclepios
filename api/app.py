"""Factory FastAPI Asclepios."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

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
    push,
    reports,
    settings,
    sport,
    suivi,
    vault_edits,
    vault_files,
)
from api.routers import auth as auth_router


class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        return await auth.auth_middleware(request, call_next)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    from api.deps import ensure_canonical_vault_files
    from api.push_reminders import reminder_loop

    ensure_canonical_vault_files()
    task = asyncio.create_task(reminder_loop())
    try:
        yield
    finally:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    openapi_url = None if config.ASCLEPIOS_ENV == "production" else "/openapi.json"
    app = FastAPI(
        title="Asclepios API",
        version=config.APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=openapi_url,
        lifespan=lifespan,
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
        sport,
        doctors,
        settings,
        agenda,
        reports,
        vault_edits,
        chats,
        push,
    ):
        app.include_router(module.router)
    return app
