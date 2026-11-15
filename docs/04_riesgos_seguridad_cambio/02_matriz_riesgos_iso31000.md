# 6.5 Matriz de identificación, evaluación y mitigación de riesgos

- **Proyecto:** Transformación digital de Cootransoriente Tayrona — ruta Santa Marta–Palomino
- **Fase:** Fase 2, Transversal A (Seguridad y cumplimiento) y Fase 3 (Adquisición)
- **Responsable:** Santiago Escalante Meriño — Responsable 1: Personas y cumplimiento
- **Estándares:** ISO 31000:2018; COBIT 5 (ISACA, 2013); Ley 1581 de 2012
- **Fecha:** 15 de noviembre de 2026

---

## 1. Metodología de evaluación

La matriz prioriza los riesgos de la transformación digital de Cootransoriente Tayrona bajo ISO 31000:2018 (ISO, 2018) y COBIT 5 (ISACA, 2013). El nivel de riesgo se calcula como $\text{Nivel} = \text{Probabilidad} \times \text{Impacto}$ (ambas 1–5), con cuatro rangos de actuación: **Bajo (1–4): Aceptar**; **Medio (5–9): Monitorear**; **Alto (10–16): Mitigar antes de salir a vivo**; **Crítico (20–25): Plan de choque obligatorio**. La evaluación cubre continuidad, finanzas, cumplimiento, datos personales y reputación, tomando la dimensión de mayor severidad.

**Mapa de calor 5 × 5**

| P \ I | 1 | 2 | 3 | 4 | 5 |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **5** | 5 M | 10 A | 15 A | **20 C · R1, R2** | 25 C |
| **4** | 4 B | 8 M | 12 A | **16 A · R3** | 20 C |
| **3** | 3 B | 6 M | **9 M · R8** | **12 A · R6** | **15 A · R4, R5** |
| **2** | 2 B | 4 B | 6 M | 8 M | **10 A · R7** |
| **1** | 1 B | 2 B | 3 B | 4 B | 5 M |

---

## 2. Tabla 2: Matriz de riesgos de Cootransoriente Tayrona

| ID | Categoría | Descripción | P | I | Nivel | Mitigación | Responsable |
| :--- | :--- | :--- | :---: | :---: | :---: | :--- | :--- |
| **R1** | Humano/Operativo | Resistencia o boicot de conductores al control digital del recaudo (evasión actual 15–18 %). | 5 | 4 | **20 Crítico** | Plan de choque: incentivos por tiquete escaneado, socialización con Consejo y asamblea, auditoría cruzada de ocupación, tablero semanal, canal de denuncias. | Gerencia General y Oficial de Gestión del Cambio |
| **R2** | Continuidad/Técnico | Fallas de conectividad en puntos ciegos (Mendihuaca, Guachaca, Tayrona, Palomino) que impiden validar, sincronizar o emitir manifiesto. | 5 | 4 | **20 Crítico** | Plan de choque: app *offline-first* con cola IndexedDB/SQLite, manifiesto PDF local, QR sin red, reintentos idempotentes, pruebas en los 4 sectores. | Arquitecto de Soluciones |
| **R3** | Humano/Operativo | Curva de aprendizaje lenta de taquilleros al migrar de talonario a portal web; errores, filas y pérdida de recaudo. | 4 | 4 | **16 Alto** | Operación paralela 15 días, talleres con simulador, reconversión sin despidos, manuales de bolsillo, métricas por taquillero. | Oficial de Gestión del Cambio |
| **R4** | Seguridad/Legal | Filtración o pérdida de datos personales (cédulas, pasaportes, menores) bajo Ley 1581/2012; sanción y daño reputacional. | 3 | 5 | **15 Alto** | TLS 1.3 en tránsito, AES-256 en reposo, RBAC, enmascaramiento, auditoría inmutable, aviso de privacidad, protocolo de incidentes. | Oficial de Seguridad y Cumplimiento |
| **R5** | Continuidad | Caída del servidor en la nube o corrupción de BD: interrumpe venta, despacho, manifiesto y conciliación. | 3 | 5 | **15 Alto** | Backups cada 6 h en región secundaria, RPO ≤ 15 min, RTO ≤ 2 h, monitoreo, pruebas de restauración, redundancia. | Arquitecto de Soluciones y Proveedor Nube |
| **R6** | Adquisición/Contractual | *Vendor lock-in* y alzas unilaterales de proveedor de nube o pasarela de pagos. | 3 | 4 | **12 Alto** | Contenedores Docker, exportación BD en SQL/JSON/CSV, cláusula de portabilidad y salida asistida en SLA, proveedor alterno. | Analista Financiero y Contratación |
| **R7** | Normativo | Inmovilización o sanciones por inconsistencias en manifiesto electrónico en controles viales. | 2 | 5 | **10 Alto** | Validación obligatoria de campos antes de despachar, manifiesto firmado digital y disponible offline, checklist, plan documental. | Jefe de Despacho y Oficial de Cumplimiento |
| **R8** | Financiero/Operativo | Descuadres entre pagos digitales (QR/pasarela) y efectivo en taquilla. | 3 | 3 | **9 Medio** | Cierre de caja automático por turno con trazabilidad por usuario, arqueos sorpresivos, conciliación automática, reporte de anomalías. | Contador / Auditor Interno |

*Nota:* Evaluación de riesgo inherente (antes de controles). P = Probabilidad, I = Impacto, N = P × I.

---

## 3. Análisis de riesgos críticos y plan de seguimiento

La matriz arroja 2 riesgos críticos (R1 y R2), 5 altos y 1 medio; nivel promedio 14,6. R1 y R2 son condiciones **go/no-go** (Congreso de Colombia, 2012): sin adopción de conductores el recaudo digital no funciona, y sin modo *offline* la app falla justo donde más se necesita. Ambos exigen planes de choque con criterios de salida medibles (cobertura QR ≥ 90 %, evasión < 5 %, sincronización offline ≥ 99 %). Los 5 riesgos altos (R3–R7) deben tener mitigación verificada antes de producción: operación paralela y simulador para taquilleros, cifrado y RBAC para datos, backups probados con RPO/RTO, arquitectura portable y cláusulas de salida, y manifiesto validado y disponible offline. R8 se monitorea con cierre de caja automático y conciliación diaria.

**Indicadores principales de seguimiento (cadencia semanal en oleada 1, luego mensual):**

1. Tasa de evasión ≤ 2 % (pasajeros transportados vs. tiquetes válidos).
2. Cobertura de escaneo QR ≥ 95 %.
3. Sincronización offline ≥ 99 % (operaciones sin red que se sincronizan al recuperar señal).
4. Disponibilidad del servicio ≥ 99,5 % en horario operativo.
5. Cero incidentes graves de datos personales y cero rechazos de manifiesto en control vial.

Un riesgo crítico materializado se escala a Gerencia General en ≤ 24 h; si afecta datos personales, se activa el protocolo de incidentes legal. La aceptación de riesgo residual requiere firma del dueño del riesgo y del Gerente General.

---

## Referencias

Congreso de Colombia. (2012, 17 de octubre). *Ley 1581 de 2012, por la cual se dictan disposiciones generales para la protección de datos personales*. Diario Oficial No. 48.587. https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981

ISACA. (2013). *COBIT 5: A business framework for the governance and management of enterprise IT*.

ISO. (2018). *Risk management — Guidelines* (ISO 31000:2018). International Organization for Standardization. https://www.iso.org/standard/65694.html