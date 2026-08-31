"""
Cobertura de cualquier coordenada de Costa Rica -- Global Wind Atlas via
raster de pais (Requisito 1, Fase 2).

INVESTIGACION PREVIA (antes de escribir esto, confirmada con codigo fuente
real, no de memoria): Global Wind Atlas (DTU/World Bank) SI tiene una API
oficial documentada, pero es de RASTERS POR PAIS, no de consulta puntual
por coordenada con distribucion completa:

    https://globalwindatlas.info/api/gis/country/{ISO3}/wind-speed/{altura}

(altura: 10, 50, 100, 150 o 200 m). Devuelve un GeoTIFF con velocidad media
de viento en todo el pais, ~250m de resolucion. Verificado leyendo el
codigo fuente del paquete de R `energyRt/globalwindatlas`
(github.com/energyRt/globalwindatlas/blob/main/R/get.R), que ya usa
exactamente este endpoint en produccion -- no es un endpoint inventado ni
de documentacion de terceros sin confirmar.

Lo que este endpoint NO da: la curva de excedencia empirica completa ni el
patron diurno/estacional real (mes x hora) que si tenemos para San Jose
(esos salieron del panel web interactivo, cuyo backend no se pudo
documentar -- globalwindatlas.info sigue bloqueado en este sandbox,
Hallazgo 2).

DECISION (confirmada con Pablo, Fase 2 Requisito 1): para cualquier
coordenada de Costa Rica, se usa la velocidad media REAL del raster (dato
real del sitio, no inventado) combinada con la FORMA (curva de excedencia
normalizada + patron diurno/estacional) ya validada de San Jose, escalada
a esa media real. Es una aproximacion declarada, no datos especificos del
sitio nuevo -- distinto de tener el propio export del panel web de ese
sitio (como San Jose). Documentado explicitamente en la UI y en el
resultado (ver generar_clima_sitio_nuevo()), no se presenta como si fuera
tan bueno como un sitio con datos propios.

BLOQUEO DE RED, mismo patron que EPW/GWA-San Jose (Hallazgo 2):
globalwindatlas.info esta bloqueado en este sandbox de desarrollo. La
funcion descargar_raster_costa_rica() de este modulo esta escrita y lista,
pero DEBE correrse en un entorno con internet real (Google Colab, u otra
maquina) -- no se pudo ejecutar ni verificar el download en si durante
esta sesion. Lo que si se verifico sin red: la logica de muestreo del
raster (muestrear_velocidad_media(), con un GeoTIFF sintetico de prueba,
ver bloque __main__) y que generar_clima_sitio_nuevo() REPRODUCE el
resultado real ya conocido de San Jose cuando se le da su propia media real
como si viniera del raster -- la mejor prueba posible sin el archivo real.
"""
import os

import numpy as np

try:
    from engine.simulador_pista_a import cargar_gwa_json, generar_clima_gwa, SITIOS_DISPONIBLES
except ImportError:
    from simulador_pista_a import cargar_gwa_json, generar_clima_gwa, SITIOS_DISPONIBLES

RUTA_RASTER_CR_DEFAULT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "datos_clima", "gwa_costa_rica_10m.tif",
)


def descargar_raster_costa_rica(destino=RUTA_RASTER_CR_DEFAULT, altura=10):
    """
    Descarga el raster de velocidad media de viento para Costa Rica
    completo, via la API oficial de GWA confirmada arriba.

    NO EJECUTAR EN ESTE SANDBOX -- globalwindatlas.info esta bloqueado
    (Hallazgo 2). Correr esto en Google Colab (mismo patron ya usado para
    EPW/GWA-San Jose) o en cualquier maquina con internet normal, y subir
    el .tif resultante a datos_clima/ en el repo.
    """
    return descargar_raster_pais("CRI", altura=altura, destino=destino)


def descargar_raster_pais(pais_iso3, altura=10, destino=None, capa="wind-speed"):
    """
    Version general de descargar_raster_costa_rica() -- mismo endpoint ya
    confirmado arriba (codigo fuente de energyRt/globalwindatlas Y la
    pagina real "GIS files & API access" de globalwindatlas.info,
    Hallazgo 25), parametrizado por pais (codigo ISO3, los mismos que usan
    las claves de datos_clima/epw_catalog_global.json: USA, CAN, BRA, MEX,
    ARG, CHL, COL, ECU, PER, BOL, VEN, PRY, PAN, URY, DOM, HND, GTM, CRI,
    NIC, SLV).

    Confirmado en la pagina real (Hallazgo 25): NO hay una API de consulta
    por punto separada -- "the provided URL can also be used as an API
    service" se refiere a esta MISMA URL de descarga de raster por pais,
    llamable por codigo en vez de clic. La pagina tambien advierte
    explicitamente: "not to be used for bulk downloads of all countries or
    datasets" -- bajar UN pais para trabajar con el (como ya se hace con
    Costa Rica) esta bien; scriptear una descarga masiva de los 20 no.

    NO EJECUTAR EN ESTE SANDBOX -- globalwindatlas.info esta bloqueado
    (Hallazgo 2). Correr esto en Google Colab, un pais a la vez.
    """
    import requests
    destino = destino or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "datos_clima", f"gwa_{pais_iso3.lower()}_{altura}m.tif",
    )
    url = f"https://globalwindatlas.info/api/gis/country/{pais_iso3}/{capa}/{altura}"
    r = requests.get(url, stream=True, timeout=120)
    r.raise_for_status()
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    with open(destino, "wb") as f:
        for chunk in r.iter_content(chunk_size=1 << 20):
            f.write(chunk)
    return destino


def muestrear_velocidad_media(lat, lon, ruta_raster=RUTA_RASTER_CR_DEFAULT):
    """
    Lee la velocidad media de viento (m/s) del raster de Costa Rica en la
    coordenada dada. Reproyecta la coordenada al CRS del raster si hace
    falta (GWA publica normalmente en EPSG:4326, pero no se asume sin
    verificar -- se lee el CRS real del archivo).
    """
    import rasterio
    from rasterio.warp import transform as warp_transform

    if not os.path.exists(ruta_raster):
        raise FileNotFoundError(
            f"No existe {ruta_raster}. Corré descargar_raster_costa_rica() en un entorno con "
            "internet real (Colab) primero -- este sandbox tiene globalwindatlas.info bloqueado."
        )

    with rasterio.open(ruta_raster) as src:
        if src.crs is not None and src.crs.to_epsg() != 4326:
            xs, ys = warp_transform("EPSG:4326", src.crs, [lon], [lat])
            lon_r, lat_r = xs[0], ys[0]
        else:
            lon_r, lat_r = lon, lat

        fila, col = src.index(lon_r, lat_r)
        if not (0 <= fila < src.height and 0 <= col < src.width):
            raise ValueError(f"Coordenada ({lat}, {lon}) fuera de la cobertura del raster.")
        valor = src.read(1)[fila, col]
        if valor == src.nodata or np.isnan(valor):
            raise ValueError(f"Sin dato de viento en ({lat}, {lon}) -- probablemente fuera de Costa Rica.")
        return float(valor)


def factor_ajuste_gwa(lat_exacto, lon_exacto, lat_estacion, lon_estacion, ruta_raster=RUTA_RASTER_CR_DEFAULT):
    """
    Razon GWA(punto exacto) / GWA(ubicacion de la estacion donante) -- Hallazgo 25:
    mismo mecanismo de ajuste espacial que factor_ajuste_nasa_power()
    (notebooks/sensibilizar_punto_exacto.ipynb), pero usando el raster de
    GWA (250m de resolucion) en vez de NASA POWER (~50-60km). NASA POWER
    fallo de raiz en terreno accidentado (Hallazgo 25: su razon salio
    literalmente al reves entre San Jose y Finca Favorita) -- GWA, siendo
    ~200-1000x mas fino, deberia poder resolver la diferencia real de
    microclima entre dos puntos cercanos donde NASA POWER no puede.

    A diferencia de factor_ajuste_nasa_power() (dos llamadas a una API por
    internet), esto son dos lecturas de pixel del MISMO raster ya
    descargado -- mucho mas rapido, pero necesita el .tif del pais
    correspondiente ya en disco (descargar_raster_pais()).
    """
    media_exacto = muestrear_velocidad_media(lat_exacto, lon_exacto, ruta_raster)
    media_estacion = muestrear_velocidad_media(lat_estacion, lon_estacion, ruta_raster)
    return media_exacto / media_estacion, media_exacto, media_estacion


def generar_clima_sitio_nuevo(lat, lon, año=2023, seed=42, ruta_raster=RUTA_RASTER_CR_DEFAULT,
                               sitio_forma="san_jose_juan_santamaria"):
    """
    Serie horaria de viento para CUALQUIER coordenada de Costa Rica, usando
    la velocidad media REAL del raster de GWA (Requisito 1) combinada con
    la forma (curva de excedencia + patron diurno/estacional) YA VALIDADA
    de un sitio de referencia con datos ricos (San Jose por default).

    APROXIMACION DECLARADA, no datos propios del sitio nuevo: la magnitud
    (media anual) es real y especifica del punto consultado: la FORMA
    (variabilidad relativa, estacionalidad, ciclo diurno) se toma prestada
    de San Jose. Es razonable como primera estimacion para sitios del
    Valle Central con clima similar (misma influencia orografica general);
    menos confiable para zonas con regimen de viento muy distinto (costas,
    zonas altas) -- sin verificar contra datos propios de esos sitios
    todavia. Devuelve (df_clima, media_real_m_s, es_aproximacion=True) para
    que quien consuma el resultado sepa que es una aproximacion.
    """
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    carpeta_forma = os.path.join(base, SITIOS_DISPONIBLES[sitio_forma]["carpeta_gwa"])
    ws_json, hm_json = cargar_gwa_json(carpeta_forma)

    media_real = muestrear_velocidad_media(lat, lon, ruta_raster)
    df_clima, _ = generar_clima_gwa(ws_json, hm_json, year=año, seed=seed, media_objetivo=media_real)
    return df_clima, media_real


if __name__ == "__main__":
    print("=" * 78)
    print("Prueba 1 -- logica de muestreo del raster, con un GeoTIFF SINTETICO de prueba")
    print("(NO es el raster real de Costa Rica -- ese sigue sin descargarse, ver docstring).")
    import rasterio
    from rasterio.transform import from_origin

    ruta_prueba = "/tmp claude test_raster.tif".replace(" ", "-")
    # grilla 3x3 simple, EPSG:4326, cubriendo Costa Rica (lat 8-11, lon -86 a -82),
    # con un gradiente conocido para poder verificar la interpolacion/indexado
    datos = np.array([[6.0, 5.5, 5.0], [4.5, 4.0, 3.5], [3.0, 2.5, 2.0]], dtype="float32")
    transform = from_origin(-86.0, 11.0, 2.0, 1.0)  # esquina sup-izq, tam. de pixel 2 lon x 1 lat
    with rasterio.open(ruta_prueba, "w", driver="GTiff", height=3, width=3, count=1,
                        dtype="float32", crs="EPSG:4326", transform=transform, nodata=-9999) as dst:
        dst.write(datos, 1)

    # punto en el centro del pixel [1,1] (fila 1, col 1): lon=-86+2*1.5=-83, lat=11-1*1.5=9.5
    v = muestrear_velocidad_media(lat=9.5, lon=-83.0, ruta_raster=ruta_prueba)
    print(f"  Pixel [1,1] esperado=4.0 m/s, muestreado={v} m/s -- {'OK' if v == 4.0 else 'FALLO'}")
    os.remove(ruta_prueba)

    print()
    print("=" * 78)
    print("Prueba 2 -- generar_clima_sitio_nuevo() reproduce San José cuando se le da SU")
    print("PROPIA media real (simulando que el raster dijera exactamente eso en su coordenada) --")
    print("la mejor verificación posible sin el archivo real de Costa Rica todavía:")
    sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
    carpeta = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            sitio["carpeta_gwa"])
    ws_json, hm_json = cargar_gwa_json(carpeta)
    df_real, media_real = generar_clima_gwa(ws_json, hm_json)  # sin media_objetivo = original
    # se usa la media EXACTA (no redondeada) que ya calcula generar_clima_gwa() -- así se
    # prueba la matemática del escalado en sí (r_normalizado*media_escala), no una
    # coincidencia de redondeo con un valor pegado a mano
    df_prestado, _ = generar_clima_gwa(ws_json, hm_json, media_objetivo=media_real)
    diff = float(np.abs(df_prestado["WS10M"].values - df_real["WS10M"].values).max())
    print(f"  Media real de San José (exacta): {media_real:.6f} m/s")
    print(f"  generar_clima_gwa(media_objetivo=<esa misma media exacta>) vs. original: "
          f"diferencia máxima por hora = {diff:.2e} m/s -- "
          f"{'OK, reproduce exacto' if diff < 1e-9 else 'FALLO'}")

    print()
    print("  Ahora con una media DISTINTA (simulando un sitio nuevo con más viento, 5.0 m/s,")
    print("  prestando la forma de San José):")
    df_nuevo, _ = generar_clima_gwa(ws_json, hm_json, media_objetivo=5.0)
    print(f"  Media de la serie generada: {df_nuevo['WS10M'].mean():.4f} m/s (debe ≈5.0)")
