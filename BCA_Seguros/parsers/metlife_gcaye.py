from __future__ import annotations

from .base import ParserBase

# TODO Etapa 8: confirmar nombres exactos de columnas contra un CSV real
# de MetLife (archivo GCAYE — ramo GMM). Tentativos según specs §5.3
# y §4.2. Pueden requerir ajuste por acentos, mayúsculas o espacios.
COLUMNAS_GCAYE = [
    'numero_poliza', 'estatus_pago', 'agente', 'contratante',
    'fecha_aplicacion', 'vigencia_desde', 'vigencia_hasta', 'conducto',
    'prima_neta', 'recargo', 'gastos_expedicion', 'impuestos',
    'prima_total', 'folio_endoso',
]

ESTATUS_ANULADOS = {'anulado', 'cancelado'}


class ParserMetLifeGMM(ParserBase):
    """Parser del archivo GCAYE de MetLife (ramo GMM).

    Reglas aplicadas: R-COB-01 (anulaciones omitidas en ``filtrar_filas``),
    R-COB-02/04/06/08 (idénticas a Vida), más propagación de ``folio_endoso``
    al recibo (campo GMM-only).
    """

    aseguradora_codigo = 'METLIFE'
    ramo = 'gmm'
    columnas_requeridas = COLUMNAS_GCAYE

    def filtrar_filas(self, filas: list[dict]) -> list[dict]:
        """R-COB-01: omite filas con estatus 'anulado'/'cancelado'.

        Side-effect intencional: crea la línea de bitácora ``marca='anulado'``
        y suma al contador ``anulaciones_ignoradas`` directamente. El parser
        es dueño de esta regla; el wizard (E8) no necesita conocerla.
        """
        BitacoraLinea = self.env['bca.bitacora.linea'].sudo()
        filtradas: list[dict] = []
        anulaciones = 0
        for idx, fila in enumerate(filas):
            estatus = str(fila.get('estatus_pago') or '').strip().lower()
            if estatus in ESTATUS_ANULADOS:
                raw = (fila.get('numero_poliza') or '').strip()
                BitacoraLinea.create({
                    'bitacora_id': self.bitacora.id,
                    'numero_fila': idx + 1,
                    'marca': 'anulado',
                    'mensaje': "Estatus '%s' — fila omitida (R-COB-01)" % estatus,
                    'numero_poliza_raw': raw,
                })
                anulaciones += 1
            else:
                filtradas.append(fila)
        if anulaciones:
            self.bitacora.sudo().write({
                'anulaciones_ignoradas':
                    self.bitacora.anulaciones_ignoradas + anulaciones,
            })
        return filtradas

    def _procesar_fila_interna(self, env, fila: dict, numero_fila: int,
                               raw: str) -> dict:
        poliza = self._buscar_poliza(env, raw)
        if not poliza:
            return {
                'marca': 'no_encontrada',
                'recibo_id': False,
                'mensaje': "Póliza no existe en el sistema",
                'numero_poliza_raw': raw,
            }
        recibo = self._primer_recibo_pendiente(poliza)
        if not recibo:
            return {
                'marca': 'sin_recibo',
                'recibo_id': False,
                'mensaje': "Sin recibos pendientes",
                'numero_poliza_raw': raw,
            }
        fecha_pago = self.normalizar_fecha(fila.get('fecha_aplicacion'))
        prima_neta = self.normalizar_monto(fila.get('prima_neta'))
        recargo = self.normalizar_monto(fila.get('recargo'))
        prima_total = self.normalizar_monto(fila.get('prima_total'))
        folio_endoso = str(fila.get('folio_endoso') or '').strip() or False
        conducto_id, advertencia = self._resolver_conducto(env, fila.get('conducto'))
        vals = {
            'fecha_pago': fecha_pago,
            'prima_neta': prima_neta,
            'prima_total': prima_total or prima_neta,
            'recargo': recargo,
            'conducto_id': conducto_id,
            'folio_endoso': folio_endoso,
        }
        with env.cr.savepoint():
            recibo.action_registrar_pago(vals)
        mensaje = "Recibo %s pagado por %s" % (recibo.name, prima_neta)
        if advertencia:
            return {
                'marca': 'advertencia',
                'recibo_id': recibo.id,
                'mensaje': "%s | %s" % (mensaje, advertencia),
                'numero_poliza_raw': raw,
            }
        return {
            'marca': 'aplicado',
            'recibo_id': recibo.id,
            'mensaje': mensaje,
            'numero_poliza_raw': raw,
        }
