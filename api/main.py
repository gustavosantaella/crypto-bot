"""Launcher independiente de la API.

Inicia la API sin depender del bot (el bot solo hace peticiones HTTP).

Uso:
    cd api
    python main.py

Alternativa con uvicorn directo:
    uvicorn app.main:app --reload --port 8000
"""
from __future__ import annotations

import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="localhost",
        port=8000,
        reload=False,
    )
