import os
from dotenv import load_dotenv

# Cargar variables de entorno desde el archivo .env
env_file = os.getenv("ENV_FILE", ".env")
load_dotenv(env_file, override=True)


# ── Modo de Operación ─────────────────────────────────────────────────────────
# CONSERVATIVE: Estrategia de bajo riesgo, menos operaciones pero más seguras.
# SCALPING: Micro-ganancias frecuentes, más operaciones, objetivos cortos.
BOT_MODE = os.getenv("BOT_MODE", "CONSERVATIVE").upper()

# ── Par y temporalidad ────────────────────────────────────────────────────────
# Par de criptomonedas a operar (ej: SOLUSDT, BTCUSDT)
SYMBOL = os.getenv("SYMBOL", "SOLUSDT")

# Cargar archivo .env específico de la moneda (p.ej. .sol.env) si existe
coin_part = SYMBOL.replace('USDT', '').replace('USD', '').lower()
coin_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../environments', f".{coin_part}.env"))
if os.path.isfile(coin_env_path):
    load_dotenv(coin_env_path, override=True)

# Timeframe de las velas. Más alto = menos ruido pero menos señales.
# Recomendado: 1h (balance entre frecuencia y calidad de señal)
TIMEFRAME = os.getenv("TIMEFRAME", "1h")

# Segundos entre cada ciclo del bot (5s es suficiente para timeframe 1h)
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL", 5))

# ── Futuros ───────────────────────────────────────────────────────────────────
LEVERAGE = int(os.getenv("LEVERAGE", 3))
MARGIN_TYPE = os.getenv("MARGIN_TYPE", "ISOLATED")

# ── RSI (Relative Strength Index) ─────────────────────────────────────────────
RSI_PERIOD    = int(os.getenv("RSI_PERIOD", 14))
RSI_OVERSOLD  = float(os.getenv("RSI_OVERSOLD", 30))
RSI_OVERBOUGHT= float(os.getenv("RSI_OVERBOUGHT", 68))

# ── ATR (Average True Range) — Volatilidad dinámica ───────────────────────────
ATR_PERIOD        = int(os.getenv("ATR_PERIOD", 14))
ATR_SL_MULTIPLIER = float(os.getenv("ATR_SL_MULTIPLIER", 1.5))
ATR_TP_MULTIPLIER = float(os.getenv("ATR_TP_MULTIPLIER", 2.5))
ATR_MULTIPLIER    = float(os.getenv("ATR_MULTIPLIER", 2.0))  # Retrocompatibilidad

# ── ADX (Average Directional Index) — Filtro de fuerza de tendencia ───────────
ADX_PERIOD    = int(os.getenv("ADX_PERIOD", 14))
ADX_THRESHOLD = float(os.getenv("ADX_THRESHOLD", 25.0))

# ── EMA (Exponential Moving Average) — Filtro de tendencia macro ──────────────
EMA_FAST_PERIOD = int(os.getenv("EMA_FAST_PERIOD", 50))
EMA_SLOW_PERIOD = int(os.getenv("EMA_SLOW_PERIOD", 200))

# ── Gestión de Riesgo Fallback ────────────────────────────────────────────────
STOP_LOSS_PCT     = float(os.getenv("STOP_LOSS_PCT", 0.03))
TAKE_PROFIT_PCT   = float(os.getenv("TAKE_PROFIT_PCT", 0.05))
TRADE_PERCENTAGE  = float(os.getenv("TRADE_PERCENTAGE", 0.10))

# ── Trailing Stop (Stop Loss dinámico) ────────────────────────────────────────
USE_TRAILING_STOP    = os.getenv("USE_TRAILING_STOP", "True").lower() == "true"
TRAILING_TRIGGER_ATR = float(os.getenv("TRAILING_TRIGGER_ATR", 1.0))

# ── DCA (Dollar Cost Averaging) ───────────────────────────────────────────────
DCA_ENABLED       = os.getenv("DCA_ENABLED", "True").lower() == "true"
MAX_DCA_ORDERS    = int(os.getenv("MAX_DCA_ORDERS", 3))
DCA_ENTRY_SIZE_PCT= float(os.getenv("DCA_ENTRY_SIZE_PCT", 0.10))
DCA_RSI_LEVEL_2   = float(os.getenv("DCA_RSI_LEVEL_2", 25))
DCA_RSI_LEVEL_3   = float(os.getenv("DCA_RSI_LEVEL_3", 20))
DCA_RSI_LEVEL_4   = float(os.getenv("DCA_RSI_LEVEL_4", 15))
DCA_MIN_DROP_PCT  = float(os.getenv("DCA_MIN_DROP_PCT", 0.02))


# ── Sobreescritura desde base de datos (tabla bot_config) ─────────────────────
# Si un parámetro está en la tabla Y tiene enabled=True, su valor de DB
# tiene prioridad sobre el .env. Esto permite cambiar parámetros desde
# el portal sin reiniciar el bot.
def _load_db_config():
    """
    Lee la tabla bot_config y sobreescribe los parámetros globales
    que tengan enabled=True. Si falla (DB no disponible, tabla vacía),
    se usan los valores del .env sin error.
    """
    try:
        import pymysql
        db_user = os.getenv("DB_USER", "root")
        db_pass = os.getenv("DB_PASS", "")
        db_host = os.getenv("DB_HOST", "localhost")
        db_port = int(os.getenv("DB_PORT", "3306"))
        db_name = os.getenv("DB_NAME", "crypto-bot")

        conn = pymysql.connect(host=db_host, port=db_port,
                               user=db_user, password=db_pass,
                               database=db_name, connect_timeout=3)
        cursor = conn.cursor()
        cursor.execute("SELECT `key`, `value`, `dtype` FROM bot_config WHERE enabled = 1")
        rows = cursor.fetchall()
        conn.close()

        overrides = {}
        for key, value, dtype in rows:
            try:
                if dtype == "int":
                    overrides[key] = int(value)
                elif dtype == "float":
                    overrides[key] = float(value)
                elif dtype == "bool":
                    overrides[key] = value.lower() in ("true", "1", "yes")
                else:
                    overrides[key] = str(value)
            except (ValueError, TypeError):
                pass  # Valor inválido → usa el del .env

        return overrides
    except Exception:
        return {}   # DB no disponible → continúa con los valores del .env


_db_cfg = _load_db_config()

def _get(key, default):
    """Devuelve el valor de DB si está habilitado, si no el default (.env)."""
    return _db_cfg.get(key, default)


# Sobreescribir con valores de DB (si existen y están habilitados)
BOT_MODE          = _get("BOT_MODE",          BOT_MODE).upper()
SYMBOL            = _get("SYMBOL",            SYMBOL)
TIMEFRAME         = _get("TIMEFRAME",         TIMEFRAME)
CHECK_INTERVAL    = _get("CHECK_INTERVAL",    CHECK_INTERVAL)
LEVERAGE          = _get("LEVERAGE",          LEVERAGE)
MARGIN_TYPE       = _get("MARGIN_TYPE",       MARGIN_TYPE)
RSI_PERIOD        = _get("RSI_PERIOD",        RSI_PERIOD)
RSI_OVERSOLD      = _get("RSI_OVERSOLD",      RSI_OVERSOLD)
RSI_OVERBOUGHT    = _get("RSI_OVERBOUGHT",    RSI_OVERBOUGHT)
ATR_PERIOD        = _get("ATR_PERIOD",        ATR_PERIOD)
ATR_SL_MULTIPLIER = _get("ATR_SL_MULTIPLIER", ATR_SL_MULTIPLIER)
ATR_TP_MULTIPLIER = _get("ATR_TP_MULTIPLIER", ATR_TP_MULTIPLIER)
ADX_PERIOD        = _get("ADX_PERIOD",        ADX_PERIOD)
ADX_THRESHOLD     = _get("ADX_THRESHOLD",     ADX_THRESHOLD)
EMA_FAST_PERIOD   = _get("EMA_FAST_PERIOD",   EMA_FAST_PERIOD)
EMA_SLOW_PERIOD   = _get("EMA_SLOW_PERIOD",   EMA_SLOW_PERIOD)
USE_TRAILING_STOP    = _get("USE_TRAILING_STOP",    USE_TRAILING_STOP)
TRAILING_TRIGGER_ATR = _get("TRAILING_TRIGGER_ATR", TRAILING_TRIGGER_ATR)
DCA_ENABLED       = _get("DCA_ENABLED",       DCA_ENABLED)
MAX_DCA_ORDERS    = _get("MAX_DCA_ORDERS",    MAX_DCA_ORDERS)
DCA_ENTRY_SIZE_PCT= _get("DCA_ENTRY_SIZE_PCT",DCA_ENTRY_SIZE_PCT)
DCA_RSI_LEVEL_2   = _get("DCA_RSI_LEVEL_2",   DCA_RSI_LEVEL_2)
DCA_RSI_LEVEL_3   = _get("DCA_RSI_LEVEL_3",   DCA_RSI_LEVEL_3)
DCA_RSI_LEVEL_4   = _get("DCA_RSI_LEVEL_4",   DCA_RSI_LEVEL_4)
DCA_MIN_DROP_PCT  = _get("DCA_MIN_DROP_PCT",  DCA_MIN_DROP_PCT)
STOP_LOSS_PCT     = _get("STOP_LOSS_PCT",     STOP_LOSS_PCT)
TAKE_PROFIT_PCT   = _get("TAKE_PROFIT_PCT",   TAKE_PROFIT_PCT)


# ── Ajustes Dinámicos por Modo (BOT_MODE) ─────────────────────────────────────
if BOT_MODE == "SCALPING":
    RSI_OVERSOLD     = _get("RSI_OVERSOLD",      35.0)
    ATR_TP_MULTIPLIER= _get("ATR_TP_MULTIPLIER", 1.0)
    ATR_SL_MULTIPLIER= _get("ATR_SL_MULTIPLIER", 1.2)
    DCA_MIN_DROP_PCT = _get("DCA_MIN_DROP_PCT",  0.01)
    DCA_RSI_LEVEL_2  = _get("DCA_RSI_LEVEL_2",   30.0)
    DCA_RSI_LEVEL_3  = _get("DCA_RSI_LEVEL_3",   25.0)
    DCA_RSI_LEVEL_4  = _get("DCA_RSI_LEVEL_4",   20.0)
    print(f"MODO DE OPERACION: SCALPING (Micro-ganancias) activado.")
elif BOT_MODE == "AGGRESSIVE":
    DCA_RSI_LEVEL_2  = RSI_OVERSOLD - 4.0
    DCA_RSI_LEVEL_3  = RSI_OVERSOLD - 8.0
    DCA_RSI_LEVEL_4  = RSI_OVERSOLD - 12.0
    print(f"MODO DE OPERACION: AGGRESSIVE (Grid activo, altos niveles) activado.")
elif BOT_MODE == "AGRESIVE_MEDIUM":
    RSI_OVERSOLD     = _get("RSI_OVERSOLD",      32.5)
    ATR_TP_MULTIPLIER= _get("ATR_TP_MULTIPLIER", 1.8)
    ATR_SL_MULTIPLIER= _get("ATR_SL_MULTIPLIER", 1.35)
    DCA_MIN_DROP_PCT = _get("DCA_MIN_DROP_PCT",  0.015)
    DCA_RSI_LEVEL_2  = _get("DCA_RSI_LEVEL_2",   27.5)
    DCA_RSI_LEVEL_3  = _get("DCA_RSI_LEVEL_3",   22.5)
    DCA_RSI_LEVEL_4  = _get("DCA_RSI_LEVEL_4",   17.5)
    print(f"MODO DE OPERACION: AGRESIVE_MEDIUM activado.")
else:
    print(f"MODO DE OPERACION: CONSERVATIVE activado.")
