"""Factory FastAPI Asclepios."""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api import config
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
)


def create_app() -> FastAPI:
    app = FastAPI(
        title="Asclepios API",
        version=config.APP_VERSION,
        docs_url=None,
        redoc_url=None,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    for module in (
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
