from __future__ import annotations

from odoo import fields, models, tools
from odoo.tools import SQL

from ..models.product_template import RAMO_SELECTION


class BcaReportePcaConsolidado(models.Model):
    _name = 'bca.reporte.pca.consolidado'
    _description = 'Reporte PCA Consolidado BCA'
    _auto = False
    _order = 'fecha_pago desc'

    # Grano fino (un recibo pagado) para permitir el drill-down del pivot
    # holding → promotoría → agente → ramo (Arquitectura §6.3). El "consolidado"
    # es el total que el pivot agrega; mantener las filas detalladas habilita
    # abrir hacia abajo sin perder el nivel BCA.
    promotoria_id: int = fields.Many2one('res.partner', string='Promotoría', readonly=True)
    agente_id: int = fields.Many2one('res.partner', string='Agente', readonly=True)
    aseguradora_id: int = fields.Many2one('res.partner', string='Aseguradora', readonly=True)
    producto_id: int = fields.Many2one('product.template', string='Producto', readonly=True)
    ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo', readonly=True)
    fecha_pago: fields.Date = fields.Date(string='Fecha de Pago', readonly=True)

    pca_currency_id: int = fields.Many2one('res.currency', string='Moneda PCA', readonly=True)
    pca: float = fields.Monetary(
        string='PCA', currency_field='pca_currency_id', readonly=True,
    )

    def init(self) -> None:
        """Vista SQL consolidada del holding (drill-down promotoría→agente→recibo).

        Mismo origen y filtros que el reporte por agente. Ver Arquitectura §6.3.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL(
            """
            CREATE VIEW %s AS (
                SELECT
                    r.id AS id,
                    r.promotoria_id AS promotoria_id,
                    r.agente_id AS agente_id,
                    p.aseguradora_id AS aseguradora_id,
                    p.producto_id AS producto_id,
                    p.ramo AS ramo,
                    r.fecha_pago AS fecha_pago,
                    r.pca_currency_id AS pca_currency_id,
                    r.pca_aplicada AS pca
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
