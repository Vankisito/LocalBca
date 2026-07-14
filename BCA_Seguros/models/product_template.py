from __future__ import annotations

from odoo import fields, models

RAMO_SELECTION = [
    ('vida', 'Vida'),
    ('gmm', 'GMM'),
    ('autos', 'Autos'),
    ('danos', 'Daños'),
]


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    bca_es_producto_seguro: bool = fields.Boolean(
        string='Es Producto de Seguro',
        default=False,
    )
    bca_aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        domain=[('bca_tipo', '=', 'aseguradora')],
    )
    bca_ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo')
    bca_temporalidad_anios: int = fields.Integer(string='Temporalidad (años)')
    bca_es_capitalizable: bool = fields.Boolean(
        string='Es Capitalizable',
        default=False,
    )
    bca_nombre_archivo_aseguradora: str = fields.Char(
        string='Nombre en Archivo Aseguradora',
        help='Clave exacta de mapeo usada en los CSV de la aseguradora',
    )
