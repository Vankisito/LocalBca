"""D-24: Puesto Interno adopta Recibido…Cena del embudo BCA; se borran las 4
etapas nativas intermedias que contaminaban los 3 kanbans (BUG-020/BUG-021).

En BDs ya instaladas, `data/hr_recruitment_stages.xml` lleva `noupdate="1"`, así
que un `-u` no reaplica el cambio de `job_ids` a los registros existentes. Esta
migración empuja los cambios a mano (PRE-migration, mismo patrón que
`migrations/19.0.1.7.7` para retirar una etapa: corre antes de que el ORM
recargue los datos del módulo, con SQL directo para evitar disparar
`_bca_procesar_transicion_etapa` del override `write()` de hr.applicant):

1) Añade `job_interno` al `job_ids` de las 4 etapas Recibido…Cena (seq 1-4).
   Si una migración previa (19.0.1.8.3 intermedia, nunca liberada) llegó a
   añadir `job_interno` a "Evaluación PDA"/"Acuerdo de Arranque", lo retira
   (esas fases no aplican a Puesto Interno).
2) Identifica las 4 etapas nativas intermedias de `hr_recruitment` ("Nuevo"/
   "New", "Calificación"/"Qualified", "Primera Entrevista"/"First Interview",
   "Segunda Entrevista"/"Second Interview") por: NO pertenecer a las 13 etapas
   de `BCA_Seguros`, `hired_stage=False` y nombre en una lista candidata ES/EN
   (nunca por xmlid hardcodeado de `hr_recruitment`, no confirmado en este
   entorno). Reasigna cualquier `hr.applicant` en ellas (de cualquier job) a
   `stage_recibido`, y las **borra** — el cliente prefirió borrar antes que
   mantener un puesto placeholder técnico como ancla de scope.

Idempotente: si se corre dos veces, el paso 1 solo actualiza `job_ids` si hace
falta, y el paso 2 no encuentra las etapas ya borradas.
"""

import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)

# Las 4 etapas Recibido…Cena que sí comparte Puesto Interno (D-24).
_STAGES_PUESTO_INTERNO_XMLIDS = [
    'stage_recibido', 'stage_prospeccion', 'stage_cafe', 'stage_entrevista',
]

# Etapas exclusivas de las figuras comerciales de las que se retira job_interno
# por si una migración previa lo hubiera añadido por error.
_STAGES_EXCLUIR_INTERNO_XMLIDS = [
    'stage_evaluacion_pda', 'stage_acuerdo_arranque',
]

# Las 13 etapas BCA (Fase A + Fase B), para excluirlas explícitamente de la
# búsqueda de etapas nativas (defensa extra; sus nombres ya no coinciden).
_STAGE_XMLIDS_BCA = _STAGES_PUESTO_INTERNO_XMLIDS + _STAGES_EXCLUIR_INTERNO_XMLIDS + [
    'stage_clave_arranque', 'stage_inscripcion_cia', 'stage_curso_cedula',
    'stage_examen', 'stage_cedula_emitida', 'stage_en_desarrollo',
    'stage_clave_definitiva',
]

# Nombres candidatos ES/EN de las 4 etapas nativas intermedias de hr_recruitment.
_ETAPAS_NATIVAS_CANDIDATAS = [
    'Nuevo', 'New',
    'Calificación', 'Calificacion', 'Qualified', 'Qualification',
    'Primera Entrevista', 'First Interview',
    'Segunda Entrevista', 'Second Interview',
]


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # 1) job_interno → job_ids de Recibido…Cena; retirarlo de PDA/Acuerdo si
    #    una migración previa (no liberada) lo hubiera añadido por error.
    job_interno = env.ref('BCA_Seguros.job_interno', raise_if_not_found=False)
    if job_interno:
        actualizadas = 0
        for xmlid in _STAGES_PUESTO_INTERNO_XMLIDS:
            stage = env.ref(f'BCA_Seguros.{xmlid}', raise_if_not_found=False)
            if stage and job_interno not in stage.job_ids:
                stage.job_ids = [(4, job_interno.id)]
                actualizadas += 1
        for xmlid in _STAGES_EXCLUIR_INTERNO_XMLIDS:
            stage = env.ref(f'BCA_Seguros.{xmlid}', raise_if_not_found=False)
            if stage and job_interno in stage.job_ids:
                stage.job_ids = [(3, job_interno.id)]
                _logger.info(
                    'D-24: job_interno retirado de %s (no aplica a Puesto Interno).',
                    xmlid,
                )
        if actualizadas:
            _logger.info(
                'D-24: job_interno añadido al job_ids de %s etapa(s) '
                '(Recibido…Cena).', actualizadas,
            )

    # 2) Identificar y borrar las 4 etapas nativas intermedias.
    stages_bca = env['hr.recruitment.stage'].browse([
        s.id for s in (
            env.ref(f'BCA_Seguros.{xmlid}', raise_if_not_found=False)
            for xmlid in _STAGE_XMLIDS_BCA
        ) if s
    ])
    candidatas = env['hr.recruitment.stage'].search([
        ('hired_stage', '=', False),
        ('name', 'in', _ETAPAS_NATIVAS_CANDIDATAS),
    ]) - stages_bca

    if not candidatas:
        _logger.info(
            'D-24: no se encontraron etapas nativas intermedias a borrar '
            '(ya borradas o no existen en este entorno).'
        )
        return

    stage_recibido = env.ref('BCA_Seguros.stage_recibido', raise_if_not_found=False)
    if not stage_recibido:
        _logger.warning(
            'D-24: stage_recibido no encontrado; se aborta el borrado de '
            'etapas nativas para no dejar candidatos huérfanos.'
        )
        return

    stage_ids = tuple(candidatas.ids)
    nombres = candidatas.mapped('name')

    # Reasignar candidatos en esas etapas (SQL directo: evita disparar la
    # lógica de conversión del override write() de hr.applicant).
    cr.execute(
        "SELECT COUNT(*) FROM hr_applicant WHERE stage_id IN %s", (stage_ids,),
    )
    total_candidatos = cr.fetchone()[0]
    if total_candidatos:
        cr.execute(
            "UPDATE hr_applicant SET stage_id = %s WHERE stage_id IN %s",
            (stage_recibido.id, stage_ids),
        )
        _logger.info(
            'D-24: %s candidato(s) reasignado(s) de %s a "Recibido" antes de borrar.',
            total_candidatos, nombres,
        )

    # Borrar (DELETE), mismo patrón que la retirada de stage_alta_interna en 19.0.1.7.7.
    cr.execute("DELETE FROM hr_recruitment_stage WHERE id IN %s", (stage_ids,))
    _logger.info(
        'D-24: %s etapa(s) nativa(s) intermedia(s) borrada(s): %s.',
        len(stage_ids), nombres,
    )
