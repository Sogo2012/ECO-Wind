#!/usr/bin/env python3
"""
Pruebas del Eco-Roof Energy Hub (Small Tulip, 1m) -- Pista Eco-Roof, producto
nuevo y separado del motor de 3-M Tulip.

Cubre lo que pide el prompt original:
1. La interpolación da EXACTO los valores de tabla en los puntos exactos.
2. eco_roof_2m_2 (placeholder sin tabla oficial) nunca devuelve un número de
   energía sin la advertencia -- de hecho, ni siquiera calcula: lanza
   PresetSinTablaOficialError.
3. Guardas estructurales de que este módulo nunca usa
   power_in_bouquet()/M(N)=e^(0.21103×(N-1)) (el multiplicador del 3-M Tulip).

La no-regresión del motor de 3-M Tulip existente NO se duplica acá -- se
verifica corriendo tests/test_simulador_pista_a.py tal cual, sin cambios
(ver README del PR/avance-de-proyecto.md): si ese archivo sigue pasando
exactamente igual después de este cambio, el motor viejo no se tocó.
"""
import inspect

import numpy as np
import pandas as pd
import pytest

from engine.eco_roof_catalog import ECO_ROOF_PRESETS, preset_disponible
from engine.eco_roof_curves import TABLA_N3, TABLA_N5, potencia_tabla_w
from engine.eco_roof_simulador import PresetSinTablaOficialError, simular_eco_roof
from engine.eco_roof_solar import irradiancia_poa, posicion_solar, simular_solar_eco_roof


def _clima_horas_fijas(velocidades_ms, ghi=0.0, dni=0.0, dhi=0.0, year=2026):
    """Mismo patrón que tests/test_simulador_pista_a.py::_clima_horas_fijas(), con
    GHI/DNI/DHI agregadas para el bloque solar."""
    idx = pd.date_range(f"{year}-01-01", periods=len(velocidades_ms), freq="h")
    n = len(velocidades_ms)
    return pd.DataFrame({
        "WS10M": velocidades_ms,
        "GHI": [ghi] * n, "DNI": [dni] * n, "DHI": [dhi] * n,
    }, index=idx)


class TestInterpolacionTablaOficial:
    """La tabla se interpola tal cual, sin ajustar ninguna curva continua."""

    def test_puntos_exactos_n3(self):
        assert potencia_tabla_w(11.0, TABLA_N3) == pytest.approx(83.9)
        assert potencia_tabla_w(5.0, TABLA_N3) == pytest.approx(7.9)
        assert potencia_tabla_w(0.0, TABLA_N3) == pytest.approx(0.0)
        assert potencia_tabla_w(15.0, TABLA_N3) == pytest.approx(212.6)

    def test_puntos_exactos_n5(self):
        assert potencia_tabla_w(11.0, TABLA_N5) == pytest.approx(109.2)
        assert potencia_tabla_w(5.0, TABLA_N5) == pytest.approx(10.3)
        assert potencia_tabla_w(0.0, TABLA_N5) == pytest.approx(0.0)
        assert potencia_tabla_w(15.0, TABLA_N5) == pytest.approx(277.0)

    def test_interpolacion_lineal_entre_puntos(self):
        # 11.25 m/s está exactamente a mitad de camino entre 11.0 (83.9) y 11.5 (95.8).
        esperado = (83.9 + 95.8) / 2
        assert potencia_tabla_w(11.25, TABLA_N3) == pytest.approx(esperado)

    def test_fuera_de_rango_usa_extremo_mas_cercano(self):
        """Velocidades fuera de 0-15 m/s: valor del extremo, sin extrapolar la
        pendiente (si extrapolara, v=20 daría MÁS que el valor en 15.0)."""
        assert potencia_tabla_w(-5.0, TABLA_N3) == pytest.approx(0.0)
        assert potencia_tabla_w(20.0, TABLA_N3) == pytest.approx(212.6)
        assert potencia_tabla_w(100.0, TABLA_N5) == pytest.approx(277.0)

    def test_vectorizado(self):
        resultado = potencia_tabla_w(np.array([0.0, 11.0, 15.0, 30.0]), TABLA_N3)
        np.testing.assert_allclose(resultado, [0.0, 83.9, 212.6, 212.6])


class TestPresetSinTablaOficial:
    def test_eco_roof_2m_2_no_disponible(self):
        assert ECO_ROOF_PRESETS["eco_roof_2m_2"]["status"] == "sin_tabla_oficial"
        assert not preset_disponible("eco_roof_2m_2")
        assert ECO_ROOF_PRESETS["eco_roof_2m_2"]["tabla_potencia"] is None

    def test_eco_roof_2m_2_nunca_devuelve_energia(self):
        df = _clima_horas_fijas([8.0] * 24)
        with pytest.raises(PresetSinTablaOficialError):
            simular_eco_roof("eco_roof_2m_2", df, elevacion_m=1000.0,
                              lat_deg=10.0, lon_deg=-84.0, utc_offset_h=-6.0)

    def test_presets_ok_si_disponibles(self):
        assert preset_disponible("eco_roof_1m_3_flat")
        assert preset_disponible("eco_roof_1m_5_flat")
        assert preset_disponible("eco_roof_1m_3_sloped")


class TestSolarPOA:
    def test_poa_igual_a_ghi_con_tilt_cero(self):
        """Identidad física: para una superficie perfectamente horizontal,
        POA == GHI (por definición: GHI = DNI*cos(zenith) + DHI, y con tilt=0
        el haz se escala igual por cos(zenith) y la difusa entra completa)."""
        altitudes = np.array([10.0, 30.0, 60.0, 89.0])
        acimutes = np.array([90.0, 45.0, -30.0, 0.0])
        cos_zenith = np.sin(np.radians(altitudes))
        dni = np.array([800.0, 900.0, 950.0, 200.0])
        dhi = np.array([100.0, 120.0, 80.0, 50.0])
        ghi = dni * cos_zenith + dhi

        poa = irradiancia_poa(ghi, dni, dhi, altitudes, acimutes, tilt_deg=0.0)
        np.testing.assert_allclose(poa, ghi, rtol=1e-6)

    def test_poa_nocturno_no_negativo(self):
        """Sol bajo el horizonte (altitud negativa) -- sin haz directo, la
        irradiancia no debería salir negativa."""
        poa = irradiancia_poa(ghi=0.0, dni=0.0, dhi=0.0,
                               altitud_solar_deg=-20.0, acimut_solar_deg=180.0, tilt_deg=15.0)
        assert poa == pytest.approx(0.0)

    def test_posicion_solar_mediodia_solar_altitud_maxima(self):
        """En el mediodía SOLAR (no de reloj) del solsticio de verano boreal, para un
        sitio en el hemisferio norte, la altitud debe acercarse a su máximo del año."""
        idx = pd.date_range("2026-06-21", periods=24, freq="h")
        # utc_offset_h y lon_deg calzados para que el mediodía solar caiga cerca de
        # las 12:00 de reloj (mismo meridiano que la referencia UTC).
        pos = posicion_solar(idx, lat_deg=10.0, lon_deg=-90.0, utc_offset_h=-6.0)
        hora_pico = int(np.argmax(pos["altitud_deg"]))
        assert 11 <= hora_pico <= 13
        # Altitud solar máxima teórica al mediodía = 90 - |lat - declinación|; declinación
        # en el solsticio de junio ~23.44° -> 90 - |10-23.44| = 76.56°, no 90° (10°N no
        # está bajo el sol en junio, la declinación ya se pasó de largo hacia el norte).
        assert pos["altitud_deg"].max() == pytest.approx(76.56, abs=0.5)


class TestSimularEcoRoofCompleto:
    def test_estructura_resultado(self):
        df = _clima_horas_fijas([8.0] * 48, ghi=400.0, dni=600.0, dhi=100.0)
        r = simular_eco_roof("eco_roof_1m_3_flat", df, elevacion_m=1000.0,
                              lat_deg=10.0, lon_deg=-84.0, utc_offset_h=-6.0)

        assert r["kwh_anual_eolico"] > 0
        assert r["kwh_anual_solar"] >= 0
        assert r["kwh_anual_total"] == pytest.approx(r["kwh_anual_eolico"] + r["kwh_anual_solar"])
        assert r["solar"]["advertencia"]  # nunca vacía -- siempre marcado como estimado
        assert r["N"] == 3

    def test_n5_da_mas_energia_eolica_que_n3_mismo_viento(self):
        df = _clima_horas_fijas([10.0] * 48)
        r3 = simular_eco_roof("eco_roof_1m_3_flat", df, elevacion_m=0.0,
                               lat_deg=10.0, lon_deg=-84.0, utc_offset_h=-6.0)
        r5 = simular_eco_roof("eco_roof_1m_5_flat", df, elevacion_m=0.0,
                               lat_deg=10.0, lon_deg=-84.0, utc_offset_h=-6.0)
        assert r5["kwh_anual_eolico"] > r3["kwh_anual_eolico"]

    def test_correccion_densidad_reduce_energia_en_altura(self):
        df = _clima_horas_fijas([10.0] * 48)
        r_mar = simular_eco_roof("eco_roof_1m_3_flat", df, elevacion_m=0.0,
                                  lat_deg=10.0, lon_deg=-84.0, utc_offset_h=-6.0)
        r_alto = simular_eco_roof("eco_roof_1m_3_flat", df, elevacion_m=1500.0,
                                   lat_deg=10.0, lon_deg=-84.0, utc_offset_h=-6.0)
        assert r_alto["kwh_anual_eolico"] < r_mar["kwh_anual_eolico"]
        assert r_alto["factor_correccion_densidad"] < 1.0


class TestNoUsaMultiplicadorBouquetDel3MTulip:
    """Guarda estructural: los módulos Eco-Roof nunca importan ni referencian
    power_in_bouquet()/CURVE_COEFFICIENTS (el multiplicador M(N)=e^(0.21103×(N-1))
    calibrado para 2M/3M/6M Tulip, no para la Small Tulip)."""

    def test_ningun_modulo_eco_roof_importa_el_motor_viejo(self):
        """Ningún módulo Eco-Roof trae power_in_bouquet()/CURVE_COEFFICIENTS a su
        propio namespace -- la guarda decisiva es que NUNCA se importan (los
        docstrings SÍ los mencionan, a propósito, para explicar por qué no se usan;
        por eso esta prueba revisa el namespace importado, no el texto crudo del
        módulo, que incluiría esos docstrings como falsos positivos)."""
        import engine.eco_roof_catalog as cat
        import engine.eco_roof_curves as curvas
        import engine.eco_roof_simulador as sim
        import engine.eco_roof_solar as solar

        for modulo in (cat, curvas, sim, solar):
            assert not hasattr(modulo, "power_in_bouquet"), f"{modulo.__name__} importa power_in_bouquet()"
            assert not hasattr(modulo, "CURVE_COEFFICIENTS"), f"{modulo.__name__} importa CURVE_COEFFICIENTS"

    def test_ninguna_funcion_eco_roof_usa_el_multiplicador_m_de_n(self):
        """El CÓDIGO (no los docstrings, que sí lo mencionan a propósito) de ninguna
        función Eco-Roof usa el multiplicador M(N)=e^(0.21103×(N-1)) del 3-M Tulip."""
        import engine.eco_roof_catalog as cat
        import engine.eco_roof_curves as curvas
        import engine.eco_roof_simulador as sim
        import engine.eco_roof_solar as solar

        for modulo in (cat, curvas, sim, solar):
            for nombre, funcion in inspect.getmembers(modulo, inspect.isfunction):
                if funcion.__module__ != modulo.__name__:
                    continue  # función importada de otro módulo, no definida acá
                fuente_funcion = inspect.getsource(funcion)
                assert "power_in_bouquet" not in fuente_funcion, f"{modulo.__name__}.{nombre}"
                assert "0.21103" not in fuente_funcion, f"{modulo.__name__}.{nombre}"
