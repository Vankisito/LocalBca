# Plan de Desarrollo — Módulo `bca_core`

**Proyecto:** Grupo BCA — Gestión de Pólizas, Cobranza y PCA  
**Plataforma:** Odoo Community 19  
**Autor:** Hábitat Digital  
**Audiencia:** Desarrolladores humanos y agentes IA  
**Estado:** Documento vivo — actualizar al cerrar cada etapa

> **Documentos de referencia obligatorios (leer antes de este plan):**
> 1. `Specs/Arquitectura_BCA_Seguros.md` — modelo de datos, reglas, correcciones arquitectónicas
> 2. `Specs/Logica de Negocios_BCA_Seguros.md` — qué debe hacer el negocio y por qué
> 3. `Specs/Decisiones.md` (cuando exista) — decisiones ya tomadas y sus razones

---

## 1. Cómo usar este documento

### Para un humano desarrollador
Lee las secciones 2–4 para entender el alcance y las reglas. Luego avanza etapa por etapa en orden: cada etapa lista los archivos a crear, las reglas de negocio que implementa y un checklist de verificación antes de continuar.

### Para un agente IA
Sigue este protocolo antes de generar cualquier código:

1. **Lee `Specs/Arquitectura_BCA_Seguros.md` completo.** Contiene las definiciones exactas de campos, tipos, constraints y 13 correcciones críticas (C1–M5). No asumir nada que no esté ahí.
2. **Consulta la versión de Odoo:** es **19 Community**. Aplican: OWL v3 (si se necesita frontend), `invisible=...` (no `attrs`), `groups=` en campos en lugar de `attrs="{'invisible': [...]}"` para seguridad.
3. **Antes de cada etapa, lee el patrón correspondiente** en `C:\Users\rafav\.claude\skills\odoo-development-skill\skills\` según el índice del skill.
4. **No generes código de memoria.** Si hay duda sobre sintaxis de Odoo 19, lee el archivo de pattern primero.
5. **Marca la tarea como completada** (cambia `[ ]` a `[x]`) cuando la etapa pase su checklist.

---

## 2. Principios de desarrollo (no negociables)

### 2.0 Decisión de diseño — Tipo de usuario del agente

> **Los agentes son usuarios internos de Odoo** (`share=False`). No son usuarios portal.
> Esto supercede lo que dice `Arquitectura_BCA_Seguros.md §8` sobre `share=True`, que fue una decisión previa revertida.

Consecuencias:
- Los agentes inician sesión en el **backend** de Odoo como cualquier usuario interno.
- Tienen acceso a módulos estándar (CRM, calendario, etc.) según los grupos que el Director General les asigne.
- Dentro de `bca_core`, las **record rules** los restringen a ver solo sus propias pólizas y recibos — no se necesita ninguna ruta portal para esto.
- **No existe un portal de agente** (`/my/polizas`). El módulo `portal` no es una dependencia de `bca_core`.
- El nombre del grupo es `group_bca_agente` (no `group_bca_agente_portal`).

---

### 2.1 Reglas de oro del módulo (de `Arquitectura_BCA_Seguros.md` §10)
1. **Nunca editar `pagado_hasta` directamente.** Es un campo Computed almacenado gestionado por Odoo.
2. **Nunca recalcular PCA de un recibo pagado.** `pca_aplicada` y `factor_aplicado` son inmutables desde `estado='pagado'`.
3. **Toda fila del CSV en savepoint independiente.** Patrón: `with self.env.cr.savepoint()`. (Nunca usar `context={}`).
4. **Campos críticos con `tracking=True`.** `pagado_hasta`, `pca_aplicada`, `factor_aplicado`, `estado`, `factor`.
5. **No incrustar nombres de productos ni factores en código.** Todo en catálogo.
6. **Encoding Latin-1 manejado en el parser.** Nunca pedir al usuario que convierta.
7. **Nueva aseguradora = parser + calculador + factores.** Sin tocar modelos.
8. **Validar estructura del CSV antes del loop.** `parser.validar_estructura(df)` primero; si falla, detener sin bitácora.
9. **Limitar bypass de contexto.** Usar solo para bypass técnico necesario (ej. evitar loops recursivos) o usar `env.su`.
10. **`promotoria_id` en póliza es computed puro, nunca stored.** SQL views hacen el JOIN directo a `parent_id`.

### 2.2 Estándares OCA para Odoo 19
- Python: PEP8, SOLID, DRY, KISS. Sin `# -*- coding: utf-8 -*-`. Usar `super()`.
- Todo modelo nuevo: `_name`, `_description`. Agregar `_rec_name` si no es `name`.
- Campos en `res.partner` filtrados frecuentemente: `index=True` (corrección A2 — `bca_tipo`, `bca_estado_agente`, `bca_codigo_aseguradora`).
- SQL constraints (`_sql_constraints`) preferidos sobre Python `@api.constrains` cuando el constraint es de unicidad.
- Todo modelo nuevo tiene entrada en `security/ir.model.access.csv`.
- Vistas XML: solo `<xpath>` / herencia, nunca reemplazar.
- Menús: estructura jerárquica en `views/menu.xml` separado.
- Record rules: declarar **explícitamente** para todos los grupos, incluso con dominio `[(1,'=',1)]` (corrección A3 — ver §2.4.3 para el por qué).

### 2.3 Correcciones arquitectónicas críticas a respetar
Referencia rápida a las 13 correcciones en `Arquitectura_BCA_Seguros.md` §13:

| ID | Impacto en código |
|---|---|
| C1 | `pagado_hasta` es Computed stored; permitir a superusuarios / sistema editar recibos pagados |
| C2 | `promotoria_id` en `bca.poliza`: `store=False`, implementar `_search_promotoria_id()` |
| C3 | No `Many2many` para agente↔aseguradora; usar `res.partner.agente.aseguradora` |
| C4 | En wizard cobranza: usar `self.env` conservando contexto (idioma, zona horaria) en `savepoint` |
| C5 | `depends` en manifest: sin `contacts`; agregar `post_init_hook` |
| A1 | `post_init_hook_bca_core` en `__init__.py` raíz; carpeta `migrations/1.0.0/` |
| A2 | `index=True` en `bca_tipo`, `bca_estado_agente`, `bca_codigo_aseguradora` |
| A3 | Record rules explícitas para todos los grupos — ver §2.4.3 para el por qué real |
| A4 | `get_parser()` en lugar de dict estático |
| A5 | `validar_estructura()` implementada en base y llamada antes del loop |
| M1 | Wizard portafolio: fase validar sin tocar BD → fase grabar |
| M2 | `factor_pca` hereda `mail.thread`, campos `factor`/vigencias con `tracking=True` |
| M3 | PCA siempre en MXN; conversión vía `res.currency` antes del factor |
| M4 | `bca.poliza.cambio.agente` + método `cambiar_agente()` obligatorio |
| M5 | Grupo `group_bca_director_comercial` con permisos específicos |

---

### 2.4 Errores conocidos en Odoo 19 — anticipados desde el inicio

> Estos errores fueron descubiertos en producción en un módulo similar de Hábitat Digital. Se documentan aquí para que **no se repitan**. Antes de escribir cualquier vista o configuración de seguridad, verificar el patrón contra el código fuente de `addons/crm` o `addons/project` de Odoo 19.

#### 2.4.1 Cambios de API breaking en Odoo 19

| Qué usar | Por qué | Lo incorrecto |
|---|---|---|
| `res.groups.privilege` con `privilege_id` | `category_id` fue eliminado de `res.groups` en v19 | `category_id="..."` en `<record model="res.groups">` |
| `<group>` sin atributos en `<search>` | RELAXNG de v19 no acepta ningún atributo en `<group>` dentro de `<search>` | `<group expand="0" string="Agrupar por">` |
| Smart buttons: `type="object"` con método Python que retorna el action dict | `type="action"` con `active_id` en contexto rechazados en v19 | `type="action"` + `context="{'active_id': active_id}"` |
| `_read_group(groupby=[...], aggregates=['campo:sum'])` que retorna **tuplas** | `read_group()` deprecado en v19 | `self.read_group(domain, fields, groupby)` |
| Etapas CRM globales (sin `team_id`) | `team_id` eliminado de `crm.stage` en v19 | `<field name="team_id">` en stages de CRM |
| `<xpath expr="//t[@t-name='kanban-box']">` para heredar kanban de `crm.lead` | En v19 los campos del kanban viven dentro del template QWeb, no son nodos de primer nivel | XPath a campos de primer nivel en kanban de CRM |

**Regla de oro:** Antes de escribir cualquier vista XML o configuración de seguridad, abrir el archivo correspondiente en `odoo/addons/` (crm, project, sale) y verificar la sintaxis exacta en v19.

#### 2.4.2 XML — namespacing y orden de carga

| Regla | Consecuencia si se ignora |
|---|---|
| Todo `ref` propio del módulo **siempre con prefijo** `bca_core.`, incluso dentro del mismo archivo | `ValueError: External ID not found` al cargar datos |
| **Un solo bloque `<data>`** por archivo XML | Dos bloques `<data>` en el mismo archivo no garantizan commit entre ellos; puede fallar la FK del segundo bloque |
| Todo `<menuitem>` raíz **debe tener atributo `groups`** | En Odoo 19, un menuitem raíz sin `groups` solo es visible en modo debug; invisible en producción |
| El orden entre **archivos** en la lista `data[]` del manifest **sí es secuencial** | Usar esta garantía (no la del orden intra-archivo) para gestionar dependencias entre registros |

#### 2.4.3 Seguridad — el problema real de `implied_ids` y record rules

**El error más costoso conceptualmente en módulos similares:**

`implied_ids` en Odoo no es solo herencia de permisos — es **membresía acumulativa**. Si `group_bca_director` tiene `implied_ids = [group_bca_director_comercial]`, el Director General **pertenece a ambos grupos simultáneamente** y las record rules de `group_bca_director_comercial` le aplican también.

Consecuencia práctica: si `group_bca_operador` tiene una record rule restrictiva (ej. solo pólizas propias), y `group_bca_lider` tiene `implied_ids = operador`, entonces el Líder también queda restringido a pólizas propias aunque organizacionalmente deba ver todas.

**Fix correcto (corrección A3):** Declarar una record rule explícita `[(1,'=',1)]` para cada grupo no-agente en cada modelo con record rules, **incluso si parece redundante**.

**Corolario — topología de grupos:** Si dos roles tienen visibilidades no lineales (el Líder ve más que el Operador en algunos modelos pero menos en otros), **no pueden estar en una cadena lineal de `implied_ids`**. En ese caso se necesita topología de hermanos: ambos implican un grupo base común, pero no se implican entre sí. Revisar antes de definir la jerarquía final.

#### 2.4.4 Bug crítico en `pagado_hasta` — uso de método manual vs computed

**El error más común en implementaciones de este patrón (C1):**
Intentar bloquear `write` y usar un método manual dedicado. Al hacer eso, el propio método manual queda atrapado por el bloqueo de `write` generando un *deadlock* o requiriendo bypass no elegante.

**Solución correcta (Computed Field):**
Declarar `pagado_hasta` como un campo computed almacenado. Odoo gestionará el avance (pagos) y retroceso (cancelaciones) automáticamente.

```python
pagado_hasta = fields.Date(
    compute='_compute_pagado_hasta',
    store=True,
    tracking=True
)

@api.depends('recibo_ids.estado', 'recibo_ids.fecha_hasta')
def _compute_pagado_hasta(self):
    for pol en self:
        ultimo = pol.recibo_ids.filtered(
            lambda r: r.estado == 'pagado'
        ).sorted('fecha_hasta', reverse=True)[:1]
        pol.pagado_hasta = ultimo.fecha_hasta.date() if ultimo else False
```
Esto funciona de forma atómica y auditable sin requerir bloqueos sobre el método `write()`.

#### 2.4.5 Reglas generales de modelos para evitar bugs silenciosos

| Regla | Por qué |
|---|---|
| SQL `UNIQUE` con columna nullable → agregar también `@api.constrains` Python | `NULL ≠ NULL` en PostgreSQL: dos registros con `None` pasan el unique constraint |
| Todo `Many2one` con restricción de elegibilidad → `domain` desde el primer commit | Sin domain, el campo muestra todos los registros del modelo incluidos los inválidos |
| Campos `Monetary` → `default=lambda self: self.env.company.currency_id` en `currency_id` | Sin default, Odoo emite `WARNING: NOT NULL constraint` al instalar |
| `action_registrar_pago()` y cualquier método que genera estado irreversible → **validar precondiciones antes de ejecutar** | Si `fecha_pago`, `prima_neta` o `conducto_id` están vacíos, la PCA queda congelada con valor corrupto e inmutable |

#### 2.4.6 Clave de agente — campo único puede ser insuficiente

El modelo `res.partner.agente.aseguradora` tiene un solo campo `clave_agente`. Si los CSVs históricos siguen usando la **clave provisional** del agente después de su promoción a definitiva, el parser no encontrará match.

Evaluar al implementar el parser de MetLife si los archivos históricos mezclan claves provisionales y definitivas. Si es así, agregar `clave_agente_provisional` y búsqueda OR en el parser:
```python
registro = env['res.partner.agente.aseguradora'].search([
    ('aseguradora_id', '=', aseguradora_id),
    '|',
    ('clave_agente', '=', clave_raw),
    ('clave_agente_provisional', '=', clave_raw),
], limit=1)
```

#### 2.4.7 Dependencias Python externas

Declarar siempre en el manifest. Sin esto, Odoo instala el módulo aunque la librería no exista y falla en runtime con `ImportError` difícil de diagnosticar:

```python
'external_dependencies': {
    'python': ['openpyxl'],  # para wizard de carga de portafolio (Excel)
    # 'python': ['pandas'],  # agregar si se usa en parsers CSV
},
```

`openpyxl` viene incluido con Odoo 19 — verificar antes de declararlo. Para cualquier librería **no incluida en Odoo**, agregar también `requirements.txt` en la raíz del módulo (sobrevive recreaciones de contenedor).

---

## 3. Grafo de dependencias

```
[Odoo: base, mail, product, hr_recruitment, crm, web]
        │
        ▼
[ETAPA 0] Scaffolding: __manifest__.py + __init__.py de todos los paquetes
        │
        ▼
[ETAPA 1] Modelos base (sin dependencias cruzadas entre sí)
  ├── res_partner.py          (extiende res.partner)
  ├── res_partner_agente_aseg.py  (depende de res.partner ext)
  ├── product_template.py     (extiende product.template)
  ├── conducto.py             (depende de res.partner)
  └── factor_pca.py           (depende de res.partner + product.template)
        │
        ▼
[ETAPA 2] Modelos core de negocio
  ├── poliza.py               (depende de todos los de etapa 1)
  ├── poliza_cambio_agente.py (depende de poliza.py)
  ├── recibo.py               (depende de poliza.py + conducto.py)
  │                           ↳ Copia y guarda `agente_id` y `promotoria_id` en el momento de creación/pago (Foto Inmutable).
  └── bitacora.py             (depende de recibo.py — y recibo tiene bitacora_linea_id,
                               referencia circular resuelta por el ORM; deben estar en
                               la misma etapa y el mismo __init__.py de models/)
        │
        ▼
[ETAPA 3] Modelos de integración Odoo
  ├── hr_applicant.py         (depende de res.partner ext)
  └── crm_lead.py             (depende de poliza.py + product.template ext)
        │
        ▼
[ETAPA 4] Seguridad
  ├── security/groups.xml
  ├── security/ir.model.access.csv
  └── security/record_rules.xml
        │
        ▼
[ETAPA 5] Datos iniciales (XML)
  ├── sequences.xml
  ├── partner_categories.xml
  ├── product_categories.xml
  ├── hr_jobs.xml
  ├── aseguradoras_iniciales.xml
  ├── conductos_metlife.xml
  └── factores_metlife_2026.xml
        │
        ▼
[ETAPAS 6–7] Parsers + Calculadores PCA (independientes entre sí, paralelos)
  parsers/                    calculadores_pca/
  ├── base.py                 ├── base.py
  ├── metlife_lsp.py          └── metlife.py
  │   ↳ usa res.partner.agente.aseguradora para resolver
  │     clave_agente del CSV → agente_id (res.partner)
  │     si el parser necesita validar/identificar al agente
  │     por código de aseguradora antes de buscar la póliza
  ├── metlife_gcaye.py
  ├── qualitas.py (placeholder)
  └── __init__.py (get_parser)
        │
        ▼
[ETAPA 8] Wizards (dependen de parsers + calculadores)
  ├── carga_portafolio.py
  └── cobranza_diaria.py
        │
        ▼
[ETAPA 9] Reportes SQL (dependen de bca.recibo)
  ├── pca_por_agente.py       (Lee agente_id y promotoria_id del recibo inmutable)
  ├── pca_por_promotoria.py
  ├── pca_consolidado.py
  └── estado_cartera.py
        │
        ▼
[ETAPA 10] Vistas XML (dependen de todos los modelos)
  views/
  ├── menu.xml
  ├── res_partner_views.xml
  ├── product_template_views.xml
  ├── crm_lead_views.xml
  ├── poliza_views.xml
  ├── recibo_views.xml
  ├── factor_pca_views.xml
  ├── conducto_views.xml
  ├── bitacora_views.xml
  ├── reportes_views.xml
  ├── wizard_carga_portafolio_views.xml
  └── wizard_cobranza_diaria_views.xml
        │
        ▼
[ETAPA 11] Pruebas
  tests/
  ├── test_poliza.py
  ├── test_cobranza_fifo.py
  ├── test_pca_metlife.py
  ├── test_inmutabilidad.py
  └── test_record_rules.py
```

---

## 4. Etapas de desarrollo

### Etapa 0 — Scaffolding del módulo
**Tiempo estimado:** 1–2 horas  
**Objetivo:** Estructura de archivos y manifest instalable.

**Archivos a crear:**

| Archivo | Contenido clave |
|---|---|
| `BCA_seguros/__manifest__.py` | `name`, `version='19.0.1.0.0'`, `depends`, `data`, `post_init_hook='post_init_hook_bca_core'` |
| `BCA_seguros/__init__.py` | Imports de subpaquetes + función `post_init_hook_bca_core` |
| `BCA_seguros/models/__init__.py` | Imports de todos los archivos de models/ |
| `BCA_seguros/wizards/__init__.py` | Imports |
| `BCA_seguros/parsers/__init__.py` | `get_parser()` (esqueleto inicial) |
| `BCA_seguros/calculadores_pca/__init__.py` | `CALCULADOR_REGISTRY` |
| `BCA_seguros/reports/__init__.py` | Imports |
| `BCA_seguros/tests/__init__.py` | Import |
| `BCA_seguros/static/description/icon.png` | Ícono (placeholder PNG 16x16) |

**Contenido de `__manifest__.py`:**
```python
{
    'name': 'BCA Core — Gestión de Pólizas y Cobranza',
    'version': '19.0.1.0.0',
    'category': 'Insurance',
    'summary': 'Módulo vertical BCA para pólizas, cobranza, PCA y comisiones',
    'author': 'Hábitat Digital',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'product', 'hr_recruitment', 'crm', 'web'],
    'data': [
        # Seguridad (siempre primero)
        'security/groups.xml',
        'security/ir.model.access.csv',
        'security/record_rules.xml',
        # Datos iniciales
        'data/sequences.xml',
        'data/partner_categories.xml',
        'data/product_categories.xml',
        'data/hr_jobs.xml',
        'data/aseguradoras_iniciales.xml',
        'data/conductos_metlife.xml',
        'data/factores_metlife_2026.xml',
        # Vistas
        'views/menu.xml',
        'views/res_partner_views.xml',
        'views/product_template_views.xml',
        'views/crm_lead_views.xml',
        'views/poliza_views.xml',
        'views/recibo_views.xml',
        'views/factor_pca_views.xml',
        'views/conducto_views.xml',
        'views/bitacora_views.xml',
        'views/reportes_views.xml',
        'views/wizard_carga_portafolio_views.xml',
        'views/wizard_cobranza_diaria_views.xml',
    ],
    'post_init_hook': 'post_init_hook_bca_core',
    'installable': True,
    'application': True,
    # Declarar SIEMPRE librerías externas. Sin esto Odoo instala el módulo
    # aunque la lib no exista y falla en runtime con ImportError (ver §2.4.7)
    'external_dependencies': {
        'python': ['openpyxl'],  # verificar si ya viene incluida en Odoo 19
    },
}
```

**`post_init_hook_bca_core`** en `__init__.py` raíz:
```python
def post_init_hook_bca_core(env):
    """Inicializar SQL views de reportes al instalar/actualizar."""
    for model_name in [
        'bca.reporte.pca.agente',
        'bca.reporte.pca.promotoria',
        'bca.reporte.pca.consolidado',
        'bca.reporte.estado.cartera',
    ]:
        env[model_name].init()
```

**Checklist Etapa 0:**
- [ ] `odoo-bin -i bca_core` instala sin errores (aunque sin datos todavía)
- [ ] No hay imports circulares
- [ ] `post_init_hook` definido y referenciado en manifest

---

### Etapa 1 — Modelos base
**Tiempo estimado:** 4–6 horas  
**Reglas de negocio cubiertas:** R-ORG-01, R-ORG-02 (parcial)

#### `models/res_partner.py`
Extiende `res.partner`. Campos nuevos (todos con `index=True` donde aplica):
- `bca_tipo`: Selection `[('holding','Holding BCA'),('aseguradora','Aseguradora'),('promotoria','Promotoría Afiliada'),('agente','Agente'),('contratante','Contratante')]`, `index=True`
- `bca_estado_agente`: Selection `[('prospecto','Prospecto'),('con_licencia','Con Licencia')]`, `index=True`
- `bca_fecha_licencia`: Date
- `bca_codigo_aseguradora`: Char, `index=True` — Ej: METLIFE, QUALITAS
- `bca_promotoria_id`: Many2one computed **sin store** → retorna `parent_id` si `bca_tipo='agente'`
- `agente_aseguradora_ids`: One2many → `res.partner.agente.aseguradora`

Constraints Python (`@api.constrains`):
- Si `bca_tipo='agente'` → `parent_id.bca_tipo` debe ser `'promotoria'`
- Si `bca_tipo='promotoria'` → `parent_id.bca_tipo` debe ser `'holding'`

Computed `_compute_category_id`: asignar categoría automáticamente según `bca_tipo`.

#### `models/res_partner_agente_aseg.py`
Modelo `res.partner.agente.aseguradora`:
```python
_sql_constraints = [
    ('unique_clave_aseg', 'UNIQUE(aseguradora_id, clave_agente)',
     'La clave del agente debe ser única por aseguradora'),
    ('unique_agente_aseg', 'UNIQUE(agente_id, aseguradora_id)',
     'Un agente solo puede registrarse una vez por aseguradora'),
]
```
Campos: `agente_id` (M2o, cascade), `aseguradora_id` (M2o, restrict), `clave_agente` (Char), `estado` (Selection), `fecha_licencia` (Date).

#### `models/product_template.py`
Extiende `product.template`. Campos nuevos:
- `bca_es_producto_seguro`: Boolean
- `bca_aseguradora_id`: Many2one res.partner, domain aseguradoras
- `bca_ramo`: Selection `[('vida','Vida'),('gmm','GMM'),('autos','Autos'),('danos','Daños')]`
- `bca_temporalidad_anios`: Integer
- `bca_es_capitalizable`: Boolean
- `bca_nombre_archivo_aseguradora`: Char

#### `models/conducto.py`
Modelo `bca.conducto` (sin mail.thread):
- `name`, `codigo_archivo`, `aseguradora_id`, `activo`
- `_sql_constraints`: `UNIQUE(codigo_archivo, aseguradora_id)`

#### `models/factor_pca.py`
Modelo `bca.factor.pca` hereda `mail.thread`:
- Todos los campos de Arquitectura §2.3.3
- `factor`, `vigencia_desde`, `vigencia_hasta`, `activo` con `tracking=True` (corrección M2)

**Checklist Etapa 1:**
- [ ] `res.partner` se abre sin error en Odoo con los nuevos campos visibles
- [ ] Constraint agente→promotoría funciona
- [ ] Constraint SQL de `res.partner.agente.aseguradora` rechaza duplicados
- [ ] Producto se puede marcar como producto de seguro

---

### Etapa 2 — Modelos core de negocio
**Tiempo estimado:** 6–8 horas  
**Reglas de negocio cubiertas:** R-POL-01 a R-POL-07, R-PCA-01

#### `models/poliza.py`
Modelo `bca.poliza`, hereda `mail.thread, mail.activity.mixin`:
- Todos los campos de Arquitectura §2.3.1
- `promotoria_id`: computed **sin store**, implementar `_search_promotoria_id()` para filtrabilidad (corrección C2)
- `_sql_constraints`: `UNIQUE(name, aseguradora_id)` (R-POL-01)
- Métodos:
  - `action_confirmar()`: borrador→activa, llama `_generar_plan_pagos()`
  - `_generar_plan_pagos()`: genera N recibos según periodicidad; no ejecutar si ya hay pagados (R-POL-05)
  - `action_cancelar()`: pasa a cancelada
  - `_compute_pagado_hasta(self)`: computed `store=True` dependiente de `recibo_ids`. Actualiza `pagado_hasta` basado en la máxima fecha de los recibos pagados. (C1)
  - `cambiar_agente(nuevo_agente, motivo)`: único punto para cambiar agente; crea registro en `bca.poliza.cambio.agente` (M4)

#### `models/poliza_cambio_agente.py`
Modelo `bca.poliza.cambio.agente` (readonly, inmutable):
- Campos de Arquitectura §2.3.4b
- Todos los campos `readonly=True`

#### `models/recibo.py`
Modelo `bca.recibo`, hereda `mail.thread`:
- Campos de Arquitectura §2.3.2 (incluyendo `agente_id` y `promotoria_id`)
- `pca_aplicada` y `factor_aplicado` con `tracking=True`
- `write()`: si `estado='pagado'`, bloquear escritura de `pca_aplicada` y `factor_aplicado`, permitiendo si `self.env.su` o en proceso de cancelación.
- `action_registrar_pago(vals)`: **Validar precondiciones antes de ejecutar** (`fecha_pago`, `prima_neta`). Congelar PCA, `agente_id` y `promotoria_id` desde la póliza. (No es necesario llamar update en la póliza si es computed).
- `action_cancelar_pago()`: solo directores; requiere chequeo explícito de grupo.
- `_calcular_pca()`: delega al calculador de la aseguradora
- `_sql_constraints`: `UNIQUE(poliza_id, numero_recibo)`

#### `models/bitacora.py`
Modelos `bca.bitacora.importacion` y `bca.bitacora.linea`:
- `write()` y `unlink()` lanzan `UserError` solo si `not self.env.su` (para permitir purga por sistema/admin).

**Checklist Etapa 2:**
- [ ] Crear póliza → confirmar → genera N recibos correctamente
- [ ] Intentar editar `pagado_hasta` directamente → ValidationError
- [ ] Pagar recibo → PCA se congela → write() sobre `pca_aplicada` lanza UserError
- [ ] Registrar pago con `prima_neta` vacía → UserError antes de congelar nada
- [ ] Registrar pago avanza `pagado_hasta` (el computed se recalcula solo)
- [ ] Cancelar ese recibo → `pagado_hasta` retrocede (el computed se recalcula solo)
- [ ] Segunda póliza con mismo número + aseguradora → constraint SQL rechaza

---

### Etapa 3 — Modelos de integración Odoo
**Tiempo estimado:** 2–3 horas

#### `models/hr_applicant.py`
- Agrega campo `bca_promotoria_destino_id`: Many2one res.partner, domain promotorías
- Método `_bca_crear_partner_desde_contratado()`: al cerrar "Contratado", crear res.partner con tipo correcto

#### `models/crm_lead.py`
- Campos de Arquitectura §2.2.4
- Botón "Generar Póliza desde Lead" (server action)

**Checklist Etapa 3:**
- [ ] Pipeline CRM visible con campos BCA
- [ ] Pipeline de reclutamiento visible con campo `bca_promotoria_destino_id`

---

### Etapa 4 — Seguridad
**Tiempo estimado:** 3–4 horas  
**Archivos:** `security/groups.xml`, `security/ir.model.access.csv`, `security/record_rules.xml`

**Grupos (de menor a mayor privilegio):**
```
group_bca_agente         (independiente — NO en la cadena implied_ids; usuario interno de Odoo)
group_bca_operador
group_bca_lider          implied_ids: operador
group_bca_director_comercial  implied_ids: lider
group_bca_director       implied_ids: director_comercial
```

> **Advertencia de implied_ids (§2.4.3):** `implied_ids` causa membresía acumulativa. El Director pertenece simultáneamente a todos los grupos de la cadena. Las record rules restrictivas de grupos inferiores **le aplican también**. Por eso las rules `[(1,'=',1)]` son obligatorias para todos los grupos no-agente.

> **Si Líder tuviera menos visibilidad que Operador en algún modelo** (hoy no es el caso), no podría estar en su cadena de `implied_ids`. Se necesitaría topología de hermanos con un grupo base común. Verificar si esto aplica antes de implementar.

> **`res.groups` en Odoo 19:** No usar `category_id`. Usar `res.groups.privilege` con `privilege_id` para agrupar grupos en la UI de administración (§2.4.1).

**ACL completa** para todos los modelos propios y modelos puente. Ver Arquitectura §7.2.

**Record rules explícitas** para `bca.poliza` y `bca.recibo` en todos los grupos (A3):
- Agente (usuario interno): domain por `user_ids`
- Otros grupos: domain `[(1,'=',1)]` — obligatorio aunque parezca redundante (ver §2.4.3)

**Checklist Etapa 4:**
- [ ] Módulo instala con security sin errores de XML ID
- [ ] Agente (usuario interno) solo ve sus propias pólizas en backend de `bca_core`
- [ ] Agente puede abrir CRM y ver/crear sus leads sin restricción
- [ ] Operador no puede cancelar recibos
- [ ] `ir.model.access.csv` cubre todos los modelos nuevos (verificar con `odoo-bin --test-enable`)

---

### Etapa 5 — Datos iniciales
**Tiempo estimado:** 2–3 horas

| Archivo | Registros |
|---|---|
| `data/sequences.xml` | Secuencia `bca.recibo` |
| `data/partner_categories.xml` | Aseguradora, Promotoría BCA, Agente BCA, Contratante BCA |
| `data/product_categories.xml` | Seguros / MetLife / Vida, Seguros / MetLife / GMM |
| `data/hr_jobs.xml` | Captación de Promotoría, Reclutamiento de Agente |
| `data/aseguradoras_iniciales.xml` | MetLife (METLIFE), Qualitas (QUALITAS) como `res.partner` |
| `data/conductos_metlife.xml` | 7 conductos MetLife (Vida: 2, GMM: 5) |
| `data/factores_metlife_2026.xml` | 17 registros: 14 Vida (7 productos × 2 monedas) + 3 GMM |

**Checklist Etapa 5:**
- [ ] Datos cargados correctamente al instalar
- [ ] Factores MetLife 2026 visibles en UI con vigencia correcta
- [ ] Conductos con `codigo_archivo` exacto del CSV

---

### Etapa 6 — Parsers de cobranza
**Tiempo estimado:** 4–5 horas  
**Patrón:** Strategy (ver Arquitectura §4)

#### `parsers/base.py`
```python
class ParserBase:
    aseguradora_codigo = None
    ramo = None
    columnas_requeridas = []   # OBLIGATORIO en subclases

    def __init__(self, env, bitacora): ...
    def validar_estructura(self, df): ...    # implementación completa en base (A5)
    def filtrar_filas(self, df): ...
    def procesar_fila(self, env, fila): ... # env = self.env del wizard (conservar lang y tz) (C4)
    def normalizar_monto(self, valor): ...
    def normalizar_fecha(self, valor): ...
```

#### `parsers/metlife_lsp.py`
`ParserMetLifeVida`: `columnas_requeridas` con los 13 campos del archivo LSP. Encoding Latin-1.

#### `parsers/metlife_gcaye.py`
`ParserMetLifeGMM`: `columnas_requeridas` del archivo GCAYE. Filtrar anulaciones (R-COB-01).

#### `parsers/qualitas.py`
`ParserQualitas`: placeholder con `columnas_requeridas = []` y `NotImplementedError` en `procesar_fila`.

#### `parsers/__init__.py`
Función `get_parser(aseguradora_codigo, ramo)` con mensaje de error descriptivo (A4).

**Checklist Etapa 6:**
- [ ] `get_parser('METLIFE', 'vida')` retorna `ParserMetLifeVida`
- [ ] `get_parser('DESCONOCIDA', 'vida')` lanza `UserError` con mensaje útil
- [ ] `validar_estructura()` detecta columna faltante antes de procesar ninguna fila
- [ ] Normalización de fechas `DD/MM/YYYY` → `date` funciona
- [ ] Normalización de importes con coma como miles funciona

---

### Etapa 7 — Calculadores de PCA
**Tiempo estimado:** 2–3 horas

#### `calculadores_pca/base.py`
```python
class CalculadorPCABase:
    aseguradora_codigo = None
    def __init__(self, env): ...
    def calcular(self, recibo):
        """Retorna (pca, factor_aplicado, motivo_exclusion)."""
```

#### `calculadores_pca/metlife.py`
`CalculadorPCAMetLife`:
1. Evaluar exclusiones Vida: aportación adicional en capitalizable, cobertura individual de accidentes/invalidez, temporalidad < 10 años
2. Evaluar exclusiones GMM: coaseguro ≤ 5% → PCA = 0
3. Buscar factor en `bca.factor.pca` según dominio (aseguradora, ramo, producto, moneda, coaseguro, deducible)
4. Convertir prima_neta a MXN si es USD vía `res.currency` (M3)
5. PCA = prima_neta_mxn × factor
6. Retornar `(pca, factor, motivo_exclusion)`

**Checklist Etapa 7:**
- [ ] Póliza Vida MXN TempoLife → factor 1.0 aplicado
- [ ] Póliza Vida USD TempoLife → factor 0.8 aplicado + conversión a MXN
- [ ] Póliza Vida capitalizable con aportación adicional → PCA = 0 con motivo
- [ ] Póliza GMM coaseguro ≤ 5% → PCA = 0 con motivo
- [ ] Póliza GMM coaseguro ≥ 10% + deducible ≥ 29,000 → factor 1.2

---

### Etapa 8 — Wizards
**Tiempo estimado:** 4–5 horas

#### `wizards/carga_portafolio.py`
`bca.wizard.carga.portafolio` (TransientModel):
- Campos: `archivo` (Binary), `nombre_archivo`, `aseguradora_id`, `modo` (crear_actualizar / solo_crear)
- Flujo en dos fases (M1):
  1. `action_validar()`: lee Excel con `openpyxl`, verifica hojas `VIDA`/`GMM`/`AUTOS`, columnas, formatos. Si errores → mostrar reporte. Sin tocar BD.
  2. `action_grabar()`: por cada póliza en savepoint independiente. Al terminar, retorna action con reporte.

#### `wizards/cobranza_diaria.py`
`bca.wizard.cobranza.diaria` (TransientModel):
- Campos: `archivo` (Binary), `nombre_archivo`, `aseguradora_id`, `ramo`
- Flujo:
  1. Obtener parser con `get_parser(aseguradora_codigo, ramo)`
  2. Llamar `parser.validar_estructura(df)` — si falla, `UserError` sin crear bitácora (R-COB-09)
  3. Crear `bca.bitacora.importacion`
  4. Loop de filas con patrón de savepoint (C4):
     ```python
     with self.env.cr.savepoint():
         # Mantener el context original (C4)
         resultado = parser.procesar_fila(self.env, fila)
     ```
  5. Cerrar bitácora con totales
  6. Retornar action → vista de la bitácora generada

**Checklist Etapa 8:**
- [ ] CSV de MetLife Vida con 5 filas: 4 válidas + 1 póliza no encontrada → bitácora con 5 líneas
- [ ] Error en fila 3 no detiene proceso (filas 4 y 5 se procesan)
- [ ] Fila con póliza ya pagada → "Sin recibo disponible" en bitácora
- [ ] Archivo sin columna crítica → UserError antes de crear bitácora
- [ ] Portafolio Excel: validar detecta hoja faltante sin tocar BD

---

### Etapa 9 — Reportes SQL (SICs)
**Tiempo estimado:** 3–4 horas

Todos usan `_auto = False`. El método `init()` crea/recrea la vista SQL.
**Patrón crítico:** en el SQL, siempre tomar `agente_id` y `promotoria_id` del `bca_recibo` (inmutabilidad histórica). NO hacer join hacia la póliza actual (C2).

#### Modelos SQL:
| Modelo | Tabla SQL | Filtro base |
|---|---|---|
| `bca.reporte.pca.agente` | `bca_reporte_pca_agente` | `recibo.estado='pagado'` (leer dimensiones desde `bca_recibo`) |
| `bca.reporte.pca.promotoria` | `bca_reporte_pca_promotoria` | Mismo + GROUP BY `recibo.promotoria_id` |
| `bca.reporte.pca.consolidado` | `bca_reporte_pca_consolidado` | Total holding |
| `bca.reporte.estado.cartera` | `bca_reporte_estado_cartera` | Por póliza con clasificación vigente/en_riesgo/caida |

`migrations/1.0.0/post_migrate.py`: script que invoca `init()` de todos los modelos de reporte.

**Checklist Etapa 9:**
- [ ] SIC 1 (por agente) muestra datos correctos tras pagar un recibo
- [ ] SIC 2 (por promotoría) agrupa correctamente
- [ ] Agente en estado prospecto NO aparece en los reportes de PCA
- [ ] `odoo-bin -u bca_core` recrea las SQL views sin error

---

### Etapa 10 — Vistas XML
**Tiempo estimado:** 6–8 horas

**Reglas:**
- Sintaxis Odoo 19: usar `invisible="not bca_es_producto_seguro"` (no `attrs=`)
- Grupos en campos con `groups="bca_core.group_bca_director"` para ocultar por rol
- `statusbar_visible` en campos `estado` de póliza y recibo
- Botones de acción con `confirm="..."` donde sea destructivo
- Smart buttons (contadores en form): siempre `type="object"` con método Python que retorna el action dict — **nunca** `type="action"` con `active_id` en contexto (§2.4.1)
- Vistas search: `<group>` sin atributos — no `expand`, no `string` (§2.4.1)
- Todo `ref` propio: siempre con prefijo `bca_core.` aunque sea en el mismo archivo (§2.4.2)
- Todo `<menuitem>` raíz: **atributo `groups` obligatorio** o no será visible en producción (§2.4.2)
- Herencia de kanban de `crm.lead`: `<xpath expr="//t[@t-name='kanban-box']">` (§2.4.1)

**Menú principal:** `BCA → [Pólizas | Cobranza | Reportes | Configuración]`

**Checklist Etapa 10:**
- [ ] Formulario de póliza abre sin errores de XML
- [ ] Botón "Confirmar" visible solo en estado borrador
- [ ] Campo `pagado_hasta` es readonly en UI (no hay widget de edición)
- [ ] Factor PCA editable solo para directores

---

### Etapa 11 — Pruebas
**Tiempo estimado:** 4–6 horas

| Archivo | Casos de prueba |
|---|---|
| `tests/test_poliza.py` | R-POL-03 (pagado_hasta readonly), R-POL-05 (no regenerar plan con pagados) |
| `tests/test_cobranza_fifo.py` | R-COB-03 (FIFO), R-COB-08 (fila con error no detiene proceso) |
| `tests/test_pca_metlife.py` | R-PCA-01 (congelamiento), exclusiones Vida y GMM, multimoneda |
| `tests/test_inmutabilidad.py` | Bitácora no editable, `pagado_hasta` solo vía método dedicado |
| `tests/test_record_rules.py` | Agente (usuario interno) solo ve sus pólizas; director comercial; visibilidad cross-promotoría |

**Ejecutar:** `odoo-bin --test-enable --test-tags bca_core -i bca_core`

**Checklist Etapa 11:**
- [ ] Todos los tests pasan en verde
- [ ] Sin warnings de deprecación de Odoo 19

---

## 5. Checklist de instalación y verificación final

```
INFRAESTRUCTURA
[ ] odoo-bin -i bca_core → instala sin errores
[ ] odoo-bin -u bca_core → actualiza sin errores, SQL views recreadas
[ ] Datos iniciales cargados (aseguradoras, conductos, factores MetLife 2026)

REGLAS DE NEGOCIO CRÍTICAS
[ ] pagado_hasta no editable manualmente (campo computed)
[ ] PCA congelada al pago; write() sobre pca_aplicada lanza UserError
[ ] FIFO aplicado: segundo recibo no se paga antes que el primero
[ ] CSV con columna faltante → UserError sin crear bitácora
[ ] Error en fila CSV → rollback de fila, proceso continúa

SEGURIDAD
[ ] Agente (usuario interno) solo ve sus pólizas en bca_core — puede usar CRM libremente
[ ] Operador no puede cancelar recibos
[ ] Director Comercial puede editar factores y cancelar recibos
[ ] Director General tiene acceso completo
[ ] Bitácora de importación: write() y unlink() lanzan UserError a menos que sea Admin (`env.su`)

REPORTES
[ ] SIC 1 cuadra contra cálculo manual en datos de prueba
[ ] Agente prospecto no aparece en SIC 1
[ ] Cambio de agente en póliza → SIC refleja promotoría correcta (old vs new)
```

---

## 6. Notas para sesiones siguientes

> **Antes de continuar en una sesión nueva:**
> 1. Lee `Specs/Decisiones.md` si existe (decisiones tomadas en sesiones anteriores)
> 2. Lee `Specs/Changelog.md` para saber dónde quedó la última sesión
> 3. Revisa el checklist de la última etapa completada para confirmar estado
> 4. **No asumir** que porque una etapa está marcada como iniciada está completa — verifica el checklist de esa etapa

> **Al cerrar una sesión:**
> 1. Actualiza `Specs/Changelog.md` con: qué se hizo, qué archivos se crearon/modificados, qué está pendiente, qué decisiones nuevas se tomaron
> 2. Si se tomó una decisión técnica relevante, agrégala a `Specs/Decisiones.md`
> 3. Marca en este plan las tareas completadas con `[x]`

---

*Plan elaborado por Hábitat Digital — Desarrollo activo. Cualquier desviación de la arquitectura documentada debe validarse con el arquitecto antes de implementarse.*
