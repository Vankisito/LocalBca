---
titulo: Historias de Usuario, Criterios de Aceptación y Tareas Técnicas — Reclutamiento y Habilitación de Agentes — Grupo BCA
fecha: 2026-06-29
autor: Hábitat Digital
version: v1.0
area: Entrega
---

![Hábitat Digital](https://www.habitatdigital.net/web/image/website/1/logo/Habitat%20Digital?unique=cbdfacc)

# HU + Criterios de Aceptación + Tareas Técnicas — Reclutamiento BCA

> Documento ejecutable de la fase de implementación de **Reclutamiento y Habilitación de Agentes — Grupo BCA**.
> Toma como base de estructura el `analisis-hu-tt-reclutamiento-bca-v1.md` (Épicas → HU → TT) y lo enriquece con:
> **(a)** criterios de aceptación en **Gherkin** por Historia de Usuario, y **(b)** un **checklist de Definición de Hecho (DoD)** por cada Tarea Técnica (EDEP/TT).
> Deriva del **SDD v1.1** y del **BDD v1.3** de reclutamiento, y está **verificado contra las normas de la PCA**
> (`BDD_BCA_Seguros.md`, Car. 1, 2, 8, 10). Plataforma: **Odoo 19 Community (nube)**, módulo `BCA_Seguros` → bump `19.0.1.5.0`.

---

## 1. Cómo leer este documento

Cada HU responde **quién la ejecuta y dónde vive**, y trae sus criterios de aceptación y sus tareas técnicas.

| Marca | Significa | Quién | Dónde vive |
|---|---|---|---|
| 🟦 **CÓDIGO** | Lógica, modelos, campos que el Python lee/escribe, constraints, computed, seguridad | Desarrollador | Módulo `BCA_Seguros` (Git) |
| 🟧 **UI / IMPLEMENTADOR** | Configuración nativa de Odoo, sin código | Consultor implementador | Interfaz de Odoo |
| 🟨 **HÍBRIDO** | Se prototipa en la interfaz pero se entrega versionado como **dato del módulo** | Implementador + Desarrollador | UI + `BCA_Seguros` (data) |

**Formato de criterios (híbrido):**
- **Historias de Usuario → Gherkin** (`Característica` / `Escenario` / Dado-Cuando-Entonces, en español), consistente con `BDD_BCA_Seguros.md`. Se cita la regla de negocio (R-PCA, R-ORG…) cuando aplica.
- **Tareas Técnicas (EDEP/TT) → checklist DoD**: condiciones verificables que cierran la tarea. Un `[ ]` es una condición que QA o el revisor puede comprobar.

**Convención de pruebas (sandbox).** "Tests verdes en sandbox" =
`docker exec odoo_golden odoo -d sandbox_bca1 --test-enable --test-tags BCA_Seguros --stop-after-init --no-http`
y confirmar en `/var/log/odoo/odoo.log` que **no** aparecen las líneas de `failures/errors`.

---

## 2. Resumen ejecutivo de la distribución

12 Historias de Usuario en 3 Épicas. El desarrollo se concentra en la **Épica 1** (modelo de datos + lógica + seguridad); las Épicas 2 y 3 son casi enteramente configuración.

| Clasificación | HUs | Implicación |
|---|---|---|
| 🟦 CÓDIGO | 5 | Requieren **desarrollador** sobre `BCA_Seguros` |
| 🟧 UI / IMPLEMENTADOR | 6 | Las hace un **consultor implementador** desde Odoo |
| 🟨 HÍBRIDO | 1 | Implementador arma, desarrollador empaqueta como dato |
| 🔶 Condicional | (1 TT) | Una TT de Épica 3 pasa a código solo si BCA decide "Evento" como modelo (SI-3) |

---

## 3. Verificación de cumplimiento de las normas de la PCA

> Resultado de contrastar el análisis v1.0 / SDD v1.0 contra `BDD_BCA_Seguros.md` (identidad del agente, nomenclatura de carrera y cómputo de comisiones) y el código de `BCA_Seguros`. Las correcciones ya están incorporadas a las HU/TT de este documento y al **SDD v1.1**.

| # | Hallazgo | Severidad | Corrección aplicada |
|---|---|---|---|
| **F1** | La conversión en "Cédula Emitida" creaba el puente en `estado='clave_definitiva'` → el agente computaría PCA de inmediato, violando la norma "solo Clave Definitiva computa" (Car. 8/10). Inconsistencia interna: se captura `bca_clave_arranque` pero se asentaba definitiva. | 🔴 Crítico | El puente nace en **`estado='clave_arranque'`**. El agente habilitado **NO computa PCA**. El paso a definitiva es proceso interno posterior (**SI-4**). |
| **F2** | No se capturaba **RFC ni CURP**, pese a que la identidad del agente = **Id interno (Nombre+RFC+CURP)** (Car. 2). | 🟠 Alto | Se capturan **RFC (`vat`)** y **CURP (`bca_curp`)** en el candidato; son obligatorios en la guarda de conversión. |
| **F3** | La conversión decía "idempotente" sin definir la clave; el código solo evita recrear si el applicant ya tiene partner → duplicaría un agente que ya opera con otra aseguradora. | 🟠 Alto | Idempotencia **por Id interno**: se reutiliza el partner agente existente y solo se agrega el puente de la nueva aseguradora. |
| **N1** | (Refuerza F1) Nomenclatura inconsistente en el SDD. | — | Resuelto con F1. |
| **N2** | El paso Arranque → Definitiva (habilita PCA) no estaba definido; el puente expone `estado` editable a mano, sin guarda ni permiso. | 🟠 Alto (fuera de alcance) | Registrado como **SI-4** + HU futura (acción controlada con permiso + auditoría). |
| **N3** | La conversión debe acotarse a figuras comerciales. | — | Los CA de HU-1.4 ramifican por `job_id` (`job_reclutamiento_agente`). |

**Normas PCA de referencia (fuente de verdad):**
1. Identidad del agente = **Id interno (Nombre+RFC+CURP)**, único; la clave NO identifica (varía por aseguradora). — Car. 2.
2. Carrera de 3 niveles: **Prospecto → Clave de Arranque → Clave Definitiva**, por aseguradora.
3. **Solo Clave Definitiva computa PCA/comisiones.** — Car. 8 y 10.
4. La clave vive en el puente `res.partner.agente.aseguradora` (única por aseguradora).
5. Un agente **cuelga de exactamente una promotoría**, nunca del holding. — R-ORG.

---

## 4. ÉPICA 1 — SIC: Embudo de Conversión de Reclutamiento

> **Épica ancla.** Carga la fundación del flujo (etapas, campos, modelo de sede, lógica de conversión y seguridad). Probable **2 sprints**. Las Épicas 2 y 3 dependen de los campos creados aquí.

**SIC del entregable:** `SIC: Embudo de Conversión de Reclutamiento`

---

### HU-1.0 — Administrar el catálogo de Sedes (plazas) · 🟦 CÓDIGO
*HU - Administrar catálogo de Sedes - Gerencia/Admin*

- **Por qué código:** es un **modelo nuevo** (`bca.sede`, SDD §4.3). El campo `bca_sede_id` del candidato lo referencia y la seguridad por sede lo usa.

**Criterios de aceptación**
```gherkin
Característica: Administrar el catálogo de Sedes (plazas)

Escenario: Alta de una plaza nueva sin tocar código
  Dado un usuario con rol Gerencia/Admin
  Cuando da de alta la sede "Querétaro" con su código
  Entonces la sede queda disponible para asignarse a candidatos y como eje de reportes

Escenario: Baja lógica de una plaza sin perder historial
  Dado una sede con candidatos históricos
  Cuando se archiva la sede (active = False)
  Entonces deja de ofrecerse en altas nuevas
  Pero los candidatos históricos conservan su referencia de sede

Escenario: La sede es independiente de la promotoría
  Dado que una plaza puede agrupar varias promotorías
  Cuando se consulta la sede de un candidato
  Entonces la sede no obliga a una promotoría específica
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Crear modelo bca.sede (name/codigo/active) · Backend
[ ] Modelo bca.sede con name (Char, requerido, rec_name), codigo (Char), active (Boolean, default True)
[ ] Cumple estándares v19 del módulo (from __future__ import annotations, type annotations)
[ ] ir.model.access.csv con permisos (lectura para todos los roles BCA; escritura Gerencia/Admin)
[ ] Test: alta, archivado y reactivación

TT - Crear vistas list/form + menú de configuración de Sede · UX
[ ] Vista list y form de bca.sede
[ ] Menú en Reclutamiento → Configuración → Sedes con atributo groups
[ ] Sintaxis v19 (<list>, no <tree>)

TT - Cargar catálogo inicial de plazas · Data
[ ] data/sedes_iniciales.xml con la lista oficial (pendiente SI-Sede)
[ ] noupdate="1" para protección en upgrade; plan de migración si cambia el seed
```
- **Criterio de éxito:** el cliente da de alta/baja una plaza sin tocar código; la sede es eje de reportes y visibilidad.

---

### HU-1.1 — Configurar el embudo y las etapas job-specific · 🟧 UI / IMPLEMENTADOR
*HU - Configurar embudo y etapas - Implementador*

- **Por qué UI:** el SDD §4.1 es explícito — **las etapas son configuración (sin código)**.

**Criterios de aceptación**
```gherkin
Característica: Configurar el embudo de reclutamiento y sus etapas

Escenario: El embudo comercial muestra Fase A y Fase B (agentes y promotorías)
  Dado un candidato con puesto de figura comercial (job_reclutamiento_agente o job_captacion_promotoria)
  Cuando se abre su embudo
  Entonces ve las etapas de Fase A (Recibido…Acuerdo de Arranque)
  Y las de Fase B (Clave de Arranque…Cédula Emitida…En Desarrollo Comercial)

Escenario: El puesto interno usa el embudo nativo de Odoo
  Dado un candidato a puesto interno
  Cuando se abre su embudo
  Entonces ve el embudo nativo de Odoo y su etapa hired nativa
  Pero no ve ninguna etapa del embudo comercial BCA (ni Fase A ni Fase B)

Escenario: La etapa de cédula está marcada como hired
  Dado el embudo comercial
  Cuando se consulta la etapa "Cédula Emitida"
  Entonces tiene hired_stage = True
  Y es la única etapa del embudo comercial que dispara la conversión
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Crear etapas del embudo comercial (Recibido → En Desarrollo Comercial) · UX
[ ] 12 etapas del SDD §4.1 creadas en el orden correcto
[ ] Etapa "Recibido" como default

TT - Marcar las 12 etapas como job-specific de ambas figuras comerciales · UX
[ ] Las 12 etapas (Fase A + Fase B) tienen job_ids = [job_reclutamiento_agente, job_captacion_promotoria]
[ ] Un puesto interno NO ve ninguna de ellas (usa el embudo nativo de Odoo)

TT - Marcar hired_stage=True solo en "Cédula Emitida" · UX
[ ] "Cédula Emitida" con hired_stage=True (dispara la conversión: agente o promotoría según job_id)
[ ] Ninguna otra etapa del embudo comercial tiene hired_stage=True
[ ] La etapa BCA "Contratado (Alta Interna)" queda retirada (D-20): los internos cierran con la etapa hired nativa
```
- **Criterio de éxito:** los candidatos comerciales (agentes y promotorías) ven Fase A+B; un puesto interno usa el embudo nativo de Odoo, sin etapas BCA.

---

### HU-1.2 — Registrar datos de identificación y perfil del candidato · 🟦 CÓDIGO
*HU - Registrar datos de identificación y perfil - Reclutadora*

- **Por qué código:** son **campos nuevos `bca_` en `hr.applicant`** (SDD §4.2); varios alimentan lógica o son computed (edad). Por D1 no se crean con Studio.
- **Cumplimiento PCA (F2):** incluye **RFC (`vat`) y CURP (`bca_curp`)** para soportar la identidad del agente por Id interno.

**Criterios de aceptación**
```gherkin
Característica: Registrar identificación y perfil del candidato

Escenario: Captura completa de identificación y perfil
  Dado un candidato nuevo
  Cuando la reclutadora captura sede, ramo, género, fecha de nacimiento, RFC, CURP,
        institución, perfiles, tipo de candidato, referido, folio CV, evento y banderas de contacto
  Entonces todos los datos quedan en el formulario del candidato
  Y la edad se calcula sola desde la fecha de nacimiento

Escenario: Sin campos duplicados (mapeo a nativos)
  Dado el inventario de BCA_Seguros
  Cuando se revisan los campos del candidato
  Entonces nombre, teléfono, correo, reclutadora, puesto, pretensión, CV, fuente y campaña
          usan campos nativos (partner_name, partner_phone, email_from, user_id, job_id,
          salary_expected, adjunto, source_id, campaign_id)
  Y el RFC usa el campo estándar vat
  Y no existe ningún campo bca_ duplicado de uno nativo

Escenario: RFC y CURP quedan disponibles para la conversión
  Dado un candidato con RFC y CURP capturados
  Cuando avanza hacia la habilitación
  Entonces esos datos están listos para identificar al agente por Id interno (ver HU-1.4)
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Agregar campos de identificación bca_ (sede_id, ramo, genero, fecha_nacimiento) · Backend
[ ] bca_sede_id (M2O bca.sede), bca_ramo (reusa RAMO_SELECTION), bca_genero (reusa GENERO_SELECTION),
    bca_fecha_nacimiento (Date)
[ ] Reusa selecciones existentes (cero selecciones duplicadas)

TT - Capturar RFC y CURP del candidato (identidad PCA) · Backend
[ ] RFC mapeado al campo estándar vat (no se crea campo nuevo)
[ ] bca_curp (Char) nuevo
[ ] (Opcional) validación de formato de RFC/CURP mexicano
[ ] Test: ambos quedan accesibles desde el applicant

TT - Computar edad desde bca_fecha_nacimiento · Backend
[ ] bca_edad computed (no store o store con depends), entero
[ ] Test: edad correcta para una fecha dada

TT - Agregar campos de perfil/origen · Backend
[ ] institucion, perfil_academico, perfil_laboral, tipo_candidato, referido_por, folio_cv,
    evento, contactado, entrevistado, tiene_cedula_previa
[ ] Tipos según SDD §4.2; selecciones donde aplica

TT - Insertar campos en la vista del candidato (form) · UX
[ ] Form de hr.applicant con los campos agrupados (identificación / origen / perfil / evaluación)
[ ] Sintaxis v19; herencia de vista sin position="after" ambiguo

TT - Validar mapeo a campos nativos sin duplicar (cero campos duplicados) · Backend
[ ] Checklist de mapeo del SDD §4.2 verificado contra el inventario
[ ] Tests verdes en sandbox
```
- **Criterio de éxito:** la reclutadora captura todo el perfil en un formulario; el inventario no tiene campos duplicados y la identidad (RFC/CURP) queda lista para la conversión.

---

### HU-1.3 — Capturar y evaluar PDA con compuerta de riesgo · 🟦 CÓDIGO
*HU - Evaluar PDA con compuerta de riesgo - Reclutadora/Promotor*

- **Por qué código:** campos PDA + **lógica L1** (`@api.constrains`, computed, creación de actividad, bloqueo de avance).

**Criterios de aceptación**
```gherkin
Característica: Evaluación PDA con compuerta de riesgo

Escenario: PDA apta avanza sin fricción
  Dado un candidato entrevistado
  Cuando se captura nivel PDA "Excelente", "Muy buena" o "Aceptable"
  Entonces bca_pda_riesgo queda en False
  Y el candidato puede avanzar hacia la Cena (Acuerdo de Arranque)
  Y se avisa a la reclutadora que la PDA está cargada

Escenario: PDA de riesgo bloquea el avance sin visto bueno
  Dado un candidato con nivel PDA "Baja" o "No ideal"
  Cuando se captura el resultado
  Entonces bca_pda_riesgo queda en True
  Y se crea una actividad "Visto bueno requerido" al promotor de la promotoría destino
  Y el candidato no puede avanzar más allá de "Evaluación PDA" sin bca_pda_visto_bueno_promotor = True

Escenario: Sin aprobación, se declina
  Dado un candidato de riesgo sin visto bueno del promotor
  Cuando nadie lo aprueba
  Entonces puede cerrarse como "Declinado por BCA" con motivo
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Agregar campos PDA (nivel, correlacion, perfil, visto_bueno_promotor) · Backend
[ ] bca_pda_nivel (Selection 5 niveles), bca_pda_correlacion (Float), bca_pda_perfil (Char),
    bca_pda_visto_bueno_promotor (Boolean)

TT - Computar bca_pda_riesgo (True si nivel ∈ {baja, no_ideal}) · Backend
[ ] computed con depends en bca_pda_nivel
[ ] Test: cada nivel produce el riesgo esperado

TT - Constraint L1: bloquear avance más allá de "Evaluación PDA" sin VoBo · Backend
[ ] @api.constrains sobre stage_id / bca_pda_visto_bueno_promotor
[ ] Mensaje claro al usuario
[ ] Test: riesgo sin VoBo bloquea; con VoBo permite

TT - Crear actividad "Visto bueno requerido" al promotor de la sede/promotoría destino · Backend
[ ] Actividad dirigida al promotor correspondiente
[ ] Test: se crea la actividad cuando bca_pda_riesgo pasa a True
```
- **Criterio de éxito:** un perfil de riesgo no avanza sin visto bueno del promotor; si nadie aprueba, se declina por BCA.

---

### HU-1.4 — Convertir candidato a agente habilitado al emitir cédula · 🟦 CÓDIGO
*HU - Convertir candidato a agente habilitado - Sistema/Reclutadora/Promotor*

- **Por qué código:** es el **corazón de la lógica L2** (extiende `write()`/`hired`, constraint de guarda, alta idempotente de partner + puente + empleado).
- **Cumplimiento PCA (F1/F2/F3, N3):** el puente nace en **`clave_arranque`** (no computa PCA); la identidad y la idempotencia son **por Id interno (Nombre+RFC+CURP)**; solo aplica a `job_reclutamiento_agente`.

**Criterios de aceptación**
```gherkin
Característica: Convertir candidato a agente habilitado al emitir cédula

Escenario: La cédula habilita en Clave de Arranque (no computa PCA)
  Dado un candidato (job_reclutamiento_agente) con RFC, CURP, aseguradora y promotoría destino
  Cuando su etapa pasa a "Cédula Emitida" con clave de arranque y fecha de cédula
  Entonces se crea (o reutiliza) el res.partner agente por su Id interno (Nombre+RFC+CURP)
  Y se crea el puente res.partner.agente.aseguradora en estado "clave_arranque"
  Y el agente NO computa PCA mientras no alcance "clave_definitiva"   # R-PCA-03, Car.8/10
  Y el agente cuelga de su promotoría destino, nunca del holding       # R-ORG
  Y se crea un hr.employee vinculado al partner agente
  Y se avisa a la reclutadora y al promotor "agente habilitado (Clave de Arranque)"

Escenario: Idempotencia por Id interno
  Dado un candidato cuyo RFC+CURP ya existe como agente en otra promotoría/aseguradora
  Cuando se emite su cédula
  Entonces se reutiliza el agente existente y se le agrega la clave de la nueva aseguradora
  Y no se crea un res.partner duplicado                                # Car.2 (identidad)

Escenario: Idempotencia ante doble disparo
  Dado un candidato que ya fue convertido (ya tiene su puente para esa aseguradora)
  Cuando su write() vuelve a evaluar la etapa hired
  Entonces no se crea un segundo partner, puente ni empleado

Escenario: Guarda de datos mínimos
  Dado un candidato en "Cédula Emitida" sin clave, fecha de cédula, aseguradora, RFC o CURP
  Cuando se intenta la conversión
  Entonces el sistema la impide y exige los datos faltantes

Escenario: Puesto interno no crea agente ni puente
  Dado un candidato a puesto interno (embudo nativo de Odoo)
  Cuando llega a la etapa hired nativa ("Contract Signed")
  Entonces se da de alta hr.employee nativo
  Pero sin partner agente, sin puente y sin cédula
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Agregar campos clave_arranque, fecha_cedula, aseguradora_id (y reusar vat/curp de HU-1.2) · Backend
[ ] bca_clave_arranque (Char), bca_fecha_cedula (Date), bca_aseguradora_id (M2O aseguradora)
[ ] RFC (vat) y CURP (bca_curp) ya existen por HU-1.2; no se duplican

TT - Constraint: impedir hired sin clave + fecha cédula + aseguradora + RFC + CURP · Backend
[ ] @api.constrains que bloquea hired (figura comercial) sin los 5 datos
[ ] Test: falta cualquiera → bloquea con mensaje claro

TT - Extender write()/evento hired en etapa "Cédula Emitida" · Backend
[ ] Engancha en el write() existente; ramifica por job_id (solo job_reclutamiento_agente crea puente)
[ ] No reimplementa _bca_crear_partner_desde_contratado: lo extiende

TT - Crear/ubicar res.partner agente idempotente POR ID INTERNO · Backend
[ ] Busca agente existente por Id interno (vat + curp); si existe, lo reutiliza
[ ] Si no existe, lo crea con parent_id = bca_promotoria_destino_id (pasa _check_jerarquia)
[ ] NO resuelve ni deduplica por clave de agente
[ ] Test: agente preexistente se reutiliza (no duplica partner)

TT - Crear registro puente res.partner.agente.aseguradora (estado clave_arranque) · Backend
[ ] clave_agente = bca_clave_arranque, estado = 'clave_arranque', fecha_licencia = bca_fecha_cedula,
    aseguradora_id = bca_aseguradora_id
[ ] Respeta el unique (agente_id, aseguradora_id) y (aseguradora_id, clave_agente)
[ ] Test: el agente NO aparece en reportes de PCA (porque no es clave_definitiva)

TT - Crear hr.employee vinculado al partner agente · Backend
[ ] hr.employee con work_contact/address al partner agente
[ ] Idempotente (no crea empleado duplicado)

TT - Notificar a reclutadora y promotor "agente habilitado" · Backend
[ ] Mensaje/actividad a user_id (reclutadora) y al promotor de la promotoría destino

TT - Suite de pruebas de conversión · Backend
[ ] Tests de los 5 escenarios Gherkin de esta HU
[ ] Tests verdes en sandbox
```
- **Criterio de éxito:** al llegar a "Cédula Emitida" se crean —de forma idempotente por Id interno— el agente, el puente (**en `clave_arranque`**, sin computar PCA) y el empleado, con avisos; el sistema impide la conversión si faltan clave, fecha de cédula, aseguradora, RFC o CURP.

---

### HU-1.5 — Cerrar puestos internos por el embudo nativo de Odoo · 🟧 UI / IMPLEMENTADOR
*HU - Cerrar puestos internos por el embudo nativo - Capital Humano*

- **Por qué UI:** se apoya en el **embudo y el alta nativa de empleado** de Odoo al llegar a la etapa hired nativa; la ramificación por `job_id` (job no BCA = sin puente/cédula) ya queda cubierta en el método de HU-1.4.

**Criterios de aceptación**
```gherkin
Característica: Cerrar puestos internos por el embudo nativo de Odoo

Escenario: Alta interna sin partner agente ni puente
  Dado un candidato a puesto interno (ej. Auxiliar administrativa)
  Cuando llega a la etapa hired nativa de Odoo ("Contract Signed")
  Entonces se da de alta como hr.employee nativo
  Y no se crea partner agente, ni puente, ni cédula
  Y no ve ninguna etapa del embudo comercial BCA (ni Fase A ni Fase B)
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Verificar que los puestos internos usan el embudo nativo · UX
[ ] Un job no BCA no muestra ninguna de las 12 etapas comerciales
[ ] Cierra con la etapa hired nativa de Odoo (no hay etapa BCA "Alta Interna")

TT - Validar que el alta interna NO crea puente ni cédula (ramificación por job_id de L2) · Backend (dep. HU-1.4)
[ ] Test: candidato interno → hr.employee sí; partner agente/puente no
```
- **Criterio de éxito:** un auxiliar/reclutador/gerencial se recluta por el embudo nativo y se da de alta como empleado nativo, sin partner agente ni Fase B.

---

### HU-1.6 — Restringir visibilidad de candidatos por rol y sede · 🟦 CÓDIGO
*HU - Restringir visibilidad por rol y sede - Todos los roles*

- **Por qué código:** grupos de seguridad + **record rules (`ir.rule`)** con dominios dinámicos + campo `bca_sede_ids` en el usuario. El SDD §6 lo señala como la sección de mayor cuidado.
- **🔒 Bloqueada por SI-1** (mapa rol→qué ve). No se codifica hasta cerrar ese punto.

**Criterios de aceptación**
```gherkin
Característica: Visibilidad de candidatos por rol y sede

Escenario: La reclutadora solo ve sus candidatos
  Dado una reclutadora autenticada
  Cuando consulta el embudo
  Entonces solo ve los candidatos donde user_id es ella

Escenario: El promotor ve los de su(s) sede(s)
  Dado un promotor con bca_sede_ids = {Puebla, CDMX}
  Cuando consulta candidatos
  Entonces ve los candidatos cuya bca_sede_id está en sus sedes
  Pero no ve los de otras sedes

Escenario: Separación agentes ↔ promotorías
  Dado un usuario sin permiso combinado
  Cuando consulta el embudo
  Entonces ve candidatos de agentes O de promotorías, según su job_id permitido
  Pero no ambos a la vez

Escenario: Capital Humano ve la Fase B
  Dado un usuario de Capital Humano
  Cuando consulta candidatos
  Entonces ve los candidatos en etapas de habilitación (Fase B)

Escenario: Gerencia/Dirección ve el consolidado
  Dado un usuario de Gerencia o Dirección
  Cuando consulta el embudo
  Entonces ve el consolidado nacional sin restricción de sede
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Crear grupos group_bca_reclutadora / _promotor / _capital_humano · Backend
[ ] Tres grupos en el slot de la jerarquía existente
[ ] Sin privilege_id (no existe en este build); record rules [(1,'=',1)] para grupos no-agente

TT - Agregar bca_sede_ids (M2M) en usuario/empleado promotor · Backend
[ ] Campo M2M a bca.sede en res.users (o empleado promotor)

TT - ir.rule por user_id (reclutadora ve solo sus candidatos) · Backend
[ ] Regla con dominio user_id = uid
[ ] Test record rule

TT - ir.rule por sede (promotor ve los de su(s) sede(s)) · Backend
[ ] Dominio bca_sede_id in user.bca_sede_ids
[ ] Test record rule

TT - ir.rule separación agentes ↔ promotorías por job_id · Backend
[ ] Dominio por job_id (job_reclutamiento_agente vs job_captacion_promotoria)

TT - Regla Capital Humano por etapas de Fase B · Backend
[ ] Dominio por etapas de habilitación
[ ] Tests verdes en sandbox (incluye test_record_rules)
```
- **Criterio de éxito:** cada rol ve exactamente lo que le corresponde; un usuario no ve agentes y promotorías a la vez salvo permiso.

---

### HU-1.7 — Automatizar recordatorios y avisos por etapa · 🟨 HÍBRIDO
*HU - Automatizar recordatorios y avisos - Reclutadora/Capital Humano/Promotor*

- **Por qué híbrido:** son reglas de automatización (`base_automation`) que **se arman en la interfaz** pero el SDD pide **entregarlas versionadas como dato del módulo** (L3/L6).

**Criterios de aceptación**
```gherkin
Característica: Recordatorios y avisos automáticos por etapa

Escenario: Recordatorio de seguimiento a los 3 días
  Dado un candidato "no_localizado" o sin cambio de etapa en 3 días ordinarios
  Cuando se cumple la condición de tiempo
  Entonces el sistema crea una actividad/correo recordatorio a la reclutadora responsable

Escenario: Aviso de PDA apta a la reclutadora
  Dado un candidato con PDA apta cargada
  Cuando se guarda el resultado
  Entonces se avisa a la reclutadora

Escenario: Aviso de Acuerdo de Arranque a Capital Humano
  Dado un candidato que llega a "Acuerdo de Arranque"
  Cuando entra a esa etapa
  Entonces se avisa a Capital Humano que hay un candidato para habilitación

Escenario: Las reglas viajan versionadas
  Dado el módulo BCA_Seguros
  Cuando se instala/actualiza
  Entonces las reglas de automatización se cargan como dato del módulo (no quedan solo en la UI)
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Regla recordatorio 3 días / "no_localizado" a la reclutadora (L3) · Data
[ ] base_automation temporizada; exportada como data del módulo

TT - Regla no-show: contador de reagendaciones + sugerir Stand by al 2º (L5, prioridad baja) · Data
[ ] Usa bca_reagendaciones; al 2º no-show sugiere archivar

TT - Aviso "Acuerdo de Arranque" → Capital Humano (L6) · Data
[ ] Automatización de etapa; destinatario Capital Humano

TT - Aviso "PDA apta" → reclutadora (L6) · Data
[ ] Automatización al cargar PDA apta
[ ] Todas las reglas versionadas; tests/carga verdes en sandbox
```
- **Criterio de éxito:** los seguimientos y avisos ocurren solos; las reglas viajan versionadas en el módulo.

---

### HU-1.8 — Configurar motivos de rechazo y Stand by · 🟧 UI / IMPLEMENTADOR
*HU - Configurar motivos de rechazo y Stand by - Implementador*

- **Por qué UI:** motivos de rechazo **nativos** (SDD §4.5) y Stand by = **archivar** (SDD §4.6, comportamiento nativo + SOP).

**Criterios de aceptación**
```gherkin
Característica: Motivos de rechazo y Stand by

Escenario: Rechazar exige motivo
  Dado un candidato que sale del proceso
  Cuando se rechaza como "Declinado por Prospecto" o "Declinado por BCA"
  Entonces el motivo es obligatorio

Escenario: Stand by conserva historial y es reactivable
  Dado un candidato sin decisión
  Cuando se marca Stand by (archivar)
  Entonces sale del embudo activo pero conserva su historial
  Y puede reactivarse en la etapa donde se quedó
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Configurar motivos "Declinado por Prospecto" y "Declinado por BCA" · UX
[ ] Dos motivos nativos de rechazo configurados
[ ] Motivo obligatorio al rechazar (comportamiento nativo)

TT - (Opcional) Plantillas de correo por motivo · UX
[ ] Plantilla por motivo (opcional)

SOP - Stand by = archivar (operación, sin configuración) · documentación
[ ] Procedimiento documentado para el operador
```
- **Criterio de éxito:** rechazar exige motivo; Stand by conserva historial y es reactivable.

---

### HU-1.9 — Visualizar el embudo de conversión · 🟧 UI / IMPLEMENTADOR
*HU - Visualizar embudo de conversión - Gerencia/Dirección*

- **Por qué UI:** es el **SIC** del embudo; se arma sobre el Análisis de Postulantes nativo (pivote) y, opcionalmente, un tablero en Studio-Community (es reporte, no lógica).

**Criterios de aceptación**
```gherkin
Característica: Visualizar el embudo de conversión

Escenario: Embudo por dimensiones sin exportar a Excel
  Dado pólizas/candidatos distribuidos en la red de reclutamiento
  Cuando Gerencia abre el SIC de embudo
  Entonces ve cuántos candidatos avanzan de etapa a etapa
  Y puede cortar por reclutadora, sede, puesto, ramo y periodo
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Configurar pivote Análisis de Postulantes (reclutadora · sede · job · ramo · periodo) · UX
[ ] Vista pivote/embudo guardada con las dimensiones

TT - (Opcional) Tablero de embudo en Studio-Community · UX
[ ] Tablero visual (reporte, no lógica)
```
- **Criterio de éxito:** Gerencia ve el embudo de conversión sin exportar a Excel.

---

## 5. ÉPICA 2 — SIC: Tiempos de Habilitación

> Casi enteramente nativa. Depende de las etapas creadas en la Épica 1.

**SIC del entregable:** `SIC: Tiempos de Habilitación`

### HU-2.1 — Visualizar tiempos de habilitación por etapa · 🟧 UI / IMPLEMENTADOR
*HU - Visualizar tiempos de habilitación - Gerencia*

- **Por qué UI:** usa el **Análisis de Velocidad** nativo (tiempo en etapa).

**Criterios de aceptación**
```gherkin
Característica: Tiempos de habilitación por etapa

Escenario: Ver el tiempo en cada tramo de la Fase B
  Dado candidatos que recorren la Fase B
  Cuando Gerencia abre el SIC de tiempos
  Entonces ve cuánto tarda un candidato en cada etapa
  Y puede cortar por reclutadora, sede y puesto
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Configurar Análisis de Velocidad por reclutadora · sede · puesto · UX
[ ] Vista de velocidad/tiempo en etapa configurada con las dimensiones
[ ] Depende de las etapas de HU-1.1
```
- **Criterio de éxito:** se ve cuánto tarda un candidato en cada tramo de la Fase B, por reclutadora/sede.

---

## 6. ÉPICA 3 — SIC: Efectividad por Fuente, Campaña y Evento

> Casi nativa (fuentes + UTM). El campo `bca_evento` se crea en la Épica 1 (HU-1.2). Una decisión de BCA (SI-3) puede convertir una TT en código.

**SIC del entregable:** `SIC: Efectividad por Fuente, Campaña y Evento`

### HU-3.1 — Medir efectividad por fuente, campaña y evento · 🟧 UI / IMPLEMENTADOR (🔶 con TT condicional a código)
*HU - Medir efectividad por canal - Gerencia/Dirección*

- **Por qué UI:** se arma sobre Análisis de Fuentes + UTM nativos (`source_id`, `campaign_id`) más `bca_evento`.
- **🔒 Decisión asociada — SI-3:** ¿`bca_evento` se queda como **texto** o pasa a **lista oficial (modelo)**? Si BCA elige modelo, la TT condicional se vuelve **código**.

**Criterios de aceptación**
```gherkin
Característica: Efectividad por fuente, campaña y evento

Escenario: Comparar canales de reclutamiento
  Dado candidatos con fuente, campaña y evento capturados
  Cuando Gerencia abre el SIC de efectividad
  Entonces compara volumen y conversión por fuente (OCC, Facebook, Indeed, LinkedIn, referidos)
  Y por campaña y por evento (universidades, Cancún)

Escenario: (Condicional SI-3) Evento como lista oficial
  Dado que BCA decide manejar el evento como catálogo
  Cuando se migra bca_evento de texto a Many2one(bca.evento)
  Entonces los reportes agrupan por evento oficial sin texto libre inconsistente
```

**Tareas Técnicas (EDEP/TT)**
```
TT - Configurar pivote de Fuentes + UTM (source_id · campaign_id · bca_evento) · UX
[ ] Vista pivote con las tres dimensiones

🔶 TT (condicional) - Crear modelo bca.evento y migrar bca_evento a Many2one · Backend (solo si SI-3 = modelo)
[ ] Modelo bca.evento + migración de datos de texto a M2O
[ ] Script de migración para datos existentes
[ ] Tests verdes en sandbox
```
- **Criterio de éxito:** Gerencia compara la efectividad de cada fuente, campaña y evento de reclutamiento.

---

## 7. Tabla maestra — HU → Clasificación → Razón

| HU | Épica | Clasificación | Razón |
|---|---|---|---|
| HU-1.0 Catálogo de Sedes | 1 | 🟦 CÓDIGO | Modelo nuevo `bca.sede` |
| HU-1.1 Embudo y etapas | 1 | 🟧 UI | Etapas son configuración (SDD §4.1) |
| HU-1.2 Identificación y perfil (incl. RFC/CURP) | 1 | 🟦 CÓDIGO | Campos `bca_` + computed + identidad PCA (F2) |
| HU-1.3 PDA + compuerta riesgo | 1 | 🟦 CÓDIGO | Lógica L1 (constraint + actividad) |
| HU-1.4 Conversión en cédula | 1 | 🟦 CÓDIGO | Lógica L2 (write/hired + puente `clave_arranque` + empleado) |
| HU-1.5 Puestos internos | 1 | 🟧 UI | Alta nativa (ramificación ya en L2) |
| HU-1.6 Visibilidad por rol/sede | 1 | 🟦 CÓDIGO | Grupos + `ir.rule` (SDD §6) |
| HU-1.7 Recordatorios y avisos | 1 | 🟨 HÍBRIDO | Automatización versionada como dato |
| HU-1.8 Motivos rechazo / Stand by | 1 | 🟧 UI | Motivos nativos + archivar |
| HU-1.9 SIC Embudo | 1 | 🟧 UI | Pivote/tablero (reporte) |
| HU-2.1 SIC Tiempos | 2 | 🟧 UI | Análisis de Velocidad nativo |
| HU-3.1 SIC Efectividad | 3 | 🟧 UI 🔶 | UTM nativo; condicional a código (SI-3) |

---

## 8. Solicitudes de Información (SI) que bloquean construcción

| SI | Información requerida | HU que bloquea | Prioridad |
|---|---|---|---|
| **SI-1** | Mapa rol → qué ve + mecanismo de asignación promotor ↔ sede(s) (`bca_sede_ids`) | HU-1.6 | Alta |
| **SI-2** | ¿Habilitación de Promotor usa el flujo de cédula + puente o el de partner promotoría existente? | Alcance futuro de conversión | Alta |
| **SI-3** | ¿`bca_evento` como texto basta, o lista oficial (modelo)? | HU-3.1 (TT condicional) | Media |
| **SI-Sede** | Lista oficial de plazas para el catálogo | HU-1.0 (carga inicial) | Media |
| **SI-4** | **Criterio del paso Clave de Arranque → Clave Definitiva** (qué lo dispara, quién autoriza, qué auditoría). Hoy el puente expone `estado` editable a mano: promover a definitiva **activa el cómputo de PCA**, por lo que debe blindarse como acción controlada. **Fuera del alcance del reclutamiento** (HU futura). | (HU futura de PCA/agente) | Alta |

---

## 9. Encadenamiento con MIOR

- Cada **SIC** es una Épica (3 épicas).
- Cada **HU** lleva su `PLANNING - Sprint`, `REVIEW - Sprint`, `AGENDA - Capacitación de Flujo` y `DEV - Pase a Producción` al ejecutarse.
- Reglas de oro: ninguna HU cierra sin Pase a Producción en Hecho; la capacitación va siempre antes del pase y en ambiente de pruebas.
- **Secuencia sugerida (valor rápido visible):** HU-1.0 → 1.1 → 1.2 (incl. RFC/CURP) → 1.3 → 1.4 (flujo end-to-end, agente en `clave_arranque`) → 1.6 (visibilidad) → 1.9/2.1/3.1 (SICs) → 1.7/1.8 (afinación).
- **Dependencia PCA:** la promoción a `clave_definitiva` (SI-4) es una HU **posterior** a esta fase; el reclutamiento entrega al agente habilitado pero sin computar PCA.

---

*Hábitat Digital · HU + Criterios de Aceptación + TT — Reclutamiento de Agentes · Grupo BCA · v1.0 · Verificado contra las normas de la PCA · Alineado a MIOR*
