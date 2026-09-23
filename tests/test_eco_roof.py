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
4. El bloque solar, migrado a EnergyPlus real (engine/eco_roof_solar.py) --
   geometría del arreglo (rápido, sin EnergyPlus) + una corrida real de
   punta a punta contra el EPW de San José que ya trae el repo (Hallazgo de
   migración: "sin tabla/ficha inventada" se extiende acá a "sin resultado
   solar inventado" -- se corre el binario real, no se aproxima).

La no-regresión del motor de 3-M Tulip existente NO se duplica acá -- se
verifica corriendo tests/test_simulador_pista_a.py tal cual, sin cambios
(ver README del PR/avance-de-proyecto.md): si ese archivo sigue pasando
exactamente igual después de este cambio, el motor viejo no se tocó.

Las pruebas que corren EnergyPlus de verdad (TestGeometriaSuperficiePV no
--las de geometría son puro cálculo, no tocan el binario-- pero sí
TestSimularSolarEcoRoofEnergyPlusReal y TestSimularEcoRoofCompleto) tardan
unos segundos cada una (el motor real, no una aproximación) y se saltan
automáticamente (pytest.mark.skip) si este entorno no tiene el binario de
EnergyPlus instalado -- mismo criterio que exigirle a un test de base de
datos que la base de datos esté disponible, no es una falla de este código.
"""
import inspect
import math

import numpy as np
import pandas as pd
import pytest

from engine.eco_roof_catalog import ECO_ROOF_PRESETS, preset_disponible
from engine.eco_roof_curves import TABLA_N3, TABLA_N5, potencia_tabla_w
from engine.eco_roof_simulador import PresetSinTablaOficialError, simular_eco_roof
from engine.epw_real import SITIOS_EPW_REAL, cargar_epw_real
from engine.eco_roof_solar import (
    ACTIVE_AREA_FRACTION_GENERICO,
    RATED_EFFICIENCY_GENERICO,
    _area_para_capacidad_m2,
    _construir_superficie_pv,
    _detectar_energyplus,
    simular_solar_eco_roof,
)

try:
    _detectar_energyplus()
    _ENERGYPLUS_DISPONIBLE = True
    _RAZON_SIN_ENERGYPLUS = ""
except RuntimeError as e:
    _ENERGYPLUS_DISPONIBLE = False
    _RAZON_SIN_ENERGYPLUS = str(e)

_requiere_energyplus = pytest.mark.skipif(
    not _ENERGYPLUS_DISPONIBLE, reason=f"EnergyPlus no disponible en este entorno: {_RAZON_SIN_ENERGYPLUS}",
)


def _clima_horas_fijas(velocidades_ms, year=2026):
    """Mismo patrón que tests/test_simulador_pista_a.py::_clima_horas_fijas() -- sólo
    para el bloque EÓLICO (no sirve para el bloque solar, que ahora necesita un EPW
    real completo de 8760/8784 horas para correr EnergyPlus, ver
    TestSimularEcoRoofCompleto más abajo)."""
    idx = pd.date_range(f"{year}-01-01", periods=len(velocidades_ms), freq="h")
    return pd.DataFrame({"WS10M": velocidades_ms}, index=idx)


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
        """Se niega ANTES de tocar el bloque solar (ruta_epw="" nunca se usa, la
        excepción sale apenas se revisa preset_disponible()) -- no necesita EnergyPlus."""
        df = _clima_horas_fijas([8.0] * 24)
        with pytest.raises(PresetSinTablaOficialError):
            simular_eco_roof("eco_roof_2m_2", df, ruta_epw="", elevacion_m=1000.0)

    def test_presets_ok_si_disponibles(self):
        assert preset_disponible("eco_roof_1m_3_flat")
        assert preset_disponible("eco_roof_1m_5_flat")
        assert preset_disponible("eco_roof_1m_3_sloped")


class TestAreaParaCapacidad:
    """Área que hace que PVProperties.to_idf() calcule exacto la capacidad DC pedida
    (área × active_area_fraction × rated_efficiency × 1000, ver
    honeybee_energy/generator/pv.py) -- puro cálculo, no toca EnergyPlus."""

    def test_area_reproduce_la_capacidad_pedida(self):
        capacidad_kwp = 0.200
        area_m2 = _area_para_capacidad_m2(
            capacidad_kwp, RATED_EFFICIENCY_GENERICO, ACTIVE_AREA_FRACTION_GENERICO)
        capacidad_recalculada_w = area_m2 * ACTIVE_AREA_FRACTION_GENERICO * RATED_EFFICIENCY_GENERICO * 1000
        assert capacidad_recalculada_w == pytest.approx(capacidad_kwp * 1000.0)

    def test_area_positiva_y_crece_con_la_capacidad(self):
        area_200w = _area_para_capacidad_m2(0.200, RATED_EFFICIENCY_GENERICO, ACTIVE_AREA_FRACTION_GENERICO)
        area_400w = _area_para_capacidad_m2(0.400, RATED_EFFICIENCY_GENERICO, ACTIVE_AREA_FRACTION_GENERICO)
        assert area_200w > 0
        assert area_400w == pytest.approx(area_200w * 2)


class TestGeometriaSuperficiePV:
    """Geometría del arreglo (tilt/acimut) -- puro cálculo con Ladybug Face3D, sin
    correr EnergyPlus (rápido). Confirma que _construir_superficie_pv() efectivamente
    orienta la superficie como se le pide, no sólo que no explota."""

    @pytest.mark.parametrize("tilt_deg,acimut_deg", [
        (0.0, 0.0), (20.0, 0.0), (20.0, 90.0), (20.0, 135.0),
        (20.0, 180.0), (35.0, 270.0), (10.0, 45.0),
    ])
    def test_tilt_y_acimut_obtenidos_coinciden_con_lo_pedido(self, tilt_deg, acimut_deg):
        shade = _construir_superficie_pv(
            capacidad_kwp=0.200, tilt_deg=tilt_deg, acimut_superficie_deg=acimut_deg,
            rated_efficiency=RATED_EFFICIENCY_GENERICO,
            active_area_fraction=ACTIVE_AREA_FRACTION_GENERICO, system_loss_fraction=0.14,
        )
        geo = shade.geometry
        assert math.degrees(geo.tilt) == pytest.approx(tilt_deg, abs=0.5)
        if tilt_deg > 1e-9:
            diferencia = (math.degrees(geo.azimuth) - acimut_deg + 180) % 360 - 180
            assert diferencia == pytest.approx(0.0, abs=0.5)

    def test_area_de_la_superficie_coincide_con_la_capacidad(self):
        capacidad_kwp = 0.400
        shade = _construir_superficie_pv(
            capacidad_kwp=capacidad_kwp, tilt_deg=0.0, acimut_superficie_deg=0.0,
            rated_efficiency=RATED_EFFICIENCY_GENERICO,
            active_area_fraction=ACTIVE_AREA_FRACTION_GENERICO, system_loss_fraction=0.14,
        )
        area_esperada = _area_para_capacidad_m2(
            capacidad_kwp, RATED_EFFICIENCY_GENERICO, ACTIVE_AREA_FRACTION_GENERICO)
        assert shade.geometry.area == pytest.approx(area_esperada, rel=1e-6)


@_requiere_energyplus
class TestSimularSolarEcoRoofEnergyPlusReal:
    """Corrida real de punta a punta (Honeybee -> IDF -> subprocess EnergyPlus ->
    eplusout.sql) contra el EPW de San José que ya trae el repo -- una sola corrida
    (fixture de módulo), reutilizada por todas las aserciones de esta clase."""

    @staticmethod
    @pytest.fixture(scope="class")
    def resultado_solar_sj():
        ruta = SITIOS_EPW_REAL["san_jose"]["ruta_epw"]
        df_clima, _meta = cargar_epw_real(ruta)
        return simular_solar_eco_roof(df_clima, ruta, capacidad_kwp=0.200), df_clima

    def test_estructura_y_magnitud_plausible(self, resultado_solar_sj):
        r, df_clima = resultado_solar_sj
        assert set(r) >= {"serie_horaria_kwh", "kwh_anual", "kwh_mensual", "capacidad_kwp",
                           "tilt_deg", "advertencia"}
        assert len(r["serie_horaria_kwh"]) == len(df_clima)
        # Orden de magnitud esperado para 0.2 kWp en Costa Rica (tropical, GHI moderado-alto):
        # "specific yield" típico de PVWatts ~1200-1900 kWh/kWp/año -> 240-380 kWh/año para 0.2 kWp.
        # Rango amplio a propósito (no es una aserción de valor exacto, que cambiaría con
        # cualquier ajuste fino de EnergyPlus/PVWatts) -- sólo confirma que el resultado es
        # físicamente razonable, no un número roto (cero, negativo, o miles de veces más grande).
        assert 100.0 < r["kwh_anual"] < 600.0
        assert r["advertencia"]  # nunca vacía -- siempre marcado como estimado (panel genérico)

    def test_serie_horaria_no_negativa_y_nula_de_noche(self, resultado_solar_sj):
        r, df_clima = resultado_solar_sj
        serie = r["serie_horaria_kwh"]
        assert (serie >= -1e-9).all()
        horas_medianoche = serie[df_clima.index.hour.isin([0, 1, 2, 3])]
        assert (horas_medianoche.abs() < 1e-6).all()

    def test_kwh_mensual_suma_al_anual(self, resultado_solar_sj):
        r, _df_clima = resultado_solar_sj
        assert r["kwh_mensual"].sum() == pytest.approx(r["kwh_anual"], rel=1e-6)

    def test_mas_capacidad_da_mas_energia(self):
        ruta = SITIOS_EPW_REAL["san_jose"]["ruta_epw"]
        df_clima, _meta = cargar_epw_real(ruta)
        r_chico = simular_solar_eco_roof(df_clima, ruta, capacidad_kwp=0.200)
        r_grande = simular_solar_eco_roof(df_clima, ruta, capacidad_kwp=0.400)
        assert r_grande["kwh_anual"] == pytest.approx(r_chico["kwh_anual"] * 2, rel=0.02)

    def test_epw_inexistente_falla_explicito(self):
        ruta = SITIOS_EPW_REAL["san_jose"]["ruta_epw"]
        df_clima, _meta = cargar_epw_real(ruta)
        with pytest.raises(ValueError):
            simular_solar_eco_roof(df_clima, "/no/existe/este/archivo.epw", capacidad_kwp=0.2)


@_requiere_energyplus
class TestSimularEcoRoofCompleto:
    """Igual que TestSimularSolarEcoRoofEnergyPlusReal: reutiliza los resultados vía
    fixtures de módulo para no repetir la corrida real de EnergyPlus más de lo
    necesario (cada simular_eco_roof() de acá corre el motor real una vez)."""

    @staticmethod
    @pytest.fixture(scope="class")
    def epw_sj():
        ruta = SITIOS_EPW_REAL["san_jose"]["ruta_epw"]
        df_clima, meta = cargar_epw_real(ruta)
        return ruta, df_clima, meta

    @staticmethod
    @pytest.fixture(scope="class")
    def resultado_3flat(epw_sj):
        ruta, df_clima, meta = epw_sj
        return simular_eco_roof("eco_roof_1m_3_flat", df_clima, ruta, elevacion_m=meta["elevacion_m"])

    @staticmethod
    @pytest.fixture(scope="class")
    def resultado_5flat(epw_sj):
        ruta, df_clima, meta = epw_sj
        return simular_eco_roof("eco_roof_1m_5_flat", df_clima, ruta, elevacion_m=meta["elevacion_m"])

    def test_estructura_resultado(self, resultado_3flat):
        r = resultado_3flat
        assert r["kwh_anual_eolico"] > 0
        assert r["kwh_anual_solar"] >= 0
        assert r["kwh_anual_total"] == pytest.approx(r["kwh_anual_eolico"] + r["kwh_anual_solar"])
        assert r["solar"]["advertencia"]  # nunca vacía -- siempre marcado como estimado
        assert r["N"] == 3

    def test_n5_da_mas_energia_eolica_que_n3_mismo_viento(self, resultado_3flat, resultado_5flat):
        assert resultado_5flat["kwh_anual_eolico"] > resultado_3flat["kwh_anual_eolico"]

    def test_correccion_densidad_reduce_energia_en_altura(self, epw_sj, resultado_3flat):
        ruta, df_clima, _meta = epw_sj
        r_alto = simular_eco_roof("eco_roof_1m_3_flat", df_clima, ruta, elevacion_m=3000.0)
        assert r_alto["kwh_anual_eolico"] < resultado_3flat["kwh_anual_eolico"]
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
