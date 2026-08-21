"""Endpoints de balance spot de Binance."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..binance import BinanceAccountClient, BinanceBalanceError
from ..config import settings

router = APIRouter(prefix="/api/balance", tags=["balance"])


@router.get("")
def get_balance(
    test_mode: Annotated[bool | None, Query(description="true=testnet, false=producción")] = None,
) -> dict:
    """Balance de la cuenta spot del ambiente indicado.

    ``test_mode`` lo define el switch del portal; si no se indica se usa el
    ``TEST_MODE`` de ``api/.env``.
    """
    try:
        balances = BinanceAccountClient(test_mode=test_mode).get_balances()
    except BinanceBalanceError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo consultar Binance: {exc}") from exc
    return {
        "test_mode": test_mode,
        "symbol": settings.symbol,
        "currency": settings.currency,
        "balances": balances,
    }
