from __future__ import annotations

from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase


class TestPolizaGMM(TransactionCase):
    """Campos GMM del layout de portafolio: importes informativos (IVA,
    recargo fijo), sub-ramo, y asegurados adicionales (dependientes) que
    reúsan beneficiario_ids SIN la regla del 100% que sí aplica a Vida."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.holding = Partner.create({'name': 'BCA Holding G', 'bca_tipo': 'holding'})
        cls.promotoria = Partner.create({
            'name': 'Promotoría G',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = Partner.create({
            'name': 'Agente G',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        # Rollup bca_estado_agente: clave definitiva vía puente (fuente de verdad).
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'CLV-G',
            'estado': 'clave_definitiva',
        })
        cls.contratante = Partner.create({
            'name': 'Contratante G',
        })
        cls.dependiente_1 = Partner.create({'name': 'Dependiente 1'})
        cls.dependiente_2 = Partner.create({'name': 'Dependiente 2'})
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Cargo Automático GMM',
            'codigo_archivo': 'CARGO_GMM_TEST',
            'aseguradora_id': cls.aseguradora.id,
        })
        cls.producto = cls.env['product.template'].create({
            'name': 'GMM Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'gmm',
        })

    def _crear_poliza(self, name: str = 'POL-GMM-001', **overrides) -> object:
        vals = {
            'name': name,
            'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto.id,
            'agente_id': self.agente.id,
            'contratante_id': self.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'anual',
            'prima_anual': 24000.0,
        }
        vals.update(overrides)
        return self.env['bca.poliza'].create(vals)

    def _dependiente(self, partner, parentesco: str, fnac: date):
        return Command.create({
            'beneficiario_id': partner.id,
            'parentesco': parentesco,
            'fecha_nacimiento': fnac,
        })

    def test_ramo_se_deriva_a_gmm(self) -> None:
        """El producto GMM fija ramo='gmm' en la póliza."""
        poliza = self._crear_poliza()
        self.assertEqual(poliza.ramo, 'gmm')

    def test_confirmar_con_asegurados_adicionales(self) -> None:
        """Una póliza GMM con asegurados adicionales (sin porcentaje) se
        confirma sin disparar la validación del 100% de beneficiarios."""
        poliza = self._crear_poliza(beneficiario_ids=[
            self._dependiente(self.dependiente_1, 'conyuge', date(1990, 5, 10)),
            self._dependiente(self.dependiente_2, 'hijo', date(2015, 8, 1)),
        ])
        # Reúsa beneficiario_ids → porcentaje 0; en Vida esto fallaría.
        self.assertAlmostEqual(poliza.beneficiarios_porcentaje_total, 0.0, places=2)
        poliza.action_confirmar()
        self.assertEqual(poliza.estado, 'activa')

    def test_fecha_nacimiento_dependiente_persiste(self) -> None:
        """La fecha de nacimiento del asegurado adicional vive en la línea."""
        poliza = self._crear_poliza(beneficiario_ids=[
            self._dependiente(self.dependiente_1, 'hijo', date(2018, 2, 14)),
        ])
        linea = poliza.beneficiario_ids
        self.assertEqual(len(linea), 1)
        self.assertEqual(linea.fecha_nacimiento, date(2018, 2, 14))
        self.assertEqual(linea.parentesco, 'hijo')

    def test_campos_gmm_persisten(self) -> None:
        """IVA, recargo fijo, sub-ramo, deducible y coaseguro persisten."""
        poliza = self._crear_poliza(
            deducible=29000.0,
            coaseguro=0.10,
            nivel_hospitalario='Alta especialidad',
            iva=3840.0,
            recargo_fijo=250.0,
            bca_sub_ramo_codigo='0721',
            coberturas_adicionales='Maternidad',
        )
        self.assertEqual(poliza.deducible, 29000.0)
        self.assertAlmostEqual(poliza.coaseguro, 0.10, places=2)
        self.assertEqual(poliza.nivel_hospitalario, 'Alta especialidad')
        self.assertEqual(poliza.iva, 3840.0)
        self.assertEqual(poliza.recargo_fijo, 250.0)
        self.assertEqual(poliza.bca_sub_ramo_codigo, '0721')
        self.assertEqual(poliza.coberturas_adicionales, 'Maternidad')

    def test_conducto_se_propaga_a_recibos(self) -> None:
        """El conducto por defecto de la póliza GMM pasa a sus recibos
        (mismo campo bca.conducto que usa el recibo)."""
        poliza = self._crear_poliza(conducto_id=self.conducto.id)
        poliza.action_confirmar()
        self.assertTrue(poliza.recibo_ids)
        for recibo in poliza.recibo_ids:
            self.assertEqual(recibo.conducto_id, self.conducto)

    def test_ref_prima_medica_persiste(self) -> None:
        """La referencia de prima médica del contratante persiste."""
        self.contratante.bca_ref_prima_medica = 'MED-12345'
        self.assertEqual(self.contratante.bca_ref_prima_medica, 'MED-12345')
