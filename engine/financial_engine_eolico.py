# engine/financial_engine_eolico.py
# =============================================================================
# Análisis Financiero para Sistemas Eólicos Flower Turbines + Sol-Ark
# Calcula CAPEX, OPEX, Payback, ROI, y NPV para proyectos eólicos
# =============================================================================

import math
from typing import Dict, List, Optional


VIDA_UTIL_DEFAULT = 40  # Flower Turbines: 40 años


def _calcular_viabilidad(capex, ahorro_anual_usd, mantenimiento_anual_usd,
                          vida_util_anos, tasa_descuento_pct):
    """
    Núcleo común de Payback/ROI/NPV a partir de CAPEX y mantenimiento anual YA
    RESUELTOS en dólares -- lo reutilizan tanto el modo por % (turbinas/inversor/BESS
    + costo_instalacion_pct, ver _calcular_punto_financiero) como el modo de datos
    financieros reales ingresados a mano por el usuario (Hallazgo 53: "dejemos de
    adivinar" -- ver FinancialEngineEolico.calcular_punto_capex_directo).
    """
    opex_anual_neto = ahorro_anual_usd - mantenimiento_anual_usd
    if capex <= 0 or opex_anual_neto <= 0:
        return {
            "opex_anual_neto": round(opex_anual_neto, 2),
            "payback_years": None,
            "roi_percentage": None,
            "npv_usd": None,
        }

    payback = capex / opex_anual_neto
    roi = ((opex_anual_neto * vida_util_anos) - capex) / capex * 100

    tasa_desc = tasa_descuento_pct / 100
    npv = -capex
    for anio in range(1, vida_util_anos + 1):
        npv += opex_anual_neto / ((1 + tasa_desc) ** anio)

    return {
        "opex_anual_neto": round(opex_anual_neto, 2),
        "payback_years": round(payback, 2),
        "roi_percentage": round(roi, 2),
        "npv_usd": round(npv, 2),
    }


def _calcular_punto_financiero(
    potencia_pico_W: int,
    n_turbinas: int,
    energia_anual_kWh: float,
    costo_turbinas_USD: float,
    costo_inversor_USD: float,
    costo_bess_USD: float,
    tarifa_kwh_USD: float,
    costo_instalacion_pct: float = 0.35,
    costo_mantenimiento_pct_anual: float = 0.02,
    vida_util_anos: int = VIDA_UTIL_DEFAULT,
    tasa_descuento_pct: float = 8.0,
    sistema_tipo: str = "Standalone",
) -> dict:
    """
    Calcula métricas financieras para un punto de diseño del sistema eólico.

    Args:
        potencia_pico_W              : Potencia pico total del arreglo (W)
        n_turbinas                  : Cantidad de turbinas
        energia_anual_kWh            : Energía anual generada (kWh/año)
        costo_turbinas_USD           : Costo total turbinas (USD)
        costo_inversor_USD           : Costo inversor Sol-Ark (USD)
        costo_bess_USD               : Costo BESS (USD); 0 si Hybrid sin batería
        tarifa_kwh_USD               : Tarifa eléctrica ($/kWh)
        costo_instalacion_pct        : Costo instalación como % de equipos (default 0.35 = 35%)
        costo_mantenimiento_pct_anual: Mantenimiento anual como % de CAPEX (default 0.02 = 2%)
        vida_util_anos               : Vida útil del proyecto (default 40 años Flower)
        tasa_descuento_pct           : Tasa de descuento para NPV (default 8%)
        sistema_tipo                 : "Standalone" (con BESS) o "Hybrid" (sin BESS)

    Returns:
        dict con: potencia_pico_W, turbinas_count, sistema_tipo, capex,
                  opex_anual_neto, payback_years, roi_percentage, npv_usd
    """
    # CAPEX = (Turbinas + Inversor + BESS) × (1 + instalación%)
    costo_equipos = costo_turbinas_USD + costo_inversor_USD + costo_bess_USD
    costo_instalacion = costo_equipos * costo_instalacion_pct
    capex = costo_equipos + costo_instalacion

    # OPEX = (energía_anual × tarifa) - mantenimiento_anual
    ahorro_anual_kwh = energia_anual_kWh * tarifa_kwh_USD
    costo_mantenimiento_anual = capex * costo_mantenimiento_pct_anual
    opex_anual_neto = ahorro_anual_kwh - costo_mantenimiento_anual

    # Validaciones
    if capex <= 0 or n_turbinas == 0:
        return {
            "potencia_pico_W": potencia_pico_W,
            "turbinas_count": n_turbinas,
            "sistema_tipo": sistema_tipo,
            "capex": 0.0,
            "capex_equipos": 0.0,
            "capex_instalacion": 0.0,
            "ahorro_anual_kwh": energia_anual_kWh,
            "ahorro_anual_USD": round(ahorro_anual_kwh, 2),
            "mantenimiento_anual_USD": round(costo_mantenimiento_anual, 2),
            "opex_anual_neto": round(opex_anual_neto, 2),
            "payback_years": None,
            "roi_percentage": None,
            "npv_usd": None,
        }

    if opex_anual_neto <= 0:
        return {
            "potencia_pico_W": potencia_pico_W,
            "turbinas_count": n_turbinas,
            "sistema_tipo": sistema_tipo,
            "capex": round(capex, 2),
            "capex_equipos": round(costo_equipos, 2),
            "capex_instalacion": round(costo_instalacion, 2),
            "ahorro_anual_kwh": energia_anual_kWh,
            "ahorro_anual_USD": round(ahorro_anual_kwh, 2),
            "mantenimiento_anual_USD": round(costo_mantenimiento_anual, 2),
            "opex_anual_neto": round(opex_anual_neto, 2),
            "payback_years": None,
            "roi_percentage": None,
            "npv_usd": None,
        }

    # Payback/ROI/NPV -- núcleo compartido con el modo de datos financieros reales
    # (ver _calcular_viabilidad y FinancialEngineEolico.calcular_punto_capex_directo)
    viabilidad = _calcular_viabilidad(
        capex, ahorro_anual_kwh, costo_mantenimiento_anual, vida_util_anos, tasa_descuento_pct
    )

    return {
        "potencia_pico_W": potencia_pico_W,
        "turbinas_count": n_turbinas,
        "sistema_tipo": sistema_tipo,
        "capex": round(capex, 2),
        "capex_equipos": round(costo_equipos, 2),
        "capex_instalacion": round(costo_instalacion, 2),
        "ahorro_anual_kwh": energia_anual_kWh,
        "ahorro_anual_USD": round(ahorro_anual_kwh, 2),
        "mantenimiento_anual_USD": round(costo_mantenimiento_anual, 2),
        "opex_anual_neto": viabilidad["opex_anual_neto"],
        "payback_years": viabilidad["payback_years"],
        "roi_percentage": viabilidad["roi_percentage"],
        "npv_usd": viabilidad["npv_usd"],
    }


class FinancialEngineEolico:
    """
    Motor de análisis financiero paramétrico para sistemas eólicos.

    Recibe:
    - Specs técnicos del sistema (turbinas, inversor, BESS)
    - Energía anual calculada por simulación
    - Parámetros financieros (tarifa, vida útil, tasa descuento)

    Produce:
    - Análisis completo de CAPEX, OPEX, Payback, ROI, NPV
    - Sensibilidad a parámetros clave
    - Comparativa Standalone vs Hybrid
    """

    def __init__(
        self,
        tarifa_kwh_USD: float,
        costo_instalacion_pct: float = 0.35,
        costo_mantenimiento_pct_anual: float = 0.02,
        vida_util_anos: int = VIDA_UTIL_DEFAULT,
        tasa_descuento_pct: float = 8.0,
    ):
        """
        Args:
            tarifa_kwh_USD            : Tarifa eléctrica ($/kWh)
            costo_instalacion_pct     : Costo instalación como % de equipos (default 0.35 = 35%)
            costo_mantenimiento_pct_anual: Mantenimiento anual como % de CAPEX (default 0.02 = 2%)
            vida_util_anos            : Vida útil del proyecto (default 40 años)
            tasa_descuento_pct        : Tasa de descuento para NPV (default 8%)
        """
        if tarifa_kwh_USD < 0:
            raise ValueError("La tarifa eléctrica no puede ser negativa.")
        if costo_instalacion_pct < 0 or costo_instalacion_pct > 1:
            raise ValueError("El porcentaje de instalación debe estar entre 0 y 1.")
        if vida_util_anos <= 0:
            raise ValueError("La vida útil debe ser mayor a cero.")
        if tasa_descuento_pct < 0 or tasa_descuento_pct > 100:
            raise ValueError("La tasa de descuento debe estar entre 0 y 100%.")

        self.tarifa_kwh_USD = tarifa_kwh_USD
        self.costo_instalacion_pct = costo_instalacion_pct
        self.costo_mantenimiento_pct_anual = costo_mantenimiento_pct_anual
        self.vida_util_anos = vida_util_anos
        self.tasa_descuento_pct = tasa_descuento_pct

    def calcular_punto_unico(
        self,
        potencia_pico_W: int,
        n_turbinas: int,
        energia_anual_kWh: float,
        costo_turbinas_USD: float,
        costo_inversor_USD: float,
        costo_bess_USD: float = 0.0,
        sistema_tipo: str = "Standalone",
    ) -> dict:
        """Calcula métricas financieras para un único punto de diseño."""
        return _calcular_punto_financiero(
            potencia_pico_W=potencia_pico_W,
            n_turbinas=n_turbinas,
            energia_anual_kWh=energia_anual_kWh,
            costo_turbinas_USD=costo_turbinas_USD,
            costo_inversor_USD=costo_inversor_USD,
            costo_bess_USD=costo_bess_USD,
            tarifa_kwh_USD=self.tarifa_kwh_USD,
            costo_instalacion_pct=self.costo_instalacion_pct,
            costo_mantenimiento_pct_anual=self.costo_mantenimiento_pct_anual,
            vida_util_anos=self.vida_util_anos,
            tasa_descuento_pct=self.tasa_descuento_pct,
            sistema_tipo=sistema_tipo,
        )

    def calcular_punto_capex_directo(
        self,
        capex_usd: float,
        energia_anual_kWh: float,
        mantenimiento_anual_usd: float,
        potencia_pico_W: int = 0,
        n_turbinas: int = 0,
        sistema_tipo: str = "Standalone",
    ) -> dict:
        """
        Calcula Payback/ROI/NPV a partir de un CAPEX y un mantenimiento anual dados
        DIRECTAMENTE en dólares (Hallazgo 53) -- en vez de derivarlos de costo_turbinas_USD
        + costo_inversor_USD + costo_bess_USD + costo_instalacion_pct +
        costo_mantenimiento_pct_anual como hace calcular_punto_unico(). Para cuando el
        usuario ya tiene su propio precio de venta real y su propio costo de
        mantenimiento real, y no quiere que la app se los adivine con supuestos de
        margen/flete/instalación/mantenimiento porcentual.

        capex_usd               : precio de venta real del proyecto al cliente (USD) --
                                  la inversión real que se recupera con el ahorro.
        mantenimiento_anual_usd : costo de mantenimiento anual real (USD/año), NO un %.
        potencia_pico_W/n_turbinas: sólo informativos en el resultado, no afectan el
                                  cálculo -- se pasan si están disponibles para que el
                                  resultado tenga la misma forma que calcular_punto_unico().
        """
        ahorro_anual_usd = energia_anual_kWh * self.tarifa_kwh_USD
        viabilidad = _calcular_viabilidad(
            capex_usd, ahorro_anual_usd, mantenimiento_anual_usd,
            self.vida_util_anos, self.tasa_descuento_pct,
        )
        return {
            "potencia_pico_W": potencia_pico_W,
            "turbinas_count": n_turbinas,
            "sistema_tipo": sistema_tipo,
            "capex": round(capex_usd, 2),
            "ahorro_anual_kwh": energia_anual_kWh,
            "ahorro_anual_USD": round(ahorro_anual_usd, 2),
            "mantenimiento_anual_USD": round(mantenimiento_anual_usd, 2),
            "opex_anual_neto": viabilidad["opex_anual_neto"],
            "payback_years": viabilidad["payback_years"],
            "roi_percentage": viabilidad["roi_percentage"],
            "npv_usd": viabilidad["npv_usd"],
        }

    def calcular_sensibilidad_parametrica(
        self,
        potencia_pico_W: int,
        n_turbinas: int,
        energia_anual_kWh: float,
        costo_turbinas_USD: float,
        costo_inversor_USD: float,
        costo_bess_USD: float = 0.0,
        sistema_tipo: str = "Standalone",
        parametros_variar: Optional[Dict[str, List[float]]] = None,
    ) -> List[dict]:
        """
        Calcula análisis de sensibilidad variando parámetros clave.

        Args:
            (mismos parámetros que calcular_punto_unico)
            parametros_variar: Dict con {nombre_parametro: [valores]}
                              Ej: {"tarifa_kwh_USD": [0.10, 0.15, 0.20]}

        Returns:
            Lista de resultados para cada combinación de parámetros
        """
        if parametros_variar is None:
            parametros_variar = {
                "tarifa_kwh_USD": [
                    self.tarifa_kwh_USD * 0.8,
                    self.tarifa_kwh_USD,
                    self.tarifa_kwh_USD * 1.2,
                ],
                "costo_instalacion_pct": [0.25, 0.35, 0.45],
            }

        resultados = []

        # Generar todas las combinaciones
        def generar_combinaciones(params, idx=0, combo=None):
            if combo is None:
                combo = {}

            if idx == len(params):
                # Crear punto con esta combinación
                tarifa = combo.get(
                    "tarifa_kwh_USD", self.tarifa_kwh_USD
                )
                costo_inst = combo.get(
                    "costo_instalacion_pct", self.costo_instalacion_pct
                )

                resultado = _calcular_punto_financiero(
                    potencia_pico_W=potencia_pico_W,
                    n_turbinas=n_turbinas,
                    energia_anual_kWh=energia_anual_kWh,
                    costo_turbinas_USD=costo_turbinas_USD,
                    costo_inversor_USD=costo_inversor_USD,
                    costo_bess_USD=costo_bess_USD,
                    tarifa_kwh_USD=tarifa,
                    costo_instalacion_pct=costo_inst,
                    costo_mantenimiento_pct_anual=self.costo_mantenimiento_pct_anual,
                    vida_util_anos=self.vida_util_anos,
                    tasa_descuento_pct=self.tasa_descuento_pct,
                    sistema_tipo=sistema_tipo,
                )
                resultado["variaciones"] = combo.copy()
                resultados.append(resultado)
                return

            param_nombres = list(parametros_variar.keys())
            param_nombre = param_nombres[idx]
            for valor in parametros_variar[param_nombre]:
                combo[param_nombre] = valor
                generar_combinaciones(params, idx + 1, combo)

        generar_combinaciones(list(parametros_variar.keys()))
        return resultados

    def comparar_standalone_vs_hybrid(
        self,
        potencia_pico_W: int,
        n_turbinas: int,
        energia_anual_kWh: float,
        costo_turbinas_USD: float,
        costo_inversor_USD: float,
        costo_bess_USD: float,
    ) -> dict:
        """
        Compara economía de sistema Standalone (con BESS) vs Hybrid (sin BESS).

        Returns:
            dict con ambos escenarios y análisis comparativo
        """
        standalone = self.calcular_punto_unico(
            potencia_pico_W=potencia_pico_W,
            n_turbinas=n_turbinas,
            energia_anual_kWh=energia_anual_kWh,
            costo_turbinas_USD=costo_turbinas_USD,
            costo_inversor_USD=costo_inversor_USD,
            costo_bess_USD=costo_bess_USD,
            sistema_tipo="Standalone",
        )

        hybrid = self.calcular_punto_unico(
            potencia_pico_W=potencia_pico_W,
            n_turbinas=n_turbinas,
            energia_anual_kWh=energia_anual_kWh,
            costo_turbinas_USD=costo_turbinas_USD,
            costo_inversor_USD=costo_inversor_USD,
            costo_bess_USD=0.0,
            sistema_tipo="Hybrid",
        )

        # Análisis comparativo
        diferencia_capex = standalone["capex"] - hybrid["capex"]
        diferencia_roi = standalone["roi_percentage"] - hybrid["roi_percentage"]
        diferencia_payback = standalone["payback_years"] - hybrid["payback_years"] if (
            standalone["payback_years"] and hybrid["payback_years"]
        ) else None

        return {
            "standalone": standalone,
            "hybrid": hybrid,
            "comparativa": {
                "diferencia_capex_usd": round(diferencia_capex, 2),
                "costo_bess_como_pct_capex_standalone": round(
                    (costo_bess_USD / standalone["capex"] * 100), 2
                ) if standalone["capex"] > 0 else 0,
                "diferencia_roi_puntos_porcentuales": round(diferencia_roi, 2),
                "diferencia_payback_anos": round(diferencia_payback, 2) if diferencia_payback else None,
                "recomendacion": (
                    "Hybrid es más viable economicamente"
                    if hybrid["roi_percentage"] and standalone["roi_percentage"]
                    and hybrid["roi_percentage"] > standalone["roi_percentage"]
                    else "Standalone tiene mejor ROI"
                ),
            },
        }
