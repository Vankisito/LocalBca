# Catálogo de Coberturas por Producto — MetLife

## 1. Propósito de este documento
Este catálogo se extrajo del correo/PPT enviado por la aseguradora (`coberturas_adicionales_por_producto.pptx`) y sirve como **insumo de referencia para QA**: nos permite validar que el módulo `hd_seguros` filtre correctamente los productos y coberturas disponibles según Aseguradora → Ramo → Producto, tal como se documentó en `Errores_Modulo_Seguros.md` (sección "Aseguradora y producto").

No es un documento de despliegue — es contexto de negocio para diseñar/ejecutar casos de prueba (ej. Plan de Pruebas sección 7 "Cálculo de PCA" y catálogo `hd.pca.cobertura`).

**Ramo:** Vida (todos los productos de este PPT son de Vida) — excepto donde se indique Gastos Médicos.

---

## 2. Producto: MetaLife

**Coberturas disponibles (seleccionables vía cotización):**
- Fallecimiento *(cobertura base)*
- Exención del pago de primas por invalidez total y permanente
- Pago anticipado de la suma asegurada por invalidez total y permanente
- Indemnización por muerte accidental
- Indemnización por muerte accidental y/o pérdidas orgánicas
- Doble indemnización en caso de muerte accidental y/o pérdidas orgánicas
- Graves enfermedades

---

## 3. Producto: Horizonte

**Cobertura Básica:**
- (Fallecimiento — cobertura base del plan)

**Coberturas adicionales:**
- Exención de pago de primas por invalidez
- Pago anticipado de suma asegurada por invalidez
- Indemnización por muerte accidental
- Indemnización por Muerte Accidental y/o Pérdidas Orgánicas
- Indemnización por Muerte Accidental y/o Pérdidas Orgánicas por Accidente Colectivo
- Graves enfermedades
- Gastos funerarios

---

## 4. Producto: Educalife

> Nota: el slide de origen muestra una captura de ejemplo (cotización con datos de un titular ficticio: edad, fumador/no fumador, prima), no solo el catálogo puro. Se extraen aquí únicamente las coberturas.

**Cobertura Básica:**
- Básica Temporal

**Coberturas adicionales:**
- Pago de suma asegurada por invalidez
- Garantia de pago por fallecimiento (cubierto)
- Garantia de pago de primas por invalidez (cubierto)
- Indemnización por muerte accidental
- Indemnización por Muerte Accidental y/o Pérdidas Orgánicas por Accidente Colectivo
- Graves enfermedades
- Gastos funerarios
- Enfermedad terminal

*(Ejemplo de cotización visto en el slide: Suma asegurada básica $150,000, prima total del titular $1,472.33 — útil como caso de prueba de referencia, no como dato maestro.)*

---

## 5. Productos: Perfectlife, Totalife, TempoLife

*(Comparten el mismo catálogo de coberturas según el PPT.)*

**Cobertura Básica:**
- Básica

**Coberturas adicionales:**
- Exención de pago de primas por invalidez
- Pago anticipado de suma asegurada por invalidez
- Indemnización por muerte accidental
- Indemnización por Muerte Accidental y/o Pérdidas Orgánicas
- Indemnización por Muerte Accidental y/o Pérdidas Orgánicas por Accidente Colectivo
- Graves enfermedades
- Gastos funerarios

---

## 6. Productos: FlexiLife Sueño, FlexiLife Inversión

*(Comparten el mismo catálogo de coberturas según el PPT.)*

**Cobertura Básica:**
- Básica — Suma Asegurada $150,000

**Coberturas adicionales:**
- Pago anticipado de suma asegurada por invalidez
- Indemnización por muerte accidental
- Indemnización por Muerte Accidental y/o Pérdidas Orgánicas
- Triple Indemnización por Muerte Accidental y/o Pérdidas Orgánicas
- Graves enfermedades
- Gastos funerarios

---

## 7. Producto: Medicalife Familiar
*(Ramo: Gastos Médicos)*

**Coberturas opcionales:**
- MetDental Plus
- Visión
- Emergencia en el extranjero
- Enfermedad catastrófica en el extranjero
- Reducción de deducible
- Estudiantes en el extranjero
- Protección Garantizada

---

## 8. Producto: Primordial

**Plan:** Familiar

**Coberturas adicionales:**
- Suma Asegurada adicional (opcional — *"Puede o no tener Suma asegurada adicional"*, según lo indicado en el PPT)

> ⚠️ Este slide trae menos detalle que los demás; si se requiere el catálogo completo de coberturas de Primordial, habría que solicitarlo explícitamente — no inventar datos no confirmados (regla de "No Alucinar" del proyecto).

---

## 9. Producto: Met4U

**Coberturas:**
- Básica — Suma Asegurada $400,000, Prima anual $20,216.00
- Invalidez
- Cáncer — Suma Asegurada $1,600,000, Prima anual $34,592.00
- Diabetes
- Graves Enfermedades

**Forma de pago:** Anual
**Prima anual total por coberturas / Aportación anual total (ejemplo del slide):** $54,808.00

---

## 10. Resumen — Tabla rápida Producto vs. Coberturas

| Producto | Ramo | # Coberturas listadas | Tipo de dato |
| :--- | :--- | :--- | :--- |
| MetaLife | Vida | 6 adicionales | Catálogo puro |
| Horizonte | Vida | 7 adicionales | Catálogo puro |
| Educalife | Vida | 6 adicionales | Catálogo + ejemplo de cotización |
| Perfectlife / Totalife / TempoLife | Vida | 7 adicionales | Catálogo puro |
| FlexiLife Sueño / FlexiLife Inversión | Vida | 6 adicionales | Catálogo puro |
| Medicalife Familiar | Gastos Médicos | 7 opcionales | Catálogo puro |
| Primordial | Vida | 1 (Suma Asegurada adicional) | Incompleto — validar con cliente |
| Met4U | Vida | 4 (incl. Básica) | Catálogo + ejemplo de prima |

---

## 11. Notas para QA
- Al probar el selector Aseguradora → Ramo → Producto → Coberturas (bug reportado en `Errores_Modulo_Seguros.md`), usar esta lista como set de casos de prueba: cada producto debe mostrar únicamente sus coberturas correspondientes.
- Verificar si estas coberturas deben alimentar el modelo `hd.pca.cobertura` (tabla de ponderación PCA, ver `GrupoBCA_Backlog_F1_Cartera_Cobranza.md` sección "Calcular y Reportar PCA por Agente") — actualmente esa tabla está bloqueada por SI-04 (catálogo de coberturas con ponderación PCA), pendiente de Guillermo.
- El producto **Primordial** quedó con información incompleta en el PPT recibido; no se debe asumir o completar el catálogo — corresponde solicitar el insumo faltante antes de dar por válida cualquier prueba sobre este producto.
