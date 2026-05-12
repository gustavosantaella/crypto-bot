from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.ws_manager import manager
import logging

router = APIRouter()

@router.post("/notify")
async def notify_update(data: dict):
    """
    Endpoint para que el Bot notifique actualizaciones (precio, rsi, trades)
    y estas se retransmitan por WebSocket.
    """
    await manager.broadcast(data)
    return {"status": "broadcasted"}
