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
    """Posición abierta: una compra que aún no se ha vendido."""

    symbol: str
    buy_order_id: int
    buy_price: float
    buy_quantity: float
    buy_quote: float
    buy_time: int
    test_mode: bool = True
    # id devuelto por la API del proyecto al crear la transacción (ciclo).
    transaction_id: int | None = None


@dataclass
class TradeDecision:
    """Decisión tomada por la estrategia."""

    action: str  # "BUY" | "SELL"
    price: float
