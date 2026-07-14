from __future__ import annotations

from datetime import date, timedelta

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

# PCA esperada: 17 factores en la tabla 2026 (data/factores_metlife_2026.xml).
FACTORES_ESPERADOS = 17

# Mapa de claves de navegación → (modelo, nombre de la vista). El dominio se
# resuelve dinámicamente en _domain_navegacion() porque depende de "hoy".
_NAV_MODELOS = {
    'cartera_activas': ('bca.poliza', 'Pólizas activas'),
    'cartera_borrador': ('bca.poliza', 'Pólizas en borrador'),
    'cartera_vencidas': ('bca.poliza', 'Pólizas vencidas'),
    'cobranza_pendientes': ('bca.recibo', 'Recibos pendientes'),
    'cobranza_vencidos': ('bca.recibo', 'Recibos vencidos'),
    'cobranza_cobrado_mes': ('bca.recibo', 'Recibos cobrados del mes'),
    'pca_computables': ('bca.recibo', 'Recibos computables (PCA)'),
    'pca_exclusiones': ('bca.recibo', 'Recibos excluidos de PCA'),
    'vigencia_al_dia': ('bca.poliza', 'Pólizas al día'),
    'vigencia_por_caer': ('bca.poliza', 'Pólizas por caer'),
    'vigencia_sin_cobertura': ('bca.poliza', 'Pólizas sin cobertura'),
    'importaciones': ('bca.bitacora.importacion', 'Bitácoras de importación'),
    'agentes_con_licencia': ('res.partner', 'Agentes con clave definitiva'),
    'agentes_prospectos': ('res.partner', 'Agentes prospecto'),
}


class BcaDashboard(models.AbstractModel):
    """Agregador de solo lectura del Tablero de Inicio.

    Regla de oro (spec §3): SOLO lee y agrega. Nunca escribe en ningún modelo;
    jamás toca pagado_hasta, pca_aplicada ni factor_aplicado. Toda cifra sale
    de search_count / _read_group, que respetan las record rules existentes
    (un agente solo ve agregados de lo suyo). El front (OWL) solo dibuja lo que
    get_dashboard_data() ya resolvió.
    """

    _name = 'bca.dashboard'
    _description = 'Agregador de datos del Tablero BCA Seguros'

    # ------------------------------------------------------------------ helpers
    def _sum(self, model: str, domain: list, campo: str) -> float:
        """Suma `campo` sobre `domain` vía _read_group (v19; read_group está
        deprecado). Devuelve 0.0 si no hay registros."""
        grupos = self.env[model]._read_group(domain, [], [f'{campo}:sum'])
        return grupos[0][0] or 0.0 if grupos else 0.0

    def _hoy(self) -> date:
        return fields.Date.context_today(self)

    # -------------------------------------------------------------- contrato §6
    @api.model
    def get_dashboard_data(self) -> dict:
        """Devuelve TODAS las cifras del tablero ya calculadas (contrato spec §6).
        Las claves son estables: el componente OWL depende de ellas."""
        hoy = self._hoy()
        inicio_mes = hoy.replace(day=1)
        fin_mes = inicio_mes + relativedelta(months=1) - timedelta(days=1)
        inicio_anio = hoy.replace(month=1, day=1)

        Poliza = self.env['bca.poliza']
        Recibo = self.env['bca.recibo']

        return {
            'moneda': 'MXN',
            'cartera': self._datos_cartera(Poliza),
            'cobranza': self._datos_cobranza(Recibo, hoy, inicio_mes, fin_mes),
            'pca': self._datos_pca(Recibo, inicio_mes, inicio_anio, hoy),
            'vigencia': self._datos_vigencia(Poliza, hoy),
            'importaciones': self._datos_importaciones(),
            'agentes': self._datos_agentes(Recibo),
        }

    # ----------------------------------------------------- Tarjeta 1: Cartera
    def _datos_cartera(self, Poliza) -> dict:
        por_ramo = {'vida': 0, 'gmm': 0, 'autos': 0}
        for ramo, count in Poliza._read_group(
            [('estado', '=', 'activa')], ['ramo'], ['__count']
        ):
            if ramo in por_ramo:
                por_ramo[ramo] = count
        return {
            'activas': Poliza.search_count([('estado', '=', 'activa')]),
            'suma_asegurada': self._sum(
                'bca.poliza', [('estado', '=', 'activa')], 'suma_asegurada'),
            'borrador': Poliza.search_count([('estado', '=', 'borrador')]),
            'vencidas': Poliza.search_count([('estado', '=', 'vencida')]),
            'por_ramo': por_ramo,
        }

    # ---------------------------------------------------- Tarjeta 2: Cobranza
    def _datos_cobranza(self, Recibo, hoy, inicio_mes, fin_mes) -> dict:
        dom_pend = [('estado', '=', 'pendiente')]
        dom_venc = [('estado', '=', 'pendiente'), ('fecha_hasta', '<', hoy)]
        proximo = Recibo.search(dom_pend, order='fecha_desde asc', limit=1)
        return {
            'pendientes_num': Recibo.search_count(dom_pend),
            'pendientes_monto': self._sum('bca.recibo', dom_pend, 'prima_total'),
            'vencidos_num': Recibo.search_count(dom_venc),
            'vencidos_monto': self._sum('bca.recibo', dom_venc, 'prima_total'),
            'cobrado_mes': self._sum('bca.recibo', [
                ('estado', '=', 'pagado'),
                ('fecha_pago', '>=', inicio_mes),
                ('fecha_pago', '<=', fin_mes),
            ], 'prima_total'),
            'proximo_fifo': {
                'poliza': proximo.poliza_id.name or '',
                'fecha_fin': fields.Date.to_string(proximo.fecha_hasta) or '',
            },
            'tendencia_semanal': self._tendencia_semanal(hoy),
        }

    def _tendencia_semanal(self, hoy: date) -> list:
        """Suma de prima_total de recibos pagados por semana (lunes-domingo),
        últimas 6 semanas, de la más antigua a la actual."""
        lunes_actual = hoy - timedelta(days=hoy.weekday())
        serie = []
        for i in range(5, -1, -1):
            ini = lunes_actual - timedelta(weeks=i)
            fin = ini + timedelta(days=6)
            serie.append(self._sum('bca.recibo', [
                ('estado', '=', 'pagado'),
                ('fecha_pago', '>=', ini),
                ('fecha_pago', '<=', fin),
            ], 'prima_total'))
        return serie

    # -------------------------------------------------------- Tarjeta 3: PCA
    def _datos_pca(self, Recibo, inicio_mes, inicio_anio, hoy) -> dict:
        return {
            'acumulada_anio': self._sum('bca.recibo', [
                ('estado', '=', 'pagado'), ('fecha_pago', '>=', inicio_anio),
            ], 'pca_aplicada'),
            'del_mes': self._sum('bca.recibo', [
                ('estado', '=', 'pagado'), ('fecha_pago', '>=', inicio_mes),
            ], 'pca_aplicada'),
            'computables': Recibo.search_count([
                ('estado', '=', 'pagado'), ('factor_aplicado', '>', 0)]),
            'exclusiones': Recibo.search_count([
                ('estado', '=', 'pagado'), ('factor_aplicado', '=', 0)]),
            'factores_cargados': self.env['bca.factor.pca'].search_count([]),
            'factores_esperados': FACTORES_ESPERADOS,
            'tendencia_mensual': self._tendencia_mensual(hoy),
        }

    def _tendencia_mensual(self, hoy: date) -> list:
        """Suma de pca_aplicada de recibos pagados por mes del año en curso
        (enero→diciembre)."""
        serie = []
        for mes in range(1, 13):
            ini = date(hoy.year, mes, 1)
            fin = ini + relativedelta(months=1) - timedelta(days=1)
            serie.append(self._sum('bca.recibo', [
                ('estado', '=', 'pagado'),
                ('fecha_pago', '>=', ini),
                ('fecha_pago', '<=', fin),
            ], 'pca_aplicada'))
        return serie

    # --------------------------------------------------- Tarjeta 4: Vigencia
    def _datos_vigencia(self, Poliza, hoy) -> dict:
        base = [('estado', '=', 'activa')]
        return {
            'al_dia': Poliza.search_count(base + [('pagado_hasta', '>=', hoy)]),
            'por_caer': Poliza.search_count(base + [
                ('pagado_hasta', '>=', hoy),
                ('pagado_hasta', '<=', hoy + timedelta(days=15)),
            ]),
            'sin_cobertura': Poliza.search_count(base + [
                '|', ('pagado_hasta', '=', False), ('pagado_hasta', '<', hoy),
            ]),
        }

    # ----------------------------------------------- Tarjeta 5: Importaciones
    def _datos_importaciones(self) -> dict:
        ultima = self.env['bca.bitacora.importacion'].search(
            [], order='fecha_ejecucion desc', limit=1)
        return {
            'ultima_fecha': fields.Datetime.to_string(ultima.fecha_ejecucion) or '',
            'ultimo_archivo': ultima.nombre_archivo or '',
            'aplicadas': ultima.recibos_aplicados,
            'no_encontradas': ultima.polizas_no_encontradas,
            'anuladas': ultima.anulaciones_ignoradas,
            # La spec preveía "sin_recibo"; la bitácora real no tiene ese
            # contador de cabecera → se reporta "errores" (errores_procesamiento).
            'errores': ultima.errores_procesamiento,
        }

    # -------------------------------------------------- Tarjeta 6: Agentes
    def _datos_agentes(self, Recibo) -> dict:
        Partner = self.env['res.partner']
        # promotoria_id es la foto inmutable almacenada en el recibo (la misma
        # que usan los reportes PCA de E9): _read_group directo, sin saltos.
        pca_por_promotoria = []
        for promotoria, pca in Recibo._read_group(
            [('estado', '=', 'pagado')], ['promotoria_id'], ['pca_aplicada:sum']
        ):
            if promotoria:
                pca_por_promotoria.append({
                    'promotoria': promotoria.display_name,
                    'pca': pca or 0.0,
                })
        return {
            'con_licencia': Partner.search_count([
                ('bca_tipo', '=', 'agente'),
                ('bca_estado_agente', '=', 'clave_definitiva'),
            ]),
            'prospectos': Partner.search_count([
                ('bca_tipo', '=', 'agente'),
                ('bca_estado_agente', '=', 'prospecto'),
            ]),
            'pca_por_promotoria': pca_por_promotoria,
        }

    # ------------------------------------------------------------ navegación
    def _domain_navegacion(self, key: str) -> list:
        """Dominio filtrado por clave de tarjeta. Centraliza la lógica de
        negocio de navegación en backend (el front solo pasa la clave)."""
        hoy = self._hoy()
        inicio_mes = hoy.replace(day=1)
        activa = [('estado', '=', 'activa')]
        dominios = {
            'cartera_activas': activa,
            'cartera_borrador': [('estado', '=', 'borrador')],
            'cartera_vencidas': [('estado', '=', 'vencida')],
            'cobranza_pendientes': [('estado', '=', 'pendiente')],
            'cobranza_vencidos': [
                ('estado', '=', 'pendiente'), ('fecha_hasta', '<', hoy)],
            'cobranza_cobrado_mes': [
                ('estado', '=', 'pagado'), ('fecha_pago', '>=', inicio_mes)],
            'pca_computables': [
                ('estado', '=', 'pagado'), ('factor_aplicado', '>', 0)],
            'pca_exclusiones': [
                ('estado', '=', 'pagado'), ('factor_aplicado', '=', 0)],
            'vigencia_al_dia': activa + [('pagado_hasta', '>=', hoy)],
            'vigencia_por_caer': activa + [
                ('pagado_hasta', '>=', hoy),
                ('pagado_hasta', '<=', hoy + timedelta(days=15)),
            ],
            'vigencia_sin_cobertura': activa + [
                '|', ('pagado_hasta', '=', False), ('pagado_hasta', '<', hoy)],
            'importaciones': [],
            'agentes_con_licencia': [
                ('bca_tipo', '=', 'agente'),
                ('bca_estado_agente', '=', 'clave_definitiva'),
            ],
            'agentes_prospectos': [
                ('bca_tipo', '=', 'agente'),
                ('bca_estado_agente', '=', 'prospecto'),
            ],
        }
        return dominios.get(key, [])

    @api.model
    def action_open(self, key: str) -> dict:
        """Devuelve un act_window con el dominio ya filtrado para la cifra
        clickeada. Cumple DEC-026: navegación por método Python que retorna el
        action dict, sin type="action" + active_id en contexto."""
        if key not in _NAV_MODELOS:
            raise ValueError(_('Clave de navegación desconocida: %s') % key)
        model, nombre = _NAV_MODELOS[key]
        return {
            'type': 'ir.actions.act_window',
            'name': nombre,
            'res_model': model,
            'view_mode': 'list,form',
            'views': [(False, 'list'), (False, 'form')],
            'domain': self._domain_navegacion(key),
            'target': 'current',
        }
