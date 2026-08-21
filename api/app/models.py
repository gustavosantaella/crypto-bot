"""Modelos SQLAlchemy.

Entidad principal ``transactions``: cada fila representa UN ciclo completo
compra→venta, con las marcas de tiempo de compra y venta, la ganancia y el
flag ``test_mode`` para distinguir registros de prueba de los reales.

La entidad ``orders`` guarda auditoría de cada orden enviada a Binance.
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

    # --- Compra ---
    buy_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    buy_price: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    buy_quantity: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    buy_quote: Mapped[float] = mapped_column(DECIMAL(30, 10), nullable=False)
    buy_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    # --- Venta ---
    sell_order_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sell_price: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    sell_quantity: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    sell_quote: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    sell_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Resultado ---
    profit: Mapped[float | None] = mapped_column(DECIMAL(30, 10), nullable=True)
    profit_pct: Mapped[float | None] = mapped_column(DECIMAL(12, 6), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    __table_args__ = (
        Index("idx_transactions_status", "status"),
        Index("idx_transactions_test_mode", "test_mode"),
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
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    __table_args__ = (
        Index("idx_orders_binance_order_id", "binance_order_id"),
    )
