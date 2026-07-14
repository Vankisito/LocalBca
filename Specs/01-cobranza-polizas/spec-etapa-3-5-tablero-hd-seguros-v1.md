---
titulo: Spec Etapa 3.5 — Tablero de Inicio hd_seguros
fecha: 2026-06-29
autor: Hábitat Digital
version: v1.0
area: 5c. Recursos Tecnológicos
---

# Spec Etapa 3.5 — Tablero de Inicio `hd_seguros`

> **Para:** Claude Code
> **Módulo:** `hd_seguros` (Odoo 19 Community) · Rama `develop`
> **Tipo:** Nueva funcionalidad — pantalla de inicio del módulo (client action OWL).
> **Fuente de verdad visual:** el prototipo generado por Claude Design (ver §2).

---

## 1. Objetivo

Construir el **tablero de inicio** del módulo: la pantalla a la que aterriza el usuario al entrar a HD Seguros. Resume el ciclo de vida de la póliza en seis tarjetas con cifras agregadas, mini-gráficas y accesos directos a las vistas filtradas.

Esta etapa también **resuelve el pendiente v3.1** (visibilidad del menú principal sin modo debug): el tablero será la acción por defecto del menú raíz, con su grupo base correctamente declarado.

---

## 2. Fuente de verdad visual (prototipo)

El diseño visual (layout, colores, tipografía, disposición de tarjetas y mini-gráficas) lo define la **imagen del prototipo de Claude Design**.

- Guardar la imagen del prototipo en el repo, sugerido en: `hd_seguros/hd_seguros/specs/assets/tablero-prototipo.png`.
- El brief que originó el prototipo es `brief-prototipo-tablero-hd-seguros-v1.md`.
- Cualquier duda de **forma** (espaciado, color, posición) se resuelve mirando el prototipo. Cualquier duda de **dato** (qué número y de dónde sale) se resuelve con este spec (§6 y §7).

---

## 3. Reglas no negociables

Estas reglas son obligatorias y prevalecen sobre cualquier conveniencia de implementación:

1. **El tablero SOLO lee y agrega.** Nunca escribe en ningún modelo. Jamás toca `pagado_hasta`, `pca_valor` ni `factor_aplicado`. Son números derivados.
2. **La lógica de negocio vive en el backend.** El componente OWL solo dibuja lo que `get_dashboard_data()` ya resolvió. El front no calcula PCA, ni vencimientos, ni nada de negocio.
3. **Seguridad por ORM.** Las cifras salen de `search_count` / `read_group`, que respetan las record rules existentes. No usar SQL crudo para esquivar permisos.
4. **Convenciones Odoo 19 del proyecto:**
   - Todo `ref` en XML lleva el prefijo `hd_seguros.`.
   - Smart buttons / acciones de tarjeta: `type="object"` con método Python. Nunca `type="action"` con `%(xml_id)d` ni `active_id` en context (DEC-026).
   - Elementos `<group>` dentro de `<search>` sin atributos (DEC-027).
   - `from __future__ import annotations` y type hints en el modelo nuevo.
5. **Foco único.** Implementar por fases (§9), una a la vez.

---

## 4. Arquitectura técnica

### 4.1 Backend — agregador
Archivo nuevo: `models/dashboard.py`

```python
from __future__ import annotations
from odoo import api, fields, models


class HdSegurosDashboard(models.AbstractModel):
    _name = 'hd.seguros.dashboard'
    _description = 'Agregador de datos del Tablero HD Seguros'

    @api.model
    def get_dashboard_data(self) -> dict:
        """Devuelve TODAS las cifras del tablero ya calculadas.
        Solo lectura/agregación. No escribe en ningún modelo.
        Estructura de retorno: ver §6 (contrato de datos).
        """
        ...
```

- Registrar el archivo en `models/__init__.py`.
- Por ser `AbstractModel` no requiere reglas en `ir.model.access.csv`. El método se invoca por RPC desde OWL.

### 4.2 Frontend — componente OWL
Carpeta nueva: `static/src/dashboard/`

- `dashboard.js` — componente OWL que en `onWillStart` llama a `get_dashboard_data()` vía `this.orm.call('hd.seguros.dashboard', 'get_dashboard_data', [])`.
- `dashboard.xml` — plantilla OWL con las seis tarjetas (estructura del prototipo).
- `dashboard.scss` — estilos y paleta de marca.
- Registrar el componente como `client action` con `registry.category("actions").add("hd_seguros_dashboard", Dashboard)`.

### 4.3 Mini-gráficas
- Usar **Chart.js**, ya empaquetado en Odoo 19 (`import { loadJS } from "@web/core/assets"` o el wrapper disponible). **No** agregar dependencias externas.
- Tarjetas con gráfica: Cobranza (tendencia semanal), PCA (tendencia mensual), Cartera y Agentes (barras de reparto).

### 4.4 Acción y menú
Archivo: `views/dashboard_views.xml` (o `views/menuitems.xml`)

```xml
<record id="action_dashboard" model="ir.actions.client">
    <field name="name">Tablero</field>
    <field name="tag">hd_seguros_dashboard</field>
</record>
```

- El `menuitem` raíz de HD Seguros usa `action="hd_seguros.action_dashboard"` como destino por defecto.
- **Fix v3.1:** declarar el grupo base (`hd_seguros.group_user`) en el menú raíz para que sea visible sin modo debug.

### 4.5 Manifest
- Declarar los assets en `web.assets_backend`:
  ```python
  'assets': {
      'web.assets_backend': [
          'hd_seguros/static/src/dashboard/**/*',
      ],
  },
  ```

---

## 5. Decisión técnica a registrar antes de codificar

**DEC-028 — `prima_total` con `store=True` para agregación.**
Para sumar `prima_total` con `read_group` (tarjeta de Cobranza) conviene volverlo `store=True`. Es seguro: es un `compute` determinista que depende solo de campos ya almacenados (`prima_neta + recargos + gastos_expedicion + impuestos`), no introduce mutabilidad de negocio.

- **Opción A (recomendada):** `prima_total` pasa a `store=True`. Registrar DEC-028 en `decisions.md`.
- **Opción B (sin tocar modelo):** sumar los cuatro componentes dentro de la consulta del agregador.

Elegir A salvo indicación contraria. No proceder sin registrar la decisión.

---

## 6. Contrato de datos — retorno de `get_dashboard_data()`

`get_dashboard_data()` debe devolver exactamente esta estructura (claves estables; el front depende de ellas):

```json
{
  "moneda": "MXN",
  "cartera": {
    "activas": 0,
    "suma_asegurada": 0.0,
    "borrador": 0,
    "vencidas": 0,
    "por_ramo": { "vida": 0, "gmm": 0, "autos": 0 }
  },
  "cobranza": {
    "pendientes_num": 0,
    "pendientes_monto": 0.0,
    "vencidos_num": 0,
    "vencidos_monto": 0.0,
    "cobrado_mes": 0.0,
    "proximo_fifo": { "poliza": "", "fecha_fin": "" },
    "tendencia_semanal": [0, 0, 0, 0, 0, 0]
  },
  "pca": {
    "acumulada_anio": 0.0,
    "del_mes": 0.0,
    "computables": 0,
    "exclusiones": 0,
    "factores_cargados": 0,
    "factores_esperados": 17,
    "tendencia_mensual": [0,0,0,0,0,0,0,0,0,0,0,0]
  },
  "vigencia": {
    "al_dia": 0,
    "por_caer": 0,
    "sin_cobertura": 0
  },
  "importaciones": {
    "ultima_fecha": "",
    "ultimo_archivo": "",
    "aplicadas": 0,
    "no_encontradas": 0,
    "sin_recibo": 0,
    "anuladas": 0
  },
  "agentes": {
    "con_licencia": 0,
    "prospectos": 0,
    "pca_por_promotoria": [
      { "promotoria": "", "pca": 0.0 }
    ]
  }
}
```

---

## 7. Mapeo tarjeta → campos → consulta

> `hoy = fields.Date.context_today(self)`. Filtrar siempre por estado explícito (`draft` / `paid`), nunca por "distinto de cancelado".

### Tarjeta 1 — Cartera de Pólizas · modelo `hd.seguros.poliza`
| Dato | Campo / Consulta |
|---|---|
| `activas` | `search_count([('state','=','active')])` |
| `suma_asegurada` | `read_group([('state','=','active')], ['suma_asegurada:sum'], [])` |
| `borrador` | `search_count([('state','=','draft')])` |
| `vencidas` | `search_count([('state','=','lapsed')])` |
| `por_ramo` | `read_group([('state','=','active')], ['id'], ['producto_tipo'])` |

### Tarjeta 2 — Cobranza Diaria · modelo `hd.seguros.recibo`
| Dato | Campo / Consulta |
|---|---|
| `pendientes_num` / `pendientes_monto` | `read_group([('state','=','draft')], ['prima_total:sum'], [])` |
| `vencidos_num` / `vencidos_monto` | `[('state','=','draft'), ('fecha_fin','<',hoy)]` → count + `prima_total:sum` |
| `cobrado_mes` | `[('state','=','paid'), ('date_payment','>=',inicio_mes), ('date_payment','<=',fin_mes)]` → `prima_total:sum` |
| `proximo_fifo` | `search([('state','=','draft')], order='fecha_inicio asc', limit=1)` → `poliza_id.name`, `fecha_fin` |
| `tendencia_semanal` | `read_group` de `paid` por semana (`date_payment`), últimas 6 semanas, sum `prima_total` |

### Tarjeta 3 — Prima Computable (PCA) · modelo `hd.seguros.recibo` + `hd.factor.ajuste`
| Dato | Campo / Consulta |
|---|---|
| `acumulada_anio` | `[('state','=','paid'), ('date_payment','>=',inicio_anio)]` → `pca_valor:sum` |
| `del_mes` | `[('state','=','paid'), ('date_payment','>=',inicio_mes)]` → `pca_valor:sum` |
| `computables` | `search_count([('state','=','paid'), ('factor_aplicado','>',0)])` |
| `exclusiones` | `search_count([('state','=','paid'), ('factor_aplicado','=',0)])` |
| `factores_cargados` | `self.env['hd.factor.ajuste'].search_count([])` |
| `factores_esperados` | constante `17` (tabla 2026) |
| `tendencia_mensual` | `read_group` de `paid` por mes (`date_payment`), año en curso, sum `pca_valor` |

### Tarjeta 4 — Vigencia y Cobertura · modelo `hd.seguros.poliza`
> Considerar solo pólizas `state='active'`.
| Dato | Consulta |
|---|---|
| `al_dia` | `[('state','=','active'), ('pagado_hasta','>=',hoy)]` |
| `por_caer` | `[('state','=','active'), ('pagado_hasta','>=',hoy), ('pagado_hasta','<=',hoy+15d)]` |
| `sin_cobertura` | `[('state','=','active'), '|', ('pagado_hasta','=',False), ('pagado_hasta','<',hoy)]` |

### Tarjeta 5 — Últimas Importaciones · modelo `hd.seguros.log.importacion`
| Dato | Consulta |
|---|---|
| último registro | `search([], order='create_date desc', limit=1)` |
| `ultima_fecha` / `ultimo_archivo` | del registro (`create_date` / nombre de archivo) |
| `aplicadas` / `no_encontradas` / `sin_recibo` / `anuladas` | contadores del registro (`resultado_*`) |

> Confirmar los nombres exactos de los campos contadores en `models/log_importacion.py` antes de mapear.

### Tarjeta 6 — Productividad de Agentes · modelo `hd.seguros.agente` + `hd.seguros.recibo`
| Dato | Consulta |
|---|---|
| `con_licencia` | `search_count([('state','=','licencia')])` |
| `prospectos` | `search_count([('state','=','prospecto')])` |
| `pca_por_promotoria` | PCA de recibos `paid` agrupada por promotoría del agente |

> **Nota de implementación:** `read_group` no atraviesa dos saltos (`recibo → poliza → agente.promotoria`) de forma directa. Opciones: (a) campo `related` almacenado `promotoria` en `hd.seguros.recibo` para agrupar, o (b) agregación manual en Python. Documentar la elección en `decisions.md`.

---

## 8. Navegación (clic en una cifra)

Cada cifra clickeable abre la vista lista/kanban del modelo correspondiente con el dominio ya filtrado, vía método Python `type="object"`:

- Cartera → pólizas filtradas por estado/ramo.
- Cobranza → recibos `draft` (o `draft` vencidos).
- PCA → recibos `paid` del periodo.
- Vigencia → pólizas por bucket de `pagado_hasta`.
- Importaciones → bitácora `hd.seguros.log.importacion`.
- Agentes → `hd.seguros.agente`.

---

## 9. Fases de implementación (una a la vez)

| Fase | Entregable | Estado |
|---|---|---|
| A | DEC-028 registrada + `get_dashboard_data()` con test unitario | 🔲 |
| B | Componente OWL con las 6 tarjetas + navegación (sin gráficas) | 🔲 |
| C | Mini-gráficas Chart.js (Cobranza, PCA, Cartera, Agentes) | 🔲 |
| D | `menuitem` por defecto + fix de visibilidad v3.1 | 🔲 |

---

## 10. Criterios de aceptación

- Al entrar al módulo, el tablero carga sin modo debug y muestra las seis tarjetas.
- Las cifras coinciden con las vistas lista equivalentes (validación cruzada).
- Un `group_user` ve solo agregados de lo que puede leer (sin fuga por permisos).
- Ningún flujo del tablero escribe en `pagado_hasta`, `pca_valor` o `factor_aplicado`.
- El look corresponde al prototipo de Claude Design (§2).

---

## 11. Protocolo de cierre (obligatorio)

Al concluir cada fase:

- Actualizar `changelog.md` con las tareas concluidas de la fase.
- Actualizar `decisions.md` con DEC-028 (`store=True`), la decisión de promotoría (§7) y una DEC nueva que documente el patrón de **client action OWL** para el tablero.
- Commits siguiendo convención: `feat:`, `fix:`, `refactor:`, `docs:`, `chore:`.

---

## 12. Pendientes / dudas a confirmar antes de empezar

- Nombres exactos de los campos contadores en `hd.seguros.log.importacion`.
- Confirmar valor del estado "cancelado" en `hd.seguros.recibo` (para excluirlo si aplica).
- Decisión promotoría: campo `related` almacenado vs. agregación manual (§7, Tarjeta 6).
