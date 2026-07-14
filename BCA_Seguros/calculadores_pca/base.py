class CalculadorPCABase:
    aseguradora_codigo = None

    def __init__(self, env):
        self.env = env

    def calcular(self, recibo):
        """Retorna (pca, factor_aplicado, motivo_exclusion)."""
        raise NotImplementedError
