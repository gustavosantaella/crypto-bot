import requests
import logging
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")

def notify_ws(type: str, data: dict):
    """
    Envía una notificación a la API para que sea distribuida por WebSocket.
    """
    try:
        payload = {
            "type": type,
            "data": data
        }
        requests.post(f"{API_URL}/notify", json=payload, timeout=2)
    except Exception as e:
        logging.error(f"Error notifying WS: {e}")

def notify_price_update(symbol: str, price: float, rsi: float):
    notify_ws("PRICE_UPDATE", {
        "symbol": symbol,
        "price": price,
        "rsi": rsi,
        "timestamp": None # El portal usará la hora actual si es None
    })

def notify_status_update(status_data: dict):
    notify_ws("STATUS_UPDATE", status_data)

def notify_new_trade(trade_data: dict):
    notify_ws("NEW_TRADE", trade_data)
