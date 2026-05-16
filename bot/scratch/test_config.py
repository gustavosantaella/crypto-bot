import sys
import os

# Añadir el directorio raíz al path para poder importar src
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.config import trading_params

print("--- Verificación de Configuración ---")
print(f"SYMBOL: {trading_params.SYMBOL}")
print(f"BOT_MODE: {trading_params.BOT_MODE}")
print(f"RSI_OVERSOLD: {trading_params.RSI_OVERSOLD}")
print(f"EMA_FAST_PERIOD: {trading_params.EMA_FAST_PERIOD}")
print(f"DCA_ENABLED: {trading_params.DCA_ENABLED}")
print("-------------------------------------")

# Intentar conectarse a la DB directamente para ver qué hay
try:
    import pymysql
    from dotenv import load_dotenv
    load_dotenv()
    
    db_user = os.getenv("DB_USER", "root")
    db_pass = os.getenv("DB_PASS", "")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = int(os.getenv("DB_PORT", "3306"))
    db_name = os.getenv("DB_NAME", "crypto-bot")

    conn = pymysql.connect(host=db_host, port=db_port,
                           user=db_user, password=db_pass,
                           database=db_name)
    cursor = conn.cursor()
    cursor.execute("SELECT `key`, `value`, `enabled` FROM bot_config")
    rows = cursor.fetchall()
    print("\nContenido de la tabla bot_config:")
    for row in rows:
        print(f"Key: {row[0]}, Value: {row[1]}, Enabled: {row[2]}")
    conn.close()
except Exception as e:
    print(f"\nError al consultar la DB: {e}")
