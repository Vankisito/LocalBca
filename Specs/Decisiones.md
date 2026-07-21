# Decisiones Técnicas — Módulo BCA_Seguros

> Registrar aquí toda decisión técnica o de diseño no obvia. Incluir: qué se decidió, por qué, quién lo aprobó y cuándo. Esto evita repetir conversaciones ya resueltas.

---

## D-01 — Nombre técnico del módulo: `BCA_Seguros`

**Fecha:** 2026-05-26
**Decidido por:** Rafael Viera (usuario)

**Decisión:** El nombre técnico del módulo (nombre de carpeta que Odoo usa como identificador interno) es `BCA_Seguros`.

**Consecuencias:**

- Todos los XML external IDs usan prefijo `BCA_Seguros.` (ej: `BCA_Seguros.group_bca_agente`)
- Todos los `ref=` en XML usan `BCA_Seguros.algo`
- Los atributos `groups=` en vistas usan `groups="BCA_Seguros.group_bca_..."`
- La función de hook se llama `post_init_hook_bca_seguros`
- Los nombres de modelo ORM (`_name = 'bca.poliza'`) son **independientes** del nombre del módulo y no cambian

**Nota:** La versión anterior de las specs usaba `bca_core` como prefijo. Fue corregido en `Specs/Plan de Desarrollo.md` en la sesión 2026-05-26.

---

## D-02 — Agentes son usuarios internos de Odoo (no portal)

**Fecha:** Sesión previa (antes de 2026-05-26)
**Referencia:** `Plan de Desarrollo.md §2.0`

**Decisión:** Los agentes inician sesión en el **backend** de Odoo (`share=False`). No son usuarios portal.

**Consecuencias:**

- No existe `/my/polizas` ni ninguna ruta portal
- El módulo `portal` no es dependencia de `BCA_Seguros`
- El grupo se llama `group_bca_agente` (no `group_bca_agente_portal`)
- Las record rules del backend los restringen a ver solo sus pólizas

---

## D-03 — `promotoria_id` en póliza es computed puro (sin `store=True`)

**Fecha:** Sesión previa
**Referencia:** Corrección C2 en `Arquitectura_BCA_Seguros.md §13`

**Decisión:** `promotoria_id` en `bca.poliza` es un campo computed sin almacenamiento. Se implementa `_search_promotoria_id()` para mantener filtrabilidad.

**Razón:** Evitar desincronización si el agente cambia de promotoría. El valor siempre se deriva del `parent_id` del agente en tiempo real.

---

## D-04 — Asegurado: nuevo `bca_tipo='asegurado'` con domain permisivo

**Fecha:** 2026-05-28
**Decidido por:** Rafael Viera (usuario) vía AskUserQuestion

**Decisión:** La persona cuya vida está asegurada se modela como `res.partner`. Se agrega el valor `asegurado` a `bca_tipo` y un campo `bca.poliza.asegurado_id`. El domain de `asegurado_id` es **permisivo**: `['|', ('bca_tipo','=','asegurado'), ('bca_tipo','=','contratante')]`.

**Razón:** `bca_tipo` es de **valor único** por contacto. El contratante suele ser su propio asegurado (caso más común); si el domain exigiera estrictamente `bca_tipo='asegurado'`, no se podría apuntar al contratante. El tipo `asegurado` queda para personas que SOLO son asegurados.

---

## D-05 — Beneficiarios: modelo ligado a `res.partner`, validación 100% al confirmar

**Fecha:** 2026-05-28
**Decidido por:** Rafael Viera (usuario) vía AskUserQuestion

**Decisión:** Modelo `bca.poliza.beneficiario` (One2many en la póliza) con `beneficiario_id` → `res.partner`, `parentesco` (Selection) y `porcentaje` (Float). **NO** se fuerza un `bca_tipo` en el beneficiario. La suma de porcentajes debe ser 100%, validada **al confirmar** la póliza (`_validar_porcentaje_beneficiarios` desde `action_confirmar`), **no** como `@api.constrains`.

**Razón:**

- Ligarlo a `res.partner` permite reutilizar datos del contacto y, a futuro, CRM/dirección. Un beneficiario suele ser cónyuge/hijo que podría ser contratante en otra póliza → por eso NO se fuerza `bca_tipo` (incompatible con el valor único, ver D-04).
- Validar al confirmar (y no en cada `write`) permite capturar la póliza en borrador con datos parciales sin que la constraint estorbe.

**Consecuencia de seguridad:** Como el modelo es hijo de la póliza y el agente lo ve en el One2many del form, lleva su propio bloque de `ir.rule` (agente solo de SUS pólizas vía `poliza_id.agente_id.user_ids`; resto `[(1,'=',1)]` por la regla A3 de `implied_ids`).

---

## D-06 — `estatus_pago` es declarativo, no fuente de verdad operativa  ⚠️ SUPERADA por D-09

**Fecha:** 2026-05-28
**Decidido por:** Rafael Viera (usuario) vía AskUserQuestion
**Estado:** Superada por **D-09** (Etapa 8): `estatus_pago` deja de ser un campo capturable
y pasa a **computed** derivado de la fecha pagada. El espíritu de D-06 (que la verdad
operativa la da `pagado_hasta`) se mantiene y se refuerza.

**Decisión:** Se agrega `bca.poliza.estatus_pago` (Selection capturable) para reflejar el "Estatus de Pago" del layout. NO reemplaza ni alimenta la lógica de vigencia de pago: esa la determina el computed `pagado_hasta` a partir de los recibos.

**Razón:** El layout trae un estatus de pago declarativo de la aseguradora. Mantenerlo como dato informativo evita acoplar la cobranza operativa (FIFO + recibos) a un campo que puede quedar desincronizado. Valores tentativos (al corriente / vencido / suspendido) **pendientes de confirmar** con el catálogo real de MetLife.

---

## D-07 — Nomenclatura de carrera del agente: 3 estados, fuente en el puente, rollup computed en el contacto

**Fecha:** 2026-06-05
**Decidido por:** Rafael Viera (usuario) vía AskUserQuestion

**Decisión:** El estado de carrera del agente tiene **tres niveles** —`prospecto` → `clave_arranque` → `clave_definitiva`— y es **por aseguradora**.

- **Fuente de verdad:** `res.partner.agente.aseguradora.estado` (modelo puente), con `default='prospecto'`. Un agente puede tener estado distinto por aseguradora (Definitiva en MetLife, Arranque en Qualitas).
- **`res.partner.bca_estado_agente`** pasa a ser un **rollup computed `store=True`** del puente: el mejor estado alcanzado en cualquier aseguradora (Definitiva > Arranque > Prospecto; sin claves = Prospecto). **No editable a mano.** Solo para filtros/listas/visual.
- **PCA:** solo `clave_definitiva` computa, y se filtra por el estado del **puente** de esa aseguradora (`aa.estado='clave_definitiva'`), **no** por `res.partner.bca_estado_agente`. Filtrar por el rollup sería un bug (corregido en `Arquitectura §6.1`).
- Se **eliminó** `res.partner.bca_fecha_licencia` (redundante): la fecha vive por aseguradora en `res.partner.agente.aseguradora.fecha_licencia`.
- **Reclutamiento (`hr_recruitment`) es dueño del ciclo.** Vía automated actions sobre `hr.applicant`: crea el partner agente en Prospecto, crea el registro puente con `clave_arranque` al aprobar examen, y actualiza a `clave_definitiva` cuando la aseguradora confirma (la transición Arranque→Definitiva también la automatiza Reclutamiento). El contacto refleja el rollup + un **smart button** a `hr.applicant`; el detalle fino de exámenes/etapas vive en Reclutamiento.

**Razón:**

- El puente debe existir igual (claves múltiples + constraint SQL por aseguradora, ver C3). Guardar además un estado manual en el partner duplicaría la fuente → desync. Hacer el partner un rollup computed elimina el desync (misma filosofía que C2/D-03).
- El estado es genuinamente por aseguradora, así que la PCA debe leerlo del puente; un campo global del partner no puede expresarlo correctamente.
- Reclutamiento ya lleva la prospección/exámenes; automatizar la alimentación del puente evita que Operaciones de Seguros tenga que mover estados a mano.

**Pendiente de implementación:** campos destino en `hr.applicant` (`bca_aseguradora_destino_id`, `bca_clave_arranque`), las automated actions del ciclo completo y el smart button. Hoy `hr_applicant.py` solo crea el partner al cerrar "Contratado". El rollup y el puente ya soportan los tres estados.

---

## D-08 — PCA multimoneda: factor por moneda de la póliza, resultado convertido a MXN

**Fecha:** 2026-06-05
**Decidido por:** Rafael Viera (usuario) vía AskUserQuestion (Etapa 7)

**Decisión:** El cálculo de PCA (`calculadores_pca/metlife.py`) expresa la PCA **siempre en MXN**.

- **Selección de factor por moneda de la póliza.** En Vida la tabla de factores distingue MXN vs USD (ej. TempoLife 100% MXN / 80% USD). Se selecciona la fila cuyo `currency_id` coincide con `poliza.currency_id` — la póliza USD recibe su factor USD (conserva el "haircut" del 80%). GMM no discrimina por moneda (los 3 factores son MXN).
- **Conversión a MXN al final.** `pca_ccy = prima_neta × factor` (en moneda de la póliza); si la póliza no es MXN, se convierte vía `res.currency._convert(pca_ccy, MXN, company, fecha_pago)`. Matemáticamente equivalente a "convertir antes del factor" (resuelve la corrección M3 de Arquitectura §5.2, que queda obsoleta en su lectura "siempre factor MXN").
- **Campo nuevo `bca.recibo.pca_currency_id`** (default MXN), al que apunta `currency_field` de `pca_aplicada`. Necesario porque la PCA está en MXN aunque la póliza (y `recibo.currency_id`) puedan ser USD. Se congela al pago junto con `pca_aplicada`/`factor_aplicado` (R-PCA-01).
- **Exclusión "coberturas individuales de accidentes/invalidez": fuera de alcance E7.** No existe campo estructurado (solo el texto libre `coberturas_adicionales`); queda como ajuste manual futuro. E7 implementa solo las exclusiones con campo: aportación adicional y temporalidad < 10 (Vida); coaseguro ≤ 5% (GMM).

**Razón:**

- Conservar el factor por moneda mantiene la semántica económica (las pólizas USD sí valen menos PCA), y aun así el resultado queda homogéneo en MXN para reportes y liquidaciones consolidadas.
- Pinear la PCA a su propia moneda (`pca_currency_id`) evita mostrar montos ambiguos cuando la póliza es USD.
- La exclusión por coberturas individuales no es auto-evaluable desde texto libre; forzarla sería adivinar. Mejor dejarla explícita como pendiente que producir PCA incorrecta.

**Hallazgo asociado (deuda de datos):** `bca.poliza.coaseguro` se guarda como **fracción** (0.10 = 10%) mientras que `bca.factor.pca.coaseguro_min` del seed GMM usa **puntos porcentuales** (10.0). El calculador normaliza (`coaseguro_pct = poliza.coaseguro × 100`) antes de comparar. Registrado en `Bugs.md`.

---

## D-09 — `estatus_pago` computed: una sola fuente de verdad para la salud de pago (supera D-06)

**Fecha:** 2026-06-05
**Decidido por:** Rafael Viera (usuario) vía AskUserQuestion (Etapa 8)

**Contexto:** `bca.poliza` tenía dos ejes que parecían redundantes y colisionaban en la palabra "vencida/vencido": `estado` (ciclo de vida contractual: borrador/activa/vencida/cancelada) y `estatus_pago` (salud de pago: al_corriente/vencido/suspendido, editable a mano por D-06). Además `estatus_pago` podía contradecir a `pagado_hasta`, que el propio modelo declara como la verdad operativa.

**Decisión:** `estatus_pago` deja de ser capturable y pasa a **computed `store=True`** (`_compute_estatus_pago`):

- **Derivación:** la fecha de pago efectiva = `pagado_hasta` (recibos pagados) y, en su defecto, `pagado_hasta_inicial` (declarado en la carga de portafolio). Si `fecha + gracia >= hoy` → `al_corriente`, si no → `vencido`. Estados `borrador`/`cancelada` → vacío.
- **`pago_suspendido`** (Boolean, nuevo): único override manual, ya que `suspendido` no es derivable de una fecha.
- **Período de gracia** configurable: `ir.config_parameter` `bca_seguros.dias_gracia_pago` (default 30), semilla en `data/config_parameters.xml`.
- **Aging por tiempo:** como el cómputo depende de "hoy" y es `store=True`, un `ir.cron` diario (`data/cron_estatus_pago.xml` → `_cron_refrescar_estatus_pago`) recalcula las pólizas activas. Deja lista la clasificación de cartera de la Etapa 9.
- **`pagado_hasta_inicial`** (Date, nuevo): dato declarado del layout. `pagado_hasta` (computed desde recibos) sigue siendo la verdad operativa; este campo solo siembra el arranque mientras no haya recibos pagados, y ancla la generación del plan (solo recibos posteriores al corte).
- **Colisión de etiqueta:** la etiqueta de `estado='vencida'` se renombró a **"Expirada"** (la clave `vencida` no cambia → sin migración).

**Razón:**

- Un solo eje de verdad para el pago elimina el riesgo de desincronización que D-06 aceptaba como "informativo". El estatus nunca contradice a los recibos.
- `estado` (lifecycle) y `estatus_pago` (pago) son ejes ortogonales legítimos; el problema era solo el solapamiento semántico y la doble fuente, no la existencia de ambos.
- El `pagado_hasta_inicial` permite cargar pólizas en vigor sin inventar recibos históricos pagados (decisión del usuario en Etapa 8: generar solo recibos posteriores al corte).

**Impacto:** `bca.poliza.estatus_pago` ahora `readonly` en la vista (badge). El layout "Estatus de Pago" ya no se almacena verbatim: "suspendido" → `pago_suspendido=True`; al_corriente/vencido los deriva el computed desde `pagado_hasta_inicial`. Tests que asignaban `estatus_pago` a mano se ajustaron.

---

## D-10 — `prima_total` NO requiere `store=True` para el Tablero (revisa spec DEC-028)

**Fecha:** 2026-06-29
**Contexto:** La spec Etapa 3.5 (§5) proponía volver `bca.recibo.prima_total` a `store=True` (DEC-028) para poder sumarlo con `_read_group` en la tarjeta de Cobranza.

**Decisión:** No se modifica el modelo. `bca.recibo.prima_total` **ya es un campo `Monetary` almacenado** (no computed): se captura en `action_registrar_pago` y vive en BD. La agregación del tablero se hace directamente con `_read_group([...], [], ['prima_total:sum'])`. DEC-028 queda como innecesaria.

**Razón:** El supuesto de la spec (genérica `hd_seguros`) no aplica al modelo real; tocar el campo sería un cambio sin beneficio y con riesgo de migración.

---

## D-11 — PCA por promotoría en el Tablero usa la foto inmutable del recibo

**Fecha:** 2026-06-29
**Contexto:** La spec (§7, Tarjeta 6) advertía que `_read_group` no atraviesa `recibo → poliza → agente.promotoria` y proponía un campo `related` almacenado o agregación manual en Python.

**Decisión:** Se agrupa directamente por `bca.recibo.promotoria_id`, que **ya está almacenado** como foto inmutable al pago (asignado en `action_registrar_pago`, el mismo campo que consumen los reportes PCA de E9). No se crea ningún campo nuevo ni se hace agregación manual.

**Razón:** El salto a dos niveles que temía la spec no existe en el modelo real; la dimensión ya está materializada en el recibo, así que la agregación es un `_read_group` de un solo nivel y además respeta la semántica histórica (no se mueve si el agente de la póliza cambia).

---

## D-12 — Tablero de Inicio: client action OWL sobre `AbstractModel` agregador solo-lectura

**Fecha:** 2026-06-29
**Contexto:** Etapa 3.5 introduce la primera pantalla OWL del módulo (pantalla de inicio).

**Decisión:** Patrón del tablero:

- **Backend:** `models.AbstractModel` `bca.dashboard` con `get_dashboard_data()` (devuelve el contrato §6 ya calculado) y `action_open(key)` (devuelve el `act_window` filtrado por tarjeta). Solo lee/agrega vía `search_count`/`_read_group` (respetan record rules); nunca escribe. Por ser `AbstractModel` no requiere ACL.
- **Frontend:** componente OWL en `static/src/dashboard/`, registrado en `registry.category("actions")` como `bca_dashboard`; consume los datos por RPC en `onWillStart`. Mini-gráficas con Chart.js empaquetado en Odoo 19 (sin dependencias externas).
- **Navegación:** los clics llaman `action_open()` (método Python que retorna el action dict) — **cumple DEC-026**: nada de `type="action"` + `active_id` en contexto.
- **Acción y menú:** `ir.actions.client` `action_dashboard`; el `menuitem` raíz la usa como acción por defecto (resuelve el pendiente de visibilidad). Visible a los 5 grupos BCA; los agregados se filtran por las record rules de cada rol.

**Razón:** Mantiene toda la lógica de negocio en backend y la seguridad en el ORM; el front solo dibuja. Reutiliza la foto inmutable del recibo y las acciones de lista existentes por dominio.

## D-13 — Los fixtures crean su propio conducto (no dependen del seed) — inmunidad al drift

**Fecha:** 2026-06-29
**Contexto:** Etapa 11 (cierre de la suite). 3 tests (parsers Vida/GMM y wizard de cobranza) fallaban en sandbox con `marca='advertencia'` (conducto no-match). Hardcodeaban el literal `'AGENTE_DIRECTO'` / `env.ref(seed)` apuntando al conducto semilla `BCA_Seguros.conducto_metlife_agente_directo`. `ParserBase._resolver_conducto` busca por **`codigo_archivo` + `aseguradora_id` + `activo=True`**; el conducto semilla no es estable entre entornos (su `codigo_archivo` cambia por diseño y su aseguradora/`activo` pueden diferir en sandbox), así que el match se rompía y `recibo.conducto_id` quedaba vacío.

**Decisión:** Ningún fixture debe depender del conducto semilla (ni por literal ni por `env.ref`). Cada fixture **crea su propio conducto** ligado a la aseguradora del test, con un `codigo_archivo` único, y alimenta ese código:

```python
# setUpClass
cls.conducto = cls.env['bca.conducto'].create({
    'name': 'Conducto Test ...',
    'codigo_archivo': 'TEST_COND_...',
    'aseguradora_id': cls.aseguradora.id,
})
# fila
'conducto': self.conducto.codigo_archivo,
```

Es el mismo patrón que ya usaban `test_pca_metlife`, `test_reportes`, `test_poliza_vida` y `test_poliza_gmm`. El caso negativo deliberado (`'CONDUCTO_INVENTADO'` en `test_metlife_vida_conducto_no_match_continua`) sí usa un literal a propósito y permanece.

**Razón:** El match del parser depende de 3 condiciones (código + aseguradora + activo); sincronizar sólo el código contra el seed no basta porque la aseguradora o el flag pueden haber drifteado. Crear el conducto en el propio test garantiza las 3 condiciones de forma determinista, sin acoplarse a datos semilla mutables. No es regresión funcional. Ver `Specs/TESTS_COVERAGE.md §4`.

---

> **Etapa 12 — Reclutamiento (D-14…D-18).** Decisiones acordadas en planificación
> (2026-06-30); se asientan en código durante las Fases A–E. Documento director:
> `Specs/02-reclutamiento/spec-etapa-12-reclutamiento-bca-v1.md`.

## D-14 — El puente al emitir cédula nace en `clave_arranque`, no en `clave_definitiva`

**Fecha:** 2026-06-30 (Etapa 12, planificación)
**Contexto:** Al "Cédula Emitida" (`hired`), la conversión crea/alimenta el puente `res.partner.agente.aseguradora`. La versión previa del flujo de reclutamiento proponía `clave_definitiva`.

**Decisión:** El puente se crea con `estado='clave_arranque'`. El agente recién habilitado **NO computa PCA ni comisiones**.

**Razón:** Solo `clave_definitiva` computa PCA (`BDD_BCA_Seguros.md` Car. 8 y 10; R-PCA-03). El reclutamiento entrega al agente habilitado pero en arranque; asentar definitiva activaría comisiones indebidas. Red de seguridad: `test_agente_clave_arranque_no_computa_pca` (cruza con reportes E9). La promoción a definitiva es proceso interno posterior (ver SI-4, fuera de alcance).

---

## D-15 — Idempotencia de la conversión por Id interno (Nombre+RFC+CURP), nunca por clave

**Fecha:** 2026-06-30 (Etapa 12, planificación)
**Contexto:** La conversión en cédula debe crear o reutilizar el `res.partner` agente sin duplicar cuando el mismo agente se habilita en otra aseguradora/promotoría.

**Decisión:** La identidad del agente es el **Id interno = Nombre + RFC (`vat`) + CURP (`bca_curp`)**. La búsqueda de idempotencia es por `vat`+`bca_curp` (+ nombre normalizado), **nunca** por la clave de agente. Si el agente ya existe, se reutiliza y solo se agrega la clave de la nueva aseguradora al puente. Se agrega `bca_curp` (Char, `index=True`) a `res.partner`.

**Razón:** Norma de identidad PCA (Car. 2): la clave varía por aseguradora y no identifica a la persona. Los UNIQUE del puente (`aseguradora_id,clave_agente` y `agente_id,aseguradora_id`) protegen contra duplicados; capturar `IntegrityError` y reutilizar.

---

## D-16 — "Evento" se modela como campo de texto (`bca_evento`), no como modelo

**Fecha:** 2026-06-30 (Etapa 12, planificación · resuelve SI-3)
**Contexto:** El reporte de efectividad por fuente/campaña/evento (HU-3.1) necesita una dimensión "evento".

**Decisión:** `bca_evento` (Char/Selection) en `hr.applicant`; los reportes agrupan por ese campo. No se crea el modelo relacional `bca.evento`.

**Razón:** Suficiente para arrancar con reporte pivote; menor superficie. El catálogo relacional (con inversión por evento) queda como mejora futura si BCA lo solicita — migración Char→M2o aislada.

---

## D-17 — La conversión vive en el override de `write()`, no en `base.automation`

**Fecha:** 2026-06-30 (Etapa 12, planificación)
**Contexto:** Al cambiar `hr.applicant` a la etapa "Cédula Emitida" debe crearse partner agente + puente + empleado.

**Decisión:** La lógica de conversión permanece en el **override de `write()`** (Python) de `hr.applicant` — `_bca_crear_partner_desde_contratado()`. `base.automation` se reserva exclusivamente para avisos/recordatorios (L3/L5/L6).

**Razón:** La conversión crea varios registros relacionados que deben ser **atómicos e idempotentes**; un automated action declarativo no garantiza el control transaccional ni la idempotencia por Id interno. Mantiene la lógica de negocio en el modelo.

---

## D-18 — Visibilidad del embudo de reclutamiento por reclutadora asignada

**Fecha:** 2026-06-30 (Etapa 12, planificación · resuelve SI-1)
**Contexto:** Hay que definir qué candidatos (`hr.applicant`) ve cada rol.

**Decisión:** Record rule sobre `hr.applicant`: la reclutadora ve sus candidatos (`user_id == uid`); Director Comercial y Director ven todo (regla `[(1,'=',1)]` explícita, A3). El **Promotor** es solo destino + notificación (SI-2), no opera el embudo. Los grupos nuevos (`group_bca_reclutadora`, `group_bca_capital_humano`) se declaran como **hermanos**, fuera de la cadena `implied_ids` de los 5 grupos existentes.

**Razón:** Modelo de visibilidad por responsable, simple y nativo a `hr_recruitment`. Encadenar los grupos por `implied_ids` rompería la semántica de visibilidad no lineal (§2.4.3, corrección A3).

---

## D-19 — Depuración de pestañas Perfil/Origen del postulante (reuso de lo nativo)

**Fecha:** 2026-07-03 (Etapa 12, post-cierre · revisión de UI con el usuario)
**Contexto:** Las pestañas propias "Perfil" y "Origen" que se agregaron en Fase A a `hr.applicant` duplicaban campos nativos o del embudo. El arch nativo v19 tiene la pestaña **"Detalles"** (`application_details`) con Grado (`type_id`), Búsqueda de talentos (`source_id`/`medium_id`/`campaign_id`), Puesto y Paquete salarial.

**Decisión:** Se eliminan ambas pestañas propias y **7 campos**:

- Origen: `bca_evento` (→ `campaign_id` nativo), `bca_referido_por` (→ `source_id`), `bca_contactado`/`bca_entrevistado`/`bca_reagendaciones` (→ embudo de etapas + actividades nativas).
- Perfil: `bca_perfil_academico` (→ `type_id`/Grado nativo), `bca_tiene_cedula_previa` (→ se infiere de la pestaña Habilitación: si tiene cédula, se captura ahí).

Se **conservan y reubican**: `bca_folio_cv` → pestaña Identificación; `bca_ramo`/`bca_perfil_laboral`/`bca_tipo_candidato` → grupo "Perfil BCA" inyectado en la pestaña **Detalles** nativa. Migración `19.0.1.7.5/post-migrate.py` elimina las 7 columnas huérfanas.

**Razón:** Principio "reusar antes que crear" (§2.6). El origen y el nivel académico ya son nativos; el seguimiento de contacto/entrevista es redundante con el `stage_id` (doble fuente de verdad); la cédula previa es un paso manual innecesario. Menos campos, formulario coherente, sin duplicar el estándar de Odoo. Ajusta —sin invalidar— el inventario de campos de Fase A y la decisión D-16 (el "evento" ya no es campo de texto propio; se modela con `campaign_id`).

---

## D-20 — El embudo BCA (Fase A+B) es exclusivo de figuras comerciales; los internos usan el embudo nativo

**Fecha:** 2026-07-03 (Etapa 12, post-cierre · corrección de alcance con el usuario)
**Contexto:** El BDD v1.3 y los specs derivados modelaban el embudo como si los **puestos internos** recorrieran la **Fase A** y cerraran en una etapa BCA "Contratado (Alta Interna)". Además, en código las 12 etapas solo estaban scopeadas a `job_reclutamiento_agente`, dejando fuera a las **promotorías** (`job_captacion_promotoria`) pese a que el BDD dice que "la promotoría sigue el mismo embudo".

**Decisión:** El embudo BCA (Fase A + Fase B, 12 etapas) es **exclusivo de las figuras comerciales** y **compartido** por **Agentes y Promotorías**: las 12 etapas llevan `job_ids = [job_reclutamiento_agente, job_captacion_promotoria]`. Los **puestos internos** (cualquier otro `hr.job`) se reclutan por el **embudo nativo de Odoo** (`hr_recruitment`) y cierran con su etapa hired nativa ("Contract Signed"). Se **retira** la etapa BCA `stage_alta_interna` (migración `19.0.1.7.7/pre-migration.py`, que reasigna candidatos antes de borrarla). El ruteo de conversión sigue siendo **por `job_id`** en `_bca_crear_partner_desde_contratado()` (sin cambios de lógica): agente → habilitación, promotoría → alta de promotoría, cualquier otro job → nada.

**Razón:** Un solo embudo por tipo de puesto, más limpio y fiel al negocio: los internos no tienen Fase A/B ni cédula, así que no deben ver etapas comerciales; y las promotorías, que sí son figuras comerciales, deben compartir el mismo embudo que los agentes. Corrige el error documental (internos en Fase A) y el hueco de código (promotorías fuera del embudo). Bump `19.0.1.7.6` → **`19.0.1.7.7`**.

---

## D-21 — Flujo de conversión en 3 fases + traspaso a Capital Humano nativo

**Fecha:** 2026-07-03 (Etapa 12, correcciones QA con el usuario)
**Contexto:** El QA del embudo pidió separar el proceso en dos frentes (Fase A: reclutamiento; Fase B: capital humano) y repartir la conversión, que hasta ahora ocurría toda de golpe al llegar a la etapa hired "Cédula Emitida" (contacto + clave + empleado en `_bca_crear_partner_desde_contratado()`). También pidió una etapa nueva "Clave Definitiva" y un traspaso de gestión a Capital Humano.

**Decisión:** La conversión se dispara por **cruce de umbral de `sequence`** en el override `write()` (`_bca_procesar_transicion_etapa`, patrón D-13 "nunca por ID"), en 3 fases idempotentes:

1. **Acuerdo de Arranque (seq 6):** crea el contacto `res.partner`. Para el agente exige **Promotoría destino + Sede + RFC + CURP** (identidad idempotente por RFC+CURP, D-15). Además hace el **traspaso Reclutamiento→Capital Humano** con campos **nativos** (sin modelo/campo de "equipo"): la reclutadora se preserva en `interviewer_ids` y `user_id` se reasigna al usuario del `ir.config_parameter` `bca_reclutamiento.capital_humano_user_id` (si no está configurado, solo se avisa en el chatter).
2. **Cédula Emitida (seq 11, hired):** asienta la clave por aseguradora, **siempre** en `clave_arranque` (D-14). La compuerta L2 (5 datos) se mantiene.
3. **Clave Definitiva (seq 13, nueva):** crea el `hr.employee` (exige `bca_clave_definitiva`). **NO** promueve el puente a `clave_definitiva` — eso sigue siendo un proceso interno posterior que sí computa PCA (SI-4). El botón nativo "Create Employee" se oculta hasta esta etapa (campo computado `bca_puede_crear_empleado`).

Se retira `bca_tipo_candidato` (duplicaba el origen nativo `source_id`; `DROP COLUMN`, patrón D-19). Se renombran la etapa "Entrevista"→"Cena" y los puestos a "Promotores"/"Agentes" (empujados en migración por `noupdate="1"`). Se añade validación de **formato** RFC/CURP mexicano (`@api.constrains`), independiente del gate L2 de **presencia**.

**Razón:** El proceso real de negocio es de dos fases con dueños distintos; crear el contacto antes (Acuerdo de Arranque) y el empleado después (Clave Definitiva) refleja esa realidad y habilita el traspaso de responsabilidad en la frontera A/B. Usar `interviewer_ids`/`user_id` nativos evita inventar un modelo de "equipo" y reutiliza las record rules existentes. El cruce por `sequence` (no por hired_stage único) hace el flujo robusto a saltos de etapa y a cada fase idempotente. Reemplaza a `_bca_crear_partner_desde_contratado()`/`_bca_habilitar_agente()`. Bump `19.0.1.7.7` → **`19.0.1.7.8`**.

---

## D-22 — Paridad de identidad (RFC/CURP) entre Agentes y Promotores; el puente sigue exclusivo de Agente

**Fecha:** 2026-07-14
**Contexto:** BUG-001 (`Bugs_2026-06-10.md`) reportó que el puesto "Promotores" (`job_captacion_promotoria`) permitía avanzar hasta "Cédula Emitida" sin RFC ni CURP, mientras "Agentes" (`job_reclutamiento_agente`) sí lo exigía. La causa: `_check_habilitacion_datos` (L2) y la creación del contacto en "Acuerdo de Arranque" (`_bca_crear_partner_agente_basico` vs `_bca_crear_promotoria`) filtraban explícitamente solo por `job_reclutamiento_agente` — decisión de alcance deliberada en su momento (`spec-etapa-12-reclutamiento-bca-v1.md`: "Flujo de Captación de Promotoría... no se modifica en esta etapa"), que el propio SDD (`sdd-reclutamiento-habilitacion-agentes-bca-v1.md §11.2`) dejó como pregunta abierta.

**Decisión:** Se extiende la exigencia de **RFC + CURP** a ambas figuras comerciales:

- `_bca_crear_promotoria()` ahora exige RFC + CURP (igual que `_bca_crear_partner_agente_basico`) antes de crear el contacto en "Acuerdo de Arranque", y los persiste en el partner promotoría (`vat`/`bca_curp`). NO exige Promotoría destino ni Sede (son conceptos de Agente que no aplican a quien crea la promotoría).
- `_check_habilitacion_datos` (L2) ahora aplica a ambos jobs comerciales. `_bca_datos_habilitacion_faltantes()` se parametriza por job: RFC+CURP para ambos; Clave de Arranque, Fecha de Cédula y Aseguradora **solo** para `job_reclutamiento_agente`.
- **NO se extiende** la creación del puente `res.partner.agente.aseguradora` (Fase 2) a Promotores: sigue exclusiva de `job_reclutamiento_agente`. Es un concepto de licencia de agente ante una aseguradora que no aplica a la creación de una promotoría (empresa).

**Razón:** El síntoma reportado es específicamente la falta de bloqueo de identidad (RFC/CURP), no la ausencia del flujo de licenciamiento por aseguradora. Corregir solo la paridad de identidad resuelve el bug sin prejuzgar la pregunta arquitectónica todavía abierta en el SDD §11.2 (si Promotor debe generar puente/clave como un Agente); esa decisión requiere confirmación de negocio aparte. Bump `19.0.1.8.0` → **`19.0.1.8.1`**.

---

## D-23 — `vat` (RFC) se excluye de la sincronización comercial de `res.partner`

**Fecha:** 2026-07-21
**Contexto:** BUG-022 (`Bugs.md`). El core de Odoo sincroniza ciertos campos "comerciales" (entre ellos `vat`) hacia arriba y hacia abajo en la jerarquía de `parent_id` (`_synced_commercial_fields` / `_fields_sync`), asumiendo que `parent_id` representa una relación de subsidiaria legal (razón social matriz-filial). BCA reutiliza `parent_id` para la jerarquía organizacional propia (Holding > Promotoría > Agente), no para subsidiarias legales, y el RFC es un dato personal por agente. El resultado era que, al crear o escribir un registro, el RFC del primer agente procesado se propagaba automáticamente al resto de la promotoría/holding.

**Decisión:** Override de `_synced_commercial_fields()` en `res_partner.py` que retorna la lista del core **sin** `'vat'`.

**Razón:** Es la intervención mínima y específica al síntoma: preserva el resto de la sincronización comercial estándar de Odoo (útil para otros campos que sí tiene sentido heredar) y solo corta la propagación del RFC, que en el modelo de datos de BCA nunca debe compartirse entre contactos de una misma jerarquía. Bump `19.0.1.8.4` → **`19.0.1.8.5`**.

---
