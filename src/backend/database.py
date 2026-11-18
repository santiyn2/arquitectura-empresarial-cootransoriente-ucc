"""Persistencia local del backend de Cootransoriente Tayrona.

Usa SQLite para mantener el despliegue simple (menos de 10 minutos) y conserva
la tabla ``audit_logs`` como registro inmutable mediante disparadores SQL.

El esquema se crea en cuatro fases estrictas: tablas -> migración de
``tiquetes`` -> índices -> semilla demo.
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


# ---------------------------------------------------------------------------
# 1) Tablas y disparadores de inmutabilidad
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS usuarios (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    usuario           TEXT    NOT NULL UNIQUE,
    nombre            TEXT    NOT NULL,
    rol               TEXT    NOT NULL
                              CHECK (rol IN ('ADMIN_DESPACHO', 'TAQUILLERO', 'CONDUCTOR')),
    password_hash     TEXT    NOT NULL,
    activo            INTEGER NOT NULL DEFAULT 1
                              CHECK (activo IN (0, 1)),
    intentos_fallidos INTEGER NOT NULL DEFAULT 0
                              CHECK (intentos_fallidos >= 0),
    bloqueado_hasta   TEXT
);

CREATE TABLE IF NOT EXISTS vehiculos (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    placa     TEXT    NOT NULL UNIQUE,
    capacidad INTEGER NOT NULL CHECK (capacidad > 0),
    activo    INTEGER NOT NULL DEFAULT 1 CHECK (activo IN (0, 1))
);

CREATE TABLE IF NOT EXISTS viajes (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ruta              TEXT    NOT NULL,
    vehiculo_id       INTEGER NOT NULL REFERENCES vehiculos (id),
    conductor_usuario TEXT    NOT NULL REFERENCES usuarios (usuario),
    salida_programada TEXT    NOT NULL,
    tarifa            REAL    NOT NULL CHECK (tarifa >= 0),
    estado            TEXT    NOT NULL DEFAULT 'programado'
                              CHECK (estado IN ('programado', 'despachado', 'cerrado')),
    creado_por        TEXT    NOT NULL,
    despachado_por    TEXT,
    fecha_despacho    TEXT
);

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
    creado_por            TEXT    NOT NULL,
    viaje_id              INTEGER REFERENCES viajes (id),
    codigo_qr             TEXT,
    valor                 REAL    CHECK (valor IS NULL OR valor >= 0),
    representante_documento TEXT
);

CREATE TABLE IF NOT EXISTS abordajes (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    tiquete_id     INTEGER NOT NULL UNIQUE REFERENCES tiquetes (id),
    viaje_id       INTEGER NOT NULL REFERENCES viajes (id),
    validado_por   TEXT    NOT NULL,
    fecha_escaneo  TEXT    NOT NULL,
    fecha_registro TEXT    NOT NULL,
    id_cliente     TEXT    NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS pagos (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    viaje_id       INTEGER NOT NULL REFERENCES viajes (id),
    tiquete_id     INTEGER REFERENCES tiquetes (id),
    valor          REAL    NOT NULL CHECK (valor > 0),
    medio          TEXT    NOT NULL CHECK (medio IN ('efectivo', 'digital')),
    registrado_por TEXT    NOT NULL,
    fecha_registro TEXT    NOT NULL,
    id_cliente     TEXT    UNIQUE
);

CREATE TABLE IF NOT EXISTS manifiestos (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    viaje_id      INTEGER NOT NULL UNIQUE REFERENCES viajes (id),
    generado_por  TEXT    NOT NULL,
    fecha         TEXT    NOT NULL,
    contenido     TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    accion    TEXT NOT NULL,
    usuario   TEXT NOT NULL,
    rol       TEXT NOT NULL,
    detalle   TEXT NOT NULL DEFAULT '',
    timestamp TEXT NOT NULL
);

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


# ---------------------------------------------------------------------------
# 2) Migración de la tabla ``tiquetes``
# ---------------------------------------------------------------------------
COLUMNAS_NUEVAS_TIQUETES: dict[str, str] = {
    "viaje_id": "INTEGER REFERENCES viajes (id)",
    "codigo_qr": "TEXT",
    "valor": "REAL",
    "representante_documento": "TEXT",
}


def _migrar_tiquetes(conn: sqlite3.Connection) -> None:
    """Agrega dinámicamente las columnas nuevas a una tabla ``tiquetes`` antigua."""
    columnas = {
        fila["name"] for fila in conn.execute("PRAGMA table_info(tiquetes)")
    }
    if not columnas:
        return

    for nombre, definicion in COLUMNAS_NUEVAS_TIQUETES.items():
        if nombre not in columnas:
            conn.execute(
                f"ALTER TABLE tiquetes ADD COLUMN {nombre} {definicion}"
            )


# ---------------------------------------------------------------------------
# 3) Índices (incluye los únicos parciales que exige la operación)
# ---------------------------------------------------------------------------
INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp
    ON audit_logs (timestamp);

CREATE UNIQUE INDEX IF NOT EXISTS uq_tiquetes_viaje_asiento
    ON tiquetes (viaje_id, asiento)
    WHERE viaje_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_tiquetes_codigo_qr
    ON tiquetes (codigo_qr)
    WHERE codigo_qr IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_tiquetes_viaje_id
    ON tiquetes (viaje_id);

CREATE INDEX IF NOT EXISTS idx_pagos_viaje_id
    ON pagos (viaje_id);

CREATE INDEX IF NOT EXISTS idx_abordajes_viaje_id
    ON abordajes (viaje_id);
"""


# ---------------------------------------------------------------------------
# 4) Semilla demo
# ---------------------------------------------------------------------------
USUARIOS_DEMO: tuple[tuple[str, str, str, str], ...] = (
    ("admin", "Administrador de Despacho", "ADMIN_DESPACHO", "Admin2026*"),
    ("taquilla", "Taquillero de Turno", "TAQUILLERO", "Taquilla2026*"),
    ("conductor", "Conductor de Turno", "CONDUCTOR", "Conductor2026*"),
)


def _sembrar_demo(conn: sqlite3.Connection) -> None:
    """Inserta los usuarios demo solo si la semilla está activa y no hay usuarios."""
    if os.getenv("COOTRANSORIENTE_SEED_DEMO") != "1":
        return

    if conn.execute("SELECT 1 FROM usuarios LIMIT 1").fetchone() is not None:
        return

    # Import local para evitar ciclos: ``auth`` no debe depender de este módulo.
    from . import auth

    conn.executemany(
        """
        INSERT INTO usuarios (usuario, nombre, rol, password_hash)
        VALUES (?, ?, ?, ?)
        """,
        [
            (usuario, nombre, rol, auth.hash_password(password))
            for usuario, nombre, rol, password in USUARIOS_DEMO
        ],
    )


def get_connection() -> sqlite3.Connection:
    """Abre una conexión SQLite con filas accesibles por nombre y FKs activas."""
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    """Crea tablas, migra, indexa y siembra, en ese orden estricto."""
    conn = get_connection()
    try:
        # 1) Creación de tablas (y disparadores de auditoría).
        conn.executescript(SCHEMA_SQL)
        # 2) Migración de columnas nuevas en tiquetes.
        _migrar_tiquetes(conn)
        # 3) Índices, incluidos los únicos parciales.
        conn.executescript(INDEX_SQL)
        # 4) Semilla demo opcional.
        _sembrar_demo(conn)
        conn.commit()
    finally:
        conn.close()
