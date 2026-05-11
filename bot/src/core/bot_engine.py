import time
import logging
from src.core.exchange import ExchangeManager
from src.strategies.rsi_strategy import RSIStrategy
from src.config.trading_params import SYMBOL, QUANTITY, CHECK_INTERVAL
from src.utils.db import log_trade, log_price, update_status

class BotEngine:
    def __init__(self):
        self.exchange = ExchangeManager()
        self.has_position = False
        self.last_buy_price = None
        self._check_initial_balance()
        self._sync_db_status()

    def _sync_db_status(self):
        update_status(self.has_position, self.last_buy_price)

    def _check_initial_balance(self):
        balance = self.exchange.get_balance('SOL')
        self.has_position = balance >= QUANTITY
        logging.info(f"Bot listo. Posición: {self.has_position}")

    def start(self):
        logging.info("--- Iniciando Motor del Bot ---")
        while True:
            try:
                price = self.exchange.get_ticker_price(SYMBOL)
                klines = self.exchange.get_klines(SYMBOL)
                
                if not price or not klines:
                    continue

                rsi = RSIStrategy.calculate_rsi(klines)
                signal = RSIStrategy.get_signal(rsi, price, self.last_buy_price, self.has_position)
                
                # Log price to DB
                log_price(SYMBOL, price, rsi)
                
                logging.info(f"[{SYMBOL}] Price: {price} | RSI: {rsi:.2f} | Signal: {signal}")

                if signal == 'BUY':
                    balance_before = self.exchange.get_balance('USDT') # Or whatever base currency
                    if self.exchange.execute_market_order(SYMBOL, 'BUY', QUANTITY):
                        self.has_position = True
                        self.last_buy_price = price
                        log_trade(SYMBOL, 'BUY', price, QUANTITY, balance_before=balance_before)
                        update_status(True, price)
                        logging.info("COMPRA EJECUTADA")
                        
                elif signal == 'SELL':
                    balance_before = self.exchange.get_balance('SOL')
                    if self.exchange.execute_market_order(SYMBOL, 'SELL', QUANTITY):
                        pnl = (price - self.last_buy_price) * QUANTITY if self.last_buy_price else 0
                        self.has_position = False
                        self.last_buy_price = None
                        log_trade(SYMBOL, 'SELL', price, QUANTITY, balance_before=balance_before, pnl=pnl)
                        update_status(False, None)
                        logging.info(f"VENTA EJECUTADA | PnL: {pnl:.4f}")

            except Exception as e:
                logging.error(f"Engine error: {e}")
            
            time.sleep(CHECK_INTERVAL)
