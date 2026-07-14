from __future__ import annotations

from datetime import date

from odoo.exceptions import UserError, ValidationError
from odoo.tests.common import TransactionCase, tagged

from ..parsers import (
    ParserMetLifeGMM,
    ParserMetLifeVida,
    ParserQualitas,
    get_parser,
)


@tagged('BCA_Seguros')
class TestParserRegistry(TransactionCase):
    """Etapa 6 — A4: dispatcher con error descriptivo."""

    def test_get_parser_metlife_vida_returns_class(self) -> None:
        self.assertIs(get_parser('METLIFE', 'vida'), ParserMetLifeVida)

    def test_get_parser_metlife_gmm_returns_class(self) -> None:
        self.assertIs(get_parser('METLIFE', 'gmm'), ParserMetLifeGMM)

    def test_get_parser_qualitas_returns_class(self) -> None:
        self.assertIs(get_parser('QUALITAS', 'autos'), ParserQualitas)

    def test_get_parser_desconocida_raises_usererror(self) -> None:
        with self.assertRaises(UserError) as ctx:
            get_parser('AXA', 'vida')
        self.assertIn('Parsers disponibles', str(ctx.exception))


@tagged('BCA_Seguros')
class TestParserBase(TransactionCase):
    """Etapa 6 — A5: validar_estructura y normalizadores."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.bitacora = cls.env['bca.bitacora.importacion'].sudo().create({
            'aseguradora_id': cls.aseguradora.id,
            'ramo': 'vida',
            'nombre_archivo': 'base_test.csv',
        })
        cls.parser = ParserMetLifeVida(cls.env, cls.bitacora)

    def test_validar_estructura_detecta_columnas_faltantes(self) -> None:
        incompletas = [c for c in self.parser.columnas_requeridas
                       if c != 'numero_poliza']
        with self.assertRaises(UserError) as ctx:
            self.parser.validar_estructura(incompletas)
        self.assertIn('numero_poliza', str(ctx.exception))

    def test_normalizar_monto_coma_miles(self) -> None:
        self.assertAlmostEqual(
            self.parser.normalizar_monto('1,234.56'), 1234.56, places=2)

    def test_normalizar_monto_sin_separador(self) -> None:
        self.assertAlmostEqual(
            self.parser.normalizar_monto('1234.56'), 1234.56, places=2)

    def test_normalizar_monto_vacio_es_cero(self) -> None:
        self.assertEqual(self.parser.normalizar_monto(''), 0.0)
        self.assertEqual(self.parser.normalizar_monto(None), 0.0)
        self.assertEqual(self.parser.normalizar_monto('   '), 0.0)

    def test_normalizar_fecha_formato_metlife(self) -> None:
        self.assertEqual(
            self.parser.normalizar_fecha('15/03/2026'), date(2026, 3, 15))

    def test_normalizar_fecha_invalida_lanza_error(self) -> None:
        with self.assertRaises(ValidationError):
            self.parser.normalizar_fecha('2026-03-15')


@tagged('BCA_Seguros')
class TestParserMetLifeVida(TransactionCase):
    """Etapa 6 — procesar_fila LSP (R-COB-02/04/06/08)."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Conducto Test Vida',
            'codigo_archivo': 'TEST_COND_VIDA',
            'aseguradora_id': cls.aseguradora.id,
        })
        cls.holding = Partner.create({
            'name': 'Holding Vida Test',
            'bca_tipo': 'holding',
        })
        cls.promotoria = Partner.create({
            'name': 'Promo Vida Test',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = Partner.create({
            'name': 'Agente Vida Test',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        # Rollup bca_estado_agente: clave definitiva vía puente (fuente de verdad).
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'CLV-PV',
            'estado': 'clave_definitiva',
        })
        cls.contratante = Partner.create({
            'name': 'Cliente Vida Test',
        })
        cls.producto = cls.env['product.template'].create({
            'name': 'Vida LSP Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })
        cls.poliza = cls.env['bca.poliza'].create({
            'name': 'POL-VIDA-001',
            'aseguradora_id': cls.aseguradora.id,
            'producto_id': cls.producto.id,
            'agente_id': cls.agente.id,
            'contratante_id': cls.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'mensual',
            'prima_anual': 12000.0,
        })
        cls.poliza.action_confirmar()
        cls.bitacora = cls.env['bca.bitacora.importacion'].sudo().create({
            'aseguradora_id': cls.aseguradora.id,
            'ramo': 'vida',
            'nombre_archivo': 'lsp_test.csv',
        })
        cls.parser = ParserMetLifeVida(cls.env, cls.bitacora)

    def _fila_valida(self, **overrides) -> dict:
        fila = {
            'numero_poliza': 'POL-VIDA-001',
            'producto': 'Vida LSP Test',
            'agente': 'Agente Vida Test',
            'contratante': 'Cliente Vida Test',
            'moneda': 'MXN',
            'fecha_aplicacion': '15/01/2026',
            'vigencia_desde': '01/01/2026',
            'vigencia_hasta': '01/02/2026',
            'conducto': self.conducto.codigo_archivo,
            'prima_modal': '1,000.00',
            'recargo': '0.00',
            'prima_total': '1,000.00',
            'comision_informativa': '100.00',
        }
        fila.update(overrides)
        return fila

    def test_metlife_vida_procesa_fila_basica(self) -> None:
        resultado = self.parser.procesar_fila(self.env, self._fila_valida(), 1)
        self.assertEqual(resultado['marca'], 'aplicado')
        self.assertEqual(resultado['numero_poliza_raw'], 'POL-VIDA-001')
        recibo = self.env['bca.recibo'].browse(resultado['recibo_id'])
        self.assertEqual(recibo.estado, 'pagado')
        self.assertEqual(recibo.numero_recibo, 1, 'FIFO: primer recibo es el 1')
        self.assertAlmostEqual(recibo.prima_neta, 1000.0, places=2)
        self.assertEqual(recibo.conducto_id, self.conducto)

    def test_metlife_vida_poliza_no_encontrada(self) -> None:
        resultado = self.parser.procesar_fila(
            self.env, self._fila_valida(numero_poliza='POL-NO-EXISTE'), 1)
        self.assertEqual(resultado['marca'], 'no_encontrada')
        self.assertFalse(resultado['recibo_id'])
        for r in self.poliza.recibo_ids:
            self.assertEqual(r.estado, 'pendiente',
                             'Recibos intactos cuando no hay match de póliza')

    def test_metlife_vida_sin_recibo_pendiente(self) -> None:
        for r in self.poliza.recibo_ids:
            r.sudo().write({
                'estado': 'pagado',
                'fecha_pago': date(2026, 1, 1),
                'pca_aplicada': 0.0,
                'factor_aplicado': 0.0,
            })
        resultado = self.parser.procesar_fila(self.env, self._fila_valida(), 1)
        self.assertEqual(resultado['marca'], 'sin_recibo')
        self.assertFalse(resultado['recibo_id'])

    def test_metlife_vida_conducto_no_match_continua(self) -> None:
        resultado = self.parser.procesar_fila(
            self.env, self._fila_valida(conducto='CONDUCTO_INVENTADO'), 1)
        self.assertEqual(resultado['marca'], 'advertencia')
        self.assertTrue(resultado['recibo_id'])
        recibo = self.env['bca.recibo'].browse(resultado['recibo_id'])
        self.assertEqual(recibo.estado, 'pagado')
        self.assertFalse(recibo.conducto_id,
                         'conducto_id queda vacío cuando no hay match')

    def test_metlife_vida_tolerancia_fila_con_error(self) -> None:
        resultado = self.parser.procesar_fila(
            self.env, self._fila_valida(prima_modal='0.00'), 1)
        self.assertEqual(resultado['marca'], 'error',
                         'R-COB-08: error en fila no propaga, se reporta')
        primer_recibo = self.poliza.recibo_ids.sorted('numero_recibo')[0]
        self.assertEqual(primer_recibo.estado, 'pendiente',
                         'Savepoint hace rollback de la fila fallida')


@tagged('BCA_Seguros')
class TestParserMetLifeGMM(TransactionCase):
    """Etapa 6 — procesar_fila GCAYE + R-COB-01 anulaciones."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Conducto Test GMM',
            'codigo_archivo': 'TEST_COND_GMM',
            'aseguradora_id': cls.aseguradora.id,
        })
        cls.holding = Partner.create({
            'name': 'Holding GMM Test',
            'bca_tipo': 'holding',
        })
        cls.promotoria = Partner.create({
            'name': 'Promo GMM Test',
            'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = Partner.create({
            'name': 'Agente GMM Test',
            'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        # Rollup bca_estado_agente: clave definitiva vía puente (fuente de verdad).
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'CLV-PG',
            'estado': 'clave_definitiva',
        })
        cls.contratante = Partner.create({
            'name': 'Cliente GMM Test',
        })
        cls.producto = cls.env['product.template'].create({
            'name': 'GMM GCAYE Test',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'gmm',
        })
        cls.poliza = cls.env['bca.poliza'].create({
            'name': 'POL-GMM-001',
            'aseguradora_id': cls.aseguradora.id,
            'producto_id': cls.producto.id,
            'agente_id': cls.agente.id,
            'contratante_id': cls.contratante.id,
            'fecha_inicio': date(2026, 1, 1),
            'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'mensual',
            'prima_anual': 12000.0,
        })
        cls.poliza.action_confirmar()
        cls.bitacora = cls.env['bca.bitacora.importacion'].sudo().create({
            'aseguradora_id': cls.aseguradora.id,
            'ramo': 'gmm',
            'nombre_archivo': 'gcaye_test.csv',
        })
        cls.parser = ParserMetLifeGMM(cls.env, cls.bitacora)

    def _fila_valida(self, **overrides) -> dict:
        fila = {
            'numero_poliza': 'POL-GMM-001',
            'estatus_pago': 'normal',
            'agente': 'Agente GMM Test',
            'contratante': 'Cliente GMM Test',
            'fecha_aplicacion': '15/01/2026',
            'vigencia_desde': '01/01/2026',
            'vigencia_hasta': '01/02/2026',
            'conducto': self.conducto.codigo_archivo,
            'prima_neta': '1,000.00',
            'recargo': '0.00',
            'gastos_expedicion': '0.00',
            'impuestos': '0.00',
            'prima_total': '1,000.00',
            'folio_endoso': 'END-001',
        }
        fila.update(overrides)
        return fila

    def test_metlife_gmm_anulacion_se_ignora(self) -> None:
        anulaciones_antes = self.bitacora.anulaciones_ignoradas
        filas = [
            self._fila_valida(numero_poliza='POL-AAA', estatus_pago='ANULADO'),
            self._fila_valida(),
        ]
        filtradas = self.parser.filtrar_filas(filas)
        self.assertEqual(len(filtradas), 1)
        self.assertEqual(filtradas[0]['numero_poliza'], 'POL-GMM-001')
        self.bitacora.invalidate_recordset(['anulaciones_ignoradas'])
        self.assertEqual(
            self.bitacora.anulaciones_ignoradas, anulaciones_antes + 1)
        lineas_anuladas = self.env['bca.bitacora.linea'].search([
            ('bitacora_id', '=', self.bitacora.id),
            ('marca', '=', 'anulado'),
        ])
        self.assertTrue(lineas_anuladas,
                        'Debe crearse línea bitácora marca=anulado')

    def test_metlife_gmm_folio_endoso_se_propaga(self) -> None:
        resultado = self.parser.procesar_fila(
            self.env, self._fila_valida(folio_endoso='ENDOSO-XYZ'), 1)
        self.assertEqual(resultado['marca'], 'aplicado')
        recibo = self.env['bca.recibo'].browse(resultado['recibo_id'])
        self.assertEqual(recibo.folio_endoso, 'ENDOSO-XYZ')

    def test_metlife_gmm_estructura_requiere_folio_endoso(self) -> None:
        fieldnames = [c for c in self.parser.columnas_requeridas
                      if c != 'folio_endoso']
        with self.assertRaises(UserError) as ctx:
            self.parser.validar_estructura(fieldnames)
        self.assertIn('folio_endoso', str(ctx.exception))


@tagged('BCA_Seguros')
class TestParserQualitas(TransactionCase):
    """Etapa 6 — placeholder post v1.0."""

    def test_qualitas_lanza_not_implemented(self) -> None:
        aseguradora = self.env.ref('BCA_Seguros.partner_qualitas')
        bitacora = self.env['bca.bitacora.importacion'].sudo().create({
            'aseguradora_id': aseguradora.id,
            'nombre_archivo': 'qualitas_test.csv',
        })
        parser = ParserQualitas(self.env, bitacora)
        with self.assertRaises(NotImplementedError):
            parser.procesar_fila(self.env, {'numero_poliza': 'X'}, 1)
