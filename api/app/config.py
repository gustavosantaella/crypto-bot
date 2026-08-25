"""Configuración de la API (lectura de ``api/.env``)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# El .env vive en la raíz de la API, un nivel por encima de este paquete.
BASE_DIR = Path(__file__).resolve().parent.parent
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


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_user: str
    db_pass: str
    db_name: str
    db_port: int

    # --- Binance (balance spot/futuros de ambos ambientes) ---
    test_mode: bool
    trade_mode: str                # "spot" | "futures"
    currency: str
    leverage: int
    binance_api_key_test: str
    binance_secret_key_test: str
    binance_api_key_prod: str
    binance_secret_key_prod: str
    # Futuros (fallback a las de spot si no se definen).
    binance_api_key_test_futures: str
    binance_secret_key_test_futures: str
    binance_api_key_prod_futures: str
    binance_secret_key_prod_futures: str
    binance_rest_url: str
    binance_ws_stream: str

    # --- Análisis de mercado ---
    kline_interval: str
    kline_limit: int
    analysis_refresh_ms: int
    ema_fast: int
    ema_slow: int
    ema_signal: int
    ema_trend_fast: int
    ema_trend_slow: int
    rsi_period: int
    rsi_oversold: float
    rsi_overbought: float

    @property
    def symbol(self) -> str:
        return f"{self.currency}USDT"

    @property
    def market_type(self) -> str:
        """Tipo de mercado: ``FUTURES`` o ``SPOT``."""
        return "FUTURES" if self.trade_mode == "futures" else "SPOT"

    @classmethod
    def load(cls) -> "Settings":
        test_mode = _get_bool("TEST_MODE", True)
        trade_mode = os.getenv("TRADE_MODE", "spot").strip().lower()
        if trade_mode not in ("spot", "futures"):
            trade_mode = "spot"
        currency = os.getenv("CURRENCY_TO_USE", "BTC").upper().strip()
        is_futures = trade_mode == "futures"

        if is_futures:
            rest_url = "https://testnet.binancefuture.com" if test_mode else "https://fapi.binance.com"
        else:
            rest_url = "https://testnet.binance.vision" if test_mode else "https://api.binance.com"

        # Stream de precios: se usa BINANCE_WEBSOCKET_URL (si existe) para
        # saber qué stream escuchar (ej. btcusdt@trade); si no, se deriva del
        # símbolo configurado.
        stream_name = f"{currency.lower()}usdt@trade"
        raw_ws = os.getenv("BINANCE_WEBSOCKET_URL", "")
        if raw_ws:
            try:
                from urllib.parse import parse_qs, urlparse

                streams = parse_qs(urlparse(raw_ws).query).get("streams")
                if streams and streams[0]:
                    stream_name = streams[0]
            except Exception:  # noqa: BLE001
                pass

        return cls(
            db_host=os.getenv("DB_HOST", "localhost"),
            db_user=os.getenv("DB_USER", "root"),
            db_pass=os.getenv("DB_PASS", ""),
            db_name=os.getenv("DB_NAME", "cryptobot"),
            db_port=int(os.getenv("DB_PORT", "3306")),
            test_mode=test_mode,
            trade_mode=trade_mode,
            currency=currency,
            leverage=max(1, _get_int("LEVERAGE", 1)),
            binance_api_key_test=os.getenv("BINANCE_API_KEY_TEST") or os.getenv("BINANCE_API_KEY", ""),
            binance_secret_key_test=os.getenv("BINANCE_SECRET_KEY_TEST") or os.getenv("BINANCE_SECRET_KEY", ""),
            binance_api_key_prod=os.getenv("BINANCE_API_KEY_PROD", ""),
            binance_secret_key_prod=os.getenv("BINANCE_SECRET_KEY_PROD", ""),
            binance_api_key_test_futures=os.getenv("BINANCE_API_KEY_TEST_FUTURES")
            or os.getenv("BINANCE_API_KEY_FUTURES", "") or os.getenv("BINANCE_API_KEY_TEST", ""),
            binance_secret_key_test_futures=os.getenv("BINANCE_SECRET_KEY_TEST_FUTURES")
            or os.getenv("BINANCE_SECRET_KEY_FUTURES", "") or os.getenv("BINANCE_SECRET_KEY_TEST", ""),
            binance_api_key_prod_futures=os.getenv("BINANCE_API_KEY_PROD_FUTURES")
            or os.getenv("BINANCE_API_KEY_FUTURES_PROD", "") or os.getenv("BINANCE_API_KEY_PROD", ""),
            binance_secret_key_prod_futures=os.getenv("BINANCE_SECRET_KEY_PROD_FUTURES")
            or os.getenv("BINANCE_SECRET_KEY_FUTURES_PROD", "") or os.getenv("BINANCE_SECRET_KEY_PROD", ""),
            binance_rest_url=rest_url,
            binance_ws_stream=stream_name,
            kline_interval=os.getenv("KLINE_INTERVAL", "1m").strip(),
            kline_limit=max(100, _get_int("KLINE_LIMIT", 300)),
            analysis_refresh_ms=max(5_000, _get_int("ANALYSIS_REFRESH_MS", 15_000)),
            ema_fast=_get_int("EMA_FAST", 12),
            ema_slow=_get_int("EMA_SLOW", 26),
            ema_signal=_get_int("EMA_SIGNAL", 9),
            ema_trend_fast=_get_int("EMA_TREND_FAST", 50),
            ema_trend_slow=_get_int("EMA_TREND_SLOW", 200),
            rsi_period=_get_int("RSI_PERIOD", 14),
            rsi_oversold=_get_float("RSI_OVERSOLD", 30.0),
            rsi_overbought=_get_float("RSI_OVERBOUGHT", 70.0),
        )


settings = Settings.load()

