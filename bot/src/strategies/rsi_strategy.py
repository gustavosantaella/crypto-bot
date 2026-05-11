import pandas as pd
from src.config.trading_params import RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, STOP_LOSS_PCT, TAKE_PROFIT_PCT

class RSIStrategy:
    @staticmethod
    def calculate_rsi(data):
        df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ct', 'qa', 'nt', 'tb', 'tq', 'i'])
        df['c'] = df['c'].astype(float)
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1]

    @staticmethod
    def get_signal(rsi, current_price, last_buy_price, has_position):
        if not has_position:
            if rsi < RSI_OVERSOLD:
                return 'BUY'
        else:
            if rsi > RSI_OVERBOUGHT:
                return 'SELL'
            
            if last_buy_price:
                change = (current_price - last_buy_price) / last_buy_price
                if change > TAKE_PROFIT_PCT or change < -STOP_LOSS_PCT:
                    return 'SELL'
        return 'HOLD'
