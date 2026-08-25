"""Demo: una operación REAL en la testnet con el cliente de Binance.

Ejecuta el ciclo completo (apertura -> cierre -> registra en la API) usando
las credenciales del .env. Segura: TEST_MODE=1 usa fondos virtuales.

- spot    -> compra + venta.
- futures -> abre LONG (o SHORT con --short) y cierra con TP/SL.

Uso:
    python demo_trade.py
    python demo_trade.py --short
"""
from __future__ import annotations

import logging
import sys
import time

from app.api_reporter import ApiReporter
from app.binance_client import BinanceClient
from app.models import Position
from config import Config

logger = logging.getLogger("demo")


def main() -> None:
    short = "--short" in sys.argv[1:]
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s | %(message)s")
    cfg = Config.load()
    client = BinanceClient(cfg, logger)
    reporter = ApiReporter(cfg.api_url, logger)

    print("=" * 70)
    print(f"DEMO de trading | Mercado: {cfg.market_type} | "
          f"Modo: {'TESTNET' if cfg.test_mode else 'REAL'} | {cfg.symbol}")
    print("=" * 70)

    price = client.get_ticker_price(cfg.symbol)
    print(f"Precio actual: {price:.2f}")

    if cfg.trade_mode == "futures":
        client.set_leverage(cfg.symbol, cfg.leverage)
        client.set_margin_type(cfg.symbol, cfg.margin_type)

        if short:
            order = client.market_open_short(
                cfg.symbol, client.quantity_for_notional(cfg.symbol, cfg.quote_amount * cfg.leverage))
            side, tp_dir = "SHORT", -1
        else:
            order = client.market_open_long(
                cfg.symbol, client.quantity_for_notional(cfg.symbol, cfg.quote_amount * cfg.leverage))
            side, tp_dir = "LONG", +1
        print(f"{side} ABIERTO | orderId={order.order_id} | qty={order.executed_qty} | "
              f"avg={order.avg_price:.2f} | nocional={order.quote_qty:.2f} USDT")

        position = Position(
            symbol=cfg.symbol,
            buy_order_id=order.order_id,
            buy_price=order.avg_price,
            buy_quantity=order.executed_qty,
            buy_quote=order.quote_qty,
            buy_time=order.transact_time,
            test_mode=cfg.test_mode,
            market_type="FUTURES",
            side=side,
            leverage=cfg.leverage,
            margin=round(order.quote_qty / cfg.leverage, 10),
        )
        reporter.create_transaction(position)
        reporter.report_order(cfg.symbol, "BUY" if side == "LONG" else "SELL", order,
                              cfg.test_mode, market_type="FUTURES", position_side=side, leverage=cfg.leverage)

        target = order.avg_price * (1.0 + tp_dir * cfg.futures_take_profit_pct / 100.0)
        stop = order.avg_price * (1.0 - tp_dir * cfg.futures_stop_loss_pct / 100.0)
        print(f"Esperando cierre: TP={target:.2f} / SL={stop:.2f}...")
        closed = None
        deadline = time.time() + 120
        while time.time() < deadline:
            current = client.get_ticker_price(cfg.symbol)
            if side == "LONG" and (current >= target or current <= stop):
                closed = client.market_close_long(cfg.symbol, order.executed_qty)
                break
            if side == "SHORT" and (current <= target or current >= stop):
                closed = client.market_close_short(cfg.symbol, order.executed_qty)
                break
            time.sleep(5)

        if closed is None:
            print("No se alcanzó TP/SL en 120s; cerrando al precio actual...")
            closed = (client.market_close_long if side == "LONG" else client.market_close_short)(
                cfg.symbol, order.executed_qty)

        if side == "LONG":
            profit = (closed.avg_price - position.buy_price) * closed.executed_qty
            profit_pct = (closed.avg_price / position.buy_price - 1.0) * cfg.leverage * 100.0
        else:
            profit = (position.buy_price - closed.avg_price) * closed.executed_qty
            profit_pct = (1.0 - closed.avg_price / position.buy_price) * cfg.leverage * 100.0
        print(f"{side} CERRADO | orderId={closed.order_id} | avg={closed.avg_price:.2f}")
        print(f"PNL: {profit:.4f} USDT ({profit_pct:+.2f}% con {cfg.leverage}x)")

        reporter.close_transaction(position, closed, profit, profit_pct)
        reporter.report_order(cfg.symbol, "SELL" if side == "LONG" else "BUY", closed,
                              cfg.test_mode, market_type="FUTURES", position_side=side, leverage=cfg.leverage)
        reporter.flush(timeout=8)
        print("Ciclo registrado en la API y en MySQL.")
        return

    # --- SPOT: compra + venta ---
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
        market_type="SPOT",
        side="LONG",
        leverage=1,
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
