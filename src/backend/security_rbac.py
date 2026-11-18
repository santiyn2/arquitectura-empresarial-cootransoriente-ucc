"""Control de acceso basado en roles (RBAC) para la API.

La identidad ya no viaja en cabeceras de confianza: se resuelve validando el
token **Bearer JWT** emitido por :mod:`src.backend.auth`. El token es la única
fuente de verdad para el nombre, el rol y el identificador del usuario.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Header, HTTPException, status

from . import auth

ADMIN_DESPACHO = "ADMIN_DESPACHO"
TAQUILLERO = "TAQUILLERO"
CONDUCTOR = "CONDUCTOR"

ROLES_VALIDOS = frozenset({ADMIN_DESPACHO, TAQUILLERO, CONDUCTOR})

_ESQUEMA_BEARER = "bearer"


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Identidad resuelta a partir de un token Bearer válido."""

    nombre: str
    rol: str
    usuario: str = ""


def _no_autenticado(detalle: str) -> HTTPException:
    """Construye un ``401`` con el reto ``WWW-Authenticate`` exigido por RFC 6750."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detalle,
        headers={"WWW-Authenticate": "Bearer"},
    )


def _extraer_token(authorization: str | None) -> str:
    """Extrae el token de una cabecera ``Authorization: Bearer <token>``."""
    if not authorization:
        raise _no_autenticado(
            "Se requiere la cabecera Authorization con esquema Bearer"
        )

    esquema, separador, token = authorization.strip().partition(" ")
    if not separador or esquema.lower() != _ESQUEMA_BEARER or not token.strip():
        raise _no_autenticado(
            "La cabecera Authorization debe usar el esquema Bearer"
        )

    return token.strip()


def require_roles(*roles_permitidos: str) -> Callable[..., UsuarioAutenticado]:
    """Construye una dependencia FastAPI que exige uno de los roles indicados.

    - ``401`` si falta el token, no usa el esquema ``Bearer``, es inválido o
      está vencido.
    - ``403`` si el rol del token es desconocido o no está autorizado para el
      recurso.
    """
    permitidos = frozenset(roles_permitidos)
    desconocidos = permitidos - ROLES_VALIDOS
    if desconocidos:
        raise ValueError(f"Roles no definidos en el sistema: {sorted(desconocidos)}")

    def dependencia(
        authorization: str | None = Header(default=None, alias="Authorization"),
    ) -> UsuarioAutenticado:
        token = _extraer_token(authorization)

        try:
            datos = auth.verificar_token(token)
        except Exception as exc:  # firma inválida, expirado, formato corrupto...
            raise _no_autenticado("Token inválido o vencido") from exc

        if not isinstance(datos, dict):
            raise _no_autenticado("Token inválido o vencido")

        rol = str(datos.get("rol") or "").strip().upper()
        nombre = str(datos.get("nombre") or "").strip()
        usuario = str(datos.get("usuario") or "").strip()

        if not rol or not nombre:
            raise _no_autenticado("El token no contiene una identidad válida")

        if rol not in ROLES_VALIDOS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol '{rol}' no está autorizado: no existe en el sistema",
            )

        if rol not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol {rol} no está autorizado para este recurso",
            )

        return UsuarioAutenticado(nombre=nombre, rol=rol, usuario=usuario)

    return dependencia
