from src.core.bot_engine import BotEngine
from src.utils.logger import setup_logger

def main():
    setup_logger()
    print("========================================")
    print("      SOLANA BOT PROFESSIONAL v2        ")
    print("========================================")
    
    bot = BotEngine()
    try:
        bot.start()
    except KeyboardInterrupt:
        print("\nSaliendo...")

if __name__ == "__main__":
    main()
