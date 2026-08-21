"""Stream de precios de Binance vía WebSocket.

Consume el market stream ``<symbol>@trade`` y notifica cada tick al estado
del bot. Corre en un hilo propio para no bloquear el motor de trading.

Reconexión automática: si la conexión se cae (tiempo de inactividad, error de
red, reinicio de Binance...) el hilo la restablece con *backoff exponencial*
(1s, 2s, 4s, ... hasta ``max_reconnect_delay``), de forma indefinida.

Documentación del stream de mercado:
https://developers.binance.com/docs/binance-spot-api-docs/web-socket-streams
"""
from __future__ import annotations

import json
import logging
import threading

import websocket


class PriceStream(threading.Thread):
    def __init__(
        self,
        url: str,
        on_trade,
        on_status=None,
        max_reconnect_delay: float = 30.0,
        ping_interval: int = 20,
        ping_timeout: int = 10,
    ) -> None:
        super().__init__(name="PriceStream", daemon=True)
        self._url = url
        self._on_trade = on_trade
        self._on_status = on_status or (lambda _status: None)
        self._max_reconnect_delay = max_reconnect_delay
        self._ping_interval = ping_interval
        self._ping_timeout = ping_timeout
        self._stop_event = threading.Event()
        self._connected = threading.Event()
        self._log = logging.getLogger("crypto_bot.price_stream")

    def stop(self) -> None:
        self._stop_event.set()

    @property
    def is_connected(self) -> bool:
        return self._connected.is_set()

    def _parse(self, message: str) -> None:
        """Parsea un mensaje del stream combinado y notifica el trade."""
        try:
            payload = json.loads(message)
        except json.JSONDecodeError:
            self._log.warning("Mensaje no-JSON ignorado")
            return
        # Stream combinado: {"stream": "...", "data": {...}}
        data = payload.get("data", payload)
        if data.get("e") != "trade":
            return  # solo nos interesan los ticks de tipo trade
        self._on_trade(data)

    def run(self) -> None:
        backoff = 1.0
        while not self._stop_event.is_set():
            ws = None
            try:
                self._log.info("Conectando al stream: %s", self._url)
                ws = websocket.create_connection(
                    self._url,
                    timeout=10,
                    ping_interval=self._ping_interval,
                    ping_timeout=self._ping_timeout,
                )
                self._connected.set()
                backoff = 1.0
                self._on_status("connected")
                self._log.info("Stream conectado.")

                while not self._stop_event.is_set():
                    message = ws.recv()
                    if message:
                        self._parse(message)

            except websocket.WebSocketTimeoutException:
                self._log.warning("Timeout del WebSocket (sin pong).")
            except (websocket.WebSocketConnectionClosedException, ConnectionError, OSError) as exc:
                self._log.warning("Conexión del stream cerrada: %s", exc)
            except Exception as exc:  # noqa: BLE001 - el loop debe sobrevivir a todo
                self._log.error("Error inesperado en el stream: %s", exc)
            finally:
                self._connected.clear()
                self._on_status("disconnected")
                if ws is not None:
                    try:
                        ws.close()
                    except Exception:  # noqa: BLE001
                        pass

            if self._stop_event.is_set():
                break

            self._log.info("Reintentando conexión en %.1fs (backoff)...", backoff)
            self._stop_event.wait(backoff)
            backoff = min(backoff * 2, self._max_reconnect_delay)

        self._log.info("Stream detenido.")
