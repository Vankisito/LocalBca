"""D-20: alinea el embudo comercial con las figuras comerciales (agente + promotoría).

En BDs ya instaladas, `data/hr_recruitment_stages.xml` lleva `noupdate="1"`, así que un
simple `-u` **no** reaplica los cambios del XML a los registros existentes. Por eso esta
migración empuja los dos cambios a mano:

1) Añade `job_captacion_promotoria` al `job_ids` de las 12 etapas comerciales (antes solo
   estaba `job_reclutamiento_agente`), de modo que las promotorías compartan el embudo.
2) Retira la etapa BCA "Contratado (Alta Interna)": los puestos internos pasan al embudo
   nativo de Odoo. Reasigna cualquier candidato en esa etapa a una etapa hired de
   reemplazo (preferentemente nativa) antes de borrarla.

Nota: en instalación limpia (`-i`) el XML crea las etapas ya con ambos jobs (noupdate solo
bloquea updates, no la creación inicial), por lo que esta migración solo afecta al upgrade.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# XML ids de las 12 etapas del embudo comercial (Fase A + Fase B).
_STAGE_XMLIDS = [
    'stage_recibido', 'stage_prospeccion', 'stage_cafe', 'stage_entrevista',
    'stage_evaluacion_pda', 'stage_acuerdo_arranque', 'stage_clave_arranque',
    'stage_inscripcion_cia', 'stage_curso_cedula', 'stage_examen',
    'stage_cedula_emitida', 'stage_en_desarrollo',
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) Añadir la promotoría al job_ids de las 12 etapas comerciales.
    job_promotoria = env.ref(
        'BCA_Seguros.job_captacion_promotoria', raise_if_not_found=False,
    )
    if job_promotoria:
        actualizadas = 0
        for xmlid in _STAGE_XMLIDS:
            stage = env.ref(f'BCA_Seguros.{xmlid}', raise_if_not_found=False)
            if stage and job_promotoria not in stage.job_ids:
                stage.job_ids = [(4, job_promotoria.id)]
                actualizadas += 1
        if actualizadas:
            _logger.info(
                'D-20: promotoría añadida al job_ids de %s etapas comerciales.',
                actualizadas,
            )

    # 2) Retirar la etapa "Contratado (Alta Interna)" (SQL: evita disparar la
    #    lógica de conversión del override write() de hr.applicant).
    cr.execute(
        """
        SELECT res_id FROM ir_model_data
        WHERE module = 'BCA_Seguros' AND name = 'stage_alta_interna'
        """
    )
    row = cr.fetchone()
    if not row:
        return
    stage_id = row[0]

    # Etapa hired de reemplazo distinta de la que se retira; se prefiere una NATIVA
    # (no perteneciente a BCA_Seguros) para que los internos queden en el cierre nativo.
    cr.execute(
        """
        SELECT s.id
        FROM hr_recruitment_stage s
        WHERE s.hired_stage = true AND s.id != %s
        ORDER BY
            (s.id IN (
                SELECT d.res_id FROM ir_model_data d
                WHERE d.model = 'hr.recruitment.stage'
                  AND d.module = 'BCA_Seguros'
            )) ASC,          -- nativas primero (False < True)
            s.sequence ASC, s.id ASC
        LIMIT 1
        """,
        (stage_id,),
    )
    fb = cr.fetchone()
    fallback_id = fb[0] if fb else None

    if fallback_id:
        cr.execute(
            "UPDATE hr_applicant SET stage_id = %s WHERE stage_id = %s",
            (fallback_id, stage_id),
        )

    cr.execute(
        "SELECT COUNT(*) FROM hr_applicant WHERE stage_id = %s", (stage_id,)
    )
    if cr.fetchone()[0] != 0:
        _logger.warning(
            "No se pudo retirar stage_alta_interna (id=%s): aún hay candidatos "
            "en ella y no se halló etapa hired de reemplazo.", stage_id,
        )
        return

    cr.execute("DELETE FROM hr_recruitment_stage WHERE id = %s", (stage_id,))
    cr.execute(
        """
        DELETE FROM ir_model_data
        WHERE module = 'BCA_Seguros' AND name = 'stage_alta_interna'
        """
    )
    _logger.info(
        "D-20: etapa 'Contratado (Alta Interna)' (id=%s) retirada; "
        "candidatos reasignados a la etapa hired %s.", stage_id, fallback_id,
    )
