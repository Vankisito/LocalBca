"""Generador de la plantilla CSV de cobranza diaria.

Python puro (sin dependencias Odoo) para poder probarse de forma aislada y
reutilizarse desde scripts de dev. Espejo de ``plantilla_portafolio`` pero
emitiendo CSV (lo que el wizard ingiere) en lugar de XLSX.

Las columnas NO se hardcodean aquí: el wizard pasa
``parser_cls.columnas_requeridas`` (``COLUMNAS_LSP``/``COLUMNAS_GCAYE``), única
fuente de verdad. Este módulo solo aporta el valor de ejemplo por columna y el
ensamblado del CSV.
"""

from __future__ import annotations

import csv
import io

# Valor de ejemplo por nombre de columna, con formatos que el parser acepta
# (ver ``ParserBase.normalizar_fecha`` / ``normalizar_monto``):
#   - fechas en dd/mm/aaaa
#   - montos con punto decimal y sin separador de miles (la coma se interpreta
#     como separador de miles, así que el ejemplo la evita)
#   - estatus_pago distinto de 'anulado'/'cancelado' (esos se omiten, R-COB-01)
# Columnas sin entrada (no debería haber) caen a '' vía .get().
EJEMPLOS: dict[str, str] = {
    'numero_poliza': 'POL-0001',
    'producto': 'Nombre del Producto',
    'agente': 'CLAVE-AGENTE',
    'contratante': 'Nombre del Contratante',
    'moneda': 'MXN',
    'estatus_pago': 'normal',
    'fecha_aplicacion': '15/06/2026',
    'vigencia_desde': '01/01/2026',
    'vigencia_hasta': '01/01/2027',
    'conducto': 'AGENTE_DIRECTO',
    'prima_modal': '1000.00',
    'prima_neta': '1000.00',
    'prima_total': '1000.00',
    'recargo': '0.00',
    'gastos_expedicion': '0.00',
    'impuestos': '0.00',
    'comision_informativa': '0.00',
    'folio_endoso': '',
}


def construir_csv_bytes(columnas: list[str]) -> bytes:
    """Devuelve los bytes del CSV (encabezados + 1 fila de ejemplo).

    ``columnas`` define tanto el orden como los encabezados exactos que el
    wizard valida (``validar_estructura``). Codificado en ``utf-8-sig`` para
    coincidir con la ruta preferida de ``_abrir_csv`` y abrir bien en Excel.
    """
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=columnas, extrasaction='ignore')
    writer.writeheader()
    writer.writerow({col: EJEMPLOS.get(col, '') for col in columnas})
    return buffer.getvalue().encode('utf-8-sig')
