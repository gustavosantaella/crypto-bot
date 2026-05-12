import pandas as pd
from src.config.trading_params import RSI_PERIOD, RSI_OVERSOLD, RSI_OVERBOUGHT, STOP_LOSS_PCT, TAKE_PROFIT_PCT, ATR_PERIOD, ATR_MULTIPLIER, ADX_PERIOD, ADX_THRESHOLD

class RSIStrategy:
    @staticmethod
    def calculate_indicators(data):
        df = pd.DataFrame(data, columns=['ts', 'o', 'h', 'l', 'c', 'v', 'ct', 'qa', 'nt', 'tb', 'tq', 'i'])
        df['c'] = df['c'].astype(float)
        df['h'] = df['h'].astype(float)
        df['l'] = df['l'].astype(float)
        
        # 1. RSI
        delta = df['c'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = loss.replace(0, 0.00001)
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        
        # 2. ATR
        df['tr'] = pd.concat([
            df['h'] - df['l'],
            (df['h'] - df['c'].shift()).abs(),
            (df['l'] - df['c'].shift()).abs()
        ], axis=1).max(axis=1)
        atr = df['tr'].rolling(window=ATR_PERIOD).mean()
        
        # 3. ADX
        up_move = df['h'] - df['h'].shift(1)
        down_move = df['l'].shift(1) - df['l']
        
        plus_dm = pd.Series(0.0, index=df.index)
        minus_dm = pd.Series(0.0, index=df.index)
        
        cond_plus = (up_move > down_move) & (up_move > 0)
        cond_minus = (down_move > up_move) & (down_move > 0)
        
        plus_dm[cond_plus] = up_move[cond_plus]
        minus_dm[cond_minus] = down_move[cond_minus]
        
        alpha = 1 / ADX_PERIOD
        tr_smooth = df['tr'].ewm(alpha=alpha, adjust=False).mean()
        plus_di = 100 * (plus_dm.ewm(alpha=alpha, adjust=False).mean() / tr_smooth)
        minus_di = 100 * (minus_dm.ewm(alpha=alpha, adjust=False).mean() / tr_smooth)
        
        dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di).replace(0, 1))
        adx = dx.ewm(alpha=alpha, adjust=False).mean()
        
        return rsi.iloc[-1], atr.iloc[-1], adx.iloc[-1], plus_di.iloc[-1], minus_di.iloc[-1]

    @staticmethod
    def get_signal(rsi, atr, adx, plus_di, minus_di, current_price, has_position, target_tp=None, target_sl=None, trade_type="LONG"):
        # Niveles dinámicos por ATR
        # Multiplicador 2.0 para SL y 2.0 para TP (Risk/Reward 1.0)
        sl_dist = atr * ATR_MULTIPLIER
        tp_dist = atr * ATR_MULTIPLIER

        is_strong_trend = adx > ADX_THRESHOLD
        is_uptrend = plus_di > minus_di

        if not has_position:
            if rsi < RSI_OVERSOLD:
                # Evitar LONG si hay una fuerte tendencia BAJISTA
                if not (is_strong_trend and not is_uptrend):
                    tp = current_price + tp_dist
                    sl = current_price - sl_dist
                    return 'BUY', tp, sl
            if rsi > RSI_OVERBOUGHT:
                # Evitar SHORT si hay una fuerte tendencia ALCISTA
                if not (is_strong_trend and is_uptrend):
                    tp = current_price - tp_dist
                    sl = current_price + sl_dist
                    return 'SELL_SHORT', tp, sl
        else:
            if trade_type == "LONG":
                if rsi > RSI_OVERBOUGHT: return 'SELL', None, None
                if target_tp and current_price >= target_tp: return 'SELL', None, None
                if target_sl and current_price <= target_sl: return 'SELL', None, None
            
            elif trade_type == "SHORT":
                if rsi < RSI_OVERSOLD: return 'BUY_BACK', None, None
                if target_tp and current_price <= target_tp: return 'BUY_BACK', None, None
                if target_sl and current_price >= target_sl: return 'BUY_BACK', None, None
                    
        return 'HOLD', target_tp, target_sl
