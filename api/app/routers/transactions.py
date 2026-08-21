"""Endpoints de transacciones (ciclos compra→venta)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Transaction
from ..schemas import TransactionClose, TransactionCreate, TransactionOut, TransactionStats

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

Db = Annotated[Session, Depends(get_db)]


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionCreate, db: Db) -> Transaction:
    """Crea una transacción cuando el bot COMPRA."""
    transaction = Transaction(**payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.patch("/{transaction_id}", response_model=TransactionOut)
def close_transaction(transaction_id: int, payload: TransactionClose, db: Db) -> Transaction:
    """Cierra una transacción cuando el bot VENDE (actualiza precios/ganancia)."""
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    for key, value in payload.model_dump().items():
        setattr(transaction, key, value)
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    db: Db,
    test_mode: bool | None = Query(default=None, description="Filtrar por modo de prueba"),
    status: str | None = Query(default=None, pattern="^(OPEN|CLOSED|CANCELED)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Transaction]:
    query = select(Transaction).order_by(Transaction.buy_time.desc())
    if test_mode is not None:
        query = query.where(Transaction.test_mode == test_mode)
    if status is not None:
        query = query.where(Transaction.status == status)
    return list(db.execute(query.limit(limit).offset(offset)).scalars().all())


@router.get("/stats", response_model=TransactionStats)
def get_stats(db: Db) -> TransactionStats:
    total = db.scalar(select(func.count(Transaction.id))) or 0
    open_count = db.scalar(select(func.count(Transaction.id)).where(Transaction.status == "OPEN")) or 0
    closed_count = db.scalar(select(func.count(Transaction.id)).where(Transaction.status == "CLOSED")) or 0
    test_count = db.scalar(select(func.count(Transaction.id)).where(Transaction.test_mode.is_(True))) or 0
    real_count = total - test_count

    def _sum_profit(*filters) -> float:
        stmt = (
            select(func.coalesce(func.sum(Transaction.profit), 0))
            .where(Transaction.status == "CLOSED", *filters)
        )
        return float(db.scalar(stmt) or 0.0)

    def _count(*filters) -> int:
        stmt = select(func.count(Transaction.id)).where(Transaction.status == "CLOSED", *filters)
        return int(db.scalar(stmt) or 0)

    total_profit = _sum_profit()
    total_profit_test = _sum_profit(Transaction.test_mode.is_(True))
    total_profit_real = _sum_profit(Transaction.test_mode.is_(False))

    wins_test = _count(Transaction.test_mode.is_(True), Transaction.profit > 0)
    losses_test = _count(Transaction.test_mode.is_(True), Transaction.profit < 0)
    wins_real = _count(Transaction.test_mode.is_(False), Transaction.profit > 0)
    losses_real = _count(Transaction.test_mode.is_(False), Transaction.profit < 0)

    avg_profit = total_profit / closed_count if closed_count else 0.0
    return TransactionStats(
        total=total,
        open=open_count,
        closed=closed_count,
        test_mode=test_count,
        real=real_count,
        total_profit=total_profit,
        avg_profit=avg_profit,
        total_profit_test=total_profit_test,
        total_profit_real=total_profit_real,
        wins_test=wins_test,
        losses_test=losses_test,
        wins_real=wins_real,
        losses_real=losses_real,
    )


@router.post("/{transaction_id}/cancel", response_model=TransactionOut)
def cancel_transaction(transaction_id: int, db: Db) -> Transaction:
    """Cancela una transacción OPEN huérfana (p. ej. tras matar el bot)."""
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    transaction.status = "CANCELED"
    db.commit()
    db.refresh(transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: int, db: Db) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return transaction
