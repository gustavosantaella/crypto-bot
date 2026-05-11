import logging
import time
from binance.client import Client
from src.config.settings import BINANCE_API_KEY, BINANCE_SECRET_KEY, IS_TESTNET
from src.config.trading_params import LEVERAGE, MARGIN_TYPE

class ExchangeManager:
    def __init__(self):
        self.client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=IS_TESTNET)
        self._sync_time()
        self.set_leverage(LEVERAGE)
        # self.set_margin_type(MARGIN_TYPE) # Comentado porque solo se puede cambiar si no hay posiciones

    def _sync_time(self):
        try:
            server_time = self.client.futures_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
        except Exception as e:
            logging.error(f"Error sync time: {e}")

    def set_leverage(self, leverage, symbol="SOLUSDT"):
        try:
            self.client.futures_change_leverage(symbol=symbol, leverage=leverage)
            logging.info(f"Leverage configurado a {leverage}x para {symbol}")
        except Exception as e:
            logging.error(f"Error setting leverage: {e}")

    def get_balance(self, asset='USDT'):
        try:
            balances = self.client.futures_account_balance()
            for b in balances:
                if b['asset'] == asset:
                    return float(b['availableBalance'])
            return 0.0
        except Exception as e:
            logging.error(f"Error balance {asset}: {e}")
            return 0.0

    def get_ticker_price(self, symbol):
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            logging.error(f"Error precio {symbol}: {e}")
            return None

    def get_klines(self, symbol, interval='1m', limit=100):
        try:
            return self.client.futures_klines(symbol=symbol, interval=interval, limit=limit)
        except Exception as e:
            logging.error(f"Error klines: {e}")
            return []

    def get_symbol_info(self, symbol):
        try:
            info = self.client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    return s
            return None
        except Exception as e:
            logging.error(f"Error getting symbol info: {e}")
            return None

    def round_quantity(self, symbol, quantity):
        info = self.get_symbol_info(symbol)
        if not info: return quantity
        for f in info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = float(f['stepSize'])
                precision = str(step_size).find('1') - str(step_size).find('.')
                if precision < 0: precision = 0
                return round(quantity, precision)
        return quantity

    def execute_market_order(self, symbol, side, quantity):
        try:
            rounded_qty = self.round_quantity(symbol, quantity)
            logging.info(f"Ejecutando FUTURES {side} de {rounded_qty} {symbol}")
            return self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=rounded_qty
            )
        except Exception as e:
            logging.error(f"Error {side} futures order: {e}")
            return None
