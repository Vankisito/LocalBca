"""D-21: correcciones Etapa 12 sobre BDs ya instaladas.

`data/hr_recruitment_stages.xml` y `data/hr_jobs.xml` llevan `noupdate="1"`, así que
un `-u` NO reaplica los renombres a los registros existentes. Esta migración los
empuja a mano y limpia la columna del campo retirado:

1) Renombra la etapa "Entrevista" → "Cena".
2) Renombra los puestos: "Captación de Promotoría" → "Promotores";
   "Reclutamiento de Agente" → "Agentes".
3) Elimina la columna `bca_tipo_candidato` de hr_applicant (campo retirado, duplicaba
   el origen nativo; patrón D-19 de DROP COLUMN).

En instalación limpia (`-i`) el XML ya crea los nombres correctos y el modelo ya no
declara `bca_tipo_candidato`, por lo que esta migración solo aplica en upgrade.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    if not version:
        return
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) Renombrar la etapa "Entrevista" → "Cena".
    stage_cena = env.ref('BCA_Seguros.stage_entrevista', raise_if_not_found=False)
    if stage_cena and stage_cena.name != 'Cena':
        stage_cena.name = 'Cena'
        _logger.info("D-21: etapa 'Entrevista' renombrada a 'Cena'.")

    # 2) Renombrar los puestos comerciales.
    renombres_job = {
        'BCA_Seguros.job_captacion_promotoria': 'Promotores',
        'BCA_Seguros.job_reclutamiento_agente': 'Agentes',
    }
    for xmlid, nuevo_nombre in renombres_job.items():
        job = env.ref(xmlid, raise_if_not_found=False)
        if job and job.name != nuevo_nombre:
            job.name = nuevo_nombre
            _logger.info("D-21: puesto %s renombrado a '%s'.", xmlid, nuevo_nombre)

    # 3) Eliminar la columna del campo retirado bca_tipo_candidato (D-19).
    cr.execute(
        "ALTER TABLE hr_applicant DROP COLUMN IF EXISTS bca_tipo_candidato"
    )
    _logger.info("D-21: columna hr_applicant.bca_tipo_candidato eliminada (si existía).")
