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
import numpy as np
import pandas as pd

from engine.atmosfera_estandar import factor_correccion_densidad
from engine.eco_roof_catalog import (
    ECO_ROOF_PRESETS, PRESET_POR_MODELO, articulo_incluye_solar, preset_disponible,
)
from engine.eco_roof_curves import potencia_tabla_w
from engine.eco_roof_solar import simular_solar_eco_roof
from engine.simulador_pista_a import Z0_DEFAULT, Z0_MET_DEFAULT, wind_at_height
from engine.turbine_specs import SPECS_TURBINAS


class PresetSinTablaOficialError(ValueError):
    """Preset Eco-Roof sin tabla de potencia oficial (ej. eco_roof_2m_2) -- nunca
    se calcula ni se devuelve un número de energía para uno de estos, ver
    engine/eco_roof_catalog.py::ECO_ROOF_PRESETS."""


def simular_eco_roof(clave_preset, df_clima, ruta_epw, elevacion_m,
                      h_ref=10, z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT, incluir_solar=True,
                      altura_techo_m=0.0):
    """
    Producción anual (eólica + solar) de UN equipo de un preset fijo del catálogo
    Eco-Roof, hora por hora, contra un df_clima real (el mismo formato que ya usa
    simular() -- columna WS10M, ver engine.epw_real.cargar_epw_real()).

    clave_preset: una clave de ECO_ROOF_PRESETS (ej. "eco_roof_1m_3_flat").
    ruta_epw: ruta al MISMO archivo .epw que produjo df_clima -- lo necesita el
    bloque solar para correr EnergyPlus real (engine/eco_roof_solar.py); el
    bloque eólico no lo usa, sólo df_clima.
    elevacion_m: del EPW real del sitio (meta["elevacion_m"] de
    cargar_epw_real()) -- corrección de densidad de aire del bloque eólico.
    h_ref, z0, z0_met: mismo significado que en simular() (Pista A) -- alturas
    y rugosidades del perfil logarítmico de viento.
    incluir_solar: False cuando el artículo elegido no trae paneles solares --
    no se corre EnergyPlus y la producción solar es 0.
    altura_techo_m: altura del techo sobre el terreno donde se instala el equipo.
    El buje queda a altura_techo_m + la altura propia del producto
    (preset["altura_buje_m"], 1.149 m) y a ESA altura se lleva el viento de
    referencia con el perfil logarítmico -- aproximación de primer orden: no
    modela la aceleración ni la turbulencia del flujo sobre el borde del edificio.

    Devuelve dict con el desglose eólico, el desglose solar (de
    simular_solar_eco_roof(), con su propia advertencia de "estimado"; None si
    incluir_solar=False), y el total combinado.

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
    altura_buje_m = altura_techo_m + preset["altura_buje_m"]
    v_hub = wind_at_height(df_clima["WS10M"].values, h_ref, altura_buje_m, z0=z0, z0_met=z0_met)
    factor_densidad = factor_correccion_densidad(elevacion_m)
    potencia_w_por_turbina = potencia_tabla_w(v_hub, preset["tabla_potencia"]) * factor_densidad

    N = preset["N"]
    serie_kwh_eolico = pd.Series(potencia_w_por_turbina * N / 1000.0, index=df_clima.index,
                                  name="kwh_eolico")

    # --- Solar (ver engine/eco_roof_solar.py -- EnergyPlus real, panel genérico) ---
    resultado_solar = None
    kwh_anual_solar = 0.0
    if incluir_solar:
        resultado_solar = simular_solar_eco_roof(
            df_clima, ruta_epw, preset["capacidad_solar_kwp"],
            tilt_deg=preset["tilt_deg"], acimut_superficie_deg=preset["acimut_superficie_deg"],
        )
        kwh_anual_solar = resultado_solar["kwh_anual"]

    kwh_anual_eolico = float(serie_kwh_eolico.sum())
    return {
        "preset": clave_preset, "N": N, "v_hub": v_hub,
        "serie_horaria_kwh_eolico": serie_kwh_eolico,
        "kwh_anual_eolico": kwh_anual_eolico,
        "kwh_mensual_eolico": serie_kwh_eolico.resample("MS").sum(),
        "factor_correccion_densidad": factor_densidad,
        "v_hub_medio": float(v_hub.mean()),
        "solar": resultado_solar,
        "kwh_anual_solar": kwh_anual_solar,
        "kwh_anual_total": kwh_anual_eolico + kwh_anual_solar,
    }


def simular_cluster_eco_roof(modelo, N_equipos, df_clima, ruta_epw, elevacion_m, articulo,
                              h_ref=10, z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT, altura_techo_m=0.0):
    """
    Una fila Eco-Roof del proyecto ("Equipos y configuración"), devuelta con el MISMO
    formato de dict que simulador_pista_a.simular() -- así Resultados, Análisis
    Financiero, Especificación Técnica y el informe PDF la tratan como a cualquier otro
    producto de la cartera, sin tocar simular() ni el motor de curvas del 3-M Tulip.

    modelo: clave de la cartera ("ecoroof_flat_3", "ecoroof_flat_5", "ecoroof_slanted").
    N_equipos: cantidad de EQUIPOS Eco-Roof de la fila, no de turbinas -- cada equipo ya
    trae su bouquet fijo de fábrica (3 o 5 turbinas) y se cotiza por unidad en el
    catálogo de precios (precio × N).
    articulo: el artículo elegido del catálogo -- la producción solar sólo se suma si
    el artículo trae paneles ("... plus solar panels", ver articulo_incluye_solar()).
    altura_techo_m: altura del techo sobre el terreno -- el buje queda a esta altura +
    1.149 m (ver simular_eco_roof()).

    Diferencias de significado respecto a simular(), a propósito:
    - "serie_horaria_W_por_turbina" es la potencia eólica de UN EQUIPO completo (todas
      sus turbinas) -- el resto de la app la multiplica por N, que acá son equipos, y
      el total queda bien. Es sólo eólica: la usan la curva de duración y el desglose
      por velocidad de viento, que no tienen sentido para la parte solar.
    - "kwh_anual"/"kwh_mensual" SÍ incluyen la solar (energía total que entrega la
      fila). La solar hora por hora del clúster va aparte, en "serie_horaria_kwh_solar",
      para que la tarifa horaria del Análisis Financiero también la cuente.
    - Sin recorte por electrónica: no hay dato de capacidad de controlador para los
      artículos Eco-Roof, y la tabla oficial ya es la potencia que entrega el producto
      -- recortarla con la "potencia nominal" de la ficha sería repetir justamente la
      confusión del business case de CNFL.
    """
    clave_preset = PRESET_POR_MODELO[modelo]
    preset = ECO_ROOF_PRESETS[clave_preset]
    incluye_solar = articulo_incluye_solar(articulo)
    r = simular_eco_roof(clave_preset, df_clima, ruta_epw, elevacion_m, h_ref=h_ref, z0=z0,
                         z0_met=z0_met, incluir_solar=incluye_solar, altura_techo_m=altura_techo_m)

    serie_w_por_equipo = r["serie_horaria_kwh_eolico"] * 1000.0
    serie_kwh_solar_cluster = (r["solar"]["serie_horaria_kwh"] * N_equipos if incluye_solar
                               else pd.Series(0.0, index=df_clima.index))
    energia_cluster_kwh = r["serie_horaria_kwh_eolico"] * N_equipos + serie_kwh_solar_cluster
    v_cutin = SPECS_TURBINAS[preset["turbina_key"]]["velocidad_cutin_ms"]

    return {
        "serie_horaria_W_por_turbina": serie_w_por_equipo.rename("W_por_equipo"),
        "serie_horaria_kwh_perdido_por_turbina": pd.Series(0.0, index=df_clima.index),
        "v_hub": r["v_hub"],
        "kwh_mensual": energia_cluster_kwh.resample("MS").sum(),
        "kwh_anual": float(energia_cluster_kwh.sum()),
        "v_hub_medio": r["v_hub_medio"],
        "pct_horas_bajo_cutin": float(np.mean(r["v_hub"] < v_cutin) * 100),
        "factor_correccion_densidad": float(r["factor_correccion_densidad"]),
        "elevacion_m": float(elevacion_m),
        "capacidad_electronica_w": None,
        "energia_perdida_por_recorte_kwh": 0.0,
        "pct_horas_con_recorte": 0.0,
        "es_eco_roof": True,
        "preset": clave_preset,
        "turbinas_por_equipo": preset["N"],
        "incluye_solar": incluye_solar,
        "kwh_anual_eolico": r["kwh_anual_eolico"] * N_equipos,
        "kwh_anual_solar": r["kwh_anual_solar"] * N_equipos,
        "serie_horaria_kwh_solar": serie_kwh_solar_cluster,
    }
