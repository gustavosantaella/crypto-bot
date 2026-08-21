"""Demo: una compra+venta REAL en la testnet con el cliente de Binance.

Ejecuta el ciclo completo (compra -> venta -> registra en la API) usando las
credenciales del .env. Segura: TEST_MODE=1 usa fondos virtuales.

Uso:
    python demo_trade.py
"""
from __future__ import annotations

import logging
import time

from app.api_reporter import ApiReporter
from app.binance_client import BinanceClient
from app.models import Position
from config import Config

logger = logging.getLogger("demo")


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s | %(message)s")
    cfg = Config.load()
    client = BinanceClient(cfg, logger)
    reporter = ApiReporter(cfg.api_url, logger)

    print("=" * 70)
    print(f"DEMO de trading | Modo: {'TESTNET' if cfg.test_mode else 'REAL'} | {cfg.symbol}")
    print("=" * 70)

    price = client.get_ticker_price(cfg.symbol)
    print(f"Precio actual: {price:.2f}")

    # --- COMPRA ---
    buy = client.market_buy(cfg.symbol, cfg.quote_amount)
    print(f"COMPRA  | orderId={buy.order_id} | qty={buy.executed_qty} | "
          f"avg={buy.avg_price:.2f} | gasto={buy.quote_qty:.2f} USDT")

    position = Position(
        symbol=cfg.symbol,
        buy_order_id=buy.order_id,
        buy_price=buy.avg_price,
        buy_quantity=buy.executed_qty,
        buy_quote=buy.quote_qty,
        buy_time=buy.transact_time,
        test_mode=cfg.test_mode,
    )
    reporter.create_transaction(position)
    reporter.report_order(cfg.symbol, "BUY", buy, cfg.test_mode)

    # --- VENTA (cuando el precio suba SELL_PROFIT_PCT%, con timeout) ---
    target = buy.avg_price * (1.0 + cfg.sell_profit_pct / 100.0)
    print(f"Esperando venta: precio objetivo >= {target:.2f} (+{cfg.sell_profit_pct}%)...")
    sold = None
    deadline = time.time() + 120
    while time.time() < deadline:
        current = client.get_ticker_price(cfg.symbol)
        if current >= target:
            sold = client.market_sell(cfg.symbol, buy.executed_qty)
            break
        time.sleep(5)

    if sold is None:
        print("No se alcanzó el objetivo en 120s; vendiendo al precio actual...")
        sold = client.market_sell(cfg.symbol, buy.executed_qty)

    profit = sold.quote_qty - position.buy_quote
    profit_pct = (sold.avg_price / position.buy_price - 1.0) * 100.0
    print(f"VENTA   | orderId={sold.order_id} | avg={sold.avg_price:.2f} | "
          f"ingreso={sold.quote_qty:.2f} USDT")
    print(f"GANANCIA: {profit:.4f} USDT ({profit_pct:+.2f}%)")

    reporter.close_transaction(position, sold, profit, profit_pct)
    reporter.report_order(cfg.symbol, "SELL", sold, cfg.test_mode)
    reporter.flush(timeout=8)
    print("Ciclo registrado en la API y en MySQL.")


if __name__ == "__main__":
    main()
