from __future__ import annotations

from odoo import fields, models, tools
from odoo.tools import SQL

from ..models.product_template import RAMO_SELECTION


class BcaReportePcaPromotoria(models.Model):
    _name = 'bca.reporte.pca.promotoria'
    _description = 'Reporte PCA por Promotoría'
    _auto = False
    _rec_name = 'promotoria_id'

    # Dimensiones (agregado por promotoría / aseguradora / ramo).
    promotoria_id: int = fields.Many2one('res.partner', string='Promotoría', readonly=True)
    aseguradora_id: int = fields.Many2one('res.partner', string='Aseguradora', readonly=True)
    ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo', readonly=True)

    # Métricas — PCA en MXN (D-08). recibo_count para densidad de cartera.
    pca_currency_id: int = fields.Many2one('res.currency', string='Moneda PCA', readonly=True)
    pca: float = fields.Monetary(
        string='PCA', currency_field='pca_currency_id', readonly=True,
    )
    recibo_count: int = fields.Integer(string='# Recibos', readonly=True)

    def init(self) -> None:
        """Vista SQL agregada de PCA por promotoría.

        Mismo origen y filtros que el reporte por agente (recibo pagado +
        agente con clave definitiva en esa aseguradora), agregando por
        promotoría / aseguradora / ramo. El `id` se sintetiza por grupo con
        row_number() (las vistas pivot/graph solo necesitan un id único).
        Ver Arquitectura §6.2.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL(
            """
            CREATE VIEW %s AS (
                SELECT
                    row_number() OVER () AS id,
                    sub.promotoria_id AS promotoria_id,
                    sub.aseguradora_id AS aseguradora_id,
                    sub.ramo AS ramo,
                    sub.pca_currency_id AS pca_currency_id,
                    sub.pca AS pca,
                    sub.recibo_count AS recibo_count
                FROM (
                    SELECT
                        r.promotoria_id AS promotoria_id,
                        p.aseguradora_id AS aseguradora_id,
                        p.ramo AS ramo,
                        r.pca_currency_id AS pca_currency_id,
                        SUM(r.pca_aplicada) AS pca,
                        COUNT(r.id) AS recibo_count
                    FROM bca_recibo r
                    JOIN bca_poliza p ON r.poliza_id = p.id
                    JOIN res_partner_agente_aseguradora aa
                         ON aa.agente_id = r.agente_id
                        AND aa.aseguradora_id = p.aseguradora_id
                    WHERE r.estado = 'pagado'
                      AND aa.estado = 'clave_definitiva'
                    GROUP BY
                        r.promotoria_id,
                        p.aseguradora_id,
                        p.ramo,
                        r.pca_currency_id
                ) sub
            )
            """,
            SQL.identifier(self._table),
        ))
