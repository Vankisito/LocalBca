from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import UserError

RAMO_SELECTION = [
    ('vida', 'Vida'),
    ('gmm', 'GMM'),
    ('autos', 'Autos'),
    ('danos', 'Daños'),
]
PERIODICIDAD_SELECTION = [
    ('mensual', 'Mensual'),
    ('trimestral', 'Trimestral'),
    ('semestral', 'Semestral'),
    ('anual', 'Anual'),
]


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    bca_aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        domain=[('bca_tipo', '=', 'aseguradora')],
    )
    bca_ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo')
    bca_producto_id: int = fields.Many2one(
        'product.template',
        string='Producto de Seguro',
        domain=[('bca_es_producto_seguro', '=', True)],
    )
    bca_prima_estimada: float = fields.Monetary(
        string='Prima Anual Estimada',
        currency_field='company_currency',
    )
    bca_periodicidad: str = fields.Selection(
        PERIODICIDAD_SELECTION,
        string='Periodicidad',
        default='anual',
    )
    bca_poliza_generada_id: int = fields.Many2one(
        'bca.poliza',
        string='Póliza Generada',
        readonly=True,
        copy=False,
        help='Póliza creada desde este lead al ganarlo.',
    )

    @api.onchange('bca_producto_id')
    def _onchange_bca_producto_id(self) -> None:
        """Autollenar ramo y aseguradora desde el producto seleccionado."""
        for lead in self:
            if lead.bca_producto_id:
                lead.bca_ramo = lead.bca_producto_id.bca_ramo
                lead.bca_aseguradora_id = lead.bca_producto_id.bca_aseguradora_id

    def action_bca_generar_poliza(self) -> dict:
        """Abre el formulario de bca.poliza con datos precargados desde el lead.

        Solo permitido si el lead está en stage ganado y aún no tiene
        póliza generada. Tras crear y guardar la póliza desde la UI, el
        usuario o un siguiente paso podrá vincularla a bca_poliza_generada_id.
        """
        self.ensure_one()
        if not self.stage_id or not self.stage_id.is_won:
            raise UserError(_(
                'Solo se puede generar póliza desde un lead ganado.'
            ))
        if self.bca_poliza_generada_id:
            raise UserError(_(
                'Este lead ya tiene una póliza generada: %s.'
            ) % self.bca_poliza_generada_id.name)

        ctx = {}
        if self.partner_id:
            ctx['default_contratante_id'] = self.partner_id.id
        if self.bca_aseguradora_id:
            ctx['default_aseguradora_id'] = self.bca_aseguradora_id.id
        if self.bca_producto_id:
            ctx['default_producto_id'] = self.bca_producto_id.id
        if self.bca_prima_estimada:
            ctx['default_prima_anual'] = self.bca_prima_estimada
        if self.bca_periodicidad:
            ctx['default_periodicidad'] = self.bca_periodicidad
        if self.user_id and self.user_id.partner_id:
            ctx['default_agente_id'] = self.user_id.partner_id.id

        return {
            'type': 'ir.actions.act_window',
            'name': _('Nueva Póliza desde Lead'),
            'res_model': 'bca.poliza',
            'view_mode': 'form',
            'target': 'current',
            'context': ctx,
        }
