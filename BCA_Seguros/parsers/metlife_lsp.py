from __future__ import annotations

from .base import ParserBase

# TODO Etapa 8: confirmar nombres exactos de columnas contra un CSV real
# de MetLife (archivo LSP — ramo Vida). Los nombres aquí son tentativos
# según specs §5.3 (Lógica de Negocios) y §4.2 (Arquitectura). Pueden
# requerir ajuste por acentos, mayúsculas o espacios del CSV real.
COLUMNAS_LSP = [
    'numero_poliza', 'producto', 'agente', 'contratante', 'moneda',
    'fecha_aplicacion', 'vigencia_desde', 'vigencia_hasta', 'conducto',
    'prima_modal', 'recargo', 'prima_total', 'comision_informativa',
]


class ParserMetLifeVida(ParserBase):
    """Parser del archivo LSP de MetLife (ramo Vida).

    Reglas aplicadas: R-COB-02 (póliza no encontrada), R-COB-03 (FIFO,
    delegado a ``action_registrar_pago``), R-COB-04 (sin recibo pendiente),
    R-COB-06 (conducto sin match → advertencia, no aborta), R-COB-08
    (tolerancia por fila vía wrapper de base), R-GLOB-01 (encoding Latin-1
    gestionado por el wizard E8 antes de invocar este parser).
    """

    aseguradora_codigo = 'METLIFE'
    ramo = 'vida'
    columnas_requeridas = COLUMNAS_LSP

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
        prima_neta = self.normalizar_monto(fila.get('prima_modal'))
        recargo = self.normalizar_monto(fila.get('recargo'))
        prima_total = self.normalizar_monto(fila.get('prima_total'))
        conducto_id, advertencia = self._resolver_conducto(env, fila.get('conducto'))
        vals = {
            'fecha_pago': fecha_pago,
            'prima_neta': prima_neta,
            'prima_total': prima_total or prima_neta,
            'recargo': recargo,
            'conducto_id': conducto_id,
            'folio_endoso': False,
        }
        # R-COB-08: rollback aislado por fila. La excepción se propaga al
        # wrapper procesar_fila que la convierte en marca='error'.
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
