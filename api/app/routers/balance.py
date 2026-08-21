"""Endpoints de balance spot de Binance."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException

from ..binance import BinanceAccountClient, BinanceBalanceError
from ..config import settings

router = APIRouter(prefix="/api/balance", tags=["balance"])


@router.get("")
def get_balance() -> dict:
    """Balance de la cuenta spot (según TEST_MODE de api/.env)."""
    try:
        balances = BinanceAccountClient().get_balances()
    except BinanceBalanceError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo consultar Binance: {exc}") from exc
    return {
        "test_mode": settings.test_mode,
        "symbol": settings.symbol,
        "currency": settings.currency,
        "balances": balances,
    }
