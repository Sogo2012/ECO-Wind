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

ECO-Wind no tiene (todavía) un catálogo pre-scrapeado propio -- construir
uno análogo a epw_catalog_global.json queda pendiente. Lo que SÍ se adopta
aquí, ya en este módulo: (a) un parser EPW genérico y liviano (sin
depender de ladybug, que DDP-lite sí usa pero que no es dependencia de
ECO-Wind todavía), reutilizable para cualquier .epw nuevo, San José
incluido si algún día se reemplaza el export manual de GWA por su propio
EPW real; (b) el mismo concepto de "EPW personalizado" vía uploader en la
app (ver app/app.py).
"""
import csv
import os

import numpy as np
import pandas as pd

_AQUI = os.path.dirname(os.path.abspath(__file__))
_BASE = os.path.dirname(_AQUI)
CARPETA_EPW_REAL = os.path.join(_BASE, "datos_clima", "epw_real")


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
