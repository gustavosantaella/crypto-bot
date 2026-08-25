"""Motor de trading.

Coordina el stream de precios, la estrategia y las órdenes de Binance.

Garantías de diseño:
- **Una sola operación por ciclo**: mientras haya una posición abierta o una
  orden en vuelo, no se evalúa ninguna operación nueva.
- **Spot**: la venta siempre es mayor que la compra (``SELL_PROFIT_PCT``).
- **Futuros**: abre LONG/SHORT según el score de la estrategia y cierra con
  take-profit, stop-loss o señal en contra.
- **Sin duplicados**: el flag ``order_in_flight`` (bajo lock) impide lanzar
  dos órdenes por error; el stream deduplica ticks por trade id.
- **No bloquea el trading**: los datos se reportan a la API en background
  (ApiReporter).
"""
from __future__ import annotations

import logging
import threading
import time
from datetime import datetime

from config import Config
from .api_client import ApiClient, ApiClientError
from .api_reporter import ApiReporter
from .binance_client import BinanceAPIError, BinanceClient
from .models import Position, TradeDecision
from .price_stream import PriceStream
from .state import TradingState
from .strategy import FuturesStrategy, SMAStrategy


class TradingEngine:
    def __init__(
        self,
        config: Config,
        client: BinanceClient,
        stream: PriceStream,
        state: TradingState,
        strategy: SMAStrategy | FuturesStrategy,
        reporter: ApiReporter,
        api_client: ApiClient,
        logger: logging.Logger,
    ) -> None:
        self._cfg = config
        self._client = client
        self._stream = stream
        self._state = state
        self._strategy = strategy
        self._reporter = reporter
        self._api_client = api_client
        self._log = logger.getChild("engine")
        self._stop = threading.Event()
        self._symbol = config.symbol
        # Caché de los filtros del símbolo (step size, minNotional...).
        self._symbol_info: dict | None = None
        # Timestamp: próxima vez que se permite reintentar una venta tras un
        # fallo de filtro (evita reintentos en bucle cada CHECK_INTERVAL_MS).
        self._next_sell_attempt: float = 0.0
        # Timestamp: próxima vez que se permite reintentar una operación de
        # futuros (apertura/cierre) tras un fallo (cantidad mínima, saldo
        # insuficiente, filtros...). Evita el spam de reintentos cada ciclo.
        self._next_futures_attempt: float = 0.0
        # Heartbeat: último log periódico de estado (para ver actividad).
        self._last_status_log: float = 0.0
        # Acumulador (ms) para el muestreo temporal de la SMA.
        self._sample_accumulator: int = 0
        # Acumulador (ms) para refrescar el análisis de velas en futuros.
        self._analysis_accumulator: int = 0

    @property
    def _is_futures(self) -> bool:
        return self._cfg.trade_mode == "futures"

    def _get_symbol_info(self) -> dict:
        """Filtros del símbolo, obtenidos una sola vez (se cachean)."""
        if self._symbol_info is None:
            self._symbol_info = self._client.get_symbol_info(self._symbol)
        return self._symbol_info

    def _maybe_sample(self) -> None:
        """Muestrea el precio para la SMA cada ``SMA_SAMPLE_MS`` ms.

        La SMA debe reflejar un PERIODO DE TIEMPO (no los últimos ticks, que
        ocurren en milisegundos); si no, precio y media quedan clavados y la
        estrategia nunca detecta caídas para comprar.
        """
        self._sample_accumulator += self._cfg.check_interval_ms
        if self._sample_accumulator >= self._cfg.sma_sample_ms:
            self._sample_accumulator = 0
            self._state.sample()

    def _maybe_refresh_analysis(self) -> None:
        """En futuros, refresca las velas históricas desde REST periódicamente.

        Así el buffer de velas se mantiene sincronizado aunque el stream de
        trades se caiga (se cubren huecos con las klines del servidor).
        """
        if not self._is_futures:
            return
        self._analysis_accumulator += self._cfg.check_interval_ms
        if self._analysis_accumulator < self._cfg.analysis_refresh_ms:
            return
        self._analysis_accumulator = 0
        try:
            klines = self._client.get_klines(
                self._symbol, self._cfg.kline_interval, self._cfg.kline_limit,
            )
            if self._state.candle_buffer is not None:
                self._state.candle_buffer.seed_from_klines(klines)
        except BinanceAPIError as exc:
            self._log.warning("No se pudo refrescar klines: %s", exc)

    # ------------------------------------------------------------------
    # Ciclo de vida
    # ------------------------------------------------------------------
    def run(self) -> None:
        self._log.info(
            "Bot iniciado | mercado=%s | símbolo=%s | modo=%s",
            self._cfg.market_type, self._symbol,
            "TESTNET" if self._cfg.test_mode else "REAL",
        )
        if self._is_futures:
            self._log.info(
                "Futuros | apalancamiento=%dx | margen=%s | TP=+%.2f%% | SL=-%.2f%% | umbral señal=±%.2f",
                self._cfg.leverage, self._cfg.margin_type,
                self._cfg.futures_take_profit_pct, self._cfg.futures_stop_loss_pct,
                self._cfg.signal_open_score,
            )
        else:
            self._log.info("Spot | compra<=SMA*%.2f%% | venta>=compra*+%.2f%%",
                           self._cfg.buy_threshold_pct, self._cfg.sell_profit_pct)
        self._log.info("Stream WebSocket: %s", self._cfg.binance_ws_url)

        self._recover_open_position()
        self._stream.start()
        self._warmup()

        try:
            while not self._stop.is_set():
                self._maybe_sample()
                self._maybe_refresh_analysis()
                self._process_cycle()
                self._log_status(interval=15.0)
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
    # Reconciliación de posiciones al arrancar
    # ------------------------------------------------------------------
    def _recover_open_position(self) -> None:
        """Reconcilia posiciones abiertas al arrancar.

        Si el proceso anterior se cerró con una operación sin cerrar, la
        transacción quedó OPEN en la API. En spot se comprueba que el activo
        siga en la cuenta; en futuros se consulta el ``positionRisk`` de
        Binance y se recupera la posición real (entrada, cantidad y precio de
        liquidación). Si la posición ya no existe, la transacción se cancela.
        """
        if self._is_futures:
            self._recover_open_futures()
        else:
            self._recover_open_spot()

    def _recover_open_spot(self) -> None:
        try:
            open_txs = self._api_client.get_open_transactions(market_type="SPOT")
        except ApiClientError as exc:
            self._log.warning("No se pudo consultar transacciones OPEN (%s); se omite la reconciliación.", exc)
            return
        if not open_txs:
            self._log.info("No hay transacciones OPEN previas; arranque limpio.")
            return

        base_asset = self._cfg.currency
        try:
            balances = self._client.get_account_balances()
        except BinanceAPIError as exc:
            self._log.warning("No se pudo consultar el balance (%s); se omite la reconciliación.", exc)
            return
        base_free = balances.get(base_asset, 0.0)

        position_recovered = False
        for tx in open_txs:
            tx_id = tx["id"]
            buy_qty = float(tx.get("buy_quantity") or 0.0)
            buy_price = float(tx.get("buy_price") or 0.0)
            buy_quote = float(tx.get("buy_quote") or 0.0)
            buy_order_id = int(tx.get("buy_order_id") or 0)

            if not position_recovered and buy_qty > 0 and base_free >= buy_qty * 0.999:
                try:
                    buy_time_ms = int(datetime.fromisoformat(tx["buy_time"]).timestamp() * 1000)
                except (ValueError, KeyError, TypeError):
                    buy_time_ms = int(time.time() * 1000)
                position = Position(
                    symbol=self._symbol,
                    buy_order_id=buy_order_id,
                    buy_price=buy_price,
                    buy_quantity=buy_qty,
                    buy_quote=buy_quote,
                    buy_time=buy_time_ms,
                    test_mode=self._cfg.test_mode,
                    market_type="SPOT",
                    side="LONG",
                    leverage=1,
                )
                self._state.open_position(position)
                position_recovered = True
                self._log.info(
                    "Posición spot recuperada (tx #%s): %.8f %s a %.2f.",
                    tx_id, buy_qty, base_asset, buy_price,
                )
            else:
                try:
                    self._api_client.cancel_transaction(tx_id)
                    self._log.warning(
                        "Transacción OPEN #%s cancelada: activo %s (%.8f) no respaldado en la cuenta spot (libre=%.8f).",
                        tx_id, base_asset, buy_qty, base_free,
                    )
                except ApiClientError as exc:
                    self._log.warning("No se pudo cancelar la transacción #%s: %s", tx_id, exc)

    def _recover_open_futures(self) -> None:
        try:
            open_txs = self._api_client.get_open_transactions(market_type="FUTURES")
        except ApiClientError as exc:
            self._log.warning("No se pudo consultar transacciones OPEN (%s); se omite la reconciliación.", exc)
            return
        try:
            risks = self._client.get_position_risk(self._symbol)
        except BinanceAPIError as exc:
            self._log.warning("No se pudo consultar positionRisk (%s); se omite la reconciliación.", exc)
            return

        live = [r for r in risks if float(r.get("positionAmt", 0) or 0) != 0]
        live_pos = live[0] if live else None

        for tx in open_txs:
            tx_id = tx["id"]
            if live_pos is not None:
                amt = float(live_pos["positionAmt"])
                side = "LONG" if amt > 0 else "SHORT"
                try:
                    buy_time_ms = int(datetime.fromisoformat(tx["buy_time"]).timestamp() * 1000)
                except (ValueError, KeyError, TypeError):
                    buy_time_ms = int(time.time() * 1000)
                position = Position(
                    symbol=self._symbol,
                    buy_order_id=int(tx.get("buy_order_id") or 0),
                    buy_price=float(live_pos.get("entryPrice", 0) or 0),
                    buy_quantity=abs(amt),
                    buy_quote=abs(amt) * float(live_pos.get("entryPrice", 0) or 0),
                    buy_time=buy_time_ms,
                    test_mode=self._cfg.test_mode,
                    market_type="FUTURES",
                    side=side,
                    leverage=int(float(live_pos.get("leverage", 1) or 1)),
                    liquidation_price=(
                        float(live_pos["liquidationPrice"]) if live_pos.get("liquidationPrice") else None
                    ),
                )
                self._state.open_position(position)
                self._log.info(
                    "Posición futuros recuperada (tx #%s): %s %.8f a %.2f (liq=%.2f, apalancamiento=%dx).",
                    tx_id, side, position.buy_quantity, position.buy_price,
                    position.liquidation_price or 0.0, position.leverage,
                )
                live_pos = None  # solo se recupera la primera OPEN
            else:
                try:
                    self._api_client.cancel_transaction(tx_id)
                    self._log.warning(
                        "Transacción OPEN #%s cancelada: no hay posición en Binance Futures para %s.",
                        tx_id, self._symbol,
                    )
                except ApiClientError as exc:
                    self._log.warning("No se pudo cancelar la transacción #%s: %s", tx_id, exc)

    # ------------------------------------------------------------------
    # Arranque
    # ------------------------------------------------------------------
    def _warmup(self) -> None:
        """Prepara el entorno: configura futuros y carga historia de velas."""
        if self._is_futures:
            self._setup_futures_account()

        if self._state.get_price() is None:
            try:
                price = self._client.get_ticker_price(self._symbol)
                self._state.seed_price(price)
                self._log.info("Precio inicial (REST): %.2f", price)
            except BinanceAPIError as exc:
                self._log.warning("No se pudo obtener el precio inicial: %s", exc)

        if self._is_futures:
            self._seed_candles()
            return

        self._log.info("Esperando datos del stream para llenar la ventana SMA (%d)...", self._cfg.sma_period)
        while not self._stop.is_set() and self._state.sma() is None:
            self._maybe_sample()  # muestreo temporal mientras esperamos
            time.sleep(self._cfg.check_interval_ms / 1000.0)

    def _setup_futures_account(self) -> None:
        """Aplica apalancamiento y tipo de margen al símbolo (futuros)."""
        try:
            resp = self._client.set_leverage(self._symbol, self._cfg.leverage)
            self._log.info("Apalancamiento aplicado: %s (%s)", self._symbol, resp.get("leverage"))
        except BinanceAPIError as exc:
            self._log.warning("No se pudo aplicar apalancamiento %dx a %s: %s",
                              self._cfg.leverage, self._symbol, exc)
        try:
            resp = self._client.set_margin_type(self._symbol, self._cfg.margin_type)
            self._log.info("Tipo de margen aplicado: %s", resp)
        except BinanceAPIError as exc:
            self._log.warning("No se pudo aplicar margen %s a %s: %s",
                              self._cfg.margin_type, self._symbol, exc)

    def _seed_candles(self) -> None:
        """Siembra el buffer de velas con klines históricas (futuros)."""
        if self._state.candle_buffer is None:
            return
        try:
            klines = self._client.get_klines(
                self._symbol, self._cfg.kline_interval, self._cfg.kline_limit,
            )
            self._state.candle_buffer.seed_from_klines(klines)
            self._log.info("Velas sembradas: %d (%s) para análisis.", len(klines), self._cfg.kline_interval)
        except BinanceAPIError as exc:
            self._log.warning("No se pudieron obtener klines (%s); el bot esperará al stream.", exc)

    # ------------------------------------------------------------------
    # Heartbeat / estado
    # ------------------------------------------------------------------
    def _log_status(self, interval: float) -> None:
        """Log periódico con el estado del bot (precio, SMA, señal)."""
        now = time.time()
        if now - self._last_status_log < interval:
            return
        self._last_status_log = now

        price = self._state.get_price()
        if price is None:
            return
        position = self._state.position

        if self._is_futures:
            analysis = self._state.last_analysis
            score = (analysis or {}).get("score", 0.0)
            if position is not None:
                self._log.info(
                    "[estado] precio=%.2f | %s ABIERTA (entrada=%.2f, liq=%.2f) | score=%+.2f",
                    price, position.side, position.buy_price,
                    position.liquidation_price or 0.0, score,
                )
            else:
                rec = (
                    "LONG" if score >= self._cfg.signal_open_score
                    else ("SHORT" if score <= -self._cfg.signal_open_score else "NEUTRAL")
                )
                self._log.info(
                    "[estado] precio=%.2f | score=%+.2f | recomendación=%s | sin posición",
                    price, score, rec,
                )
            return

        sma = self._state.sma()
        if position is not None:
            sell_target = position.buy_price * (1.0 + self._cfg.sell_profit_pct / 100.0)
            potential = (sell_target / position.buy_price - 1.0) * 100.0
            self._log.info(
                "[estado] precio=%.2f | posición=ABIERTA (compra=%.2f) | vender si precio>=%.2f (+%.2f%%)",
                price, position.buy_price, sell_target, potential,
            )
        else:
            buy_limit = (sma * (1.0 - self._cfg.buy_threshold_pct / 100.0)) if sma else None
            self._log.info(
                "[estado] precio=%.2f | SMA=%.2f | comprar si precio<=%.2f | sin posición",
                price, sma or 0.0, buy_limit or 0.0,
            )

    # ------------------------------------------------------------------
    # Ciclo principal
    # ------------------------------------------------------------------
    def _process_cycle(self) -> None:
        if self._state.order_in_flight:
            return  # no operar hasta confirmar la orden anterior
        if time.time() < self._next_sell_attempt:
            return  # cooldown tras un fallo de filtro (p. ej. NOTIONAL)
        if time.time() < self._next_futures_attempt:
            return  # cooldown tras un fallo de futuros (cantidad mínima, saldo...)

        decision = self._strategy.evaluate()
        if decision is None:
            return
        if decision.price is None or decision.price <= 0:
            self._log.warning("Precio inválido (%.2f); se omite la decisión %s.", decision.price, decision.action)
            return

        try:
            if decision.action == "BUY":
                self._execute_buy(decision)
            elif decision.action == "SELL":
                self._execute_sell(decision)
            elif decision.action == "LONG_OPEN":
                self._execute_futures_open(decision)
            elif decision.action == "SHORT_OPEN":
                self._execute_futures_open(decision)
            elif decision.action == "LONG_CLOSE":
                self._execute_futures_close(decision)
            elif decision.action == "SHORT_CLOSE":
                self._execute_futures_close(decision)
            else:
                self._log.warning("Acción de estrategia desconocida: %s", decision.action)
        except BinanceAPIError as exc:
            self._log.error("Fallo al ejecutar %s: %s", decision.action, exc)
            self._state.order_in_flight = False
            if exc.code == -1013 and "NOTIONAL" in str(exc):
                self._next_sell_attempt = time.time() + 60
                self._log.error("La orden falló por el filtro NOTIONAL; se reintentará en 60s.")
            if self._is_futures:
                self._next_futures_attempt = time.time() + 60
                self._log.error("Se reintentará la operación de futuros en 60s.")

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
            market_type="SPOT",
            side="LONG",
            leverage=1,
        )
        self._state.open_position(position)
        self._state.order_in_flight = False

        self._log.info(
            "COMPRA ejecutada | orderId=%d | qty=%.8f | avg=%.2f | gasto=%.2f USDT",
            order.order_id, order.executed_qty, order.avg_price, order.quote_qty,
        )
        # Reportar en background (no bloquea el trading).
        self._reporter.create_transaction(position)
        self._reporter.report_order(
            self._symbol, "BUY", order, self._cfg.test_mode,
            market_type="SPOT", position_side="BOTH", leverage=1,
        )

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
        self._reporter.report_order(
            self._symbol, "SELL", order, self._cfg.test_mode,
            market_type="SPOT", position_side="BOTH", leverage=1,
        )

    # ------------------------------------------------------------------
    # Órdenes de futuros (LONG / SHORT)
    # ------------------------------------------------------------------
    def _futures_margin_budget(self) -> float:
        """Margen efectivo: QUOTE_AMOUNT limitado al saldo USDT disponible."""
        margin = self._cfg.quote_amount
        try:
            balances = self._client.get_account_balances()
            available = float(balances.get("USDT", 0.0) or 0.0)
            if available > 0 and available < margin:
                self._log.info(
                    "Saldo disponible (%.2f USDT) < QUOTE_AMOUNT (%.2f); se usa el saldo como margen.",
                    available, margin,
                )
                margin = available
        except BinanceAPIError as exc:
            self._log.warning("No se pudo consultar el saldo disponible: %s", exc)
        return margin

    def _execute_futures_open(self, decision: TradeDecision) -> None:
        if self._state.is_busy():
            return  # una sola operación por ciclo

        side = decision.side  # LONG | SHORT
        self._log.info(">>> ABRIR %s %s (precio tick: %.2f, score=%s)",
                       side, self._symbol, decision.price, decision.score)

        margin = self._futures_margin_budget()
        budget_notional = margin * self._cfg.leverage

        # Validación preventiva: la cantidad mínima del contrato (1 step) no
        # debe exigir más nocional del presupuestado (margen × apalancamiento).
        try:
            info = self._get_symbol_info()
        except BinanceAPIError as exc:
            self._log.warning("No se pudo obtener los filtros del símbolo: %s", exc)
            info = {}
        min_qty = max(float(info.get("min_qty", 0) or 0), float(info.get("step_size", 0) or 0))
        if min_qty > 0:
            min_notional = min_qty * decision.price
            if min_notional > budget_notional:
                self._next_futures_attempt = time.time() + 60
                self._log.error(
                    "No se puede abrir %s %s: la cantidad mínima del contrato es %.8f "
                    "(≈%.2f USDT) y el margen disponible (%.2f USDT × %dx = %.2f USDT de "
                    "nocional) no lo cubre. Aumenta QUOTE_AMOUNT a ≥ %.2f USDT, sube "
                    "LEVERAGE o usa un símbolo con step menor.",
                    side, self._symbol, min_qty, min_notional, margin,
                    self._cfg.leverage, budget_notional,
                    min_notional / self._cfg.leverage,
                )
                return

        self._state.order_in_flight = True
        try:
            quantity = self._client.quantity_for_notional(self._symbol, budget_notional)
            if side == "LONG":
                order = self._client.market_open_long(self._symbol, quantity)
            else:
                order = self._client.market_open_short(self._symbol, quantity)
        except BinanceAPIError:
            self._state.order_in_flight = False
            raise

        if order.executed_qty <= 0 or order.status != "FILLED":
            self._log.error("La apertura %s no se ejecutó (status=%s).", side, order.status)
            self._state.order_in_flight = False
            self._next_futures_attempt = time.time() + 30
            return

        entry = order.avg_price
        leverage = self._cfg.leverage
        tp_pct = self._cfg.futures_take_profit_pct
        sl_pct = self._cfg.futures_stop_loss_pct

        position = Position(
            symbol=self._symbol,
            buy_order_id=order.order_id,
            buy_price=entry,
            buy_quantity=order.executed_qty,
            buy_quote=order.quote_qty,
            buy_time=order.transact_time,
            test_mode=self._cfg.test_mode,
            market_type="FUTURES",
            side=side,
            leverage=leverage,
            margin=round(order.quote_qty / leverage, 10) if leverage else order.quote_qty,
        )
        if leverage > 1:
            factor = 1.0 - 1.0 / leverage if side == "LONG" else 1.0 + 1.0 / leverage
            position.liquidation_price = round(entry * factor, 4)
        if side == "LONG":
            position.take_profit_price = round(entry * (1.0 + tp_pct / 100.0), 4)
            position.stop_loss_price = round(entry * (1.0 - sl_pct / 100.0), 4)
        else:
            position.take_profit_price = round(entry * (1.0 - tp_pct / 100.0), 4)
            position.stop_loss_price = round(entry * (1.0 + sl_pct / 100.0), 4)

        self._state.open_position(position)
        self._state.order_in_flight = False

        self._log.info(
            "%s ABIERTO | orderId=%d | qty=%.8f | entrada=%.2f | nocional=%.2f USDT | margen=%.2f | TP=%.2f | SL=%.2f | liq≈%.2f",
            side, order.order_id, order.executed_qty, entry, order.quote_qty,
            position.margin or 0.0, position.take_profit_price or 0.0,
            position.stop_loss_price or 0.0, position.liquidation_price or 0.0,
        )
        # Reportar en background.
        self._reporter.create_transaction(position)
        self._reporter.report_order(
            self._symbol, "BUY" if side == "LONG" else "SELL", order, self._cfg.test_mode,
            market_type="FUTURES", position_side=side, leverage=leverage,
        )
    def _execute_futures_close(self, decision: TradeDecision) -> None:
        position = self._state.position
        if position is None:
            return

        self._state.order_in_flight = True
        side = position.side
        self._log.info(">>> CERRAR %s %s (precio tick: %.2f, razón: %s)",
                       side, self._symbol, decision.price, decision.reason)

        try:
            if side == "LONG":
                order = self._client.market_close_long(self._symbol, position.buy_quantity)
            else:
                order = self._client.market_close_short(self._symbol, position.buy_quantity)
        except BinanceAPIError:
            self._state.order_in_flight = False
            raise

        if order.executed_qty <= 0 or order.status != "FILLED":
            self._log.error("El cierre %s no se ejecutó (status=%s).", side, order.status)
            self._state.order_in_flight = False
            self._next_futures_attempt = time.time() + 30
            return

        # PnL real en USDT y rentabilidad sobre el margen (con apalancamiento).
        qty = order.executed_qty
        if side == "LONG":
            profit = (order.avg_price - position.buy_price) * qty
            price_pct = (order.avg_price / position.buy_price - 1.0) if position.buy_price else 0.0
        else:
            profit = (position.buy_price - order.avg_price) * qty
            price_pct = (1.0 - order.avg_price / position.buy_price) if position.buy_price else 0.0
        profit_pct = price_pct * position.leverage * 100.0

        self._state.close_position(profit)
        self._state.order_in_flight = False

        self._log.info(
            "%s CERRADO | orderId=%d | qty=%.8f | salida=%.2f | pnl=%.4f USDT (%.2f%% con %dx)",
            side, order.order_id, qty, order.avg_price, profit, profit_pct, position.leverage,
        )
        if profit < 0:
            self._log.warning("Pérdida realizada: revisa SL, slippage y el score de salida.")

        # Reportar en background.
        self._reporter.close_transaction(position, order, profit, profit_pct)
        self._reporter.report_order(
            self._symbol, "SELL" if side == "LONG" else "BUY", order, self._cfg.test_mode,
            market_type="FUTURES", position_side=side, leverage=position.leverage,
        )

