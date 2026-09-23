"""
Bloque solar del Eco-Roof Energy Hub -- Pista Eco-Roof, módulo nuevo y separado.

NO HAY, en este repo, un motor de producción solar horaria ya construido para
reutilizar (se buscó explícitamente en engine/ y en todo el historial de git --
lo único relacionado con "solar" es solark_specs.py, que es la ficha del
INVERSOR Sol-Ark, no un cálculo de producción de paneles). Decisión tomada con
Pablo: en vez de inventar una ficha de panel específica (que el prompt original
pedía explícitamente NO hacer), se implementa acá la física que ya usa
EnergyPlus para este caso -- el archivo EPW que ya carga toda la app ES un
archivo de EnergyPlus, con GHI/DNI/DHI reales hora por hora.

Dos piezas, ambas EXACTAMENTE como las documenta el "EnergyPlus Engineering
Reference" (no una aproximación propia):

1. Posición solar (declinación + ecuación del tiempo): serie de Fourier de
   Spencer (1971), la misma que EnergyPlus usa internamente
   (WeatherManager::CalcSolarPosition/SolarShading).
2. Potencia del generador FV: modelo "PhotovoltaicPerformance:Simple" de
   EnergyPlus -- P = Irradiancia_POA × Área_equivalente × eficiencia, sin
   modelo térmico de celda (ese requeriría datasheet real del panel, que no
   tenemos -- EnergyPlus mismo recomienda "Simple" quirúrgicamente para este
   caso, cuando no hay ficha detallada). Expresado en términos de capacidad
   nominal (kWp) en vez de área×eficiencia por separado, para no inventar un
   área de panel que tampoco tenemos:

        P_dc(t) = capacidad_kwp × (POA(t) / 1000 W/m²) × derate

   `derate` agrupa pérdidas típicas de sistema (cableado, inversor, suciedad,
   temperatura promedio) en un solo factor genérico -- NO es una ficha de
   panel, es un performance ratio de industria (~0.80, PVWatts default de
   referencia). Ver DERATE_GENERICO más abajo.

MARCADO EXPLÍCITAMENTE COMO ESTIMADO (punto 4/7 del prompt original): sin una
ficha de panel Eco-Roof real, cualquier resultado de este módulo es una
aproximación de orden de magnitud, no una cotización -- ver
`ADVERTENCIA_ESTIMADO` y cómo se usa en el informe (engine/pdf_reporte.py).
"""
import numpy as np
import pandas as pd

DERATE_GENERICO = 0.80  # performance ratio genérico de industria (PVWatts default
                         # de referencia: ~14% pérdidas de sistema + efecto térmico
                         # promedio) -- NO viene de una ficha de panel Eco-Roof real.
ALBEDO_GENERICO = 0.20   # reflectancia de suelo/techo genérica (pasto/concreto claro)

ADVERTENCIA_ESTIMADO = (
    "Producción solar ESTIMADA -- modelo genérico (EnergyPlus "
    "PhotovoltaicPerformance:Simple, sin ficha de panel Eco-Roof específica). "
    "No usar como cotización firme."
)


def posicion_solar(indice_horario, lat_deg, lon_deg, utc_offset_h):
    """
    Declinación y ángulo horario, hora por hora, con las mismas fórmulas que
    EnergyPlus (serie de Fourier de Spencer 1971) -- ver docstring del módulo.

    indice_horario: DatetimeIndex (el mismo índice horario de df_clima, ya en
    hora LOCAL ESTÁNDAR del sitio -- así vienen los EPW, sin horario de verano).
    lat_deg, lon_deg: coordenadas del sitio (grados, longitud negativa = oeste,
    mismo signo que ya usa meta['lon'] en epw_real.py).
    utc_offset_h: desfase UTC del sitio (meta['utc'] de epw_real.py) -- define
    el meridiano estándar de referencia para la corrección de tiempo solar.

    Devuelve dict con arreglos (mismo largo que indice_horario): 'altitud_deg'
    (elevación solar, negativa = sol bajo el horizonte), 'acimut_deg' (desde
    el sur, positivo hacia el oeste -- convención Duffie & Beckman, igual de
    válida que la de EnergyPlus ya que ambas se comparan siempre en seno/coseno,
    nunca en valor crudo).
    """
    n = indice_horario.dayofyear.values.astype(float)
    hora_reloj = indice_horario.hour.values.astype(float) + indice_horario.minute.values.astype(float) / 60.0

    gamma = 2 * np.pi * (n - 1) / 365.0  # ángulo del día (radianes)

    declinacion = (
        0.006918 - 0.399912 * np.cos(gamma) + 0.070257 * np.sin(gamma)
        - 0.006758 * np.cos(2 * gamma) + 0.000907 * np.sin(2 * gamma)
        - 0.002697 * np.cos(3 * gamma) + 0.00148 * np.sin(3 * gamma)
    )  # radianes

    ecuacion_tiempo_min = 229.18 * (
        0.000075 + 0.001868 * np.cos(gamma) - 0.032077 * np.sin(gamma)
        - 0.014615 * np.cos(2 * gamma) - 0.04089 * np.sin(2 * gamma)
    )

    meridiano_estandar_deg = 15.0 * utc_offset_h
    correccion_tiempo_min = 4.0 * (lon_deg - meridiano_estandar_deg) + ecuacion_tiempo_min
    hora_solar = hora_reloj + correccion_tiempo_min / 60.0

    angulo_horario_deg = 15.0 * (hora_solar - 12.0)
    H = np.radians(angulo_horario_deg)
    lat = np.radians(lat_deg)

    sin_altitud = np.sin(lat) * np.sin(declinacion) + np.cos(lat) * np.cos(declinacion) * np.cos(H)
    sin_altitud = np.clip(sin_altitud, -1.0, 1.0)
    altitud = np.arcsin(sin_altitud)
    cos_altitud = np.cos(altitud)

    with np.errstate(divide="ignore", invalid="ignore"):
        sin_acimut = np.where(cos_altitud > 1e-6, np.cos(declinacion) * np.sin(H) / cos_altitud, 0.0)
        cos_acimut = np.where(
            cos_altitud > 1e-6,
            (sin_altitud * np.sin(lat) - np.sin(declinacion)) / (cos_altitud * np.cos(lat)),
            1.0,
        )
    acimut = np.arctan2(np.clip(sin_acimut, -1.0, 1.0), np.clip(cos_acimut, -1.0, 1.0))

    return {
        "altitud_deg": np.degrees(altitud),
        "acimut_deg": np.degrees(acimut),
    }


def irradiancia_poa(ghi, dni, dhi, altitud_solar_deg, acimut_solar_deg,
                     tilt_deg=0.0, acimut_superficie_deg=0.0, albedo=ALBEDO_GENERICO):
    """
    Irradiancia en el plano del arreglo (POA, W/m²) -- modelo de cielo isotrópico
    (Liu & Jordan 1963), el mismo que EnergyPlus ofrece como
    'SolarDistribution = MinimalShadowing/Isotropic' cuando no se necesita el
    modelo anisotrópico completo de Perez. Para un techo plano (tilt≈0°, el
    caso de eco_roof_1m_3_flat/eco_roof_1m_5_flat) la diferencia isotrópico vs.
    Perez es mínima -- casi toda la irradiancia difusa de un cielo despejado
    llega igual de "arriba" cuando la superficie ya está casi horizontal.

    Con tilt_deg=0 exacto, por identidad matemática (ver test), POA == GHI --
    ambos representan lo mismo (irradiancia total sobre una superficie
    horizontal) para una superficie perfectamente plana.

    ghi, dni, dhi: irradiancia horaria (W/m², arreglos del mismo largo que
    posicion_solar()) -- columnas GHI/DNI/DHI que ya trae cualquier EPW
    (engine/epw_real.py las expone desde Fase Eco-Roof).
    altitud_solar_deg, acimut_solar_deg: de posicion_solar().
    tilt_deg: inclinación del arreglo respecto a la horizontal (0°=techo
    plano). acimut_superficie_deg: orientación del arreglo, misma convención
    que el acimut solar (desde el sur, positivo al oeste) -- sin efecto
    cuando tilt_deg=0.
    """
    ghi = np.asarray(ghi, dtype=float)
    dni = np.asarray(dni, dtype=float)
    dhi = np.asarray(dhi, dtype=float)
    altitud = np.radians(altitud_solar_deg)
    acimut_sol = np.radians(acimut_solar_deg)
    beta = np.radians(tilt_deg)
    acimut_sup = np.radians(acimut_superficie_deg)

    cos_incidencia = (
        np.sin(altitud) * np.cos(beta)
        + np.cos(altitud) * np.sin(beta) * np.cos(acimut_sol - acimut_sup)
    )
    cos_incidencia = np.clip(cos_incidencia, 0.0, None)  # sol detrás del plano -> sin haz directo

    poa_haz = dni * cos_incidencia
    poa_difusa = dhi * (1 + np.cos(beta)) / 2.0
    poa_reflejada = ghi * albedo * (1 - np.cos(beta)) / 2.0
    return poa_haz + poa_difusa + poa_reflejada


def simular_solar_eco_roof(df_clima, lat_deg, lon_deg, utc_offset_h, capacidad_kwp,
                            tilt_deg=0.0, acimut_superficie_deg=0.0, derate=DERATE_GENERICO):
    """
    Producción solar horaria del Eco-Roof (kWh) -- ver docstring del módulo
    para la física y las limitaciones (modelo ESTIMADO, sin ficha de panel
    específica).

    df_clima: el mismo DataFrame horario que usa el bloque eólico -- necesita
    columnas GHI/DNI/DHI (W/m²), ya expuestas por
    engine.epw_real.cargar_epw_real().
    capacidad_kwp: capacidad nominal del arreglo del preset (ej. 0.2 kWp para
    eco_roof_1m_3_flat -- 2×100W, ver engine/eco_roof_catalog.py).

    Devuelve dict: 'serie_horaria_kwh' (pd.Series, mismo índice que df_clima),
    'kwh_anual' (float), 'kwh_mensual' (pd.Series, resample mensual),
    'advertencia' (ADVERTENCIA_ESTIMADO, siempre presente -- nunca se omite).
    """
    for col in ("GHI", "DNI", "DHI"):
        if col not in df_clima.columns:
            raise ValueError(
                f"df_clima no tiene columna '{col}' -- el EPW cargado no trae radiación "
                "solar (revisar engine.epw_real.cargar_epw_real(), o el archivo EPW en sí)."
            )

    pos = posicion_solar(df_clima.index, lat_deg, lon_deg, utc_offset_h)
    poa = irradiancia_poa(
        df_clima["GHI"].values, df_clima["DNI"].values, df_clima["DHI"].values,
        pos["altitud_deg"], pos["acimut_deg"], tilt_deg=tilt_deg,
        acimut_superficie_deg=acimut_superficie_deg,
    )
    potencia_kw = capacidad_kwp * (poa / 1000.0) * derate
    serie_kwh = pd.Series(potencia_kw, index=df_clima.index, name="kwh_solar")

    return {
        "serie_horaria_kwh": serie_kwh,
        "kwh_anual": float(serie_kwh.sum()),
        "kwh_mensual": serie_kwh.resample("MS").sum(),
        "capacidad_kwp": capacidad_kwp,
        "derate": derate,
        "tilt_deg": tilt_deg,
        "advertencia": ADVERTENCIA_ESTIMADO,
    }
