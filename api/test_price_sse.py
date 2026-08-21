"""Prueba del SSE de precios: conecta a /api/events y muestra los eventos price."""
from __future__ import annotations

import urllib.request

STREAM_URL = "http://127.0.0.1:8000/api/events"

req = urllib.request.Request(STREAM_URL)
prices: dict = {}
transactions = 0
with urllib.request.urlopen(req, timeout=12) as resp:
    event_type = None
    for raw in resp:
        line = raw.decode("utf-8", errors="replace").strip()
        if line.startswith("event:"):
            event_type = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and event_type:
            import json

            data = json.loads(line.split(":", 1)[1].strip())
            if event_type == "price":
                key = "testnet" if data.get("test_mode") else "prod"
                prices[key] = (data.get("symbol"), data.get("price"))
            elif event_type.startswith("transaction."):
                transactions += 1
            event_type = None
        if len(prices) >= 2:
            break

print("precios recibidos:", prices)
if prices.get("testnet") and prices.get("prod"):
    print("[OK] SSE de precios: ambos ambientes llegando en vivo")
else:
    print("[FAIL] faltan precios de algun ambiente:", prices)
