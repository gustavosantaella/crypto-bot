"""Cliente REST de Binance (spot).

Autenticación HMAC-SHA256 (http://security.headers). Las peticiones firmadas
llevan ``X-MBX-APIKEY``, ``timestamp``, ``recvWindow`` y ``signature``.

- TEST_MODE=1  -> https://testnet.binance.vision
- TEST_MODE=0  -> https://api.binance.com
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import math
import time
import urllib.parse

import requests

from config import Config
from .models import FilledOrder


class BinanceAPIError(RuntimeError):
    """Error devuelto por la API de Binance o de red."""

    def __init__(self, code: int, message: str, payload: dict | None = None) -> None:
        super().__init__(f"Binance error {code}: {message}")
        self.code = code
        self.message = message
        self.payload = payload or {}


def floor_to_step(value: float, step: float) -> float:
    """Ajusta una cantidad al step size del símbolo (hacia abajo).

    Ej.: floor_to_step(0.0001234, 0.00001) -> 0.00012
    """
    if step <= 0:
        return value
    decimals = max(0, int(round(-math.log10(step))))
    floored = math.floor(value / step + 1e-9) * step
    return round(floored, decimals)


class BinanceClient:
    def __init__(self, config: Config, logger: logging.Logger) -> None:
        self._cfg = config
        self._log = logger.getChild("binance")
        self._recv_window = 10_000
        # Offset entre el reloj local y el servidor de Binance (evita el error
        # -1021 "Timestamp ahead of server's time" en máquinas desincronizadas).
        self._time_offset = 0
        self._session = requests.Session()
        self._session.headers.update(
            {"X-MBX-APIKEY": config.binance_api_key, "Content-Type": "application/x-www-form-urlencoded"}
        )
        self._sync_clock()

    # ------------------------------------------------------------------
    # Sincronización de reloj
    # ------------------------------------------------------------------
    def _sync_clock(self) -> None:
        """Calcula el offset del reloj local respecto al servidor de Binance."""
        try:
            server_time = int(self._get("/api/v3/time")["serverTime"])
            self._time_offset = server_time - int(time.time() * 1000)
            self._log.info("Reloj sincronizado con Binance (offset=%+d ms)", self._time_offset)
        except Exception as exc:  # noqa: BLE001
            self._log.warning("No se pudo sincronizar el reloj con Binance: %s", exc)
            self._time_offset = 0

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------
    def _request(self, method: str, path: str, params: dict | None = None, signed: bool = False):
        params = dict(params or {})
        if signed:
            params["timestamp"] = int(time.time() * 1000) + self._time_offset
            params["recvWindow"] = self._recv_window
            query = urllib.parse.urlencode(params)
            signature = hmac.new(
                self._cfg.binance_secret_key.encode("utf-8"),
                query.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            url = f"{self._cfg.binance_rest_url}{path}?{query}&signature={signature}"
        else:
            url = f"{self._cfg.binance_rest_url}{path}"

        try:
            resp = self._session.request(method, url, params=params if not signed else None, timeout=self._cfg.request_timeout)
        except requests.RequestException as exc:
            raise BinanceAPIError(-1, f"error de red: {exc}") from exc

        if resp.status_code >= 400:
            try:
                data = resp.json()
            except ValueError:
                data = {"code": resp.status_code, "msg": resp.text}
            raise BinanceAPIError(int(data.get("code", resp.status_code)), data.get("msg", resp.text), data)
        return resp.json()

    def _get(self, path: str, params: dict | None = None):
        return self._request("GET", path, params, signed=False)

    def _signed(self, method: str, path: str, params: dict | None = None):
        return self._request(method, path, params, signed=True)

    # ------------------------------------------------------------------
    # Endpoints públicos
    # ------------------------------------------------------------------
    def ping(self) -> dict:
        return self._get("/api/v3/ping")

    def get_ticker_price(self, symbol: str) -> float:
        data = self._get("/api/v3/ticker/price", {"symbol": symbol})
        return float(data["price"])

    def get_symbol_info(self, symbol: str) -> dict:
        """Filtros del símbolo: step size, cantidad mínima y notional mínimo."""
        info = self._get("/api/v3/exchangeInfo", {"symbol": symbol})
        symbol_info = info["symbols"][0]
        filters = {f["filterType"]: f for f in symbol_info["filters"]}
        lot = filters.get("LOT_SIZE", {})
        min_notional = float(
            filters.get("NOTIONAL", {}).get("minNotional", 0)
            or filters.get("MIN_NOTIONAL", {}).get("minNotional", 0)
            or 0
        )
        return {
            "step_size": float(lot.get("stepSize", 1)),
            "min_qty": float(lot.get("minQty", 0)),
            "min_notional": min_notional,
        }

    # ------------------------------------------------------------------
    # Órdenes de mercado (spot)
    # ------------------------------------------------------------------
    def market_buy(self, symbol: str, quote_amount: float) -> FilledOrder:
        """Compra al mercado usando ``quoteOrderQty`` (gasta ``quote_amount`` USDT).

        Si Binance rechaza ``quoteOrderQty`` se reintenta calculando la
        cantidad exacta a partir del step size del símbolo.
        """
        try:
            data = self._signed(
                "POST", "/api/v3/order",
                {"symbol": symbol, "side": "BUY", "type": "MARKET", "quoteOrderQty": f"{quote_amount:.2f}"},
            )
        except BinanceAPIError as exc:
            # Fallback: cantidad explícita alineada al step size.
            if exc.code in (-1013, -1111, -1100):
                self._log.warning("quoteOrderQty rechazado (%s), usando quantity", exc.code)
                price = self.get_ticker_price(symbol)
                info = self.get_symbol_info(symbol)
                quantity = floor_to_step(quote_amount / price, info["step_size"])
                data = self._signed(
                    "POST", "/api/v3/order",
                    {"symbol": symbol, "side": "BUY", "type": "MARKET", "quantity": f"{quantity:.8f}"},
                )
            else:
                raise
        return FilledOrder.from_binance(data)

    def market_sell(self, symbol: str, quantity: float) -> FilledOrder:
        """Vende al mercado toda la ``quantity`` (la que compramos antes)."""
        data = self._signed(
            "POST", "/api/v3/order",
            {"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": f"{quantity:.8f}"},
        )
        return FilledOrder.from_binance(data)

