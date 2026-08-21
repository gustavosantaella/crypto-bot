"""Configuración de la API (lectura de ``api/.env``)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

# El .env vive en la raíz de la API, un nivel por encima de este paquete.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_user: str
    db_pass: str
    db_name: str
    db_port: int

    # --- Binance (balance spot de ambos ambientes) ---
    test_mode: bool
    currency: str
    binance_api_key_test: str
    binance_secret_key_test: str
    binance_api_key_prod: str
    binance_secret_key_prod: str
    binance_rest_url: str
    binance_ws_stream: str

    @property
    def symbol(self) -> str:
        return f"{self.currency}USDT"

    @classmethod
    def load(cls) -> "Settings":
        test_mode = os.getenv("TEST_MODE", "1").strip().lower() in {"1", "true", "yes", "on"}
        currency = os.getenv("CURRENCY_TO_USE", "BTC").upper().strip()
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
            currency=currency,
            binance_api_key_test=os.getenv("BINANCE_API_KEY_TEST") or os.getenv("BINANCE_API_KEY", ""),
            binance_secret_key_test=os.getenv("BINANCE_SECRET_KEY_TEST") or os.getenv("BINANCE_SECRET_KEY", ""),
            binance_api_key_prod=os.getenv("BINANCE_API_KEY_PROD", ""),
            binance_secret_key_prod=os.getenv("BINANCE_SECRET_KEY_PROD", ""),
            binance_rest_url=rest_url,
            binance_ws_stream=stream_name,
        )


settings = Settings.load()

