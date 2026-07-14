from __future__ import annotations

from odoo import api, fields, models
from odoo.exceptions import ValidationError

RAMO_SELECTION = [
    ('vida', 'Vida'),
    ('gmm', 'GMM'),
    ('autos', 'Autos'),
    ('danos', 'Daños'),
]


class BcaFactorPca(models.Model):
    _name = 'bca.factor.pca'
    _description = 'Factor PCA'
    # Lista: modelo NUEVO que hereda capacidades de mixins (no extensión de otro modelo)
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name: str = fields.Char(string='Nombre', required=True)
    aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        required=True,
        ondelete='restrict',
        domain=[('bca_tipo', '=', 'aseguradora')],
    )
    ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo')
    producto_ids: list[int] = fields.Many2many(
        'product.template',
        string='Productos',
        domain=[('bca_es_producto_seguro', '=', True)],
    )
    currency_id: int = fields.Many2one(
        'res.currency',
        string='Moneda',
    )

    # Campos exclusivos GMM
    coaseguro_min: float = fields.Float(
        string='Coaseguro Mínimo (%)',
        help='Solo aplica para ramo GMM',
    )
    coaseguro_max: float = fields.Float(
        string='Coaseguro Máximo (%)',
        help='Solo aplica para ramo GMM',
    )
    deducible_min: float = fields.Monetary(
        string='Deducible Mínimo',
        currency_field='currency_id',
        help='Solo aplica para ramo GMM',
    )

    # Campo principal — tracking obligatorio (corrección M2)
    factor: float = fields.Float(
        string='Factor',
        required=True,
        tracking=True,
        digits=(6, 4),
    )
    vigencia_desde: fields.Date = fields.Date(
        string='Vigente Desde',
        required=True,
        tracking=True,
    )
    vigencia_hasta: fields.Date = fields.Date(
        string='Vigente Hasta',
        tracking=True,
    )
    activo: bool = fields.Boolean(
        string='Activo',
        default=True,
        tracking=True,
    )

    @api.constrains('factor')
    def _check_factor_rango(self) -> None:
        """Valida que el factor esté en el rango permitido [0.0, 1.2]."""
        for rec in self:
            if not (0.0 <= rec.factor <= 1.2):
                raise ValidationError(
                    f'El factor debe estar entre 0.0 y 1.2 (recibido: {rec.factor})'
                )
