import pandas as pd
from src.config.trading_params import RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, STOP_LOSS_PCT, TAKE_PROFIT_PCT

class RSIStrategy:
    @staticmethod
    def calculate_rsi(data):
        if len(data) < RSI_PERIOD + 1:
            return 50.0 # Neutral RSI if not enough data
            
        df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ct', 'qa', 'nt', 'tb', 'tq', 'i'])
        df['c'] = df['c'].astype(float)
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        
        # Evitar división por cero
        loss = loss.replace(0, 0.00001)
        
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    @staticmethod
    def get_signal(rsi, current_price, has_position, target_tp=None, target_sl=None, trade_type="LONG"):
        if not has_position:
            # Lógica para entrar en LONG
            if rsi < RSI_OVERSOLD:
                return 'BUY'
            # Lógica para entrar en SHORT
            if rsi > RSI_OVERBOUGHT:
                return 'SELL_SHORT'
        else:
            if trade_type == "LONG":
                if rsi > RSI_OVERBOUGHT: return 'SELL'
                if target_tp and current_price >= target_tp: return 'SELL'
                if target_sl and current_price <= target_sl: return 'SELL'
            
            elif trade_type == "SHORT":
                if rsi < RSI_OVERSOLD: return 'BUY_BACK'
                if target_tp and current_price <= target_tp: return 'BUY_BACK'
                if target_sl and current_price >= target_sl: return 'BUY_BACK'
                    
        return 'HOLD'
