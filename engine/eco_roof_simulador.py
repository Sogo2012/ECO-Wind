"""
Orquestador del Eco-Roof Energy Hub (eólico tabla-a-tabla + solar) -- Pista
Eco-Roof, módulo nuevo y separado del motor de 3-M Tulip
(engine/simulador_pista_a.py, que NO se toca ni se importa su función
`simular()` desde acá).

Reutiliza, sin modificarlos, dos piezas de física que SÍ son genéricas (no
dependen del modelo de turbina):
  - `wind_at_height()` (engine/simulador_pista_a.py): perfil logarítmico de
    viento por altura -- misma corrección que usa el motor de 3-M Tulip.
  - `factor_correccion_densidad()` (engine/atmosfera_estandar.py): corrección
    de densidad de aire por elevación -- las tablas oficiales del Eco-Roof,
    igual que la curva de 3-M Tulip, están calibradas a nivel del mar.

Lo que NO reutiliza, a propósito: `power_in_bouquet()`/`CURVE_COEFFICIENTS`
(engine/flower_turbines_curves.py) -- el multiplicador de Efecto Bouquet
`M(N) = e^(0.21103×(N-1))` ahí es propio de la línea 2M/3M/6M, no de la Small
Tulip. Acá la potencia por turbina sale de interpolar la tabla oficial
(engine/eco_roof_curves.py), N ya viene implícito en cuál tabla se usa.
"""
import pandas as pd

from engine.atmosfera_estandar import factor_correccion_densidad
from engine.eco_roof_catalog import ECO_ROOF_PRESETS, preset_disponible
from engine.eco_roof_curves import potencia_tabla_w
from engine.eco_roof_solar import simular_solar_eco_roof
from engine.simulador_pista_a import Z0_DEFAULT, Z0_MET_DEFAULT, wind_at_height


class PresetSinTablaOficialError(ValueError):
    """Preset Eco-Roof sin tabla de potencia oficial (ej. eco_roof_2m_2) -- nunca
    se calcula ni se devuelve un número de energía para uno de estos, ver
    engine/eco_roof_catalog.py::ECO_ROOF_PRESETS."""


def simular_eco_roof(clave_preset, df_clima, ruta_epw, elevacion_m,
                      h_ref=10, z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT):
    """
    Producción anual (eólica + solar) de un preset fijo del catálogo Eco-Roof,
    hora por hora, contra un df_clima real (el mismo formato que ya usa
    simular() -- columna WS10M, ver engine.epw_real.cargar_epw_real()).

    clave_preset: una clave de ECO_ROOF_PRESETS (ej. "eco_roof_1m_3_flat").
    ruta_epw: ruta al MISMO archivo .epw que produjo df_clima -- lo necesita el
    bloque solar para correr EnergyPlus real (engine/eco_roof_solar.py); el
    bloque eólico no lo usa, sólo df_clima.
    elevacion_m: del EPW real del sitio (meta["elevacion_m"] de
    cargar_epw_real()) -- corrección de densidad de aire del bloque eólico.
    h_ref, z0, z0_met: mismo significado que en simular() (Pista A) -- alturas
    y rugosidades del perfil logarítmico de viento.

    Devuelve dict con el desglose eólico, el desglose solar (de
    simular_solar_eco_roof(), con su propia advertencia de "estimado"), y el
    total combinado.

    Lanza PresetSinTablaOficialError si el preset no tiene tabla de potencia
    oficial (status != "ok" en ECO_ROOF_PRESETS) -- nunca calcula ni devuelve
    energía "aproximada" para esos casos.
    """
    preset = ECO_ROOF_PRESETS.get(clave_preset)
    if preset is None:
        raise KeyError(f"Preset Eco-Roof desconocido: {clave_preset!r}")
    if not preset_disponible(clave_preset):
        raise PresetSinTablaOficialError(
            f"{clave_preset!r} no tiene tabla de potencia oficial todavía "
            f"(status={preset['status']!r}) -- no se genera un número de energía sin esa "
            "tabla real (ver ECO_ROOF_PRESETS en engine/eco_roof_catalog.py)."
        )

    # --- Eólico: interpolación de tabla oficial (ver eco_roof_curves.py) ---
    v_hub = wind_at_height(df_clima["WS10M"].values, h_ref, preset["altura_buje_m"],
                            z0=z0, z0_met=z0_met)
    factor_densidad = factor_correccion_densidad(elevacion_m)
    potencia_w_por_turbina = potencia_tabla_w(v_hub, preset["tabla_potencia"]) * factor_densidad

    N = preset["N"]
    serie_kwh_eolico = pd.Series(potencia_w_por_turbina * N / 1000.0, index=df_clima.index,
                                  name="kwh_eolico")

    # --- Solar (ver engine/eco_roof_solar.py -- EnergyPlus real, panel genérico) ---
    resultado_solar = simular_solar_eco_roof(
        df_clima, ruta_epw, preset["capacidad_solar_kwp"],
        tilt_deg=preset["tilt_deg"], acimut_superficie_deg=preset["acimut_superficie_deg"],
    )

    kwh_anual_eolico = float(serie_kwh_eolico.sum())
    return {
        "preset": clave_preset, "N": N, "v_hub": v_hub,
        "serie_horaria_kwh_eolico": serie_kwh_eolico,
        "kwh_anual_eolico": kwh_anual_eolico,
        "kwh_mensual_eolico": serie_kwh_eolico.resample("MS").sum(),
        "factor_correccion_densidad": factor_densidad,
        "v_hub_medio": float(v_hub.mean()),
        "solar": resultado_solar,
        "kwh_anual_solar": resultado_solar["kwh_anual"],
        "kwh_anual_total": kwh_anual_eolico + resultado_solar["kwh_anual"],
    }
