---
titulo: Diccionario de Campos — Layout GMM (MetLife) · Módulo BCA_Seguros
fecha: 2026-05-28
autor: Hábitat Digital
version: v1.0
area: Entrega
---

# Diccionario de Campos — Layout GMM (MetLife)

## Propósito

Describir cada campo de la hoja **GMM** del archivo `LAY_OUT_-_Portafolio_BCA`
en lenguaje de negocio: qué es, su tipo de dato y notas relevantes. Sirve como
referencia para llenar correctamente el layout antes de la carga masiva de pólizas
de Gastos Médicos Mayores de MetLife.

---

## Alcance

- **Aseguradora:** MetLife · **Ramo:** Gastos Médicos Mayores (GMM).
- **Hoja origen:** `GMM` (encabezados en fila 2, tipos en fila 3, datos desde fila 4).
- **Formato de fecha:** `DD/MM/YYYY`.
- **Formato de importe:** coma como separador de miles, punto decimal.

---

## Tabla de campos — Hoja GMM

| Campo Layout | Tipo | Descripción del campo | Notas sobre el campo |
|---|---|---|---|
| Póliza Original | Numero | Número de la póliza de origen cuando hubo renovación o conversión. | Permite la trazabilidad histórica de la póliza. |
| Poliza actual | Numero | Número de póliza vigente. | Identificador único por aseguradora. |
| Ramo / Sub ramo | Numero | Código del ramo o sub-ramo de la póliza. | Clasificación del tipo de cobertura. |
| Nombre del Contratante | Texto | Persona o entidad que contrata y paga la póliza. | Titular del contrato. |
| Nombre del Asegurado | Texto | Persona asegurada titular de la póliza. | Puede ser distinto del contratante; se registra como contacto aparte vinculado a la póliza. |
| Clave de Agente | Numero | Clave con la que la aseguradora identifica al agente que vendió la póliza. | Se usa para asociar la póliza con su agente. |
| Nombre Agente | Texto | Nombre del agente que vendió la póliza. | Apoyo para validar la clave de agente. |
| Estatus de Póliza | Texto | Situación actual de la póliza (vigente, vencida, cancelada). | Requiere catálogo de valores normalizado. |
| Producto | Texto | Producto comercial de GMM contratado. | Determina el ramo y el factor de PCA. |
| Nivel Hospitalario | Texto | Nivel hospitalario cubierto por la póliza. | Exclusivo de GMM. |
| Fecha emisión | Fecha | Fecha en que se emitió la póliza. | Formato DD/MM/YYYY. |
| Fecha inicio Vigencia | Fecha | Fecha en que inicia la cobertura. | Requerido. |
| Fecha Fin Vigencia | Fecha | Fecha en que termina la cobertura. | Requerido. |
| Conducto de Cobro | Texto | Medio por el que se cobra la prima (cargo automático, tarjeta, etc.). | Aplica como conducto por defecto de la póliza y de sus recibos. |
| Frecuencia de Pago | Texto | Periodicidad con la que se paga la prima. | Mensual, trimestral, semestral o anual. |
| Prima de Riesgo Anual | Numero | Prima total anual de la póliza. | Importe con separador de miles. |
| Prima Fraccionada | Numero | Prima correspondiente a cada periodo de pago. | Importe. |
| Recargo Fijo | Numero | Recargo fijo aplicado a la póliza. | Importe. |
| Recargos (pago fraccionado) | Numero | Recargo por fraccionar el pago de la prima. | Importe. |
| IVA | Numero | Impuesto al Valor Agregado correspondiente a la prima. | Exclusivo de GMM. Importe. |
| Moneda | Texto | Divisa de la póliza. | MXN o USD. |
| Suma Asegurada | Numero | Monto asegurado de la póliza. | Importe. |
| Deducible | Numero | Monto deducible de la póliza. | Exclusivo de GMM. Influye en el factor de PCA. |
| Coaseguro | Porcentaje | Porcentaje de coaseguro de la póliza. | Exclusivo de GMM. Un coaseguro ≤ 5% no computa PCA. |
| Pagado Hasta | Fecha | Fecha hasta la cual la póliza está pagada. | Métrica de vigencia operativa; se determina a partir de los pagos. |
| Estatus de Pago | Texto | Situación de pago de la póliza. | Requiere catálogo de valores. |
| R.F.C. Contratante | Texto | RFC del contratante. | Validar formato mexicano. La CURP no está incluida en este layout. |
| Fecha de nacimiento | Fecha | Fecha de nacimiento del contratante. | Dato demográfico del contratante. |
| Estado Civil | Texto | Estado civil del contratante. | Dato demográfico del contratante. |
| Género | Texto | Género del contratante. | Dato demográfico del contratante. |
| Calle y número | Texto | Calle y número del domicilio del contratante. | Dirección. |
| Colonia | Texto | Colonia del domicilio. | Dirección. |
| Población (Alcaldía o Municipio) | Texto | Alcaldía o municipio del domicilio. | Dirección. |
| C.P | Numero | Código postal del domicilio. | Dirección. |
| Ciudad o Estado | Texto | Ciudad o estado del domicilio. | Dirección. |
| Teléfono o Celular | Telefono | Teléfono de contacto del contratante. | Contacto. |
| e-mail del Contratante | Mail | Correo electrónico del contratante. | Contacto. |
| Coberturas Adicionales | Texto | Coberturas adicionales incluidas en la póliza. | Información de la póliza. |
| e-mail Asegurado | Mail | Correo electrónico del asegurado. | Corresponde al asegurado titular. |
| Referencia de cobro Prima (MEDICA) | Texto | Referencia de cobro de la prima médica. | Referencia de pago del contratante. |
| Nombre del Asegurado 1 | Texto | Nombre de la primera persona adicional cubierta. | Dependiente cubierto bajo la póliza. |
| Parentesco 1 | Texto | Relación del asegurado adicional 1 con el contratante. | |
| Fecha de nacimiento (Asegurado 1) | Texto | Fecha de nacimiento del asegurado adicional 1. | En el layout viene como Texto; normalizar a fecha. |
| Nombre del Asegurado 2 | Texto | Nombre de la segunda persona adicional cubierta. | |
| Parentesco 2 | Texto | Relación del asegurado adicional 2 con el contratante. | |
| Fecha de nacimiento (Asegurado 2) | Texto | Fecha de nacimiento del asegurado adicional 2. | En el layout viene como Texto; normalizar a fecha. |
| Nombre del Asegurado 3 | Texto | Nombre de la tercera persona adicional cubierta. | |
| Parentesco 3 | Texto | Relación del asegurado adicional 3 con el contratante. | |
| Fecha de nacimiento (Asegurado 3) | Texto | Fecha de nacimiento del asegurado adicional 3. | En el layout viene como Texto; normalizar a fecha. |
| Nombre del Asegurado 4 | Texto | Nombre de la cuarta persona adicional cubierta. | |
| Parentesco 4 | Texto | Relación del asegurado adicional 4 con el contratante. | |
| Fecha de nacimiento (Asegurado 4) | Texto | Fecha de nacimiento del asegurado adicional 4. | En el layout viene como Texto; normalizar a fecha. |
| Nombre del Asegurado 5 | Texto | Nombre de la quinta persona adicional cubierta. | El layout repite la etiqueta "Asegurado 4"; corresponde al 5º. |
| Parentesco 5 | Texto | Relación del asegurado adicional 5 con el contratante. | |
| Fecha de nacimiento (Asegurado 5) | Texto | Fecha de nacimiento del asegurado adicional 5. | En el layout viene como Texto; normalizar a fecha. |

---

## Notas generales

- **Asegurados adicionales:** la póliza GMM admite hasta **5 asegurados adicionales**
  (dependientes cubiertos), cada uno con nombre, parentesco y fecha de nacimiento.
- **Asegurado titular:** cuando es distinto del contratante, se captura como una
  persona aparte ligada a la póliza.
- **Coaseguro y deducible:** son determinantes para el cálculo de PCA en GMM.
- **Fechas e importes:** respetar el formato `DD/MM/YYYY` y el uso de coma para miles
  y punto para decimales.

---

*Documento elaborado por Hábitat Digital. Referencia de negocio para el llenado del
layout de portafolio (ramo Gastos Médicos Mayores).*
