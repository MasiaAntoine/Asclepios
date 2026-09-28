"""Jobs de génération chat/rapport, indépendants de la connexion HTTP."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import AsyncGenerator

from api import config


@dataclass
class ChatJob:
    chat_id: str
    kind: str  # reply | report
    assistant_id: str | None = None
    events: list[bytes] = field(default_factory=list)
    subscribers: list[asyncio.Queue[bytes | None]] = field(default_factory=list)
    done: bool = False
    error: str | None = None


_jobs: dict[str, ChatJob] = {}


def job_key(chat_id: str, kind: str) -> str:
    return f"{chat_id}:{kind}"


def get_job(chat_id: str, kind: str) -> ChatJob | None:
    return _jobs.get(job_key(chat_id, kind))


def begin_job(chat_id: str, kind: str, *, assistant_id: str | None = None) -> ChatJob:
    key = job_key(chat_id, kind)
    existing = _jobs.get(key)
    if existing and not existing.done:
        return existing
    job = ChatJob(chat_id=chat_id, kind=kind, assistant_id=assistant_id)
    _jobs[key] = job
    return job


async def emit(job: ChatJob, payload: str) -> None:
    chunk = f"data: {payload}\n\n".encode()
    job.events.append(chunk)
    dead: list[asyncio.Queue[bytes | None]] = []
    for queue in job.subscribers:
        try:
            queue.put_nowait(chunk)
        except asyncio.QueueFull:
            dead.append(queue)
    for queue in dead:
        if queue in job.subscribers:
            job.subscribers.remove(queue)


async def finish_job(job: ChatJob, *, error: str | None = None) -> None:
    job.error = error
    job.done = True
    for queue in list(job.subscribers):
        try:
            queue.put_nowait(None)
        except asyncio.QueueFull:
            pass
    await asyncio.sleep(90)
    key = job_key(job.chat_id, job.kind)
    if _jobs.get(key) is job:
        _jobs.pop(key, None)


async def stream_job(job: ChatJob) -> AsyncGenerator[bytes, None]:
    queue: asyncio.Queue[bytes | None] = asyncio.Queue(maxsize=500)
    job.subscribers.append(queue)
    try:
        for chunk in job.events:
            yield chunk
        if job.done:
            return
        while True:
            try:
                item = await asyncio.wait_for(queue.get(), timeout=20)
            except asyncio.TimeoutError:
                yield b": keepalive\n\n"
                if job.done:
                    return
                continue
            if item is None:
                return
            yield item
    finally:
        if queue in job.subscribers:
            job.subscribers.remove(queue)


def notify_chat_ready(chat_id: str, *, title: str, body: str) -> None:
    """Push : le SW n’affiche rien si une fenêtre Asclepios est visible."""
    from api.push_service import send_push, subscription_count

    if not config.vapid_is_configured() or subscription_count() == 0:
        return
    preview = " ".join((body or "").split())
    if len(preview) > 110:
        preview = preview[:107].rstrip() + "…"
    send_push(
        {
            "title": title,
            "body": preview or "Ouvre le chat pour lire la réponse.",
            "url": f"/assistant/{chat_id}",
            "tag": f"asclepios-chat-{chat_id}",
        },
        ttl=12 * 3600,
    )
