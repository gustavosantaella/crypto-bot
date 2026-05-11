import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Símbolo de trading (Par de criptomonedas a operar)
SYMBOL = os.getenv("SYMBOL", "SOLUSDT")

# Porcentaje del balance disponible (USDT) a usar por operación (0.0 a 1.0)
TRADE_PERCENTAGE = float(os.getenv("TRADE_PERCENTAGE", 0.5))

# Configuración del Indicador RSI
RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", 30))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", 70))

# Configuración ATR (Volatilidad Dinámica)
ATR_PERIOD = int(os.getenv("ATR_PERIOD", 14))
ATR_MULTIPLIER = float(os.getenv("ATR_MULTIPLIER", 2.0))  # SL = Price +/- (ATR * 2)
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

# Gestión de Riesgo (Risk Management)
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.03)) # Fallback
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.05)) # Fallback

# Intervalo de revisión del bot en segundos
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 5))

# Configuración de Futuros
LEVERAGE = int(os.getenv("LEVERAGE", 5))
MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED") # ISOLATED o CROSSED
