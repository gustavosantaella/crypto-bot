"""Configuración central del bot.

Carga las variables desde ``bot/.env`` y expone un objeto :class:`Config`
inmutable con todos los parámetros que necesita el bot.

Cuando ``TEST_MODE=1`` (entorno de pruebas), todas las URLs de Binance
(REST y WebSocket) se reemplazan automáticamente por las de la Testnet
(https://testnet.binance.vision) tal y como documenta Binance en
https://testnet.binance.vision/.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import parse_qs, urlparse, urlunparse

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


def _build_ws_url(raw_url: str, test_mode: bool, stream: str) -> str:
    """Construye la URL del WebSocket.

    Se parte de ``BINANCE_WEBSOCKET_URL`` del .env (que define qué streams
    escuchar, p.ej. ``streams=btcusdt@trade``) y, si estamos en test mode, se
    reemplaza el host por el de la Testnet de Binance conservando los streams.
    """
    parsed = urlparse(raw_url)
    if parsed.scheme not in ("wss", "ws"):
        parsed = urlparse("wss://stream.binance.com/stream")
    # El stream SIEMPRE se deriva del símbolo configurado (CURRENCY_TO_USE),
    # así que aunque el .env diga btcusdt@trade, el bot escucha el símbolo real.
    query = f"streams={stream}"
    host = parsed.hostname or "stream.binance.com"
    if test_mode and "testnet" not in host:
        host = "stream.testnet.binance.vision"
    return urlunparse(("wss", host, parsed.path or "/stream", "", query, ""))


@dataclass(frozen=True)
class Config:
    # --- Credenciales / modo ---
    binance_api_key: str
    binance_secret_key: str
    test_mode: bool
    currency: str
    symbol: str
    quote_asset: str

    # --- URLs de Binance ---
    binance_rest_url: str
    binance_ws_url: str

    # --- API del proyecto (donde se registran las transacciones) ---
    api_url: str

    # --- Parámetros de trading ---
    quote_amount: float          # USDT invertidos por operación
    sma_period: int              # Periodo de la media móvil (ventana de precios)
    buy_threshold_pct: float     # Comprar si precio <= SMA * (1 - X%)
    sell_profit_pct: float       # Vender si precio >= compra * (1 + X%)
    check_interval_ms: int       # Cada cuánto evalúa la estrategia (ms)

    # --- Robustez / red ---
    max_reconnect_delay: float   # Backoff máximo (s) para el WebSocket
    request_timeout: float       # Timeout de las peticiones REST (s)

    @classmethod
    def load(cls) -> "Config":
        test_mode = _get_bool("TEST_MODE", True)
        currency = os.getenv("CURRENCY_TO_USE", "BTC").upper().strip()
        symbol = f"{currency}USDT"
        quote_asset = "USDT"

        # --- REST: testnet cuando TEST_MODE=1, producción en caso contrario ---
        rest_url = os.getenv("BINANCE_REST_URL", "").strip().rstrip("/")
        if not rest_url:
            rest_url = "https://testnet.binance.vision" if test_mode else "https://api.binance.com"
        elif test_mode and "testnet" not in rest_url:
            rest_url = "https://testnet.binance.vision"

        # --- WebSocket ---
        raw_ws = os.getenv(
            "BINANCE_WEBSOCKET_URL",
            "wss://stream.binance.com/stream?streams=btcusdt@trade",
        )
        ws_url = _build_ws_url(raw_ws, test_mode, stream=f"{symbol.lower()}@trade")

        return cls(
            binance_api_key=os.getenv("BINANCE_API_KEY", ""),
            binance_secret_key=os.getenv("BINANCE_SECRET_KEY", ""),
            test_mode=test_mode,
            currency=currency,
            symbol=symbol,
            quote_asset=quote_asset,
            binance_rest_url=rest_url,
            binance_ws_url=ws_url,
            api_url=os.getenv("API_URL", "http://localhost:8000").rstrip("/"),
            quote_amount=_get_float("QUOTE_AMOUNT", 5.0),
            sma_period=_get_int("SMA_PERIOD", 20),
            buy_threshold_pct=_get_float("BUY_THRESHOLD_PCT", 0.8),
            sell_profit_pct=_get_float("SELL_PROFIT_PCT", 1.0),
            check_interval_ms=_get_int("CHECK_INTERVAL_MS", 500),
            max_reconnect_delay=_get_float("MAX_RECONNECT_DELAY", 30.0),
            request_timeout=_get_float("REQUEST_TIMEOUT", 5.0),
        )
