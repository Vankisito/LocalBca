---
titulo: BDD — Proceso de Reclutamiento y Habilitación de Agentes (Grupo BCA)
fecha: 2026-07-03
autor: Hábitat Digital
version: v1.5
area: Entrega
---

> **Cambio v1.5 (D-21):** correcciones de QA y separación del proceso en dos frentes.
> El **contacto** del candidato se crea al llegar a **"Acuerdo de Arranque"** (no al final), y
> ahí ocurre el **traspaso de gestión de Reclutamiento a Capital Humano** (la reclutadora queda
> como *entrevistadora* y el *responsable* pasa a Capital Humano). Se añade la etapa final
> **"Clave Definitiva"**, donde se **crea el empleado** (requiere el dato de Clave Definitiva);
> el botón de crear empleado no aparece antes. La etapa **"Entrevista" pasa a llamarse "Cena"**
> y los puestos a **"Promotores"/"Agentes"**. La Sede/Plaza es **obligatoria** para dar de alta
> al agente, y RFC/CURP se validan con formato mexicano. Nota: llegar a "Clave Definitiva"
> **no** convierte la clave del agente en definitiva-PCA (eso sigue siendo un proceso interno posterior).

> **Cambio v1.4 (D-20):** el embudo BCA (Fase A + Fase B) es exclusivo de las **figuras
> comerciales** —**Agentes y Promotorías**—, que comparten el mismo embudo. Los **puestos
> internos** ya **no** recorren la Fase A: se reclutan por el **flujo nativo de Odoo** y
> cierran con su etapa hired nativa. Se corrige la versión previa, que hacía pasar a los
> puestos internos por la Fase A.

# BDD — Proceso de Reclutamiento y Habilitación de Agentes
## Grupo BCA · Documento de Comportamiento a nivel Negocio

> Este documento describe **qué pasa y para qué**, en el lenguaje real de BCA. No describe cómo se construye el sistema: eso se define después, usando este documento como base. Si aquí aparece algo, es porque hace falta para entender el comportamiento del negocio.

---

## 1. Propósito y alcance

**Propósito:** dejar por escrito, sin ambigüedad y con ejemplos concretos, cómo se comporta el proceso de reclutamiento y habilitación de agentes de BCA, para que todos —Dirección, Capital Humano y quien lo implemente— estemos de acuerdo antes de tocar nada.

- **Cubre:** el embudo de las **figuras comerciales** (Agentes y Promotorías), desde que se recibe o identifica al candidato hasta que tiene su **cédula emitida** y entra a Desarrollo Comercial.
- **No cubre:** los **puestos internos** (Auxiliar administrativa, Reclutador, Gerencial, etc.), que se reclutan por el **embudo nativo de Odoo** y cierran con su etapa hired nativa —sin Fase A/B ni cédula—; tampoco la productividad y ventas del agente una vez habilitado (es otro proceso).
- **A quién sirve:** Dirección y Capital Humano de BCA (validan que esto es su realidad) y el equipo que lo implementa.

---

## 2. Lenguaje común (glosario)

| Término | Significado en BCA |
|---|---|
| Candidato | Persona en proceso para un puesto comercial o interno |
| Reclutadora | Identifica, contacta y acompaña al candidato hasta el acuerdo de arranque |
| Promotor | Responsable comercial de una plaza; da el visto bueno del prospecto y supervisa el embudo de su plaza |
| Gerencia | Da la consideración final para que un prospecto continúe (última palabra), sobre todo en casos de riesgo |
| Puesto | Figura comercial (Agente, Promotor, GDC) o puesto interno (Auxiliar administrativa, Reclutador, Gerencial). Solo las figuras comerciales requieren cédula |
| Ramo | Línea de negocio: Vida o Autos. Un candidato sin perfil para Vida puede pasar a Autos y continuar por el mismo embudo |
| Sede | Plaza a nivel nacional, de una lista oficial del negocio (CDMX, Puebla, GDL, QRO, HGO, MTY, etc.) |
| Café / Comida | Primera reunión donde se platica la oportunidad |
| Entrevista | Reunión formal de evaluación, posterior al café |
| PDA | Evaluación conductual (dato manual). Resultado en escala: Excelente / Muy buena / Aceptable / Baja / No ideal, más un % de correlación |
| Cena | Reunión donde se cierra el acuerdo de arranque |
| CIA | Inscripción al programa de inducción y adiestramiento de la aseguradora, dentro de la habilitación |
| Clave de arranque | Folio que asigna la aseguradora al aprobar el examen; habilita al agente |
| Cédula | Credencial que habilita legalmente al agente |
| Evento de reclutamiento | Ferias, universidades y convenciones (ej. Cancún) donde también se capta |
| Desarrollo Comercial | Etapa en que el agente ya está reclutado y en entrenamiento |

---

## 3. Actores y responsabilidades *(propuesta a validar)*

| Actor | Qué hace | Qué ve |
|---|---|---|
| **Reclutadora** | Registra candidatos, los contacta, agenda café y entrevista, captura datos y el resultado de PDA, mueve al candidato por el embudo | Solo sus candidatos |
| **Promotor** | Da el visto bueno del prospecto y supervisa el embudo de su plaza | Los candidatos de su sede |
| **Gerencia** | Da la consideración final para que un prospecto continúe (última palabra), sobre todo en casos de riesgo | Los candidatos a su cargo |
| **Capital Humano** | Recibe al candidato tras el acuerdo de arranque; gestiona CIA, curso, examen y cédula | Los candidatos en habilitación |
| **Dirección** | Lee los reportes para decidir | El consolidado nacional |

---

## 4. Mapa del proceso

> Este embudo (Fase A + Fase B) es el de las **figuras comerciales**: aplica por igual a
> **Agentes** y **Promotorías**, que lo recorren completo. Los **puestos internos** no entran
> aquí: se reclutan por el **embudo nativo de Odoo** (ver §1 y §8).

**Fase A — Atracción y Reclutamiento** *(Reclutadora / Promotor)*
Recibido → Prospección → Primer contacto → **Café** → **Entrevista** → Evaluación PDA → Cena (acuerdo de arranque)

**Al cerrar la Fase A:**
- La figura comercial (Agente o Promotoría) pasa a la **Fase B** (habilitación), con el **acuerdo de arranque aceptado**.
- Si el candidato no tiene perfil para **Vida** → se le puede ofrecer **Autos**: cambia de ramo y continúa por el mismo embudo, sin reiniciar su historial.

**Fase B — Habilitación** *(Capital Humano, figuras comerciales)*
Clave de arranque → Inscripción a CIA → Curso de cédula → Pago y examen → Cédula emitida → Desarrollo Comercial

---

## 5. Estados del candidato

| Estado | Significa | Agrupación |
|---|---|---|
| **Recibido** | Candidato o CV recibido, aún sin trabajar | Activos |
| **En proceso** | Avanza activamente por el embudo | Activos |
| **Stand by (On Hold)** | Sin decisión, queda en espera; conserva su historial | On Hold |
| **Declinado Prospecto** | El candidato decidió no continuar | Cerrados |
| **Declinado BCA** | BCA decidió no continuar con el candidato | Cerrados |
| **Contratado** | Aceptó el acuerdo de arranque | Convertidos |
| **En Desarrollo Comercial** | Ya reclutado, en entrenamiento | Convertidos |

---

## 6. Datos que se capturan del candidato

- **Identificación:** nombre, puesto (figura comercial o interna), ramo (Vida/Autos), sede, género, edad.
- **Contacto:** teléfono, correo, contactado (Sí / No localizado / Pendiente).
- **Origen:** tipo de candidato (Postulado / Prospectado / Referido / Sugerido), quién lo refirió, fuente (incluido el formulario del sitio web, ya en operación), campaña, evento de reclutamiento, folio del CV de la bolsa.
- **Asignación:** reclutadora, promotor.
- **Perfil:** grado y perfil académico, institución, pretensión económica, perfil laboral, si ya cuenta con cédula, CV adjunto.
- **Evaluación:** entrevistado (Sí/No), nivel de correlación PDA y % de correlación, perfil PDA.
- **Fechas:** prospección, primer contacto, café, entrevista, cena y cada cambio de etapa (para medir tiempos).
- **Habilitación:** clave de arranque, fecha de CIA, fecha de curso, fecha y pago de examen, fecha de cédula emitida.
- **Cierre:** estado final y motivo (obligatorio si se declina).

> El negocio mantiene listas oficiales de sede, puesto, fuente, campaña y promotor, para que todos capturen igual y los reportes sean confiables.

---

## 7. Comportamientos esperados (escenarios)

### Funcionalidad: Registro de un nuevo candidato
*Como reclutadora, quiero registrar al candidato desde que lo identifico, para no perder seguimiento y medir desde el día uno.*

**▸ Alta de candidato**
- **Dado** que la reclutadora identifica a un candidato en la sede Puebla
- **Cuando** lo registra con nombre, puesto "Agente", ramo "Vida", fuente "OCC" y fecha de prospección
- **Entonces** el candidato queda "Recibido" y luego "En proceso" en la etapa "Prospección"
- **Y** queda asignado a su reclutadora y aparece en el embudo de su sede

**▸ No se permite registrar sin sede ni puesto**
- **Dado** que la reclutadora intenta registrar sin indicar sede o puesto
- **Cuando** intenta guardar
- **Entonces** el sistema no lo permite y avisa que sede y puesto son obligatorios

### Funcionalidad: Café y luego Entrevista (dos pasos)

**▸ Café realizado**
- **Dado** un candidato contactado
- **Cuando** la reclutadora registra el café donde se platicó la oportunidad
- **Entonces** el candidato avanza a la etapa "Café"

**▸ Entrevista formal**
- **Dado** un candidato que ya tuvo el café
- **Cuando** la reclutadora realiza la entrevista y marca "Entrevistado: Sí"
- **Entonces** el candidato avanza a la etapa "Entrevista"

**▸ No se presenta**
- **Dado** un café o una entrevista agendada
- **Cuando** el candidato no se presenta
- **Entonces** la reclutadora puede reagendar una vez; si no asiste de nuevo, el sistema sugiere pasarlo a "Stand by"

### Funcionalidad: Evaluación PDA (dato manual, escala de cinco)

**▸ Correlación apta**
- **Dado** un candidato entrevistado
- **Cuando** se captura su perfil PDA, el % de correlación y el nivel como "Excelente", "Muy buena" o "Aceptable"
- **Entonces** el candidato queda habilitado para avanzar a la "Cena"
- **Y** se avisa a la reclutadora que el resultado PDA ya está cargado

**▸ Correlación Baja o No ideal requiere visto bueno**
- **Dado** un candidato con correlación PDA "Baja" o "No ideal"
- **Cuando** se captura el resultado
- **Entonces** el sistema marca una alerta de riesgo y pide el visto bueno del promotor
- **Y** con el visto bueno del promotor, el prospecto puede continuar a consideración de Gerencia
- **Y** si nadie lo aprueba, se cierra como "Declinado BCA" con motivo

### Funcionalidad: Cambio de ramo (Vida → Autos)

**▸ Candidato sin perfil para Vida pasa a Autos**
- **Dado** un candidato cuyo perfil no encaja con Vida
- **Cuando** se le ofrece la oportunidad en Autos y acepta explorarla
- **Entonces** se cambia su ramo a "Autos" y continúa por el mismo embudo, sin reiniciar su historial

### Funcionalidad: Cena y acuerdo de arranque (conversión)

**▸ Acuerdo aceptado — figura comercial**
- **Dado** un candidato con PDA apto y puesto de figura comercial
- **Cuando** se registra la cena y acepta el acuerdo de arranque
- **Entonces** cambia a "Contratado" y se entrega a Capital Humano para habilitación
- **Y** se avisa a Capital Humano que hay un candidato nuevo para curso de cédula

**▸ Acuerdo aceptado — promotoría (misma bifurcación que el agente)**
- **Dado** un candidato de **Captación de Promotoría** con PDA apto
- **Cuando** se registra la cena y acepta el acuerdo de arranque
- **Entonces** cambia a "Contratado" y pasa a Fase B por el mismo embudo comercial

> Los **puestos internos** no aparecen en este proceso: se reclutan por el **embudo nativo de Odoo** y cierran con su etapa hired nativa, sin pasar por Fase A/B ni cédula.

**▸ El candidato se baja**
- **Dado** un candidato en cualquier etapa
- **Cuando** decide no continuar
- **Entonces** pasa a "Declinado Prospecto" con motivo

### Funcionalidad: Habilitación y cédula (Capital Humano)

**▸ Cédula emitida**
- **Dado** un candidato "Contratado" de figura comercial
- **Cuando** recibe su clave de arranque, se inscribe a CIA, toma el curso y aprueba el examen
- **Y** Capital Humano registra la cédula como emitida con su fecha
- **Entonces** pasa a "En Desarrollo Comercial"
- **Y** se avisa a la reclutadora y al promotor que el agente quedó habilitado

**▸ No aprueba el examen**
- **Dado** un candidato en curso de cédula
- **Cuando** no aprueba el examen en el primer intento
- **Entonces** permanece en habilitación y se agenda un segundo intento
- **Y** si no aprueba de nuevo, Capital Humano decide entre "Stand by" o "Declinado BCA" con motivo

### Funcionalidad: Stand by, Declinaciones, Visibilidad y Avisos

**▸ Pausar y reactivar**
- **Dado** un candidato sin decisión de continuar
- **Cuando** la reclutadora lo marca "Stand by"
- **Entonces** sale del embudo activo pero conserva su historial, y puede reactivarse en la etapa donde se quedó

**▸ Declinaciones con motivo**
- **Dado** un candidato que sale del proceso
- **Cuando** se cierra como "Declinado Prospecto" (se baja él) o "Declinado BCA" (lo rechaza BCA)
- **Entonces** el motivo es obligatorio en ambos casos

**▸ Cada quien ve lo suyo**
- **Dado** los distintos roles
- **Cuando** entran a su tablero
- **Entonces** la reclutadora ve sus candidatos, el promotor los de su sede y Dirección el consolidado nacional
- **Y** los prospectos de agentes y de promotorías se ven por separado: un usuario no ve ambos, salvo que tenga permiso para ello

**▸ Recordatorio de seguimiento (3 días ordinarios)**
- **Dado** un candidato "No localizado" o sin avanzar de etapa
- **Cuando** pasan 3 días ordinarios
- **Entonces** el sistema envía un recordatorio a la reclutadora responsable para que actúe

---

## 8. Reglas de negocio

- El embudo BCA (Fase A + Fase B) es exclusivo de las figuras comerciales (Agentes y Promotorías), que lo recorren completo. Los puestos internos no entran a este embudo: se reclutan por el flujo nativo de Odoo y cierran con su etapa hired nativa, sin Fase A/B ni cédula (D-20).
- Un candidato no puede entregarse a Capital Humano sin acuerdo de arranque aceptado.
- "Declinado Prospecto" y "Declinado BCA" siempre exigen motivo.
- PDA Excelente, Muy buena o Aceptable avanzan; Baja o No ideal requieren el visto bueno del promotor, y la continuación final queda a consideración de Gerencia.
- Un candidato sin perfil para Vida puede pasar al ramo Autos y continuar por el mismo embudo, sin reiniciar su historial.
- La visibilidad separa a los agentes de las promotorías: un usuario no ve ambos tipos salvo que tenga permiso para ello.
- Los recordatorios de seguimiento ("no localizado" y "candidato estancado") se disparan a los 3 días ordinarios.
- El negocio mantiene listas oficiales de sede, puesto, fuente, campaña y promotor para que todos capturen igual.
- Cada cambio de etapa registra su fecha, para poder medir tiempos.

---

## 9. Resultados de negocio esperados (reportes)

- **Reporte 1 — Embudo de conversión:** cuántos candidatos avanzan de una etapa a la siguiente, de Recibido a Cédula emitida. Se ve por reclutadora, sede, puesto, ramo y periodo. Responde: ¿dónde se cae la mayoría?, ¿quién convierte mejor?, ¿qué sede está más sana?
- **Reporte 2 — Tiempos del proceso:** cuánto tarda cada etapa y el total de prospección a cédula emitida. Se ve por reclutadora, sede y puesto. Responde: ¿cuánto tardamos en habilitar un agente?, ¿dónde se atora?
- **Reporte 3 — Efectividad por fuente, campaña y evento:** volumen y conversión por fuente (OCC, Facebook, Indeed, LinkedIn, referidos), por campaña, universidad y eventos como Cancún. Responde: ¿qué canal trae a los mejores candidatos?, ¿qué campaña conviene repetir?

> En el histórico real la conversión es de apenas 3–4% (1,366 declinados por el prospecto y 265 por BCA contra unos 28 contratados). Por eso estos tres reportes son el corazón del proyecto.

---

## 10. Definición de Hecho (a nivel negocio)

- Se puede llevar a un candidato de "Recibido" hasta "En Desarrollo Comercial" sin salir del sistema.
- Cada estado y etapa se actualiza con un clic.
- Los tres reportes salen solos, sin Excel.
- Una reclutadora nueva entiende el flujo sin necesidad de explicación técnica.

---

## 11. Aclaraciones del negocio

> Respuestas de Guillermo incorporadas a esta versión. Quedan como acuerdo del comportamiento del proceso.

### Confirmado
- **Autos:** un candidato sin perfil para Vida puede pasar a Autos y continúa por el mismo embudo.
- **Visto bueno:** el promotor da el visto bueno del prospecto; la continuación final queda a consideración de Gerencia.
- **Sitio web:** no se construye nada; el formulario del sitio ya opera y entra como un canal de captación más.
- **Plazos de seguimiento:** recordatorio a los 3 días ordinarios, tanto para "no localizado" como para "candidato estancado".
- **Promotoría:** sigue el mismo embudo; la diferencia es de permisos — los usuarios no ven indistintamente prospectos de agentes y de promotorías.

### Sigue pendiente
- **Inversión por canal:** definir si BCA quiere medir cuánto cuesta cada contratación por fuente o campaña, o si por ahora basta con volumen y conversión.

---

*Hábitat Digital · Documento de uso interno · BDD v1.3 · Alineado a metodología MIOR*
