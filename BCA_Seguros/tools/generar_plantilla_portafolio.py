"""Escribe la plantilla de portafolio (.xlsx) a ``static/src/plantillas/``.

Utilidad de desarrollo: la lógica y el catálogo de columnas viven en
``BCA_Seguros/wizards/plantilla_portafolio.py`` (fuente única, compartida con la
acción de descarga del wizard ``bca.wizard.carga.portafolio``). Este script solo
materializa un asset estático en disco para quien lo prefiera.

Ejecutar desde un contexto con ``openpyxl`` disponible::

    python3 tools/generar_plantilla_portafolio.py

Se importa el helper directamente del directorio ``wizards`` (sin pasar por su
``__init__``, que arrastra dependencias de Odoo) añadiéndolo a ``sys.path``.
"""

from __future__ import annotations

import os
import sys

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_BASE, 'wizards'))

import plantilla_portafolio  # noqa: E402  (tras ajustar sys.path)


def main() -> str:
    destino_dir = os.path.join(_BASE, 'static', 'src', 'plantillas')
    os.makedirs(destino_dir, exist_ok=True)
    destino = os.path.join(destino_dir, 'plantilla_portafolio_BCA.xlsx')

    plantilla_portafolio.construir_workbook().save(destino)
    print('Plantilla generada: %s' % destino)
    print('  VIDA: %d columnas, %d filas de ejemplo' % (
        len(plantilla_portafolio.COLUMNAS_VIDA),
        len(plantilla_portafolio.EJEMPLOS_VIDA)))
    print('  GMM : %d columnas, %d filas de ejemplo' % (
        len(plantilla_portafolio.COLUMNAS_GMM),
        len(plantilla_portafolio.EJEMPLOS_GMM)))
    print('  BENEFICIARIOS: %d columnas, %d filas de ejemplo' % (
        len(plantilla_portafolio.COLUMNAS_BENEFICIARIOS),
        len(plantilla_portafolio.EJEMPLOS_BENEFICIARIOS)))
    print('  COBERTURAS: %d columnas, %d filas de ejemplo' % (
        len(plantilla_portafolio.COLUMNAS_COBERTURAS),
        len(plantilla_portafolio.EJEMPLOS_COBERTURAS)))
    return destino


if __name__ == '__main__':
    main()
