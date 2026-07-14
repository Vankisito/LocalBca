from __future__ import annotations

from odoo import fields, models


class BcaConducto(models.Model):
    _name = 'bca.conducto'
    _description = 'Conducto de Pago'

    name: str = fields.Char(string='Nombre', required=True)
    codigo_archivo: str = fields.Char(
        string='Código en Archivo',
        required=True,
        help='Clave exacta en la columna de conducto de los CSV de la aseguradora',
    )
    aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        required=True,
        ondelete='restrict',
        domain=[('bca_tipo', '=', 'aseguradora')],
    )
    activo: bool = fields.Boolean(string='Activo', default=True)

    # v19: models.Constraint()
    _unique_codigo_aseg = models.Constraint(
        'UNIQUE(codigo_archivo, aseguradora_id)',
        'El código de conducto debe ser único por aseguradora',
    )
