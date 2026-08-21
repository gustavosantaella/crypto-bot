"""Bus de eventos en memoria para SSE (Server-Sent Events).

Los endpoints que modifican transacciones (crear/cerrar/cancelar) publican
eventos; el endpoint ``GET /api/events`` los reenvía a los clientes
conectados en tiempo real.

Es seguro llamar a ``publish`` desde cualquier hilo (usa ``queue.Queue``
thread-safe). Si un cliente va lento y su cola se llena, se descarta el
evento más antiguo para conservar siempre el más reciente.
"""
from __future__ import annotations

import json
import queue
import threading


class EventBus:
    def __init__(self, max_queue: int = 50) -> None:
        self._lock = threading.Lock()
        self._subscribers: set[queue.Queue] = set()
        self._max_queue = max_queue

    def subscribe(self) -> queue.Queue:
        subscription: queue.Queue = queue.Queue(maxsize=self._max_queue)
        with self._lock:
            self._subscribers.add(subscription)
        return subscription

    def unsubscribe(self, subscription: queue.Queue) -> None:
        with self._lock:
            self._subscribers.discard(subscription)

    def publish(self, event_type: str, data: dict) -> None:
        """Publica un evento a todos los suscriptores con formato SSE."""
        payload = "event: {}\ndata: {}\n\n".format(
            event_type,
            json.dumps(data, ensure_ascii=False, default=str),
        )
        with self._lock:
            subscribers = list(self._subscribers)
        for subscription in subscribers:
            try:
                subscription.put_nowait(payload)
            except queue.Full:
                # Cliente lento: descartar el más antiguo y guardar el reciente.
                try:
                    subscription.get_nowait()
                    subscription.put_nowait(payload)
                except (queue.Empty, queue.Full):
                    pass


# Instancia única del bus de eventos.
event_bus = EventBus()
