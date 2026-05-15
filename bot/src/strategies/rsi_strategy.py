import pandas as pd
from src.config.trading_params import (
    RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT,
    ATR_PERIOD, ATR_SL_MULTIPLIER, ATR_TP_MULTIPLIER,
    ADX_PERIOD, ADX_THRESHOLD,
    EMA_FAST_PERIOD, EMA_SLOW_PERIOD,
    DCA_RSI_LEVEL_2, DCA_RSI_LEVEL_3, DCA_RSI_LEVEL_4,
    BOT_MODE
)
# Defaults from config — can be overridden per-cycle by parameter_adapter


class RSIStrategy:

    @staticmethod
    def calculate_indicators(data):
        """
        Calcula todos los indicadores técnicos necesarios para la estrategia.

        Retorna un diccionario con:
          rsi         → RSI actual (último período)
          rsi_prev    → RSI del período anterior (para detectar si está subiendo)
          atr         → ATR actual (volatilidad)
          adx         → ADX actual (fuerza de tendencia)
          plus_di     → DI+ (presión compradora)
          minus_di    → DI- (presión vendedora)
          ema_fast    → EMA rápida (ej: EMA50)
          ema_slow    → EMA lenta (ej: EMA200), filtro de tendencia macro
          volume_ratio→ Ratio volumen actual vs promedio (>1.0 = volumen alto)
        """
        df = pd.DataFrame(
            data,
            columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ct', 'qa', 'nt', 'tb', 'tq', 'i']
        )
        df['c'] = df['c'].astype(float)
        df['h'] = df['h'].astype(float)
        df['l'] = df['l'].astype(float)
        df['v'] = df['v'].astype(float)

        # ── 1. RSI (Relative Strength Index) ──────────────────────────────────
        # RSI < 30: mercado sobrevendido → oportunidad de compra
        # RSI > 70: mercado sobrecomprado → oportunidad de venta / cierre
        # rsi_prev nos permite detectar si el RSI está "girando" hacia arriba,
        # lo que confirma que el momentum bajista está agotándose.
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = loss.replace(0, 0.00001)  # Evitar división por cero
        rs = gain / loss
        rsi_series = 100 - (100 / (1 + rs))

        # ── 2. ATR (Average True Range) ───────────────────────────────────────
        # Mide la volatilidad real del mercado usando máximos, mínimos y cierre.
        # Un ATR alto = mercado volátil → SL y TP más amplios.
        # Un ATR bajo = mercado tranquilo → SL y TP más ajustados.
        df['tr'] = pd.concat([
            df['h'] - df['l'],
            (df['h'] - df['c'].shift()).abs(),
            (df['l'] - df['c'].shift()).abs()
        ], axis=1).max(axis=1)
        atr_series = df['tr'].rolling(window=ATR_PERIOD).mean()

        # ── 3. ADX + DI (Average Directional Index) ───────────────────────────
        # ADX > 25: tendencia fuerte (puede ser alcista o bajista)
        # plus_di > minus_di: presión compradora domina → tendencia alcista
        # minus_di > plus_di: presión vendedora domina → tendencia bajista
        up_move = df['h'] - df['h'].shift(1)
        down_move = df['l'].shift(1) - df['l']

        plus_dm = pd.Series(0.0, index=df.index)
        minus_dm = pd.Series(0.0, index=df.index)
        plus_dm[(up_move > down_move) & (up_move > 0)] = up_move[(up_move > down_move) & (up_move > 0)]
        minus_dm[(down_move > up_move) & (down_move > 0)] = down_move[(down_move > up_move) & (down_move > 0)]

        alpha = 1 / ADX_PERIOD
        tr_smooth = df['tr'].ewm(alpha=alpha, adjust=False).mean()
        plus_di_series = 100 * (plus_dm.ewm(alpha=alpha, adjust=False).mean() / tr_smooth)
        minus_di_series = 100 * (minus_dm.ewm(alpha=alpha, adjust=False).mean() / tr_smooth)

        dx = 100 * (abs(plus_di_series - minus_di_series) / (plus_di_series + minus_di_series).replace(0, 1))
        adx_series = dx.ewm(alpha=alpha, adjust=False).mean()

        # ── 4. EMA (Exponential Moving Average) — Filtro de tendencia macro ───
        # EMA lenta (200): Si el precio está por debajo, estamos en mercado bajista.
        #   → No abrir LONG si precio < EMA200 (evita comprar en tendencia bajista).
        # EMA rápida (50): Para detectar micro-tendencia y posibles resistencias.
        ema_fast_series = df['c'].ewm(span=EMA_FAST_PERIOD, adjust=False).mean()
        ema_slow_series = df['c'].ewm(span=EMA_SLOW_PERIOD, adjust=False).mean()

        # ── 5. Ratio de Volumen ────────────────────────────────────────────────
        # Compara el volumen actual con el promedio de las últimas 20 velas.
        # volume_ratio > 1.2: hay interés institucional confirmando el movimiento.
        # Un RSI bajo CON volumen alto = fuerza de la señal de compra.
        avg_volume = df['v'].rolling(window=20).mean()
        volume_ratio = df['v'].iloc[-1] / avg_volume.iloc[-1] if avg_volume.iloc[-1] > 0 else 1.0

        return {
            'rsi':          rsi_series.iloc[-1],
            'rsi_prev':     rsi_series.iloc[-2],   # RSI de la vela anterior
            'atr':          atr_series.iloc[-1],
            'adx':          adx_series.iloc[-1],
            'plus_di':      plus_di_series.iloc[-1],
            'minus_di':     minus_di_series.iloc[-1],
            'ema_fast':     ema_fast_series.iloc[-1],
            'ema_slow':     ema_slow_series.iloc[-1],
            'volume_ratio': volume_ratio,
            'timestamp':    df['ts'].iloc[-1],     # Timestamp de la vela actual
        }

    @staticmethod
    def get_signal(ind, current_price, has_position,
                   target_tp=None, target_sl=None,
                   trade_type="LONG",
                   dca_count=0, last_dca_price=None, max_dca_orders=3,
                   # Parámetros dinámicos — si no se pasan, se usan los valores del .env
                   dyn_rsi_oversold=None,
                   dyn_rsi_overbought=None,
                   dyn_dca_rsi_2=None,
                   dyn_dca_rsi_3=None,
                   dyn_dca_rsi_4=None,
                   dyn_atr_sl_mult=None,
                   dyn_atr_tp_mult=None):
        """
        Genera la señal de trading con filtros múltiples para máxima calidad.
        """
        rsi = ind['rsi']
        rsi_prev = ind['rsi_prev']
        atr = ind['atr']
        adx = ind['adx']
        plus_di = ind['plus_di']
        minus_di = ind['minus_di']
        ema_fast = ind['ema_fast']
        ema_slow = ind['ema_slow']
        volume_ratio = ind['volume_ratio']

        # Usar parámetros dinámicos si se pasaron, si no usar los del .env como fallback
        effective_rsi_oversold = dyn_rsi_oversold if dyn_rsi_oversold is not None else RSI_OVERSOLD
        effective_rsi_overbought = dyn_rsi_overbought if dyn_rsi_overbought is not None else RSI_OVERBOUGHT
        effective_sl_mult      = dyn_atr_sl_mult  if dyn_atr_sl_mult  is not None else ATR_SL_MULTIPLIER
        effective_tp_mult      = dyn_atr_tp_mult  if dyn_atr_tp_mult  is not None else ATR_TP_MULTIPLIER
        effective_dca_rsi_2    = dyn_dca_rsi_2    if dyn_dca_rsi_2    is not None else DCA_RSI_LEVEL_2
        effective_dca_rsi_3    = dyn_dca_rsi_3    if dyn_dca_rsi_3    is not None else DCA_RSI_LEVEL_3
        effective_dca_rsi_4    = dyn_dca_rsi_4    if dyn_dca_rsi_4    is not None else DCA_RSI_LEVEL_4

        # Distancias ASIMÉTRICAS calculadas con multiplicadores efectivos (dinámicos o base)
        sl_dist = atr * effective_sl_mult
        tp_dist = atr * effective_tp_mult

        # Hard Stop Fallback (Punto 3 del usuario):
        # Si el ATR da un valor muy loco (demasiado grande), limitamos el SL al porcentaje fijo del .env.
        from src.config.trading_params import STOP_LOSS_PCT
        hard_sl_dist = current_price * STOP_LOSS_PCT
        if hard_sl_dist > 0 and sl_dist > hard_sl_dist:
            sl_dist = hard_sl_dist

        # Banderas de tendencia
        is_strong_trend   = adx > ADX_THRESHOLD         # Hay tendencia fuerte
        is_uptrend_di     = plus_di > minus_di          # DI+ > DI- = alcista
        is_downtrend_hard = is_strong_trend and not is_uptrend_di  # Tendencia bajista fuerte

        # Filtro de tendencia EMA desactivado globalmente a petición del usuario
        price_above_ema_slow = True
        
        if BOT_MODE == "AGGRESSIVE":
            # En modo agresivo relajamos el filtro de tendencia bajista, pero lo mantenemos si el ADX es extremo (>45)
            is_downtrend_hard = adx > 45.0 and not is_uptrend_di
        elif BOT_MODE == "SCALPING":
            is_downtrend_hard = adx > (ADX_THRESHOLD + 5) and not is_uptrend_di

        # RSI girando hacia arriba: el momentum bajista se está agotando
        rsi_turning_up = rsi > rsi_prev

        # Confirmación de volumen — desactivado como condición de entrada (solo informativo)
        volume_confirms = True

        # ── Sin posición: evaluar si abrir ────────────────────────────────────
        if not has_position:

            # ── Señal LONG ────────────────────────────────────────────────────
            # Condiciones de entrada (todas deben cumplirse para ser conservador):
            rsi_oversold_ok = rsi < effective_rsi_oversold  # Cond 1: RSI sobrevendido (dinámico)
            trend_ok        = not is_downtrend_hard          # Cond 2: No en tendencia bajista fuerte
            macro_trend_ok  = price_above_ema_slow           # Cond 3: Precio sobre EMA lenta

            if rsi_oversold_ok and trend_ok and macro_trend_ok:
                # Entrada confirmada: RSI bajo + mercado alcista + sin tendencia bajista
                tp = current_price + tp_dist
                sl = current_price - sl_dist
                return 'BUY', tp, sl

            # ── Señal SHORT ───────────────────────────────────────────────────
            # Short counter-trend agresivo (Top-catching) según feedback del usuario:
            # Permite shortear el tope de una tendencia si el RSI está sobrecomprado, 
            # el RSI empezó a caer, la presión vendedora supera la compradora (DI- > DI+), y hay volumen.
            rsi_overbought   = rsi > effective_rsi_overbought
            
            # Condición de contexto bajista (puede ser clásico bajo la EMA, o tope alcista sobre la EMA)
            # Para simplificar y hacer lo que el usuario pide (short en pleno precio alto):
            # No exigiremos que el precio esté bajo la EMA200. Solo que el momentum se agote.
            # Señal de agotamiento alcista: basta con que la presión vendedora domine
            # O que el RSI esté cayendo. No se exige las dos simultáneamente.
            bearish_pressure = minus_di >= plus_di       # DI- >= DI+ (vendedores dominan)
            rsi_falling      = rsi < rsi_prev            # RSI girando a la baja
            momentum_agotado = bearish_pressure or rsi_falling
            no_uptrend_hard  = not (is_strong_trend and is_uptrend_di)

            if rsi_overbought and momentum_agotado and no_uptrend_hard:
                tp = current_price - tp_dist
                sl = current_price + sl_dist
                return 'SELL_SHORT', tp, sl

        # ── Con posición LONG activa ───────────────────────────────────────────
        elif trade_type == "LONG":

            # Prioridad 1: verificar condiciones de cierre ANTES de evaluar DCA
            # Stop Loss: el precio cayó hasta nuestro nivel de pérdida máxima
            if target_sl and current_price <= target_sl:
                return 'SELL', None, None

            # Take Profit: el precio alcanzó nuestro objetivo de ganancia
            if target_tp and current_price >= target_tp:
                return 'SELL', None, None

            # RSI en sobrecompra extrema: el mercado podría revertir pronto
            if rsi > effective_rsi_overbought:
                return 'SELL', None, None

            # Prioridad 2: evaluar si agregar una entrada DCA adicional
            # Solo si aún no llegamos al máximo de entradas
            if dca_count < max_dca_orders and last_dca_price is not None:
                # Cada nivel DCA requiere un RSI más bajo (umbrales dinámicos o del .env)
                rsi_thresholds = {
                    1: effective_dca_rsi_2,
                    2: effective_dca_rsi_3,
                    3: effective_dca_rsi_4,
                }
                required_rsi = rsi_thresholds.get(dca_count)

                if required_rsi and rsi < required_rsi:
                    # No entrar en DCA si hay tendencia bajista brutal confirmada
                    # (ADX muy fuerte + DI bajista = mejor no promediar a la baja)
                    if adx > (ADX_THRESHOLD + 10) and is_downtrend_hard:
                        pass  # Tendencia bajista demasiado fuerte, no agregar
                    else:
                        tp = current_price + tp_dist
                        sl = current_price - sl_dist
                        return 'BUY_DCA', tp, sl

        # ── Con posición SHORT activa ──────────────────────────────────────────
        elif trade_type == "SHORT":
            if target_sl and current_price >= target_sl:
                return 'BUY_BACK', None, None  # Stop Loss alcanzado
            if target_tp and current_price <= target_tp:
                return 'BUY_BACK', None, None  # Take Profit alcanzado
            if rsi < RSI_OVERSOLD:
                return 'BUY_BACK', None, None  # RSI sobrevendido → cerrar SHORT

        # Sin señal clara
        return 'HOLD', target_tp, target_sl
