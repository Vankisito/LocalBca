from __future__ import annotations

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestCrmLead(TransactionCase):
    """Etapa 3 — crm.lead: campos BCA y generación de póliza desde lead."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.partner_cliente = cls.env['res.partner'].create({
            'name': 'Cliente Prospecto',
        })
        cls.producto_seguro = cls.env['product.template'].create({
            'name': 'Vida LSP Lead Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })
        cls.producto_no_seguro = cls.env['product.template'].create({
            'name': 'Producto Cualquiera',
            'bca_es_producto_seguro': False,
        })

        Stage = cls.env['crm.stage']
        cls.stage_nuevo = Stage.create({'name': 'Test - Nuevo', 'sequence': 1})
        cls.stage_ganado = Stage.create({
            'name': 'Test - Ganado', 'sequence': 10, 'is_won': True,
        })

    def _crear_lead(self, **overrides) -> object:
        vals = {
            'name': 'Lead Test',
            'partner_id': self.partner_cliente.id,
            'stage_id': self.stage_nuevo.id,
            'bca_aseguradora_id': self.aseguradora.id,
            'bca_producto_id': self.producto_seguro.id,
            'bca_ramo': 'vida',
            'bca_prima_estimada': 24000.0,
            'bca_periodicidad': 'mensual',
        }
        vals.update(overrides)
        return self.env['crm.lead'].create(vals)

    def test_campos_bca_existen(self) -> None:
        """Los 6 campos bca_* existen y aceptan valores."""
        lead = self._crear_lead()
        self.assertEqual(lead.bca_aseguradora_id, self.aseguradora)
        self.assertEqual(lead.bca_producto_id, self.producto_seguro)
        self.assertEqual(lead.bca_ramo, 'vida')
        self.assertEqual(lead.bca_prima_estimada, 24000.0)
        self.assertEqual(lead.bca_periodicidad, 'mensual')
        self.assertFalse(lead.bca_poliza_generada_id)

    def test_generar_poliza_falla_si_no_ganado(self) -> None:
        """action_bca_generar_poliza falla en stage no ganado."""
        lead = self._crear_lead()
        with self.assertRaises(UserError):
            lead.action_bca_generar_poliza()

    def test_generar_poliza_falla_si_ya_generada(self) -> None:
        """action_bca_generar_poliza falla si ya hay póliza vinculada."""
        lead = self._crear_lead(stage_id=self.stage_ganado.id)
        # Forzar un valor para bca_poliza_generada_id sin crear una póliza real:
        # crear un dummy y vincularlo.
        agente = self.env['res.partner'].create({
            'name': 'Agente Dummy',
            'bca_tipo': 'agente',
            'parent_id': self.env['res.partner'].create({
                'name': 'Prom Dummy',
                'bca_tipo': 'promotoria',
                'parent_id': self.env.ref('BCA_Seguros.partner_bca_holding').id,
            }).id,
        })
        from datetime import date
        poliza = self.env['bca.poliza'].create({
            'name': 'POL-LEAD-DUMMY',
            'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto_seguro.id,
            'agente_id': agente.id,
            'contratante_id': self.partner_cliente.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'anual',
            'prima_anual': 12000.0,
        })
        lead.bca_poliza_generada_id = poliza
        with self.assertRaises(UserError):
            lead.action_bca_generar_poliza()

    def test_generar_poliza_retorna_action_con_defaults(self) -> None:
        """Lead ganado → action de form bca.poliza con contexto precargado."""
        lead = self._crear_lead(stage_id=self.stage_ganado.id)
        action = lead.action_bca_generar_poliza()
        self.assertEqual(action['res_model'], 'bca.poliza')
        self.assertEqual(action['view_mode'], 'form')
        ctx = action['context']
        self.assertEqual(ctx['default_aseguradora_id'], self.aseguradora.id)
        self.assertEqual(ctx['default_producto_id'], self.producto_seguro.id)
        self.assertEqual(ctx['default_prima_anual'], 24000.0)
        self.assertEqual(ctx['default_periodicidad'], 'mensual')
        self.assertEqual(ctx['default_contratante_id'], self.partner_cliente.id)

    def test_onchange_producto_autollena_ramo_aseguradora(self) -> None:
        """Onchange de bca_producto_id autollena ramo y aseguradora."""
        lead = self.env['crm.lead'].new({
            'name': 'Lead Onchange',
            'bca_producto_id': self.producto_seguro.id,
        })
        lead._onchange_bca_producto_id()
        self.assertEqual(lead.bca_ramo, 'vida')
        self.assertEqual(lead.bca_aseguradora_id, self.aseguradora)
