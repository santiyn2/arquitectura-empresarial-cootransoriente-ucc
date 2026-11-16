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

> **Requisitos previos:** Git 2.40+, Python 3.11+, Node.js 20 LTS+, npm 10+.

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

### Comandos de arranque objetivo (al integrarse)

```bash
# API REST
source .venv/bin/activate
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000

# Portal web
cd src/frontend-web
npm install
npm run dev

# App móvil / PWA
cd src/mobile-app
npm install
npm run dev
```

| Servicio | URL local | Verificación |
|---|---|---|
| API REST | `http://localhost:8000` | `GET /health` y documentación interactiva OpenAPI/Swagger en `http://localhost:8000/docs` |
| Portal web | `http://localhost:5173` | Login con dos roles distintos |
| PWA | `http://localhost:5174` | Carga de manifiesto y validación QR en modo avión |

### Despliegue con Docker (objetivo)

```bash
docker compose up --build -d
docker compose ps
```

> El archivo `docker-compose.yml` se incorporará con la entrega del producto. El criterio de aceptación es que un jurado pueda clonar, ejecutar y abrir el sistema en **menos de 10 minutos**, sin pasos manuales ocultos.

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

La identidad se envía en las cabeceras `X-User-Role` y `X-User-Name`:

```bash
# Emitir un tiquete
curl -X POST http://localhost:8000/api/tiquetes \
  -H "Content-Type: application/json" \
  -H "X-User-Role: TAQUILLERO" \
  -H "X-User-Name: Maria Taquilla" \
  -d '{
    "pasajero_nombre": "Ana Maria Torres",
    "documento": "1087654321",
    "es_menor": false,
    "ruta": "Santa Marta - Palomino",
    "asiento": "14A",
    "autorizacion_ley1581": true
  }'

# Consultar auditoría (solo administración de despacho)
curl http://localhost:8000/api/admin/auditoria \
  -H "X-User-Role: ADMIN_DESPACHO" \
  -H "X-User-Name: Carlos Despacho"
```

Para arrancar la API:

```bash
uvicorn src.backend.main:app --reload --host 0.0.0.0 --port 8000
```

---

## Referencias

- Guía oficial del curso (documento entregado por la docente)
- Repositorio remoto: `https://github.com/santiyn2/arquitectura-empresarial-cootransoriente-ucc`