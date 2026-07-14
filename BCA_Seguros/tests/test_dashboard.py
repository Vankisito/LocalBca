from __future__ import annotations

from datetime import date

from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('BCA_Seguros')
class TestDashboard(TransactionCase):
    """Etapa 3.5 — Agregador del Tablero de Inicio (bca.dashboard).

    El tablero solo lee/agrega: validamos que la estructura del contrato §6
    esté completa y que las cifras cuadren con los search_count equivalentes.
    """

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.dashboard = cls.env['bca.dashboard']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.mxn = cls.env.ref('base.MXN')
        cls.mxn.active = True
        cls.producto = cls.env.ref('BCA_Seguros.producto_metlife_tempolife')

        cls.holding = Partner.create({'name': 'BCA Holding DB', 'bca_tipo': 'holding'})
        cls.promotoria = Partner.create({
            'name': 'Promotoría DB',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = cls._crear_agente('Agente DB', 'CLV-DB-A', 'clave_definitiva')
        cls.prospecto = cls._crear_agente('Prospecto DB', 'CLV-DB-P', 'prospecto')

        cls.contratante = Partner.create({
            'name': 'Contratante DB',
        })
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Conducto DB',
            'codigo_archivo': 'DB_TEST',
            'aseguradora_id': cls.aseguradora.id,
        })

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

    def _crear_poliza(self, **overrides):
        vals = {
            'name': overrides.pop('name', 'POL-DB'),
            'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto.id,
            'agente_id': self.agente.id,
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
            'fecha_pago': fecha or date.today(),
            'prima_neta': recibo.prima_neta,
            'prima_total': recibo.prima_neta,
            'conducto_id': self.conducto.id,
        })
        return recibo

    # --------------------------------------------------------- estructura §6
    def test_estructura_contrato_completa(self) -> None:
        """get_dashboard_data() devuelve todas las claves del contrato §6."""
        data = self.dashboard.get_dashboard_data()
        self.assertEqual(data['moneda'], 'MXN')
        self.assertEqual(
            set(data['cartera']),
            {'activas', 'suma_asegurada', 'borrador', 'vencidas', 'por_ramo'})
        self.assertEqual(
            set(data['cobranza']),
            {'pendientes_num', 'pendientes_monto', 'vencidos_num',
             'vencidos_monto', 'cobrado_mes', 'proximo_fifo', 'tendencia_semanal'})
        self.assertEqual(
            set(data['pca']),
            {'acumulada_anio', 'del_mes', 'computables', 'exclusiones',
             'factores_cargados', 'factores_esperados', 'tendencia_mensual'})
        self.assertEqual(
            set(data['vigencia']), {'al_dia', 'por_caer', 'sin_cobertura'})
        self.assertEqual(
            set(data['importaciones']),
            {'ultima_fecha', 'ultimo_archivo', 'aplicadas', 'no_encontradas',
             'anuladas', 'errores'})
        self.assertEqual(
            set(data['agentes']),
            {'con_licencia', 'prospectos', 'pca_por_promotoria'})
        # Series con longitud fija (el front itera sobre ellas).
        self.assertEqual(len(data['cobranza']['tendencia_semanal']), 6)
        self.assertEqual(len(data['pca']['tendencia_mensual']), 12)
        self.assertEqual(data['pca']['factores_esperados'], 17)

    # ------------------------------------------------------- cifras cuadran
    def test_cifras_cuadran_con_search_count(self) -> None:
        """Las cifras de cartera/cobranza/PCA coinciden con los search_count
        equivalentes (validación cruzada, criterio §10)."""
        # Una póliza activa con su primer recibo pagado.
        poliza = self._crear_poliza(name='POL-DB-ACT')
        recibo = self._pagar(self._confirmar_y_recibo(poliza))
        self.env.flush_all()

        data = self.dashboard.get_dashboard_data()
        Poliza = self.env['bca.poliza']
        Recibo = self.env['bca.recibo']

        self.assertEqual(
            data['cartera']['activas'],
            Poliza.search_count([('estado', '=', 'activa')]))
        self.assertEqual(
            data['cobranza']['pendientes_num'],
            Recibo.search_count([('estado', '=', 'pendiente')]))
        # El recibo pagado computó PCA (factor>0) → cuenta como computable.
        self.assertEqual(
            data['pca']['computables'],
            Recibo.search_count([
                ('estado', '=', 'pagado'), ('factor_aplicado', '>', 0)]))
        self.assertGreater(recibo.pca_aplicada, 0)
        # No hardcodear conteos: la BD puede traer otros agentes (seed / demo).
        # Validamos que la cifra del tablero == search_count equivalente y que
        # nuestros agentes de prueba quedan incluidos.
        Partner = self.env['res.partner']
        self.assertEqual(
            data['agentes']['con_licencia'],
            Partner.search_count([
                ('bca_tipo', '=', 'agente'),
                ('bca_estado_agente', '=', 'clave_definitiva')]))
        self.assertEqual(
            data['agentes']['prospectos'],
            Partner.search_count([
                ('bca_tipo', '=', 'agente'),
                ('bca_estado_agente', '=', 'prospecto')]))
        self.assertGreaterEqual(data['agentes']['con_licencia'], 1)
        self.assertGreaterEqual(data['agentes']['prospectos'], 1)

    # ---------------------------------------------------------- navegación
    def test_action_open_devuelve_act_window(self) -> None:
        """action_open() retorna un act_window con dominio filtrado (DEC-026)."""
        accion = self.dashboard.action_open('cartera_activas')
        self.assertEqual(accion['type'], 'ir.actions.act_window')
        self.assertEqual(accion['res_model'], 'bca.poliza')
        self.assertIn(('estado', '=', 'activa'), accion['domain'])

    def test_action_open_clave_invalida(self) -> None:
        with self.assertRaises(ValueError):
            self.dashboard.action_open('clave_inexistente')

    # ------------------------------------------------------- solo lectura
    def test_no_escribe_en_modelos(self) -> None:
        """El agregador no muta pagado_hasta/pca_aplicada/factor_aplicado."""
        poliza = self._crear_poliza(name='POL-DB-RO')
        recibo = self._pagar(self._confirmar_y_recibo(poliza))
        self.env.flush_all()
        antes = (poliza.pagado_hasta, recibo.pca_aplicada, recibo.factor_aplicado)

        self.dashboard.get_dashboard_data()
        self.dashboard.action_open('vigencia_al_dia')
        self.env.flush_all()

        self.assertEqual(
            (poliza.pagado_hasta, recibo.pca_aplicada, recibo.factor_aplicado),
            antes)
