# Manual de Capacitación a Usuario — Módulo BCA Seguros

**Plataforma:** Odoo 19 Community
**Módulo:** BCA Seguros — Gestión de Pólizas y Cobranza
**Audiencia:** Operadores, Líderes, Dirección, Gerentes de Promotoría y Agentes de Grupo BCA
**Propósito:** Documento base para diseñar la capacitación a usuarios finales (sesiones presenciales, guías rápidas, material de onboarding).
**Versión:** 1.0 — base inicial

> **Cómo usar este documento.** Es la materia prima para armar la capacitación. Las secciones 1–6 cubren lo que el usuario **puede hacer hoy** en el sistema. La sección 9 describe funciones **en desarrollo** que se incorporarán por etapas; inclúyalas solo como anticipo, no como práctica guiada todavía.

---

## 1. Introducción

### 1.1 ¿Qué es BCA Seguros?

Es el módulo que reemplaza las hojas de cálculo manuales con las que hoy se gestiona la operación de seguros de Grupo BCA. Centraliza en un solo lugar:

- El **catálogo de pólizas** y sus recibos de pago.
- El **registro de cobranza** (qué recibos se pagaron, cuándo y por qué medio).
- El cálculo de la **Prima Computable (PCA)** — el indicador de productividad sobre el que se liquidan comisiones.
- La **estructura organizacional** de la red: BCA → promotorías afiliadas → agentes.

### 1.2 ¿Qué es Grupo BCA? (contexto que todo usuario debe entender)

BCA es una **promotoría de promotorías**: agrupa bajo su paraguas a varias promotorías más pequeñas con sus agentes. El ingreso de BCA **no es la prima** que paga el cliente (esa va a la aseguradora), sino las **comisiones, premios y bonos** que la aseguradora paga sobre el volumen y la calidad de la cartera.

La cadena de valor que el sistema modela:

```
Cliente paga prima → Aseguradora cobra → Aseguradora libera comisión sobre la PCA
                                                  ↓
                                    BCA recibe y administra
                                                  ↓
                          Distribuye entre: Promotoría · Agente · BCA
```

### 1.3 Glosario rápido (memorizar antes de operar)

| Término | Qué significa |
|---|---|
| **Póliza** | Contrato entre el cliente (contratante) y la aseguradora. Vive años. |
| **Recibo** | Fracción de la prima anual de una póliza, correspondiente a un periodo. Es la unidad que se cobra. |
| **Prima Neta** | Monto base del recibo, sin impuestos ni recargos. Base del cálculo de PCA. |
| **Prima Total** | Lo que efectivamente paga el cliente (neta + recargos + impuestos). |
| **PCA (Prima Computable)** | Prima Neta ajustada por un factor de la aseguradora. Base para liquidar comisiones. |
| **Pagado Hasta** | Fecha hasta la cual la póliza está cubierta por pagos efectivos. Métrica crítica de vigencia. |
| **FIFO** | Regla de cobranza: siempre se paga primero el recibo pendiente **más antiguo**. |
| **Conducto** | Vía de pago (tarjeta, cargo automático, CLABE, etc.). |
| **Ramo** | Familia de producto: **Vida**, **GMM** (Gastos Médicos Mayores) o **Autos**. |
| **Promotoría afiliada** | Promotoría pequeña integrada bajo BCA, con su propia red de agentes. |
| **Aseguradora** | Compañía emisora. En v1.0: MetLife (Vida + GMM) y Qualitas (Autos). |

---

## 2. Acceso y roles

El sistema asigna a cada usuario un **rol** que define qué puede ver y hacer. Nadie opera sin un rol asignado.

| Rol | Quién lo usa | Qué puede hacer |
|---|---|---|
| **Agente BCA** | Agente vendedor | Consulta **sus propias** pólizas y recibos. No ve datos de otros agentes ni de otras promotorías. No importa archivos ni edita catálogos. |
| **Operador BCA** | Personal administrativo | Da de alta y edita pólizas, registra pagos, mantiene el catálogo de productos. No cancela pagos ni ve el factor PCA aplicado en detalle de auditoría. |
| **Líder BCA** | Dirección operativa | Todo lo del Operador + bitácoras de importación y reportes consolidados de toda la red. (Hereda los permisos del Operador.) |
| **Director Comercial BCA** | Dirección comercial | Todo lo del Líder + **cancelar pagos**, **anular recibos**, editar factores PCA y esquemas de comisión. |
| **Director BCA** | Dueño/CEO | Acceso completo: todo lo anterior + gestión de promotorías, agentes y usuarios. |

**Reglas de permiso clave que conviene anticipar en la capacitación:**

- **Cancelar un pago** o **anular un recibo**: exclusivo de **Director Comercial** y **Director General**. El botón ni siquiera aparece para los demás roles.
- Un **Agente** solo ve lo suyo; un **Gerente de Promotoría** solo ve su red — nunca otras promotorías.
- El campo **"Pagado Hasta" es de solo lectura para todos**, incluido el Director. Solo se mueve como consecuencia de un pago.

---

## 3. Navegación general

Todo el módulo vive bajo el menú principal **BCA Seguros**. La estructura se adapta al rol (cada usuario ve solo los menús a los que tiene acceso):

```
BCA Seguros
├── Pólizas
│   ├── Pólizas        ← alta y gestión de pólizas
│   └── Recibos        ← cobranza recibo por recibo
├── Cobranza
│   └── Bitácoras de Importación   ← auditoría de cargas (Operador+)
├── Reportes           ← PCA y productividad (Líder+) · en desarrollo
└── Configuración      ← catálogos (Director Comercial+)
    ├── Aseguradoras
    ├── Promotorías
    ├── Agentes
    ├── Productos de Seguro
    ├── Conductos de Pago
    └── Factores PCA
```

**Conceptos de la interfaz de Odoo que el usuario debe conocer:**

- **Vista de lista** (varios registros en tabla) y **vista de formulario** (un registro en detalle). Se alterna con un clic.
- **Filtros y agrupaciones**: la barra de búsqueda superior permite filtrar (ej. "Activas", "Pendientes") y agrupar (ej. "Por agente", "Por aseguradora").
- **Botones de acción** (arriba a la izquierda del formulario, ej. "Confirmar", "Registrar Pago") y la **barra de estado** (arriba a la derecha, muestra el ciclo de vida).
- **Botones inteligentes** (esquina superior derecha del formulario, ej. "Recibos", "Pólizas"): atajos con contadores que abren registros relacionados.

---

## 4. Datos maestros (Configuración)

Antes de operar pólizas, los catálogos deben estar poblados. Estos los mantiene principalmente Dirección/Director Comercial; el Operador mantiene productos.

### 4.1 Aseguradoras
`Configuración → Aseguradoras`. Cada aseguradora es un contacto de tipo **Aseguradora** con su **Código de Aseguradora** (clave interna que conecta con sus reglas de PCA y formatos de archivo). Iniciales: **MetLife** (Vida + GMM) y **Qualitas** (Autos).

### 4.2 Promotorías afiliadas
`Configuración → Promotorías`. Cada promotoría es un contacto tipo **Promotoría** que cuelga del **Holding** (Grupo BCA). Representa una red de agentes.

### 4.3 Agentes
`Configuración → Agentes`. Cada agente es un contacto tipo **Agente** que pertenece (campo **"Pertenece a"**) a **exactamente una promotoría**. Datos clave:

- **Estado del agente**: tiene tres niveles de carrera — **Prospecto** (en reclutamiento, sin clave asignada), **Clave de Arranque** (la aseguradora le dio clave inicial, sin certificar) y **Clave Definitiva** (certificado). **Solo Clave Definitiva computa** para PCA y comisiones; Prospecto y Clave de Arranque pueden tener pólizas asignadas pero **no computan**. Este estado es de **solo lectura** en el contacto: se calcula a partir de las Claves por Aseguradora (lo gestiona Reclutamiento, no se edita a mano aquí).
- **Claves por Aseguradora**: un agente puede tener una clave —y un estado de carrera— distinto en cada aseguradora (p. ej. Clave Definitiva en MetLife y Clave de Arranque en Qualitas); se capturan en la pestaña correspondiente con su fecha de clave definitiva.

> **Regla organizacional:** un agente debe tener parent de tipo Promotoría, y una promotoría parent de tipo Holding. El sistema lo valida al guardar.

### 4.4 Contratantes (clientes finales)
Se gestionan como contactos tipo **Contratante**. En la pestaña **"BCA Seguros"** del contacto se capturan:

- **Datos demográficos**: fecha de nacimiento, estado civil, género. (El **RFC** va en el campo estándar `NIF/VAT`; el domicilio en los campos estándar de dirección.)
- **Referencias de pago** (Vida MetLife): prima básica TRAD, fondos variables/fijos, PPR, CPEA.

El contacto del contratante muestra **botones inteligentes** con el número de pólizas y recibos asociados.

### 4.5 Productos de seguro
`Configuración → Productos de Seguro`. Catálogo de productos por aseguradora y ramo (ej. TempoLife, TotalLife, EducaLife en Vida). Lo mantiene el Operador a medida que las aseguradoras publican productos nuevos.

### 4.6 Conductos de pago
`Configuración → Conductos de Pago`. Cada conducto tiene un **nombre visible** y el **código exacto** tal como aparece en los archivos de la aseguradora, además de su aseguradora y estado activo/inactivo. Ejemplos MetLife: `CARGOS AUTOMÁTICOS`, `AGENTE DIRECTO` (Vida); `TARJ.CRED.`, `TAR DEBITO`, `CLABE`, `AMEX` (GMM).

### 4.7 Factores PCA
`Configuración → Factores PCA`. Tabla de multiplicadores por aseguradora, año, ramo y producto. Ejemplo Vida MetLife 2026: Universales 100% MXN/100% USD; TempoLife 100% MXN/80% USD; EducaLife 100% MXN/70% USD. Para GMM el factor depende de coaseguro y deducible.

> **Importante:** editar un factor **no recalcula** recibos ya pagados. La PCA queda **congelada** al momento del pago (ver §7).

---

## 5. Gestión de Pólizas

`BCA Seguros → Pólizas → Pólizas`

### 5.1 Anatomía de una póliza

Una póliza agrupa: identificación (número único por aseguradora), partes (contratante, asegurado, agente — que arrastra su promotoría), términos financieros (prima anual, fraccionada, suma asegurada, periodicidad, moneda), vigencia (inicio, fin, **Pagado Hasta**) y atributos propios del ramo.

### 5.2 Alta manual de una póliza (paso a paso)

1. Clic en **Nuevo**.
2. Capturá el **Número de Póliza** (ej. `MET-2026-00001`). Es único por aseguradora.
3. **Aseguradora y producto** (funciona en cascada):
   - Elegí la **Aseguradora**.
   - Elegí el **Ramo** (Vida / GMM / Autos).
   - El campo **Producto** se filtra automáticamente para mostrar solo los productos de esa aseguradora y ramo.
   - Opcional: **Plan** y **Póliza Origen** (si es renovación o conversión).
4. **Asignación organizacional**:
   - **Contratante** (cliente).
   - **Asegurado** (solo Vida; suele ser el mismo contratante).
   - **Agente** — al elegirlo, la **Promotoría** se completa sola (solo lectura).
5. **Vigencia y periodicidad**: fecha de emisión, inicio, fin, **periodicidad** (mensual/trimestral/semestral/anual), conducto de cobro. La fecha de fin se sugiere automáticamente.
6. **Importes**: moneda (MXN/USD), prima anual, prima fraccionada, recargo, suma asegurada.
7. Según el ramo, completá la pestaña correspondiente:
   - **Atributos Vida**: tipo de cobertura, temporalidad en años, aportación adicional, coberturas adicionales.
   - **Atributos GMM**: deducible, coaseguro, nivel hospitalario.
   - **Beneficiarios** (Vida): agregá beneficiarios con su parentesco y porcentaje. **La suma debe ser exactamente 100%** para poder confirmar.
8. Guardá. La póliza queda en estado **Borrador**.

### 5.3 Confirmar la póliza y generar el plan de pagos

Con la póliza en Borrador, presioná **Confirmar**. Esto:

- Cambia el estado a **Activa**.
- **Genera automáticamente los recibos** del primer año según la periodicidad (mensual → 12, trimestral → 4, semestral → 2, anual → 1).
- Valida que, si hay beneficiarios, sumen 100%.

Los recibos aparecen en la pestaña **Recibos** de la póliza. Los años siguientes se generan solos a medida que se pagan los recibos, o manualmente con el botón **Generar siguiente anualidad**.

> Una vez que una póliza tiene recibos **pagados**, el sistema **no permite regenerar** el plan de pagos (protege el historial).

### 5.4 Ciclo de vida de la póliza

```
Borrador  →  Activa  →  Vencida
                  ↓
              Cancelada
```

- **Confirmar**: Borrador → Activa (genera recibos).
- **Cancelar**: la póliza pasa a Cancelada. Los recibos pagados se conservan (auditoría), pero no se generan nuevas cobranzas. Pide confirmación.
- Los campos de definición (aseguradora, producto, fechas, importes) quedan **bloqueados** una vez confirmada.

### 5.5 "Pagado Hasta" (concepto crítico)

Es la fecha hasta la cual la póliza está efectivamente cubierta por pagos. **Nadie puede editarlo a mano** — ni Operador, ni Líder, ni Director. Solo avanza cuando se registra un pago, y solo retrocede si se cancela un pago. Es la fuente de verdad de la vigencia operativa.

### 5.6 Cambio de agente e historial

Si una póliza cambia de agente, el sistema conserva el **historial completo** (agente y promotoría anterior y nueva, fecha, motivo y quién lo hizo). Las pólizas históricas siguen acreditadas a la promotoría original para efectos de liquidación. El historial es visible en la pestaña **Historial de Agentes** y en el botón inteligente correspondiente.

---

## 6. Recibos y Cobranza

`BCA Seguros → Pólizas → Recibos`

### 6.1 ¿Qué es un recibo y qué estados tiene?

Un recibo es una fracción de la prima de una póliza para un periodo. Estados:

| Estado | Color | Significado |
|---|---|---|
| **Pendiente** | Amarillo | Generado pero aún no cobrado. |
| **Pagado** | Verde | Cobro registrado; PCA congelada. |
| **Cancelado** | Gris | Anulado, no se cobrará. |

### 6.2 Registrar un pago (recibo por recibo)

1. Abrí el recibo **Pendiente** (desde la lista de Recibos o desde la pestaña Recibos de la póliza).
2. Completá los **Datos del Pago**:
   - **Fecha de Pago** (obligatoria).
   - **Conducto** (obligatorio en el flujo manual).
   - **Folio de Endoso** (solo GMM, opcional).
   - Ajustá la **Prima Total** si el cliente pagó un monto con recargos.
3. Presioná **Registrar Pago** y confirmá.

Al registrar el pago, el sistema:
- Cambia el estado a **Pagado**.
- **Congela la PCA y el factor aplicado** (quedan de solo lectura para siempre).
- Toma una **foto inmutable** del agente y promotoría al momento del pago.
- Actualiza **"Pagado Hasta"** de la póliza.
- Si era el último recibo de la anualidad, **genera la siguiente anualidad** automáticamente.

### 6.3 Regla FIFO (importantísima)

Cuando una póliza tiene varios recibos pendientes, **siempre se paga primero el más antiguo**. El sistema impide saltarse recibos: si intentás pagar uno fuera de orden, avisa cuál debe pagarse antes. Esto mantiene íntegro el "Pagado Hasta" y refleja la lógica de la aseguradora.

### 6.4 Cancelar un pago (solo Director / Director Comercial)

El botón **Cancelar Pago** deshace un cobro: el recibo vuelve a **Pendiente**, se limpian fecha, conducto y PCA, y "Pagado Hasta" se recalcula hacia atrás. Solo puede revertirse el **último** recibo pagado (regla FIFO inversa). El botón solo aparece para Director y Director Comercial.

### 6.5 Anular un recibo (solo Director / Director Comercial)

El botón **Anular Recibo** marca un recibo Pendiente como **Cancelado** (nunca se cobrará). Si el recibo ya está pagado, primero hay que cancelar el pago.

### 6.6 Buscar y agrupar recibos

La lista de recibos abre por defecto filtrada en **Pendientes**. Se puede filtrar por Pagados, Cancelados o "Pagados este año", y agrupar por póliza, estado, agente, promotoría o conducto — útil para revisar productividad y cobranza.

---

## 7. PCA — Prima Computable (concepto)

### 7.1 Qué es

La PCA es el **corazón económico** del sistema. No es lo que pagó el cliente: es la **Prima Neta ajustada por un factor** que define la aseguradora:

```
PCA del recibo = Prima Neta × Factor de Ajuste
```

### 7.2 Reglas que el usuario debe conocer

- **Solo los recibos pagados generan PCA.** Un recibo pendiente tiene PCA = 0.
- **Inmutabilidad:** la PCA y el factor se **congelan al momento del pago**. Si la aseguradora cambia su tabla de factores el año siguiente, los recibos ya pagados **no se recalculan**. Esto garantiza reportes y liquidaciones estables y auditables.
- **Solo agentes con licencia computan.** Las pólizas de agentes en estado Prospecto no entran en reportes de PCA ni comisiones.
- **Exclusiones (PCA = 0):** aportaciones adicionales en productos capitalizables, coberturas individuales de accidentes/invalidez, Vida con temporalidad menor a 10 años, y GMM con coaseguro ≤ 5%.

> **Nota para la capacitación (estado actual):** el **cálculo automático del factor PCA** está en proceso de habilitación (ver §9). Hasta que se active la tabla de factores definitiva, un pago registrado puede mostrar PCA en 0 con la nota correspondiente. El **flujo de registro de pago funciona** desde ya; la cifra de PCA se completará al activar los calculadores.

---

## 8. Bitácoras de importación

`BCA Seguros → Cobranza → Bitácoras de Importación`

Cada sesión de carga de cobranza queda registrada de forma **permanente** (no se puede editar ni borrar, ni siquiera el administrador), con: quién y cuándo ejecutó, aseguradora y ramo, nombre de archivo, conteos (pagos exitosos, anulaciones ignoradas, pólizas no encontradas, errores), PCA total de la sesión y el detalle línea por línea de las excepciones.

**Códigos de marca que aparecen en la bitácora:**

| Marca | Significado |
|---|---|
| `[ANULADO]` | Anulación ignorada (no es error). |
| `[NO ENCONTRADA]` | La póliza no existe o no está activa. |
| `[SIN RECIBO]` | La póliza no tiene recibos pendientes (deduplicación FIFO). |
| `[ADVERTENCIA]` | No crítico (conducto desconocido, diferencia menor). |
| `[ERROR]` | Fila no procesada por fallo técnico. |
| `[INFO]` | Evento informativo (ej. tipo de cambio aplicado). |

---

## 9. Funcionalidades en desarrollo (anticipo del roadmap)

Estas funciones forman parte del alcance del proyecto pero **aún no están disponibles para operar**. Inclúyalas en la capacitación solo como anticipo:

- **Cobranza masiva diaria (CSV).** Carga de los archivos diarios de la aseguradora (MetLife entrega Vida/LSP y GMM/GCAYE) que liquidan automáticamente los recibos por FIFO, aplican PCA y generan la bitácora. *(Hoy la cobranza se hace recibo por recibo, §6.)*
- **Carga masiva del portafolio.** Importación en bloque de pólizas desde hoja de cálculo (hojas Vida/GMM/Autos) para el arranque o la incorporación de nuevas promotorías.
- **Cálculo automático de PCA.** Activación de los calculadores por aseguradora y de las tablas de factores definitivas.
- **Reportes de PCA y productividad.** Cortes por total BCA, por promotoría y por agente, con filtros por aseguradora, ramo, producto y fecha.
- **Liquidación de comisiones a la red.** Esquemas de comisión, cortes de liquidación, bonos, premios y ajustes/clawbacks.

---

## 10. Buenas prácticas y errores comunes

- **No intentes editar "Pagado Hasta" a mano**: es automático. Si una fecha de vigencia está mal, revisá los pagos de los recibos.
- **Confirmá la póliza para que existan recibos.** En Borrador no hay plan de pagos.
- **Beneficiarios de Vida deben sumar 100%** o la confirmación falla.
- **Respetá el orden FIFO**: si el sistema no te deja pagar un recibo, es porque hay uno anterior pendiente.
- **¿No aparece el botón "Cancelar Pago" / "Anular Recibo"?** Es un permiso de Dirección. Escalá al Director Comercial o Director General.
- **El número de póliza es único por aseguradora**: si da error de duplicado, verificá que no exista ya.
- **Antes de asignar pólizas a un agente, confirmá su estado**: si es Prospecto, sus pólizas no computarán para PCA ni comisiones.

---

## Apéndice A — Matriz de permisos por acción

| Acción | Agente | Operador | Líder | Dir. Comercial | Director |
|---|:---:|:---:|:---:|:---:|:---:|
| Ver sus propias pólizas/recibos | ✅ | ✅ | ✅ | ✅ | ✅ |
| Ver toda la red | ❌ | ✅ | ✅ | ✅ | ✅ |
| Crear/editar pólizas | ❌ | ✅ | ✅ | ✅ | ✅ |
| Confirmar póliza / generar recibos | ❌ | ✅ | ✅ | ✅ | ✅ |
| Registrar pago | ❌ | ✅ | ✅ | ✅ | ✅ |
| Cancelar pago / anular recibo | ❌ | ❌ | ❌ | ✅ | ✅ |
| Ver bitácoras de importación | ❌ | ✅ | ✅ | ✅ | ✅ |
| Editar factores PCA / esquemas de comisión | ❌ | ❌ | ❌ | ✅ | ✅ |
| Gestionar promotorías / agentes / usuarios | ❌ | ❌ | ❌ | ❌ | ✅ |

---

## Apéndice B — Flujo operativo diario (resumen visual)

```
1. Alta de póliza (Borrador)
         │ Confirmar
         ▼
2. Póliza Activa  ──►  se generan recibos Pendientes (plan de pagos)
         │
         ▼
3. Cobranza: abrir recibo Pendiente más antiguo (FIFO)
         │ completar fecha + conducto → Registrar Pago
         ▼
4. Recibo Pagado  ──►  PCA congelada · foto del agente · "Pagado Hasta" avanza
         │ (si era el último de la anualidad)
         ▼
5. Se genera la siguiente anualidad automáticamente
```

---

*Documento base de capacitación elaborado para Grupo BCA. Refleja la funcionalidad disponible en la versión actual del módulo; actualícese conforme se liberen las etapas de cobranza masiva, PCA automática, reportes y comisiones.*
