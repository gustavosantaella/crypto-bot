"""Hilo que publica la señal de mercado por SSE periódicamente.

Cada ``ANALYSIS_REFRESH_MS`` ms se analiza el símbolo en ambos ambientes
(testnet y producción) y se publica un evento ``market.analysis`` con la
señal LONG/SHORT/NEUTRAL. El portal se suscribe a ``GET /api/events`` para
mostrarla en vivo sin hacer polling.
"""
from __future__ import annotations

import logging
import threading

from .analysis import MarketAnalyzer
from .config import settings
from .events import event_bus

_logger = logging.getLogger("crypto_api.analysis_emitter")


class AnalysisEmitter(threading.Thread):
    def __init__(self) -> None:
        super().__init__(name="AnalysisEmitter", daemon=True)
        self._stop = threading.Event()
        self._analyzers = {
            market_type: MarketAnalyzer(
                symbol=settings.symbol,
                interval=settings.kline_interval,
                limit=settings.kline_limit,
            )
            for market_type in ("SPOT", "FUTURES")
        }

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        _logger.info("AnalysisEmitter iniciado (cada %d ms).", settings.analysis_refresh_ms)
        while not self._stop.is_set():
            for market_type, analyzer in self._analyzers.items():
                for test_mode in (True, False):
                    try:
                        payload = analyzer.analyze(market_type=market_type, test_mode=test_mode)
                        event_bus.publish("market.analysis", payload)
                    except Exception as exc:  # noqa: BLE001
                        _logger.debug("No se pudo analizar %s/%s: %s", market_type, test_mode, exc)
            self._stop.wait(settings.analysis_refresh_ms / 1000.0)
        _logger.info("AnalysisEmitter detenido.")
