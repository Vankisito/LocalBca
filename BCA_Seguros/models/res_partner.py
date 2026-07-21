from __future__ import annotations

import re
import unicodedata

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Eje "posición en la RED de distribución de BCA" (excluyente por contacto). El
# cliente de BCA es la ASEGURADORA (a quien BCA cobra comisiones); contratante y
# asegurado NO viven aquí: son roles de póliza (no excluyentes) expresados en los
# flags computados bca_es_contratante / bca_es_asegurado.
TIPO_SELECTION = [
    ('holding', 'Holding'),
    ('aseguradora', 'Aseguradora'),
    ('promotoria', 'Promotoría'),
    ('agente', 'Agente'),
]
# Entidades estructurales de la red que NUNCA pueden ser contratante/asegurado de
# una póliza; se excluyen de la deduplicación de personas y del domain de póliza.
TIPOS_RED_EXCLUIDOS_POLIZA = ('aseguradora', 'promotoria', 'holding')
# Nomenclatura de carrera del agente (BDD §"Agentes — identidad y nomenclatura").
# Es el estado POR ASEGURADORA y vive en el modelo puente
# res.partner.agente.aseguradora. En res.partner, bca_estado_agente es un
# rollup computado de estos valores (ver _compute_bca_estado_agente).
# Solo 'clave_definitiva' computa para PCA.
ESTADO_AGENTE_SELECTION = [
    ('prospecto', 'Prospecto'),
    ('clave_arranque', 'Clave de Arranque'),
    ('clave_definitiva', 'Clave Definitiva'),
]
# Prioridad para el rollup: el "mejor" estado alcanzado en alguna aseguradora.
_ESTADO_AGENTE_PRIORIDAD = ['clave_definitiva', 'clave_arranque', 'prospecto']
ESTADO_CIVIL_SELECTION = [
    ('soltero', 'Soltero(a)'),
    ('casado', 'Casado(a)'),
    ('divorciado', 'Divorciado(a)'),
    ('viudo', 'Viudo(a)'),
    ('union_libre', 'Unión Libre'),
]
GENERO_SELECTION = [
    ('masculino', 'Masculino'),
    ('femenino', 'Femenino'),
    ('otro', 'Otro'),
]


class ResPartner(models.Model):
    _inherit = 'res.partner'

    bca_tipo: str = fields.Selection(
        TIPO_SELECTION,
        string='Tipo BCA',
        index=True,
    )
    # Rollup computado y almacenado del estado de carrera del agente: el "mejor"
    # estado alcanzado en cualquiera de sus aseguradoras (Definitiva > Arranque >
    # Prospecto; sin claves = Prospecto). NO se edita a mano: la fuente de verdad
    # es el modelo puente, que Reclutamiento alimenta vía automated actions.
    # Sirve solo para filtros/listas/visual; la PCA filtra por el estado del
    # PUENTE (clave_definitiva) por aseguradora, no por este campo.
    bca_estado_agente: str = fields.Selection(
        ESTADO_AGENTE_SELECTION,
        string='Estado Agente',
        compute='_compute_bca_estado_agente',
        store=True,
        index=True,
    )
    bca_codigo_aseguradora: str = fields.Char(
        string='Código Aseguradora',
        index=True,
    )

    # Datos demográficos del contratante (los faltantes en res.partner estándar).
    # RFC → campo estándar `vat`; domicilio → street/street2/city/zip/state_id.
    bca_fecha_nacimiento: fields.Date = fields.Date(string='Fecha de Nacimiento')
    bca_estado_civil: str = fields.Selection(
        ESTADO_CIVIL_SELECTION,
        string='Estado Civil',
    )
    bca_genero: str = fields.Selection(
        GENERO_SELECTION,
        string='Género',
    )
    # CURP: parte del Id interno PCA del agente (Nombre + RFC(`vat`) + CURP,
    # norma PCA Car. 2). RFC reusa el campo nativo `vat`. index para la búsqueda
    # de idempotencia de la conversión (Etapa 12 Fase C, D-15).
    bca_curp: str = fields.Char(
        string='CURP',
        index=True,
        copy=False,
    )

    # Referencias BANCARIAS de cobro que MetLife entrega en el layout de
    # portafolio: son las referencias con las que el CONTRATANTE paga a MetLife
    # cada concepto/fondo de su póliza (no importes, son cadenas de referencia).
    # NO son inventadas: cada campo se alimenta 1:1 de una columna del layout
    # (ver _datos_contratante en wizards/carga_portafolio.py). Se conservan como
    # Char por decisión de negocio (mantener el desglose por concepto que trae la
    # aseguradora); no se migran a res.partner.bank porque ese modelo no tiene
    # concepto/fondo nativo y se perdería el detalle.
    bca_ref_prima_basica_trad: str = fields.Char(
        string='Referencia Prima Básica (TRAD)',
        help="Layout MetLife Vida, columna 'Referencia Prima Básica (TRAD)'.",
    )
    bca_ref_prima_medica: str = fields.Char(
        string='Referencia Prima (MÉDICA)',
        help="Layout MetLife GMM, columna 'Referencia de cobro Prima (MEDICA)'.",
    )
    bca_fondo_variable: str = fields.Char(
        string='Fondo Variable',
        help="Layout MetLife Vida, columna 'Fondo Variable'.",
    )
    bca_fondo_fijo: str = fields.Char(
        string='Fondo Fijo',
        help="Layout MetLife Vida, columna 'Fondo Fijo'.",
    )
    bca_fondo_variable_ppr: str = fields.Char(
        string='Fondo Variable PPR',
        help="Layout MetLife Vida, 'Fondo Variable Plan Personal de Retiro (PPR)'.",
    )
    bca_fondo_fijo_ppr: str = fields.Char(
        string='Fondo Fijo PPR',
        help="Layout MetLife Vida, 'Fondo Fijo Plan Personal de Retiro (PPR)'.",
    )
    bca_fondo_variable_cpea: str = fields.Char(
        string='Fondo Variable CPEA',
        help="Layout MetLife Vida, 'Fondo Variable Cuenta Personal Especial de "
             "Ahorro (CPEA)'.",
    )
    bca_fondo_fijo_cpea: str = fields.Char(
        string='Fondo Fijo CPEA',
        help="Layout MetLife Vida, 'Fondo Fijo Cuenta Especial de Ahorro (CPEA)'.",
    )

    agente_aseguradora_ids: list[int] = fields.One2many(
        'res.partner.agente.aseguradora',
        'agente_id',
        string='Claves por Aseguradora',
    )

    # Roles de PÓLIZA (no excluyentes): un mismo contacto puede ser contratante
    # y asegurado a la vez, y además tener posición de red (p. ej. agente). Se
    # derivan de las pólizas (fuente única de verdad) vía estas relaciones
    # inversas; los flags almacenados sirven para filtros/visibilidad.
    bca_polizas_como_contratante: list[int] = fields.One2many(
        'bca.poliza',
        'contratante_id',
        string='Pólizas como Contratante',
    )
    bca_polizas_como_asegurado: list[int] = fields.One2many(
        'bca.poliza',
        'asegurado_id',
        string='Pólizas como Asegurado',
    )
    bca_es_contratante: bool = fields.Boolean(
        string='Es Contratante',
        compute='_compute_bca_roles_poliza',
        store=True,
    )
    bca_es_asegurado: bool = fields.Boolean(
        string='Es Asegurado',
        compute='_compute_bca_roles_poliza',
        store=True,
    )

    # C2: computed SIN store — retorna parent_id en tiempo real, nunca stale data.
    # search= permite filtrabilidad desde domain y search_read de la API.
    bca_promotoria_id: int = fields.Many2one(
        'res.partner',
        string='Promotoría',
        compute='_compute_promotoria_id',
        store=False,
        search='_search_promotoria_id',
    )
    bca_categoria_id: int = fields.Many2one(
        'res.partner.category',
        string='Categoría BCA',
        compute='_compute_categoria_id',
    )

    # C1: contadores para smart buttons de Pólizas y Recibos. Un mismo contacto
    # puede acumular pólizas por rol de contratante (vía contratante_id) y/o de
    # agente (vía agente vigente); el contador es la unión de ambos.
    bca_poliza_count: int = fields.Integer(
        string='# Pólizas',
        compute='_compute_bca_counts',
    )
    bca_recibo_count: int = fields.Integer(
        string='# Recibos',
        compute='_compute_bca_counts',
    )

    @api.depends('bca_tipo', 'agente_aseguradora_ids.estado')
    def _compute_bca_estado_agente(self) -> None:
        """Rollup del estado de carrera: el mejor estado en cualquier aseguradora.

        Sin claves (o no-agente) → 'prospecto'. La fuente de verdad es el puente
        res.partner.agente.aseguradora; aquí solo se proyecta para filtros/listas.
        """
        for rec in self:
            if rec.bca_tipo != 'agente':
                rec.bca_estado_agente = False
                continue
            estados = set(rec.agente_aseguradora_ids.mapped('estado'))
            rec.bca_estado_agente = next(
                (e for e in _ESTADO_AGENTE_PRIORIDAD if e in estados),
                'prospecto',
            )

    @api.depends('bca_tipo', 'parent_id')
    def _compute_promotoria_id(self) -> None:
        for rec in self:
            rec.bca_promotoria_id = rec.parent_id if rec.bca_tipo == 'agente' else False

    def _search_promotoria_id(self, operator: str, value: object) -> list:
        return [('parent_id', operator, value)]

    @api.depends('bca_polizas_como_contratante', 'bca_polizas_como_asegurado')
    def _compute_bca_roles_poliza(self) -> None:
        """Deriva los roles de póliza (no excluyentes) desde las relaciones."""
        for rec in self:
            rec.bca_es_contratante = bool(rec.bca_polizas_como_contratante)
            rec.bca_es_asegurado = bool(rec.bca_polizas_como_asegurado)

    @staticmethod
    def _bca_norm_nombre(valor: str) -> str:
        """Normaliza un nombre para deduplicación: sin acentos, mayúsculas,
        espacios colapsados. 'Juan  Pérez ' y 'JUAN PEREZ' → 'JUAN PEREZ'."""
        if not valor:
            return ''
        sin_acentos = ''.join(
            c for c in unicodedata.normalize('NFKD', valor)
            if not unicodedata.combining(c)
        )
        return re.sub(r'\s+', ' ', sin_acentos).strip().upper()

    @api.depends('bca_tipo')
    def _compute_categoria_id(self) -> None:
        """Asigna categoría de contacto según bca_tipo.

        raise_if_not_found=False es OBLIGATORIO: el computed puede ejecutarse
        antes de que partner_categories.xml esté cargado en la instalación inicial,
        causando ValueError sin esta bandera.
        """
        xmlid_map = {
            'holding':     'BCA_Seguros.partner_cat_holding',
            'aseguradora': 'BCA_Seguros.partner_cat_aseguradora',
            'promotoria':  'BCA_Seguros.partner_cat_promotoria',
            'agente':      'BCA_Seguros.partner_cat_agente',
        }
        for rec in self:
            xmlid = xmlid_map.get(rec.bca_tipo)
            if xmlid:
                rec.bca_categoria_id = self.env.ref(xmlid, raise_if_not_found=False)
            else:
                rec.bca_categoria_id = False

    @api.depends(
        'bca_polizas_como_contratante', 'bca_polizas_como_asegurado', 'bca_tipo')
    def _compute_bca_counts(self) -> None:
        Poliza = self.env['bca.poliza']
        Recibo = self.env['bca.recibo']
        for rec in self:
            # Unión de roles: pólizas donde es contratante y/o agente.
            rec.bca_poliza_count = Poliza.search_count([
                '|', ('contratante_id', '=', rec.id), ('agente_id', '=', rec.id),
            ])
            rec.bca_recibo_count = Recibo.search_count([
                '|',
                ('poliza_id.contratante_id', '=', rec.id),
                ('agente_poliza_id', '=', rec.id),
            ])

    def action_view_bca_polizas(self) -> dict:
        self.ensure_one()
        domain = [
            '|', ('contratante_id', '=', self.id), ('agente_id', '=', self.id),
        ]
        # Contexto de creación: prioriza el rol de contratante; si es un agente
        # puro, precarga el agente.
        if self.bca_tipo == 'agente' and not self.bca_es_contratante:
            context = {'default_agente_id': self.id}
        else:
            context = {'default_contratante_id': self.id}
        return {
            'type': 'ir.actions.act_window',
            'name': _('Pólizas de %s') % self.display_name,
            'res_model': 'bca.poliza',
            'view_mode': 'list,form',
            'domain': domain,
            'context': context,
        }

    def action_view_bca_recibos(self) -> dict:
        self.ensure_one()
        domain = [
            '|',
            ('poliza_id.contratante_id', '=', self.id),
            ('agente_poliza_id', '=', self.id),
        ]
        return {
            'type': 'ir.actions.act_window',
            'name': _('Recibos de %s') % self.display_name,
            'res_model': 'bca.recibo',
            'view_mode': 'list,form',
            'domain': domain,
        }

    @api.model
    def _synced_commercial_fields(self) -> list:
        # BCA reutiliza parent_id para la jerarquía organizacional (Holding >
        # Promotoría > Agente), no para relaciones de subsidiaria legal como
        # asume el core. El RFC (vat) es personal por agente: si se deja en
        # la lista de "commercial fields", Odoo lo sincroniza automáticamente
        # hacia arriba y hacia abajo en la jerarquía (via _fields_sync /
        # _load_records_create), haciendo que todos los agentes de una misma
        # promotoría/holding terminen con el RFC del primero que se procese.
        return [f for f in super()._synced_commercial_fields() if f != 'vat']

    @api.constrains('bca_tipo', 'parent_id')
    def _check_jerarquia(self) -> None:
        """Valida que la jerarquía organizacional sea coherente:
        - Agente debe tener parent de tipo 'promotoria'
        - Promotoría debe tener parent de tipo 'holding'
        """
        for rec in self:
            if rec.bca_tipo == 'agente' and rec.parent_id:
                if rec.parent_id.bca_tipo != 'promotoria':
                    raise ValidationError(
                        f'Un agente debe pertenecer a una Promotoría BCA '
                        f'(parent actual: {rec.parent_id.bca_tipo or "sin tipo"}).'
                    )
            elif rec.bca_tipo == 'promotoria' and rec.parent_id:
                if rec.parent_id.bca_tipo != 'holding':
                    raise ValidationError(
                        f'Una Promotoría debe pertenecer a un Holding BCA '
                        f'(parent actual: {rec.parent_id.bca_tipo or "sin tipo"}).'
                    )
