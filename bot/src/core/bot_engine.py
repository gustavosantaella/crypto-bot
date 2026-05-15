import time
import logging
from src.core.exchange import ExchangeManager
from src.strategies.rsi_strategy import RSIStrategy
from src.strategies.parameter_adapter import get_dynamic_params
from src.config.trading_params import (
    SYMBOL, CHECK_INTERVAL, LEVERAGE, TIMEFRAME, BOT_MODE,
    DCA_ENABLED, MAX_DCA_ORDERS, DCA_ENTRY_SIZE_PCT, DCA_MIN_DROP_PCT,
    ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER,
    USE_TRAILING_STOP, TRAILING_TRIGGER_ATR,
    RSI_OVERBOUGHT, RSI_OVERSOLD
)
from src.utils.db import log_trade, log_price, update_status, get_last_status, init_db
from src.utils.telegram_notifier import TelegramNotifier
from src.utils.ws_notifier import notify_price_update, notify_status_update, notify_new_trade


class BotEngine:
    def __init__(self):
        self.exchange = ExchangeManager()

        # -- Estado principal ---------------------------------------------------
        self.has_position = False      # True si hay al menos una posición abierta
        self.trade_type = "LONG"       # Tipo: LONG o SHORT

        # ── Gestión de riesgo ─────────────────────────────────────────────────
        self.target_tp = None          # Precio de Take Profit (desde precio promedio)
        self.target_sl = None          # Precio de Stop Loss (desde precio promedio)
        self.breakeven_activated = False  # True si el SL ya fue movido a breakeven

        # ── Estado DCA ────────────────────────────────────────────────────────
        # Lista de entradas: [{"price": float, "quantity": float}, ...]
        self.dca_entries = []
        self.avg_entry_price = None    # Precio promedio ponderado de todas las entradas

        # Optimización: evitar escribir en DB en cada ciclo de 2 segundos
        self.last_candle_ts = None     # Timestamp de la última vela guardada

        # Cooldown anti-spam: si una orden falla, bloquear nuevos intentos por N segundos
        self._buy_blocked_until: float = 0.0  # timestamp unix; 0 = sin bloqueo

        # Recuperar estado previo si el bot se reinicio con posicion abierta
        self._recover_state()
        self._sync_db_status()

    # ─────────────────────────────────────────────────────────────────────────
    # Sincronización con DB y WebSocket
    # ─────────────────────────────────────────────────────────────────────────
    def _sync_db_status(self):
        """Persiste el estado actual en la base de datos y notifica al dashboard."""
        update_status(
            self.has_position,
            self.avg_entry_price,
            self.target_tp,
            self.target_sl,
            self.trade_type
        )
        notify_status_update({
            "has_position":       self.has_position,
            "last_buy_price":     self.avg_entry_price,   # Precio promedio ponderado
            "target_take_profit": self.target_tp,          # TP global (calculado desde avg)
            "target_stop_loss":   self.target_sl,          # SL global (calculado desde avg)
            "trade_type":         self.trade_type,
            # DCA: cuantas entradas hay y el detalle de cada una
            "dca_count":          len(self.dca_entries),
            "max_dca_orders":     MAX_DCA_ORDERS,
            # Lista de entradas DCA con precio y cantidad de cada una
            # [{"price": 95.0, "quantity": 0.1}, {"price": 93.0, "quantity": 0.1}]
            "dca_entries":        self.dca_entries,
            # Trailing stop
            "breakeven":          self.breakeven_activated,
            "updated_at":         None
        })

    # ─────────────────────────────────────────────────────────────────────────
    # Recuperar estado previo al reiniciar el bot
    # ─────────────────────────────────────────────────────────────────────────
    def _recover_state(self):
        """
        Al iniciar, consulta Binance para ver si hay posiciones abiertas.
        Si las hay, reconstruye el estado interno desde la base de datos.
        """
        try:
            positions = self.exchange.client.futures_position_information(symbol=SYMBOL)
            pos = next((p for p in positions if p['symbol'] == SYMBOL), None)
            if pos:
                amount = float(pos['positionAmt'])
                self.has_position = abs(amount) > 0.001
                if self.has_position:
                    self.trade_type = "LONG" if amount > 0 else "SHORT"

            # Recuperar precio de entrada y niveles desde la base de datos
            status = get_last_status()
            if status:
                self.avg_entry_price = float(status.last_buy_price) if status.last_buy_price else None
                self.target_tp = float(status.target_take_profit) if status.target_take_profit else None
                self.target_sl = float(status.target_stop_loss) if status.target_stop_loss else None

                # Si no hay posicion real, limpiar estado para evitar señales fantasma
                if not self.has_position:
                    self._reset_state()

            # Si hay posicion pero avg_entry_price sigue siendo None (posicion huerfana),
            # usar el precio de entrada que reporta Binance directamente
            if self.has_position and not self.avg_entry_price and pos:
                entry_price = float(pos.get('entryPrice', 0))
                if entry_price > 0:
                    self.avg_entry_price = entry_price
                    logging.warning(
                        f"[RECOVERY] Posicion sin historial en DB. "
                        f"Usando precio de entrada de Binance: {entry_price:.4f}"
                    )

            # Reconstruir lista DCA con la posicion actual
            if self.has_position and self.avg_entry_price and pos:
                total_qty = abs(float(pos['positionAmt']))
                self.dca_entries = [{"price": self.avg_entry_price, "quantity": total_qty}]

            logging.info(
                f"Bot iniciado | Posicion: {self.has_position} ({self.trade_type}) | "
                f"DCA: {len(self.dca_entries)}/{MAX_DCA_ORDERS} | "
                f"Avg entrada: {self.avg_entry_price}"
            )
        except Exception as e:
            logging.error(f"Error al recuperar estado: {e}")


    # ─────────────────────────────────────────────────────────────────────────
    # Helpers de estado
    # ─────────────────────────────────────────────────────────────────────────
    def _reset_state(self):
        """Limpia completamente el estado del bot tras cerrar una posición."""
        self.has_position = False
        self.dca_entries = []
        self.avg_entry_price = None
        self.target_tp = None
        self.target_sl = None
        self.breakeven_activated = False

    def _check_notional(self, price, quantity):
        """Verifica que la orden supere el minimo de 10 USDT de Binance Futures."""
        return (price * quantity) >= 10.0

    def _adjust_to_min_notional(self, price, quantity, balance_usdt):
        """
        Si la cantidad calculada no alcanza el minimo notional (10 USDT),
        intenta ajustarla al minimo siempre que el balance lo permita.
        Retorna la cantidad ajustada, o None si no hay balance suficiente.
        """
        MIN_NOTIONAL = 10.0
        if self._check_notional(price, quantity):
            return quantity  # Ya cumple, no ajustar

        # Cantidad minima para cumplir notional (redondeada a 3 decimales)
        min_qty = round((MIN_NOTIONAL / price) + 0.001, 3)
        margin_needed = (min_qty * price) / LEVERAGE

        if balance_usdt >= margin_needed:
            logging.info(
                f"[NOTIONAL] Cantidad ajustada: {quantity:.4f} -> {min_qty:.4f} SOL "
                f"(notional minimo: {min_qty*price:.2f} USDT)"
            )
            return min_qty

        return None  # No hay balance suficiente ni para el minimo

    def _calculate_avg_price(self):
        """
        Calcula el precio promedio ponderado de todas las entradas DCA.
        Fórmula: Σ(precio_i × cantidad_i) / Σ(cantidad_i)
        """
        if not self.dca_entries:
            return None
        total_cost = sum(e["price"] * e["quantity"] for e in self.dca_entries)
        total_qty = sum(e["quantity"] for e in self.dca_entries)
        return total_cost / total_qty if total_qty > 0 else None

    def _total_quantity(self):
        """Suma las cantidades de todas las entradas DCA activas."""
        return sum(e["quantity"] for e in self.dca_entries)

    def _recalculate_sl_tp(self, atr, sl_mult=None, tp_mult=None):
        """
        Recalcula SL y TP desde el precio PROMEDIO usando multiplicadores asimétricos.
        Acepta multiplicadores dinámicos opcionales; si no se pasan, usa los del .env.
        """
        if not self.avg_entry_price:
            return
        effective_sl = sl_mult if sl_mult is not None else ATR_SL_MULTIPLIER
        effective_tp = tp_mult if tp_mult is not None else ATR_TP_MULTIPLIER
        self.target_sl = self.avg_entry_price - (atr * effective_sl)
        self.target_tp = self.avg_entry_price + (atr * effective_tp)

    # ─────────────────────────────────────────────────────────────────────────
    # Trailing Stop / Breakeven
    # ─────────────────────────────────────────────────────────────────────────
    def _check_trailing_stop(self, price, atr):
        """
        Trailing stop conservador: mueve el SL al precio de entrada (breakeven)
        una vez que el precio sube TRAILING_TRIGGER_ATR por encima del promedio.

        Efecto: una vez activado, el peor resultado posible es empate (sin pérdida).
        Solo se activa una vez por trade (no es trailing móvil, es breakeven fijo).
        """
        if not USE_TRAILING_STOP or self.breakeven_activated:
            return  # Ya activado o función deshabilitada

        if not self.avg_entry_price or not self.target_sl:
            return

        # Umbral: precio debe superar avg + (ATR × trigger) para activar breakeven
        trigger_price = self.avg_entry_price + (atr * TRAILING_TRIGGER_ATR)

        if price >= trigger_price:
            # El nuevo SL es el precio de entrada promedio (breakeven)
            new_sl = self.avg_entry_price

            # Solo mover si el nuevo SL es mejor que el actual (nunca bajar el SL)
            if new_sl > self.target_sl:
                old_sl = self.target_sl
                self.target_sl = new_sl
                self.breakeven_activated = True

                # Actualizar la orden SL/TP en Binance con el nuevo SL
                self.exchange.cancel_all_orders(SYMBOL)
                total_qty = self._total_quantity()
                self.exchange.set_sl_tp(SYMBOL, 'BUY', self.target_sl, self.target_tp, total_qty)
                self.exchange.cleanup_duplicate_orders(SYMBOL)

                # Guardar en DB y notificar
                self._sync_db_status()

                logging.info(
                    f"[TRAILING STOP] Breakeven activado | "
                    f"SL movido de {old_sl:.4f} → {self.target_sl:.4f} (precio promedio)"
                )
                TelegramNotifier.notify_breakeven(
                    SYMBOL, price, self.target_sl, self.target_tp
                )

    # ─────────────────────────────────────────────────────────────────────────
    # Abrir entrada DCA
    # ─────────────────────────────────────────────────────────────────────────
    def _open_dca_entry(self, price, atr):
        """
        Ejecuta una orden de compra (LONG) como parte del DCA.

        Proceso:
         1. Calcula la cantidad basada en DCA_ENTRY_SIZE_PCT del balance disponible
         2. Ejecuta la orden de mercado en Binance
         3. Registra la entrada y recalcula precio promedio
         4. Recalcula SL/TP desde el nuevo promedio (asimétrico)
         5. Cancela las órdenes SL/TP anteriores y coloca las nuevas
         6. Notifica por Telegram y WebSocket
        """
        entry_num = len(self.dca_entries) + 1  # Número de esta entrada (1, 2, 3...)
        balance_usdt = self.exchange.get_balance('USDT')
        quantity = (balance_usdt * DCA_ENTRY_SIZE_PCT * LEVERAGE) / price

        # Auto-ajustar al minimo notional si el balance lo permite
        quantity = self._adjust_to_min_notional(price, quantity, balance_usdt)
        if quantity is None:
            logging.warning(
                f"[DCA #{entry_num}] Balance insuficiente para minimo notional. "
                f"Balance: {balance_usdt:.2f} USDT | Precio: {price:.4f}"
            )
            # Cooldown de 5 minutos para no spamear cada 5 segundos
            self._buy_blocked_until = time.time() + 300
            return False

        if self.exchange.execute_market_order(SYMBOL, 'BUY', quantity):
            # Registrar nueva entrada
            self.dca_entries.append({"price": price, "quantity": quantity})
            self.avg_entry_price = self._calculate_avg_price()
            self.has_position = True
            self.trade_type = "LONG"

            # Recalcular SL y TP desde el nuevo precio promedio (asimétrico)
            # Cada vez que promediamos, los niveles se ajustan al nuevo avg
            self._recalculate_sl_tp(atr)

            # Reemplazar órdenes SL/TP anteriores por las nuevas
            self.exchange.cancel_all_orders(SYMBOL)
            self.exchange.set_sl_tp(
                SYMBOL, 'BUY',
                self.target_sl, self.target_tp,
                self._total_quantity()
            )
            self.exchange.cleanup_duplicate_orders(SYMBOL)

            # Registrar trade en la base de datos
            log_trade(
                SYMBOL, 'BUY', price, quantity,
                balance_before=balance_usdt,
                trade_type="LONG",
                target_tp=self.target_tp,
                target_sl=self.target_sl,
                message=f"DCA #{entry_num}/{MAX_DCA_ORDERS} | Avg: {self.avg_entry_price:.4f} | R/R: {ATR_TP_MULTIPLIER/ATR_SL_MULTIPLIER:.1f}x"
            )
            update_status(True, self.avg_entry_price, self.target_tp, self.target_sl, "LONG")

            # Notificar por Telegram
            TelegramNotifier.notify_trade_open(
                SYMBOL, f'LONG DCA #{entry_num}/{MAX_DCA_ORDERS}',
                price, quantity, self.target_tp, self.target_sl
            )

            # Notificar al dashboard
            notify_new_trade({
                "symbol":           SYMBOL,
                "side":             "BUY",
                "price":            price,
                "quantity":         quantity,
                "trade_type":       f"LONG_DCA_{entry_num}",
                "avg_entry_price":  self.avg_entry_price,
                "dca_count":        len(self.dca_entries),
                "target_tp":        self.target_tp,
                "target_sl":        self.target_sl,
                "rr_ratio":         round(ATR_TP_MULTIPLIER / ATR_SL_MULTIPLIER, 2),
                "timestamp":        None
            })

            logging.info(
                f"[DCA #{entry_num}] ✅ Compra | Precio: {price:.4f} | Qty: {quantity:.4f} | "
                f"Avg: {self.avg_entry_price:.4f} | SL: {self.target_sl:.4f} | TP: {self.target_tp:.4f} | "
                f"R/R: {ATR_TP_MULTIPLIER/ATR_SL_MULTIPLIER:.1f}x"
            )
            return True

        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Cerrar posición LONG
    # ─────────────────────────────────────────────────────────────────────────
    def _close_long_position(self, price, reason="Signal"):
        """
        Cierra TODA la posición LONG (todas las entradas DCA a la vez).
        Calcula el PnL real desde el precio promedio ponderado.
        """
        positions = self.exchange.client.futures_position_information(symbol=SYMBOL)
        pos = next((p for p in positions if p['symbol'] == SYMBOL), None)

        if not pos or abs(float(pos['positionAmt'])) == 0:
            logging.warning(f"[SELL] Intento de cierre LONG pero no hay posición activa en Binance.")
            self._reset_state()
            self._sync_db_status()
            return

        qty = abs(float(pos['positionAmt']))

        if self.exchange.execute_market_order(SYMBOL, 'SELL', qty):
            avg_price = self.avg_entry_price or price
            pnl = (price - avg_price) * qty
            entries_info = f"{len(self.dca_entries)} entrada(s) DCA"

            log_trade(
                SYMBOL, 'SELL', price, qty,
                balance_before=qty * price,
                pnl=pnl,
                trade_type="LONG",
                message=f"Cierre | {entries_info} | Razón: {reason} | PnL: {pnl:.4f}"
            )
            TelegramNotifier.notify_trade_close(
                SYMBOL, f'LONG DCA x{len(self.dca_entries)}',
                price, qty, pnl
            )

            # Cancelar órdenes SL/TP pendientes que Binance no ejecutó
            self.exchange.cancel_all_orders(SYMBOL)

            # Notificar al dashboard
            notify_new_trade({
                "symbol":     SYMBOL,
                "side":       "SELL",
                "price":      price,
                "quantity":   qty,
                "trade_type": "LONG",
                "pnl":        pnl,
                "dca_count":  0,
                "timestamp":  None
            })

            logging.info(
                f"[LONG CERRADO] ✅ Precio: {price:.4f} | PnL: {pnl:.4f} USDT | "
                f"Avg entrada: {avg_price:.4f} | Razón: {reason}"
            )

            # Limpiar estado
            self._reset_state()
            self._sync_db_status()

    # ─────────────────────────────────────────────────────────────────────────
    # Ciclo principal del bot
    # ─────────────────────────────────────────────────────────────────────────
    def start(self):
        # Migrar DB al iniciar (agrega columnas nuevas si faltan)
        init_db()

        logging.info("==========================================================")
        logging.info(f"  Bot FUTUROS - Estrategia DCA | Modo: {BOT_MODE}")
        logging.info(f"  DCA: {'Activo' if DCA_ENABLED else 'Inactivo'} | Max entradas: {MAX_DCA_ORDERS}")
        logging.info(f"  Tamano por entrada: {DCA_ENTRY_SIZE_PCT*100:.0f}% | Expo maxima: {DCA_ENTRY_SIZE_PCT*MAX_DCA_ORDERS*100:.0f}%")
        logging.info(f"  R/R base: {ATR_TP_MULTIPLIER}x TP / {ATR_SL_MULTIPLIER}x SL (se ajusta dinamicamente)")
        logging.info(f"  Trailing stop: {'Activo' if USE_TRAILING_STOP else 'Inactivo'}")
        logging.info("==========================================================")

        while True:
            try:
                # ── 1. Obtener datos del mercado ───────────────────────────────
                price = self.exchange.get_ticker_price(SYMBOL)
                klines = self.exchange.get_klines(SYMBOL, interval=TIMEFRAME)

                if not price or not klines:
                    logging.warning("Sin datos del mercado. Reintentando...")
                    time.sleep(CHECK_INTERVAL)
                    continue

                # ── 2. Calcular indicadores ────────────────────────────────────
                # Ahora retorna un dict con todos los indicadores
                ind = RSIStrategy.calculate_indicators(klines)
                atr = ind['atr']
                rsi = ind['rsi']
                adx = ind['adx']

                # ── 2b. Calcular parámetros dinámicos para este ciclo ───────────
                dyn = get_dynamic_params(ind)

                # ── 2c. Recalcular TP/SL si hay posicion abierta pero sin niveles ──
                # Ocurre cuando el bot se reinicia con una posicion abierta y la DB
                # no tenia los niveles guardados (posicion huerfana).
                if self.has_position and self.avg_entry_price and (not self.target_tp or not self.target_sl):
                    self._recalculate_sl_tp(atr, dyn['atr_sl_mult'], dyn['atr_tp_mult'])
                    # Reponer las ordenes SL/TP en Binance
                    self.exchange.cancel_all_orders(SYMBOL)
                    self.exchange.set_sl_tp(
                        SYMBOL, 'BUY' if self.trade_type == 'LONG' else 'SELL',
                        self.target_sl, self.target_tp,
                        self._total_quantity()
                    )
                    self.exchange.cleanup_duplicate_orders(SYMBOL)
                    self._sync_db_status()
                    logging.warning(
                        f"[RECOVERY] TP/SL recalculados desde ATR | "
                        f"Avg: {self.avg_entry_price:.4f} | "
                        f"SL: {self.target_sl:.4f} | TP: {self.target_tp:.4f}"
                    )

                # ── 3. Trailing stop / Breakeven (antes de evaluar señal) ───────
                # Si ya hay posición LONG y está en positivo, proteger ganancias
                if self.has_position and self.trade_type == "LONG":
                    self._check_trailing_stop(price, atr)

                # ── 4. Obtener señal de la estrategia ──────────────────────────
                last_dca_price = self.dca_entries[-1]["price"] if self.dca_entries else None

                signal, new_tp, new_sl = RSIStrategy.get_signal(
                    ind=ind,
                    current_price=price,
                    has_position=self.has_position,
                    target_tp=self.target_tp,
                    target_sl=self.target_sl,
                    trade_type=self.trade_type,
                    dca_count=len(self.dca_entries),
                    last_dca_price=last_dca_price,
                    max_dca_orders=MAX_DCA_ORDERS if DCA_ENABLED else 1,
                    # Pasar parámetros dinámicos calculados en este ciclo
                    dyn_rsi_oversold=dyn['rsi_oversold'],
                    dyn_rsi_overbought=dyn['rsi_overbought'],
                    dyn_dca_rsi_2=dyn['dca_rsi_level_2'],
                    dyn_dca_rsi_3=dyn['dca_rsi_level_3'],
                    dyn_dca_rsi_4=dyn['dca_rsi_level_4'],
                    dyn_atr_sl_mult=dyn['atr_sl_mult'],
                    dyn_atr_tp_mult=dyn['atr_tp_mult']
                )

                # -- 5. Persistir precio + indicadores en DB solo cuando cambie la vela --
                # Esto reduce drásticamente el uso de CPU y disco, y hace que la IA aprenda mejor
                # de un histórico más amplio en lugar de saturarse con datos de cada 2 segundos.
                current_candle_ts = ind.get('timestamp')
                if current_candle_ts != self.last_candle_ts:
                    log_price(SYMBOL, price, ind)
                    self.last_candle_ts = current_candle_ts

                # -- 6. Log del ciclo con distancias --
                target_oversold = dyn['rsi_oversold']
                target_overbought = dyn['rsi_overbought']
                
                if self.has_position:
                    if self.trade_type == "LONG":
                        dist_rsi = target_overbought - rsi
                        rsi_status = f"Falta {dist_rsi:.1f} para >{target_overbought:.1f}" if dist_rsi > 0 else "TP Alcanzado"
                    else:
                        dist_rsi = rsi - target_oversold
                        rsi_status = f"Falta {dist_rsi:.1f} para <{target_oversold:.1f}" if dist_rsi > 0 else "TP Alcanzado"
                else:
                    dist_to_oversold = rsi - target_oversold
                    dist_to_overbought = target_overbought - rsi
                    
                    if dist_to_oversold < dist_to_overbought:
                        rsi_status = f"Falta {dist_to_oversold:.1f} para <{target_oversold:.1f}" if dist_to_oversold > 0 else "Entrada"
                    else:
                        rsi_status = f"Falta {dist_to_overbought:.1f} para >{target_overbought:.1f}" if dist_to_overbought > 0 else "Entrada"

                                # ADX
                target_adx = 30.0 if dyn['mode_active'] == 'AGGRESSIVE' else 20.0  # más permisivo
                # Si ADX es menor al target, está OK; si es mayor, sigue permitiendo la operación en modo conservador.
                adx_status = "EXTREMO" if adx > target_adx else "OK"

                # Volumen (solo informativo, no bloquea la entrada)
                vol_ratio = ind.get('volume_ratio', 1.0)
                vol_status = f"{vol_ratio:.2f}x del promedio"

                # Evaluar las 4 condiciones del portal para el log
                looking_for_short = rsi > 50
                
                cond_vol = True  # Volumen desactivado como condición de entrada
                
                if looking_for_short:
                    cond_rsi = rsi > dyn['rsi_overbought']
                    
                    # Contexto de giro bajista (top-catching)
                    rsi_prev = ind.get('rsi_prev', 50)
                    cond_context = (rsi < rsi_prev) and (ind.get('minus_di', 0) >= ind.get('plus_di', 0))
                    
                    if dyn['mode_active'] == 'AGGRESSIVE':
                        is_uptrend_hard = adx > 45 and ind.get('plus_di', 0) > ind.get('minus_di', 0)
                    else:
                        is_uptrend_hard = adx > 25 and ind.get('plus_di', 0) > ind.get('minus_di', 0)
                    cond_trend = not is_uptrend_hard
                else:
                    cond_rsi = rsi < dyn['rsi_oversold']
                    # Umbral unificado: solo bloquear LONG si ADX > 45 (igual que estrategia y portal)
                    cond_context = True  # EMA desactivado a petición del usuario
                    is_downtrend_hard = adx > 45 and ind.get('minus_di', 0) > ind.get('plus_di', 0)
                    cond_trend = not is_downtrend_hard
                    
                conditions_met_count = sum([cond_rsi, cond_context, cond_trend, cond_vol])
                logging.info(
                    f"[{SYMBOL}] P: {price:.4f} | RSI: {rsi:.1f} ({rsi_status}) | "
                    f"ADX: {adx:.1f} ({adx_status}) | Vol: {vol_ratio:.2f}x ({vol_status}) | "
                    f"Cond: {conditions_met_count}/4 | Signal: {signal} | "
                    f"DCA: {len(self.dca_entries)}/{MAX_DCA_ORDERS} | "
                    f"Mode: {dyn['mode_active']}"
                )
                # Añadir umbrales activos al payload para que el portal los muestre correctamente
                ind['rsi_oversold']   = dyn.get('rsi_oversold', RSI_OVERSOLD)
                ind['rsi_overbought'] = dyn.get('rsi_overbought', RSI_OVERBOUGHT)
                notify_price_update(SYMBOL, price, ind)

                # -- 7. Resumen periódico de estado a Telegram (cada 5 min) ------
                TelegramNotifier.maybe_send_status(
                    symbol=SYMBOL, price=price, ind=ind, dyn=dyn,
                    has_position=self.has_position,
                    avg_price=self.avg_entry_price,
                    target_tp=self.target_tp,
                    target_sl=self.target_sl,
                    dca_count=len(self.dca_entries),
                    max_dca=MAX_DCA_ORDERS,
                    breakeven=self.breakeven_activated
                )

                # ── 6. Ejecutar señal ──────────────────────────────────────────

                if signal == 'BUY':
                    # Primera entrada LONG — verificar cooldown anti-spam
                    if time.time() < self._buy_blocked_until:
                        wait_s = int(self._buy_blocked_until - time.time())
                        logging.info(f"[BUY] Bloqueado por cooldown. Reintento en {wait_s}s")
                    else:
                        logging.info(
                            f"[BUY] Primera entrada LONG | "
                            f"RSI: {rsi:.1f} | Precio: {price:.4f} | EMA200: {ind['ema_slow']:.2f} | "
                            f"Vol: {ind['volume_ratio']:.2f}x"
                        )
                        self._open_dca_entry(price, atr)

                elif signal == 'BUY_DCA' and DCA_ENABLED:
                    # Entrada DCA adicional — validar distancia minima de precio
                    if last_dca_price:
                        drop_pct = (last_dca_price - price) / last_dca_price
                        if drop_pct >= DCA_MIN_DROP_PCT:
                            logging.info(
                                f"[BUY_DCA] Entrada #{len(self.dca_entries)+1} | "
                                f"Caida: {drop_pct*100:.2f}% | RSI: {rsi:.1f}"
                            )
                            self._open_dca_entry(price, atr)
                        else:
                            logging.info(
                                f"[BUY_DCA] Ignorado - caida insuficiente: "
                                f"{drop_pct*100:.2f}% (min: {DCA_MIN_DROP_PCT*100:.1f}%)"
                            )

                elif signal == 'SELL_SHORT':
                    # Abrir SHORT — sin DCA en modo conservador
                    balance_usdt = self.exchange.get_balance('USDT')
                    sell_qty = (balance_usdt * DCA_ENTRY_SIZE_PCT * LEVERAGE) / price

                    if self._check_notional(price, sell_qty):
                        if self.exchange.execute_market_order(SYMBOL, 'SELL', sell_qty):
                            self.has_position = True
                            self.trade_type = "SHORT"
                            self.avg_entry_price = price
                            self.target_tp = new_tp
                            self.target_sl = new_sl
                            self.dca_entries = [{"price": price, "quantity": sell_qty}]

                            self.exchange.set_sl_tp(SYMBOL, 'SELL', self.target_sl, self.target_tp, sell_qty)
                            log_trade(SYMBOL, 'SELL', price, sell_qty,
                                      balance_before=balance_usdt, trade_type="SHORT",
                                      target_tp=self.target_tp, target_sl=self.target_sl)
                            update_status(True, price, self.target_tp, self.target_sl, "SHORT")
                            TelegramNotifier.notify_trade_open(
                                SYMBOL, 'SHORT', price, sell_qty, self.target_tp, self.target_sl
                            )
                            self._sync_db_status()
                            logging.info(f"[SHORT] Abierto | Precio: {price:.4f}")

                elif signal == 'SELL':
                    # Cerrar posicion LONG
                    if self.target_sl and price <= self.target_sl:
                        reason = "Stop Loss"
                    elif self.target_tp and price >= self.target_tp:
                        reason = "Take Profit"
                    else:
                        reason = "RSI Sobrecomprado"
                    self._close_long_position(price, reason=reason)

                elif signal == 'BUY_BACK':
                    # Cerrar posición SHORT
                    positions = self.exchange.client.futures_position_information(symbol=SYMBOL)
                    pos = next((p for p in positions if p['symbol'] == SYMBOL), None)
                    if pos:
                        qty = abs(float(pos['positionAmt']))
                        if qty > 0 and self.exchange.execute_market_order(SYMBOL, 'BUY', qty):
                            avg_price = self.avg_entry_price or price
                            pnl = (avg_price - price) * qty
                            log_trade(SYMBOL, 'BUY', price, qty,
                                      balance_before=qty * price, pnl=pnl, trade_type="SHORT")
                            TelegramNotifier.notify_trade_close(SYMBOL, 'SHORT', price, qty, pnl)
                            self.exchange.cancel_all_orders(SYMBOL)
                            self._reset_state()
                            self._sync_db_status()
                            notify_new_trade({
                                "symbol": SYMBOL, "side": "BUY", "price": price,
                                "quantity": qty, "trade_type": "SHORT", "pnl": pnl
                            })
                            logging.info(f"[SHORT CERRADO] PnL: {pnl:.4f} USDT")
                    else:
                        logging.warning("[BUY_BACK] Sin posicion SHORT en Binance.")

            except Exception as e:
                logging.error(f"Error en ciclo del bot: {e}", exc_info=True)
                TelegramNotifier.notify_error("Ciclo principal del bot", e)
                time.sleep(20)

            time.sleep(CHECK_INTERVAL)
