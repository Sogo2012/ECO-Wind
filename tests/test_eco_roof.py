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

from engine.eco_roof_catalog import (
    ALTURA_BUJE_ECO_ROOF_M, ECO_ROOF_PRESETS, PRESET_POR_MODELO, articulo_incluye_solar,
    es_modelo_eco_roof, preset_disponible,
)
from engine.eco_roof_curves import TABLA_N3, TABLA_N5, potencia_tabla_w
from engine.eco_roof_simulador import (
    PresetSinTablaOficialError, simular_cluster_eco_roof, simular_eco_roof,
)
from engine.precios_flower_turbines import get_articulos_disponibles
from engine.simulador_pista_a import Z0_DEFAULT, Z0_MET_DEFAULT, simular, wind_at_height
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


class TestValidacionCapacidadKwp:
    """capacidad_kwp<=0 se rechaza ANTES de tocar geometría/EnergyPlus -- sin esto, un
    valor negativo hace area_m2 negativa y area_m2**0.5 se vuelve un número complejo
    (Python no lanza ValueError ahí), que después revienta con un TypeError confuso
    adentro de ladybug_geometry en vez de decir claramente cuál es el problema real. No
    necesita EnergyPlus instalado -- la validación ocurre antes de cualquier subprocess."""

    @staticmethod
    def _df_y_ruta():
        ruta = SITIOS_EPW_REAL["san_jose"]["ruta_epw"]
        df_clima, _meta = cargar_epw_real(ruta)
        return df_clima, ruta

    def test_capacidad_negativa_da_value_error_claro(self):
        df_clima, ruta = self._df_y_ruta()
        with pytest.raises(ValueError, match="capacidad_kwp"):
            simular_solar_eco_roof(df_clima, ruta, capacidad_kwp=-0.2)

    def test_capacidad_cero_da_value_error_claro(self):
        df_clima, ruta = self._df_y_ruta()
        with pytest.raises(ValueError, match="capacidad_kwp"):
            simular_solar_eco_roof(df_clima, ruta, capacidad_kwp=0.0)


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

    def test_epw_corrupto_el_error_trae_la_causa_real_no_generica(self, tmp_path):
        """Una corrida real que SÍ falla adentro de EnergyPlus (EPW con encabezado pero
        sin ninguna fila de datos horaria) -- el RuntimeError debe traer el detalle real
        de eplusout.err (la causa concreta que EnergyPlus imprime ahí), no sólo el texto
        genérico de "EnergyPlus terminó con error". Antes de la corrección, eplusout.err
        nunca se leía y se perdía apenas el TemporaryDirectory se borraba."""
        ruta_real = SITIOS_EPW_REAL["san_jose"]["ruta_epw"]
        df_clima, _meta = cargar_epw_real(ruta_real)

        with open(ruta_real, encoding="latin-1") as f:
            encabezado = [next(f) for _ in range(8)]
        ruta_corrupta = tmp_path / "sin_datos.epw"
        ruta_corrupta.write_text("".join(encabezado), encoding="latin-1")

        with pytest.raises(RuntimeError) as exc_info:
            simular_solar_eco_roof(df_clima, str(ruta_corrupta), capacidad_kwp=0.2)
        mensaje = str(exc_info.value)
        assert "eplusout.err" in mensaje
        # No es sólo el texto genérico de "el proceso terminó con error" -- tiene que
        # incluir algo del detalle real que EnergyPlus imprime en eplusout.err.
        assert "Severe" in mensaje or "Fatal" in mensaje


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


_ART_FLAT3_CON_SOLAR = "ecoroof with 3 1-meter turbines on grid with inverter plus solar panels"
# Ya no existe como artículo real del catálogo (ver test_todos_los_articulos_incluyen_solar) --
# se usa acá solo como texto sintético para probar que articulo_incluye_solar()/
# simular_cluster_eco_roof() siguen tratando correctamente cualquier texto sin "solar",
# por si algún día se reintroduce una variante sin paneles en el catálogo.
_ART_FLAT3_SIN_SOLAR = "ecoroof with 3 1-meter turbines on grid with inverter"


class TestCarteraEcoRoof:
    """Eco-Roof como producto más de la cartera (selector "Modelo") -- puro catálogo,
    no necesita EnergyPlus."""

    def test_mapa_modelo_a_preset(self):
        assert PRESET_POR_MODELO == {
            "ecoroof_flat_3": "eco_roof_1m_3_flat",
            "ecoroof_flat_5": "eco_roof_1m_5_flat",
            "ecoroof_slanted": "eco_roof_1m_3_sloped",
        }

    def test_eco_roof_2m_2_no_entra_a_la_cartera(self):
        assert "eco_roof_2m_2" not in PRESET_POR_MODELO.values()

    def test_es_modelo_eco_roof(self):
        assert es_modelo_eco_roof("ecoroof_flat_3")
        assert es_modelo_eco_roof("ecoroof_slanted")
        assert not es_modelo_eco_roof("three_m_tulip")
        assert not es_modelo_eco_roof("small_tulip")

    def test_todos_los_articulos_incluyen_solar(self):
        """El catálogo de precios ya no ofrece la variante Eco-Roof sin paneles -- el
        cliente no puede elegir turbinas solas para este producto, así que
        articulo_incluye_solar() tiene que dar True para los 2 artículos de cada
        modelo (on-grid y off-grid, los dos "plus solar panels")."""
        for modelo in ("ecoroof_flat_3", "ecoroof_flat_5"):
            articulos = [art for art, _ in get_articulos_disponibles(modelo)]
            assert len(articulos) == 2
            assert all("plus solar panels" in art for art in articulos)
            assert all(articulo_incluye_solar(art) for art in articulos)
        assert not articulo_incluye_solar(None)
        assert not articulo_incluye_solar("")


class TestSimularClusterEcoRoofSinPaneles:
    """Fila Eco-Roof con un artículo SIN paneles: no corre EnergyPlus (ruta_epw nunca
    se usa), así que alcanza con un clima sintético -- pruebas rápidas del formato y de
    la escala por cantidad de equipos."""

    @staticmethod
    def _fila(N_equipos, df=None, articulo=_ART_FLAT3_SIN_SOLAR, modelo="ecoroof_flat_3"):
        df = df if df is not None else _clima_horas_fijas([8.0] * 48)
        return simular_cluster_eco_roof(modelo, N_equipos, df, ruta_epw="", elevacion_m=0.0,
                                        articulo=articulo)

    def test_mismas_claves_que_simular(self):
        df = _clima_horas_fijas([8.0] * 48)
        referencia = simular(df, altura_buje=3.0, modelo="three_m_tulip", N=3)
        assert set(referencia) <= set(self._fila(1, df))

    def test_n_es_cantidad_de_equipos(self):
        uno, cuatro = self._fila(1), self._fila(4)
        assert cuatro["kwh_anual"] == pytest.approx(uno["kwh_anual"] * 4)
        assert cuatro["turbinas_por_equipo"] == 3

    def test_eolica_igual_a_un_equipo_del_motor_eco_roof(self):
        """La fila con N equipos = N × la producción de un equipo que ya calcula
        simular_eco_roof() (tabla oficial, sin multiplicador Bouquet)."""
        df = _clima_horas_fijas([8.0] * 48)
        un_equipo = simular_eco_roof("eco_roof_1m_3_flat", df, ruta_epw="", elevacion_m=0.0,
                                     incluir_solar=False)
        fila = self._fila(3, df)
        assert fila["kwh_anual_eolico"] == pytest.approx(un_equipo["kwh_anual_eolico"] * 3)

    def test_sin_paneles_no_hay_solar_ni_recorte(self):
        fila = self._fila(2)
        assert not fila["incluye_solar"]
        assert fila["kwh_anual_solar"] == 0.0
        assert fila["kwh_anual"] == pytest.approx(fila["kwh_anual_eolico"])
        assert (fila["serie_horaria_kwh_solar"] == 0.0).all()
        assert fila["energia_perdida_por_recorte_kwh"] == 0.0
        assert fila["capacidad_electronica_w"] is None

    def test_serie_por_equipo_por_n_suma_la_eolica(self):
        """El resto de la app arma el total horario como serie_horaria_W_por_turbina × N
        -- con N = equipos tiene que dar exacto la eólica del clúster."""
        fila = self._fila(5)
        assert (fila["serie_horaria_W_por_turbina"] * 5 / 1000.0).sum() == pytest.approx(
            fila["kwh_anual_eolico"])
        assert fila["kwh_mensual"].sum() == pytest.approx(fila["kwh_anual"])

    def test_buje_es_altura_del_techo_mas_la_del_equipo(self):
        """El viento se lleva a (techo + 1.149 m) sobre el terreno, con el mismo perfil
        logarítmico que el resto de las turbinas."""
        df = _clima_horas_fijas([5.0] * 48)
        fila = simular_cluster_eco_roof("ecoroof_flat_3", 1, df, ruta_epw="", elevacion_m=0.0,
                                        articulo=None, altura_techo_m=10.0)
        esperado = wind_at_height(df["WS10M"].values, 10, 10.0 + ALTURA_BUJE_ECO_ROOF_M,
                                  z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT)
        np.testing.assert_allclose(fila["v_hub"], esperado)

    def test_techo_mas_alto_da_mas_eolico(self):
        df = _clima_horas_fijas([5.0] * 48)
        kwh = [simular_cluster_eco_roof("ecoroof_flat_3", 1, df, ruta_epw="", elevacion_m=0.0,
                                        articulo=None, altura_techo_m=h)["kwh_anual"]
               for h in (0.0, 5.0, 10.0, 20.0)]
        assert kwh == sorted(kwh)
        assert kwh[0] < kwh[-1]

    def test_flat_5_usa_tabla_n5(self):
        df = _clima_horas_fijas([8.0] * 48)
        fila = simular_cluster_eco_roof("ecoroof_flat_5", 1, df, ruta_epw="", elevacion_m=0.0,
                                        articulo=None)
        un_equipo = simular_eco_roof("eco_roof_1m_5_flat", df, ruta_epw="", elevacion_m=0.0,
                                     incluir_solar=False)
        assert fila["turbinas_por_equipo"] == 5
        assert fila["kwh_anual"] == pytest.approx(un_equipo["kwh_anual_eolico"])


@_requiere_energyplus
class TestSimularClusterEcoRoofConPaneles:
    """Artículo "plus solar panels": la solar (EnergyPlus real) se suma a la fila."""

    @staticmethod
    @pytest.fixture(scope="class")
    def filas_sj():
        ruta = SITIOS_EPW_REAL["san_jose"]["ruta_epw"]
        df_clima, meta = cargar_epw_real(ruta)
        uno = simular_cluster_eco_roof("ecoroof_flat_3", 1, df_clima, ruta, meta["elevacion_m"],
                                       _ART_FLAT3_CON_SOLAR)
        tres = simular_cluster_eco_roof("ecoroof_flat_3", 3, df_clima, ruta, meta["elevacion_m"],
                                        _ART_FLAT3_CON_SOLAR)
        return uno, tres

    def test_total_es_eolica_mas_solar(self, filas_sj):
        uno, _tres = filas_sj
        assert uno["incluye_solar"]
        assert uno["kwh_anual_solar"] > 0
        assert uno["kwh_anual"] == pytest.approx(uno["kwh_anual_eolico"] + uno["kwh_anual_solar"])
        assert uno["serie_horaria_kwh_solar"].sum() == pytest.approx(uno["kwh_anual_solar"])

    def test_solar_escala_con_la_cantidad_de_equipos(self, filas_sj):
        uno, tres = filas_sj
        assert tres["kwh_anual_solar"] == pytest.approx(uno["kwh_anual_solar"] * 3)
        assert tres["kwh_anual"] == pytest.approx(uno["kwh_anual"] * 3)


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
