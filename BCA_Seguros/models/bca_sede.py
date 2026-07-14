from __future__ import annotations

from odoo import fields, models


class BcaSede(models.Model):
    """Sede / plaza de reclutamiento BCA.

    Catálogo simple usado como Many2one en el candidato (hr.applicant) para
    ubicar geográficamente el reclutamiento. La lista oficial de plazas la
    provee BCA (SI-Sede); data/bca_sedes_iniciales.xml es un seed placeholder.
    """

    _name = 'bca.sede'
    _description = 'Sede / Plaza de Reclutamiento BCA'
    _order = 'name'

    name: str = fields.Char(string='Sede', required=True)
    codigo: str = fields.Char(string='Código', copy=False)
    active: bool = fields.Boolean(string='Activa', default=True)

    # v19: models.Constraint() reemplaza _sql_constraints (deprecated en v19).
    # codigo nullable ⇒ UNIQUE permite múltiples NULL (NULL≠NULL en Postgres),
    # así que varias sedes sin código conviven; los códigos rellenados son únicos.
    _unique_codigo = models.Constraint(
        'UNIQUE(codigo)',
        'El código de la sede debe ser único',
    )
