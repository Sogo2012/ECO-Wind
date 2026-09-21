#!/usr/bin/env python3
"""
Pruebas unitarias para el recorte por electrónica en simular()
(engine/simulador_pista_a.py) -- correo del proyecto Estadio Heredia,
Flower Turbines: sin capacidad_electronica_w, kWh/año asume que toda la
energía aerodinámica (incluido el Efecto Bouquet) se aprovecha, sin importar
qué controlador/inversor tiene cada turbina. Con capacidad_electronica_w, se
recorta hora por hora, watt por watt, ANTES de integrar a kWh.

Ninguna prueba depende de datos climáticos reales -- se arma un DataFrame
sintético de viento a mano para poder calcular el resultado esperado a mano
también.
"""
import numpy as np
import pandas as pd
import pytest

from engine.simulador_pista_a import simular
from engine.flower_turbines_curves import power_in_bouquet


def _clima_horas_fijas(velocidades_ms):
    """DataFrame de 'clima' con una fila por hora, WS10M = velocidades_ms."""
    idx = pd.date_range("2026-01-01", periods=len(velocidades_ms), freq="h")
    return pd.DataFrame({"WS10M": velocidades_ms}, index=idx)


class TestSinRecorte:
    """capacidad_electronica_w=None (default) -- mismo comportamiento que antes."""

    def test_default_no_recorta(self):
        df = _clima_horas_fijas([12.0] * 10)  # bien arriba de cut-in, sube P por encima de "nominal"
        r = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03)

        assert r["capacidad_electronica_w"] is None
        assert r["energia_perdida_por_recorte_kwh"] == 0.0
        assert r["pct_horas_con_recorte"] == 0.0

    def test_capacidad_muy_alta_no_recorta(self):
        """Un tope que nunca se alcanza da el mismo resultado que sin tope."""
        df = _clima_horas_fijas([12.0] * 10)
        sin_tope = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03)
        con_tope_alto = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03,
                                 capacidad_electronica_w=999_999.0)

        assert con_tope_alto["kwh_anual"] == pytest.approx(sin_tope["kwh_anual"])
        assert con_tope_alto["energia_perdida_por_recorte_kwh"] == pytest.approx(0.0, abs=1e-6)
        assert con_tope_alto["pct_horas_con_recorte"] == 0.0


class TestConRecorte:
    def test_recorta_al_tope_exacto(self):
        """altura_buje=10 con z0=z0_met iguala v_hub a WS10M -- así el cálculo a mano
        (power_in_bouquet directo) es exactamente comparable, sin el perfil logarítmico
        de por medio."""
        velocidades = [12.0] * 24  # arriba de la velocidad nominal (11 m/s) -> P > "nominal"
        df = _clima_horas_fijas(velocidades)
        tope_w = 1000.0

        r = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03,
                    capacidad_electronica_w=tope_w)

        # Potencia real (sin recorte) a 12 m/s, aislada (N=1): power_in_bouquet ya
        # está validado contra la tabla oficial de Flower Turbines (1400.0 W).
        potencia_sin_recorte = float(power_in_bouquet(12.0, "three_m_tulip", 1))
        assert potencia_sin_recorte == pytest.approx(1400.0, abs=0.5)
        assert potencia_sin_recorte > tope_w  # la premisa de esta prueba

        # Con recorte: cada hora entrega como máximo el tope, nunca los 1400W reales.
        kwh_esperado = tope_w * len(velocidades) / 1000.0
        assert r["kwh_anual"] == pytest.approx(kwh_esperado, rel=0.01)
        assert r["pct_horas_con_recorte"] == pytest.approx(100.0)
        assert r["energia_perdida_por_recorte_kwh"] > 0

    def test_energia_perdida_es_la_diferencia_real(self):
        df = _clima_horas_fijas([12.0] * 24)
        tope_w = 1000.0

        sin_tope = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03)
        con_tope = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03,
                            capacidad_electronica_w=tope_w)

        diferencia = sin_tope["kwh_anual"] - con_tope["kwh_anual"]
        assert con_tope["energia_perdida_por_recorte_kwh"] == pytest.approx(diferencia, rel=0.01)

    def test_viento_bajo_cutin_no_activa_recorte_igual(self):
        """Con viento flojo (P real ya está bajo el tope), el recorte no debería
        activarse -- el resultado debe ser igual con o sin tope."""
        df = _clima_horas_fijas([2.0] * 24)  # viento chico, P << 1000W para three_m_tulip
        sin_tope = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03)
        con_tope = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03,
                            capacidad_electronica_w=1000.0)

        assert con_tope["kwh_anual"] == pytest.approx(sin_tope["kwh_anual"])
        assert con_tope["pct_horas_con_recorte"] == 0.0
        assert con_tope["energia_perdida_por_recorte_kwh"] == pytest.approx(0.0, abs=1e-6)

    def test_recorte_es_por_turbina_y_crece_con_el_efecto_bouquet(self):
        """El tope es POR TURBINA (confirmado con Flower Turbines): en un clúster,
        kwh_anual SIEMPRE es N x (lo que entrega una turbina, ya recortada). Pero la
        potencia SIN recortar de cada turbina también crece con N (Efecto Bouquet,
        power_in_bouquet ya lo aplica) -- así que la pérdida por recorte, por turbina,
        es MAYOR en un clúster grande que en una turbina aislada con el mismo tope."""
        df = _clima_horas_fijas([12.0] * 24)
        tope_w = 1000.0

        r_n1 = simular(df, altura_buje=10, modelo="three_m_tulip", N=1, z0=0.03, z0_met=0.03,
                        capacidad_electronica_w=tope_w)
        r_n5 = simular(df, altura_buje=10, modelo="three_m_tulip", N=5, z0=0.03, z0_met=0.03,
                        capacidad_electronica_w=tope_w)

        # kwh_anual = N x (tope, ya que a 12 m/s ambos casos recortan el 100% de las
        # horas) -- el TOTAL entregado sí escala linealmente con N, el tope es por turbina.
        kwh_esperado_n1 = tope_w * 24 / 1000.0
        assert r_n1["kwh_anual"] == pytest.approx(kwh_esperado_n1, rel=0.01)
        assert r_n5["kwh_anual"] == pytest.approx(kwh_esperado_n1 * 5, rel=0.01)

        # La pérdida por recorte NO escala 5x parejo -- el Efecto Bouquet ya sube la
        # potencia SIN recortar de cada turbina al crecer N, así que hay más para
        # recortar por turbina en el clúster de 5 que en la turbina aislada.
        perdida_por_turbina_n1 = r_n1["energia_perdida_por_recorte_kwh"] / 1
        perdida_por_turbina_n5 = r_n5["energia_perdida_por_recorte_kwh"] / 5
        assert perdida_por_turbina_n5 > perdida_por_turbina_n1
