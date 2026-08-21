"""API del proyecto Crypto Bot.

Registra en MySQL las transacciones (ciclos compra→venta) y las órdenes que
el bot ejecuta en Binance.

Uso:
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import Base, engine, ensure_database
from .routers import balance, orders, transactions


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Crea la base de datos y las tablas si no existen.
    ensure_database()
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="Crypto Bot API",
    description="API para registrar transacciones y órdenes del bot de Binance.",
    version="1.0.0",
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


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "crypto-bot-api"}
