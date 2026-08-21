"""Cliente de Binance de la API (solo lectura: balance spot).

Usa las credenciales de ``api/.env`` (copiadas de ``bot/.env``) y consulta el
balance de la cuenta spot vía ``GET /api/v3/account`` (firmado con
HMAC-SHA256). Según ``TEST_MODE`` apunta a la Testnet o a producción.
"""
from __future__ import annotations

import hashlib
import hmac
import time
import urllib.parse

import requests

from .config import settings


class BinanceBalanceError(RuntimeError):
    """Error al consultar el balance de Binance."""


class BinanceAccountClient:
    """Cliente de balance para un ambiente concreto.

    - ``test_mode=True``  -> Testnet (claves ``_TEST``)
    - ``test_mode=False`` -> Producción (claves ``_PROD``)
    """

    def __init__(self, test_mode: bool = True) -> None:
        self._test_mode = test_mode
        if test_mode:
            self._base = "https://testnet.binance.vision"
            self._api_key = settings.binance_api_key_test
            self._secret = settings.binance_secret_key_test
        else:
            self._base = "https://api.binance.com"
            self._api_key = settings.binance_api_key_prod
            self._secret = settings.binance_secret_key_prod

        if not self._api_key or not self._secret:
            env_name = "testnet" if test_mode else "producción"
            raise BinanceBalanceError(
                f"faltan credenciales de Binance para {env_name} en api/.env"
            )

        self._time_offset = 0
        self._sync_clock()

    def _sync_clock(self) -> None:
        try:
            server_time = int(requests.get(f"{self._base}/api/v3/time", timeout=5).json()["serverTime"])
            self._time_offset = server_time - int(time.time() * 1000)
        except Exception:  # noqa: BLE001
            self._time_offset = 0

    def _signed_get(self, path: str) -> dict:
        params = {
            "timestamp": int(time.time() * 1000) + self._time_offset,
            "recvWindow": 10_000,
        }
        query = urllib.parse.urlencode(params)
        signature = hmac.new(
            self._secret.encode("utf-8"),
            query.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        url = f"{self._base}{path}?{query}&signature={signature}"
        try:
            resp = requests.get(
                url,
                headers={"X-MBX-APIKEY": self._api_key},
                timeout=10,
            )
        except requests.RequestException as exc:
            raise BinanceBalanceError(f"error de red: {exc}") from exc
        if resp.status_code >= 400:
            try:
                data = resp.json()
                msg = f"{data.get('code')}: {data.get('msg')}"
            except ValueError:
                msg = resp.text
            raise BinanceBalanceError(msg)
        return resp.json()

    def get_balances(self) -> list[dict]:
        """Devuelve los balances con saldo > 0 (free o locked)."""
        account = self._signed_get("/api/v3/account")
        balances = [
            {
                "asset": balance["asset"],
                "free": float(balance["free"]),
                "locked": float(balance["locked"]),
            }
            for balance in account.get("balances", [])
            if float(balance["free"]) > 0 or float(balance["locked"]) > 0
        ]
        balances.sort(key=lambda b: (-b["free"], b["asset"]))
        return balances
