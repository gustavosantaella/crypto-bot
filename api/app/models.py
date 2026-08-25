"""Modelos SQLAlchemy.

Entidad principal ``transactions``: cada fila representa UN ciclo completo
(compra→venta o apertura→cierre), con las marcas de tiempo, la ganancia, el
flag ``test_mode`` y el tipo de mercado (``market_type``: SPOT o FUTURES)
para distinguir los registros de spot y futuros.

La entidad ``orders`` guarda auditoría de cada orden enviada a Binance.

Los campos nuevos (apalancamiento, margen, liquidación, TP/SL...) son
nullable o tienen default para no romper los registros antiguos de spot.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    DECIMAL,
    Enum,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        Enum("OPEN", "CLOSED", "CANCELED", name="transaction_status"),
        nullable=False,
        default="OPEN",
    )
    test_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # --- Identificación del mercado ---
    market_type: Mapped[str] = mapped_column(String(10), nullable=False, default="SPOT")
    side: Mapped[str] = mapped_column(String(10), nullable=False, default="LONG")
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # --- Compra / apertura ---
    buy_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    buy_price: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    buy_quantity: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    buy_quote: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    buy_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # --- Venta / cierre ---
    sell_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sell_price: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    sell_quantity: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    sell_quote: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    sell_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Resultado ---
    profit: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    profit_pct: Mapped[float | None] = mapped_column(DECIMAL(12, 6), nullable=True)

    # --- Futuros (null en spot) ---
    notional: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    margin: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    liquidation_price: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    take_profit_price: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    stop_loss_price: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_transactions_status", "status"),
        Index("idx_transactions_test_mode", "test_mode"),
        Index("idx_transactions_market_type", "market_type"),
        Index("idx_transactions_buy_time", "buy_time"),
    )


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True, index=True)
    symbol: Mapped[str] = mapped_column(String(20), nullable=False)
    side: Mapped[str] = mapped_column(Enum("BUY", "SELL", name="order_side"), nullable=False)
    binance_order_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    price: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    quantity: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    quote_quantity: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    test_mode: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # --- Identificación del mercado ---
    market_type: Mapped[str] = mapped_column(String(10), nullable=False, default="SPOT")
    position_side: Mapped[str | None] = mapped_column(String(10), nullable=True)
    leverage: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_orders_binance_order_id", "binance_order_id"),
        Index("idx_orders_market_type", "market_type"),
    )
