from __future__ import annotations

from odoo import fields, models, tools
from odoo.tools import SQL

from ..models.product_template import RAMO_SELECTION

ESTADO_CARTERA_SELECTION = [
    ('vigente', 'Vigente'),
    ('en_riesgo', 'En Riesgo'),
    ('caida', 'Caída'),
]


class BcaReporteEstadoCartera(models.Model):
    _name = 'bca.reporte.estado.cartera'
    _description = 'Reporte Estado de Cartera'
    _auto = False
    _rec_name = 'poliza_id'

    # Grano: una póliza activa.
    poliza_id: int = fields.Many2one('bca.poliza', string='Póliza', readonly=True)
    # agente_id es el VIGENTE de la póliza (no la foto): la cartera viva refleja
    # quién atiende hoy la póliza. promotoria_id sale de agente_id.parent_id
    # (la póliza no almacena promotoría — es computed sin store).
    agente_id: int = fields.Many2one('res.partner', string='Agente', readonly=True)
    promotoria_id: int = fields.Many2one('res.partner', string='Promotoría', readonly=True)
    aseguradora_id: int = fields.Many2one('res.partner', string='Aseguradora', readonly=True)
    producto_id: int = fields.Many2one('product.template', string='Producto', readonly=True)
    ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo', readonly=True)
    pagado_hasta: fields.Date = fields.Date(string='Pagado Hasta', readonly=True)
    estado_cartera: str = fields.Selection(
        ESTADO_CARTERA_SELECTION, string='Estado de Cartera', readonly=True,
    )

    currency_id: int = fields.Many2one('res.currency', string='Moneda', readonly=True)
    prima_anual: float = fields.Monetary(
        string='Prima Anual', currency_field='currency_id', readonly=True,
    )
    poliza_count: int = fields.Integer(string='# Pólizas', readonly=True)

    def init(self) -> None:
        """Vista SQL del estado de cartera (una fila por póliza activa).

        Clasificación por `pagado_hasta` vs hoy (Arquitectura §6.4):
          - caida     → pagado_hasta < hoy (o sin pagos)
          - en_riesgo → hoy <= pagado_hasta < hoy + 30 días
          - vigente   → pagado_hasta >= hoy + 30 días
        El umbral de 30 días replica `bca_seguros.dias_gracia_pago`
        (data/config_parameters.xml); como literal SQL, no se lee el parámetro.
        """
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute(SQL(
            """
            CREATE VIEW %s AS (
                SELECT
                    p.id AS id,
                    p.id AS poliza_id,
                    p.agente_id AS agente_id,
                    ag.parent_id AS promotoria_id,
                    p.aseguradora_id AS aseguradora_id,
                    p.producto_id AS producto_id,
                    p.ramo AS ramo,
                    p.pagado_hasta AS pagado_hasta,
                    p.currency_id AS currency_id,
                    p.prima_anual AS prima_anual,
                    1 AS poliza_count,
                    CASE
                        WHEN p.pagado_hasta IS NULL
                          OR p.pagado_hasta < CURRENT_DATE
                            THEN 'caida'
                        WHEN p.pagado_hasta < CURRENT_DATE + INTERVAL '30 day'
                            THEN 'en_riesgo'
                        ELSE 'vigente'
                    END AS estado_cartera
                FROM bca_poliza p
                LEFT JOIN res_partner ag ON ag.id = p.agente_id
                WHERE p.estado = 'activa'
            )
            """,
            SQL.identifier(self._table),
        ))
