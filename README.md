# Sistema de Despacho y Boletería Digital – Cootransoriente Tayrona

**Universidad Cooperativa de Colombia · Campus Santa Marta**
**Programa de Ingeniería de Software**
**Electiva II: Arquitectura Empresarial de TI**
**Docente: Sabina Rada Mendoza · 2026-2**

---

## Transformación digital de Cootransoriente Tayrona

**Ruta: Santa Marta — Palomino**

*Reducción de tiempo de despacho de 4,5 min a 1,5 min y control de evasión en ruta del 15%‑18% al ≤2%.*

---

## Equipo y roles

| # | Integrante | Rol principal | Responsabilidades |
|---|---|---|---|
| 1 | Santiago Escalante Meriño | Oficial de Riesgos, Seguridad (Ley 1581) y Gestión del Cambio | Matriz de stakeholders, riesgos ISO 31000, ADKAR, plan de capacitación, seguridad y privacidad |
| 2 | Andrea Camila Mendoza Figueroa | Arquitecta de Negocio y Diagnóstico Empresarial | Evidencias primarias, entrevistas, observación, Canvas, BPMN AS-IS/TO-BE, capacidades y línea base |
| 3 | Luis Eduardo Arrieta Caballero | Arquitecto de Soluciones y Líder Técnico del Producto | Capas TO-BE, análisis de brechas, diagramas, decisiones de arquitectura, API, persistencia e integración |
| 4 | Juan Sebastián Laborde Escorcia | Analista Financiero, Adquisición (TCO) y Contratos (SLA) | TCO a 36 meses, CapEx/OpEx, cotizaciones, matriz build/buy/rent, SLA y presupuesto |

> **Regla de participación:** todos programan, todos documentan y todos sustentan. La nota individual se ajusta según la capacidad de explicar cualquier parte del trabajo y según la evidencia de commits en el repositorio.

---

## Estructura del repositorio

```text
Proyecto_final_TI/
├── docs/
│   ├── 01_diagnostico_negocio/          # Diagnóstico, Canvas, BPMN AS-IS/TO-BE
│   ├── 02_arquitectura_empresarial/     # Arquitectura TO-BE, brechas, diagramas
│   ├── 03_finanzas_adquisicion/         # TCO 36 meses, CapEx/OpEx, SLA, cotizaciones
│   ├── 04_riesgos_seguridad_cambio/     # Stakeholders, ISO 31000, ADKAR, Ley 1581
│   └── 05_anexos_entrega/               # Anexos A‑F, informe consolidado, presentación
├── src/
│   ├── backend/                         # API REST, RBAC, manifiestos, sync offline y auditoría
│   ├── frontend-web/                    # Portal web de taquilla y módulo administración/despacho
│   └── mobile-app/                      # App móvil/PWA para conductor/ayudante con QR y cola offline
├── tests/                               # Mínimo 5 pruebas automatizadas exigidas por la rúbrica
├── .gitignore
└── README.md
```

Los archivos `.gitkeep` preservan las carpetas mientras cada integrante agrega su contenido directamente sobre `main`.

---

## Instalación y despliegue local (menos de 10 minutos)

> **Requisitos previos:** Git 2.40+ y Python 3.11+. No se necesita Node.js ni npm: el portal y la app móvil son archivos estáticos que sirve la propia API. Docker es opcional.

```bash
# 1. Clonar el repositorio
git clone https://github.com/santiyn2/arquitectura-empresarial-cootransoriente-ucc.git
cd arquitectura-empresarial-cootransoriente-ucc

# 2. Entorno virtual y dependencias
python3 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements-dev.txt

# 3. Ejecutar la suite de pruebas
pytest -q
```

### Arranque local

```bash
# Con el entorno virtual activo (paso 2). Crea usuarios DEMO solo si se pide:
COOTRANSORIENTE_SEED_DEMO=1 uvicorn src.backend.main:app --host 0.0.0.0 --port 8000
# Windows (PowerShell):  $env:COOTRANSORIENTE_SEED_DEMO="1"; uvicorn src.backend.main:app --port 8000
```

| Servicio | URL local | Verificación |
|---|---|---|
| API REST | `http://localhost:8000` | `GET /health` y documentación OpenAPI en `http://localhost:8000/docs` |
| Portal web (taquilla y despacho) | `http://localhost:8000/portal/` | Ingresar como `taquilla` y como `admin` (dos roles) |
| App móvil / PWA (ayudante/conductor) | `http://localhost:8000/movil/` | Descargar manifiesto, activar modo avión y validar un QR |

**Usuarios de demostración** (solo con `COOTRANSORIENTE_SEED_DEMO=1`; **no usar en producción**):

| Usuario | Contraseña | Rol |
|---|---|---|
| `admin` | `Admin2026*` | `ADMIN_DESPACHO` |
| `taquilla` | `Taquilla2026*` | `TAQUILLERO` |
| `conductor` | `Conductor2026*` | `CONDUCTOR` |

Variables de entorno: `COOTRANSORIENTE_JWT_SECRET` (secreto de firma de sesiones y QR; si falta se genera uno aleatorio por arranque), `COOTRANSORIENTE_DB` (ruta del SQLite), `COOTRANSORIENTE_TOKEN_MINUTOS` (vida de la sesión, 480 por defecto).

### Despliegue con Docker

```bash
docker compose up --build -d
docker compose ps          # el servicio debe quedar "healthy"
# Portal: http://localhost:8000/portal/   ·   Móvil: http://localhost:8000/movil/
```

El compose usa un secreto de demostración y crea los usuarios de ejemplo; para otro entorno defina `COOTRANSORIENTE_JWT_SECRET` y `COOTRANSORIENTE_SEED_DEMO=0`. La base SQLite persiste en el volumen `datos`.

> La PWA pide cámara y service worker: el navegador solo los permite en `localhost` o HTTPS. Para probarla desde un teléfono real hace falta HTTPS (p. ej. un túnel o un proxy con certificado).

### Cómo usar el producto (flujo mínimo de demostración)

1. `admin` → *Flota*: agregar vehículo (placa, capacidad) → *Viajes*: programar un viaje con el conductor `conductor`.
2. `taquilla` → *Vender tiquete*: elegir viaje y asiento, leer el aviso de privacidad, marcar la autorización y emitir; se muestra el QR.
3. `admin` → *Viajes* → **Despachar**: se genera el manifiesto digital (409 si no hay tiquetes).
4. `conductor` en `/movil/`: *Descargar manifiesto* → *Escanear* (o escribir el código) → los abordajes quedan en cola y se sincronizan al haber señal; en *Pagos* registra cobros a bordo.
5. `admin` → *Viajes* → *Ver*: manifiesto y **conciliación** (esperado vs. recaudado). *Auditoría* muestra todo lo anterior.

---

## Flujo de trabajo Git (trabajo directo sobre `main`)

### Rama única

| Rama | Propósito | Regla |
|---|---|---|
| `main` | Única rama de trabajo y entregable | Todos hacen commits directamente sobre ella; no se crean ramas de features |

**Reglas de convivencia sobre `main`:**

1. Antes de empezar a trabajar: `git pull origin main`.
2. Commits **pequeños, frecuentes y con autoría propia** (cada quien sube con su propio usuario de GitHub).
3. No subir archivos ajenos a tu rol ni reescribir el historial (`--force` prohibido).
4. Si el push es rechazado, integrar con `git pull --rebase` y volver a intentar.
5. Usar la convención de commits `<tipo>(<alcance>): <descripción>`.

### Ciclo de trabajo

```bash
# 1. Actualizar main
git pull --ff-only origin main

# 2. Trabajar y confirmar cambios pequeños y verificables
git add docs/04_riesgos_seguridad_cambio/02_matriz_riesgos_iso31000.md
git commit -m "docs(riesgos): agregar matriz ISO 31000 con seis riesgos y tratamiento"

# 3. Publicar
git push origin main
```

### Verificación de participación

```bash
# Commits por autor
git shortlog -sne --all

# Historial lineal
git log --oneline --graph --decorate

# Commits de un integrante en una fecha
git log --author="Santiago Escalante" --since="2026-11-01" --oneline
```

---

## Seguridad, Ley 1581 y auditoría (Responsable 1)

### Cómo ejecutar las pruebas

```bash
# Desde la raíz del repositorio, con el entorno virtual activo
source .venv/bin/activate
python -m pip install -r requirements-dev.txt

# Toda la suite
pytest -q

# Solo las pruebas de seguridad, Ley 1581 y RBAC
pytest tests/test_seguridad_ley1581.py -v
```

La suite `tests/test_seguridad_ley1581.py` valida el aviso de privacidad y los
plazos ARCO, el bloqueo de tiquetes sin autorización, la emisión con
consentimiento y auditoría, y los permisos `TAQUILLERO`/`CONDUCTOR`/`ADMIN_DESPACHO`.
Cada prueba usa una base SQLite temporal y aislada.

### Endpoints de cumplimiento y auditoría

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| `GET` | `/api/privacidad` | Público | Aviso de privacidad vigente (Ley 1581 de 2012), canal de contacto y plazos ARCO: 10 días hábiles para consultas y 15 para reclamos. |
| `POST` | `/api/tiquetes` | `TAQUILLERO`, `ADMIN_DESPACHO` | Emite el tiquete. Exige `autorizacion_ley1581: true`; persiste `fecha_autorizacion` en UTC y registra la acción en `audit_logs`. Sin autorización responde `400 Bad Request` sin guardar datos. |
| `GET` | `/api/admin/auditoria` | Solo `ADMIN_DESPACHO` | Retorna los registros inmutables de `audit_logs`. `TAQUILLERO` y `CONDUCTOR` reciben `403 Forbidden`. |

La identidad se prueba con un token de sesión (`Authorization: Bearer <token>`) obtenido en `POST /api/auth/login`. *(Antes se enviaba en cabeceras `X-User-Role`/`X-User-Name`, que cualquiera podía falsificar; se reemplazó al implementar el login.)*

```bash
# Iniciar sesión (usuarios demo) y guardar el token
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"usuario":"taquilla","password":"Taquilla2026*"}' | python -c "import sys,json;print(json.load(sys.stdin)['access_token'])")

# Emitir un tiquete
curl -X POST http://localhost:8000/api/tiquetes \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "pasajero_nombre": "Ana Maria Torres",
    "documento": "1087654321",
    "es_menor": false,
    "ruta": "Santa Marta - Palomino",
    "asiento": "14A",
    "autorizacion_ley1581": true
  }'

# Consultar auditoría (requiere el token de un usuario ADMIN_DESPACHO)
curl http://localhost:8000/api/admin/auditoria \
  -H "Authorization: Bearer $TOKEN_ADMIN"
```


---

## Producto: API operativa, portal y app móvil (Responsable 3)

Pruebas: `pytest -q` ejecuta `tests/test_seguridad_ley1581.py` (Responsable 1) y `tests/test_producto.py` (sesión, RBAC, tiquetes con QR, despacho/manifiesto, abordajes idempotentes, pagos, conciliación y pantallas).

| Método | Endpoint | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/auth/login` | Público | Usuario y contraseña → token. 5 fallos seguidos bloquean la cuenta 5 min (429). |
| `GET`/`POST` | `/api/admin/usuarios` | `ADMIN_DESPACHO` | Listar / crear usuarios (contraseña con scrypt). |
| `GET`/`POST` | `/api/vehiculos` | `ADMIN_DESPACHO` | Flota. |
| `GET`/`POST` | `/api/viajes` · `GET /api/viajes/{id}` | Admin / taquilla / conductor (este solo ve los suyos) | Viajes y asientos ocupados. |
| `POST` | `/api/tiquetes` | `TAQUILLERO`, `ADMIN_DESPACHO` | Emite tiquete con QR firmado; asiento único por viaje (409), capacidad, menor con representante (Ley 1581 art. 7). |
| `GET` | `/api/tiquetes/{id}/qr.svg` | `TAQUILLERO`, `ADMIN_DESPACHO` | Imagen del QR. |
| `POST` | `/api/viajes/{id}/despacho` | `ADMIN_DESPACHO` | Despacha y genera el manifiesto (409 si ya salió o no hay tiquetes). |
| `GET` | `/api/viajes/{id}/manifiesto` | Admin / conductor del viaje | Manifiesto digital con los QR válidos. |
| `POST` | `/api/viajes/{id}/cierre` | `ADMIN_DESPACHO` | Cierra el viaje. |
| `POST` | `/api/abordajes/lote` | `CONDUCTOR` | Sincroniza abordajes escaneados; idempotente por `id_cliente`; responde aceptado/duplicado/rechazado por cada uno. |
| `POST` | `/api/pagos` | `CONDUCTOR`, `TAQUILLERO` | Registra recaudo (efectivo/digital); idempotente por `id_cliente`. |
| `GET` | `/api/viajes/{id}/conciliacion` | `ADMIN_DESPACHO` | Esperado vs. recaudado, abordajes y diferencia. |

**Limitaciones conocidas (honestas):** SQLite de un solo nodo; sesión por token sin revocación (expira a las 8 h); la PWA guarda la cola en `localStorage` y valida contra el manifiesto descargado (la firma del QR se verifica en el servidor al sincronizar); lectura de QR con la API `BarcodeDetector` (Chrome/Android; en otros navegadores queda la entrada manual); sin integración con pasarela de pago ni con el RNDC; interfaz web sin pruebas automatizadas de navegador.

---

## Referencias

- Guía oficial del curso (documento entregado por la docente)
- Repositorio remoto: `https://github.com/santiyn2/arquitectura-empresarial-cootransoriente-ucc`