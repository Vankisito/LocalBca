from .base import ParserBase
from .metlife_lsp import ParserMetLifeVida
from .metlife_gcaye import ParserMetLifeGMM
from .qualitas import ParserQualitas

_REGISTRY = {
    ('METLIFE', 'vida'): ParserMetLifeVida,
    ('METLIFE', 'gmm'): ParserMetLifeGMM,
    ('QUALITAS', 'autos'): ParserQualitas,
}


def get_parser(aseguradora_codigo, ramo):
    key = (aseguradora_codigo.upper(), ramo.lower())
    cls = _REGISTRY.get(key)
    if not cls:
        from odoo.exceptions import UserError
        raise UserError(
            f"No existe parser para aseguradora='{aseguradora_codigo}' ramo='{ramo}'. "
            f"Parsers disponibles: {list(_REGISTRY.keys())}"
        )
    return cls
