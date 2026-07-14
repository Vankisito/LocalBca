# BDD — Comportamiento Esperado del Sistema · Grupo BCA Seguros

**Proyecto:** Grupo BCA — Gestión de Pólizas, Cobranza, PCA y Comisiones
**Audiencia:** Dirección de BCA, analistas funcionales, desarrolladores y QA
**Propósito:** Documento base de *Behavior Driven Development*. Describe, en lenguaje de comportamiento, **qué debe hacer el sistema** desde la perspectiva del negocio.
**Versión:** 3.0 — base inicial
**Fecha:** Mayo 2026

---

## Cómo leer este documento

Este documento recoge la visión del **Director General de Grupo BCA** y el **Director Comercial de Grupo BCA** sobre cómo debe comportarse el sistema que reemplaza las hojas de cálculo con las que hoy se administra la operación de seguros. Está redactado como una conversación traducida a escenarios: cada **Característica** abre con la intención de negocio y se desglosa en **Escenarios** con la forma *Dado* (contexto) → *Cuando* (acción) → *Entonces* (resultado esperado).

- No es un manual de uso ni un documento técnico: describe **comportamiento**, no pantallas ni implementación.
- Los escenarios son la fuente de verdad de "qué significa que esto funcione". Sirven de base para pruebas y para validar entregas.
- Al cierre de cada característica hay una línea de **Reglas** que la conecta con las reglas de negocio, para trazabilidad.

### Convención Gherkin (español)

`Característica` · `Antecedentes` · `Escenario` · `Esquema del escenario` + `Ejemplos` · pasos `Dado` / `Cuando` / `Entonces` / `Y` / `Pero`.

### Glosario mínimo

| Término                    | Significado                                                                         |
| -------------------------- | ----------------------------------------------------------------------------------- |
| **Póliza**                 | Contrato entre el contratante y la aseguradora. Vive años.                          |
| **Recibo**                 | Fracción de la prima anual de una póliza para un periodo. Unidad de cobranza.       |
| **Prima Neta**             | Monto base del recibo, sin impuestos ni recargos. Base de la PCA.                   |
| **Prima Total**            | Lo que efectivamente paga el cliente (neta + recargos + impuestos).                 |
| **PCA (Prima Computable)** | Prima Neta ajustada por un factor de la aseguradora. Base para liquidar comisiones. |
| **Pagado Hasta**           | Fecha hasta la cual la póliza está cubierta por pagos efectivos.                    |
| **FIFO**                   | Regla de cobranza: siempre se paga primero el recibo pendiente más antiguo.         |
| **Conducto**               | Vía de pago (tarjeta, cargo automático, CLABE, etc.).                               |
| **Ramo**                   | Familia de producto: Vida, GMM (Gastos Médicos Mayores) o Autos.                    |
| **Promotoría afiliada**    | Promotoría  integrada bajo BCA, con su propia red de agentes.                       |
| **Clave Definitiva**       | Clave que la aseguradora asigna al agente certificado. Solo este nivel computa PCA. |
| **Clawback**               | Descuento de comisión ya pagada cuando una póliza se cancela después.               |
| **Corte de liquidación**   | Periodo cerrado sobre el que se calculan y pagan las comisiones a la red.           |

---

## Característica 1 — Estructura organizacional de la red

> Como Dirección de BCA, quiero que el sistema modele la red en tres niveles (BCA → promotorías afiliadas → agentes), para poder atribuir cada póliza a su cadena y liquidar correctamente a cada nivel.

```gherkin
Antecedentes:
  Dado un holding "Grupo BCA"
  Y una promotoría afiliada "Promotoría Norte" que cuelga del holding
  Y una promotoría afiliada "Promotoría Sur" que cuelga del holding
```

```gherkin
Escenario: Un agente pertenece a exactamente una promotoría
  Dado un agente nuevo "Ana López"
  Cuando se le adscribe a "Promotoría Norte"
  Entonces el sistema muestra a "Ana López" como parte de "Promotoría Norte"
  Y la cadena del agente queda como Ana López → Promotoría Norte → Grupo BCA
```

```gherkin
Escenario: Rechazar una jerarquía organizacional inválida
  Dado un agente "Ana López"
  Cuando se intenta adscribirlo directamente al holding "Grupo BCA" sin promotoría
  Entonces el sistema rechaza el guardado
  Y exige que el agente cuelgue de una promotoría afiliada
```

```gherkin
Escenario: Cambio de promotoría conserva las pólizas históricas en la promotoría original
  Dado un agente "Ana López" en "Promotoría Norte"
  Y una póliza "MET-001" vendida por ella mientras estaba en "Promotoría Norte"
  Cuando "Ana López" se mueve a "Promotoría Sur"
  Entonces sus nuevas pólizas se acreditan a "Promotoría Sur"
  Y la póliza "MET-001" sigue acreditada a "Promotoría Norte" para efectos de liquidación
  Y el sistema conserva el historial del cambio (de dónde, a dónde, cuándo y quién lo hizo)
```

```gherkin
Escenario: Inactivar una promotoría exige migrar a sus agentes primero
  Dado una "Promotoría Norte" con agentes adscritos
  Cuando se intenta inactivar "Promotoría Norte"
  Entonces el sistema lo impide mientras tenga agentes adscritos
  Y solicita migrar esos agentes a otra promotoría antes de inactivarla
```

```gherkin
Escenario: La productividad se puede reportar a tres niveles
  Dado pólizas pagadas distribuidas entre varias promotorías y agentes
  Cuando se consulta el reporte de productividad
  Entonces se puede ver el total de BCA
  Y el total por cada promotoría afiliada
  Y el total por cada agente individual
```

*Reglas: R-ORG-01, R-ORG-02, R-ORG-03, R-ORG-04, R-ORG-05.*

---

## Característica 2 — Catálogos y datos maestros

> Como Dirección de BCA, quiero catálogos configurables (aseguradoras, productos, conductos, factores, agentes y contratantes), para operar sin pedir desarrollo cada vez que cambia un dato maestro.

### Aseguradoras y productos

```gherkin
Escenario: Alta de aseguradora con su código
  Dado el catálogo de aseguradoras
  Cuando se da de alta "MetLife" con su código de aseguradora y sus ramos (Vida y GMM)
  Entonces "MetLife" queda disponible para asociar productos, conductos, factores y archivos de cobranza
```

```gherkin
Escenario: El producto se maneja con atributos y variantes
  Dado un producto base de Vida
  Cuando se definen sus atributos (por ejemplo plan, tipo de cobertura y moneda)
  Entonces el sistema genera las variantes correspondientes del producto
  Y cada variante puede tener su propio factor de PCA según moneda
```

```gherkin
Escenario: Se espera cargar el catálogo completo de productos por aseguradora
  Dado que cada aseguradora entrega su catálogo de productos con sus atributos y variantes
  Cuando se carga el catálogo completo de la aseguradora
  Entonces todos sus productos y variantes quedan disponibles para asociarse a pólizas y factores
  Y una póliza solo puede apuntar a un producto existente en el catálogo
```

```gherkin
Escenario: Alta de conducto de pago con su código exacto
  Dado el catálogo de conductos de "MetLife"
  Cuando se registra el conducto "Cargo Automático" con el código exacto tal como aparece en sus archivos
  Entonces ese conducto puede mapearse automáticamente al procesar la cobranza de "MetLife"
```

```gherkin
Escenario: Las tablas de factores PCA son editables por aseguradora, año y ramo
  Dado el catálogo de factores
  Cuando la Dirección carga la tabla de factores de "MetLife" para 2027
  Entonces los nuevos factores aplican a los pagos futuros
  Pero no recalculan los recibos ya pagados con la tabla anterior
```

### Agentes — identidad y nomenclatura de carrera

```gherkin
Escenario: La identidad del agente es su Id interno, no su clave
  Dado un agente identificado por su nombre, RFC y CURP
  Cuando se intenta registrar otro agente con el mismo Id interno (nombre, RFC, CURP)
  Entonces el sistema lo rechaza por duplicado
  Y deja claro que el Id interno es el identificador definitivo de la organización
```

```gherkin
Escenario: Un mismo agente tiene claves distintas por aseguradora
  Dado un agente "Ana López"
  Cuando se le registra una clave para "MetLife" y otra clave distinta para "Qualitas"
  Entonces ambas claves conviven en el mismo agente
  Y la clave no se usa como identificador del agente, porque varía entre aseguradoras
```

```gherkin
Esquema del escenario: Nomenclatura de carrera del agente por aseguradora
  Dado un agente en etapa "<etapa>"
  Cuando se consulta su clave en la aseguradora
  Entonces su situación es "<descripcion>"

  Ejemplos:
    | etapa            | descripcion                                                        |
    | Prospecto        | En reclutamiento, sin clave asignada por la aseguradora            |
    | Clave de Arranque| La aseguradora le asignó clave al iniciar la carrera, sin certificar|
    | Clave Definitiva | La aseguradora le asignó la clave definitiva, ya certificado       |
```

### Contratantes (clientes finales)

```gherkin
Escenario: Alta de contratante con expediente completo
  Dado el catálogo de contratantes
  Cuando se registra un contratante con su RFC válido (formato mexicano)
  Y sus datos demográficos (fecha de nacimiento, estado civil, género)
  Y su domicilio y datos de contacto
  Entonces el contratante queda disponible para asociarse a pólizas
  Y su expediente concentra beneficiarios, coberturas y referencias de pago de sus pólizas
```

```gherkin
Escenario: Validar el formato del RFC del contratante
  Dado el alta de un contratante
  Cuando se captura un RFC con formato inválido
  Entonces el sistema rechaza el dato y solicita un RFC con formato mexicano correcto
```

*Reglas: §9 (datos maestros), R-PCA-02 (factores configurables), nomenclatura de agentes, identidad por Id interno.*

---

## Característica 3 — Gestión de pólizas

> Como Operador de BCA, quiero dar de alta y gestionar pólizas con su plan de pagos, para tener un catálogo confiable que alimente cobranza, PCA y comisiones.

```gherkin
Escenario: El número de póliza es único por aseguradora
  Dado una póliza "MET-2026-00001" de "MetLife"
  Cuando se intenta crear otra póliza con el mismo número en "MetLife"
  Entonces el sistema rechaza el duplicado
  Pero permite ese mismo número si la aseguradora es distinta
```

```gherkin
Escenario: La selección de producto funciona en cascada
  Dado una póliza nueva
  Cuando se elige la aseguradora "MetLife" y el ramo "Vida"
  Entonces el campo Producto solo ofrece productos de "MetLife" del ramo "Vida"
```

```gherkin
Escenario: El asegurado puede ser distinto del contratante
  Dado una póliza de Vida con contratante "Juan Pérez"
  Cuando el asegurado es una persona distinta
  Entonces el asegurado se captura como contacto aparte ligado a la póliza, con su propio correo
  Pero si el asegurado es el mismo contratante, se puede apuntar al contratante
```

```gherkin
Escenario: Al elegir el agente se completa la promotoría
  Dado una póliza nueva
  Cuando se asigna el agente "Ana López"
  Entonces la promotoría se completa sola con la promotoría actual del agente
  Y queda de solo lectura
```

```gherkin
Esquema del escenario: Confirmar la póliza genera el plan de pagos del primer año
  Dado una póliza en borrador con periodicidad "<periodicidad>"
  Cuando se confirma la póliza
  Entonces la póliza pasa a "Activa"
  Y se generan "<recibos>" recibos pendientes con su ventana de fechas y prima modal

  Ejemplos:
    | periodicidad | recibos |
    | Mensual      | 12      |
    | Trimestral   | 4       |
    | Semestral    | 2       |
    | Anual        | 1       |
```

```gherkin
Escenario: Los beneficiarios de Vida deben sumar exactamente 100% para confirmar
  Dado una póliza de Vida con beneficiarios cuyos porcentajes suman 90%
  Cuando se intenta confirmar la póliza
  Entonces el sistema impide la confirmación
  Y avisa que la suma de porcentajes de los beneficiarios debe ser 100%
```

```gherkin
Escenario: Una póliza de Vida admite hasta diez beneficiarios
  Dado una póliza de Vida
  Cuando se capturan beneficiarios con su parentesco y porcentaje
  Entonces se aceptan hasta diez beneficiarios
  Y al confirmar, sus porcentajes deben sumar 100%
```

```gherkin
Escenario: Una póliza de GMM admite asegurados adicionales (dependientes)
  Dado una póliza de GMM
  Cuando se capturan asegurados adicionales con nombre, parentesco y fecha de nacimiento
  Entonces se aceptan hasta cinco dependientes cubiertos bajo la póliza
```

```gherkin
Escenario: No se puede regenerar el plan de pagos si ya hay recibos pagados
  Dado una póliza activa con al menos un recibo pagado
  Cuando se intenta regenerar el plan de pagos
  Entonces el sistema lo impide para proteger el historial
```

```gherkin
Escenario: El estatus de pago es declarativo y no determina la vigencia
  Dado una póliza con estatus de pago "al corriente"
  Cuando ese estatus difiere de lo que indican los recibos pagados
  Entonces "Pagado Hasta" sigue determinándose por los recibos pagados
  Y el estatus de pago se conserva solo como dato informativo
```

```gherkin
Escenario: La póliza conserva su póliza origen para trazar renovaciones
  Dado una póliza que renueva o convierte a otra anterior
  Cuando se registra la póliza origen
  Entonces el sistema conserva la trazabilidad histórica entre ambas
```

```gherkin
Escenario: Cambio de agente de una póliza con historial
  Dado una póliza activa atribuida a "Ana López"
  Cuando se cambia el agente de la póliza a "Beto Ruiz" indicando el motivo
  Entonces la póliza queda atribuida a "Beto Ruiz" en adelante
  Y el historial registra agente y promotoría anteriores y nuevos, fecha, motivo y autor
```

*Reglas: R-POL-01 a R-POL-07, D-04, D-05, D-06.*

---

## Característica 4 — Carga masiva del portafolio

> Como Operador de BCA, quiero cargar el portafolio desde el layout de hojas de cálculo, para dar de alta cientos de pólizas en el arranque o al incorporar una promotoría, sin duplicar ni corromper datos.

```gherkin
Antecedentes:
  Dado el layout de portafolio "LAY_OUT_-_Portafolio_BCA"
  Y que sus hojas son "VIDA", "GMM" y "Autos"
  Y que cada hoja tiene encabezados en la fila 2 y datos desde la fila 4
```

```gherkin
Escenario: Validación previa sin tocar la base de datos
  Dado un archivo de portafolio al que le falta una hoja o una columna requerida
  Cuando el operador ejecuta la validación previa
  Entonces el sistema reporta los faltantes
  Y no crea ni modifica ninguna póliza
```

```gherkin
Escenario: Cargar el portafolio sin duplicar pólizas
  Dado un archivo válido con pólizas nuevas y pólizas ya existentes
  Cuando el operador graba la carga
  Entonces se crean las pólizas nuevas
  Y no se duplica ninguna póliza ya existente para esa aseguradora
  Y cada póliza creada genera su plan de recibos hacia adelante
```

```gherkin
Escenario: GMM autopobla deducible y coaseguro desde el archivo
  Dado una fila de la hoja "GMM" con deducible y coaseguro
  Cuando se crea la póliza GMM
  Entonces el deducible y el coaseguro se toman del archivo
  Porque son insumos del cálculo de PCA de GMM
```

```gherkin
Escenario: El conducto del layout queda como conducto por defecto
  Dado una fila con un conducto de cobro
  Cuando se crea la póliza
  Entonces ese conducto queda como conducto por defecto de la póliza y de sus recibos
```

```gherkin
Escenario: La póliza se asocia a su agente por la clave de la aseguradora
  Dado una fila con una Clave de Agente
  Cuando se crea la póliza
  Entonces el agente se resuelve por esa clave dentro de la aseguradora
  Y la búsqueda contempla tanto la clave de arranque como la definitiva
```

```gherkin
Escenario: El producto del layout se mapea a la variante del catálogo
  Dado una fila con Producto y Plan
  Cuando se crea la póliza
  Entonces el producto se mapea contra el catálogo a la variante correspondiente
```

```gherkin
Escenario: Beneficiarios y dependientes se desglosan desde la misma fila
  Dado una fila de "VIDA" con beneficiarios y una de "GMM" con asegurados adicionales
  Cuando se crean las pólizas
  Entonces los beneficiarios de Vida se desglosan en sus registros (hasta diez)
  Y los asegurados adicionales de GMM se desglosan en sus registros (hasta cinco)
```

```gherkin
Escenario: La carga produce un reporte de resultados
  Dado una carga ejecutada
  Cuando termina el proceso
  Entonces el sistema reporta cuántas pólizas se crearon, cuántas se actualizaron y cuántas se rechazaron con su motivo
```

```gherkin
Escenario: Incorporar una promotoría nueva con su cartera
  Dado que se incorpora una promotoría afiliada nueva con su portafolio
  Cuando se carga su cartera de forma aislada
  Entonces todas esas pólizas quedan atribuidas correctamente a esa promotoría
```

```gherkin
Escenario: Carga con filas mixtas — las válidas se crean y la inválida se rechaza
  Dado un archivo de portafolio con cuatro filas válidas y una con clave de agente inexistente
  Cuando el operador graba la carga
  Entonces se crean las cuatro pólizas válidas
  Y la fila con clave inexistente se rechaza indicando su motivo
  Y el proceso no se detiene por la fila rechazada
  Y el reporte de resultados deja constancia de las creadas y de la rechazada
```

*Reglas: §4.4 (carga masiva), R-POL-01, R-POL-02.*

---

## Característica 5 — Cobranza recibo por recibo

> Como Operador de BCA, quiero registrar el pago de un recibo, para mantener al día la vigencia de la póliza y disparar el cálculo de PCA.

```gherkin
Escenario: Registrar el pago de un recibo pendiente
  Dado un recibo pendiente de una póliza activa
  Cuando el operador captura la fecha de pago y el conducto y registra el pago
  Entonces el recibo pasa a "Pagado"
  Y se congela su PCA y su factor aplicado
  Y se toma una foto inmutable del agente y la promotoría al momento del pago
  Y "Pagado Hasta" de la póliza avanza a la fecha de fin de vigencia del recibo
```

```gherkin
Escenario: No se puede registrar un pago sin las precondiciones mínimas
  Dado un recibo pendiente sin fecha de pago o sin conducto
  Cuando se intenta registrar el pago
  Entonces el sistema lo impide
  Y no congela ninguna PCA con datos incompletos
```

```gherkin
Escenario: Regla FIFO — no se puede pagar un recibo fuera de orden
  Dado una póliza con recibos pendientes de enero, febrero y marzo
  Cuando se intenta registrar el pago del recibo de marzo
  Entonces el sistema rechaza el pago
  Y avisa que primero debe pagarse el recibo de enero
```

```gherkin
Escenario: Pagar el último recibo de la anualidad genera la siguiente
  Dado una póliza cuyo recibo pagado es el último de la anualidad
  Cuando se registra ese pago
  Entonces el sistema genera automáticamente los recibos de la siguiente anualidad
```

```gherkin
Escenario: Cancelar un pago (solo Dirección) revierte el recibo a pendiente
  Dado un recibo pagado que es el último pago de su póliza
  Y un usuario con rol de Director o Director Comercial
  Cuando cancela el pago
  Entonces el recibo vuelve a "Pendiente"
  Y se limpian su fecha de pago, conducto y PCA
  Y "Pagado Hasta" de la póliza retrocede en consecuencia
```

```gherkin
Escenario: Solo se puede cancelar el último pago (FIFO inverso)
  Dado una póliza con recibos de enero y febrero pagados
  Cuando se intenta cancelar el pago de enero estando febrero pagado
  Entonces el sistema lo impide
  Y exige cancelar primero el pago de febrero
```

```gherkin
Escenario: Anular un recibo pendiente (solo Dirección)
  Dado un recibo pendiente
  Y un usuario con rol de Director o Director Comercial
  Cuando anula el recibo
  Entonces el recibo pasa a "Cancelado" y nunca se cobrará
  Pero si el recibo ya estaba pagado, primero debe cancelarse el pago
```

*Reglas: R-COB-03, R-COB-07, R-PCA-04, §6 (capacitación).*

---

## Característica 6 — Cobranza masiva diaria y conciliación

> Como Operador de BCA, quiero procesar el archivo diario de cada aseguradora, para conciliar la cobranza por FIFO de forma automática y auditable, sin que un error puntual detenga el proceso.

```gherkin
Antecedentes:
  Dado que cada aseguradora entrega sus propios archivos de cobranza
  Y que el operador elige la aseguradora y el ramo antes de procesar
```

```gherkin
Escenario: La selección de aseguradora y ramo determina las reglas a aplicar
  Dado un archivo de cobranza
  Cuando el operador selecciona aseguradora "MetLife" y ramo "Vida"
  Entonces el sistema usa el lector, las columnas esperadas y la tabla de factores de ese formato
```

```gherkin
Escenario: Validación previa detiene el proceso si falta una columna crítica
  Dado un archivo al que le falta una columna requerida
  Cuando el operador inicia el procesamiento
  Entonces el sistema se detiene antes de tocar datos
  Y no crea bitácora de importación
```

```gherkin
Escenario: Las anulaciones se omiten y se registran
  Dado una fila marcada como anulación de pago
  Cuando se procesa el archivo
  Entonces esa fila se omite con la marca [ANULADO]
  Y no se cuenta como error
```

```gherkin
Escenario: Póliza inexistente o inactiva no detiene el proceso
  Dado una fila cuya póliza no existe o no está activa
  Cuando se procesa el archivo
  Entonces esa fila se marca [NO ENCONTRADA]
  Y el proceso continúa con las demás filas
```

```gherkin
Escenario: El pago liquida el recibo pendiente más antiguo (FIFO)
  Dado una póliza con varios recibos pendientes
  Cuando una fila de cobranza aplica un pago a esa póliza
  Entonces se liquida el recibo pendiente más antiguo, sin saltarse ninguno
```

```gherkin
Escenario: No se paga dos veces el mismo periodo (deduplicación)
  Dado una póliza sin recibos pendientes disponibles
  Cuando una fila intenta aplicar otro pago
  Entonces esa fila se marca [SIN RECIBO]
  Y el folio de endoso se conserva solo como dato de auditoría
```

```gherkin
Escenario: Pago en moneda distinta a la de la póliza
  Dado una fila cuya moneda difiere de la moneda de la póliza
  Cuando se procesa el pago
  Entonces se aplica el tipo de cambio del día de la fecha de aplicación
  Y se deja una marca [INFO] del tipo de cambio aplicado
```

```gherkin
Escenario: Conducto sin coincidencia en el catálogo
  Dado una fila con un conducto que no existe en el catálogo de la aseguradora
  Cuando se procesa el pago
  Entonces el conducto queda vacío
  Y se registra una marca [ADVERTENCIA]
```

```gherkin
Escenario: Un error en una fila no detiene el proceso completo
  Dado un archivo de cinco filas donde la tercera provoca un fallo técnico
  Cuando se procesa el archivo
  Entonces la fila con fallo se aísla y se marca [ERROR]
  Y las filas cuarta y quinta se procesan normalmente
```

*Reglas: R-COB-01 a R-COB-10, R-GLOB-01, R-GLOB-02, R-GLOB-03, R-GLOB-05.*

---

## Característica 7 — Bitácora de importación

> Como Líder de BCA, quiero que cada sesión de cobranza quede registrada de forma permanente, para poder auditar qué pasó en cualquier corrida pasada.

```gherkin
Escenario: Cada sesión de importación deja una bitácora completa
  Dado un archivo de cobranza procesado
  Cuando termina la sesión
  Entonces la bitácora registra quién ejecutó y cuándo, la aseguradora y el ramo, y el nombre del archivo
  Y los conteos de pagos exitosos, anulaciones ignoradas, pólizas no encontradas y errores
  Y la PCA total cobrada en la sesión
  Y el detalle línea por línea de las excepciones con su marca
```

```gherkin
Escenario: La bitácora no puede editarse ni borrarse
  Dado una bitácora de importación existente
  Cuando cualquier usuario, incluido el administrador, intenta editarla o eliminarla
  Entonces el sistema lo impide
```

```gherkin
Escenario: Una sesión sin pagos exitosos también deja bitácora
  Dado un archivo cuyas filas son todas anulaciones o pólizas inexistentes
  Cuando se procesa el archivo
  Entonces el sistema crea la bitácora de la sesión
  Y los conteos de pagos exitosos quedan en cero
  Y la PCA total de la sesión queda en cero
  Y las marcas correspondientes (por ejemplo [ANULADO] o [NO ENCONTRADA]) quedan en el detalle línea por línea
```

*Reglas: §5.4, §5.5 (códigos de marca).*

---

## Característica 8 — Prima Computable (PCA)

> Como Dirección de BCA, quiero que la PCA se calcule y se congele al momento del pago, para que las comisiones sean estables, auditables y nunca cambien retroactivamente.

```gherkin
Escenario: La PCA solo existe sobre recibos pagados
  Dado un recibo pendiente
  Cuando se consulta su PCA
  Entonces su PCA es cero, porque solo los pagos efectivos generan productividad
```

```gherkin
Escenario: La PCA se congela al pago y no se recalcula después
  Dado un recibo pagado con su PCA y su factor congelados
  Cuando la aseguradora publica una nueva tabla de factores el año siguiente
  Entonces ese recibo conserva su PCA y su factor originales
  Y los reportes históricos no cambian
```

```gherkin
Escenario: Solo el agente con Clave Definitiva genera PCA
  Dado pólizas pagadas de un agente "Prospecto", uno con "Clave de Arranque" y uno con "Clave Definitiva"
  Cuando se calcula la productividad
  Entonces solo computa la PCA del agente con "Clave Definitiva"
  Y las pólizas de "Prospecto" y "Clave de Arranque" no entran a PCA ni a comisiones, aunque tengan pólizas asignadas
```

```gherkin
Esquema del escenario: Factor de PCA de Vida MetLife 2026 por producto y moneda
  Dado un recibo pagado de Vida del producto "<producto>" en moneda "<moneda>"
  Cuando se calcula la PCA
  Entonces el factor aplicado es "<factor>"

  Ejemplos:
    | producto                                       | moneda | factor |
    | Universales                                    | MXN    | 100%   |
    | Universales                                    | USD    | 100%   |
    | TempoLife                                      | MXN    | 100%   |
    | TempoLife                                      | USD    | 80%    |
    | TempoLife Grandes Sumas y Riesgo Preferente    | USD    | 80%    |
    | TotalLife                                      | USD    | 80%    |
    | EducaLife                                      | USD    | 70%    |
    | PerfectLife                                    | USD    | 70%    |
    | Horizonte                                      | USD    | 70%    |
```

```gherkin
Esquema del escenario: Factor de PCA de GMM MetLife 2026 por coaseguro y deducible
  Dado un recibo pagado de GMM con coaseguro "<coaseguro>" y deducible "<deducible>"
  Cuando se calcula la PCA
  Entonces el factor aplicado es "<factor>"

  Ejemplos:
    | coaseguro | deducible          | factor          |
    | >= 10%    | >= $29,000 MXN     | 120%            |
    | >= 10%    | < $29,000 MXN      | 100%            |
    | <= 5%     | cualquiera         | 0% (no computa) |
```

```gherkin
Esquema del escenario: Exclusiones que dejan la PCA en cero
  Dado un recibo pagado con la condición "<condicion>"
  Cuando se calcula la PCA
  Entonces la PCA queda en cero con su motivo registrado
  Y el factor aplicado queda en cero

  Ejemplos:
    | condicion                                                    |
    | Aportación adicional en producto capitalizable               |
    | Cobertura individual de accidentes o invalidez               |
    | Vida con temporalidad menor a 10 años                        |
    | GMM con coaseguro menor o igual a 5%                         |
```

```gherkin
Escenario: La PCA siempre se expresa en pesos
  Dado un recibo pagado en dólares
  Cuando se calcula la PCA
  Entonces la prima neta se convierte a pesos antes de aplicar el factor
  Y la PCA queda expresada en pesos
```

```gherkin
Escenario: Cancelar un recibo pagado pone su PCA en cero
  Dado un recibo pagado con PCA
  Cuando se cancela ese pago
  Entonces su PCA pasa a cero
  Y "Pagado Hasta" de la póliza se recalcula
  Y si la cancelación afecta una liquidación ya emitida, se registra como ajuste en el siguiente corte
```

*Reglas: R-PCA-01 a R-PCA-04, §6.4, §6.5, §6.6, M3.*

---

## Característica 9 — Liquidación de comisiones a la red

> Como Dirección de BCA, quiero convertir la PCA cobrada en comisiones a repartir entre BCA, promotorías y agentes, con cortes cerrados e inmutables, para liquidar a la red de forma confiable.

```gherkin
Escenario: Cada recibo pagado genera comisión sobre su PCA
  Dado un recibo pagado con PCA
  Cuando se aplica el esquema de comisión vigente
  Entonces el sistema calcula la comisión correspondiente a cada nivel de la red
```

```gherkin
Escenario: Distinguir comisión de primer año y de renovación
  Dado un recibo del primer año de vigencia y otro de una renovación
  Cuando se calculan sus comisiones
  Entonces el sistema aplica el esquema de primer año al primero
  Y el esquema de renovación al segundo
```

```gherkin
Escenario: Bonos por superar umbrales de volumen
  Dado una red que supera un umbral acumulado de PCA en el periodo
  Cuando se evalúa el avance
  Entonces el sistema registra el bono liberado correspondiente
```

```gherkin
Escenario: Premios por permanencia o conservación de cartera
  Dado una cartera con baja cancelación y alta retención
  Cuando se evalúan las métricas de conservación
  Entonces el sistema reporta el sustento del premio correspondiente
```

```gherkin
Escenario: Clawback por cancelación posterior a una comisión pagada
  Dado una póliza cuya comisión ya se pagó
  Cuando la póliza se cancela en un periodo posterior
  Entonces el sistema genera el ajuste de clawback
  Y lo propaga a la promotoría y al agente
```

```gherkin
Esquema del escenario: Estados de una comisión
  Dado una comisión en estado "<estado>"
  Entonces su significado es "<significado>"

  Ejemplos:
    | estado     | significado                                              |
    | Devengada  | La póliza se pagó y generó la comisión                   |
    | Liquidable | Entró en el corte de liquidación                         |
    | Liquidada  | BCA ya cobró de la aseguradora o ya pagó a la red        |
    | Ajustada   | Sufrió clawback o corrección                             |
```

```gherkin
Escenario: Un corte de liquidación cerrado es inmutable
  Dado un corte de liquidación ya cerrado
  Cuando surge un ajuste posterior
  Entonces las comisiones del corte cerrado no se modifican
  Y el ajuste se registra en el corte siguiente
```

```gherkin
Escenario: Periodicidad de corte configurable por contrato
  Dado promotorías con periodicidades de corte distintas
  Cuando se configuran sus cortes (mensual, quincenal o según contrato)
  Entonces el sistema genera cada corte con su periodicidad acordada
```

*Reglas: R-COM-01 a R-COM-08.*

---

## Característica 10 — Reportes de PCA y productividad

> Como Dirección, Líder y Gerente, quiero ver la productividad por nivel y con filtros, para evaluar la red y liquidar con datos consistentes.

```gherkin
Escenario: Cortar el reporte por los tres niveles
  Dado pólizas pagadas distribuidas en la red
  Cuando se consulta el reporte de PCA
  Entonces se puede ver el total de BCA, el total por promotoría y el total por agente
  Y se puede filtrar por aseguradora, ramo, producto y rango de fechas de pago
```

```gherkin
Escenario: Los agentes sin Clave Definitiva no aparecen en los reportes de PCA
  Dado pólizas pagadas de agentes "Prospecto" y "Clave de Arranque"
  Cuando se consulta el reporte de PCA
  Entonces esos agentes no aparecen
  Porque solo computa la Clave Definitiva
```

```gherkin
Escenario: El reporte refleja la promotoría histórica, no la actual
  Dado un recibo pagado mientras el agente estaba en "Promotoría Norte"
  Y que después el agente se movió a "Promotoría Sur"
  Cuando se consulta el reporte de PCA del periodo del pago
  Entonces ese recibo aparece bajo "Promotoría Norte"
  Porque el reporte usa la foto inmutable tomada al momento del pago
```

*Reglas: §6.8, §7.5, R-PCA-03, C2.*

---

## Característica 11 — Roles, permisos y visibilidad

> Como Director General, quiero que cada rol vea y pueda hacer exactamente lo que le corresponde, para proteger la integridad de los datos y la confidencialidad entre promotorías.

```gherkin
Escenario: Un agente solo ve lo suyo
  Dado un agente que inicia sesión
  Cuando consulta pólizas y recibos
  Entonces solo ve sus propias pólizas y recibos
  Y no ve datos de otros agentes ni de otras promotorías
```

```gherkin
Escenario: Un gerente de promotoría solo ve su red
  Dado un gerente de "Promotoría Norte"
  Cuando consulta la productividad
  Entonces ve la de todos los agentes bajo "Promotoría Norte"
  Pero nunca la de otras promotorías
```

```gherkin
Escenario: El Operador no puede cancelar pagos ni anular recibos
  Dado un usuario con rol de Operador
  Cuando abre un recibo pagado
  Entonces no ve el botón de cancelar pago ni el de anular recibo
```

```gherkin
Escenario: "Pagado Hasta" es de solo lectura para todos
  Dado cualquier usuario, incluido el Director General
  Cuando abre una póliza
  Entonces no puede editar "Pagado Hasta" a mano
  Porque solo se mueve como consecuencia de un pago o de su cancelación
```

```gherkin
Esquema del escenario: Matriz de permisos por acción
  Dado un usuario con rol "<rol>"
  Cuando intenta la acción "<accion>"
  Entonces el sistema "<resultado>"

  Ejemplos:
    | rol               | accion                                   | resultado |
    | Agente            | Ver sus propias pólizas                  | permite   |
    | Agente            | Ver toda la red                          | impide    |
    | Operador          | Crear y confirmar pólizas                | permite   |
    | Operador          | Cancelar pago o anular recibo            | impide    |
    | Líder             | Ver bitácoras y reportes consolidados    | permite   |
    | Líder             | Editar factores o esquemas de comisión   | impide    |
    | Director Comercial| Cancelar pago, editar factores/esquemas  | permite   |
    | Director Comercial| Gestionar promotorías, agentes, usuarios | impide    |
    | Director General  | Gestionar promotorías, agentes, usuarios | permite   |
```

```gherkin
Escenario: Un usuario sin rol asignado no puede operar el módulo
  Dado un usuario al que no se le asignó ningún rol de BCA Seguros
  Cuando intenta acceder al módulo
  Entonces el sistema le niega el acceso
  Porque nadie opera sin un rol asignado
```

*Reglas: §8 (roles y permisos), Apéndice A (capacitación), R-POL-03.*

---

## Característica 12 — Reglas transversales

> Como Dirección de BCA, quiero que el sistema sea robusto ante formatos, monedas y nuevas aseguradoras, para que la operación no dependa de ajustes manuales ni de reescribir el núcleo.

```gherkin
Escenario: Detección de codificación de archivo sin intervención
  Dado un archivo de "MetLife" en codificación Latin-1
  Cuando se procesa
  Entonces el sistema lo lee correctamente sin pedirle al operador convertir el archivo
```

```gherkin
Escenario: Normalización de fechas e importes
  Dado fechas en formato "DD/MM/YYYY" e importes con coma de miles y punto decimal
  Cuando se procesan
  Entonces el sistema los normaliza a su formato interno estándar
```

```gherkin
Escenario: Trazabilidad de cambios a campos críticos
  Dado un cambio en un campo crítico (estado de recibo, PCA, factor, "Pagado Hasta", estado de póliza, estado de agente o esquema de comisión)
  Cuando se guarda el cambio
  Entonces queda registrado quién lo hizo y cuándo
```

```gherkin
Escenario: Multimoneda con peso como divisa funcional
  Dado un movimiento en dólares
  Cuando se contabiliza
  Entonces se aplica el tipo de cambio a la fecha contable del movimiento
  Y el peso mexicano es la divisa funcional de referencia
```

```gherkin
Escenario: Incorporar una nueva aseguradora sin reescribir el núcleo
  Dado que en una fase posterior se incorpora la aseguradora "Atlas"
  Cuando se agrega su lector de archivo y sus tablas maestras (productos, conductos, factores)
  Entonces "Atlas" opera en el sistema sin modificar el núcleo existente
```

*Reglas: R-GLOB-01 a R-GLOB-06.*

---

## Apéndice — Matriz de trazabilidad (regla → característica)

| Regla de negocio | Característica que la cubre |
|---|---|
| R-ORG-01 … R-ORG-05 | 1 — Estructura organizacional |
| R-POL-01 … R-POL-07 | 3 — Gestión de pólizas; 4 — Carga masiva |
| R-COB-01 … R-COB-10 | 6 — Cobranza masiva; 5 — Cobranza recibo por recibo (FIFO, Pagado Hasta) |
| R-PCA-01 … R-PCA-04 | 8 — PCA; 10 — Reportes (agente que computa) |
| R-COM-01 … R-COM-08 | 9 — Liquidación de comisiones |
| R-GLOB-01 … R-GLOB-06 | 12 — Reglas transversales |
| D-04 (asegurado) | 3 — Gestión de pólizas |
| D-05 (beneficiarios 100% al confirmar) | 3 — Gestión de pólizas |
| D-06 (estatus de pago declarativo) | 3 — Gestión de pólizas |
| Identidad por Id interno / nomenclatura de claves | 2 — Catálogos; 8 y 10 — quién computa |
| Productos con atributos y variantes | 2 — Catálogos; 4 — Carga masiva (mapeo) |
| §5.4–§5.5 (bitácora y marcas) | 7 — Bitácora de importación |
| §8 / Apéndice A (roles) | 11 — Roles, permisos y visibilidad |

---

*Documento base de comportamiento esperado para Grupo BCA Seguros. Refleja la visión funcional acordada con la Dirección; se actualiza conforme el negocio precise reglas pendientes (esquemas de comisión, formatos de aseguradoras futuras y catálogos completos de producto).*
