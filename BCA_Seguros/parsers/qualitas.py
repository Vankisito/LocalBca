from __future__ import annotations

from .base import ParserBase


class ParserQualitas(ParserBase):
    """Placeholder de Qualitas (ramo Autos). Implementación post v1.0."""

    aseguradora_codigo = 'QUALITAS'
    ramo = 'autos'
    columnas_requeridas: list[str] = []

    def _procesar_fila_interna(self, env, fila: dict, numero_fila: int,
                               raw: str) -> dict:
        raise NotImplementedError(
            'Parser Qualitas no implementado (post v1.0).'
        )
