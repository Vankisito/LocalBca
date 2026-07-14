---
titulo: Diccionario de Campos — Layout VIDA (MetLife) · Módulo BCA_Seguros
fecha: 2026-05-28
autor: Hábitat Digital
version: v1.0
area: Entrega
---

# Diccionario de Campos — Layout VIDA (MetLife)

## Propósito

Describir cada campo de la hoja **VIDA** del archivo `LAY_OUT_-_Portafolio_BCA`
en lenguaje de negocio: qué es, su tipo de dato y notas relevantes. Sirve como
referencia para llenar correctamente el layout antes de la carga masiva de pólizas
de Vida de MetLife.

---

## Alcance

- **Aseguradora:** MetLife · **Ramo:** Vida.
- **Hoja origen:** `VIDA` (encabezados en fila 2, tipos en fila 3, datos desde fila 4).
- **Formato de fecha:** `DD/MM/YYYY`.
- **Formato de importe:** coma como separador de miles, punto decimal.

---

## Tabla de campos — Hoja VIDA

| Campo Layout | Tipo | Descripción del campo | Notas sobre el campo |
|---|---|---|---|
| Póliza | Numero | Número que identifica la póliza. | Identificador único por aseguradora. |
| Nombre del Contratante | Texto | Persona o entidad que contrata y paga la póliza. | Titular del contrato. |
| Nombre del Asegurado | Texto | Persona cuya vida está asegurada. | Puede ser distinto del contratante; se registra como contacto aparte vinculado a la póliza. |
| Clave de Agente | Numero | Clave con la que la aseguradora identifica al agente que vendió la póliza. | Se usa para asociar la póliza con su agente. |
| Nombre Agente | Texto | Nombre del agente que vendió la póliza. | Apoyo para validar la clave de agente. |
| Estatus de Póliza | Texto | Situación actual de la póliza (vigente, vencida, cancelada). | Requiere catálogo de valores normalizado. |
| Producto | Texto | Producto comercial de Vida contratado. | Determina el ramo y el factor de PCA. |
| Plan | Texto | Plan específico asociado al producto. | Complementa al producto. |
| Fecha emisión | Fecha | Fecha en que se emitió la póliza. | Formato DD/MM/YYYY. |
| Fecha inicio Vigencia | Fecha | Fecha en que inicia la cobertura. | Requerido. |
| Fecha Fin Vigencia | Fecha | Fecha en que termina la cobertura. | Requerido. |
| Conducto de Cobro | Texto | Medio por el que se cobra la prima (cargo automático, agente directo, etc.). | Aplica como conducto por defecto de la póliza y de sus recibos. |
| Frecuencia de Pago | Texto | Periodicidad con la que se paga la prima. | Mensual, trimestral, semestral o anual. |
| Prima de Riesgo Anual | Numero | Prima total anual de la póliza. | Importe con separador de miles. |
| Prima Fraccionada | Numero | Prima correspondiente a cada periodo de pago. | Importe. |
| Recargo Fijo | Numero | Recargo aplicado por el fraccionamiento del pago. | Importe. |
| Moneda | Texto | Divisa de la póliza. | MXN o USD. |
| Suma Asegurada | Numero | Monto asegurado de la póliza. | Importe. |
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
| e-mail Asegurado | Mail | Correo electrónico del asegurado. | Corresponde al contacto del asegurado. |
| Referencia Prima Básica (TRAD) | Texto | Referencia de cobro de la prima básica tradicional. | Referencia de pago del contratante. |
| Fondo Variable | Texto | Referencia del fondo variable. | Referencia de pago del contratante. |
| Fondo Fijo | Texto | Referencia del fondo fijo. | Referencia de pago del contratante. |
| Fondo Variable Plan Personal de Retiro (PPR) | Texto | Fondo variable del Plan Personal de Retiro. | Referencia de pago del contratante. |
| Fondo Fijo Plan Personal de Retiro (PPR) | Texto | Fondo fijo del Plan Personal de Retiro. | Referencia de pago del contratante. |
| Fondo Variable Cuenta Personal Especial de Ahorro (CPEA) | Texto | Fondo variable de la Cuenta Personal Especial de Ahorro. | Referencia de pago del contratante. |
| Fondo Fijo Cuenta Especial de Ahorro (CPEA) | Texto | Fondo fijo de la Cuenta Personal Especial de Ahorro. | Referencia de pago del contratante. |
| Nombre del Beneficiario 1 | Texto | Nombre del primer beneficiario de la póliza. | Hasta 10 beneficiarios por póliza. |
| Parentesco 1 | Texto | Relación del beneficiario 1 con el contratante. | |
| % al que tiene Derecho 1 | Porcentaje | Porcentaje de la suma asegurada que corresponde al beneficiario 1. | La suma de los porcentajes de todos los beneficiarios debe ser 100%. |
| Nombre del Beneficiario 2 | Texto | Nombre del segundo beneficiario de la póliza. | |
| Parentesco 2 | Texto | Relación del beneficiario 2 con el contratante. | |
| % al que tiene Derecho 2 | Porcentaje | Porcentaje que corresponde al beneficiario 2. | |
| Nombre del Beneficiario 3 | Texto | Nombre del tercer beneficiario de la póliza. | |
| Parentesco 3 | Texto | Relación del beneficiario 3 con el contratante. | |
| % al que tiene Derecho 3 | Porcentaje | Porcentaje que corresponde al beneficiario 3. | |
| Nombre del Beneficiario 4 | Texto | Nombre del cuarto beneficiario de la póliza. | |
| Parentesco 4 | Texto | Relación del beneficiario 4 con el contratante. | |
| % al que tiene Derecho 4 | Porcentaje | Porcentaje que corresponde al beneficiario 4. | |
| Nombre del Beneficiario 5 | Texto | Nombre del quinto beneficiario de la póliza. | |
| Parentesco 5 | Texto | Relación del beneficiario 5 con el contratante. | |
| % al que tiene Derecho 5 | Porcentaje | Porcentaje que corresponde al beneficiario 5. | |
| Nombre del Beneficiario 6 | Texto | Nombre del sexto beneficiario de la póliza. | |
| Parentesco 6 | Texto | Relación del beneficiario 6 con el contratante. | |
| % al que tiene Derecho 6 | Porcentaje | Porcentaje que corresponde al beneficiario 6. | |
| Nombre del Beneficiario 7 | Texto | Nombre del séptimo beneficiario de la póliza. | |
| Parentesco 7 | Texto | Relación del beneficiario 7 con el contratante. | |
| % al que tiene Derecho 7 | Porcentaje | Porcentaje que corresponde al beneficiario 7. | |

---

## Notas generales

- **Beneficiarios:** la póliza admite hasta **10 beneficiarios**. Cada beneficiario
  requiere su parentesco y su porcentaje, y **la suma de los porcentajes debe ser 100%**.
- **Asegurado:** cuando el asegurado es distinto del contratante, se captura como
  una persona aparte ligada a la póliza.
- **Fechas e importes:** respetar el formato `DD/MM/YYYY` y el uso de coma para miles
  y punto para decimales.

---

*Documento elaborado por Hábitat Digital. Referencia de negocio para el llenado del
layout de portafolio (ramo Vida).*
