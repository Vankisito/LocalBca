from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('BCA_Seguros')
class TestReportes(TransactionCase):
    """Etapa 9 — Reportes SQL (SICs): PCA por agente/promotoría/consolidado
    (foto inmutable del recibo + solo clave definitiva) y estado de cartera."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.mxn = cls.env.ref('base.MXN')
        cls.mxn.active = True

        cls.holding = Partner.create({'name': 'BCA Holding Rep', 'bca_tipo': 'holding'})
        cls.promotoria = Partner.create({
            'name': 'Promotoría Rep',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = cls._crear_agente('Agente Rep A', 'CLV-REP-A', 'clave_definitiva')
        cls.agente2 = cls._crear_agente('Agente Rep B', 'CLV-REP-B', 'clave_definitiva')
        cls.agente_arranque = cls._crear_agente(
            'Agente Rep Arranque', 'CLV-REP-ARR', 'clave_arranque')

        cls.contratante = Partner.create({
            'name': 'Contratante Rep',
        })
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Conducto Rep',
            'codigo_archivo': 'REP_TEST',
            'aseguradora_id': cls.aseguradora.id,
        })
        # TempoLife: factor 1.0 MXN (seed). Cualquier ramo/factor sirve: los
        # reportes no dependen del valor de PCA, solo de que el recibo se pague.
        cls.producto = cls.env.ref('BCA_Seguros.producto_metlife_tempolife')

    @classmethod
    def _crear_agente(cls, nombre, clave, estado):
        agente = cls.env['res.partner'].create({
            'name': nombre,
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': clave,
            'estado': estado,
        })
        return agente

    def _crear_poliza(self, agente, **overrides):
        vals = {
            'name': overrides.pop('name', 'POL-REP-%s' % agente.id),
            'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto.id,
            'agente_id': agente.id,
            'contratante_id': self.contratante.id,
            'currency_id': self.mxn.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2031, 1, 1),
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

    # ---- SIC 1: PCA por Agente -----------------------------------------------

    def test_sic1_agente_muestra_pca(self) -> None:
        """Tras pagar, el reporte por agente expone 1 fila con la PCA congelada
        y las dimensiones tomadas de la foto del recibo."""
        poliza = self._crear_poliza(self.agente)
        recibo = self._pagar(self._confirmar_y_recibo(poliza))
        self.env.flush_all()

        rep = self.env['bca.reporte.pca.agente'].search([
            ('agente_id', '=', self.agente.id),
        ])
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep.promotoria_id, self.promotoria)
        self.assertEqual(rep.aseguradora_id, self.aseguradora)
        self.assertAlmostEqual(rep.pca, recibo.pca_aplicada, places=2)
        self.assertEqual(rep.pca_currency_id, self.mxn)

    def test_sic1_agente_no_definitiva_no_aparece(self) -> None:
        """R-PCA-03: un agente en clave_arranque NO computa, aunque su recibo
        esté pagado."""
        poliza = self._crear_poliza(self.agente_arranque)
        self._pagar(self._confirmar_y_recibo(poliza))
        self.env.flush_all()

        rep = self.env['bca.reporte.pca.agente'].search([
            ('agente_id', '=', self.agente_arranque.id),
        ])
        self.assertFalse(rep)

    # ---- SIC 2: PCA por Promotoría -------------------------------------------

    def test_sic2_promotoria_agrega_dos_agentes(self) -> None:
        """Dos agentes de la misma promotoría → fila agregada con la suma y el
        conteo de recibos."""
        r1 = self._pagar(self._confirmar_y_recibo(self._crear_poliza(self.agente)))
        r2 = self._pagar(self._confirmar_y_recibo(self._crear_poliza(self.agente2)))
        self.env.flush_all()

        rep = self.env['bca.reporte.pca.promotoria'].search([
            ('promotoria_id', '=', self.promotoria.id),
        ])
        # Mismo aseguradora/ramo/moneda → una sola fila agregada.
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep.recibo_count, 2)
        self.assertAlmostEqual(rep.pca, r1.pca_aplicada + r2.pca_aplicada, places=2)

    # ---- SIC 3: Consolidado --------------------------------------------------

    def test_sic3_consolidado_drilldown(self) -> None:
        """El consolidado mantiene filas detalladas (una por recibo) para el
        drill-down promotoría→agente."""
        self._pagar(self._confirmar_y_recibo(self._crear_poliza(self.agente)))
        self._pagar(self._confirmar_y_recibo(self._crear_poliza(self.agente2)))
        self.env.flush_all()

        rep = self.env['bca.reporte.pca.consolidado'].search([
            ('promotoria_id', '=', self.promotoria.id),
        ])
        self.assertEqual(len(rep), 2)
        self.assertEqual(set(rep.mapped('agente_id')), {self.agente, self.agente2})

    # ---- Inmutabilidad histórica (C2) ----------------------------------------

    def test_reporte_usa_foto_inmutable_del_recibo(self) -> None:
        """Cambiar el agente de la póliza tras el pago NO mueve la PCA ya
        reportada: el reporte sigue la foto del recibo, no la póliza actual."""
        poliza = self._crear_poliza(self.agente)
        self._pagar(self._confirmar_y_recibo(poliza))
        poliza.cambiar_agente(self.agente2, 'Reasignación de prueba')
        self.env.flush_all()

        # La PCA sigue contando para el agente original (foto del recibo)...
        rep_a = self.env['bca.reporte.pca.agente'].search([
            ('agente_id', '=', self.agente.id),
        ])
        self.assertEqual(len(rep_a), 1)
        # ...y NO para el nuevo agente vigente de la póliza.
        rep_b = self.env['bca.reporte.pca.agente'].search([
            ('agente_id', '=', self.agente2.id),
        ])
        self.assertFalse(rep_b)

    # ---- SIC 4: Estado de Cartera --------------------------------------------

    def test_sic4_caida_sin_pagos(self) -> None:
        """Póliza activa sin pagos (pagado_hasta vacío) → caída."""
        poliza = self._crear_poliza(self.agente, name='POL-CAIDA')
        poliza.action_confirmar()
        self.env.flush_all()
        rep = self.env['bca.reporte.estado.cartera'].search([
            ('poliza_id', '=', poliza.id),
        ])
        self.assertEqual(len(rep), 1)
        self.assertEqual(rep.estado_cartera, 'caida')
        self.assertEqual(rep.promotoria_id, self.promotoria)

    def test_sic4_vigente_y_en_riesgo(self) -> None:
        """pagado_hasta lejano → vigente; pagado_hasta dentro de 30 días →
        en_riesgo. Las fechas se anclan relativas a hoy para ser deterministas."""
        hoy = date.today()

        # Vigente: arranca hoy → primer recibo cubre ~1 año (>> hoy + 30d).
        pol_vig = self._crear_poliza(
            self.agente, name='POL-VIGENTE',
            fecha_inicio=hoy, fecha_fin=hoy + relativedelta(years=5),
        )
        rec_vig = self._confirmar_y_recibo(pol_vig)
        self._pagar(rec_vig, fecha=hoy)

        # En riesgo: el primer recibo termina ~15 días después de hoy.
        inicio_riesgo = hoy - relativedelta(years=1) + timedelta(days=15)
        pol_riesgo = self._crear_poliza(
            self.agente2, name='POL-RIESGO',
            fecha_inicio=inicio_riesgo, fecha_fin=inicio_riesgo + relativedelta(years=5),
        )
        rec_riesgo = self._confirmar_y_recibo(pol_riesgo)
        self._pagar(rec_riesgo, fecha=hoy)
        self.env.flush_all()

        rep_vig = self.env['bca.reporte.estado.cartera'].search([
            ('poliza_id', '=', pol_vig.id)])
        rep_riesgo = self.env['bca.reporte.estado.cartera'].search([
            ('poliza_id', '=', pol_riesgo.id)])

        # Sanidad: el corte engendrado cae donde lo planeamos.
        self.assertGreaterEqual(pol_vig.pagado_hasta, hoy + timedelta(days=30))
        self.assertTrue(hoy <= pol_riesgo.pagado_hasta < hoy + timedelta(days=30))

        self.assertEqual(rep_vig.estado_cartera, 'vigente')
        self.assertEqual(rep_riesgo.estado_cartera, 'en_riesgo')
