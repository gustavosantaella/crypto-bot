"""Conexión a MySQL (SQLAlchemy + PyMySQL)."""
from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import settings


class Base(DeclarativeBase):
    pass


def _build_url(db_name: str | None = None) -> str:
    return (
        f"mysql+pymysql://{settings.db_user}:{settings.db_pass}"
        f"@{settings.db_host}:{settings.db_port}/{db_name or settings.db_name}?charset=utf8mb4"
    )


def ensure_database() -> None:
    """Crea la base de datos si no existe (se conecta sin seleccionar BD)."""
    import pymysql

    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        charset="utf8mb4",
    )
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{settings.db_name}` "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()


engine = create_engine(
    _build_url(),
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db():
    """Dependencia de FastAPI que inyecta una sesión de base de datos."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
