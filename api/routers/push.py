"""Abonnements Web Push (VAPID)."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from api import config
from api import push_service

router = APIRouter(prefix="/api/push", tags=["push"])


class PushKeys(BaseModel):
    p256dh: str = Field(min_length=8)
    auth: str = Field(min_length=8)


class SubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=8)
    keys: PushKeys


class UnsubscribeRequest(BaseModel):
    endpoint: str = Field(min_length=8)


@router.get("/vapid-public-key")
def vapid_public_key():
    if not config.vapid_is_configured():
        raise HTTPException(status_code=503, detail="Web Push non configuré (clés VAPID)")
    return {"publicKey": config.VAPID_PUBLIC_KEY}


@router.get("/status")
def push_status():
    return {
        "configured": config.vapid_is_configured(),
        "subscriptions": push_service.subscription_count(),
    }


@router.post("/subscribe")
def subscribe(body: SubscribeRequest):
    if not config.vapid_is_configured():
        raise HTTPException(status_code=503, detail="Web Push non configuré (clés VAPID)")
    record = push_service.upsert_subscription(
        body.endpoint.strip(),
        body.keys.p256dh.strip(),
        body.keys.auth.strip(),
    )
    return {"ok": True, "endpoint": record["endpoint"]}


@router.post("/unsubscribe")
def unsubscribe(body: UnsubscribeRequest):
    push_service.remove_subscription(body.endpoint.strip())
    return {"ok": True}


@router.post("/test")
def test_push():
    if not config.vapid_is_configured():
        raise HTTPException(status_code=503, detail="Web Push non configuré (clés VAPID)")
    if push_service.subscription_count() == 0:
        raise HTTPException(status_code=400, detail="Aucun appareil abonné")
    result = push_service.send_push(
        {
            "title": "Asclepios",
            "body": "Les notifications sont bien activées.",
            "url": "/",
            "tag": "asclepios-test",
        },
        ttl=60,
    )
    return result
