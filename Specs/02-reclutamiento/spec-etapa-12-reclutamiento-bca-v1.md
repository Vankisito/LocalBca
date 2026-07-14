---
titulo: Spec Etapa 12 — Reclutamiento y Habilitación de Agentes BCA_Seguros
fecha: 2026-06-30
autor: Hábitat Digital
version: v1.0
area: Recursos Humanos / Reclutamiento — Módulo BCA_Seguros
---

# Spec Etapa 12 — Reclutamiento y Habilitación de Agentes `BCA_Seguros`

> **Actualización D-21 (`v19.0.1.7.8`):** el flujo de conversión se separa en **3 fases** por
> cruce de umbral de etapa (ver Decisión D-21 y Changelog): (1) **Acuerdo de Arranque** crea el
> contacto `res.partner` —exige Promotoría + Sede + RFC + CURP— y hace el **traspaso a Capital
> Humano** (`interviewer_ids`/`user_id` + parámetro `bca_reclutamiento.capital_humano_user_id`);
> (2) **Cédula Emitida** asienta la clave `clave_arranque`; (3) **Clave Definitiva** (nueva etapa
> seq 13) crea el `hr.employee`. Renombres "Entrevista"→"Cena" y puestos→"Promotores"/"Agentes";
> validación de formato RFC/CURP; `bca_tipo_candidato` retirado. Las Fases A–E de abajo describen
> la construcción histórica; este bloque prevalece donde difieran.

> **Para:** Claude Code (y desarrollador humano)
> **Módulo:** `BCA_Seguros` (Odoo 19 Community) · Rama `desarrollo`
> **Tipo:** Nueva funcionalidad — integración del ciclo de carrera del agente con `hr_recruitment`.
> **Fuente de verdad de negocio:** `Specs/02-reclutamiento/` (BDD v1.3, SDD v1.1, análisis HU/TT, HU+criterios).
> **Documento director:** este spec ordena la construcción en Fases A–E; cada Fase es un commit con bump de versión.

---

## 1. Objetivo

Construir la **Fase de Reclutamiento y Habilitación de Agentes**: el ciclo de vida del candidato desde que se recibe/identifica hasta que su **cédula es emitida** y queda habilitado como agente **en Clave de Arranque**, listo para Desarrollo Comercial.

El reclutamiento se apoya en `hr_recruitment` (embudo de `hr.applicant`) y, al emitir la cédula, **alimenta el modelo puente** `res.partner.agente.aseguradora` ya existente, creando/ubicando al agente de forma idempotente. El agente recién habilitado **NO computa PCA** (solo `clave_definitiva` computa; la promoción a definitiva es proceso interno posterior fuera de alcance — SI-4).

Esta etapa traduce las **3 épicas (SICs) / 12 HUs** del SDD a entregables de ingeniería con criterios de aceptación verificables y SOPs de configuración para el implementador.

---

## 2. Reglas no negociables

Prevalecen sobre cualquier conveniencia de implementación:

1. **No hay conversión sin cédula emitida.** El evento `hired` (crea agente + puente + empleado) ocurre **únicamente** en la etapa "Cédula Emitida" del job `job_reclutamiento_agente`. El hito "Acuerdo de Arranque" NO dispara conversión.
2. **El puente nace en `clave_arranque`, nunca en `clave_definitiva`** (F1 crítico). Asentar `clave_definitiva` activaría cómputo de PCA/comisiones indebido (`BDD_BCA_Seguros.md` Car. 8 y 10).
3. **Identidad por Id interno = Nombre + RFC + CURP** (norma PCA Car. 2). La idempotencia se resuelve por `vat` + `bca_curp`, **nunca** por la clave de agente (que varía por aseguradora).
4. **La conversión vive en el override de `write()` (Python), no en `base.automation`.** Crea registros transaccionales (partner + puente + empleado) que deben ser atómicos e idempotentes. `base.automation` se reserva para avisos/recordatorios.
5. **El agente cuelga de exactamente una promotoría, nunca del holding.** Respetar `_check_jerarquia` existente (`parent_id = bca_promotoria_destino_id`).
6. **Reusar antes que crear.** RFC→`vat`, nombre→`partner_name`, tel→`partner_phone`, correo→`email_from`, reclutadora→`user_id`, fuente→`source_id`, campaña→`campaign_id`. Selecciones `GENERO`/`RAMO` se importan, no se redefinen.
7. **Etapas del embudo y motivos de rechazo son datos del módulo** (XML), no configuración manual — para reproducibilidad en CI/sandbox. Referenciar por `env.ref('BCA_Seguros.stage_…')` y comparar por `sequence`, nunca por ID hardcodeado (evita el drift tipo D-13).
8. **Convenciones Odoo 19 del proyecto:** `invisible="…"` (no `attrs=`); `groups=` en campos para seguridad; smart buttons `type="object"`; `<group>` en `<search>` sin atributos; todo `ref` con prefijo `BCA_Seguros.`; todo modelo nuevo con entrada en `ir.model.access.csv`; `from __future__ import annotations` + type hints.

---

## 3. Decisiones de negocio confirmadas (SIs resueltos)

| SI | Tema | Decisión | Impacto |
|---|---|---|---|
| **SI-1** | Visibilidad del embudo | **Por reclutadora asignada.** Reclutadora ve `user_id == uid`; Director Comercial y Director ven todo. | Fase E con record rule sobre `hr.applicant` (no se difiere). |
| **SI-2** | Rol del Promotor | **Solo destino + notificación.** No opera el embudo; es `bca_promotoria_destino_id` y recibe actividad/aviso al habilitarse el agente. | Capital Humano/reclutadora mueven etapas. |
| **SI-3** | "Evento" (efectividad) | **Campo simple ahora** (`bca_evento` Char en `hr.applicant`). | Sin modelo `bca.evento`; mejora futura si BCA lo pide. |
| **SI-Sede** | Catálogo de plazas | **Seed con lista que pasa el usuario.** Modelo `bca.sede` + vista + `data/bca_sedes_iniciales.xml`. | Lista oficial pendiente; seed placeholder hasta cerrar Fase A. |
| **SI-4** | `clave_arranque → clave_definitiva` | **Fuera de alcance.** El reclutamiento entrega en `clave_arranque`. | Promoción a definitiva = HU futura con permiso + auditoría. |
| Alcance | HUs código + config | **Todo.** Código en el módulo + SOPs del implementador para HUs de UI. | §7 documenta los SOP. |

---

## 4. Arquitectura técnica por Fase

**Una sola Etapa 12 en Fases A–E atómicas** (commit + bump por fase, como Etapa 3.5). Dependencias: **A → B → C → D**; **E** puede ir en paralelo a D (SI-1 ya resuelto) pero se numera al final por ser la de mayor cuidado en seguridad. Regla dura: *sedes y campos antes de la conversión; conversión antes de reportes*.

| Fase | Versión | Nombre | HUs |
|---|---|---|---|
| A | `19.0.1.7.0` | Cimientos: `bca.sede` + campos identificación/perfil + embudo 12 etapas | 1.0, 1.1, 1.2 |
| B | `19.0.1.7.1` | PDA + compuerta de riesgo (L1) | 1.3 |
| C | `19.0.1.7.2` | **Núcleo:** conversión en Cédula Emitida (L2) + RFC/CURP + puente `clave_arranque` | 1.4, 1.5 |
| D | `19.0.1.7.3` | Automatizaciones (L3/L5/L6) + motivos de rechazo + SICs/reportes | 1.7, 1.8, 1.9, 2.1, 3.1 |
| E | `19.0.1.7.4` | Visibilidad por reclutadora (record rules) | 1.6 |

### Fase A — Cimientos (`19.0.1.7.0`)

**Objetivo:** modelo `bca.sede`, todos los campos `bca_` de identificación/perfil en `hr.applicant` (sin lógica), y el embudo de 12 etapas como datos del módulo.

**Archivos a crear:**

| Archivo | Contenido clave |
|---|---|
| `models/bca_sede.py` | Modelo `bca.sede`: `name` (Char req, `_rec_name`), `codigo` (Char), `active` (Boolean default True). |
| `views/bca_sede_views.xml` | list/form + `action_bca_sede` + menú en Configuración. |
| `data/bca_sedes_iniciales.xml` | Catálogo seed (`noupdate="1"`) — **lista oficial pendiente de SI-Sede; placeholder mínimo**. |
| `data/hr_recruitment_stages.xml` | 12 etapas comerciales (agente + promotoría) como datos del módulo. |
| `tests/test_bca_sede.py` | CRUD sede, `_rec_name`, archivado. |

**Archivos a modificar:**

| Archivo | Cambio |
|---|---|
| `models/hr_applicant.py` | Campos `bca_` de identificación/perfil (§4.2 SDD), sin lógica; `bca_edad` computed desde `bca_fecha_nacimiento`; **reusar** selecciones `GENERO`/`RAMO` por import. |
| `views/hr_applicant_views.xml` | Pestañas Identificación / Perfil / Origen vía `<xpath>`. |
| `models/__init__.py` | Import `bca_sede`. |
| `__manifest__.py` | Bump `19.0.1.7.0`; añadir `bca_sede_views.xml`, `bca_sedes_iniciales.xml`, `hr_recruitment_stages.xml` (sede antes del candidato; stages antes del menú). |
| `tests/test_hr_applicant.py` | Tests de campos + computed edad + no-duplicación. |

**Campos nuevos en `hr.applicant`:** `bca_sede_id` (M2o `bca.sede`), `bca_ramo` (reusa `RAMO`), `bca_genero` (reusa `GENERO`), `bca_fecha_nacimiento` (Date), `bca_edad` (Integer computed), `bca_institucion` (Char), `bca_perfil_academico` (Char/Selection), `bca_perfil_laboral` (Char/Selection), `bca_tiene_cedula_previa` (Boolean), `bca_tipo_candidato` (Selection), `bca_referido_por` (Char/M2o), `bca_folio_cv` (Char), `bca_evento` (Char — SI-3), `bca_contactado` (Boolean), `bca_entrevistado` (Boolean), `bca_reagendaciones` (Integer default 0).

> **Revisión post-cierre (D-19, `19.0.1.7.5`):** tras revisar la UI se eliminaron 7 de estos campos por redundancia con lo nativo/embudo: `bca_perfil_academico` (→ `type_id`/Grado nativo), `bca_evento` (→ `campaign_id`), `bca_referido_por` (→ `source_id`), `bca_tiene_cedula_previa` (→ se infiere de Habilitación), y `bca_contactado`/`bca_entrevistado`/`bca_reagendaciones` (→ embudo de etapas + actividades). Se conservan `bca_folio_cv` (Identificación) y `bca_ramo`/`bca_perfil_laboral`/`bca_tipo_candidato` (pestaña Detalles nativa). Las pestañas propias "Perfil" y "Origen" desaparecen.

**Las 12 etapas (embudo comercial, `job_reclutamiento_agente` y `job_captacion_promotoria`):** 1 Recibido · 2 Prospección · 3 Café · 4 Entrevista · 5 Evaluación PDA · 6 Acuerdo de Arranque · 7 Clave de Arranque · 8 Inscripción CIA · 9 Curso de Cédula · 10 Examen · 11 **Cédula Emitida** (`hired_stage=True`) · 12 En Desarrollo Comercial. Agentes y promotorías comparten este embudo (D-20). Los **puestos internos** usan el **embudo nativo de Odoo**, sin etapas BCA (la etapa "Contratado (Alta Interna)" fue retirada en `19.0.1.7.7`).

**Checklist Fase A:**
- [ ] `bca.sede` CRUD desde UI y visible como M2o en el candidato.
- [ ] 12 etapas cargan como datos del módulo, scopeadas a ambos jobs comerciales.
- [ ] "Cédula Emitida" con `hired_stage=True` (única etapa hired del embudo comercial).
- [ ] Form del candidato muestra todos los campos sin error XML.
- [ ] Cero campos duplicados (RFC usa `vat`; género/ramo reusan selecciones) — test `test_no_campos_duplicados`.

### Fase B — PDA + compuerta de riesgo L1 (`19.0.1.7.1`)

**Objetivo:** campos PDA y lógica L1 (riesgo computed, bloqueo de avance, actividad al promotor).

**Modificar `models/hr_applicant.py`:** `bca_pda_nivel` (Selection 5 niveles), `bca_pda_correlacion` (Float), `bca_pda_perfil` (Char), `bca_pda_visto_bueno_promotor` (Boolean), `bca_pda_riesgo` (Boolean computed: nivel ∈ {baja, no_ideal}). **L1:** `@api.constrains('stage_id','bca_pda_riesgo','bca_pda_visto_bueno_promotor')` que bloquea avanzar más allá de "Evaluación PDA" si `bca_pda_riesgo and not bca_pda_visto_bueno_promotor`; al activarse el riesgo, crear `mail.activity` "Visto bueno requerido" para el promotor de la promotoría destino (consistente con SI-2: solo notificación).

**Riesgo de diseño:** la etapa de corte se resuelve con `env.ref('BCA_Seguros.stage_evaluacion_pda')` comparando por `sequence` (no hardcodear ID). Las 12 etapas llevan `job_ids` → `[job_reclutamiento_agente, job_captacion_promotoria]` para no aparecer en puestos internos (D-20).

**Checklist Fase B:**
- [ ] PDA "baja"/"no_ideal" ⇒ `bca_pda_riesgo=True` y crea actividad al promotor.
- [ ] Avanzar más allá de "Evaluación PDA" sin VoBo ⇒ `ValidationError`.
- [ ] Con VoBo ⇒ avanza; sin aprobación ⇒ se puede rechazar como "Declinado por BCA".

### Fase C — Conversión en Cédula Emitida L2 (`19.0.1.7.2`) — NÚCLEO

**Objetivo:** datos de habilitación + constraint de guarda + conversión idempotente que crea partner agente + puente `clave_arranque` + `hr.employee`.

**Modificar `models/hr_applicant.py`:**
- Campos: `bca_clave_arranque` (Char), `bca_fecha_cedula` (Date), `bca_aseguradora_id` (M2o `res.partner`, domain aseguradora), `bca_curp` (Char). RFC ya es `vat`.
- **Constraint guarda L2:** `@api.constrains('stage_id')` — si la etapa es `hired_stage=True` **y** el job es `job_reclutamiento_agente`, exige los 5 datos (`bca_clave_arranque`, `bca_fecha_cedula`, `bca_aseguradora_id`, `vat`, `bca_curp`); si falta alguno ⇒ `ValidationError` con mensaje claro. No aplica a promotorías ni a puestos internos (embudo nativo).
- **Reescribir `_bca_crear_partner_desde_contratado()`** (hoy idempotente por nombre): idempotencia **por Id interno = Nombre+RFC+CURP** — buscar partner agente por `('vat','=',vat),('bca_curp','=',curp)` (+ nombre normalizado); si existe (aunque sea en otra promotoría/aseguradora), reutilizar y solo agregar la clave de la nueva aseguradora. Luego:
  1. Crear/ubicar partner agente (`bca_tipo='agente'`, `parent_id=bca_promotoria_destino_id`, set `bca_curp`).
  2. Crear `res.partner.agente.aseguradora` con `estado='clave_arranque'` (**F1 — NO definitiva**), `clave_agente=bca_clave_arranque`, `fecha_licencia=bca_fecha_cedula`, `aseguradora_id=bca_aseguradora_id`. Los UNIQUE existentes del puente protegen contra duplicados; capturar `IntegrityError` y reutilizar.
  3. Crear `hr.employee` vinculado al partner agente (`work_contact_id`).
  4. `message_post` + actividad a reclutadora (`user_id`) y promotor.
- **Ramificación HU-1.5:** job interno (cualquier otro) ⇒ alta nativa de empleado, sin partner agente, sin puente, sin cédula. El filtro por `job_id` ya existe; mantenerlo.

**Modificar `models/res_partner.py`:** agregar `bca_curp` (Char, `index=True`) como parte del Id interno PCA. Si se exige unicidad, complementar con `@api.constrains` (cuidado `NULL≠NULL`, §2.4.5).

**Modificar `views/hr_applicant_views.xml`:** grupo "Habilitación" (clave_arranque, fecha_cedula, aseguradora, CURP; RFC=`vat`).

**Migración:** `migrations/19.0.1.7.2/post-migrate.py` solo si hace falta backfill (campos nuevos → probablemente no).

**Checklist Fase C:**
- [ ] No se llega a "Cédula Emitida" sin los 5 datos — `test_hired_sin_5_datos_bloquea`.
- [ ] Conversión crea partner + puente(`clave_arranque`) + empleado, idempotente por Id interno — `test_conversion_crea_puente_clave_arranque`, `test_conversion_crea_employee`.
- [ ] Agente existente en otra aseguradora se reutiliza; se le agrega la nueva clave — `test_idempotencia_por_rfc_curp`.
- [ ] Agente recién habilitado **no** aparece en reportes PCA (E9) — `test_agente_clave_arranque_no_computa_pca`.
- [ ] Puesto interno (embudo nativo) no crea partner agente ni puente — `test_job_interno_nativo_no_crea_puente_ni_agente`.

### Fase D — Automatizaciones + motivos + SICs (`19.0.1.7.3`)

**Objetivo:** automatizaciones versionadas (L3/L5/L6), motivos de rechazo seed, y los 3 SICs (reportes).

**Crear:**

| Archivo | Contenido |
|---|---|
| `data/base_automation_reclutamiento.xml` | L3 (recordatorio 3 días / no localizado), L5 (no-show → Stand by), L6 (avisos por etapa) como `base.automation`. |
| `data/hr_refuse_reasons.xml` | "Declinado por Prospecto" y "Declinado por BCA" (`hr.applicant.refuse.reason`). |

**SICs (HU-1.9 / 2.1 / 3.1):** configuración nativa (pivote de postulantes, velocidad de habilitación, fuentes+UTM+evento). Se documentan como **SOP** (§7). Opcional: una `ir.actions.act_window` con vista pivot/graph preconfigurada sobre `hr.applicant`, dimensiones `user_id · bca_sede_id · job_id · bca_ramo · bca_evento`.

**Checklist Fase D:**
- [ ] Rechazar exige motivo; los 2 motivos están seed — `test_refuse_reasons_seed`.
- [ ] Recordatorio 3 días y avisos por etapa disparan (verificable por automation/cron).
- [ ] Pivote de embudo agrupa por sede/reclutadora/ramo/periodo sin Excel.

### Fase E — Visibilidad por reclutadora (`19.0.1.7.4`)

**Objetivo:** grupos de reclutamiento y record rules según SI-1.

**Crear/modificar:**

| Archivo | Cambio |
|---|---|
| `security/groups.xml` | `group_bca_reclutadora`, `group_bca_capital_humano` como **hermanos** (no en la cadena lineal de los 5 existentes). |
| `security/record_rules.xml` | `ir.rule` sobre `hr.applicant`: reclutadora `user_id == uid`; Director Comercial / Director `[(1,'=',1)]` explícito (A3); separación por `job_id`. |
| `security/ir.model.access.csv` | ACL para `bca.sede` y nuevos grupos. |
| `tests/test_record_rules.py` | Visibilidad por rol. |

**Checklist Fase E:**
- [ ] Reclutadora ve solo sus candidatos (`user_id == uid`).
- [ ] Director ve todo (reglas `[(1,'=',1)]` evitan el bug de `implied_ids`).
- [ ] Separación agente/promotoría por `job_id`.

---

## 5. Decisiones a registrar (en `Decisiones.md`)

Registrar antes/durante la construcción de la fase correspondiente:

- **D-14** — Puente al emitir cédula = `estado='clave_arranque'` (NO `clave_definitiva`); el agente recién habilitado no computa PCA (F1, Car. 8/10).
- **D-15** — Idempotencia de la conversión por **Id interno (Nombre+RFC+CURP)**, nunca por clave de agente (F2/F3, Car. 2).
- **D-16** — "Evento" se modela como **campo de texto** `bca_evento` (SI-3); modelo `bca.evento` queda como mejora futura.
- **D-17** — La conversión (partner+puente+empleado) vive en el **override de `write()`** en Python (atómica/idempotente), no en `base.automation`; las automatizaciones solo emiten avisos.
- **D-18** — Visibilidad del embudo de reclutamiento **por reclutadora asignada** (`user_id`); Director Comercial+ ven todo (SI-1). Grupos nuevos como hermanos, fuera de la cadena `implied_ids` (A3).

---

## 6. Riesgos técnicos Odoo 19

1. **Conversión en override de `write()`, no en `base.automation`** (D-17) — atomicidad e idempotencia de partner+puente+empleado.
2. **Idempotencia por Id interno** (F2/F3) — `search` por `vat`+`bca_curp` (+nombre normalizado: cuidar espacios/acentos); capturar `IntegrityError` de los UNIQUE del puente y reutilizar.
3. **Estado del puente = `clave_arranque`** (F1) — asentar `clave_definitiva` activaría PCA indebido; `test_agente_clave_arranque_no_computa_pca` es la red de seguridad (cruzar con reportes E9).
4. **Etapas como datos del módulo + `env.ref` por `sequence`** — evita el drift tipo D-13 en CI/sandbox; Fase B con `job_ids` específicos.
5. **`bca_curp` nullable + UNIQUE `NULL≠NULL`** (§2.4.5) — complementar con `@api.constrains` Python si se exige unicidad.
6. **Grupos nuevos fuera de la cadena `implied_ids`** (§2.4.3, A3) — reclutadora/capital humano como hermanos; `[(1,'=',1)]` explícito para directores.
7. **`hr.employee` para no-empleado** (SDD §5 L2) — el agente no es empleado legal; se usa por gestión, vinculado por `work_contact_id`.

---

## 7. SOPs de configuración (implementador) — HUs de UI

Estas HUs no son código del módulo; se entregan como procedimiento operativo y se documentan aquí:

- **HU-1.1 (Kanban del embudo):** verificar que las 12 etapas (datos del módulo) muestren columnas en orden por `sequence`; kanban agrupado por `stage_id`.
- **HU-1.8 (Afinación de vistas):** filtros guardados por sede / reclutadora / ramo / evento en la vista search de `hr.applicant`.
- **HU-1.9 (SIC postulantes):** vista pivote de `hr.applicant` (dimensiones sede × ramo × etapa × periodo); guardar como acción.
- **HU-2.1 (SIC tiempos de habilitación):** medición de velocidad por diferencia de fechas de etapa (nativo de `hr_recruitment`); pivote por sede/promotoría.
- **HU-3.1 (SIC efectividad por fuente/campaña/evento):** pivote por `source_id` / `campaign_id` / `bca_evento`; con SI-3 = texto, se agrupa por `bca_evento`.

---

## 8. Trazabilidad HU → Fase

| HU | Descripción | Fase | Tipo |
|---|---|---|---|
| 1.0 | Carga de sedes (`bca.sede`) | A | Código + seed |
| 1.1 | Embudo de 12 etapas (kanban) | A | Config (SOP) |
| 1.2 | Datos de identificación / perfil (incl. RFC/CURP a nivel campo) | A | Código |
| 1.3 | Evaluación PDA + compuerta de riesgo (L1) | B | Código |
| 1.4 | Conversión en Cédula Emitida (L2) → agente + puente `clave_arranque` | C | Código |
| 1.5 | Alta interna (sin partner agente) | C | Código |
| 1.6 | Visibilidad por reclutadora | E | Código |
| 1.7 | Automatizaciones (recordatorios/avisos) | D | Híbrido |
| 1.8 | Afinación de vistas/filtros | D | Config (SOP) |
| 1.9 | SIC postulantes | D | Config (SOP) |
| 2.1 | SIC tiempos de habilitación | D | Config (SOP) |
| 3.1 | SIC efectividad por fuente/campaña/evento | D | Config (SOP) |

---

## 9. Verificación en sandbox (todas las fases)

```bash
docker exec odoo_golden odoo -d sandbox_bca1 -u BCA_Seguros \
  --test-enable --test-tags BCA_Seguros --stop-after-init --no-http \
  --logfile=/var/log/odoo/test_e12.log
tail -n 120 /var/log/odoo/test_e12.log
```

Esperado por fase: `0 failed, 0 error(s)`, sin `DeprecationWarning`. Cada fase cierra solo cuando su checklist pasa en sandbox.

> La consola del sandbox queda vacía (logfile en `odoo.conf`); capturar con `--logfile` y leer el archivo (ver `reference-sandbox-test-output`).

---

## 10. Fuera de alcance

- **SI-4** — Promoción `clave_arranque → clave_definitiva` (habilita PCA): proceso interno posterior, HU futura. Debe blindarse como **acción controlada** con permiso + auditoría; hoy el puente expone `estado` editable a mano y eso debe corregirse en esa HU, no aquí.
- **SI-2 ampliado** — Flujo del Promotor co-operando el embudo (queda en "solo destino + notificación").
- **Modelo `bca.evento`** (SI-3) — se usa campo de texto; el catálogo relacional es mejora futura.
- **Flujo de Captación de Promotoría** (`job_captacion_promotoria`) — conserva su comportamiento actual; no se modifica en esta etapa.

---

## 11. Protocolo de cierre (obligatorio, por fase)

Al cerrar cada Fase:
1. `__manifest__.py` — bump a la versión de la fase (`19.0.1.7.X`).
2. `Specs/Changelog.md` — entrada con qué se hizo, archivos, decisiones, verificación sandbox.
3. `Specs/Decisiones.md` — registrar D-14…D-18 según corresponda a la fase.
4. `Specs/TESTS_COVERAGE.md` — registrar los tests nuevos.
5. `Specs/Plan de Desarrollo.md §4` — marcar `[x]` el checklist de la fase + fecha.
6. Commit: `feat(reclutamiento): Etapa 12 Fase X — <descripción> · 19.0.1.7.X`.
