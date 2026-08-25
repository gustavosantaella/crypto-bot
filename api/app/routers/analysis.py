"""Endpoints de análisis de mercado (señal LONG/SHORT/NEUTRAL)."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query

from ..analysis import MarketAnalyzer

router = APIRouter(prefix="/api/analysis", tags=["analysis"])

_analyzer_cache: dict[tuple[str, bool, str], MarketAnalyzer] = {}


def _get_analyzer(market_type: str, test_mode: bool, interval: str, limit: int) -> MarketAnalyzer:
    from ..config import settings

    key = (market_type, test_mode, f"{interval}:{limit}")
    if key not in _analyzer_cache:
        _analyzer_cache[key] = MarketAnalyzer(
            symbol=settings.symbol,
            interval=interval,
            limit=limit,
        )
    return _analyzer_cache[key]


@router.get("/signal")
def get_signal(
    test_mode: Annotated[bool | None, Query(description="true=testnet, false=producción")] = None,
    market_type: Annotated[str | None, Query(description="SPOT o FUTURES")] = None,
    interval: str = Query(default="1m", description="Intervalo de velas (1m, 5m, 15m...)"),
    limit: int = Query(default=300, ge=100, le=1000),
) -> dict:
    """Señal de mercado: tendencia, score e indicadores (RSI, MACD, EMA...).

    Devuelve la recomendación LONG / SHORT / NEUTRAL para decidir si es buen
    momento de abrir una posición larga o corta (útil en futuros).
    """
    from ..config import settings

    market_type = (market_type or settings.market_type).upper()
    if market_type not in ("SPOT", "FUTURES"):
        raise HTTPException(status_code=400, detail="market_type debe ser SPOT o FUTURES")

    try:
        analyzer = _get_analyzer(market_type, test_mode, interval, limit)
        return analyzer.analyze(market_type=market_type, test_mode=test_mode)
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=f"No se pudo analizar el mercado: {exc}") from exc
