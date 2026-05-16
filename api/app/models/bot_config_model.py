from sqlalchemy import Column, Integer, String, Boolean, Text, DateTime
from app.db.session import Base
import datetime


class BotConfig(Base):
    """
    Tabla de configuración dinámica del bot.
    Cada fila representa un parámetro del .env con su valor actual,
    si está habilitado (enabled=True → el bot lo usa; False → usa el .env).
    """
    __tablename__ = "bot_config"

    id          = Column(Integer, primary_key=True, index=True)
    key         = Column(String(80), unique=True, nullable=False, index=True)
    value       = Column(String(200), nullable=False)          # Valor actual (string)
    env_default = Column(String(200), nullable=True)           # Valor original del .env
    enabled     = Column(Boolean, default=True)                # Switch ON/OFF
    category    = Column(String(50), nullable=True)            # Grupo visual en UI
    label       = Column(String(120), nullable=True)           # Nombre legible
    description = Column(Text, nullable=True)                  # Explicación
    dtype       = Column(String(20), default="float")          # int | float | str | bool
    updated_at  = Column(DateTime, default=datetime.datetime.utcnow,
                         onupdate=datetime.datetime.utcnow)
