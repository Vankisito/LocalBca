from .base import CalculadorPCABase


class CalculadorPCAMetLife(CalculadorPCABase):
    """Calculador de PCA para MetLife (ramos Vida y GMM).

    PCA = prima_neta x factor, evaluando exclusiones antes del factor.
    El resultado se expresa SIEMPRE en MXN (decision D-08): para polizas en
    otra moneda se selecciona el factor de la fila correspondiente a la moneda
    de la poliza (conserva el ajuste, ej. Vida USD 80%) y el monto resultante
    se convierte a MXN via res.currency a la fecha de pago.
    """

    aseguradora_codigo = 'METLIFE'

    def calcular(self, recibo):
        """Retorna (pca, factor_aplicado, motivo_exclusion) con pca en MXN."""
        poliza = recibo.poliza_id
        ramo = poliza.ramo

        if ramo not in ('vida', 'gmm'):
            return (0.0, 0.0, 'Ramo no soportado por calculador MetLife')

        # 1. Exclusiones (se evaluan ANTES de aplicar cualquier factor).
        motivo = self._evaluar_exclusiones(poliza, ramo)
        if motivo:
            return (0.0, 0.0, motivo)

        # 2. Factor vigente a la fecha de pago.
        factor = self._buscar_factor(recibo, poliza, ramo)
        if factor is None:
            return (0.0, 0.0, 'Sin factor PCA vigente')

        # 3. PCA = prima_neta x factor (en moneda de la poliza) -> convertir a MXN.
        pca_ccy = recibo.prima_neta * factor.factor
        mxn = self.env.ref('base.MXN')
        if poliza.currency_id == mxn:
            pca = pca_ccy
        else:
            pca = poliza.currency_id._convert(
                pca_ccy, mxn, self.env.company, recibo.fecha_pago
            )
        return (pca, factor.factor, '')

    def _evaluar_exclusiones(self, poliza, ramo):
        """Retorna el motivo de exclusion (str) o '' si no hay exclusion."""
        if ramo == 'vida':
            if poliza.es_aportacion_adicional:
                return 'Aportación adicional (producto capitalizable)'
            # temporalidad 0/sin capturar = permanente -> no excluye.
            if 0 < poliza.temporalidad_anios < 10:
                return 'Temporalidad < 10 años'
        elif ramo == 'gmm':
            # poliza.coaseguro es fraccion (0.05 = 5%); el catalogo de factores
            # lo guarda en puntos porcentuales (coaseguro_min = 10.0). Normalizar.
            coaseguro_pct = poliza.coaseguro * 100.0
            if coaseguro_pct <= 5.0:
                return 'Coaseguro ≤ 5%'
        return ''

    def _buscar_factor(self, recibo, poliza, ramo):
        """Localiza el bca.factor.pca vigente. Retorna el record o None."""
        fecha = recibo.fecha_pago
        domain = [
            ('aseguradora_id', '=', poliza.aseguradora_id.id),
            ('ramo', '=', ramo),
            ('activo', '=', True),
            ('vigencia_desde', '<=', fecha),
            '|',
            ('vigencia_hasta', '=', False),
            ('vigencia_hasta', '>=', fecha),
        ]

        if ramo == 'vida':
            domain += [
                ('producto_ids', 'in', poliza.producto_id.id),
                ('currency_id', '=', poliza.currency_id.id),
            ]
            return self.env['bca.factor.pca'].search(domain, limit=1) or None

        # GMM: filtra por umbrales de coaseguro/deducible y toma la regla mas
        # especifica (mayor deducible_min, luego mayor coaseguro_min).
        coaseguro_pct = poliza.coaseguro * 100.0
        candidatos = self.env['bca.factor.pca'].search(domain)
        aplicables = candidatos.filtered(
            lambda f: coaseguro_pct >= f.coaseguro_min
            and poliza.deducible >= f.deducible_min
            and (not f.coaseguro_max or coaseguro_pct <= f.coaseguro_max)
        )
        if not aplicables:
            return None
        return aplicables.sorted(
            key=lambda f: (f.deducible_min, f.coaseguro_min), reverse=True
        )[0]
