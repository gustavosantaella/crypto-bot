"""
parameter_adapter.py — Adaptador Dinámico de Parámetros

Este módulo calcula en tiempo real los parámetros óptimos de la estrategia
basándose en las condiciones actuales del mercado (ATR, ADX, Volumen).

De esta forma, el bot se adapta solo:
  - Mercado tranquilo   → RSI más alto, DCA más cercano
  - Mercado volátil     → RSI más bajo, SL más amplio
  - Tendencia fuerte    → Mayor exigencia para entrar (solo extremos reales)
"""

from src.config.trading_params import (
    BOT_MODE,
    RSI_OVERSOLD,
    ATR_SL_MULTIPLIER,
    ATR_TP_MULTIPLIER,
    DCA_MIN_DROP_PCT,
    DCA_RSI_LEVEL_2,
    DCA_RSI_LEVEL_3,
    DCA_RSI_LEVEL_4,
    ADX_THRESHOLD,
)


def get_dynamic_params(ind: dict) -> dict:
    """
    Calcula los parámetros dinámicos para el ciclo actual basándose en los
    indicadores técnicos del mercado.

    Returns un dict con parámetros adaptados para LONG y SHORT.
    """
    adx = ind.get('adx', 20.0)
    volume_ratio = ind.get('volume_ratio', 1.0)
    ema_fast = ind.get('ema_fast', 0.0)
    ema_slow = ind.get('ema_slow', 0.0)

    # Valores base para Shorts (Asimetría)
    from src.config.trading_params import RSI_OVERBOUGHT
    rsi_overbought = RSI_OVERBOUGHT
    dca_min_pump = DCA_MIN_DROP_PCT  # Usamos el drop como base para el pump

    # ── Modo SCALPING: parámetros sobrescritos por .env, solo retornarlos ──────
    if BOT_MODE == "SCALPING":
        return {
            'rsi_oversold':    RSI_OVERSOLD,
            'rsi_overbought':  RSI_OVERBOUGHT,
            'atr_sl_mult':     ATR_SL_MULTIPLIER,
            'atr_tp_mult':     ATR_TP_MULTIPLIER,
            'dca_min_drop':    DCA_MIN_DROP_PCT,
            'dca_min_pump':    DCA_MIN_DROP_PCT,
            'dca_rsi_level_2': DCA_RSI_LEVEL_2,
            'dca_rsi_level_3': DCA_RSI_LEVEL_3,
            'dca_rsi_level_4': DCA_RSI_LEVEL_4,
            'mode_active':     'SCALPING',
        }

    # ── Modo CONSERVATIVE / SMART: calcular dinámicamente ─────────────────────
    
    if adx < 20.0:
        # Mercado lateral: más oportunidades permitidas
        rsi_oversold    = min(RSI_OVERSOLD + 5.0, 40.0)   # Sube max 5 puntos (tope 40)
        rsi_overbought   = max(RSI_OVERBOUGHT - 5.0, 55.0)  # Baja max 5 puntos (min 55)
        atr_sl_mult     = ATR_SL_MULTIPLIER                 # Sin cambio en SL
        atr_tp_mult     = ATR_TP_MULTIPLIER                 # Sin cambio en TP
        dca_min_drop    = max(DCA_MIN_DROP_PCT * 0.8, 0.01) # DCA 20% más cercano (min 1%)
        dca_min_pump    = max(DCA_MIN_DROP_PCT * 0.8, 0.01)
        dca_rsi_2       = min(DCA_RSI_LEVEL_2 + 3.0, 35.0)  # DCA más accesible
        dca_rsi_3       = min(DCA_RSI_LEVEL_3 + 3.0, 28.0)
        dca_rsi_4       = min(DCA_RSI_LEVEL_4 + 3.0, 23.0)
        mode_label      = 'CONSERVATIVE/LATERAL'

    elif adx >= ADX_THRESHOLD:
        # Tendencia activa y fuerte
        atr_sl_mult     = ATR_SL_MULTIPLIER + 0.5           # SL 0.5 ATR más amplio
        atr_tp_mult     = ATR_TP_MULTIPLIER + 0.5           # TP también más amplio
        
        # Validar dirección de la tendencia (Punto 1 del usuario)
        if ema_fast > ema_slow:
            # Tendencia ALCISTA fuerte: Permitir Longs exigentes, bloquear Shorts o hacerlos muy estrictos
            rsi_oversold    = max(RSI_OVERSOLD - 5.0, 20.0)    # Baja max 5 puntos (min 20)
            rsi_overbought   = min(RSI_OVERBOUGHT + 5.0, 80.0)  # Shorts casi imposibles
            dca_min_drop    = min(DCA_MIN_DROP_PCT * 1.3, 0.05) # DCA más lejano
            dca_min_pump    = min(DCA_MIN_DROP_PCT * 1.5, 0.06)
            mode_label      = 'CONSERVATIVE/BULL_TREND'
        else:
            # Tendencia BAJISTA fuerte: ¡Bloquear Longs! (Punto 1). Relajar Shorts
            rsi_oversold    = 0.0  # Bloquea compras por completo!
            rsi_overbought   = max(RSI_OVERBOUGHT - 5.0, 55.0)  # Shorts más accesibles
            dca_min_drop    = min(DCA_MIN_DROP_PCT * 1.5, 0.06)
            dca_min_pump    = max(DCA_MIN_DROP_PCT * 0.8, 0.01) # DCA para shorts más cercano
            mode_label      = 'CONSERVATIVE/BEAR_TREND'

        dca_rsi_2       = max(DCA_RSI_LEVEL_2 - 3.0, 18.0)  # DCA más exigente
        dca_rsi_3       = max(DCA_RSI_LEVEL_3 - 3.0, 14.0)
        dca_rsi_4       = max(DCA_RSI_LEVEL_4 - 3.0, 10.0)

    else:
        # Zona gris (ADX 20-25): usar valores base del .env sin modificación
        rsi_oversold    = RSI_OVERSOLD
        rsi_overbought   = RSI_OVERBOUGHT
        atr_sl_mult     = ATR_SL_MULTIPLIER
        atr_tp_mult     = ATR_TP_MULTIPLIER
        dca_min_drop    = DCA_MIN_DROP_PCT
        dca_min_pump    = DCA_MIN_DROP_PCT
        dca_rsi_2       = DCA_RSI_LEVEL_2
        dca_rsi_3       = DCA_RSI_LEVEL_3
        dca_rsi_4       = DCA_RSI_LEVEL_4
        mode_label      = 'CONSERVATIVE/NEUTRAL'

    return {
        'rsi_oversold':    rsi_oversold,
        'rsi_overbought':  rsi_overbought,
        'atr_sl_mult':     atr_sl_mult,
        'atr_tp_mult':     atr_tp_mult,
        'dca_min_drop':    dca_min_drop,
        'dca_min_pump':    dca_min_pump,
        'dca_rsi_level_2': dca_rsi_2,
        'dca_rsi_level_3': dca_rsi_3,
        'dca_rsi_level_4': dca_rsi_4,
        'mode_active':     mode_label,
    }
