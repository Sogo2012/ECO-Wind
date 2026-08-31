"""
Sitios de Costa Rica con archivo EPW REAL propio (no aproximación de forma
prestada) -- Requisito 1, Fase 2, seguimiento del Hallazgo 17/18.

ORIGEN DE LOS ARCHIVOS: climate.onebuilding.org está bloqueado en este
sandbox de desarrollo (confirmado con curl y WebFetch, dos métodos
independientes -- ver Hallazgo 2, ahora extendido a 6 hosts). Los 3 archivos
EPW de este módulo los descargó Pablo directamente desde
climate.onebuilding.org (con internet real) y los subió al chat -- son
datos reales de esa fuente, igual que el EPW de San José que ya estaba en
el repo (mismo patrón, mismo dominio de origen, misma convención de
nombres TMYx).

PATRÓN ADOPTADO DE DDP-Lite (Sogo2012/DDP-lite, revisado a pedido de
Pablo): ese proyecto resuelve "clima real por sitio" con un catálogo
estático pre-scrapeado de climate.onebuilding.org (epw_catalog_global.json,
5276 estaciones) + búsqueda geodésica (Haversine) + una opción explícita
"¿Usar archivo EPW personalizado?" (toggle + st.file_uploader) que reemplaza
la estación más cercana del catálogo por el EPW real que suba el usuario,
cuando lo tiene. Ver weather_utils.py::obtener_estaciones_cercanas() y
app.py líneas ~1259-1298 de ese repo.

ACTUALIZACIÓN (Hallazgo 19): sí se portó un catálogo propio --
`datos_clima/epw_catalog_cr.json`, las 12 entradas de Costa Rica extraídas
directo de `epw_catalog_global.json` de DDP-lite (que ya lo tenía
scrapeado real de climate.onebuilding.org, con 5,276 estaciones de 20
países -- acá solo se usan las 12 de Costa Rica, todo lo demás está fuera
de alcance de ECO-Wind). Se recortó también la lógica de
`obtener_estaciones_cercanas()`: sin geocodificación inversa (Photon/
Nominatim) ni fallback de países vecinos -- ECO-Wind ya sólo cubre Costa
Rica (lat 8-11.3, lon -86/-82.5, ver límites en app.py), así que buscar
"a qué país pertenece la coordenada" no aplica. Sólo queda la búsqueda
Haversine sobre las 12 estaciones (`buscar_estaciones_cercanas()`).

**Discrepancia real encontrada al portar esto (no ignorada):** el catálogo
trae Finca Favorita en (9.8833, -83.9167), pero el EPW real que Pablo
subió (Hallazgo 18) trae en su propio encabezado LOCATION (9.517,
-82.650) -- casi 50 km de diferencia. El catálogo es sólo una posición
aproximada para dibujar el mapa y ordenar por distancia ANTES de
descargar; la metadata que de verdad se usa (lat/lon/elevación) siempre
sale del encabezado del EPW ya descargado, nunca del catálogo -- por eso
esto no afecta ningún resultado ya calculado, pero es una razón más para
no confiar en el catálogo como fuente de verdad de la posición.

Lo que SÍ se adopta aquí, ya en este módulo: (a) un parser EPW genérico y
liviano (sin depender de ladybug, que DDP-lite sí usa pero que no es
dependencia de ECO-Wind todavía), reutilizable para cualquier .epw nuevo,
San José incluido si algún día se reemplaza el export manual de GWA por
su propio EPW real; (b) el mismo concepto de "EPW personalizado" vía
uploader en la app (ver app/app.py); (c) desde Hallazgo 19, el mapa +
búsqueda de estaciones + descarga bajo demanda, mismo patrón que DDP-lite.
"""
import csv
import json
import math
import os
import tempfile
import zipfile

import numpy as np
import pandas as pd

_AQUI = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_AQUI)
CARPETA_EPW_REAL = os.path.join(_BASE, "datos_clima", "epw_real")
RUTA_CATALOGO_CR = os.path.join(_BASE, "datos_clima", "epw_catalog_cr.json")


def cargar_epw_real(ruta_epw, year=2023):
    """
    Parser EPW mínimo (formato estándar EnergyPlus/climate.onebuilding.org):
    8 líneas de encabezado (la primera, LOCATION, con metadata del sitio),
    luego una fila por hora. Campo 21 = dirección de viento (°), campo 22 =
    velocidad de viento a 10m (m/s) -- 1-indexado, ver EPW Data Dictionary.

    Devuelve (df_clima, meta): df_clima con índice datetime horario y
    columnas WS10M/WD10/T2M (mismo formato que generar_clima_gwa(), para
    poder pasarlo directo a simular() sin cambios); meta con la ubicación y
    elevación real que trae el propio archivo (más confiable que un valor
    tecleado a mano).
    """
    with open(ruta_epw, encoding="latin-1") as f:
        header = [next(f) for _ in range(8)]
        filas = list(csv.reader(f))

    loc = header[0].strip().split(",")
    meta = {
        "estacion": loc[1], "region": loc[2], "pais": loc[3],
        "fuente": loc[4], "wmo": loc[5],
        "lat": float(loc[6]), "lon": float(loc[7]),
        "utc": float(loc[8]), "elevacion_m": float(loc[9]),
    }

    ws = np.array([float(r[21]) for r in filas])
    wd = np.array([float(r[20]) for r in filas])
    t2m = np.array([float(r[6]) for r in filas])

    n_horas = len(ws)
    if n_horas not in (8760, 8784):
        raise ValueError(f"{ruta_epw}: {n_horas} horas de datos, se esperaban 8760 u 8784.")

    idx = pd.date_range(f"{year}-01-01", periods=n_horas, freq="h")
    df_clima = pd.DataFrame({"WS10M": ws, "WD10": wd, "T2M": t2m}, index=idx)
    return df_clima, meta


def heatmap_json_desde_epw(df_clima):
    """
    Construye el mismo formato que heatmapData.json de GWA (lista de
    {month, hour, value}, value = índice respecto a la media anual) pero a
    partir de datos EPW reales -- para que graficar_heatmap_clima() en la
    app funcione igual sin importar la fuente climática.
    """
    media = df_clima["WS10M"].mean()
    tabla = (df_clima.assign(m=df_clima.index.month, h=df_clima.index.hour)
             .groupby(["m", "h"])["WS10M"].mean() / media)
    return [{"month": int(m), "hour": int(h), "value": float(v)}
            for (m, h), v in tabla.items()]


def rosa_frecuencia_desde_epw(df_clima, n_sectores=12, vel_min_calma=0.3):
    """
    Rosa de vientos real (frecuencia % por sector direccional) calculada
    directamente de la columna WD10 del EPW -- no depende del .lib
    paramétrico (Weibull) que sólo existe para San José. Mismo filtro de
    calmas (<0.3 m/s) que usa DDP-lite (weather_utils.py,
    generar_rosa_vientos_avanzada()).
    """
    df = df_clima[df_clima["WS10M"] > vel_min_calma]
    ancho = 360.0 / n_sectores
    bins = np.arange(-ancho / 2, 360 - ancho / 2 + 0.01, ancho)
    sector = pd.cut(df["WD10"] % 360, bins=bins, labels=False, include_lowest=True)
    sector = sector.fillna(0) % n_sectores  # wrap del último bin (350-360=0-10) al sector N
    conteo = sector.value_counts(normalize=True).reindex(range(n_sectores), fill_value=0.0) * 100
    return conteo.sort_index().tolist()


def _haversine_km(lat1, lon1, lat2, lon2):
    """Distancia geodésica en km entre dos puntos -- misma fórmula que
    weather_utils.py::_haversine() de DDP-lite."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cargar_catalogo_cr(ruta=RUTA_CATALOGO_CR):
    """Catálogo de estaciones EPW de Costa Rica (12 entradas, ver docstring
    del módulo -- extraído de epw_catalog_global.json de DDP-lite)."""
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


def buscar_estaciones_cercanas(lat, lon, top_n=6, ruta_catalogo=RUTA_CATALOGO_CR):
    """
    Estaciones del catálogo de Costa Rica más cercanas a (lat, lon), por
    distancia Haversine -- versión recortada de
    weather_utils.py::obtener_estaciones_cercanas() de DDP-lite: sin
    geocodificación inversa ni fallback de países vecinos, porque ECO-Wind
    ya está acotado a Costa Rica (no hace falta adivinar el país).

    Devuelve (cercanas, sin_coordenada): la lista ordenada por distancia
    (sólo estaciones con lat/lon conocidos en el catálogo -- algunas no
    los traen, ver docstring del módulo) y la lista aparte de estaciones
    del catálogo sin coordenada (igual utilizables por nombre, pero no se
    pueden ubicar en el mapa ni ordenar por distancia).
    """
    catalogo = cargar_catalogo_cr(ruta_catalogo)
    con_coord = [s for s in catalogo if s.get("lat") is not None and s.get("lon") is not None]
    sin_coord = [s for s in catalogo if s.get("lat") is None or s.get("lon") is None]

    cercanas = []
    for s in con_coord:
        d = _haversine_km(lat, lon, s["lat"], s["lon"])
        cercanas.append({**s, "distancia_km": round(d, 1)})
    cercanas.sort(key=lambda x: x["distancia_km"])
    return cercanas[:top_n], sin_coord


def descargar_y_extraer_epw(url_zip, carpeta_destino=None):
    """
    Descarga un ZIP de climate.onebuilding.org (URL del catálogo) y
    extrae el .epw -- mismo patrón que
    weather_utils.py::descargar_y_extraer_epw() de DDP-lite.

    NO SE PUDO PROBAR EN VIVO EN ESTE SANDBOX: climate.onebuilding.org
    está bloqueado (Hallazgo 2/18, confirmado con curl y WebFetch). Esta
    función está escrita y lista, pero sólo se puede ejercitar de verdad
    con internet real (Docker local de Pablo, Cloud Run, o Colab) -- mismo
    patrón ya usado para el ráster de GWA (engine/gwa_raster.py) y el EPW
    de San José. Lo que sí se probó sin red: la lógica de
    buscar_estaciones_cercanas() (Haversine pura) y que el .epw ya
    descargado (los 3 de Hallazgo 18) se parsea bien con cargar_epw_real().
    """
    import requests

    destino = carpeta_destino or tempfile.mkdtemp(prefix="eco_wind_epw_")
    os.makedirs(destino, exist_ok=True)
    zip_path = os.path.join(destino, "clima.zip")

    headers = {"User-Agent": "ECO Wind/1.0 (ECO Consultor; simulador eolico)"}
    r = requests.get(url_zip, headers=headers, timeout=60, stream=True)
    r.raise_for_status()
    with open(zip_path, "wb") as f:
        for chunk in r.iter_content(chunk_size=8192):
            f.write(chunk)

    with zipfile.ZipFile(zip_path) as z:
        epw_files = [n for n in z.namelist() if n.lower().endswith(".epw")]
        if not epw_files:
            raise ValueError(f"El ZIP de {url_zip} no contiene ningún archivo .epw.")
        z.extract(epw_files[0], destino)
        return os.path.join(destino, epw_files[0])


SITIOS_EPW_REAL = {
    "nicoya": {
        "nombre": "Nicoya A.P. (Guanacaste, Pacífico seco)",
        "ruta_epw": os.path.join(CARPETA_EPW_REAL, "CRI_GU_Nicoya.AP.787550_TMYx.2007-2021.epw"),
    },
    "liberia": {
        "nombre": "Daniel Oduber / Liberia Intl. A.P. (Guanacaste, Pacífico)",
        "ruta_epw": os.path.join(CARPETA_EPW_REAL, "CRI_GU_Quiros-Liberia.Intl.AP.787740_TMYx.2004-2018.epw"),
    },
    "finca_favorita": {
        "nombre": "Finca Favorita (Limón, Caribe)",
        "ruta_epw": os.path.join(CARPETA_EPW_REAL, "CRI_LI_Finca.Favorita.749033_TMYx.2007-2021.epw"),
    },
}


if __name__ == "__main__":
    for clave, s in SITIOS_EPW_REAL.items():
        df, meta = cargar_epw_real(s["ruta_epw"])
        print(f"{s['nombre']}: media={df['WS10M'].mean():.3f} m/s, "
              f"elev={meta['elevacion_m']:.0f}m, lat={meta['lat']:.4f}, lon={meta['lon']:.4f}, "
              f"{len(df)} horas -- {'OK' if len(df) in (8760, 8784) else 'FALLO'}")
