from __future__ import annotations

from datetime import date

from psycopg2 import IntegrityError

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


class TestPoliza(TransactionCase):
    """Etapa 2 — R-POL-01, R-POL-03, R-POL-05, M4."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.holding = Partner.create({'name': 'BCA Holding', 'bca_tipo': 'holding'})
        cls.promotoria_a = Partner.create({
            'name': 'Promotoría A',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.promotoria_b = Partner.create({
            'name': 'Promotoría B',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente_a = Partner.create({
            'name': 'Agente A',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria_a.id,
        })
        cls.agente_b = Partner.create({
            'name': 'Agente B',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria_b.id,
        })
        cls.contratante = Partner.create({
            'name': 'Cliente Test',
        })
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        # bca_estado_agente es un rollup computed: para que los agentes "jueguen"
        # se les da clave definitiva vía el modelo puente (fuente de verdad).
        AgenteAseg = cls.env['res.partner.agente.aseguradora']
        for idx, agente in enumerate((cls.agente_a, cls.agente_b)):
            AgenteAseg.create({
                'agente_id': agente.id,
                'aseguradora_id': cls.aseguradora.id,
                'clave_agente': 'CLV-%s' % idx,
                'estado': 'clave_definitiva',
            })
        cls.producto = cls.env['product.template'].create({
            'name': 'Vida LSP Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })

    def _crear_poliza(self, name: str = 'POL-TEST-001', **overrides) -> object:
        vals = {
            'name': name,
            'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto.id,
            'agente_id': self.agente_a.id,
            'contratante_id': self.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'mensual',
            'prima_anual': 12000.0,
        }
        vals.update(overrides)
        return self.env['bca.poliza'].create(vals)

    def test_creacion_minima(self) -> None:
        """Crear una póliza válida con los campos mínimos."""
        poliza = self._crear_poliza()
        self.assertEqual(poliza.estado, 'borrador')
        self.assertEqual(poliza.promotoria_id, self.promotoria_a,
                         'promotoria_id (computed) debe reflejar al agente actual.')
        self.assertFalse(poliza.recibo_ids,
                         'No deben existir recibos antes de confirmar.')

    def test_unique_name_aseguradora(self) -> None:
        """R-POL-01: número de póliza único por aseguradora."""
        self._crear_poliza(name='POL-DUP')
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            with self.cr.savepoint():
                self._crear_poliza(name='POL-DUP')

    def test_confirmar_genera_plan_pagos_mensual(self) -> None:
        """action_confirmar genera 12 recibos mensuales con prima fraccionada."""
        poliza = self._crear_poliza()
        poliza.action_confirmar()
        self.assertEqual(poliza.estado, 'activa')
        self.assertEqual(len(poliza.recibo_ids), 12)
        numeros = sorted(poliza.recibo_ids.mapped('numero_recibo'))
        self.assertEqual(numeros, list(range(1, 13)))
        # 12000 / 12 = 1000 cada uno
        for recibo in poliza.recibo_ids:
            self.assertAlmostEqual(recibo.prima_neta, 1000.0, places=2)
            self.assertEqual(recibo.estado, 'pendiente')

    def test_no_regenerar_plan_con_recibos_pagados(self) -> None:
        """R-POL-05: no se puede regenerar el plan si ya hay recibos pagados."""
        poliza = self._crear_poliza()
        poliza.action_confirmar()
        # Marcamos un recibo como pagado vía bypass (sudo) para simular estado real.
        primer_recibo = poliza.recibo_ids.sorted('numero_recibo')[0]
        primer_recibo.sudo().write({
            'estado': 'pagado',
            'fecha_pago': date(2026, 1, 15),
            'pca_aplicada': 50.0,
            'factor_aplicado': 0.05,
        })
        with self.assertRaises(UserError):
            poliza._generar_plan_pagos()

    def test_cambiar_agente_registra_historial(self) -> None:
        """M4: cambiar_agente crea registro en cambio.agente y actualiza promotoria_id."""
        poliza = self._crear_poliza()
        self.assertEqual(poliza.promotoria_id, self.promotoria_a)
        poliza.cambiar_agente(self.agente_b, motivo='Reasignación de prueba')
        self.assertEqual(poliza.agente_id, self.agente_b)
        self.assertEqual(poliza.promotoria_id, self.promotoria_b,
                         'promotoria_id debe recomputarse al cambiar agente.')
        self.assertEqual(len(poliza.cambio_agente_ids), 1)
        cambio = poliza.cambio_agente_ids
        self.assertEqual(cambio.agente_anterior_id, self.agente_a)
        self.assertEqual(cambio.promotoria_anterior_id, self.promotoria_a)
        self.assertEqual(cambio.agente_nuevo_id, self.agente_b)
        self.assertEqual(cambio.promotoria_nueva_id, self.promotoria_b)
        self.assertEqual(cambio.motivo, 'Reasignación de prueba')

    def test_cambiar_agente_rechaza_no_agente(self) -> None:
        """cambiar_agente debe validar que el destinatario sea de tipo agente."""
        poliza = self._crear_poliza()
        with self.assertRaises(ValidationError):
            poliza.cambiar_agente(self.contratante, motivo='Inválido')

    # --- P5: generación por anualidad con avance automático ---

    def test_anualidad_vida_anual_genera_un_recibo(self) -> None:
        """Vida anual 10 años: al confirmar solo se genera la 1ª anualidad."""
        poliza = self._crear_poliza(
            periodicidad='anual',
            fecha_fin=date(2036, 1, 1),
            temporalidad_anios=10,
        )
        poliza.action_confirmar()
        self.assertEqual(len(poliza.recibo_ids), 1,
                         'Solo debe generarse el recibo de la anualidad vigente.')
        recibo = poliza.recibo_ids
        self.assertEqual(recibo.numero_recibo, 1)
        self.assertEqual(recibo.fecha_desde, date(2026, 1, 1))
        self.assertEqual(recibo.fecha_hasta, date(2027, 1, 1))
        self.assertAlmostEqual(recibo.prima_neta, 12000.0, places=2)

    def test_anualidad_avance_al_pagar(self) -> None:
        """Pagar el último recibo de la anualidad genera la siguiente."""
        poliza = self._crear_poliza(
            periodicidad='anual',
            fecha_fin=date(2036, 1, 1),
            temporalidad_anios=10,
        )
        poliza.action_confirmar()
        poliza.recibo_ids.action_registrar_pago({
            'fecha_pago': date(2026, 1, 15),
            'prima_neta': 12000.0,
        })
        self.assertEqual(len(poliza.recibo_ids), 2,
                         'Al pagar la anualidad vigente se genera la siguiente.')
        pendiente = poliza.recibo_ids.filtered(lambda r: r.estado == 'pendiente')
        self.assertEqual(len(pendiente), 1)
        self.assertEqual(pendiente.numero_recibo, 2)
        self.assertEqual(pendiente.fecha_desde, date(2027, 1, 1))
        self.assertEqual(pendiente.fecha_hasta, date(2028, 1, 1))

    def test_anualidad_no_excede_fecha_fin(self) -> None:
        """Al cubrir hasta fecha_fin no se generan más anualidades."""
        poliza = self._crear_poliza(
            periodicidad='anual',
            fecha_fin=date(2027, 1, 1),
            temporalidad_anios=1,
        )
        poliza.action_confirmar()
        poliza.recibo_ids.action_registrar_pago({
            'fecha_pago': date(2026, 1, 15),
            'prima_neta': 12000.0,
        })
        self.assertEqual(len(poliza.recibo_ids), 1,
                         'La póliza ya cubre hasta fecha_fin: sin nuevas anualidades.')
        self.assertEqual(poliza.recibo_ids.estado, 'pagado')
