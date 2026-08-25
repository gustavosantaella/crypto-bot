"""Modelos de dominio del bot."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FilledOrder:
    """Orden de mercado ejecutada por Binance."""

    symbol: str
    side: str
    order_id: int
    status: str
    executed_qty: float
    avg_price: float
    quote_qty: float
    transact_time: int
    raw: dict

    @classmethod
    def from_binance(cls, data: dict) -> "FilledOrder":
        executed_qty = float(data.get("executedQty", 0.0) or 0.0)
        quote_qty = float(data.get("cummulativeQuoteQty", 0.0) or 0.0)
        avg_price = quote_qty / executed_qty if executed_qty > 0 else 0.0
        return cls(
            symbol=data.get("symbol", ""),
            side=data.get("side", ""),
            order_id=int(data.get("orderId", 0)),
            status=data.get("status", "UNKNOWN"),
            executed_qty=executed_qty,
            avg_price=avg_price,
            quote_qty=quote_qty,
            transact_time=int(data.get("transactTime", 0)),
            raw=data,
        )


@dataclass
class Position:
    """Posición abierta: una operación que aún no se ha cerrado.

    En spot representa una compra pendiente de vender; en futuros una posición
    LONG o SHORT abierta (con apalancamiento, margen y precio de liquidación).
    """

    symbol: str
    buy_order_id: int
    buy_price: float          # precio de entrada (compra o apertura)
    buy_quantity: float       # cantidad (spot) o nº de contratos (futuros)
    buy_quote: float          # nocional total = cantidad * precio
    buy_time: int
    test_mode: bool = True
    # --- Identificación del mercado ---
    market_type: str = "SPOT"        # "SPOT" | "FUTURES"
    side: str = "LONG"               # "LONG" | "SHORT"
    leverage: int = 1
    # --- Futuros ---
    margin: float | None = None          # colateral invertido (quote / leverage)
    liquidation_price: float | None = None
    take_profit_price: float | None = None
    stop_loss_price: float | None = None
    # id devuelto por la API del proyecto al crear la transacción (ciclo).
    transaction_id: int | None = None

    @property
    def notional(self) -> float:
        return self.buy_quote


@dataclass
class TradeDecision:
    """Decisión tomada por la estrategia.

    ``action`` puede ser: BUY, SELL (spot) o LONG_OPEN, SHORT_OPEN,
    LONG_CLOSE, SHORT_CLOSE (futuros).
    """

    action: str
    price: float
    side: str = "LONG"
    score: float | None = None
    reason: str = ""


@dataclass
class MarketAnalysis:
    """Snapshot del análisis de mercado (se guarda para diagnóstico)."""

    price: float
    score: float
    recommendation: str          # LONG | SHORT | NEUTRAL
    trend: str                   # bullish | bearish | neutral
    indicators: dict
    funding_rate: float | None = None
    mark_price: float | None = None
    index_price: float | None = None
    change_24h_pct: float | None = None
    created_ms: int = 0

