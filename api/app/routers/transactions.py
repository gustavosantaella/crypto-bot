"""Endpoints de transacciones (ciclos compra→venta)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..database import get_db
from ..events import event_bus
from ..models import Transaction
from ..schemas import TransactionClose, TransactionCreate, TransactionOut, TransactionStats

router = APIRouter(prefix="/api/transactions", tags=["transactions"])

Db = Annotated[Session, Depends(get_db)]


def _publish(event_type: str, transaction: Transaction) -> None:
    """Publica un evento SSE con los datos de la transacción."""
    event_bus.publish(event_type, TransactionOut.model_validate(transaction).model_dump())


@router.post("", response_model=TransactionOut, status_code=201)
def create_transaction(payload: TransactionCreate, db: Db) -> Transaction:
    """Crea una transacción cuando el bot COMPRA."""
    transaction = Transaction(**payload.model_dump())
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    _publish("transaction.created", transaction)
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
    _publish("transaction.updated", transaction)
    return transaction


@router.get("", response_model=list[TransactionOut])
def list_transactions(
    db: Db,
    test_mode: bool | None = Query(default=None, description="Filtrar por modo de prueba"),
    market_type: str | None = Query(default=None, pattern="^(SPOT|FUTURES)$", description="Filtrar por mercado"),
    side: str | None = Query(default=None, pattern="^(LONG|SHORT)$"),
    status: str | None = Query(default=None, pattern="^(OPEN|CLOSED|CANCELED)$"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> list[Transaction]:
    query = select(Transaction).order_by(Transaction.buy_time.desc())
    if test_mode is not None:
        query = query.where(Transaction.test_mode == test_mode)
    if market_type is not None:
        query = query.where(Transaction.market_type == market_type)
    if side is not None:
        query = query.where(Transaction.side == side)
    if status is not None:
        query = query.where(Transaction.status == status)
    return list(db.execute(query.limit(limit).offset(offset)).scalars().all())


@router.get("/stats", response_model=TransactionStats)
def get_stats(
    db: Db,
    test_mode: Annotated[bool | None, Query(description="true=testnet, false=producción")] = None,
    market_type: Annotated[str | None, Query(pattern="^(SPOT|FUTURES)$", description="Filtrar por mercado")] = None,
) -> TransactionStats:
    """Resumen de transacciones.

    - Sin filtros: totales con desglose TEST/REAL y SPOT/FUTURES.
    - Con ``test_mode``: solo el ambiente indicado (lo que el switch del portal
      selecciona).
    - Con ``market_type``: solo ese mercado (spot o futuros).
    - Con ambos: solo ese mercado dentro de ese ambiente (p. ej. futuros +
      testnet).
    """

    def _count_total(*filters) -> int:
        stmt = select(func.count(Transaction.id)).where(*filters)
        return int(db.scalar(stmt) or 0)

    def _sum_profit(*filters) -> float:
        stmt = (
            select(func.coalesce(func.sum(Transaction.profit), 0))
            .where(Transaction.status == "CLOSED", *filters)
        )
        return float(db.scalar(stmt) or 0.0)

    def _count(*filters) -> int:
        stmt = select(func.count(Transaction.id)).where(Transaction.status == "CLOSED", *filters)
        return int(db.scalar(stmt) or 0)

    # Filtro de mercado (opcional) que se combina con el de ambiente.
    market_filter = (Transaction.market_type == market_type) if market_type else None

    if test_mode is not None:
        env_filter = Transaction.test_mode.is_(test_mode)
        if market_filter is not None:
            env_filter = env_filter & market_filter
        total = _count_total(env_filter)
        open_count = _count_total(env_filter, Transaction.status == "OPEN")
        closed_count = _count_total(env_filter, Transaction.status == "CLOSED")
        total_profit = _sum_profit(env_filter)
        wins = _count(env_filter, Transaction.profit > 0)
        losses = _count(env_filter, Transaction.profit < 0)
        avg_profit = total_profit / closed_count if closed_count else 0.0
        # Desglose por mercado (respetando el filtro de mercado si viene).
        spot_filter = env_filter & (Transaction.market_type == "SPOT")
        futures_filter = env_filter & (Transaction.market_type == "FUTURES")
        total_spot = _count_total(spot_filter)
        total_futures = _count_total(futures_filter)
        profit_spot = _sum_profit(spot_filter)
        profit_futures = _sum_profit(futures_filter)
        return TransactionStats(
            total=total,
            open=open_count,
            closed=closed_count,
            test_mode=total if test_mode else 0,
            real=0 if test_mode else total,
            total_profit=total_profit,
            avg_profit=avg_profit,
            total_profit_test=total_profit if test_mode else 0.0,
            total_profit_real=0.0 if test_mode else total_profit,
            wins_test=wins if test_mode else 0,
            losses_test=losses if test_mode else 0,
            wins_real=0 if test_mode else wins,
            losses_real=0 if test_mode else losses,
            total_spot=total_spot,
            total_futures=total_futures,
            total_profit_spot=profit_spot,
            total_profit_futures=profit_futures,
            wins_spot=_count(spot_filter, Transaction.profit > 0),
            losses_spot=_count(spot_filter, Transaction.profit < 0),
            wins_futures=_count(futures_filter, Transaction.profit > 0),
            losses_futures=_count(futures_filter, Transaction.profit < 0),
        )

    # Sin filtro de ambiente: aplicar el de mercado a todo si viene.
    base_filters = [market_filter] if market_filter is not None else []
    total = _count_total(*base_filters)
    open_count = _count_total(*base_filters, Transaction.status == "OPEN")
    closed_count = _count_total(*base_filters, Transaction.status == "CLOSED")
    test_count = _count_total(*base_filters, Transaction.test_mode.is_(True))
    real_count = total - test_count

    total_profit = _sum_profit(*base_filters)
    total_profit_test = _sum_profit(*base_filters, Transaction.test_mode.is_(True))
    total_profit_real = _sum_profit(*base_filters, Transaction.test_mode.is_(False))

    wins_test = _count(*base_filters, Transaction.test_mode.is_(True), Transaction.profit > 0)
    losses_test = _count(*base_filters, Transaction.test_mode.is_(True), Transaction.profit < 0)
    wins_real = _count(*base_filters, Transaction.test_mode.is_(False), Transaction.profit > 0)
    losses_real = _count(*base_filters, Transaction.test_mode.is_(False), Transaction.profit < 0)

    avg_profit = total_profit / closed_count if closed_count else 0.0

    # Desglose spot / futuros (respetando el filtro de mercado si viene).
    spot_filter = Transaction.market_type == "SPOT"
    futures_filter = Transaction.market_type == "FUTURES"
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
        total_spot=_count_total(*base_filters, spot_filter),
        total_futures=_count_total(*base_filters, futures_filter),
        total_profit_spot=_sum_profit(*base_filters, spot_filter),
        total_profit_futures=_sum_profit(*base_filters, futures_filter),
        wins_spot=_count(*base_filters, spot_filter, Transaction.profit > 0),
        losses_spot=_count(*base_filters, spot_filter, Transaction.profit < 0),
        wins_futures=_count(*base_filters, futures_filter, Transaction.profit > 0),
        losses_futures=_count(*base_filters, futures_filter, Transaction.profit < 0),
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
    _publish("transaction.canceled", transaction)
    return transaction


@router.get("/{transaction_id}", response_model=TransactionOut)
def get_transaction(transaction_id: int, db: Db) -> Transaction:
    transaction = db.get(Transaction, transaction_id)
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transacción no encontrada")
    return transaction
