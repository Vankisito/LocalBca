---
titulo: Guía de Pruebas Manuales (UI) — Etapa 12 Reclutamiento BCA_Seguros
version_modulo: 19.0.1.7.4
fecha: 2026-07-02
dirigido_a: QA Junior
tipo: UAT / Pruebas de interfaz (Odoo backend)
---

# 🧪 Guía de Pruebas Manuales — Etapa 12: Reclutamiento y Habilitación de Agentes

> **Para:** QA Junior
> **Módulo:** `BCA_Seguros` · versión **19.0.1.7.4**
> **Objetivo:** verificar en la **interfaz de Odoo** que la Etapa 12 (Reclutamiento) funciona sin errores, antes de dar por buena la entrega.
> **Cómo usar esta guía:** ejecuta cada prueba en orden. Marca `[x]` cuando el resultado coincida con lo esperado. Si algo falla, anótalo en la **§10 Plantilla de incidencias** con captura de pantalla.

---

## 1. Entorno y acceso

| Dato | Valor |
|---|---|
| URL | `http://localhost:8069` |
| Base de datos | `Devlocal` |
| Usuario | Administrador (para preparar datos) + usuarios de prueba (ver §3) |
| Versión esperada del módulo | `19.0.1.7.4` |

**Verificación previa (obligatoria):**
- [ ] Inicio sesión en `http://localhost:8069` sin errores.
- [ ] En **Ajustes → Aplicaciones**, busco "BCA" y confirmo que **BCA Seguros** está **Instalada** con versión **19.0.1.7.4**.
- [ ] Activo el **modo desarrollador** (Ajustes → al final: *Activar el modo desarrollador*). Facilita ver errores técnicos y nombres de campos.

> 💡 Si aparece cualquier pantalla roja de error (traceback) en cualquier paso, **es un bug**: captúralo y regístralo. La interfaz nunca debe mostrar un traceback al usuario normal.

---

## 2. Glosario rápido de dónde está cada cosa

| Elemento | Ruta en el menú |
|---|---|
| App de Reclutamiento (embudo) | **Reclutamiento** (app nativa de Odoo) |
| Puesto de agentes | Reclutamiento → *Reclutamiento de Agente* |
| Catálogo de Sedes | **BCA Seguros → Configuración → Sedes / Plazas** |
| Agentes creados | **BCA Seguros → Configuración → Agentes** |
| Aseguradoras | **BCA Seguros → Configuración → Aseguradoras** |
| Promotorías | **BCA Seguros → Configuración → Promotorías** |
| Reporte SIC de reclutamiento | **BCA Seguros → Reportes → SIC Reclutamiento** |
| Empleados (para verificar alta) | App **Empleados** |

---

## 3. Preparación de datos de prueba (una sola vez, como Administrador)

- [ ] **P1.** En **BCA Seguros → Configuración → Aseguradoras**, confirmo que existe al menos una aseguradora (ej. MetLife). Si no, creo una: *Nuevo* → Nombre "Aseguradora QA" → Tipo BCA = **Aseguradora** → Guardar.
- [ ] **P2.** En **BCA Seguros → Configuración → Promotorías**, creo una promotoría de prueba: *Nuevo* → Nombre "Promotoría QA" → Tipo BCA = **Promotoría** → (debe colgar del holding Grupo BCA) → Guardar.
- [ ] **P3.** Usuarios de prueba (**Ajustes → Usuarios y compañías → Usuarios**), creo 3 usuarios internos y les asigno grupos (pestaña *Otros* / permisos):
  - `qa_reclutadora` → grupo **Reclutadora BCA**
  - `qa_capital_humano` → grupo **Capital Humano BCA**
  - `qa_director` → grupo **Director BCA**

---

## 4. T1 — Catálogo de Sedes / Plazas (Fase A)

- [ ] **T1.1** Voy a **BCA Seguros → Configuración → Sedes / Plazas**. Se abre la lista y veo las sedes semilla: **Matriz, Ciudad de México, Monterrey**.
- [ ] **T1.2** *Nuevo* → creo una sede "Sede QA" con código "QA1" → Guardar. Se guarda sin error.
- [ ] **T1.3** Intento crear otra sede con el **mismo código** "QA1" → al guardar debe **rechazarlo** con un mensaje de que el código debe ser único.
- [ ] **T1.4** Archivo "Sede QA" (botón de engranaje/acciones → Archivar). Deja de aparecer en la lista por defecto; con el filtro *Archivadas* vuelve a verse.

**Resultado esperado:** CRUD de sedes funciona, código único se respeta, archivado funciona.

---

## 5. T2 — Embudo de 12 etapas y campos del candidato (Fase A)

- [ ] **T2.1** Abro la app **Reclutamiento** → entro al puesto **"Reclutamiento de Agente"**. La vista kanban muestra las **12 columnas en este orden**:
  1. Recibido · 2. Prospección · 3. Café · 4. Entrevista · 5. Evaluación PDA · 6. Acuerdo de Arranque · 7. Clave de Arranque · 8. Inscripción CIA · 9. Curso de Cédula · 10. Examen · 11. **Cédula Emitida** · 12. En Desarrollo Comercial.
- [ ] **T2.2** Creo un candidato nuevo (*Nuevo*): Nombre del candidato "Juan Pérez QA". Guardo. Se abre el formulario sin error.
- [ ] **T2.3** En el formulario del candidato confirmo que aparece el campo **Promotoría destino** y las pestañas: **Nota** y **Detalles** (nativas) + **Identificación**, **Evaluación PDA**, **Habilitación** (BCA). **NO** deben existir pestañas "Perfil" ni "Origen" (se depuraron por reuso de lo nativo — D-19).
- [ ] **T2.4** Pestaña **Identificación**: relleno **Sede / Plaza** (elijo "Matriz"), **Género**, **Fecha de Nacimiento** (ej. 01/01/1990), **Institución**, **Folio CV**. Verifico que el campo **Edad** se calcula solo (≈ la edad correcta) y **no es editable**.
- [ ] **T2.5** Pestaña **Detalles** (nativa) → grupo **"Perfil BCA"**: relleno **Ramo**, **Perfil Laboral**, **Tipo de Candidato**. En el mismo tab, el **Grado** (nativo, "Postulante") cumple el rol de perfil académico, y **Búsqueda de talentos** (Fuente/Medio/Campaña) es el origen del candidato.
- [ ] **T2.6** *(Verificación de depuración)* Confirmo que **NO** hay checks "Contactado/Entrevistado" ni "Reagendaciones" ni "¿Tiene Cédula Previa?" — el avance del candidato se refleja moviéndolo de **etapa** en el embudo, y la cédula (si la tiene) se captura en la pestaña **Habilitación**.
- [ ] **T2.7** Guardo. Todo persiste sin error. Reabro el candidato y los datos siguen ahí.

**Resultado esperado:** 12 etapas visibles y ordenadas; el formulario muestra Identificación / Detalles (con "Perfil BCA") / Evaluación PDA / Habilitación, **sin** pestañas Perfil ni Origen; edad calculada; todo se guarda.

---

## 6. T3 — Evaluación PDA y compuerta de riesgo L1 (Fase B)

> Trabaja con el candidato "Juan Pérez QA" (u otro nuevo del puesto de agentes). **Asigna la Promotoría destino = "Promotoría QA"**.

- [ ] **T3.1** Pestaña **Evaluación PDA**: pongo **Nivel PDA = "Baja Compatibilidad"**. Al guardar, el campo **PDA en Riesgo** se marca solo (✓) y aparece el campo **Visto Bueno del Promotor**.
- [ ] **T3.2** Con Nivel PDA = "Ideal" (o "Recomendado"/"Aceptable"), **PDA en Riesgo** queda **desmarcado**.
- [ ] **T3.3** **Compuerta L1 (bloqueo):** dejo Nivel PDA = "Baja Compatibilidad", **Visto Bueno del Promotor = desmarcado**, e intento mover el candidato a una etapa posterior a "Evaluación PDA" (ej. arrastrar en kanban a **"Acuerdo de Arranque"**, o cambiar la etapa en el formulario). Debe **bloquearse** con un mensaje de validación que pide el visto bueno del promotor.
- [ ] **T3.4** Marco **Visto Bueno del Promotor = ✓** y repito el movimiento a "Acuerdo de Arranque". Ahora **sí avanza**.
- [ ] **T3.5** *(Aviso al promotor)* Al marcar el riesgo (T3.1), si la Promotoría destino tiene un usuario responsable, se genera una **actividad "Visto bueno PDA requerido"**. *(Opcional; requiere que la promotoría tenga usuario ligado.)*

**Resultado esperado:** el riesgo se calcula solo; no se puede pasar de "Evaluación PDA" con riesgo y sin visto bueno; con visto bueno sí avanza.

---

## 7. T4 — Habilitación / Conversión en "Cédula Emitida" (Fase C) ⭐ NÚCLEO

> Esta es la prueba **más importante**. Usa un candidato del puesto **"Reclutamiento de Agente"** con **Promotoría destino = "Promotoría QA"** y sin riesgo PDA pendiente (o con visto bueno).

- [ ] **T4.1 (Bloqueo por datos faltantes):** intento mover el candidato a la etapa **"Cédula Emitida"** SIN llenar la pestaña Habilitación. Debe **bloquearse** con un mensaje que dice qué datos faltan (Clave de Arranque, Fecha de Cédula, Aseguradora, RFC, CURP).
- [ ] **T4.2** Voy a la pestaña **Habilitación** y relleno los **5 datos**:
  - **RFC** = "PEJJ900101ABC"
  - **CURP** = "PEJJ900101HDFXXX01"
  - **Aseguradora** = "Aseguradora QA"
  - **Clave de Arranque** = "QA-CLV-001"
  - **Fecha de Cédula** = hoy
- [ ] **T4.3** Ahora muevo el candidato a **"Cédula Emitida"**. Debe **avanzar sin error** y aparecer un mensaje/nota en el historial (chatter) de que se creó/vinculó el contacto agente.
- [ ] **T4.4 (Se creó el agente):** voy a **BCA Seguros → Configuración → Agentes**. Aparece un nuevo agente con el nombre del candidato, colgando de **"Promotoría QA"**. Al abrirlo, en **RFC** está el valor y hay un campo **CURP** con el valor capturado.
- [ ] **T4.5 (Puente en Clave de Arranque):** en el agente, en **Claves por Aseguradora** hay **una línea** con: Aseguradora = "Aseguradora QA", Clave = "QA-CLV-001", **Estado = "Clave de Arranque"** (⚠️ **NO** debe ser "Clave Definitiva").
- [ ] **T4.6 (Se creó el empleado):** en la app **Empleados**, busco por el nombre del candidato; existe un empleado vinculado a ese contacto.

**Resultado esperado:** no se llega a "Cédula Emitida" sin los 5 datos; al llegar, se crean automáticamente **agente + clave en estado Clave de Arranque + empleado**.

---

## 8. T5 — Idempotencia, promotoría y puestos internos (Fase C)

- [ ] **T5.1 (Reutilización por RFC+CURP):** creo un **segundo** candidato de "Reclutamiento de Agente" con **el mismo RFC y CURP** del T4, pero **otra Aseguradora** (creo "Aseguradora QA 2") y otra Clave (ej. "QA-CLV-002"). Lo llevo a "Cédula Emitida".
  - **Esperado:** **NO** se crea un agente duplicado. En **Agentes** sigue existiendo **un solo** agente con ese RFC/CURP, pero ahora tiene **2 líneas** en *Claves por Aseguradora* (una por aseguradora), ambas en estado **Clave de Arranque**.
- [ ] **T5.2 (Puesto interno usa el embudo nativo, no crea agente):** en la app **Reclutamiento**, en un puesto **que NO sea** de agentes/promotoría (ej. un puesto interno de RH cualquiera), creo un candidato.
  - **Esperado:** el candidato **no** ve ninguna de las 12 etapas BCA (Recibido…En Desarrollo Comercial); ve el **embudo nativo de Odoo**. Al llevarlo a la etapa hired nativa (**"Contract Signed"**) se da de alta como empleado normal, **sin** crear contacto agente ni línea de clave por aseguradora. Nota: ya **no** existe la etapa "Contratado (Alta Interna)".
- [ ] **T5.3 (Promotoría recorre el embudo comercial):** creo un candidato de **"Captación de Promotoría"**.
  - **Esperado:** ve las **mismas 12 etapas** que un agente (Fase A + Fase B). Al llevarlo a **"Cédula Emitida"** se crea el **contacto Promotoría** (bajo Grupo BCA), sin exigir los 5 datos de habilitación del agente.

**Resultado esperado:** la misma persona no se duplica (se le suman claves); la promotoría comparte el embudo comercial; los puestos internos usan el embudo nativo y no generan agentes ni puentes.

---

## 9. T6 — Motivos de rechazo, aviso por etapa y pivote SIC (Fase D)

- [ ] **T6.1 (Motivos de rechazo):** abro un candidato y uso el botón **Rechazar / Refuse**. En la lista de motivos deben aparecer **"Declinado por Prospecto"** y **"Declinado por BCA"**. Selecciono uno y confirmo. El candidato queda rechazado.
- [ ] **T6.2 (Aviso por cambio de etapa):** muevo un candidato del embudo comercial ("Reclutamiento de Agente" **o** "Captación de Promotoría") de una etapa a otra. En el **historial (chatter)** del candidato aparece una nota tipo "El candidato avanzó a la etapa: …".
- [ ] **T6.3 (Pivote SIC):** voy a **BCA Seguros → Reportes → SIC Reclutamiento**. Se abre una **tabla dinámica (pivote)** sobre los candidatos. Puedo agrupar por **Sede, Reclutadora, Puesto, Ramo, Evento, Etapa** y cambiar a vista **Gráfica**. No debe dar error.

**Resultado esperado:** rechazar exige y ofrece los 2 motivos; los cambios de etapa dejan nota; el pivote agrupa por las dimensiones sin error.

---

## 10. T7 — Visibilidad por rol (Fase E)

> Prepara: crea **2 candidatos** de "Reclutamiento de Agente" y asigna el campo **Reclutador/a (Recruiter)** — uno a `qa_reclutadora` y otro a otro usuario distinto.

- [ ] **T7.1 (Reclutadora ve solo lo suyo):** cierro sesión y entro como **`qa_reclutadora`**. En la app Reclutamiento **solo veo mi(s) candidato(s)** (los asignados a mí), **no** los de otra reclutadora.
- [ ] **T7.2 (Director ve todo):** entro como **`qa_director`**. Desde **BCA Seguros → Reportes → SIC Reclutamiento** (o Reclutamiento) **veo todos** los candidatos, sin filtro por reclutadora.
- [ ] **T7.3 (Capital Humano ve todo):** entro como **`qa_capital_humano`**. Veo y puedo gestionar **todos** los candidatos del embudo.

**Resultado esperado:** reclutadora aislada a sus candidatos; director y capital humano ven todo.

---

## 11. Verificación cruzada crítica (PCA)

> Regla de negocio clave: un agente recién habilitado (**Clave de Arranque**) **NO** debe computar PCA.

- [ ] **T8.1** Con el agente creado en T4 (estado *Clave de Arranque*), voy a **BCA Seguros → Reportes → PCA por Agente**. El agente **NO** debe aparecer con producción (solo computan los de **Clave Definitiva**).

**Resultado esperado:** el agente en Clave de Arranque no aparece en los reportes de PCA.

---

## 12. Limitaciones conocidas — NO reportar como bug

Estos puntos son **decisiones documentadas**, no errores:

- **Sedes semilla** (Matriz / CDMX / Monterrey) son **placeholder**; la lista oficial la entregará BCA más adelante.
- **Recordatorios automáticos L3 (3 días) y L5 (no-show → Stand by)** **no** están implementados aún (requieren definición de la etapa "Stand by"). Solo existe el aviso por cambio de etapa (T6.2).
- **Separación por tipo de puesto (job_id)** en la visibilidad de la reclutadora es un refinamiento futuro; hoy la reclutadora ve por *usuario asignado*.
- La **promoción de Clave de Arranque → Clave Definitiva** (que sí computa PCA) es un proceso posterior **fuera del alcance** de esta etapa.

---

## 13. Plantilla de reporte de incidencias

Por cada fallo encontrado, copia este bloque:

```
### Incidencia #___
- Prueba (ID): T_._
- Usuario con el que probé: (admin / qa_reclutadora / qa_director / qa_capital_humano)
- Pasos para reproducir:
  1.
  2.
- Resultado esperado:
- Resultado obtenido:
- ¿Apareció pantalla roja / traceback? (Sí/No) — pega el texto del error:
- Captura de pantalla: (adjuntar)
- Severidad: (Bloqueante / Alta / Media / Baja)
```

---

## 14. Resumen de aceptación

La Etapa 12 se considera **verificada en UI** cuando:

- [ ] T1 a T8 completas sin pantallas de error.
- [ ] El núcleo (T4) crea agente + clave **Clave de Arranque** + empleado.
- [ ] La idempotencia (T5.1) no duplica agentes.
- [ ] La visibilidad por rol (T7) funciona.
- [ ] El agente en Clave de Arranque no aparece en PCA (T8.1).

**Firma QA:** ______________  **Fecha:** __________  **Resultado global:** ☐ Aprobado ☐ Con incidencias
