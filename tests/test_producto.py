"""Pruebas del producto: sesión, viajes, despacho, abordajes por QR, pagos,
conciliación y pantallas estáticas. Responsable: Luis Arrieta."""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient  # noqa: E402

from src.backend import database  # noqa: E402
from src.backend.auth import firmar_qr, verificar_qr  # noqa: E402
from src.backend.main import app  # noqa: E402

client = TestClient(app)

ADMIN = ("admin", "Admin2026*")
TAQUILLA = ("taquilla", "Taquilla2026*")
CONDUCTOR = ("conductor", "Conductor2026*")


@pytest.fixture(autouse=True)
def base_aislada(tmp_path, monkeypatch):
    monkeypatch.setenv("COOTRANSORIENTE_SEED_DEMO", "1")
    monkeypatch.setattr(database, "DATABASE_PATH", tmp_path / "producto_test.db")
    database.init_db()
    yield


def _login(cred: tuple[str, str]) -> dict[str, str]:
    r = client.post("/api/auth/login", json={"usuario": cred[0], "password": cred[1]})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _viaje(capacidad: int = 2, tarifa: int = 25000) -> tuple[int, dict]:
    admin = _login(ADMIN)
    v = client.post("/api/vehiculos", json={"placa": "ABC123", "capacidad": capacidad}, headers=admin)
    assert v.status_code == 201, v.text
    r = client.post(
        "/api/viajes",
        json={
            "ruta": "Santa Marta - Palomino",
            "vehiculo_id": v.json()["id"],
            "conductor_usuario": "conductor",
            "salida_programada": "2026-11-20T06:30",
            "tarifa": tarifa,
        },
        headers=admin,
    )
    assert r.status_code == 201, r.text
    return r.json()["id"], admin


def _tiquete(viaje_id: int, asiento: str, documento: str = "10010001", **extra) -> dict:
    cuerpo = {
        "pasajero_nombre": "Ana Perez",
        "documento": documento,
        "es_menor": False,
        "asiento": asiento,
        "autorizacion_ley1581": True,
        "viaje_id": viaje_id,
        **extra,
    }
    r = client.post("/api/tiquetes", json=cuerpo, headers=_login(TAQUILLA))
    assert r.status_code == 201, r.text
    return r.json()


# --------------------------------------------------------------------- sesión
def test_health_responde_ok():
    r = client.get("/health")
    assert r.status_code == 200


def test_login_correcto_entrega_token_y_rol():
    r = client.post("/api/auth/login", json={"usuario": "admin", "password": "Admin2026*"})
    assert r.status_code == 200
    assert r.json()["rol"] == "ADMIN_DESPACHO"
    assert r.json()["token_type"] == "bearer"


def test_login_incorrecto_da_401_sin_revelar_si_existe_el_usuario():
    mal_clave = client.post("/api/auth/login", json={"usuario": "admin", "password": "x"})
    no_existe = client.post("/api/auth/login", json={"usuario": "nadie", "password": "x"})
    assert mal_clave.status_code == no_existe.status_code == 401
    assert mal_clave.json() == no_existe.json()


def test_cuenta_se_bloquea_tras_cinco_intentos_fallidos():
    for _ in range(5):
        assert client.post("/api/auth/login", json={"usuario": "taquilla", "password": "mala"}).status_code == 401
    r = client.post("/api/auth/login", json={"usuario": "taquilla", "password": "Taquilla2026*"})
    assert r.status_code == 429


def test_sin_token_o_con_token_alterado_da_401():
    assert client.get("/api/viajes").status_code == 401
    token = _login(ADMIN)["Authorization"]
    r = client.get("/api/viajes", headers={"Authorization": token[:-3] + "xxx"})
    assert r.status_code == 401


def test_rbac_taquillero_no_crea_vehiculos_ni_viajes():
    h = _login(TAQUILLA)
    assert client.post("/api/vehiculos", json={"placa": "XYZ987", "capacidad": 10}, headers=h).status_code == 403
    assert client.get("/api/admin/usuarios", headers=h).status_code == 403


# ------------------------------------------------------------ viajes y tiquetes
def test_vehiculo_duplicado_da_409():
    admin = _login(ADMIN)
    assert client.post("/api/vehiculos", json={"placa": "ABC123", "capacidad": 10}, headers=admin).status_code == 201
    assert client.post("/api/vehiculos", json={"placa": "abc 123", "capacidad": 10}, headers=admin).status_code == 409


def test_tiquete_asiento_repetido_da_409_y_capacidad_se_respeta():
    viaje_id, _ = _viaje(capacidad=1)
    t = _tiquete(viaje_id, "1")
    assert t["codigo_qr"].startswith("CT1.")
    otra = client.post(
        "/api/tiquetes",
        json={"pasajero_nombre": "Luis Diaz", "documento": "20020002", "es_menor": False,
              "asiento": "1", "autorizacion_ley1581": True, "viaje_id": viaje_id},
        headers=_login(TAQUILLA),
    )
    assert otra.status_code == 409


def test_menor_sin_representante_se_rechaza_y_con_representante_se_acepta():
    viaje_id, _ = _viaje()
    base = {"pasajero_nombre": "Nico Perez", "documento": "30030003", "es_menor": True,
            "asiento": "2", "autorizacion_ley1581": True, "viaje_id": viaje_id}
    h = _login(TAQUILLA)
    assert client.post("/api/tiquetes", json=base, headers=h).status_code == 400
    ok = client.post("/api/tiquetes", json={**base, "representante_documento": "10010001"}, headers=h)
    assert ok.status_code == 201


def test_qr_svg_solo_para_taquilla_o_admin():
    viaje_id, _ = _viaje()
    t = _tiquete(viaje_id, "1")
    r = client.get(f"/api/tiquetes/{t['id']}/qr.svg", headers=_login(TAQUILLA))
    assert r.status_code == 200
    assert "<svg" in r.text
    assert client.get(f"/api/tiquetes/{t['id']}/qr.svg", headers=_login(CONDUCTOR)).status_code == 403


def test_qr_firmado_detecta_alteraciones():
    codigo = firmar_qr(7, 3)
    assert verificar_qr(codigo) == (7, 3)
    assert verificar_qr(codigo.replace(".7.", ".8.")) is None
    assert verificar_qr("basura") is None


# ----------------------------------------------------------- despacho y manifiesto
def test_despacho_sin_tiquetes_da_409_y_con_tiquetes_genera_manifiesto():
    viaje_id, admin = _viaje()
    assert client.post(f"/api/viajes/{viaje_id}/despacho", headers=admin).status_code == 409
    _tiquete(viaje_id, "1")
    r = client.post(f"/api/viajes/{viaje_id}/despacho", headers=admin)
    assert r.status_code == 200
    assert r.json()["total_pasajeros"] == 1
    man = client.get(f"/api/viajes/{viaje_id}/manifiesto", headers=_login(CONDUCTOR))
    assert man.status_code == 200
    assert man.json()["pasajeros"][0]["codigo_qr"].startswith("CT1.")
    # ya despachado: no se despacha dos veces ni se venden más tiquetes
    assert client.post(f"/api/viajes/{viaje_id}/despacho", headers=admin).status_code == 409
    venta = client.post(
        "/api/tiquetes",
        json={"pasajero_nombre": "Tarde Llega", "documento": "90090009", "es_menor": False,
              "asiento": "2", "autorizacion_ley1581": True, "viaje_id": viaje_id},
        headers=_login(TAQUILLA),
    )
    assert venta.status_code == 409


# ---------------------------------------------------------------------- abordajes
def _despachado_con_dos() -> tuple[int, dict, list[dict]]:
    viaje_id, admin = _viaje(capacidad=2)
    ts = [_tiquete(viaje_id, "1", "10010001"), _tiquete(viaje_id, "2", "10020002")]
    assert client.post(f"/api/viajes/{viaje_id}/despacho", headers=admin).status_code == 200
    return viaje_id, admin, ts


def test_abordajes_en_lote_son_idempotentes():
    viaje_id, _, ts = _despachado_con_dos()
    h = _login(CONDUCTOR)
    lote = {"viaje_id": viaje_id, "abordajes": [
        {"id_cliente": "cliente-0001", "codigo_qr": ts[0]["codigo_qr"]}]}
    primero = client.post("/api/abordajes/lote", json=lote, headers=h).json()
    segundo = client.post("/api/abordajes/lote", json=lote, headers=h).json()
    assert primero["aceptado"] == 1
    assert segundo["duplicado"] == 1 and segundo["aceptado"] == 0


def test_abordaje_con_qr_invalido_de_otro_viaje_o_repetido_se_rechaza():
    viaje_id, _, ts = _despachado_con_dos()
    h = _login(CONDUCTOR)
    lote = {"viaje_id": viaje_id, "abordajes": [
        {"id_cliente": "cliente-0001", "codigo_qr": "CT1.1.1.firmafalsa"},
        {"id_cliente": "cliente-0002", "codigo_qr": firmar_qr(ts[0]["id"], 999)},
        {"id_cliente": "cliente-0003", "codigo_qr": ts[1]["codigo_qr"]},
        {"id_cliente": "cliente-0004", "codigo_qr": ts[1]["codigo_qr"]},
    ]}
    r = client.post("/api/abordajes/lote", json=lote, headers=h).json()
    assert r["aceptado"] == 1
    assert r["rechazado"] == 3
    motivos = [x["motivo"] for x in r["resultados"]]
    assert "QR no válido o alterado" in motivos
    assert "El tiquete es de otro viaje" in motivos
    assert "Este QR ya fue usado" in motivos


def test_abordajes_solo_conductor_y_solo_en_viaje_despachado():
    viaje_id, admin = _viaje()
    _tiquete(viaje_id, "1")
    cuerpo = {"viaje_id": viaje_id, "abordajes": [{"id_cliente": "cliente-0001", "codigo_qr": "x"}]}
    assert client.post("/api/abordajes/lote", json=cuerpo, headers=_login(CONDUCTOR)).status_code == 409
    assert client.post("/api/abordajes/lote", json=cuerpo, headers=admin).status_code == 403


# ------------------------------------------------------------- pagos y conciliación
def test_pago_con_mismo_id_cliente_no_duplica():
    viaje_id, _, ts = _despachado_con_dos()
    h = _login(CONDUCTOR)
    cuerpo = {"viaje_id": viaje_id, "valor": 25000, "medio": "efectivo",
              "id_cliente": "pago-cliente-1"}
    primero = client.post("/api/pagos", json=cuerpo, headers=h)
    segundo = client.post("/api/pagos", json=cuerpo, headers=h)
    assert primero.status_code == 201
    assert segundo.status_code == 200 and segundo.json()["duplicado"] is True


def test_conciliacion_detecta_faltante_y_luego_cuadra():
    viaje_id, admin, ts = _despachado_con_dos()
    h = _login(CONDUCTOR)
    client.post("/api/pagos", json={"viaje_id": viaje_id, "tiquete_id": ts[0]["id"],
                                    "valor": 25000, "medio": "digital"}, headers=h)
    r = client.get(f"/api/viajes/{viaje_id}/conciliacion", headers=admin).json()
    assert r["valor_esperado"] == 50000
    assert r["recaudado_total"] == 25000
    assert r["diferencia"] == -25000 and r["resultado"] == "faltante"
    client.post("/api/pagos", json={"viaje_id": viaje_id, "tiquete_id": ts[1]["id"],
                                    "valor": 25000, "medio": "efectivo"}, headers=h)
    r = client.get(f"/api/viajes/{viaje_id}/conciliacion", headers=admin).json()
    assert r["resultado"] == "cuadra"
    assert r["recaudado_efectivo"] == 25000 and r["recaudado_digital"] == 25000


def test_conductor_no_ve_viajes_de_otro_conductor():
    viaje_id, admin = _viaje()
    client.post("/api/admin/usuarios", headers=admin, json={
        "usuario": "conductor2", "nombre": "Otro Conductor",
        "password": "Clave12345*", "rol": "CONDUCTOR"})
    h2 = _login(("conductor2", "Clave12345*"))
    assert client.get("/api/viajes", headers=h2).json()["viajes"] == []
    assert client.get(f"/api/viajes/{viaje_id}", headers=h2).status_code == 403


def test_auditoria_registra_login_y_despacho():
    viaje_id, admin, _ = _despachado_con_dos()
    registros = client.get("/api/admin/auditoria", headers=admin).json()["registros"]
    assert {"LOGIN_OK", "DESPACHO_VIAJE", "EMISION_TIQUETE"} <= {r["accion"] for r in registros}


# ------------------------------------------------------------------- pantallas
@pytest.mark.parametrize("ruta", ["/portal/", "/movil/", "/movil/manifest.webmanifest", "/movil/sw.js"])
def test_pantallas_estaticas_se_sirven(ruta):
    assert client.get(ruta).status_code == 200
