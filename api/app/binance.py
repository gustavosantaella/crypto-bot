"""Cliente de Binance de la API (solo lectura: balance y posiciones).

Usa las credenciales de ``api/.env`` y consulta la cuenta vía endpoints
firmados con HMAC-SHA256. Soporta:

- spot:    ``GET /api/v3/account``  -> balances.
- futuros: ``GET /fapi/v2/balance`` -> balances de la cartera y
           ``GET /fapi/v2/positionRisk`` -> posiciones abiertas (con precio de
           liquidación, apalancamiento y PnL no realizado).

Según ``TEST_MODE`` apunta a la Testnet o a producción, y según el tipo de
mercado usa unas credenciales u otras (las de futuros pueden definirse por
separado en el .env; si no existen, se usan las de spot como fallback).
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
    """Cliente de balance/posiciones para un ambiente y mercado concretos."""

    def __init__(self, test_mode: bool = True, market_type: str = "SPOT") -> None:
        self._test_mode = test_mode
        self._market_type = market_type.upper()
        if self._market_type not in ("SPOT", "FUTURES"):
            self._market_type = "SPOT"
        self._is_futures = self._market_type == "FUTURES"

        if self._is_futures:
            self._base = (
                "https://testnet.binancefuture.com" if test_mode else "https://fapi.binance.com"
            )
            self._api_key = (
                settings.binance_api_key_test_futures if test_mode else settings.binance_api_key_prod_futures
            )
            self._secret = (
                settings.binance_secret_key_test_futures if test_mode else settings.binance_secret_key_prod_futures
            )
        else:
            self._base = "https://testnet.binance.vision" if test_mode else "https://api.binance.com"
            self._api_key = (
                settings.binance_api_key_test if test_mode else settings.binance_api_key_prod
            )
            self._secret = (
                settings.binance_secret_key_test if test_mode else settings.binance_secret_key_prod
            )

        if not self._api_key or not self._secret:
            env_name = "testnet" if test_mode else "producción"
            raise BinanceBalanceError(
                f"faltan credenciales de Binance para {self._market_type.lower()} "
                f"({env_name}) en api/.env"
            )

        self._time_offset = 0
        self._sync_clock()

    def _sync_clock(self) -> None:
        path = "/fapi/v1/time" if self._is_futures else "/api/v3/time"
        try:
            server_time = int(requests.get(f"{self._base}{path}", timeout=5).json()["serverTime"])
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
        """Devuelve los balances con saldo > 0.

        - Spot:    ``/api/v3/account``  -> free / locked.
        - Futuros: ``/fapi/v2/balance`` -> disponible / margen / PnL no realizado.
        """
        if self._is_futures:
            account = self._signed_get("/fapi/v2/balance")
            balances = [
                {
                    "asset": balance["asset"],
                    "free": float(balance.get("availableBalance", 0) or 0),
                    "locked": max(
                        0.0,
                        float(balance.get("balance", 0) or 0)
                        - float(balance.get("availableBalance", 0) or 0),
                    ),
                    "margin_balance": float(balance.get("marginBalance", 0) or 0),
                    "wallet_balance": float(balance.get("balance", 0) or 0),
                    "unrealized_profit": float(balance.get("crossUnPnl", 0) or 0),
                }
                for balance in account
                if float(balance.get("marginBalance", 0) or 0) > 0
            ]
            balances.sort(key=lambda b: (-b["free"], b["asset"]))
            return balances

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

    def get_positions(self, symbol: str | None = None) -> list[dict]:
        """Posiciones abiertas en futuros (solo market_type=FUTURES)."""
        if not self._is_futures:
            return []
        query = ""
        if symbol:
            query = f"?{urllib.parse.urlencode({'symbol': symbol})}"
        data = self._signed_get(f"/fapi/v2/positionRisk{query}")
        positions = []
        for pos in data:
            amt = float(pos.get("positionAmt", 0) or 0)
            if amt == 0:
                continue
            side = "LONG" if amt > 0 else "SHORT"
            entry = float(pos.get("entryPrice", 0) or 0)
            mark = float(pos.get("markPrice", 0) or 0)
            notional = abs(amt) * mark
            unrealized = float(pos.get("unRealizedProfit", 0) or 0)
            leverage = int(float(pos.get("leverage", 1) or 1))
            positions.append({
                "symbol": pos.get("symbol"),
                "side": side,
                "position_amt": abs(amt),
                "entry_price": entry,
                "mark_price": mark,
                "notional": notional,
                "unrealized_profit": unrealized,
                "profit_pct": round((unrealized / notional * 100.0), 4) if notional else 0.0,
                "liquidation_price": (
                    float(pos["liquidationPrice"]) if pos.get("liquidationPrice") else None
                ),
                "leverage": leverage,
                "margin_type": pos.get("marginType", "ISOLATED"),
                "margin_ratio": float(pos.get("marginRatio", 0) or 0),
            })
        positions.sort(key=lambda p: -abs(p["unrealized_profit"]))
        return positions
