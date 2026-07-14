from .base import CalculadorPCABase
from .metlife import CalculadorPCAMetLife

CALCULADOR_REGISTRY = {
    'METLIFE': CalculadorPCAMetLife,
}
