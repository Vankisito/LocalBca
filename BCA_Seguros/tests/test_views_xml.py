from __future__ import annotations

from odoo.tests.common import TransactionCase
from odoo.tests import tagged


@tagged('post_install', '-at_install')
class TestViewsXml(TransactionCase):
    """Etapa 10 — Validación estática de las vistas XML del módulo.

    Carga las vistas declaradas y fuerza el parseo de `arch` para atrapar:
    - referencias a campos inexistentes en el modelo,
    - sintaxis `invisible="..."` mal escrita,
    - xpaths que ya no resuelven contra la vista heredada,
    - actions referenciadas en `<menuitem>` que no existen.

    Cada test pide a Odoo que combine la vista heredada con sus padres y
    valide el resultado contra el modelo. Si falla, levanta excepción y
    el test queda en rojo con un mensaje útil para el desarrollador.
    """

    def _validate(self, xmlid: str) -> None:
        view = self.env.ref(xmlid)
        # get_view combina la vista heredada con sus padres y valida el arch
        # resultante contra el modelo (campos, sintaxis invisible=,
        # xpaths que resuelvan). Si algo falla levanta excepción.
        result = self.env[view.model].get_view(
            view_id=view.id,
            view_type=view.type,
        )
        self.assertIn('arch', result, f'Vista {xmlid} no produjo arch')

    def test_poliza_views(self) -> None:
        self._validate('BCA_Seguros.view_poliza_list')
        self._validate('BCA_Seguros.view_poliza_form')
        self._validate('BCA_Seguros.view_poliza_search')

    def test_recibo_views(self) -> None:
        self._validate('BCA_Seguros.view_recibo_list')
        self._validate('BCA_Seguros.view_recibo_form')
        self._validate('BCA_Seguros.view_recibo_search')

    def test_bitacora_views(self) -> None:
        self._validate('BCA_Seguros.view_bitacora_importacion_list')
        self._validate('BCA_Seguros.view_bitacora_importacion_form')
        self._validate('BCA_Seguros.view_bitacora_importacion_search')

    def test_factor_pca_views(self) -> None:
        self._validate('BCA_Seguros.view_factor_pca_list')
        self._validate('BCA_Seguros.view_factor_pca_form')
        self._validate('BCA_Seguros.view_factor_pca_search')

    def test_conducto_views(self) -> None:
        self._validate('BCA_Seguros.view_conducto_list')
        self._validate('BCA_Seguros.view_conducto_form')
        self._validate('BCA_Seguros.view_conducto_search')

    def test_herencia_partner(self) -> None:
        self._validate('BCA_Seguros.view_partner_form_bca')
        self._validate('BCA_Seguros.view_partner_list_bca')
        self._validate('BCA_Seguros.view_partner_search_bca')

    def test_herencia_product(self) -> None:
        self._validate('BCA_Seguros.view_product_template_form_bca')

    def test_herencia_crm_lead(self) -> None:
        self._validate('BCA_Seguros.view_crm_lead_form_bca')

    def test_herencia_hr_applicant(self) -> None:
        self._validate('BCA_Seguros.view_hr_applicant_form_bca')

    def test_wizard_skeletons_cargan(self) -> None:
        self._validate('BCA_Seguros.view_wizard_carga_portafolio_form')
        self._validate('BCA_Seguros.view_wizard_cobranza_diaria_form')

    def test_reportes_views(self) -> None:
        """Etapa 9 — pivot/graph/list/search de los 4 reportes SQL parsean
        contra las columnas reales de la vista."""
        for base in (
            'view_reporte_pca_agente',
            'view_reporte_pca_promotoria',
            'view_reporte_pca_consolidado',
            'view_reporte_estado_cartera',
        ):
            for tipo in ('pivot', 'graph', 'list', 'search'):
                self._validate(f'BCA_Seguros.{base}_{tipo}')

    def test_menu_root_existe(self) -> None:
        menu = self.env.ref('BCA_Seguros.menu_bca_root')
        self.assertTrue(menu, 'Menú raíz BCA no se cargó')
        self.assertFalse(menu.parent_id, 'Menú raíz no debería tener padre')
        # v19: ir.ui.menu.group_ids (renombrado desde groups_id).
        self.assertTrue(
            menu.group_ids,
            'Menú raíz sin groups= queda invisible en producción '
            '(Plan §2.4.2)',
        )

    def test_actions_principales_existen(self) -> None:
        """Las actions referenciadas en menu.xml deben existir."""
        for xmlid in (
            'BCA_Seguros.action_dashboard',
            'BCA_Seguros.action_poliza',
            'BCA_Seguros.action_recibo',
            'BCA_Seguros.action_bitacora',
            'BCA_Seguros.action_conducto',
            'BCA_Seguros.action_factor_pca',
            'BCA_Seguros.action_partner_aseguradoras',
            'BCA_Seguros.action_partner_promotorias',
            'BCA_Seguros.action_partner_agentes',
            'BCA_Seguros.action_product_bca',
            'BCA_Seguros.action_wizard_carga_portafolio',
            'BCA_Seguros.action_wizard_cobranza_diaria',
            'BCA_Seguros.action_reporte_pca_agente',
            'BCA_Seguros.action_reporte_pca_promotoria',
            'BCA_Seguros.action_reporte_pca_consolidado',
            'BCA_Seguros.action_reporte_estado_cartera',
        ):
            self.assertTrue(
                self.env.ref(xmlid, raise_if_not_found=False),
                f'Action {xmlid} referenciada en menu.xml no existe',
            )
