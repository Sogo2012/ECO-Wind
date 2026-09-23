"""
Bloque solar del Eco-Roof Energy Hub -- Pista Eco-Roof, módulo nuevo y separado.

MIGRACIÓN A ENERGYPLUS REAL (decisión de Pablo): la primera versión de este
módulo reimplementaba en Python puro la física de posición solar (Fourier de
Spencer) + transposición al plano del arreglo (cielo isotrópico) que documenta
el "EnergyPlus Engineering Reference". Esta versión corre esa física DENTRO
del binario real de EnergyPlus 23.2 -- mismo patrón que motor/termico.py de
Sogo2012/Skyplus (armar un modelo -> traducirlo a IDF ->
`subprocess.run([energyplus, ...])` -> leer eplusout.sql), usando el
generador fotovoltaico nativo de EnergyPlus, `Generator:PVWatts` (el wrapper
sobre el modelo PVWatts de NREL), expuesto en Python vía
`honeybee_energy.generator.pv.PVProperties`.

El EPW ya cargado por la app (engine.epw_real.cargar_epw_real()) es el MISMO
archivo que EnergyPlus usa como clima -- EnergyPlus toma Site:Location
directamente del encabezado del EPW, no hace falta repetirle lat/lon/UTC a
mano (a diferencia de la versión anterior, que sí los pedía como parámetros).

Modelo Honeybee mínimo: una habitación auxiliar sin climatizar (EnergyPlus
exige al menos una zona -- "GetHeatBalanceInput: no zones found" si no hay
ninguna; no participa del cálculo solar, que corre sobre una superficie
huérfana aparte) + una superficie (Shade) del tamaño exacto que hace que la
capacidad DC nominal que calcula PVProperties.to_idf() (área ×
active_area_fraction × rated_efficiency × 1000, ver
honeybee_energy/generator/pv.py) coincida con la capacidad del preset -- así
no se inventa un ancho/alto de panel, se despeja el área para que dé la
capacidad real del producto.

Sigue siendo un panel GENÉRICO -- no hay todavía una ficha Eco-Roof real de
un fabricante: eficiencia nominal, fracción de área activa y pérdidas de
sistema (RATED_EFFICIENCY_GENERICO / ACTIVE_AREA_FRACTION_GENERICO /
SYSTEM_LOSS_FRACTION_GENERICO) son valores de referencia de industria
(defaults de PVWatts/NREL), no una ficha de producto real. Lo que SÍ es real
ahora: la simulación hora por hora corre en el mismo motor de física
(EnergyPlus) que usa el resto de la industria para "modelado de energía de
edificios" -- ya no es una aproximación aparte hecha a mano.

Se reporta la energía AC ("Facility Total Produced Electricity Energy" --
después del inversor), no la DC cruda del generador ("Generator Produced DC
Electricity Energy"): es la cantidad convencional para reportar producción de
un sistema fotovoltaico (lo que efectivamente se inyecta/consume). El
inversor usa los defaults estándar de PVWatts/NREL que honeybee-energy aplica
automáticamente en cuanto detecta un generador PVWatts en el modelo (0.96 de
eficiencia, relación DC:AC de 1.1 -- objeto ElectricLoadCenter:Inverter:PVWatts
del IDF generado, valores de referencia de NREL, no inventados acá).

Cross-validación (dato de verificación, no un resultado que se reporte): para
el mismo preset/EPW (eco_roof_1m_3_flat, 200W, EPW del Estadio Heredia), esta
versión con EnergyPlus real dio 298.18 kWh/año DC (285.40 kWh/año AC) -- la
versión anterior en Python puro daba 296.9 kWh/año para el mismo caso, ~0.4%
de diferencia contra la DC de acá. Confirma que ambas implementaciones son
físicamente consistentes entre sí.
"""
import math
import os
import shutil
import sqlite3
import subprocess
import tempfile

import pandas as pd
from honeybee.model import Model
from honeybee.room import Room
from honeybee.shade import Shade
from honeybee_energy.config import folders as _hbe_folders
from honeybee_energy.generator.pv import PVProperties
from honeybee_energy.simulation.parameter import SimulationParameter
from honeybee_energy.writer import energyplus_idf_version
from ladybug_geometry.geometry3d.face import Face3D
from ladybug_geometry.geometry3d.pointvector import Point3D, Vector3D

# Valores de referencia de industria (defaults de PVWatts/NREL) -- NO es una ficha de
# panel Eco-Roof real, todavía no existe una (ver docstring del módulo).
RATED_EFFICIENCY_GENERICO = 0.15
ACTIVE_AREA_FRACTION_GENERICO = 0.90
SYSTEM_LOSS_FRACTION_GENERICO = 0.14

# Altura del arreglo en el modelo Honeybee -- arbitraria, sin efecto en el resultado
# (PVWatts no modela auto-sombreado entre superficies en este modelo mínimo de una sola
# superficie); sólo debe quedar por encima del nivel 0 para ser geometría válida.
_ALTURA_REFERENCIA_ARREGLO_M = 3.0

_NOMBRE_VARIABLE_AC = "Facility Total Produced Electricity Energy"

ADVERTENCIA_ESTIMADO = (
    "Producción solar de un panel GENÉRICO (eficiencia, área activa y pérdidas de sistema "
    "tipo PVWatts/NREL) simulada con EnergyPlus real (Generator:PVWatts vía Honeybee) contra "
    "el EPW real del sitio -- no hay todavía una ficha de panel Eco-Roof específica. No usar "
    "como cotización firme, sólo como orden de magnitud."
)


def _detectar_energyplus():
    """Localiza el binario real de EnergyPlus -- mismo patrón que
    motor/termico.py::_detectar_energyplus() de Sogo2012/Skyplus (variable de entorno,
    luego la ruta estándar de instalación, luego el PATH)."""
    candidatos = [
        os.environ.get("ENERGYPLUS_EXEC"),
        "/usr/local/bin/energyplus",
        shutil.which("energyplus"),
    ]
    for candidato in candidatos:
        if candidato and os.path.isfile(candidato) and os.access(candidato, os.X_OK):
            return candidato
    raise RuntimeError(
        "No se encontró el binario de EnergyPlus (se buscó $ENERGYPLUS_EXEC, "
        "/usr/local/bin/energyplus y el PATH) -- necesario para simular la producción solar "
        "del Eco-Roof con el motor real. Ver el Dockerfile (instalación de EnergyPlus 23.2)."
    )


def _area_para_capacidad_m2(capacidad_kwp, rated_efficiency, active_area_fraction):
    """
    Área de arreglo (m²) que hace que la capacidad DC nominal que calcula
    PVProperties.to_idf() -- área × active_area_fraction × rated_efficiency × 1000, ver
    honeybee_energy/generator/pv.py -- dé EXACTO capacidad_kwp: se despeja el área en vez
    de inventar un ancho/alto de panel que no tenemos.
    """
    capacidad_w = capacidad_kwp * 1000.0
    return capacidad_w / (active_area_fraction * rated_efficiency * 1000.0)


def _construir_superficie_pv(capacidad_kwp, tilt_deg, acimut_superficie_deg,
                              rated_efficiency, active_area_fraction, system_loss_fraction):
    """
    Superficie (Shade) cuadrada, del área exacta para la capacidad pedida, orientada con
    el tilt/acimut del preset -- convención brújula/EnergyPlus (0°=Norte, 90°=Este,
    180°=Sur, 270°=Oeste, sentido horario; Face3D.azimuth/.tilt de Ladybug, no la
    convención "desde el sur" de Duffie & Beckman que usaba la versión anterior en Python
    puro de este módulo).

    Se arma horizontal primero y se rota en dos pasos (tilt sobre el eje X, luego acimut
    sobre el eje Z, corrigiendo por el acimut que ya quedó tras la primera rotación) --
    verificado EMPÍRICAMENTE contra las propiedades reales .tilt/.azimuth de Face3D (no
    sólo derivado a mano) para no depender de adivinar el sentido de giro de
    Face3D.rotate(); el assert de abajo lo re-confirma en cada corrida.
    """
    area_m2 = _area_para_capacidad_m2(capacidad_kwp, rated_efficiency, active_area_fraction)
    lado = area_m2 ** 0.5
    z = _ALTURA_REFERENCIA_ARREGLO_M
    pts = (Point3D(0, 0, z), Point3D(lado, 0, z), Point3D(lado, lado, z), Point3D(0, lado, z))
    geo = Face3D(pts)

    if abs(tilt_deg) > 1e-9:
        centro = geo.center
        geo = geo.rotate(Vector3D(1, 0, 0), -math.radians(tilt_deg), centro)
        az_actual_deg = math.degrees(geo.azimuth)
        delta_deg = az_actual_deg - acimut_superficie_deg
        geo = geo.rotate(Vector3D(0, 0, 1), math.radians(delta_deg), centro)

        tilt_obtenido_deg = math.degrees(geo.tilt)
        az_obtenido_deg = math.degrees(geo.azimuth)
        assert abs(tilt_obtenido_deg - tilt_deg) < 0.5, (
            f"Geometría del arreglo Eco-Roof: tilt esperado {tilt_deg}°, "
            f"obtenido {tilt_obtenido_deg:.2f}°"
        )
        assert abs((az_obtenido_deg - acimut_superficie_deg + 180) % 360 - 180) < 0.5, (
            f"Geometría del arreglo Eco-Roof: acimut esperado {acimut_superficie_deg}°, "
            f"obtenido {az_obtenido_deg:.2f}°"
        )

    shade = Shade("eco_roof_pv_array", geo)
    shade.properties.energy.pv_properties = PVProperties(
        "eco_roof_pv_props", rated_efficiency=rated_efficiency,
        active_area_fraction=active_area_fraction, module_type="Standard",
        mounting_type="FixedRoofMounted", system_loss_fraction=system_loss_fraction,
    )
    return shade


def _armar_idf(shade):
    """Ensambla el texto IDF completo -- mismo patrón de honeybee_energy.cli.translate
    .model_to_idf(): versión + parámetros de simulación + modelo, separados por líneas en
    blanco. Sin Site:Location -- EnergyPlus lo toma solo del encabezado del EPW (-w)."""
    habitacion_auxiliar = Room.from_box("eco_roof_dummy_zone", width=1, depth=1, height=1)
    model = Model("eco_roof_pv_model", rooms=[habitacion_auxiliar], orphaned_shades=[shade])

    sim_par = SimulationParameter()
    sim_par.output.add_electricity_generation()
    sim_par.output.reporting_frequency = "Hourly"
    sim_par.simulation_control.do_zone_sizing = False
    sim_par.simulation_control.do_system_sizing = False
    sim_par.simulation_control.do_plant_sizing = False
    sim_par.simulation_control.run_for_sizing_periods = False
    sim_par.simulation_control.run_for_run_periods = True

    ver_str = energyplus_idf_version() if _hbe_folders.energyplus_version is not None else ""
    sim_par_str = sim_par.to_idf()
    model_str = model.to.idf(model)
    return "\n\n".join(s for s in (ver_str, sim_par_str, model_str) if s)


def _correr_energyplus(idf_str, ruta_epw, carpeta_trabajo):
    """Escribe el IDF y corre el binario real -- mismo patrón (subprocess, capture_output)
    que motor/termico.py::traducir_y_simular() de Skyplus."""
    idf_path = os.path.join(carpeta_trabajo, "eco_roof_pv.idf")
    with open(idf_path, "w") as f:
        f.write(idf_str)

    ep_exec = _detectar_energyplus()
    resultado = subprocess.run(
        [ep_exec, "-w", ruta_epw, "-d", carpeta_trabajo, idf_path],
        capture_output=True, text=True, timeout=600,
    )
    if resultado.returncode != 0:
        raise RuntimeError(
            f"EnergyPlus terminó con error (código {resultado.returncode}) simulando la "
            f"producción solar del Eco-Roof:\n{resultado.stdout[-3000:]}\n{resultado.stderr[-3000:]}"
        )

    sql_path = os.path.join(carpeta_trabajo, "eplusout.sql")
    if not os.path.exists(sql_path):
        raise RuntimeError(
            "EnergyPlus terminó sin errores pero no generó eplusout.sql -- no se puede leer "
            "la producción solar."
        )
    return sql_path


def _leer_serie_horaria_kwh(sql_path, nombre_variable, n_horas_esperadas):
    """
    Lee la serie horaria (kWh) de una variable de salida de EnergyPlus desde
    eplusout.sql -- mismo patrón que motor/termico.py::leer_kwh_sql() de Skyplus
    (ReportDataDictionary + ReportData, unidos por ReportDataDictionaryIndex).

    Se ordena por TimeIndex (orden cronológico) y se toma tal cual, POSICIÓN a posición
    -- no hace falta reconstruir fechas de calendario reales (el año del TMY trae meses
    de años distintos) porque el EPW que ve EnergyPlus es el MISMO archivo, fila por
    fila, que ya leyó engine.epw_real.cargar_epw_real() para armar el índice horario de
    df_clima: la posición N de esta serie es la misma hora-del-año que la posición N de
    df_clima.index, siempre.
    """
    conn = sqlite3.connect(sql_path)
    try:
        dic = pd.read_sql_query(
            "SELECT ReportDataDictionaryIndex FROM ReportDataDictionary WHERE Name = ?",
            conn, params=(nombre_variable,),
        )
        if dic.empty:
            raise RuntimeError(
                f"eplusout.sql no tiene la variable de salida '{nombre_variable}' -- revisar "
                "que SimulationParameter tenga add_electricity_generation() y "
                "reporting_frequency='Hourly'."
            )
        indice = int(dic["ReportDataDictionaryIndex"].iloc[0])
        datos = pd.read_sql_query(
            "SELECT TimeIndex, Value FROM ReportData WHERE ReportDataDictionaryIndex = ? "
            "ORDER BY TimeIndex",
            conn, params=(indice,),
        )
    finally:
        conn.close()

    if len(datos) != n_horas_esperadas:
        raise RuntimeError(
            f"eplusout.sql trae {len(datos)} horas para '{nombre_variable}', se esperaban "
            f"{n_horas_esperadas} (mismo largo que el EPW ya cargado)."
        )
    joules = datos["Value"].to_numpy()
    return joules / 3.6e6  # J -> kWh


def simular_solar_eco_roof(df_clima, ruta_epw, capacidad_kwp, tilt_deg=0.0,
                            acimut_superficie_deg=0.0,
                            rated_efficiency=RATED_EFFICIENCY_GENERICO,
                            active_area_fraction=ACTIVE_AREA_FRACTION_GENERICO,
                            system_loss_fraction=SYSTEM_LOSS_FRACTION_GENERICO):
    """
    Producción solar horaria del Eco-Roof (kWh), simulada con EnergyPlus real -- ver
    docstring del módulo para la física, las limitaciones y qué tan "real" es esto
    (motor real, panel todavía genérico).

    df_clima: el DataFrame horario ya cargado (engine.epw_real.cargar_epw_real()) -- se
    usa sólo para el índice de tiempo (largo y timestamps) del resultado, la física corre
    directo sobre el archivo de ruta_epw.
    ruta_epw: ruta al MISMO archivo .epw que produjo df_clima -- EnergyPlus necesita el
    archivo real (clima hora por hora + encabezado de ubicación), no alcanza con las
    columnas ya extraídas en df_clima.
    capacidad_kwp: capacidad nominal DC del arreglo del preset (ej. 0.2 kWp para
    eco_roof_1m_3_flat -- 2×100W, ver engine/eco_roof_catalog.py).

    Devuelve dict: 'serie_horaria_kwh' (pd.Series, energía AC, mismo índice que
    df_clima), 'kwh_anual' (float, AC), 'kwh_mensual' (pd.Series, resample mensual),
    'capacidad_kwp', 'tilt_deg', 'advertencia' (ADVERTENCIA_ESTIMADO, siempre presente).
    """
    if not os.path.exists(ruta_epw):
        raise ValueError(
            f"No existe el archivo EPW '{ruta_epw}' -- necesario para simular la "
            "producción solar del Eco-Roof con EnergyPlus real."
        )

    shade = _construir_superficie_pv(capacidad_kwp, tilt_deg, acimut_superficie_deg,
                                      rated_efficiency, active_area_fraction, system_loss_fraction)
    idf_str = _armar_idf(shade)

    with tempfile.TemporaryDirectory(prefix="eco_roof_ep_") as carpeta:
        sql_path = _correr_energyplus(idf_str, ruta_epw, carpeta)
        kwh_ac = _leer_serie_horaria_kwh(sql_path, _NOMBRE_VARIABLE_AC, len(df_clima))

    serie_kwh = pd.Series(kwh_ac, index=df_clima.index, name="kwh_solar")
    return {
        "serie_horaria_kwh": serie_kwh,
        "kwh_anual": float(serie_kwh.sum()),
        "kwh_mensual": serie_kwh.resample("MS").sum(),
        "capacidad_kwp": capacidad_kwp,
        "tilt_deg": tilt_deg,
        "advertencia": ADVERTENCIA_ESTIMADO,
    }
