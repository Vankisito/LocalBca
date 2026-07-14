from . import models, wizards, parsers, calculadores_pca, reports


def post_init_hook_bca_seguros(env):
    """Recrear SQL views de reportes al instalar o actualizar el módulo."""
    for model_name in [
        'bca.reporte.pca.agente',
        'bca.reporte.pca.promotoria',
        'bca.reporte.pca.consolidado',
        'bca.reporte.estado.cartera',
    ]:
        env[model_name].init()
