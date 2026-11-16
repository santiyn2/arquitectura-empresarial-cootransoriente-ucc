"""Persistencia local del backend de Cootransoriente Tayrona.

Usa SQLite para mantener el despliegue simple (menos de 10 minutos) y conserva
la tabla ``audit_logs`` como registro inmutable mediante disparadores SQL.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_FILENAME = "cootransoriente.db"
DEFAULT_DB_PATH = Path(__file__).resolve().parent / DB_FILENAME

# Permite aislar la base de datos en pruebas o despliegues alternos.
DATABASE_PATH = Path(
    os.getenv("COOTRANSORIENTE_DB", str(DEFAULT_DB_PATH))
).expanduser()


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS tiquetes (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    pasajero_nombre       TEXT    NOT NULL,
    documento             TEXT    NOT NULL,
    es_menor              INTEGER NOT NULL DEFAULT 0
                                  CHECK (es_menor IN (0, 1)),
    ruta                  TEXT    NOT NULL,
    asiento               TEXT    NOT NULL,
    autorizacion_ley1581  INTEGER NOT NULL
                                  CHECK (autorizacion_ley1581 = 1),
    fecha_autorizacion    TEXT    NOT NULL,
    creado_por            TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    accion    TEXT NOT NULL,
    usuario   TEXT NOT NULL,
    rol       TEXT NOT NULL,
    detalle   TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp
    ON audit_logs (timestamp);

-- Los registros de auditoría son inmutables: no se pueden alterar ni borrar.
CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_update
BEFORE UPDATE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit_logs es un registro inmutable');
END;

CREATE TRIGGER IF NOT EXISTS trg_audit_logs_no_delete
BEFORE DELETE ON audit_logs
BEGIN
    SELECT RAISE(ABORT, 'audit_logs es un registro inmutable');
END;
"""


def get_connection() -> sqlite3.Connection:
    """Abre una conexión SQLite con filas accesibles por nombre."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Crea las tablas, índices y disparadores si aún no existen."""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA_SQL)
        conn.commit()
    finally:
        conn.close()
