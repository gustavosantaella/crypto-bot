"""Configuración central del bot.

Carga las variables desde ``bot/.env`` y expone un objeto :class:`Config`
inmutable con todos los parámetros que necesita el bot.

Modos de trading soportados (``TRADE_MODE``):

- ``spot``    -> Binance Spot clásico (compra barato / vende caro).
- ``futures`` -> Futuros USDT-M con apalancamiento (LONG/SHORT según señal).

Cuando ``TEST_MODE=1`` (entorno de pruebas), todas las URLs de Binance
(REST y WebSocket) se reemplazan automáticamente por las de la Testnet
(spot: https://testnet.binance.vision, futuros: https://testnet.binancefuture.com).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

# El archivo .env vive en la misma carpeta que este módulo.
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _get_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _get_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


def _get_str(name: str, default: str) -> str:
    return os.getenv(name, default).strip()


def _build_ws_url(raw_url: str, test_mode: bool, stream: str, trade_mode: str) -> str:
    """Construye la URL del WebSocket.

    Se parte de ``BINANCE_WEBSOCKET_URL`` del .env (que define qué streams
    escuchar, p.ej. ``streams=btcusdt@trade``) y se reemplaza el host según el
    modo de trading y el entorno, conservando los streams configurados.
    """
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("wss", "ws"):
        parsed = urlparse("wss://stream.binance.com/stream")
    # El stream SIEMPRE se deriva del símbolo configurado (CURRENCY_TO_USE),
    # así que aunque el .env diga btcusdt@trade, el bot escucha el símbolo real.
    query = f"streams={stream}"
    if trade_mode == "futures":
        host = "stream.testnet.binancefuture.com" if test_mode else "fstream.binance.com"
    else:
        host = "stream.testnet.binance.vision" if test_mode else "stream.binance.com"
    return urlunparse(("wss", host, parsed.path or "/stream", "", query, ""))


@dataclass(frozen=True)
class Config:
    # --- Credenciales / modo ---
    binance_api_key: str
    binance_secret_key: str
    test_mode: bool
    trade_mode: str               # "spot" | "futures"
    currency: str
    symbol: str
    quote_asset: str

    # --- URLs de Binance ---
    binance_rest_url: str
    binance_ws_url: str

    # --- API del proyecto (donde se registran las transacciones) ---
    api_url: str

    # --- Parámetros de trading (spot: compra barato / vende caro) ---
    quote_amount: float          # USDT de margen invertidos por operación
    sma_period: int              # Nº de muestras de la ventana de la SMA
    sma_sample_ms: int           # Cada cuántos ms se muestrea el precio para la SMA
    buy_threshold_pct: float     # Comprar si precio <= SMA * (1 - X%)
    sell_profit_pct: float       # Vender si precio >= compra * (1 + X%)
    check_interval_ms: int       # Cada cuánto evalúa la estrategia (ms)

    # --- Parámetros de trading (futuros: apalancamiento + señal) ---
    leverage: int                # Apalancamiento configurable (1..125 según símbolo)
    margin_type: str             # "ISOLATED" | "CROSSED"
    futures_take_profit_pct: float  # Cerrar LONG/SHORT con +X% de beneficio
    futures_stop_loss_pct: float    # Cerrar LONG/SHORT con -X% de pérdida
    signal_open_score: float     # Abrir posición si |score| >= este umbral
    signal_close_score: float    # Cerrar posición si |score| <= este umbral (señal en contra)
    kline_interval: str          # Intervalo de velas para los indicadores (ej. 1m, 5m)
    kline_limit: int             # Nº de velas históricas para calcular indicadores
    analysis_refresh_ms: int     # Cada cuánto se refresca el análisis por REST

    # --- Indicadores (RSI / MACD / EMA) ---
    rsi_period: int
    rsi_oversold: float
    rsi_overbought: float
    ema_fast: int                # EMA rápida del MACD
    ema_slow: int                # EMA lenta del MACD
    ema_signal: int              # Línea de señal del MACD
    ema_trend_fast: int          # EMA de tendencia rápida (50)
    ema_trend_slow: int          # EMA de tendencia lenta (200)

    # --- Robustez / red ---
    max_reconnect_delay: float   # Backoff máximo (s) para el WebSocket
    request_timeout: float       # Timeout de las peticiones REST (s)

    @property
    def market_type(self) -> str:
        """Tipo de mercado: ``FUTURES`` o ``SPOT`` (identificador para BD/API)."""
        return "FUTURES" if self.trade_mode == "futures" else "SPOT"

    @classmethod
    def load(cls) -> "Config":
        test_mode = _get_bool("TEST_MODE", True)
        trade_mode = _get_str("TRADE_MODE", "spot").lower()
        if trade_mode not in ("spot", "futures"):
            trade_mode = "spot"
        currency = os.getenv("CURRENCY_TO_USE", "BTC").upper().strip()
        symbol = f"{currency}USDT"
        quote_asset = "USDT"
        is_futures = trade_mode == "futures"

        # --- Credenciales según modo de trading ---
        if is_futures:
            api_key = os.getenv("BINANCE_API_KEY_FUTURES") or os.getenv("BINANCE_API_KEY", "")
            secret_key = os.getenv("BINANCE_SECRET_KEY_FUTURES") or os.getenv("BINANCE_SECRET_KEY", "")
        else:
            api_key = os.getenv("BINANCE_API_KEY", "")
            secret_key = os.getenv("BINANCE_SECRET_KEY", "")

        # --- REST: testnet cuando TEST_MODE=1, producción en caso contrario ---
        rest_url = os.getenv("BINANCE_REST_URL", "").strip().rstrip("/")
        if not rest_url:
            if is_futures:
                rest_url = "https://testnet.binancefuture.com" if test_mode else "https://fapi.binance.com"
            else:
                rest_url = "https://testnet.binance.vision" if test_mode else "https://api.binance.com"
        elif test_mode and "testnet" not in rest_url:
            rest_url = (
                "https://testnet.binancefuture.com" if is_futures else "https://testnet.binance.vision"
            )

        # --- WebSocket ---
        raw_ws = os.getenv(
            "BINANCE_WEBSOCKET_URL",
            "wss://stream.binance.com/stream?streams=btcusdt@trade",
        )
        ws_url = _build_ws_url(raw_ws, test_mode, stream=f"{symbol.lower()}@trade", trade_mode=trade_mode)

        return cls(
            binance_api_key=api_key,
            binance_secret_key=secret_key,
            test_mode=test_mode,
            trade_mode=trade_mode,
            currency=currency,
            symbol=symbol,
            quote_asset=quote_asset,
            binance_rest_url=rest_url,
            binance_ws_url=ws_url,
            api_url=os.getenv("API_URL", "http://localhost:8000").rstrip("/"),
            quote_amount=_get_float("QUOTE_AMOUNT", 10.0),
            sma_period=_get_int("SMA_PERIOD", 20),
            sma_sample_ms=_get_int("SMA_SAMPLE_MS", 2000),
            buy_threshold_pct=_get_float("BUY_THRESHOLD_PCT", 0.3),
            sell_profit_pct=_get_float("SELL_PROFIT_PCT", 0.5),
            check_interval_ms=_get_int("CHECK_INTERVAL_MS", 500),
            leverage=max(1, _get_int("LEVERAGE", 1)),
            margin_type=_get_str("MARGIN_TYPE", "ISOLATED").upper(),
            futures_take_profit_pct=_get_float("FUTURES_TAKE_PROFIT_PCT", 1.0),
            futures_stop_loss_pct=_get_float("FUTURES_STOP_LOSS_PCT", 0.5),
            signal_open_score=_get_float("SIGNAL_OPEN_SCORE", 2.0),
            signal_close_score=_get_float("SIGNAL_CLOSE_SCORE", 0.5),
            kline_interval=_get_str("KLINE_INTERVAL", "1m"),
            kline_limit=max(100, _get_int("KLINE_LIMIT", 300)),
            analysis_refresh_ms=max(5_000, _get_int("ANALYSIS_REFRESH_MS", 15_000)),
            rsi_period=_get_int("RSI_PERIOD", 14),
            rsi_oversold=_get_float("RSI_OVERSOLD", 30.0),
            rsi_overbought=_get_float("RSI_OVERBOUGHT", 70.0),
            ema_fast=_get_int("EMA_FAST", 12),
            ema_slow=_get_int("EMA_SLOW", 26),
            ema_signal=_get_int("EMA_SIGNAL", 9),
            ema_trend_fast=_get_int("EMA_TREND_FAST", 50),
            ema_trend_slow=_get_int("EMA_TREND_SLOW", 200),
            max_reconnect_delay=_get_float("MAX_RECONNECT_DELAY", 30.0),
            request_timeout=_get_float("REQUEST_TIMEOUT", 5.0),
        )
