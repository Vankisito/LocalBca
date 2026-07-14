from __future__ import annotations

from odoo import _, api, fields, models
from odoo.exceptions import AccessError, RedirectWarning, UserError, ValidationError

ESTADO_RECIBO_SELECTION = [
    ('pendiente', 'Pendiente'),
    ('pagado', 'Pagado'),
    ('cancelado', 'Cancelado'),
]

CAMPOS_PCA_PROTEGIDOS = {'pca_aplicada', 'factor_aplicado', 'pca_currency_id'}


class BcaRecibo(models.Model):
    _name = 'bca.recibo'
    _description = 'Recibo de Póliza BCA'
    _inherit = ['mail.thread']
    _order = 'poliza_id, numero_recibo'

    name: str = fields.Char(
        string='Folio',
        default=lambda self: self.env['ir.sequence'].next_by_code('bca.recibo'),
        readonly=True,
        copy=False,
    )
    poliza_id: int = fields.Many2one(
        'bca.poliza',
        string='Póliza',
        required=True,
        ondelete='restrict',
        index=True,
    )
    # Foto inmutable del agente/promotoría al momento del pago.
    # Asignado por action_registrar_pago — NO confiar en poliza.agente_id
    # para reportes históricos (puede cambiar vía cambiar_agente()).
    agente_id: int = fields.Many2one(
        'res.partner',
        string='Agente (al pagar)',
        ondelete='restrict',
        domain=[('bca_tipo', '=', 'agente')],
    )
    promotoria_id: int = fields.Many2one(
        'res.partner',
        string='Promotoría (al pagar)',
        ondelete='restrict',
    )
    # Agente VIGENTE de la póliza (no la foto al pagar). Siempre poblado, aun en
    # recibos pendientes — usado para agrupar la lista por agente sin que los
    # pendientes caigan en el grupo "Ninguno".
    agente_poliza_id: int = fields.Many2one(
        'res.partner',
        string='Agente (póliza)',
        related='poliza_id.agente_id',
        store=True,
        index=True,
    )
    numero_recibo: int = fields.Integer(
        string='Número de Recibo',
        readonly=True,
        help='Secuencia dentro de la póliza (1, 2, 3...).',
    )
    fecha_desde: fields.Date = fields.Date(string='Cobertura Desde', required=True)
    fecha_hasta: fields.Date = fields.Date(string='Cobertura Hasta', required=True)

    monto_modal: float = fields.Monetary(
        string='Prima Modal',
        currency_field='currency_id',
    )
    recargo: float = fields.Monetary(
        string='Recargo',
        currency_field='currency_id',
    )
    prima_neta: float = fields.Monetary(
        string='Prima Neta',
        currency_field='currency_id',
        help='Base para el cálculo de PCA.',
    )
    prima_total: float = fields.Monetary(
        string='Prima Total',
        currency_field='currency_id',
        help='Lo que paga el cliente (incluye recargo e impuestos).',
    )
    currency_id: int = fields.Many2one(
        'res.currency',
        related='poliza_id.currency_id',
        store=True,
        readonly=True,
    )

    estado: str = fields.Selection(
        ESTADO_RECIBO_SELECTION,
        string='Estado',
        default='pendiente',
        required=True,
        tracking=True,
        index=True,
    )
    fecha_pago: fields.Date = fields.Date(string='Fecha de Pago')
    conducto_id: int = fields.Many2one(
        'bca.conducto',
        string='Conducto',
        ondelete='restrict',
    )
    folio_endoso: str = fields.Char(
        string='Folio de Endoso',
        help='Solo aplica para ramo GMM.',
    )

    # PCA congelada al pago. Inmutable salvo por env.su o cancelación autorizada.
    # Se expresa SIEMPRE en MXN (decisión D-08), por eso usa pca_currency_id
    # (no currency_id, que es la moneda de la póliza y puede ser USD).
    pca_currency_id: int = fields.Many2one(
        'res.currency',
        string='Moneda PCA',
        readonly=True,
        default=lambda self: (
            self.env.ref('base.MXN', raise_if_not_found=False)
            or self.env.company.currency_id
        ),
    )
    pca_aplicada: float = fields.Monetary(
        string='PCA Aplicada',
        currency_field='pca_currency_id',
        readonly=True,
        tracking=True,
    )
    factor_aplicado: float = fields.Float(
        string='Factor Aplicado',
        digits=(6, 4),
        readonly=True,
        tracking=True,
    )
    motivo_exclusion_pca: str = fields.Char(
        string='Motivo Exclusión PCA',
        help='Razón por la que la PCA es 0 (ej: aportación adicional).',
    )
    bitacora_linea_id: int = fields.Many2one(
        'bca.bitacora.linea',
        string='Línea de Bitácora',
        ondelete='set null',
        help='Línea de la importación de cobranza que generó este pago.',
    )

    # Unicidad del número de recibo dentro de una póliza.
    _unique_numero_por_poliza = models.Constraint(
        'UNIQUE(poliza_id, numero_recibo)',
        'El número de recibo debe ser único dentro de cada póliza.',
    )

    @api.constrains('fecha_desde', 'fecha_hasta')
    def _check_fechas(self) -> None:
        for rec in self:
            if rec.fecha_desde and rec.fecha_hasta and rec.fecha_desde >= rec.fecha_hasta:
                raise ValidationError(
                    _('Fecha desde debe ser anterior a fecha hasta.')
                )

    @api.onchange('poliza_id')
    def _onchange_poliza_id(self) -> None:
        """R1: al elegir póliza en un recibo NUEVO, previsualiza el recibo
        pendiente más antiguo (FIFO). Al guardar, create() redirige al recibo
        existente en vez de duplicarlo."""
        if not self.poliza_id or self._origin.id:
            return
        pendiente = self.poliza_id.recibo_ids.filtered(
            lambda r: r.estado == 'pendiente'
        ).sorted('numero_recibo')[:1]
        if not pendiente:
            return {'warning': {
                'title': _('Sin recibos pendientes'),
                'message': _('La póliza %s no tiene recibos pendientes para cobrar.')
                           % self.poliza_id.name,
            }}
        self.numero_recibo = pendiente.numero_recibo
        self.fecha_desde = pendiente.fecha_desde
        self.fecha_hasta = pendiente.fecha_hasta
        self.monto_modal = pendiente.monto_modal
        self.recargo = pendiente.recargo
        self.prima_neta = pendiente.prima_neta
        self.prima_total = pendiente.prima_total

    @api.model_create_multi
    def create(self, vals_list: list[dict]) -> object:
        """R1: la creación manual de un recibo para una póliza que ya tiene un
        pendiente redirige a ese recibo (los recibos nacen del plan de pagos,
        no a mano). La generación interna del plan pasa `bca_generando_plan`."""
        if not self.env.context.get('bca_generando_plan'):
            for vals in vals_list:
                poliza_id = vals.get('poliza_id')
                if not poliza_id:
                    continue
                pendiente = self.env['bca.poliza'].browse(poliza_id).recibo_ids.filtered(
                    lambda r: r.estado == 'pendiente'
                ).sorted('numero_recibo')[:1]
                if pendiente:
                    raise RedirectWarning(
                        _('La póliza ya tiene el recibo pendiente %s. Abrilo para '
                          'registrar el pago en lugar de crear uno nuevo.')
                        % pendiente.name,
                        {
                            'type': 'ir.actions.act_window',
                            'res_model': 'bca.recibo',
                            'res_id': pendiente.id,
                            'view_mode': 'form',
                            'views': [(False, 'form')],
                            'target': 'current',
                        },
                        _('Abrir recibo pendiente'),
                    )
        return super().create(vals_list)

    def write(self, vals: dict) -> bool:
        """C1: bloquea edición de PCA en recibos pagados.

        Escape autorizado:
        - self.env.su (superusuario / acciones internas del módulo)
        - bypass explícito vía contexto allow_pca_edit=True (usado por
          action_cancelar_pago tras chequeo de grupo).
        """
        if (set(vals) & CAMPOS_PCA_PROTEGIDOS
                and not self.env.su
                and not self.env.context.get('allow_pca_edit')):
            for rec in self:
                if rec.estado == 'pagado':
                    raise UserError(
                        _('PCA y factor de recibo pagado son inmutables '
                          '(recibo %s).') % rec.name
                    )
        return super().write(vals)

    def action_registrar_pago(self, vals: dict) -> bool:
        """R-COB-09: valida precondiciones ANTES de tocar BD.

        Si fecha_pago o prima_neta no vienen, levantamos sin haber
        modificado nada — la BD queda intacta y el recibo sigue pendiente.
        """
        if not vals.get('fecha_pago'):
            raise ValidationError(_('La fecha de pago es obligatoria.'))
        if not vals.get('prima_neta') or vals['prima_neta'] <= 0:
            raise ValidationError(_('La prima neta debe ser un valor positivo.'))

        for rec in self:
            if rec.estado != 'pendiente':
                raise UserError(
                    _("Solo se pueden pagar recibos en estado 'Pendiente' "
                      "(recibo %s, estado %s).") % (rec.name, rec.estado)
                )

            # FIFO: este recibo debe ser el más antiguo pendiente de la póliza.
            pendientes = rec.poliza_id.recibo_ids.filtered(
                lambda r: r.estado == 'pendiente'
            )
            fifo = pendientes.sorted('numero_recibo')[:1]
            if fifo and fifo.id != rec.id:
                raise UserError(
                    _('Debe pagarse el recibo %s antes que el %s (FIFO).')
                    % (fifo.name, rec.name)
                )

            # La PCA depende de la fecha de pago: vigencia del factor en el
            # catálogo y, en multimoneda, la tasa de conversión a esa fecha.
            # El cálculo corre ANTES del write principal (para usar la prima del
            # plan), así que fijamos fecha_pago primero — de lo contrario el
            # calculador lee recibo.fecha_pago=False y `vigencia_desde <= False`
            # no encuentra el factor vigente (PCA quedaría en 0).
            rec.fecha_pago = vals['fecha_pago']
            pca, factor, motivo = rec._calcular_pca()
            # Usa super().write para esquivar nuestro propio bloqueo de write()
            # (el recibo aún no está 'pagado' cuando entra aquí, pero el
            # contexto allow_pca_edit deja explícita la autoría del cambio).
            super(BcaRecibo, rec.with_context(allow_pca_edit=True)).write({
                'estado': 'pagado',
                'fecha_pago': vals['fecha_pago'],
                'prima_neta': vals['prima_neta'],
                'prima_total': vals.get('prima_total', vals['prima_neta']),
                'recargo': vals.get('recargo', 0.0),
                'conducto_id': vals.get('conducto_id'),
                'folio_endoso': vals.get('folio_endoso'),
                'agente_id': rec.poliza_id.agente_id.id,
                'promotoria_id': rec.poliza_id.promotoria_id.id,
                'pca_aplicada': pca,
                'pca_currency_id': (
                    self.env.ref('base.MXN', raise_if_not_found=False)
                    or self.env.company.currency_id
                ).id,
                'factor_aplicado': factor,
                'motivo_exclusion_pca': motivo,
                'bitacora_linea_id': vals.get('bitacora_linea_id'),
            })

            # P5: si se pagó el último pendiente de la anualidad y aún queda
            # término, generar la siguiente anualidad (avance automático).
            if not rec.poliza_id.recibo_ids.filtered(lambda r: r.estado == 'pendiente'):
                rec.poliza_id._generar_siguiente_anualidad()
        return True

    def action_registrar_pago_ui(self) -> bool:
        """Wrapper UI: toma los valores ya editados en el form y registra el pago.

        Diseñado para el botón "Registrar Pago" del form view. El usuario debe
        haber completado fecha_pago, prima_neta y conducto_id antes de presionar.
        """
        self.ensure_one()
        # R4: el conducto es obligatorio para cobrar (solo en el flujo UI; el
        # método núcleo lo deja flexible para imports/llamadas programáticas).
        if not self.conducto_id:
            raise ValidationError(
                _('El conducto es obligatorio para registrar el pago.')
            )
        return self.action_registrar_pago({
            'fecha_pago': self.fecha_pago,
            'prima_neta': self.prima_neta,
            'prima_total': self.prima_total or self.prima_neta,
            'recargo': self.recargo,
            'conducto_id': self.conducto_id.id,
            'folio_endoso': self.folio_endoso,
        })

    def action_cancelar_pago(self) -> bool:
        """M5/R6: deshace el PAGO — el recibo vuelve a 'pendiente' y se limpian
        los datos del pago. NO anula el recibo (para eso, action_anular_recibo).
        Solo Director General o Director Comercial.

        Validación explícita de grupo además de la ACL — la ACL restringe
        write/unlink pero no impide ejecutar el método por sí sola.
        """
        if not (self.env.user.has_group('BCA_Seguros.group_bca_director')
                or self.env.user.has_group('BCA_Seguros.group_bca_director_comercial')):
            raise AccessError(
                _('Solo Director General o Director Comercial pueden cancelar pagos.')
            )
        for rec in self:
            if rec.estado != 'pagado':
                raise UserError(
                    _("Solo se pueden cancelar pagos de recibos en estado 'Pagado' "
                      "(recibo %s, estado %s).") % (rec.name, rec.estado)
                )
            # Guardia FIFO: solo el último recibo pagado puede revertirse, para
            # no dejar un pendiente antes de un pagado.
            posteriores = rec.poliza_id.recibo_ids.filtered(
                lambda r: r.estado == 'pagado' and r.numero_recibo > rec.numero_recibo
            )
            if posteriores:
                ultimo = posteriores.sorted('numero_recibo', reverse=True)[:1]
                raise UserError(
                    _('Cancelá primero el pago del recibo %s (FIFO).') % ultimo.name
                )
            rec.with_context(allow_pca_edit=True).write({
                'estado': 'pendiente',
                'fecha_pago': False,
                'conducto_id': False,
                'folio_endoso': False,
                'pca_aplicada': 0.0,
                'factor_aplicado': 0.0,
                'motivo_exclusion_pca': False,
                'agente_id': False,
                'promotoria_id': False,
                'bitacora_linea_id': False,
            })
        return True

    def action_anular_recibo(self) -> bool:
        """R6: anula el RECIBO (no se cobrará nunca) → estado 'cancelado'.
        Solo desde 'pendiente'; si está pagado hay que cancelar el pago primero.
        Solo Director General o Director Comercial.
        """
        if not (self.env.user.has_group('BCA_Seguros.group_bca_director')
                or self.env.user.has_group('BCA_Seguros.group_bca_director_comercial')):
            raise AccessError(
                _('Solo Director General o Director Comercial pueden anular recibos.')
            )
        for rec in self:
            if rec.estado != 'pendiente':
                raise UserError(
                    _("Solo se pueden anular recibos en estado 'Pendiente' "
                      "(recibo %s, estado %s). Si está pagado, cancelá el pago primero.")
                    % (rec.name, rec.estado)
                )
            rec.estado = 'cancelado'
        return True

    def _calcular_pca(self) -> tuple:
        """Delega al calculador de PCA registrado para la aseguradora.

        Retorna (pca, factor_aplicado, motivo_exclusion) con la PCA en MXN.
        El registry levanta UserError si la aseguradora no tiene calculador
        asignado (ej. Qualitas/Autos, diferido a post-v1).
        """
        from ..calculadores_pca import CALCULADOR_REGISTRY
        self.ensure_one()
        codigo = self.poliza_id.aseguradora_id.bca_codigo_aseguradora
        if not codigo:
            raise UserError(
                _('La aseguradora %s no tiene código asignado.')
                % self.poliza_id.aseguradora_id.display_name
            )
        if codigo not in CALCULADOR_REGISTRY:
            raise UserError(
                _('No hay calculador de PCA registrado para %s.') % codigo
            )
        return CALCULADOR_REGISTRY[codigo](self.env).calcular(self)
