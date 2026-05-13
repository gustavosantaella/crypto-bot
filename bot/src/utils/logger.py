import os
import sys
import logging

def setup_logger(log_dir="logs"):
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    fmt = '%(asctime)s [%(levelname)s] %(message)s'

    # Handler para archivo — siempre UTF-8 sin problemas
    file_handler = logging.FileHandler(
        os.path.join(log_dir, "trading_bot.log"),
        encoding="utf-8"
    )
    file_handler.setFormatter(logging.Formatter(fmt))

    # Handler para consola — forzar UTF-8 en Windows (evita UnicodeEncodeError con emojis)
    # reconfigure() está disponible desde Python 3.7+
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(logging.Formatter(fmt))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler]
    )

    return logging.getLogger("CryptoBot")
