import time
import logging
from src.core.exchange import ExchangeManager
from src.strategies.rsi_strategy import RSIStrategy
from src.config.trading_params import SYMBOL, TRADE_PERCENTAGE, CHECK_INTERVAL, TAKE_PROFIT_PCT, STOP_LOSS_PCT
from src.utils.db import log_trade, log_price, update_status, get_last_status

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

    def _recover_state(self):
        # 1. Recuperar del exchange (Saldo real)
        balance = self.exchange.get_balance('SOL')
        self.has_position = balance > 0.01 # Umbral mínimo para detectar posición (aprox $1)
        
        # 2. Recuperar de DB (Estado lógico)
        status = get_last_status()
        if status:
            self.last_buy_price = float(status.last_buy_price) if status.last_buy_price else None
            self.target_tp = float(status.target_take_profit) if status.target_take_profit else None
            self.target_sl = float(status.target_stop_loss) if status.target_stop_loss else None
            self.trade_type = status.trade_type if status.trade_type else "LONG"
            
            if self.has_position and not self.last_buy_price:
                logging.warning("Posición detectada sin precio de compra en DB.")
        
        logging.info(f"Bot listo. Posición: {self.has_position} | TP: {self.target_tp} | SL: {self.target_sl}")

    def _check_notional(self, price, quantity):
        return (price * quantity) >= 10.0 # Mínimo 10 USDT

    def start(self):
        logging.info("--- Iniciando Motor del Bot ---")
        while True:
            try:
                price = self.exchange.get_ticker_price(SYMBOL)
                klines = self.exchange.get_klines(SYMBOL)
                
                if not price or not klines:
                    continue

                rsi = RSIStrategy.calculate_rsi(klines)
                signal = RSIStrategy.get_signal(
                    rsi, 
                    price, 
                    self.has_position, 
                    target_tp=self.target_tp, 
                    target_sl=self.target_sl,
                    trade_type=self.trade_type
                )
                
                # Log price to DB
                log_price(SYMBOL, price, rsi)
                
                logging.info(f"[{SYMBOL}] Price: {price} | RSI: {rsi:.2f} | Signal: {signal}")

                if signal == 'BUY':
                    balance_usdt = self.exchange.get_balance('USDT')
                    amount_to_spend = balance_usdt * TRADE_PERCENTAGE
                    buy_quantity = amount_to_spend / price
                    
                    if not self._check_notional(price, buy_quantity):
                        logging.warning(f"Orden BUY cancelada: Valor insuficiente ({price * buy_quantity:.2f} < 10 USDT)")
                        continue

                    balance_before = balance_usdt
                    if self.exchange.execute_market_order(SYMBOL, 'BUY', buy_quantity):
                        self.has_position = True
                        self.last_buy_price = price
                        self.target_tp = price * (1 + TAKE_PROFIT_PCT)
                        self.target_sl = price * (1 - STOP_LOSS_PCT)
                        
                        # Guardamos la cantidad real comprada (redondeada por el exchange)
                        actual_qty = self.exchange.round_quantity(SYMBOL, buy_quantity)
                        
                        log_trade(SYMBOL, 'BUY', price, actual_qty, balance_before=balance_before, 
                                  target_tp=self.target_tp, target_sl=self.target_sl)
                        update_status(True, price, self.target_tp, self.target_sl, self.trade_type)
                        logging.info(f"COMPRA EJECUTADA | Cantidad: {actual_qty} | TP: {self.target_tp} | SL: {self.target_sl}")
                        
                elif signal == 'SELL':
                    # Vendemos todo el balance del activo (SOL) para cerrar posición
                    base_asset = SYMBOL.replace('USDT', '')
                    balance_base = self.exchange.get_balance(base_asset)
                    
                    if balance_base > 0:
                        if self.exchange.execute_market_order(SYMBOL, 'SELL', balance_base):
                            pnl = (price - self.last_buy_price) * balance_base if self.last_buy_price else 0
                            
                            log_trade(SYMBOL, 'SELL', price, balance_base, balance_before=balance_base, pnl=pnl,
                                      target_tp=self.target_tp, target_sl=self.target_sl)
                            
                            self.has_position = False
                            self.last_buy_price = None
                            self.target_tp = None
                            self.target_sl = None
                            update_status(False, None, None, None, self.trade_type)
                            logging.info(f"VENTA EJECUTADA | PnL: {pnl:.4f}")
                    else:
                        logging.warning("Señal SELL recibida pero no hay balance de activo.")

            except Exception as e:
                logging.error(f"Engine error: {e}")
            
            time.sleep(CHECK_INTERVAL)
