# 1.3 Análisis y Gestión de Stakeholders: Matriz de Poder e Interés

## Introducción

En el contexto de la transformación digital de las organizaciones de transporte terrestre de pasajeros, como la Cooperativa de Transportadores del Oriente de la Magdalena (Cootransoriente Tayrona) —que opera la ruta estratégica entre Santa Marta y Palomino—, la gestión efectiva de los actores involucrados (stakeholders) resulta un factor determinante para el éxito o el fracaso de la arquitectura empresarial propuesta. La implementación de nuevas capacidades tecnológicas (como pasarelas de pago digital, sistemas de despacho automatizados y control de flota en la nube) altera de forma directa las rutinas operativas, los flujos de información y las relaciones de poder existentes. Como señalan **Ross, Weill y Robertson (2006)**, la gobernanza de TI requiere un alineamiento estricto entre los objetivos estratégicos de la empresa y la participación activa de los líderes y operativos, asegurando que las decisiones sobre digitalización cuenten con el respaldo y la adopción necesarios en todos los niveles jerárquicos. Asimismo, la perspectiva de la arquitectura empresarial defendida por **Lankhorst (2017)** subraya que una empresa no es meramente un conjunto de sistemas técnicos, sino un sistema socio-técnico complejo donde las personas, los procesos y las tecnologías interactúan permanentemente. Por tanto, identificar, clasificar y gestionar las expectativas de los grupos de interés permite mitigar resistencias al cambio, anticipar conflictos operacionales derivados de los dolores actuales (como los tiempos de abordaje de 4.5 minutos por pasajero y el desfase de 15% a 18% en el recaudo manual) y canalizar el apoyo institucional requerido para la transición hacia el modelo TO-BE.

---

## Tabla 1: Matriz de Identificación y Clasificación de Stakeholders

| ID | Actor / Rol | Tipo | Poder (1-5) | Interés (1-5) | Expectativa frente al sistema TO-BE | Actitud Esperada |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| **S1** | Gerente General y Consejo de Administración | Interno | 5 | 5 | Maximizar la rentabilidad operativa, reducir el desfase de recaudo (15%-18% actual) a menos del 2%, garantizar la transparencia financiera y cumplir con la normatividad de transporte. | Favorable / Proactivo |
| **S2** | Conductores asociados y asalariados | Interno | 4 | 4 | Reducir la manipulación de efectivo durante la conducción, mejorar la agilidad en el abordaje y contar con herramientas de navegación y despacho confiables sin sobrecarga de tareas. | Neutral / Inicialmente escéptica (requiere gestión) |
| **S3** | Ayudantes de bus (Auxiliares de ruta) | Interno | 2 | 4 | Claridad en las funciones de validación de tiquetes digitales y pago sin contacto, manteniendo la estabilidad de sus incentivos o remuneración diaria. | Resistente al cambio (temor a pérdida de control informal) |
| **S4** | Taquilleros (Terminal de Transporte Santa Marta) | Interno | 2 | 4 | Simplificación en la emisión de tiquetes mediante POS integrados, reducción de filas en taquilla y sincronización en tiempo real con la disponibilidad de asientos. | Resistente al cambio (temor a automatización de su rol) |
| **S5** | Despachadores de ruta | Interno | 3 | 4 | Automatización del control de tiempos de salida desde Santa Marta y Palomino, eliminando planillas manuales y agilizando el despacho de la flota. | Favorable |
| **S6** | Contador y Auditor interno | Interno | 3 | 4 | Reportes financieros automatizados, conciliación diaria de pasarelas de pago y trazabilidad fiscal estricta conforme a la normatividad DIAN. | Favorable / Colaborativo |
| **S7** | Pasajeros (Turistas, estudiantes y trabajadores) | Externo | 1 | 2 | Reducir el tiempo de abordaje (actualmente en 4.5 min/pasajero), aceptar múltiples medios de pago (tarjetas, códigos QR, efectivo) y mejorar la predictibilidad de los horarios. | Favorable / Indiferente a la arquitectura interna |
| **S8** | Superintendencia de Transporte y Policía de Carreteras | Externo | 5 | 2 | Cumplimiento normativo, reportes en tiempo real de operación vehicular, seguridad en las vías y formalización de la operación de transporte. | Neutral / Exigente regulador |
| **S9** | Proveedor de infraestructura en la nube y pasarela de pagos | Externo | 4 | 2 | Integración técnica fluida, cumplimiento de acuerdos de nivel de servicio (SLA), seguridad de datos bajo Ley 1581 de 2012 y sostenibilidad del modelo de licenciamiento. | Favorable / Socio estratégico |

---

## Análisis de la Matriz Poder–Interés por Cuadrantes

El análisis de la matriz de poder e interés permite estructurar la estrategia de gestión del cambio y gobernanza para Cootransoriente Tayrona, dividiendo a los actores en cuatro cuadrantes operativos:

### Cuadrante I: Gestionar de cerca (Alto Poder, Alto Interés)
* **Actores incluidos:** S1 (Gerente General y Consejo de Administración) y S2 (Conductores asociados y asalariados).
* **Estrategia de gestión:** Representan el núcleo decisorio y operativo del negocio. Para **S1**, se requiere un reporte ejecutivo continuo de indicadores clave de desempeño (KPIs), ROI de la transformación digital y control de riesgos financieros. Para **S2**, dada su resistencia inicial y su alto impacto en la operación diaria, se implementarán talleres participativos, incentivos por adopción exitosa del sistema de recaudo digital y capacitación práctica en campo, asegurando que perciban la tecnología como un facilitador de su labor y seguridad.

### Cuadrante II: Mantener satisfechos (Alto Poder, Bajo Interés)
* **Actores incluidos:** S8 (Superintendencia de Transporte y Policía de Carreteras) y S9 (Proveedor de infraestructura en la nube y pasarela de pagos).
* **Estrategia de gestión:** Tienen alta capacidad de incidencia regulatoria o técnica, pero bajo interés operativo cotidiano en los detalles internos de la cooperativa. La estrategia consiste en mantener canales formales de comunicación orientados al cumplimiento normativo y contractual. Para **S8**, reportes automáticos y transparentes de operación. Para **S9**, seguimiento estricto a los SLAs de disponibilidad, ciberseguridad y soporte técnico.

### Cuadrante III: Mantener informados (Bajo Poder, Alto Interés)
* **Actores incluidos:** S3 (Ayudantes de bus), S4 (Taquilleros), S5 (Despachadores de ruta) y S6 (Contador/Auditor interno).
* **Estrategia de gestión:** Son actores directamente afectados por la digitalización en su rutina diaria, aunque con menor poder de veto corporativo. Requieren comunicación constante, boletines informativos, mesas de ayuda técnicas y programas de capacitación formativa (modelo ADKAR) para reducir la incertidumbre, mitigar el temor a la obsolescencia de roles y garantizar una transición fluida hacia el sistema TO-BE.

### Cuadrante IV: Monitorear (Bajo Poder, Bajo Interés)
* **Actores incluidos:** S7 (Pasajeros turistas, estudiantes y trabajadores).
* **Estrategia de gestión:** Este grupo agrupa a los usuarios finales del servicio de transporte. Su nivel de poder e interés institucional en la arquitectura empresarial es bajo, aunque su satisfacción es la razón de ser del negocio. La estrategia se limita a la difusión pública de las mejoras en el servicio (tiempos de viaje más cortos, agilidad en el abordaje) mediante campañas de comunicación visual en terminales y buses, monitoreando su retroalimentación a través de canales de PQR digitales.

---

## Referencias

* Lankhorst, M. (2017). *Enterprise Architecture at Work: Modelling, Communication and Analysis* (4th ed.). Springer. https://doi.org/10.1007/978-3-662-53933-0
* Ross, J. W., Weill, P., & Robertson, D. C. (2006). *Enterprise Architecture as Strategy: Creating a Foundation for Business Execution*. Harvard Business Press.
