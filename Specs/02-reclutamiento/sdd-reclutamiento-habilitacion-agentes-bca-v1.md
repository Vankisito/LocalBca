---
titulo: SDD — Reclutamiento y Habilitación de Agentes — Grupo BCA
fecha: 2026-06-29
autor: Hábitat Digital
version: v1.1
area: Entrega
---

> **Changelog v1.1 (2026-06-29) — Cumplimiento de las normas de la PCA.** Verificado contra
> `BDD_BCA_Seguros.md` (Car. 2, 8, 10) y el código de `BCA_Seguros`. Correcciones:
> 1. **F1 (crítico):** la conversión en "Cédula Emitida" crea el puente en `estado='clave_arranque'`
>    (antes `clave_definitiva`). Solo Clave Definitiva computa PCA; el agente recién habilitado **no**
>    debe computar. El paso a definitiva es un proceso interno posterior (ver §11 · SI-4).
> 2. **F2/F3:** se captura **RFC (`vat`) y CURP** en el candidato y la conversión crea/ubica el agente
>    de forma idempotente **por Id interno (Nombre+RFC+CURP)**, nunca por clave (norma de identidad del agente).

![Hábitat Digital](https://www.habitatdigital.net/web/image/website/1/logo/Habitat%20Digital?unique=cbdfacc)

# SDD — Reclutamiento y Habilitación de Agentes — Grupo BCA

> **Spec-Driven Development.** Especificación técnica de implementación derivada del
> **BDD v1.3** ("Proceso de Reclutamiento y Habilitación de Agentes — Grupo BCA") y del
> **GAP Analysis** contra Odoo 19 Community + el módulo `BCA_Seguros` (`19.0.1.4.0`).
> Este documento define **cómo se construye** lo que el BDD describe como comportamiento.
> Alineado a la metodología **MIOR**.

| Campo | Valor |
|---|---|
| **Proyecto** | BCA Seguros — Reclutamiento |
| **Documento base** | BDD v1.3 (comportamiento) + GAP Analysis |
| **Módulo objetivo** | `BCA_Seguros` → bump a `19.0.1.5.0` |
| **Plataforma** | Odoo 19 Community (nube) |
| **Estado** | Para revisión y construcción |

---

## 1. Propósito y alcance del SDD

Traducir el comportamiento del BDD a una especificación construible **sin interpretación**,
reusando al máximo lo de fábrica de Odoo y lo que ya existe en `BCA_Seguros`, con **cero
campos duplicados**.

- **Cubre:** el embudo de reclutamiento de **figuras comerciales (Agente y Promotoría)** de Fase A a
  Fase B hasta cédula emitida y conversión. Ambas figuras comparten el mismo embudo (D-20).
- **No cubre (fuera de alcance):** los **puestos internos**, que se reclutan por el **embudo nativo de
  Odoo** (sin Fase A/B ni cédula); demás puntos en §10.

---

## 2. Principios de diseño

1. **Reusar antes que crear.** Si Odoo o `BCA_Seguros` ya lo resuelve, no se duplica.
2. **La lógica vive en código, en `BCA_Seguros`.** Lo que el Python necesita leer/escribir va en el
   módulo (versionado en Git). La herramienta tipo Studio-Community se reserva para tableros y
   prototipos de vista, nunca para lógica.
3. **Adoptabilidad sobre completitud técnica.** El mejor sistema es el que el cliente usa.
4. **Alineación MIOR.** Cada salida (reportes) es una SIC; el SDD alimenta Épicas, HUs y TTs.

---

## 3. Decisiones de arquitectura (confirmadas)

| # | Decisión | Confirmada |
|---|---|---|
| **D1** | Se **extiende `BCA_Seguros` en código** (bump `19.0.1.5.0`). Studio-Community solo para tableros/prototipos | ✅ |
| **D2** | **No hay conversión sin cédula emitida.** El evento `hired` (que crea agente + clave + empleado) ocurre **únicamente en la etapa "Cédula Emitida"**. Antes de eso, el candidato permanece en Reclutamiento | ✅ |
| **D3** | La Fase B se modela como **etapas** (las fechas intermedias se capturan por timestamp nativo de etapa). **No se crean campos de fechas intermedias** (CIA, curso, examen, pago) | ✅ |
| **D4** | **Sede = plaza, lista oficial independiente de la promotoría** (una plaza puede tener varias promotorías). Se modela como un modelo maestro nuevo `bca.sede` | ✅ |

> **Aclaración D2 (reconciliación con el BDD).** El BDD marca "Contratado" al aceptar el acuerdo de
> arranque (Cena). En el SDD ese hito es la **etapa "Acuerdo de Arranque"** (se entrega a Capital
> Humano), **no** el evento técnico `hired`. La **conversión real** (alta de agente/empleado) se
> dispara solo al llegar a **"Cédula Emitida"**. Así honramos "no contratación sin cédula" sin perder
> el hito de negocio del BDD.

---

## 4. Modelo de datos

### 4.1 Etapas del embudo

Las etapas son **configuración** (sin código). Las **12 etapas** (Fase A + Fase B) se marcan
*job-specific* de **ambas figuras comerciales** (`job_reclutamiento_agente` y `job_captacion_promotoria`),
para que solo aparezcan ahí; los **puestos internos no las ven** —usan el embudo nativo de Odoo (D-20).

**Embudo COMERCIAL (Agente y Promotoría — `job_reclutamiento_agente`, `job_captacion_promotoria`):**

| # | Etapa | Fase | `hired_stage` | Notas |
|---|---|---|---|---|
| 1 | Recibido | A | — | Default (equivale a "New") |
| 2 | Prospección | A | — | |
| 3 | Café | A | — | |
| 4 | Entrevista | A | — | Marca `bca_entrevistado` |
| 5 | Evaluación PDA | A | — | Compuerta de riesgo (§5 · L1) |
| 6 | Acuerdo de Arranque | A→B | — | Hito BDD "Contratado"; entrega a Capital Humano. **No** dispara conversión |
| 7 | Clave de Arranque | B | — | Inicio habilitación |
| 8 | Inscripción CIA | B | — | |
| 9 | Curso de Cédula | B | — | |
| 10 | Examen | B | — | |
| 11 | **Cédula Emitida** | B | ✅ **True** | **Dispara conversión** (§5 · L2) |
| 12 | En Desarrollo Comercial | B | — | Post-conversión (entrenamiento) |

**Puestos INTERNOS (Auxiliar admin., Reclutador, Gerencial, cualquier otro `hr.job`):**

Usan el **embudo nativo de Odoo** (`hr_recruitment`): las etapas nativas (New … Contract Signed) y
su etapa hired nativa. **No** ven ninguna de las 12 etapas comerciales. Al llegar a la etapa hired
nativa se da de alta el `hr.employee`; el ruteo por `job_id` (§5 · L2) **no** crea partner agente,
puente ni cédula. La etapa BCA "Contratado (Alta Interna)" queda **retirada** (D-20, `19.0.1.7.7`).

> Las etapas de Stand by y rechazo **no** son columnas: Stand by = **archivar** el candidato
> (conserva historial, reactivable); rechazo = **motivo de rechazo** nativo (§4.5).

### 4.2 Campos nuevos en `hr.applicant`

Prefijo `bca_`. Todos justificados por el BDD §6. Se **reutilizan** selecciones existentes donde
aplica. (Recuerda: `bca_promotoria_destino_id` **ya existe** y no se toca.)

| Campo | Tipo | Reusa / Nuevo | Origen BDD |
|---|---|---|---|
| `bca_sede_id` | Many2one(`bca.sede`) | **Nuevo** (modelo §4.3) | Sede/plaza |
| `bca_ramo` | Selection(`RAMO_SELECTION`) | **Reusa selección** | Ramo Vida/Autos |
| `bca_genero` | Selection(`GENERO_SELECTION`) | **Reusa selección** | Género |
| `bca_fecha_nacimiento` | Date | Nuevo (edad = computed) | Edad |
| `bca_institucion` | Char | Nuevo | Institución |
| `bca_perfil_academico` | Char | Nuevo | Perfil académico |
| `bca_perfil_laboral` | Char | Nuevo | Perfil laboral |
| `bca_tiene_cedula_previa` | Boolean | Nuevo | "¿ya cuenta con cédula?" |
| `bca_tipo_candidato` | Selection [postulado/prospectado/referido/sugerido] | Nuevo | Tipo de candidato |
| `bca_referido_por` | Char | Nuevo | Quién lo refirió |
| `bca_folio_cv` | Char | Nuevo | Folio CV de la bolsa |
| `bca_evento` | Char | Nuevo | Evento de reclutamiento (Cancún, universidades) |
| `bca_contactado` | Selection [si/no_localizado/pendiente] | Nuevo | Contactado (dispara recordatorio) |
| `bca_entrevistado` | Boolean | Nuevo | Entrevistado Sí/No |
| `bca_pda_nivel` | Selection [excelente/muy_buena/aceptable/baja/no_ideal] | **Nuevo (núcleo)** | PDA escala de 5 |
| `bca_pda_correlacion` | Float | Nuevo | % de correlación PDA |
| `bca_pda_perfil` | Char | Nuevo | Perfil PDA |
| `bca_pda_riesgo` | Boolean (computed) | Nuevo | True si nivel ∈ {baja, no_ideal} |
| `bca_pda_visto_bueno_promotor` | Boolean | Nuevo | Aprobación del promotor en riesgo |
| `bca_clave_arranque` | Char | Nuevo | Clave de arranque (alimenta el puente) |
| `bca_fecha_cedula` | Date | Nuevo | Fecha de cédula emitida (capturada en el candidato; se almacena en el puente como `fecha_licencia`) |
| `bca_aseguradora_id` | Many2one(`res.partner`, domain aseguradora) | **Reusa modelo** | Aseguradora emisora (para el puente) |
| `bca_curp` | Char | **Nuevo (identidad PCA)** | CURP — parte del Id interno del agente (Nombre+RFC+CURP) |
| `bca_reagendaciones` | Integer (default 0) | Nuevo | Control de no-show (§5 · L5) |

**Mapeo a campos nativos (NO se crean):** nombre → `partner_name`/`candidate`; **RFC → `vat`** (estándar);
teléfono → `partner_phone`; correo → `email_from`; reclutadora → `user_id` (recruiter); puesto → `job_id`;
pretensión económica → `salary_expected`; CV → adjunto nativo; grado académico → `type_id`/degree;
fuente → `source_id` (UTM); campaña → `campaign_id` (UTM); motivo de declinación → `refuse_reason_id` (nativo, §4.5).

> **Identidad del agente (norma PCA).** El **RFC (`vat`)** y el **CURP (`bca_curp`)** se capturan en el
> candidato porque, al convertir en cédula (§5 · L2), el agente se crea/ubica por su **Id interno
> (Nombre + RFC + CURP)** — nunca por la clave, que varía por aseguradora. Sin estos datos no se puede
> garantizar la identidad ni la idempotencia de la conversión.

### 4.3 Modelo nuevo `bca.sede`

Master data simple (lista oficial de plazas). Independiente de la promotoría.

| Campo | Tipo | Notas |
|---|---|---|
| `name` | Char | Requerido (CDMX, Puebla, GDL, QRO, HGO, MTY…). Rec name |
| `codigo` | Char | Opcional, para reportes |
| `active` | Boolean | default True |

> Una plaza agrupa a varias promotorías. El candidato lleva su `bca_sede_id` directamente
> (puede registrarse antes de tener promotoría destino). La sede es eje de **reportes** y de
> **visibilidad** (§6).

### 4.4 Reuso del puente `res.partner.agente.aseguradora`

**No se crea nada nuevo aquí.** La habilitación se materializa en el puente ya existente:

| Dato del BDD | Campo del puente |
|---|---|
| Clave de arranque (folio) | `clave_agente` |
| Habilitado al emitir cédula (aún no certificado para PCA) | `estado = 'clave_arranque'` |
| Fecha de cédula | `fecha_licencia` |
| Aseguradora emisora | `aseguradora_id` |

> **Estado del puente al emitir cédula = `clave_arranque` (norma PCA).** El agente se **contrata en
> Clave de Arranque**; en este nivel **NO computa PCA ni comisiones** (solo `clave_definitiva` computa,
> ver `BDD_BCA_Seguros.md` Car. 8 y 10). El paso **Clave de Arranque → Clave Definitiva** es un
> **proceso interno posterior de BCA**, fuera del alcance del reclutamiento (ver §10 y §11 · SI-4).
> Asentar `clave_definitiva` aquí activaría el cómputo de comisiones de forma indebida.

> El **gap conocido** del inventario (el flujo de contratación no creaba aún el registro del puente)
> se **cierra** en este SDD: la conversión en "Cédula Emitida" crea el puente (§5 · L2).

### 4.5 Motivos de rechazo (nativos)

Se configuran dos motivos en *Reclutamiento → Configuración → Motivos de rechazo*:

| Motivo | Equivale a |
|---|---|
| Declinado por Prospecto | El candidato se baja |
| Declinado por BCA | BCA no continúa |

El motivo es **obligatorio** al rechazar (comportamiento nativo). Cada motivo puede llevar plantilla
de correo.

### 4.6 Mapeo Estado del BDD → mecanismo Odoo

| Estado BDD | Mecanismo Odoo |
|---|---|
| Recibido | Etapa "Recibido" |
| En proceso | Etapas activas (Prospección…Cédula) |
| Stand by (On Hold) | **Archivar** (`active=False`); reactivable en su etapa |
| Declinado Prospecto | Rechazo + motivo "Declinado por Prospecto" |
| Declinado BCA | Rechazo + motivo "Declinado por BCA" |
| Contratado (figura comercial) | Etapa "Acuerdo de Arranque" (hito) + conversión real en "Cédula Emitida" |
| Contratado (interno) | Etapa hired nativa de Odoo ("Contract Signed") en el embudo nativo |
| En Desarrollo Comercial | Etapa post-conversión |

---

## 5. Comportamiento / lógica

Cada regla indica **disparador → condición → acción → dónde vive**. Las que el Python necesita
viven en `BCA_Seguros` (código); los recordatorios/avisos pueden ir como reglas de automatización
**versionadas como datos del módulo**.

### L1 — Compuerta PDA de riesgo
- **Disparador:** escritura de `bca_pda_nivel`.
- **Condición:** nivel ∈ {baja, no_ideal} → `bca_pda_riesgo = True`.
- **Acción:** crear actividad "Visto bueno requerido" al **promotor** de la promotoría destino;
  **bloquear** el avance más allá de "Evaluación PDA" hasta `bca_pda_visto_bueno_promotor = True`.
  Si nadie aprueba → puede rechazarse como "Declinado por BCA".
- **Dónde:** código en `BCA_Seguros` (`@api.constrains` + creación de actividad).

### L2 — Conversión en "Cédula Emitida" (evento `hired`)
- **Disparador:** el candidato entra a la etapa con `hired_stage=True` ("Cédula Emitida"). Se
  engancha en el `write()` ya existente.
- **Guarda (constraint):** **no** permitir `hired` sin `bca_clave_arranque`, `bca_fecha_cedula`,
  `bca_aseguradora_id`, **RFC (`vat`) y CURP (`bca_curp`)**. (Materializa "no contratación sin cédula"
  y garantiza el Id interno para la identidad/idempotencia del agente.)
- **Acción (figura comercial, `job_reclutamiento_agente`):**
  1. Crear/ubicar `res.partner` agente extendiendo `_bca_crear_partner_desde_contratado`, **idempotente
     por Id interno (Nombre + RFC + CURP)**: si ya existe un agente con ese Id interno (p. ej. ya opera
     con otra aseguradora), se **reutiliza**; nunca se duplica ni se resuelve por clave.
  2. Crear `res.partner.agente.aseguradora` con `clave_agente = bca_clave_arranque`,
     **`estado = 'clave_arranque'`**, `fecha_licencia = bca_fecha_cedula`, `aseguradora_id = bca_aseguradora_id`.
     El agente queda habilitado pero **no computa PCA** hasta el paso posterior a `clave_definitiva`
     (proceso interno, §11 · SI-4).
  3. Crear `hr.employee` (gestión vía módulo de Empleados) **vinculado** al partner agente.
  4. Notificar a reclutadora y promotor: "agente habilitado (Clave de Arranque)".
- **Acción (puesto interno):** alta nativa de `hr.employee` al llegar a la etapa hired nativa de Odoo
  (embudo nativo). **Sin** partner agente, **sin** puente, **sin** cédula. El ruteo por `job_id` ignora
  cualquier job no comercial (D-20).
- **Dónde:** código en `BCA_Seguros` (extiende el método existente).

> **Nota de vínculo agente↔empleado:** el `hr.employee` del agente referencia al partner agente BCA
> como su contacto. Se gestiona con las bondades del módulo de Empleados aunque, legalmente, el agente
> no sea empleado. (Decisión confirmada por Dirección.)

### L3 — Recordatorio de seguimiento (3 días ordinarios)
- **Disparador:** condición de tiempo (regla de automatización temporizada, `base_automation`).
- **Condición:** `bca_contactado = 'no_localizado'` **o** sin cambio de etapa en 3 días ordinarios.
- **Acción:** actividad/correo recordatorio a la reclutadora responsable.
- **Dónde:** regla de automatización entregada como **dato del módulo** (versionada).

### L4 — Cambio de ramo (Vida → Autos)
- **Disparador:** edición de `bca_ramo` en el mismo candidato.
- **Acción:** continúa por el mismo embudo, **sin reiniciar historial** (es el mismo registro).
- **Dónde:** solo el campo + nota en chatter. Sin lógica adicional. (SOP de operación.)

### L5 — No-show: reagendar una vez
- **Disparador:** registro de inasistencia a café/entrevista.
- **Acción:** permitir reagendar (incrementa `bca_reagendaciones`); al **segundo** no-show, el sistema
  **sugiere** pasar a Stand by (archivar).
- **Dónde:** regla de automatización + el contador. **Prioridad baja.**

### L6 — Avisos por etapa
| Evento | Destinatario | Mecanismo |
|---|---|---|
| Llega a "Acuerdo de Arranque" | Capital Humano | Automatización / correo de etapa |
| PDA cargada (apta) | Reclutadora | Automatización |
| Llega a "Cédula Emitida" | Reclutadora + Promotor | Automatización (parte de L2) |

---

## 6. Seguridad y visibilidad

Se **reutiliza** la jerarquía de grupos existente y se añaden reglas específicas de reclutamiento.
Esta es la sección de mayor cuidado del proyecto.

| Rol BDD | Qué ve | Regla (record rule) |
|---|---|---|
| Reclutadora | Solo sus candidatos | `user_id == uid` (recruiter nativo) |
| Promotor | Los de su(s) sede(s) | `bca_sede_id ∈ user.bca_sede_ids` |
| Capital Humano | Candidatos en Fase B | Por grupo + etapas de habilitación |
| Gerencia / Dirección | Consolidado nacional | Sin restricción (grupos director_comercial / director) |
| Separación agentes ↔ promotorías | Un usuario no ve ambos salvo permiso | Regla por `job_id` (`job_reclutamiento_agente` vs `job_captacion_promotoria`) |

**Grupos propuestos (slot dentro de la jerarquía existente):**
`group_bca_reclutadora`, `group_bca_promotor`, `group_bca_capital_humano`.
**Mecanismo para "promotor ↔ sede":** campo `bca_sede_ids` (Many2many) en el usuario/empleado promotor,
que alimenta la regla de visibilidad por sede.

> ⚠️ **A confirmar con BCA** el mapa exacto rol→qué ve antes de codificar las reglas (ver §11).

---

## 7. Reportes (SICs MIOR)

Los tres reportes del BDD son el corazón del proyecto y se nombran como **SICs**.

| SIC | Vista nativa base | Dimensiones | Estado |
|---|---|---|---|
| **SIC: Embudo de Conversión de Reclutamiento** | Análisis de Postulantes (pivote) | reclutadora · `bca_sede_id` · `job_id` · `bca_ramo` · periodo | Funciona al existir los campos; tablero/pivote a configurar |
| **SIC: Tiempos de Habilitación** | Análisis de Velocidad (tiempo en etapa) | reclutadora · sede · puesto | Prácticamente nativo |
| **SIC: Efectividad por Fuente, Campaña y Evento** | Análisis de Fuentes + UTM | `source_id` · `campaign_id` · `bca_evento` | Casi nativo |

> Un tablero "bonito" de embudo puede construirse en **Studio-Community** (es reporte, no lógica).

---

## 8. Definición de Hecho (técnica)

- Un candidato fluye de "Recibido" a "En Desarrollo Comercial" **sin salir del sistema**.
- El sistema **impide** marcar "Cédula Emitida" sin clave de arranque + fecha de cédula + aseguradora
  + RFC + CURP.
- Al emitir cédula se crean, de forma **idempotente por Id interno (Nombre+RFC+CURP)**: partner agente
  + registro de puente (**`clave_arranque`**) + `hr.employee` vinculado, con aviso a reclutadora y promotor.
- El agente recién habilitado **NO computa PCA ni comisiones** (queda en `clave_arranque`; el cómputo
  inicia solo al promoverlo a `clave_definitiva`, proceso interno posterior — §11 · SI-4).
- PDA "Baja"/"No ideal" **bloquea** el avance sin visto bueno del promotor.
- Stand by archiva conservando historial; rechazo exige motivo.
- Los **3 SICs** salen sin Excel.
- **Cero campos duplicados** respecto al inventario de `BCA_Seguros`.

---

## 9. Trazabilidad BDD → SDD

| Escenario / regla BDD | Elemento SDD |
|---|---|
| Alta de candidato (sede y puesto obligatorios) | Etapas §4.1 + `bca_sede_id` + constraint de obligatoriedad |
| Café y luego Entrevista (dos pasos) | Etapas 3 y 4 + `bca_entrevistado` |
| Evaluación PDA escala de 5 | `bca_pda_nivel/_correlacion/_perfil` |
| Riesgo PDA → visto bueno → Gerencia | L1 |
| Cambio de ramo Vida→Autos | L4 |
| Cena / acuerdo de arranque (conversión) | Etapa "Acuerdo de Arranque" (hito) + L2 (conversión real en cédula) |
| Habilitación y cédula | Etapas Fase B + puente (§4.4) + L2 |
| No aprueba examen | Etapas + Stand by/Rechazo (SOP) |
| Stand by / Declinaciones | §4.5 + §4.6 |
| Visibilidad por rol + separación | §6 |
| Recordatorio 3 días | L3 |
| Reportes 1, 2, 3 | §7 (SICs) |

---

## 10. Fuera de alcance

- **Formulario del sitio web** (ya opera; entra como canal nativo).
- **Campos de fechas intermedias** de Fase B (CIA, curso, examen, pago): se capturan por timestamp de
  etapa, no como campos (D3).
- **Inversión por canal** (costo por contratación): pendiente de decisión de BCA (BDD §11).
- **Integración con proveedor PDA:** la PDA es captura manual.
- **Promoción Clave de Arranque → Clave Definitiva:** es un **proceso interno posterior de BCA** que
  habilita el cómputo de PCA. El reclutamiento termina en `clave_arranque`; el paso a `clave_definitiva`
  se diseña aparte como acción controlada (permiso + auditoría) — ver §11 · SI-4.
- **Habilitación de Promotor vía puente:** ver §11 (open item).

---

## 11. Puntos a confirmar antes de construir

1. **Mapa de visibilidad rol→qué ve** (para cerrar las record rules de §6) y mecanismo de asignación
   **promotor ↔ sede(s)** (`bca_sede_ids`).
2. **Habilitación de Promotor:** ¿el candidato a Promotor (figura comercial) usa el mismo flujo de
   cédula + puente, o el flujo de partner promotoría existente? El BDD dice "mismo embudo, distinta
   visibilidad"; el módulo hoy crea la promotoría como partner-empresa. Confirmar.
3. **Evento de reclutamiento:** ¿`bca_evento` como texto basta, o se quiere lista oficial (modelo)?
4. **SI-4 — Promoción a Clave Definitiva (habilita PCA):** ¿qué evento/criterio interno dispara el
   paso `clave_arranque → clave_definitiva` (certificación, antigüedad, producción), quién lo autoriza
   y qué auditoría exige? Hoy el puente expone `estado` editable a mano, sin guarda ni permiso: promover
   a definitiva activa el cómputo de comisiones, por lo que debe blindarse como **acción controlada**
   (HU futura, fuera del alcance de reclutamiento). Bloquea el diseño de esa HU, no el reclutamiento.

---

## 12. Mapeo a MIOR (hacia el backlog)

Este SDD alimenta las siguientes Épicas/HUs (la lista detallada con TTs sale en `BACKLOG - Creación`):

- **ÉPICA — SIC: Embudo de Conversión de Reclutamiento**
- **ÉPICA — SIC: Tiempos de Habilitación**
- **ÉPICA — SIC: Efectividad por Canal**
- **HUs transversales (config + dev):** configurar embudo y etapas job-specific · agregar campos
  PDA y de identificación · compuerta de riesgo PDA (L1) · conversión en cédula + puente + empleado
  (L2) · record rules de visibilidad (§6) · recordatorios y avisos (L3/L6) · modelo `bca.sede`.

---

*Hábitat Digital · SDD — Reclutamiento de Agentes · Grupo BCA · v1.0*
