"""Reporter en segundo plano hacia la API del proyecto.

El trading no debe bloquearse esperando a que la API registre los datos, por
eso todos los envíos se encolan en una cola FIFO que un hilo *worker*
(daemon) consume en background.

La cola FIFO + un solo worker garantizan que la transacción (ciclo) se CREE
en la API antes de que llegue el cierre de la misma (orden de eventos).

Los payloads viajan con una clave local de referencia (``ref_key`` = el
``orderId`` de la compra de Binance); el worker traduce esa clave al id real
que la API devuelve al crear la fila, y la reutiliza al cerrarla.
"""
from __future__ import annotations

import logging
import queue
import threading
import time
from datetime import datetime, timezone

import requests

from .models import Position


def _utc_iso(epoch_ms: int) -> str:
    return datetime.fromtimestamp(epoch_ms / 1000.0, tz=timezone.utc).isoformat()


class ApiReporter:
    def __init__(self, api_url: str, logger: logging.Logger, max_retries: int = 3) -> None:
        self._api_url = api_url
        self._log = logger.getChild("api_reporter")
        self._max_retries = max_retries
        self._queue: "queue.Queue[tuple]" = queue.Queue()
        self._ref_lock = threading.Lock()
        self._local_to_remote: dict[str, int] = {}
        self._worker = threading.Thread(target=self._run, name="ApiReporter", daemon=True)
        self._worker.start()
        self._log.info("ApiReporter iniciado (worker en background).")

    # ------------------------------------------------------------------
    # API pública (no bloqueante)
    # ------------------------------------------------------------------
    def create_transaction(self, position: Position) -> None:
        """Crea la transacción (ciclo) en la API en cuanto se abre la posición."""
        payload = {
            "symbol": position.symbol,
            "buy_order_id": position.buy_order_id,
            "buy_price": position.buy_price,
            "buy_quantity": position.buy_quantity,
            "buy_quote": position.buy_quote,
            "buy_time": _utc_iso(position.buy_time),
            "test_mode": position.test_mode,
            "market_type": position.market_type,
            "side": position.side,
            "leverage": position.leverage,
            "notional": position.buy_quote,
            "margin": position.margin,
            "liquidation_price": position.liquidation_price,
            "take_profit_price": position.take_profit_price,
            "stop_loss_price": position.stop_loss_price,
            "status": "OPEN",
        }
        self._queue.put(("create", str(position.buy_order_id), payload))

    def close_transaction(self, position: Position, order, profit: float, profit_pct: float) -> None:
        """Cierra la transacción con los datos de la venta/cierre."""
        payload = {
            "sell_order_id": order.order_id,
            "sell_price": order.avg_price,
            "sell_quantity": order.executed_qty,
            "sell_quote": order.quote_qty,
            "sell_time": _utc_iso(order.transact_time),
            "profit": round(profit, 10),
            "profit_pct": round(profit_pct, 6),
            "status": "CLOSED",
        }
        self._queue.put(("close", str(position.buy_order_id), payload))

    def report_order(
        self,
        symbol: str,
        side: str,
        order,
        test_mode: bool,
        market_type: str = "SPOT",
        position_side: str = "BOTH",
        leverage: int = 1,
    ) -> None:
        """Registra una orden individual (auditoría) en la API."""
        payload = {
            "symbol": symbol,
            "side": side,
            "binance_order_id": order.order_id,
            "price": order.avg_price,
            "quantity": order.executed_qty,
            "quote_quantity": order.quote_qty,
            "status": order.status,
            "test_mode": test_mode,
            "market_type": market_type,
            "position_side": position_side,
            "leverage": leverage,
        }
        self._queue.put(("order", None, payload))

    def flush(self, timeout: float = 5.0) -> None:
        """Espera a que la cola se vacíe (para un cierre limpio)."""
        deadline = time.time() + timeout
        while self._queue.unfinished_tasks and time.time() < deadline:
            time.sleep(0.05)

    # ------------------------------------------------------------------
    # Worker
    # ------------------------------------------------------------------
    def _run(self) -> None:
        while True:
            kind, ref_key, payload = self._queue.get()
            try:
                if kind == "create":
                    remote_id = self._post("/api/transactions", payload)
                    if remote_id is not None:
                        with self._ref_lock:
                            self._local_to_remote[ref_key] = remote_id
                        self._log.info("Transacción creada en API: id=%s", remote_id)
                elif kind == "close":
                    with self._ref_lock:
                        remote_id = self._local_to_remote.get(ref_key)
                    if remote_id is None:
                        self._log.error("No existe transacción remota para ref=%s (¿falló el create?)", ref_key)
                    else:
                        self._patch(f"/api/transactions/{remote_id}", payload)
                        self._log.info("Transacción cerrada en API: id=%s", remote_id)
                elif kind == "order":
                    self._post("/api/orders", payload)
                else:
                    self._log.error("Tipo de item desconocido en cola: %s", kind)
            except Exception as exc:  # noqa: BLE001
                self._log.error("Fallo al reportar '%s' (%s): %s", kind, ref_key, exc)
            finally:
                self._queue.task_done()

    def _post(self, path: str, payload: dict) -> int | None:
        resp = self._request_with_retry("POST", path, payload)
        if resp is None:
            return None
        return resp.get("id")

    def _patch(self, path: str, payload: dict) -> None:
        self._request_with_retry("PATCH", path, payload)

    def _request_with_retry(self, method: str, path: str, payload: dict) -> dict | None:
        url = f"{self._api_url}{path}"
        last_error: Exception | None = None
        for attempt in range(1, self._max_retries + 1):
            try:
                resp = requests.request(method, url, json=payload, timeout=5)
                if resp.status_code < 300:
                    return resp.json()
                last_error = RuntimeError(f"HTTP {resp.status_code}: {resp.text[:200]}")
            except requests.RequestException as exc:
                last_error = exc
            self._log.warning("Intento %d/%d fallido (%s %s): %s", attempt, self._max_retries, method, path, last_error)
            if attempt < self._max_retries:
                time.sleep(0.5 * attempt)
        return None

