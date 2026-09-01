"""
Pista A -- Motor empirico de simulacion (ECO | Wind).

Extraido de notebooks/pista_a_motor_empirico.ipynb (Pasos 2c-4) a un
modulo importable, para poder usarlo desde la app de Fase 2 (Streamlit)
sin depender del notebook. Misma logica, sin cambios de fondo -- ver el
notebook para el desarrollo/validacion paso a paso (Hallazgo de Pista A,
z0/GWA confirmado con datos reales a 10m).

FUENTE CLIMATICA: Global Wind Atlas (GWA), no NASA POWER. Dos razones,
ya documentadas en avance-de-proyecto.md:
1) NASA POWER subestima el viento real en el Valle Central (~3x, Hallazgo 1).
2) NASA POWER no es alcanzable desde este entorno de desarrollo (bloqueado
   por el proxy de red, confirmado 31/ago/2026) -- sin verificar todavia si
   aplica igual al entorno de produccion (Cloud Run).
GWA si esta confirmado con datos reales (Hallazgo 3).

LIMITACION IMPORTANTE, no escondida: la ingesta de GWA aqui es un export
manual del panel web (carpeta con windSpeed.json + heatmapData.json por
sitio) -- NO es una API en vivo para cualquier coordenada arbitraria.
Hoy solo existe un sitio preparado (San Jose / Juan Santamaria,
datos_clima/gwa_juan_santamaria/). El flujo "coordenada -> pronostico
instantaneo" del plan (seccion 5) para un sitio nuevo cualquiera sigue
sin resolverse -- pendiente real de Fase 2, no de esta sesion.
"""
import calendar
import json

import numpy as np
import pandas as pd

try:
    from engine.flower_turbines_curves import power_in_bouquet, CURVE_COEFFICIENTS
    from engine.atmosfera_estandar import factor_correccion_densidad
    from engine.terrain_classification import query_worldcover_z0
except ImportError:
    from flower_turbines_curves import power_in_bouquet, CURVE_COEFFICIENTS
    from atmosfera_estandar import factor_correccion_densidad
    try:
        from terrain_classification import query_worldcover_z0
    except ImportError:
        # Fallback si terrain_classification no está disponible aún
        def query_worldcover_z0(lat, lon, raster_path=None):
            return 0.3, None, "fallback"

Z0_DEFAULT = 0.3      # rugosidad del sitio DESTINO (donde va la turbina) -- ver wind_at_height()
Z0_MET_DEFAULT = 0.1  # rugosidad del sitio de REFERENCIA meteorologica (aeropuerto/GWA/EPW) --
                       # clase "country" de EnergyPlus/ladybug-tools, ver wind_at_height()

# Tabla real de la ley de potencia que usa EnergyPlus por default (no la logaritmica) --
# confirmada en el codigo fuente de ladybug-tools/ladybug, windprofile.py::TERRAIN_PARAMETERS
# (revisado 31/ago/2026, Hallazgo 20 -- no es de memoria ni de un resumen sin verificar).
# {terreno: (altura de capa limite [m], exponente de la ley de potencia, longitud de
# rugosidad z0 [m])}. "country" es la clase que ladybug-tools documenta explicitamente como
# "typical of most airports where wind measurements are taken" -- coincide con nuestra
# situacion real (toda la referencia climatica del proyecto viene de aeropuertos/GWA/EPW).
TERRENOS_ENERGYPLUS = {
    "water": (210, 0.10, 0.03),
    "country": (270, 0.14, 0.1),
    "suburban": (370, 0.22, 0.5),
    "city": (460, 0.33, 1.0),
}


def wind_at_height(v_ref, h_ref, h_target, z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT):
    """
    Perfil logaritmico de viento CON DOS rugosidades distintas (Hallazgo 20):

        v(h) = v_ref * ln(h_target/z0) / ln(h_ref/z0_met)

    Corrige un error real que tenia esta funcion hasta Hallazgo 20: usaba
    el MISMO z0 tanto para el sitio de referencia (donde se midio v_ref,
    normalmente un aeropuerto/GWA/EPW a 10m) como para el sitio destino
    (donde va la turbina) -- pero son sitios distintos con rugosidad
    distinta casi siempre. Confirmado como un patron real (no una
    idealizacion nuestra) en el codigo fuente de ladybug-tools/ladybug
    (windprofile.py, WindProfile.calculate_wind() con log_law=True), que
    SI distingue explicitamente "meteorological_terrain" de "terrain". Con
    datos reales de San Jose, ignorar esta distincion sobreestimaba la
    velocidad en buje 16-24% (segun el metodo de comparacion) -- y como
    P∝v^3, eso es ~1.6-1.9x de mas en energia. Ver avance-de-proyecto.md.

    h_ref   : altura del dato de referencia (10 para GWA/WS10M/EPW).
    h_target: altura real de buje de la turbina.
    z0      : rugosidad (m) del sitio DESTINO -- 0.03 campo abierto, 0.1
              cultivos bajos, 0.3 suburbano (default), 1.0 urbano denso.
    z0_met  : rugosidad (m) del sitio de REFERENCIA meteorologica -- 0.1
              por default ("country"/aeropuerto, ver TERRENOS_ENERGYPLUS
              arriba). Las turbinas Flower Turbines son muy bajas (buje
              1-6m), casi siempre POR DEBAJO de los 10m de referencia -- la
              correccion casi siempre REDUCE la velocidad respecto al dato
              crudo.

    Si h_target <= z0 (el buje queda dentro/debajo de la subcapa de
    rugosidad del sitio destino), se devuelve 0 -- mismo criterio que
    ladybug-tools/ladybug (el perfil logaritmico no es fisicamente
    confiable ahi; mejor un 0 explicito que un numero negativo o
    indefinido silencioso).
    """
    v_ref = np.asarray(v_ref, dtype=float)
    if h_target <= z0:
        return v_ref * 0.0
    return v_ref * np.log(h_target / z0) / np.log(h_ref / z0_met)


def wind_at_height_potencia(v_ref, h_ref, h_target, terreno="suburban", terreno_met="country"):
    """
    Ley de potencia (la que usa EnergyPlus por default, NO la logaritmica
    de wind_at_height()) -- cross-check independiente, misma tabla real de
    terrenos que ladybug-tools/ladybug (TERRENOS_ENERGYPLUS arriba). No
    reemplaza wind_at_height(): es una segunda fuente para comparar y
    detectar si ambos metodos concuerdan razonablemente -- mismo patron de
    doble verificacion ya usado en el proyecto (p.ej. GWA vs. EPW, Hallazgo 3).

    terreno/terreno_met: uno de "water", "country", "suburban", "city" --
    ver TERRENOS_ENERGYPLUS para la definicion de cada clase.
    """
    d_met, a_met, _ = TERRENOS_ENERGYPLUS[terreno_met]
    d_dst, a_dst, _ = TERRENOS_ENERGYPLUS[terreno]
    v_ref = np.asarray(v_ref, dtype=float)
    factor_met = (d_met / h_ref) ** a_met
    return ((h_target / d_dst) ** a_dst) * (v_ref * factor_met)


def wind_at_height_dynamic(v_ref, h_ref, h_target, lat, lon, z0_met=Z0_MET_DEFAULT):
    """
    PHASE B - Perfil logarítmico de viento con z0 DINÁMICO desde ESA WorldCover.

    Reemplaza el valor hardcoded Z0_DEFAULT=0.3m (que asumía suburbano en TODOS
    los sitios) con valores reales de Davenport-Wieringa calibrados automáticamente
    por tipo de cobertura terrestre.

    Parámetros:
    -----------
    v_ref : float o array
        Velocidad de referencia (m/s) a altura h_ref
    h_ref : float
        Altura de referencia (típicamente 10m para GWA/EPW)
    h_target : float
        Altura del buje de la turbina (típicamente 1-6m para Flower Turbines)
    lat, lon : float
        Coordenadas WGS84 del sitio DESTINO (donde va la turbina)
    z0_met : float, optional
        Rugosidad del sitio meteorológico de referencia (default 0.1m = "country")

    Devuelve:
    ---------
    v_target : float o array
        Velocidad corregida a altura h_target, con z0 dinámico

    Nota: Si h_target <= z0, devuelve 0 (subcapa de rugosidad, perfil no confiable).
    """
    z0_dynamic, _, _ = query_worldcover_z0(lat, lon)
    return wind_at_height(v_ref, h_ref, h_target, z0=z0_dynamic, z0_met=z0_met)


def simular_dynamic(df_clima, lat, lon, altura_buje, modelo, N, elevacion_m=0.0,
                   h_ref=10, z0_met=Z0_MET_DEFAULT, metodo_bouquet="real"):
    """
    PHASE B - Wrapper de simular() que usa z0 dinámico desde ESA WorldCover.

    Reemplaza el parámetro 'z0' hardcoded por consultas dinámicas a terrain_classification.py.

    Parámetros: igual que simular(), excepto:
    - Remueve parámetro 'z0' (se obtiene automáticamente)
    - Agrega 'lat', 'lon' para consultar z0 dinámico

    Devuelve: mismo formato que simular()
    """
    z0_dynamic, _, _ = query_worldcover_z0(lat, lon)
    return simular(df_clima, altura_buje, modelo, N, elevacion_m=elevacion_m,
                  h_ref=h_ref, z0=z0_dynamic, z0_met=z0_met, metodo_bouquet=metodo_bouquet)


def cargar_gwa_json(carpeta):
    """Carga windSpeed.json (curva de excedencia empirica) y
    heatmapData.json (indice real mes x hora) de un export de plot data
    del Global Wind Atlas (panel web, descarga manual por sitio)."""
    with open(f"{carpeta}/windSpeed.json") as f:
        ws = json.load(f)
    with open(f"{carpeta}/heatmapData.json") as f:
        hm = json.load(f)
    return ws, hm


def generar_clima_gwa(windspeed_json, heatmap_json, year=2023, seed=42, media_objetivo=None):
    """
    Serie horaria de viento a partir del export real del Global Wind Atlas.
    Ver notebooks/pista_a_motor_empirico.ipynb Paso 2c para el desarrollo
    completo -- resumen: transformada inversa sobre la curva de excedencia
    real (sin asumir Weibull) + indice real mes x hora para reproducir
    estacionalidad y ciclo diurno reales.

    media_objetivo: si es None (default), reproduce el sitio del que viene
    windspeed_json/heatmap_json tal cual (su propia media real). Si se da
    un valor, se usa la FORMA (curva de excedencia normalizada + patron
    diurno/estacional) de este sitio pero ESCALADA a esa media distinta --
    es la base de generar_clima_sitio_nuevo() (Requisito 1, Fase 2): tomar
    prestada la forma de un sitio con datos ricos (San Jose) para un sitio
    nuevo del que solo se tiene la media real (del raster de Costa Rica),
    no su distribucion/patron diurno propios. Ver docstring de esa funcion
    para las limitaciones de esta aproximacion -- no se debe confundir con
    tener datos reales del sitio nuevo.
    """
    perc = np.array([r["perc"] for r in windspeed_json], dtype=float)
    val = np.array([r["val"] for r in windspeed_json], dtype=float)
    orden = np.argsort(perc)
    perc_ord, val_ord = perc[orden], val[orden]
    media_global = val_ord.mean()
    media_escala = media_objetivo if media_objetivo is not None else media_global

    idx_lookup = {(r["month"], r["hour"]): r["value"] for r in heatmap_json}

    n_horas = 8784 if calendar.isleap(year) else 8760
    idx_dt = pd.date_range(f"{year}-01-01", periods=n_horas, freq="h")
    rng = np.random.default_rng(seed)

    u = rng.uniform(0, 1, size=n_horas)
    perc_objetivo = 100 * (1 - u)
    r_normalizado = np.interp(perc_objetivo, perc_ord, val_ord) / media_global

    factores = np.array([idx_lookup[(m, h)] for m, h in zip(idx_dt.month, idx_dt.hour)])
    ws = r_normalizado * media_escala * factores

    return pd.DataFrame({"WS10M": ws, "T2M": 22.0}, index=idx_dt), media_global


def cargar_wind_rose_lib(ruta_lib, z0=0.030, altura=10.0):
    """
    Parsea un archivo .lib (formato WAsP, export nativo de GWA) y devuelve
    la rosa de vientos direccional real: frecuencia (%), y parámetros
    Weibull A (escala) y k (forma) por sector, en los 12 sectores
    estándar de 30° cada uno (0°=Norte, sentido horario).

    Formato .lib (binado por sector): línea 3 = lista de z0 (m)
    disponibles, línea 4 = lista de alturas (m) disponibles; luego, para
    cada z0, un bloque con: frecuencia (12 valores), y por cada altura,
    A (12 valores) y k (12 valores). Ver notebooks/pista_a_motor_empirico.ipynb
    Paso 2c/celda de wind rose para el desarrollo original de este parser.
    """
    with open(ruta_lib) as f:
        lineas = [l.split() for l in f.readlines()]
    z0_vals = [float(x) for x in lineas[2]]
    alturas = [float(x) for x in lineas[3]]

    idx = 4
    bloques = {}
    for z0_disp in z0_vals:
        freq = [float(x) for x in lineas[idx]]; idx += 1
        for h in alturas:
            A = [float(x) for x in lineas[idx]]; idx += 1
            k = [float(x) for x in lineas[idx]]; idx += 1
            bloques[(z0_disp, h)] = {"freq": freq, "A": A, "k": k}

    if (z0, altura) not in bloques:
        raise KeyError(f"(z0={z0}, altura={altura}) no está en el .lib -- disponibles: "
                        f"z0={z0_vals}, alturas={alturas}")
    return bloques[(z0, altura)]


def simular(df_clima, altura_buje, modelo, N, elevacion_m=0.0, h_ref=10, z0=Z0_DEFAULT,
            z0_met=Z0_MET_DEFAULT, metodo_bouquet="real"):
    """
    Ensambla la serie horaria de potencia del cluster y la agrega a kWh
    mensual/anual, usando P(v)=k*v^3 x M(N) del motor empirico
    (engine/flower_turbines_curves.py, validado Hallazgo 12), CORREGIDA por
    densidad de aire real segun la elevacion del sitio (Requisito 2, Fase
    2 -- ver engine/atmosfera_estandar.py).

    IMPORTANTE sobre el calculo horario (Requisito 3, Fase 2): esta funcion
    ya aplica P=k*v^3 HORA POR HORA sobre el arreglo completo de v_hub (8760
    valores), no sobre la velocidad media -- v_hub es un arreglo, no un
    escalar, y power_in_bouquet() lo evalua elemento a elemento antes de
    sumar. Esto es CORRECTO y necesario: como P∝v^3 es convexa, evaluar en
    la media subestima la energia real (desigualdad de Jensen,
    E[v^3]>=(E[v])^3) -- ver comparar_metodo_ingenuo_vs_horario() para
    cuantificar esa diferencia con datos reales, y el aviso mas abajo.

    df_clima: DataFrame con indice datetime horario y columna 'WS10M' (m/s).
    elevacion_m: elevacion del sitio (m sobre el nivel del mar). Default 0.0
    (sin corregir, nivel del mar) -- pasar la elevacion real del sitio para
    que la correccion de densidad se aplique.
    """
    v_hub = wind_at_height(df_clima["WS10M"].values, h_ref, altura_buje, z0=z0, z0_met=z0_met)
    potencia_w_por_turbina = power_in_bouquet(v_hub, modelo, N, metodo=metodo_bouquet)
    factor_densidad = factor_correccion_densidad(elevacion_m)
    potencia_w_por_turbina = potencia_w_por_turbina * factor_densidad

    serie = pd.Series(potencia_w_por_turbina, index=df_clima.index,
                       name="potencia_W_por_turbina")
    energia_cluster_kwh = serie * N / 1000.0
    return {
        "serie_horaria_W_por_turbina": serie,
        "kwh_mensual": energia_cluster_kwh.resample("MS").sum(),
        "kwh_anual": float(energia_cluster_kwh.sum()),
        "v_hub_medio": float(np.mean(v_hub)),
        "pct_horas_bajo_cutin": float(np.mean(v_hub < CURVE_COEFFICIENTS[modelo]["v_cutin"]) * 100),
        "factor_correccion_densidad": float(factor_densidad),
        "elevacion_m": float(elevacion_m),
    }


def comparar_metodo_ingenuo_vs_horario(df_clima, altura_buje, modelo, N, elevacion_m=0.0,
                                        h_ref=10, z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT,
                                        metodo_bouquet="real"):
    """
    Cuantifica el efecto de Jensen (Requisito 3, Fase 2): compara el
    resultado CORRECTO (P=k*v^3 hora por hora, sumado sobre las 8760 horas
    -- lo que ya hace simular()) contra el metodo INGENUO (evaluar P en la
    velocidad media anual una sola vez, y multiplicar por 8760 horas).

    Como P∝v^3 es convexa, E[v^3] >= (E[v])^3 para cualquier distribucion
    no constante (desigualdad de Jensen) -- el metodo ingenuo SIEMPRE
    subestima (nunca sobre-estima) la energia real de un recurso variable,
    y la brecha crece con la variabilidad del viento (mientras mas disperso
    el viento, peor el metodo ingenuo).

    Devuelve un diccionario con ambos resultados y la razon entre ellos.
    """
    correcto = simular(df_clima, altura_buje, modelo, N, elevacion_m, h_ref, z0, z0_met, metodo_bouquet)

    v_hub = wind_at_height(df_clima["WS10M"].values, h_ref, altura_buje, z0=z0, z0_met=z0_met)
    v_media = float(np.mean(v_hub))
    n_horas = len(df_clima)
    potencia_en_media = float(power_in_bouquet(v_media, modelo, N, metodo=metodo_bouquet))
    factor_densidad = factor_correccion_densidad(elevacion_m)
    kwh_anual_ingenuo = potencia_en_media * factor_densidad * N * n_horas / 1000.0

    return {
        "kwh_anual_correcto": correcto["kwh_anual"],
        "kwh_anual_ingenuo": kwh_anual_ingenuo,
        "razon_correcto_sobre_ingenuo": correcto["kwh_anual"] / kwh_anual_ingenuo if kwh_anual_ingenuo > 0 else float("inf"),
        "v_media": v_media,
    }


SITIOS_DISPONIBLES = {
    "san_jose_juan_santamaria": {
        "nombre": "San José (Aeropuerto Juan Santamaría)",
        "carpeta_gwa": "datos_clima/gwa_juan_santamaria",
        "lat": 10.0034, "lon": -84.2033,
        "elevacion_m": 921.0,  # verificado AIP/DGAC Costa Rica (3021-3022 ft), múltiples fuentes
    },
}


if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
    ws_json, hm_json = cargar_gwa_json(os.path.join(base, sitio["carpeta_gwa"]))
    df_gwa, media_global = generar_clima_gwa(ws_json, hm_json)
    print(f"Sitio: {sitio['nombre']} -- media GWA confirmada: {media_global:.3f} m/s, "
          f"elevación: {sitio['elevacion_m']:.0f} m")

    r_sin_densidad = simular(df_gwa, altura_buje=3.0, modelo="medium_tulip", N=3, elevacion_m=0.0)
    r = simular(df_gwa, altura_buje=3.0, modelo="medium_tulip", N=3, elevacion_m=sitio["elevacion_m"])
    print()
    print("Requisito 2 -- corrección de densidad de aire:")
    print(f"  Sin corregir (rho nivel del mar, como si el sitio estuviera a 0m): "
          f"{r_sin_densidad['kwh_anual']:.1f} kWh/año")
    print(f"  Corregido (rho real a {sitio['elevacion_m']:.0f}m, factor="
          f"{r['factor_correccion_densidad']:.4f}): {r['kwh_anual']:.1f} kWh/año")
    print(f"  Reducción: {(1 - r['kwh_anual']/r_sin_densidad['kwh_anual'])*100:.1f}%")

    print()
    print("Requisito 3 -- efecto de Jensen (método correcto horario vs. método ingenuo):")
    cmp = comparar_metodo_ingenuo_vs_horario(df_gwa, altura_buje=3.0, modelo="medium_tulip", N=3,
                                              elevacion_m=sitio["elevacion_m"])
    print(f"  Método CORRECTO (P=k·v³ hora por hora, 8760 horas, ya con densidad corregida): "
          f"{cmp['kwh_anual_correcto']:.1f} kWh/año")
    print(f"  Método INGENUO (P en la velocidad media {cmp['v_media']:.2f} m/s, x8760 horas): "
          f"{cmp['kwh_anual_ingenuo']:.1f} kWh/año")
    print(f"  El método ingenuo SUBESTIMA la energía real en {cmp['razon_correcto_sobre_ingenuo']:.2f}x "
          f"-- consecuencia directa de la desigualdad de Jensen (E[v³]≥(E[v])³) sobre un "
          f"recurso con variabilidad real, no una diferencia menor a ignorar.")
