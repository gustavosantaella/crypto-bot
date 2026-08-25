"""Punto de entrada del bot de trading (spot y futuros).

Uso:
    python main.py

Requisitos:
    - ``bot/.env`` con las credenciales y la configuración (TRADE_MODE,
      TEST_MODE, apalancamiento...).
    - La API del proyecto levantada para registrar las transacciones.
"""
from __future__ import annotations

import logging

from app.api_client import ApiClient
from app.api_reporter import ApiReporter
from app.binance_client import BinanceClient
from app.candle_buffer import CandleBuffer, interval_to_ms
from app.engine import TradingEngine
from app.price_stream import PriceStream
from app.state import TradingState
from app.strategy import FuturesStrategy, SMAStrategy
from config import Config


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("crypto_bot")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s | %(levelname)-8s | %(name)-22s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    logger.addHandler(handler)
    logger.propagate = False
    return logger


def main() -> None:
    cfg = Config.load()
    logger = setup_logging()

    logger.info("=" * 70)
    logger.info("Crypto Bot | Mercado: %s | Modo: %s | Símbolo: %s",
                cfg.market_type, "TESTNET" if cfg.test_mode else "PRODUCCIÓN", cfg.symbol)
    logger.info("=" * 70)

    # En futuros, un buffer de velas alimenta los indicadores (RSI, MACD,
    # EMA...) en tiempo real; en spot se mantiene la ventana de SMA clásica.
    candle_buffer: CandleBuffer | None = None
    if cfg.trade_mode == "futures":
        candle_buffer = CandleBuffer(
            interval_ms=interval_to_ms(cfg.kline_interval),
            limit=cfg.kline_limit,
        )

    state = TradingState(max_sma_window=cfg.sma_period, candle_buffer=candle_buffer)
    client = BinanceClient(cfg, logger)
    reporter = ApiReporter(cfg.api_url, logger)
    api_client = ApiClient(cfg.api_url, logger)
    stream = PriceStream(
        cfg.binance_ws_url,
        on_trade=state.update_tick,
        max_reconnect_delay=cfg.max_reconnect_delay,
    )

    if cfg.trade_mode == "futures":
        strategy: SMAStrategy | FuturesStrategy = FuturesStrategy(state, cfg)
    else:
        strategy = SMAStrategy(state, cfg.buy_threshold_pct, cfg.sell_profit_pct)

    engine = TradingEngine(cfg, client, stream, state, strategy, reporter, api_client, logger)

    engine.run()


if __name__ == "__main__":
    main()
