"""Estado compartido y thread-safe.

El hilo del WebSocket actualiza el precio y el hilo del engine lo lee.
Todo acceso a los campos se hace bajo un mismo ``RLock``.
"""
from __future__ import annotations

import threading
from collections import deque
from datetime import datetime

from .models import Position


class TradingState:
    def __init__(self, max_sma_window: int = 20) -> None:
        self._lock = threading.RLock()
        self._latest_price: float | None = None
        self._latest_trade_id: int | None = None
        self._sma_window: deque[float] = deque(maxlen=max_sma_window)
        self.position: Position | None = None
        self.order_in_flight: bool = False
        self.total_closed_trades: int = 0
        self.total_profit: float = 0.0
        self.started_at: datetime = datetime.now()

    # ------------------------------------------------------------------
    # Precio / ticks
    # ------------------------------------------------------------------
    def update_tick(self, trade: dict) -> None:
        """Actualiza el último precio con un trade del stream.

        Deduplicación: los trades llegan a cientos por segundo y con las
        reconexiones pueden repetirse; se ignora cualquier tick con el mismo
        ``trade id`` que el último procesado.

        NOTA: aquí NO se llena la ventana de la media móvil. La SMA se
        construye con :meth:`sample`, llamada cada ``SMA_SAMPLE_MS`` desde el
        engine. Si se llenara con cada trade, la media quedaría clavada al
        precio actual (los últimos N trades ocurren en milisegundos) y la
        estrategia nunca detectaría caídas.
        """
        try:
            price = float(trade.get("p"))
        except (TypeError, ValueError):
            return

        trade_id = trade.get("t")
        with self._lock:
            if trade_id is not None and trade_id == self._latest_trade_id:
                return
            self._latest_trade_id = trade_id
            self._latest_price = price

    def sample(self) -> None:
        """Toma una muestra temporal del precio para la ventana de la SMA.

        El engine la invoca cada ``SMA_SAMPLE_MS`` milisegundos, de forma que
        la media móvil represente el promedio del ÚLTIMO PERIODO DE TIEMPO
        (p. ej. 20 muestras x 2 s = últimos 40 s) en vez de los últimos ticks.
        """
        with self._lock:
            if self._latest_price is not None:
                self._sma_window.append(self._latest_price)

    def seed_price(self, price: float) -> None:
        """Siembra el precio inicial (por ejemplo desde REST al arrancar)."""
        with self._lock:
            self._latest_price = float(price)
            self._sma_window.append(float(price))

    def get_price(self) -> float | None:
        with self._lock:
            return self._latest_price

    def sma(self) -> float | None:
        """Media móvil simple de la ventana de precios, o None si está vacía."""
        with self._lock:
            if not self._sma_window:
                return None
            return sum(self._sma_window) / len(self._sma_window)

    # ------------------------------------------------------------------
    # Posición / ciclo de trading
    # ------------------------------------------------------------------
    def has_position(self) -> bool:
        with self._lock:
            return self.position is not None

    def is_busy(self) -> bool:
        """El bot no debe abrir otra operación mientras haya una orden en
        vuelo o una posición abierta (una sola operación por ciclo)."""
        with self._lock:
            return self.order_in_flight or self.position is not None

    def open_position(self, position: Position) -> None:
        with self._lock:
            self.position = position

    def close_position(self, profit: float) -> Position | None:
        with self._lock:
            position = self.position
            self.position = None
            if position is not None:
                self.total_closed_trades += 1
                self.total_profit += profit
            return position
