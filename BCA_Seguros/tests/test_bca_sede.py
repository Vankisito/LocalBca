from __future__ import annotations

from psycopg2 import IntegrityError

from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.tools import mute_logger


@tagged('BCA_Seguros')
class TestBcaSede(TransactionCase):
    """Etapa 12 Fase A — catálogo bca.sede (HU-1.0)."""

    def test_crud_y_rec_name(self) -> None:
        """Crea una sede y su display_name usa `name` (rec_name por defecto)."""
        sede = self.env['bca.sede'].create({'name': 'Guadalajara', 'codigo': 'GDL'})
        self.assertEqual(sede.display_name, 'Guadalajara')
        self.assertTrue(sede.active, 'active por defecto True.')

    def test_archivado(self) -> None:
        """Archivar una sede la retira de las búsquedas por defecto."""
        sede = self.env['bca.sede'].create({'name': 'Sede Temporal'})
        sede.active = False
        encontradas = self.env['bca.sede'].search([('name', '=', 'Sede Temporal')])
        self.assertFalse(encontradas, 'Sede archivada no debe salir en search default.')
        con_inactivas = self.env['bca.sede'].with_context(
            active_test=False,
        ).search([('name', '=', 'Sede Temporal')])
        self.assertIn(sede, con_inactivas)

    def test_codigo_unico(self) -> None:
        """El código de sede es único (models.Constraint UNIQUE)."""
        self.env['bca.sede'].create({'name': 'Sede A', 'codigo': 'DUP'})
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['bca.sede'].create({'name': 'Sede B', 'codigo': 'DUP'})
            self.env.flush_all()

    def test_codigo_nulo_permite_varias(self) -> None:
        """Varias sedes sin código conviven (NULL≠NULL en el UNIQUE)."""
        self.env['bca.sede'].create({'name': 'Sin Código 1'})
        self.env['bca.sede'].create({'name': 'Sin Código 2'})
        self.env.flush_all()  # no debe lanzar IntegrityError
