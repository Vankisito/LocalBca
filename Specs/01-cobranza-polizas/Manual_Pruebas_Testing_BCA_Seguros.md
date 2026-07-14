# Manual de Pruebas — Módulo BCA Seguros (Interfaz de Usuario)

**Dirigido a:** Equipo de Testing / QA
**Módulo:** BCA Seguros — Gestión de Pólizas y Cobranza (`BCA_Seguros`)
**Versión del módulo:** 19.0.1.4.0
**Plataforma:** Odoo 19 Community
**Ámbito:** Pruebas funcionales desde la interfaz de usuario (UI). No requiere conocimientos técnicos ni acceso a la base de datos.

---

## 1. Cómo usar este manual

- Cada sección es un **bloque de pruebas** sobre una funcionalidad.
- Cada prueba tiene: **objetivo**, **precondiciones**, **pasos** y **resultado esperado**.
- Marca el resultado en la casilla:  `[ ] OK`   `[ ] Falla`   y anota observaciones.
- Si una prueba falla, registra el defecto usando la **plantilla de la Sección 14**.
- Ejecuta las secciones **en orden**: las pruebas de cobranza dependen de que existan pólizas, que a su vez dependen de que existan agentes y productos.

> **Importante:** No uses datos reales de clientes en el ambiente de pruebas. Usa datos ficticios (ej. "Cliente Prueba 01").

---

## 2. Glosario rápido

| Término | Significado |
|---|---|
| **Póliza** | Contrato de seguro. Tiene vigencia, periodicidad y genera recibos. |
| **Recibo** | Cada pago programado de una póliza (mensual, trimestral, etc.). |
| **Ramo** | Tipo de seguro: **Vida**, **GMM** (gastos médicos), **Autos**, **Daños**. |
| **Conducto de pago** | Medio por el que se cobra (cargo automático, tarjeta, agente directo). |
| **PCA** | Producción de Cartera Acumulada — el valor que se le acredita al agente cuando se paga un recibo. |
| **Promotoría** | Oficina/grupo al que pertenecen los agentes. |
| **Agente** | Vendedor. Estados: **Prospecto** → **Clave de Arranque** → **Clave Definitiva**. |
| **Bitácora** | Registro inmutable de cada importación de cobranza. |
| **Aseguradora** | Compañía emisora (MetLife, Qualitas). |

---

## 3. Acceso y roles

### 3.1 Roles a probar

El módulo define 5 roles. Pide al administrador **un usuario de prueba por cada rol** para validar permisos.

| Rol | Qué puede hacer |
|---|---|
| **Agente BCA** | Ver solo sus propias pólizas y recibos. |
| **Operador BCA** | Crear/editar pólizas, cargar portafolio, importar cobranza, mantener catálogo de productos. |
| **Líder BCA** | Todo lo del Operador + ver Reportes. |
| **Director Comercial BCA** | Todo lo anterior + Configuración (aseguradoras, promotorías, agentes, conductos, factores) + cancelar/anular recibos. |
| **Director BCA** | Acceso total. |

### 3.2 Prueba de acceso (hacer con cada rol)

**Objetivo:** Confirmar que el menú "BCA Seguros" se ve y que cada rol solo ve lo que le corresponde.

**Pasos:**
1. Inicia sesión con el usuario del rol.
2. Verifica que aparece el menú principal **BCA Seguros** (icono en el panel de apps).
3. Abre el menú y revisa qué submenús aparecen.

**Resultado esperado por rol:**

| Submenú | Agente | Operador | Líder | Dir. Comercial | Director |
|---|:---:|:---:|:---:|:---:|:---:|
| Pólizas → Pólizas | ✅ | ✅ | ✅ | ✅ | ✅ |
| Pólizas → Recibos | ✅ | ✅ | ✅ | ✅ | ✅ |
| Pólizas → Cargar Portafolio | ❌ | ✅ | ✅ | ✅ | ✅ |
| Cobranza | ❌ | ✅ | ✅ | ✅ | ✅ |
| Reportes | ❌ | ❌ | ✅ | ✅ | ✅ |
| Configuración | ❌ | ❌ | ❌ | ✅ | ✅ |

`[ ] OK   [ ] Falla` — Observaciones: ____________________

> Si no tienes los 5 usuarios, ejecuta las pruebas funcionales con un **Director** (ve todo) y haz al menos una verificación de permisos con un **Agente** (Sección 13).

---

## 4. Datos iniciales que ya trae el módulo

Al instalarse, el módulo carga datos base. Verifícalos antes de empezar (menú **Configuración**, solo Director/Dir. Comercial):

| Prueba | Pasos | Resultado esperado |
|---|---|---|
| Aseguradoras | Configuración → Aseguradoras | Aparece **MetLife** (y Qualitas si aplica). |
| Productos | Configuración → Productos de Seguro | Hay productos MetLife de Vida y GMM. |
| Conductos | Configuración → Conductos de Pago | Existen conductos MetLife (cargo automático, tarjeta, agente directo, etc.). |
| Factores PCA | Configuración → Factores PCA | Existen factores MetLife 2026. |

`[ ] OK   [ ] Falla` — Observaciones: ____________________

---

## 5. Reclutamiento → alta automática de agente/promotoría

El alta de agentes se hace desde el módulo de **Reclutamiento** (Recruitment), no a mano. Al contratar a un candidato, el sistema crea automáticamente el contacto.

### 5.1 Contratar un Agente

**Objetivo:** Verificar que al marcar un candidato como "Contratado" se crea un contacto tipo Agente ligado a su promotoría.

**Precondiciones:** Debe existir al menos una Promotoría (ver Sección 6.1 si no hay).

**Pasos:**
1. Abre el módulo **Reclutamiento**.
2. Crea un candidato nuevo en el puesto **"Reclutamiento de Agente"**.
3. Llena Nombre, Email y Teléfono.
4. En el campo **Promotoría destino**, selecciona una promotoría.
5. Mueve el candidato a la etapa **Contratado** (etapa marcada como "hired").

**Resultado esperado:**
- En el chatter del candidato aparece un mensaje: *"Se creó automáticamente el contacto BCA … (agente)"*.
- En **BCA Seguros → Configuración → Agentes** aparece el nuevo agente, con su promotoría asignada.

`[ ] OK   [ ] Falla` — Observaciones: ____________________

### 5.2 Validación: agente sin promotoría destino

**Objetivo:** El sistema debe impedir contratar a un agente sin promotoría.

**Pasos:**
1. Crea otro candidato en "Reclutamiento de Agente", **sin** llenar Promotoría destino.
2. Intenta moverlo a **Contratado**.

**Resultado esperado:** Mensaje de error: *"Para contratar a un agente debe especificar la Promotoría destino en el candidato."* No se crea el contacto.

`[ ] OK   [ ] Falla` — Observaciones: ____________________

### 5.3 Contratar una Promotoría

**Objetivo:** Verificar el alta de promotoría desde reclutamiento.

**Pasos:**
1. Crea un candidato en el puesto **"Captación de Promotoría"**.
2. Muévelo a **Contratado**.

**Resultado esperado:** Se crea un contacto tipo **Promotoría** colgando del holding Grupo BCA. Aparece en Configuración → Promotorías.

`[ ] OK   [ ] Falla` — Observaciones: ____________________

---

## 6. Configuración (Director Comercial / Director)

### 6.1 Crear una Promotoría manualmente

**Pasos:**
1. Configuración → **Promotorías** → Nuevo.
2. Nombre: "Promotoría Prueba". Guardar.

**Resultado esperado:** Se guarda como tipo Promotoría, colgando del holding.

`[ ] OK   [ ] Falla`

### 6.2 Crear un Agente y asignarle claves por aseguradora

**Objetivo:** Verificar el manejo de claves por aseguradora y el estado del agente.

**Pasos:**
1. Configuración → **Agentes** → Nuevo.
2. Nombre: "Agente Prueba 01". Asigna una Promotoría en "Pertenece a".
3. Abre la pestaña **BCA Seguros** → sección **Claves por Aseguradora**.
4. Agrega una línea: Aseguradora = MetLife, Clave de Agente = (ej. `19799`), Estado = **Clave Definitiva**, Fecha de licencia.
5. Guarda.

**Resultado esperado:**
- El campo **Estado del agente** (solo lectura) refleja **Clave Definitiva**.
- Verifica el badge de color: Definitiva (verde), Arranque (azul), Prospecto (gris).

`[ ] OK   [ ] Falla` — Observaciones: ____________________

> **Nota de negocio:** Solo la **Clave Definitiva** computa PCA y comisiones. Prospecto y Arranque pueden tener pólizas pero no generan PCA.

### 6.3 Revisar Productos, Conductos y Factores

**Pasos:** Abre cada submenú de Configuración (Productos de Seguro, Conductos de Pago, Factores PCA) y verifica que las listas cargan y se pueden abrir registros.

`[ ] OK   [ ] Falla`

---

## 7. Crear una póliza manualmente

### 7.1 Alta y confirmación de póliza de Vida

**Objetivo:** Crear una póliza, confirmarla y verificar que se genera el plan de recibos.

**Precondiciones:** Debe existir un Agente con Clave Definitiva (6.2), un producto Vida MetLife y un conducto.

**Pasos:**
1. Pólizas → **Pólizas** → Nuevo.
2. **Número de Póliza:** `MET-2026-00001`.
3. **Aseguradora:** MetLife → **Ramo:** Vida → **Producto:** elige un producto Vida (el listado se filtra por aseguradora y ramo).
4. **Contratante:** crea o elige un contacto de prueba.
5. **Agente:** "Agente Prueba 01". Verifica que **Promotoría** se llena sola (solo lectura).
6. **Vigencia:** Fecha inicio y fecha fin (ej. un año).
7. **Periodicidad:** Mensual.
8. **Conducto:** elige uno.
9. **Importes:** Prima anual (ej. 12000), moneda MXN.
10. Pestaña **Atributos Vida**: llena tipo de cobertura y temporalidad.
11. Pestaña **Beneficiarios**: agrega 1–2 beneficiarios cuyos porcentajes sumen 100%.
12. Guarda. La póliza queda en estado **Borrador**.
13. Presiona **Confirmar**.

**Resultado esperado:**
- El estado pasa a **Activa** (barra de estado arriba).
- En la pestaña **Recibos** se generan automáticamente los recibos según la periodicidad (12 recibos mensuales).
- El botón inteligente **Recibos** muestra el conteo.
- Los campos de la sección de producto/vigencia quedan en **solo lectura** tras confirmar.

`[ ] OK   [ ] Falla` — Observaciones: ____________________

### 7.2 Validación de beneficiarios (Vida)

**Pasos:** En una póliza de Vida, pon beneficiarios cuyos porcentajes **no** sumen 100% y guarda.

**Resultado esperado:** El sistema advierte / impide que el total sea distinto de 100%.

`[ ] OK   [ ] Falla`

### 7.3 Póliza de GMM

**Pasos:** Repite 7.1 con **Ramo: GMM**. Verifica que aparece la pestaña **Atributos GMM** (deducible, coaseguro, nivel hospitalario) y la sección de **Asegurados Adicionales** (dependientes con fecha de nacimiento).

`[ ] OK   [ ] Falla`

### 7.4 Cancelar una póliza

**Pasos:** En una póliza Activa, presiona **Cancelar** y confirma el diálogo.

**Resultado esperado:** Estado pasa a **Cancelada**, aparece la cinta roja "Cancelada". Los recibos ya pagados se conservan; no se generan nuevas cobranzas.

`[ ] OK   [ ] Falla`

### 7.5 Generar siguiente anualidad

**Pasos:** En una póliza Activa, presiona **Generar siguiente anualidad**.

**Resultado esperado:** Se generan los recibos del siguiente periodo de vigencia.

`[ ] OK   [ ] Falla`

### 7.6 Filtros y vista de lista de pólizas

**Pasos:** En la lista de Pólizas prueba los filtros (Activas, Borrador, Vencidas, Canceladas; Vida/GMM/Autos) y los agrupamientos (por Aseguradora, Ramo, Agente, Promotoría, Estado).

**Resultado esperado:** Los filtros funcionan; los colores de fila distinguen estados (activa=verde, borrador=azul, vencida=naranja, cancelada=gris).

`[ ] OK   [ ] Falla`

---

## 8. Crear póliza desde un Lead (CRM)

**Objetivo:** Verificar el puente CRM → Póliza.

**Pasos:**
1. Abre **CRM**, crea una oportunidad/lead.
2. En la pestaña **Datos de Seguro**: elige un Producto de Seguro (verifica que **Ramo** y **Aseguradora** se autollenan), prima estimada y periodicidad.
3. Lleva el lead a una etapa **Ganada**.
4. Presiona el botón **Generar Póliza** (arriba) y confirma.

**Resultado esperado:**
- Se abre el formulario de una **nueva póliza** con los datos precargados (contratante, aseguradora, producto, prima, periodicidad, y el agente = vendedor del lead).
- Si intentas generar póliza en un lead **no ganado**, sale error: *"Solo se puede generar póliza desde un lead ganado."*

`[ ] OK   [ ] Falla` — Observaciones: ____________________

---

## 9. Recibos y registro de pagos

### 9.1 Registrar el pago de un recibo (manual)

**Objetivo:** Verificar el pago de un recibo y el congelamiento de la PCA.

**Pasos:**
1. Pólizas → **Recibos** (filtro por defecto: Pendientes). Abre un recibo pendiente de la póliza creada.
2. Llena **Fecha de pago** y **Conducto** (obligatorios).
3. Presiona **Registrar Pago** y confirma el diálogo.

**Resultado esperado:**
- Estado pasa a **Pagado** (verde).
- Aparece la sección **PCA congelada** con **PCA aplicada** y **factor aplicado** (solo lectura).
- Aparece la **Foto inmutable**: agente y promotoría con que se acreditó el pago.
- Los datos del pago ya no se pueden editar.

`[ ] OK   [ ] Falla` — Observaciones: ____________________

> **Verificación PCA:** Si el recibo es de un agente con **Clave Definitiva**, la PCA debe ser mayor a 0. Si el agente es Prospecto/Arranque, debe quedar en 0 con un motivo de exclusión.

### 9.2 Cancelar un pago (solo Director / Director Comercial)

**Pasos:** En un recibo **Pagado**, presiona **Cancelar Pago** y confirma.

**Resultado esperado:** El recibo vuelve a **Pendiente**; se limpian PCA, conducto y fecha de pago. (El botón solo es visible para Director y Director Comercial.)

`[ ] OK   [ ] Falla`

### 9.3 Anular un recibo (solo Director / Director Comercial)

**Pasos:** En un recibo **Pendiente**, presiona **Anular Recibo** y confirma.

**Resultado esperado:** Estado pasa a **Cancelado** (cinta roja). No se cobrará.

`[ ] OK   [ ] Falla`

### 9.4 Filtros de recibos

**Pasos:** Prueba filtros Pendientes / Pagados / Cancelados / "Pagados este año" y agrupar por Póliza, Estado, Agente, Promotoría, Conducto.

`[ ] OK   [ ] Falla`

---

## 10. Carga masiva de Portafolio (.xlsx)

Sirve para dar de alta muchas pólizas de golpe desde una plantilla Excel. Menú: **Pólizas → Cargar Portafolio** (Operador o superior).

### 10.1 Descargar la plantilla

**Pasos:**
1. Pólizas → **Cargar Portafolio**.
2. Selecciona **Aseguradora** (MetLife).
3. Presiona **Descargar plantilla**.

**Resultado esperado:** Se descarga un archivo `.xlsx` con hojas **VIDA** y **GMM**, encabezados en la fila 2 y filas de ejemplo desde la fila 4.

`[ ] OK   [ ] Falla`

### 10.2 Validar un archivo correcto

**Pasos:**
1. Llena la plantilla con 2–3 pólizas de prueba. Columnas obligatorias: número de póliza (`Póliza` en VIDA / `Poliza actual` en GMM), `Producto`, `Clave de Agente`, `Nombre del Contratante`, `Moneda` (MXN/USD), `Fecha inicio Vigencia`, `Fecha Fin Vigencia` (dd/mm/aaaa), `Frecuencia de Pago` (Mensual/Trimestral/Semestral/Anual).
2. Usa un **Producto** y una **Clave de Agente** que **ya existan** en MetLife.
3. Adjunta el archivo en **Archivo** y presiona **Validar**.

**Resultado esperado:**
- Aparece la sección **Resumen**: total de filas, creadas, actualizadas, rechazadas.
- Aparece un **reporte HTML** con el detalle por fila.
- Aún **no** se han grabado las pólizas (es una vista previa).

`[ ] OK   [ ] Falla` — Observaciones: ____________________

### 10.3 Grabar

**Pasos:** Tras validar sin errores graves, presiona **Grabar** y confirma.

**Resultado esperado:** Las pólizas validadas se crean/actualizan y aparecen en la lista de Pólizas.

`[ ] OK   [ ] Falla`

### 10.4 Validar archivo con errores

**Pasos:** Carga una plantilla con una fila que use un **Producto inexistente** o una **Clave de Agente inexistente**.

**Resultado esperado:** Esas filas se reportan como **Rechazadas** con el motivo; las válidas se pueden grabar igual.

`[ ] OK   [ ] Falla`

---

## 11. Importar Cobranza Diaria (.csv)

Aplica pagos masivos a recibos pendientes desde un archivo de la aseguradora. Menú: **Cobranza → Importar Cobranza** (Operador o superior).

### 11.1 Descargar plantilla

**Pasos:**
1. Cobranza → **Importar Cobranza**.
2. Selecciona **Aseguradora** y **Ramo** (Vida o GMM — las columnas difieren).
3. Presiona **Descargar plantilla**.

**Resultado esperado:** Se descarga un `.csv` con los encabezados del ramo seleccionado en la primera fila.

`[ ] OK   [ ] Falla`

### 11.2 Procesar cobranza

**Pasos:**
1. Llena el `.csv`: separador coma, fechas `dd/mm/aaaa`, montos con punto decimal (`1234.56`), moneda MXN/USD.
2. Usa números de póliza que existan y tengan recibos **pendientes**.
3. Selecciona Aseguradora + Ramo, adjunta el archivo y presiona **Procesar** (confirma el diálogo).

**Resultado esperado:**
- Los pagos se aplican a los recibos pendientes en orden **FIFO** (el más antiguo primero).
- Se genera una **Bitácora de Importación** (se abre o aparece en Cobranza → Bitácoras).
- Los recibos afectados pasan a **Pagado** con su PCA congelada.

`[ ] OK   [ ] Falla` — Observaciones: ____________________

### 11.3 Casos especiales en cobranza

| Caso | Cómo probarlo | Resultado esperado |
|---|---|---|
| Póliza inexistente | Pon un número de póliza que no exista | La fila se marca **No encontrada** (advertencia), no aborta el proceso. |
| Conducto sin coincidencia | Usa un conducto desconocido | **Advertencia**, no aborta. |
| Anulación (solo GMM) | Fila con estatus `anulado`/`cancelado` | La fila se **omite** (regla R-COB-01). |
| Clave de agente con ceros | Clave `19799` vs `000019799` | Debe resolver el agente correctamente (ignora ceros a la izquierda). |

`[ ] OK   [ ] Falla` — Observaciones: ____________________

---

## 12. Bitácoras de Importación (inmutabilidad)

**Objetivo:** Verificar que las bitácoras son un registro inmutable y auditable.

**Pasos:**
1. Cobranza → **Bitácoras de Importación**. Abre la bitácora generada en la Sección 11.
2. Revisa los **Totales**: total de filas, recibos aplicados, anulaciones ignoradas, pólizas no encontradas, errores, PCA total de la sesión.
3. Abre la pestaña **Líneas** y revisa el detalle (cada fila con su marca: aplicado/error/no encontrada/anulado, con colores).
4. Verifica que puedes descargar el **archivo adjunto** original.
5. **Intenta editar o borrar** la bitácora.

**Resultado esperado:**
- La cinta dice **Inmutable**.
- No es posible crear, editar ni borrar bitácoras desde la UI (formulario de solo lectura).

`[ ] OK   [ ] Falla` — Observaciones: ____________________

---

## 13. Reportes

**Pasos:** Líder o superior → menú **Reportes**.

**Resultado esperado:** El menú existe para Líder y superiores. *(Nota: los reportes de PCA/productividad están en desarrollo — Etapa 9. Verifica con el responsable qué reportes deben estar disponibles en la versión que estás probando y documenta lo que veas.)*

`[ ] OK   [ ] Falla` — Observaciones: ____________________

---

## 14. Pruebas de seguridad / permisos (rol Agente)

**Objetivo:** Confirmar que un Agente solo ve **sus** datos y no puede hacer operaciones de Operador/Director.

**Pasos (con usuario rol Agente):**
1. Abre **Pólizas → Pólizas**. Verifica que solo aparecen las pólizas donde él es el agente.
2. Verifica que **NO** aparecen los menús: Cargar Portafolio, Cobranza, Reportes, Configuración.
3. Abre un recibo pagado: verifica que **NO** ve los botones "Cancelar Pago" ni "Anular Recibo".

**Resultado esperado:** El agente tiene acceso restringido conforme a la tabla de la Sección 3.

`[ ] OK   [ ] Falla` — Observaciones: ____________________

---

## 15. Resumen de cobertura (checklist final)

| # | Bloque | Estado |
|---|---|:---:|
| 3 | Acceso y roles | ☐ |
| 4 | Datos iniciales | ☐ |
| 5 | Reclutamiento → alta de agente/promotoría | ☐ |
| 6 | Configuración (promotorías, agentes, claves) | ☐ |
| 7 | Pólizas manuales (Vida/GMM, confirmar, cancelar) | ☐ |
| 8 | Póliza desde Lead (CRM) | ☐ |
| 9 | Recibos y pagos (PCA, cancelar, anular) | ☐ |
| 10 | Carga masiva de Portafolio (.xlsx) | ☐ |
| 11 | Importar Cobranza Diaria (.csv) | ☐ |
| 12 | Bitácoras (inmutabilidad) | ☐ |
| 13 | Reportes | ☐ |
| 14 | Seguridad / permisos (Agente) | ☐ |

---

## 16. Plantilla para reportar defectos

Copia este bloque por cada falla encontrada:

```
ID del defecto:        BCA-___
Sección del manual:    (ej. 9.1 Registrar pago)
Rol con que se probó:  (Agente / Operador / Líder / Dir. Comercial / Director)
Severidad:             Crítica / Alta / Media / Baja
Resumen:               (una línea)

Pasos para reproducir:
  1.
  2.
  3.

Resultado esperado:
Resultado obtenido:

Datos de prueba usados: (número de póliza, archivo, etc.)
Evidencia:              (captura de pantalla / archivo adjunto)
Navegador / fecha:
```

### Criterios de severidad sugeridos
- **Crítica:** bloquea el flujo (no se puede pagar, importar o crear póliza) o corrompe datos.
- **Alta:** funcionalidad importante falla pero hay alternativa.
- **Media:** error de validación, cálculo menor o permiso mal aplicado.
- **Baja:** texto, etiqueta, formato visual.

---

*Fin del manual. Ante cualquier comportamiento no descrito aquí, repórtalo como observación con captura de pantalla.*
