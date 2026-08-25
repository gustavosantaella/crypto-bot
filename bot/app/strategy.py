"""Estrategias de trading: spot (compra barato / vende caro) y futuros (LONG/SHORT).

Spot (:class:`SMAStrategy`)
---------------------------
1. **Compra**: cuando el precio cae por debajo de la media móvil simple (SMA)
   menos un umbral. La SMA actúa como "precio de referencia".
2. **Venta**: cuando el precio sube por encima del precio de compra más un
   margen de ganancia fijo (``SELL_PROFIT_PCT``).

Futuros (:class:`FuturesStrategy`)
----------------------------------
Decide LONG/SHORT con un **score compuesto** de indicadores (ver
``bot/app/indicators.py``): tendencia (precio vs EMA50/EMA200), RSI, MACD y
Bollinger. Con posición abierta cierra por take-profit, stop-loss o cuando la
señal se gira en contra.
"""
from __future__ import annotations

from config import Config

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
class FuturesStrategy:
    """Estrategia de futuros basada en el score compuesto de indicadores."""

    def __init__(self, state: TradingState, config: Config) -> None:
        self._state = state
        self._cfg = config

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _analyze(self) -> dict | None:
        """Análisis actual; None si el buffer de velas no está listo."""
        if self._state.candle_buffer is None:
            return None
        if not self._state.candle_buffer.is_ready(min_candles=60):
            return None
        self._state.candle_buffer.roll_current()
        analysis = self._state.candle_buffer.analyze(self._cfg)
        self._state.last_analysis = analysis
        return analysis

    # ------------------------------------------------------------------
    # Evaluación
    # ------------------------------------------------------------------
    def evaluate(self) -> TradeDecision | None:
        price = self._state.get_price()
        if price is None:
            return None
        analysis = self._analyze()
        if analysis is None:
            return None

        score = analysis["score"]
        position = self._state.position

        # ---------- Con posición abierta: ¿cerrar? ----------
        if position is not None:
            return self._evaluate_exit(position, price, score)

        # ---------- Sin posición: ¿abrir LONG o SHORT? ----------
        if score >= self._cfg.signal_open_score:
            return TradeDecision(
                "LONG_OPEN", price, side="LONG", score=score,
                reason=f"Score {score:+.2f} >= {self._cfg.signal_open_score} (tendencia alcista)",
            )
        if score <= -self._cfg.signal_open_score:
            return TradeDecision(
                "SHORT_OPEN", price, side="SHORT", score=score,
                reason=f"Score {score:+.2f} <= -{self._cfg.signal_open_score} (tendencia bajista)",
            )
        return None

    # ------------------------------------------------------------------
    # Salidas (take-profit / stop-loss / señal en contra)
    # ------------------------------------------------------------------
    def _evaluate_exit(self, position, price: float, score: float) -> TradeDecision | None:
        cfg = self._cfg
        entry = position.buy_price
        if entry <= 0:
            return None

        if position.side == "LONG":
            tp = position.take_profit_price or entry * (1.0 + cfg.futures_take_profit_pct / 100.0)
            sl = position.stop_loss_price or entry * (1.0 - cfg.futures_stop_loss_pct / 100.0)
            if price >= tp:
                return TradeDecision("LONG_CLOSE", price, side="LONG", score=score, reason="Take-profit LONG")
            if price <= sl:
                return TradeDecision("LONG_CLOSE", price, side="LONG", score=score, reason="Stop-loss LONG")
            if score <= -self._cfg.signal_close_score:
                return TradeDecision(
                    "LONG_CLOSE", price, side="LONG", score=score,
                    reason=f"Señal en contra (score {score:+.2f})",
                )
        else:  # SHORT
            tp = position.take_profit_price or entry * (1.0 - cfg.futures_take_profit_pct / 100.0)
            sl = position.stop_loss_price or entry * (1.0 + cfg.futures_stop_loss_pct / 100.0)
            if price <= tp:
                return TradeDecision("SHORT_CLOSE", price, side="SHORT", score=score, reason="Take-profit SHORT")
            if price >= sl:
                return TradeDecision("SHORT_CLOSE", price, side="SHORT", score=score, reason="Stop-loss SHORT")
            if score >= self._cfg.signal_close_score:
                return TradeDecision(
                    "SHORT_CLOSE", price, side="SHORT", score=score,
                    reason=f"Señal en contra (score {score:+.2f})",
                )
        return None

