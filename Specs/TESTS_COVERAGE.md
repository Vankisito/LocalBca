# Cobertura de Pruebas — Módulo BCA_Seguros

> Estado de la suite automatizada al cierre de la **Etapa 11 — Pruebas** (`v19.0.1.6.1`).
> Este documento es el artefacto de cierre de la etapa: inventaría la cobertura real,
> reconoce los huecos aceptados y fija convenciones para no reintroducir fragilidad.
>
> **Última actualización:** 2026-07-03 (D-21, `v19.0.1.7.8`): suite total **164 tests, 0 failed**.
> `test_hr_applicant.py` reescrito al flujo de conversión por 3 fases. Mantener sincronizado.

---

## 1. Resumen

- **14 archivos de test**, **~127 métodos**, todos bajo el tag `BCA_Seguros`.
- **0** tests marcados `@skip` / `@expectedFailure`; **0** `TODO`/`FIXME` en la suite.
- Comando de ejecución:
  ```bash
  odoo -d <bd> -u BCA_Seguros --test-enable --test-tags BCA_Seguros --stop-after-init
  ```

| Archivo | Tests | Cubre | Etapa |
|---|---|---|---|
| `test_poliza.py` | 9 | `bca.poliza`: alta, confirmación, plan de recibos, cambio de agente, anualidad | 2 |
| `test_poliza_vida.py` | 7 | Póliza ramo Vida: beneficiarios, conducto, asegurado, demográficos | 2 |
| `test_poliza_gmm.py` | 6 | Póliza ramo GMM: sub-ramo, deducible, coaseguro, IVA, conducto | 2 |
| `test_cobranza_fifo.py` | 10 | Wizard cobranza diaria: FIFO, errores no fatales, plantilla CSV | 8 |
| `test_pca_metlife.py` | 10 | `CalculadorPCAMetLife`: factores ramo/moneda, exclusiones, congelamiento | 7 |
| `test_inmutabilidad.py` | 9 | `bca.recibo`: `pagado_hasta` computed, PCA bloqueada, bitácora inmutable | 2 |
| `test_record_rules.py` | 6 | Acceso por rol: agente/operador/líder/DC/director | 4 |
| `test_hr_applicant.py` | 5 | `hr.applicant` → alta de agente/promotoría, idempotencia | 3 |
| `test_crm_lead.py` | 5 | `crm.lead`: campos `bca_*`, generación de póliza, onchange | 3 |
| `test_parsers.py` | 19 | `ParserRegistry`/`Base`, MetLife Vida/GMM, Qualitas (stub) | 6 |
| `test_carga_portafolio.py` | 16 | Wizard carga portafolio (XLSX): validación, grabado, `estatus_pago` | 5 |
| `test_reportes.py` | 7 | Reportes SQL SIC 1–4 + foto inmutable | 9 |
| `test_dashboard.py` | 5 | `bca.dashboard`: contrato §6, cuadre con `search_count`, no-escritura | 3.5 |
| `test_views_xml.py` | 13 | Validación estática de vistas/acciones/menú/reportes | 10 |

---

## 1.b Cobertura planificada — Etapa 12 (Reclutamiento) 🔲

> Tests **a implementar** durante las Fases A–E de la Etapa 12. Documento director:
> `Specs/02-reclutamiento/spec-etapa-12-reclutamiento-bca-v1.md`. Se incorporan al inventario
> §1 al cerrar cada fase con su conteo real.

| Archivo | Tests previstos | Fase |
|---|---|---|
| `test_bca_sede.py` (nuevo) ✅ | `test_crud_y_rec_name`, `test_archivado`, `test_codigo_unico`, `test_codigo_nulo_permite_varias` | A |
| `test_hr_applicant.py` (ext.) ✅ | `test_embudo_13_etapas_cargadas` (13 etapas, ambos jobs), `test_etapa_entrevista_renombrada_cena`, `test_puestos_renombrados` (Promotores/Agentes), `test_hired_stages_flag` (Clave Definitiva NO hired), `test_campos_identificacion_capturables` (sin bca_tipo_candidato), `test_institucion_educativa_label`, `test_edad_computed_no_almacenada`, `test_no_campos_duplicados` | A |
| `test_hr_applicant.py` (ext.) ✅ | `test_pda_riesgo_computed`, `test_pda_riesgo_crea_actividad_promotor`, `test_pda_avance_sin_vobo_bloquea`, `test_pda_con_vobo_avanza` | B |
| `test_hr_applicant.py` (ext.) ✅ D-21 | **Fase 1 (Acuerdo):** `test_acuerdo_reclutamiento_crea_agente`, `test_acuerdo_captacion_crea_promotoria`, `test_acuerdo_sin_sede_bloquea`, `test_acuerdo_sin_promotoria_destino_bloquea`, `test_acuerdo_sin_rfc_curp_bloquea`, `test_idempotencia_doble_acuerdo`; **traspaso CH:** `test_traspaso_capital_humano_en_acuerdo`, `test_traspaso_sin_parametro_no_reasigna`. **Fase 2 (Cédula):** `test_hired_sin_datos_habilitacion_bloquea`, `test_conversion_crea_puente_clave_arranque`, `test_idempotencia_por_rfc_curp`, `test_job_interno_nativo_no_crea_puente_ni_agente`. **Fase 3 (Clave Definitiva):** `test_empleado_solo_en_clave_definitiva`, `test_clave_definitiva_faltante_bloquea_empleado`, `test_clave_definitiva_no_promueve_pca`. **Formato:** `test_rfc_formato_invalido`, `test_curp_formato_invalido`, `test_rfc_curp_validos_persisten` | C |
| `test_hr_applicant.py` (ext.) ✅ | `test_refuse_reasons_seed`, `test_automation_aviso_etapa_seed`, `test_sic_action_pivote_seed` (L3/L5 diferidos a SOP) | D |
| `test_record_rules.py` (ext.) ✅ | `TestReclutamientoRecordRules`: `test_reclutadora_ve_solo_sus_candidatos`, `test_director_ve_todos_los_candidatos` (separación por job_id → refinamiento futuro) | E |

**Cruce crítico de seguridad PCA:** `test_agente_clave_arranque_no_computa_pca` debe verificar contra
los reportes SQL de E9 que un agente en `clave_arranque` **no** aparece en la PCA (red de seguridad de D-14/F1).

---

## 2. Cobertura fuerte (núcleo de negocio)

Modelos y flujos con tests dedicados y aserciones de comportamiento:

- **`bca.poliza`** y ramos Vida/GMM — alta, confirmación, plan de pagos, cambio de
  agente con historial, avance de anualidad.
- **`bca.recibo`** — registro/cancelación/anulación de pago, `pagado_hasta` computed,
  FIFO, inmutabilidad de PCA tras el pago (M5).
- **`CalculadorPCAMetLife`** — factores por ramo/moneda, exclusiones Vida/GMM,
  conversión a MXN (D-08), congelamiento al pago (R-PCA-01).
- **Parsers** (MetLife LSP/GCAYE) — validación de estructura, normalización,
  tolerancia a fila con error (R-COB-08), anulaciones (R-COB-01).
- **Wizards** de cobranza diaria y carga de portafolio — round-trip de plantillas,
  rollback por fila, columnas faltantes → `UserError`.
- **Reportes SQL** (SIC 1–4) — agregación por agente/promotoría, foto inmutable (C2).
- **Dashboard** — contrato de datos, cuadre con `search_count`, garantía de no-escritura.
- **Vistas XML** — validación estática de formularios/listas/búsquedas/acciones/menú.

---

## 3. Huecos conocidos y aceptados

Cubiertos **indirectamente** vía fixtures de los flujos anteriores, pero **sin tests
unitarios dedicados**. Se aceptan para el cierre de la Etapa 11 (alcance DoD mínimo) y
quedan como deuda de cobertura ampliable sin bloquear el sub-proyecto de Reclutamiento:

| Modelo / Componente | Cómo se cubre hoy | Deuda |
|---|---|---|
| `bca.factor_pca` | Indirecto en `test_pca_metlife.py` | CRUD, vigencia, unicidad (producto+moneda) |
| `bca.conducto` | Indirecto en parsers / pólizas | CRUD, unicidad de `codigo_archivo`, relación aseguradora |
| `bca.poliza.cambio.agente` | 1 uso en `test_poliza.py` | Historial completo, validaciones anterior≠nuevo |
| `bca.poliza.beneficiario` | Fixtures Vida/GMM/portafolio | Validación suma 100% como unidad |
| `bca.bitacora.linea` | Indirecto en cobranza | Estados de `marca`, creación como unidad |
| `res.partner` (ext. BCA) | Fixtures | Validaciones `bca_tipo` y jerarquía `parent_id` |
| `product.template` (ext. BCA) | Fixtures | Cross-validación `bca_es_producto_seguro`/ramo |
| `res.partner.agente.aseguradora` | Indirecto en reportes | Transiciones de `bca_estado_agente` |
| `CalculadorPCABase` | Vía `CalculadorPCAMetLife` | Interfaz base + `obtener_calculador` |
| Record rules (modelos 2.°) | `test_record_rules.py` (núcleo) | Acceso a bitácora/factor/conducto por rol |

---

## 4. Convención: inmunidad al *drift* de conductos

El parser resuelve el conducto con `ParserBase._resolver_conducto`, que busca por
**`codigo_archivo` + `aseguradora_id` + `activo=True`**. El conducto semilla
(`BCA_Seguros.conducto_metlife_agente_directo`) **no es estable** entre entornos: su
`codigo_archivo` está diseñado para cambiar según los CSV reales, y en despliegues como
sandbox su aseguradora o su flag `activo` pueden diferir. Por eso un fixture **nunca debe
depender del seed** (ni del literal `'AGENTE_DIRECTO'` ni de `env.ref(seed)`).

**Patrón obligatorio** — cada fixture crea su propio conducto, ligado a la aseguradora del
test y con un `codigo_archivo` único (no choca con el `UNIQUE(codigo_archivo,
aseguradora_id)`), y luego alimenta ese código:

```python
# en setUpClass
cls.conducto = cls.env['bca.conducto'].create({
    'name': 'Conducto Test ...',
    'codigo_archivo': 'TEST_COND_...',
    'aseguradora_id': cls.aseguradora.id,
})
# en el fixture de fila
'conducto': self.conducto.codigo_archivo,
```

Así el match siempre se satisface (mismo código, misma aseguradora, `activo=True`) de
forma determinista en BD limpia y en sandbox drifteado. Este es el patrón que ya usaban
`test_pca_metlife`, `test_reportes`, `test_poliza_vida` y `test_poliza_gmm`; los 3 tests
que fallaban (`test_parsers` Vida/GMM y `test_cobranza_fifo`) eran los únicos acoplados al
seed y se alinearon a esta convención. Ver **D-13** en `Decisiones.md`. El caso negativo
deliberado (`'CONDUCTO_INVENTADO'` en `test_metlife_vida_conducto_no_match_continua`) sí
usa un literal a propósito y debe permanecer.
