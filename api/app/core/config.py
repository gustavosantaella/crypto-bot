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

env_file = os.getenv("ENV_FILE", ".env")
load_dotenv(env_file)

# Load coin‑specific .env (e.g. .sol.env) if it exists.
# The symbol is read from the base .env (SYMBOL=SOLUSDT, BTCUSDT, …)
coin_symbol = os.getenv("SYMBOL", "")
coin_part = coin_symbol.replace('USDT', '').replace('USD', '').lower()
coin_env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../environments', f".{coin_part}.env"))
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
