from __future__ import annotations

from odoo import _, fields, models
from odoo.exceptions import UserError

RAMO_BITACORA_SELECTION = [
    ('vida', 'Vida'),
    ('gmm', 'GMM'),
]
MARCA_LINEA_SELECTION = [
    ('aplicado', 'Aplicado'),
    ('anulado', 'Anulado'),
    ('no_encontrada', 'Póliza no encontrada'),
    ('sin_recibo', 'Sin recibo pendiente'),
    ('advertencia', 'Advertencia'),
    ('error', 'Error'),
    ('info', 'Información'),
]


class BcaBitacoraImportacion(models.Model):
    """Cabecera de auditoría de cada corrida del wizard de cobranza.

    Inmutabilidad: write/unlink bloqueados salvo env.su (admin/crons).
    Solo se crea desde el wizard de cobranza (Etapa 8).
    """

    _name = 'bca.bitacora.importacion'
    _description = 'Bitácora de Importación de Cobranza'
    _inherit = ['mail.thread']
    _order = 'fecha_ejecucion desc'

    name: str = fields.Char(
        string='Folio',
        default=lambda self: self.env['ir.sequence'].next_by_code(
            'bca.bitacora.importacion'
        ),
        readonly=True,
        copy=False,
    )
    usuario_id: int = fields.Many2one(
        'res.users',
        string='Ejecutado por',
        required=True,
        readonly=True,
        default=lambda self: self.env.user,
    )
    fecha_ejecucion: fields.Datetime = fields.Datetime(
        string='Fecha de Ejecución',
        required=True,
        readonly=True,
        default=fields.Datetime.now,
    )
    aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        required=True,
        readonly=True,
        ondelete='restrict',
        domain=[('bca_tipo', '=', 'aseguradora')],
    )
    ramo: str = fields.Selection(
        RAMO_BITACORA_SELECTION,
        string='Ramo',
        readonly=True,
    )
    nombre_archivo: str = fields.Char(string='Nombre del Archivo', readonly=True)
    archivo_adjunto: bytes = fields.Binary(
        string='Archivo Original',
        readonly=True,
        attachment=True,
    )
    total_filas: int = fields.Integer(string='Total de Filas', readonly=True)
    recibos_aplicados: int = fields.Integer(string='Recibos Aplicados', readonly=True)
    anulaciones_ignoradas: int = fields.Integer(
        string='Anulaciones Ignoradas',
        readonly=True,
    )
    polizas_no_encontradas: int = fields.Integer(
        string='Pólizas No Encontradas',
        readonly=True,
    )
    errores_procesamiento: int = fields.Integer(
        string='Errores de Procesamiento',
        readonly=True,
    )
    pca_total_sesion: float = fields.Monetary(
        string='PCA Total Sesión',
        currency_field='currency_id',
        readonly=True,
    )
    currency_id: int = fields.Many2one(
        'res.currency',
        string='Moneda',
        default=lambda self: self.env.company.currency_id,
        readonly=True,
    )
    linea_ids: list[int] = fields.One2many(
        'bca.bitacora.linea',
        'bitacora_id',
        string='Líneas',
        readonly=True,
    )

    def write(self, vals: dict) -> bool:
        if not self.env.su:
            raise UserError(_('La bitácora de importación es inmutable.'))
        return super().write(vals)

    def unlink(self) -> bool:
        if not self.env.su:
            raise UserError(_('La bitácora de importación es inmutable.'))
        return super().unlink()


class BcaBitacoraLinea(models.Model):
    """Detalle por fila del CSV procesado. Inmutable como la cabecera."""

    _name = 'bca.bitacora.linea'
    _description = 'Línea de Bitácora de Importación'
    _order = 'bitacora_id, numero_fila'

    bitacora_id: int = fields.Many2one(
        'bca.bitacora.importacion',
        string='Bitácora',
        required=True,
        ondelete='cascade',
        readonly=True,
        index=True,
    )
    numero_fila: int = fields.Integer(string='Número de Fila', readonly=True)
    marca: str = fields.Selection(
        MARCA_LINEA_SELECTION,
        string='Marca',
        required=True,
        readonly=True,
    )
    mensaje: str = fields.Text(string='Mensaje', readonly=True)
    numero_poliza_raw: str = fields.Char(
        string='Número de Póliza (CSV)',
        readonly=True,
        help='Valor exacto como aparece en el CSV (auditoría).',
    )
    recibo_id: int = fields.Many2one(
        'bca.recibo',
        string='Recibo Aplicado',
        ondelete='set null',
        readonly=True,
    )

    def write(self, vals: dict) -> bool:
        if not self.env.su:
            raise UserError(_('Las líneas de bitácora son inmutables.'))
        return super().write(vals)

    def unlink(self) -> bool:
        if not self.env.su:
            raise UserError(_('Las líneas de bitácora son inmutables.'))
        return super().unlink()
