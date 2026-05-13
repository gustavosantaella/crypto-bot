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

    # Handler para consola — forzar UTF-8 en Windows
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    # Formateador con colores para la consola
    class ColoredFormatter(logging.Formatter):
        COLORS = {
            'INFO': '\033[92m',     # Verde
            'WARNING': '\033[93m',  # Amarillo
            'ERROR': '\033[91m',    # Rojo
            'CRITICAL': '\033[95m'  # Magenta
        }
        RESET = '\033[0m'

        def format(self, record):
            orig_levelname = record.levelname
            color = self.COLORS.get(orig_levelname, '')
            reset = self.RESET if color else ''
            
            # Mutar temporalmente el levelname para el log de consola
            record.levelname = f"{color}{orig_levelname}{reset}"
            formatted = super().format(record)
            # Restaurar para que no afecte a otros handlers (como el archivo)
            record.levelname = orig_levelname
            return formatted

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.setFormatter(ColoredFormatter(fmt))

    logging.basicConfig(
        level=logging.INFO,
        handlers=[file_handler, stream_handler]
    )

    return logging.getLogger("CryptoBot")
