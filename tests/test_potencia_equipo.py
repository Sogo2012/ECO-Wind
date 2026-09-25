#!/usr/bin/env python3
"""
Potencia de los equipos (engine/potencia_equipo.py + ficha del 3-M Tulip).

Caso real (correo de Daniel Farb, Flower Turbines): informe del Estadio Heredia, 20
turbinas 3-M Tulip -- la página 1 decía 20 kW pico (ficha: 1,000 W por generador)
mientras la energía anual dejaba llegar cada turbina a los 3 kW del cargador. Corrección:
generador de 3 kW, potencia pico instalada 20 × 3 kW = 60 kW, con cualquier cargador.
"""
import numpy as np
import pandas as pd
import pytest

from engine.flower_turbines_curves import power_in_bouquet
from engine.potencia_equipo import potencia_max_turbina_w, velocidad_a_potencia_ms
from engine.simulador_pista_a import simular
from engine.turbine_specs import SPECS_TURBINAS

ART_3M_1KW = "3-meter tulip off grid with charger 1 kilowatt"
ART_3M_3KW = "3-meter tulip off grid with charger 3 kilowatts"


class TestPotenciaMaxTurbina:
    def test_3m_tulip_sigue_al_cargador_del_articulo(self):
        assert potencia_max_turbina_w("three_m_tulip", ART_3M_3KW) == 3000
        assert potencia_max_turbina_w("three_m_tulip", ART_3M_1KW) == 1000

    def test_estadio_heredia_potencia_pico_instalada_60kw(self):
        """Potencia pico instalada = 20 × potencia nominal del generador = 60 kW
        (corrección de Daniel), con cualquier cargador -- el cargador limita la
        energía, no la capacidad instalada."""
        assert 20 * SPECS_TURBINAS["three_m_tulip"]["potencia_nominal_w"] == 60_000

    def test_sin_kw_en_el_articulo_cae_al_generador(self):
        assert potencia_max_turbina_w("three_m_tulip", None) == SPECS_TURBINAS["three_m_tulip"]["potencia_nominal_w"]
        assert potencia_max_turbina_w(
            "three_m_tulip", "3-meter tulip hurricane reinforcements per blade set") == 3000

    def test_controlador_mayor_o_menor_que_el_generador(self):
        """Large Tulip (generador 5 kW) con inversor de 10 kW, y AL13 8m (generador
        10 kW) con inversor de 5 kW: manda el controlador en los dos sentidos -- es lo
        que el cálculo de energía deja pasar."""
        assert potencia_max_turbina_w("large_tulip", "5-meter tulip on grid with inverter 10 kilowatts") == 10000
        assert potencia_max_turbina_w("al13_8m", "8-meter blade height turbine on grid with inverter 5 kilowatts") == 5000

    def test_el_maximo_horario_simulado_nunca_supera_la_potencia_pico(self):
        """La prueba de consistencia que falló en el informe original: con viento fuerte,
        la potencia horaria simulada llega justo al tope del cargador, y ni ella ni la
        media del año pasan la potencia pico instalada (generador de la ficha)."""
        idx = pd.date_range("2026-01-01", periods=48, freq="h")
        df = pd.DataFrame({"WS10M": np.linspace(3.0, 20.0, 48)}, index=idx)
        pico_instalada = SPECS_TURBINAS["three_m_tulip"]["potencia_nominal_w"]
        for articulo in (ART_3M_1KW, ART_3M_3KW):
            tope = potencia_max_turbina_w("three_m_tulip", articulo)
            r = simular(df, altura_buje=25.0, modelo="three_m_tulip", N=10, capacidad_electronica_w=tope)
            serie = r["serie_horaria_W_por_turbina"]
            assert serie.max() == pytest.approx(tope)
            assert serie.max() <= pico_instalada
            assert serie.mean() <= pico_instalada


class TestFicha3MTulip:
    """Correcciones de Daniel Farb (Flower Turbines) a la ficha del 3-M Tulip."""

    def test_potencia_nominal_3kw(self):
        assert SPECS_TURBINAS["three_m_tulip"]["potencia_nominal_w"] == 3000

    def test_supervivencia_40_y_54_con_refuerzo(self):
        specs = SPECS_TURBINAS["three_m_tulip"]
        assert specs["velocidad_supervivencia_ms"] == 40.0
        assert specs["velocidad_supervivencia_reforzada_ms"] == 54.0


class TestVelocidadAPotencia:
    @pytest.mark.parametrize("N", [1, 3, 5, 10])
    def test_ida_y_vuelta_con_la_curva(self, N):
        """A la velocidad devuelta, la curva validada da exactamente la potencia pedida."""
        v = velocidad_a_potencia_ms("three_m_tulip", N, 3000.0)
        assert float(power_in_bouquet(v, "three_m_tulip", N)) == pytest.approx(3000.0)

    def test_3kw_en_bouquet_si_aislada_no_dentro_de_la_tabla(self):
        """3 kW: la turbina aislada no llega dentro de la tabla oficial (0-15 m/s); en
        bouquet sí, y más temprano cuanto más grande el bouquet."""
        v1 = velocidad_a_potencia_ms("three_m_tulip", 1, 3000.0)
        v5 = velocidad_a_potencia_ms("three_m_tulip", 5, 3000.0)
        v10 = velocidad_a_potencia_ms("three_m_tulip", 10, 3000.0)
        assert v1 > 15.0
        assert v10 < v5 < 15.0

    def test_punto_de_la_ficha_anterior(self):
        """La ficha anterior decía 1000 W a 11 m/s: sigue siendo el punto de la turbina
        aislada en la curva validada."""
        assert velocidad_a_potencia_ms("three_m_tulip", 1, 1000.0) == pytest.approx(11.0, abs=0.3)
