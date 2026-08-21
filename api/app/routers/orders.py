"""Endpoints de órdenes (auditoría de cada orden enviada a Binance)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Order
from ..schemas import OrderCreate, OrderOut

router = APIRouter(prefix="/api/orders", tags=["orders"])

Db = Annotated[Session, Depends(get_db)]


@router.post("", response_model=OrderOut, status_code=201)
def create_order(payload: OrderCreate, db: Db) -> Order:
    order = Order(**payload.model_dump())
    db.add(order)
    db.commit()
    db.refresh(order)
    return order


@router.get("", response_model=list[OrderOut])
def list_orders(
    db: Db,
    symbol: str | None = Query(default=None),
    side: str | None = Query(default=None, pattern="^(BUY|SELL)$"),
    test_mode: bool | None = Query(default=None, description="true=testnet, false=producción"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Order]:
    query = select(Order).order_by(Order.created_at.desc())
    if symbol:
        query = query.where(Order.symbol == symbol.upper())
    if side:
        query = query.where(Order.side == side)
    if test_mode is not None:
        query = query.where(Order.test_mode.is_(test_mode))
    return list(db.execute(query.limit(limit).offset(offset)).scalars().all())
