"""Configuración de la API (lectura de ``api/.env``)."""
from __future__ import annotations

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

    @classmethod
    def load(cls) -> "Settings":
        import os

        return cls(
            db_host=os.getenv("DB_HOST", "localhost"),
            db_user=os.getenv("DB_USER", "root"),
            db_pass=os.getenv("DB_PASS", ""),
            db_name=os.getenv("DB_NAME", "cryptobot"),
            db_port=int(os.getenv("DB_PORT", "3306")),
        )


settings = Settings.load()
