from __future__ import annotations

from datetime import date

from dateutil.relativedelta import relativedelta

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase

from odoo.addons.BCA_Seguros.models.product_template import RAMO_SELECTION
from odoo.addons.BCA_Seguros.models.res_partner import GENERO_SELECTION

# Identidad mexicana válida para el gate de formato (HU-1.4). RFC física 13 y CURP 18.
_RFC_VALIDO = 'AGEJ800101ABC'
_CURP_VALIDO = 'MAHJ800101HDFRRR09'


@tagged('BCA_Seguros')
class TestHrApplicant(TransactionCase):
    """Etapa 12 — hr.applicant: campos BCA y conversión por fases (Acuerdo/Cédula/Definitiva)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.holding = cls.env.ref('BCA_Seguros.partner_bca_holding')
        cls.job_captacion = cls.env.ref('BCA_Seguros.job_captacion_promotoria')
        cls.job_reclutamiento = cls.env.ref('BCA_Seguros.job_reclutamiento_agente')
        cls.job_interno = cls.env.ref('BCA_Seguros.job_interno')

        # Etapas reales del embudo comercial (la conversión se dispara por cruce
        # de umbral de `sequence`, no por etapas ad-hoc).
        cls.stage_recibido = cls.env.ref('BCA_Seguros.stage_recibido')
        cls.stage_acuerdo = cls.env.ref('BCA_Seguros.stage_acuerdo_arranque')
        cls.stage_cedula = cls.env.ref('BCA_Seguros.stage_cedula_emitida')
        cls.stage_definitiva = cls.env.ref('BCA_Seguros.stage_clave_definitiva')

        cls.promotoria = cls.env['res.partner'].create({
            'name': 'Promotoría Origen',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.aseguradora = cls.env['res.partner'].create({
            'name': 'Aseguradora Test',
            'bca_tipo': 'aseguradora',
        })
        cls.sede = cls.env['bca.sede'].create({'name': 'Sede Central', 'codigo': 'SC1'})

        Stage = cls.env['hr.recruitment.stage']
        cls.stage_open = Stage.create({'name': 'Test - En Proceso', 'sequence': 1})
        cls.stage_hired = Stage.create({
            'name': 'Test - Contratado',
            'sequence': 10,
            'hired_stage': True,
        })

        cls.job_estandar = cls.env['hr.job'].create({'name': 'Puesto estándar RH'})

    def _crear_applicant(self, job, **overrides) -> object:
        vals = {
            'partner_name': 'Candidato Test',
            'job_id': job.id,
            'stage_id': self.stage_recibido.id,
            'email_from': 'candidato@example.com',
        }
        vals.update(overrides)
        return self.env['hr.applicant'].create(vals)

    def _datos_completos(self, **overrides) -> dict:
        """Identidad (Acuerdo) + habilitación (Cédula) + clave definitiva."""
        vals = {
            'bca_promotoria_destino_id': self.promotoria.id,
            'bca_sede_id': self.sede.id,
            'bca_rfc': _RFC_VALIDO,
            'bca_curp': _CURP_VALIDO,
            'bca_clave_arranque': 'CLV-001',
            'bca_fecha_cedula': date(2026, 1, 15),
            'bca_aseguradora_id': self.aseguradora.id,
            'bca_clave_definitiva': 'CLV-DEF-001',
        }
        vals.update(overrides)
        return vals

    # ---------------------------------------------------------------
    # Fase 1 — Acuerdo de Arranque: creación del contacto (#10) + gate (#5)
    # ---------------------------------------------------------------
    def test_acuerdo_reclutamiento_crea_agente(self) -> None:
        """Agente con identidad completa → al llegar a Acuerdo se crea el contacto."""
        applicant = self._crear_applicant(
            self.job_reclutamiento,
            partner_name='Juan Agente',
            **self._datos_completos(),
        )
        applicant.stage_id = self.stage_acuerdo
        agente = applicant.partner_id
        self.assertTrue(agente, 'Debe crearse partner_id en Acuerdo de Arranque.')
        self.assertEqual(agente.bca_tipo, 'agente')
        self.assertEqual(agente.parent_id, self.promotoria)
        self.assertEqual(agente.name, 'Juan Agente')
        # RFC → vat nativo; CURP → bca_curp.
        self.assertEqual(agente.vat, _RFC_VALIDO)
        self.assertEqual(agente.bca_curp, _CURP_VALIDO)

    def test_acuerdo_captacion_crea_promotoria(self) -> None:
        """Applicant de Promotores → al llegar a Acuerdo crea res.partner promotoría."""
        applicant = self._crear_applicant(
            self.job_captacion,
            partner_name='Nueva Promotoría SA',
            bca_rfc=_RFC_VALIDO,
            bca_curp=_CURP_VALIDO,
        )
        applicant.stage_id = self.stage_acuerdo
        self.assertTrue(applicant.partner_id)
        self.assertEqual(applicant.partner_id.bca_tipo, 'promotoria')
        self.assertEqual(applicant.partner_id.parent_id, self.holding)
        self.assertEqual(applicant.partner_id.name, 'Nueva Promotoría SA')
        # Paridad de identidad con Agentes: RFC → vat, CURP → bca_curp (BUG-001).
        self.assertEqual(applicant.partner_id.vat, _RFC_VALIDO)
        self.assertEqual(applicant.partner_id.bca_curp, _CURP_VALIDO)

    def test_acuerdo_captacion_sin_rfc_curp_bloquea(self) -> None:
        """Promotor sin RFC/CURP al llegar a Acuerdo → ValidationError (BUG-001)."""
        applicant = self._crear_applicant(
            self.job_captacion, partner_name='Promotoría Incompleta',
        )
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_acuerdo

    def test_acuerdo_sin_sede_bloquea(self) -> None:
        """Agente sin Sede/Plaza al llegar a Acuerdo → ValidationError (#5)."""
        datos = self._datos_completos(bca_sede_id=False)
        applicant = self._crear_applicant(self.job_reclutamiento, **datos)
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_acuerdo

    def test_acuerdo_sin_promotoria_destino_bloquea(self) -> None:
        """Agente sin promotoría destino al llegar a Acuerdo → ValidationError."""
        datos = self._datos_completos(bca_promotoria_destino_id=False)
        applicant = self._crear_applicant(self.job_reclutamiento, **datos)
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_acuerdo

    def test_acuerdo_sin_rfc_curp_bloquea(self) -> None:
        """Agente sin RFC/CURP al llegar a Acuerdo → ValidationError (identidad)."""
        datos = self._datos_completos(bca_rfc=False, bca_curp=False)
        applicant = self._crear_applicant(self.job_reclutamiento, **datos)
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_acuerdo

    def test_idempotencia_doble_acuerdo(self) -> None:
        """Cruzar dos veces el umbral de Acuerdo no duplica el contacto."""
        applicant = self._crear_applicant(
            self.job_captacion, partner_name='Promotoría Idempotente',
            bca_rfc=_RFC_VALIDO, bca_curp=_CURP_VALIDO,
        )
        applicant.stage_id = self.stage_acuerdo
        primer_partner = applicant.partner_id
        self.assertTrue(primer_partner)

        applicant.stage_id = self.stage_recibido
        applicant.stage_id = self.stage_acuerdo
        self.assertEqual(applicant.partner_id, primer_partner,
                         'partner_id no debe cambiar en segunda transición.')

    def test_job_ajeno_no_crea_partner(self) -> None:
        """Applicant en job estándar (no BCA) → no se crea partner BCA."""
        applicant = self._crear_applicant(self.job_estandar)
        applicant.stage_id = self.stage_hired
        partner = applicant.partner_id
        if partner:
            self.assertNotIn(partner.bca_tipo, ('agente', 'promotoria'),
                             'Job ajeno no debe producir partner con bca_tipo BCA.')

    # ---------------------------------------------------------------
    # Fase 1 — Bifurcación de equipo Reclutamiento → Capital Humano (#11)
    # ---------------------------------------------------------------
    def test_traspaso_capital_humano_en_acuerdo(self) -> None:
        """En Acuerdo: user_id → responsable CH del parámetro; reclutadora → interviewer_ids."""
        ch_user = self.env['res.users'].create({
            'name': 'Encargada Capital Humano', 'login': 'ch_bca@test.com',
        })
        self.env['ir.config_parameter'].sudo().set_param(
            'bca_reclutamiento.capital_humano_user_id', str(ch_user.id))
        reclutadora = self.env['res.users'].create({
            'name': 'Reclutadora BCA', 'login': 'recl_bca@test.com',
        })
        applicant = self._crear_applicant(
            self.job_reclutamiento, user_id=reclutadora.id,
            **self._datos_completos(),
        )
        applicant.stage_id = self.stage_acuerdo
        self.assertEqual(applicant.user_id, ch_user,
                         'El responsable debe reasignarse a Capital Humano.')
        self.assertIn(reclutadora, applicant.interviewer_ids,
                      'La reclutadora debe preservarse como entrevistadora.')

    def test_traspaso_sin_parametro_no_reasigna(self) -> None:
        """Sin parámetro CH configurado, no se reasigna el responsable (solo aviso)."""
        self.env['ir.config_parameter'].sudo().set_param(
            'bca_reclutamiento.capital_humano_user_id', '')
        reclutadora = self.env['res.users'].create({
            'name': 'Reclutadora Sin CH', 'login': 'recl_noch@test.com',
        })
        applicant = self._crear_applicant(
            self.job_reclutamiento, user_id=reclutadora.id,
            **self._datos_completos(),
        )
        applicant.stage_id = self.stage_acuerdo
        self.assertEqual(applicant.user_id, reclutadora,
                         'Sin parámetro CH, el responsable no debe cambiar.')

    # ---------------------------------------------------------------
    # Fase 2 — Cédula Emitida (hired): clave por aseguradora (D-14) + L2
    # ---------------------------------------------------------------
    def test_hired_sin_datos_habilitacion_bloquea(self) -> None:
        """Llegar a Cédula Emitida sin los datos de habilitación ⇒ ValidationError (L2)."""
        # Identidad completa (pasa Acuerdo) pero sin clave/fecha/aseguradora.
        datos = self._datos_completos(
            bca_clave_arranque=False, bca_fecha_cedula=False, bca_aseguradora_id=False)
        applicant = self._crear_applicant(self.job_reclutamiento, **datos)
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_cedula

    def test_conversion_crea_puente_clave_arranque(self) -> None:
        """En Cédula Emitida se asienta el puente en estado clave_arranque (F1/D-14)."""
        applicant = self._crear_applicant(
            self.job_reclutamiento, partner_name='Ana Agente',
            **self._datos_completos(),
        )
        applicant.stage_id = self.stage_cedula
        claves = applicant.partner_id.agente_aseguradora_ids
        self.assertEqual(len(claves), 1)
        self.assertEqual(claves.estado, 'clave_arranque')
        self.assertNotEqual(claves.estado, 'clave_definitiva',
                            'El recién habilitado NO debe computar PCA.')
        self.assertEqual(claves.aseguradora_id, self.aseguradora)
        self.assertEqual(claves.clave_agente, 'CLV-001')

    def test_idempotencia_por_rfc_curp(self) -> None:
        """Mismo RFC+CURP en otra aseguradora ⇒ mismo agente, clave agregada (D-15)."""
        aseguradora2 = self.env['res.partner'].create({
            'name': 'Aseguradora Dos', 'bca_tipo': 'aseguradora',
        })
        app1 = self._crear_applicant(
            self.job_reclutamiento, partner_name='Caro Agente',
            **self._datos_completos(),
        )
        app1.stage_id = self.stage_cedula
        agente1 = app1.partner_id

        app2 = self._crear_applicant(
            self.job_reclutamiento, partner_name='Caro Agente',
            **self._datos_completos(
                bca_aseguradora_id=aseguradora2.id, bca_clave_arranque='CLV-002'),
        )
        app2.stage_id = self.stage_cedula
        self.assertEqual(app2.partner_id, agente1,
                         'Debe reutilizarse el mismo agente por Id interno.')
        self.assertEqual(len(agente1.agente_aseguradora_ids), 2,
                         'Se agrega la clave de la nueva aseguradora.')
        self.assertEqual(
            set(agente1.agente_aseguradora_ids.mapped('estado')), {'clave_arranque'})

    def test_hired_promotor_sin_rfc_curp_bloquea(self) -> None:
        """Promotor sin RFC/CURP en Cédula Emitida ⇒ ValidationError (L2, BUG-001)."""
        applicant = self._crear_applicant(
            self.job_captacion, partner_name='Promotoría Sin Identidad',
        )
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_cedula

    def test_hired_promotor_no_exige_datos_agente(self) -> None:
        """Promotor con RFC/CURP llega a Cédula Emitida sin clave/fecha/aseguradora.

        Esos 3 datos son licencia específica de Agente ante una aseguradora y NO
        se exigen a Promotores en este fix (SDD §11.2, fuera de alcance).
        """
        applicant = self._crear_applicant(
            self.job_captacion, partner_name='Promotoría Ligera',
            bca_rfc=_RFC_VALIDO, bca_curp=_CURP_VALIDO,
        )
        applicant.stage_id = self.stage_cedula  # no debe lanzar
        self.assertEqual(applicant.stage_id, self.stage_cedula)

    def test_hired_promotor_no_crea_puente(self) -> None:
        """Promotor en Cédula Emitida no crea res.partner.agente.aseguradora.

        La Fase 2 (clave por aseguradora) sigue exclusiva de `job_reclutamiento_agente`.
        """
        antes = self.env['res.partner.agente.aseguradora'].search_count([])
        applicant = self._crear_applicant(
            self.job_captacion, partner_name='Promotoría Sin Puente',
            bca_rfc=_RFC_VALIDO, bca_curp=_CURP_VALIDO,
        )
        applicant.stage_id = self.stage_cedula
        despues = self.env['res.partner.agente.aseguradora'].search_count([])
        self.assertEqual(antes, despues, 'Promotor no debe crear puente de agente.')

    def test_job_interno_nativo_no_crea_puente_ni_agente(self) -> None:
        """Puesto interno (job no BCA) en etapa hired ⇒ sin partner agente ni puente.

        Los internos cierran por el embudo nativo; el despachador por umbral solo
        actúa sobre los dos jobs comerciales BCA (D-20).
        """
        antes = self.env['res.partner.agente.aseguradora'].search_count([])
        applicant = self._crear_applicant(self.job_estandar)
        applicant.stage_id = self.stage_hired
        if applicant.partner_id:
            self.assertNotEqual(applicant.partner_id.bca_tipo, 'agente')
        despues = self.env['res.partner.agente.aseguradora'].search_count([])
        self.assertEqual(antes, despues, 'El alta interna no debe crear puentes.')

    def test_puesto_interno_no_crea_partner_ni_puente(self) -> None:
        """BUG-002: el job real "Puesto Interno" tampoco crea partner ni puente.

        Regresión directa sobre el bug reportado (antes no existía este `hr.job`);
        mismo comportamiento que cualquier job no comercial (D-20). Provee
        RFC/CURP para satisfacer el gate mínimo de datos de BUG-020/D-24 (el
        candidato debe poder llegar al hired nativo antes de verificar que no
        se crea partner/puente).
        """
        antes = self.env['res.partner.agente.aseguradora'].search_count([])
        applicant = self._crear_applicant(
            self.job_interno, bca_rfc=_RFC_VALIDO, bca_curp=_CURP_VALIDO)
        applicant.stage_id = self.stage_hired
        if applicant.partner_id:
            self.assertNotEqual(applicant.partner_id.bca_tipo, 'agente')
        despues = self.env['res.partner.agente.aseguradora'].search_count([])
        self.assertEqual(antes, despues, 'Puesto Interno no debe crear puentes.')

    # ---------------------------------------------------------------
    # BUG-020 — Gate mínimo de datos para Puesto Interno antes del hired (D-24)
    # ---------------------------------------------------------------
    def test_bug020_puesto_interno_sin_datos_bloquea_hired(self) -> None:
        """job_interno sin RFC/CURP/email_from no llega a la etapa hired."""
        applicant = self._crear_applicant(self.job_interno, email_from=False)
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_hired

    def test_bug020_puesto_interno_con_datos_completos_avanza(self) -> None:
        """Con RFC+CURP+email_from, job_interno sí llega al hired nativo."""
        applicant = self._crear_applicant(
            self.job_interno, bca_rfc=_RFC_VALIDO, bca_curp=_CURP_VALIDO,
        )
        applicant.stage_id = self.stage_hired  # no debe lanzar
        self.assertEqual(applicant.stage_id, self.stage_hired)

    def test_bug020_no_afecta_gate_existente_de_figuras_comerciales(self) -> None:
        """El gate nuevo de job_interno no reemplaza a `_check_habilitacion_datos`."""
        applicant = self._crear_applicant(
            self.job_reclutamiento, bca_rfc=_RFC_VALIDO, bca_curp=_CURP_VALIDO)
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_cedula  # faltan clave_arranque/aseguradora/fecha

    # ---------------------------------------------------------------
    # Fase 3 — Clave Definitiva: creación del empleado (#8/#9)
    # ---------------------------------------------------------------
    def test_empleado_solo_en_clave_definitiva(self) -> None:
        """El empleado se crea al llegar a Clave Definitiva, no antes."""
        applicant = self._crear_applicant(
            self.job_reclutamiento, partner_name='Delia Agente',
            **self._datos_completos(),
        )
        applicant.stage_id = self.stage_cedula  # crea agente + clave, NO empleado
        Employee = self.env['hr.employee']
        self.assertFalse(
            Employee.search([('work_contact_id', '=', applicant.partner_id.id)]),
            'No debe existir empleado antes de Clave Definitiva.')
        self.assertFalse(applicant.bca_puede_crear_empleado,
                         'El botón de empleado NO debe habilitarse en Cédula Emitida.')

        applicant.stage_id = self.stage_definitiva  # crea empleado
        empleado = Employee.search(
            [('work_contact_id', '=', applicant.partner_id.id)])
        self.assertEqual(len(empleado), 1)
        self.assertEqual(empleado.name, 'Delia Agente')
        self.assertEqual(applicant.employee_id, empleado,
                         'El empleado creado debe vincularse a employee_id.')
        self.assertTrue(applicant.bca_puede_crear_empleado,
                        'El botón de empleado debe habilitarse en Clave Definitiva.')

    def test_clave_definitiva_faltante_bloquea_empleado(self) -> None:
        """Llegar a Clave Definitiva sin el dato bca_clave_definitiva ⇒ ValidationError."""
        datos = self._datos_completos(bca_clave_definitiva=False)
        applicant = self._crear_applicant(self.job_reclutamiento, **datos)
        applicant.stage_id = self.stage_cedula
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_definitiva

    def test_clave_definitiva_no_promueve_pca(self) -> None:
        """Clave Definitiva crea el empleado pero NO promueve el puente a clave_definitiva."""
        applicant = self._crear_applicant(
            self.job_reclutamiento, **self._datos_completos())
        applicant.stage_id = self.stage_cedula
        applicant.stage_id = self.stage_definitiva
        claves = applicant.partner_id.agente_aseguradora_ids
        self.assertEqual(set(claves.mapped('estado')), {'clave_arranque'},
                         'El puente NO debe pasar a clave_definitiva (D-14/SI-4).')

    # ---------------------------------------------------------------
    # Validación de formato de identidad mexicana (#7)
    # ---------------------------------------------------------------
    def test_rfc_formato_invalido(self) -> None:
        with self.assertRaises(ValidationError):
            self._crear_applicant(self.job_reclutamiento, bca_rfc='RFC_INVALIDO')

    def test_curp_formato_invalido(self) -> None:
        with self.assertRaises(ValidationError):
            self._crear_applicant(self.job_reclutamiento, bca_curp='CURP123')

    def test_rfc_curp_validos_persisten(self) -> None:
        applicant = self._crear_applicant(
            self.job_reclutamiento, bca_rfc=_RFC_VALIDO, bca_curp=_CURP_VALIDO)
        self.assertEqual(applicant.bca_rfc, _RFC_VALIDO)
        self.assertEqual(applicant.bca_curp, _CURP_VALIDO)

    # ---------------------------------------------------------------
    # Etapa 12 Fase A — cimientos (HU-1.0/1.1/1.2)
    # ---------------------------------------------------------------
    def test_embudo_13_etapas_cargadas(self) -> None:
        """Las 13 etapas comerciales cargan scopeadas a los jobs esperados.

        Recibido…Cena (seq 1-4) incluye también `job_interno` desde D-24
        (BUG-020/BUG-021); "Evaluación PDA"/"Acuerdo de Arranque" (seq 5-6) y
        Fase B (seq 7-13) siguen exclusivas de las figuras comerciales (esas
        fases no aplican a un puesto interno).
        """
        job_recl = self.job_reclutamiento
        job_capt = self.job_captacion
        puesto_interno_si = [
            ('stage_recibido', 1), ('stage_prospeccion', 2), ('stage_cafe', 3),
            ('stage_entrevista', 4),
        ]
        puesto_interno_no = [
            ('stage_evaluacion_pda', 5), ('stage_acuerdo_arranque', 6),
            ('stage_clave_arranque', 7), ('stage_inscripcion_cia', 8),
            ('stage_curso_cedula', 9), ('stage_examen', 10),
            ('stage_cedula_emitida', 11), ('stage_en_desarrollo', 12),
            ('stage_clave_definitiva', 13),
        ]
        for xmlid, seq in puesto_interno_si:
            stage = self.env.ref(f'BCA_Seguros.{xmlid}')
            self.assertEqual(stage.sequence, seq, f'{xmlid} sequence != {seq}')
            self.assertIn(job_recl, stage.job_ids,
                          f'{xmlid} debe estar scopeada a job_reclutamiento_agente.')
            self.assertIn(job_capt, stage.job_ids,
                          f'{xmlid} debe estar scopeada a job_captacion_promotoria.')
            self.assertIn(self.job_interno, stage.job_ids,
                          f'{xmlid} SÍ debe estar scopeada a job_interno (D-24).')
        for xmlid, seq in puesto_interno_no:
            stage = self.env.ref(f'BCA_Seguros.{xmlid}')
            self.assertEqual(stage.sequence, seq, f'{xmlid} sequence != {seq}')
            self.assertIn(job_recl, stage.job_ids,
                          f'{xmlid} debe estar scopeada a job_reclutamiento_agente.')
            self.assertIn(job_capt, stage.job_ids,
                          f'{xmlid} debe estar scopeada a job_captacion_promotoria.')
            self.assertNotIn(self.job_interno, stage.job_ids,
                              f'{xmlid} NO debe estar scopeada a job_interno (D-24).')

    def test_bug021_puesto_interno_ve_recibido_a_cena(self) -> None:
        """job_interno queda scopeado solo a Recibido…Cena (D-24), no a
        "Evaluación PDA"/"Acuerdo de Arranque" (exclusivas de las figuras
        comerciales)."""
        si_xmlids = [
            'stage_recibido', 'stage_prospeccion', 'stage_cafe', 'stage_entrevista',
        ]
        for xmlid in si_xmlids:
            stage = self.env.ref(f'BCA_Seguros.{xmlid}')
            self.assertIn(self.job_interno, stage.job_ids)
        self.assertNotIn(
            self.job_interno,
            self.env.ref('BCA_Seguros.stage_evaluacion_pda').job_ids)
        self.assertNotIn(
            self.job_interno, self.stage_acuerdo.job_ids)

    def test_bug021_criterio_borrado_etapas_nativas(self) -> None:
        """Reproduce el criterio de `migrations/19.0.1.8.3` para identificar
        las etapas nativas intermedias a borrar: NO son de BCA_Seguros,
        `hired_stage=False`, nombre en la lista candidata ES/EN. Una etapa BCA
        (aunque comparta nombre por coincidencia) o una etapa hired no deben
        matchear. `hr.recruitment.stage` no tiene campo `active` en Odoo 19
        (BUG-021): se retiran con `unlink()`, no con `active=False`.
        """
        Stage = self.env['hr.recruitment.stage']
        nativa = Stage.create({'name': 'Nuevo', 'sequence': 1})
        nativa_en = Stage.create({'name': 'First Interview', 'sequence': 2})
        hired_no_matchea = Stage.create({
            'name': 'Nuevo', 'sequence': 3, 'hired_stage': True,
        })
        nativa_id, nativa_en_id = nativa.id, nativa_en.id

        candidatas_es_en = [
            'Nuevo', 'New', 'Calificación', 'Calificacion', 'Qualified',
            'Qualification', 'Primera Entrevista', 'First Interview',
            'Segunda Entrevista', 'Second Interview',
        ]
        stages_bca = self.env['hr.recruitment.stage'].browse([
            self.stage_recibido.id, self.stage_acuerdo.id,
            self.stage_cedula.id, self.stage_definitiva.id,
        ])
        candidatas = Stage.search([
            ('hired_stage', '=', False),
            ('name', 'in', candidatas_es_en),
        ]) - stages_bca

        self.assertIn(nativa, candidatas)
        self.assertIn(nativa_en, candidatas)
        self.assertNotIn(hired_no_matchea, candidatas,
                          'Una etapa hired no debe borrarse aunque coincida el nombre.')
        self.assertNotIn(self.stage_recibido, candidatas,
                          'Una etapa BCA no debe borrarse (nombre no coincide).')

        # Simula el borrado real (unlink), nunca active=False.
        candidatas.unlink()
        self.assertFalse(Stage.browse(nativa_id).exists())
        self.assertFalse(Stage.browse(nativa_en_id).exists())

    def test_etapa_entrevista_renombrada_cena(self) -> None:
        """La etapa "Entrevista" ahora se llama "Cena" (terminología del equipo)."""
        self.assertEqual(self.env.ref('BCA_Seguros.stage_entrevista').name, 'Cena')

    def test_puestos_renombrados(self) -> None:
        """Los puestos comerciales se llaman "Promotores" y "Agentes"."""
        self.assertEqual(self.job_captacion.name, 'Promotores')
        self.assertEqual(self.job_reclutamiento.name, 'Agentes')

    def test_puesto_interno_existe(self) -> None:
        """BUG-002: existe un hr.job genérico "Puesto Interno" (D-20/D-23)."""
        self.assertEqual(self.job_interno.name, 'Puesto Interno')

    def test_hired_stages_flag(self) -> None:
        """Cédula Emitida es la etapa hired; Clave Definitiva NO lo es."""
        self.assertTrue(self.stage_cedula.hired_stage,
                        'Cédula Emitida debe ser hired_stage.')
        self.assertFalse(self.env.ref('BCA_Seguros.stage_recibido').hired_stage,
                         'Recibido NO debe ser hired_stage.')
        self.assertFalse(self.stage_definitiva.hired_stage,
                         'Clave Definitiva NO debe ser hired_stage.')
        self.assertIn(self.job_reclutamiento, self.stage_cedula.job_ids)
        self.assertIn(self.job_captacion, self.stage_cedula.job_ids)
        self.assertFalse(
            self.env.ref('BCA_Seguros.stage_alta_interna', raise_if_not_found=False),
            'stage_alta_interna debe estar retirada (D-20).',
        )

    def test_campos_identificacion_capturables(self) -> None:
        """Los campos bca_ de identificación/perfil se capturan y persisten.

        Tras D-19/D-21: académico=type_id nativo, origen=UTM nativo, seguimiento=embudo;
        se conservan folio_cv (LinkedIn) y ramo/perfil_laboral (Detalles). El campo
        bca_tipo_candidato fue retirado (duplicaba el origen nativo).
        """
        applicant = self._crear_applicant(
            self.job_reclutamiento,
            bca_sede_id=self.sede.id,
            bca_ramo='vida',
            bca_genero='femenino',
            bca_institucion='Universidad X',
            bca_perfil_laboral='Ventas',
            bca_folio_cv='CV-001',
        )
        self.assertEqual(applicant.bca_sede_id, self.sede)
        self.assertEqual(applicant.bca_ramo, 'vida')
        self.assertEqual(applicant.bca_genero, 'femenino')
        self.assertEqual(applicant.bca_perfil_laboral, 'Ventas')
        self.assertEqual(applicant.bca_folio_cv, 'CV-001')
        # bca_tipo_candidato fue retirado del modelo.
        self.assertNotIn('bca_tipo_candidato', self.env['hr.applicant']._fields)

    def test_institucion_educativa_label(self) -> None:
        """El campo bca_institucion se renombró a "Institución Educativa"."""
        self.assertEqual(
            self.env['hr.applicant']._fields['bca_institucion'].string,
            'Institución Educativa')

    def test_edad_computed_no_almacenada(self) -> None:
        """bca_edad se calcula desde la fecha de nacimiento y NO se almacena."""
        nacimiento = date.today() - relativedelta(years=30)
        applicant = self._crear_applicant(
            self.job_reclutamiento,
            bca_fecha_nacimiento=nacimiento,
        )
        self.assertEqual(applicant.bca_edad, 30)
        self.assertFalse(
            self.env['hr.applicant']._fields['bca_edad'].store,
            'bca_edad debe ser computed no almacenado (depende de hoy).',
        )
        vacio = self._crear_applicant(self.job_reclutamiento)
        self.assertEqual(vacio.bca_edad, 0)

    def test_no_campos_duplicados(self) -> None:
        """Reuso, no reinvención: género/ramo reusan selecciones; sin campos RFC/nombre duplicados."""
        fields = self.env['hr.applicant']._fields
        self.assertEqual(fields['bca_genero'].selection, GENERO_SELECTION)
        self.assertEqual(fields['bca_ramo'].selection, RAMO_SELECTION)
        for redundante in ('bca_nombre', 'bca_correo', 'bca_telefono'):
            self.assertNotIn(redundante, fields,
                             f'{redundante} duplica un campo nativo; debe reusarse.')
        for nativo in ('partner_name', 'email_from', 'partner_phone', 'linkedin_profile'):
            self.assertIn(nativo, fields, f'Se esperaba reusar el campo nativo {nativo}.')
        partner_fields = self.env['res.partner']._fields
        self.assertIn('vat', partner_fields)
        self.assertNotIn('bca_rfc', partner_fields,
                         'res.partner debe reusar `vat`, no crear bca_rfc.')
        self.assertIn('bca_rfc', fields,
                      'hr.applicant necesita bca_rfc (no tiene `vat` nativo).')

    # ---------------------------------------------------------------
    # Etapa 12 Fase B — PDA + compuerta de riesgo L1 (HU-1.3)
    # ---------------------------------------------------------------
    def _crear_applicant_pda(self, nivel: str, **overrides) -> object:
        """Applicant de agente con identidad completa (para aislar la compuerta L1)."""
        base = {
            'bca_promotoria_destino_id': self.promotoria.id,
            'bca_sede_id': self.sede.id,
            'bca_rfc': _RFC_VALIDO,
            'bca_curp': _CURP_VALIDO,
            'bca_pda_nivel': nivel,
        }
        base.update(overrides)
        return self._crear_applicant(self.job_reclutamiento, **base)

    def test_pda_riesgo_computed(self) -> None:
        """Nivel baja/no_ideal ⇒ riesgo; ideal/recomendado/aceptable ⇒ sin riesgo."""
        for nivel in ('baja', 'no_ideal'):
            self.assertTrue(self._crear_applicant_pda(nivel).bca_pda_riesgo)
        for nivel in ('ideal', 'recomendado', 'aceptable'):
            self.assertFalse(self._crear_applicant_pda(nivel).bca_pda_riesgo)

    def test_pda_riesgo_crea_actividad_promotor(self) -> None:
        """Riesgo PDA sin VoBo ⇒ actividad "Visto bueno PDA requerido" al promotor."""
        promotor = self.env['res.users'].create({
            'name': 'Promotor Responsable',
            'login': 'promotor_pda@test.com',
            'partner_id': self.promotoria.id,
        })
        applicant = self._crear_applicant(
            self.job_reclutamiento,
            bca_promotoria_destino_id=self.promotoria.id,
        )
        applicant.bca_pda_nivel = 'baja'  # dispara notificación vía write
        actividades = applicant.activity_ids.filtered(
            lambda a: a.user_id == promotor)
        self.assertTrue(actividades, 'Debe crear actividad para el promotor.')
        self.assertEqual(actividades[0].summary, 'Visto bueno PDA requerido')
        applicant.bca_pda_nivel = 'no_ideal'
        self.assertEqual(
            len(applicant.activity_ids.filtered(lambda a: a.user_id == promotor)),
            1, 'No debe duplicar la actividad del promotor.')

    def test_pda_avance_sin_vobo_bloquea(self) -> None:
        """Avanzar más allá de "Evaluación PDA" con riesgo y sin VoBo ⇒ ValidationError."""
        applicant = self._crear_applicant_pda('baja')
        with self.assertRaises(ValidationError):
            applicant.stage_id = self.stage_acuerdo

    def test_pda_con_vobo_avanza(self) -> None:
        """Con VoBo del promotor, el candidato en riesgo sí avanza."""
        applicant = self._crear_applicant_pda(
            'baja', bca_pda_visto_bueno_promotor=True)
        applicant.stage_id = self.stage_acuerdo  # no debe lanzar
        self.assertEqual(applicant.stage_id, self.stage_acuerdo)

    # ---------------------------------------------------------------
    # Etapa 12 Fase D — motivos de rechazo + automatización + SIC (HU-1.7/1.9)
    # ---------------------------------------------------------------
    def test_refuse_reasons_seed(self) -> None:
        """Los 2 motivos de rechazo están seed como datos del módulo."""
        prospecto = self.env.ref('BCA_Seguros.refuse_reason_declinado_prospecto')
        bca = self.env.ref('BCA_Seguros.refuse_reason_declinado_bca')
        self.assertEqual(prospecto.name, 'Declinado por Prospecto')
        self.assertEqual(bca.name, 'Declinado por BCA')

    def test_automation_aviso_etapa_seed(self) -> None:
        """La automatización de aviso por etapa (L6) está seed y activa."""
        automation = self.env.ref('BCA_Seguros.automation_aviso_cambio_etapa')
        self.assertEqual(automation.trigger, 'on_stage_set')
        self.assertEqual(automation.model_id.model, 'hr.applicant')
        self.assertTrue(automation.action_server_ids, 'Debe tener acción servidor.')

    def test_sic_action_pivote_seed(self) -> None:
        """La acción SIC de reclutamiento abre pivote sobre hr.applicant."""
        action = self.env.ref('BCA_Seguros.action_sic_reclutamiento')
        self.assertEqual(action.res_model, 'hr.applicant')
        self.assertIn('pivot', action.view_mode)
