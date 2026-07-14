from __future__ import annotations

from odoo import fields, models

from .res_partner import ESTADO_AGENTE_SELECTION


class ResPartnerAgenteAseguradora(models.Model):
    _name = 'res.partner.agente.aseguradora'
    _description = 'Clave de Agente por Aseguradora'
    _rec_name = 'clave_agente'

    agente_id: int = fields.Many2one(
        'res.partner',
        string='Agente',
        required=True,
        ondelete='cascade',
        domain=[('bca_tipo', '=', 'agente')],
        index=True,
    )
    aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        required=True,
        ondelete='restrict',
        domain=[('bca_tipo', '=', 'aseguradora')],
        index=True,
    )
    clave_agente: str = fields.Char(string='Clave Agente', required=True)
    # Estado de carrera del agente EN ESTA aseguradora (fuente de verdad).
    # Solo 'clave_definitiva' computa para PCA. Reclutamiento lo alimenta vía
    # automated actions; el rollup res.partner.bca_estado_agente se deriva de aquí.
    estado: str = fields.Selection(
        ESTADO_AGENTE_SELECTION,
        string='Estado',
        required=True,
        default='prospecto',
    )
    fecha_licencia: fields.Date = fields.Date(string='Fecha de Licencia')

    # v19: models.Constraint() reemplaza _sql_constraints (deprecated en v19)
    _unique_clave_aseg = models.Constraint(
        'UNIQUE(aseguradora_id, clave_agente)',
        'La clave del agente debe ser única por aseguradora',
    )
    _unique_agente_aseg = models.Constraint(
        'UNIQUE(agente_id, aseguradora_id)',
        'Un agente solo puede registrarse una vez por aseguradora',
    )
