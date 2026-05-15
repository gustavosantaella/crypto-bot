import time
import logging
import sys
import os
from dotenv import load_dotenv

# Directorio de environments (siempre relativo a este script)
ENVS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../environments'))

# 1. Cargar siempre el .env principal (API keys, Telegram, DB, etc.)
base_env = os.path.join(ENVS_DIR, '.env')
load_dotenv(base_env, override=True)

# 2. Si se pasa --env=sol, cargar también el .env de la moneda encima
coin_env = None
for arg in sys.argv:
    if arg.startswith("--env="):
        coin = arg.split("=")[1]
        coin_env = os.path.join(ENVS_DIR, f".{coin}.env")
        if os.path.exists(coin_env):
            load_dotenv(coin_env, override=True)
        else:
            print(f"[WARN] Archivo de entorno no encontrado: {coin_env}")
        break

# Mantener ENV_FILE apuntando al archivo de moneda (o al base si no hay moneda)
os.environ["ENV_FILE"] = coin_env if coin_env and os.path.exists(coin_env) else base_env

from src.core.bot_engine import BotEngine
from src.utils.logger import setup_logger

def main():
    setup_logger()
    print("========================================")
    print("      SOLANA BOT PROFESSIONAL v2        ")
    print("========================================")
    
    while True:
        try:
            bot = BotEngine()
            bot.start()
        except KeyboardInterrupt:
            print("\nDeteniendo bot por el usuario...")
            break
        except Exception as e:
            logging.error(f"Falla crítica en el motor: {e}")
            print(f"\n[!] ERROR DE CONEXIÓN O CRÍTICO: {e}")
            print("Reintentando conexión en 20 segundos...")
            time.sleep(20)
            print("Reiniciando ejecución...\n")

if __name__ == "__main__":
    main()
