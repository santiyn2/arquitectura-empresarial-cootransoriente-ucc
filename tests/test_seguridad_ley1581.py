"""Pruebas de seguridad, Ley 1581 de 2012 y control de acceso RBAC.

Responsable: Santiago Escalante Meriño (Responsable 1).
"""

from __future__ import annotations

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Aísla la base de datos antes de importar la aplicación.
_BOOTSTRAP_DIR = Path(tempfile.mkdtemp(prefix="cootransoriente-ley1581-"))
os.environ["COOTRANSORIENTE_DB"] = str(_BOOTSTRAP_DIR / "bootstrap.db")

from fastapi.testclient import TestClient  # noqa: E402

from src.backend import database  # noqa: E402
from src.backend.main import app  # noqa: E402


client = TestClient(app)


@pytest.fixture(autouse=True)
def base_de_datos_aislada(tmp_path, monkeypatch):
    """Crea un SQLite limpio para cada prueba."""
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "cootransoriente_test.db")
    database.init_db()
    yield


def _headers(rol: str, usuario: str = "Usuario Prueba") -> dict[str, str]:
    return {"X-User-Role": rol, "X-User-Name": usuario}


def _payload_tiquete(**overrides) -> dict:
    datos = {
        "pasajero_nombre": "Ana María Torres",
        "documento": "1087654321",
        "es_menor": False,
        "ruta": "Santa Marta — Palomino",
        "asiento": "14A",
        "autorizacion_ley1581": True,
    }
    datos.update(overrides)
    return datos


def _contar(tabla: str) -> int:
    conn = database.get_connection()
    try:
        return int(conn.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()[0])
    finally:
        conn.close()


def test_obtener_aviso_privacidad():
    respuesta = client.get("/api/privacidad")

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["ley"] == "Ley 1581 de 2012"
    assert "10" in datos["plazos_arco"]["consultas"]
    assert "15" in datos["plazos_arco"]["reclamos"]
    assert "protecciondatos@cootransorientetayrona.com.co" in datos["aviso_privacidad"]
    assert "Decreto 1079 de 2015" in datos["aviso_privacidad"]
    assert "póliza de seguro" in datos["aviso_privacidad"]


def test_bloquear_tiquete_sin_autorizacion_ley1581():
    respuesta = client.post(
        "/api/tiquetes",
        json=_payload_tiquete(autorizacion_ley1581=False),
        headers=_headers("TAQUILLERO", "Maria Taquilla"),
    )

    assert respuesta.status_code == 400
    assert "Ley 1581 de 2012" in respuesta.json()["detail"]
    assert _contar("tiquetes") == 0
    assert _contar("audit_logs") == 0


def test_emitir_tiquete_con_autorizacion_y_auditoria():
    respuesta = client.post(
        "/api/tiquetes",
        json=_payload_tiquete(),
        headers=_headers("TAQUILLERO", "Maria Taquilla"),
    )

    assert respuesta.status_code == 201
    tiquete = respuesta.json()
    assert tiquete["autorizacion_ley1581"] is True
    assert tiquete["creado_por"] == "Maria Taquilla"

    fecha = datetime.fromisoformat(tiquete["fecha_autorizacion"])
    assert fecha.tzinfo is not None
    assert fecha.utcoffset().total_seconds() == 0

    conn = database.get_connection()
    try:
        fila = conn.execute(
            "SELECT autorizacion_ley1581, fecha_autorizacion FROM tiquetes WHERE id = ?",
            (tiquete["id"],),
        ).fetchone()
        auditoria = conn.execute(
            "SELECT accion, usuario, rol, detalle, timestamp FROM audit_logs"
        ).fetchall()
    finally:
        conn.close()

    assert fila is not None
    assert fila["autorizacion_ley1581"] == 1
    assert fila["fecha_autorizacion"] == tiquete["fecha_autorizacion"]
    assert len(auditoria) == 1
    assert auditoria[0]["accion"] == "EMISION_TIQUETE"
    assert auditoria[0]["usuario"] == "Maria Taquilla"
    assert auditoria[0]["rol"] == "TAQUILLERO"
    assert "tiquete_id" in auditoria[0]["detalle"]
    assert datetime.fromisoformat(auditoria[0]["timestamp"]).tzinfo is not None


def test_rbac_bloquear_taquillero_en_auditoria():
    for rol in ("TAQUILLERO", "CONDUCTOR"):
        respuesta = client.get(
            "/api/admin/auditoria",
            headers=_headers(rol, "Usuario No Autorizado"),
        )

        assert respuesta.status_code == 403
        assert "no está autorizado" in respuesta.json()["detail"]


def test_rbac_permitir_admin_en_auditoria():
    emision = client.post(
        "/api/tiquetes",
        json=_payload_tiquete(asiento="2C"),
        headers=_headers("ADMIN_DESPACHO", "Carlos Despacho"),
    )
    assert emision.status_code == 201

    respuesta = client.get(
        "/api/admin/auditoria",
        headers=_headers("ADMIN_DESPACHO", "Carlos Despacho"),
    )

    assert respuesta.status_code == 200
    datos = respuesta.json()
    assert datos["total"] == 1
    assert datos["registros"][0]["accion"] == "EMISION_TIQUETE"
    assert datos["registros"][0]["rol"] == "ADMIN_DESPACHO"
