# Fase 2 — Transversal A y Fase 3 — Sección 6.5: seguridad de la información y protección de datos personales (Ley 1581 de 2012)

- **Proyecto:** Transformación digital de Cootransoriente Tayrona — ruta Santa Marta–Palomino.
- **Fase del informe:** Fase 2 (Transversal A — Seguridad y protección de datos personales) y Fase 3 (Sección 6.5 — Seguridad de la información).
- **Responsable:** Santiago Escalante Meriño — Responsable 1: Personas y cumplimiento.
- **Marcos de referencia:** Ley 1581 de 2012 (Congreso de Colombia, 2012); Decreto 1074 de 2015 y Decreto 1079 de 2015 (Presidencia de la República de Colombia, 2015); ISO/IEC 27001:2022 (ISO/IEC, 2022); COBIT 5 (ISACA, 2013).
- **Fecha de elaboración:** 15 de noviembre de 2026.
- **Versión:** 1.0.
- **Documentos relacionados:** matriz de riesgos ISO 31000 (Tabla 2) y plan de gestión del cambio (Tabla 3 en adelante).

La numeración de tablas continúa la del informe consolidado; por eso este documento inicia en la Tabla 14.

---

## 1. Clasificación de datos personales tratados por el producto

El producto software —portal web de venta, aplicación móvil de validación y módulo de taquilla— captura, por cada pasajero, los siguientes datos: **nombre completo**; **tipo y número de documento de identidad** (CC, CE o pasaporte); **teléfono**; **correo electrónico**; y **ruta y asiento** asignado. Estos campos no son un exceso de diseño: cada uno sostiene una función operativa o una obligación legal del transportador.

La clasificación aplicada al tratamiento es la siguiente:

- **Datos identificativos (nombre y documento):** permiten individualizar al pasajero, validar que la persona que aborda es la titular del tiquete y evitar la suplantación en el control de embarque.
- **Datos de contacto (teléfono y correo):** habilitan la confirmación de la compra, el envío del tiquete electrónico y el contacto ante emergencias viales en la vía Santa Marta–Palomino.
- **Datos de viaje (ruta y asiento):** soportan la asignación de cupo, el control de ocupación y la conciliación entre tiquete y manifiesto.
- **Datos sensibles y de protección reforzada de menores de edad:** cuando el pasajero es un niño, niña o adolescente, el registro de su identidad y edad permite inferir su condición de menor, lo que constituye un dato de **protección reforzada** en los términos del Artículo 7 de la Ley 1581 de 2012 (Congreso de Colombia, 2012). En ese caso el tratamiento es obligatorio para la **póliza de seguro** y para el **manifiesto de transporte** exigido por el Decreto 1079 de 2015 (Presidencia de la República de Colombia, 2015), y se realiza con autorización del representante legal y bajo el principio del interés superior del menor.

El producto no captura datos de salud, biométricos, de orientación sexual ni de convicciones religiosas. La condición de menor no se infiere de un campo opcional: se deriva de la fecha de nacimiento o del documento aportado, y activa controles adicionales de acceso y de auditoría descritos en la sección 3.

---

## 2. Cumplimiento de la Ley 1581 de 2012 y del Decreto 1074 de 2015

### 2.1 Finalidad legítima y limitada

Los datos se tratan con una finalidad **exclusiva y declarada**: (a) emitir el tiquete y formalizar la relación de transporte; (b) generar el manifiesto obligatorio de pasajeros; (c) gestionar la cobertura de seguros exigida para la operación; y (d) contactar al pasajero o a su acudiente ante una emergencia vial. Cualquier uso distinto —mercadeo, analítica comercial o cesión a terceros no relacionados con el servicio— requiere una autorización separada y no se ejecuta en el MVP. El principio de finalidad del Artículo 4 de la Ley 1581 de 2012 se traduce en una regla de diseño: cada campo del formulario tiene un consumidor identificado en el modelo de datos y una justificación funcional o normativa.

### 2.2 Autorización previa, expresa e informada (Art. 9)

La autorización no se presume. En el **canal web**, el formulario incorpora un *checkbox* obligatorio y **no premarcado** que el pasajero debe seleccionar de forma consciente antes de habilitar el pago; si no lo marca, la transacción no continúa. En la **taquilla física**, el taquillero lee al pasajero el **Aviso de Privacidad corto**, que resume la finalidad, los derechos del titular, el canal de atención y la existencia de transferencia internacional, y solo después registra la venta.

En ambos canales, la base de datos almacena la evidencia de la autorización: la **marca de tiempo** (`timestamp`) del consentimiento, el **usuario taquillero** que la gestionó cuando aplica, la versión del aviso aceptado y el canal de origen. Esa trazabilidad convierte la autorización en una prueba verificable ante la Superintendencia de Industria y Comercio y ante una solicitud del propio titular, en lugar de una cláusula decorativa.

### 2.3 Atención de derechos ARCO (Arts. 14 y 15)

El titular puede conocer, actualizar, rectificar y suprimir sus datos, y revocar la autorización. Para ello se habilita un canal dedicado: **protecciondatos@cootransorientetayrona.com.co**, atendido por el área administrativa con registro de radicado. Los plazos aplicados son los legales: **10 días hábiles** para atender consultas y **15 días hábiles** para atender reclamos, con prórroga únicamente en los casos y con los avisos que la norma permite.

La supresión procede cuando no exista un deber legal o contractual de conservación. En el contexto del transporte, el tiquete y el manifiesto deben conservarse como soporte de la operación y de la póliza; por tanto, la solicitud de supresión se resuelve conservando el registro estrictamente necesario y anonimizando o bloqueando el resto, con constancia escrita al solicitante. La respuesta se emite por el mismo canal y queda auditada.

### 2.4 Transferencia internacional de datos (Art. 26)

La aplicación y la base de datos se alojan en servidores en la nube ubicados fuera de Colombia (por ejemplo, en Estados Unidos). Esa arquitectura es una transferencia internacional de datos y, por tanto, exige cumplir el Artículo 26 de la Ley 1581 de 2012. El cumplimiento se soporta en dos mecanismos complementarios:

1. **Acuerdo de Procesamiento de Datos (DPA)** firmado con el proveedor de nube, que incorpora cláusulas contractuales de seguridad, confidencialidad, notificación de incidentes, ubicación del tratamiento y obligaciones de devolución o eliminación al finalizar el servicio.
2. **Autorización expresa del pasajero** en el Aviso de Privacidad, que informa de forma clara que sus datos serán almacenados en servidores fuera del país y que la transferencia se realiza con fines exclusivamente operativos.

El DPA no reemplaza la autorización del titular ni la autorización lo reemplaza a él: el primero obliga al encargado, la segunda legitima el tratamiento frente al titular.

---

## 3. Controles técnicos de seguridad aplicados al producto software

Los controles del MVP se seleccionaron con base en los anexos de ISO/IEC 27001:2022 (ISO/IEC, 2022) y en los procesos de COBIT 5 (ISACA, 2013). La Tabla 14 los resume con su implementación concreta y su trazabilidad normativa.

**Tabla 14**

*Controles técnicos de seguridad implementados en el MVP*

| Control | Implementación en el MVP | Referencia ISO/IEC 27001:2022 | Proceso COBIT 5 |
|---|---|---|---|
| Autenticación segura | Contraseñas almacenadas con función de *hash* adaptativa (`bcrypt` o Argon2, con *salt* por usuario); sesiones mediante tokens JWT firmados y con expiración corta; bloqueo temporal tras intentos fallidos. | A.5.17, A.8.5 | DSS05.04 |
| Autorización por roles (RBAC) | Separación estricta de permisos entre *Administrador/Despachador*, *Taquillero* y *Conductor/Ayudante*; el conductor solo valida tiquetes y el taquillero no accede a configuración ni a reportes financieros. | A.5.15, A.8.2, A.8.3 | DSS05.04 |
| Cifrado en tránsito y en reposo | HTTPS obligatorio con TLS 1.3 y rechazo de conexiones inseguras; base de datos cifrada en reposo con AES-256; códigos QR firmados con HMAC para impedir su falsificación o reutilización. | A.8.24, A.8.20 | DSS05.02, DSS05.04 |
| Registro de auditoría (`audit_logs`) | Trazabilidad de quién crea, consulta, valida o anula un tiquete o un manifiesto, con usuario, fecha, hora, IP y acción; el registro es de solo adición y no admite edición desde la aplicación. | A.8.15, A.8.16 | DSS05.07, MEA02 |
| Manejo de secretos | Credenciales, llaves de firma y cadenas de conexión aisladas en variables de entorno (`.env`), excluidas del repositorio Git mediante `.gitignore`; rotación periódica y acceso restringido al equipo de despliegue. | A.5.17, A.8.9 | DSS05.04, DSS05.07 |

*Nota.* Elaboración propia con base en ISO/IEC 27001:2022 (ISO/IEC, 2022) y COBIT 5 (ISACA, 2013). Los controles se verifican en la matriz de riesgos (Tabla 2) y se refuerzan con la formación por rol del plan de gestión del cambio.

Estos cinco controles no agotan el universo de ISO/IEC 27001, pero cubren las amenazas de mayor probabilidad e impacto identificadas en la matriz de riesgos: acceso indebido a datos de pasajeros, suplantación de tiquetes, manipulación del manifiesto y fuga de credenciales. Su verificación se realiza antes de la salida a vivo y se repite en cada despliegue relevante.

---

## 4. Referencias

Congreso de Colombia. (2012, 17 de octubre). *Ley 1581 de 2012, por la cual se dictan disposiciones generales para la protección de datos personales*. Diario Oficial No. 48.587. https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=49981

ISACA. (2013). *COBIT 5: A business framework for the governance and management of enterprise IT*. ISACA.

ISO/IEC. (2022). *ISO/IEC 27001:2022. Information security, cybersecurity and privacy protection — Information security management systems — Requirements*. International Organization for Standardization.

Presidencia de la República de Colombia. (2015, 26 de mayo). *Decreto 1074 de 2015, por medio del cual se expide el Decreto Único Reglamentario del Sector Comercio, Industria y Turismo*. Diario Oficial No. 49.523. https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=76608

Presidencia de la República de Colombia. (2015, 26 de mayo). *Decreto 1079 de 2015, por medio del cual se expide el Decreto Único Reglamentario del Sector Transporte*. Diario Oficial No. 49.523. https://www.funcionpublica.gov.co/eva/gestornormativo/norma.php?i=77826
