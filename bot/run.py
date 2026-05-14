import time
import logging
import sys
import os

env_file = ".env" # Default
for arg in sys.argv:
    if arg.startswith("--env="):
        env = arg.split("=")[1]
        env_file = f"environments/.{env}.env"
        break
os.environ["ENV_FILE"] = env_file

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
