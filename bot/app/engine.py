"""Motor de trading.

Coordina el stream de precios, la estrategia y las órdenes de Binance.

Garantías de diseño:
- **Una sola operación por ciclo**: mientras haya una posición abierta o una
  orden en vuelo, no se evalúa ninguna compra nueva.
- **La venta siempre es mayor que la compra**: la estrategia solo ordena
  vender cuando ``precio >= precio_compra * (1 + SELL_PROFIT_PCT/100)`` y la
  ganancia real se calcula con los precios de ejecución reales.
- **Sin duplicados**: el flag ``order_in_flight`` (bajo lock) impide lanzar
  dos órdenes por error; el stream deduplica ticks por trade id.
- **No bloquea el trading**: los datos se reportan a la API en background
  (ApiReporter).
"""
from __future__ import annotations

import logging
import threading
import time

from config import Config
from .api_reporter import ApiReporter
from .binance_client import BinanceAPIError, BinanceClient
from .models import Position, TradeDecision
from .price_stream import PriceStream
from .state import TradingState
from .strategy import SMAStrategy


class TradingEngine:
    def __init__(
        self,
        config: Config,
        client: BinanceClient,
        stream: PriceStream,
        state: TradingState,
        strategy: SMAStrategy,
        reporter: ApiReporter,
        logger: logging.Logger,
    ) -> None:
        self._cfg = config
        self._client = client
        self._stream = stream
        self._state = state
        self._strategy = strategy
        self._reporter = reporter
        self._log = logger.getChild("engine")
        self._stop = threading.Event()
        self._symbol = config.symbol
        # Caché de los filtros del símbolo (step size, minNotional...).
        self._symbol_info: dict | None = None
        # Timestamp: próxima vez que se permite reintentar una venta tras un
        # fallo de filtro (evita reintentos en bucle cada CHECK_INTERVAL_MS).
        self._next_sell_attempt: float = 0.0

    def _get_symbol_info(self) -> dict:
        """Filtros del símbolo, obtenidos una sola vez (se cachean)."""
        if self._symbol_info is None:
            self._symbol_info = self._client.get_symbol_info(self._symbol)
        return self._symbol_info

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def run(self) -> None:
        self._log.info("Bot iniciado | símbolo=%s | modo=%s | compra<=SMA*%.2f%% | venta>=compra*+%.2f%%",
                       self._symbol, "TESTNET" if self._cfg.test_mode else "REAL",
                       self._cfg.buy_threshold_pct, self._cfg.sell_profit_pct)
        self._log.info("Stream WebSocket: %s", self._cfg.binance_ws_url)

        self._stream.start()
        self._warmup()

        try:
            while not self._stop.is_set():
                self._process_cycle()
                time.sleep(self._cfg.check_interval_ms / 1000.0)
        except KeyboardInterrupt:
            self._log.info("Interrupción (Ctrl+C) recibida.")
            self.shutdown()
        except Exception as exc:  # noqa: BLE001
            self._log.exception("Error fatal en el motor: %s", exc)
            self.shutdown()

    def shutdown(self) -> None:
        self._stop.set()
        self._log.info("Deteniendo el bot...")
        self._stream.stop()
        self._reporter.flush(timeout=5)
        self._log.info(
            "Bot detenido | ciclos cerrados=%d | ganancia total=%.8f USDT",
            self._state.total_closed_trades,
            self._state.total_profit,
        )

    # ------------------------------------------------------------------
    # Arranque
    # ------------------------------------------------------------------
    def _warmup(self) -> None:
        """Obtiene un precio inicial (REST) y espera a llenar la ventana SMA."""
        if self._state.get_price() is None:
            try:
                price = self._client.get_ticker_price(self._symbol)
                self._state.seed_price(price)
                self._log.info("Precio inicial (REST): %.2f", price)
            except BinanceAPIError as exc:
                self._log.warning("No se pudo obtener el precio inicial: %s", exc)

        self._log.info("Esperando datos del stream para llenar la ventana SMA (%d)...", self._cfg.sma_period)
        while not self._stop.is_set() and self._state.sma() is None:
            time.sleep(0.5)

    # ------------------------------------------------------------------
    # Ciclo principal
    # ------------------------------------------------------------------
    def _process_cycle(self) -> None:
        if self._state.order_in_flight:
            return  # no operar hasta confirmar la orden anterior
        if time.time() < self._next_sell_attempt:
            return  # cooldown tras un fallo de filtro (p. ej. NOTIONAL)

        decision = self._strategy.evaluate()
        if decision is None:
            return

        try:
            if decision.action == "BUY":
                self._execute_buy(decision)
            else:
                self._execute_sell(decision)
        except BinanceAPIError as exc:
            self._log.error("Fallo al ejecutar %s: %s", decision.action, exc)
            self._state.order_in_flight = False
            if exc.code == -1013 and "NOTIONAL" in str(exc):
                self._next_sell_attempt = time.time() + 60
                self._log.error("La orden falló por el filtro NOTIONAL; se reintentará en 60s.")

    def _execute_buy(self, decision: TradeDecision) -> None:
        if self._state.is_busy():
            return  # una sola operación por ciclo

        self._state.order_in_flight = True
        self._log.info(">>> COMPRAR %.4f USDT de %s (precio tick: %.2f)",
                       self._cfg.quote_amount, self._symbol, decision.price)

        order = self._client.market_buy(self._symbol, self._cfg.quote_amount, reference_price=decision.price)

        if order.executed_qty <= 0 or order.status != "FILLED":
            self._log.error("La compra no se ejecutó (status=%s).", order.status)
            self._state.order_in_flight = False
            return

        position = Position(
            symbol=self._symbol,
            buy_order_id=order.order_id,
            buy_price=order.avg_price,
            buy_quantity=order.executed_qty,
            buy_quote=order.quote_qty,
            buy_time=order.transact_time,
            test_mode=self._cfg.test_mode,
        )
        self._state.open_position(position)
        self._state.order_in_flight = False

        self._log.info(
            "COMPRA ejecutada | orderId=%d | qty=%.8f | avg=%.2f | gasto=%.2f USDT",
            order.order_id, order.executed_qty, order.avg_price, order.quote_qty,
        )
        # Reportar en background (no bloquea el trading).
        self._reporter.create_transaction(position)
        self._reporter.report_order(self._symbol, "BUY", order, self._cfg.test_mode)

    def _execute_sell(self, decision: TradeDecision) -> None:
        position = self._state.position
        if position is None:
            return

        # Validación preventiva del notional mínimo: Binance rechaza la orden
        # con -1013 NOTIONAL si la cantidad a vender vale menos que el mínimo.
        try:
            info = self._get_symbol_info()
            notional = position.buy_quantity * decision.price
            if notional < info["min_notional"]:
                self._next_sell_attempt = time.time() + 60
                self._log.error(
                    "Venta bloqueada: nocional %.2f USDT < minNotional %.2f USDT "
                    "(cantidad %.8f). Se reintentará en 60s.",
                    notional, info["min_notional"], position.buy_quantity,
                )
                return
        except BinanceAPIError as exc:
            self._log.warning("No se pudo validar el minNotional: %s", exc)

        self._state.order_in_flight = True
        self._log.info(">>> VENDER %.8f %s (precio tick: %.2f)",
                       position.buy_quantity, position.symbol, decision.price)

        order = self._client.market_sell(self._symbol, position.buy_quantity)

        if order.executed_qty <= 0 or order.status != "FILLED":
            self._log.error("La venta no se ejecutó (status=%s).", order.status)
            self._state.order_in_flight = False
            return

        profit = order.quote_qty - position.buy_quote
        profit_pct = (order.avg_price / position.buy_price - 1.0) * 100.0 if position.buy_price else 0.0

        self._state.close_position(profit)
        self._state.order_in_flight = False

        self._log.info(
            "VENTA ejecutada | orderId=%d | qty=%.8f | avg=%.2f | ingreso=%.2f USDT | ganancia=%.4f USDT (%.2f%%)",
            order.order_id, order.executed_qty, order.avg_price, order.quote_qty, profit, profit_pct,
        )
        if profit <= 0:
            self._log.warning("¡Ganancia <= 0! Revisa el slippage o el margen (SELL_PROFIT_PCT).")

        # Reportar en background.
        self._reporter.close_transaction(position, order, profit, profit_pct)
        self._reporter.report_order(self._symbol, "SELL", order, self._cfg.test_mode)

