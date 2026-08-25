"""Cliente REST de Binance (spot y futuros USDT-M).

Autenticación HMAC-SHA256 (http://security.headers). Las peticiones firmadas
llevan ``X-MBX-APIKEY``, ``timestamp``, ``recvWindow`` y ``signature``.

Según ``TRADE_MODE`` y ``TEST_MODE`` del .env:

- spot + TEST_MODE=1  -> https://testnet.binance.vision
- spot + TEST_MODE=0  -> https://api.binance.com
- futuros + TEST=1    -> https://testnet.binancefuture.com  (fapi)
- futuros + TEST=0    -> https://fapi.binance.com
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


def ceil_to_step(value: float, step: float) -> float:
    """Ajusta una cantidad al step size del símbolo (hacia arriba).

    Ej.: ceil_to_step(0.0000662, 0.00001) -> 0.00007
    """
    if step <= 0:
        return value
    decimals = max(0, int(round(-math.log10(step))))
    ceiled = math.ceil(value / step - 1e-9) * step
    return round(ceiled, decimals)


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
    # Helpers de endpoints según el mercado
    # ------------------------------------------------------------------
    @property
    def _is_futures(self) -> bool:
        return self._cfg.trade_mode == "futures"

    def _api_path(self, spot_path: str, futures_path: str) -> str:
        """Devuelve el path REST según el modo de trading (spot vs futuros)."""
        return futures_path if self._is_futures else spot_path

    def _time_path(self) -> str:
        return self._api_path("/api/v3/time", "/fapi/v1/time")

    def _exchange_path(self) -> str:
        return self._api_path("/api/v3/exchangeInfo", "/fapi/v1/exchangeInfo")

    def _klines_path(self) -> str:
        return self._api_path("/api/v3/klines", "/fapi/v1/klines")

    def _order_path(self) -> str:
        return self._api_path("/api/v3/order", "/fapi/v1/order")

    def _ticker_path(self) -> str:
        return self._api_path("/api/v3/ticker/price", "/fapi/v1/ticker/price")

    def _ticker24_path(self) -> str:
        return self._api_path("/api/v3/ticker/24hr", "/fapi/v1/ticker/24hr")

    # ------------------------------------------------------------------
    # Sincronización de reloj
    # ------------------------------------------------------------------
    def _sync_clock(self) -> None:
        """Calcula el offset del reloj local respecto al servidor de Binance."""
        try:
            server_time = int(self._get(self._time_path())["serverTime"])
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
        return self._get(self._api_path("/api/v3/ping", "/fapi/v1/ping"))

    def get_ticker_price(self, symbol: str) -> float:
        data = self._get(self._ticker_path(), {"symbol": symbol})
        return float(data["price"])

    def get_ticker_24h(self, symbol: str) -> dict:
        """Cambio en 24h (priceChangePercent, lastPrice...) para spot y futuros."""
        data = self._get(self._ticker24_path(), {"symbol": symbol})
        return {
            "price": float(data.get("lastPrice", 0) or 0),
            "change_24h_pct": float(data.get("priceChangePercent", 0) or 0),
            "high": float(data.get("highPrice", 0) or 0),
            "low": float(data.get("lowPrice", 0) or 0),
            "volume": float(data.get("volume", 0) or 0),
        }

    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 300) -> list[list]:
        """Velas OHLC históricas: spot (/api/v3/klines) o futuros (/fapi/v1/klines).

        Cada vela es ``[openTime, open, high, low, close, volume, ...]``.
        """
        return self._get(self._klines_path(), {"symbol": symbol, "interval": interval, "limit": limit})

    def get_symbol_info(self, symbol: str) -> dict:
        """Filtros del símbolo: step size, cantidad mínima y notional mínimo."""
        info = self._get(self._exchange_path(), {"symbol": symbol})
        symbol_info = info["symbols"][0]
        filters = {f["filterType"]: f for f in symbol_info["filters"]}
        lot = filters.get("LOT_SIZE", {})
        min_notional = float(
            filters.get("NOTIONAL", {}).get("minNotional", 0)
            or filters.get("MIN_NOTIONAL", {}).get("minNotional", 0)
            or 0
        )
        # En futuros el exchangeInfo también expone la precisión de precio/cantidad.
        return {
            "step_size": float(lot.get("stepSize", 1)),
            "min_qty": float(lot.get("minQty", 0)),
            "min_notional": min_notional,
            "price_precision": int(symbol_info.get("pricePrecision", 8)),
            "quantity_precision": int(symbol_info.get("quantityPrecision", 8)),
        }

    def get_account_balances(self) -> dict[str, float]:
        """Balance disponible de la cuenta: {activo: cantidad}.

        - Spot:   ``/api/v3/account``  -> campo ``free``.
        - Futuros: ``/fapi/v2/balance`` -> campo ``availableBalance``.
        """
        if self._is_futures:
            account = self._signed("GET", "/fapi/v2/balance")
            return {
                balance["asset"]: float(balance.get("availableBalance", 0) or 0)
                for balance in account
                if float(balance.get("availableBalance", 0) or 0) > 0
            }
        account = self._signed("GET", "/api/v3/account")
        balances = {
            balance["asset"]: float(balance["free"])
            for balance in account.get("balances", [])
        }
        return {asset: free for asset, free in balances.items() if free > 0}

    # ------------------------------------------------------------------
    # Órdenes de mercado (spot)
    # ------------------------------------------------------------------
    def market_buy(self, symbol: str, quote_amount: float, reference_price: float | None = None) -> FilledOrder:
        """Compra al mercado la cantidad de ``symbol`` que alcance con ``quote_amount`` USDT.

        La cantidad se alinea al *step size* del símbolo y se garantiza que su
        valor nocional sea >= al ``minNotional`` para que la venta posterior
        NUNCA sea rechazada con ``-1013 Filter failure: NOTIONAL``.

        Si ``quote_amount`` no alcanza el ``minNotional`` (por el redondeo al
        step), la cantidad se sube al siguiente múltiplo del step que sí lo
        cumpla (p. ej. 5 USDT pedidos -> 0.00007 BTC ≈ 5.29 USDT).
        """
        info = self.get_symbol_info(symbol)
        price = reference_price or self.get_ticker_price(symbol)
        step = info["step_size"]
        min_notional = info["min_notional"]

        quantity = floor_to_step(quote_amount / price, step)
        if quantity * price < min_notional:
            quantity = ceil_to_step(min_notional / price, step)
            self._log.warning(
                "quote_amount=%.2f no cubre el minNotional (%.2f USDT); "
                "cantidad de compra ajustada a %.8f",
                quote_amount, min_notional, quantity,
            )
        if quantity <= 0:
            raise BinanceAPIError(-1, f"cantidad de compra inválida (quote={quote_amount}, price={price})")

        data = self._signed(
            "POST", self._order_path(),
            {"symbol": symbol, "side": "BUY", "type": "MARKET", "quantity": f"{quantity:.8f}"},
        )
        return FilledOrder.from_binance(data)

    def market_sell(self, symbol: str, quantity: float) -> FilledOrder:
        """Vende al mercado toda la ``quantity`` (la que compramos antes)."""
        data = self._signed(
            "POST", self._order_path(),
            {"symbol": symbol, "side": "SELL", "type": "MARKET", "quantity": f"{quantity:.8f}"},
        )
        return FilledOrder.from_binance(data)

    # ------------------------------------------------------------------
    # Futuros USDT-M: configuración de la cuenta
    # ------------------------------------------------------------------
    def set_leverage(self, symbol: str, leverage: int) -> dict:
        """Aplica el apalancamiento al símbolo (POST /fapi/v1/leverage)."""
        return self._signed(
            "POST", "/fapi/v1/leverage",
            {"symbol": symbol, "leverage": leverage},
        )

    def set_margin_type(self, symbol: str, margin_type: str) -> dict:
        """Cambia el tipo de margen (ISOLATED / CROSSED) del símbolo."""
        margin_type = margin_type.upper()
        if margin_type not in ("ISOLATED", "CROSSED"):
            margin_type = "ISOLATED"
        return self._signed(
            "POST", "/fapi/v1/marginType",
            {"symbol": symbol, "marginType": margin_type},
        )

    def get_position_risk(self, symbol: str | None = None) -> list[dict]:
        """Posiciones abiertas en futuros (GET /fapi/v2/positionRisk)."""
        params = {"symbol": symbol} if symbol else None
        return self._signed("GET", "/fapi/v2/positionRisk", params)

    def get_premium_index(self, symbol: str) -> dict:
        """Mark price, index price y funding rate actuales (GET /fapi/v1/premiumIndex)."""
        return self._get("/fapi/v1/premiumIndex", {"symbol": symbol})

    # ------------------------------------------------------------------
    # Órdenes de mercado (futuros USDT-M)
    # ------------------------------------------------------------------
    def _futures_order(
        self,
        symbol: str,
        side: str,
        quantity: float,
        position_side: str = "BOTH",
        reduce_only: bool = False,
    ) -> FilledOrder:
        params = {
            "symbol": symbol,
            "side": side,
            "type": "MARKET",
            "quantity": f"{quantity:.8f}",
            "positionSide": position_side,
            "newOrderRespType": "RESULT",
        }
        if reduce_only:
            params["reduceOnly"] = "true"
        data = self._signed("POST", "/fapi/v1/order", params)
        return FilledOrder.from_binance(data)

    def market_open_long(self, symbol: str, quantity: float) -> FilledOrder:
        """Abre un LONG (compra) en futuros USDT-M (modo one-way, positionSide BOTH)."""
        return self._futures_order(symbol, "BUY", quantity)

    def market_open_short(self, symbol: str, quantity: float) -> FilledOrder:
        """Abre un SHORT (venta) en futuros USDT-M (modo one-way)."""
        return self._futures_order(symbol, "SELL", quantity)

    def market_close_long(self, symbol: str, quantity: float) -> FilledOrder:
        """Cierra un LONG (vende con reduceOnly para no abrir SHORT)."""
        return self._futures_order(symbol, "SELL", quantity, reduce_only=True)

    def market_close_short(self, symbol: str, quantity: float) -> FilledOrder:
        """Cierra un SHORT (compra con reduceOnly para no abrir LONG)."""
        return self._futures_order(symbol, "BUY", quantity, reduce_only=True)

    def quantity_for_notional(self, symbol: str, notional: float) -> float:
        """Cantidad de contratos para un nocional dado (aligna al step size)."""
        info = self.get_symbol_info(symbol)
        step = info["step_size"]
        price = self.get_ticker_price(symbol)
        if price <= 0:
            raise BinanceAPIError(-1, "precio inválido para calcular cantidad")
        qty = floor_to_step(notional / price, step)
        if qty <= 0:
            raise BinanceAPIError(
                -1,
                f"nocional {notional:.2f} USDT demasiado pequeño para {symbol} "
                f"(step={step})",
            )
        return qty


