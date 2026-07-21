from __future__ import annotations

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('BCA_Seguros')
class TestResPartnerVatSync(TransactionCase):
    """Regresión: el RFC (vat) no debe propagarse entre agentes que
    comparten Holding/Promotoría.

    Odoo core marca `vat` como "commercial field" y lo sincroniza a través
    de la jerarquía `parent_id` (pensada para subsidiarias legales). BCA
    reutiliza `parent_id` para la jerarquía organizacional Holding >
    Promotoría > Agente, donde cada agente tiene su propio RFC personal.
    Sin el override de `_synced_commercial_fields`, el RFC del primer
    agente creado/vinculado bajo un Holding se filtraba hacia todos los
    demás agentes de esa misma red.
    """

    def setUp(self) -> None:
        super().setUp()
        self.holding = self.env['res.partner'].create({
            'name': 'Holding Test', 'is_company': True, 'bca_tipo': 'holding',
        })
        self.promotoria = self.env['res.partner'].create({
            'name': 'Promotoria Test', 'parent_id': self.holding.id,
            'bca_tipo': 'promotoria',
        })

    def test_vat_no_se_propaga_entre_agentes_de_la_misma_promotoria(self) -> None:
        agente_uno = self.env['res.partner'].create({
            'name': 'Agente Uno', 'parent_id': self.promotoria.id,
            'bca_tipo': 'agente', 'vat': 'RFCUNO111AAA',
        })
        agente_dos = self.env['res.partner'].create({
            'name': 'Agente Dos', 'parent_id': self.promotoria.id,
            'bca_tipo': 'agente', 'vat': 'RFCDOS222BBB',
        })
        self.assertEqual(agente_uno.vat, 'RFCUNO111AAA')
        self.assertEqual(agente_dos.vat, 'RFCDOS222BBB')
        self.assertNotEqual(agente_uno.vat, agente_dos.vat)
        # el Holding/Promotoría compartidos no deben haber heredado ningún RFC
        self.assertFalse(self.holding.vat)
        self.assertFalse(self.promotoria.vat)

    def test_vat_no_se_propaga_al_reasignar_parent_id(self) -> None:
        """Mismo bug, disparado por write() en vez de create() (ej. import en
        dos pasadas: primero se crea el agente, luego se le asigna la
        promotoría)."""
        agente_uno = self.env['res.partner'].create({
            'name': 'Agente Uno', 'bca_tipo': 'agente', 'vat': 'RFCUNO111AAA',
        })
        agente_dos = self.env['res.partner'].create({
            'name': 'Agente Dos', 'bca_tipo': 'agente', 'vat': 'RFCDOS222BBB',
        })
        agente_uno.write({'parent_id': self.promotoria.id})
        agente_dos.write({'parent_id': self.promotoria.id})
        self.assertEqual(agente_uno.vat, 'RFCUNO111AAA')
        self.assertEqual(agente_dos.vat, 'RFCDOS222BBB')
