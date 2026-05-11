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
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", 35))
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", 65))

# Gestión de Riesgo (Risk Management)
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.03))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.05))

# Intervalo de revisión del bot en segundos
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 5))
