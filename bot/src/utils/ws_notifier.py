import requests
import logging
import os

API_URL = os.getenv("API_URL", "http://localhost:8000/api/v1")


def notify_ws(type: str, data: dict):
    """
    Envía una notificación a la API para que sea distribuida por WebSocket
    a todos los clientes del portal conectados.
    """
    try:
        payload = {"type": type, "data": data}
        requests.post(f"{API_URL}/notify", json=payload, timeout=2)
    except Exception as e:
        logging.error(f"Error notifying WS: {e}")


def notify_price_update(symbol: str, price: float, indicators: dict):
    """
    Emite una actualización de precio + TODOS los indicadores técnicos al portal.

    indicators debe contener (todos opcionales, usa 0 si no disponible):
      rsi          → RSI actual
      rsi_prev     → RSI vela anterior (para detectar giro)
      atr          → ATR actual (volatilidad)
      adx          → ADX (fuerza de tendencia)
      plus_di      → DI+ (presión compradora)
      minus_di     → DI- (presión vendedora)
      ema_fast     → EMA rápida (ej: EMA50)
      ema_slow     → EMA lenta (ej: EMA200)
      volume_ratio → Volumen actual vs promedio
    """
    notify_ws("PRICE_UPDATE", {
        "symbol":       symbol,
        "price":        price,
        # RSI
        "rsi":          round(indicators.get("rsi", 0), 2),
        "rsi_prev":     round(indicators.get("rsi_prev", 0), 2),
        # Tendencia
        "adx":          round(indicators.get("adx", 0), 2),
        "plus_di":      round(indicators.get("plus_di", 0), 2),
        "minus_di":     round(indicators.get("minus_di", 0), 2),
        # EMAs
        "ema_fast":     round(indicators.get("ema_fast", 0), 4),
        "ema200":       round(indicators.get("ema_slow", 0), 4),   # alias para el portal
        # Volatilidad y volumen
        "atr":          round(indicators.get("atr", 0), 4),
        "volume_ratio": round(indicators.get("volume_ratio", 0), 4),
        # Timestamp (el portal usa la hora local si es None)
        "timestamp":    None
    })


def notify_status_update(status_data: dict):
    """Emite el estado completo del bot (posicion, SL, TP, DCA, breakeven)."""
    notify_ws("STATUS_UPDATE", status_data)


def notify_new_trade(trade_data: dict):
    """Emite una nueva operacion para actualizar el historial en el portal."""
    notify_ws("NEW_TRADE", trade_data)
