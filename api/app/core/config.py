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

load_dotenv()

class Settings(BaseSettings):
    PROJECT_NAME: str = "Crypto Bot API"
    API_V1_STR: str = "/api/v1"
    
    BINANCE_API_KEY: str = os.getenv("BINANCE_API_KEY", "")
    BINANCE_SECRET_KEY: str = os.getenv("BINANCE_SECRET_KEY", "")
    IS_TESTNET: bool = os.getenv("IS_TESTNET", "True") == "True"
    
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
