"""Endpoint SSE para notificaciones en tiempo real.

Los clientes se conectan a ``GET /api/events`` y reciben eventos como:

    event: transaction.created
    data: {"id": 10, "symbol": "BTCUSDT", ...}

Se envía un *heartbeat* (comentario ``: ping``) cada 15 s para mantener la
conexión viva a través de proxies/intermediarios.
"""
from __future__ import annotations

import asyncio
import queue

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from ..events import event_bus

router = APIRouter(prefix="/api/events", tags=["events"])

_HEARTBEAT_SECONDS = 15
_POLL_SECONDS = 0.5


@router.get("")
async def stream(request: Request) -> StreamingResponse:
    subscription = event_bus.subscribe()

    async def event_generator():
        loop = asyncio.get_event_loop()
        last_beat = loop.time()
        try:
            yield "event: connected\ndata: {}\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    yield subscription.get_nowait()
                    last_beat = loop.time()
                except queue.Empty:
                    now = loop.time()
                    if now - last_beat >= _HEARTBEAT_SECONDS:
                        yield ": ping\n\n"
                        last_beat = now
                await asyncio.sleep(_POLL_SECONDS)
        finally:
            event_bus.unsubscribe(subscription)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
