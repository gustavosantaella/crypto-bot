import logging
import time
from binance.client import Client
from src.config.settings import BINANCE_API_KEY, BINANCE_SECRET_KEY, IS_TESTNET
from src.config.trading_params import LEVERAGE, MARGIN_TYPE, SYMBOL

# Número de velas a solicitar al exchange.
# Mínimo 250 para que la EMA200 tenga suficientes datos históricos.
# Si es menor, los primeros valores del EMA serán incorrectos (NaN o distorsionados).
KLINES_LIMIT = 250

class ExchangeManager:
    def __init__(self):
        self.client = Client(BINANCE_API_KEY, BINANCE_SECRET_KEY, testnet=IS_TESTNET)
        self._sync_time()
        # Configurar apalancamiento al iniciar usando el símbolo del .env
        self.set_leverage(LEVERAGE, symbol=SYMBOL)
        # El tipo de margen solo se puede cambiar cuando NO hay posiciones abiertas.
        # Descomentar la siguiente línea solo si necesitas cambiarlo manualmente:
        # self.set_margin_type(MARGIN_TYPE)

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

    def get_klines(self, symbol, interval='1m', limit=KLINES_LIMIT):
        """
        Obtiene las velas (candlesticks) del exchange.
        Por defecto solicita KLINES_LIMIT=250 velas para garantizar
        que indicadores como EMA200 tengan suficientes datos históricos.
        """
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

    def set_sl_tp(self, symbol, side, stop_loss, take_profit, quantity, max_retries=3):
        """
        Coloca órdenes SL y TP en Binance con reintentos.
        El error -4130 ocurre cuando Binance no ha procesado aún la cancelación
        de las órdenes anteriores. Se reintenta hasta max_retries veces con delay.
        """
        exit_side = 'SELL' if side == 'BUY' else 'BUY'
        rounded_sl = self.round_price(symbol, stop_loss)
        rounded_tp = self.round_price(symbol, take_profit)
        orders_placed = []

        for attempt in range(1, max_retries + 1):
            orders_placed = []

            # Crear Stop Loss
            try:
                sl_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=exit_side,
                    type='STOP_MARKET',
                    stopPrice=rounded_sl,
                    closePosition=True,
                    workingType='MARK_PRICE'
                )
                logging.info(f"SUCCESS: Stop Loss en {rounded_sl} (intento {attempt})")
                orders_placed.append(sl_order)
            except Exception as e:
                logging.error(f"FAIL: Stop Loss ({rounded_sl}) intento {attempt}: {e}")
                if attempt < max_retries:
                    time.sleep(1.5)
                    continue

            # Crear Take Profit
            try:
                tp_order = self.client.futures_create_order(
                    symbol=symbol,
                    side=exit_side,
                    type='TAKE_PROFIT_MARKET',
                    stopPrice=rounded_tp,
                    closePosition=True,
                    workingType='MARK_PRICE'
                )
                logging.info(f"SUCCESS: Take Profit en {rounded_tp} (intento {attempt})")
                orders_placed.append(tp_order)
            except Exception as e:
                logging.error(f"FAIL: Take Profit ({rounded_tp}) intento {attempt}: {e}")
                if attempt < max_retries:
                    time.sleep(1.5)
                    continue

            # Si ambas órdenes se colocaron, salir del loop
            if len(orders_placed) == 2:
                break

            time.sleep(1.5)

        return orders_placed

    def cancel_all_orders(self, symbol, wait_ms=1500):
        """
        Cancela todas las órdenes abiertas y espera wait_ms milisegundos
        para que Binance procese la cancelación antes de colocar nuevas órdenes.
        Esto previene el error -4130 (orden SL/TP existente conflictiva).
        """
        try:
            self.client.futures_cancel_all_open_orders(symbol=symbol)
            logging.info(f"Todas las órdenes pendientes de {symbol} han sido canceladas.")
            time.sleep(wait_ms / 1000)  # Esperar a que Binance procese la cancelación
        except Exception as e:
            logging.error(f"Error cancelando órdenes: {e}")

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
