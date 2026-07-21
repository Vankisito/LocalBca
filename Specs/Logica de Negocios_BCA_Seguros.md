# Requerimientos de Negocio — Grupo BCA
## Gestión del Ciclo de Vida de Pólizas, Cobranza, PCA y Comisiones

**Cliente:** Grupo BCA — Promotoría de Promotorías
**Aseguradoras:** MetLife, Qualitas, Atlas (en v1.1 — 3 aseguradoras planeadas)
**Documento:** Requerimientos funcionales de negocio
**Propósito:** Servir de base para diseñar escenarios de implementación
**Audiencia:** Arquitecto de solución, desarrollador, líder de proyecto
**Autor:** Hábitat Digital — Equipo de consultoría
**Fecha:** Mayo 2026
**Versión:** 2.0 — incorpora modelo de negocio de promotoría de promotorías

> Este documento describe **qué necesita el negocio**, no cómo construirlo. Las decisiones de plataforma, modelo de datos, arquitectura de despliegue, lenguaje y tecnología son responsabilidad del arquitecto de solución a partir de este insumo.

---

## 1. Contexto del Negocio

### 1.1 Qué es BCA realmente

Grupo BCA no es una promotoría tradicional. Es una **promotoría de promotorías**: un consolidador que ha integrado bajo su paraguas a varias promotorías más pequeñas con sus respectivos agentes. El modelo de escalamiento de BCA tiene una lógica clara:

- **Más promotorías afiliadas** → más agentes activos vendiendo.
- **Más agentes vendiendo** → mayor volumen agregado de pólizas y prima.
- **Mayor volumen agregado** → mejores escalas de comisión, premios y bonos por parte de las aseguradoras.

A cambio de absorber a las promotorías pequeñas bajo su estructura, BCA ofrece dos cosas: **infraestructura** (sistemas, procesos, soporte) y **centralización de la operación administrativa**. La promesa de valor es que cada actor se enfoque en lo que mejor hace:

| Actor | Su foco operativo |
|---|---|
| **BCA (consolidador)** | Administración, sistemas, relación con aseguradoras, liquidación de comisiones |
| **Promotorías afiliadas** | Reclutar, formar y retener agentes |
| **Agentes** | Vender y atender al cliente final |

### 1.2 De dónde vienen los ingresos de BCA

El ingreso de BCA **no es la prima que paga el cliente**. La prima va a la aseguradora. El ingreso real de BCA es:

```
Ingreso BCA = Comisiones + Premios + Bonos pagados por las aseguradoras
              a partir del volumen y la calidad de la cartera intermediada
```

Estas comisiones se generan principalmente sobre la **Prima Computable (PCA)** — un indicador de productividad ajustada que la aseguradora calcula sobre la prima neta de cada recibo cobrado. La PCA es el corazón económico del sistema: define cuánto recibe BCA de la aseguradora, cuánto se reparte con la promotoría afiliada y cuánto le toca al agente.

### 1.3 Cadena de valor económica

```
Cliente paga prima → Aseguradora cobra → Aseguradora libera comisión sobre PCA
                                                    ↓
                                      BCA recibe y administra
                                                    ↓
                              Distribuye según esquema entre:
                              · Promotoría afiliada
                              · Agente
                              · BCA (margen del consolidador)
```

### 1.4 Las aseguradoras en alcance

| Aseguradora | Ramos | Estado |
|---|---|---|
| **MetLife** | Vida (LSP) + Gastos Médicos Mayores (GCAYE) | ✅ v1.0 — En alcance |
| **Qualitas** | Autos | ✅ v1.0 — En alcance (estructura de archivos pendiente) |
| **Atlas** | Por confirmar con BCA | 🔄 v1.1 — Fase posterior |

El sistema debe diseñarse **agnóstico a la aseguradora** desde el inicio. Aunque MetLife es la primera implementación, la arquitectura no debe acoplarse a ella. Cada aseguradora tendrá su propio formato de archivo, sus propios productos, sus propias reglas de PCA y sus propios esquemas de comisión.

### 1.5 El dolor actual

Hoy esta operación se sostiene con hojas de cálculo y procesos manuales. Esto genera tres problemas estructurales:

1. **Conciliación lenta** — buscar póliza por póliza en los archivos de cada aseguradora consume horas/día.
2. **Cálculo de PCA propenso a error** — los factores se aplican a mano y los resultados son difíciles de auditar.
3. **Liquidación opaca a las promotorías afiliadas y a los agentes** — no hay forma rápida y confiable de mostrarle a una promotoría afiliada cuánto generó su red este mes, ni a un agente cuánto le corresponde por sus pólizas.

El objetivo del sistema es **eliminar la carga administrativa de BCA y a la vez darle a cada actor de la red la visibilidad que hoy no tiene**, de manera que cada quien pueda enfocarse en su rol sin pelearse con la operación.

---

## 2. Estructura Organizacional que el Sistema Debe Modelar

Esta es una de las decisiones más importantes del diseño porque atraviesa todo: pólizas, comisiones, reportes y permisos.

### 2.1 Jerarquía y roles estratégicos

**Dentro de BCA operan dos roles estratégicos en paralelo:**
- **Director General:** Máxima autoridad, responsable de la configuración general del sistema, autorización de excepciones y definición de esquemas. Acceso completo.
- **Director Comercial:** Responsable de la operación comercial, supervisión de comisiones, liquidaciones y relación estratégica con aseguradoras. Permisos equivalentes al Director General en materia de cancelaciones, edición de factores y esquemas de comisión (ver sección 8).

**Jerarquía operativa de cuatro niveles:**

```
                    GRUPO BCA (Consolidador)
              Director General | Director Comercial
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   Promotoría A        Promotoría B        Promotoría C
        │                   │                   │
    ┌───┴───┐          ┌────┴────┐         ┌────┴────┐
   Ag1   Ag2          Ag3   Ag4           Ag5   Ag6
```

- **Nivel 1 — BCA (Dirección):** la cabeza. Director General y Director Comercial ven todo, administran todo, liquidan a todos.
- **Nivel 2 — Promotorías afiliadas:** cada una con su nombre, su estructura, su gerente. Reclutan y desarrollan agentes.
- **Nivel 3 — Agentes:** quienes venden las pólizas y atienden al cliente final. Cada agente pertenece a una sola promotoría afiliada en un momento dado.

### 2.2 Reglas estructurales

**R-ORG-01.** Cada agente debe estar adscrito a exactamente una promotoría afiliada. El sistema debe registrar y mostrar a qué promotoría pertenece cada agente.

**R-ORG-02.** Un agente puede cambiar de promotoría afiliada con el tiempo. El sistema debe conservar el historial: las pólizas vendidas bajo la promotoría anterior siguen acreditadas a esa promotoría para efectos históricos; las nuevas se acreditan a la nueva.

**R-ORG-03.** Cada póliza queda permanentemente vinculada al agente que la vendió. Si el agente cambia de promotoría, la póliza histórica conserva la promotoría original para fines de liquidación.

**R-ORG-04.** El sistema debe permitir reportar PCA y comisiones a **tres niveles simultáneos**: total BCA, por promotoría afiliada, y por agente individual.

**R-ORG-05.** Una promotoría afiliada puede estar activa o inactiva. Si se inactiva, sus agentes deben migrarse explícitamente a otra promotoría antes; no quedan "huérfanos".

---

## 3. Alcance Funcional

El sistema debe cubrir **cuatro procesos centrales** y los **datos maestros** que los habilitan.

### 3.1 Procesos centrales

| Proceso | Frecuencia | Origen del dato |
|---|---|---|
| **A. Registro y gestión de pólizas** | Eventual + masivo en arranque | Portafolio interno BCA + alta manual |
| **B. Cobranza y conciliación diaria** | Diaria, por aseguradora y por ramo | Archivos planos enviados por cada aseguradora |
| **C. Cálculo de PCA** | Continuo (se actualiza con cada cobranza) | Calculado por el sistema |
| **D. Liquidación de comisiones a la red** | Mensual o según corte acordado | Calculado por el sistema |

### 3.2 Datos maestros requeridos

- Catálogo de **aseguradoras** (con sus reglas particulares).
- Catálogo de **promotorías afiliadas** (la red de BCA).
- Catálogo de **agentes** (con su promotoría y estado).
- Catálogo de **productos** por aseguradora.
- Catálogo de **conductos de pago**.
- **Tablas de factores PCA** por aseguradora y por año.
- **Esquemas de comisión** por aseguradora, por producto y por nivel de la red.
- Catálogo de **contratantes** (clientes finales).

### 3.3 Fuera de alcance de la versión inicial

- Aseguradora Atlas — fase v1.1, pendiente definición.
- Lectura automática de carátulas PDF para alta de pólizas — fase posterior.
- Dispersión efectiva de comisiones (transferencia bancaria a agentes) — el sistema entrega el cálculo; el pago se ejecuta en sistema bancario o de nómina externo.
- Portal autoservicio para el cliente final.

---

## 4. Proceso A — Registro y Gestión de Pólizas

### 4.1 Concepto de póliza

Una **póliza** es el contrato entre el cliente y la aseguradora. Tiene vigencia larga (años), una prima anual fraccionada en recibos periódicos, y está asignada a un agente que la vendió y la atiende. **A través del agente queda implícitamente asignada también a la promotoría afiliada y, por encima, a BCA.**

### 4.2 Información que el sistema debe capturar por póliza

**Identificación:**
- Número de póliza (único por aseguradora).
- Aseguradora emisora.
- Producto comercial específico.
- Ramo (Vida / GMM / Autos en fase posterior).
- Póliza origen (cuando es renovación o conversión).

**Partes involucradas:**
- Contratante (con RFC y CURP).
- Agente responsable (que arrastra a su promotoría afiliada).

**Términos financieros:**
- Moneda (MXN o USD).
- Prima anual total.
- Prima fraccionada.
- Recargo por fraccionamiento.
- Suma asegurada.
- Periodicidad: mensual, trimestral, semestral o anual.

**Vigencia:**
- Fecha de inicio.
- Fecha de fin.
- **Pagado Hasta** — fecha hasta la cual el cliente cubrió. Métrica crítica de vigencia operativa.

**Información exclusiva de Gastos Médicos:**
- Deducible.
- Coaseguro.
- Nivel hospitalario.

**Información exclusiva de Vida:**
- Tipo de cobertura (estándar / accidentes / invalidez).
- Temporalidad en años.
- Indicador de aportación adicional.

### 4.3 Reglas de negocio sobre pólizas

**R-POL-01.** El número de póliza es único por aseguradora. El sistema impide duplicados dentro de la misma aseguradora.

**R-POL-02.** Al confirmar una póliza, el sistema genera automáticamente el **plan de pagos** completo: los N recibos correspondientes a la periodicidad, cada uno con su ventana de fechas y su prima modal. 

**R-POL-03.** **"Pagado Hasta" es de solo lectura para todo usuario.** Se actualiza únicamente como consecuencia del registro de un pago. Ningún operador, líder ni administrador puede editarlo manualmente.

**R-POL-04.** Las pólizas tienen ciclo de vida: borrador → activa → vencida o cancelada. Transiciones controladas.

**R-POL-05.** Si una póliza ya tiene recibos pagados, el sistema **no permite regenerar el plan de pagos**.

**R-POL-06.** **Ciclo de vida de recibos:** Los recibos se crean automáticamente cuando una póliza es confirmada o modificada. Los recibos se cancelan automáticamente cuando la póliza es cancelada. En ambos casos, se generan entradas en la bitácora de auditoría con quién, cuándo y por qué.

Una póliza debe poder vincularse a una "póliza origen" para conservar trazabilidad histórica de renovaciones.

**R-POL-07.** **Toda póliza debe estar atribuida a un agente activo (con licencia Definitiva o Temporal no se puede a nivel prospecto).** El sistema debe poder reconstruir en cualquier momento la cadena agente → promotoría afiliada → BCA para fines de liquidación.

### 4.4 Carga masiva del portafolio

Para arranque y para incorporaciones de promotorías afiliadas nuevas, BCA necesita cargar pólizas en bloque desde archivos de hoja de cálculo. El portafolio BCA actual tiene formato con tres hojas (Vida,GMM y Autos).

**Reglas:**

- El sistema lee las hojas y crea pólizas sin duplicar.
- Para GMM, deducible y coaseguro se autopopulan desde el archivo.
- Cada póliza cargada genera automáticamente su plan de recibos hacia adelante.
- La carga produce reporte de resultados: creadas, actualizadas, rechazadas y motivos.
- **Si se incorpora una nueva promotoría afiliada con su cartera**, debe poder cargarse de forma aislada y atribuirse correctamente a esa promotoría.

### 4.5 Alta unitaria

Además de la carga masiva, el operador debe poder dar de alta una póliza nueva manualmente con los mismos campos de 4.2.

---

## 5. Proceso B — Cobranza y Conciliación Diaria

### 5.1 Origen del dato

Cada aseguradora entrega periódicamente sus propios archivos de cobranza con los pagos recibidos. En la versión inicial, MetLife entrega **dos archivos diarios** (formato CSV):

- **Archivo de Vida** (LSP) — pagos de pólizas del ramo Vida.
- **Archivo de Gastos Médicos** (GCAYE) — pagos de pólizas GMM.

Cada archivo tiene formato fijo: título en fila 1, encabezados en fila 2, registros desde fila 3, totales en última fila (a descartar). Encoding Latin-1 (no UTF-8). Importes con separador de miles.

**La arquitectura debe asumir desde el inicio que cada aseguradora tendrá su propio formato** y que el sistema debe poder incorporar nuevos formatos sin reescribir el núcleo.

### 5.2 Información típica por archivo

**Archivo de Vida MetLife:**
- Número de póliza, producto, agente, contratante, moneda, fecha de aplicación, vigencia del periodo, conducto de pago, prima modal, recargos, comisión informativa.

**Archivo de Gastos Médicos MetLife:**
- Número de póliza, estatus del pago (normal o anulado), agente, contratante, fecha de aplicación, vigencia, conducto, prima neta, recargos, gastos de expedición, impuestos, prima total, folio de endoso.

### 5.3 Reglas de negocio sobre cobranza

**R-COB-01 — Filtrado de anulaciones.** Las filas marcadas como anulación de pago se registran en bitácora con marca correspondiente y se omiten. No son error.

**R-COB-02 — Búsqueda de póliza.** Cada fila se asocia a una póliza por su número (dentro de la aseguradora correspondiente). Si no existe o no está activa, se reporta como "No encontrada" y el proceso continúa.

**R-COB-03 — Regla FIFO (crítica).** Cuando una póliza tiene varios recibos pendientes, el pago liquida siempre el más antiguo. Nunca se salta recibos. Esto refleja la lógica de la aseguradora y mantiene íntegro el campo "Pagado Hasta".

**R-COB-04 — Deduplicación natural.** El sistema **no permite pagar dos veces el mismo periodo**. Si no hay recibo pendiente disponible, la fila se rechaza con marca "Sin recibo disponible". El folio de endoso se conserva como dato de auditoría informativo, no como mecanismo de control.

**R-COB-05 — Multimoneda.** Si la moneda del archivo difiere de la de la póliza, se aplica tipo de cambio del día de la fecha de aplicación.

**R-COB-06 — Conducto de pago.** Mapeo automático contra catálogo configurable. Sin coincidencia → campo vacío + advertencia en bitácora.

**R-COB-07 — Actualización de "Pagado Hasta".** Al registrar el pago, el sistema actualiza "Pagado Hasta" usando la fecha de fin de vigencia del recibo. Solo avanza hacia adelante, nunca retrocede (salvo por cancelación explícita de recibo).

**R-COB-08 — Tolerancia a fallos por fila.** Cada fila se procesa aislada. Un error en una fila no detiene el proceso completo: rollback de esa fila, registro en bitácora, continúa con la siguiente.

**R-COB-09 — Validación previa.** Antes de tocar datos, el sistema valida extensión del archivo y presencia de columnas requeridas. Si falta una columna crítica, se detiene sin procesar.

**R-COB-10 — Procesamiento por aseguradora.** El operador debe seleccionar la aseguradora y el ramo al cargar el archivo. **El sistema usa esa selección para elegir el conjunto de reglas, columnas esperadas y tabla de factores PCA aplicable.** No debe haber un único parser monolítico; debe haber una pieza por formato.

### 5.4 Bitácora permanente de cobranza

Cada sesión de importación queda registrada en bitácora permanente, no efímera, con:

- Quién ejecutó, cuándo.
- Aseguradora y ramo procesado.
- Nombre del archivo.
- Conteos: recibos exitosos, anulaciones ignoradas, pólizas no encontradas, errores.
- PCA total cobrada en la sesión.
- Detalle línea por línea de las excepciones.

**La bitácora no debe poder ser editada ni eliminada por ningún usuario, incluido el administrador.**

### 5.5 Códigos de marca para la bitácora

- `[ANULADO]` — anulación ignorada.
- `[NO ENCONTRADA]` — póliza no existe o inactiva.
- `[SIN RECIBO]` — póliza sin recibos pendientes (deduplicación FIFO).
- `[ADVERTENCIA]` — no crítico (conducto desconocido, diferencia menor, etc.).
- `[ERROR]` — fila no procesada por fallo técnico.
- `[INFO]` — evento informativo (tipo de cambio aplicado, etc.).

---

## 6. Proceso C — Prima Computable (PCA)

### 6.1 Qué es y por qué importa

La **PCA** es el corazón económico del negocio. **No es lo que pagó el cliente**: es un monto ajustado que la aseguradora usa para liquidar comisiones a BCA, y que BCA usa internamente para liquidar a la promotoría afiliada y al agente.

```
PCA del recibo = Prima Neta del recibo × Factor de Ajuste
```

El factor depende de la aseguradora, el ramo, el producto, la moneda y, en GMM, de coaseguro y deducible. Lo entrega cada aseguradora anualmente.

### 6.2 Cuándo se calcula

**En el momento exacto en que un recibo se marca como pagado.** Un recibo pendiente no tiene PCA. Solo los pagos efectivos generan productividad.

### 6.3 Regla crítica de inmutabilidad

**R-PCA-01 — Congelamiento al pago.** El valor de PCA y el factor aplicado se **congelan en el recibo al momento del pago**. Si la aseguradora actualiza la tabla de factores en años siguientes, los recibos pagados previamente **no se recalculan**. Esto es no negociable. Garantiza que los reportes históricos de comisiones sean estables y auditables, y que las liquidaciones ya pagadas a promotorías y agentes no se vuelvan inconsistentes.

### 6.4 Tabla de factores Ramo Vida MetLife — 2026

| Producto | MXN | USD |
|---|---|---|
| Universales | 100% | 100% |
| TempoLife | 100% | 80% |
| TempoLife Grandes Sumas y Riesgo Preferente | 100% | 80% |
| TotalLife | 100% | 80% |
| EducaLife | 100% | 70% |
| PerfectLife | 100% | 70% |
| Horizonte | 100% | 70% |

### 6.5 Tabla de factores Ramo GMM MetLife — 2026

| Coaseguro | Deducible | Factor |
|---|---|---|
| ≥ 10% | ≥ $29,000 MXN | 120% |
| ≥ 10% | < $29,000 MXN | 100% |
| ≤ 5% | Cualquiera | **0% — no computa** |

### 6.6 Exclusiones — recibos que no computan PCA

**En Vida:**
- Aportaciones adicionales en productos capitalizables (FlexiLife, Universales).
- Coberturas individuales de accidentes o invalidez.
- Pólizas con temporalidad menor a 10 años.

**En GMM:**
- Coaseguro ≤ 5%.

Estas exclusiones se evalúan **antes** de aplicar cualquier factor. El recibo queda con PCA = 0 y factor aplicado = 0, debidamente registrado.

### 6.7 Reglas adicionales

**R-PCA-02 — Tablas configurables por aseguradora.** Los factores deben vivir en catálogo editable por aseguradora y por año. Cuando MetLife entregue la tabla 2027 o cuando Qualitas/Insurance entreguen las suyas, el administrador las carga sin pedir desarrollo.

**R-PCA-03 — Solo agentes con licencia computan.** Los agentes en estado prospecto pueden tener pólizas asignadas, pero sus pólizas **no entran en los reportes de PCA ni en el cálculo de comisiones**. Solo los agentes con licencia generan productividad reportable.

**R-PCA-04 — Cancelación de recibo.** Si un recibo pagado se cancela, su PCA pasa a cero y "Pagado Hasta" de la póliza se recalcula. Operación exclusiva del administrador. Si la cancelación afecta una liquidación ya emitida, debe registrarse como ajuste en el siguiente corte.

### 6.8 Visibilidad de PCA por nivel jerárquico

El reporte central de PCA debe poder cortarse por:

- **Total BCA** — vista del consolidador.
- **Por promotoría afiliada** — para evaluar productividad de cada red.
- **Por agente** — para liquidación individual.

Filtros: por aseguradora, por ramo, por producto, por rango de fechas de pago.

---

## 7. Proceso D — Liquidación de Comisiones a la Red

Este es el proceso que **convierte la PCA en dinero efectivo a repartir entre los tres niveles** (BCA, promotorías afiliadas, agentes). Es el cierre del ciclo económico del negocio.

### 7.1 Diferencias entre ingreso de la aseguradora y liquidación a la red

```
[Lo que entra]
Comisión que paga la aseguradora a BCA sobre PCA + Premios + Bonos

[Lo que sale]
- Liquidación a las promotorías afiliadas (su participación)
- Liquidación a los agentes (su participación)
- Margen que retiene BCA como consolidador
```

### 7.2 Esquemas de comisión — el dato maestro central

Cada aseguradora paga a BCA con su propio esquema. Y dentro de BCA, cada promotoría afiliada y cada agente pueden tener su propio esquema interno acordado contractualmente.

El sistema debe permitir configurar **esquemas de comisión** con al menos las siguientes dimensiones:

- **Por aseguradora** (MetLife paga distinto que Qualitas).
- **Por ramo y producto** (Vida paga distinto que GMM; dentro de Vida, TotalLife paga distinto que TempoLife).
- **Por nivel de la red** (BCA, promotoría, agente).
- **Por año o vigencia temporal** (un esquema 2026 puede cambiar en 2027).
- **Por tipo de evento**: comisión sobre primer año, comisión de renovación, bonos por volumen, premios por permanencia.

### 7.3 Tipos de eventos que generan comisión

**R-COM-01 — Comisión sobre PCA cobrada (recurrente).** Cada recibo pagado genera una comisión calculable sobre su PCA según el esquema vigente. Este es el ingreso base recurrente.

**R-COM-02 — Comisiones de primer año vs renovación.** Muchas aseguradoras pagan más sobre los recibos del primer año de vigencia de una póliza que sobre las renovaciones. El sistema debe poder distinguir si un recibo corresponde al primer año o a una renovación.

**R-COM-03 — Bonos por volumen.** Cuando la red supera ciertos umbrales acumulados de PCA en un periodo (típicamente trimestral o anual), la aseguradora paga bonos adicionales. El sistema debe poder calcular el avance hacia esos umbrales y registrar los bonos liberados.

**R-COM-04 — Premios por permanencia o conservación.** Algunas aseguradoras premian la calidad de la cartera (baja cancelación, alta retención). El sistema debe poder reportar las métricas que sustenten estos premios.

**R-COM-05 — Ajustes y clawbacks.** Si una póliza se cancela en un periodo en el que ya se pagó comisión, la aseguradora puede descontar ("clawback") la comisión en el siguiente corte. El sistema debe poder generar el ajuste correspondiente y propagarlo a promotoría y agente.

### 7.4 Cortes de liquidación

**R-COM-06 — Periodicidad configurable.** El corte de liquidación interno (de BCA hacia su red) puede ser mensual, quincenal o según contrato con cada promotoría afiliada. El sistema debe soportar cortes configurables.

**R-COM-07 — Estado de comisión.** Cada comisión calculada tiene estado: **devengada** (la póliza se pagó y generó la comisión), **liquidable** (entró en el corte), **liquidada** (BCA ya cobró de la aseguradora o ya pagó a la promotoría/agente), **ajustada** (sufrió clawback o corrección).

**R-COM-08 — Inmutabilidad de cortes cerrados.** Una vez cerrado un corte de liquidación, las comisiones de ese corte no se modifican. Cualquier ajuste posterior se registra en el corte siguiente.

### 7.5 Reportes de liquidación que el negocio necesita

**Para BCA (dirección):**
- Comisión total cobrada de cada aseguradora por periodo.
- Comparativo: lo que se cobró vs lo que se liquidó a la red vs margen retenido.
- Ranking de promotorías afiliadas por productividad.
- Ranking de agentes por productividad (global y dentro de su promotoría).
- Avance hacia bonos y premios por umbral.
- Ajustes y clawbacks registrados.

**Para promotorías afiliadas:**
- Su PCA acumulada y la de su red de agentes.
- Comisión calculada para el corte actual.
- Detalle por agente bajo su promotoría.
- Histórico de liquidaciones recibidas.

**Para agentes:**
- Su PCA personal acumulada.
- Comisión calculada en el corte actual.
- Detalle de los recibos que componen su cálculo.
- Estado de vigencia de sus pólizas.

### 7.6 Lo que el sistema **no** hace en v1.0

- **No ejecuta pagos bancarios.** Entrega el cálculo y el reporte; la dispersión efectiva se hace en el sistema de tesorería o bancario externo.
- **No emite recibos fiscales.** La factura/CFDI de la comisión sigue siendo proceso administrativo separado, aunque el sistema entrega los datos base para emitirla.
- **No reconcilia automáticamente lo cobrado de la aseguradora contra lo calculado.** Se sugiere que esta función exista pero queda como mejora de v1.1 una vez estables las reglas básicas.

---

## 8. Roles y Permisos

El sistema opera con perfiles diferenciados que reflejan la jerarquía de la red.

| Rol | Quién lo encarna | Qué hace en el día a día | Qué ve y hace en el sistema |
|---|---|---|---|
| **Agente Portal** | Agente vendedor | Vende y atiende clientes | Consulta sus propias pólizas, estado de vigencia, su PCA y su comisión calculada. No ve datos de otros agentes, otras promotorías ni factores aplicados. No importa archivos. |
| **Gerente de Promotoría Afiliada** | Cabeza de promotoría afiliada | Recluta y desarrolla agentes de su red | Consulta pólizas, PCA y comisiones de **todos los agentes bajo su promotoría**. Ve avance hacia bonos. No ve otras promotorías. No importa archivos. |
| **Operador de Datos** | Personal administrativo de BCA | Alta de pólizas, corrida diaria de cobranza | Crea pólizas, ejecuta importaciones, ve reportes de PCA agregados. No ve factor aplicado. No cancela recibos. |
| **Líder** | Dirección operativa BCA | Audita resultados, valida productividad y comisiones | Todo lo del Operador + ve factor aplicado, bitácora de importaciones, reportes consolidados de toda la red. Genera y aprueba cortes de liquidación. No edita factores ni esquemas de comisión. |
| **Director Comercial** | Dirección comercial / Operativa estratégica | Supervisión de comisiones, liquidaciones, relación con aseguradoras | Acceso equivalente al Director General: cancela recibos, edita factores, define esquemas de comisión, gestiona cortes de liquidación. No tiene acceso a configuración de usuarios ni promotorías afiliadas (responsabilidad del Director General). |
| **Director General** | Dueño/CEO de BCA | Configura el sistema, autoriza excepciones, define esquemas | Acceso completo. Cancela recibos, edita factores, define esquemas de comisión, gestiona promotorías, agentes y usuarios. |

**Reglas adicionales:**

- Ningún usuario accede sin un rol asignado.
- **Cancelación de recibos:** exclusiva del Director General y Director Comercial.
- **Edición de tablas de factores PCA:** exclusiva del Director General y Director Comercial.
- **Definición de esquemas de comisión:** exclusiva del Director General y Director Comercial.
- **Apertura y cierre de cortes de liquidación:** Líder, Director General y Director Comercial.
- **Gestión de promotorías y agentes:** exclusiva del Director General.
- **Gestión de usuarios y roles:** exclusiva del Director General.
- **Visibilidad cruzada entre promotorías afiliadas:** prohibida — cada gerente solo ve su red.

---

## 9. Datos Maestros — Catálogos Configurables

### 9.1 Aseguradoras

Catálogo de las aseguradoras con las que BCA opera. Cada una con:
- Nombre, identificación.
- Estado activa/inactiva.
- Ramos que ofrece.
- Definición del formato de archivo de cobranza (referencia al parser correspondiente).

**Iniciales:** MetLife (activa, Vida y GMM), Qualitas (futura, Autos), Insurance (pendiente definición).

### 9.2 Promotorías afiliadas

Catálogo de las promotorías bajo el paraguas de BCA. Cada una con:
- Nombre.
- Datos fiscales.
- Gerente responsable.
- Estado activa/inactiva.
- Esquema de comisión interno acordado con BCA.

### 9.3 Agentes

Cada agente:
- Nombre completo y datos de contacto.
- Clave de agente (la que usa cada aseguradora — puede tener varias).
- **Promotoría afiliada a la que pertenece actualmente.**
- Estado: **prospecto** (no computa) o **con licencia** (computa para PCA y comisiones).
- Historial de cambios de promotoría afiliada.
- Esquema de comisión personal (si difiere del de su promotoría).

### 9.4 Conductos de pago

Por aseguradora (cada una usa sus propios códigos). Editable. Cada conducto: nombre visible + código exacto en archivo + estado activo/inactivo.

Conductos iniciales conocidos para MetLife:
- `CARGOS AUTOMÁTICOS`, `AGENTE DIRECTO` (Vida).
- `TARJ.CRED.`, `TAR DEBITO`, `CLABE`, `AMEX`, `AGENTE` (GMM).

### 9.5 Tablas de factores PCA

Por aseguradora, por año, por ramo. Editable por el administrador. Carga inicial: tabla MetLife 2026 (17 registros).

### 9.6 Esquemas de comisión

Por aseguradora, por ramo, por producto, por nivel de red, por tipo de evento (primer año, renovación, bono, premio). Editable.

### 9.7 Contratantes

Catálogo de clientes finales con estructura completa para almacenar y recuperar información con facilidad. Cada contratante incluye:

**Identificación (requerida):**
- RFC (17 caracteres) — con validación de formato mexicano.
- CURP (18 caracteres) — con validación de formato mexicano.
- Nombre completo.
- Dirección.

**Datos de Contacto:**
- Teléfono(s).
- Correo electrónico.
- Contacto alterno (si aplica).

**Expediente — Datos Adicionales (vinculados automáticamente desde pólizas):**
Esta sección almacena información que los agentes y usuarios del sistema necesitan recuperar rápidamente para atender al contratante:

  - **Beneficiarios de la Póliza:** Nombres, relación con contratante, porcentaje de participación. Se actualiza cada vez que se modifica una póliza con beneficiarios.
  - **Coberturas de la Póliza:** Listado de coberturas activas, montos asegurados y números de póliza asociados. Permite al agente conocer rápidamente qué está cubierto.
  - **Referencias de Pago de la Póliza:** Historial de conductos de pago registrados (tarjeta de crédito, CLABE, cargo automático, etc.), últimos 4 dígitos (si aplica), cuentas bancarias vinculadas. Facilita al agente processar pagos o redirigir al contratante al conducto correcto.

**Nota de implementación:** Estos datos adicionales se almacenan como **copia en el registro del contratante** para acceso rápido, pero su fuente de verdad son las pólizas y los recibos. Cuando una póliza se cancela o se modifica, el sistema actualiza estos campos de forma automática (con trazabilidad según R-GLOB-04).

---

## 10. Restricciones y Reglas Transversales

**R-GLOB-01 — Encoding.** Los archivos de MetLife vienen en Latin-1. El sistema debe detectar el encoding sin pedir intervención del operador. Otras aseguradoras pueden traer otros encodings; el sistema debe ser tolerante.

**R-GLOB-02 — Formato de fecha.** Las fechas vienen en `DD/MM/YYYY` (formato mexicano). Se almacenan internamente en formato estándar.

**R-GLOB-03 — Formato de importes.** Coma como separador de miles, punto como decimal. El sistema normaliza.

**R-GLOB-04 — Trazabilidad de cambios.** Toda modificación a campos críticos (estado de recibo, PCA, factor aplicado, "Pagado Hasta", estado de póliza, estado de agente, esquemas de comisión) queda trazada con quién y cuándo.

**R-GLOB-05 — Moneda.** Pesos mexicanos como divisa funcional; dólares como secundaria. Tipo de cambio a fecha contable del movimiento.

**R-GLOB-06 — Diseño multi-aseguradora desde el inicio.** Aunque la v1.0 solo cubra MetLife y Qualitas operativamente, el modelo de datos y la arquitectura deben asumir desde el diseño que habrá Atlas y potencialmente más. **No hardcodear MetLife en ningún punto crítico.**

---

## 11. Datos de Referencia para Dimensionamiento

| Variable | Volumen aproximado |
|---|---|
| Aseguradoras en v1.0 | 2 (MetLife, Qualitas). v1.1 prevista: 3 (+ Atlas) |
| Promotorías afiliadas a BCA | Decenas |
| Agentes activos en la red | Cientos (a confirmar) |
| Pólizas vigentes en arranque | A confirmar tras corte 1 de Junio de 2026 |
| Filas por archivo diario Vida MetLife | ~200 |
| Filas por archivo diario GMM MetLife | ~260 |
| Archivos procesados por día | 2 en v1.0 (uno por ramo MetLife) |
| Productos comercializados | ~10 Vida + ~5 GMM (MetLife) |
| Usuarios concurrentes | Decenas (operación interna BCA + gerentes de promotoría + agentes consultando) |

El sistema **no es de alto tráfico transaccional**. Es de **alta integridad de datos, alta exigencia de auditoría y alta visibilidad jerárquica** (cada nivel ve lo que le corresponde).

---

## 12. Criterios de Aceptación del Negocio

El negocio considerará exitosa la implementación si:

1. La carga del portafolio inicial completa en menos de una hora.
2. La corrida diaria de cobranza toma menos de 10 minutos de operación humana y produce bitácora clara.
3. El reporte de PCA por agente cuadra contra el cálculo manual actual de BCA dentro de un margen explicable por exclusiones legítimas.
4. Los recibos históricos no cambian su PCA aunque cambien las tablas de factores.
5. Ningún operador puede modificar "Pagado Hasta" manualmente.
6. La cancelación de un recibo se refleja correctamente en "Pagado Hasta" y dispara el ajuste de comisión correspondiente.
7. La bitácora de importaciones permite auditar cualquier sesión pasada.
8. **Un agente solo ve sus propias pólizas, su PCA y su comisión.**
9. **Un gerente de promotoría afiliada solo ve a su red — nunca a otras promotorías.**
10. **El corte de liquidación mensual se genera con un clic y produce reportes diferenciados para BCA, para cada promotoría afiliada y para cada agente.**
11. La incorporación de Atlas en v1.1 **no requiere reescribir el núcleo del sistema** — solo agregar el parser de su archivo y sus tablas maestras.

---

## 13. Pendientes de Definición con Cliente

| # | Punto | Responsable | Impacto |
|---|---|---|---|
| 1 | Estructura organizacional real: cuántas promotorías afiliadas hay, sus nombres, sus gerentes, sus agentes | BCA | Datos maestros y modelo de seguridad |
| 2 | Esquema de comisión que MetLife paga a BCA: porcentajes, primer año vs renovación, bonos por volumen, premios | BCA + MetLife | Proceso D — corazón del cálculo de ingresos |
| 3 | Esquema de comisión interno: cómo reparte BCA entre las promotorías y los agentes | Dirección BCA | Proceso D — distribución a la red |
| 4 | Periodicidad y mecánica de los cortes de liquidación internos | Dirección BCA | Proceso D — corte de liquidación |
| 5 | Confirmación de tabla GMM del primer trimestre 2026 | Guillermo (BCA) | Carga de factores con vigencia temporal |
| 6 | Confirmación de campos de exclusión Vida en archivos futuros vs captura manual | Guillermo (BCA) | Modelo de datos y wizards |
| 7 | Confirmación nombre exacto del producto "TempoLife Grandes Sumas y Riesgo Preferente" | Guillermo (BCA) | Mapeo de factores Vida |
| 8 | Estructura del archivo de Qualitas (Autos) | BCA + Qualitas | Diseño del parser fase 2 |
| 9 | Aseguradora "Atlas": confirmar nombre comercial, ramos que ofrece, formato de archivo | BCA | Alcance v1.1 / v1.2 |
| 10 | Manejo de clawbacks: ¿la aseguradora los notifica en archivo separado? ¿en el mismo CSV? | BCA + aseguradoras | Proceso D — ajustes |
| 11 | Necesidad o no de reconciliar lo cobrado de la aseguradora contra lo calculado por el sistema | Dirección BCA | Alcance v1.1 |

---

## 14. Glosario

| Término | Definición |
|---|---|
| **Promotoría de promotorías** | Modelo de BCA: consolidador que agrupa varias promotorías afiliadas bajo su estructura para escalar volumen y obtener mejores condiciones de las aseguradoras. |
| **Promotoría afiliada** | Promotoría pequeña que se ha unido a BCA bajo su paraguas administrativo, conservando su identidad comercial y su red de agentes. |
| **Aseguradora** | Compañía emisora de las pólizas. En el alcance v1.0: MetLife, Qualitas. v1.1: Atlas. |
| **Agente** | Persona que vende y atiende pólizas. Pertenece a una promotoría afiliada. |
| **Póliza** | Contrato entre contratante y aseguradora. |
| **Recibo** | Fracción de la prima anual correspondiente a un periodo. Unidad de cobranza. |
| **Prima Neta** | Monto base del recibo, sin impuestos ni gastos. Base de cálculo de PCA. |
| **Prima Total** | Prima Neta + recargos + gastos + impuestos. Lo que pagó el cliente. |
| **PCA (Prima Computable)** | Prima Neta ajustada por un factor. Indicador de productividad sobre el cual se liquidan comisiones. |
| **Factor de Ajuste** | Multiplicador definido por la aseguradora que se aplica a la Prima Neta para obtener la PCA. |
| **Pagado Hasta** | Fecha hasta la cual la póliza tiene cobertura efectivamente pagada. |
| **FIFO** | Regla de aplicación de pagos al recibo pendiente más antiguo. |
| **Conducto** | Vía de pago (tarjeta, cargo automático, etc.). |
| **Ramo** | Familia de productos: Vida, GMM, Autos. |
| **Comisión** | Pago de la aseguradora a BCA (y de BCA a su red) calculado sobre la PCA. |
| **Bono** | Pago adicional por superar umbrales de volumen. |
| **Premio** | Pago adicional por calidad de la cartera (conservación, retención). |
| **Clawback** | Descuento de comisión previamente pagada por cancelación posterior de la póliza. |
| **Corte de liquidación** | Periodo cerrado sobre el cual se calculan y pagan las comisiones a la red. |
| **Aportación adicional** | Pago extra del cliente sobre productos capitalizables. No computa PCA. |
| **LSP / GCAYE** | Nombres internos MetLife de los archivos planos de Vida y Gastos Médicos respectivamente. |

---

*Documento elaborado por Hábitat Digital como insumo para diseño de arquitectura. No prescribe plataforma, modelo de datos físico, ni stack tecnológico.*
