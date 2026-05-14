"""
ws_manager.py — Robust WebSocket Connection Manager

Features:
  - Safe disconnect handling (no crashes on double-remove)
  - Automatic cleanup of dead connections during broadcast
  - Connection counting for monitoring
"""

from typing import List
from fastapi import WebSocket
import logging

logger = logging.getLogger("WSManager")


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WS client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        try:
            self.active_connections.remove(websocket)
        except ValueError:
            pass  # Already removed
        logger.info(f"WS client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: dict):
        """
        Broadcasts a message to all connected clients.
        Automatically removes dead connections that fail to receive.
        """
        if not self.active_connections:
            return

        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                dead_connections.append(connection)

        # Cleanup dead connections
        for dead in dead_connections:
            try:
                self.active_connections.remove(dead)
            except ValueError:
                pass

        if dead_connections:
            logger.info(f"Cleaned up {len(dead_connections)} dead WS connections. Remaining: {len(self.active_connections)}")

    @property
    def connection_count(self) -> int:
        return len(self.active_connections)


manager = ConnectionManager()
