"""Buffer de velas OHLC.

Combina las velas históricas (klines de Binance, vía REST) con los trades que
llegan por WebSocket para mantener velas actualizadas en tiempo real.

El hilo del WebSocket llama a :meth:`update_trade` con cada tick (campos ``p``
y ``T``); el engine llama a :meth:`refresh_klines` periódicamente para cerrar
huecos tras reconexiones y para sembrar historia al arrancar.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any, Callable

from . import indicators


class CandleBuffer:
    """Almacena velas de un intervalo fijo y calcula indicadores.

    Atributos configurables (se inyectan desde la Config del bot):
      interval_ms  -> duración de cada vela en milisegundos.
      limit        -> máximo de velas que se conservan en memoria.
    """

    def __init__(
        self,
        interval_ms: int,
        limit: int = 300,
        seed_callback: Callable[[], None] | None = None,
    ) -> None:
        self._lock = threading.RLock()
        self._interval_ms = interval_ms
        self._limit = limit
        self._seed_callback = seed_callback
        self._candles: deque[dict] = deque(maxlen=limit)
        self._current: dict | None = None
        self._last_refresh = 0.0

    # ------------------------------------------------------------------
    # Construcción de velas
    # ------------------------------------------------------------------
    def _bucket_time(self, event_time_ms: int) -> int:
        return (event_time_ms // self._interval_ms) * self._interval_ms

    def seed_from_klines(self, klines: list[list]) -> None:
        """Siembra el buffer con klines de Binance ``[[time, o, h, l, c, v, ...], ...]``."""
        with self._lock:
            self._candles.clear()
            self._current = None
            for k in klines:
                open_time = int(k[0])
                candle = {
                    "open_time": open_time,
                    "open": float(k[1]),
                    "high": float(k[2]),
                    "low": float(k[3]),
                    "close": float(k[4]),
                    "volume": float(k[5]),
                }
                self._candles.append(candle)

    def update_trade(self, price: float, event_time_ms: int) -> None:
        """Actualiza la vela actual con un tick del stream de trades.

        Si el tick pertenece al bucket de la última vela sembrada por klines,
        se actualiza esa vela en su sitio (evita duplicar el último minuto).
        """
        bucket = self._bucket_time(event_time_ms)
        with self._lock:
            if self._current is not None and self._current["open_time"] == bucket:
                c = self._current
                c["high"] = max(c["high"], price)
                c["low"] = min(c["low"], price)
                c["close"] = price
                c["_updated"] = event_time_ms
                return

            if self._current is not None:
                self._candles.append(self._current)
                self._current = None

            # ¿El tick pertenece al bucket de la última vela sembrada?
            if self._candles and self._candles[-1]["open_time"] == bucket:
                c = self._candles[-1]
                c["high"] = max(c["high"], price)
                c["low"] = min(c["low"], price)
                c["close"] = price
                c["_updated"] = event_time_ms
                return

            self._current = {
                "open_time": bucket,
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": 0.0,
                "_updated": event_time_ms,
            }

    def roll_current(self) -> None:
        """Cierra la vela actual (si está en otro bucket de tiempo) y la archiva."""
        now = int(time.time() * 1000)
        with self._lock:
            if self._current is not None and self._bucket_time(now) != self._current["open_time"]:
                self._candles.append(self._current)
                self._current = None

    # ------------------------------------------------------------------
    # Lectura
    # ------------------------------------------------------------------
    def candles(self) -> list[dict]:
        with self._lock:
            items = list(self._candles)
            if self._current is not None:
                items.append(dict(self._current))
            return items

    def closes(self) -> list[float]:
        return [c["close"] for c in self.candles()]

    def highs(self) -> list[float]:
        return [c["high"] for c in self.candles()]

    def lows(self) -> list[float]:
        return [c["low"] for c in self.candles()]

    def last_close(self) -> float | None:
        candles = self.candles()
        return candles[-1]["close"] if candles else None

    def is_ready(self, min_candles: int = 60) -> bool:
        return len(self.candles()) >= min_candles

    # ------------------------------------------------------------------
    # Análisis
    # ------------------------------------------------------------------
    def analyze(self, params: Any) -> dict:
        """Indicadores + score a partir de las velas acumuladas.

        ``params`` debe exponer: ema_fast, ema_slow, ema_signal,
        ema_trend_fast, ema_trend_slow, rsi_period, rsi_oversold,
        rsi_overbought (p.ej. la propia ``Config`` del bot).
        """
        candles = self.candles()
        closes = [c["close"] for c in candles]
        highs = [c["high"] for c in candles]
        lows = [c["low"] for c in candles]
        return indicators.compute_all(
            closes=closes,
            highs=highs,
            lows=lows,
            ema_fast=params.ema_fast,
            ema_slow=params.ema_slow,
            ema_signal=params.ema_signal,
            ema_trend_fast=params.ema_trend_fast,
            ema_trend_slow=params.ema_trend_slow,
            rsi_period=params.rsi_period,
            rsi_oversold=params.rsi_oversold,
            rsi_overbought=params.rsi_overbought,
        )


def interval_to_ms(interval: str) -> int:
    """Convierte un intervalo de Binance (1m, 5m, 1h...) a milisegundos."""
    interval = interval.strip().lower()
    unit = interval[-1]
    try:
        value = int(interval[:-1])
    except ValueError:
        return 60_000
    multipliers = {"s": 1000, "m": 60_000, "h": 3_600_000, "d": 86_400_000, "w": 604_800_000}
    return value * multipliers.get(unit, 60_000)
