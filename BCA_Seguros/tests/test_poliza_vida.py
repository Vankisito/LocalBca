from __future__ import annotations

from datetime import date

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase


class TestPolizaVida(TransactionCase):
    """Campos VIDA: asegurado, beneficiarios (suma 100% al confirmar),
    conducto por defecto propagado a recibos y persistencia de campos nuevos."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.holding = Partner.create({'name': 'BCA Holding', 'bca_tipo': 'holding'})
        cls.promotoria = Partner.create({
            'name': 'Promotoría V',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = Partner.create({
            'name': 'Agente V',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        # Rollup bca_estado_agente: clave definitiva vía puente (fuente de verdad).
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'CLV-V',
            'estado': 'clave_definitiva',
        })
        cls.contratante = Partner.create({
            'name': 'Contratante V',
        })
        cls.asegurado = Partner.create({
            'name': 'Asegurado V',
        })
        cls.benef_1 = Partner.create({'name': 'Beneficiario 1'})
        cls.benef_2 = Partner.create({'name': 'Beneficiario 2'})
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Cargo Automático Test',
            'codigo_archivo': 'CARGO_TEST',
            'aseguradora_id': cls.aseguradora.id,
        })
        cls.producto = cls.env['product.template'].create({
            'name': 'Vida Test V',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })

    def _crear_poliza(self, name: str = 'POL-VIDA-001', **overrides) -> object:
        vals = {
            'name': name,
            'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto.id,
            'agente_id': self.agente.id,
            'contratante_id': self.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'mensual',
            'prima_anual': 12000.0,
        }
        vals.update(overrides)
        return self.env['bca.poliza'].create(vals)

    def _benef(self, partner, porcentaje: float, parentesco: str = 'otro'):
        return Command.create({
            'beneficiario_id': partner.id,
            'parentesco': parentesco,
            'porcentaje': porcentaje,
        })

    def test_confirmar_beneficiarios_suman_100(self) -> None:
        """Confirma cuando los beneficiarios suman exactamente 100%."""
        poliza = self._crear_poliza(beneficiario_ids=[
            self._benef(self.benef_1, 60.0, 'conyuge'),
            self._benef(self.benef_2, 40.0, 'hijo'),
        ])
        self.assertAlmostEqual(poliza.beneficiarios_porcentaje_total, 100.0, places=2)
        poliza.action_confirmar()
        self.assertEqual(poliza.estado, 'activa')

    def test_confirmar_beneficiarios_no_suman_100(self) -> None:
        """Bloquea la confirmación si los beneficiarios no suman 100%."""
        poliza = self._crear_poliza(beneficiario_ids=[
            self._benef(self.benef_1, 60.0),
            self._benef(self.benef_2, 30.0),
        ])
        with self.assertRaises(ValidationError):
            poliza.action_confirmar()
        self.assertEqual(poliza.estado, 'borrador',
                         'La póliza no debe activarse si la validación falla.')

    def test_confirmar_sin_beneficiarios(self) -> None:
        """Sin beneficiarios la validación de 100% no aplica."""
        poliza = self._crear_poliza()
        poliza.action_confirmar()
        self.assertEqual(poliza.estado, 'activa')

    def test_conducto_se_propaga_a_recibos(self) -> None:
        """El conducto por defecto de la póliza pasa a los recibos generados."""
        poliza = self._crear_poliza(conducto_id=self.conducto.id)
        poliza.action_confirmar()
        self.assertEqual(len(poliza.recibo_ids), 12)
        for recibo in poliza.recibo_ids:
            self.assertEqual(recibo.conducto_id, self.conducto)

    def test_asegurado_y_campos_persisten(self) -> None:
        """asegurado_id y los campos nuevos de la póliza persisten."""
        poliza = self._crear_poliza(
            asegurado_id=self.asegurado.id,
            plan='Plan Protección',
            fecha_emision=date(2025, 12, 15),
            coberturas_adicionales='Invalidez total y permanente',
        )
        self.assertEqual(poliza.asegurado_id, self.asegurado)
        self.assertEqual(poliza.plan, 'Plan Protección')
        self.assertEqual(poliza.fecha_emision, date(2025, 12, 15))
        self.assertEqual(poliza.coberturas_adicionales, 'Invalidez total y permanente')

    def test_contratante_puede_ser_su_propio_asegurado(self) -> None:
        """El domain permite usar al contratante como asegurado (caso común)."""
        poliza = self._crear_poliza(asegurado_id=self.contratante.id)
        self.assertEqual(poliza.asegurado_id, self.contratante)

    def test_campos_contratante_persisten(self) -> None:
        """Demográficos y referencias de pago en res.partner."""
        self.contratante.write({
            'bca_fecha_nacimiento': date(1985, 3, 20),
            'bca_estado_civil': 'casado',
            'bca_genero': 'masculino',
            'bca_ref_prima_basica_trad': 'TRAD-001',
            'bca_fondo_variable_ppr': 'PPR-VAR-9',
        })
        self.assertEqual(self.contratante.bca_estado_civil, 'casado')
        self.assertEqual(self.contratante.bca_genero, 'masculino')
        self.assertEqual(self.contratante.bca_ref_prima_basica_trad, 'TRAD-001')
        self.assertEqual(self.contratante.bca_fondo_variable_ppr, 'PPR-VAR-9')
