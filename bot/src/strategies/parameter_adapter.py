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

    Returns un dict con:
      - rsi_oversold:    Umbral de RSI para considerar el mercado sobrevendido
      - atr_sl_mult:     Multiplicador del ATR para el Stop Loss
      - atr_tp_mult:     Multiplicador del ATR para el Take Profit
      - dca_min_drop:    Caída mínima (%) para activar una entrada DCA
      - dca_rsi_level_2: RSI requerido para activar la 2da entrada DCA
      - dca_rsi_level_3: RSI requerido para activar la 3ra entrada DCA
      - dca_rsi_level_4: RSI requerido para activar la 4ta entrada DCA
      - mode_active:     Modo actual (CONSERVATIVE / SCALPING / SMART)
    """
    adx = ind.get('adx', 20.0)
    volume_ratio = ind.get('volume_ratio', 1.0)

    # ── Modo SCALPING: parámetros sobrescritos por .env, solo retornarlos ──────
    # Los valores ya se aplicaron en trading_params.py al cargar el .env
    if BOT_MODE == "SCALPING":
        return {
            'rsi_oversold':    RSI_OVERSOLD,
            'atr_sl_mult':     ATR_SL_MULTIPLIER,
            'atr_tp_mult':     ATR_TP_MULTIPLIER,
            'dca_min_drop':    DCA_MIN_DROP_PCT,
            'dca_rsi_level_2': DCA_RSI_LEVEL_2,
            'dca_rsi_level_3': DCA_RSI_LEVEL_3,
            'dca_rsi_level_4': DCA_RSI_LEVEL_4,
            'mode_active':     'SCALPING',
        }

    # ── Modo CONSERVATIVE / SMART: calcular dinámicamente ─────────────────────
    #
    # La lógica es la siguiente:
    #
    #  ADX < 20  → Mercado lateral, sin tendencia definida
    #              El bot puede ser más agresivo en las entradas (RSI más alto)
    #              porque el riesgo de tendencia bajista sostenida es bajo.
    #
    #  20 ≤ ADX < ADX_THRESHOLD (25) → Tendencia naciente, zona gris
    #              Parámetros base del .env (sin modificación)
    #
    #  ADX ≥ ADX_THRESHOLD (25) → Tendencia activa y fuerte
    #              El bot exige más confirmación (RSI más bajo) y da más espacio
    #              al SL para evitar ser sacado por ruido en la tendencia.
    #

    if adx < 20.0:
        # Mercado lateral: más oportunidades permitidas
        rsi_oversold    = min(RSI_OVERSOLD + 5.0, 40.0)   # Sube max 5 puntos (tope 40)
        atr_sl_mult     = ATR_SL_MULTIPLIER                 # Sin cambio en SL
        atr_tp_mult     = ATR_TP_MULTIPLIER                 # Sin cambio en TP
        dca_min_drop    = max(DCA_MIN_DROP_PCT * 0.8, 0.01) # DCA 20% más cercano (min 1%)
        dca_rsi_2       = min(DCA_RSI_LEVEL_2 + 3.0, 35.0)  # DCA más accesible
        dca_rsi_3       = min(DCA_RSI_LEVEL_3 + 3.0, 28.0)
        dca_rsi_4       = min(DCA_RSI_LEVEL_4 + 3.0, 23.0)
        mode_label      = 'CONSERVATIVE/LATERAL'

    elif adx >= ADX_THRESHOLD:
        # Tendencia activa: más exigente para entrar, SL más amplio
        rsi_oversold    = max(RSI_OVERSOLD - 5.0, 20.0)    # Baja max 5 puntos (min 20)
        atr_sl_mult     = ATR_SL_MULTIPLIER + 0.5           # SL 0.5 ATR más amplio
        atr_tp_mult     = ATR_TP_MULTIPLIER + 0.5           # TP también más amplio
        dca_min_drop    = min(DCA_MIN_DROP_PCT * 1.3, 0.05) # DCA 30% más lejano (max 5%)
        dca_rsi_2       = max(DCA_RSI_LEVEL_2 - 3.0, 18.0)  # DCA más exigente
        dca_rsi_3       = max(DCA_RSI_LEVEL_3 - 3.0, 14.0)
        dca_rsi_4       = max(DCA_RSI_LEVEL_4 - 3.0, 10.0)
        mode_label      = 'CONSERVATIVE/TRENDING'

    else:
        # Zona gris (ADX 20-25): usar valores base del .env sin modificación
        rsi_oversold    = RSI_OVERSOLD
        atr_sl_mult     = ATR_SL_MULTIPLIER
        atr_tp_mult     = ATR_TP_MULTIPLIER
        dca_min_drop    = DCA_MIN_DROP_PCT
        dca_rsi_2       = DCA_RSI_LEVEL_2
        dca_rsi_3       = DCA_RSI_LEVEL_3
        dca_rsi_4       = DCA_RSI_LEVEL_4
        mode_label      = 'CONSERVATIVE/NEUTRAL'

    return {
        'rsi_oversold':    rsi_oversold,
        'atr_sl_mult':     atr_sl_mult,
        'atr_tp_mult':     atr_tp_mult,
        'dca_min_drop':    dca_min_drop,
        'dca_rsi_level_2': dca_rsi_2,
        'dca_rsi_level_3': dca_rsi_3,
        'dca_rsi_level_4': dca_rsi_4,
        'mode_active':     mode_label,
    }
