#!/usr/bin/env python3
"""
Pruebas unitarias para FinancialEngineEolico

Verifica:
- Cálculo correcto de CAPEX, OPEX, Payback, ROI, NPV
- Validación de parámetros de entrada
- Comparación Standalone vs Hybrid
- Análisis de sensibilidad
"""

import pytest
import math
from engine.financial_engine_eolico import FinancialEngineEolico, _calcular_punto_financiero


class TestCalcularPuntoFinanciero:
    """Pruebas para función _calcular_punto_financiero"""

    def test_capex_basico(self):
        """CAPEX = (Turbinas + Inversor + BESS) × (1 + 35% instalación)"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            tarifa_kwh_USD=0.15,
            costo_instalacion_pct=0.35,
        )

        # Equipos = 16000 + 5000 + 8000 = 29000
        # Instalación = 29000 × 0.35 = 10150
        # CAPEX = 29000 + 10150 = 39150
        assert resultado["capex"] == pytest.approx(39150, abs=1)
        assert resultado["capex_equipos"] == pytest.approx(29000, abs=1)
        assert resultado["capex_instalacion"] == pytest.approx(10150, abs=1)

    def test_opex_neto(self):
        """OPEX_neto = (Energía × Tarifa) - Mantenimiento"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            tarifa_kwh_USD=0.15,
            costo_instalacion_pct=0.35,
            costo_mantenimiento_pct_anual=0.02,
        )

        # Ahorro anual = 15000 × 0.15 = 2250
        # Mantenimiento = 39150 × 0.02 = 783
        # OPEX_neto = 2250 - 783 = 1467
        assert resultado["ahorro_anual_USD"] == pytest.approx(2250, abs=1)
        assert resultado["mantenimiento_anual_USD"] == pytest.approx(783, abs=1)
        assert resultado["opex_anual_neto"] == pytest.approx(1467, abs=1)

    def test_payback_years(self):
        """Payback = CAPEX / OPEX_neto"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            tarifa_kwh_USD=0.15,
            costo_instalacion_pct=0.35,
            costo_mantenimiento_pct_anual=0.02,
        )

        # Payback = 39150 / 1467 ≈ 26.68 años
        assert resultado["payback_years"] == pytest.approx(26.68, abs=0.1)

    def test_roi_percentage(self):
        """ROI = ((OPEX_neto × vida_util) - CAPEX) / CAPEX × 100"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            tarifa_kwh_USD=0.15,
            costo_instalacion_pct=0.35,
            costo_mantenimiento_pct_anual=0.02,
            vida_util_anos=40,
        )

        # OPEX_neto × 40 = 1467 × 40 = 58680
        # ROI = (58680 - 39150) / 39150 × 100 = 19680 / 39150 × 100 ≈ 50.26%
        assert resultado["roi_percentage"] == pytest.approx(50.26, abs=1)

    def test_npv_basico(self):
        """NPV = Σ(OPEX_neto / (1 + tasa)^año) - CAPEX"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=30000,  # Mayor energía para NPV positivo
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            tarifa_kwh_USD=0.15,
            costo_instalacion_pct=0.35,
            costo_mantenimiento_pct_anual=0.02,
            vida_util_anos=40,
            tasa_descuento_pct=8.0,
        )

        # NPV debe ser calculado (no None)
        assert resultado["npv_usd"] is not None
        # Con 2x energía, NPV debería ser positivo
        assert resultado["npv_usd"] > 0

    def test_sistema_hybrid_sin_bess(self):
        """Sistema Hybrid: CAPEX sin costo de BESS"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=0.0,
            tarifa_kwh_USD=0.15,
            costo_instalacion_pct=0.35,
            sistema_tipo="Hybrid",
        )

        # Equipos = 16000 + 5000 + 0 = 21000
        # Instalación = 21000 × 0.35 = 7350
        # CAPEX = 21000 + 7350 = 28350
        assert resultado["capex"] == pytest.approx(28350, abs=1)
        assert resultado["sistema_tipo"] == "Hybrid"

    def test_capex_cero_retorna_valores_none(self):
        """Cuando CAPEX es 0, retorna None para métricas"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=0,
            n_turbinas=0,
            energia_anual_kWh=0,
            costo_turbinas_USD=0,
            costo_inversor_USD=0,
            costo_bess_USD=0,
            tarifa_kwh_USD=0.15,
        )

        assert resultado["capex"] == 0
        assert resultado["payback_years"] is None
        assert resultado["roi_percentage"] is None

    def test_opex_negativo_retorna_valores_none(self):
        """Cuando OPEX_neto es negativo, retorna None para métricas"""
        resultado = _calcular_punto_financiero(
            potencia_pico_W=1000,
            n_turbinas=1,
            energia_anual_kWh=100,  # Muy baja energía
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            tarifa_kwh_USD=0.15,
            costo_mantenimiento_pct_anual=0.10,  # Mantenimiento alto
        )

        # Ahorro = 100 × 0.15 = 15
        # Mantenimiento = 37450 × 0.10 = 3745
        # OPEX_neto = 15 - 3745 = -3730 (negativo)
        assert resultado["opex_anual_neto"] < 0
        assert resultado["payback_years"] is None
        assert resultado["roi_percentage"] is None


class TestFinancialEngineEolico:
    """Pruebas para la clase FinancialEngineEolico"""

    def test_init_validacion_tarifa_negativa(self):
        """No permite tarifa negativa"""
        with pytest.raises(ValueError, match="tarifa eléctrica no puede ser negativa"):
            FinancialEngineEolico(tarifa_kwh_USD=-0.15)

    def test_init_validacion_vida_util_negativa(self):
        """No permite vida útil <= 0"""
        with pytest.raises(ValueError, match="vida útil debe ser mayor a cero"):
            FinancialEngineEolico(tarifa_kwh_USD=0.15, vida_util_anos=0)

    def test_init_validacion_tasa_descuento_invalida(self):
        """No permite tasa de descuento fuera de rango 0-100"""
        with pytest.raises(ValueError, match="tasa de descuento debe estar entre 0 y 100"):
            FinancialEngineEolico(tarifa_kwh_USD=0.15, tasa_descuento_pct=150)

    def test_calcular_punto_unico_standalone(self):
        """Cálculo de punto único para Standalone"""
        fe = FinancialEngineEolico(tarifa_kwh_USD=0.15)

        resultado = fe.calcular_punto_unico(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            sistema_tipo="Standalone",
        )

        assert resultado["sistema_tipo"] == "Standalone"
        assert resultado["capex"] > 0
        assert resultado["roi_percentage"] is not None

    def test_calcular_punto_unico_hybrid(self):
        """Cálculo de punto único para Hybrid"""
        fe = FinancialEngineEolico(tarifa_kwh_USD=0.15)

        resultado = fe.calcular_punto_unico(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=0.0,
            sistema_tipo="Hybrid",
        )

        assert resultado["sistema_tipo"] == "Hybrid"
        assert resultado["capex"] > 0

    def test_calcular_sensibilidad_parametrica(self):
        """Análisis de sensibilidad con variaciones"""
        fe = FinancialEngineEolico(tarifa_kwh_USD=0.15)

        resultados = fe.calcular_sensibilidad_parametrica(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
            parametros_variar={
                "tarifa_kwh_USD": [0.12, 0.15, 0.18],
            },
        )

        assert len(resultados) == 3
        assert all(isinstance(r, dict) for r in resultados)
        assert all("variaciones" in r for r in resultados)

    def test_comparar_standalone_vs_hybrid(self):
        """Comparación entre Standalone y Hybrid"""
        fe = FinancialEngineEolico(tarifa_kwh_USD=0.15)

        resultado = fe.comparar_standalone_vs_hybrid(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
        )

        assert "standalone" in resultado
        assert "hybrid" in resultado
        assert "comparativa" in resultado

        # Hybrid debe tener menor CAPEX que Standalone
        assert resultado["hybrid"]["capex"] < resultado["standalone"]["capex"]

        # CAPEX difference debe ser igual al costo del BESS + instalación
        bess_con_inst = 8000 * 1.35
        assert resultado["comparativa"]["diferencia_capex_usd"] == pytest.approx(
            bess_con_inst, abs=1
        )

    def test_roi_sensible_a_tarifa(self):
        """ROI aumenta con tarifa eléctrica más alta"""
        fe_baja = FinancialEngineEolico(tarifa_kwh_USD=0.10)
        fe_alta = FinancialEngineEolico(tarifa_kwh_USD=0.20)

        resultado_baja = fe_baja.calcular_punto_unico(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
        )

        resultado_alta = fe_alta.calcular_punto_unico(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
        )

        # Mayor tarifa → mayor ROI
        assert resultado_alta["roi_percentage"] > resultado_baja["roi_percentage"]

    def test_vida_util_afecta_roi(self):
        """ROI aumenta con mayor vida útil"""
        fe_corta = FinancialEngineEolico(tarifa_kwh_USD=0.15, vida_util_anos=20)
        fe_larga = FinancialEngineEolico(tarifa_kwh_USD=0.15, vida_util_anos=40)

        resultado_corta = fe_corta.calcular_punto_unico(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
        )

        resultado_larga = fe_larga.calcular_punto_unico(
            potencia_pico_W=10000,
            n_turbinas=4,
            energia_anual_kWh=15000,
            costo_turbinas_USD=16000,
            costo_inversor_USD=5000,
            costo_bess_USD=8000,
        )

        # Mayor vida útil → mayor ROI
        assert resultado_larga["roi_percentage"] > resultado_corta["roi_percentage"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
