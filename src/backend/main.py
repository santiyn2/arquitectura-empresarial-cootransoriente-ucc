"""API REST de Cootransoriente Tayrona — seguridad, Ley 1581 y operación.

Responsable: Santiago Escalante Meriño (Responsable 1).

La identidad se resuelve con Bearer JWT (``security_rbac``) y los endpoints
operativos del equipo se montan desde :mod:`src.backend.operacion`.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from . import auth, operacion
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

MEDIOS_PAGO_VALIDOS = frozenset({"efectivo", "digital"})


@asynccontextmanager
async def lifespan(_: FastAPI):
    """Garantiza el esquema SQLite al arrancar la API."""
    init_db()
    yield


app = FastAPI(
    title="Cootransoriente Tayrona API",
    description=(
        "API de seguridad, cumplimiento de la Ley 1581 de 2012, auditoría "
        "inmutable, control de acceso por roles (RBAC) y operación de viajes."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

# Endpoints operativos del equipo (despacho, abordajes, manifiestos, etc.).
app.include_router(operacion.router)


class TiqueteCreate(BaseModel):
    """Datos mínimos para emitir un tiquete con consentimiento informado."""

    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    pasajero_nombre: str = Field(min_length=3, max_length=120)
    documento: str = Field(min_length=5, max_length=30)
    es_menor: bool = False
    ruta: str | None = Field(default=None, min_length=3, max_length=120)
    asiento: str = Field(min_length=1, max_length=10)
    autorizacion_ley1581: bool
    viaje_id: int | None = Field(default=None, ge=1)
    representante_documento: str | None = Field(default=None, max_length=30)
    medio_pago: str | None = Field(default=None, max_length=20)


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
    viaje_id: int | None = None
    codigo_qr: str | None = None
    valor: float | None = None
    representante_documento: str | None = None


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _firmar_qr(datos: dict) -> str:
    """Firma el contenido del tiquete con el contrato ``auth.firmar_qr(datos)``."""
    return auth.firmar_qr(datos)


@app.get("/health", tags=["Salud"])
def health() -> dict:
    """Verifica conectividad real con SQLite: ``200`` si responde, ``503`` si no."""
    try:
        conn = get_connection()
        try:
            conn.execute("SELECT 1").fetchone()
        finally:
            conn.close()
    except Exception as exc:  # cualquier fallo de conectividad o de archivo
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Base de datos no disponible",
        ) from exc

    return {"status": "ok", "version": app.version}


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
    """Emite un tiquete con consentimiento Ley 1581, QR y auditoría atómica."""
    try:
        validar_consentimiento_datos(
            autorizacion=payload.autorizacion_ley1581,
            es_menor=payload.es_menor,
            representante_documento=payload.representante_documento,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc

    fecha_autorizacion = _utc_now_iso()
    conn = get_connection()
    try:
        viaje = None
        valor: float | None = None

        if payload.viaje_id is not None:
            viaje = conn.execute(
                "SELECT * FROM viajes WHERE id = ?", (payload.viaje_id,)
            ).fetchone()
            if viaje is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El viaje {payload.viaje_id} no existe",
                )

            if viaje["estado"] != "programado":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"El viaje {payload.viaje_id} no está disponible para "
                        f"venta (estado '{viaje['estado']}')"
                    ),
                )

            # El conflicto de asiento se evalúa antes del cupo para devolver
            # un detalle preciso al taquillero.
            asiento_ocupado = conn.execute(
                "SELECT 1 FROM tiquetes WHERE viaje_id = ? AND asiento = ?",
                (payload.viaje_id, payload.asiento),
            ).fetchone()
            if asiento_ocupado is not None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        f"El asiento {payload.asiento} ya está ocupado en el "
                        f"viaje {payload.viaje_id}"
                    ),
                )

            vehiculo = conn.execute(
                "SELECT capacidad FROM vehiculos WHERE id = ?",
                (viaje["vehiculo_id"],),
            ).fetchone()
            if vehiculo is None:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El vehículo asignado al viaje no existe",
                )

            ocupados = conn.execute(
                "SELECT COUNT(*) FROM tiquetes WHERE viaje_id = ?",
                (payload.viaje_id,),
            ).fetchone()[0]
            if int(ocupados) >= int(vehiculo["capacidad"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="El viaje no tiene cupo disponible",
                )

            ruta = payload.ruta or viaje["ruta"]
            valor = float(viaje["tarifa"])
        else:
            ruta = payload.ruta

        if not ruta:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Debe indicar 'viaje_id' o 'ruta' para emitir el tiquete",
            )

        codigo_qr = _firmar_qr(
            {
                "viaje_id": payload.viaje_id,
                "documento": payload.documento,
                "asiento": payload.asiento,
                "ruta": ruta,
                "fecha_emision": fecha_autorizacion,
            }
        )

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
                creado_por,
                viaje_id,
                codigo_qr,
                valor,
                representante_documento
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.pasajero_nombre,
                payload.documento,
                int(payload.es_menor),
                ruta,
                payload.asiento,
                int(payload.autorizacion_ley1581),
                fecha_autorizacion,
                usuario.nombre,
                payload.viaje_id,
                codigo_qr,
                valor,
                payload.representante_documento,
            ),
        )
        tiquete_id = int(cursor.lastrowid)

        # El pago solo aplica a ventas asociadas a un viaje con tarifa > 0.
        if payload.viaje_id is not None and valor is not None and valor > 0:
            medio = (payload.medio_pago or "efectivo").strip().lower()
            if medio not in MEDIOS_PAGO_VALIDOS:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="'medio_pago' debe ser 'efectivo' o 'digital'",
                )

            conn.execute(
                """
                INSERT INTO pagos (
                    viaje_id,
                    tiquete_id,
                    valor,
                    medio,
                    registrado_por,
                    fecha_registro,
                    id_cliente
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.viaje_id,
                    tiquete_id,
                    valor,
                    medio,
                    usuario.nombre,
                    fecha_autorizacion,
                    f"PAGO-{uuid4().hex}",
                ),
            )

        registrar_auditoria(
            conn,
            accion="EMISION_TIQUETE",
            usuario=usuario.nombre,
            rol=usuario.rol,
            detalle=json.dumps(
                {
                    "tiquete_id": tiquete_id,
                    "documento": payload.documento,
                    "ruta": ruta,
                    "asiento": payload.asiento,
                    "es_menor": payload.es_menor,
                    "autorizacion_ley1581": payload.autorizacion_ley1581,
                    "fecha_autorizacion": fecha_autorizacion,
                    "viaje_id": payload.viaje_id,
                    "valor": valor,
                    "codigo_qr": codigo_qr,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        )

        # Transacción atómica: tiquete + pago + auditoría en un único commit.
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="El asiento o el código QR ya se encuentran registrados",
        ) from exc
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
        ruta=ruta,
        asiento=payload.asiento,
        autorizacion_ley1581=payload.autorizacion_ley1581,
        fecha_autorizacion=fecha_autorizacion,
        creado_por=usuario.nombre,
        viaje_id=payload.viaje_id,
        codigo_qr=codigo_qr,
        valor=valor,
        representante_documento=payload.representante_documento,
    )


@app.get(
    "/api/tiquetes/{tiquete_id}/qr.svg",
    tags=["Tiquetes"],
    response_class=Response,
)
def obtener_qr_tiquete(
    tiquete_id: int,
    _: UsuarioAutenticado = Depends(require_roles(TAQUILLERO, ADMIN_DESPACHO)),
) -> Response:
    """Genera el código QR del tiquete en formato SVG."""
    conn = get_connection()
    try:
        fila = conn.execute(
            """
            SELECT id, viaje_id, documento, asiento, codigo_qr
            FROM tiquetes
            WHERE id = ?
            """,
            (tiquete_id,),
        ).fetchone()
    finally:
        conn.close()

    if fila is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"El tiquete {tiquete_id} no existe",
        )

    contenido = fila["codigo_qr"] or json.dumps(
        {
            "tiquete_id": fila["id"],
            "viaje_id": fila["viaje_id"],
            "documento": fila["documento"],
            "asiento": fila["asiento"],
        },
        ensure_ascii=False,
        sort_keys=True,
    )

    try:
        import segno  # import local: solo se exige al usar el endpoint
    except ImportError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="La dependencia 'segno' no está instalada",
        ) from exc

    svg = segno.make(contenido).svg_inline(scale=6, border=2)
    return Response(content=svg, media_type="image/svg+xml")


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


# ---------------------------------------------------------------------------
# Frontend web y app móvil (solo si las carpetas existen en disco)
# ---------------------------------------------------------------------------
_SRC_DIR = Path(__file__).resolve().parents[1]
_FRONTEND_DIR = _SRC_DIR / "frontend-web"
_MOBILE_DIR = _SRC_DIR / "mobile-app"

if _FRONTEND_DIR.is_dir():
    app.mount(
        "/portal",
        StaticFiles(directory=_FRONTEND_DIR, html=True),
        name="portal",
    )

if _MOBILE_DIR.is_dir():
    app.mount(
        "/movil",
        StaticFiles(directory=_MOBILE_DIR, html=True),
        name="movil",
    )
