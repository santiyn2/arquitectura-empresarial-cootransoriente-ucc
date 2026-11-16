"""Control de acceso basado en roles (RBAC) para la API.

Los roles y la identidad llegan en las cabeceras ``X-User-Role`` y
``X-User-Name``. En producción estas cabeceras deben ser emitidas por el
proveedor de identidad o por un API Gateway que las valide criptográficamente.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Header, HTTPException, status

ADMIN_DESPACHO = "ADMIN_DESPACHO"
TAQUILLERO = "TAQUILLERO"
CONDUCTOR = "CONDUCTOR"

ROLES_VALIDOS = frozenset({ADMIN_DESPACHO, TAQUILLERO, CONDUCTOR})


@dataclass(frozen=True)
class UsuarioAutenticado:
    """Identidad mínima resuelta a partir de las cabeceras de confianza."""

    nombre: str
    rol: str


def require_roles(*roles_permitidos: str) -> Callable[..., UsuarioAutenticado]:
    """Construye una dependencia FastAPI que exige uno de los roles indicados.

    Retorna ``HTTP 401`` si faltan las cabeceras de identidad y ``HTTP 403`` si
    el rol no existe o no está autorizado para el endpoint.
    """
    permitidos = frozenset(roles_permitidos)
    desconocidos = permitidos - ROLES_VALIDOS
    if desconocidos:
        raise ValueError(f"Roles no definidos en el sistema: {sorted(desconocidos)}")

    def dependencia(
        x_user_role: str | None = Header(default=None, alias="X-User-Role"),
        x_user_name: str | None = Header(default=None, alias="X-User-Name"),
    ) -> UsuarioAutenticado:
        rol = (x_user_role or "").strip().upper()
        nombre = (x_user_name or "").strip()

        if not rol or not nombre:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Se requieren las cabeceras X-User-Role y X-User-Name",
            )

        if rol not in ROLES_VALIDOS:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Rol '{rol}' no reconocido por el sistema",
            )

        if rol not in permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"El rol {rol} no está autorizado para este recurso",
            )

        return UsuarioAutenticado(nombre=nombre, rol=rol)

    return dependencia
