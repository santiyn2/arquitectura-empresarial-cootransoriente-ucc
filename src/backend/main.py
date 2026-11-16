"""API REST de Cootransoriente Tayrona — seguridad y Ley 1581 de 2012.

Responsable: Santiago Escalante Meriño (Responsable 1).
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import Depends, FastAPI, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from .database import get_connection, init_db
from .legal_compliance import (
    AVISO_PRIVACIDAD_LEY_1581,
    CANAL_CONTACTO_DATOS,
    PLAZOS_ARCO,
    registrar_auditoria,
    validar_consentimiento_datos,
)
from .security_rbac import (
    ADMIN_DESPACHO,
    TAQUILLERO,
    UsuarioAutenticado,
    require_roles,
)


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Garantiza el esquema SQLite al arrancar la API."""
    init_db()
    yield


app = FastAPI(
    title="Cootransoriente Tayrona API",
    description=(
        "API de seguridad, cumplimiento de la Ley 1581 de 2012, auditoría "
        "inmutable y control de acceso por roles (RBAC)."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


class TiqueteCreate(BaseModel):
    """Datos mínimos para emitir un tiquete con consentimiento informado."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    pasajero_nombre: str = Field(min_length=3, max_length=120)
    documento: str = Field(min_length=5, max_length=30)
    es_menor: bool = False
    ruta: str = Field(min_length=3, max_length=120)
    asiento: str = Field(min_length=1, max_length=10)
    autorizacion_ley1581: bool


class TiqueteOut(BaseModel):
    """Representación del tiquete persistido."""

    id: int
    pasajero_nombre: str
    documento: str
    es_menor: bool
    ruta: str
    asiento: str
    autorizacion_ley1581: bool
    fecha_autorizacion: str
    creado_por: str


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@app.get("/api/privacidad", tags=["Cumplimiento Ley 1581"])
def obtener_aviso_privacidad() -> dict:
    """Devuelve el aviso de privacidad vigente y los plazos ARCO."""
    return {
        "ley": "Ley 1581 de 2012",
        "aviso_privacidad": AVISO_PRIVACIDAD_LEY_1581,
        "canal_contacto": CANAL_CONTACTO_DATOS,
        "plazos_arco": {
            "consultas": PLAZOS_ARCO["consultas"],
            "reclamos": PLAZOS_ARCO["reclamos"],
        },
    }


@app.post(
    "/api/tiquetes",
    response_model=TiqueteOut,
    status_code=status.HTTP_201_CREATED,
    tags=["Tiquetes"],
)
def emitir_tiquete(
    payload: TiqueteCreate,
    usuario: UsuarioAutenticado = Depends(require_roles(TAQUILLERO, ADMIN_DESPACHO)),
) -> TiqueteOut:
    """Emite un tiquete validando la autorización de datos y auditando la acción."""
    try:
        validar_consentimiento_datos(
            autorizacion=payload.autorizacion_ley1581,
            es_menor=payload.es_menor,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    fecha_autorizacion = _utc_now_iso()
    conn = get_connection()
    try:
        cursor = conn.execute(
            """
            INSERT INTO tiquetes (
                pasajero_nombre,
                documento,
                es_menor,
                ruta,
                asiento,
                autorizacion_ley1581,
                fecha_autorizacion,
                creado_por
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.pasajero_nombre,
                payload.documento,
                int(payload.es_menor),
                payload.ruta,
                payload.asiento,
                int(payload.autorizacion_ley1581),
                fecha_autorizacion,
                usuario.nombre,
            ),
        )
        tiquete_id = int(cursor.lastrowid)

        registrar_auditoria(
            conn,
            accion="EMISION_TIQUETE",
            usuario=usuario.nombre,
            rol=usuario.rol,
            detalle=json.dumps(
                {
                    "tiquete_id": tiquete_id,
                    "documento": payload.documento,
                    "ruta": payload.ruta,
                    "asiento": payload.asiento,
                    "es_menor": payload.es_menor,
                    "autorizacion_ley1581": payload.autorizacion_ley1581,
                    "fecha_autorizacion": fecha_autorizacion,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="No fue posible persistir el tiquete y su registro de auditoría",
        ) from exc
    finally:
        conn.close()

    return TiqueteOut(
        id=tiquete_id,
        pasajero_nombre=payload.pasajero_nombre,
        documento=payload.documento,
        es_menor=payload.es_menor,
        ruta=payload.ruta,
        asiento=payload.asiento,
        autorizacion_ley1581=payload.autorizacion_ley1581,
        fecha_autorizacion=fecha_autorizacion,
        creado_por=usuario.nombre,
    )


@app.get("/api/admin/auditoria", tags=["Auditoría"])
def consultar_auditoria(
    _: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    """Consulta los registros de auditoría. Exclusivo de ADMIN_DESPACHO."""
    conn = get_connection()
    try:
        filas = conn.execute(
            """
            SELECT id, accion, usuario, rol, detalle, timestamp
            FROM audit_logs
            ORDER BY id ASC
            """
        ).fetchall()
    finally:
        conn.close()

    registros = [dict(fila) for fila in filas]
    return {"total": len(registros), "registros": registros}
