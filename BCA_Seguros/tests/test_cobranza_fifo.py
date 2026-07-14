from __future__ import annotations

import base64
import csv
import io

from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

from odoo.addons.BCA_Seguros.parsers.metlife_gcaye import COLUMNAS_GCAYE
from odoo.addons.BCA_Seguros.parsers.metlife_lsp import COLUMNAS_LSP


def _csv_b64(headers: list[str], filas: list[dict]) -> bytes:
    """Arma un CSV (texto → base64) con `headers` y una fila por dict."""
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers, extrasaction='ignore')
    writer.writeheader()
    for fila in filas:
        writer.writerow(fila)
    return base64.b64encode(buffer.getvalue().encode('utf-8'))


class _CobranzaFixtures(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.promotoria = Partner.create({
            'name': 'Promotoría C', 'bca_tipo': 'promotoria',
        })
        cls.agente = Partner.create({
            'name': 'Agente C', 'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'C100',
            'estado': 'clave_definitiva',
        })
        cls.contratante = Partner.create({
            'name': 'Contratante C',
        })
        cls.producto_vida = cls.env['product.template'].create({
            'name': 'TempoLife Cobranza',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })
        cls.producto_gmm = cls.env['product.template'].create({
            'name': 'GMM Cobranza',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'gmm',
        })
        cls.conducto = cls.env['bca.conducto'].create({
            'name': 'Conducto Test Cobranza',
            'codigo_archivo': 'TEST_COND_COB',
            'aseguradora_id': cls.aseguradora.id,
        })

    # -- helpers -------------------------------------------------------- #
    def _poliza(self, name: str, ramo: str = 'vida',
                periodicidad: str = 'mensual', confirmar: bool = True):
        """Crea una póliza activa con su plan de recibos pendientes."""
        producto = self.producto_vida if ramo == 'vida' else self.producto_gmm
        pol = self.env['bca.poliza'].create({
            'name': name,
            'aseguradora_id': self.aseguradora.id,
            'producto_id': producto.id,
            'agente_id': self.agente.id,
            'contratante_id': self.contratante.id,
            'periodicidad': periodicidad,
            'fecha_inicio': '2025-01-01',
            'fecha_fin': '2027-01-01',
            'prima_anual': 12000.0,
        })
        if confirmar:
            pol.action_confirmar()
        return pol

    def _fila_vida(self, poliza_name: str, **ov) -> dict:
        base = {
            'numero_poliza': poliza_name,
            'producto': 'TempoLife Cobranza',
            'agente': 'C100',
            'contratante': 'Contratante C',
            'moneda': 'MXN',
            'fecha_aplicacion': '15/01/2025',
            'vigencia_desde': '01/01/2025',
            'vigencia_hasta': '01/02/2025',
            'conducto': self.conducto.codigo_archivo,
            'prima_modal': '1,000.00',
            'recargo': '0.00',
            'prima_total': '1,000.00',
            'comision_informativa': '0.00',
        }
        base.update(ov)
        return base

    def _fila_gmm(self, poliza_name: str, **ov) -> dict:
        base = {
            'numero_poliza': poliza_name,
            'estatus_pago': 'vigente',
            'agente': 'C100',
            'contratante': 'Contratante C',
            'fecha_aplicacion': '15/01/2025',
            'vigencia_desde': '01/01/2025',
            'vigencia_hasta': '01/02/2025',
            'conducto': self.conducto.codigo_archivo,
            'prima_neta': '1,000.00',
            'recargo': '0.00',
            'gastos_expedicion': '0.00',
            'impuestos': '0.00',
            'prima_total': '1,000.00',
            'folio_endoso': '',
        }
        base.update(ov)
        return base

    def _wizard(self, archivo: bytes, ramo: str = 'vida'):
        return self.env['bca.wizard.cobranza.diaria'].create({
            'archivo': archivo,
            'nombre_archivo': 'cobranza.csv',
            'aseguradora_id': self.aseguradora.id,
            'ramo': ramo,
        })

    def _procesar(self, headers, filas, ramo='vida'):
        """Ejecuta el wizard y devuelve la bitácora generada."""
        wizard = self._wizard(_csv_b64(headers, filas), ramo=ramo)
        action = wizard.action_procesar()
        return self.env['bca.bitacora.importacion'].browse(action['res_id'])


@tagged('BCA_Seguros')
class TestCobranzaDiaria(_CobranzaFixtures):
    """Etapa 8 — wizard de cobranza diaria. R-COB-02/03/04/08/09."""

    def test_cinco_filas_cuatro_validas_una_no_encontrada(self) -> None:
        """R-COB-02: 4 pólizas válidas + 1 inexistente → 5 líneas."""
        for i in range(1, 5):
            self._poliza('PV-%d' % i)
        filas = [self._fila_vida('PV-%d' % i) for i in range(1, 5)]
        filas.append(self._fila_vida('NO-EXISTE'))

        bitacora = self._procesar(COLUMNAS_LSP, filas)

        self.assertEqual(len(bitacora.linea_ids), 5)
        self.assertEqual(bitacora.recibos_aplicados, 4)
        self.assertEqual(bitacora.polizas_no_encontradas, 1)
        no_enc = bitacora.linea_ids.filtered(lambda l: l.marca == 'no_encontrada')
        self.assertEqual(no_enc.numero_poliza_raw, 'NO-EXISTE')

    def test_error_en_fila_no_detiene_proceso(self) -> None:
        """R-COB-08: una fila con error no aborta el lote."""
        pol = self._poliza('PV-ERR')
        filas = [
            self._fila_vida('PV-ERR'),                              # fila 1 → recibo 1
            self._fila_vida('PV-ERR'),                              # fila 2 → recibo 2
            self._fila_vida('PV-ERR', fecha_aplicacion='FECHA-MALA'),  # fila 3 → error
            self._fila_vida('PV-ERR'),                              # fila 4 → recibo 3
            self._fila_vida('PV-ERR'),                              # fila 5 → recibo 4
        ]
        bitacora = self._procesar(COLUMNAS_LSP, filas)

        self.assertEqual(len(bitacora.linea_ids), 5)
        self.assertEqual(bitacora.recibos_aplicados, 4)
        self.assertEqual(bitacora.errores_procesamiento, 1)
        linea3 = bitacora.linea_ids.filtered(lambda l: l.numero_fila == 3)
        self.assertEqual(linea3.marca, 'error')
        # Las 4 cuotas pagadas son las primeras (FIFO no se rompe por el error).
        pagados = pol.recibo_ids.filtered(lambda r: r.estado == 'pagado')
        self.assertEqual(sorted(pagados.mapped('numero_recibo')), [1, 2, 3, 4])

    def test_poliza_sin_recibo_pendiente(self) -> None:
        """R-COB-04: póliza ya pagada → marca 'sin_recibo'."""
        pol = self._poliza('PV-PAGADA', periodicidad='anual')
        recibo = pol.recibo_ids.sorted('numero_recibo')[0]
        recibo.action_registrar_pago({
            'fecha_pago': '2025-01-10',
            'prima_neta': 12000.0,
            'prima_total': 12000.0,
            'conducto_id': self.conducto.id,
        })
        # 'anual' genera 1 recibo por anualidad; tras pagarlo no quedan pendientes
        # en la anualidad vigente, pero el avance automático crea la siguiente.
        pol.recibo_ids.filtered(lambda r: r.estado == 'pendiente').unlink()

        bitacora = self._procesar(COLUMNAS_LSP, [self._fila_vida('PV-PAGADA')])

        self.assertEqual(len(bitacora.linea_ids), 1)
        self.assertEqual(bitacora.recibos_aplicados, 0)
        self.assertEqual(bitacora.linea_ids.marca, 'sin_recibo')

    def test_columna_faltante_no_crea_bitacora(self) -> None:
        """R-COB-09: falta columna crítica → UserError, sin bitácora."""
        Bitacora = self.env['bca.bitacora.importacion']
        previas = Bitacora.search_count([])
        headers = [c for c in COLUMNAS_LSP if c != 'prima_modal']
        wizard = self._wizard(_csv_b64(headers, [self._fila_vida('PV-X')]))

        with self.assertRaises(UserError):
            wizard.action_procesar()
        self.assertEqual(Bitacora.search_count([]), previas)

    def test_fifo_aplica_en_orden(self) -> None:
        """R-COB-03: pagos consecutivos toman los recibos en orden ascendente."""
        pol = self._poliza('PV-FIFO')
        filas = [self._fila_vida('PV-FIFO') for _ in range(3)]

        self._procesar(COLUMNAS_LSP, filas)

        pagados = pol.recibo_ids.filtered(lambda r: r.estado == 'pagado')
        self.assertEqual(sorted(pagados.mapped('numero_recibo')), [1, 2, 3])
        pendiente_min = min(
            pol.recibo_ids.filtered(lambda r: r.estado == 'pendiente')
            .mapped('numero_recibo')
        )
        self.assertEqual(pendiente_min, 4)

    def test_gmm_anulado_se_omite(self) -> None:
        """R-COB-01: filas anuladas se omiten y suman a anulaciones_ignoradas."""
        self._poliza('PG-1', ramo='gmm', periodicidad='mensual')
        self._poliza('PG-2', ramo='gmm', periodicidad='mensual')
        filas = [
            self._fila_gmm('PG-1'),
            self._fila_gmm('PG-2', estatus_pago='anulado'),
        ]
        bitacora = self._procesar(COLUMNAS_GCAYE, filas, ramo='gmm')

        self.assertEqual(bitacora.anulaciones_ignoradas, 1)
        self.assertEqual(bitacora.recibos_aplicados, 1)
        marcas = bitacora.linea_ids.mapped('marca')
        self.assertIn('anulado', marcas)


@tagged('BCA_Seguros')
class TestPlantillaCobranzaDescarga(_CobranzaFixtures):
    """Descarga de la plantilla CSV y round-trip: lo que genera el wizard debe
    pasar la propia ``validar_estructura`` del parser (lo descargado es subible).
    """

    def _leer_plantilla(self, ramo: str) -> tuple:
        """Descarga la plantilla del ramo y devuelve (accion, adjunto, reader)."""
        wizard = self.env['bca.wizard.cobranza.diaria'].create({
            'aseguradora_id': self.aseguradora.id,
            'ramo': ramo,
        })
        self.assertFalse(wizard.archivo, 'la descarga no debe exigir archivo')
        accion = wizard.action_descargar_plantilla()
        att_id = int(accion['url'].split('/web/content/')[1].split('?')[0])
        adjunto = self.env['ir.attachment'].browse(att_id)
        texto = base64.b64decode(adjunto.datas).decode('utf-8-sig')
        reader = csv.DictReader(io.StringIO(texto))
        return accion, adjunto, reader

    def test_descargar_plantilla_devuelve_act_url_y_adjunto(self) -> None:
        accion, adjunto, _reader = self._leer_plantilla('vida')
        self.assertEqual(accion['type'], 'ir.actions.act_url')
        self.assertEqual(accion['target'], 'download')
        self.assertIn('/web/content/', accion['url'])
        self.assertEqual(adjunto.name, 'plantilla_cobranza_metlife_vida.csv')
        self.assertEqual(adjunto.mimetype, 'text/csv')
        self.assertTrue(adjunto.datas)
        # Atado al transient para que el vacuum lo purgue.
        self.assertEqual(adjunto.res_model, 'bca.wizard.cobranza.diaria')

    def test_plantilla_vida_tiene_columnas_requeridas(self) -> None:
        _accion, _adjunto, reader = self._leer_plantilla('vida')
        self.assertEqual(reader.fieldnames, COLUMNAS_LSP)
        filas = list(reader)
        self.assertEqual(len(filas), 1, 'plantilla con una fila de ejemplo')

    def test_plantilla_gmm_tiene_columnas_requeridas(self) -> None:
        _accion, adjunto, reader = self._leer_plantilla('gmm')
        self.assertEqual(adjunto.name, 'plantilla_cobranza_metlife_gmm.csv')
        self.assertEqual(reader.fieldnames, COLUMNAS_GCAYE)

    def test_plantilla_round_trip_es_procesable(self) -> None:
        """La plantilla descargada se sube tal cual: estructura válida (no
        lanza UserError) y la fila de ejemplo (póliza inexistente) se reporta."""
        _accion, adjunto, _reader = self._leer_plantilla('vida')
        wizard = self.env['bca.wizard.cobranza.diaria'].create({
            'archivo': adjunto.datas,
            'nombre_archivo': adjunto.name,
            'aseguradora_id': self.aseguradora.id,
            'ramo': 'vida',
        })
        action = wizard.action_procesar()  # no debe lanzar por estructura
        bitacora = self.env['bca.bitacora.importacion'].browse(action['res_id'])
        self.assertEqual(len(bitacora.linea_ids), 1)
        self.assertEqual(bitacora.linea_ids.marca, 'no_encontrada')
