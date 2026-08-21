"""Validación del bot contra la TESTNET de Binance (sin operar).

Comprueba: conectividad REST, precios, autenticación de las API keys y
recepción de ticks por WebSocket. Se elimina después de la validación.
"""
from __future__ import annotations

import logging
import time

from app.api_reporter import ApiReporter
from app.binance_client import BinanceAPIError, BinanceClient
from app.price_stream import PriceStream
from app.state import TradingState
from config import Config


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)-8s %(name)s | %(message)s")
    logger = logging.getLogger("validate")
    cfg = Config.load()
    client = BinanceClient(cfg, logger)

    print("\n[1] Ping testnet:", client.ping())
    price = client.get_ticker_price(cfg.symbol)
    print(f"[2] Precio {cfg.symbol}: {price:.2f}")

    try:
        account = client._signed("GET", "/api/v3/account")
        balances = {b["asset"]: float(b["free"]) for b in account.get("balances", []) if float(b["free"]) > 0}
        print("[3] Auth OK. Balances:", balances)
        auth_ok = True
    except BinanceAPIError as exc:
        print(f"[3] Auth FALLÓ: {exc}")
        auth_ok = False

    print("\n[4] Stream WebSocket (5s):", cfg.binance_ws_url)
    state = TradingState(max_sma_window=cfg.sma_period)
    stream = PriceStream(cfg.binance_ws_url, on_trade=state.update_tick, max_reconnect_delay=5)
    stream.start()
    start = time.time()
    while time.time() - start < 5:
        time.sleep(0.2)
    stream.stop()
    ticks = len(state._sma_window)
    print(f"    ticks recibidos: {ticks} | último precio: {state.get_price()}")
    if ticks == 0:
        print("    ¡ADVERTENCIA! No llegó ningún tick del stream.")

    print(f"\nResumen: auth_ok={auth_ok} ticks={ticks} testnet={'SÍ' if cfg.test_mode else 'NO'}")


if __name__ == "__main__":
    main()
