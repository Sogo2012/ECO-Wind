"""
Selección de forma climática por vecino más cercano, entre los 4 sitios con
datos reales (San José, Nicoya, Liberia, Finca Favorita) -- "Alternativa 4"
del pendiente de Hallazgo 18/19, pedida explícitamente por Pablo como la más
fácil de probar antes de ir a algo más sofisticado (zonas de Köppen,
polígonos, ERA5+quantile mapping).

IDEA: `generar_clima_gwa(ws_json, hm_json, media_objetivo=...)` (Hallazgo 17)
ya sabía tomar prestada una forma (curva de excedencia + patrón mes×hora) de
UN sitio y escalarla a la media real de otro -- lo que faltaba, y es lo que
agrega este módulo, es la SELECCIÓN de cuál de los 4 sitios conocidos prestar,
por cercanía geográfica, en vez de tener a San José fijo como única opción
(que es justo lo que Hallazgo 18 encontró que falla -41% a -44% en
Guanacaste).

DE DÓNDE SALE LA FORMA DE CADA SITIO: San José tiene su propio export real
del panel de Global Wind Atlas (windSpeed.json + heatmapData.json,
Hallazgo 3). Los otros 3 NO tienen un export de GWA -- tienen un EPW real
(Hallazgo 18). Para poder comparar/prestar formas entre los 4 con el mismo
mecanismo, `excedencia_json_desde_epw()` (nueva, este módulo) construye una
curva de excedencia en el MISMO formato y la MISMA resolución que el
windSpeed.json real de GWA (verificado: 50 puntos, perc=2,4,...,100,
`val` = percentil (100-perc) de los datos) directo de la serie horaria del
EPW -- `heatmap_json_desde_epw()` (Hallazgo 18, ya existía) hace lo mismo
para el patrón mes×hora.

QUÉ NO ES ESTO TODAVÍA: no está conectado a `app.py` -- es investigación
(Pablo fue explícito: "no conectes nada de esto a app.py... recién se
decide si esto reemplaza la aproximación actual cuando haya números"). Ver
`validar_leave_one_out()` al final para los resultados cuantificados.
"""
import os

import numpy as np
import pandas as pd

try:
    from engine.simulador_pista_a import (
        SITIOS_DISPONIBLES, cargar_gwa_json, generar_clima_gwa, cargar_wind_rose_lib,
        simular, Z0_DEFAULT, Z0_MET_DEFAULT,
    )
    from engine.epw_real import (
        SITIOS_EPW_REAL, cargar_epw_real, heatmap_json_desde_epw, rosa_frecuencia_desde_epw, _haversine_km,
    )
    from engine.flower_turbines_curves import CURVE_COEFFICIENTS
    from engine.gwa_raster import factor_ajuste_gwa, RUTA_RASTER_CR_DEFAULT
except ImportError:
    from simulador_pista_a import (
        SITIOS_DISPONIBLES, cargar_gwa_json, generar_clima_gwa, cargar_wind_rose_lib,
        simular, Z0_DEFAULT, Z0_MET_DEFAULT,
    )
    from epw_real import (
        SITIOS_EPW_REAL, cargar_epw_real, heatmap_json_desde_epw, rosa_frecuencia_desde_epw, _haversine_km,
    )
    from flower_turbines_curves import CURVE_COEFFICIENTS
    from gwa_raster import factor_ajuste_gwa, RUTA_RASTER_CR_DEFAULT

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def excedencia_json_desde_epw(df_clima, n_puntos=50):
    """
    Curva de excedencia empírica en el MISMO formato y resolución que el
    windSpeed.json real de GWA (verificado leyendo
    datos_clima/gwa_juan_santamaria/windSpeed.json: 50 puntos, perc=2,4,...,100
    cada 2, no inventado). Convención confirmada en el propio archivo real:
    "perc" = % de horas con velocidad >= "val" (curva de excedencia, no un
    percentil directo) -- por eso val(perc) = percentil ESTÁNDAR (100-perc)
    de la serie horaria: perc=100 -> percentil 0 (el mínimo, 100% de las
    horas tienen viento >= el mínimo, trivial); perc=2 -> percentil 98 (un
    valor alto, sólo 2% de las horas lo alcanzan o superan).
    """
    ws = np.asarray(df_clima["WS10M"].values, dtype=float)
    percs = np.arange(2, 100 + 1, 100 // (n_puntos - 1) if n_puntos > 1 else 100)[:n_puntos]
    vals = np.percentile(ws, 100 - percs)
    return [{"perc": float(p), "val": float(v)} for p, v in zip(percs, vals)]


def excedencia_json_desde_epw_residual(df_clima, hm_json, n_puntos=50):
    """
    Igual que excedencia_json_desde_epw(), pero construida sobre los
    RESIDUOS (v(t) dividido entre el factor de heatmap de su propio
    mes×hora) en vez de la serie cruda -- arregla (parcialmente, ver
    Hallazgo 21 continuación) el artefacto encontrado ahí: cuando la curva
    se arma de la serie cruda, ya contiene el patrón diurno/estacional
    completo, y generar_clima_gwa() lo vuelve a inyectar al multiplicar
    por el heatmap -- duplica esa variación y por eso E[v^3]/media^3 salía
    ~2x inflado en Guanacaste. Esta versión divide el patrón ANTES de
    construir la curva, para que generar_clima_gwa() lo aplique una sola
    vez. `hm_json` debe ser EXACTAMENTE el mismo heatmap que después se le
    pase a generar_clima_gwa() junto con esta curva -- si no coinciden, la
    corrección no cierra matemáticamente.
    """
    idx_lookup = {(r["month"], r["hour"]): r["value"] for r in hm_json}
    factor = np.array([idx_lookup[(m, h)] for m, h in zip(df_clima.index.month, df_clima.index.hour)])
    ws_residual = df_clima["WS10M"].values / factor
    df_residual = pd.DataFrame({"WS10M": ws_residual}, index=df_clima.index)
    return excedencia_json_desde_epw(df_residual, n_puntos=n_puntos)


def _cargar_forma_san_jose():
    sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
    ws_json, hm_json = cargar_gwa_json(os.path.join(_BASE, sitio["carpeta_gwa"]))
    return dict(nombre=sitio["nombre"], lat=sitio["lat"], lon=sitio["lon"],
                elevacion_m=sitio["elevacion_m"], ws_json=ws_json, hm_json=hm_json)


def _cargar_forma_epw(clave, usar_residuo=False):
    sitio = SITIOS_EPW_REAL[clave]
    df_clima, meta = cargar_epw_real(sitio["ruta_epw"])
    hm_json = heatmap_json_desde_epw(df_clima)
    ws_json = (excedencia_json_desde_epw_residual(df_clima, hm_json) if usar_residuo
               else excedencia_json_desde_epw(df_clima))
    return dict(nombre=sitio["nombre"], lat=meta["lat"], lon=meta["lon"],
                elevacion_m=meta["elevacion_m"], ws_json=ws_json, hm_json=hm_json, df_real=df_clima)


def cargar_formas_conocidas(usar_residuo=False):
    """Las 4 formas reales disponibles hoy -- carga todo en memoria (liviano,
    4 sitios). Devuelve {clave: {nombre, lat, lon, elevacion_m, ws_json,
    hm_json, [df_real si viene de EPW]}}.

    usar_residuo: si True, las 3 formas EPW-derivadas usan
    excedencia_json_desde_epw_residual() (Hallazgo 21 continuación) en vez
    de la curva cruda -- default False para no cambiar por sorpresa los
    números ya documentados en Hallazgo 21; compárense ambas explícitamente.
    San José no se ve afectado (su forma es nativa de GWA, no EPW-derivada).
    """
    formas = {"san_jose": _cargar_forma_san_jose()}
    for clave in SITIOS_EPW_REAL:
        formas[clave] = _cargar_forma_epw(clave, usar_residuo=usar_residuo)
    return formas


def vecino_mas_cercano(lat, lon, formas=None, excluir=None):
    """
    De las formas conocidas (default: las 4 reales), la más cercana a
    (lat, lon) por distancia Haversine -- excluyendo `excluir` si se da
    (para la validación leave-one-out: "cuál sería la más cercana SI no
    conociéramos la propia").

    Devuelve (clave, distancia_km). None si no queda ninguna candidata
    (sólo pasa si se excluye la única disponible).
    """
    formas = formas or cargar_formas_conocidas()
    candidatas = [(k, _haversine_km(lat, lon, v["lat"], v["lon"]))
                  for k, v in formas.items() if k != excluir]
    if not candidatas:
        return None, None
    candidatas.sort(key=lambda x: x[1])
    return candidatas[0]


def generar_clima_prestado(lat, lon, media_objetivo, año=2023, seed=42, formas=None, excluir=None):
    """
    Serie horaria para (lat, lon) usando la media REAL dada (del ráster GWA
    cuando exista, o -- para la validación leave-one-out -- la media real ya
    conocida del propio sitio) combinada con la forma del vecino real más
    cercano entre los 4 conocidos (en vez de tener a San José fijo).

    Devuelve (df_clima, clave_donante, distancia_km).
    """
    formas = formas or cargar_formas_conocidas()
    clave_donante, dist_km = vecino_mas_cercano(lat, lon, formas, excluir=excluir)
    donante = formas[clave_donante]
    df_clima, _ = generar_clima_gwa(donante["ws_json"], donante["hm_json"],
                                     year=año, seed=seed, media_objetivo=media_objetivo)
    return df_clima, clave_donante, dist_km


def _media_real_donante(clave, donante):
    """San José: su media real sale del propio windSpeed.json (no tiene df_real horario,
    es la curva de excedencia real de GWA). Los demás (EPW real): media de su serie horaria."""
    return (float(np.mean([r["val"] for r in donante["ws_json"]])) if clave == "san_jose"
            else float(donante["df_real"]["WS10M"].mean()))


def _rosa_freq_donante(clave, donante):
    """Misma lógica que _media_real_donante() pero para la rosa de vientos -- San José
    tiene su propio export real del panel de GWA (.lib, Hallazgo 3); los demás la sacan de
    su EPW real. En los dos casos es la rosa REAL del donante, nunca la del punto exacto
    (eso no se puede sensibilizar con nada de lo que tenemos hoy -- ver docstring de
    generar_clima_sensibilizado())."""
    if clave == "san_jose":
        sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
        ruta_lib = os.path.join(_BASE, sitio["carpeta_gwa"], "gwc_point_1_10m.lib")
        return cargar_wind_rose_lib(ruta_lib)["freq"]
    return rosa_frecuencia_desde_epw(donante["df_real"])


def generar_clima_sensibilizado(lat, lon, ruta_raster=RUTA_RASTER_CR_DEFAULT, formas=None,
                                 año=2023, seed=42):
    """
    Sensibilización real del punto exacto (Hallazgo 21-30): reemplaza a
    generar_clima_sitio_nuevo() de gwa_raster.py (que siempre prestaba la
    forma de San José y confiaba en el valor crudo del ráster) por el
    mecanismo validado con datos reales -- GWA es la fuente de ajuste que
    le ganó a NASA POWER y a ERA5/CDS en los 4 sitios reales de Costa Rica
    (Hallazgo 25/26/28), y el vecino más cercano real (no siempre San José)
    para la FORMA es mejor que anclar a un solo sitio (Hallazgo 21/22).

    Dos piezas, cada una resuelta por separado:
    1. FORMA (curva de excedencia + patrón mes×hora): del vecino real más
       cercano entre los sitios conocidos (vecino_mas_cercano()) -- no
       necesariamente San José.
    2. MAGNITUD: media real del donante × factor_ajuste_gwa(punto exacto,
       ubicación del donante) -- la razón entre dos lecturas del ráster de
       GWA, que cancela su sesgo sistemático mejor que confiar en su valor
       absoluto en el punto exacto (Hallazgo 25).

    LÍMITE HONESTO, no resuelto por este mecanismo ni por ningún otro
    probado hasta ahora: la ROSA DE VIENTOS (dirección) es siempre la del
    donante, sin ningún ajuste -- no existe (todavía) un mecanismo de
    razón para dirección como el que sí existe para magnitud. Es una
    aproximación declarada, igual que la forma.

    Devuelve un dict con el mismo formato que usa app.py para las otras 3
    rutas (estación precacheada / EPW recién descargado / EPW subido):
    df_clima, media, hm_json, rosa_freq, es_aproximacion=True,
    donante_nombre, distancia_km, factor_ajuste -- estos dos últimos para
    que la app pueda mostrar de qué estación real y con qué factor salió
    el número, en vez de ocultarlo.
    """
    formas = formas or cargar_formas_conocidas(usar_residuo=True)
    clave_donante, dist_km = vecino_mas_cercano(lat, lon, formas)
    donante = formas[clave_donante]

    factor, _, _ = factor_ajuste_gwa(lat, lon, donante["lat"], donante["lon"], ruta_raster=ruta_raster)
    media_donante_real = _media_real_donante(clave_donante, donante)
    media_ajustada = media_donante_real * factor

    df_clima, _ = generar_clima_gwa(donante["ws_json"], donante["hm_json"],
                                     year=año, seed=seed, media_objetivo=media_ajustada)
    rosa_freq = _rosa_freq_donante(clave_donante, donante)

    return dict(df_clima=df_clima, media=media_ajustada, hm_json=donante["hm_json"], rosa_freq=rosa_freq,
                es_aproximacion=True, error=None, donante_nombre=donante["nombre"],
                distancia_km=dist_km, factor_ajuste=factor)


def validar_leave_one_out(modelo="medium_tulip", N=3, altura_buje=3.0, usar_residuo=False):
    """
    Para cada uno de los 4 sitios reales, por turno: tapar su propia forma,
    predecir su producción con su propia media real + la forma del vecino
    real más cercano de los OTROS 3, y comparar contra su producción real ya
    conocida. También calcula, con el MISMO pipeline de hoy (post-Hallazgo
    20, dos rugosidades), el escenario "siempre prestar de San José" para
    poder comparar error nuevo vs. error viejo en igualdad de condiciones.

    NOTA IMPORTANTE sobre los números "viejos" citados en el pedido original
    (Hallazgo 18: -41.0%, -43.6%, +18.4%): esos salieron ANTES de la
    corrección del perfil de viento de Hallazgo 20 (antes se usaba un solo
    z0 para referencia y destino). Para que esta comparación sea manzanas
    con manzanas, acá se recalculan ambos escenarios (siempre-San-José y
    vecino-más-cercano) con el pipeline ACTUAL, ya corregido -- los
    porcentajes de error salen distintos a los citados en el pedido, pero
    es la comparación correcta, no un error de cálculo.

    usar_residuo: ver cargar_formas_conocidas() -- corrección de Hallazgo 21
    (continuación) para el artefacto de doble conteo de varianza. False
    reproduce exactamente los números ya documentados en Hallazgo 21.
    """
    formas = cargar_formas_conocidas(usar_residuo=usar_residuo)
    filas = []
    for clave, sitio in formas.items():
        # "Verdad de terreno": producción real de este sitio con su propia forma real.
        if clave == "san_jose":
            df_real, _ = generar_clima_gwa(sitio["ws_json"], sitio["hm_json"])
            media_real = float(np.mean([r["val"] for r in sitio["ws_json"]]))
        else:
            df_real = sitio["df_real"]
            media_real = float(df_real["WS10M"].mean())
        r_real = simular(df_real, altura_buje, modelo, N, elevacion_m=sitio["elevacion_m"])

        # Predicción NUEVA: forma del vecino real más cercano de los OTROS 3.
        df_vecino, donante, dist_km = generar_clima_prestado(
            sitio["lat"], sitio["lon"], media_real, formas=formas, excluir=clave)
        r_vecino = simular(df_vecino, altura_buje, modelo, N, elevacion_m=sitio["elevacion_m"])
        error_nuevo_pct = (r_vecino["kwh_anual"] / r_real["kwh_anual"] - 1) * 100

        # Predicción VIEJA (para comparar): siempre forma de San José, salvo cuando el
        # sitio evaluado ES San José -- ahí no hay un "siempre San José" que tenga sentido
        # (sería comparar San José contra sí mismo), se deja explícitamente en blanco.
        if clave == "san_jose":
            error_viejo_pct = None
            kwh_viejo = None
        else:
            df_sj, _ = generar_clima_gwa(formas["san_jose"]["ws_json"], formas["san_jose"]["hm_json"],
                                          media_objetivo=media_real)
            r_sj = simular(df_sj, altura_buje, modelo, N, elevacion_m=sitio["elevacion_m"])
            kwh_viejo = r_sj["kwh_anual"]
            error_viejo_pct = (kwh_viejo / r_real["kwh_anual"] - 1) * 100

        filas.append(dict(
            sitio=sitio["nombre"], clave=clave, media_real_m_s=media_real,
            kwh_real=r_real["kwh_anual"], donante_nuevo=formas[donante]["nombre"],
            distancia_km=dist_km, kwh_nuevo=r_vecino["kwh_anual"], error_nuevo_pct=error_nuevo_pct,
            kwh_viejo_san_jose=kwh_viejo, error_viejo_pct=error_viejo_pct,
        ))
    return pd.DataFrame(filas)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    pd.set_option("display.float_format", lambda x: f"{x:.2f}")

    print("=" * 100)
    print("Verificación: excedencia_json_desde_epw() replica el formato real de windSpeed.json de GWA")
    print("=" * 100)
    sj_gwa = _cargar_forma_san_jose()
    print(f"  windSpeed.json real de San José: {len(sj_gwa['ws_json'])} puntos, "
          f"perc {sj_gwa['ws_json'][0]['perc']}-{sj_gwa['ws_json'][-1]['perc']}")
    ruta_epw_sj = os.path.join(_BASE, "datos_clima",
                                "CRI_AL_San.Jose-Santamaria.Intl.AP.787620_TMYx.2007-2021.epw")
    if os.path.exists(ruta_epw_sj):
        df_sj_epw, _ = cargar_epw_real(ruta_epw_sj)
        ws_derivado = excedencia_json_desde_epw(df_sj_epw)
        print(f"  Derivado del EPW de San José: {len(ws_derivado)} puntos, "
              f"perc {ws_derivado[0]['perc']}-{ws_derivado[-1]['perc']} -- "
              f"{'OK, mismo formato' if len(ws_derivado) == len(sj_gwa['ws_json']) else 'FALLO'}")

    print()
    print("=" * 100)
    print(f"Validación leave-one-out -- {len(cargar_formas_conocidas())} sitios reales, "
          f"medium_tulip×3, buje 3.0m, pipeline actual (post-Hallazgo 20)")
    print("=" * 100)
    resultado = validar_leave_one_out()
    print(resultado.to_string(index=False))

    print()
    print("=" * 100)
    print("Misma validación CON la corrección de curva por residuos (Hallazgo 22, usar_residuo=True)")
    print("=" * 100)
    resultado_residuo = validar_leave_one_out(usar_residuo=True)
    print(resultado_residuo.to_string(index=False))
