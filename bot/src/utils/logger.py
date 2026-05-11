import os
import logging

def setup_logger(log_dir="logs"):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
        
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(log_dir, "trading_bot.log")),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger("CryptoBot")
