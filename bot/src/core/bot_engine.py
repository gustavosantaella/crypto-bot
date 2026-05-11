import time
import logging
from src.core.exchange import ExchangeManager
from src.strategies.rsi_strategy import RSIStrategy
from src.config.trading_params import SYMBOL, QUANTITY, CHECK_INTERVAL

class BotEngine:
    def __init__(self):
        self.exchange = ExchangeManager()
        self.has_position = False
        self.last_buy_price = None
        self._check_initial_balance()

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
                
                logging.info(f"[{SYMBOL}] Price: {price} | RSI: {rsi:.2f} | Signal: {signal}")

                if signal == 'BUY':
                    if self.exchange.execute_market_order(SYMBOL, 'BUY', QUANTITY):
                        self.has_position = True
                        self.last_buy_price = price
                        logging.info("COMPRA EJECUTADA")
                        
                elif signal == 'SELL':
                    if self.exchange.execute_market_order(SYMBOL, 'SELL', QUANTITY):
                        self.has_position = False
                        self.last_buy_price = None
                        logging.info("VENTA EJECUTADA")

            except Exception as e:
                logging.error(f"Engine error: {e}")
            
            time.sleep(CHECK_INTERVAL)
