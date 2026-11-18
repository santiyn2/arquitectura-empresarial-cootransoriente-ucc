"""Autenticación: hash de contraseñas, tokens firmados y QR firmados.

Solo usa la biblioteca estándar de Python:

* Contraseñas: ``scrypt`` con *salt* aleatorio por usuario.
* Sesión: token con formato JWT (HS256) y expiración.
* QR del tiquete: código firmado con HMAC-SHA256 para que no se pueda
  inventar ni alterar el número de tiquete ni el viaje.

El secreto se lee de la variable de entorno ``COOTRANSORIENTE_JWT_SECRET``.
Si no existe, se genera uno aleatorio al arrancar: sirve para pruebas y
desarrollo, pero los tokens y los QR dejan de valer al reiniciar. En el
despliegue siempre hay que definir la variable.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

ENV_SECRETO = "COOTRANSORIENTE_JWT_SECRET"
ENV_MINUTOS_TOKEN = "COOTRANSORIENTE_TOKEN_MINUTOS"
MINUTOS_TOKEN_POR_DEFECTO = 480  # un turno de 8 horas

_secreto_aleatorio: bytes | None = None


def _secreto() -> bytes:
    global _secreto_aleatorio
    valor = os.getenv(ENV_SECRETO)
    if valor:
        return valor.encode("utf-8")
    if _secreto_aleatorio is None:
        _secreto_aleatorio = secrets.token_bytes(32)
    return _secreto_aleatorio


def _b64(datos: bytes) -> str:
    return base64.urlsafe_b64encode(datos).rstrip(b"=").decode("ascii")


def _b64_decode(texto: str) -> bytes:
    return base64.urlsafe_b64decode(texto + "=" * (-len(texto) % 4))


# --------------------------------------------------------------------------
# Contraseñas
# --------------------------------------------------------------------------
_SCRYPT_N, _SCRYPT_R, _SCRYPT_P = 2**14, 8, 1


def hash_password(password: str) -> str:
    """Devuelve ``scrypt$N$r$p$salt$hash`` con un salt nuevo."""
    salt = secrets.token_bytes(16)
    derivado = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=32,
    )
    return f"scrypt${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64(salt)}${_b64(derivado)}"


def verify_password(password: str, almacenado: str) -> bool:
    """Compara una contraseña con su hash en tiempo constante."""
    try:
        esquema, n, r, p, salt, esperado = almacenado.split("$")
        if esquema != "scrypt":
            return False
        derivado = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64_decode(salt),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=32,
        )
        return hmac.compare_digest(derivado, _b64_decode(esperado))
    except (ValueError, TypeError):
        return False


# Hash de relleno: se usa cuando el usuario no existe, para que la respuesta
# tarde lo mismo y no se pueda adivinar qué usuarios existen.
HASH_RELLENO = hash_password("relleno-sin-uso")


# --------------------------------------------------------------------------
# Tokens de sesión (JWT HS256)
# --------------------------------------------------------------------------
def minutos_de_vida_token() -> int:
    try:
        return max(1, int(os.getenv(ENV_MINUTOS_TOKEN, MINUTOS_TOKEN_POR_DEFECTO)))
    except ValueError:
        return MINUTOS_TOKEN_POR_DEFECTO


def crear_token(nombre: str, rol: str, usuario: str | None = None) -> str:
    """Crea un token firmado con ``sub`` (usuario), ``nombre``, ``rol`` y ``exp``."""
    encabezado = {"alg": "HS256", "typ": "JWT"}
    cuerpo = {
        "sub": usuario or nombre,
        "nombre": nombre,
        "rol": rol,
        "exp": int(time.time()) + minutos_de_vida_token() * 60,
    }
    partes = [
        _b64(json.dumps(encabezado, separators=(",", ":")).encode()),
        _b64(json.dumps(cuerpo, separators=(",", ":"), ensure_ascii=False).encode()),
    ]
    firma = hmac.new(_secreto(), ".".join(partes).encode("ascii"), hashlib.sha256)
    return ".".join(partes + [_b64(firma.digest())])


def verificar_token(token: str) -> dict:
    """Valida firma y expiración. Lanza ``ValueError`` si algo falla."""
    try:
        enc_b64, cuerpo_b64, firma_b64 = token.split(".")
        encabezado = json.loads(_b64_decode(enc_b64))
        if encabezado.get("alg") != "HS256":
            raise ValueError("algoritmo no permitido")
        esperada = hmac.new(
            _secreto(), f"{enc_b64}.{cuerpo_b64}".encode("ascii"), hashlib.sha256
        ).digest()
        if not hmac.compare_digest(esperada, _b64_decode(firma_b64)):
            raise ValueError("firma inválida")
        cuerpo = json.loads(_b64_decode(cuerpo_b64))
    except (ValueError, TypeError, UnicodeError) as exc:
        raise ValueError("token inválido") from exc

    if int(cuerpo.get("exp", 0)) < int(time.time()):
        raise ValueError("token vencido")
    if not cuerpo.get("rol") or not cuerpo.get("nombre"):
        raise ValueError("token incompleto")
    return cuerpo


# --------------------------------------------------------------------------
# Código QR del tiquete
# --------------------------------------------------------------------------
PREFIJO_QR = "CT1"


def _firma_qr(tiquete_id: int, viaje_id: int) -> str:
    mensaje = f"qr:{tiquete_id}:{viaje_id}".encode("ascii")
    return hmac.new(_secreto(), mensaje, hashlib.sha256).hexdigest()[:20]


def firmar_qr(tiquete_id: int, viaje_id: int | None) -> str:
    """Código que se imprime en el QR: ``CT1.<tiquete>.<viaje>.<firma>``."""
    viaje = viaje_id or 0
    return f"{PREFIJO_QR}.{tiquete_id}.{viaje}.{_firma_qr(tiquete_id, viaje)}"


def verificar_qr(codigo: str) -> tuple[int, int] | None:
    """Devuelve ``(tiquete_id, viaje_id)`` si la firma es válida; si no, ``None``."""
    try:
        prefijo, tiquete, viaje, firma = codigo.strip().split(".")
        if prefijo != PREFIJO_QR:
            return None
        tiquete_id, viaje_id = int(tiquete), int(viaje)
    except (ValueError, AttributeError):
        return None
    if not hmac.compare_digest(firma, _firma_qr(tiquete_id, viaje_id)):
        return None
    return tiquete_id, viaje_id
