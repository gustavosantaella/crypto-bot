"""Analizador de mercado para el portal (señal LONG/SHORT/NEUTRAL).

Consulta los endpoints públicos de Binance (klines, ticker 24h y funding)
y calcula indicadores (RSI, MACD, EMA, Bollinger, ATR) junto con un score
compuesto. El score se traduce a una recomendación:

- ``score >= umbral``  -> LONG  (momento de comprar / abrir largo)
- ``score <= -umbral`` -> SHORT (momento de vender / abrir corto)
- si no                -> NEUTRAL

Se usa desde ``GET /api/analysis/signal`` y desde el hilo de eventos SSE.
"""
from __future__ import annotations

import logging
import time

import requests

from .config import settings
from .indicators import compute_all, recommendation

_logger = logging.getLogger("crypto_api.analysis")

_UMBRAL = 1.5  # umbral por defecto para abrir posición


def _base_url(market_type: str, test_mode: bool) -> str:
    is_futures = market_type.upper() == "FUTURES"
    if is_futures:
        return "https://testnet.binancefuture.com" if test_mode else "https://fapi.binance.com"
    return "https://testnet.binance.vision" if test_mode else "https://api.binance.com"


class MarketAnalyzer:
    """Analiza un símbolo en spot o futuros (solo endpoints públicos)."""

    def __init__(
        self,
        symbol: str,
        interval: str | None = None,
        limit: int | None = None,
        open_threshold: float = _UMBRAL,
    ) -> None:
        self._symbol = symbol
        self._interval = interval or settings.kline_interval
        self._limit = limit or settings.kline_limit
        self._open_threshold = open_threshold

    # ------------------------------------------------------------------
    # Fetch
    # ------------------------------------------------------------------
    def _get(self, market_type: str, test_mode: bool, path: str, params: dict | None = None) -> dict | list:
        url = f"{_base_url(market_type, test_mode)}{path}"
        try:
            resp = requests.get(url, params=params, timeout=10)
        except requests.RequestException as exc:
            _logger.warning("Fallo de red al analizar %s: %s", self._symbol, exc)
            raise RuntimeError(f"error de red: {exc}") from exc
        if resp.status_code >= 400:
            raise RuntimeError(f"Binance {resp.status_code}: {resp.text[:200]}")
        return resp.json()

    def fetch_klines(self, market_type: str, test_mode: bool) -> list[list]:
        path = "/fapi/v1/klines" if market_type.upper() == "FUTURES" else "/api/v3/klines"
        return self._get(market_type, test_mode, path, {
            "symbol": self._symbol, "interval": self._interval, "limit": self._limit,
        })

    def fetch_ticker24(self, market_type: str, test_mode: bool) -> dict:
        path = "/fapi/v1/ticker/24hr" if market_type.upper() == "FUTURES" else "/api/v3/ticker/24hr"
        return self._get(market_type, test_mode, path, {"symbol": self._symbol})

    def fetch_funding(self, test_mode: bool) -> dict:
        """Funding / mark / index price (solo futuros)."""
        data = self._get("FUTURES", test_mode, "/fapi/v1/premiumIndex", {"symbol": self._symbol})
        return data if isinstance(data, dict) else {}
    # ------------------------------------------------------------------
    # Análisis
    # ------------------------------------------------------------------
    def analyze(self, market_type: str | None = None, test_mode: bool | None = None) -> dict:
        """Devuelve el payload completo de análisis para el portal."""
        market_type = (market_type or settings.market_type).upper()
        if market_type not in ("SPOT", "FUTURES"):
            market_type = "SPOT"
        test_mode = settings.test_mode if test_mode is None else test_mode

        klines = self.fetch_klines(market_type, test_mode)
        if not klines:
            raise RuntimeError("no hay velas disponibles")

        closes = [float(k[4]) for k in klines]
        highs = [float(k[2]) for k in klines]
        lows = [float(k[3]) for k in klines]
        volumes = [float(k[5]) for k in klines]
        price = closes[-1]

        ind = compute_all(
            closes=closes,
            highs=highs,
            lows=lows,
            ema_fast=settings.ema_fast,
            ema_slow=settings.ema_slow,
            ema_signal=settings.ema_signal,
            ema_trend_fast=settings.ema_trend_fast,
            ema_trend_slow=settings.ema_trend_slow,
            rsi_period=settings.rsi_period,
            rsi_oversold=settings.rsi_oversold,
            rsi_overbought=settings.rsi_overbought,
        )

        score = float(ind["score"])
        rec = recommendation(score, self._open_threshold)
        confidence = min(100.0, round(abs(score) / 6.0 * 100.0))

        payload: dict = {
            "market_type": market_type,
            "test_mode": test_mode,
            "symbol": self._symbol,
            "price": price,
            "interval": self._interval,
            "change_24h_pct": None,
            "funding_rate": None,
            "mark_price": None,
            "index_price": None,
            "indicators": ind,
            "trend": ind["trend"],
            "score": score,
            "recommendation": rec,
            "confidence_pct": confidence,
            "summary": self._summary(rec, ind, market_type),
            "time": int(time.time() * 1000),
        }

        # Volumen total en el rango analizado.
        try:
            payload["volume"] = round(sum(volumes), 2)
        except Exception:  # noqa: BLE001
            pass

        # Ticker 24h (público).
        try:
            ticker = self.fetch_ticker24(market_type, test_mode)
            payload["change_24h_pct"] = round(float(ticker.get("priceChangePercent", 0) or 0), 4)
            if payload["price"] is None:
                payload["price"] = float(ticker.get("lastPrice", 0) or 0)
        except RuntimeError as exc:
            _logger.warning("No se pudo obtener el ticker 24h: %s", exc)

        # Datos de futuros (mark/index/funding).
        if market_type == "FUTURES":
            try:
                funding = self.fetch_funding(test_mode)
                payload["funding_rate"] = float(funding.get("lastFundingRate", 0) or 0)
                payload["mark_price"] = float(funding.get("markPrice", 0) or 0)
                payload["index_price"] = float(funding.get("indexPrice", 0) or 0)
                payload["next_funding_time"] = int(funding.get("nextFundingTime", 0) or 0)
            except RuntimeError as exc:
                _logger.warning("No se pudo obtener el funding rate: %s", exc)

        return payload

    @staticmethod
    def _summary(rec: str, ind: dict, market_type: str) -> str:
        rsi = ind.get("rsi14")
        macd_hist = ind.get("macd_hist")
        ema50 = ind.get("ema50")
        ema200 = ind.get("ema200")
        trend = ind.get("trend", "neutral")

        parts = [f"Tendencia {trend}"]
        if rsi is not None:
            zone = "sobrecomprado" if rsi >= ind.get("rsi_overbought", 70) else (
                "sobrevendido" if rsi <= ind.get("rsi_oversold", 30) else "neutral")
            parts.append(f"RSI {rsi:.1f} ({zone})")
        if macd_hist is not None:
            parts.append("MACD alcista" if macd_hist > 0 else "MACD bajista")
        if ema50 and ema200:
            parts.append("EMA50 > EMA200 (estructura alcista)" if ema50 >= ema200 else "EMA50 < EMA200 (estructura bajista)")

        rec_text = {
            "LONG": "Señal favorable para LONG: momento de comprar o abrir posición larga.",
            "SHORT": "Señal favorable para SHORT: momento de vender o abrir posición corta.",
            "NEUTRAL": "Sin señal clara: esperar a que el score supere el umbral.",
        }[rec]
        return f"{', '.join(parts)}. {rec_text}"


analyzer = MarketAnalyzer(symbol=settings.symbol)

