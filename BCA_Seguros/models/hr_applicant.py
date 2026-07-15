from __future__ import annotations

import logging
import re

from dateutil.relativedelta import relativedelta
from psycopg2 import IntegrityError

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError

from .product_template import RAMO_SELECTION
from .res_partner import GENERO_SELECTION

_logger = logging.getLogger(__name__)

# Niveles de compatibilidad PDA (Etapa 12 Fase B, HU-1.3). Constante de módulo
# (patrón del proyecto). Los niveles 'no_ideal' y 'baja' marcan riesgo y activan
# la compuerta L1 (requieren visto bueno del promotor para avanzar).
PDA_NIVEL_SELECTION = [
    ('ideal', 'Ideal'),
    ('recomendado', 'Recomendado'),
    ('aceptable', 'Aceptable'),
    ('no_ideal', 'No Ideal'),
    ('baja', 'Baja Compatibilidad'),
]
_PDA_NIVELES_RIESGO = ('no_ideal', 'baja')

# Validación de formato de identidad mexicana (Etapa 12, HU-1.4). Se valida el
# patrón sobre el valor en mayúsculas/sin espacios; el contenido vacío se permite
# (los campos se capturan en etapas tempranas). RFC: física (13) o moral (12).
_RFC_REGEX = re.compile(r'^[A-ZÑ&]{3,4}\d{6}[A-Z0-9]{3}$')
# CURP: 18 posiciones con dígito verificador (patrón oficial RENAPO).
_CURP_REGEX = re.compile(
    r'^[A-Z][AEIOUX][A-Z]{2}\d{6}[HM][A-Z]{2}[B-DF-HJ-NP-TV-Z]{3}[A-Z0-9]\d$'
)


class HrApplicant(models.Model):
    _inherit = 'hr.applicant'

    bca_promotoria_destino_id: int = fields.Many2one(
        'res.partner',
        string='Promotoría destino',
        domain=[('bca_tipo', '=', 'promotoria')],
        help='Promotoría a la que se afiliará el agente al ser contratado. '
             'Requerido cuando el puesto es "Reclutamiento de Agente".',
        tracking=True,
    )

    # --- Identificación / perfil del candidato (Etapa 12 Fase A, HU-1.2) ---
    # Campos de captura sin lógica. RFC → campo estándar `vat`; nombre →
    # partner_name; teléfono → partner_phone; correo → email_from (se reusan,
    # no se redefinen). Género/ramo reusan las selecciones ya existentes.
    bca_sede_id: int = fields.Many2one(
        'bca.sede',
        string='Sede / Plaza',
        ondelete='set null',
        help='Plaza donde se recluta al candidato.',
    )
    bca_ramo: str = fields.Selection(RAMO_SELECTION, string='Ramo')
    bca_genero: str = fields.Selection(GENERO_SELECTION, string='Género')
    bca_fecha_nacimiento: fields.Date = fields.Date(string='Fecha de Nacimiento')
    bca_edad: int = fields.Integer(
        string='Edad',
        compute='_compute_bca_edad',
        store=False,
        help='Edad calculada a la fecha actual desde la fecha de nacimiento. '
             'No se almacena (cambia con el tiempo); para segmentar por edad '
             'en reportes use rangos de fecha de nacimiento.',
    )
    bca_institucion: str = fields.Char(string='Institución Educativa')
    bca_folio_cv: str = fields.Char(string='Folio CV', copy=False)
    # Campos de perfil que se muestran en la pestaña nativa "Detalles" (D-19).
    # Perfil académico se cubre con el nativo `type_id` (Grado); el origen del
    # candidato con `source_id`/`medium_id`/`campaign_id` nativos; el seguimiento
    # (contactado/entrevistado/reagendaciones) con el embudo de etapas + actividades.
    # El "tipo de candidato" también se cubre con el origen nativo (D-21, retirado).
    bca_perfil_laboral: str = fields.Char(string='Perfil Laboral')

    @api.depends('bca_fecha_nacimiento')
    def _compute_bca_edad(self) -> None:
        """Edad a la fecha actual. No almacenado: se recalcula en cada lectura."""
        today = fields.Date.context_today(self)
        for applicant in self:
            if applicant.bca_fecha_nacimiento:
                applicant.bca_edad = relativedelta(
                    today, applicant.bca_fecha_nacimiento,
                ).years
            else:
                applicant.bca_edad = 0

    # --- Evaluación PDA + compuerta de riesgo L1 (Etapa 12 Fase B, HU-1.3) ---
    bca_pda_nivel: str = fields.Selection(
        PDA_NIVEL_SELECTION, string='Nivel PDA', copy=False,
    )
    bca_pda_correlacion: float = fields.Float(string='Correlación PDA', copy=False)
    bca_pda_perfil: str = fields.Char(string='Perfil PDA', copy=False)
    bca_pda_visto_bueno_promotor: bool = fields.Boolean(
        string='Visto Bueno del Promotor', copy=False,
        help='El promotor autoriza avanzar pese al nivel PDA de riesgo.',
    )
    bca_pda_riesgo: bool = fields.Boolean(
        string='PDA en Riesgo',
        compute='_compute_bca_pda_riesgo',
        store=True,
        copy=False,
        help='Verdadero cuando el nivel PDA es "No Ideal" o "Baja Compatibilidad". '
             'Bloquea avanzar más allá de "Evaluación PDA" sin visto bueno (L1).',
    )

    @api.depends('bca_pda_nivel')
    def _compute_bca_pda_riesgo(self) -> None:
        """Riesgo PDA: niveles no_ideal / baja."""
        for applicant in self:
            applicant.bca_pda_riesgo = applicant.bca_pda_nivel in _PDA_NIVELES_RIESGO

    @api.constrains('stage_id', 'bca_pda_riesgo', 'bca_pda_visto_bueno_promotor')
    def _check_pda_gate(self) -> None:
        """L1: bloquea avanzar más allá de "Evaluación PDA" con riesgo sin VoBo.

        Solo aplica al embudo de reclutamiento de agentes. La etapa de corte se
        resuelve por `env.ref` y se compara por `sequence` (nunca por ID: D-13).
        """
        job_recl = self.env.ref(
            'BCA_Seguros.job_reclutamiento_agente', raise_if_not_found=False,
        )
        stage_pda = self.env.ref(
            'BCA_Seguros.stage_evaluacion_pda', raise_if_not_found=False,
        )
        if not job_recl or not stage_pda:
            return
        for applicant in self:
            if applicant.job_id != job_recl or not applicant.stage_id:
                continue
            if applicant.stage_id.sequence <= stage_pda.sequence:
                continue
            if applicant.bca_pda_riesgo and not applicant.bca_pda_visto_bueno_promotor:
                raise ValidationError(_(
                    'El candidato "%s" tiene un nivel PDA de riesgo y no puede '
                    'avanzar más allá de "Evaluación PDA" sin el visto bueno del '
                    'promotor de la promotoría destino.'
                ) % (applicant.partner_name or applicant.display_name))

    def _bca_notificar_riesgo_pda(self) -> None:
        """Al activarse el riesgo PDA sin VoBo, crea actividad para el promotor.

        SI-2: el promotor solo recibe la notificación. Idempotente: no duplica la
        actividad si ya existe una abierta para el mismo usuario.
        """
        self.ensure_one()
        job_recl = self.env.ref(
            'BCA_Seguros.job_reclutamiento_agente', raise_if_not_found=False,
        )
        if self.job_id != job_recl:
            return
        if not (self.bca_pda_riesgo and not self.bca_pda_visto_bueno_promotor):
            return
        if not self.bca_promotoria_destino_id:
            return
        # Promotor = usuario ligado a la promotoría; fallback a la reclutadora.
        promotor_user = self.bca_promotoria_destino_id.user_ids[:1] or self.user_id
        if not promotor_user:
            return
        summary = _('Visto bueno PDA requerido')
        ya_existe = self.activity_ids.filtered(
            lambda a: a.summary == summary and a.user_id == promotor_user,
        )
        if ya_existe:
            return
        nivel_label = dict(self._fields['bca_pda_nivel'].selection).get(
            self.bca_pda_nivel, self.bca_pda_nivel or '',
        )
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            summary=summary,
            note=_('El candidato tiene un nivel PDA de riesgo (%s). Se requiere '
                   'su visto bueno para que avance en el embudo.') % nivel_label,
            user_id=promotor_user.id,
        )

    # --- Datos de habilitación / emisión de cédula (Etapa 12 Fase C, HU-1.4) ---
    # RFC → bca_rfc (hr.applicant NO tiene `vat` nativo); se mapea a partner.vat
    # en la conversión. CURP → bca_curp; ambos forman el Id interno PCA (D-15).
    bca_clave_arranque: str = fields.Char(string='Clave de Arranque', copy=False)
    # Clave definitiva: se captura al llegar a la etapa "Clave Definitiva" y es
    # requisito para crear el empleado (Fase 3). NO promueve el estado del agente
    # a `clave_definitiva` en res.partner.agente.aseguradora (D-14/SI-4: eso es un
    # proceso interno posterior que sí computa PCA).
    bca_clave_definitiva: str = fields.Char(string='Clave Definitiva', copy=False)
    bca_fecha_cedula: fields.Date = fields.Date(string='Fecha de Cédula', copy=False)
    bca_aseguradora_id: int = fields.Many2one(
        'res.partner',
        string='Aseguradora',
        domain=[('bca_tipo', '=', 'aseguradora')],
        ondelete='restrict',
        copy=False,
    )
    bca_rfc: str = fields.Char(string='RFC', copy=False)
    bca_curp: str = fields.Char(string='CURP', index=True, copy=False)

    # Habilita el botón nativo "Create Employee" solo cuando el agente llega a la
    # etapa "Clave Definitiva" (#9). Para el resto de puestos deja el criterio
    # nativo intacto (True aquí; la vista mantiene el `date_closed` nativo).
    bca_puede_crear_empleado: bool = fields.Boolean(
        string='Puede crear empleado',
        compute='_compute_bca_puede_crear_empleado',
        store=False,
    )

    @api.depends('job_id', 'stage_id')
    def _compute_bca_puede_crear_empleado(self) -> None:
        job_recl = self.env.ref(
            'BCA_Seguros.job_reclutamiento_agente', raise_if_not_found=False,
        )
        stage_def = self.env.ref(
            'BCA_Seguros.stage_clave_definitiva', raise_if_not_found=False,
        )
        for applicant in self:
            if job_recl and applicant.job_id == job_recl:
                applicant.bca_puede_crear_empleado = bool(
                    stage_def and applicant.stage_id
                    and applicant.stage_id.sequence >= stage_def.sequence
                )
            else:
                applicant.bca_puede_crear_empleado = True

    @api.constrains('bca_rfc', 'bca_curp')
    def _check_identidad_formato(self) -> None:
        """Valida el formato de RFC y CURP mexicanos (solo si tienen valor)."""
        for applicant in self:
            if applicant.bca_rfc:
                rfc = applicant.bca_rfc.upper().strip()
                if not _RFC_REGEX.match(rfc):
                    raise ValidationError(_(
                        'El RFC "%s" no tiene un formato válido. Debe ser un RFC '
                        'mexicano (12 caracteres para persona moral o 13 para '
                        'persona física).'
                    ) % applicant.bca_rfc)
            if applicant.bca_curp:
                curp = applicant.bca_curp.upper().strip()
                if not _CURP_REGEX.match(curp):
                    raise ValidationError(_(
                        'La CURP "%s" no tiene un formato válido. Debe ser una CURP '
                        'mexicana de 18 caracteres.'
                    ) % applicant.bca_curp)

    @api.constrains('stage_id')
    def _check_habilitacion_datos(self) -> None:
        """L2: no se llega a una etapa hired del embudo comercial sin identidad.

        Aplica a AMBAS figuras comerciales (`job_reclutamiento_agente` y
        `job_captacion_promotoria`, paridad de bloqueo RFC/CURP); NO aplica a los
        puestos internos (embudo nativo). Los datos exigidos dependen del job:
        ver `_bca_datos_habilitacion_faltantes`.
        """
        job_recl = self.env.ref(
            'BCA_Seguros.job_reclutamiento_agente', raise_if_not_found=False,
        )
        job_capt = self.env.ref(
            'BCA_Seguros.job_captacion_promotoria', raise_if_not_found=False,
        )
        if not job_recl and not job_capt:
            return
        jobs_comerciales = self.env['hr.job'].browse(
            [j.id for j in (job_recl, job_capt) if j],
        )
        for applicant in self:
            if (applicant.job_id in jobs_comerciales and applicant.stage_id
                    and applicant.stage_id.hired_stage):
                faltantes = applicant._bca_datos_habilitacion_faltantes()
                if faltantes:
                    raise ValidationError(_(
                        'No se puede habilitar al candidato "%(nombre)s": faltan datos '
                        'de habilitación: %(faltantes)s.'
                    ) % {
                        'nombre': applicant.partner_name or applicant.display_name,
                        'faltantes': ', '.join(faltantes),
                    })

    def _bca_datos_habilitacion_faltantes(self) -> list:
        """Devuelve las etiquetas de los datos de habilitación ausentes.

        RFC + CURP se exigen a ambas figuras comerciales (paridad de identidad).
        Clave de Arranque, Fecha de Cédula y Aseguradora son licencia específica
        de agente ante una aseguradora: solo se exigen a `job_reclutamiento_agente`
        (la creación del puente `res.partner.agente.aseguradora` sigue siendo
        exclusiva de Agente; ver SDD §11.2, pendiente de confirmar para Promotor).
        """
        self.ensure_one()
        requeridos = [
            ('bca_rfc', _('RFC')),
            ('bca_curp', _('CURP')),
        ]
        job_recl = self.env.ref(
            'BCA_Seguros.job_reclutamiento_agente', raise_if_not_found=False,
        )
        if job_recl and self.job_id == job_recl:
            requeridos += [
                ('bca_clave_arranque', _('Clave de Arranque')),
                ('bca_fecha_cedula', _('Fecha de Cédula')),
                ('bca_aseguradora_id', _('Aseguradora')),
            ]
        return [label for field_name, label in requeridos if not self[field_name]]

    @api.constrains('stage_id', 'bca_rfc', 'bca_curp', 'email_from')
    def _check_habilitacion_datos_puesto_interno(self) -> None:
        """L2-interno (BUG-020): Puesto Interno no llega al hired nativo sin datos.

        Exclusivo de `job_interno` (D-24, revisión parcial de D-20/D-23); NO
        modifica `_check_habilitacion_datos` (ese sigue exclusivo de las figuras
        comerciales). La etapa de corte es cualquiera con `hired_stage=True`
        (hoy la nativa "Contract Signed"), resuelta por el campo `hired_stage`
        de la propia etapa, nunca por un xmlid hardcodeado de `hr_recruitment`.
        """
        job_interno = self.env.ref(
            'BCA_Seguros.job_interno', raise_if_not_found=False,
        )
        if not job_interno:
            return
        for applicant in self:
            if (applicant.job_id == job_interno and applicant.stage_id
                    and applicant.stage_id.hired_stage):
                faltantes = applicant._bca_datos_habilitacion_faltantes_interno()
                if faltantes:
                    raise ValidationError(_(
                        'No se puede habilitar al candidato "%(nombre)s" en '
                        '"%(etapa)s": faltan datos: %(faltantes)s.'
                    ) % {
                        'nombre': applicant.partner_name or applicant.display_name,
                        'etapa': applicant.stage_id.name,
                        'faltantes': ', '.join(faltantes),
                    })

    def _bca_datos_habilitacion_faltantes_interno(self) -> list:
        """BUG-020: RFC, CURP y correo mínimos para "Puesto Interno" hired."""
        self.ensure_one()
        requeridos = [
            ('bca_rfc', _('RFC')),
            ('bca_curp', _('CURP')),
            ('email_from', _('Correo electrónico')),
        ]
        return [label for field_name, label in requeridos if not self[field_name]]

    def write(self, vals: dict) -> bool:
        """Dispara la conversión por CRUCE de umbral de etapa (3 fases).

        Captura la secuencia de etapa previa por registro para detectar el cruce
        de cada umbral (Acuerdo de Arranque → contacto; Cédula Emitida → clave;
        Clave Definitiva → empleado) y disparar cada fase una sola vez, robusto a
        saltos de etapa. También notifica al promotor cuando el PDA marca riesgo.
        """
        prev_seq = {
            applicant.id: (applicant.stage_id.sequence if applicant.stage_id else None)
            for applicant in self
        }
        result = super().write(vals)
        if 'stage_id' in vals:
            for applicant in self:
                applicant._bca_procesar_transicion_etapa(prev_seq.get(applicant.id))
        if {'bca_pda_nivel', 'bca_pda_visto_bueno_promotor'} & vals.keys():
            for applicant in self:
                applicant._bca_notificar_riesgo_pda()
        return result

    def _bca_procesar_transicion_etapa(self, prev_seq) -> None:
        """Despacha la conversión por umbral de `sequence` de la etapa (D-13).

        Tres fases idempotentes en el embudo comercial, cada una disparada al
        CRUZAR su umbral desde una etapa inferior (una sola vez, robusto a saltos):
          - Acuerdo de Arranque: traspaso Reclutamiento→Capital Humano (#11) +
            creación del contacto res.partner (#10).
          - Cédula Emitida (hired): asienta la clave por aseguradora (clave_arranque).
          - Clave Definitiva: crea el hr.employee (exige bca_clave_definitiva, #9).
        Ignora silenciosamente los jobs no comerciales (puestos internos).
        """
        self.ensure_one()
        if not self.stage_id:
            return
        job_captacion = self.env.ref(
            'BCA_Seguros.job_captacion_promotoria', raise_if_not_found=False,
        )
        job_reclutamiento = self.env.ref(
            'BCA_Seguros.job_reclutamiento_agente', raise_if_not_found=False,
        )
        if not self.job_id or self.job_id not in (job_captacion, job_reclutamiento):
            return

        stage_acuerdo = self.env.ref(
            'BCA_Seguros.stage_acuerdo_arranque', raise_if_not_found=False,
        )
        stage_cedula = self.env.ref(
            'BCA_Seguros.stage_cedula_emitida', raise_if_not_found=False,
        )
        stage_definitiva = self.env.ref(
            'BCA_Seguros.stage_clave_definitiva', raise_if_not_found=False,
        )
        new_seq = self.stage_id.sequence

        def _cruza(threshold_stage) -> bool:
            if not threshold_stage:
                return False
            thr = threshold_stage.sequence
            return (prev_seq is None or prev_seq < thr) and new_seq >= thr

        # Fase 1 — Acuerdo de Arranque: traspaso de equipo + creación del contacto.
        if _cruza(stage_acuerdo):
            self._bca_traspaso_capital_humano()
            ya_tiene_partner = (
                self.partner_id and self.partner_id.bca_tipo in ('promotoria', 'agente')
            )
            if not ya_tiene_partner:
                if self.job_id == job_captacion:
                    self._bca_crear_promotoria()
                else:
                    self._bca_crear_partner_agente_basico()

        # Fase 2 — Cédula Emitida (hired): asienta la clave por aseguradora.
        if (self.job_id == job_reclutamiento and _cruza(stage_cedula)
                and self.partner_id and self.partner_id.bca_tipo == 'agente'):
            self._bca_crear_clave_aseguradora(self.partner_id)
            self._bca_actividad_habilitacion(self.partner_id)

        # Fase 3 — Clave Definitiva: crea el empleado (exige la clave definitiva).
        if self.job_id == job_reclutamiento and _cruza(stage_definitiva):
            if not self.bca_clave_definitiva:
                raise ValidationError(_(
                    'No se puede crear el empleado del agente "%s": debe capturar '
                    'primero la Clave Definitiva en la pestaña Habilitación.'
                ) % (self.partner_name or self.display_name))
            if self.partner_id and self.partner_id.bca_tipo == 'agente':
                empleado = self._bca_crear_empleado(self.partner_id)
                if empleado and not self.employee_id:
                    self.sudo().employee_id = empleado.id

    def _bca_traspaso_capital_humano(self) -> None:
        """Fase B (#11): traspasa la gestión de Reclutamiento a Capital Humano.

        Nativo, sin campos custom: preserva a la reclutadora actual como
        entrevistadora (`interviewer_ids`) y reasigna el responsable (`user_id`)
        al usuario de Capital Humano del parámetro
        `bca_reclutamiento.capital_humano_user_id`. Si el parámetro no está
        configurado, solo deja constancia en el chatter. Idempotente.
        """
        self.ensure_one()
        ch_param = self.env['ir.config_parameter'].sudo().get_param(
            'bca_reclutamiento.capital_humano_user_id',
        )
        ch_user = self.env['res.users']
        if ch_param and str(ch_param).isdigit():
            ch_user = self.env['res.users'].browse(int(ch_param)).exists()

        # Ya traspasado: el responsable actual ya es el de Capital Humano.
        if ch_user and self.user_id == ch_user:
            return

        reclutadora = self.user_id
        if reclutadora and reclutadora not in self.interviewer_ids:
            self.interviewer_ids = [(4, reclutadora.id)]

        if ch_user:
            self.user_id = ch_user
            self.message_post(body=_(
                'Traspaso a Capital Humano: responsable reasignado a '
                '<b>%(ch)s</b>; la reclutadora <b>%(recl)s</b> se conserva como '
                'entrevistadora.'
            ) % {'ch': ch_user.name, 'recl': reclutadora.name or '—'})
        else:
            self.message_post(body=_(
                'El candidato llegó a "Acuerdo de Arranque" (Fase B). Capital '
                'Humano debe tomar la gestión. Configure el parámetro '
                '<code>bca_reclutamiento.capital_humano_user_id</code> para la '
                'reasignación automática del responsable.'
            ))

    def _bca_crear_promotoria(self) -> None:
        """Captación: crea el res.partner promotoría bajo el holding Grupo BCA.

        Exige identidad (RFC + CURP, #5-paridad) del candidato a Promotor, igual
        que se exige al Agente en `_bca_crear_partner_agente_basico`. NO exige
        Promotoría destino ni Sede: son conceptos de Agente que no aplican aquí
        (el candidato a Promotor crea la promotoría, no se afilia a una).
        """
        self.ensure_one()
        requeridos = [
            (self.bca_rfc, _('RFC')),
            (self.bca_curp, _('CURP')),
        ]
        faltantes = [label for value, label in requeridos if not value]
        if faltantes:
            raise ValidationError(_(
                'No se puede generar el contacto de la promotoría "%(nombre)s" al '
                'llegar a "Acuerdo de Arranque": faltan datos: %(faltantes)s.'
            ) % {
                'nombre': self.partner_name or self.display_name,
                'faltantes': ', '.join(faltantes),
            })
        holding = self.env.ref(
            'BCA_Seguros.partner_bca_holding', raise_if_not_found=False,
        )
        if not holding:
            raise UserError(_(
                'No se encontró el partner Grupo BCA holding '
                '(BCA_Seguros.partner_bca_holding). Verifique que '
                'data/aseguradoras_iniciales.xml esté cargado.'
            ))
        partner = self.env['res.partner'].create({
            'name': self.partner_name or self.name,
            'email': self.email_from or False,
            'phone': self.partner_phone or False,
            'bca_tipo': 'promotoria',
            'parent_id': holding.id,
            'is_company': True,
            'vat': self.bca_rfc,
            'bca_curp': self.bca_curp,
        })
        self.partner_id = partner
        self._bca_log_partner_vinculado(partner)

    def _bca_crear_partner_agente_basico(self) -> None:
        """Fase 1 (#10): crea/reutiliza el res.partner agente en Acuerdo de Arranque.

        Exige identidad completa (Promotoría destino + Sede + RFC + CURP, #5) para
        identificar al agente de forma idempotente (Id interno = RFC+CURP, D-15).
        NO asienta clave ni crea empleado: eso ocurre después (Fases 2 y 3).
        """
        self.ensure_one()
        requeridos = [
            (self.bca_promotoria_destino_id, _('Promotoría destino')),
            (self.bca_sede_id, _('Sede / Plaza')),
            (self.bca_rfc, _('RFC')),
            (self.bca_curp, _('CURP')),
        ]
        faltantes = [label for value, label in requeridos if not value]
        if faltantes:
            raise ValidationError(_(
                'No se puede generar el contacto del agente "%(nombre)s" al llegar '
                'a "Acuerdo de Arranque": faltan datos: %(faltantes)s.'
            ) % {
                'nombre': self.partner_name or self.display_name,
                'faltantes': ', '.join(faltantes),
            })

        Partner = self.env['res.partner'].sudo()
        # Idempotencia por Id interno: reutiliza el agente aunque exista en otra
        # promotoría; se vincula al candidato sin duplicar (D-15).
        agente = Partner.search([
            ('bca_tipo', '=', 'agente'),
            ('vat', '=', self.bca_rfc),
            ('bca_curp', '=', self.bca_curp),
        ], limit=1)
        if not agente:
            agente = Partner.create({
                'name': (self.partner_name or self.name or '').strip(),
                'email': self.email_from or False,
                'phone': self.partner_phone or False,
                'bca_tipo': 'agente',
                'parent_id': self.bca_promotoria_destino_id.id,
                'is_company': False,
                'vat': self.bca_rfc,
                'bca_curp': self.bca_curp,
            })
        self.partner_id = agente
        self._bca_log_partner_vinculado(agente)

    def _bca_crear_clave_aseguradora(self, agente):
        """Asienta la clave por aseguradora en `clave_arranque` (F1). Idempotente."""
        self.ensure_one()
        Clave = self.env['res.partner.agente.aseguradora'].sudo()
        existente = Clave.search([
            ('agente_id', '=', agente.id),
            ('aseguradora_id', '=', self.bca_aseguradora_id.id),
        ], limit=1)
        if existente:
            return existente
        vals = {
            'agente_id': agente.id,
            'aseguradora_id': self.bca_aseguradora_id.id,
            'clave_agente': self.bca_clave_arranque,
            'estado': 'clave_arranque',  # F1: NUNCA clave_definitiva (D-14)
            'fecha_licencia': self.bca_fecha_cedula,
        }
        try:
            with self.env.cr.savepoint():
                clave = Clave.create(vals)
                clave.flush_recordset()
                return clave
        except IntegrityError:
            _logger.info(
                'Clave duplicada (agente %s / aseguradora %s); se reutiliza.',
                agente.id, self.bca_aseguradora_id.id,
            )
            return Clave.search([
                ('aseguradora_id', '=', self.bca_aseguradora_id.id),
                ('clave_agente', '=', self.bca_clave_arranque),
            ], limit=1)

    def _bca_crear_empleado(self, agente):
        """Crea el hr.employee vinculado al partner agente (no-empleado legal).

        Se usa `sudo()`: la reclutadora puede no tener ACL de creación de empleados.
        """
        self.ensure_one()
        Employee = self.env['hr.employee'].sudo()
        existente = Employee.search([('work_contact_id', '=', agente.id)], limit=1)
        if existente:
            return existente
        return Employee.create({
            'name': agente.name,
            'work_contact_id': agente.id,
            'work_email': self.email_from or False,
        })

    def _bca_actividad_habilitacion(self, agente) -> None:
        """Notifica a la reclutadora y al promotor de la promotoría destino."""
        self.ensure_one()
        destinatarios = self.user_id | self.bca_promotoria_destino_id.user_ids[:1]
        summary = _('Agente habilitado en Clave de Arranque')
        for user in destinatarios:
            self.activity_schedule(
                'mail.mail_activity_data_todo',
                summary=summary,
                note=_('Se habilitó al agente %(agente)s en clave de arranque '
                       'para %(aseg)s.') % {
                    'agente': agente.name,
                    'aseg': self.bca_aseguradora_id.name,
                },
                user_id=user.id,
            )

    def _bca_log_partner_vinculado(self, partner) -> None:
        """Chatter + log del partner creado/vinculado."""
        self.ensure_one()
        self.message_post(body=_(
            'Se creó/vinculó el contacto BCA <a href="#" data-oe-model="res.partner" '
            'data-oe-id="%(id)s">%(name)s</a> (%(tipo)s).'
        ) % {'id': partner.id, 'name': partner.name, 'tipo': partner.bca_tipo})
        _logger.info(
            'hr.applicant %s: partner %s (%s, bca_tipo=%s).',
            self.id, partner.id, partner.name, partner.bca_tipo,
        )
