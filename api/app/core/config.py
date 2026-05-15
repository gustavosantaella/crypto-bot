import os
from dotenv import load_dotenv

# En Pydantic v2, BaseSettings se movió a pydantic-settings
# Intentamos importarlo de las distintas ubicaciones posibles para compatibilidad
try:
    from pydantic_settings import BaseSettings
except ImportError:
    try:
        from pydantic import BaseSettings
    except (ImportError, AttributeError):
        try:
            from pydantic.v1 import BaseSettings
        except ImportError:
            # Fallback final si todo falla (poco probable)
            from pydantic import BaseModel as BaseSettings

# Ruta absoluta al directorio environments/ (dos niveles arriba de este archivo)
_HERE = os.path.dirname(os.path.abspath(__file__))
_ENVIRONMENTS_DIR = os.path.abspath(os.path.join(_HERE, '../../environments'))

# 1. Cargar SIEMPRE el .env principal (contiene BINANCE_API_KEY, BINANCE_SECRET_KEY, TELEGRAM, etc.)
_main_env = os.path.join(_ENVIRONMENTS_DIR, '.env')
if os.path.isfile(_main_env):
    load_dotenv(_main_env, override=False)

# 2. Superponer el .env de moneda si se especificó via ENV_FILE o SYMBOL
_env_file_arg = os.getenv("ENV_FILE", "")
if _env_file_arg and os.path.isfile(_env_file_arg):
    load_dotenv(_env_file_arg, override=True)
else:
    # Detectar por SYMBOL (ya cargado del .env principal)
    coin_symbol = os.getenv("SYMBOL", "")
    coin_part = coin_symbol.replace('USDT', '').replace('USD', '').lower()
    if coin_part:
        coin_env_path = os.path.join(_ENVIRONMENTS_DIR, f'.{coin_part}.env')
        if os.path.isfile(coin_env_path):
            load_dotenv(coin_env_path, override=True)

class Settings(BaseSettings):
    PROJECT_NAME: str = "Crypto Bot API"
    API_V1_STR: str = "/api/v1"
    
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")
    IS_TESTNET: bool = str(os.getenv("IS_TESTNET", "True")).lower() == "true"
    
    TELEGRAM_TOKEN: str = os.getenv("TELEGRAM_TOKEN", "")
    TELEGRAM_ID: int = int(os.getenv("TELEGRAM_ID", "0"))
    
    # Database config
    DB_USER: str = os.getenv("DB_USER", "root")
    DB_PASS: str = os.getenv("DB_PASS", "")
    DB_HOST: str = os.getenv("DB_HOST", "localhost")
    DB_PORT: str = os.getenv("DB_PORT", "3306")
    DB_NAME: str = os.getenv("DB_NAME", "crypto-bot")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASS}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        case_sensitive = True

settings = Settings()
