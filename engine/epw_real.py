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

PATRÓN ADOPTADO DE DDP-Lite Y SKYPLUS (Sogo2012/DDP-lite, Sogo2012/Skyplus
-- mismo módulo `weather_utils.py`, prácticamente idéntico entre los dos
salvo branding, confirmado con `diff` línea por línea): "clima real por
sitio" se resuelve con un catálogo estático pre-scrapeado de
climate.onebuilding.org (`epw_catalog_global.json`, 5,276 estaciones, 20
países de América -- USA/CAN/MEX + 17 LATAM) + búsqueda geodésica
(Haversine) + geocodificación (Photon/Nominatim, tanto inversa para
inferir el país de una coordenada como directa para "buscar por nombre")
+ un mapa Folium con clic-para-buscar + una opción explícita "¿Usar
archivo EPW personalizado?" que reemplaza la estación por el EPW real que
suba el usuario. Ver `weather_utils.py::obtener_estaciones_cercanas()`,
`get_location_info()`, `geocode_name()` de esos repos.

CORRECCIÓN, Hallazgo 19 (v1 -> v2): la primera versión de este módulo
recortaba el catálogo a sólo las 12 estaciones de Costa Rica y eliminaba
la geocodificación -- una simplificación que Pablo pidió deshacer
explícitamente ("no me hardcodes ninguna estación ni me limites a costa
rica... necesito la misma cosa [que DDP-lite/Skyplus]"). Esta versión es
un port fiel y completo: el catálogo completo (5,276 estaciones, 20
países) y `obtener_estaciones_cercanas()` con toda su lógica real
(geocodificación inversa + bounding boxes de los 20 países + expansión a
países vecinos + fallback global), más `geocode_name()` para buscar por
nombre -- nada acotado a Costa Rica. La única simplificación real que
queda, y es deliberada: no se usa `ladybug.epw.EPW` para parsear el EPW
descargado (DDP-lite/Skyplus sí la usan) -- se usa el parser propio y
liviano `cargar_epw_real()` de este mismo módulo, ya construido y
validado en Hallazgo 18, que lee exactamente los mismos campos.

**Discrepancia real encontrada al portar esto (no ignorada):** el catálogo
trae Finca Favorita en (9.8833, -83.9167), pero el EPW real que Pablo
subió (Hallazgo 18) trae en su propio encabezado LOCATION (9.517,
-82.650) -- casi 50 km de diferencia. El catálogo es sólo una posición
aproximada para dibujar el mapa y ordenar por distancia ANTES de
descargar; la metadata que de verdad se usa (lat/lon/elevación) siempre
sale del encabezado del EPW ya descargado, nunca del catálogo -- por eso
esto no afecta ningún resultado ya calculado, pero es una razón más para
no confiar en el catálogo como fuente de verdad de la posición.

BLOQUEO DE RED, mismo patrón de todo el proyecto (Hallazgo 2): tanto
`nominatim.openstreetmap.org` como `photon.komoot.io` están bloqueados en
este sandbox (confirmado con curl, `connect_rejected`) -- la
geocodificación (buscar por nombre, o inferir país por reversa) no se
pudo probar en vivo acá. Lo que SÍ se probó sin red: el fallback por
bounding box (`_infer_country_from_bbox()`, pura aritmética, no necesita
geocodificación para funcionar) y la búsqueda Haversine sobre el catálogo
completo -- por eso la búsqueda por coordenada funciona igual de bien
aunque la geocodificación esté caída (es justamente el fallback para eso).
"""
import csv
import json
import math
import os
import random
import tempfile
import time
import zipfile

import numpy as np
import pandas as pd

_AQUI = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_AQUI)
CARPETA_EPW_REAL = os.path.join(_BASE, "datos_clima", "epw_real")
RUTA_CATALOGO_GLOBAL = os.path.join(_BASE, "datos_clima", "epw_catalog_global.json")

try:
    from geopy.geocoders import Nominatim, Photon
    GEOPY_OK = True
except ImportError:
    GEOPY_OK = False


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
    weather_utils.py::_haversine() de DDP-lite/Skyplus."""
    R = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlon / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def cargar_catalogo_global(ruta=RUTA_CATALOGO_GLOBAL):
    """Catálogo completo: 5,276 estaciones, 20 países (USA/CAN/MEX + 17
    LATAM) -- idéntico (`diff` sin diferencias) al de DDP-lite y Skyplus."""
    with open(ruta, encoding="utf-8") as f:
        return json.load(f)


# ── Mapeo país -> código ISO del catálogo (idéntico a weather_utils.py) ────

_COUNTRY_MAP = {
    "united states": "USA", "united states of america": "USA", "usa": "USA", "us": "USA",
    "mexico": "MEX", "méxico": "MEX",
    "canada": "CAN", "canadá": "CAN",
    "guatemala": "GTM",
    "honduras": "HND",
    "nicaragua": "NIC",
    "el salvador": "SLV",
    "costa rica": "CRI",
    "panama": "PAN", "panamá": "PAN",
    "dominican republic": "DOM", "república dominicana": "DOM", "republica dominicana": "DOM",
    "colombia": "COL",
    "venezuela": "VEN",
    "ecuador": "ECU",
    "peru": "PER", "perú": "PER",
    "bolivia": "BOL",
    "brazil": "BRA", "brasil": "BRA",
    "chile": "CHL",
    "argentina": "ARG",
    "paraguay": "PRY",
    "uruguay": "URY",
}


def _country_to_code(country_name):
    if not country_name:
        return None
    key = country_name.lower().strip()
    if key in _COUNTRY_MAP:
        return _COUNTRY_MAP[key]
    for k, v in _COUNTRY_MAP.items():
        if k in key or key in k:
            return v
    return None


def get_location_info(lat, lon):
    """
    Geocodificación inversa robusta (Photon, luego Nominatim) -- idéntica a
    weather_utils.py::get_location_info(). Retorna (country_name, city_name)
    en inglés, o cae al fallback por bounding box si la red falla (ambos
    hosts de geocodificación están bloqueados en este sandbox, Hallazgo 2).
    """
    user_agents = [
        f"eco_wind_v1_{random.randint(100, 999)}",
        "Mozilla/5.0",
        "ECO Wind/1.0 ECO Consultor",
    ]
    if GEOPY_OK:
        try:
            geo = Photon(user_agent=random.choice(user_agents))
            loc = geo.reverse(f"{lat}, {lon}", timeout=10)
            if loc and "properties" in loc.raw:
                props = loc.raw["properties"]
                country = props.get("country")
                city = props.get("city") or props.get("name")
                if country:
                    return country, city
        except Exception:
            pass
        try:
            time.sleep(0.5)
            geo = Nominatim(user_agent=random.choice(user_agents))
            loc = geo.reverse(f"{lat}, {lon}", language="en", timeout=10)
            if loc and "address" in loc.raw:
                addr = loc.raw["address"]
                country = addr.get("country")
                city = (addr.get("city") or addr.get("town")
                        or addr.get("village") or addr.get("municipality"))
                if country:
                    return country, city
        except Exception:
            pass
    country = _infer_country_from_bbox(lat, lon)
    return country, None


def _infer_country_from_bbox(lat, lon):
    """Fallback rápido, sin red -- bounding boxes de los 20 países del
    catálogo, idéntico a weather_utils.py::_infer_country_from_bbox()."""
    boxes = [
        ("United States", 24.4, 49.4, -125.0, -66.9),
        ("United States", 18.9, 28.5, -168.0, -154.8),
        ("United States", 51.2, 71.5, -179.9, -129.9),
        ("Mexico", 14.5, 32.7, -117.1, -86.7),
        ("Canada", 41.7, 83.1, -141.0, -52.6),
        ("Guatemala", 13.7, 17.8, -92.2, -88.2),
        ("Honduras", 13.0, 16.5, -89.4, -83.1),
        ("Nicaragua", 10.7, 15.0, -87.7, -83.1),
        ("El Salvador", 13.1, 14.5, -90.1, -87.7),
        ("Costa Rica", 8.0, 11.2, -85.9, -82.6),
        ("Panama", 7.2, 9.7, -83.0, -77.2),
        ("Dominican Republic", 17.5, 20.0, -72.1, -68.3),
        ("Colombia", -4.2, 13.4, -79.0, -66.9),
        ("Venezuela", 0.6, 12.2, -73.4, -59.8),
        ("Ecuador", -5.0, 1.5, -81.1, -75.2),
        ("Peru", -18.4, -0.1, -81.4, -68.6),
        ("Bolivia", -22.9, -9.7, -69.6, -57.5),
        ("Brazil", -33.8, 5.3, -73.9, -34.8),
        ("Chile", -55.9, -17.5, -75.6, -66.4),
        ("Argentina", -55.1, -21.8, -73.6, -53.6),
        ("Paraguay", -27.6, -19.3, -62.7, -54.3),
        ("Uruguay", -34.9, -30.1, -58.4, -53.1),
    ]
    for country, lat_min, lat_max, lon_min, lon_max in boxes:
        if lat_min <= lat <= lat_max and lon_min <= lon <= lon_max:
            return country
    return None


def _search_in_codes(lat, lon, catalog, codes, limit):
    candidates = []
    for code in codes:
        for s in catalog.get(code, []):
            if s.get("lat") is None or s.get("lon") is None:
                continue
            dist = _haversine_km(lat, lon, s["lat"], s["lon"])
            candidates.append({
                "name": s.get("name", "Unknown"), "state": s.get("state", ""),
                "country": code, "distancia_km": round(dist, 2), "url": s.get("url", ""),
                "lat": s["lat"], "lon": s["lon"],
            })
    candidates.sort(key=lambda x: x["distancia_km"])
    return candidates[:limit]


def _merge_dedupe(a, b):
    seen = {x["url"] for x in a}
    return a + [x for x in b if x["url"] not in seen]


def _nearest_country_from_catalog(lat, lon, catalog):
    best_code, best_dist = None, float("inf")
    for code, stations in catalog.items():
        for s in stations:
            if s.get("lat") is None:
                continue
            d = _haversine_km(lat, lon, s["lat"], s["lon"])
            if d < best_dist:
                best_dist, best_code = d, code
            if best_dist < 50:
                break
    return best_code


_NEIGHBOR_CODES = {
    "MEX": ["USA", "GTM"], "USA": ["CAN", "MEX"], "CAN": ["USA"],
    "GTM": ["MEX", "HND", "SLV"], "HND": ["GTM", "NIC", "SLV"], "NIC": ["HND", "CRI"],
    "SLV": ["GTM", "HND"], "CRI": ["NIC", "PAN"], "PAN": ["CRI", "COL"], "DOM": ["PAN"],
    "COL": ["PAN", "VEN", "ECU", "PER"], "VEN": ["COL", "BRA"], "ECU": ["COL", "PER"],
    "PER": ["ECU", "COL", "BOL", "CHL", "BRA"], "BOL": ["PER", "CHL", "ARG", "BRA", "PRY"],
    "BRA": ["COL", "VEN", "PER", "BOL", "PRY", "ARG", "URY"], "CHL": ["PER", "BOL", "ARG"],
    "ARG": ["CHL", "BOL", "PRY", "BRA", "URY"], "PRY": ["BOL", "BRA", "ARG"],
    "URY": ["BRA", "ARG"],
}


def obtener_estaciones_cercanas(lat, lon, top_n=6, ruta_catalogo=RUTA_CATALOGO_GLOBAL):
    """
    Búsqueda de estaciones EPW más cercanas a (lat, lon) EN CUALQUIER PARTE
    de los 20 países del catálogo -- port fiel de
    weather_utils.py::obtener_estaciones_cercanas() de DDP-lite/Skyplus, sin
    ninguna restricción geográfica propia de ECO-Wind (Hallazgo 19, v2).

    Estrategia idéntica al original: (1) inferir país por geocodificación
    inversa, con fallback a bounding box si la red falla; (2) buscar en ese
    país; (3) si hay pocas (<3), ampliar a países vecinos; (4) si aún hay
    pocas (<2), buscar en TODOS los países del catálogo -- así cualquier
    coordenada del mundo devuelve algo, aunque esté lejos de los 20 países
    cubiertos (mejor una respuesta lejana y honesta que ninguna).

    Devuelve un DataFrame ordenado por distancia (puede estar vacío).
    """
    catalog = cargar_catalogo_global(ruta_catalogo)
    if not catalog:
        return pd.DataFrame()

    country_name, _ = get_location_info(lat, lon)
    country_code = _country_to_code(country_name) if country_name else None
    if not country_code:
        country_code = _nearest_country_from_catalog(lat, lon, catalog)

    results = _search_in_codes(lat, lon, catalog, [country_code] if country_code else [], top_n * 2)

    if len(results) < 3:
        neighbors = _NEIGHBOR_CODES.get(country_code, [])
        extra = _search_in_codes(lat, lon, catalog, neighbors, top_n * 2)
        results = _merge_dedupe(results, extra)

    if len(results) < 2:
        all_codes = [c for c in catalog.keys() if c != country_code]
        extra = _search_in_codes(lat, lon, catalog, all_codes, top_n)
        results = _merge_dedupe(results, extra)

    if not results:
        return pd.DataFrame()

    results.sort(key=lambda x: x["distancia_km"])
    return pd.DataFrame(results[:top_n])


def geocode_name(name):
    """Geocodifica un nombre de ciudad/país a (lat, lon) -- idéntico a
    weather_utils.py::geocode_name() (Photon, luego Nominatim)."""
    if not GEOPY_OK:
        return None, None
    ua = f"eco_wind_search_{random.randint(100, 999)}"
    for GeoClass in (Photon, Nominatim):
        try:
            geo = GeoClass(user_agent=ua)
            loc = geo.geocode(name, timeout=10)
            if loc:
                return loc.latitude, loc.longitude
            time.sleep(0.5)
        except Exception:
            pass
    return None, None


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


# Coordenadas reales de los 4 sitios con datos propios (del encabezado real
# de su propio EPW/GWA -- no del catálogo, ver la discrepancia de Finca
# Favorita documentada arriba). San José coincide con
# SITIOS_DISPONIBLES["san_jose_juan_santamaria"] de simulador_pista_a.py
# (no se importa para no acoplar los dos módulos -- mismo valor, verificado).
_SITIOS_PRECACHEADOS_COORDS = {
    "san_jose": (10.0034, -84.2033),
    "nicoya": (10.150, -85.450),
    "liberia": (10.593, -85.544),
    "finca_favorita": (9.517, -82.650),
}


def sitio_precacheado_cercano(lat, lon, umbral_km=2.0):
    """
    Hallazgo 19 (v3): parte de consolidar en un solo flujo -- si (lat, lon)
    cae a menos de umbral_km de uno de los 4 sitios que ya tenemos con datos
    propios validados (San José vía GWA, Nicoya/Liberia/Finca Favorita vía
    EPW real, Hallazgo 18), esta función devuelve su clave para que la app
    sirva el dato LOCAL ya validado en vez de descargar de nuevo lo mismo
    desde climate.onebuilding.org -- el usuario no ve ninguna diferencia
    (sigue siendo "elegí una estación real de la lista"), es sólo una
    optimización interna. Match por PROXIMIDAD, no por texto del nombre --
    no depende de que el catálogo escriba el nombre exactamente igual.
    """
    for clave, (slat, slon) in _SITIOS_PRECACHEADOS_COORDS.items():
        if _haversine_km(lat, lon, slat, slon) <= umbral_km:
            return clave
    return None


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
