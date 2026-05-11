import time
import logging
from src.core.exchange import ExchangeManager
from src.strategies.rsi_strategy import RSIStrategy
from src.config.trading_params import SYMBOL, TRADE_PERCENTAGE, CHECK_INTERVAL, TAKE_PROFIT_PCT, STOP_LOSS_PCT
from src.utils.db import log_trade, log_price, update_status, get_last_status
from src.utils.telegram_notifier import TelegramNotifier

class BotEngine:
    def __init__(self):
        self.exchange = ExchangeManager()
        self.has_position = False
        self.last_buy_price = None
        self.target_tp = None
        self.target_sl = None
        self.trade_type = "LONG"
        self._recover_state()
        self._sync_db_status()

    def _sync_db_status(self):
        update_status(self.has_position, self.last_buy_price, self.target_tp, self.target_sl, self.trade_type)
    def _check_notional(self, price, quantity):
        return (price * quantity) >= 10.0 # Mínimo 10 USDT

    def _recover_state(self):
        try:
            positions = self.exchange.client.futures_position_information(symbol=SYMBOL)
            pos = next((p for p in positions if p['symbol'] == SYMBOL), None)
            if pos:
                amount = float(pos['positionAmt'])
                self.has_position = abs(amount) > 0.001
                if self.has_position:
                    self.trade_type = "LONG" if amount > 0 else "SHORT"
            
            status = get_last_status()
            if status:
                self.last_buy_price = float(status.last_buy_price) if status.last_buy_price else None
                self.target_tp = float(status.target_take_profit) if status.target_take_profit else None
                self.target_sl = float(status.target_stop_loss) if status.target_stop_loss else None
                if not self.has_position: # Si no hay posicion real, resetear
                    self.last_buy_price = self.target_tp = self.target_sl = None
            
            logging.info(f"Bot FUTUROS listo. Posición: {self.has_position} ({self.trade_type})")
        except Exception as e:
            logging.error(f"Error recovering state: {e}")

    def start(self):
        logging.info("--- Iniciando Motor FUTUROS (Estrategia Pro) ---")
        from src.config.trading_params import LEVERAGE, TIMEFRAME
        while True:
            try:
                price = self.exchange.get_ticker_price(SYMBOL)
                klines = self.exchange.get_klines(SYMBOL, interval=TIMEFRAME)
                if not price or not klines: continue

                rsi, atr = RSIStrategy.calculate_indicators(klines)
                signal, new_tp, new_sl = RSIStrategy.get_signal(rsi, atr, price, self.has_position, self.target_tp, self.target_sl, self.trade_type)
                
                log_price(SYMBOL, price, rsi)
                logging.info(f"[{SYMBOL}] Price: {price} | RSI: {rsi:.2f} | ATR: {atr:.4f} | Signal: {signal}")

                if signal == 'BUY': # Open LONG
                    balance_usdt = self.exchange.get_balance('USDT')
                    buy_quantity = (balance_usdt * TRADE_PERCENTAGE * LEVERAGE) / price
                    
                    if self._check_notional(price, buy_quantity):
                        if self.exchange.execute_market_order(SYMBOL, 'BUY', buy_quantity):
                            self.has_position = True
                            self.trade_type = "LONG"
                            self.last_buy_price = price
                            self.target_tp = new_tp
                            self.target_sl = new_sl
                            
                            # Configurar SL y TP en Binance (Órdenes reales)
                            self.exchange.set_sl_tp(SYMBOL, 'BUY', self.target_sl, self.target_tp, buy_quantity)
                            
                            log_trade(SYMBOL, 'BUY', price, buy_quantity, balance_before=balance_usdt, trade_type="LONG", target_tp=self.target_tp, target_sl=self.target_sl)
                            update_status(True, price, self.target_tp, self.target_sl, "LONG")
                            TelegramNotifier.notify_trade_open(SYMBOL, 'LONG', price, buy_quantity, self.target_tp, self.target_sl)

                elif signal == 'SELL_SHORT': # Open SHORT
                    balance_usdt = self.exchange.get_balance('USDT')
                    sell_quantity = (balance_usdt * TRADE_PERCENTAGE * LEVERAGE) / price
                    
                    if self._check_notional(price, sell_quantity):
                        if self.exchange.execute_market_order(SYMBOL, 'SELL', sell_quantity):
                            self.has_position = True
                            self.trade_type = "SHORT"
                            self.last_buy_price = price
                            self.target_tp = new_tp
                            self.target_sl = new_sl
                            
                            # Configurar SL y TP en Binance (Órdenes reales)
                            self.exchange.set_sl_tp(SYMBOL, 'SELL', self.target_sl, self.target_tp, sell_quantity)
                            
                            log_trade(SYMBOL, 'SELL', price, sell_quantity, balance_before=balance_usdt, trade_type="SHORT", target_tp=self.target_tp, target_sl=self.target_sl)
                            update_status(True, price, self.target_tp, self.target_sl, "SHORT")
                            TelegramNotifier.notify_trade_open(SYMBOL, 'SHORT', price, sell_quantity, self.target_tp, self.target_sl)

                elif signal == 'SELL': # Close LONG
                    positions = self.exchange.client.futures_position_information(symbol=SYMBOL)
                    pos = next((p for p in positions if p['symbol'] == SYMBOL), None)
                    if pos:
                        qty = abs(float(pos['positionAmt']))
                        if self.exchange.execute_market_order(SYMBOL, 'SELL', qty):
                            pnl = (price - self.last_buy_price) * qty
                            log_trade(SYMBOL, 'SELL', price, qty, balance_before=qty*price, pnl=pnl, trade_type="LONG")
                            TelegramNotifier.notify_trade_close(SYMBOL, 'LONG (Exit)', price, qty, pnl)
                            self.has_position = False
                            # Cancelar órdenes pendientes (SL/TP) en Binance
                            self.exchange.cancel_all_orders(SYMBOL)
                            update_status(False, None, None, None, "LONG")

                elif signal == 'BUY_BACK': # Close SHORT
                    positions = self.exchange.client.futures_position_information(symbol=SYMBOL)
                    pos = next((p for p in positions if p['symbol'] == SYMBOL), None)
                    if pos:
                        qty = abs(float(pos['positionAmt']))
                        if self.exchange.execute_market_order(SYMBOL, 'BUY', qty):
                            pnl = (self.last_buy_price - price) * qty
                            log_trade(SYMBOL, 'BUY', price, qty, balance_before=qty*price, pnl=pnl, trade_type="SHORT")
                            TelegramNotifier.notify_trade_close(SYMBOL, 'SHORT (Exit)', price, qty, pnl)
                            self.has_position = False
                            # Cancelar órdenes pendientes (SL/TP) en Binance
                            self.exchange.cancel_all_orders(SYMBOL)
                            update_status(False, None, None, None, "SHORT")
                    else:
                        logging.warning("Señal SELL recibida pero no hay balance de activo.")

            except Exception as e:
                logging.error(f"Engine error: {e}")
            
            time.sleep(CHECK_INTERVAL)
