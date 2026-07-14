# Migración D-07: nomenclatura de carrera del agente a 3 estados.
# Mapea el valor viejo 'con_licencia' (modelo binario prospecto/con_licencia) al
# nuevo 'clave_definitiva' y recalcula el rollup res.partner.bca_estado_agente.
# Sin esta migración, los registros viejos rompen el SelectionField (OwlError) al
# abrir un Agente, porque 'con_licencia' ya no es una opción válida.
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:          # instalación fresca: nada que migrar
        return

    # Aviso: agentes 'Con Licencia' SIN clave registrada pasarán a Prospecto
    # (el modelo nuevo exige Clave Definitiva por aseguradora para computar PCA).
    cr.execute("""
        SELECT count(*) FROM res_partner p
        WHERE p.bca_estado_agente = 'con_licencia'
          AND NOT EXISTS (SELECT 1 FROM res_partner_agente_aseguradora aa
                          WHERE aa.agente_id = p.id)
    """)
    sin_clave = cr.fetchone()[0]
    if sin_clave:
        _logger.warning(
            "BCA D-07: %s agente(s) estaban 'Con Licencia' sin clave registrada; "
            "pasan a 'Prospecto' y no computarán PCA hasta registrar una Clave "
            "Definitiva por aseguradora. Revisar.", sin_clave)

    # 1) Fuente de verdad: puente con_licencia -> clave_definitiva.
    cr.execute("""
        UPDATE res_partner_agente_aseguradora
           SET estado = 'clave_definitiva'
         WHERE estado = 'con_licencia'
    """)
    _logger.info("BCA D-07: %s clave(s) de agente migradas a clave_definitiva", cr.rowcount)

    # 2) Sanear de inmediato el valor inválido del rollup (evita el crash del
    #    SelectionField aunque el recompute no se disparara).
    cr.execute("""
        UPDATE res_partner
           SET bca_estado_agente = 'clave_definitiva'
         WHERE bca_estado_agente = 'con_licencia'
    """)

    # 3) Recalcular el rollup desde el puente (agente sin claves -> prospecto).
    env = api.Environment(cr, SUPERUSER_ID, {})
    agentes = env['res.partner'].search([('bca_tipo', '=', 'agente')])
    if agentes:
        agentes._compute_bca_estado_agente()
        agentes.flush_recordset(['bca_estado_agente'])
