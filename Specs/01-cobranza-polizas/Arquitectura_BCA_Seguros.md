# Manual de Arquitectura — Módulo `BCA_Seguros`

**Cliente:** Grupo BCA (Holding de Promotorías de Seguros)
**Plataforma:** Odoo Community **versión 19**
**Autor:** Hábitat Digital — Equipo de consultoría
**Audiencia:** Desarrollador implementador
**Propósito:** Documento de referencia técnica para el desarrollo del módulo. Define el modelo de datos, las conexiones con módulos estándar de Odoo, las reglas de negocio críticas y la estructura de archivos del módulo.

> **Revisión arquitectónica — Mayo 2026:** Este documento incorpora correcciones críticas identificadas antes del inicio del desarrollo. Los cambios están marcados con `[CORRECCIÓN]`. Ver sección 13 para el resumen completo de cambios.

---

## 1. Visión general del módulo

`BCA_Seguros` es un módulo Odoo Community V19 que gestiona el ciclo de vida operativo de la promotoría de seguros: pólizas, recibos, cobranza, cálculo de Prima Computable (PCA) y reportes de productividad. Se apoya intensivamente en módulos estándar de Odoo y agrega solo los modelos propios del dominio asegurador que no calzan con objetos estándar.

### 1.1 Principios de diseño

1. **Reutilizar antes de crear.** Todo lo que Odoo ya hace (contactos, productos, multimoneda, ACL, mail.thread) se reutiliza.
2. **Modelos propios solo para conceptos del dominio asegurador.** Póliza, recibo, factor PCA, conducto, bitácora.
3. **Aseguradora como dimensión de primera clase.** Parsers, calculadores y catálogos son intercambiables por aseguradora desde el día 1.
4. **Inmutabilidad financiera.** Una vez pagado un recibo, su PCA y factor aplicado se congelan para siempre.
5. **Correctitud sobre escala.** El cuello de botella es integridad de datos, no throughput.

### 1.2 Módulos Odoo de los que depende

| Módulo Odoo | Para qué se usa | Carácter |
|---|---|---|
| `base` | `res.partner`, modelos fundamentales, ACL, grupos, record rules | Obligatorio |
| `mail` | `mail.thread` y `mail.activity.mixin` para auditoría y actividades | Obligatorio |
| `product` | `product.template` extendido para productos de seguro | Obligatorio |
| `hr_recruitment` | Captación de promotorías y reclutamiento de agentes | Obligatorio |
| `crm` | Gestión de prospectos de venta de pólizas por agente | Obligatorio |
| `web` | Vistas, dashboards | Obligatorio |

> **[CORRECCIÓN C5]** El módulo `contacts` **no existe** en Odoo Community v19 como módulo independiente. Fue eliminado. `res.partner` vive en `base`. La dependencia anterior causaba fallo de instalación en instancia limpia.

Declaración en `__manifest__.py`:

```python
'depends': [
    'base', 'mail', 'product',
    'hr_recruitment', 'crm', 'web',
],

# Hooks de inicialización para SQL views de reportes
'post_init_hook': 'post_init_hook_BCA_Seguros',
```

El hook `post_init_hook_BCA_Seguros` se define en el `__init__.py` raíz del módulo e invoca `init()` de todos los modelos de reporte (`_auto=False`) al instalar y al actualizar el módulo. Ver sección A1 de correcciones.

---

## 2. Modelo de datos

### 2.1 Diagrama lógico

```
res.partner (extendido)
│
├─ BCA Holding (raíz, bca_tipo = 'holding')
│   ├─ Promotoría A (bca_tipo = 'promotoria', parent_id = BCA)
│   │   ├─ Agente A1 (bca_tipo = 'agente', parent_id = Promotoría A)
│   │   ├─ Agente A2
│   │   └─ ...
│   └─ Promotoría B
│
├─ Aseguradora MetLife (bca_tipo = 'aseguradora')
├─ Aseguradora Qualitas
├─ Aseguradora Insurance
│
└─ Contratantes (bca_tipo = 'contratante')

res.partner.agente.aseguradora  ← [NUEVO] modelo puente con constraint SQL
└─ (agente_id, aseguradora_id, clave_agente, estado)
   UNIQUE(aseguradora_id, clave_agente)

product.template (extendido, bca_es_producto_seguro = True)
└─ Productos de seguro (FK a aseguradora)

bca.poliza ──┬──> res.partner (aseguradora, agente, contratante)
             ├──> product.template (producto)
             ├──> bca.recibo (1:N)
             └──> bca.poliza.cambio.agente (1:N) ← [NUEVO] historial de reasignaciones

bca.recibo ──┬──> bca.poliza
             ├──> bca.conducto
             └──> [PCA congelada al pago — inmutable via tracking]

bca.factor.pca ──> res.partner (aseguradora)   [hereda mail.thread]
bca.conducto ──> res.partner (aseguradora)
bca.bitacora.importacion ──> bca.bitacora.linea (1:N)

hr.applicant (pipelines BCA)
crm.lead (pipeline venta de pólizas)
```

### 2.2 Modelos extendidos (de Odoo estándar)

#### 2.2.1 `res.partner` (extensión)

**Archivo:** `models/res_partner.py`

| Campo nuevo | Tipo | Descripción |
|---|---|---|
| `bca_tipo` | Selection `index=True` | `holding`, `aseguradora`, `promotoria`, `agente`, `contratante` |
| `bca_estado_agente` | Selection **computed `store=True`** `index=True` | Rollup de carrera: `prospecto`, `clave_arranque`, `clave_definitiva`. Es el "mejor" estado alcanzado en cualquier aseguradora (Definitiva > Arranque > Prospecto; sin claves = Prospecto). **No editable a mano** — se deriva del modelo puente. Solo para filtros/listas/visual. **La PCA NO filtra por este campo** (ver corrección PCA). |
| `bca_codigo_aseguradora` | Char `index=True` | Código corto interno (METLIFE, QUALITAS, INSURANCE) |
| `bca_promotoria_id` | Many2one (computed, **sin store**) | Para agentes: retorna `parent_id` si es promotoría |
| `agente_aseguradora_ids` | One2many → `res.partner.agente.aseguradora` | Asociaciones del agente con aseguradoras y sus claves |

> **[CORRECCIÓN C3]** Los campos `bca_clave_agente` (Char) y `bca_aseguradoras_ids` (Many2many) fueron **eliminados** de `res.partner`. No es posible implementar un constraint SQL `UNIQUE(clave, aseguradora)` sobre una relación Many2many. Se reemplazan por el modelo puente `res.partner.agente.aseguradora` (sección 2.3.0) que sí soporta el constraint real.

> **[NOMENCLATURA DE AGENTES — DECISIÓN D-07]** El estado de carrera del agente tiene **tres niveles** (`prospecto` → `clave_arranque` → `clave_definitiva`) y es **por aseguradora**: vive en el modelo puente `res.partner.agente.aseguradora.estado` (fuente de verdad). En `res.partner`, `bca_estado_agente` es un **rollup computado `store=True`** del puente (no se edita a mano). El campo redundante `bca_fecha_licencia` se **eliminó** de `res.partner` (la fecha es por aseguradora: `res.partner.agente.aseguradora.fecha_licencia`). Reclutamiento (`hr_recruitment`) maneja todo el ciclo y alimenta el puente vía automated actions; el contacto solo refleja el rollup + un smart button al registro de reclutamiento. Ver §2.2.3 (integración Reclutamiento) y `Decisiones.md` D-07. **Solo `clave_definitiva` computa para PCA.**

> **[CORRECCIÓN A2]** Los campos `bca_tipo`, `bca_estado_agente` y `bca_codigo_aseguradora` deben declararse con `index=True`. `res.partner` es la tabla más consultada de Odoo; sin índices los filtros por tipo causan full table scan.

**Constraints en `res.partner`:**
- Si `bca_tipo = 'agente'`, `parent_id` debe ser un partner con `bca_tipo = 'promotoria'`. (Python `@api.constrains`)
- Si `bca_tipo = 'promotoria'`, `parent_id` debe ser el partner holding BCA. (Python `@api.constrains`)

**Categorías (`res.partner.category`):**
Se crean en `data/partner_categories.xml`: `Aseguradora`, `Promotoría BCA`, `Agente BCA`, `Contratante BCA`. Se asignan automáticamente vía `_compute` según `bca_tipo` para facilitar filtrado en vistas estándar.

---

#### 2.2.1b `res.partner.agente.aseguradora` — **[NUEVO]** Modelo puente Agente↔Aseguradora

**Archivo:** `models/res_partner_agente_aseg.py`

Este modelo reemplaza la antigua Many2many `bca_aseguradoras_ids` en `res.partner`. Permite constraint SQL real sobre la unicidad de la clave de agente por aseguradora, y soporta múltiples propiedades por relación (estado, fecha de alta, etc.).

| Campo | Tipo | Descripción |
|---|---|---|
| `agente_id` | Many2one (`res.partner`) | Agente. `ondelete='cascade'`. Domain: `bca_tipo='agente'` |
| `aseguradora_id` | Many2one (`res.partner`) | Aseguradora. `ondelete='restrict'`. Domain: `bca_tipo='aseguradora'` |
| `clave_agente` | Char | Clave exacta que usa la aseguradora para identificar al agente |
| `estado` | Selection (default `prospecto`) | **Fuente de verdad** del estado de carrera EN ESTA aseguradora: `prospecto`, `clave_arranque`, `clave_definitiva`. **Solo `clave_definitiva` computa para PCA.** Alimentado por Reclutamiento vía automated actions |
| `fecha_licencia` | Date | Fecha en que la clave pasó a definitiva |

**Constraints SQL:**
```python
_sql_constraints = [
    ('unique_clave_aseg', 'UNIQUE(aseguradora_id, clave_agente)',
     'La clave del agente debe ser única por aseguradora'),
    ('unique_agente_aseg', 'UNIQUE(agente_id, aseguradora_id)',
     'Un agente solo puede registrarse una vez por aseguradora'),
]
```

**ACL:** Este modelo requiere entrada en `ir.model.access.csv` para todos los grupos.

---

#### 2.2.2 `product.template` (extensión)

**Archivo:** `models/product_template.py`

| Campo nuevo | Tipo | Descripción |
|---|---|---|
| `bca_es_producto_seguro` | Boolean | Marca el producto como producto de seguro |
| `bca_aseguradora_id` | Many2one (`res.partner`) | Aseguradora emisora. Domain: `[('bca_tipo','=','aseguradora')]` |
| `bca_ramo` | Selection | `vida`, `gmm`, `autos`, `danos` |
| `bca_temporalidad_anios` | Integer | Solo Vida. Para excluir pólizas con temporalidad < 10 años |
| `bca_es_capitalizable` | Boolean | Solo Vida. Si es producto capitalizable (Universales, FlexiLife) |
| `bca_nombre_archivo_aseguradora` | Char | Nombre exacto como aparece en el CSV de la aseguradora (para mapeo) |

**Categorías de producto (`product.category`):**
Se crean en `data/product_categories.xml`: `Seguros / MetLife / Vida`, `Seguros / MetLife / GMM`, etc.

**Nota arquitectónica:** este modelo habilita la facturación futura de comisiones de BCA hacia las aseguradoras. En v1 los productos solo se usan como catálogo. La cuenta contable de ingresos por producto queda configurada para fase futura.

**Nota catálogo:** El catálogo de productos (nombres exactos, códigos, factores) es actualizable en tiempo de ejecución vía UI sin requerir cambios en la estructura de datos del módulo.

---

#### 2.2.3 `hr.applicant` (uso, sin extensión obligatoria en v1)

Se crean dos `hr.job` en `data/hr_jobs.xml`:
- `Captación de Promotoría`
- `Reclutamiento de Agente`

Cada uno con su pipeline (`hr.recruitment.stage` filtrado por `job_ids`).

**Reclutamiento es dueño del ciclo de carrera del agente (D-07).** El estado del agente se refleja en el contacto automáticamente, sin que nadie en el módulo de seguros lo actualice. Flujo (todo vía automated actions sobre `hr.applicant`):

| Momento (Reclutamiento) | Acción automatizada | Estado resultante |
|---|---|---|
| Alta del prospecto | Crear `res.partner` con `bca_tipo='agente'`, `parent_id`=`bca_promotoria_destino_id`. Aún sin puente. | `bca_estado_agente` (rollup) = **Prospecto** |
| Examen aprobado / la aseguradora asigna clave inicial | Crear registro puente `res.partner.agente.aseguradora` con `estado='clave_arranque'`, `clave_agente`, `aseguradora_id` | rollup → **Clave de Arranque** |
| La aseguradora asigna la clave definitiva (meses) | Actualizar el puente a `estado='clave_definitiva'` | rollup → **Clave Definitiva** → empieza a computar PCA |

- Si `hr.job` = Captación de Promotoría → crear `res.partner` con `bca_tipo='promotoria'` y `parent_id=BCA`.

**Campos a agregar a `hr.applicant`:** `bca_promotoria_destino_id` (ya existe), `bca_aseguradora_destino_id` (Many2one aseguradora) y `bca_clave_arranque` (Char) — necesarios para que la automated action cree el registro puente al aprobar el examen.

**En el contacto del agente:** smart button "Reclutamiento" que enlaza al `hr.applicant`. El detalle fino (asignación/aprobación de exámenes, etapas) vive en Reclutamiento, no se espeja en el contacto.

> **[ESTADO DE IMPLEMENTACIÓN]** Hoy `models/hr_applicant.py` solo crea el `res.partner` al cerrar "Contratado" (un único momento). El ciclo completo de tres estados + alimentación del puente + smart button es **trabajo pendiente** de esta etapa de integración con Reclutamiento. El rollup `bca_estado_agente` y el modelo puente ya soportan los tres estados.

**Archivo:** `models/hr_applicant.py` (extensión para los campos destino y los métodos de creación de partner / alimentación del puente).

---

#### 2.2.4 `crm.lead` (uso, con extensión mínima)

**Archivo:** `models/crm_lead.py`

| Campo nuevo | Tipo | Descripción |
|---|---|---|
| `bca_aseguradora_id` | Many2one (`res.partner`) | Aseguradora del producto cotizado |
| `bca_ramo` | Selection | `vida`, `gmm`, `autos`, `danos` |
| `bca_producto_id` | Many2one (`product.template`) | Producto cotizado. Domain: `[('bca_es_producto_seguro','=',True)]` |
| `bca_prima_estimada` | Monetary | Prima anual estimada |
| `bca_periodicidad` | Selection | `mensual`, `trimestral`, `semestral`, `anual` |
| `bca_poliza_generada_id` | Many2one (`bca.poliza`) | Si el lead se ganó y generó póliza |

**Botón en vista form del lead:** "Generar Póliza desde Lead" — solo visible si `stage_id` = ganado y `bca_poliza_generada_id` = False. Abre el formulario de creación de `bca.poliza` con los datos del lead precargados.

**`crm.team`:** uno por promotoría, creado vía automated action al alta de la promotoría. Cada agente queda asignado al team de su promotoría.

---

### 2.3 Modelos propios

#### 2.3.1 `bca.poliza`

**Archivo:** `models/poliza.py`
**Hereda:** `mail.thread`, `mail.activity.mixin`

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | Char | Número de póliza. **Único por aseguradora** (constraint SQL: `unique(name, aseguradora_id)`) |
| `aseguradora_id` | Many2one (`res.partner`) | Required. Domain: `[('bca_tipo','=','aseguradora')]` |
| `producto_id` | Many2one (`product.template`) | Required. Domain: `[('bca_es_producto_seguro','=',True)]` |
| `ramo` | Selection (related) | Related a `producto_id.bca_ramo` |
| `agente_id` | Many2one (`res.partner`) `tracking=True` | Required. Domain: `[('bca_tipo','=','agente')]` |
| `promotoria_id` | Many2one (`res.partner`, computed, **sin store**) | `agente_id.parent_id`. Derivado en tiempo real. |
| `contratante_id` | Many2one (`res.partner`) | Required. Domain: `[('bca_tipo','=','contratante')]` |
| `poliza_origen_id` | Many2one (`bca.poliza`) | Para renovaciones/conversiones |
| `currency_id` | Many2one (`res.currency`) | Required. MXN o USD |
| `prima_anual` | Monetary | Prima total anual |
| `prima_fraccionada` | Monetary | Prima por recibo |
| `recargo_fraccionamiento` | Monetary | |
| `suma_asegurada` | Monetary | |
| `periodicidad` | Selection | `mensual`, `trimestral`, `semestral`, `anual` |
| `fecha_inicio` | Date | Required |
| `fecha_fin` | Date | Required |
| `pagado_hasta` | Date `readonly=True` `tracking=True` | Computed con `store=True`, depende de `recibo_ids.estado` y `recibo_ids.fecha_hasta`. |
| `estado` | Selection `tracking=True` | `borrador`, `activa`, `vencida`, `cancelada` |
| `deducible` | Monetary | Solo GMM |
| `coaseguro` | Float | Solo GMM (porcentaje) |
| `nivel_hospitalario` | Char | Solo GMM |
| `tipo_cobertura` | Selection | Solo Vida: `estandar`, `accidentes`, `invalidez` |
| `temporalidad_anios` | Integer | Solo Vida |
| `es_aportacion_adicional` | Boolean | Solo Vida |
| `recibo_ids` | One2many (`bca.recibo`) | Recibos generados |
| `cambio_agente_ids` | One2many (`bca.poliza.cambio.agente`) | **[NUEVO]** Historial de reasignaciones de agente |

> **[CORRECCIÓN C2]** `promotoria_id` en póliza **no debe usar `store=True`** para evitar stale data, PERO los recibos sí deben almacenar `agente_id` y `promotoria_id` como foto inmutable. Los reportes de PCA apuntarán a los campos del recibo para garantizar la inmutabilidad histórica.

**Métodos clave:**
- `action_confirmar()`: Pasa de `borrador` → `activa` y dispara `_generar_plan_pagos()`.
- `_generar_plan_pagos()`: Genera los N recibos según periodicidad. **No se ejecuta si ya hay recibos pagados** (R-POL-05).
- `action_cancelar()`: Pasa a `cancelada`. No borra recibos.
- `_compute_pagado_hasta()`: **[CORRECCIÓN C1]** Método compute (con `store=True`, `depends=['recibo_ids.estado', 'recibo_ids.fecha_hasta']`) que recalcula `pagado_hasta` basado en el recibo pagado con `fecha_hasta` máxima. El ORM lo invoca automáticamente tanto al pagar (avanza) como al cancelar (retrocede). Ver Plan de Desarrollo §2.4.4.

> **[CORRECCIÓN C1]** Se **elimina** el método manual de bypass en el `write()` y se cambia `pagado_hasta` a un campo Computed almacenado (`store=True`). Esto permite que el ORM de Odoo lo actualice de forma atómica y segura cuando cambian los recibos, evitando el problema del bypass por contexto.

**Reglas de negocio implementadas (referencia al doc original):**
- R-POL-01 a R-POL-06.
- Campo `pagado_hasta` computed stored — inmutable por UI y gestionado automáticamente por el ORM. Todo cambio queda registrado en chatter (`tracking=True`).

---

#### 2.3.2 `bca.recibo`

**Archivo:** `models/recibo.py`
**Hereda:** `mail.thread`

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | Char | Secuencia `bca.recibo` |
| `poliza_id` | Many2one (`bca.poliza`) | Required, ondelete='restrict' |
| `agente_id` | Many2one (`res.partner`) | **[NUEVO]** Foto inmutable del agente que cobró. Domain: agente |
| `promotoria_id` | Many2one (`res.partner`) | **[NUEVO]** Foto inmutable de la promotoría en el momento del pago |
| `numero_recibo` | Integer | Número secuencial dentro de la póliza (1, 2, 3...) |
| `fecha_desde` | Date | Inicio de cobertura del recibo |
| `fecha_hasta` | Date | Fin de cobertura del recibo |
| `monto_modal` | Monetary | Prima modal calculada |
| `recargo` | Monetary | |
| `prima_neta` | Monetary | Base para PCA |
| `prima_total` | Monetary | Lo que paga el cliente |
| `currency_id` | Many2one (related a póliza) | |
| `estado` | Selection | `pendiente`, `pagado`, `cancelado` |
| `fecha_pago` | Date | Set al pagar |
| `conducto_id` | Many2one (`bca.conducto`) | Set al pagar, opcional |
| `folio_endoso` | Char | Solo GMM. Dato informativo |
| `pca_aplicada` | Monetary `readonly=True` `tracking=True` | **Congelada al pago. Inmutable una vez pagado.** |
| `factor_aplicado` | Float `readonly=True` `tracking=True` | **Congelado al pago.** |
| `motivo_exclusion_pca` | Char | Si PCA = 0, por qué |
| `bitacora_linea_id` | Many2one (`bca.bitacora.linea`) | Línea de bitácora que generó el pago |

**Métodos clave:**
- `action_registrar_pago(vals)`: Recibe datos del CSV. Valida FIFO (debe ser el recibo pendiente más antiguo de la póliza). Calcula PCA, congela factor, llama a `poliza_id._actualizar_pagado_hasta_desde_recibo()`. Llamado por el parser de cobranza.
- `action_cancelar_pago()`: Solo Director General **y Director Comercial**. Pone `pca_aplicada=0`, recalcula `pagado_hasta` de la póliza (puede retroceder), registra en bitácora. Requiere chequeo explícito de grupo además de ACL.
- `_calcular_pca()`: Llama al calculador de PCA correspondiente a la aseguradora.
- `write()`: Bloquea escritura de `pca_aplicada` y `factor_aplicado` si `estado='pagado'`. Permite el bypass solo si se hace desde `action_cancelar_pago()` y se es superusuario o se fuerza contextualmente por el propio módulo, según estándares OCA.

> **[CORRECCIÓN C1]** El bypass de validación en `write()` para `pca_aplicada` solo se debe hacer mediante validación de `self.env.su` o por cambio temporal de estado a cancelado antes de modificar, evitando bloqueos estructurales que impidan cancelar el recibo desde el método autorizado.

**Constraint SQL:** `unique(poliza_id, numero_recibo)`.

---

#### 2.3.3 `bca.factor.pca`

**Archivo:** `models/factor_pca.py`
**Hereda:** `mail.thread` **[CORRECCIÓN M2]**

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | Char | Descripción legible |
| `aseguradora_id` | Many2one (`res.partner`) | Required. Domain aseguradoras |
| `ramo` | Selection | `vida`, `gmm`, etc. |
| `producto_ids` | Many2many (`product.template`) | Productos a los que aplica (Vida) |
| `currency_id` | Many2one | MXN, USD o nulo (aplica a cualquiera) |
| `coaseguro_min` | Float | Solo GMM |
| `coaseguro_max` | Float | Solo GMM |
| `deducible_min` | Monetary | Solo GMM |
| `factor` | Float `tracking=True` | El multiplicador (0.0 a 1.2) |
| `vigencia_desde` | Date `tracking=True` | |
| `vigencia_hasta` | Date `tracking=True` | Nulable (vigente indefinidamente) |
| `activo` | Boolean `tracking=True` | |

> **[CORRECCIÓN M2]** Este modelo hereda `mail.thread` y los campos `factor`, `vigencia_desde`, `vigencia_hasta`, `activo` llevan `tracking=True`. Si el Director cambia un factor, el chatter registra quién, cuándo y de qué valor a cuál. Esto permite auditar qué recibos se congelaron con qué valor de factor, sin necesidad de una tabla histórica separada.

**Editable solo por Director General y Director Comercial** (groups `BCA_Seguros.group_bca_director` y `BCA_Seguros.group_bca_director_comercial`).

Data inicial: `data/factores_metlife_2026.xml` con los 17 registros (14 Vida + 3 GMM).

---

#### 2.3.4 `bca.conducto`

**Archivo:** `models/conducto.py`

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | Char | Nombre visible |
| `codigo_archivo` | Char | Código exacto del CSV. **Clave de mapeo automático** |
| `aseguradora_id` | Many2one (`res.partner`) | A qué aseguradora pertenece |
| `activo` | Boolean | |

**Constraint:** `unique(codigo_archivo, aseguradora_id)`.

Data inicial: `data/conductos_metlife.xml` con los 7 conductos conocidos.

---

#### 2.3.4b `bca.poliza.cambio.agente` — **[NUEVO]** Historial de reasignaciones

**Archivo:** `models/poliza_cambio_agente.py`

Requerido por **R-ORG-02** ("conservar historial" de cambios de promotoría del agente). Las pólizas históricas siguen acreditando a la promotoría original para liquidación; las nuevas a la nueva.

| Campo | Tipo | Descripción |
|---|---|---|
| `poliza_id` | Many2one (`bca.poliza`) | `ondelete='cascade'` |
| `agente_anterior_id` | Many2one (`res.partner`) | Agente previo al cambio |
| `promotoria_anterior_id` | Many2one (`res.partner`) | Promotoría anterior (snapshot) |
| `agente_nuevo_id` | Many2one (`res.partner`) | Nuevo agente asignado |
| `promotoria_nueva_id` | Many2one (`res.partner`) | Nueva promotoría (snapshot) |
| `fecha_cambio` | Date | Fecha efectiva del cambio |
| `motivo` | Char | Razón del cambio |
| `usuario_id` | Many2one (`res.users`) | Quién autorizó |

**Regla:** El cambio de `agente_id` en una póliza solo puede hacerse vía método `poliza.cambiar_agente(nuevo_agente, motivo)`, que registra automáticamente en esta tabla. Los campos del modelo son todos `readonly=True`.

---

#### 2.3.5 `bca.bitacora.importacion` y `bca.bitacora.linea`

**Archivo:** `models/bitacora.py`
**Hereda:** `mail.thread`

**`bca.bitacora.importacion`:**

| Campo | Tipo | Descripción |
|---|---|---|
| `name` | Char | Secuencia |
| `usuario_id` | Many2one (`res.users`) | Quién ejecutó |
| `fecha_ejecucion` | Datetime | |
| `aseguradora_id` | Many2one (`res.partner`) | |
| `ramo` | Selection | `vida`, `gmm` |
| `nombre_archivo` | Char | |
| `archivo_adjunto` | Binary | Archivo original guardado |
| `total_filas` | Integer | |
| `recibos_aplicados` | Integer | |
| `anulaciones_ignoradas` | Integer | |
| `polizas_no_encontradas` | Integer | |
| `errores_procesamiento` | Integer | |
| `pca_total_sesion` | Monetary | |
| `linea_ids` | One2many | |

**`bca.bitacora.linea`:**

| Campo | Tipo | Descripción |
|---|---|---|
| `bitacora_id` | Many2one | |
| `numero_fila` | Integer | Fila del CSV |
| `marca` | Selection | `aplicado`, `anulado`, `no_encontrada`, `sin_recibo`, `advertencia`, `error`, `info` |
| `mensaje` | Text | |
| `numero_poliza_raw` | Char | |
| `recibo_id` | Many2one (`bca.recibo`) | Si se aplicó |

**Inmutabilidad:**
- Métodos `write()` y `unlink()` overrideados para lanzar `UserError` si el usuario no es superusuario (`not self.env.su`). Esto protege la información pero permite tareas de sistema (cron de purga).
- Solo el `create()` desde el wizard de cobranza la genera.

---

## 3. Wizards (procesos transitorios)

### 3.1 Wizard de carga masiva de portafolio

**Archivo:** `wizards/carga_portafolio.py`
**Modelo:** `bca.wizard.carga.portafolio` (TransientModel)

| Campo | Tipo |
|---|---|
| `archivo` | Binary (Excel .xlsx) |
| `nombre_archivo` | Char |
| `aseguradora_id` | Many2one (`res.partner`) |
| `modo` | Selection: `crear_actualizar`, `solo_crear` |

**Flujo (dos fases obligatorias):**
1. **Fase VALIDAR** — Leer y validar el archivo sin tocar la base de datos. Verificar extensión, hojas requeridas (`VIDA`, `GMM`, `AUTOS`), columnas, formatos de fecha y moneda. Si hay errores estructurales, mostrar reporte y detener.
2. **Fase GRABAR** — Solo si la validación fue exitosa. Por cada póliza:
   - Aislar en `savepoint` independiente.
   - Crear o actualizar `bca.poliza`. El campo `pagado_hasta` se recalcula automáticamente (computed `store=True`).
   - Generar plan de pagos pendientes hacia adelante.
3. Generar reporte: pólizas creadas, actualizadas, rechazadas con razón.
4. Retornar action que muestra el reporte en vista.

> **[CORRECCIÓN M1]** Separar validación de grabado ("validar antes de grabar") evita importaciones parciales difíciles de depurar. El operador puede revisar el preview antes de confirmar.

**Librería:** `openpyxl` (ya viene con Odoo).
**Performance:** Búsqueda de póliza por número usa índice (`name` debe tener `index=True`). Usar `search([...], limit=1)` en lugar de `search([...])`. Medir tiempo con `_logger.info()`. Límite recomendado de worker: `limit_time_real = 600` en `odoo.conf`.

---

### 3.2 Wizard de cobranza diaria

**Archivo:** `wizards/cobranza_diaria.py`
**Modelo:** `bca.wizard.cobranza.diaria` (TransientModel)

| Campo | Tipo |
|---|---|
| `archivo` | Binary (CSV) |
| `nombre_archivo` | Char |
| `aseguradora_id` | Many2one |
| `ramo` | Selection |

**Flujo:**
1. Validar archivo (extensión, encoding Latin-1). Obtener parser con `get_parser(aseguradora_codigo, ramo)`.
2. Llamar `parser.validar_estructura(df)` **antes de crear bitácora ni procesar ninguna fila**. Si falta una columna crítica, detener con `UserError` sin tocar datos. (R-COB-09)
3. Crear registro `bca.bitacora.importacion` (cabecera).
4. Por cada fila del CSV:
   ```python
   try:
       with self.env.cr.savepoint():
           # El context original debe conservarse para idioma (lang) y traducciones de error
           resultado = parser.procesar_fila(self.env, fila)
           self._log_linea(bitacora, num_fila, 'aplicado', fila)
   except (UserError, ValidationError) as e:
       self._log_linea(bitacora, num_fila, 'error', fila, str(e))
   except Exception as e:
       _logger.exception("Error técnico fila %s", num_fila)
       self._log_linea(bitacora, num_fila, 'error', fila, str(e)[:200])
   ```
5. Cerrar bitácora con totales.
6. Retornar action que muestra la bitácora generada.

> **[CORRECCIÓN C4]** El savepoint de PostgreSQL hace rollback en BD y Odoo se encarga de invalidar la caché del ORM automáticamente al salir del bloque por error en versiones >= 14. NO se debe usar `self.env(context={})` porque destruye variables vitales del entorno como el idioma (`lang`) y la zona horaria (`tz`), provocando mensajes de error sin traducir y fechas incorrectas.

---

## 4. Parsers de cobranza (patrón Strategy)

**Carpeta:** `parsers/`

### 4.1 Interfaz base

**Archivo:** `parsers/base.py`

```python
class ParserBase:
    """Interfaz común para todos los parsers de cobranza."""

    aseguradora_codigo = None  # 'METLIFE', 'QUALITAS', 'INSURANCE'
    ramo = None                # 'vida' o 'gmm'
    columnas_requeridas = []   # OBLIGATORIO definir en cada subclase

    def __init__(self, env, bitacora):
        self.env = env
        self.bitacora = bitacora

    def validar_estructura(self, df):
        """
        Valida columnas requeridas ANTES de procesar cualquier fila.
        Lanza UserError con lista de columnas faltantes si hay error estructural.
        DEBE llamarse desde el wizard antes del loop de filas.
        """
        faltantes = set(self.columnas_requeridas) - set(df.columns)
        if faltantes:
            raise UserError(
                f"Archivo inválido para {self.aseguradora_codigo}/{self.ramo}. "
                f"Columnas faltantes: {sorted(faltantes)}"
            )

    def filtrar_filas(self, df):
        """Aplica filtros pre-procesamiento (ej. anulaciones GMM)."""

    def procesar_fila(self, env, fila):
        """
        Procesa una fila: busca póliza, aplica pago FIFO, registra bitácora.
        Recibe `env` como parámetro explícito para inyección de dependencias.
        """

    def normalizar_monto(self, valor):
        """Coma como miles, punto como decimal → float."""

    def normalizar_fecha(self, valor):
        """DD/MM/YYYY → date."""
```

> **[CORRECCIÓN A5]** `columnas_requeridas` es una lista vacía en la base pero **obligatoria** en cada implementación concreta. El método `validar_estructura()` tiene implementación completa en la base; las subclases no deben sobreescribirlo. La validación se llama en el wizard **antes** del loop de filas (fail-fast).

> **[CORRECCIÓN C4]** `procesar_fila()` recibe `env` como parámetro. El caller (wizard) pasa `self.env` (manteniendo el contexto intacto para respetar `lang` y `tz`).

### 4.2 Implementaciones v1

- `parsers/metlife_lsp.py` — `ParserMetLifeVida` (LSP). `columnas_requeridas` completo con los 13 campos del archivo MetLife Vida.
- `parsers/metlife_gcaye.py` — `ParserMetLifeGMM` (GCAYE). `columnas_requeridas` completo con los campos del archivo GMM.
- `parsers/qualitas.py` — `ParserQualitas` (autos, v1.0). `columnas_requeridas` pendiente de especificación de Qualitas.

> **Nota:** Los nombres exactos de las columnas del CSV deben verificarse contra los archivos reales de cada aseguradora antes de codificar. Pendiente documentar en `parsers/specs/` o en este documento como anexo.

### 4.3 Placeholders para v2

- `parsers/insurance.py` — `ParserInsurance` (a definir).

### 4.4 Registry de parsers

**Archivo:** `parsers/__init__.py`

> **[CORRECCIÓN A4]** El dict estático `PARSER_REGISTRY` se reemplaza por la función `get_parser()` con mensaje de error descriptivo. Esto facilita agregar parsers nuevos sin romper el contrato y da mensajes de error útiles al operador.

```python
from .metlife_lsp import ParserMetLifeVida
from .metlife_gcaye import ParserMetLifeGMM
from .qualitas import ParserQualitas

_PARSER_REGISTRY = {
    ('METLIFE', 'vida'): ParserMetLifeVida,
    ('METLIFE', 'gmm'): ParserMetLifeGMM,
    ('QUALITAS', 'autos'): ParserQualitas,
}

def get_parser(aseguradora_codigo, ramo):
    """Obtener clase de parser para la combinación aseguradora+ramo."""
    key = (aseguradora_codigo.upper(), ramo)
    cls = _PARSER_REGISTRY.get(key)
    if not cls:
        disponibles = ', '.join(f"{a}/{r}" for a, r in _PARSER_REGISTRY)
        raise UserError(
            f"No existe parser para aseguradora='{aseguradora_codigo}' ramo='{ramo}'. "
            f"Parsers disponibles: {disponibles}"
        )
    return cls
```

**Para agregar un nuevo parser** (ej. Atlas Vida): crear `parsers/atlas_vida.py` con `ParserAtlasVida` que herede `ParserBase`, definir `columnas_requeridas`, y agregar la entrada en `_PARSER_REGISTRY`. No requiere modificar ningún otro archivo.

---

## 5. Calculadores de PCA (patrón Strategy)

**Carpeta:** `calculadores_pca/`

### 5.1 Interfaz base

**Archivo:** `calculadores_pca/base.py`

```python
class CalculadorPCABase:
    """Interfaz común para todos los calculadores de PCA."""

    aseguradora_codigo = None

    def __init__(self, env):
        self.env = env

    def calcular(self, recibo):
        """
        Retorna tupla (pca, factor_aplicado, motivo_exclusion).
        Evalúa exclusiones antes de aplicar factor.
        """
```

### 5.2 Implementación MetLife — IMPLEMENTADO (Etapa 7)

**Archivo:** `calculadores_pca/metlife.py`

Lógica (`calcular(recibo) → (pca, factor_aplicado, motivo_exclusion)`, **pca en MXN**):
1. Resolver `ramo` de la póliza (solo `vida`/`gmm`; otro → `(0,0,'Ramo no soportado…')`).
2. Evaluar exclusiones **antes del factor** (D-08). Si excluido → `(0, 0, motivo)`:
   - Vida: `es_aportacion_adicional`; `0 < temporalidad_anios < 10`.
   - GMM: `coaseguro ≤ 5%` (normalizado a puntos porcentuales — ver nota de unidades).
   - *(La exclusión "coberturas individuales de accidentes/invalidez" queda fuera de
     alcance: no hay campo estructurado. Ver D-08.)*
3. Buscar factor vigente en `bca.factor.pca` (aseguradora, ramo, `activo`, vigencia ⊇ `fecha_pago`).
   - Vida: además por `producto_ids` y `currency_id == poliza.currency_id`.
   - GMM: por umbrales `coaseguro_min`/`deducible_min`, tomando la regla más específica
     (mayor `deducible_min`, luego mayor `coaseguro_min`).
   - Sin factor → `(0, 0, 'Sin factor PCA vigente')` (no aborta la cobranza).
4. `pca_ccy = prima_neta × factor`; convertir a MXN vía `res.currency._convert()` a `fecha_pago`.
   Retornar `(pca_mxn, factor, '')`.

> **[RESOLUCIÓN M3 / D-08]** La PCA se expresa **siempre en MXN**. El factor se
> selecciona por la **moneda de la póliza** (conserva el ajuste USD, ej. Vida 80%) y el
> monto resultante se convierte a MXN. El recibo guarda la PCA en `pca_currency_id`
> (= MXN, default), no en `currency_id` (moneda de la póliza, que puede ser USD).
>
> **Nota de unidades (deuda de datos, ver `Bugs.md`):** `bca.poliza.coaseguro` es fracción
> (`0.10`=10%) y `bca.factor.pca.coaseguro_min` del seed es puntos porcentuales (`10.0`).
> El calculador normaliza (`coaseguro × 100`) antes de comparar.

### 5.3 Registry

**Archivo:** `calculadores_pca/__init__.py`

```python
CALCULADOR_REGISTRY = {
    'METLIFE': CalculadorPCAMetLife,
    'QUALITAS': CalculadorPCAQualitas,
}
```

---

## 6. Reportes (SICs)

**Carpeta:** `reports/`

### 6.1 SIC 1 — PCA por Agente

**Archivo:** `reports/pca_por_agente.py`
**Modelo:** `bca.reporte.pca.agente` (Model con SQL view)

```python
class ReportePCAAgente(models.Model):
    _name = 'bca.reporte.pca.agente'
    _auto = False  # SQL view
    _description = 'Reporte de PCA por Agente'

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW bca_reporte_pca_agente AS (
                SELECT
                    r.id AS id,
                    r.agente_id AS agente_id,       -- Obtenido del recibo (inmutable)
                    r.promotoria_id AS promotoria_id, -- Obtenido del recibo (inmutable)
                    p.aseguradora_id AS aseguradora_id,
                    p.producto_id AS producto_id,
                    p.ramo AS ramo,
                    r.currency_id AS currency_id,
                    r.fecha_pago AS fecha_pago,
                    r.pca_aplicada AS pca,
                    r.factor_aplicado AS factor
                FROM bca_recibo r
                JOIN bca_poliza p ON r.poliza_id = p.id
                -- Solo computa el agente con CLAVE DEFINITIVA *en esa aseguradora*.
                -- El estado es por aseguradora (modelo puente), NO el rollup del
                -- partner: un agente puede ser Definitiva en MetLife y Arranque en
                -- Qualitas. Filtrar por res_partner.bca_estado_agente sería un bug.
                JOIN res_partner_agente_aseguradora aa
                     ON aa.agente_id = r.agente_id
                    AND aa.aseguradora_id = p.aseguradora_id
                WHERE r.estado = 'pagado'
                  AND aa.estado = 'clave_definitiva'
            )
        """)
```

**Vistas:** pivot (default), gráfica, lista.
**Filtros:** agente, promotoría, aseguradora, ramo, rango fechas, moneda.
**Menú:** `BCA → Reportes → Productividad → Por Agente`.

---

### 6.2 SIC 2 — PCA por Promotoría

**Archivo:** `reports/pca_por_promotoria.py`
**Modelo:** `bca.reporte.pca.promotoria` (SQL view agregada)

Mismo patrón que SIC 1, agregando `GROUP BY promotoria_id, aseguradora_id, ramo`.

**Vistas:** pivot por promotoría con drill-down a agentes.
**Menú:** `BCA → Reportes → Productividad → Por Promotoría`.

---

### 6.3 SIC 3 — PCA Consolidado BCA

**Archivo:** `reports/pca_consolidado.py`
**Modelo:** `bca.reporte.pca.consolidado`

Vista total holding. Drill-down: promotoría → agente → recibo.
**Menú:** `BCA → Reportes → Consolidado BCA`.
**Visibilidad:** solo Director General y Líder.

---

### 6.4 SIC 4 — Estado de cartera

**Archivo:** `reports/estado_cartera.py`
**Modelo:** `bca.reporte.estado.cartera`

Por póliza: `vigente` / `en_riesgo` (pagado_hasta < hoy + 30d) / `caida` (pagado_hasta < hoy).
Filtrable por agente, promotoría, aseguradora.

---

## 7. Seguridad (ACL y Record Rules)

**Archivos:** `security/groups.xml`, `security/record_rules.xml`, `security/ir.model.access.csv`

### 7.1 Grupos

| Grupo XML ID | Nombre | Equivale a rol |
|---|---|---|
| `BCA_Seguros.group_bca_agente` | Agente | Agente vendedor (usuario interno de Odoo) |
| `BCA_Seguros.group_bca_operador` | Operador de Datos | Personal administrativo BCA |
| `BCA_Seguros.group_bca_lider` | Líder | Dirección operativa BCA |
| `BCA_Seguros.group_bca_director_comercial` | Director Comercial | **[NUEVO]** Dirección comercial |
| `BCA_Seguros.group_bca_director` | Director General | CEO / Dueño de BCA |

Herencia: Director ⊃ Director Comercial ⊃ Líder ⊃ Operador. Agente es independiente (no hereda).

> **[CORRECCIÓN M5]** Se agrega `group_bca_director_comercial`. El documento de Lógica de Negocio (Sección 8) define al Director Comercial con permisos equivalentes al Director General en cancelaciones de recibos, edición de factores y esquemas de comisión, **excepto** gestión de usuarios y promotorías (eso es exclusivo del Director General).

### 7.2 ACL por modelo (resumen)

| Modelo | Agente | Operador | Líder | Dir. Comercial | Director |
|---|---|---|---|---|---|
| `bca.poliza` | R (solo propias) | RWC | RWC | RWCD | RWCD |
| `bca.recibo` | R (solo propias) | RW | RW | RWCD | RWCD |
| `bca.factor.pca` | — | R | R | RWCD | RWCD |
| `bca.conducto` | — | R | R | RWC | RWCD |
| `bca.bitacora.importacion` | — | — | R | R | R |
| `bca.bitacora.linea` | — | — | R | R | R |
| `res.partner.agente.aseguradora` | R (propio) | RWC | RWC | RWC | RWCD |
| `bca.poliza.cambio.agente` | — | R | R | R | R |

### 7.3 Record rules clave

**`bca.poliza`:**
- Agente (usuario interno): `[('agente_id.user_ids', 'in', [user.id])]`
- Operador: `[(1, '=', 1)]` (acceso global)
- Líder: `[(1, '=', 1)]`
- Director Comercial: `[(1, '=', 1)]`
- Director: `[(1, '=', 1)]`

**`bca.recibo`:**
- Agente (usuario interno): `[('poliza_id.agente_id.user_ids', 'in', [user.id])]`
- Operador / Líder / Dir. Comercial / Director: `[(1, '=', 1)]`

> **[CORRECCIÓN A3]** Las record rules para grupos distintos al Agente Portal deben declararse **explícitamente** con dominio `[(1,'=',1)]`. Sin declaración explícita, Odoo puede combinar rules de grupos heredados de forma inesperada.

**Reporte por Promotoría** (activado desde v1.0):
- Gerente de Promotoría (rol futuro): `[('agente_id.parent_id.user_ids', 'in', [user.id])]`

### 7.4 Bloqueos en código (no solo ACL)

- `bca.poliza.pagado_hasta`: Campo computed (`store=True`). No editable en UI. **[CORRECCIÓN C1]**
- `bca.recibo.pca_aplicada` y `factor_aplicado`: `readonly=True` + bloqueo en `write()` si `estado='pagado'`. Con bypass autorizado para administradores (`env.su`) o estado intermedio para cancelación. **[CORRECCIÓN C1]**
- `bca.recibo.action_cancelar_pago()`: chequeo explícito de `group_bca_director` **o** `group_bca_director_comercial` + ACL. **[CORRECCIÓN M5]**
- `bca.bitacora.*`: `write()` y `unlink()` lanzan `UserError` si `not self.env.su`. Protección de aplicación con escotilla para sistema.

---

## 8. Usuarios y acceso del agente

**Decisión de diseño (Mayo 2026) — supercede la versión anterior de este documento:**

Los agentes son **usuarios internos de Odoo** (`share=False`). No son usuarios portal.

- Los agentes inician sesión en el **backend** de Odoo como cualquier usuario interno.
- Dentro de `BCA_Seguros`, las record rules (§7.3) los restringen a ver únicamente sus propias pólizas y recibos.
- Tienen acceso a otros módulos de Odoo (CRM, calendario, etc.) según los grupos adicionales que el Director General les asigne.
- **No existe portal de agente** (`/my/polizas`). El módulo `portal` **no es dependencia** de `BCA_Seguros`.
- El grupo es `BCA_Seguros.group_bca_agente` (no `group_bca_agente_portal`).
- No se crean `controllers/portal.py` ni `views/portal_templates.xml`.

---

## 9. Estructura del módulo (árbol de archivos)

```
BCA_Seguros/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── res_partner.py                  # + index=True; sin bca_clave_agente ni Many2many
│   ├── res_partner_agente_aseg.py      # [NUEVO] modelo puente con constraint SQL
│   ├── product_template.py
│   ├── hr_applicant.py
│   ├── crm_lead.py
│   ├── poliza.py                       # promotoria_id sin store; método _actualizar_pagado_hasta
│   ├── poliza_cambio_agente.py         # [NUEVO] historial de reasignaciones
│   ├── recibo.py                       # tracking en pca_aplicada y factor_aplicado
│   ├── factor_pca.py                   # + mail.thread, tracking en factor y vigencias
│   ├── conducto.py
│   └── bitacora.py
├── wizards/
│   ├── __init__.py
│   ├── carga_portafolio.py             # flujo validar → grabar; savepoint correcto
│   └── cobranza_diaria.py             # validar_estructura antes del loop; sin destruir context
├── parsers/
│   ├── __init__.py                     # get_parser() con error descriptivo
│   ├── base.py                         # validar_estructura() implementado; procesar_fila(env, fila)
│   ├── metlife_lsp.py                  # columnas_requeridas completo
│   └── metlife_gcaye.py                # columnas_requeridas completo
├── calculadores_pca/
│   ├── __init__.py
│   ├── base.py
│   └── metlife.py                      # manejo de multimoneda via res.currency
├── reports/
│   ├── __init__.py
│   ├── pca_por_agente.py               # JOIN directo a parent_id (no promotoria_id stored)
│   ├── pca_por_promotoria.py
│   ├── pca_consolidado.py
│   └── estado_cartera.py
├── migrations/
│   └── 1.0.0/                          # [NUEVO] scripts de post-migración
│       └── post_migrate.py             # recrear SQL views + crear índices parciales
├── security/
│   ├── groups.xml                      # + group_bca_director_comercial
│   ├── record_rules.xml               # rules explícitas para todos los grupos
│   └── ir.model.access.csv            # + res.partner.agente.aseguradora y poliza.cambio.agente
├── data/
│   ├── partner_categories.xml
│   ├── product_categories.xml
│   ├── hr_jobs.xml
│   ├── aseguradoras_iniciales.xml
│   ├── factores_metlife_2026.xml
│   ├── conductos_metlife.xml
│   └── sequences.xml
├── views/
│   ├── menu.xml
│   ├── res_partner_views.xml
│   ├── product_template_views.xml
│   ├── crm_lead_views.xml
│   ├── poliza_views.xml
│   ├── recibo_views.xml
│   ├── factor_pca_views.xml
│   ├── conducto_views.xml
│   ├── bitacora_views.xml
│   ├── reportes_views.xml
│   ├── wizard_carga_portafolio_views.xml
│   └── wizard_cobranza_diaria_views.xml
├── static/
│   └── description/
│       └── icon.png
└── tests/
    ├── __init__.py
    ├── test_poliza.py                   # R-POL-03, R-POL-05
    ├── test_cobranza_fifo.py           # R-COB-03, R-COB-08
    ├── test_pca_metlife.py             # R-PCA-01 (congelamiento)
    ├── test_inmutabilidad.py           # bitácora, pagado_hasta
    └── test_record_rules.py           # agente portal, director comercial
```

---

## 10. Reglas de oro para el desarrollador

1. **Nunca editar `pagado_hasta` directamente.** Es un campo Computed gestionado por el ORM. Cualquier intento de escritura directa será ignorado o lanzará un error.
2. **Nunca recalcular PCA de un recibo pagado.** El factor se busca al momento del pago y se congela. `pca_aplicada` y `factor_aplicado` son de solo lectura una vez que `estado='pagado'`.
3. **Toda fila del CSV se procesa en savepoint independiente.** Usar `with self.env.cr.savepoint()`. El context debe mantenerse para que no se pierdan `lang` ni `tz`. Error de una fila no detiene la corrida.
4. **Toda modificación a campos críticos pasa por `mail.thread`.** Los campos marcados con `tracking=True` quedan auditados automáticamente en chatter. Verificar que `pagado_hasta`, `pca_aplicada`, `factor_aplicado`, `estado`, `factor` estén en tracking.
5. **No incrustar nombres de productos o factores en código.** Todo va a catálogo.
6. **El encoding Latin-1 se detecta y maneja en el parser.** Nunca pedir al usuario que convierta.
7. **Cualquier nueva aseguradora se agrega creando parser + calculador + cargando factores.** No tocar modelos ni el resto del registry.
8. **Validar estructura del CSV antes del loop de filas.** `parser.validar_estructura(df)` se llama primero. Si falla, detener sin crear bitácora ni procesar nada.
9. **Limitar bypass de contexto.** Usarlo solo cuando sea estrictamente necesario para operaciones internas del sistema donde el ORM lo exija (ej. override restrictivo), o validar con `self.env.su`.
10. **`promotoria_id` en póliza es siempre computed, nunca stored.** Los SQL views hacen el JOIN a `parent_id` directamente. No almacenar para evitar stale data al cambiar agente de promotoría.

---

## 11. Decisiones resueltas con cliente

### 11.1 Decisiones ya resueltas

| # | Decisión | Resolución |
|---|---|---|
| 1 | Versión exacta de Odoo | **Odoo Community V19** |
| 2 | Cantidad de promotorías y proyección 12m | **6 promotorias hoy; proyección 12 en 12 meses** |
| 3 | Tabla GMM Q1 2026 | **Cambios aceptados; vigencia temporal soportada via `vigencia_desde/hasta`** |
| 4 | Campos de exclusión Vida | **Camino A: Vive en póliza. Se capturan en modelo `bca.poliza` y se evalúan al registrar recibos** |
| 5 | Nombre exacto producto Vida | **Catálogo de productos actualizable en tiempo de ejecución. No afecta arquitectura** |
| 6 | Alcance de v1 | **MetLife + Qualitas (Vida, GMM, Autos). Insurance pospuesto a v2** |
| 7 | Liquidación a promotorías/agentes | **Pospuesto a v2 (módulo `bca_liquidaciones`)** |

### 11.2 Notas de implementación

- **Exclusiones Vida (Camino A):** Se implementan como campos capturables en la póliza durante el alta manual o carga de portafolio. El calculador de PCA evaluará estas exclusiones al procesar cada recibo.
- **Catálogo de productos:** Totalmente actualizable vía UI. El mapeo a aseguradoras y la asignación de factores se gestiona dinámicamente.

---

## 12. Roadmap de evolución del módulo

| Versión | Alcance | Tiempo estimado |
|---|---|---|
| **v1.0** | Pólizas + cobranza MetLife + Qualitas (Vida, GMM, Autos) + PCA + reportes | 8-10 semanas |
| **v1.5** | Liquidación a promotorías y agentes (módulo `bca_liquidaciones`) | +4 semanas |
| **v2.0** | Insurance + conciliación inversa contra aseguradoras | +6 semanas |
| **v2.5** | Lectura automática de carátulas PDF + portal contratante | A definir |

---

---

## 13. Registro de correcciones arquitectónicas — Mayo 2026

Correcciones incorporadas en revisión pre-desarrollo. Cada una tiene referencia cruzada en la sección afectada.

| ID | Severidad | Componente afectado | Problema original | Corrección aplicada |
|---|---|---|---|---|
| **C1** | CRÍTICO | `poliza.pagado_hasta`, `recibo.pca_aplicada` | Bypass manual / overrides rígidos que bloquean las propias funciones de Odoo | Hacer `pagado_hasta` computed (`store=True`). En recibos, permitir validación `env.su` |
| **C2** | CRÍTICO | `bca.poliza.promotoria_id` | `store=True` causa stale data al cambiar `parent_id` del agente | Eliminar `store=True`. Campo computed puro con `_search_promotoria_id()` |
| **C3** | CRÍTICO | `res.partner.bca_aseguradoras_ids` | Constraint `UNIQUE(clave, aseguradora)` imposible en Many2many SQL | Nuevo modelo `res.partner.agente.aseguradora` con constraint SQL real |
| **C4** | CRÍTICO | `wizards/cobranza_diaria.py` | Pérdida de idioma y zona horaria al usar `context={}` | Usar `self.env` normal; Odoo >= 14 limpia la caché en savepoints |
| **C5** | CRÍTICO | `__manifest__.py` | `contacts` no existe en Odoo Community v19 | Eliminar de `depends`. Agregar `post_init_hook` |
| **A1** | ALTO | `reports/*.py` | SQL views sin `post_init_hook` — no se recrean en upgrade | Agregar `post_init_hook_BCA_Seguros` en manifest + carpeta `migrations/1.0.0/` |
| **A2** | ALTO | `models/res_partner.py` | Campos `bca_*` sin `index=True` — full table scan en `res.partner` | Agregar `index=True` en `bca_tipo`, `bca_estado_agente`, `bca_codigo_aseguradora` |
| **A3** | ALTO | `security/record_rules.xml` | Rules solo para Agente Portal; otros grupos sin declaración explícita | Agregar rule `[(1,'=',1)]` para todos los grupos en `bca.poliza` y `bca.recibo` |
| **A4** | ALTO | `parsers/__init__.py` | `PARSER_REGISTRY` dict estático — no extensible sin tocar `__init__.py` | Convertir a función `get_parser()` con mensaje de error descriptivo |
| **A5** | ALTO | `parsers/base.py` | `columnas_requeridas = []` sin implementación — KeyError llega hasta fila | Implementar `validar_estructura()` completo; llamar antes del loop en wizard |
| **M1** | MEDIO | `wizards/*.py` | TransientModel sin separación validar/grabar — importaciones parciales difíciles de depurar | Flujo en dos fases: validar (sin tocar BD) → grabar. Índice en `bca.poliza.name` |
| **M2** | MEDIO | `models/factor_pca.py` | Sin auditoría de cambios en factores | Heredar `mail.thread` + `tracking=True` en `factor`, `vigencias`, `activo` |
| **M3** | MEDIO | `calculadores_pca/metlife.py` | Multimoneda en PCA no especificada (MXN vs USD antes/después del factor) | PCA siempre en MXN. Conversión via `res.currency` antes de aplicar factor |
| **M4** | MEDIO | `models/poliza.py` | Sin historial de cambio de agente (R-ORG-02) | Nuevo modelo `bca.poliza.cambio.agente` + método `cambiar_agente()` obligatorio |
| **M5** | MEDIO | `security/groups.xml` | Director Comercial ausente como grupo — tiene permisos distintos al Director General | Agregar `group_bca_director_comercial` con permisos equivalentes excepto gestión de usuarios |

---

*Documento elaborado por Hábitat Digital. Base técnica para el desarrollo del módulo `BCA_Seguros`. Cualquier desviación del diseño aquí descrito debe documentarse y validarse con el arquitecto de solución antes de implementarse.*
