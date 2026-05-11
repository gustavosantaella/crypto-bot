import logging
import time
from binance.client import Client
from src.config.settings import BINANCE_API_KEY, BINANCE_SECRET_KEY, IS_TESTNET

class ExchangeManager:
    def __init__(self):
        self.client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=IS_TESTNET)
        self._sync_time()
        
    def _sync_time(self):
        try:
            server_time = self.client.get_server_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
        except Exception as e:
            logging.error(f"Error sync time: {e}")

    def get_balance(self, asset):
        try:
            balance = self.client.get_asset_balance(asset=asset)
            return float(balance['free']) if balance else 0.0
        except Exception as e:
            logging.error(f"Error balance {asset}: {e}")
            return 0.0

    def get_ticker_price(self, symbol):
        try:
            ticker = self.client.get_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logging.error(f"Error precio {symbol}: {e}")
            return None

    def get_klines(self, symbol, interval='15m', limit=100):
        try:
            return self.client.get_klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            logging.error(f"Error klines: {e}")
            return []

    def execute_market_order(self, symbol, side, quantity):
        try:
            return self.client.create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=quantity
            )
        except Exception as e:
            logging.error(f"Error {side} order: {e}")
            return None
