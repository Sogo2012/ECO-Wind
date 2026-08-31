"""
ERA5 (Copernicus Climate Data Store) como tercera fuente candidata para el
ajuste espacial del punto exacto (Hallazgo 25/26 -- ver
notebooks/sensibilizar_punto_exacto.ipynb). Pablo decidió seguir con ERA5
después de que NASA POWER fallara de raíz (Hallazgo 25) y GWA diera un
resultado mixto -- mejor que NASA POWER, pero con el ráster crudo alejado
de la realidad en San José y Finca Favorita (Hallazgo 26). GWA queda
pausado como algo para afinar más adelante, no descartado.

MISMO MECANISMO que factor_ajuste_nasa_power()/factor_ajuste_gwa(): la
razón ERA5(punto exacto) / ERA5(ubicación de la estación donante) para
escalar la forma REAL de la estación donante -- no el valor absoluto de
ERA5 en ningún punto, que sabemos sesgado como cualquier reanálisis/
producto de grilla (aunque ERA5, a ~31km, es más fino que NASA POWER,
~50-60km).

ACCESO -- requiere que Pablo tenga una cuenta y token de Copernicus CDS
(investigado en Hallazgo 21, confirmado alcanzable desde Colab en
Hallazgo 23): registrarse gratis en https://cds.climate.copernicus.eu/,
copiar el "Personal Access Token" de la página de perfil, y guardarlo en
$HOME/.cdsapirc:

    url: https://cds.climate.copernicus.eu/api
    key: <PERSONAL-ACCESS-TOKEN>

Después aceptar los Términos y Condiciones del dataset ERA5 (paso aparte
del registro general, se hace una vez en la página del dataset). Sin
esto, cdsapi.Client() falla al autenticar -- no hay forma de saltearlo.

API CONFIRMADA (no adivinada, verificada con WebSearch contra la
documentación real de ecmwf/cdsapi y la página de "how-to-api" de CDS,
31 de agosto 2026 -- la CDS API tuvo una migración real "legacy -> new"
reciente, así que no se asume el formato viejo): dataset
"reanalysis-era5-single-levels", parámetros como LISTAS (year/month/day/
time), clave "data_format" (no "format", que era el nombre viejo).

FORMATO DE RESPUESTA -- sin confirmar en vivo (CDS bloqueado en este
sandbox, Hallazgo 2): ERA5 devuelve un NetCDF con variables u10/v10
(nombres cortos ya establecidos hace años para
10m_u_component_of_wind/10m_v_component_of_wind -- viento como vector,
no como magnitud directa, hay que calcular sqrt(u²+v²)) y dimensiones
latitude/longitude + una dimensión de tiempo cuyo nombre SÍ cambió
recientemente entre versiones de CDS ("time" en exports viejos,
"valid_time" en algunos nuevos) -- este módulo prueba los dos nombres
posibles en vez de asumir uno solo. La lógica de selección del punto de
grilla más cercano y cálculo de magnitud SÍ se probó, con un NetCDF
sintético de prueba (ver bloque __main__) -- no la descarga real todavía.
"""
import os
import tempfile

import numpy as np
import pandas as pd

_POSIBLES_NOMBRES_TIEMPO = ("valid_time", "time")


def fetch_era5_hourly(lat, lon, year, margen_grados=0.15):
    """
    Descarga un año completo de viento horario a 10m de ERA5 (componentes
    u/v) en un pequeño recuadro alrededor de (lat, lon), vía cdsapi, y
    devuelve un DataFrame con índice datetime horario y columna WS10M
    (magnitud del vector viento, no una de sus componentes).

    NO EJECUTAR EN ESTE SANDBOX -- cds.climate.copernicus.eu está
    bloqueado (Hallazgo 2) y además hace falta credencial real (ver
    docstring del módulo). Correr en Colab, con $HOME/.cdsapirc ya
    configurado.

    A diferencia de NASA POWER (JSON, respuesta casi instantánea) o GWA
    (raster, descarga directa), el CDS procesa el pedido en una cola --
    puede tardar minutos, a veces bastante más si la cola está ocupada.
    """
    import cdsapi

    cliente = cdsapi.Client()
    ruta = tempfile.mktemp(suffix=".nc")
    cliente.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": ["reanalysis"],
            "variable": ["10m_u_component_of_wind", "10m_v_component_of_wind"],
            "year": [str(year)],
            "month": [f"{m:02d}" for m in range(1, 13)],
            "day": [f"{d:02d}" for d in range(1, 32)],
            "time": [f"{h:02d}:00" for h in range(24)],
            "area": [lat + margen_grados, lon - margen_grados, lat - margen_grados, lon + margen_grados],
            "data_format": "netcdf",
        },
        ruta,
    )
    try:
        return _parsear_era5_netcdf(ruta, lat, lon)
    finally:
        if os.path.exists(ruta):
            os.remove(ruta)


def _parsear_era5_netcdf(ruta_nc, lat, lon):
    """
    Separado de fetch_era5_hourly() para poder probarlo con un NetCDF
    sintético sin necesitar red (ver bloque __main__) -- la parte que de
    verdad se puede verificar sin credencial de CDS.
    """
    import xarray as xr

    with xr.open_dataset(ruta_nc) as ds:
        punto = ds.sel(latitude=lat, longitude=lon, method="nearest")

        nombre_tiempo = next((n for n in _POSIBLES_NOMBRES_TIEMPO if n in punto.dims or n in punto.coords), None)
        if nombre_tiempo is None:
            raise KeyError(
                f"No se encontró una dimensión de tiempo reconocida en el NetCDF de ERA5 -- "
                f"se probaron {_POSIBLES_NOMBRES_TIEMPO}, dims disponibles: {list(ds.dims)}."
            )

        u10 = punto["u10"].values
        v10 = punto["v10"].values
        ws = np.sqrt(u10 ** 2 + v10 ** 2)
        tiempos = pd.to_datetime(punto[nombre_tiempo].values)

    return pd.DataFrame({"WS10M": ws}, index=tiempos).sort_index()


def factor_ajuste_era5(lat_exacto, lon_exacto, lat_estacion, lon_estacion, year=2023):
    """
    Razón ERA5(punto exacto) / ERA5(ubicación de la estación donante) --
    mismo mecanismo que factor_ajuste_nasa_power()/factor_ajuste_gwa()
    (notebooks/sensibilizar_punto_exacto.ipynb, Hallazgo 25/26), pero con
    ERA5 (~31km) en vez de NASA POWER (~50-60km) o el ráster de GWA
    (250m, pero con valores crudos alejados de la realidad en 2 de los 4
    sitios conocidos, Hallazgo 26).
    """
    media_exacto = fetch_era5_hourly(lat_exacto, lon_exacto, year)["WS10M"].mean()
    media_estacion = fetch_era5_hourly(lat_estacion, lon_estacion, year)["WS10M"].mean()
    return media_exacto / media_estacion, media_exacto, media_estacion


if __name__ == "__main__":
    print("=" * 78)
    print("Prueba -- parseo de NetCDF sintético (mismo patrón que el test de rasterio")
    print("en gwa_raster.py): NO es una descarga real de ERA5, sólo verifica que")
    print("_parsear_era5_netcdf() lee bien la grilla, elige el punto más cercano, y")
    print("calcula la magnitud del viento a partir de u/v -- antes de gastar una consulta")
    print("real (y credencial real) contra el CDS.")
    print("=" * 78)

    import xarray as xr

    ruta_prueba = "/tmp/claude-test-era5.nc"
    lats = np.array([10.5, 10.0, 9.5])
    lons = np.array([-85.0, -84.5, -84.0])
    tiempos_prueba = pd.date_range("2023-01-01", periods=3, freq="h")

    # u=3, v=4 en el punto central (10.0, -84.5) -> magnitud esperada = 5.0 (3-4-5 clásico)
    u10 = np.zeros((3, 3, 3))
    v10 = np.zeros((3, 3, 3))
    u10[:, 1, 1] = 3.0
    v10[:, 1, 1] = 4.0

    ds_prueba = xr.Dataset(
        {"u10": (["valid_time", "latitude", "longitude"], u10),
         "v10": (["valid_time", "latitude", "longitude"], v10)},
        coords={"valid_time": tiempos_prueba, "latitude": lats, "longitude": lons},
    )
    ds_prueba.to_netcdf(ruta_prueba)

    df = _parsear_era5_netcdf(ruta_prueba, lat=10.0, lon=-84.5)
    print(f"  Punto (10.0, -84.5): media WS10M = {df['WS10M'].mean():.3f} m/s "
          f"(esperado 5.0, triángulo 3-4-5) -- {'OK' if abs(df['WS10M'].mean() - 5.0) < 1e-9 else 'FALLO'}")
    print(f"  {len(df)} horas, índice datetime: {df.index[0]} .. {df.index[-1]}")
    os.remove(ruta_prueba)
