from __future__ import annotations

from datetime import date

from odoo import Command
from odoo.tests.common import TransactionCase


class TestPolizaCoberturas(TransactionCase):
    """Coberturas modeladas con atributos nativos (product.attribute /
    product.template.attribute.value). Verifica el seed, el selector encadenado
    por producto y que el dominio rechaza una cobertura de otro producto."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.attr_basica = cls.env.ref('BCA_Seguros.attr_cobertura_basica')
        cls.attr_adicional = cls.env.ref('BCA_Seguros.attr_cobertura_adicional')
        # Productos con catálogo distinto (para probar el filtrado por producto).
        cls.horizonte = cls.env.ref('BCA_Seguros.producto_metlife_horizonte')
        cls.medicalife = cls.env.ref('BCA_Seguros.producto_metlife_gmm_medicalife')

        Partner = cls.env['res.partner']
        cls.agente = Partner.create({'name': 'Agente C', 'bca_tipo': 'agente'})
        cls.contratante = Partner.create({'name': 'Contratante C'})

    def _ptav(self, producto, attribute):
        """PTAV materializadas para (producto, atributo)."""
        return self.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', producto.id),
            ('attribute_id', '=', attribute.id),
            ('ptav_active', '=', True),
        ])

    def _crear_poliza(self, producto, **overrides) -> object:
        vals = {
            'name': 'POL-COB-001',
            'aseguradora_id': self.aseguradora.id,
            'producto_id': producto.id,
            'agente_id': self.agente.id,
            'contratante_id': self.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'anual',
            'prima_anual': 10000.0,
        }
        vals.update(overrides)
        return self.env['bca.poliza'].create(vals)

    def test_seed_atributos_no_variant(self) -> None:
        """Los atributos de cobertura no generan variantes."""
        self.assertEqual(self.attr_basica.create_variant, 'no_variant')
        self.assertEqual(self.attr_adicional.create_variant, 'no_variant')

    def test_producto_materializa_ptav(self) -> None:
        """Cada producto expone solo sus coberturas (PTAV materializadas)."""
        adic_horizonte = self._ptav(self.horizonte, self.attr_adicional)
        adic_medicalife = self._ptav(self.medicalife, self.attr_adicional)
        self.assertTrue(adic_horizonte, 'Horizonte debe tener adicionales')
        self.assertTrue(adic_medicalife, 'MedicaLife debe tener opcionales')
        # No hay solape: las opcionales GMM no son las adicionales Vida.
        self.assertFalse(adic_horizonte & adic_medicalife)

    def test_helper_attrs_resuelven(self) -> None:
        """Los campos helper resuelven los atributos agrupadores (para el dominio)."""
        pol = self._crear_poliza(self.horizonte)
        self.assertEqual(pol.cobertura_basica_attr_id, self.attr_basica)
        self.assertEqual(pol.cobertura_adicional_attr_id, self.attr_adicional)

    def test_asignar_coberturas_del_producto(self) -> None:
        """Se pueden asignar coberturas que ofrece el producto contratado."""
        pol = self._crear_poliza(self.horizonte)
        basica = self._ptav(self.horizonte, self.attr_basica)[:1]
        adicionales = self._ptav(self.horizonte, self.attr_adicional)
        pol.write({
            'cobertura_basica_id': basica.id,
            'cobertura_adicional_ids': [Command.set(adicionales.ids)],
        })
        self.assertEqual(pol.cobertura_basica_id, basica)
        self.assertEqual(pol.cobertura_adicional_ids, adicionales)

    def test_onchange_producto_limpia_coberturas(self) -> None:
        """Cambiar de producto limpia las coberturas (quedan de otro template)."""
        pol = self._crear_poliza(self.horizonte)
        adicionales = self._ptav(self.horizonte, self.attr_adicional)
        pol.cobertura_adicional_ids = [Command.set(adicionales.ids)]

        form_pol = pol
        form_pol.producto_id = self.medicalife
        form_pol._onchange_producto_limpiar_coberturas()
        self.assertFalse(form_pol.cobertura_basica_id)
        self.assertFalse(form_pol.cobertura_adicional_ids)

    def test_ptav_de_otro_producto_no_pertenece_al_dominio(self) -> None:
        """La cobertura de un producto no aparece en el dominio de otro producto.

        Es la garantía del selector Aseguradora→Ramo→Producto→Coberturas:
        el dominio filtra por product_tmpl_id, así que las opcionales de
        MedicaLife nunca son elegibles en una póliza de Horizonte."""
        adic_medicalife = self._ptav(self.medicalife, self.attr_adicional)
        elegibles_horizonte = self.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', self.horizonte.id),
            ('attribute_id', '=', self.attr_adicional.id),
            ('ptav_active', '=', True),
        ])
        self.assertFalse(
            adic_medicalife & elegibles_horizonte,
            'Las opcionales GMM no deben ser elegibles en una póliza Vida.',
        )
