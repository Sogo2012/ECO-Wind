"""
ECO | Wind -- Simulador de microgeneración eólica (Fase 2).

Sobre el motor validado de Pista A (engine/simulador_pista_a.py +
engine/flower_turbines_curves.py, Hallazgo 12), extendido con clima
multi-sitio, corrección de densidad, multi-clúster y gráficos (Hallazgo 17
-- ver avance-de-proyecto.md).

ALCANCE HONESTO:
- Un solo flujo de clima, homologado con DDP-lite/Skyplus (Hallazgo 19,
  v3): buscás tu sitio por nombre, coordenada o clic en el mapa, la app te
  muestra las estaciones climáticas REALES más cercanas (catálogo de
  climate.onebuilding.org, 5,276 estaciones, 20 países -- sin acotar a
  Costa Rica), y elegís una. No hay "modos" que elegir de antemano.
- San José, Nicoya, Liberia y Finca Favorita (Limón) ya están validados
  localmente (San José vía export del panel de Global Wind Atlas -- curva
  de excedencia + patrón diurno reales -- los otros 3 vía EPW real de
  climate.onebuilding.org, Hallazgo 18): si la búsqueda te devuelve una de
  estas 4 estaciones, la app sirve ese dato local en vez de descargar de
  nuevo lo mismo -- invisible para vos, sigue siendo "elegí una estación
  real de la lista" (ver engine/epw_real.py::sitio_precacheado_cercano()).
- Si la estación real más cercana a tu punto queda a más de
  UMBRAL_APROXIMACION_KM, la app ofrece AL LADO (mismo flujo, no una
  pantalla aparte) una sensibilización del punto exacto (Hallazgo 21-30,
  engine/formas_regionales.py::generar_clima_sensibilizado()): forma
  (estacionalidad, ciclo diurno) del vecino real más cercano entre los
  sitios conocidos (no siempre San José) + magnitud ajustada con la razón
  entre dos lecturas del ráster de GWA en ese punto y en la ubicación del
  donante -- GWA es la fuente de ajuste validada como mejor contra NASA
  POWER y ERA5/CDS en los 4 sitios reales de Costa Rica (Hallazgo 25/26/28).
  La dirección del viento (rosa) sigue siendo la del donante sin ajuste --
  no existe un mecanismo de razón para dirección, sólo para magnitud. El
  ráster no se pudo descargar en este entorno de desarrollo
  (globalwindatlas.info bloqueado, Hallazgo 2) -- si no existe el archivo,
  la opción simplemente no aparece, en vez de fallar oscuro.
- ¿Tenés el EPW real de tu sitio? Subilo directo -- opción secundaria
  discreta (mismo patrón que DDP-lite/Skyplus), no compite con la
  búsqueda de arriba.
- Elevación: de la estación real (encabezado del EPW, o AIP/DGAC para San
  José) siempre que hay una estación real elegida; sólo se pide manual
  cuando se usa la aproximación (el ráster no trae elevación -- búsqueda
  automática por DEM pendiente, Hallazgo 17).
- Sin PDF, sin registro de leads todavía.
- Corre local; despliegue a Cloud Run sigue pendiente.
"""
import os
import sys
import tempfile

import folium
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_folium import st_folium

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulador_pista_a import (
    SITIOS_DISPONIBLES, cargar_gwa_json, generar_clima_gwa, cargar_wind_rose_lib,
    simular, comparar_metodo_ingenuo_vs_horario, wind_at_height_potencia,
)
from engine.flower_turbines_curves import CURVE_COEFFICIENTS
from engine.gwa_raster import RUTA_RASTER_CR_DEFAULT
from engine.formas_regionales import generar_clima_sensibilizado
from engine.epw_real import (
    SITIOS_EPW_REAL, cargar_epw_real, heatmap_json_desde_epw, rosa_frecuencia_desde_epw,
    obtener_estaciones_cercanas, geocode_name, descargar_y_extraer_epw, sitio_precacheado_cercano,
)

# Hallazgo 19 (v3): a partir de qué distancia a la estación real más cercana la app ofrece
# la sensibilización del punto exacto (Hallazgo 21-30) como alternativa. Es una decisión de
# producto, no un valor medido -- Costa Rica es topográficamente compartimentada (cordilleras
# separan microclimas a distancias cortas), así que 40 km ya es generoso, no conservador.
# Documentado explícitamente para que Pablo lo ajuste si no es el número correcto.
UMBRAL_APROXIMACION_KM = 40.0

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Paleta corporativa ECO (plan-tecnico-eco-wind.md, seccion 5) ---
AZUL = "#003C52"
VERDE = "#4A7C2F"
GRIS = "#4A5568"
FONDO = "#E8F0F3"

NOMBRES_MODELO = {
    "small_tulip": "Small Tulip (1.15m pala)",
    "medium_tulip": "Medium Tulip (2m pala)",
    "three_m_tulip": "3-M Tulip (3m pala)",
    "large_tulip": "Large Tulip (5m pala)",
    "al13_2m": "AL13 Power Tower (2 módulos)",
    "al13_4m": "AL13 Power Tower (4 módulos)",
    "al13_6m": "AL13 Power Tower (6 módulos)",
    "al13_8m": "AL13 Power Tower (8 módulos, sin verificar aún -- Hallazgo 11)",
}
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]

st.set_page_config(page_title="ECO | Wind — Simulador", page_icon="🌬️", layout="wide")

st.markdown(f"""
<style>
    .stApp {{ background-color: {FONDO}; }}
    h1, h2, h3 {{ color: {AZUL}; }}
    .stButton>button, button[kind="primary"], button[kind="primaryFormSubmit"] {{
        background-color: {VERDE} !important; color: white !important; border: none !important;
    }}
</style>
""", unsafe_allow_html=True)

st.title("🌬️ ECO | Wind — Simulador de microgeneración")
st.caption("Ver avance-de-proyecto.md (Hallazgos 1-3, 16-17) para el detalle técnico completo.")

if "clusters" not in st.session_state:
    st.session_state.clusters = [{"modelo": "medium_tulip", "N": 3, "altura_buje": 3.0}]

if "sitio_lat" not in st.session_state:
    st.session_state.sitio_lat, st.session_state.sitio_lon = 9.9, -84.0
    st.session_state.sitio_cercanas = None
    st.session_state.sitio_activo, st.session_state.sitio_nombre_activo = None, None


# --- Helpers de clima/geometría ---

def _rosa_y_heatmap_san_jose():
    sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
    ws_json, hm_json = cargar_gwa_json(os.path.join(BASE_DIR, sitio["carpeta_gwa"]))
    ruta_lib = os.path.join(BASE_DIR, sitio["carpeta_gwa"], "gwc_point_1_10m.lib")
    rosa_freq = cargar_wind_rose_lib(ruta_lib)["freq"]
    return ws_json, hm_json, rosa_freq


def _resultado_desde_epw(df_clima, meta):
    """Arma el dict unificado (mismo formato para las 3 rutas que terminan en un EPW
    real: precacheado, recién descargado, o subido por el usuario)."""
    hm_json = heatmap_json_desde_epw(df_clima)
    rosa_freq = rosa_frecuencia_desde_epw(df_clima)
    return dict(df_clima=df_clima, media=float(df_clima["WS10M"].mean()), hm_json=hm_json,
                rosa_freq=rosa_freq, es_aproximacion=False, elevacion_m=meta["elevacion_m"],
                error=None, meta=meta)


def _resultado_san_jose():
    """San José usa el export real de GWA (curva de excedencia + patrón mes×hora propios,
    Hallazgo 3) en vez de un EPW -- es el único de los 4 sitios precacheados así."""
    sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
    ws_json, hm_json, rosa_freq = _rosa_y_heatmap_san_jose()
    df_clima, media = generar_clima_gwa(ws_json, hm_json)
    meta = dict(estacion="San José (Juan Santamaría)", pais="Costa Rica", wmo="787620",
                lat=sitio["lat"], lon=sitio["lon"], elevacion_m=sitio["elevacion_m"])
    return dict(df_clima=df_clima, media=media, hm_json=hm_json, rosa_freq=rosa_freq,
                es_aproximacion=False, elevacion_m=sitio["elevacion_m"], error=None, meta=meta)


def cargar_estacion_elegida(row):
    """
    Hallazgo 19 (v3): un solo camino para "el usuario eligió una estación real de la
    lista" -- mismo patrón que DDP-lite/Skyplus (obtener_estaciones_cercanas() +
    descargar_y_extraer_epw()). Si la estación elegida coincide (por proximidad, no por
    texto) con uno de los 4 sitios que ya tenemos validados localmente (San José vía GWA,
    Nicoya/Liberia/Finca Favorita vía EPW real, Hallazgo 18), sirve ese dato local en vez
    de descargar de nuevo lo mismo -- invisible para el usuario, sigue siendo "elegí una
    estación real y ya".
    """
    clave = sitio_precacheado_cercano(row["lat"], row["lon"]) if pd.notna(row.get("lat")) else None
    if clave == "san_jose":
        return _resultado_san_jose()
    if clave in SITIOS_EPW_REAL:
        df_clima, meta = cargar_epw_real(SITIOS_EPW_REAL[clave]["ruta_epw"])
        return _resultado_desde_epw(df_clima, meta)
    try:
        ruta = descargar_y_extraer_epw(row["url"])
        df_clima, meta = cargar_epw_real(ruta)
        return _resultado_desde_epw(df_clima, meta)
    except Exception as e:
        return dict(error=(
            f"No se pudo descargar {row['name']}: {e} -- necesita internet real "
            "(no funciona en este sandbox de desarrollo, Hallazgo 2)."
        ))


def cargar_epw_subido(ruta):
    """EPW propio subido por el usuario -- opción secundaria discreta (mismo patrón que
    DDP-lite/Skyplus), no un modo aparte: llega al mismo resultado unificado que elegir
    una estación de la lista."""
    try:
        df_clima, meta = cargar_epw_real(ruta)
    except (FileNotFoundError, ValueError, KeyError) as e:
        return dict(error=str(e))
    return _resultado_desde_epw(df_clima, meta)


def cargar_aproximacion(lat, lon, elevacion_m):
    """
    Sensibilización real del punto exacto (Hallazgo 21-30, engine/formas_regionales.py::
    generar_clima_sensibilizado()) -- desde Hallazgo 19 (v3) YA NO es un modo que el
    usuario elige de entrada: la app la ofrece sola, dentro del mismo flujo de búsqueda,
    sólo cuando la estación real más cercana queda a más de UMBRAL_APROXIMACION_KM (ver
    arriba). Reemplaza el mecanismo viejo (generar_clima_sitio_nuevo(), siempre forma de
    San José + valor crudo del ráster) por el validado con datos reales: vecino más
    cercano real para la FORMA (no siempre San José) + razón GWA(punto exacto)/GWA(donante)
    para la MAGNITUD -- GWA le ganó a NASA POWER y a ERA5/CDS en los 4 sitios reales de
    Costa Rica (Hallazgo 25/26/28). La rosa de vientos (dirección) sigue siendo la del
    donante sin ajuste -- no existe un mecanismo de razón para dirección, sólo para
    magnitud (límite honesto, ver docstring de generar_clima_sensibilizado()).
    """
    if not os.path.exists(RUTA_RASTER_CR_DEFAULT):
        return dict(error=(
            f"No existe el ráster de Costa Rica ({os.path.basename(RUTA_RASTER_CR_DEFAULT)}). "
            "Hay que descargarlo primero desde un entorno con internet real (Colab) -- "
            "ver engine/gwa_raster.py, descargar_raster_costa_rica()."
        ))
    try:
        resultado = generar_clima_sensibilizado(lat, lon)
    except (FileNotFoundError, ValueError, KeyError) as e:
        return dict(error=str(e))
    resultado["elevacion_m"] = elevacion_m
    return resultado


# --- Helpers de gráficos ---

def graficar_rosa_vientos(freq_por_sector):
    fig = plt.figure(figsize=(4, 4))
    ax = fig.add_subplot(111, polar=True)
    ax.set_theta_zero_location("N")
    ax.set_theta_direction(-1)
    n = len(freq_por_sector)
    angulos = np.linspace(0, 2 * np.pi, n, endpoint=False)
    ancho = 2 * np.pi / n * 0.9
    ax.bar(angulos, freq_por_sector, width=ancho, color=VERDE, edgecolor="white", linewidth=0.8)
    ax.set_xticks(np.linspace(0, 2 * np.pi, 4, endpoint=False))
    ax.set_xticklabels(["N", "E", "S", "O"])
    ax.set_ylabel("")
    ax.set_title("Frecuencia por dirección (%)", pad=15, color=AZUL)
    fig.tight_layout()
    return fig


def graficar_heatmap_clima(heatmap_json):
    grid = np.zeros((12, 24))
    for r in heatmap_json:
        grid[r["month"] - 1, r["hour"]] = r["value"]
    fig, ax = plt.subplots(figsize=(8, 3.5))
    im = ax.imshow(grid, aspect="auto", cmap="Greens", origin="lower")
    ax.set_xlabel("Hora del día")
    ax.set_yticks(range(12))
    ax.set_yticklabels(MESES)
    ax.set_title("Índice de viento relativo a la media anual (mes × hora)", color=AZUL)
    fig.colorbar(im, ax=ax, label="Índice (1.0 = media anual)")
    fig.tight_layout()
    return fig


def graficar_curva_duracion(serie_w):
    ordenado = np.sort(serie_w.values)[::-1]
    pct_horas = np.arange(1, len(ordenado) + 1) / len(ordenado) * 100
    fig, ax = plt.subplots(figsize=(8, 3.5))
    ax.fill_between(pct_horas, ordenado, color=VERDE, alpha=0.25)
    ax.plot(pct_horas, ordenado, color=VERDE, linewidth=1.5)
    ax.set_xlabel("% de las 8,760 horas del año (ordenadas de mayor a menor producción)")
    ax.set_ylabel("Potencia (W, total del proyecto)")
    ax.set_title("Curva de duración -- resolución horaria completa", color=AZUL)
    fig.tight_layout()
    return fig


# --- Layout ---
# Cuatro pestañas de nivel superior, mismo espíritu de Skyplus/DDP-lite (Hallazgo 19):
# el mapa es el protagonista de "SELECCIÓN DE CLIMA", el contexto climático (rosa de
# vientos + heatmap) vive aparte en "CONTEXTO CLIMÁTICO" -- desacoplado del botón de
# cálculo, para que se pueda ver apenas se elige un sitio -- y la configuración de
# turbinas/parámetros queda en su propia pestaña, separada de los resultados.

if st.session_state.get("sitio_activo"):
    st.success(f"📍 Sitio activo: {st.session_state.get('sitio_nombre_activo')}")
else:
    st.info("📍 Sin sitio seleccionado -- elegí uno en \"SELECCIÓN DE CLIMA\".")

tab_clima, tab_contexto, tab_config, tab_resultados = st.tabs([
    "SELECCIÓN DE CLIMA", "CONTEXTO CLIMÁTICO",
    "CONFIGURACIÓN DEL PROYECTO", "RESULTADOS FINANCIEROS",
])


# --- Tab 1: Selección de clima -- el mapa manda ---

with tab_clima:
    st.caption(
        "Un solo flujo, igual que DDP-lite/Skyplus (Hallazgo 19): buscá dónde está tu "
        "proyecto -- por nombre, por coordenada, o clic en el mapa -- y elegí la estación "
        "climática real más cercana. Nada de \"modos\" para decidir de antemano."
    )

    def _buscar_y_guardar(_lat, _lon):
        with st.spinner("Buscando estaciones cercanas..."):
            st.session_state.sitio_lat, st.session_state.sitio_lon = _lat, _lon
            df = obtener_estaciones_cercanas(_lat, _lon)
            st.session_state.sitio_cercanas = df
            if df is None or df.empty:
                st.error("No se encontraron estaciones para esta ubicación.")

    col_busq_nombre, col_busq_epw = st.columns(2)
    with col_busq_nombre:
        with st.expander("Buscar por nombre o coordenada",
                          expanded=(st.session_state.sitio_activo is None)):
            _nombre_busqueda = st.text_input(
                "Ciudad o país", placeholder="Ej: Alajuela, Costa Rica",
                label_visibility="collapsed", key="sitio_busqueda_nombre",
            )
            if st.button("Buscar por nombre", use_container_width=True, key="btn_sitio_buscar_nombre"):
                if _nombre_busqueda:
                    _lat_g, _lon_g = geocode_name(_nombre_busqueda)
                    if _lat_g is not None:
                        _buscar_y_guardar(_lat_g, _lon_g)
                        st.rerun()
                    else:
                        st.error(
                            "No se pudo geocodificar ese nombre -- necesita internet real "
                            "(Nominatim/Photon están bloqueados en este sandbox, Hallazgo 2)."
                        )
            st.divider()
            _lat_manual = st.number_input("Latitud", value=st.session_state.sitio_lat, format="%.4f",
                                           key="sitio_lat_input")
            _lon_manual = st.number_input("Longitud", value=st.session_state.sitio_lon, format="%.4f",
                                           key="sitio_lon_input")
            if st.button("Buscar por coordenada", use_container_width=True, key="btn_sitio_buscar_coord"):
                _buscar_y_guardar(_lat_manual, _lon_manual)
                st.rerun()

    with col_busq_epw:
        with st.expander("¿Tenés el EPW real de tu sitio? Subilo directo"):
            st.caption(
                "Opción secundaria (mismo patrón que DDP-lite/Skyplus) -- no compite con la "
                "búsqueda de al lado, sólo se usa si subís un archivo."
            )
            _archivo = st.file_uploader("Cargar archivo .epw", type=["epw"], key="archivo_epw_custom")
            if _archivo is not None and st.session_state.get("_ultimo_epw_subido") != _archivo.name:
                _ruta_subida = os.path.join(tempfile.gettempdir(), f"eco_wind_custom_{_archivo.name}")
                with open(_ruta_subida, "wb") as _f:
                    _f.write(_archivo.getbuffer())
                _res_subida = cargar_epw_subido(_ruta_subida)
                st.session_state["_ultimo_epw_subido"] = _archivo.name
                if _res_subida.get("error"):
                    st.error(_res_subida["error"])
                else:
                    st.session_state.sitio_activo = _res_subida
                    st.session_state.sitio_nombre_activo = f"{_res_subida['meta']['estacion']} (EPW propio)"
                    st.rerun()

    st.divider()

    col_mapa, col_estaciones = st.columns([2, 1])

    with col_mapa:
        st.subheader("Mapa interactivo")
        _m = folium.Map(location=[st.session_state.sitio_lat, st.session_state.sitio_lon],
                         zoom_start=8, tiles="CartoDB positron")
        folium.Marker(
            [st.session_state.sitio_lat, st.session_state.sitio_lon], tooltip="Ubicación del proyecto",
            icon=folium.Icon(color="red", icon="crosshairs"),
        ).add_to(_m)
        _df_cerc = st.session_state.sitio_cercanas
        if _df_cerc is not None and not _df_cerc.empty:
            for _, _row in _df_cerc.iterrows():
                if pd.notna(_row.get("lat")) and pd.notna(_row.get("lon")):
                    folium.Marker(
                        [_row["lat"], _row["lon"]], tooltip=f"{_row['name']} ({_row['distancia_km']} km)",
                        icon=folium.Icon(color="blue", icon="cloud"),
                    ).add_to(_m)
        _salida_mapa = st_folium(_m, height=480, use_container_width=True, key="mapa_sitio")

        if _salida_mapa and _salida_mapa.get("last_clicked"):
            _c_lat, _c_lon = _salida_mapa["last_clicked"]["lat"], _salida_mapa["last_clicked"]["lng"]
            if (round(_c_lat, 4), round(_c_lon, 4)) != (
                    round(st.session_state.sitio_lat, 4), round(st.session_state.sitio_lon, 4)):
                _buscar_y_guardar(_c_lat, _c_lon)
                st.rerun()

    with col_estaciones:
        st.subheader("Estaciones disponibles")

        if st.session_state.sitio_activo:
            st.markdown(f"✅ **Sitio activo:** {st.session_state.sitio_nombre_activo}")
            st.divider()

        if _df_cerc is not None and not _df_cerc.empty:
            st.caption("Estaciones reales más cercanas (clic en el mapa, o buscá arriba, para actualizar):")
            for _i, _row in _df_cerc.iterrows():
                with st.container(border=True):
                    st.markdown(f"**{_row['name']}**")
                    st.caption(f"{_row.get('state', '')} -- {_row['distancia_km']} km")
                    if st.button("Usar esta estación", key=f"btn_sitio_est_{_i}", use_container_width=True):
                        _res_est = cargar_estacion_elegida(_row)
                        if _res_est.get("error"):
                            st.error(_res_est["error"])
                        else:
                            st.session_state.sitio_activo = _res_est
                            st.session_state.sitio_nombre_activo = _row["name"]
                            st.rerun()

            # Hallazgo 19 (v3): aproximación como fallback automático DENTRO del mismo flujo,
            # sólo cuando la estación real más cercana ya no representa bien el sitio -- no es
            # un modo aparte que el usuario elige de entrada.
            _dist_min = float(_df_cerc["distancia_km"].min())
            _dentro_de_cr = (8.0 <= st.session_state.sitio_lat <= 11.3
                              and -86.0 <= st.session_state.sitio_lon <= -82.5)
            if _dist_min > UMBRAL_APROXIMACION_KM and _dentro_de_cr and os.path.exists(RUTA_RASTER_CR_DEFAULT):
                with st.container(border=True):
                    st.markdown(
                        f"⚠️ **Aproximación para este punto exacto** -- la estación real más "
                        f"cercana está a {_dist_min:.0f} km."
                    )
                    st.caption(
                        "Sensibilización del punto exacto (Hallazgo 21-30): se toma prestada la forma "
                        "(estacionalidad, ciclo diurno) de la estación real más cercana entre las "
                        "conocidas, y la magnitud se ajusta con la razón entre dos lecturas del ráster "
                        "de GWA en vez de confiar en su valor crudo -- no son datos propios de este "
                        "sitio exacto. La estación donante concreta se muestra después de calcular. "
                        "GWA es la fuente de ajuste validada como mejor contra NASA POWER y ERA5/CDS "
                        "en los 4 sitios reales de Costa Rica (Hallazgo 25/26/28)."
                    )
                    _elev_aprox = st.number_input(
                        "Elevación (m sobre el nivel del mar)", value=800.0, min_value=0.0,
                        max_value=3800.0, step=50.0, key="sitio_elev_aprox",
                        help="El ráster no trae elevación -- búsqueda automática por DEM pendiente "
                             "(Hallazgo 17), por ahora manual.",
                    )
                    if st.button("Usar esta aproximación", key="btn_usar_aproximacion", use_container_width=True):
                        _res_aprox = cargar_aproximacion(
                            st.session_state.sitio_lat, st.session_state.sitio_lon, _elev_aprox)
                        if _res_aprox.get("error"):
                            st.error(_res_aprox["error"])
                        else:
                            st.session_state.sitio_activo = _res_aprox
                            st.session_state.sitio_nombre_activo = (
                                f"Aproximación -- forma de {_res_aprox['donante_nombre']} "
                                f"({_res_aprox['distancia_km']:.0f} km), ajustada con GWA")
                            st.rerun()
        else:
            st.caption("Buscá tu sitio arriba, o clickeá en el mapa, para ver las estaciones cercanas.")


# --- Tab 2: Contexto climático -- rosa de vientos + heatmap, sin depender de "Calcular" ---

with tab_contexto:
    resultado_clima = st.session_state.get("sitio_activo")
    error_clima = None if resultado_clima is None else resultado_clima.get("error")

    if resultado_clima is None:
        st.info("Elegí primero un sitio en \"SELECCIÓN DE CLIMA\" para ver su contexto climático.")
    elif error_clima:
        st.error(error_clima, icon="🚫")
    else:
        hm_json = resultado_clima["hm_json"]
        rosa_freq = resultado_clima["rosa_freq"]
        es_aproximacion = resultado_clima["es_aproximacion"]
        media_confirmada = resultado_clima["media"]

        if "meta" in resultado_clima:
            _meta = resultado_clima["meta"]
            st.success(f"Estación real: {_meta['estacion']} ({_meta['pais']}, WMO {_meta['wmo']}) -- "
                       f"lat={_meta['lat']:.4f}, lon={_meta['lon']:.4f}, elevación={_meta['elevacion_m']:.0f}m. "
                       f"Media anual real (10m): {media_confirmada:.2f} m/s.", icon="✅")
        if es_aproximacion:
            _donante = resultado_clima.get("donante_nombre", "estación desconocida")
            _dist = resultado_clima.get("distancia_km")
            _factor = resultado_clima.get("factor_ajuste")
            st.info(
                f"Media sensibilizada para este punto exacto "
                f"({st.session_state.sitio_lat:.4f},{st.session_state.sitio_lon:.4f}): "
                f"**{media_confirmada:.2f} m/s** -- media real de {_donante}"
                + (f" ({_dist:.0f} km)" if _dist is not None else "")
                + (f" × factor de ajuste GWA {_factor:.3f}" if _factor is not None else ""),
                icon="ℹ️",
            )
            st.caption(
                f"Forma (estacionalidad, ciclo diurno) y rosa de vientos: prestadas de {_donante} "
                "-- la magnitud sí se ajustó al punto exacto (Hallazgo 25/26/28), la dirección no "
                "tiene todavía un mecanismo de ajuste, sigue siendo la del donante tal cual."
            )

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.pyplot(graficar_rosa_vientos(rosa_freq))
        with col_g2:
            st.pyplot(graficar_heatmap_clima(hm_json))


# --- Tab 3: Configuración del proyecto -- turbinas, clústers, parámetros avanzados ---

with tab_config:
    st.subheader("Clústers del proyecto")
    for i, c in enumerate(st.session_state.clusters):
        with st.container(border=True):
            cc1, cc2, cc3, cc4 = st.columns([2, 1, 1, 0.4])
            c["modelo"] = cc1.selectbox(
                "Modelo", options=list(CURVE_COEFFICIENTS.keys()),
                format_func=lambda k: NOMBRES_MODELO.get(k, k),
                index=list(CURVE_COEFFICIENTS.keys()).index(c["modelo"]), key=f"modelo_{i}",
            )
            c["N"] = cc2.number_input("N", min_value=1, max_value=20, value=c["N"], step=1, key=f"n_{i}")
            c["altura_buje"] = cc3.number_input("Buje (m)", min_value=0.5, max_value=15.0,
                                                 value=c["altura_buje"], step=0.5, key=f"h_{i}")
            if cc4.button("✕", key=f"del_{i}", help="Quitar este clúster") and len(st.session_state.clusters) > 1:
                st.session_state.clusters.pop(i)
                st.rerun()

    if st.button("+ Agregar clúster"):
        st.session_state.clusters.append({"modelo": "medium_tulip", "N": 1, "altura_buje": 3.0})
        st.rerun()

    st.divider()

    with st.expander("Parámetros avanzados"):
        z0 = st.selectbox(
            "Rugosidad DEL SITIO donde va la turbina (z0)", options=[0.03, 0.1, 0.3, 1.0],
            format_func=lambda z: {0.03: "0.03 — campo abierto", 0.1: "0.1 — cultivos bajos",
                                    0.3: "0.3 — suburbano (default)", 1.0: "1.0 — urbano denso"}[z],
            index=2,
            help="Rugosidad del sitio DESTINO (donde se instala la turbina), no la del sitio "
                 "de referencia climática. Desde Hallazgo 20, esta app usa dos rugosidades "
                 "distintas -- ver la nota en Resultados financieros.",
        )
        metodo_bouquet = st.radio(
            "Modelo de Efecto Bouquet", options=["real", "lineal"],
            format_func=lambda m: "Real (exponencial, validado R²≥0.999996)" if m == "real"
            else "Lineal de marketing (solo referencia, subestima fuerte)",
        )

    st.divider()

    if not st.session_state.get("sitio_activo"):
        st.warning("Elegí un sitio en \"SELECCIÓN DE CLIMA\" antes de calcular.", icon="⚠️")

    calcular = st.button("Calcular producción del proyecto", type="primary", use_container_width=True)
    if calcular:
        st.success("Cálculo listo -- mirá la pestaña **RESULTADOS FINANCIEROS**.")


# --- Tab 4: Resultados financieros -- por ahora, producción de energía (Hallazgo 12/17) ---

with tab_resultados:
    st.caption(
        "Cálculo financiero (CAPEX, tarifa eléctrica, payback) todavía no está implementado -- "
        "por ahora esta pestaña muestra la producción de energía del proyecto (fase futura)."
    )

    if calcular:
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")

        if resultado_clima is None:
            st.error(
                "Elegí primero una estación (o una aproximación) en \"SELECCIÓN DE CLIMA\".",
                icon="🚫",
            )
        elif error:
            st.error(error, icon="🚫")
        else:
            df_clima = resultado_clima["df_clima"]
            elevacion_m = resultado_clima["elevacion_m"]

            resultados = []
            serie_total_w = None
            for c in st.session_state.clusters:
                r = simular(df_clima, altura_buje=c["altura_buje"], modelo=c["modelo"], N=int(c["N"]),
                            elevacion_m=elevacion_m, z0=z0, metodo_bouquet=metodo_bouquet)
                resultados.append({**c, **r})
                serie_cluster_w = r["serie_horaria_W_por_turbina"] * c["N"]
                serie_total_w = serie_cluster_w if serie_total_w is None else serie_total_w + serie_cluster_w

            kwh_total = sum(r["kwh_anual"] for r in resultados)
            n_total = sum(c["N"] for c in st.session_state.clusters)

            c1, c2, c3 = st.columns(3)
            c1.metric("Producción anual total", f"{kwh_total:,.0f} kWh")
            c2.metric("Turbinas totales", f"{n_total}")
            c3.metric("Corrección por densidad (elevación)",
                      f"{(1 - resultados[0]['factor_correccion_densidad']) * 100:.1f}% menos")

            st.markdown("**Detalle por clúster**")
            tabla = pd.DataFrame([{
                "Modelo": NOMBRES_MODELO.get(r["modelo"], r["modelo"]), "N": r["N"],
                "Buje (m)": r["altura_buje"], "kWh/año": round(r["kwh_anual"]),
                "V. medio buje (m/s)": round(r["v_hub_medio"], 2),
                "% bajo cut-in": round(r["pct_horas_bajo_cutin"], 1),
            } for r in resultados])
            st.dataframe(tabla, hide_index=True, use_container_width=True)

            media_confirmada = resultado_clima["media"]
            with st.expander("Hallazgo 20 -- perfil de viento por altura: dos rugosidades, y un cross-check independiente"):
                _r0 = resultados[0]
                _v_pot = wind_at_height_potencia(
                    media_confirmada, 10, _r0["altura_buje"], terreno="suburban", terreno_met="country")
                st.write(
                    f"El viento de referencia (10m, aeropuerto/GWA/EPW) y el sitio real donde va la "
                    f"turbina casi nunca tienen la misma rugosidad -- hasta Hallazgo 20 esta app usaba "
                    f"un solo z0 para los dos, lo que sobreestimaba la velocidad en buje 16-24% (según "
                    f"el método) en el caso de San José, y como P∝v³ eso es ~1.6-1.9x de más en energía. "
                    f"Ahora se usa z0 del sitio destino (seleccionable en \"CONFIGURACIÓN DEL PROYECTO\") "
                    f"**distinto** de z0 de referencia (0.1, clase \"country\"/aeropuerto -- fórmula "
                    f"logarítmica, ver `engine/simulador_pista_a.py::wind_at_height()`)."
                )
                st.write(
                    f"**Cross-check independiente** (ley de potencia que usa EnergyPlus por default, "
                    f"misma tabla de terrenos que ladybug-tools/ladybug, terreno suburbano): "
                    f"{_v_pot:.2f} m/s a {_r0['altura_buje']:.1f}m de buje, vs. "
                    f"**{_r0['v_hub_medio']:.2f} m/s** con la fórmula logarítmica usada arriba -- "
                    f"{'concuerdan razonablemente' if abs(_v_pot/_r0['v_hub_medio']-1) < 0.15 else 'difieren más de lo esperado, revisar'}."
                )

            with st.expander("Requisito 3 -- ¿por qué el cálculo es hora por hora, no con la velocidad media?"):
                cmp = comparar_metodo_ingenuo_vs_horario(
                    df_clima, altura_buje=resultados[0]["altura_buje"], modelo=resultados[0]["modelo"],
                    N=int(resultados[0]["N"]), elevacion_m=elevacion_m, z0=z0, metodo_bouquet=metodo_bouquet)
                st.write(
                    f"Para el primer clúster: método correcto (P=k·v³ en cada una de las 8,760 horas) = "
                    f"**{cmp['kwh_anual_correcto']:.0f} kWh/año**. Método ingenuo (P evaluada en la velocidad "
                    f"media {cmp['v_media']:.2f} m/s, ×8,760 horas) = **{cmp['kwh_anual_ingenuo']:.0f} kWh/año** "
                    f"-- el método ingenuo subestima **{cmp['razon_correcto_sobre_ingenuo']:.2f}x**. "
                    f"Es la desigualdad de Jensen (P∝v³ es convexa, E[v³]≥(E[v])³): con un recurso variable, "
                    f"nunca es válido sustituir la velocidad media directo en la fórmula de potencia."
                )

            st.divider()
            st.markdown("**Producción mensual (todos los clústers)**")
            kwh_mensual_total = pd.concat([r["kwh_mensual"] for r in resultados], axis=1).sum(axis=1)
            st.bar_chart(kwh_mensual_total.rename("kWh"), color=VERDE)
            st.markdown("**Curva de duración anual (Requisito 3 -- detalle horario completo)**")
            st.pyplot(graficar_curva_duracion(serie_total_w))

            st.caption(
                "Motor: `flower_turbines_curves.py` (validado Hallazgo 12) + corrección de densidad de aire "
                "por elevación (Hallazgo 17). Fuente climática: Global Wind Atlas -- NO NASA POWER "
                "(subestima ~3x en Costa Rica, Hallazgo 1)."
            )
    else:
        st.info("Configurá el proyecto en \"CONFIGURACIÓN DEL PROYECTO\" y presioná "
                 "**Calcular producción del proyecto**.")

st.divider()
st.caption(
    "ECO Consultor — Simulador en desarrollo (Fase 2). "
    "Pendiente: cálculo financiero (CAPEX, tarifa, payback), DEM automático para elevación, "
    "PDF de cotización, registro de leads, despliegue a Cloud Run."
)
