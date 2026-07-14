from __future__ import annotations

from odoo import fields, models, tools
from odoo.tools import SQL

from ..models.product_template import RAMO_SELECTION


class BcaReportePcaAgente(models.Model):
    _name = 'bca.reporte.pca.agente'
    _description = 'Reporte PCA por Agente'
    _auto = False
    _order = 'fecha_pago desc'
    _rec_name = 'agente_id'

    # Dimensiones — leídas de la FOTO INMUTABLE del recibo (C2 / R-PCA-01):
    # agente_id y promotoria_id se congelan en bca_recibo al registrar el pago.
    # Nunca de la póliza actual (puede cambiar vía cambiar_agente()).
    agente_id: int = fields.Many2one('res.partner', string='Agente', readonly=True)
    promotoria_id: int = fields.Many2one('res.partner', string='Promotoría', readonly=True)
    aseguradora_id: int = fields.Many2one('res.partner', string='Aseguradora', readonly=True)
    producto_id: int = fields.Many2one('product.template', string='Producto', readonly=True)
    ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo', readonly=True)
    fecha_pago: fields.Date = fields.Date(string='Fecha de Pago', readonly=True)

    # Métricas — PCA siempre en MXN (D-08), por eso usa pca_currency_id.
    pca_currency_id: int = fields.Many2one('res.currency', string='Moneda PCA', readonly=True)
    pca: float = fields.Monetary(
        string='PCA', currency_field='pca_currency_id', readonly=True,
    )
    factor: float = fields.Float(string='Factor', digits=(6, 4), readonly=True)

    def init(self) -> None:
        """Crea la vista SQL del reporte de PCA por agente.

        Grano: un recibo pagado. Solo computa el agente con CLAVE DEFINITIVA
        *en la aseguradora de la póliza* (estado por aseguradora del modelo
        puente, no el rollup del partner). Ver Arquitectura §6.1.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL(
            """
            CREATE VIEW %s AS (
                SELECT
                    r.id AS id,
                    r.agente_id AS agente_id,
                    r.promotoria_id AS promotoria_id,
                    p.aseguradora_id AS aseguradora_id,
                    p.producto_id AS producto_id,
                    p.ramo AS ramo,
                    r.fecha_pago AS fecha_pago,
                    r.pca_currency_id AS pca_currency_id,
                    r.pca_aplicada AS pca,
                    r.factor_aplicado AS factor
                FROM bca_recibo r
                JOIN bca_poliza p ON r.poliza_id = p.id
                JOIN res_partner_agente_aseguradora aa
                     ON aa.agente_id = r.agente_id
                    AND aa.aseguradora_id = p.aseguradora_id
                WHERE r.estado = 'pagado'
                  AND aa.estado = 'clave_definitiva'
            )
            """,
            SQL.identifier(self._table),
        ))
