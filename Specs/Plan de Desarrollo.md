# Plan de Desarrollo — Módulo `BCA_Seguros`

**Proyecto:** Grupo BCA — Gestión de Pólizas, Cobranza y PCA  
**Plataforma:** Odoo Community 19  
**Autor:** Hábitat Digital  
**Audiencia:** Desarrolladores humanos y agentes IA  
**Estado:** Documento vivo — actualizar al cerrar cada etapa

> **Estructura de `Specs/`:** los documentos están organizados por fase.
> Transversales (gobiernan todo el módulo) en la raíz: `Plan de Desarrollo.md`,
> `Decisiones.md`, `Changelog.md`, `Bugs.md`, `TESTS_COVERAGE.md`.
> Fase 1 (cobranza/pólizas/cartera + tablero) en `Specs/01-cobranza-polizas/`.
> Reclutamiento de agentes en `Specs/02-reclutamiento/`.
>
> **Documentos de referencia obligatorios (leer antes de este plan):**
> 1. `Specs/01-cobranza-polizas/Arquitectura_BCA_Seguros.md` — modelo de datos, reglas, correcciones arquitectónicas
> 2. `Specs/01-cobranza-polizas/Logica de Negocios_BCA_Seguros.md` — qué debe hacer el negocio y por qué
> 3. `Specs/Decisiones.md` (cuando exista) — decisiones ya tomadas y sus razones

---

## 1. Cómo usar este documento

### Para un humano desarrollador
Lee las secciones 2–4 para entender el alcance y las reglas. Luego avanza etapa por etapa en orden: cada etapa lista los archivos a crear, las reglas de negocio que implementa y un checklist de verificación antes de continuar.

### Para un agente IA
Sigue este protocolo antes de generar cualquier código:

1. **Lee `Specs/01-cobranza-polizas/Arquitectura_BCA_Seguros.md` completo.** Contiene las definiciones exactas de campos, tipos, constraints y 13 correcciones críticas (C1–M5). No asumir nada que no esté ahí.
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
- Dentro de `BCA_Seguros`, las **record rules** los restringen a ver solo sus propias pólizas y recibos — no se necesita ninguna ruta portal para esto.
- **No existe un portal de agente** (`/my/polizas`). El módulo `portal` no es una dependencia de `BCA_Seguros`.
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
| A1 | `post_init_hook_bca_seguros` en `__init__.py` raíz; carpeta `migrations/1.0.0/` |
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
| Todo `ref` propio del módulo **siempre con prefijo** `BCA_Seguros.`, incluso dentro del mismo archivo | `ValueError: External ID not found` al cargar datos |
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
| `BCA_Seguros/__manifest__.py` | `name`, `version='19.0.1.0.0'`, `depends`, `data`, `post_init_hook='post_init_hook_bca_seguros'` |
| `BCA_Seguros/__init__.py` | Imports de subpaquetes + función `post_init_hook_bca_seguros` |
| `BCA_Seguros/models/__init__.py` | Imports de todos los archivos de models/ |
| `BCA_Seguros/wizards/__init__.py` | Imports |
| `BCA_Seguros/parsers/__init__.py` | `get_parser()` (esqueleto inicial) |
| `BCA_Seguros/calculadores_pca/__init__.py` | `CALCULADOR_REGISTRY` |
| `BCA_Seguros/reports/__init__.py` | Imports |
| `BCA_Seguros/tests/__init__.py` | Import |
| `BCA_Seguros/static/description/icon.png` | Ícono (placeholder PNG 16x16) |

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
    'post_init_hook': 'post_init_hook_bca_seguros',
    'installable': True,
    'application': True,
    # Declarar SIEMPRE librerías externas. Sin esto Odoo instala el módulo
    # aunque la lib no exista y falla en runtime con ImportError (ver §2.4.7)
    'external_dependencies': {
        'python': ['openpyxl'],  # verificar si ya viene incluida en Odoo 19
    },
}
```

**`post_init_hook_bca_seguros`** en `__init__.py` raíz:
```python
def post_init_hook_bca_seguros(env):
    """Inicializar SQL views de reportes al instalar/actualizar."""
    for model_name in [
        'bca.reporte.pca.agente',
        'bca.reporte.pca.promotoria',
        'bca.reporte.pca.consolidado',
        'bca.reporte.estado.cartera',
    ]:
        env[model_name].init()
```

**Checklist Etapa 0:** ✅ Completado 2026-05-26
- [x] `odoo-bin -i BCA_Seguros` instala sin errores (verificado en sandbox_bca1)
- [x] No hay imports circulares
- [x] `post_init_hook` definido y referenciado en manifest

---

### Etapa 1 — Modelos base
**Tiempo estimado:** 4–6 horas  
**Reglas de negocio cubiertas:** R-ORG-01, R-ORG-02 (parcial)

#### `models/res_partner.py`
Extiende `res.partner`. Campos nuevos (todos con `index=True` donde aplica):
- `bca_tipo`: Selection `[('holding','Holding BCA'),('aseguradora','Aseguradora'),('promotoria','Promotoría Afiliada'),('agente','Agente'),('contratante','Contratante')]`, `index=True`
- `bca_estado_agente`: Selection `[('prospecto','Prospecto'),('clave_arranque','Clave de Arranque'),('clave_definitiva','Clave Definitiva')]`, **computed `store=True`** + `index=True` — rollup del estado de carrera (mejor estado en cualquier aseguradora) derivado del modelo puente. No editable a mano. Solo `clave_definitiva` computa PCA. Ver `Decisiones.md` D-07.
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
Campos: `agente_id` (M2o, cascade), `aseguradora_id` (M2o, restrict), `clave_agente` (Char), `estado` (Selection `[('prospecto','Prospecto'),('clave_arranque','Clave de Arranque'),('clave_definitiva','Clave Definitiva')]`, default `prospecto` — **fuente de verdad** del estado de carrera por aseguradora; solo `clave_definitiva` computa PCA), `fecha_licencia` (Date).

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
- [ ] Agente (usuario interno) solo ve sus propias pólizas en backend de `BCA_Seguros`
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

**Checklist Etapa 5:** ✅ Completado 2026-05-27 (commit pendiente; verificación sandbox pendiente)
- [x] Datos cargados correctamente al instalar (estructura completa, deploy sandbox pendiente)
- [x] Factores MetLife 2026 visibles en UI con vigencia correcta (vinculados a productos vía `producto_ids`)
- [⚠] Conductos con `codigo_archivo` exacto del CSV — los 4 reales están creados pero `codigo_archivo` es placeholder hasta confirmar contra CSV real en E6
- [x] Productos MetLife (11 Vida + 2 GMM) creados — **agregado al alcance original de E5** porque los factores los referencian
- [x] Operador puede crear conductos y productos desde UI (ACL `bca.conducto` RWC + `implied_ids product.group_product_manager`)

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

### Etapa 7 — Calculadores de PCA  ✅ COMPLETADA (2026-06-05, commit `b187215`)
**Tiempo estimado:** 2–3 horas

> **Cierre:** calculador MetLife Vida + GMM implementado. Verificado en `sandbox_bca1`:
> **116 tests, 0 failures, 0 errors**. Migración `19.0.1.2.0` aplicada en el deploy.
> Decisiones de multimoneda y alcance de exclusiones en `Decisiones.md` D-08. Ver
> también `Changelog.md` (sesión 2026-06-05 Etapa 7).

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

> **Nota D-08:** el paso 4 se resolvió como "factor por moneda de la póliza → resultado
> convertido a MXN" (conserva el haircut USD). La exclusión "cobertura individual de
> accidentes/invalidez" del paso 1 quedó **fuera de alcance** (sin campo estructurado).

**Checklist Etapa 7:**
- [x] Póliza Vida MXN TempoLife → factor 1.0 aplicado — test `test_vida_mxn_factor_1`
- [x] Póliza Vida USD TempoLife → factor 0.8 aplicado + conversión a MXN — test `test_vida_usd_factor_080_convertido_a_mxn`
- [x] Póliza Vida capitalizable con aportación adicional → PCA = 0 con motivo — test `test_vida_excluye_aportacion_adicional`
- [x] Póliza GMM coaseguro ≤ 5% → PCA = 0 con motivo — test `test_gmm_excluye_coaseguro_5`
- [x] Póliza GMM coaseguro ≥ 10% + deducible ≥ 29,000 → factor 1.2 — test `test_gmm_coaseguro10_deducible_alto_factor_120`

---

### Etapa 8 — Wizards
**Tiempo estimado:** 4–5 horas
**Estado:** ✅ Completada y **verificada en sandbox_bca1** (2026-06-05, **143 tests, 0 failures**,
commit `adb05a3`) — **Carga de Portafolio** (v`19.0.1.3.0`) + **Cobranza Diaria** (v`19.0.1.4.0`). Decisión asociada: **D-09**
(`estatus_pago` computed). El deploy de portafolio destapó **BUG-016** (PCA congelada en 0
por `fecha_pago=False` al calcular), corregido en `recibo.py` (commit `38736b7`).
Cobranza Diaria: flujo de **una sola fase** (la bitácora es el reporte auditable),
selector de ramo limitado a **Vida/GMM** (Autos/Qualitas placeholder). Ver `Changelog.md`.

#### `wizards/carga_portafolio.py`
`bca.wizard.carga.portafolio` (TransientModel):
- Campos: `archivo` (Binary), `nombre_archivo`, `aseguradora_id`, `modo` (crear_actualizar / solo_crear)
- Flujo en dos fases (M1):
  1. `action_validar()`: lee Excel con `openpyxl`, verifica hojas `VIDA`/`GMM`/`AUTOS`, columnas, formatos. Si errores → mostrar reporte. Sin tocar BD.
  2. `action_grabar()`: por cada póliza en savepoint independiente. Al terminar, retorna action con reporte.

#### `wizards/cobranza_diaria.py` ✅ implementado
`bca.wizard.cobranza.diaria` (TransientModel):
- Campos: `archivo` (Binary), `nombre_archivo`, `aseguradora_id`, `ramo` (Vida/GMM — sin Autos)
- Flujo de **una sola fase** (`action_procesar`):
  1. Decodificar CSV (Latin-1, R-GLOB-01) → `csv.DictReader` (sniff de delimitador)
  2. `get_parser(aseguradora.bca_codigo_aseguradora, ramo)`
  3. `parser_cls.validar_estructura(fieldnames)` (ahora `@classmethod`) — si falla, `UserError`
     **antes** de crear la bitácora (R-COB-09)
  4. Crear `bca.bitacora.importacion`; `parser.filtrar_filas()` (GMM omite anulados, R-COB-01)
  5. Loop `parser.procesar_fila()` (savepoint por fila vive en el parser, R-COB-08) → crea
     `bca.bitacora.linea` y acumula contadores + PCA
  6. Escribir totales y retornar action → form de la bitácora generada

**Checklist Etapa 8:**
- [x] CSV de MetLife Vida con 5 filas: 4 válidas + 1 póliza no encontrada → bitácora con 5 líneas — test `test_cinco_filas_cuatro_validas_una_no_encontrada`
- [x] Error en fila 3 no detiene proceso (filas 4 y 5 se procesan) — test `test_error_en_fila_no_detiene_proceso`
- [x] Fila con póliza ya pagada → "Sin recibo disponible" en bitácora — test `test_poliza_sin_recibo_pendiente`
- [x] Archivo sin columna crítica → UserError antes de crear bitácora — test `test_columna_faltante_no_crea_bitacora`
- [x] FIFO: pagos consecutivos aplican recibos en orden ascendente — test `test_fifo_aplica_en_orden`
- [x] GMM: fila anulada se omite y suma a `anulaciones_ignoradas` (R-COB-01) — test `test_gmm_anulado_se_omite`
- [x] Portafolio Excel: validar detecta hoja faltante sin tocar BD — test `test_validar_sin_hoja_soportada`
- [x] Portafolio: validar detecta columna crítica faltante (fail-fast, 0 pólizas) — test `test_validar_columna_faltante`
- [x] Portafolio: grabar crea pólizas VIDA + GMM con agente/contratante/producto resueltos — test `test_crea_vida_y_gmm`
- [x] Portafolio: "Pagado Hasta" genera solo recibos posteriores al corte — test `test_pagado_hasta_genera_solo_recibos_posteriores`
- [x] Portafolio: beneficiarios VIDA + dependientes GMM en `bca.poliza.beneficiario` — test `test_beneficiarios_vida_y_dependientes_gmm`
- [x] Portafolio: fila con error no detiene el proceso (savepoint por póliza) — test `test_fila_con_error_no_detiene_proceso`

---

### Etapa 9 — Reportes SQL (SICs)  ✅ COMPLETADA (2026-06-29, v`19.0.1.5.0`)
**Tiempo estimado:** 3–4 horas

> **Cierre:** 4 vistas SQL reales (`_auto=False` + `init()` con `SQL()` builder de v19, patrón
> `sale.report` de Odoo core) con pivot/graph/list/search y menú. Foto inmutable del recibo
> (C2), solo Clave Definitiva computa (R-PCA-03, por aseguradora), PCA en MXN (D-08), estado de
> cartera caída/en_riesgo/vigente. Se reorganizó el menú (Pólizas/Cobranza/Reportes/
> Configuración) y se ocultó "Registrar Pago" al agente. Tests en `test_reportes.py` +
> `test_views_xml`. Migración `19.0.1.5.0`. Ver `Changelog.md` (sesión 2026-06-29).

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
- [x] SIC 1 (por agente) muestra datos correctos tras pagar un recibo — test `test_sic1_agente_muestra_pca`
- [x] SIC 2 (por promotoría) agrupa correctamente — test `test_sic2_promotoria_agrega_dos_agentes`
- [x] Agente sin Clave Definitiva NO aparece en los reportes de PCA — test `test_sic1_agente_no_definitiva_no_aparece`
- [x] `odoo-bin -u BCA_Seguros` recrea las SQL views sin error — migración `19.0.1.5.0/post-migrate.py` + post_init_hook
- [x] Inmutabilidad: cambiar agente tras el pago no mueve la PCA reportada — test `test_reporte_usa_foto_inmutable_del_recibo`
- [x] SIC 4 (estado de cartera) clasifica caída/en_riesgo/vigente — tests `test_sic4_*`

---

### Etapa 10 — Vistas XML
**Tiempo estimado:** 6–8 horas

**Reglas:**
- Sintaxis Odoo 19: usar `invisible="not bca_es_producto_seguro"` (no `attrs=`)
- Grupos en campos con `groups="BCA_Seguros.group_bca_director"` para ocultar por rol
- `statusbar_visible` en campos `estado` de póliza y recibo
- Botones de acción con `confirm="..."` donde sea destructivo
- Smart buttons (contadores en form): siempre `type="object"` con método Python que retorna el action dict — **nunca** `type="action"` con `active_id` en contexto (§2.4.1)
- Vistas search: `<group>` sin atributos — no `expand`, no `string` (§2.4.1)
- Todo `ref` propio: siempre con prefijo `BCA_Seguros.` aunque sea en el mismo archivo (§2.4.2)
- Todo `<menuitem>` raíz: **atributo `groups` obligatorio** o no será visible en producción (§2.4.2)
- Herencia de kanban de `crm.lead`: `<xpath expr="//t[@t-name='kanban-box']">` (§2.4.1)

**Menú principal:** `BCA → [Pólizas | Cobranza | Reportes | Configuración]`

**Checklist Etapa 10:** ✅ Completado 2026-05-27 (verificación sandbox pendiente)
- [x] Formulario de póliza abre sin errores de XML — test `test_poliza_views`
- [x] Botón "Confirmar" visible solo en estado borrador — `invisible="estado != 'borrador'"`
- [x] Campo `pagado_hasta` es readonly en UI — atributo `readonly="1"`
- [x] Factor PCA editable solo para directores — restricción vía ACL (Director Comercial+ tiene perm_write)
- [x] Skeleton wizards (E8) y reportes (E9) cargan sin error
- [x] Menú raíz BCA con jerarquía Pólizas | Cobranza | Reportes | Configuración
- [x] 12 tests nuevos validan parseo XML de todas las vistas + actions del menú
- [x] Campo `parent_id` visible y editable cuando `bca_tipo in (promotoria, agente)` (hotfix 2026-05-27 d)

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

**Ejecutar:** `odoo-bin --test-enable --test-tags BCA_Seguros -i BCA_Seguros`

**Checklist Etapa 11:** _(cierre formal 2026-06-29 · `v19.0.1.6.1`)_
- [x] Suite estabilizada y reproducible — fixtures inmunes al *drift* de conductos
  (D-13); cobertura inventariada en `Specs/TESTS_COVERAGE.md` (14 archivos / ~127 tests,
  0 skip/xfail). Alcance de cierre: DoD mínimo (sin tests nuevos; huecos documentados).
- [x] Sin warnings de deprecación de Odoo 19 — escaneo estático limpio (usa `<list>`,
  sin `attrs=`/`states=`/`@api.one`/`name_get(`).
- [ ] Verde `0 failed, 0 error(s)` confirmado en sandbox (corrida del usuario; ver
  Changelog 2026-06-29 Etapa 11).

---

### Etapa 12 — Reclutamiento y Habilitación de Agentes  ✅ COMPLETA (`19.0.1.7.4`, 2026-07-02)
**Tiempo estimado:** 16–22 horas (5 fases)
**Documento director:** `Specs/02-reclutamiento/spec-etapa-12-reclutamiento-bca-v1.md`
**Specs de negocio:** `Specs/02-reclutamiento/` (BDD v1.3, SDD v1.1, análisis HU/TT, HU+criterios)
**Reglas de negocio cubiertas:** R-PCA-03 (solo Clave Definitiva computa), Car. 2/8/10 (Id interno, carrera por aseguradora).

> **Objetivo:** integrar el ciclo del candidato con `hr_recruitment` (embudo `hr.applicant`) hasta
> la **cédula emitida**, que alimenta el puente `res.partner.agente.aseguradora` en
> `estado='clave_arranque'` (NO computa PCA). Identidad por **Id interno = Nombre+RFC+CURP**;
> conversión idempotente en el override de `write()`. La promoción a `clave_definitiva` es
> proceso interno posterior (SI-4), **fuera de alcance**.
>
> **Decisiones de negocio (SIs):** SI-1 visibilidad **por reclutadora** (`user_id`); SI-2 promotor
> **solo destino + notificación**; SI-3 evento **campo de texto** (`bca_evento`); SI-Sede **seed con
> lista del usuario**; SI-4 paso a definitiva **fuera de alcance**. Decisiones a registrar: D-14…D-18.

**Fases (commit + bump por fase):**

| Fase | Versión | Nombre | HUs |
|---|---|---|---|
| A | `19.0.1.7.0` | Cimientos: `bca.sede` + campos identificación/perfil + embudo 12 etapas | 1.0, 1.1, 1.2 |
| B | `19.0.1.7.1` | PDA + compuerta de riesgo (L1) | 1.3 |
| C | `19.0.1.7.2` | **Núcleo:** conversión en Cédula Emitida (L2) + RFC/CURP + puente `clave_arranque` | 1.4, 1.5 |
| D | `19.0.1.7.3` | Automatizaciones (L3/L5/L6) + motivos de rechazo + SICs/reportes | 1.7–1.9, 2.1, 3.1 |
| E | `19.0.1.7.4` | Visibilidad por reclutadora (record rules) | 1.6 |

**Archivos clave:** `models/bca_sede.py` (nuevo), `models/hr_applicant.py` (campos + L1 + L2/conversión),
`models/res_partner.py` (`bca_curp`), `models/res_partner_agente_aseg.py` (puente, sin cambios de esquema),
`data/hr_recruitment_stages.xml` · `data/bca_sedes_iniciales.xml` · `data/base_automation_reclutamiento.xml` ·
`data/hr_refuse_reasons.xml` (nuevos), `security/groups.xml` + `record_rules.xml` (Fase E), `__manifest__.py` (bumps).

**Checklist Etapa 12:**
- [x] **Fase A** (2026-07-02, `19.0.1.7.0`): `bca.sede` CRUD; 12 etapas + "Alta Interna" como datos del módulo; `hired_stage=True` en cédula/alta; form sin error XML; sin campos duplicados (género/ramo reusan selección; RFC=`vat` diferido a Fase C por confirmar). Sandbox local `Devlocal`: 136 tests, 0 failed.
- [x] **Fase B** (2026-07-02, `19.0.1.7.1`): PDA riesgo (nivel no_ideal/baja) ⇒ actividad al promotor; avanzar más allá de "Evaluación PDA" sin VoBo ⇒ `ValidationError`. Local `Devlocal`: 140 tests, 0 failed.
- [x] **Fase C** (2026-07-02, `19.0.1.7.2`): no se llega a hired sin los 5 datos; conversión crea partner+puente(`clave_arranque`)+empleado idempotente por Id interno (RFC=`bca_rfc`→`partner.vat`, CURP=`bca_curp`); agente reutilizado en 2ª aseguradora; recién habilitado en `clave_arranque` NO computa PCA; Alta Interna no crea agente/puente. Local `Devlocal`: 145 tests, 0 failed.
- [x] **Fase D** (2026-07-02, `19.0.1.7.3`): 2 motivos de rechazo seed; aviso L6 (base.automation on_stage_set); pivote SIC por sede/reclutadora/ramo/evento/etapa. L3/L5 diferidos a SOP (necesitan trigger por fecha + etapa Stand by). Local `Devlocal`: 148 tests, 0 failed.
- [x] **Fase E** (2026-07-02, `19.0.1.7.4`): reclutadora ve solo `user_id==uid`; Director ve todo (`[(1,'=',1)]` + ACL lectura); grupos hermanos (reclutadora/capital humano). Separación por `job_id` = refinamiento futuro. Local `Devlocal`: 150 tests, 0 failed.
- [ ] **SI-Sede pendiente:** rellenar `data/bca_sedes_iniciales.xml` con la lista oficial (seed placeholder Matriz/CDMX/MTY por ahora).
- [x] Verde `0 failed, 0 error(s)` en Docker local (`Devlocal`) por fase A–E.

---

## 5. Checklist de instalación y verificación final

```
INFRAESTRUCTURA
[ ] odoo-bin -i BCA_Seguros → instala sin errores
[ ] odoo-bin -u BCA_Seguros → actualiza sin errores, SQL views recreadas
[ ] Datos iniciales cargados (aseguradoras, conductos, factores MetLife 2026)

REGLAS DE NEGOCIO CRÍTICAS
[ ] pagado_hasta no editable manualmente (campo computed)
[ ] PCA congelada al pago; write() sobre pca_aplicada lanza UserError
[ ] FIFO aplicado: segundo recibo no se paga antes que el primero
[ ] CSV con columna faltante → UserError sin crear bitácora
[ ] Error en fila CSV → rollback de fila, proceso continúa

SEGURIDAD
[ ] Agente (usuario interno) solo ve sus pólizas en BCA_Seguros — puede usar CRM libremente
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
