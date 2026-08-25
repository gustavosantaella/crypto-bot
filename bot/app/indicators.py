"""Indicadores técnicos (funciones puras, sin dependencias externas).

Calcula SMA, EMA, RSI (Wilder), MACD, Bandas de Bollinger y ATR a partir de
una serie de cierres (o OHLC) de velas. Se usan tanto en el bot (decisión en
tiempo real) como en la API (análisis de mercado para el portal).
"""
from __future__ import annotations

import math
from typing import Iterable


def sma(values: Iterable[float], period: int) -> float | None:
    """Media móvil simple de los últimos ``period`` valores."""
    window = list(values)
    if len(window) < period:
        return None
    return sum(window[-period:]) / period


def ema(values: Iterable[float], period: int) -> list[float]:
    """Serie completa de EMA (exponential moving average) de los valores."""
    data = list(values)
    if not data:
        return []
    k = 2.0 / (period + 1)
    result = [data[0]]
    for price in data[1:]:
        result.append(price * k + result[-1] * (1.0 - k))
    return result


def ema_last(values: Iterable[float], period: int) -> float | None:
    """Último valor de la EMA (o None si no hay suficientes datos)."""
    data = list(values)
    if len(data) < period:
        return None
    return ema(data, period)[-1]


def rsi(values: Iterable[float], period: int = 14) -> float | None:
    """RSI (Wilder's smoothing) con la serie completa de cierres."""
    closes = list(values)
    if len(closes) <= period:
        return None
    gains: list[float] = []
    losses: list[float] = []
    for i in range(1, len(closes)):
        change = closes[i] - closes[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def macd(
    values: Iterable[float],
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, float | None]:
    """MACD + señal + histograma sobre los últimos cierres."""
    closes = list(values)
    if len(closes) < slow + signal:
        return {"macd": None, "signal": None, "hist": None, "prev_macd": None}

    ema_fast = ema(closes, fast)
    ema_slow = ema(closes, slow)
    macd_line = [f - s for f, s in zip(ema_fast, ema_slow)]
    signal_line = ema(macd_line, signal)

    return {
        "macd": macd_line[-1],
        "signal": signal_line[-1],
        "hist": macd_line[-1] - signal_line[-1],
        "prev_macd": macd_line[-2] if len(macd_line) > 1 else None,
    }


def bollinger(
    values: Iterable[float],
    period: int = 20,
    num_std: float = 2.0,
) -> dict[str, float | None]:
    """Bandas de Bollinger (media, superior e inferior) de los últimos cierres."""
    closes = list(values)
    if len(closes) < period:
        return {"upper": None, "middle": None, "lower": None, "width_pct": None}
    window = closes[-period:]
    middle = sum(window) / period
    variance = sum((x - middle) ** 2 for x in window) / period
    std = math.sqrt(variance)
    upper = middle + num_std * std
    lower = middle - num_std * std
    width = (upper - lower) / middle * 100.0 if middle else None
    return {"upper": upper, "middle": middle, "lower": lower, "width_pct": width}


def atr(
    highs: Iterable[float],
    lows: Iterable[float],
    closes: Iterable[float],
    period: int = 14,
) -> float | None:
    """Average True Range (Wilder)."""
    h = list(highs)
    low = list(lows)
    c = list(closes)
    if not (len(h) == len(low) == len(c)) or len(h) <= period:
        return None
    trs: list[float] = []
    for i in range(1, len(h)):
        tr = max(
            h[i] - low[i],
            abs(h[i] - c[i - 1]),
            abs(low[i] - c[i - 1]),
        )
        trs.append(tr)
    if len(trs) < period:
        return None
    atr_val = sum(trs[:period]) / period
    for tr in trs[period:]:
        atr_val = (atr_val * (period - 1) + tr) / period
    return atr_val
def compute_all(
    closes: list[float],
    highs: list[float] | None = None,
    lows: list[float] | None = None,
    ema_fast: int = 12,
    ema_slow: int = 26,
    ema_signal: int = 9,
    ema_trend_fast: int = 50,
    ema_trend_slow: int = 200,
    rsi_period: int = 14,
    rsi_oversold: float = 30.0,
    rsi_overbought: float = 70.0,
    bb_period: int = 20,
) -> dict:
    """Conjunto completo de indicadores + componentes de señal (score).

    Cada componente aporta un valor en [-1, +1]:

    - Tendencia corta: precio vs EMA rápida de tendencia.
    - Tendencia larga: EMA rápida vs EMA lenta (golden/death cross).
    - RSI: -1 si sobrecomprado, +1 si sobrevendido (escala continua).
    - MACD: signo del histograma.
    - Cruce MACD: cruce alcista reciente (+1) / bajista (-1).
    - Bollinger: precio bajo la banda inferior (+1) o sobre la superior (-1).

    El ``score`` final (rango [-6, +6]) suma las componentes ponderadas y se
    usa para recomendar LONG (>= +umbral) o SHORT (<= -umbral).
    """
    result: dict = {
        "sma20": sma(closes, 20),
        "ema50": ema_last(closes, ema_trend_fast),
        "ema200": ema_last(closes, ema_trend_slow),
        "rsi14": rsi(closes, rsi_period),
        "rsi_oversold": rsi_oversold,
        "rsi_overbought": rsi_overbought,
        "macd": None,
        "macd_signal": None,
        "macd_hist": None,
        "bb_upper": None,
        "bb_lower": None,
        "bb_middle": None,
        "atr14": None,
        "score": 0.0,
        "components": {},
        "trend": "neutral",
    }

    price = closes[-1] if closes else None
    if price is None:
        return result

    macd_data = macd(closes, ema_fast, ema_slow, ema_signal)
    result.update({k: v for k, v in macd_data.items()})
    bb = bollinger(closes, bb_period)
    result["bb_upper"] = bb["upper"]
    result["bb_lower"] = bb["lower"]
    result["bb_middle"] = bb["middle"]
    if highs and lows:
        result["atr14"] = atr(highs, lows, closes)

    comp: dict[str, float] = {}

    # --- Tendencia corta: precio vs EMA50 ---
    ema50 = result["ema50"]
    comp["trend_price_vs_ema"] = 1.0 if ema50 and price >= ema50 else -1.0

    # --- Tendencia larga: EMA50 vs EMA200 ---
    ema200 = result["ema200"]
    if ema50 and ema200:
        comp["trend_ema50_vs_ema200"] = 1.0 if ema50 >= ema200 else -1.0
    else:
        comp["trend_ema50_vs_ema200"] = 0.0

    # --- RSI (escala continua) ---
    rsi_val = result["rsi14"]
    if rsi_val is not None:
        if rsi_val <= rsi_oversold:
            comp["rsi"] = 1.0
        elif rsi_val >= rsi_overbought:
            comp["rsi"] = -1.0
        else:
            comp["rsi"] = (50.0 - rsi_val) / 50.0
    else:
        comp["rsi"] = 0.0

    # --- MACD: histograma y cruce ---
    macd_hist = macd_data.get("hist")
    prev_macd = macd_data.get("prev_macd")
    macd_val = macd_data.get("macd")
    sig_val = macd_data.get("signal")
    comp["macd_hist"] = 1.0 if macd_hist is not None and macd_hist > 0 else -1.0
    if (
        macd_hist is not None and macd_val is not None and sig_val is not None
        and prev_macd is not None and prev_macd <= sig_val < macd_val
    ):
        comp["macd_cross"] = 1.0   # cruce alcista
    elif (
        macd_hist is not None and macd_val is not None and sig_val is not None
        and prev_macd is not None and prev_macd >= sig_val > macd_val
    ):
        comp["macd_cross"] = -1.0  # cruce bajista
    else:
        comp["macd_cross"] = 0.0

    # --- Bollinger ---
    if bb["upper"] is not None and bb["lower"] is not None:
        if price <= bb["lower"]:
            comp["bollinger"] = 1.0
        elif price >= bb["upper"]:
            comp["bollinger"] = -1.0
        else:
            mid = bb["middle"] or price
            span = (bb["upper"] - bb["lower"]) / 2 or 1.0
            comp["bollinger"] = max(-1.0, min(1.0, (mid - price) / span))
    else:
        comp["bollinger"] = 0.0

    weights = {
        "trend_price_vs_ema": 1.5,
        "trend_ema50_vs_ema200": 1.5,
        "rsi": 1.0,
        "macd_hist": 1.0,
        "macd_cross": 0.5,
        "bollinger": 0.5,
    }
    score = sum(comp[k] * weights[k] for k in weights)
    result["score"] = round(score, 4)
    result["components"] = comp
    result["trend"] = (
        "bullish" if score >= 1.5 else ("bearish" if score <= -1.5 else "neutral")
    )
    return result


def recommendation(score: float, open_threshold: float) -> str:
    """Traduce el score a recomendación LONG / SHORT / NEUTRAL."""
    if score >= open_threshold:
        return "LONG"
    if score <= -open_threshold:
        return "SHORT"
    return "NEUTRAL"

