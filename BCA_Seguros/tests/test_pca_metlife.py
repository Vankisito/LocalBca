from __future__ import annotations

from datetime import date

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('BCA_Seguros')
class TestPcaMetLife(TransactionCase):
    """Calculador de PCA MetLife (Etapa 7): factor por ramo/moneda, exclusiones
    Vida y GMM, conversión a MXN (D-08) y congelamiento al pago (R-PCA-01)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.mxn = cls.env.ref('base.MXN')
        cls.usd = cls.env.ref('base.USD')
        cls.mxn.active = True
        cls.usd.active = True

        cls.holding = Partner.create({'name': 'BCA Holding PCA', 'bca_tipo': 'holding'})
        cls.promotoria = Partner.create({
            'name': 'Promotoría PCA',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = Partner.create({
            'name': 'Agente PCA',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'CLV-PCA',
            'estado': 'clave_definitiva',
        })
        cls.contratante = Partner.create({
            'name': 'Contratante PCA',
        })
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Conducto PCA',
            'codigo_archivo': 'PCA_TEST',
            'aseguradora_id': cls.aseguradora.id,
        })

        # Producto Vida con factor (seed): TempoLife = 100% MXN / 80% USD.
        cls.producto_vida = cls.env.ref('BCA_Seguros.producto_metlife_tempolife')
        # Producto GMM propio (los factores GMM seed no dependen del producto).
        cls.producto_gmm = cls.env['product.template'].create({
            'name': 'GMM PCA Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'gmm',
        })
        # Producto Vida SIN factor asignado (para el caso "sin factor vigente").
        cls.producto_sin_factor = cls.env['product.template'].create({
            'name': 'Vida Sin Factor',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })

        # Tasa USD para ejercitar la conversión a MXN. Solo se crea si USD no es
        # la moneda de la compañía (no se puede tasar la propia moneda base); el
        # test de conversión recalcula con el mismo _convert, así que es robusto
        # sea cual sea la moneda de la compañía del entorno.
        if cls.env.company.currency_id != cls.usd:
            cls.env['res.currency.rate'].create({
                'name': '2026-01-01',
                'currency_id': cls.usd.id,
                'rate': 0.05,  # 1 MXN = 0.05 USD  →  1 USD = 20 MXN
                'company_id': cls.env.company.id,
            })

    def _crear_poliza(self, producto, currency=None, **overrides):
        vals = {
            'name': overrides.pop('name', 'POL-PCA-%s' % producto.id),
            'aseguradora_id': self.aseguradora.id,
            'producto_id': producto.id,
            'agente_id': self.agente.id,
            'contratante_id': self.contratante.id,
            'currency_id': (currency or self.mxn).id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'anual',
            'prima_anual': 12000.0,
            'conducto_id': self.conducto.id,
        }
        vals.update(overrides)
        return self.env['bca.poliza'].create(vals)

    def _confirmar_y_recibo(self, poliza):
        poliza.action_confirmar()
        return poliza.recibo_ids.sorted('numero_recibo')[0]

    def _pagar(self, recibo, fecha=None):
        recibo.action_registrar_pago({
            'fecha_pago': fecha or date(2026, 3, 1),
            'prima_neta': recibo.prima_neta,
            'prima_total': recibo.prima_neta,
            'conducto_id': self.conducto.id,
        })
        return recibo

    # ---- Vida ----------------------------------------------------------------

    def test_vida_mxn_factor_1(self) -> None:
        """Vida MXN: factor 1.0 → PCA = prima_neta (en MXN)."""
        poliza = self._crear_poliza(self.producto_vida, self.mxn)
        recibo = self._confirmar_y_recibo(poliza)
        prima = recibo.prima_neta
        self._pagar(recibo)
        self.assertEqual(recibo.estado, 'pagado')
        self.assertAlmostEqual(recibo.factor_aplicado, 1.0, places=4)
        self.assertAlmostEqual(recibo.pca_aplicada, prima, places=2)
        self.assertEqual(recibo.pca_currency_id, self.mxn)
        self.assertFalse(recibo.motivo_exclusion_pca)

    def test_vida_usd_factor_080_convertido_a_mxn(self) -> None:
        """Vida USD: selecciona la fila USD (0.8) y convierte el resultado a MXN."""
        poliza = self._crear_poliza(self.producto_vida, self.usd)
        recibo = self._confirmar_y_recibo(poliza)
        prima = recibo.prima_neta
        self._pagar(recibo)
        self.assertAlmostEqual(recibo.factor_aplicado, 0.8, places=4)
        self.assertEqual(recibo.pca_currency_id, self.mxn)
        esperado = self.usd._convert(
            prima * 0.8, self.mxn, self.env.company, date(2026, 3, 1)
        )
        self.assertAlmostEqual(recibo.pca_aplicada, esperado, places=2)

    def test_vida_excluye_aportacion_adicional(self) -> None:
        poliza = self._crear_poliza(self.producto_vida, self.mxn,
                                    es_aportacion_adicional=True)
        recibo = self._pagar(self._confirmar_y_recibo(poliza))
        self.assertAlmostEqual(recibo.pca_aplicada, 0.0, places=2)
        self.assertAlmostEqual(recibo.factor_aplicado, 0.0, places=4)
        self.assertIn('Aportación adicional', recibo.motivo_exclusion_pca)

    def test_vida_excluye_temporalidad_menor_10(self) -> None:
        poliza = self._crear_poliza(self.producto_vida, self.mxn,
                                    temporalidad_anios=5)
        recibo = self._pagar(self._confirmar_y_recibo(poliza))
        self.assertAlmostEqual(recibo.pca_aplicada, 0.0, places=2)
        self.assertIn('Temporalidad', recibo.motivo_exclusion_pca)

    def test_vida_temporalidad_10_no_excluye(self) -> None:
        poliza = self._crear_poliza(self.producto_vida, self.mxn,
                                    temporalidad_anios=10)
        recibo = self._confirmar_y_recibo(poliza)
        prima = recibo.prima_neta
        self._pagar(recibo)
        self.assertAlmostEqual(recibo.factor_aplicado, 1.0, places=4)
        self.assertAlmostEqual(recibo.pca_aplicada, prima, places=2)

    def test_vida_sin_factor_vigente(self) -> None:
        poliza = self._crear_poliza(self.producto_sin_factor, self.mxn)
        recibo = self._pagar(self._confirmar_y_recibo(poliza))
        self.assertAlmostEqual(recibo.pca_aplicada, 0.0, places=2)
        self.assertEqual(recibo.motivo_exclusion_pca, 'Sin factor PCA vigente')

    # ---- GMM -----------------------------------------------------------------

    def test_gmm_coaseguro10_deducible_alto_factor_120(self) -> None:
        """Coaseguro 10% + deducible ≥ 29,000 → factor 1.2."""
        poliza = self._crear_poliza(self.producto_gmm, self.mxn,
                                    coaseguro=0.10, deducible=30000.0)
        recibo = self._confirmar_y_recibo(poliza)
        prima = recibo.prima_neta
        self._pagar(recibo)
        self.assertAlmostEqual(recibo.factor_aplicado, 1.2, places=4)
        self.assertAlmostEqual(recibo.pca_aplicada, prima * 1.2, places=2)

    def test_gmm_coaseguro10_deducible_bajo_factor_100(self) -> None:
        """Coaseguro 10% + deducible < 29,000 → factor 1.0."""
        poliza = self._crear_poliza(self.producto_gmm, self.mxn,
                                    coaseguro=0.10, deducible=20000.0)
        recibo = self._confirmar_y_recibo(poliza)
        prima = recibo.prima_neta
        self._pagar(recibo)
        self.assertAlmostEqual(recibo.factor_aplicado, 1.0, places=4)
        self.assertAlmostEqual(recibo.pca_aplicada, prima, places=2)

    def test_gmm_excluye_coaseguro_5(self) -> None:
        """Coaseguro ≤ 5% no computa PCA."""
        poliza = self._crear_poliza(self.producto_gmm, self.mxn,
                                    coaseguro=0.05, deducible=30000.0)
        recibo = self._pagar(self._confirmar_y_recibo(poliza))
        self.assertAlmostEqual(recibo.pca_aplicada, 0.0, places=2)
        self.assertIn('Coaseguro', recibo.motivo_exclusion_pca)

    # ---- R-PCA-01: congelamiento ---------------------------------------------

    def test_pca_congelada_al_pago(self) -> None:
        """Tras pagar, cambiar el factor del catálogo NO recalcula el recibo."""
        poliza = self._crear_poliza(self.producto_vida, self.mxn)
        recibo = self._confirmar_y_recibo(poliza)
        prima = recibo.prima_neta
        self._pagar(recibo)
        pca_original = recibo.pca_aplicada
        factor_original = recibo.factor_aplicado

        factor_rec = self.env.ref('BCA_Seguros.factor_metlife_tempolife_mxn')
        factor_rec.factor = 0.5

        self.assertAlmostEqual(recibo.pca_aplicada, pca_original, places=2)
        self.assertAlmostEqual(recibo.factor_aplicado, factor_original, places=4)
        self.assertAlmostEqual(recibo.pca_aplicada, prima, places=2)
