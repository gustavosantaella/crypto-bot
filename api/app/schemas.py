"""Schemas Pydantic para la API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TransactionCreate(BaseModel):
    """Cuerpo para crear una transacción (al comprar/abrir posición)."""

    symbol: str = Field(min_length=1, max_length=20)
    status: str = "OPEN"
    test_mode: bool = True
    buy_order_id: int | None = None
    buy_price: float
    buy_quantity: float
    buy_quote: float
    buy_time: datetime

    # Identificación del mercado (spot por defecto para retrocompatibilidad).
    market_type: str = "SPOT"
    side: str = "LONG"
    leverage: int = 1
    notional: float | None = None
    margin: float | None = None
    liquidation_price: float | None = None
    take_profit_price: float | None = None
    stop_loss_price: float | None = None


class TransactionClose(BaseModel):
    """Cuerpo para cerrar una transacción (al vender/cerrar posición)."""

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
    market_type: str
    side: str
    leverage: int
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
    notional: float | None
    margin: float | None
    liquidation_price: float | None
    take_profit_price: float | None
    stop_loss_price: float | None
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
    # Separación spot / futuros.
    total_spot: int = 0
    total_futures: int = 0
    total_profit_spot: float = 0.0
    total_profit_futures: float = 0.0
    wins_spot: int = 0
    losses_spot: int = 0
    wins_futures: int = 0
    losses_futures: int = 0


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
    # Identificación del mercado (spot por defecto).
    market_type: str = "SPOT"
    position_side: str | None = None
    leverage: int = 1


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
    market_type: str
    position_side: str | None
    leverage: int
    created_at: datetime
