"""Hilo que consume el WebSocket de precios de Binance y publica por SSE.

Se lanza uno por ambiente (testnet y producción) en el arranque de la API.
El precio es público (no requiere autenticación), así que ambos streams se
conectan siempre.

Para no saturar el SSE con cientos de trades por segundo, se publica el
último precio de cada ambiente cada ``sample_interval`` segundos.
"""
from __future__ import annotations

import json
import logging
import threading
import time

import websocket

from .events import event_bus

_logger = logging.getLogger("crypto_api.price_stream")


class PriceStream(threading.Thread):
    def __init__(
        self,
        name: str,
        url: str,
        test_mode: bool,
        symbol: str,
        sample_interval: float = 2.0,
    ) -> None:
        super().__init__(name=f"PriceStream-{name}", daemon=True)
        self._url = url
        self._test_mode = test_mode
        self._symbol = symbol
        self._sample_interval = sample_interval
        self._stop = threading.Event()
        self._last_price: float | None = None
        self._log = _logger.getChild(name)

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        backoff = 1.0
        while not self._stop.is_set():
            try:
                self._log.info("Conectando stream de precios: %s", self._url)
                ws = websocket.create_connection(
                    self._url, timeout=10, ping_interval=20, ping_timeout=10,
                )
                ws.settimeout(0.5)  # permite revisar el flag de stop cada 0.5 s
                backoff = 1.0
                last_publish = 0.0
                while not self._stop.is_set():
                    try:
                        message = ws.recv()
                        if message:
                            payload = json.loads(message)
                            data = payload.get("data", payload)
                            if data.get("e") == "trade":
                                self._last_price = float(data["p"])
                    except websocket.WebSocketTimeoutException:
                        pass
                    except (websocket.WebSocketConnectionClosedException, ConnectionError, OSError) as exc:
                        self._log.warning("Conexión del stream cerrada: %s", exc)
                        break
                    except Exception as exc:  # noqa: BLE001
                        self._log.error("Error inesperado en el stream: %s", exc)

                    now = time.time()
                    if self._last_price is not None and now - last_publish >= self._sample_interval:
                        event_bus.publish("price", {
                            "test_mode": self._test_mode,
                            "symbol": self._symbol,
                            "price": self._last_price,
                            "time": int(now * 1000),
                        })
                        last_publish = now

                try:
                    ws.close()
                except Exception:  # noqa: BLE001
                    pass
            except Exception as exc:  # noqa: BLE001
                self._log.error("No se pudo conectar al stream: %s", exc)

            if self._stop.is_set():
                break
            self._log.info("Reconectando stream en %.1fs (backoff)...", backoff)
            self._stop.wait(backoff)
            backoff = min(backoff * 2, 30.0)
