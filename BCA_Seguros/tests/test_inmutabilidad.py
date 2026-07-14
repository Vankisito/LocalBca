from __future__ import annotations

from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase


class TestInmutabilidad(TransactionCase):
    """Etapa 2 — C1 (pagado_hasta + PCA), R-COB-09, M5 y bitácora inmutable."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.holding = Partner.create({'name': 'BCA Holding', 'bca_tipo': 'holding'})
        cls.promotoria = Partner.create({
            'name': 'Promotoría Test',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = Partner.create({
            'name': 'Agente Test',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        cls.contratante = Partner.create({
            'name': 'Cliente Test',
        })
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        # Rollup bca_estado_agente: clave definitiva vía puente (fuente de verdad).
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'CLV-INM',
            'estado': 'clave_definitiva',
        })
        cls.producto = cls.env['product.template'].create({
            'name': 'Vida LSP Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })

    def _crear_poliza_activa(self) -> object:
        poliza = self.env['bca.poliza'].create({
            'name': 'POL-INMUT-001',
            'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto.id,
            'agente_id': self.agente.id,
            'contratante_id': self.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'mensual',
            'prima_anual': 12000.0,
        })
        poliza.action_confirmar()
        return poliza

    def test_pagado_hasta_avanza_al_pagar(self) -> None:
        """C1: pagado_hasta es computed store — avanza solo al pagar un recibo."""
        poliza = self._crear_poliza_activa()
        self.assertFalse(poliza.pagado_hasta,
                         'pagado_hasta debe ser False sin recibos pagados.')
        primer_recibo = poliza.recibo_ids.sorted('numero_recibo')[0]
        primer_recibo.action_registrar_pago({
            'fecha_pago': date(2026, 1, 15),
            'prima_neta': 1000.0,
        })
        self.assertEqual(poliza.pagado_hasta, primer_recibo.fecha_hasta,
                         'pagado_hasta debe avanzar al fecha_hasta del recibo pagado.')

    def test_pagado_hasta_retrocede_al_cancelar(self) -> None:
        """C1: pagado_hasta retrocede al cancelar el último recibo pagado."""
        poliza = self._crear_poliza_activa()
        # Promovemos el usuario actual a Director para poder cancelar.
        # Odoo 19: res.users.groups_id se renombró a group_ids.
        admin = self.env.ref('base.user_admin')
        director_group = self.env.ref('BCA_Seguros.group_bca_director')
        admin.group_ids = [(4, director_group.id)]

        recibos = poliza.recibo_ids.sorted('numero_recibo')
        recibos[0].action_registrar_pago({
            'fecha_pago': date(2026, 1, 15),
            'prima_neta': 1000.0,
        })
        recibos[1].action_registrar_pago({
            'fecha_pago': date(2026, 2, 15),
            'prima_neta': 1000.0,
        })
        self.assertEqual(poliza.pagado_hasta, recibos[1].fecha_hasta)

        recibos[1].with_user(admin).action_cancelar_pago()
        self.assertEqual(poliza.pagado_hasta, recibos[0].fecha_hasta,
                         'pagado_hasta debe retroceder al recibo anterior pagado.')

    def test_pca_inmutable_post_pago(self) -> None:
        """C1: pca_aplicada/factor_aplicado bloqueados tras pago para no-su."""
        poliza = self._crear_poliza_activa()
        recibo = poliza.recibo_ids.sorted('numero_recibo')[0]
        recibo.action_registrar_pago({
            'fecha_pago': date(2026, 1, 15),
            'prima_neta': 1000.0,
        })
        # Usuario interno no-su no puede tocar PCA.
        usuario = self.env['res.users'].create({
            'name': 'Operador Test',
            'login': 'op_test_inmut',
            'group_ids': [(4, self.env.ref('base.group_user').id),
                          (4, self.env.ref('BCA_Seguros.group_bca_operador').id)],
        })
        with self.assertRaises(UserError):
            recibo.with_user(usuario).write({'pca_aplicada': 99.0})

    def test_registrar_pago_sin_fecha_es_atomico(self) -> None:
        """R-COB-09: validación pre-ejecución no debe modificar la BD."""
        poliza = self._crear_poliza_activa()
        recibo = poliza.recibo_ids.sorted('numero_recibo')[0]
        estado_previo = recibo.estado
        with self.assertRaises(ValidationError):
            recibo.action_registrar_pago({'prima_neta': 1000.0})
        recibo.invalidate_recordset()
        self.assertEqual(recibo.estado, estado_previo,
                         'El recibo no debe haberse modificado al fallar la validación.')
        self.assertFalse(recibo.fecha_pago)
        self.assertFalse(recibo.pca_aplicada)

    # --- R6: cancelar pago (→ pendiente) vs anular recibo (→ cancelado) ---

    def _promover_a_director(self) -> None:
        director = self.env.ref('BCA_Seguros.group_bca_director')
        self.env.user.group_ids = [(4, director.id)]

    def test_cancelar_pago_revierte_a_pendiente(self) -> None:
        """R6: 'Cancelar Pago' deshace el pago y limpia los datos; NO anula."""
        self._promover_a_director()
        poliza = self._crear_poliza_activa()
        recibo = poliza.recibo_ids.sorted('numero_recibo')[0]
        recibo.action_registrar_pago({
            'fecha_pago': date(2026, 1, 15),
            'prima_neta': 1000.0,
        })
        self.assertEqual(recibo.estado, 'pagado')

        recibo.action_cancelar_pago()
        self.assertEqual(recibo.estado, 'pendiente',
                         'Cancelar el pago debe devolver el recibo a pendiente.')
        self.assertFalse(recibo.fecha_pago)
        self.assertFalse(recibo.conducto_id)
        self.assertFalse(recibo.agente_id)
        self.assertEqual(recibo.pca_aplicada, 0.0)
        self.assertFalse(poliza.pagado_hasta)

    def test_cancelar_pago_respeta_fifo(self) -> None:
        """R6: solo el último recibo pagado puede revertirse."""
        self._promover_a_director()
        poliza = self._crear_poliza_activa()
        recibos = poliza.recibo_ids.sorted('numero_recibo')
        recibos[0].action_registrar_pago({
            'fecha_pago': date(2026, 1, 15), 'prima_neta': 1000.0,
        })
        recibos[1].action_registrar_pago({
            'fecha_pago': date(2026, 2, 15), 'prima_neta': 1000.0,
        })
        with self.assertRaises(UserError):
            recibos[0].action_cancelar_pago()

    def test_anular_recibo_pendiente(self) -> None:
        """R6: 'Anular Recibo' lleva un pendiente a cancelado."""
        self._promover_a_director()
        poliza = self._crear_poliza_activa()
        recibo = poliza.recibo_ids.sorted('numero_recibo')[-1]
        recibo.action_anular_recibo()
        self.assertEqual(recibo.estado, 'cancelado')

    def test_anular_recibo_pagado_rechazado(self) -> None:
        """R6: no se puede anular un recibo pagado (cancelar el pago primero)."""
        self._promover_a_director()
        poliza = self._crear_poliza_activa()
        recibo = poliza.recibo_ids.sorted('numero_recibo')[0]
        recibo.action_registrar_pago({
            'fecha_pago': date(2026, 1, 15), 'prima_neta': 1000.0,
        })
        with self.assertRaises(UserError):
            recibo.action_anular_recibo()

    def test_bitacora_es_inmutable(self) -> None:
        """Plan §2.3.5: write/unlink sobre bitácora levantan UserError para no-su."""
        bitacora = self.env['bca.bitacora.importacion'].sudo().create({
            'aseguradora_id': self.aseguradora.id,
            'ramo': 'vida',
            'nombre_archivo': 'test.csv',
            'total_filas': 0,
        })
        usuario = self.env['res.users'].create({
            'name': 'Operador Bitácora',
            'login': 'op_test_bitacora',
            'group_ids': [(4, self.env.ref('base.group_user').id),
                          (4, self.env.ref('BCA_Seguros.group_bca_operador').id)],
        })
        with self.assertRaises(UserError):
            bitacora.with_user(usuario).write({'nombre_archivo': 'otro.csv'})
        with self.assertRaises(UserError):
            bitacora.with_user(usuario).unlink()
