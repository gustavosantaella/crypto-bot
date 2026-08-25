"""Migraciones ligeras para tablas existentes.

SQLAlchemy ``create_all`` NO altera tablas ya creadas. Para que una base de
datos existente (con filas de spot) acepte los nuevos campos de futuros sin
romperse, se ejecutan ``ALTER TABLE ... ADD COLUMN`` únicamente para las
columnas que falten (consultando ``information_schema``).

Todos los campos nuevos son nullable o con DEFAULT, por lo que las filas
antiguas de spot siguen siendo válidas (market_type='SPOT', leverage=1...).
"""
from __future__ import annotations

import logging

import pymysql

from .config import settings

_logger = logging.getLogger("crypto_api.migrations")

# tablas -> [(columna, definición SQL, índice opcional)]
_MIGRATIONS = {
    "transactions": [
        ("market_type", "VARCHAR(10) NOT NULL DEFAULT 'SPOT'", "idx_transactions_market_type"),
        ("side", "VARCHAR(10) NOT NULL DEFAULT 'LONG'", None),
        ("leverage", "INT NOT NULL DEFAULT 1", None),
        ("notional", "DECIMAL(30,10) NULL", None),
        ("margin", "DECIMAL(30,10) NULL", None),
        ("liquidation_price", "DECIMAL(30,10) NULL", None),
        ("take_profit_price", "DECIMAL(30,10) NULL", None),
        ("stop_loss_price", "DECIMAL(30,10) NULL", None),
    ],
    "orders": [
        ("market_type", "VARCHAR(10) NOT NULL DEFAULT 'SPOT'", "idx_orders_market_type"),
        ("position_side", "VARCHAR(10) NULL", None),
        ("leverage", "INT NOT NULL DEFAULT 1", None),
    ],
}


def _existing_columns(conn: pymysql.Connection, table: str) -> set[str]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT COLUMN_NAME FROM information_schema.COLUMNS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (settings.db_name, table),
        )
        return {row[0] for row in cursor.fetchall()}


def _existing_indexes(conn: pymysql.Connection, table: str) -> set[str]:
    with conn.cursor() as cursor:
        cursor.execute(
            "SELECT INDEX_NAME FROM information_schema.STATISTICS "
            "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
            (settings.db_name, table),
        )
        return {row[0] for row in cursor.fetchall()}


def run_migrations() -> None:
    """Aplica las columnas que falten en las tablas del proyecto."""
    conn = pymysql.connect(
        host=settings.db_host,
        port=settings.db_port,
        user=settings.db_user,
        password=settings.db_pass,
        database=settings.db_name,
        charset="utf8mb4",
    )
    try:
        for table, columns in _MIGRATIONS.items():
            existing = _existing_columns(conn, table)
            indexes = _existing_indexes(conn, table)
            for column, definition, index_name in columns:
                if column not in existing:
                    sql = f"ALTER TABLE `{table}` ADD COLUMN `{column}` {definition}"
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(sql)
                        conn.commit()
                        _logger.info("Migración: %s añadida a %s", column, table)
                    except pymysql.MySQLError as exc:
                        conn.rollback()
                        _logger.error("No se pudo añadir %s a %s: %s", column, table, exc)
                if index_name and index_name not in indexes:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(f"ALTER TABLE `{table}` ADD INDEX `{index_name}` (`{column}`)")
                        conn.commit()
                        _logger.info("Migración: índice %s creado en %s", index_name, table)
                    except pymysql.MySQLError as exc:
                        conn.rollback()
                        _logger.error("No se pudo crear el índice %s: %s", index_name, exc)
    finally:
        conn.close()
