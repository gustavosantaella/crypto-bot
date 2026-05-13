import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
load_dotenv()

# ── Modo de Operación ─────────────────────────────────────────────────────────
# CONSERVATIVE: Estrategia de bajo riesgo, menos operaciones pero más seguras.
# SCALPING: Micro-ganancias frecuentes, más operaciones, objetivos cortos.
BOT_MODE = os.getenv("BOT_MODE", "CONSERVATIVE").upper()

# ── Par y temporalidad ────────────────────────────────────────────────────────
# Par de criptomonedas a operar (ej: SOLUSDT, BTCUSDT)
SYMBOL = os.getenv("SYMBOL", "SOLUSDT")

# Timeframe de las velas. Más alto = menos ruido pero menos señales.
# Recomendado: 1h (balance entre frecuencia y calidad de señal)
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

# Segundos entre cada ciclo del bot (5s es suficiente para timeframe 1h)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 5))

# ── Futuros ───────────────────────────────────────────────────────────────────
# IMPORTANTE: Con DCA conservador, usar apalancamiento BAJO.
# Leverage 3x: si el precio cae 33% te liquidan. Con DCA de 4 entradas,
# el precio puede caer bastante antes del rebote. No subir de 3x.
LEVERAGE = int(os.getenv("LEVERAGE", 3))

# ISOLATED = el margen de cada posición está separado (pérdida máxima = margen de esa posición)
# CROSSED  = comparte margen entre posiciones (más riesgo)
MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED")

# ── RSI (Relative Strength Index) ─────────────────────────────────────────────
# Mide momentum. Rango 0-100.
RSI_PERIOD = int(os.getenv("RSI_PERIOD", 14))

# Señal de compra cuando RSI < RSI_OVERSOLD (mercado sobrevendido)
# 30 es el nivel clásico. Bajar a 28 reduce señales falsas pero da menos entradas.
RSI_OVERSOLD = float(os.getenv("RSI_OVERSOLD", 30))

# Señal de cierre cuando RSI > RSI_OVERBOUGHT (mercado sobrecomprado)
RSI_OVERBOUGHT = float(os.getenv("RSI_OVERBOUGHT", 68))

# ── ATR (Average True Range) — Volatilidad dinámica ───────────────────────────
ATR_PERIOD = int(os.getenv("ATR_PERIOD", 14))

# SL = precio_promedio - (ATR * ATR_SL_MULTIPLIER)
# Valor bajo = SL más ajustado = menos pérdida pero más salidas prematuras
ATR_SL_MULTIPLIER = float(os.getenv("ATR_SL_MULTIPLIER", 1.5))

# TP = precio_promedio + (ATR * ATR_TP_MULTIPLIER)
# DEBE ser mayor que ATR_SL_MULTIPLIER para tener R/R positivo.
# Con SL=1.5 y TP=2.5 → R/R = 1.67 → solo necesitas ganar 38% de los trades.
ATR_TP_MULTIPLIER = float(os.getenv("ATR_TP_MULTIPLIER", 2.5))

# Retrocompatibilidad (no se usa activamente si los multipliers están definidos)
ATR_MULTIPLIER = float(os.getenv("ATR_MULTIPLIER", 2.0))

# ── ADX (Average Directional Index) — Filtro de fuerza de tendencia ───────────
ADX_PERIOD = int(os.getenv("ADX_PERIOD", 14))

# Si ADX > ADX_THRESHOLD, hay una tendencia fuerte (evita entrar contra ella)
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD", 25.0))

# ── EMA (Exponential Moving Average) — Filtro de tendencia macro ──────────────
# Solo se compra (LONG) si el precio está POR ENCIMA de la EMA lenta.
# Esto evita comprar en pleno mercado bajista.
# EMA rápida: para detectar micro-tendencia reciente
EMA_FAST_PERIOD = int(os.getenv("EMA_FAST_PERIOD", 50))

# EMA lenta: para confirmar que estamos en contexto de mercado alcista
# Si el precio está por debajo de la EMA200, no se abren nuevos LONG
EMA_SLOW_PERIOD = int(os.getenv("EMA_SLOW_PERIOD", 200))

# ── Gestión de Riesgo Fallback ────────────────────────────────────────────────
STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", 0.03))
TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", 0.05))
TRADE_PERCENTAGE = float(os.getenv("TRADE_PERCENTAGE", 0.10))

# ── Trailing Stop (Stop Loss dinámico) ────────────────────────────────────────
# Una vez que el precio sube 1 ATR desde la entrada, el SL se mueve al
# precio de entrada (breakeven). Esto garantiza que nunca pierdes en un trade
# que llegó a estar en verde.
USE_TRAILING_STOP = os.getenv("USE_TRAILING_STOP", "True").lower() == "true"

# ATR que debe superar el precio (en ganancia) para activar el trailing
# Ej: 1.0 = cuando el precio suba 1 ATR desde el avg, activa el breakeven
TRAILING_TRIGGER_ATR = float(os.getenv("TRAILING_TRIGGER_ATR", 1.0))

# ── DCA (Dollar Cost Averaging) ───────────────────────────────────────────────
# Permite abrir entradas escalonadas si el precio sigue cayendo.
# CONSERVADOR: máximo 3 entradas al 10% cada una = 30% del capital en riesgo total.
DCA_ENABLED = os.getenv("DCA_ENABLED", "True").lower() == "true"

# Máximo de entradas DCA (incluye la primera entrada)
# Con 3 entradas al 10%, máximo 30% del capital está en uso. El 70% queda como colchón.
MAX_DCA_ORDERS = int(os.getenv("MAX_DCA_ORDERS", 3))

# Porcentaje del balance a usar en CADA entrada individual
# 10% por entrada × 3 entradas = 30% máximo del capital
DCA_ENTRY_SIZE_PCT = float(os.getenv("DCA_ENTRY_SIZE_PCT", 0.10))

# Niveles RSI para activar entradas DCA adicionales.
# Cada entrada requiere que el RSI esté en un nivel MÁS bajo que el anterior,
# garantizando que solo promedias cuando el mercado está más sobrevendido.
DCA_RSI_LEVEL_2 = float(os.getenv("DCA_RSI_LEVEL_2", 25))  # 2da entrada: RSI < 25
DCA_RSI_LEVEL_3 = float(os.getenv("DCA_RSI_LEVEL_3", 20))  # 3ra entrada: RSI < 20 (extremo)
DCA_RSI_LEVEL_4 = float(os.getenv("DCA_RSI_LEVEL_4", 15))  # 4ta (solo si MAX_DCA_ORDERS=4)

# Caída mínima de precio (%) desde la última entrada para permitir una nueva DCA.
# Evita que el bot haga compras múltiples cuando el RSI oscila sin que el precio baje.
# Ej: 0.02 = el precio debe haber caído al menos 2% desde la última compra DCA
DCA_MIN_DROP_PCT = float(os.getenv("DCA_MIN_DROP_PCT", 0.02))

# ── Ajustes Dinámicos por Modo (BOT_MODE) ─────────────────────────────────────
if BOT_MODE == "SCALPING":
    # Sobrescribir parámetros para modo Scalping (Micro-ganancias)
    # Estos valores aseguran salidas rápidas y entradas más frecuentes.
    RSI_OVERSOLD = 35.0          # Entra antes en sobreventa
    ATR_TP_MULTIPLIER = 1.0      # Objetivo de ganancia corto (Micro-ganancia)
    ATR_SL_MULTIPLIER = 1.2      # Stop Loss ajustado para proteger
    DCA_MIN_DROP_PCT = 0.01      # DCA más cercano (1%)
    DCA_RSI_LEVEL_2 = 30.0       # Niveles DCA más accesibles
    DCA_RSI_LEVEL_3 = 25.0
    DCA_RSI_LEVEL_4 = 20.0
    
    print(f"🚀 MODO DE OPERACIÓN: SCALPING (Micro-ganancias) activado.")
else:
    print(f"🛡️ MODO DE OPERACIÓN: CONSERVATIVE activado.")
