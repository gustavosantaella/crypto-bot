"""API del proyecto Crypto Bot.

Registra en MySQL las transacciones (ciclos compra→venta o apertura→cierre)
y las órdenes que el bot ejecuta en Binance, distinguiendo spot y futuros.
También expone el balance/posiciones y el análisis de mercado (LONG/SHORT).

Uso:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .analysis_emitter import AnalysisEmitter
from .config import settings
from .database import Base, engine, ensure_database
from .migrations import run_migrations
from .price_stream import PriceStream
from .routers import analysis, balance, events, orders, transactions

# Streams de precios de Binance (testnet y producción) que publican por SSE.
_price_streams: list[PriceStream] = []
_analysis_emitter: AnalysisEmitter | None = None


def _stream_host(test_mode: bool) -> str:
    if settings.trade_mode == "futures":
        return "stream.testnet.binancefuture.com" if test_mode else "fstream.binance.com"
    return "stream.testnet.binance.vision" if test_mode else "stream.binance.com"


def _start_price_streams() -> None:
    """Conecta los WebSockets de precios de ambos ambientes (públicos)."""
    stream = settings.binance_ws_stream
    environments = [
        ("testnet", True),
        ("prod", False),
    ]
    for name, test_mode in environments:
        url = f"wss://{_stream_host(test_mode)}/stream?streams={stream}"
        price_stream = PriceStream(name, url, test_mode, settings.symbol)
        price_stream.start()
        _price_streams.append(price_stream)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Crea la base de datos y las tablas si no existen.
    ensure_database()
    Base.metadata.create_all(bind=engine)
    # Migra tablas existentes para los nuevos campos de futuros (no rompe spot).
    try:
        run_migrations()
    except Exception as exc:  # noqa: BLE001
        print(f"[migraciones] No se pudieron aplicar: {exc}")
    # Conecta los WebSockets de precios y publica por SSE.
    _start_price_streams()
    # Señal de mercado en vivo (LONG/SHORT/NEUTRAL) por SSE.
    global _analysis_emitter
    _analysis_emitter = AnalysisEmitter()
    _analysis_emitter.start()
    yield
    for price_stream in _price_streams:
        price_stream.stop()
    if _analysis_emitter is not None:
        _analysis_emitter.stop()


app = FastAPI(
    title="Crypto Bot API",
    description="API para registrar transacciones y órdenes del bot de Binance "
                "(spot y futuros) y publicar el análisis de mercado.",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS abierto para el portal Angular en desarrollo.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200", "http://127.0.0.1:4200"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(transactions.router)
app.include_router(orders.router)
app.include_router(balance.router)
app.include_router(events.router)
app.include_router(analysis.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "crypto-bot-api", "market_type": settings.market_type}
