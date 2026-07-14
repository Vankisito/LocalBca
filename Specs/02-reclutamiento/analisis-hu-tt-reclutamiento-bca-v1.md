---
titulo: Análisis de Historias de Usuario y Tareas Técnicas — Reclutamiento y Habilitación de Agentes — Grupo BCA
fecha: 2026-06-26
autor: Hábitat Digital
version: v1.0
area: Entrega
---

![Hábitat Digital](https://www.habitatdigital.net/web/image/website/1/logo/Habitat%20Digital?unique=cbdfacc)

# Análisis de Historias de Usuario y Tareas Técnicas — Reclutamiento BCA

> Desglose del **SDD v1.0** ("Reclutamiento y Habilitación de Agentes — Grupo BCA") en **Épicas → Historias de Usuario (HU) → Tareas Técnicas (TT)**, alineado a la metodología **MIOR**. Cada HU indica si se resuelve **con código** (módulo `BCA_Seguros`) o **por configuración desde la interfaz de Odoo** (implementador, sin código). Plataforma: **Odoo 19 Community (nube)**, módulo `BCA_Seguros` → bump `19.0.1.5.0`.

Este documento es el insumo para la tarea MIOR **`BACKLOG - Creación: BCA Seguros`**.

---

## 1. Cómo leer la clasificación

La pregunta central que respondemos por cada HU es: **¿quién la ejecuta y dónde vive?** Esto define si requiere un desarrollador o si un consultor implementador la puede hacer desde la interfaz.

| Marca | Significa | Quién la ejecuta | Dónde vive |
|---|---|---|---|
| 🟦 **CÓDIGO** | Lógica, modelos, campos que el Python lee/escribe, constraints, computed, seguridad | Desarrollador | Módulo `BCA_Seguros` (Git, versionado) |
| 🟧 **UI / IMPLEMENTADOR** | Configuración nativa de Odoo, sin código | Consultor implementador | Interfaz de Odoo (configuración) |
| 🟨 **HÍBRIDO** | Se arma/prototipa en la interfaz (p. ej. automatizaciones) pero se entrega versionado como **dato del módulo** | Implementador + Desarrollador (empaqueta) | UI + `BCA_Seguros` (data) |

**Criterio base (del SDD, principio 2 y decisión D1):** la lógica vive en código; la herramienta tipo Studio-Community se reserva para **tableros y prototipos de vista, nunca para lógica**. Por eso todo campo `bca_` que la lógica L1/L2 lee o escribe —o que es *computed*— se clasifica como **código**, aunque "parezca" configuración.

---

## 2. Resumen ejecutivo de la distribución

12 Historias de Usuario en 3 Épicas. El esfuerzo de **desarrollo se concentra en la Épica 1** (modelo de datos + lógica de negocio + seguridad); las Épicas 2 y 3 son casi enteramente **configuración**, tal como anticipa el SDD §7.

| Clasificación | HUs | Implicación de quién la hace |
|---|---|---|
| 🟦 CÓDIGO | 5 | Requieren **desarrollador** sobre `BCA_Seguros` |
| 🟧 UI / IMPLEMENTADOR | 6 | Las puede hacer un **consultor implementador** desde Odoo |
| 🟨 HÍBRIDO | 1 | Implementador arma, desarrollador empaqueta como dato del módulo |
| 🔶 Condicional | (1 TT) | Una TT de Épica 3 pasa a código solo si BCA decide "Evento" como modelo |

**Lectura para entrega:** la Épica 1 necesita acompañamiento de desarrollo y supervisión directa; las Épicas 2 y 3 (los reportes/SICs) se pueden delegar a un consultor una vez que existan los campos.

---

## 3. ÉPICA 1 — SIC: Embudo de Conversión de Reclutamiento

> **Épica ancla.** Carga la fundación del flujo (etapas, campos, modelo de sede, lógica de conversión y seguridad) porque el reporte de embudo no puede existir sin que el flujo opere de extremo a extremo. Por volumen, es probable que abarque **2 sprints**. Las Épicas 2 y 3 dependen de los campos creados aquí.

**SIC del entregable:** `SIC: Embudo de Conversión de Reclutamiento`

---

### HU-1.0 — Administrar el catálogo de Sedes (plazas) · 🟦 CÓDIGO
*HU - Administrar catálogo de Sedes - Gerencia/Admin*

- **Por qué código:** es un **modelo nuevo** (`bca.sede`, §4.3), no existe de fábrica. El campo `bca_sede_id` del candidato lo referencia y la seguridad por sede lo usa.
- **TTs:**
  - `DEV - Crear modelo bca.sede (name/codigo/active)` · Backend
  - `DEV - Crear vistas list/form + menú de configuración de Sede` · UX
  - `DEV - Cargar catálogo inicial de plazas` · Data
- **SI asociada:** `SI - Lista oficial de plazas (CDMX, Puebla, GDL, QRO, HGO, MTY…) - Reclutamiento`
- **Criterio de éxito:** el cliente puede dar de alta/baja una plaza sin tocar código y la sede aparece como eje de reportes y visibilidad.

---

### HU-1.1 — Configurar el embudo y las etapas job-specific · 🟧 UI / IMPLEMENTADOR
*HU - Configurar embudo y etapas - Implementador*

- **Por qué UI:** el SDD §4.1 es explícito: **las etapas son configuración (sin código)**.
- **TTs:**
  - `DEV - Crear etapas del embudo comercial (Recibido → En Desarrollo Comercial)` · UX
  - `DEV - Marcar las 12 etapas como job-specific de ambas figuras comerciales (job_reclutamiento_agente, job_captacion_promotoria)` · UX
  - `DEV - Marcar hired_stage=True solo en "Cédula Emitida"` · UX
- **Criterio de éxito:** los candidatos comerciales (agentes y promotorías) ven Fase A+B; un puesto interno usa el embudo nativo de Odoo, sin etapas BCA (D-20).

---

### HU-1.2 — Registrar datos de identificación y perfil del candidato · 🟦 CÓDIGO
*HU - Registrar datos de identificación y perfil - Reclutadora*

- **Por qué código:** son **campos nuevos `bca_` en `hr.applicant`** (§4.2); varios alimentan lógica o son *computed* (edad). Por D1 no se crean con Studio.
- **TTs:**
  - `DEV - Agregar campos de identificación bca_ (sede_id, ramo, genero, fecha_nacimiento)` · Backend
  - `DEV - Computar edad desde bca_fecha_nacimiento` · Backend
  - `DEV - Agregar campos de perfil/origen (institucion, perfiles, tipo_candidato, referido, folio_cv, evento, contactado, entrevistado, tiene_cedula_previa)` · Backend
  - `DEV - Insertar campos en la vista del candidato (form)` · UX
  - `DEV - Validar mapeo a campos nativos sin duplicar (cero campos duplicados)` · Backend
- **Criterio de éxito:** la reclutadora captura todo el perfil en un formulario; el inventario de `BCA_Seguros` no tiene campos duplicados.

---

### HU-1.3 — Capturar y evaluar PDA con compuerta de riesgo · 🟦 CÓDIGO
*HU - Evaluar PDA con compuerta de riesgo - Reclutadora/Promotor*

- **Por qué código:** campos PDA + **lógica L1** (`@api.constrains`, *computed*, creación de actividad, bloqueo de avance).
- **TTs:**
  - `DEV - Agregar campos PDA (nivel, correlacion, perfil, visto_bueno_promotor)` · Backend
  - `DEV - Computar bca_pda_riesgo (True si nivel ∈ {baja, no_ideal})` · Backend
  - `DEV - Constraint L1: bloquear avance más allá de "Evaluación PDA" sin VoBo` · Backend
  - `DEV - Crear actividad "Visto bueno requerido" al promotor de la sede destino` · Backend
- **Criterio de éxito:** un perfil de riesgo no puede avanzar sin el visto bueno del promotor; si nadie aprueba, puede rechazarse como "Declinado por BCA".

---

### HU-1.4 — Convertir candidato a agente habilitado al emitir cédula · 🟦 CÓDIGO
*HU - Convertir candidato a agente habilitado - Sistema/Reclutadora/Promotor*

- **Por qué código:** es el **corazón de la lógica L2** (extiende `write()`/`hired`, constraint de guarda, alta idempotente de partner + puente + empleado).
- **TTs:**
  - `DEV - Agregar campos clave_arranque, fecha_cedula, aseguradora_id` · Backend
  - `DEV - Constraint: impedir hired sin clave + fecha de cédula + aseguradora` · Backend
  - `DEV - Extender write()/evento hired en etapa "Cédula Emitida"` · Backend
  - `DEV - Crear/ubicar res.partner agente (idempotente)` · Backend
  - `DEV - Crear registro puente res.partner.agente.aseguradora (estado clave_definitiva)` · Backend
  - `DEV - Crear hr.employee vinculado al partner agente` · Backend
  - `DEV - Notificar a reclutadora y promotor "agente habilitado"` · Backend
- **Criterio de éxito:** al llegar a "Cédula Emitida" se crean —de forma idempotente— el agente, el puente y el empleado, con avisos; el sistema impide la conversión si faltan los tres datos.

---

### HU-1.5 — Cerrar puestos internos por el embudo nativo de Odoo · 🟧 UI / IMPLEMENTADOR
*HU - Cerrar puestos internos por el embudo nativo - Capital Humano*

- **Por qué UI:** se apoya en el **embudo y el alta nativa de empleado** de Odoo al llegar a la etapa hired nativa; la ramificación por `job_id` (job no BCA = sin puente/cédula) ya queda cubierta en el método de HU-1.4.
- **TTs:**
  - `DEV - Verificar que los puestos internos usan el embudo nativo (sin etapas BCA)` · UX
  - `DEV - Validar que el alta interna NO crea puente ni cédula (ramificación por job_id de L2)` · Backend *(dependencia de HU-1.4)*
- **Criterio de éxito:** un auxiliar/reclutador/gerencial se recluta por el embudo nativo y se da de alta como empleado nativo, sin partner agente ni Fase B (D-20).

---

### HU-1.6 — Restringir visibilidad de candidatos por rol y sede · 🟦 CÓDIGO
*HU - Restringir visibilidad por rol y sede - Todos los roles*

- **Por qué código:** grupos de seguridad + **record rules (`ir.rule`)** con dominios dinámicos + campo `bca_sede_ids` en el usuario. El SDD §6 lo señala como la sección de mayor cuidado.
- **🔒 Bloqueada por SI-1** (mapa rol→qué ve). No se codifica hasta cerrar ese punto.
- **TTs:**
  - `DEV - Crear grupos group_bca_reclutadora / _promotor / _capital_humano` · Backend
  - `DEV - Agregar bca_sede_ids (M2M) en usuario/empleado promotor` · Backend
  - `DEV - ir.rule por user_id (reclutadora ve solo sus candidatos)` · Backend
  - `DEV - ir.rule por sede (promotor ve los de su(s) sede(s))` · Backend
  - `DEV - ir.rule separación agentes ↔ promotorías por job_id` · Backend
  - `DEV - Regla Capital Humano por etapas de Fase B` · Backend
- **Criterio de éxito:** cada rol ve exactamente lo que le corresponde; un usuario no ve agentes y promotorías a la vez salvo permiso.

---

### HU-1.7 — Automatizar recordatorios y avisos por etapa · 🟨 HÍBRIDO
*HU - Automatizar recordatorios y avisos - Reclutadora/Capital Humano/Promotor*

- **Por qué híbrido:** son reglas de automatización (`base_automation`) que **se arman en la interfaz** pero el SDD pide **entregarlas versionadas como dato del módulo** (L3/L6).
- **TTs:**
  - `DEV - Regla recordatorio 3 días / "no_localizado" a la reclutadora (L3)` · Data
  - `DEV - Regla no-show: contador de reagendaciones + sugerir Stand by al 2º (L5, prioridad baja)` · Data
  - `DEV - Aviso "Acuerdo de Arranque" → Capital Humano (L6)` · Data
  - `DEV - Aviso "PDA apta" → reclutadora (L6)` · Data
- **Criterio de éxito:** los seguimientos y avisos ocurren solos; las reglas viajan versionadas en el módulo.

---

### HU-1.8 — Configurar motivos de rechazo y Stand by · 🟧 UI / IMPLEMENTADOR
*HU - Configurar motivos de rechazo y Stand by - Implementador*

- **Por qué UI:** motivos de rechazo **nativos** (§4.5) y Stand by = **archivar** (§4.6, comportamiento nativo + SOP).
- **TTs:**
  - `DEV - Configurar motivos "Declinado por Prospecto" y "Declinado por BCA"` · UX
  - `DEV - (Opcional) Plantillas de correo por motivo` · UX
  - `SOP - Stand by = archivar (operación, sin configuración)` · documentación
- **Criterio de éxito:** rechazar exige motivo; Stand by conserva historial y es reactivable.

---

### HU-1.9 — Visualizar el embudo de conversión · 🟧 UI / IMPLEMENTADOR
*HU - Visualizar embudo de conversión - Gerencia/Dirección*

- **Por qué UI:** es el **SIC** del embudo; se arma sobre el Análisis de Postulantes nativo (pivote) y, opcionalmente, un tablero en Studio-Community (es reporte, no lógica).
- **SIC:** `SIC: Embudo de Conversión de Reclutamiento`
- **TTs:**
  - `DEV - Configurar pivote Análisis de Postulantes (reclutadora · sede · job · ramo · periodo)` · UX
  - `DEV - (Opcional) Tablero de embudo en Studio-Community` · UX
- **Criterio de éxito:** Gerencia ve el embudo de conversión sin exportar a Excel.

---

## 4. ÉPICA 2 — SIC: Tiempos de Habilitación

> Casi enteramente nativa. Depende de las etapas creadas en la Épica 1.

**SIC del entregable:** `SIC: Tiempos de Habilitación`

### HU-2.1 — Visualizar tiempos de habilitación por etapa · 🟧 UI / IMPLEMENTADOR
*HU - Visualizar tiempos de habilitación - Gerencia*

- **Por qué UI:** usa el **Análisis de Velocidad** nativo (tiempo en etapa). El SDD lo marca "prácticamente nativo".
- **TTs:**
  - `DEV - Configurar Análisis de Velocidad por reclutadora · sede · puesto` · UX
- **Dependencia:** etapas de HU-1.1.
- **Criterio de éxito:** se ve cuánto tarda un candidato en cada tramo de la Fase B, por reclutadora/sede.

---

## 5. ÉPICA 3 — SIC: Efectividad por Fuente, Campaña y Evento

> Casi nativa (fuentes + UTM). El campo `bca_evento` ya se crea en la Épica 1 (HU-1.2). Una decisión de BCA puede convertir una TT en código.

**SIC del entregable:** `SIC: Efectividad por Fuente, Campaña y Evento`

### HU-3.1 — Medir efectividad por fuente, campaña y evento · 🟧 UI / IMPLEMENTADOR (🔶 con TT condicional a código)
*HU - Medir efectividad por canal - Gerencia/Dirección*

- **Por qué UI:** se arma sobre Análisis de Fuentes + UTM nativos (`source_id`, `campaign_id`) más `bca_evento`.
- **🔒 Decisión asociada — SI-3:** ¿`bca_evento` se queda como **texto** o pasa a **lista oficial (modelo)**? Si BCA elige modelo, la TT condicional se vuelve **código**.
- **TTs:**
  - `DEV - Configurar pivote de Fuentes + UTM (source_id · campaign_id · bca_evento)` · UX
  - `🔶 DEV (condicional) - Crear modelo bca.evento y migrar bca_evento a Many2one` · Backend *(solo si BCA decide modelo — depende de SI-3)*
- **Criterio de éxito:** Gerencia compara la efectividad de cada fuente, campaña y evento de reclutamiento.

---

## 6. Tabla maestra — HU → Clasificación → Razón

| HU | Épica | Clasificación | Razón de la clasificación |
|---|---|---|---|
| HU-1.0 Catálogo de Sedes | 1 | 🟦 CÓDIGO | Modelo nuevo `bca.sede` |
| HU-1.1 Embudo y etapas | 1 | 🟧 UI | Etapas son configuración (§4.1) |
| HU-1.2 Identificación y perfil | 1 | 🟦 CÓDIGO | Campos `bca_` en módulo + computed (D1) |
| HU-1.3 PDA + compuerta riesgo | 1 | 🟦 CÓDIGO | Lógica L1 (constraint + actividad) |
| HU-1.4 Conversión en cédula | 1 | 🟦 CÓDIGO | Lógica L2 (write/hired + puente + empleado) |
| HU-1.5 Puestos internos | 1 | 🟧 UI | Alta nativa de empleado (ramificación ya en L2) |
| HU-1.6 Visibilidad por rol/sede | 1 | 🟦 CÓDIGO | Grupos + `ir.rule` en módulo (§6) |
| HU-1.7 Recordatorios y avisos | 1 | 🟨 HÍBRIDO | Automatización UI versionada como dato del módulo |
| HU-1.8 Motivos rechazo / Stand by | 1 | 🟧 UI | Motivos nativos + archivar (§4.5/§4.6) |
| HU-1.9 SIC Embudo | 1 | 🟧 UI | Pivote/tablero (reporte, no lógica) |
| HU-2.1 SIC Tiempos | 2 | 🟧 UI | Análisis de Velocidad nativo |
| HU-3.1 SIC Efectividad | 3 | 🟧 UI 🔶 | UTM nativo; condicional a código si "Evento" = modelo |

---

## 7. Solicitudes de Información (SI) que bloquean construcción

Estas SI provienen del §11 del SDD y deben cerrarse **antes** de codificar las HUs que dependen de ellas.

| SI | Información requerida | HU que bloquea | Prioridad |
|---|---|---|---|
| **SI-1** | Mapa rol → qué ve + mecanismo de asignación promotor ↔ sede(s) (`bca_sede_ids`) | HU-1.6 (visibilidad) | Alta |
| **SI-2** | ¿Habilitación de Promotor usa el mismo flujo de cédula + puente, o el flujo de partner promotoría existente? | (afecta alcance futuro de conversión) | Alta |
| **SI-3** | ¿`bca_evento` como texto basta, o se quiere lista oficial (modelo)? | HU-3.1 (TT condicional) | Media |
| **SI-Sede** | Lista oficial de plazas para cargar el catálogo | HU-1.0 (carga inicial) | Media |

---

## 8. Encadenamiento con MIOR

Este análisis es el contenido de la tarea **`BACKLOG - Creación: BCA Seguros`** y queda listo para estructurarse en el proyecto MIOR:

- Cada **SIC** es una Épica (3 épicas).
- Cada **HU** lleva su `PLANNING - Sprint`, `REVIEW - Sprint`, `AGENDA - Capacitación de Flujo` y `DEV - Pase a Producción` al ejecutarse.
- Reglas de oro aplicables: ninguna HU cierra sin Pase a Producción en Hecho; la capacitación va siempre antes del pase y en ambiente de pruebas.
- **Secuencia sugerida (valor rápido visible):** HU-1.0 → 1.1 → 1.2 → 1.3 → 1.4 (flujo end-to-end operando) → 1.6 (visibilidad) → 1.9/2.1/3.1 (los SICs visibles para Gerencia) → 1.7/1.8 (afinación).

---

## 9. Qué necesito de ti para avanzar

1. **Validar la estructura de épicas:** ¿te funciona concentrar la fundación en la Épica 1 (probable 2 sprints), o prefieres separar la fundación de los reportes en sprints distintos?
2. **Cerrar SI-1 y SI-2 con BCA** — son las que bloquean la parte de seguridad (la de mayor cuidado) y definen el alcance de la habilitación de Promotor.
3. **Decidir SI-3** (Evento texto vs. modelo) — define si la Épica 3 incluye una TT de código.

Con eso te genero el **archivo de Backlog MIOR formal** (Épicas/HUs/TTs con etiquetas, responsables y secuencia de sprints) en Markdown.

---

*Hábitat Digital · Análisis HU/TT — Reclutamiento de Agentes · Grupo BCA · v1.0 · Alineado a MIOR*
