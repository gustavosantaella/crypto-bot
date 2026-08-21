"""Schemas Pydantic para la API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    """Cuerpo para crear una transacción (al comprar)."""

    symbol: str = Field(min_length=1, max_length=20)
    status: str = "OPEN"
    test_mode: bool = True
    buy_order_id: int | None = None
    buy_price: float
    buy_quantity: float
    buy_quote: float
    buy_time: datetime


class TransactionClose(BaseModel):
    """Cuerpo para cerrar una transacción (al vender)."""

    status: str = "CLOSED"
    sell_order_id: int
    sell_price: float
    sell_quantity: float
    sell_quote: float
    sell_time: datetime
    profit: float
    profit_pct: float


class TransactionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    symbol: str
    status: str
    test_mode: bool
    buy_order_id: int | None
    buy_price: float
    buy_quantity: float
    buy_quote: float
    buy_time: datetime
    sell_order_id: int | None
    sell_price: float | None
    sell_quantity: float | None
    sell_quote: float | None
    sell_time: datetime | None
    profit: float | None
    profit_pct: float | None
    created_at: datetime
    updated_at: datetime


class TransactionStats(BaseModel):
    total: int
    open: int
    closed: int
    test_mode: int
    real: int
    total_profit: float
    avg_profit: float
    # Ganancia/pérdida separada por ambiente (TEST_MODE).
    total_profit_test: float
    total_profit_real: float
    wins_test: int
    losses_test: int
    wins_real: int
    losses_real: int


class OrderCreate(BaseModel):
    symbol: str = Field(min_length=1, max_length=20)
    side: str = Field(pattern="^(BUY|SELL)$")
    binance_order_id: int
    price: float
    quantity: float
    quote_quantity: float
    status: str
    test_mode: bool = True
    transaction_id: int | None = None


class OrderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    transaction_id: int | None
    symbol: str
    side: str
    binance_order_id: int
    price: float
    quantity: float
    quote_quantity: float
    status: str
    test_mode: bool
    created_at: datetime
