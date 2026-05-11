import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from src.core.exchange import ExchangeManager
from src.config.trading_params import SYMBOL

logging.basicConfig(level=logging.INFO)

def main():
    exchange = ExchangeManager()
    
    # Obtener posición actual de Binance
    positions = exchange.client.futures_position_information(symbol=SYMBOL)
    pos = next((p for p in positions if p['symbol'] == SYMBOL), None)
    
    if not pos or float(pos['positionAmt']) == 0:
        print("No hay posiciones abiertas en Binance.")
        return

    qty = abs(float(pos['positionAmt']))
    side = 'SELL' if float(pos['positionAmt']) < 0 else 'BUY'
    
    # Precios objetivo basados en lo que vimos en el dashboard
    # Trade #71: Entry 97.61, SHORT
    # Calculados anteriormente: TP 94.7857, SL 99.4929
    tp = 94.7857
    sl = 99.4929
    
    print(f"Sincronizando TP/SL para {SYMBOL}: Side={side}, Qty={qty}, TP={tp}, SL={sl}")
    exchange.cancel_all_orders(SYMBOL)
    exchange.set_sl_tp(SYMBOL, side, sl, tp, qty)
    print("Sincronización completada.")

if __name__ == "__main__":
    main()
