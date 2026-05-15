from binance.client import Client
import time
from app.core.config import settings

class ExchangeService:
    def __init__(self):
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        try:
            self.client = Client(
                settings.BINANCE_API_KEY, 
                settings.BINANCE_SECRET_KEY, 
                testnet=settings.IS_TESTNET
            )
            self._sync_time()
        except Exception as e:
            print(f"Error initializing Binance Client: {e}")

    def _sync_time(self):
        if not self.client:
            return
        try:
            server_time = self.client.futures_time()
            self.client.timestamp_offset = server_time['serverTime'] - int(time.time() * 1000)
        except Exception as e:
            print(f"Error syncing time: {e}")

    def get_all_balances(self):
        if not self.client:
            self._initialize_client()
        
        if not self.client:
            return []
            
        try:
            balances = self.client.futures_account_balance()
            filtered = []
            for b in balances:
                free = float(b.get('availableBalance', 0))
                total = float(b.get('balance', 0))
                locked = total - free
                if total > 0:
                    filtered.append({
                        "asset": b['asset'],
                        "free": str(free),
                        "locked": str(max(0, locked))
                    })
            return filtered
        except Exception as e:
            print(f"Error in get_all_balances: {e}")
            return []

    def get_ticker_price(self, symbol):
        if not self.client: self._initialize_client()
        try:
            ticker = self.client.futures_symbol_ticker(symbol=symbol)
            return float(ticker['price'])
        except Exception as e:
            print(f"Error precio {symbol}: {e}")
            return None

    def get_symbol_info(self, symbol):
        if not self.client: self._initialize_client()
        try:
            info = self.client.futures_exchange_info()
            for s in info['symbols']:
                if s['symbol'] == symbol:
                    return s
            return None
        except Exception as e:
            print(f"Error getting symbol info: {e}")
            return None

    def round_quantity(self, symbol, quantity):
        info = self.get_symbol_info(symbol)
        if not info: return quantity
        for f in info['filters']:
            if f['filterType'] == 'LOT_SIZE':
                step_size = float(f['stepSize'])
                precision = str(step_size).rstrip('0').split('.')[-1]
                if '.' not in str(step_size):
                    return round(quantity)
                return round(quantity, len(precision))
        return quantity

    def round_price(self, symbol, price):
        info = self.get_symbol_info(symbol)
        if not info: return price
        for f in info['filters']:
            if f['filterType'] == 'PRICE_FILTER':
                tick_size = float(f['tickSize'])
                precision = str(tick_size).rstrip('0').split('.')[-1]
                if '.' not in str(tick_size):
                    return round(price)
                return round(price, len(precision))
        return price

    def execute_market_order(self, symbol, side, quantity):
        if not self.client: self._initialize_client()
        try:
            rounded_qty = self.round_quantity(symbol, quantity)
            print(f"Ejecutando FUTURES {side} de {rounded_qty} {symbol}")
            return self.client.futures_create_order(
                symbol=symbol,
                side=side,
                type='MARKET',
                quantity=rounded_qty
            )
        except Exception as e:
            print(f"Error {side} futures order: {e}")
            return None

    def set_sl_tp(self, symbol, side, stop_loss, take_profit, quantity):
        if not self.client: self._initialize_client()
        exit_side = 'SELL' if side == 'BUY' else 'BUY'
        rounded_sl = self.round_price(symbol, stop_loss)
        rounded_tp = self.round_price(symbol, take_profit)
        orders_placed = []

        try:
            sl_order = self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='STOP_MARKET',
                stopPrice=rounded_sl,
                closePosition=True,
                workingType='MARK_PRICE'
            )
            orders_placed.append(sl_order)
        except Exception as e:
            print(f"FAIL: Stop Loss ({rounded_sl}): {e}")

        try:
            tp_order = self.client.futures_create_order(
                symbol=symbol,
                side=exit_side,
                type='TAKE_PROFIT_MARKET',
                stopPrice=rounded_tp,
                closePosition=True,
                workingType='MARK_PRICE'
            )
            orders_placed.append(tp_order)
        except Exception as e:
            print(f"FAIL: Take Profit ({rounded_tp}): {e}")

        return orders_placed

exchange_service = ExchangeService()
