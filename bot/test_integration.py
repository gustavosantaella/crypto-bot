"""Test de integración local (sin credenciales reales de Binance).

Valida el flujo completo del bot:
    feed de precios (simulado) → estrategia SMA → engine → órdenes (simuladas)
    → ApiReporter (background) → API real → MySQL.

REQUISITO: la API debe estar corriendo en http://localhost:8000 (el bot NO la
arranca; se lanza por separado con ``cd api && python main.py``).
"""
from __future__ import annotations

import logging
import random
import threading
import time
import urllib.request
from dataclasses import replace

from app.api_reporter import ApiReporter
from app.engine import TradingEngine
from app.models import FilledOrder
from app.state import TradingState
from app.strategy import SMAStrategy
from config import Config


def wait_for_api(url: str, timeout: float = 5.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(f"{url}/health", timeout=1)
            return True
        except Exception:
            time.sleep(0.3)
    return False


class FakeStream(threading.Thread):
    """Reemplaza al PriceStream: hilo que inyecta ticks sintéticos, sin red."""

    def __init__(self, prices: list[float], state: TradingState, delay: float = 0.05):
        super().__init__(name="FakeStream", daemon=True)
        self._prices = prices
        self._state = state
        self._delay = delay
        self._stop = threading.Event()

    def run(self) -> None:
        seq = 1
        for price in self._prices:
            if self._stop.is_set():
                break
            self._state.update_tick({"e": "trade", "p": str(price), "t": seq})
            seq += 1
            time.sleep(self._delay)

    def stop(self) -> None:
        self._stop.set()


class FakeBinanceClient:
    """Simula el mercado: compra con un 0.1% de slippage y vende con +0.1%."""

    def __init__(self, state: TradingState):
        self._state = state
        self._orders: list[FilledOrder] = []
        self.symbol_info = {
            "step_size": 0.00001,
            "min_qty": 0.00001,
            "min_notional": 5.0,
        }

    def get_ticker_price(self, symbol: str) -> float:
        return self._state.get_price()

    def get_symbol_info(self, symbol: str) -> dict:
        return self.symbol_info

    def market_buy(self, symbol: str, quote_amount: float, reference_price: float | None = None) -> FilledOrder:
        price = self._state.get_price() * 0.999
        qty = quote_amount / price
        order = FilledOrder(
            symbol=symbol, side="BUY", order_id=random.randint(10_000_000, 99_999_999),
            status="FILLED", executed_qty=qty, avg_price=price, quote_qty=qty * price,
            transact_time=int(time.time() * 1000), raw={},
        )
        self._orders.append(order)
        return order

    def market_sell(self, symbol: str, quantity: float) -> FilledOrder:
        price = self._state.get_price() * 1.001
        order = FilledOrder(
            symbol=symbol, side="SELL", order_id=random.randint(10_000_000, 99_999_999),
            status="FILLED", executed_qty=quantity, avg_price=price, quote_qty=quantity * price,
            transact_time=int(time.time() * 1000), raw={},
        )
        self._orders.append(order)
        return order


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s | %(message)s")
    logger = logging.getLogger("integration")

    cfg = Config.load()
    if not wait_for_api(cfg.api_url):
        print("\n[FAIL] La API no esta disponible. Arranca primero con: cd api && python main.py")
        raise SystemExit(1)

    # Para la prueba, muestreamos la SMA muy rápido (cada ~50ms reales).
    cfg = replace(cfg, check_interval_ms=50, sma_sample_ms=50)

    state = TradingState(max_sma_window=cfg.sma_period)

    # Precios: subida suave (llena la SMA), caída (dispara COMPRA),
    # luego subida (dispara VENTA con ganancia).
    prices = [100.0 + i * 0.2 for i in range(0, cfg.sma_period + 1)]
    prices += [99.0]                      # caída → COMPRA
    prices += [100.0, 101.0, 102.0]       # subida → VENTA (target ~99.4)

    stream = FakeStream(prices, state, delay=0.03)
    fake_client = FakeBinanceClient(state)
    reporter = ApiReporter(cfg.api_url, logger)
    strategy = SMAStrategy(state, cfg.buy_threshold_pct, cfg.sell_profit_pct)
    engine = TradingEngine(cfg, fake_client, stream, state, strategy, reporter, logger)

    stream.start()  # hilo que inyecta precios
    engine._warmup()

    deadline = time.time() + 25
    while state.total_closed_trades == 0 and time.time() < deadline:
        engine._maybe_sample()
        engine._process_cycle()
        time.sleep(0.03)

    stream.stop()
    reporter.flush(timeout=8)

    print(f"\nCiclos cerrados: {state.total_closed_trades}")
    print(f"Ganancia total: {state.total_profit:.6f} USDT")
    print(f"Posición restante: {state.position}")

    if state.total_closed_trades == 1 and state.total_profit > 0:
        print("\n[OK] TEST INTEGRACION: se compro, se vendio con ganancia y se reporto a la API.")
    else:
        print("\n[FAIL] TEST INTEGRACION fallo.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()

