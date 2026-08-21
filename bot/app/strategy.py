"""Estrategia de trading: comprar barato y vender caro.

Reglas (evaluadas en cada ciclo del engine):

1. **Compra**: cuando el precio de mercado cae por debajo de la media móvil
   simple (SMA) menos un umbral. La SMA actúa como "precio de referencia":
   si el precio es sensiblemente menor que el promedio reciente, se considera
   barato y se compra.
2. **Venta**: cuando el precio sube por encima del precio de compra más un
   margen de ganancia fijo. Esto garantiza que NUNCA vendemos por debajo de
   lo que compramos: la venta solo se dispara si
   ``precio >= precio_compra * (1 + SELL_PROFIT_PCT/100)``.
"""
from __future__ import annotations

from .models import TradeDecision
from .state import TradingState


class SMAStrategy:
    def __init__(
        self,
        state: TradingState,
        buy_threshold_pct: float,
        sell_profit_pct: float,
    ) -> None:
        self._state = state
        self._buy_threshold_pct = max(buy_threshold_pct, 0.0)
        self._sell_profit_pct = max(sell_profit_pct, 0.0)

    def evaluate(self) -> TradeDecision | None:
        price = self._state.get_price()
        if price is None:
            return None

        # ---------- Si ya hay posición, solo evaluamos vender ----------
        if self._state.has_position():
            position = self._state.position
            sell_target = position.buy_price * (1.0 + self._sell_profit_pct / 100.0)
            if price >= sell_target:
                return TradeDecision("SELL", price)
            return None

        # ---------- Sin posición: ¿es buen momento para comprar? ----------
        sma = self._state.sma()
        if sma is None or sma <= 0:
            return None  # aún no hay suficiente historia de precios

        buy_limit = sma * (1.0 - self._buy_threshold_pct / 100.0)
        if price <= buy_limit:
            return TradeDecision("BUY", price)
        return None
