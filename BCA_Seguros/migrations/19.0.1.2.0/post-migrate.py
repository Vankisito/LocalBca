# Migración E7: campo pca_currency_id en bca.recibo.
# La PCA pasa a expresarse SIEMPRE en MXN (decisión D-08). El campo nuevo
# pca_currency_id queda nulo en los recibos existentes (hoy todos con PCA 0,
# porque el calculador era un stub); lo poblamos con MXN para dejar el monto
# de pca_aplicada inequívoco y consistente.
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:          # instalación fresca: nada que migrar
        return

    cr.execute("""
        UPDATE bca_recibo r
           SET pca_currency_id = c.id
          FROM res_currency c
         WHERE c.name = 'MXN'
           AND r.pca_currency_id IS NULL
    """)
    _logger.info("BCA E7: pca_currency_id=MXN seteado en %s recibo(s)", cr.rowcount)
