#!/usr/bin/env python3
"""
Tarifa horaria real de Costa Rica (T-REH/T-RH/T-MT, Hallazgo 54) -- confirma que el
ahorro valora cada kWh generado al precio del periodo (Punta/Valle/Nocturno) en el
que REALMENTE se genera, no un promedio ni una tarifa plana. Motivado por la
pregunta directa del cliente: si el sistema genera de madrugada vs. al mediodía,
¿el kWh pesa distinto en el ahorro? Este archivo no existía -- este módulo mueve
directamente el ahorro anual (payback/ROI/NPV en la app), así que queda cubierto.
"""
import pandas as pd
import pytest

from engine.tarifas_electricas_cr import (
    PERIODOS_HORARIOS_CR, calcular_ahorro_tarifa_horaria_usd, clasificar_periodo,
)

PROV, TARIFA = "CNFL", "T-REH (0-500 kWh)"


class TestClasificarPeriodoFronteras:
    """clasificar_periodo() en cada frontera de PERIODOS_HORARIOS_CR (lunes
    2023-01-02, un día laboral) -- ver el docstring del módulo para la regla de
    "mayoría de la hora" en los bordes que no caen en una hora en punto (12:30, 17:30)."""

    @pytest.mark.parametrize("hora,esperado", [
        (5, "Nocturno"),    # madrugada
        (6, "Valle"),       # 06:00, arranca Valle
        (9, "Valle"),       # justo antes de Punta
        (10, "Punta"),      # 10:00, arranca Punta
        (12, "Punta"),      # 12:00-13:00: mayoría (30 de 60 min) es Punta (termina 12:30)
        (13, "Valle"),      # ya pasó 12:30
        (17, "Valle"),      # justo antes del segundo bloque Punta
        (18, "Punta"),      # 17:30-20:00
        (19, "Punta"),
        (20, "Nocturno"),   # 20:00, arranca Nocturno
        (23, "Nocturno"),
    ])
    def test_frontera_dia_laboral(self, hora, esperado):
        ts = pd.Timestamp(f"2023-01-02 {hora:02d}:00")  # lunes
        assert clasificar_periodo(ts, PROV, TARIFA) == esperado

    @pytest.mark.parametrize("hora", [6, 9, 11, 14, 17, 19])
    def test_fin_de_semana_nunca_es_punta(self, hora):
        """Sábado/domingo: todo el bloque 06:00-20:00 es Valle -- las ventanas de
        Punta entre semana (10-12:30, 17:30-20:00) se reclasifican como Valle."""
        sabado = pd.Timestamp(f"2023-01-07 {hora:02d}:00")   # sábado
        domingo = pd.Timestamp(f"2023-01-08 {hora:02d}:00")  # domingo
        assert clasificar_periodo(sabado, PROV, TARIFA) == "Valle"
        assert clasificar_periodo(domingo, PROV, TARIFA) == "Valle"

    def test_nocturno_cruza_medianoche_todos_los_dias(self):
        """20:00-06:00 no distingue día laboral/fin de semana."""
        for fecha in ("2023-01-02", "2023-01-07", "2023-01-08"):  # lunes, sábado, domingo
            assert clasificar_periodo(pd.Timestamp(f"{fecha} 22:00"), PROV, TARIFA) == "Nocturno"
            assert clasificar_periodo(pd.Timestamp(f"{fecha} 02:00"), PROV, TARIFA) == "Nocturno"

    def test_las_3_tarifas_conectadas_cubren_las_24_horas_sin_hueco(self):
        """Guarda estructural: para cada tarifa horaria SÍ conectada, las 24 horas de
        un día laboral Y de un día de fin de semana caen en alguna regla -- si faltara
        un tramo, clasificar_periodo() lanzaría RuntimeError (ver su docstring)."""
        for proveedor, tarifa in PERIODOS_HORARIOS_CR:
            for fecha in ("2023-01-02", "2023-01-07"):  # lunes, sábado
                for hora in range(24):
                    clasificar_periodo(pd.Timestamp(f"{fecha} {hora:02d}:00"), proveedor, tarifa)


class TestAhorroPonderaPorHoraReal:
    """El caso que importa: la MISMA cantidad de kWh vale distinto según a qué hora
    se generó -- eso es lo que hace que el ahorro no sea sólo kwh_anual × precio_plano."""

    def test_produccion_de_madrugada_es_100pct_nocturno(self):
        idx = pd.date_range("2023-01-02", periods=24 * 7, freq="h")  # semana completa
        serie = pd.Series(0.0, index=idx)
        serie[idx.hour == 3] = 10.0  # 10 kWh cada 3am, toda la semana
        r = calcular_ahorro_tarifa_horaria_usd(serie, PROV, TARIFA, 500.0)
        assert r["desglose_por_periodo"]["Nocturno"]["kwh"] == pytest.approx(r["kwh_total"])
        assert r["desglose_por_periodo"]["Punta"]["kwh"] == 0.0
        assert r["desglose_por_periodo"]["Valle"]["kwh"] == 0.0

    def test_produccion_de_mediodia_un_lunes_es_100pct_punta(self):
        idx = pd.date_range("2023-01-02", periods=24, freq="h")  # lunes
        serie = pd.Series(0.0, index=idx)
        serie[idx.hour == 11] = 10.0
        r = calcular_ahorro_tarifa_horaria_usd(serie, PROV, TARIFA, 500.0)
        assert r["desglose_por_periodo"]["Punta"]["kwh"] == pytest.approx(10.0)

    def test_misma_hora_en_sabado_no_es_punta(self):
        """La MISMA hora del día (11am) vale distinto según el día de la semana."""
        idx = pd.date_range("2023-01-07", periods=24, freq="h")  # sábado
        serie = pd.Series(0.0, index=idx)
        serie[idx.hour == 11] = 10.0
        r = calcular_ahorro_tarifa_horaria_usd(serie, PROV, TARIFA, 500.0)
        assert r["desglose_por_periodo"]["Valle"]["kwh"] == pytest.approx(10.0)
        assert r["desglose_por_periodo"]["Punta"]["kwh"] == 0.0

    def test_dos_perfiles_con_el_mismo_kwh_anual_dan_ahorro_distinto(self):
        """El corazón de la tarifa horaria: mismo total de kWh/año, repartido en horas
        distintas -> ahorro distinto. Si el ahorro sólo mirara el total anual (tarifa
        plana), esto daría el mismo resultado en los dos casos."""
        idx = pd.date_range("2023-01-02", periods=24, freq="h")  # lunes
        kwh_dia = 50.0

        perfil_nocturno = pd.Series(0.0, index=idx)
        perfil_nocturno[idx.hour == 2] = kwh_dia  # toda la producción de madrugada

        perfil_punta = pd.Series(0.0, index=idx)
        perfil_punta[idx.hour == 11] = kwh_dia  # toda la producción a media mañana (Punta)

        r_noct = calcular_ahorro_tarifa_horaria_usd(perfil_nocturno, PROV, TARIFA, 500.0)
        r_punta = calcular_ahorro_tarifa_horaria_usd(perfil_punta, PROV, TARIFA, 500.0)

        assert r_noct["kwh_total"] == pytest.approx(r_punta["kwh_total"])  # mismo total
        # Punta (134.62 ¢/kWh) vs. Nocturno (23.10 ¢/kWh): la misma energía vale ~5.8x más
        # generada a media mañana que de madrugada.
        assert r_punta["ahorro_anual_usd"] > r_noct["ahorro_anual_usd"] * 5

    def test_curva_solar_tipica_se_reparte_entre_punta_y_valle(self):
        """Producción concentrada 9am-3pm un día laboral (perfil solar típico): cae
        parte en Punta (10-12:30) y parte en Valle (resto), no toda en un solo periodo
        -- confirma que se clasifica hora por hora, no con un solo periodo "del día"."""
        idx = pd.date_range("2023-01-04", periods=24, freq="h")  # miércoles
        serie = pd.Series(0.0, index=idx)
        curva = {9: 2.0, 10: 5.0, 11: 8.0, 12: 9.0, 13: 8.0, 14: 5.0, 15: 2.0}
        for hora, kwh in curva.items():
            serie[idx.hour == hora] = kwh
        r = calcular_ahorro_tarifa_horaria_usd(serie, PROV, TARIFA, 500.0)
        # Punta = horas 10,11,12 (5+8+9); Valle = horas 9,13,14,15 (2+8+5+2).
        assert r["desglose_por_periodo"]["Punta"]["kwh"] == pytest.approx(22.0)
        assert r["desglose_por_periodo"]["Valle"]["kwh"] == pytest.approx(17.0)
        assert r["desglose_por_periodo"]["Nocturno"]["kwh"] == 0.0
        assert r["kwh_total"] == pytest.approx(sum(curva.values()))

    def test_cada_periodo_se_valora_a_su_propio_precio_no_un_promedio(self):
        idx = pd.date_range("2023-01-02", periods=24, freq="h")  # lunes
        serie = pd.Series(0.0, index=idx)
        serie[idx.hour == 11] = 10.0   # Punta
        serie[idx.hour == 8] = 10.0    # Valle
        serie[idx.hour == 2] = 10.0    # Nocturno
        r = calcular_ahorro_tarifa_horaria_usd(serie, PROV, TARIFA, 500.0)
        precios = {"Punta": 134.62, "Valle": 55.19, "Nocturno": 23.10}
        esperado_crc = sum(10.0 * precios[p] for p in precios)
        assert r["ahorro_anual_crc"] == pytest.approx(esperado_crc)
        # abs=0.01: calcular_ahorro_tarifa_horaria_usd() redondea a 2 decimales.
        assert r["ahorro_anual_usd"] == pytest.approx(esperado_crc / 500.0, abs=0.01)
        for periodo, precio in precios.items():
            assert r["desglose_por_periodo"][periodo]["precio_crc_kwh"] == precio
            assert r["desglose_por_periodo"][periodo]["crc"] == pytest.approx(10.0 * precio)

    def test_tipo_cambio_invalido_falla_explicito(self):
        idx = pd.date_range("2023-01-02", periods=24, freq="h")
        serie = pd.Series(1.0, index=idx)
        with pytest.raises(ValueError, match="tipo de cambio"):
            calcular_ahorro_tarifa_horaria_usd(serie, PROV, TARIFA, 0.0)

    def test_desglose_suma_al_total(self):
        idx = pd.date_range("2023-01-01", periods=24 * 30, freq="h")
        serie = pd.Series(1.0, index=idx)  # 1 kWh cada hora, mes completo
        r = calcular_ahorro_tarifa_horaria_usd(serie, PROV, TARIFA, 500.0)
        suma_kwh = sum(v["kwh"] for v in r["desglose_por_periodo"].values())
        suma_usd = sum(v["usd"] for v in r["desglose_por_periodo"].values())
        assert suma_kwh == pytest.approx(r["kwh_total"], abs=0.2)  # abs: redondeo a 1 decimal
        assert suma_usd == pytest.approx(r["ahorro_anual_usd"], abs=0.2)


class TestTarifaHorariaICE:
    """Mismo mecanismo con el proveedor ICE (T-RH) -- confirma que no quedó
    hardcodeado a CNFL."""

    def test_ice_t_rh_tambien_pondera_por_periodo_real(self):
        idx = pd.date_range("2023-01-02", periods=24, freq="h")  # lunes
        serie = pd.Series(0.0, index=idx)
        serie[idx.hour == 11] = 10.0  # Punta
        r = calcular_ahorro_tarifa_horaria_usd(serie, "ICE", "T-RH", 500.0)
        assert r["desglose_por_periodo"]["Punta"]["kwh"] == pytest.approx(10.0)
        assert r["desglose_por_periodo"]["Punta"]["precio_crc_kwh"] == 129.80
