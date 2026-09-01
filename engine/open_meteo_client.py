"""
Open-Meteo (archive-api.open-meteo.com) como cuarta fuente candidata para
el ajuste espacial del punto exacto (Hallazgo 25/26/27/28+ -- ver
notebooks/sensibilizar_punto_exacto.ipynb, Parte 5). Investigado por Pablo
(informe de investigación externo) mientras ERA5/CDS estaba atascado en la
cola de Copernicus por más de 40 minutos -- confirmado con el dashboard
en vivo de CDS (https://cds.climate.copernicus.eu/live) que el sistema
tenía ~4,361 pedidos en cola contra solo ~435 corriendo, así que la
demora no era un bug de nuestro lado, es congestión real del servicio.

MISMO MECANISMO que factor_ajuste_nasa_power()/factor_ajuste_gwa()/
factor_ajuste_era5(): la razón fuente(punto_exacto) / fuente(estación
donante) para escalar la forma REAL de la estación donante -- no el valor
absoluto de la fuente en ningún punto, que sabemos sesgado como cualquier
reanálisis/producto de grilla.

POR QUÉ ESTA FUENTE: a diferencia de CDS/ERA5 (cuenta, token, aceptar
licencia por dataset, cola de minutos-a-horas), Open-Meteo no pide ningún
registro ni API key para uso no comercial (CC BY 4.0), responde HTTP GET
simple casi al instante, y sirve ERA5-Land (~9km/0.1°, más fino que el
ERA5 estándar de ~31km/0.25° que usa CDS) además del ERA5 estándar --
confirmado por WebSearch contra la documentación oficial
(open-meteo.com/en/docs/historical-weather-api), 1 de septiembre 2026.
NO verificado en vivo todavía -- open-meteo.com está bloqueado en este
sandbox (mismo problema que GWA/CDS/Figshare) -- correr esto en Colab
antes de confiar en el formato exacto de la respuesta o en los límites
reales de uso gratuito (no confirmados con una llamada real todavía).

ENDPOINT (de la documentación, no adivinado): GET
https://archive-api.open-meteo.com/v1/archive con parámetros latitude,
longitude, start_date/end_date (YYYY-MM-DD), hourly=wind_speed_10m,
models=era5_land, wind_speed_unit=ms. Respuesta JSON con hourly.time
(lista ISO8601) y hourly.wind_speed_10m (lista de floats).
"""
import pandas as pd
import requests

URL_ARCHIVO = "https://archive-api.open-meteo.com/v1/archive"


def fetch_open_meteo_hourly(lat, lon, year, modelo="era5_land"):
    """
    Descarga un año completo de viento horario a 10m desde Open-Meteo
    (ERA5-Land por defecto, ~9km) para una coordenada -- sin API key, sin
    cola. NO ejecutar en este sandbox (open-meteo.com bloqueado); correr
    en Colab.
    """
    parametros = {
        "latitude": lat,
        "longitude": lon,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": "wind_speed_10m",
        "models": modelo,
        "wind_speed_unit": "ms",
        "timezone": "UTC",
    }
    r = requests.get(URL_ARCHIVO, params=parametros, timeout=60)
    r.raise_for_status()
    return _parsear_respuesta_open_meteo(r.json())


def _parsear_respuesta_open_meteo(datos):
    """
    Separado de fetch_open_meteo_hourly() para poder probarlo con una
    respuesta JSON sintética sin necesitar red (ver bloque __main__) --
    la parte que de verdad se puede verificar sin salir de este sandbox.
    """
    horario = datos["hourly"]
    tiempos = pd.to_datetime(horario["time"])
    return pd.DataFrame({"WS10M": horario["wind_speed_10m"]}, index=tiempos).sort_index()


def factor_ajuste_open_meteo(lat_exacto, lon_exacto, lat_estacion, lon_estacion, year=2023, modelo="era5_land"):
    """
    Razón Open-Meteo(punto exacto) / Open-Meteo(ubicación de la estación
    donante) -- mismo mecanismo que factor_ajuste_nasa_power()/
    factor_ajuste_gwa()/factor_ajuste_era5(), pero con Open-Meteo/ERA5-Land
    (~9km, sin fricción de acceso) en vez de CDS/ERA5 estándar (~31km, con
    cuenta+token+licencia+cola).
    """
    media_exacto = fetch_open_meteo_hourly(lat_exacto, lon_exacto, year, modelo)["WS10M"].mean()
    media_estacion = fetch_open_meteo_hourly(lat_estacion, lon_estacion, year, modelo)["WS10M"].mean()
    return media_exacto / media_estacion, media_exacto, media_estacion


if __name__ == "__main__":
    print("=" * 78)
    print("Prueba -- parseo de una respuesta JSON sintética con la forma real")
    print("documentada de Open-Meteo (no es una descarga real, solo verifica que")
    print("_parsear_respuesta_open_meteo() lee bien hourly.time/wind_speed_10m)")
    print("antes de gastar una consulta real.")
    print("=" * 78)

    respuesta_sintetica = {
        "latitude": 10.0,
        "longitude": -84.5,
        "hourly": {
            "time": ["2023-01-01T00:00", "2023-01-01T01:00", "2023-01-01T02:00"],
            "wind_speed_10m": [3.0, 4.0, 5.0],
        },
    }
    df = _parsear_respuesta_open_meteo(respuesta_sintetica)
    esperado = (3.0 + 4.0 + 5.0) / 3
    print(f"  media WS10M = {df['WS10M'].mean():.3f} m/s (esperado {esperado:.3f}) -- "
          f"{'OK' if abs(df['WS10M'].mean() - esperado) < 1e-9 else 'FALLO'}")
    print(f"  {len(df)} horas, índice datetime: {df.index[0]} .. {df.index[-1]}")
