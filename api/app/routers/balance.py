"""Endpoints de balance y posiciones de Binance (spot y futuros)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..binance import BinanceAccountClient, BinanceBalanceError
from ..config import settings

router = APIRouter(prefix="/api/balance", tags=["balance"])


@router.get("")
def get_balance(
    test_mode: Annotated[bool | None, Query(description="true=testnet, false=producción")] = None,
    market_type: Annotated[str | None, Query(description="SPOT o FUTURES")] = None,
) -> dict:
    """Balance (y posiciones en futuros) del ambiente y mercado indicados.

    ``test_mode`` lo define el switch del portal; si no se indica se usa el
    ``TEST_MODE`` de ``api/.env``. ``market_type`` define si se consulta la
    cuenta spot o la de futuros.
    """
    market_type = (market_type or settings.market_type).upper()
    if market_type not in ("SPOT", "FUTURES"):
        raise HTTPException(status_code=400, detail="market_type debe ser SPOT o FUTURES")

    try:
        client = BinanceAccountClient(test_mode=test_mode, market_type=market_type)
        balances = client.get_balances()
        positions = client.get_positions(settings.symbol) if market_type == "FUTURES" else []
    except BinanceBalanceError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo consultar Binance: {exc}") from exc

    return {
        "test_mode": test_mode,
        "market_type": market_type,
        "symbol": settings.symbol,
        "currency": settings.currency,
        "leverage": settings.leverage,
        "balances": balances,
        "positions": positions,
    }
