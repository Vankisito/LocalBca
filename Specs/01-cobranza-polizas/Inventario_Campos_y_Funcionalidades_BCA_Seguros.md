# Inventario de Campos y Funcionalidades — BCA Seguros

> **Propósito.** Mapa de referencia de **todo lo que ya existe** en el módulo `BCA_Seguros`
> (Odoo 19, `version 19.0.1.4.0`). Antes de crear un campo, modelo, selección o flujo nuevo
> —por ejemplo al implementar la etapa de **Reclutamiento de Agentes**— consultá este documento
> para reutilizar lo que ya vive en esta versión.
>
> **Última actualización:** 2026-06-26 · Generado a partir del código fuente en `BCA_Seguros/`.
> Mantener sincronizado al agregar campos/modelos.

---

## 0. Cómo leer este documento

- Los campos propios del módulo usan prefijo **`bca_`** cuando extienden modelos estándar de Odoo
  (`res.partner`, `crm.lead`, `product.template`, `hr.applicant`). Los modelos nuevos (`bca.*`)
  no necesitan prefijo en sus campos.
- **Convención de tipos de contacto:** todo en `res.partner` se distingue por `bca_tipo`
  (holding / aseguradora / promotoría / agente / contratante / asegurado). No se crean modelos
  separados por tipo de persona.
- **Dependencias del manifiesto:** `base`, `mail`, `product`, `hr_recruitment`, `crm`, `web`.
  Dependencia externa Python: `openpyxl`.

---

## 1. Modelos del módulo (resumen)

| Modelo | Tipo | Descripción | Archivo |
|---|---|---|---|
| `res.partner` | _inherit_ | Contactos: holding, aseguradora, promotoría, agente, contratante, asegurado | `models/res_partner.py` |
| `res.partner.agente.aseguradora` | nuevo | **Puente clave de agente ↔ aseguradora** (estado de carrera por aseguradora) | `models/res_partner_agente_aseg.py` |
| `hr.applicant` | _inherit_ | Candidato de reclutamiento → genera partner BCA al contratar | `models/hr_applicant.py` |
| `crm.lead` | _inherit_ | Oportunidad de venta de seguro → genera póliza al ganar | `models/crm_lead.py` |
| `product.template` | _inherit_ | Catálogo de productos de seguro | `models/product_template.py` |
| `bca.poliza` | nuevo | Póliza (Vida / GMM / Autos / Daños) | `models/poliza.py` |
| `bca.poliza.beneficiario` | nuevo | Beneficiarios (Vida) y dependientes/asegurados adicionales (GMM) | `models/poliza_beneficiario.py` |
| `bca.poliza.cambio.agente` | nuevo | Historial inmutable de cambios de agente en póliza | `models/poliza_cambio_agente.py` |
| `bca.recibo` | nuevo | Recibo de póliza + congelado de PCA al pago | `models/recibo.py` |
| `bca.conducto` | nuevo | Conducto de cobro por aseguradora | `models/conducto.py` |
| `bca.factor.pca` | nuevo | Catálogo de factores PCA con vigencia | `models/factor_pca.py` |
| `bca.bitacora.importacion` | nuevo | Cabecera de auditoría de cada corrida de cobranza | `models/bitacora.py` |
| `bca.bitacora.linea` | nuevo | Detalle por fila del CSV de cobranza | `models/bitacora.py` |
| `bca.wizard.carga.portafolio` | TransientModel | Carga masiva inicial de portafolio (.xlsx) | `wizards/carga_portafolio.py` |
| `bca.wizard.cobranza.diaria` | TransientModel | Cobranza diaria desde CSV | `wizards/cobranza_diaria.py` |

---

## 2. `res.partner` — Contactos BCA

Modelo central. Un solo modelo cubre todos los actores vía `bca_tipo`.

### 2.1 Selecciones (constantes reutilizables)

```python
# models/res_partner.py
TIPO_SELECTION = [
    ('holding', 'Holding'), ('aseguradora', 'Aseguradora'),
    ('promotoria', 'Promotoría'), ('agente', 'Agente'),
    ('contratante', 'Contratante'), ('asegurado', 'Asegurado'),
]
ESTADO_AGENTE_SELECTION = [
    ('prospecto', 'Prospecto'),
    ('clave_arranque', 'Clave de Arranque'),
    ('clave_definitiva', 'Clave Definitiva'),   # solo esta computa PCA
]
ESTADO_CIVIL_SELECTION = [
    ('soltero','Soltero(a)'),('casado','Casado(a)'),('divorciado','Divorciado(a)'),
    ('viudo','Viudo(a)'),('union_libre','Unión Libre'),
]
GENERO_SELECTION = [('masculino','Masculino'),('femenino','Femenino'),('otro','Otro')]
```

### 2.2 Campos

| Campo | Tipo | Notas |
|---|---|---|
| `bca_tipo` | Selection(TIPO) | Indexado. Discrimina el rol del contacto. |
| `bca_estado_agente` | Selection(ESTADO_AGENTE) | **Computed + store**, rollup del "mejor" estado de carrera en cualquier aseguradora. **No se edita a mano** (fuente de verdad = puente). |
| `bca_codigo_aseguradora` | Char | Indexado. Código interno de la aseguradora (clave para registry de parsers/calculadores PCA). |
| `bca_fecha_nacimiento` | Date | Demografía del contratante. |
| `bca_estado_civil` | Selection(ESTADO_CIVIL) | |
| `bca_genero` | Selection(GENERO) | |
| `bca_ref_prima_basica_trad` | Char | Referencia de pago Prima Básica TRAD (MetLife Vida). |
| `bca_ref_prima_medica` | Char | Referencia de cobro Prima MÉDICA (MetLife GMM). |
| `bca_fondo_variable` / `bca_fondo_fijo` | Char | Fondos de inversión. |
| `bca_fondo_variable_ppr` / `bca_fondo_fijo_ppr` | Char | Fondos PPR. |
| `bca_fondo_variable_cpea` / `bca_fondo_fijo_cpea` | Char | Fondos CPEA. |
| `agente_aseguradora_ids` | One2many → `res.partner.agente.aseguradora` | Claves del agente por aseguradora. |
| `bca_promotoria_id` | Many2one(res.partner) | **Computed sin store** (`parent_id` si es agente) + `search`. Tiempo real, nunca stale. |
| `bca_categoria_id` | Many2one(res.partner.category) | Computed según `bca_tipo`. |
| `bca_poliza_count` / `bca_recibo_count` | Integer computed | Smart buttons. |

> **RFC → campo estándar `vat`. Domicilio → `street/street2/city/zip/state_id`.** No se duplicaron.

### 2.3 Lógica / métodos

- `_compute_bca_estado_agente` — rollup por prioridad `clave_definitiva > clave_arranque > prospecto`; sin claves → `prospecto`.
- `_compute_promotoria_id` + `_search_promotoria_id` — promotoría = `parent_id` del agente.
- `_check_jerarquia` (`@api.constrains`) — **valida jerarquía organizacional**:
  agente → parent debe ser `promotoria`; promotoría → parent debe ser `holding`.
- `action_view_bca_polizas` / `action_view_bca_recibos` — acciones de smart button.

---

## 3. `res.partner.agente.aseguradora` — Puente clave de agente ⚑

> **Modelo clave para la etapa de Reclutamiento.** Es la **fuente de verdad** del estado de
> carrera de un agente **por aseguradora**. El rollup `res.partner.bca_estado_agente` se deriva
> de aquí, y la **PCA filtra por `estado='clave_definitiva'` de este puente**, no por el rollup.

| Campo | Tipo | Notas |
|---|---|---|
| `agente_id` | Many2one(res.partner) | Requerido, `ondelete=cascade`, domain `bca_tipo=agente`, indexado. |
| `aseguradora_id` | Many2one(res.partner) | Requerido, `ondelete=restrict`, domain `bca_tipo=aseguradora`, indexado. |
| `clave_agente` | Char | Requerido. La clave que asigna la aseguradora. _Rec name._ |
| `estado` | Selection(ESTADO_AGENTE) | Requerido, default `prospecto`. Estado de carrera **en esta aseguradora**. |
| `fecha_licencia` | Date | Fecha de licencia/clave. |

**Constraints SQL** (`models.Constraint`, estilo v19):
- `UNIQUE(aseguradora_id, clave_agente)` — clave única por aseguradora.
- `UNIQUE(agente_id, aseguradora_id)` — un agente, un registro por aseguradora.

> **Nota de negocio (memoria del proyecto):** las claves MetLife traen padding de ceros
> (`'000019799'`); los archivos las traen sin ceros → resolver por valor numérico.
> Las automated actions de Reclutamiento deben alimentar `estado` aquí.

---

## 4. `hr.applicant` — Reclutamiento (estado actual)

> **Punto de partida de la etapa de Reclutamiento.** Ya existe el flujo "candidato contratado →
> crea `res.partner` BCA". Extender esto en lugar de recrearlo.

| Campo | Tipo | Notas |
|---|---|---|
| `bca_promotoria_destino_id` | Many2one(res.partner) | domain `bca_tipo=promotoria`, tracking. **Requerido** al contratar para puesto "Reclutamiento de Agente". |

### Lógica existente

- `write()` detecta el paso a un `stage_id` con `hired_stage=True` y dispara
  `_bca_crear_partner_desde_contratado()`. **Idempotente** (no recrea si ya hay `partner_id` BCA).
- `_bca_crear_partner_desde_contratado()`:
  - Si `job_id == job_captacion_promotoria` → crea partner **promotoría** (`is_company=True`, parent = holding BCA).
  - Si `job_id == job_reclutamiento_agente` → crea partner **agente** (parent = `bca_promotoria_destino_id`); exige promotoría destino.
  - Solo actúa sobre los dos `hr.job` BCA registrados; ignora otros puestos.

### Puestos sembrados (`data/hr_jobs.xml`, `noupdate=1`)

| XML ID | Nombre |
|---|---|
| `BCA_Seguros.job_captacion_promotoria` | Captación de Promotoría |
| `BCA_Seguros.job_reclutamiento_agente` | Reclutamiento de Agente |

> **Gap conocido para Reclutamiento:** hoy se crea el `res.partner` agente, pero **no** se crea
> automáticamente el registro `res.partner.agente.aseguradora` (clave + estado de carrera).
> Ese es el siguiente eslabón natural a implementar (alta de clave de arranque / definitiva).

---

## 5. `crm.lead` — Oportunidad → Póliza

Selecciones `RAMO_SELECTION` y `PERIODICIDAD_SELECTION` (ver §7).

| Campo | Tipo | Notas |
|---|---|---|
| `bca_aseguradora_id` | Many2one(res.partner) | domain `bca_tipo=aseguradora`. |
| `bca_ramo` | Selection(RAMO) | |
| `bca_producto_id` | Many2one(product.template) | domain `bca_es_producto_seguro=True`. |
| `bca_prima_estimada` | Monetary | Prima anual estimada. |
| `bca_periodicidad` | Selection(PERIODICIDAD) | default `anual`. |
| `bca_poliza_generada_id` | Many2one(bca.poliza) | readonly, `copy=False`. |

**Lógica:** `_onchange_bca_producto_id` autollena ramo+aseguradora desde el producto;
`action_bca_generar_poliza()` abre el form de `bca.poliza` precargado (solo desde lead ganado y sin póliza previa).

---

## 6. `product.template` — Productos de seguro

| Campo | Tipo | Notas |
|---|---|---|
| `bca_es_producto_seguro` | Boolean | Marca el producto como de seguro (default False). |
| `bca_aseguradora_id` | Many2one(res.partner) | domain `bca_tipo=aseguradora`. |
| `bca_ramo` | Selection(RAMO) | |
| `bca_temporalidad_anios` | Integer | |
| `bca_es_capitalizable` | Boolean | |
| `bca_nombre_archivo_aseguradora` | Char | Clave exacta de mapeo en CSV de la aseguradora. |

---

## 7. `bca.poliza` — Póliza

Modelo más grande. Hereda `mail.thread`, `mail.activity.mixin`. `_order = 'fecha_inicio desc, name desc'`.

### 7.1 Selecciones

```python
PERIODICIDAD_SELECTION = [('mensual','Mensual'),('trimestral','Trimestral'),
                          ('semestral','Semestral'),('anual','Anual')]
ESTADO_SELECTION = [('borrador','Borrador'),('activa','Activa'),
                    ('vencida','Expirada'),('cancelada','Cancelada')]
TIPO_COBERTURA_SELECTION = [('estandar','Estándar'),('accidentes','Accidentes'),
                            ('invalidez','Invalidez')]
ESTATUS_PAGO_SELECTION = [('al_corriente','Al Corriente'),('vencido','Vencido'),
                          ('suspendido','Suspendido')]
# RAMO_SELECTION importado de product_template: vida / gmm / autos / danos
MESES_POR_PERIODO = {'mensual':1,'trimestral':3,'semestral':6,'anual':12}
```

> **Dos ejes independientes:** `estado` = ciclo de vida contractual; `estatus_pago` = salud de pago
> (derivada). "Expirada" (plazo terminó) ≠ `estatus_pago='vencido'` (prima en mora).

### 7.2 Campos — identificación y relaciones

| Campo | Tipo | Notas |
|---|---|---|
| `name` | Char | Nº de póliza, requerido, indexado, tracking. **Único por aseguradora** (`UNIQUE(name, aseguradora_id)`). |
| `aseguradora_id` | Many2one(res.partner) | Requerido, domain `bca_tipo=aseguradora`. |
| `producto_id` | Many2one(product.template) | Requerido, domain `bca_es_producto_seguro`. |
| `ramo` | Selection(RAMO) | Computed-editable desde producto (cascada Aseguradora→Ramo→Producto). |
| `agente_id` | Many2one(res.partner) | Requerido, domain `bca_tipo=agente`, tracking. **Cambiar solo vía `cambiar_agente()`**. |
| `promotoria_id` | Many2one(res.partner) | **Computed sin store** + `search` (= `agente.parent_id` en tiempo real). |
| `contratante_id` | Many2one(res.partner) | Requerido, domain `bca_tipo=contratante`. |
| `asegurado_id` | Many2one(res.partner) | domain `asegurado` o `contratante`. Vida/GMM. |
| `poliza_origen_id` | Many2one(bca.poliza) | Renovación/conversión. |
| `currency_id` | Many2one(res.currency) | Requerido. |
| `conducto_id` | Many2one(bca.conducto) | Conducto por defecto (se propaga a recibos). |

### 7.3 Campos — comercial / fechas / montos

| Campo | Tipo | Notas |
|---|---|---|
| `plan` | Char | |
| `fecha_emision` | Date | |
| `fecha_inicio` / `fecha_fin` | Date | Requeridos. `_check_fechas`: inicio < fin. |
| `periodicidad` | Selection | Requerido, default `anual`. |
| `prima_anual` | Monetary | |
| `prima_fraccionada` | Monetary | Prima por recibo. |
| `recargo_fraccionamiento` | Monetary | |
| `recargo_fijo` | Monetary | |
| `suma_asegurada` | Monetary | |
| `iva` | Monetary | Solo GMM, informativo. |

### 7.4 Campos — estatus de pago (derivado)

| Campo | Tipo | Notas |
|---|---|---|
| `estado` | Selection(ESTADO) | default `borrador`, requerido, tracking, indexado. |
| `pagado_hasta` | Date | **Computed + store**, máx `fecha_hasta` de recibos pagados. Verdad operativa. |
| `pagado_hasta_inicial` | Date | "Pagado Hasta (Importado)" — siembra el arranque desde la carga de portafolio. |
| `estatus_pago` | Selection | **Computed + store**, derivado de `pagado_hasta`/`_inicial` vs hoy + gracia. Refrescado por cron. |
| `pago_suspendido` | Boolean | Override manual → fuerza `estatus_pago='suspendido'`. |

### 7.5 Campos — GMM

| Campo | Tipo | Notas |
|---|---|---|
| `deducible` | Monetary | Influye en factor PCA. |
| `coaseguro` | Float | Formato `0.05`=5%. ≤5% no computa PCA. |
| `nivel_hospitalario` | Char | |
| `bca_sub_ramo_codigo` | Char | Código ramo/sub-ramo de la aseguradora (informativo). |

### 7.6 Campos — Vida

| Campo | Tipo | Notas |
|---|---|---|
| `tipo_cobertura` | Selection(TIPO_COBERTURA) | |
| `temporalidad_anios` | Integer | Años de vigencia. |
| `es_aportacion_adicional` | Boolean | Excluye recibo de PCA. |
| `coberturas_adicionales` | Text | Vida y GMM. |
| `beneficiario_ids` | One2many → `bca.poliza.beneficiario` | Vida: beneficiarios; GMM: dependientes. |
| `beneficiarios_porcentaje_total` | Float computed | Debe sumar 100% al confirmar (solo Vida). |

### 7.7 Relaciones inversas y contadores

`recibo_ids`, `cambio_agente_ids` (One2many); `recibo_count`, `cambio_agente_count` (Integer computed).

### 7.8 Lógica / métodos clave

- `action_confirmar()` — Borrador → Activa; valida % beneficiarios; genera plan de pagos.
- `action_cancelar()` — → Cancelada (no borra recibos, auditoría).
- `_generar_plan_pagos(desde=None)` — genera recibos de la **primera anualidad**. R-POL-05: no regenera si hay recibos pagados.
- `_crear_recibos_anualidad(inicio, numero_inicial)` — recibos de un año-póliza según periodicidad.
- `_generar_siguiente_anualidad()` / `action_generar_siguiente_anualidad()` — avance anualidad por anualidad (automático al pagar el último recibo, o botón manual).
- `cambiar_agente(nuevo_agente, motivo)` — **único punto** para cambiar agente; crea snapshot en `bca.poliza.cambio.agente`.
- `_cron_refrescar_estatus_pago()` — aging diario del estatus.
- Smart buttons: `action_view_recibos`, `action_view_cambios_agente`.

---

## 8. `bca.poliza.beneficiario`

| Campo | Tipo | Notas |
|---|---|---|
| `poliza_id` | Many2one(bca.poliza) | Requerido, `ondelete=cascade`. |
| `beneficiario_id` | Many2one(res.partner) | Requerido. Contacto genérico (no se fuerza `bca_tipo`). |
| `parentesco` | Selection | `conyuge/hijo/padre/madre/hermano/otro`. |
| `porcentaje` | Float(5,2) | % de suma asegurada (Vida; suma 100%). |
| `fecha_nacimiento` | Date | Asegurado adicional/dependiente (GMM). |

---

## 9. `bca.poliza.cambio.agente` — Historial inmutable

Todos los campos `readonly`. Se crea **solo** desde `bca.poliza.cambiar_agente()`.

| Campo | Tipo |
|---|---|
| `poliza_id` | Many2one(bca.poliza), cascade |
| `agente_anterior_id` / `agente_nuevo_id` | Many2one(res.partner), requeridos |
| `promotoria_anterior_id` / `promotoria_nueva_id` | Many2one(res.partner) |
| `fecha_cambio` | Date, default hoy |
| `motivo` | Char |
| `usuario_id` | Many2one(res.users), default usuario actual |

> Las pólizas históricas siguen acreditando a la promotoría original al liquidar (R-ORG-02).

---

## 10. `bca.recibo` — Recibo + PCA congelada

`_inherit = ['mail.thread']`, `_order = 'poliza_id, numero_recibo'`.

### 10.1 Selección y campos protegidos

```python
ESTADO_RECIBO_SELECTION = [('pendiente','Pendiente'),('pagado','Pagado'),('cancelado','Cancelado')]
CAMPOS_PCA_PROTEGIDOS = {'pca_aplicada', 'factor_aplicado', 'pca_currency_id'}
```

### 10.2 Campos

| Campo | Tipo | Notas |
|---|---|---|
| `name` | Char | Folio (secuencia `bca.recibo`), readonly. |
| `poliza_id` | Many2one(bca.poliza) | Requerido, indexado. |
| `agente_id` | Many2one(res.partner) | **Foto inmutable** del agente al pagar. |
| `promotoria_id` | Many2one(res.partner) | Foto al pagar. |
| `agente_poliza_id` | Many2one(res.partner) | **related** `poliza_id.agente_id`, store. Agente vigente (agrupar). |
| `numero_recibo` | Integer | Secuencia dentro de la póliza (1,2,3…). |
| `fecha_desde` / `fecha_hasta` | Date | Cobertura. `_check_fechas`. |
| `monto_modal` | Monetary | Prima modal. |
| `recargo` | Monetary | |
| `prima_neta` | Monetary | **Base de PCA.** |
| `prima_total` | Monetary | Lo que paga el cliente. |
| `currency_id` | Many2one | related `poliza_id.currency_id`. |
| `estado` | Selection(ESTADO_RECIBO) | default `pendiente`, tracking, indexado. |
| `fecha_pago` | Date | |
| `conducto_id` | Many2one(bca.conducto) | |
| `folio_endoso` | Char | Solo GMM. |
| `pca_currency_id` | Many2one | **Siempre MXN** (decisión D-08). readonly. |
| `pca_aplicada` | Monetary(pca_currency) | **Congelada al pago**, readonly, tracking. |
| `factor_aplicado` | Float(6,4) | readonly, tracking. |
| `motivo_exclusion_pca` | Char | Razón de PCA=0. |
| `bitacora_linea_id` | Many2one(bca.bitacora.linea) | Línea de cobranza que generó el pago. |

**Constraint:** `UNIQUE(poliza_id, numero_recibo)`.

### 10.3 Lógica / reglas

- `create()` — **R1**: crear recibo manual con un pendiente existente → `RedirectWarning` al pendiente (los recibos nacen del plan). Bypass interno: contexto `bca_generando_plan`.
- `write()` — **C1**: bloquea edición de `CAMPOS_PCA_PROTEGIDOS` en recibos pagados. Escape: `env.su` o contexto `allow_pca_edit`.
- `action_registrar_pago(vals)` — valida precondiciones, **FIFO** (paga el más antiguo), calcula y congela PCA, avanza anualidad si era el último pendiente.
- `action_registrar_pago_ui()` — wrapper de form (exige conducto).
- `action_cancelar_pago()` — deshace pago → pendiente (solo Director / Director Comercial; guardia FIFO inversa).
- `action_anular_recibo()` — pendiente → cancelado (solo Director / Director Comercial).
- `_calcular_pca()` — delega al `CALCULADOR_REGISTRY` según `bca_codigo_aseguradora`.

---

## 11. `bca.conducto` — Conducto de cobro

| Campo | Tipo | Notas |
|---|---|---|
| `name` | Char | Requerido. |
| `codigo_archivo` | Char | Requerido. Clave exacta en columna de conducto del CSV. |
| `aseguradora_id` | Many2one(res.partner) | Requerido, domain aseguradora. |
| `activo` | Boolean | default True. |

**Constraint:** `UNIQUE(codigo_archivo, aseguradora_id)`.

---

## 12. `bca.factor.pca` — Factores PCA con vigencia

`_inherit = ['mail.thread','mail.activity.mixin']`.

| Campo | Tipo | Notas |
|---|---|---|
| `name` | Char | Requerido. |
| `aseguradora_id` | Many2one(res.partner) | Requerido. |
| `ramo` | Selection(RAMO) | |
| `producto_ids` | Many2many(product.template) | Productos de seguro. |
| `currency_id` | Many2one(res.currency) | |
| `coaseguro_min` / `coaseguro_max` | Float | Solo GMM. |
| `deducible_min` | Monetary | Solo GMM. |
| `factor` | Float(6,4) | Requerido, tracking. **Rango [0.0, 1.2]** (`_check_factor_rango`). |
| `vigencia_desde` | Date | Requerido, tracking. |
| `vigencia_hasta` | Date | tracking. |
| `activo` | Boolean | default True, tracking. |

---

## 13. `bca.bitacora.importacion` / `bca.bitacora.linea` — Auditoría de cobranza

**Inmutables** (write/unlink bloqueados salvo `env.su`). Solo creadas desde el wizard de cobranza.

### Cabecera

| Campo | Tipo |
|---|---|
| `name` | Char (secuencia `bca.bitacora.importacion`) |
| `usuario_id` | Many2one(res.users), default usuario |
| `fecha_ejecucion` | Datetime, default now |
| `aseguradora_id` | Many2one(res.partner), requerido |
| `ramo` | Selection(`vida`/`gmm`) |
| `nombre_archivo` | Char |
| `archivo_adjunto` | Binary (attachment) |
| `total_filas`, `recibos_aplicados`, `anulaciones_ignoradas`, `polizas_no_encontradas`, `errores_procesamiento` | Integer |
| `pca_total_sesion` | Monetary |
| `currency_id` | Many2one(res.currency) |
| `linea_ids` | One2many → `bca.bitacora.linea` |

### Línea

| Campo | Tipo | Notas |
|---|---|---|
| `bitacora_id` | Many2one, cascade | |
| `numero_fila` | Integer | |
| `marca` | Selection | `aplicado/anulado/no_encontrada/sin_recibo/advertencia/error/info` |
| `mensaje` | Text | |
| `numero_poliza_raw` | Char | Valor exacto del CSV (auditoría). |
| `recibo_id` | Many2one(bca.recibo) | |

---

## 14. Wizards (TransientModel)

### 14.1 `bca.wizard.carga.portafolio` — Carga masiva inicial (.xlsx)

- Campos: `archivo` (Binary), `nombre_archivo`, más selección de aseguradora/ramo.
- Layout `LAY_OUT_-_Portafolio_BCA`: encabezados fila 2, tipos fila 3, datos desde fila 4.
- Hojas → ramo: `VIDA→vida`, `GMM→gmm` (Autos/Qualitas fuera de alcance).
- Mapas de normalización: `PERIODICIDAD_MAP`, `ESTADO_POLIZA_MAP`, `ESTADO_CIVIL_MAP`, `GENERO_MAP`, `PARENTESCO_MAP`.
- Botón "Descargar plantilla" genera `.xlsx` (`tools/generar_plantilla_portafolio.py`, `wizards/plantilla_portafolio.py`).
- Diccionarios de columnas: `Specs/01-cobranza-polizas/diccionario-campos-vida-bca-seguros-v1.md` y `…-gmm-…`.

### 14.2 `bca.wizard.cobranza.diaria` — Cobranza diaria (.csv)

- Campos: `archivo` (Binary), `nombre_archivo`, `aseguradora_id` (default MetLife), `ramo` (`vida`/`gmm`).
- `action_procesar()` — valida estructura (fail-fast sin bitácora), crea bitácora, aplica pagos FIFO con savepoint por fila, abre la bitácora.
- `MARCAS_APLICADAS = ('aplicado','advertencia')`.
- Botón "Descargar plantilla .csv" (`wizards/plantilla_cobranza_diaria.py`).

---

## 15. Parsers y Calculadores PCA (registries por aseguradora)

### Parsers (`parsers/`) — lectura de archivos de cobranza

| Archivo | Cubre |
|---|---|
| `base.py` | Clase base + `get_parser(codigo, ramo)` |
| `metlife_lsp.py` | MetLife Vida (LSP) |
| `metlife_gcaye.py` | MetLife GMM (GCAYE) |
| `qualitas.py` | Qualitas / Autos (placeholder, fuera de v1) |

### Calculadores PCA (`calculadores_pca/`) — cálculo de comisión

| Archivo | Cubre |
|---|---|
| `base.py` | Clase base + `CALCULADOR_REGISTRY` |
| `metlife.py` | MetLife (Vida + GMM) |

> El cálculo se selecciona por `aseguradora_id.bca_codigo_aseguradora`. Si no hay calculador
> registrado → `UserError`. Solo `clave_definitiva` del puente computa PCA; coaseguro ≤5% y
> aportaciones adicionales se excluyen.

---

## 16. Seguridad — Grupos y reglas

### Grupos (`security/groups.xml`)

| XML ID | Nombre | Hereda (implied_ids) |
|---|---|---|
| `group_bca_agente` | Agente BCA | — (independiente, solo sus registros) |
| `group_bca_operador` | Operador BCA | `product.group_product_manager` |
| `group_bca_lider` | Líder BCA | operador |
| `group_bca_director_comercial` | Director Comercial BCA | líder (→ operador) |
| `group_bca_director` | Director BCA | director_comercial (→ todo) |

> **Cancelar/anular pagos y recibos:** solo `group_bca_director` o `group_bca_director_comercial`.
> ACLs en `security/ir.model.access.csv`; record rules en `security/record_rules.xml`
> (cada grupo no-agente requiere rule explícita `[(1,'=',1)]` por la combinación AND de implied_ids).

---

## 17. Datos semilla (`data/`)

| Archivo | Contenido |
|---|---|
| `sequences.xml` | Secuencias `bca.recibo`, `bca.bitacora.importacion` |
| `partner_categories.xml` | Categorías por `bca_tipo` (holding/aseguradora/promotoría/agente/contratante) |
| `product_categories.xml` | Categorías de producto |
| `hr_jobs.xml` | Puestos `job_captacion_promotoria`, `job_reclutamiento_agente` |
| `aseguradoras_iniciales.xml` | Holding BCA (`partner_bca_holding`), MetLife (`partner_metlife`), etc. |
| `productos_metlife.xml` | Catálogo de productos MetLife |
| `conductos_metlife.xml` | Conductos MetLife |
| `factores_metlife_2026.xml` | Factores PCA MetLife 2026 |
| `config_parameters.xml` | `bca_seguros.dias_gracia_pago = 30` |
| `cron_estatus_pago.xml` | Cron diario `_cron_refrescar_estatus_pago` |

XML IDs útiles: `BCA_Seguros.partner_bca_holding`, `BCA_Seguros.partner_metlife`,
`BCA_Seguros.job_reclutamiento_agente`, `BCA_Seguros.job_captacion_promotoria`.

---

## 18. Guía rápida para la etapa de Reclutamiento

Antes de crear campos nuevos, revisá lo que **ya existe**:

- **Identidad del agente:** `res.partner` con `bca_tipo='agente'`, jerarquía vía `parent_id`
  (promotoría) validada por `_check_jerarquia`.
- **Estado de carrera:** `res.partner.agente.aseguradora.estado`
  (`prospecto` → `clave_arranque` → `clave_definitiva`) **por aseguradora**; rollup en
  `res.partner.bca_estado_agente` (computed, no editar a mano).
- **Clave de agente:** `res.partner.agente.aseguradora.clave_agente` (+ `fecha_licencia`),
  única por aseguradora. Ojo con el padding de ceros.
- **Datos demográficos:** ya hay `bca_fecha_nacimiento`, `bca_estado_civil`, `bca_genero`
  (RFC en `vat`, domicilio en `street/...`).
- **Flujo de contratación:** `hr.applicant` → `_bca_crear_partner_desde_contratado()` ya crea el
  partner agente/promotoría al pasar a stage `hired`. **Falta** crear el registro del puente
  (clave + estado) — ese es el siguiente paso lógico, no recrear el partner.
- **Promotoría destino:** `hr.applicant.bca_promotoria_destino_id` ya captura el destino del agente.

**Selecciones ya definidas y reutilizables:** `TIPO_SELECTION`, `ESTADO_AGENTE_SELECTION`,
`ESTADO_CIVIL_SELECTION`, `GENERO_SELECTION` (en `models/res_partner.py`),
`RAMO_SELECTION` (en `models/product_template.py`).
</content>
</invoke>
