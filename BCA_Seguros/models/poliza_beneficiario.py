from __future__ import annotations

from odoo import fields, models

PARENTESCO_SELECTION = [
    ('conyuge', 'Cónyuge'),
    ('hijo', 'Hijo(a)'),
    ('padre', 'Padre'),
    ('madre', 'Madre'),
    ('hermano', 'Hermano(a)'),
    ('otro', 'Otro'),
]


class BcaPolizaBeneficiario(models.Model):
    _name = 'bca.poliza.beneficiario'
    _description = 'Beneficiario de Póliza BCA'
    _order = 'poliza_id, porcentaje desc'

    poliza_id: int = fields.Many2one(
        'bca.poliza',
        string='Póliza',
        required=True,
        ondelete='cascade',
        index=True,
    )
    # Contacto genérico: NO se fuerza un bca_tipo porque un beneficiario suele
    # ser cónyuge/hijo que puede ser contratante en otra póliza, y bca_tipo es
    # de valor único.
    beneficiario_id: int = fields.Many2one(
        'res.partner',
        string='Beneficiario',
        required=True,
        ondelete='restrict',
    )
    parentesco: str = fields.Selection(
        PARENTESCO_SELECTION,
        string='Parentesco',
        help='Relación del beneficiario con el contratante.',
    )
    porcentaje: float = fields.Float(
        string='% al que tiene Derecho',
        digits=(5, 2),
        help='Porcentaje de la suma asegurada que corresponde al beneficiario. '
             'La suma de todos los beneficiarios debe ser 100%. Solo aplica a Vida.',
    )
    # Usado por los asegurados adicionales (dependientes) de GMM, que reúsan este
    # modelo. Para beneficiarios de Vida queda vacío.
    fecha_nacimiento: fields.Date = fields.Date(
        string='Fecha de Nacimiento',
        help='Fecha de nacimiento del asegurado adicional (dependiente). '
             'Solo aplica para ramo GMM.',
    )
