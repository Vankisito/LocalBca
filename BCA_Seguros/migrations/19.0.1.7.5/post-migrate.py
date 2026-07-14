# Migración: depuración de pestañas Perfil/Origen del postulante (D-19).
# Se eliminaron 7 campos redundantes de hr.applicant (origen → UTM nativo;
# académico → type_id nativo; seguimiento → embudo + actividades; cédula
# previa → se infiere de la pestaña Habilitación). Odoo quita la definición
# del campo pero NO borra la columna: la eliminamos aquí para no dejar
# columnas huérfanas.
import logging

_logger = logging.getLogger(__name__)

COLUMNAS_OBSOLETAS = [
    'bca_referido_por',
    'bca_evento',
    'bca_contactado',
    'bca_entrevistado',
    'bca_reagendaciones',
    'bca_perfil_academico',
    'bca_tiene_cedula_previa',
]


def migrate(cr, version):
    if not version:          # instalación fresca: no hay columnas que limpiar
        return
    for columna in COLUMNAS_OBSOLETAS:
        cr.execute(
            "ALTER TABLE hr_applicant DROP COLUMN IF EXISTS %s" % columna
        )
    _logger.info(
        "BCA D-19: %s columna(s) obsoleta(s) eliminada(s) de hr_applicant",
        len(COLUMNAS_OBSOLETAS),
    )
