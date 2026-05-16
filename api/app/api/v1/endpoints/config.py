"""
config.py  — Endpoint CRUD para la tabla bot_config.
GET  /config/          → lista todos los parámetros
PUT  /config/{key}     → actualiza value y/o enabled
POST /config/reset     → restaura todos al env_default
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.db.session import SessionLocal
from app.models.bot_config_model import BotConfig

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────
class ConfigUpdate(BaseModel):
    value:   Optional[str]  = None
    enabled: Optional[bool] = None


class ConfigOut(BaseModel):
    id:          int
    key:         str
    value:       str
    env_default: Optional[str]
    enabled:     bool
    category:    Optional[str]
    label:       Optional[str]
    description: Optional[str]
    dtype:       str

    class Config:
        from_attributes = True


# ── DB Dependency ──────────────────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── Seed data (todos los parámetros del .env) ──────────────────────────────────
SEED_CONFIG = [
    # ── Modo ───────────────────────────────────────────────────────────────────
    dict(key="BOT_MODE",          value="SCALPING",   env_default="SCALPING",
         category="General",      label="Modo del Bot",
         description="CONSERVATIVE / SCALPING / AGGRESSIVE / AGRESIVE_MEDIUM",
         dtype="str"),
    dict(key="SYMBOL",            value="SOLUSDT",    env_default="SOLUSDT",
         category="General",      label="Par",
         description="Par de criptomonedas a operar (ej: SOLUSDT, BTCUSDT)",
         dtype="str"),
    dict(key="TIMEFRAME",         value="1h",         env_default="1h",
         category="General",      label="Temporalidad",
         description="Timeframe de las velas: 1m, 5m, 15m, 1h, 4h",
         dtype="str"),
    dict(key="CHECK_INTERVAL",    value="2",          env_default="2",
         category="General",      label="Intervalo de ciclo (seg)",
         description="Segundos entre cada evaluación del bot",
         dtype="int"),

    # ── Futuros ────────────────────────────────────────────────────────────────
    dict(key="LEVERAGE",          value="5",          env_default="5",
         category="Futuros",      label="Apalancamiento (x)",
         description="Multiplicador de posición. Con DCA usar máx. 5-10x",
         dtype="int"),
    dict(key="MARGIN_TYPE",       value="ISOLATED",   env_default="ISOLATED",
         category="Futuros",      label="Tipo de Margen",
         description="ISOLATED = pérdida máxima acotada | CROSSED = comparte margen",
         dtype="str"),

    # ── RSI ────────────────────────────────────────────────────────────────────
    dict(key="RSI_PERIOD",        value="14",         env_default="14",
         category="RSI",          label="Período RSI",
         description="Número de velas para calcular el RSI",
         dtype="int"),
    dict(key="RSI_OVERSOLD",      value="35",         env_default="35",
         category="RSI",          label="RSI Sobrevendido (Long)",
         description="Entrada LONG cuando RSI < este valor",
         dtype="float"),
    dict(key="RSI_OVERBOUGHT",    value="70",         env_default="70",
         category="RSI",          label="RSI Sobrecomprado (Short)",
         description="Señal SHORT / cierre LONG cuando RSI > este valor",
         dtype="float"),

    # ── ATR ────────────────────────────────────────────────────────────────────
    dict(key="ATR_PERIOD",        value="14",         env_default="14",
         category="ATR",          label="Período ATR",
         description="Número de velas para calcular el ATR (volatilidad)",
         dtype="int"),
    dict(key="ATR_SL_MULTIPLIER", value="1.1",        env_default="1.1",
         category="ATR",          label="Multiplicador SL (ATR)",
         description="SL = avg_price - (ATR × este valor)",
         dtype="float"),
    dict(key="ATR_TP_MULTIPLIER", value="1.2",        env_default="1.2",
         category="ATR",          label="Multiplicador TP (ATR)",
         description="TP = avg_price + (ATR × este valor). Debe ser > SL_MULT para R/R positivo",
         dtype="float"),

    # ── ADX ────────────────────────────────────────────────────────────────────
    dict(key="ADX_PERIOD",        value="14",         env_default="14",
         category="ADX",          label="Período ADX",
         description="Número de velas para calcular el ADX",
         dtype="int"),
    dict(key="ADX_THRESHOLD",     value="25.0",       env_default="25.0",
         category="ADX",          label="Umbral ADX (tendencia fuerte)",
         description="Si ADX > este valor se considera tendencia fuerte",
         dtype="float"),

    # ── EMA ────────────────────────────────────────────────────────────────────
    dict(key="EMA_FAST_PERIOD",   value="50",         env_default="50",
         category="EMA",          label="EMA Rápida (períodos)",
         description="EMA50: filtro de micro-tendencia activo para LONG",
         dtype="int"),
    dict(key="EMA_SLOW_PERIOD",   value="100",        env_default="100",
         category="EMA",          label="EMA Lenta (períodos)",
         description="EMA lenta: referencia de tendencia macro",
         dtype="int"),

    # ── Trailing Stop ──────────────────────────────────────────────────────────
    dict(key="USE_TRAILING_STOP",    value="True",    env_default="True",
         category="Trailing Stop",   label="Activar Trailing Stop",
         description="Mueve el SL al breakeven una vez que el precio sube N ATR",
         dtype="bool"),
    dict(key="TRAILING_TRIGGER_ATR", value="1.5",     env_default="1.5",
         category="Trailing Stop",   label="Trigger Trailing (ATR)",
         description="ATR de ganancia necesario para activar el breakeven",
         dtype="float"),

    # ── DCA ────────────────────────────────────────────────────────────────────
    dict(key="DCA_ENABLED",       value="True",       env_default="True",
         category="DCA",          label="DCA Activado",
         description="Permite abrir entradas escalonadas si el precio sigue cayendo",
         dtype="bool"),
    dict(key="MAX_DCA_ORDERS",    value="3",          env_default="3",
         category="DCA",          label="Máx. Entradas DCA",
         description="Número máximo de entradas DCA (incluye la primera)",
         dtype="int"),
    dict(key="DCA_ENTRY_SIZE_PCT",value="0.07",       env_default="0.07",
         category="DCA",          label="Tamaño por Entrada (%)",
         description="Porcentaje del balance usado en cada entrada individual",
         dtype="float"),
    dict(key="DCA_RSI_LEVEL_2",   value="25",         env_default="25",
         category="DCA",          label="RSI DCA #2",
         description="RSI mínimo para activar la 2ª entrada DCA",
         dtype="float"),
    dict(key="DCA_RSI_LEVEL_3",   value="20",         env_default="20",
         category="DCA",          label="RSI DCA #3",
         description="RSI mínimo para activar la 3ª entrada DCA",
         dtype="float"),
    dict(key="DCA_RSI_LEVEL_4",   value="15",         env_default="15",
         category="DCA",          label="RSI DCA #4",
         description="RSI mínimo para activar la 4ª entrada DCA (si MAX=4)",
         dtype="float"),
    dict(key="DCA_MIN_DROP_PCT",  value="0.025",      env_default="0.025",
         category="DCA",          label="Caída mínima DCA (%)",
         description="El precio debe haber caído este % desde la última DCA",
         dtype="float"),

    # ── Riesgo Fallback ────────────────────────────────────────────────────────
    dict(key="STOP_LOSS_PCT",     value="0.12",       env_default="0.12",
         category="Riesgo",       label="SL Fallback (%)",
         description="SL fijo máximo si el ATR calcula un valor mayor",
         dtype="float"),
    dict(key="TAKE_PROFIT_PCT",   value="0.02",       env_default="0.02",
         category="Riesgo",       label="TP Fallback (%)",
         description="TP fijo de respaldo",
         dtype="float"),
]


def seed_config(db: Session):
    """Inserta los parámetros por defecto si la tabla está vacía."""
    if db.query(BotConfig).count() == 0:
        for item in SEED_CONFIG:
            db.add(BotConfig(**item))
        db.commit()


# ── Endpoints ──────────────────────────────────────────────────────────────────
@router.get("/", response_model=list[ConfigOut])
def get_all_config(db: Session = Depends(get_db)):
    """Devuelve todos los parámetros de configuración."""
    seed_config(db)
    return db.query(BotConfig).order_by(BotConfig.category, BotConfig.id).all()


@router.put("/{key}", response_model=ConfigOut)
def update_config(key: str, body: ConfigUpdate, db: Session = Depends(get_db)):
    """Actualiza el valor y/o el switch enabled de un parámetro."""
    cfg = db.query(BotConfig).filter(BotConfig.key == key).first()
    if not cfg:
        raise HTTPException(status_code=404, detail=f"Config key '{key}' not found")
    if body.value is not None:
        cfg.value = body.value
    if body.enabled is not None:
        cfg.enabled = body.enabled
    import datetime
    cfg.updated_at = datetime.datetime.utcnow()
    db.commit()
    db.refresh(cfg)
    return cfg


@router.post("/reset", response_model=list[ConfigOut])
def reset_config(db: Session = Depends(get_db)):
    """Restaura todos los valores al env_default."""
    items = db.query(BotConfig).all()
    for item in items:
        if item.env_default is not None:
            item.value = item.env_default
        item.enabled = True
    import datetime
    for item in items:
        item.updated_at = datetime.datetime.utcnow()
    db.commit()
    return db.query(BotConfig).order_by(BotConfig.category, BotConfig.id).all()
