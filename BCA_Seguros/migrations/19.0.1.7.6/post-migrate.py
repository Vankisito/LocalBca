# Migración B1: separación de ejes en res.partner.bca_tipo.
# 'contratante' y 'asegurado' dejan de ser posición de RED (bca_tipo) y pasan a
# ser ROLES de póliza no excluyentes (flags computados bca_es_contratante /
# bca_es_asegurado, derivados de las pólizas). Aquí:
#   1) Se limpian los valores huérfanos de bca_tipo (Odoo tolera el valor
#      fuera del Selection en BD hasta este UPDATE).
#   2) Se recomputan los flags de rol desde las pólizas existentes (refuerzo:
#      los stored-computed también se recalculan al añadir la columna).
# La deduplicación de contactos ya duplicados en BD NO se hace aquí (riesgo
# destructivo): usar el asistente nativo "Deduplicar contactos"
# (base.partner.merge.automatic.wizard, app Contactos).
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:          # instalación fresca: nada que migrar
        return

    cr.execute(
        "UPDATE res_partner SET bca_tipo = NULL "
        "WHERE bca_tipo IN ('contratante', 'asegurado')"
    )
    limpiados = cr.rowcount
    _logger.info(
        "BCA B1: %s contacto(s) con bca_tipo contratante/asegurado limpiados "
        "(ahora son roles de póliza)", limpiados,
    )

    # Recomputo explícito de los flags de rol desde las pólizas.
    from odoo import api, SUPERUSER_ID
    env = api.Environment(cr, SUPERUSER_ID, {})
    Partner = env['res.partner']
    con_rol = Partner.search([
        '|',
        ('bca_polizas_como_contratante', '!=', False),
        ('bca_polizas_como_asegurado', '!=', False),
    ])
    con_rol._compute_bca_roles_poliza()
    env.flush_all()
    _logger.info(
        "BCA B1: flags de rol recomputados en %s contacto(s)", len(con_rol),
    )
