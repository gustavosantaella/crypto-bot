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

    # --- Binance (balance spot) ---
    test_mode: bool
    currency: str
    binance_api_key: str
    binance_secret_key: str
    binance_rest_url: str

    @property
    def symbol(self) -> str:
        return f"{self.currency}USDT"

    @classmethod
    def load(cls) -> "Settings":
        test_mode = os.getenv("TEST_MODE", "1").strip().lower() in {"1", "true", "yes", "on"}
        rest_url = "https://testnet.binance.vision" if test_mode else "https://api.binance.com"
        return cls(
            db_host=os.getenv("DB_HOST", "localhost"),
            db_user=os.getenv("DB_USER", "root"),
            db_pass=os.getenv("DB_PASS", ""),
            db_name=os.getenv("DB_NAME", "cryptobot"),
            db_port=int(os.getenv("DB_PORT", "3306")),
            test_mode=test_mode,
            currency=os.getenv("CURRENCY_TO_USE", "BTC").upper().strip(),
            binance_api_key=os.getenv("BINANCE_API_KEY", ""),
            binance_secret_key=os.getenv("BINANCE_SECRET_KEY", ""),
            binance_rest_url=rest_url,
        )


settings = Settings.load()

