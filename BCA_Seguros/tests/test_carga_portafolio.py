from __future__ import annotations

import base64
import io
from datetime import date, timedelta

import openpyxl

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase, tagged

# Encabezados mínimos por hoja para los fixtures (subset del layout real).
HEADERS_VIDA = [
    'Póliza', 'Producto', 'Clave de Agente', 'Nombre del Contratante',
    'Nombre del Asegurado', 'Moneda', 'Fecha inicio Vigencia',
    'Fecha Fin Vigencia', 'Frecuencia de Pago', 'Prima de Riesgo Anual',
    'Pagado Hasta', 'Estatus de Póliza', 'Estatus de Pago', 'R.F.C. Contratante',
    'Nombre del Beneficiario 1', 'Parentesco 1', '% al que tiene Derecho 1',
    'Nombre del Beneficiario 2', 'Parentesco 2', '% al que tiene Derecho 2',
]
HEADERS_GMM = [
    'Poliza actual', 'Producto', 'Clave de Agente', 'Nombre del Contratante',
    'Moneda', 'Fecha inicio Vigencia', 'Fecha Fin Vigencia',
    'Frecuencia de Pago', 'Prima de Riesgo Anual', 'Deducible', 'Coaseguro',
    'Pagado Hasta', 'Nombre del Asegurado 1', 'Parentesco 1',
    'Fecha de nacimiento (Asegurado 1)',
]
# Hoja de beneficiarios en formato largo (B05).
HEADERS_BENEFICIARIOS = [
    'Póliza', 'Nombre del Beneficiario', 'Parentesco',
    '% al que tiene Derecho', 'Fecha de Nacimiento',
]
# Hoja de coberturas adicionales en formato largo.
HEADERS_COBERTURAS = [
    'Póliza', 'Cobertura Adicional', 'Descripción Plan Suplementario',
]


def _build_xlsx(sheets: dict) -> bytes:
    """sheets = {nombre: (headers, [fila_dict, ...])}. Encabezados en fila 1,
    datos desde fila 2 (estructura del layout real)."""
    wb = openpyxl.Workbook()
    wb.remove(wb.active)
    for nombre, (headers, filas) in sheets.items():
        ws = wb.create_sheet(nombre)
        ws.append(headers)                              # fila 1: encabezados
        for fila in filas:                              # fila 2+: datos
            ws.append([fila.get(h, '') for h in headers])
    buffer = io.BytesIO()
    wb.save(buffer)
    return base64.b64encode(buffer.getvalue())


class _PortafolioFixtures(TransactionCase):
    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        Partner = cls.env['res.partner']
        cls.aseguradora = cls.env.ref('BCA_Seguros.partner_metlife')
        cls.holding = Partner.create({'name': 'Holding P', 'bca_tipo': 'holding'})
        cls.promotoria = Partner.create({
            'name': 'Promotoría P', 'bca_tipo': 'promotoria',
            'parent_id': cls.holding.id,
        })
        cls.agente = Partner.create({
            'name': 'Agente P', 'bca_tipo': 'agente',
            'parent_id': cls.promotoria.id,
        })
        cls.env['res.partner.agente.aseguradora'].create({
            'agente_id': cls.agente.id,
            'aseguradora_id': cls.aseguradora.id,
            'clave_agente': 'A100',
            'estado': 'clave_definitiva',
        })
        cls.producto_vida = cls.env['product.template'].create({
            'name': 'TempoLife Portafolio',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
        })
        cls.producto_gmm = cls.env['product.template'].create({
            'name': 'GMM Portafolio',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'gmm',
        })

    def _wizard(self, archivo: bytes, modo: str = 'crear_actualizar'):
        return self.env['bca.wizard.carga.portafolio'].create({
            'archivo': archivo,
            'nombre_archivo': 'portafolio.xlsx',
            'aseguradora_id': self.aseguradora.id,
            'modo': modo,
        })

    def _fila_vida(self, **ov) -> dict:
        base = {
            'Póliza': 'PV-001', 'Producto': 'TempoLife Portafolio',
            'Clave de Agente': 'A100', 'Nombre del Contratante': 'Juan Pérez',
            'Nombre del Asegurado': 'Juan Pérez', 'Moneda': 'MXN',
            'Fecha inicio Vigencia': '01/01/2025', 'Fecha Fin Vigencia': '01/01/2027',
            'Frecuencia de Pago': 'Mensual', 'Prima de Riesgo Anual': '12,000.00',
            'Pagado Hasta': '', 'Estatus de Póliza': 'Vigente',
            'Estatus de Pago': 'Al corriente', 'R.F.C. Contratante': 'PEPJ800101AAA',
        }
        base.update(ov)
        return base

    def _fila_gmm(self, **ov) -> dict:
        base = {
            'Poliza actual': 'PG-001', 'Producto': 'GMM Portafolio',
            'Clave de Agente': 'A100', 'Nombre del Contratante': 'Ana López',
            'Moneda': 'MXN', 'Fecha inicio Vigencia': '01/01/2025',
            'Fecha Fin Vigencia': '01/01/2026', 'Frecuencia de Pago': 'Anual',
            'Prima de Riesgo Anual': '20,000.00', 'Deducible': '30,000.00',
            'Coaseguro': '10',
        }
        base.update(ov)
        return base


@tagged('BCA_Seguros')
class TestCargaPortafolioValidacion(_PortafolioFixtures):
    """Fase VALIDAR: estructura y dry-run sin tocar BD."""

    def test_validar_sin_hoja_soportada(self) -> None:
        archivo = _build_xlsx({'OTRA': (['x'], [{'x': 1}])})
        with self.assertRaises(UserError):
            self._wizard(archivo).action_validar()

    def test_validar_columna_faltante(self) -> None:
        headers = [h for h in HEADERS_VIDA if h != 'Producto']
        archivo = _build_xlsx({'VIDA': (headers, [self._fila_vida()])})
        with self.assertRaises(UserError):
            self._wizard(archivo).action_validar()

    def test_validar_no_crea_polizas(self) -> None:
        archivo = _build_xlsx({'VIDA': (HEADERS_VIDA, [self._fila_vida()])})
        wizard = self._wizard(archivo)
        wizard.action_validar()
        self.assertEqual(wizard.state, 'validado')
        self.assertEqual(wizard.total_filas, 1)
        self.assertFalse(self.env['bca.poliza'].search([('name', '=', 'PV-001')]))

    def test_validar_marca_agente_inexistente(self) -> None:
        fila = self._fila_vida(**{'Clave de Agente': 'NOPE'})
        archivo = _build_xlsx({'VIDA': (HEADERS_VIDA, [fila])})
        wizard = self._wizard(archivo)
        wizard.action_validar()
        self.assertEqual(wizard.rechazadas, 1)


@tagged('BCA_Seguros')
class TestCargaPortafolioGrabado(_PortafolioFixtures):
    """Fase GRABAR: creación, corte por Pagado Hasta, beneficiarios, duplicados."""

    def _grabar(self, sheets: dict, modo: str = 'crear_actualizar'):
        wizard = self._wizard(_build_xlsx(sheets), modo=modo)
        wizard.action_validar()
        wizard.action_grabar()
        return wizard

    def test_crea_vida_y_gmm(self) -> None:
        wizard = self._grabar({
            'VIDA': (HEADERS_VIDA, [self._fila_vida()]),
            'GMM': (HEADERS_GMM, [self._fila_gmm()]),
        })
        self.assertEqual(wizard.creadas, 2)
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        gmm = self.env['bca.poliza'].search([('name', '=', 'PG-001')])
        self.assertEqual(vida.agente_id, self.agente)
        self.assertEqual(vida.estado, 'activa')
        self.assertEqual(vida.contratante_id.name, 'Juan Pérez')
        self.assertAlmostEqual(gmm.coaseguro, 0.10, places=2)
        self.assertEqual(gmm.estado, 'activa')

    def test_pagado_hasta_genera_solo_recibos_posteriores(self) -> None:
        fila = self._fila_vida(**{'Pagado Hasta': '30/06/2025'})
        self._grabar({'VIDA': (HEADERS_VIDA, [fila])})
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        self.assertEqual(vida.pagado_hasta_inicial, date(2025, 6, 30))
        self.assertTrue(vida.recibo_ids)
        primera = min(vida.recibo_ids.mapped('fecha_desde'))
        self.assertGreaterEqual(primera, date(2025, 6, 30),
                                'No deben generarse recibos antes del corte.')
        # pagado_hasta operativo sigue vacío (no hay recibos pagados).
        self.assertFalse(vida.pagado_hasta)

    def test_beneficiarios_vida_y_dependientes_gmm(self) -> None:
        fila_v = self._fila_vida(**{
            'Nombre del Beneficiario 1': 'Hijo Uno', 'Parentesco 1': 'Hijo',
            '% al que tiene Derecho 1': '50',
            'Nombre del Beneficiario 2': 'Hija Dos', 'Parentesco 2': 'Hija',
            '% al que tiene Derecho 2': '50',
        })
        fila_g = self._fila_gmm(**{
            'Nombre del Asegurado 1': 'Dependiente Uno', 'Parentesco 1': 'Cónyuge',
            'Fecha de nacimiento (Asegurado 1)': '15/05/1990',
        })
        self._grabar({
            'VIDA': (HEADERS_VIDA, [fila_v]),
            'GMM': (HEADERS_GMM, [fila_g]),
        })
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        gmm = self.env['bca.poliza'].search([('name', '=', 'PG-001')])
        self.assertEqual(len(vida.beneficiario_ids), 2)
        self.assertAlmostEqual(
            sum(vida.beneficiario_ids.mapped('porcentaje')), 100.0, places=2)
        self.assertEqual(len(gmm.beneficiario_ids), 1)
        self.assertEqual(gmm.beneficiario_ids.fecha_nacimiento, date(1990, 5, 15))

    def test_modo_solo_crear_rechaza_duplicado(self) -> None:
        sheets = {'VIDA': (HEADERS_VIDA, [self._fila_vida()])}
        self._grabar(sheets)
        wizard2 = self._grabar(sheets, modo='solo_crear')
        self.assertEqual(wizard2.creadas, 0)
        self.assertEqual(wizard2.rechazadas, 1)

    def test_clave_agente_tolera_ceros_a_la_izquierda(self) -> None:
        # La aseguradora registra la clave con padding ('000019799') pero el
        # Excel la trae sin ceros ('19799', celda numérica). Debe resolver.
        agente = self.env['res.partner'].create({
            'name': 'Agente Padded', 'bca_tipo': 'agente',
            'parent_id': self.promotoria.id,
        })
        self.env['res.partner.agente.aseguradora'].create({
            'agente_id': agente.id, 'aseguradora_id': self.aseguradora.id,
            'clave_agente': '000019799', 'estado': 'clave_definitiva',
        })
        fila = self._fila_vida(**{'Póliza': 'PV-PAD', 'Clave de Agente': '19799'})
        wizard = self._grabar({'VIDA': (HEADERS_VIDA, [fila])})
        self.assertEqual(wizard.creadas, 1)
        self.assertEqual(wizard.rechazadas, 0)
        pol = self.env['bca.poliza'].search([('name', '=', 'PV-PAD')])
        self.assertEqual(pol.agente_id, agente)

    def test_fila_con_error_no_detiene_proceso(self) -> None:
        ok = self._fila_vida(**{'Póliza': 'PV-OK'})
        malo = self._fila_vida(**{'Póliza': 'PV-MAL', 'Clave de Agente': 'NOPE'})
        wizard = self._grabar({'VIDA': (HEADERS_VIDA, [ok, malo])})
        self.assertEqual(wizard.creadas, 1)
        self.assertEqual(wizard.rechazadas, 1)
        self.assertTrue(self.env['bca.poliza'].search([('name', '=', 'PV-OK')]))
        self.assertFalse(self.env['bca.poliza'].search([('name', '=', 'PV-MAL')]))

    def test_persona_con_doble_rol_es_un_solo_contacto(self) -> None:
        """B1: una misma persona como asegurado en una póliza y contratante en
        otra debe ser UN solo res.partner con ambos flags, aunque el nombre
        venga con distinta grafía (acentos/mayúsculas)."""
        fila_x = self._fila_vida(**{
            'Póliza': 'PV-X', 'Nombre del Contratante': 'Carlos Ruiz',
            'R.F.C. Contratante': 'RUIC800101AAA',
            'Nombre del Asegurado': 'Marta Solís',
        })
        fila_y = self._fila_vida(**{
            'Póliza': 'PV-Y', 'Nombre del Contratante': 'MARTA SOLIS',
            'R.F.C. Contratante': '', 'Nombre del Asegurado': 'MARTA SOLIS',
        })
        self._grabar({'VIDA': (HEADERS_VIDA, [fila_x, fila_y])})
        martas = self.env['res.partner'].search([('name', 'ilike', 'Marta')])
        self.assertEqual(len(martas), 1, 'No debe duplicarse por grafía distinta.')
        self.assertTrue(martas.bca_es_contratante)
        self.assertTrue(martas.bca_es_asegurado)

    def test_agente_existente_reutilizado_como_contratante(self) -> None:
        """Un agente (posición de red) que aparece como contratante en el
        portafolio se reutiliza: mismo contacto, conserva bca_tipo='agente' y
        gana el flag de contratante."""
        roberto = self.env['res.partner'].create({
            'name': 'Roberto Agente', 'bca_tipo': 'agente',
            'parent_id': self.promotoria.id,
        })
        fila = self._fila_vida(**{
            'Póliza': 'PV-AG', 'Nombre del Contratante': 'Roberto Agente',
            'R.F.C. Contratante': '', 'Nombre del Asegurado': 'Roberto Agente',
        })
        self._grabar({'VIDA': (HEADERS_VIDA, [fila])})
        robertos = self.env['res.partner'].search([('name', '=', 'Roberto Agente')])
        self.assertEqual(len(robertos), 1, 'No debe crearse un segundo contacto.')
        self.assertEqual(robertos, roberto)
        self.assertEqual(robertos.bca_tipo, 'agente')
        self.assertTrue(robertos.bca_es_contratante)
        pol = self.env['bca.poliza'].search([('name', '=', 'PV-AG')])
        self.assertEqual(pol.contratante_id, roberto)


@tagged('BCA_Seguros')
class TestCargaBeneficiariosHoja(_PortafolioFixtures):
    """B05: hoja BENEFICIARIOS en formato largo (una fila por persona),
    referenciada a la póliza por folio. Puede venir junto a las hojas de
    póliza o sola, para pólizas ya cargadas. Semántica de REEMPLAZO."""

    def _grabar(self, sheets: dict, modo: str = 'crear_actualizar'):
        wizard = self._wizard(_build_xlsx(sheets), modo=modo)
        wizard.action_validar()
        wizard.action_grabar()
        return wizard

    def _benef(self, poliza: str, nombre: str, **ov) -> dict:
        base = {
            'Póliza': poliza, 'Nombre del Beneficiario': nombre,
            'Parentesco': 'Hijo', '% al que tiene Derecho': '',
            'Fecha de Nacimiento': '',
        }
        base.update(ov)
        return base

    def test_beneficiarios_junto_a_poliza_vida(self) -> None:
        wizard = self._grabar({
            'VIDA': (HEADERS_VIDA, [self._fila_vida()]),
            'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
                self._benef('PV-001', 'Hijo Uno', **{'% al que tiene Derecho': '60'}),
                self._benef('PV-001', 'Hija Dos', **{'% al que tiene Derecho': '40'}),
            ]),
        })
        self.assertEqual(wizard.creadas, 1)
        self.assertEqual(wizard.rechazadas, 0)
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        self.assertEqual(len(vida.beneficiario_ids), 2)
        self.assertAlmostEqual(
            sum(vida.beneficiario_ids.mapped('porcentaje')), 100.0, places=2)

    def test_beneficiarios_hoja_sola_para_poliza_existente(self) -> None:
        # 1ª carga: solo la póliza.
        self._grabar({'VIDA': (HEADERS_VIDA, [self._fila_vida()])})
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        self.assertFalse(vida.beneficiario_ids)
        # 2ª carga: solo la hoja de beneficiarios (archivo distinto).
        wizard = self._grabar({'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
            self._benef('PV-001', 'Único', **{'% al que tiene Derecho': '100'}),
        ])})
        self.assertEqual(wizard.rechazadas, 0)
        self.assertEqual(len(vida.beneficiario_ids), 1)
        self.assertEqual(vida.beneficiario_ids.beneficiario_id.name, 'Único')

    def test_beneficiarios_reemplaza_en_recarga(self) -> None:
        self._grabar({'VIDA': (HEADERS_VIDA, [self._fila_vida()])})
        self._grabar({'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
            self._benef('PV-001', 'Viejo Uno', **{'% al que tiene Derecho': '50'}),
            self._benef('PV-001', 'Viejo Dos', **{'% al que tiene Derecho': '50'}),
        ])})
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        self.assertEqual(len(vida.beneficiario_ids), 2)
        # Recarga con un solo beneficiario: reemplaza (no acumula).
        self._grabar({'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
            self._benef('PV-001', 'Nuevo Único', **{'% al que tiene Derecho': '100'}),
        ])})
        self.assertEqual(len(vida.beneficiario_ids), 1)
        self.assertEqual(vida.beneficiario_ids.beneficiario_id.name, 'Nuevo Único')

    def test_beneficiarios_folio_inexistente_rechaza(self) -> None:
        wizard = self._grabar({'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
            self._benef('NO-EXISTE', 'Fulano', **{'% al que tiene Derecho': '100'}),
        ])})
        self.assertEqual(wizard.rechazadas, 1)
        self.assertEqual(wizard.creadas, 0)

    def test_beneficiarios_vida_suma_distinta_100_rechaza(self) -> None:
        self._grabar({'VIDA': (HEADERS_VIDA, [self._fila_vida()])})
        wizard = self._grabar({'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
            self._benef('PV-001', 'Uno', **{'% al que tiene Derecho': '50'}),
            self._benef('PV-001', 'Dos', **{'% al que tiene Derecho': '30'}),
        ])})
        self.assertEqual(wizard.rechazadas, 1)
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        self.assertFalse(vida.beneficiario_ids, 'El grupo inválido no debe grabarse.')

    def test_dependientes_gmm_por_folio_sin_regla_100(self) -> None:
        self._grabar({'GMM': (HEADERS_GMM, [self._fila_gmm()])})
        wizard = self._grabar({'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
            self._benef('PG-001', 'Dependiente Uno', **{
                'Parentesco': 'Cónyuge', 'Fecha de Nacimiento': '15/05/1990'}),
        ])})
        self.assertEqual(wizard.rechazadas, 0)
        gmm = self.env['bca.poliza'].search([('name', '=', 'PG-001')])
        self.assertEqual(len(gmm.beneficiario_ids), 1)
        self.assertEqual(gmm.beneficiario_ids.fecha_nacimiento, date(1990, 5, 15))

    def test_validar_beneficiarios_no_toca_bd(self) -> None:
        self._grabar({'VIDA': (HEADERS_VIDA, [self._fila_vida()])})
        wizard = self._wizard(_build_xlsx({'BENEFICIARIOS': (HEADERS_BENEFICIARIOS, [
            self._benef('PV-001', 'Solo Validar', **{'% al que tiene Derecho': '100'}),
        ])}))
        wizard.action_validar()
        self.assertEqual(wizard.state, 'validado')
        self.assertEqual(wizard.rechazadas, 0)
        vida = self.env['bca.poliza'].search([('name', '=', 'PV-001')])
        self.assertFalse(vida.beneficiario_ids, 'VALIDAR no debe crear beneficiarios.')


@tagged('BCA_Seguros')
class TestPlantillaDescarga(_PortafolioFixtures):
    """Descarga de la plantilla y round-trip: lo que genera el wizard debe
    ser re-validable por el propio wizard sin errores estructurales."""

    def test_descargar_devuelve_act_url_y_adjunto(self) -> None:
        # Sin archivo adjunto: la descarga NO debe exigir el campo 'archivo'
        # (de lo contrario el guardado previo al type='object' fallaría).
        wizard = self.env['bca.wizard.carga.portafolio'].create({
            'aseguradora_id': self.aseguradora.id,
            'modo': 'crear_actualizar',
        })
        self.assertFalse(wizard.archivo)
        accion = wizard.action_descargar_plantilla()
        self.assertEqual(accion['type'], 'ir.actions.act_url')
        self.assertEqual(accion['target'], 'download')
        self.assertIn('/web/content/', accion['url'])

        att_id = int(accion['url'].split('/web/content/')[1].split('?')[0])
        adjunto = self.env['ir.attachment'].browse(att_id)
        self.assertEqual(adjunto.name, 'plantilla_portafolio_BCA.xlsx')
        self.assertEqual(
            adjunto.mimetype,
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        self.assertTrue(adjunto.datas)
        # Atado al transient para que el vacuum lo purgue.
        self.assertEqual(adjunto.res_model, 'bca.wizard.carga.portafolio')
        self.assertEqual(adjunto.res_id, wizard.id)

    def test_round_trip_plantilla_es_validable(self) -> None:
        # La plantilla generada se vuelve a cargar: la estructura (hojas VIDA y
        # GMM, columnas requeridas) debe ser válida y no lanzar.
        origen = self._wizard(_build_xlsx({'VIDA': (HEADERS_VIDA, [self._fila_vida()])}))
        accion = origen.action_descargar_plantilla()
        att_id = int(accion['url'].split('/web/content/')[1].split('?')[0])
        datas = self.env['ir.attachment'].browse(att_id).datas

        wizard = self._wizard(datas)
        wizard.action_validar()
        self.assertEqual(wizard.state, 'validado')
        # 2 filas VIDA + 2 GMM + 5 BENEFICIARIOS + 3 COBERTURAS (formato largo).
        self.assertEqual(wizard.total_filas, 12)


@tagged('BCA_Seguros')
class TestEstatusPagoComputed(_PortafolioFixtures):
    """estatus_pago derivado de pagado_hasta/pagado_hasta_inicial vs hoy."""

    def _poliza_activa(self, **ov):
        vals = {
            'name': 'POL-EST', 'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto_vida.id, 'agente_id': self.agente.id,
            'contratante_id': self.env['res.partner'].create({
                'name': 'C Est'}).id,
            'fecha_inicio': date(2025, 1, 1), 'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'mensual', 'prima_anual': 12000.0,
        }
        vals.update(ov)
        pol = self.env['bca.poliza'].create(vals)
        pol.action_confirmar()
        return pol

    def test_borrador_sin_estatus(self) -> None:
        pol = self.env['bca.poliza'].create({
            'name': 'POL-BORR', 'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto_vida.id, 'agente_id': self.agente.id,
            'contratante_id': self.env['res.partner'].create({
                'name': 'C Borr'}).id,
            'fecha_inicio': date(2025, 1, 1), 'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'anual', 'prima_anual': 1000.0,
        })
        self.assertFalse(pol.estatus_pago)

    def test_al_corriente_por_corte_reciente(self) -> None:
        reciente = fields.Date.today() - timedelta(days=10)
        pol = self._poliza_activa(pagado_hasta_inicial=reciente)
        self.assertEqual(pol.estatus_pago, 'al_corriente')

    def test_vencido_por_corte_viejo(self) -> None:
        viejo = fields.Date.today() - timedelta(days=120)
        pol = self._poliza_activa(pagado_hasta_inicial=viejo)
        self.assertEqual(pol.estatus_pago, 'vencido')

    def test_suspendido_override(self) -> None:
        pol = self._poliza_activa(pagado_hasta_inicial=fields.Date.today())
        pol.pago_suspendido = True
        self.assertEqual(pol.estatus_pago, 'suspendido')


@tagged('BCA_Seguros')
class TestCargaCoberturasHoja(_PortafolioFixtures):
    """Hoja COBERTURAS (formato largo): asigna coberturas adicionales
    estructuradas (PTAV nativas) por póliza mapeando por la DESCRIPCIÓN, con
    reemplazo. Lo no mapeable / no ofrecido por el producto se guarda en notas y
    se omite (no aborta). Folio tolerante a ceros a la izquierda."""

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        from odoo import Command
        cls.attr_adicional = cls.env.ref('BCA_Seguros.attr_cobertura_adicional')
        cls.val_exencion = cls.env.ref(
            'BCA_Seguros.val_ad_exencion_primas_invalidez')
        cls.val_graves = cls.env.ref('BCA_Seguros.val_ad_graves_enfermedades')
        # Producto Vida que OFRECE exención + graves (materializa sus PTAV), pero
        # NO muerte accidental → sirve para probar "mapeada pero no ofrecida".
        cls.producto_cob = cls.env['product.template'].create({
            'name': 'Cobertura Vida Portafolio',
            'bca_es_producto_seguro': True,
            'bca_aseguradora_id': cls.aseguradora.id,
            'bca_ramo': 'vida',
            'attribute_line_ids': [Command.create({
                'attribute_id': cls.attr_adicional.id,
                'value_ids': [Command.set(
                    [cls.val_exencion.id, cls.val_graves.id])],
            })],
        })

    def _grabar(self, sheets: dict, modo: str = 'crear_actualizar'):
        wizard = self._wizard(_build_xlsx(sheets), modo=modo)
        wizard.action_validar()
        wizard.action_grabar()
        return wizard

    def _crear_poliza(self, name: str):
        return self.env['bca.poliza'].create({
            'name': name, 'aseguradora_id': self.aseguradora.id,
            'producto_id': self.producto_cob.id, 'agente_id': self.agente.id,
            'contratante_id': self.env['res.partner'].create(
                {'name': 'C %s' % name}).id,
            'fecha_inicio': date(2025, 1, 1), 'fecha_fin': date(2027, 1, 1),
            'periodicidad': 'anual', 'prima_anual': 1000.0,
        })

    def _cob(self, poliza: str, codigo: str, desc: str) -> dict:
        return {
            'Póliza': poliza, 'Cobertura Adicional': codigo,
            'Descripción Plan Suplementario': desc,
        }

    def _ptav(self, producto, value):
        return self.env['product.template.attribute.value'].search([
            ('product_tmpl_id', '=', producto.id),
            ('product_attribute_value_id', '=', value.id),
            ('attribute_id', '=', self.attr_adicional.id),
            ('ptav_active', '=', True),
        ], limit=1)

    def test_asigna_coberturas_ofrecidas_y_notas(self) -> None:
        pol = self._crear_poliza('COB-001')
        wizard = self._grabar({'COBERTURAS': (HEADERS_COBERTURAS, [
            self._cob('COB-001', 'NVUAEP', 'EXENCION DE PAGO DE PRIMAS INV.'),
            self._cob('COB-001', 'NVUAGE', 'GRAVES ENFERMEDADES'),
            # Mapeada pero NO ofrecida por el producto → sólo nota.
            self._cob('COB-001', 'NVUAIM', 'INDEMNIZACION MUERTE ACCIDENTAL'),
        ])})
        ptav_ex = self._ptav(self.producto_cob, self.val_exencion)
        ptav_gr = self._ptav(self.producto_cob, self.val_graves)
        self.assertEqual(pol.cobertura_adicional_ids, ptav_ex | ptav_gr)
        # Todas las filas quedan en notas, la no asignada marcada.
        self.assertIn('EXENCION', pol.coberturas_adicionales)
        self.assertIn('INDEMNIZACION MUERTE ACCIDENTAL', pol.coberturas_adicionales)
        self.assertIn('no ofrecida', pol.coberturas_adicionales)

    def test_descripcion_sin_catalogo_solo_notas(self) -> None:
        pol = self._crear_poliza('COB-002')
        self._grabar({'COBERTURAS': (HEADERS_COBERTURAS, [
            self._cob('COB-002', 'NCAM4U', 'CANCER'),
        ])})
        self.assertFalse(pol.cobertura_adicional_ids)
        self.assertIn('sin catálogo', pol.coberturas_adicionales)
        self.assertIn('CANCER', pol.coberturas_adicionales)

    def test_folio_tolera_ceros_a_la_izquierda(self) -> None:
        pol = self._crear_poliza('8312115')  # guardada sin padding
        self._grabar({'COBERTURAS': (HEADERS_COBERTURAS, [
            self._cob('0008312115', 'NVUAEP', 'EXENCION DE PAGO DE PRIMAS INV.'),
        ])})
        self.assertEqual(
            pol.cobertura_adicional_ids, self._ptav(self.producto_cob, self.val_exencion))

    def test_reemplaza_en_recarga(self) -> None:
        pol = self._crear_poliza('COB-003')
        self._grabar({'COBERTURAS': (HEADERS_COBERTURAS, [
            self._cob('COB-003', 'NVUAEP', 'EXENCION DE PAGO DE PRIMAS INV.'),
            self._cob('COB-003', 'NVUAGE', 'GRAVES ENFERMEDADES'),
        ])})
        self.assertEqual(len(pol.cobertura_adicional_ids), 2)
        # Recarga con una sola cobertura → reemplaza (no acumula).
        self._grabar({'COBERTURAS': (HEADERS_COBERTURAS, [
            self._cob('COB-003', 'NVUAGE', 'GRAVES ENFERMEDADES'),
        ])})
        self.assertEqual(
            pol.cobertura_adicional_ids, self._ptav(self.producto_cob, self.val_graves))

    def test_poliza_inexistente_se_omite(self) -> None:
        wizard = self._grabar({'COBERTURAS': (HEADERS_COBERTURAS, [
            self._cob('NO-EXISTE', 'NVUAEP', 'EXENCION DE PAGO DE PRIMAS INV.'),
        ])})
        self.assertEqual(wizard.rechazadas, 1)  # omitida (reportada), no aborta
        self.assertEqual(wizard.creadas, 0)

    def test_coberturas_junto_a_poliza_vida_misma_corrida(self) -> None:
        # La póliza se crea en la hoja VIDA y sus coberturas se asignan en la
        # misma corrida (COBERTURAS se procesa después de las pólizas).
        fila = self._fila_vida(**{
            'Póliza': 'COB-004', 'Producto': 'Cobertura Vida Portafolio'})
        self._grabar({
            'VIDA': (HEADERS_VIDA, [fila]),
            'COBERTURAS': (HEADERS_COBERTURAS, [
                self._cob('COB-004', 'NVUAEP', 'EXENCION DE PAGO DE PRIMAS INV.'),
            ]),
        })
        pol = self.env['bca.poliza'].search([('name', '=', 'COB-004')])
        self.assertEqual(
            pol.cobertura_adicional_ids, self._ptav(self.producto_cob, self.val_exencion))

    def test_validar_no_toca_bd(self) -> None:
        pol = self._crear_poliza('COB-005')
        wizard = self._wizard(_build_xlsx({'COBERTURAS': (HEADERS_COBERTURAS, [
            self._cob('COB-005', 'NVUAEP', 'EXENCION DE PAGO DE PRIMAS INV.'),
        ])}))
        wizard.action_validar()
        self.assertEqual(wizard.state, 'validado')
        self.assertFalse(
            pol.cobertura_adicional_ids, 'VALIDAR no debe asignar coberturas.')
