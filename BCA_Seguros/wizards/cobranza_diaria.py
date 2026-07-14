from __future__ import annotations

import base64
import csv
import io
import logging
from datetime import datetime

from odoo import _, fields, models
from odoo.exceptions import UserError

from . import plantilla_cobranza_diaria
from ..parsers import get_parser

_logger = logging.getLogger(__name__)

# Ramos con parser real. Autos/Qualitas (placeholder) queda fuera del selector.
RAMO_COBRANZA_SELECTION = [
    ('vida', 'Vida'),
    ('gmm', 'GMM'),
]

# Marcas que cuentan como recibo efectivamente aplicado (la advertencia es un
# pago aplicado con un aviso de conducto sin match — R-COB-06).
MARCAS_APLICADAS = ('aplicado', 'advertencia')


class BcaWizardCobranzaDiaria(models.TransientModel):
    _name = 'bca.wizard.cobranza.diaria'
    _description = 'Wizard Cobranza Diaria desde CSV'

    # Sin 'required': el botón "Descargar plantilla" es type="object" y guarda
    # el wizard antes de ejecutarse; un archivo obligatorio bloquearía la
    # descarga (que precisamente sirve para obtener el archivo). La
    # obligatoriedad se valida en _abrir_csv al procesar.
    archivo: bytes = fields.Binary(string='Archivo de Cobranza (.csv)')
    nombre_archivo: str = fields.Char(string='Nombre del Archivo')
    aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        required=True,
        domain=[('bca_tipo', '=', 'aseguradora')],
        default=lambda self: self.env.ref(
            'BCA_Seguros.partner_metlife', raise_if_not_found=False
        ),
    )
    ramo: str = fields.Selection(
        RAMO_COBRANZA_SELECTION,
        string='Ramo',
        required=True,
        default='vida',
    )

    # ------------------------------------------------------------------ #
    # Acción única (una sola fase): la bitácora es el reporte auditable.
    # ------------------------------------------------------------------ #
    def action_procesar(self) -> dict:
        """Lee el CSV, aplica los pagos FIFO y abre la bitácora generada.

        Flujo (Plan Etapa 8): validar estructura (R-COB-09, fail-fast sin
        bitácora) → crear bitácora → filtrar (R-COB-01) → loop con savepoint
        por fila dentro del parser (R-COB-08) → totales → abrir bitácora.
        """
        self.ensure_one()
        inicio = datetime.now()
        reader = self._abrir_csv()
        fieldnames = reader.fieldnames or []

        codigo = self.aseguradora_id.bca_codigo_aseguradora
        if not codigo:
            raise UserError(_(
                'La aseguradora %s no tiene código configurado '
                '(campo "Código de Aseguradora").'
            ) % self.aseguradora_id.display_name)
        parser_cls = get_parser(codigo, self.ramo)

        # R-COB-09: estructura ANTES de crear la bitácora (classmethod).
        parser_cls.validar_estructura(fieldnames)

        bitacora = self.env['bca.bitacora.importacion'].sudo().create({
            'aseguradora_id': self.aseguradora_id.id,
            'ramo': self.ramo,
            'nombre_archivo': self.nombre_archivo,
            'archivo_adjunto': self.archivo,
        })

        parser = parser_cls(self.env, bitacora)
        filas = parser.filtrar_filas(list(reader))  # R-COB-01 (GMM omite anulados)

        BitacoraLinea = self.env['bca.bitacora.linea'].sudo()
        aplicados = no_encontradas = errores = 0
        pca_total = 0.0
        for numero_fila, fila in enumerate(filas, start=1):
            resultado = parser.procesar_fila(self.env, fila, numero_fila)
            BitacoraLinea.create({
                'bitacora_id': bitacora.id,
                'numero_fila': numero_fila,
                'marca': resultado['marca'],
                'mensaje': resultado.get('mensaje'),
                'numero_poliza_raw': resultado.get('numero_poliza_raw'),
                'recibo_id': resultado.get('recibo_id') or False,
            })
            if resultado['marca'] in MARCAS_APLICADAS:
                aplicados += 1
                if resultado.get('recibo_id'):
                    pca_total += self.env['bca.recibo'].browse(
                        resultado['recibo_id']
                    ).pca_aplicada
            elif resultado['marca'] == 'no_encontrada':
                no_encontradas += 1
            elif resultado['marca'] == 'error':
                errores += 1

        # No se sobreescribe anulaciones_ignoradas (lo fija filtrar_filas).
        bitacora.sudo().write({
            'total_filas': len(filas) + bitacora.anulaciones_ignoradas,
            'recibos_aplicados': aplicados,
            'polizas_no_encontradas': no_encontradas,
            'errores_procesamiento': errores,
            'pca_total_sesion': pca_total,
        })
        _logger.info(
            'Cobranza diaria %s (%s/%s): %s filas en %.2fs '
            '(%s aplicados, %s no encontradas, %s errores)',
            bitacora.name, codigo, self.ramo, len(filas),
            (datetime.now() - inicio).total_seconds(),
            aplicados, no_encontradas, errores,
        )
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'bca.bitacora.importacion',
            'res_id': bitacora.id,
            'view_mode': 'form',
            'target': 'current',
        }

    # ------------------------------------------------------------------ #
    # Descarga de plantilla
    # ------------------------------------------------------------------ #
    def action_descargar_plantilla(self) -> dict:
        """Genera la plantilla CSV del ramo seleccionado y la entrega.

        Los encabezados salen de ``parser_cls.columnas_requeridas`` (única
        fuente de verdad, compartida con la validación de estructura), por lo
        que lo que se descarga siempre pasa ``validar_estructura``. El adjunto
        se ata al registro transient para que el vacuum lo purgue.
        """
        self.ensure_one()
        codigo = self.aseguradora_id.bca_codigo_aseguradora
        if not codigo:
            raise UserError(_(
                'La aseguradora %s no tiene código configurado '
                '(campo "Código de Aseguradora").'
            ) % self.aseguradora_id.display_name)
        parser_cls = get_parser(codigo, self.ramo)
        datos = plantilla_cobranza_diaria.construir_csv_bytes(
            parser_cls.columnas_requeridas)
        adjunto = self.env['ir.attachment'].create({
            'name': 'plantilla_cobranza_%s_%s.csv' % (codigo.lower(), self.ramo),
            'datas': base64.b64encode(datos),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'text/csv',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % adjunto.id,
            'target': 'download',
        }

    # ------------------------------------------------------------------ #
    # Lectura del archivo
    # ------------------------------------------------------------------ #
    def _abrir_csv(self) -> csv.DictReader:
        """Decodifica el binario y devuelve un ``DictReader``.

        R-GLOB-01: los archivos de MetLife vienen en Latin-1. Se intenta
        ``utf-8-sig`` primero (robustez ante exportaciones modernas) y se cae
        a ``latin-1`` (que nunca falla al decodificar).
        """
        if not self.archivo:
            raise UserError(_('Debe adjuntar un archivo.'))
        crudo = base64.b64decode(self.archivo)
        try:
            texto = crudo.decode('utf-8-sig')
        except UnicodeDecodeError:
            texto = crudo.decode('latin-1')
        try:
            dialecto = csv.Sniffer().sniff(texto[:4096], delimiters=',;\t')
        except csv.Error:
            dialecto = csv.excel  # fallback: coma
        return csv.DictReader(io.StringIO(texto), dialect=dialecto)
