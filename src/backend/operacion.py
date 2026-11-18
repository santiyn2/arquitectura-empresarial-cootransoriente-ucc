"""Operación del servicio: sesión, usuarios, vehículos, viajes, despacho,
manifiestos, abordajes por QR (con sincronización sin conexión), pagos y
conciliación. Responsable: Luis Arrieta (Responsable 3).

Toda acción que cambia datos deja un registro en ``audit_logs``.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel, ConfigDict, Field, field_validator

from .auth import (
    HASH_RELLENO,
    crear_token,
    hash_password,
    minutos_de_vida_token,
    verificar_qr,
    verify_password,
)
from .database import get_connection
from .legal_compliance import registrar_auditoria
from .security_rbac import (
    ADMIN_DESPACHO,
    CONDUCTOR,
    TAQUILLERO,
    UsuarioAutenticado,
    require_roles,
)

router = APIRouter()

MAX_INTENTOS_FALLIDOS = 5
MINUTOS_BLOQUEO = 5

Rol = Literal["ADMIN_DESPACHO", "TAQUILLERO", "CONDUCTOR"]


def _ahora() -> datetime:
    return datetime.now(timezone.utc)


def _iso(momento: datetime | None = None) -> str:
    return (momento or _ahora()).isoformat(timespec="seconds")


def _json(datos: dict) -> str:
    return json.dumps(datos, ensure_ascii=False, sort_keys=True)


def _error_base() -> HTTPException:
    return HTTPException(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "No fue posible guardar la operación; no se hicieron cambios",
    )


# ==========================================================================
# Sesión
# ==========================================================================
class LoginIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    usuario: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=128)


@router.post("/api/auth/login", tags=["Sesión"])
def iniciar_sesion(payload: LoginIn) -> dict:
    """Valida usuario y contraseña y entrega un token de sesión.

    Tras 5 intentos fallidos seguidos la cuenta se bloquea 5 minutos.
    """
    conn = get_connection()
    try:
        fila = conn.execute(
            "SELECT * FROM usuarios WHERE usuario = ?", (payload.usuario,)
        ).fetchone()

        if fila is not None and fila["bloqueado_hasta"]:
            if datetime.fromisoformat(fila["bloqueado_hasta"]) > _ahora():
                raise HTTPException(
                    status.HTTP_429_TOO_MANY_REQUESTS,
                    f"Cuenta bloqueada por intentos fallidos; espere {MINUTOS_BLOQUEO} minutos",
                )

        hash_a_comparar = fila["password_hash"] if fila is not None else HASH_RELLENO
        clave_ok = verify_password(payload.password, hash_a_comparar)

        if fila is None or not fila["activo"] or not clave_ok:
            if fila is not None:
                intentos = fila["intentos_fallidos"] + 1
                bloqueo = None
                if intentos >= MAX_INTENTOS_FALLIDOS:
                    bloqueo = _iso(_ahora() + timedelta(minutes=MINUTOS_BLOQUEO))
                    intentos = 0
                conn.execute(
                    "UPDATE usuarios SET intentos_fallidos = ?, bloqueado_hasta = ? WHERE id = ?",
                    (intentos, bloqueo, fila["id"]),
                )
            registrar_auditoria(
                conn,
                accion="LOGIN_FALLIDO",
                usuario=payload.usuario,
                rol=fila["rol"] if fila is not None else "DESCONOCIDO",
                detalle=_json({"usuario": payload.usuario}),
            )
            conn.commit()
            raise HTTPException(
                status.HTTP_401_UNAUTHORIZED,
                "Usuario o contraseña incorrectos",
                headers={"WWW-Authenticate": "Bearer"},
            )

        conn.execute(
            "UPDATE usuarios SET intentos_fallidos = 0, bloqueado_hasta = NULL WHERE id = ?",
            (fila["id"],),
        )
        registrar_auditoria(
            conn,
            accion="LOGIN_OK",
            usuario=fila["nombre"],
            rol=fila["rol"],
            detalle=_json({"usuario": fila["usuario"]}),
        )
        conn.commit()
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()

    return {
        "access_token": crear_token(fila["nombre"], fila["rol"], fila["usuario"]),
        "token_type": "bearer",
        "expira_en_minutos": minutos_de_vida_token(),
        "usuario": fila["usuario"],
        "nombre": fila["nombre"],
        "rol": fila["rol"],
    }


# ==========================================================================
# Usuarios (solo administración)
# ==========================================================================
class UsuarioCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    usuario: str = Field(pattern=r"^[a-z0-9._-]{3,30}$")
    nombre: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    rol: Rol


@router.post("/api/admin/usuarios", status_code=201, tags=["Usuarios"])
def crear_usuario(
    payload: UsuarioCreate,
    admin: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO usuarios (usuario, nombre, rol, password_hash) VALUES (?, ?, ?, ?)",
            (payload.usuario, payload.nombre, payload.rol, hash_password(payload.password)),
        )
        registrar_auditoria(
            conn,
            accion="CREAR_USUARIO",
            usuario=admin.nombre,
            rol=admin.rol,
            detalle=_json({"usuario": payload.usuario, "rol": payload.rol}),
        )
        conn.commit()
        nuevo_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "Ese usuario ya existe") from exc
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()
    return {"id": nuevo_id, "usuario": payload.usuario, "nombre": payload.nombre, "rol": payload.rol}


@router.get("/api/admin/usuarios", tags=["Usuarios"])
def listar_usuarios(
    rol: Rol | None = None,
    _: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    conn = get_connection()
    try:
        consulta = "SELECT id, usuario, nombre, rol, activo FROM usuarios"
        parametros: tuple = ()
        if rol:
            consulta += " WHERE rol = ?"
            parametros = (rol,)
        filas = conn.execute(consulta + " ORDER BY usuario", parametros).fetchall()
    finally:
        conn.close()
    return {"usuarios": [dict(f) for f in filas]}


# ==========================================================================
# Vehículos
# ==========================================================================
class VehiculoCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    placa: str = Field(min_length=5, max_length=10)
    capacidad: int = Field(gt=0, le=100)

    @field_validator("placa")
    @classmethod
    def _placa_en_mayusculas(cls, valor: str) -> str:
        return valor.upper().replace(" ", "")


@router.post("/api/vehiculos", status_code=201, tags=["Vehículos"])
def crear_vehiculo(
    payload: VehiculoCreate,
    admin: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    conn = get_connection()
    try:
        cursor = conn.execute(
            "INSERT INTO vehiculos (placa, capacidad) VALUES (?, ?)",
            (payload.placa, payload.capacidad),
        )
        registrar_auditoria(
            conn,
            accion="CREAR_VEHICULO",
            usuario=admin.nombre,
            rol=admin.rol,
            detalle=_json({"placa": payload.placa, "capacidad": payload.capacidad}),
        )
        conn.commit()
        nuevo_id = int(cursor.lastrowid)
    except sqlite3.IntegrityError as exc:
        conn.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, f"Ya existe un vehículo con placa {payload.placa}"
        ) from exc
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()
    return {"id": nuevo_id, "placa": payload.placa, "capacidad": payload.capacidad}


@router.get("/api/vehiculos", tags=["Vehículos"])
def listar_vehiculos(
    _: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    conn = get_connection()
    try:
        filas = conn.execute(
            "SELECT id, placa, capacidad, activo FROM vehiculos ORDER BY placa"
        ).fetchall()
    finally:
        conn.close()
    return {"vehiculos": [dict(f) for f in filas]}


# ==========================================================================
# Viajes
# ==========================================================================
class ViajeCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ruta: str = Field(min_length=3, max_length=120)
    vehiculo_id: int = Field(ge=1)
    conductor_usuario: str = Field(min_length=3, max_length=30)
    salida_programada: str
    tarifa: int = Field(ge=0, le=1_000_000, description="Pesos colombianos por pasajero")

    @field_validator("salida_programada")
    @classmethod
    def _fecha_valida(cls, valor: str) -> str:
        try:
            datetime.fromisoformat(valor)
        except ValueError as exc:
            raise ValueError("Use fecha y hora ISO 8601, p. ej. 2026-11-20T06:30") from exc
        return valor


_SELECT_VIAJE = """
SELECT v.id, v.ruta, v.salida_programada, v.tarifa, v.estado,
       v.conductor_usuario, v.vehiculo_id, v.fecha_despacho,
       h.placa, h.capacidad,
       (SELECT COUNT(*) FROM tiquetes t WHERE t.viaje_id = v.id) AS tiquetes,
       (SELECT COUNT(*) FROM abordajes a WHERE a.viaje_id = v.id) AS abordajes
FROM viajes v JOIN vehiculos h ON h.id = v.vehiculo_id
"""


def _viaje_o_404(conn: sqlite3.Connection, viaje_id: int) -> sqlite3.Row:
    fila = conn.execute(_SELECT_VIAJE + " WHERE v.id = ?", (viaje_id,)).fetchone()
    if fila is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "El viaje no existe")
    return fila


def _exigir_conductor_asignado(usuario: UsuarioAutenticado, viaje: sqlite3.Row) -> None:
    """Un conductor solo opera sus propios viajes."""
    if usuario.rol == CONDUCTOR and viaje["conductor_usuario"] != usuario.usuario:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, "Este viaje está asignado a otro conductor"
        )


@router.post("/api/viajes", status_code=201, tags=["Viajes"])
def crear_viaje(
    payload: ViajeCreate,
    admin: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    conn = get_connection()
    try:
        vehiculo = conn.execute(
            "SELECT id, activo FROM vehiculos WHERE id = ?", (payload.vehiculo_id,)
        ).fetchone()
        if vehiculo is None or not vehiculo["activo"]:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "El vehículo no existe o está inactivo")
        conductor = conn.execute(
            "SELECT rol, activo FROM usuarios WHERE usuario = ?", (payload.conductor_usuario,)
        ).fetchone()
        if conductor is None or conductor["rol"] != CONDUCTOR or not conductor["activo"]:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "El conductor no existe, está inactivo o no tiene rol CONDUCTOR",
            )

        cursor = conn.execute(
            """
            INSERT INTO viajes (ruta, vehiculo_id, conductor_usuario,
                                salida_programada, tarifa, creado_por)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                payload.ruta,
                payload.vehiculo_id,
                payload.conductor_usuario,
                payload.salida_programada,
                payload.tarifa,
                admin.nombre,
            ),
        )
        viaje_id = int(cursor.lastrowid)
        registrar_auditoria(
            conn,
            accion="CREAR_VIAJE",
            usuario=admin.nombre,
            rol=admin.rol,
            detalle=_json({"viaje_id": viaje_id, **payload.model_dump()}),
        )
        conn.commit()
        return dict(_viaje_o_404(conn, viaje_id))
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()


@router.get("/api/viajes", tags=["Viajes"])
def listar_viajes(
    estado: Literal["programado", "despachado", "cerrado"] | None = None,
    usuario: UsuarioAutenticado = Depends(
        require_roles(ADMIN_DESPACHO, TAQUILLERO, CONDUCTOR)
    ),
) -> dict:
    """Lista viajes. Un conductor solo ve los suyos."""
    condiciones, parametros = [], []
    if estado:
        condiciones.append("v.estado = ?")
        parametros.append(estado)
    if usuario.rol == CONDUCTOR:
        condiciones.append("v.conductor_usuario = ?")
        parametros.append(usuario.usuario)
    donde = (" WHERE " + " AND ".join(condiciones)) if condiciones else ""

    conn = get_connection()
    try:
        filas = conn.execute(
            _SELECT_VIAJE + donde + " ORDER BY v.salida_programada DESC, v.id DESC",
            parametros,
        ).fetchall()
    finally:
        conn.close()
    return {"viajes": [dict(f) for f in filas]}


@router.get("/api/viajes/{viaje_id}", tags=["Viajes"])
def ver_viaje(
    viaje_id: int,
    usuario: UsuarioAutenticado = Depends(
        require_roles(ADMIN_DESPACHO, TAQUILLERO, CONDUCTOR)
    ),
) -> dict:
    """Detalle del viaje con los asientos ya vendidos (para pintar el bus)."""
    conn = get_connection()
    try:
        viaje = _viaje_o_404(conn, viaje_id)
        _exigir_conductor_asignado(usuario, viaje)
        asientos = [
            f["asiento"]
            for f in conn.execute(
                "SELECT asiento FROM tiquetes WHERE viaje_id = ? ORDER BY id", (viaje_id,)
            )
        ]
    finally:
        conn.close()
    return {**dict(viaje), "asientos_ocupados": asientos}


# ==========================================================================
# Despacho y manifiesto
# ==========================================================================
@router.post("/api/viajes/{viaje_id}/despacho", tags=["Despacho"])
def despachar_viaje(
    viaje_id: int,
    admin: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    """Despacha el viaje y genera su manifiesto digital.

    Responde 409 si el viaje ya salió o si el manifiesto estaría incompleto
    (sin tiquetes). Después del despacho ya no se venden más tiquetes.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        viaje = _viaje_o_404(conn, viaje_id)
        if viaje["estado"] != "programado":
            raise HTTPException(
                status.HTTP_409_CONFLICT, f"El viaje ya está {viaje['estado']}"
            )

        pasajeros = [
            dict(f)
            for f in conn.execute(
                """
                SELECT id AS tiquete_id, pasajero_nombre, documento, asiento,
                       es_menor, representante_documento, codigo_qr
                FROM tiquetes WHERE viaje_id = ? ORDER BY id
                """,
                (viaje_id,),
            )
        ]
        if not pasajeros:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Manifiesto incompleto: el viaje no tiene tiquetes vendidos",
            )

        fecha = _iso()
        manifiesto = {
            "viaje_id": viaje_id,
            "ruta": viaje["ruta"],
            "placa": viaje["placa"],
            "capacidad": viaje["capacidad"],
            "conductor_usuario": viaje["conductor_usuario"],
            "salida_programada": viaje["salida_programada"],
            "generado_por": admin.nombre,
            "fecha_generacion": fecha,
            "total_pasajeros": len(pasajeros),
            "pasajeros": pasajeros,
        }
        conn.execute(
            "INSERT INTO manifiestos (viaje_id, generado_por, fecha, contenido) VALUES (?, ?, ?, ?)",
            (viaje_id, admin.nombre, fecha, _json(manifiesto)),
        )
        conn.execute(
            "UPDATE viajes SET estado = 'despachado', despachado_por = ?, fecha_despacho = ? WHERE id = ?",
            (admin.nombre, fecha, viaje_id),
        )
        registrar_auditoria(
            conn,
            accion="DESPACHO_VIAJE",
            usuario=admin.nombre,
            rol=admin.rol,
            detalle=_json(
                {"viaje_id": viaje_id, "placa": viaje["placa"], "pasajeros": len(pasajeros)}
            ),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()
    return manifiesto


@router.get("/api/viajes/{viaje_id}/manifiesto", tags=["Despacho"])
def ver_manifiesto(
    viaje_id: int,
    usuario: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO, CONDUCTOR)),
) -> dict:
    """Manifiesto del viaje (lista de pasajeros y sus códigos QR válidos)."""
    conn = get_connection()
    try:
        viaje = _viaje_o_404(conn, viaje_id)
        _exigir_conductor_asignado(usuario, viaje)
        fila = conn.execute(
            "SELECT contenido FROM manifiestos WHERE viaje_id = ?", (viaje_id,)
        ).fetchone()
    finally:
        conn.close()
    if fila is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "El manifiesto se genera al despachar el viaje"
        )
    return json.loads(fila["contenido"])


@router.post("/api/viajes/{viaje_id}/cierre", tags=["Despacho"])
def cerrar_viaje(
    viaje_id: int,
    admin: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    conn = get_connection()
    try:
        viaje = _viaje_o_404(conn, viaje_id)
        if viaje["estado"] != "despachado":
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Solo se cierran viajes que ya fueron despachados"
            )
        conn.execute("UPDATE viajes SET estado = 'cerrado' WHERE id = ?", (viaje_id,))
        registrar_auditoria(
            conn,
            accion="CIERRE_VIAJE",
            usuario=admin.nombre,
            rol=admin.rol,
            detalle=_json({"viaje_id": viaje_id}),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()
    return {"viaje_id": viaje_id, "estado": "cerrado"}


# ==========================================================================
# Abordajes por QR (admiten sincronización en lote sin duplicar)
# ==========================================================================
class AbordajeIn(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    id_cliente: str = Field(min_length=8, max_length=64)
    codigo_qr: str = Field(min_length=1, max_length=200)
    fecha_escaneo: str | None = None

    @field_validator("fecha_escaneo")
    @classmethod
    def _fecha_valida(cls, valor: str | None) -> str | None:
        if valor is not None:
            try:
                datetime.fromisoformat(valor.replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("fecha_escaneo debe ser ISO 8601") from exc
        return valor


class AbordajesLote(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viaje_id: int = Field(ge=1)
    abordajes: list[AbordajeIn] = Field(min_length=1, max_length=500)


@router.post("/api/abordajes/lote", tags=["Abordajes"])
def registrar_abordajes(
    lote: AbordajesLote,
    conductor: UsuarioAutenticado = Depends(require_roles(CONDUCTOR)),
) -> dict:
    """Registra abordajes escaneados (quizá sin señal) y los sincroniza.

    Reenviar el mismo ``id_cliente`` no duplica: se responde ``duplicado``.
    Cada abordaje es ``aceptado``, ``duplicado`` o ``rechazado`` con su motivo.
    """
    conn = get_connection()
    resultados: list[dict] = []
    try:
        conn.execute("BEGIN IMMEDIATE")
        viaje = _viaje_o_404(conn, lote.viaje_id)
        _exigir_conductor_asignado(conductor, viaje)
        if viaje["estado"] != "despachado":
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"El viaje está {viaje['estado']}: solo se registran abordajes en viajes despachados",
            )

        for item in lote.abordajes:
            def respuesta(estado: str, motivo: str = "", tiquete_id: int | None = None) -> dict:
                return {
                    "id_cliente": item.id_cliente,
                    "estado": estado,
                    "motivo": motivo,
                    "tiquete_id": tiquete_id,
                }

            if conn.execute(
                "SELECT 1 FROM abordajes WHERE id_cliente = ?", (item.id_cliente,)
            ).fetchone():
                resultados.append(respuesta("duplicado", "Ya estaba registrado"))
                continue

            datos_qr = verificar_qr(item.codigo_qr)
            if datos_qr is None:
                resultados.append(respuesta("rechazado", "QR no válido o alterado"))
                continue
            tiquete_id, viaje_del_qr = datos_qr
            if viaje_del_qr != lote.viaje_id:
                resultados.append(
                    respuesta("rechazado", "El tiquete es de otro viaje", tiquete_id)
                )
                continue
            tiquete = conn.execute(
                "SELECT id FROM tiquetes WHERE id = ? AND viaje_id = ?",
                (tiquete_id, lote.viaje_id),
            ).fetchone()
            if tiquete is None:
                resultados.append(respuesta("rechazado", "El tiquete no existe", tiquete_id))
                continue
            if conn.execute(
                "SELECT 1 FROM abordajes WHERE tiquete_id = ?", (tiquete_id,)
            ).fetchone():
                resultados.append(respuesta("rechazado", "Este QR ya fue usado", tiquete_id))
                continue

            conn.execute(
                """
                INSERT INTO abordajes (tiquete_id, viaje_id, validado_por,
                                       fecha_escaneo, fecha_registro, id_cliente)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    tiquete_id,
                    lote.viaje_id,
                    conductor.nombre,
                    item.fecha_escaneo or _iso(),
                    _iso(),
                    item.id_cliente,
                ),
            )
            resultados.append(respuesta("aceptado", "", tiquete_id))

        resumen = {
            estado: sum(1 for r in resultados if r["estado"] == estado)
            for estado in ("aceptado", "duplicado", "rechazado")
        }
        registrar_auditoria(
            conn,
            accion="ABORDAJES_LOTE",
            usuario=conductor.nombre,
            rol=conductor.rol,
            detalle=_json({"viaje_id": lote.viaje_id, **resumen}),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()
    return {"viaje_id": lote.viaje_id, **resumen, "resultados": resultados}


# ==========================================================================
# Pagos y conciliación
# ==========================================================================
class PagoCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    viaje_id: int = Field(ge=1)
    tiquete_id: int | None = Field(default=None, ge=1)
    valor: int = Field(gt=0, le=10_000_000, description="Pesos colombianos")
    medio: Literal["efectivo", "digital"]
    id_cliente: str | None = Field(default=None, min_length=8, max_length=64)


@router.post("/api/pagos", status_code=201, tags=["Recaudo"])
def registrar_pago(
    payload: PagoCreate,
    response: Response,
    usuario: UsuarioAutenticado = Depends(require_roles(CONDUCTOR, TAQUILLERO)),
) -> dict:
    """Registra un pago (p. ej. un pasajero que sube en la vía y paga en efectivo).

    Con ``id_cliente`` repetido responde 200 con el pago original y no duplica.
    """
    conn = get_connection()
    try:
        conn.execute("BEGIN IMMEDIATE")
        if payload.id_cliente:
            previo = conn.execute(
                "SELECT * FROM pagos WHERE id_cliente = ?", (payload.id_cliente,)
            ).fetchone()
            if previo is not None:
                response.status_code = status.HTTP_200_OK
                return {**dict(previo), "duplicado": True}

        viaje = _viaje_o_404(conn, payload.viaje_id)
        _exigir_conductor_asignado(usuario, viaje)
        if viaje["estado"] == "cerrado":
            raise HTTPException(status.HTTP_409_CONFLICT, "El viaje está cerrado")
        if payload.tiquete_id is not None:
            if conn.execute(
                "SELECT 1 FROM tiquetes WHERE id = ? AND viaje_id = ?",
                (payload.tiquete_id, payload.viaje_id),
            ).fetchone() is None:
                raise HTTPException(
                    status.HTTP_404_NOT_FOUND, "El tiquete no existe en este viaje"
                )

        fecha = _iso()
        cursor = conn.execute(
            """
            INSERT INTO pagos (viaje_id, tiquete_id, valor, medio,
                               registrado_por, fecha_registro, id_cliente)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.viaje_id,
                payload.tiquete_id,
                payload.valor,
                payload.medio,
                usuario.nombre,
                fecha,
                payload.id_cliente,
            ),
        )
        pago_id = int(cursor.lastrowid)
        registrar_auditoria(
            conn,
            accion="REGISTRO_PAGO",
            usuario=usuario.nombre,
            rol=usuario.rol,
            detalle=_json({"pago_id": pago_id, **payload.model_dump(exclude={"id_cliente"})}),
        )
        conn.commit()
    except HTTPException:
        conn.rollback()
        raise
    except sqlite3.Error as exc:
        conn.rollback()
        raise _error_base() from exc
    finally:
        conn.close()
    return {
        "id": pago_id,
        "viaje_id": payload.viaje_id,
        "tiquete_id": payload.tiquete_id,
        "valor": payload.valor,
        "medio": payload.medio,
        "registrado_por": usuario.nombre,
        "fecha_registro": fecha,
        "duplicado": False,
    }


@router.get("/api/viajes/{viaje_id}/conciliacion", tags=["Recaudo"])
def conciliar_viaje(
    viaje_id: int,
    _: UsuarioAutenticado = Depends(require_roles(ADMIN_DESPACHO)),
) -> dict:
    """Compara lo que debió recaudarse (tiquetes) con lo registrado (pagos).

    ``diferencia`` = recaudado − esperado: negativa es faltante.
    """
    conn = get_connection()
    try:
        viaje = _viaje_o_404(conn, viaje_id)
        tiquetes, esperado = conn.execute(
            "SELECT COUNT(*), COALESCE(SUM(valor), 0) FROM tiquetes WHERE viaje_id = ?",
            (viaje_id,),
        ).fetchone()
        abordados = conn.execute(
            "SELECT COUNT(*) FROM abordajes WHERE viaje_id = ?", (viaje_id,)
        ).fetchone()[0]
        pagos = conn.execute(
            """
            SELECT COUNT(*) AS cantidad,
                   COALESCE(SUM(valor), 0) AS total,
                   COALESCE(SUM(CASE WHEN medio = 'efectivo' THEN valor END), 0) AS efectivo,
                   COALESCE(SUM(CASE WHEN medio = 'digital' THEN valor END), 0) AS digital,
                   COALESCE(SUM(CASE WHEN tiquete_id IS NULL THEN 1 ELSE 0 END), 0) AS sin_tiquete
            FROM pagos WHERE viaje_id = ?
            """,
            (viaje_id,),
        ).fetchone()
    finally:
        conn.close()

    diferencia = int(pagos["total"]) - int(esperado)
    return {
        "viaje_id": viaje_id,
        "estado_viaje": viaje["estado"],
        "tiquetes_emitidos": tiquetes,
        "abordajes_validados": abordados,
        "tiquetes_sin_abordar": tiquetes - abordados,
        "valor_esperado": int(esperado),
        "pagos_registrados": pagos["cantidad"],
        "pagos_sin_tiquete": pagos["sin_tiquete"],
        "recaudado_total": int(pagos["total"]),
        "recaudado_efectivo": int(pagos["efectivo"]),
        "recaudado_digital": int(pagos["digital"]),
        "diferencia": diferencia,
        "resultado": "cuadra" if diferencia == 0 else ("sobrante" if diferencia > 0 else "faltante"),
    }
