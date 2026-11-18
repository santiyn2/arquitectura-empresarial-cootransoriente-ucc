"""Cumplimiento de la Ley 1581 de 2012 (protección de datos personales).

Responsable: Santiago Escalante Meriño.
"""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone

AVISO_PRIVACIDAD_LEY_1581 = """
AVISO DE PRIVACIDAD — COOTRANSORIENTE TAYRONA S.A.S.

En cumplimiento de la Ley 1581 de 2012 y del Decreto 1377 de 2013,
Cootransoriente Tayrona informa al pasajero que los datos personales
suministrados (nombre, documento de identidad, ruta, asiento y condición de
menor de edad) serán tratados con las siguientes finalidades legítimas:

1. Expedición y control del tiquete de transporte de pasajeros.
2. Elaboración del manifiesto de pasajeros exigido por el Decreto 1079 de 2015.
3. Gestión de la póliza de seguro de accidentes en ruta.

El titular puede ejercer sus derechos de acceso, corrección, actualización,
supresión y revocatoria de la autorización (derechos ARCO) escribiendo a
protecciondatos@cootransorientetayrona.com.co. Los plazos legales de respuesta
son de 10 días hábiles para consultas y 15 días hábiles para reclamos.

La autorización de tratamiento es previa, expresa e informada. En el caso de
niños, niñas y adolescentes, la autorización debe ser otorgada por su
representante legal, conforme al artículo 7 de la Ley 1581 de 2012.
""".strip()

CANAL_CONTACTO_DATOS = "protecciondatos@cootransorientetayrona.com.co"

PLAZOS_ARCO = {
    "consultas": "10 días hábiles",
    "reclamos": "15 días hábiles",
}


def validar_consentimiento_datos(
    autorizacion: bool,
    es_menor: bool,
    representante_documento: str | None = None,
) -> bool:
    """Valida la autorización previa y expresa exigida por la Ley 1581.

    Args:
        autorizacion: ``True`` si el titular (o su representante legal) aceptó
            el aviso de privacidad y autorizó el tratamiento.
        es_menor: ``True`` si el pasajero es niño, niña o adolescente; en ese
            caso la autorización debe provenir de su representante legal y se
            debe registrar su documento.
        representante_documento: documento de identidad del representante legal.
            Obligatorio cuando ``es_menor`` es ``True``.

    Raises:
        ValueError: si no existe autorización de tratamiento de datos, o si el
            pasajero es menor de edad y no se aporta el documento de su
            representante legal (artículo 7 de la Ley 1581 de 2012).

    Returns:
        ``True`` cuando el consentimiento es válido.
    """
    if autorizacion is not True:
        raise ValueError(
            "Error Ley 1581 de 2012: Debe aceptar la autorización previa y "
            "expresa de tratamiento de datos personales para emitir el tiquete"
        )

    # Artículo 7 de la Ley 1581 de 2012: los niños, niñas y adolescentes solo
    # pueden autorizar el tratamiento de sus datos a través de su representante
    # legal, cuyo documento debe quedar registrado.
    if es_menor and not (representante_documento or "").strip():
        raise ValueError(
            "Error Ley 1581 de 2012, artículo 7: los menores de edad requieren "
            "la autorización de su representante legal; debe registrar el "
            "documento de identidad del representante"
        )

    return True


def registrar_auditoria(
    conn: sqlite3.Connection,
    accion: str,
    usuario: str,
    rol: str,
    detalle: str,
) -> int:
    """Inserta un registro inmutable de auditoría con marca de tiempo UTC.

    No hace ``commit``: la transacción la cierra el llamador para que la acción
    auditada y su evidencia se confirmen de forma atómica.

    Returns:
        El identificador del registro insertado en ``audit_logs``.
    """
    timestamp = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cursor = conn.execute(
        """
        INSERT INTO audit_logs (accion, usuario, rol, detalle, timestamp)
        VALUES (?, ?, ?, ?, ?)
        """,
        (accion, usuario, rol, detalle, timestamp),
    )
    return int(cursor.lastrowid)
