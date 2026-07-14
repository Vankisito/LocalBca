# Migración E9: reportes SQL (SICs).
# Las 4 vistas SQL (_auto=False) cambian de forma: pasan de placeholder
# `SELECT 1 WHERE FALSE` a la query real con sus columnas. El post_init_hook
# del módulo ya recrea las vistas en cada -u, pero lo invocamos explícitamente
# aquí por robustez de orden (la migración corre antes del hook) y para dejar
# registro del cambio de esquema de las vistas.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

REPORTES = [
    'bca.reporte.pca.agente',
    'bca.reporte.pca.promotoria',
    'bca.reporte.pca.consolidado',
    'bca.reporte.estado.cartera',
]


def migrate(cr, version):
    if not version:          # instalación fresca: el post_init_hook se encarga
        return

    env = api.Environment(cr, SUPERUSER_ID, {})
    for model_name in REPORTES:
        env[model_name].init()
    _logger.info("BCA E9: %s vista(s) SQL de reportes recreada(s)", len(REPORTES))
