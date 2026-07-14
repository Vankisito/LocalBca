from __future__ import annotations

from datetime import date

from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


class TestRecordRules(TransactionCase):
    """Etapa 4 — Aislamiento por record rules y guard M5 de cancelación."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        Product = cls.env['product.template']
        User = cls.env['res.users'].with_context(no_reset_password=True)

        group_internal = cls.env.ref('base.group_user')
        cls.group_agente = cls.env.ref('BCA_Seguros.group_bca_agente')
        cls.group_operador = cls.env.ref('BCA_Seguros.group_bca_operador')
        cls.group_lider = cls.env.ref('BCA_Seguros.group_bca_lider')
        cls.group_dc = cls.env.ref('BCA_Seguros.group_bca_director_comercial')
        cls.group_director = cls.env.ref('BCA_Seguros.group_bca_director')

        cls.holding = Partner.create({'name': 'Holding Test', 'bca_tipo': 'holding'})
        cls.promotoria_a = Partner.create({
            'name': 'Promo A',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.promotoria_b = Partner.create({
            'name': 'Promo B',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })

        cls.user_agente_a = User.create({
            'name': 'Agente A',
            'login': 'bca_test_agente_a',
            'group_ids': [(6, 0, [group_internal.id, cls.group_agente.id])],
        })
        cls.agente_a = Partner.create({
            'name': 'Agente A Partner',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria_a.id,
            'user_ids': [(6, 0, [cls.user_agente_a.id])],
        })

        cls.user_agente_b = User.create({
            'name': 'Agente B',
            'login': 'bca_test_agente_b',
            'group_ids': [(6, 0, [group_internal.id, cls.group_agente.id])],
        })
        cls.agente_b = Partner.create({
            'name': 'Agente B Partner',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria_b.id,
            'user_ids': [(6, 0, [cls.user_agente_b.id])],
        })

        cls.user_operador = User.create({
            'name': 'Operador BCA Test',
            'login': 'bca_test_operador',
            'group_ids': [(6, 0, [group_internal.id, cls.group_operador.id])],
        })
        cls.user_lider = User.create({
            'name': 'Lider BCA Test',
            'login': 'bca_test_lider',
            'group_ids': [(6, 0, [group_internal.id, cls.group_lider.id])],
        })
        cls.user_dc = User.create({
            'name': 'Director Comercial BCA Test',
            'login': 'bca_test_dc',
            'group_ids': [(6, 0, [group_internal.id, cls.group_dc.id])],
        })
        cls.user_director = User.create({
            'name': 'Director BCA Test',
            'login': 'bca_test_director',
            'group_ids': [(6, 0, [group_internal.id, cls.group_director.id])],
        })

        cls.aseguradora = Partner.create({
            'name': 'Aseguradora Test',
            'bca_tipo': 'aseguradora',
            'bca_codigo_aseguradora': 'TEST',
        })
        cls.contratante = Partner.create({
            'name': 'Cliente Test',
        })
        cls.producto = Product.create({
            'name': 'Seguro Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })

        Poliza = cls.env['bca.poliza']
        cls.poliza_a = Poliza.create({
            'name': 'POL-TEST-A-001',
            'aseguradora_id': cls.aseguradora.id,
            'producto_id': cls.producto.id,
            'agente_id': cls.agente_a.id,
            'contratante_id': cls.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2026, 12, 31),
            'prima_anual': 12000.0,
        })
        cls.poliza_b = Poliza.create({
            'name': 'POL-TEST-B-001',
            'aseguradora_id': cls.aseguradora.id,
            'producto_id': cls.producto.id,
            'agente_id': cls.agente_b.id,
            'contratante_id': cls.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2026, 12, 31),
            'prima_anual': 12000.0,
        })

        Recibo = cls.env['bca.recibo']
        # Recibo del agente A en estado pagado — para los tests de cancelación M5.
        cls.recibo_a = Recibo.create({
            'poliza_id': cls.poliza_a.id,
            'numero_recibo': 1,
            'fecha_desde': date(2026, 1, 1),
            'fecha_hasta': date(2026, 12, 31),
            'prima_neta': 12000.0,
            'monto_modal': 12000.0,
            'estado': 'pagado',
            'fecha_pago': date(2026, 1, 15),
            'agente_id': cls.agente_a.id,
            'promotoria_id': cls.promotoria_a.id,
            'pca_aplicada': 1000.0,
            'factor_aplicado': 0.0833,
        })
        cls.recibo_b = Recibo.create({
            'poliza_id': cls.poliza_b.id,
            'numero_recibo': 1,
            'fecha_desde': date(2026, 1, 1),
            'fecha_hasta': date(2026, 12, 31),
            'prima_neta': 12000.0,
            'monto_modal': 12000.0,
        })

    def test_agente_ve_solo_sus_polizas(self) -> None:
        """Rule rule_bca_poliza_agente: filtra por agente_id.user_ids."""
        Poliza = self.env['bca.poliza'].with_user(self.user_agente_a)
        visibles = Poliza.search([('name', 'like', 'POL-TEST-')])
        self.assertEqual(visibles, self.poliza_a)
        self.assertNotIn(self.poliza_b, visibles)

    def test_director_ve_todas_las_polizas(self) -> None:
        """Director (via implied_ids) tiene rule [(1,'=',1)] — sin filtro."""
        Poliza = self.env['bca.poliza'].with_user(self.user_director)
        visibles = Poliza.search([('name', 'like', 'POL-TEST-')])
        self.assertEqual(visibles, self.poliza_a + self.poliza_b)

    def test_agente_ve_solo_sus_recibos(self) -> None:
        """Rule rule_bca_recibo_agente: poliza_id.agente_id.user_ids."""
        Recibo = self.env['bca.recibo'].with_user(self.user_agente_a)
        visibles = Recibo.search([('poliza_id.name', 'like', 'POL-TEST-')])
        self.assertEqual(visibles, self.recibo_a)
        self.assertNotIn(self.recibo_b, visibles)

    def test_lider_ve_cross_promotoria(self) -> None:
        """Líder no debe heredar el filtro restrictivo del agente (A3)."""
        Poliza = self.env['bca.poliza'].with_user(self.user_lider)
        visibles = Poliza.search([('name', 'like', 'POL-TEST-')])
        promotorias = visibles.mapped('agente_id.parent_id')
        self.assertIn(self.promotoria_a, promotorias)
        self.assertIn(self.promotoria_b, promotorias)

    def test_operador_no_puede_cancelar_recibo(self) -> None:
        """M5: action_cancelar_pago exige Director o Director Comercial."""
        with self.assertRaises(AccessError):
            self.recibo_a.with_user(self.user_operador).action_cancelar_pago()

    def test_director_comercial_puede_cancelar_recibo(self) -> None:
        """M5/R6: Director Comercial puede cancelar el pago. Cancelar el pago
        revierte el recibo a 'pendiente' (no lo anula) y limpia la PCA."""
        self.recibo_a.with_user(self.user_dc).action_cancelar_pago()
        self.assertEqual(self.recibo_a.estado, 'pendiente')
        self.assertEqual(self.recibo_a.pca_aplicada, 0.0)


@tagged('BCA_Seguros')
class TestReclutamientoRecordRules(TransactionCase):
    """Etapa 12 Fase E — visibilidad del embudo de reclutamiento (SI-1)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        User = cls.env['res.users'].with_context(no_reset_password=True)
        internal = cls.env.ref('base.group_user')
        cls.job = cls.env.ref('BCA_Seguros.job_reclutamiento_agente')
        cls.stage = cls.env.ref('BCA_Seguros.stage_recibido')
        g_reclutadora = cls.env.ref('BCA_Seguros.group_bca_reclutadora')
        g_director = cls.env.ref('BCA_Seguros.group_bca_director')

        cls.recl1 = User.create({
            'name': 'Reclutadora Uno', 'login': 'bca_test_recl_1',
            'group_ids': [(6, 0, [internal.id, g_reclutadora.id])],
        })
        cls.recl2 = User.create({
            'name': 'Reclutadora Dos', 'login': 'bca_test_recl_2',
            'group_ids': [(6, 0, [internal.id, g_reclutadora.id])],
        })
        cls.director = User.create({
            'name': 'Director Recl', 'login': 'bca_test_dir_recl',
            'group_ids': [(6, 0, [internal.id, g_director.id])],
        })

        Applicant = cls.env['hr.applicant']
        cls.app1 = Applicant.create({
            'partner_name': 'Cand de Recl1', 'job_id': cls.job.id,
            'stage_id': cls.stage.id, 'user_id': cls.recl1.id,
        })
        cls.app2 = Applicant.create({
            'partner_name': 'Cand de Recl2', 'job_id': cls.job.id,
            'stage_id': cls.stage.id, 'user_id': cls.recl2.id,
        })

    def test_reclutadora_ve_solo_sus_candidatos(self) -> None:
        """Reclutadora ve user_id==uid; no ve los de otra reclutadora (SI-1)."""
        Applicant = self.env['hr.applicant'].with_user(self.recl1)
        visibles = Applicant.search([('partner_name', 'like', 'Cand de Recl')])
        self.assertIn(self.app1, visibles)
        self.assertNotIn(self.app2, visibles,
                         'La reclutadora no debe ver candidatos de otra.')

    def test_director_ve_todos_los_candidatos(self) -> None:
        """Director ve todo (rule [(1,'=',1)] + ACL de lectura)."""
        Applicant = self.env['hr.applicant'].with_user(self.director)
        visibles = Applicant.search([('partner_name', 'like', 'Cand de Recl')])
        self.assertIn(self.app1, visibles)
        self.assertIn(self.app2, visibles)
