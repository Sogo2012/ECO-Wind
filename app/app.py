"""
ECO | Wind -- Simulador de microgeneración eólica (Fase 2).

Sobre el motor validado de Pista A (engine/simulador_pista_a.py +
engine/flower_turbines_curves.py, Hallazgo 12), extendido con clima
multi-sitio, corrección de densidad, multi-clúster y gráficos (Hallazgo 17
-- ver avance-de-proyecto.md).

ALCANCE HONESTO:
- San José (Juan Santamaría), Nicoya, Liberia y Finca Favorita (Limón)
  tienen datos climáticos REALES completos y propios: San José vía export
  del panel de Global Wind Atlas (curva de excedencia + patrón diurno
  reales), y los otros 3 vía EPW real de climate.onebuilding.org (Hallazgo
  18 -- descargados por Pablo, ver engine/epw_real.py). Ninguno de estos 4
  usa aproximación.
- Cualquier OTRA coordenada de Costa Rica usa la velocidad media real del
  ráster de GWA (si está descargado en datos_clima/gwa_costa_rica_10m.tif
  -- ver engine/gwa_raster.py) con la FORMA prestada de San José, escalada
  a esa media -- una aproximación declarada, no datos propios del sitio
  nuevo. Hallazgo 18 cuantificó el error de esta aproximación contra los 3
  sitios EPW reales: entre -44% y +18% en producción anual estimada según
  el sitio -- se muestra un aviso explícito en la app cuando se usa.
- El ráster de Costa Rica no se pudo descargar en este entorno de
  desarrollo (globalwindatlas.info bloqueado, Hallazgo 2) -- si no existe
  el archivo, la app lo dice claramente en vez de fallar oscuro.
- ¿Tenés el EPW real de tu sitio (climate.onebuilding.org u otra fuente)?
  Subilo directo -- patrón adoptado de DDP-lite (Sogo2012/DDP-lite,
  Hallazgo 18) -- y se usa sin aproximación, sin importar si el sitio está
  en la lista de arriba.
- Elevación: para los 4 sitios con datos propios ya está confirmada (AIP/
  DGAC para San José, el propio encabezado del EPW para los otros 3). Para
  coordenadas nuevas (aproximación) se pide manual por ahora -- la
  búsqueda automática por DEM queda pendiente (Hallazgo 17).
- Sin mapa, sin PDF, sin registro de leads todavía.
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
from engine.gwa_raster import generar_clima_sitio_nuevo, RUTA_RASTER_CR_DEFAULT
from engine.epw_real import (
    SITIOS_EPW_REAL, cargar_epw_real, heatmap_json_desde_epw, rosa_frecuencia_desde_epw,
    obtener_estaciones_cercanas, geocode_name, descargar_y_extraer_epw,
)

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


# --- Helpers de clima/geometría ---

def _rosa_y_heatmap_san_jose():
    sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
    ws_json, hm_json = cargar_gwa_json(os.path.join(BASE_DIR, sitio["carpeta_gwa"]))
    ruta_lib = os.path.join(BASE_DIR, sitio["carpeta_gwa"], "gwc_point_1_10m.lib")
    rosa_freq = cargar_wind_rose_lib(ruta_lib)["freq"]
    return ws_json, hm_json, rosa_freq


def cargar_clima_sitio(modo, sitio_key, lat, lon, elevacion_m, ruta_epw_custom=None):
    """
    Devuelve un dict: df_clima, media, hm_json (índice mes×hora), rosa_freq
    (12 sectores, %), es_aproximacion, elevacion_m (la real del sitio si
    viene de un EPW propio -- ignora el valor tecleado en ese caso), error.

    modo: "san_jose" | "epw_real" (sitio_key = clave en SITIOS_EPW_REAL) |
          "epw_custom" (usa ruta_epw_custom, subido por el usuario o
          descargado desde el mapa -- mismo patrón que el "¿Usar EPW
          personalizado?" de DDP-lite) | "mapa" (sin estación elegida
          todavía -- error informativo) | "coordenada" (ráster GWA + forma
          prestada de San José, aproximación).
    """
    if modo == "san_jose":
        sitio = SITIOS_DISPONIBLES[sitio_key]
        ws_json, hm_json, rosa_freq = _rosa_y_heatmap_san_jose()
        df_clima, media = generar_clima_gwa(ws_json, hm_json)
        return dict(df_clima=df_clima, media=media, hm_json=hm_json, rosa_freq=rosa_freq,
                    es_aproximacion=False, elevacion_m=elevacion_m, error=None)

    if modo == "mapa":
        return dict(error=(
            "Todavía no elegiste ninguna estación. Hacé clic en el mapa para buscar las más "
            "cercanas y presioná \"Usar\" en la que quieras."
        ))

    if modo in ("epw_real", "epw_custom"):
        try:
            ruta = SITIOS_EPW_REAL[sitio_key]["ruta_epw"] if modo == "epw_real" else ruta_epw_custom
            df_clima, meta = cargar_epw_real(ruta)
        except (FileNotFoundError, ValueError, KeyError) as e:
            return dict(error=str(e))
        hm_json = heatmap_json_desde_epw(df_clima)
        rosa_freq = rosa_frecuencia_desde_epw(df_clima)
        return dict(df_clima=df_clima, media=float(df_clima["WS10M"].mean()), hm_json=hm_json,
                    rosa_freq=rosa_freq, es_aproximacion=False, elevacion_m=meta["elevacion_m"],
                    error=None, meta=meta)

    # modo == "coordenada" -- ráster GWA + forma prestada de San José (Requisito 1, aproximación)
    if not os.path.exists(RUTA_RASTER_CR_DEFAULT):
        return dict(error=(
            f"No existe el ráster de Costa Rica ({os.path.basename(RUTA_RASTER_CR_DEFAULT)}). "
            "Hay que descargarlo primero desde un entorno con internet real (Colab) -- "
            "ver engine/gwa_raster.py, descargar_raster_costa_rica(). No se puede calcular "
            "para una coordenada nueva sin ese archivo (o subí el EPW real del sitio si lo tenés)."
        ))
    try:
        df_clima, media = generar_clima_sitio_nuevo(lat, lon)
    except (FileNotFoundError, ValueError, KeyError) as e:
        return dict(error=str(e))
    _, hm_json, rosa_freq = _rosa_y_heatmap_san_jose()
    return dict(df_clima=df_clima, media=media, hm_json=hm_json, rosa_freq=rosa_freq,
                es_aproximacion=True, elevacion_m=elevacion_m, error=None)


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

col_config, col_resultado = st.columns([1, 2])

with col_config:
    st.subheader("Sitio")

    _opciones_sitio = {"san_jose": ("San José (Juan Santamaría) — datos GWA completos", "san_jose_juan_santamaria")}
    for _k, _s in SITIOS_EPW_REAL.items():
        _opciones_sitio[f"epw_{_k}"] = (f"{_s['nombre']} — EPW real", _k)
    _opciones_sitio["mapa"] = ("🗺️ Buscar estación en el mapa (climate.onebuilding.org)", None)
    _opciones_sitio["coordenada"] = ("Coordenada personalizada (aproximación)", None)

    _modo_ui = st.selectbox(
        "Sitio del proyecto", options=list(_opciones_sitio.keys()),
        format_func=lambda k: _opciones_sitio[k][0],
    )
    if _modo_ui == "san_jose":
        modo_sitio = "san_jose"
    elif _modo_ui == "coordenada":
        modo_sitio = "coordenada"
    elif _modo_ui == "mapa":
        modo_sitio = "mapa"
    else:
        modo_sitio = "epw_real"
    sitio_key = _opciones_sitio[_modo_ui][1]
    ruta_epw_custom = None  # se completa más abajo (mapa o uploader propio), si aplica

    if modo_sitio == "san_jose":
        sitio = SITIOS_DISPONIBLES[sitio_key]
        lat, lon = sitio["lat"], sitio["lon"]
        elevacion_m = sitio["elevacion_m"]
        st.caption(f"lat={lat}, lon={lon}, elevación={elevacion_m:.0f}m (AIP/DGAC) -- datos GWA reales propios.")
    elif modo_sitio == "epw_real":
        lat, lon, elevacion_m = None, None, None  # se completan con el EPW real al cargar
        st.caption(f"EPW real de climate.onebuilding.org (Hallazgo 18) -- sin aproximación.")
    elif modo_sitio == "mapa":
        lat, lon, elevacion_m = None, None, None
        st.caption(
            "Homologado con DDP-lite y Skyplus (Sogo2012/DDP-lite, Sogo2012/Skyplus, Hallazgo 19) "
            "-- catálogo completo de climate.onebuilding.org, 5,276 estaciones en 20 países de "
            "América, sin acotar a Costa Rica. Buscá por nombre, por coordenada, o clic en el mapa; "
            "la descarga necesita internet real: no funciona en este sandbox de desarrollo "
            "(Hallazgo 2), sí en Docker local o Cloud Run."
        )
        if "mapa_lat" not in st.session_state:
            st.session_state.mapa_lat, st.session_state.mapa_lon = 9.9, -84.0
            st.session_state.mapa_cercanas = None
            st.session_state.mapa_epw_seleccionado, st.session_state.mapa_estacion_nombre = None, None

        def _buscar_y_guardar(_lat, _lon):
            with st.spinner("Buscando estaciones cercanas..."):
                st.session_state.mapa_lat, st.session_state.mapa_lon = _lat, _lon
                df = obtener_estaciones_cercanas(_lat, _lon)
                st.session_state.mapa_cercanas = df
                if df is None or df.empty:
                    st.error("No se encontraron estaciones para esta ubicación.")

        with st.expander("Buscar por nombre", expanded=False):
            _nombre_busqueda = st.text_input(
                "Ciudad o país", placeholder="Ej: Alajuela, Costa Rica",
                label_visibility="collapsed", key="mapa_busqueda_nombre",
            )
            if st.button("Buscar por nombre", use_container_width=True, key="btn_mapa_buscar_nombre"):
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
            _lat_manual = st.number_input("Latitud", value=st.session_state.mapa_lat, format="%.4f",
                                           key="mapa_lat_input")
            _lon_manual = st.number_input("Longitud", value=st.session_state.mapa_lon, format="%.4f",
                                           key="mapa_lon_input")
            if st.button("Buscar por coordenada", use_container_width=True, key="btn_mapa_buscar_coord"):
                _buscar_y_guardar(_lat_manual, _lon_manual)
                st.rerun()

        _m = folium.Map(location=[st.session_state.mapa_lat, st.session_state.mapa_lon],
                         zoom_start=8, tiles="CartoDB positron")
        folium.Marker(
            [st.session_state.mapa_lat, st.session_state.mapa_lon], tooltip="Ubicación del proyecto",
            icon=folium.Icon(color="red", icon="crosshairs"),
        ).add_to(_m)
        _df_cerc = st.session_state.mapa_cercanas
        if _df_cerc is not None and not _df_cerc.empty:
            for _, _row in _df_cerc.iterrows():
                if pd.notna(_row.get("lat")) and pd.notna(_row.get("lon")):
                    folium.Marker(
                        [_row["lat"], _row["lon"]],
                        tooltip=f"{_row['name']} ({_row['distancia_km']} km)",
                        icon=folium.Icon(color="blue", icon="cloud"),
                    ).add_to(_m)
        _salida_mapa = st_folium(_m, height=340, use_container_width=True, key="mapa_estaciones")

        if _salida_mapa and _salida_mapa.get("last_clicked"):
            _c_lat, _c_lon = _salida_mapa["last_clicked"]["lat"], _salida_mapa["last_clicked"]["lng"]
            if (round(_c_lat, 4), round(_c_lon, 4)) != (
                    round(st.session_state.mapa_lat, 4), round(st.session_state.mapa_lon, 4)):
                _buscar_y_guardar(_c_lat, _c_lon)
                st.rerun()

        if _df_cerc is not None and not _df_cerc.empty:
            st.caption("Estaciones más cercanas (clic en el mapa, o buscá arriba, para actualizar):")
            for _i, _row in _df_cerc.iterrows():
                _c1, _c2 = st.columns([3, 1])
                _c1.write(f"**{_row['name']}** ({_row.get('state', '')}) -- {_row['distancia_km']} km")
                if _c2.button("Usar", key=f"btn_mapa_est_{_i}"):
                    with st.spinner(f"Descargando {_row['name']}..."):
                        try:
                            _ruta = descargar_y_extraer_epw(_row["url"])
                            st.session_state.mapa_epw_seleccionado = _ruta
                            st.session_state.mapa_estacion_nombre = _row["name"]
                            st.rerun()
                        except Exception as _e:
                            st.error(
                                f"No se pudo descargar {_row['name']}: {_e} -- necesita internet "
                                "real (no funciona en este sandbox de desarrollo, Hallazgo 2)."
                            )

        if st.session_state.mapa_epw_seleccionado:
            st.success(f"Estación activa: {st.session_state.mapa_estacion_nombre}")
            ruta_epw_custom = st.session_state.mapa_epw_seleccionado
            modo_sitio = "epw_custom"
    else:
        st.warning(
            "Aproximación (Requisito 1, Hallazgo 17): magnitud real del ráster de GWA, forma "
            "(variabilidad, estacionalidad) prestada de San José. Hallazgo 18 midió el error de esto "
            "contra 3 sitios reales: entre -44% y +18% en producción anual según el sitio -- no son "
            "datos propios de esta coordenada.",
            icon="⚠️",
        )
        lat = st.number_input("Latitud", value=9.9, min_value=8.0, max_value=11.3, format="%.4f")
        lon = st.number_input("Longitud", value=-84.0, min_value=-86.0, max_value=-82.5, format="%.4f")
        elevacion_m = st.number_input("Elevación (m sobre el nivel del mar)", value=800.0, min_value=0.0,
                                       max_value=3800.0, step=50.0,
                                       help="Búsqueda automática por DEM pendiente (Hallazgo 17) -- por ahora, manual.")

    with st.expander("¿Tenés el EPW real de tu sitio? Subilo directo"):
        st.caption(
            "Patrón adoptado de DDP-lite (Sogo2012/DDP-lite, Hallazgo 18) -- si subís un .epw, se usa "
            "directo (sin aproximación) y reemplaza la selección de arriba para este cálculo."
        )
        _usar_custom = st.toggle("¿Usar mi propio archivo EPW?", value=False, key="usar_epw_custom")
        if _usar_custom:
            _archivo = st.file_uploader("Cargar archivo .epw", type=["epw"], key="archivo_epw_custom")
            if _archivo is not None:
                ruta_epw_custom = os.path.join(tempfile.gettempdir(), f"eco_wind_custom_{_archivo.name}")
                with open(ruta_epw_custom, "wb") as _f:
                    _f.write(_archivo.getbuffer())
                modo_sitio = "epw_custom"

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

    with st.expander("Parámetros avanzados"):
        z0 = st.selectbox(
            "Rugosidad DEL SITIO donde va la turbina (z0)", options=[0.03, 0.1, 0.3, 1.0],
            format_func=lambda z: {0.03: "0.03 — campo abierto", 0.1: "0.1 — cultivos bajos",
                                    0.3: "0.3 — suburbano (default)", 1.0: "1.0 — urbano denso"}[z],
            index=2,
            help="Rugosidad del sitio DESTINO (donde se instala la turbina), no la del sitio "
                 "de referencia climática. Desde Hallazgo 20, esta app usa dos rugosidades "
                 "distintas -- ver la nota en Resultado.",
        )
        metodo_bouquet = st.radio(
            "Modelo de Efecto Bouquet", options=["real", "lineal"],
            format_func=lambda m: "Real (exponencial, validado R²≥0.999996)" if m == "real"
            else "Lineal de marketing (solo referencia, subestima fuerte)",
        )

    calcular = st.button("Calcular producción del proyecto", type="primary", use_container_width=True)

with col_resultado:
    st.subheader("Resultado")

    if calcular:
        resultado_clima = cargar_clima_sitio(modo_sitio, sitio_key, lat, lon, elevacion_m, ruta_epw_custom)
        error = resultado_clima.get("error")

        if error:
            st.error(error, icon="🚫")
        else:
            df_clima = resultado_clima["df_clima"]
            media_confirmada = resultado_clima["media"]
            hm_json = resultado_clima["hm_json"]
            rosa_freq = resultado_clima["rosa_freq"]
            es_aproximacion = resultado_clima["es_aproximacion"]
            elevacion_m = resultado_clima["elevacion_m"]  # real del EPW si aplica, sobreescribe el input

            if modo_sitio in ("epw_real", "epw_custom"):
                _m = resultado_clima["meta"]
                st.success(f"EPW real: {_m['estacion']} ({_m['pais']}, WMO {_m['wmo']}) -- "
                           f"lat={_m['lat']:.4f}, lon={_m['lon']:.4f}, elevación={_m['elevacion_m']:.0f}m. "
                           f"Media anual real (10m): {media_confirmada:.2f} m/s.", icon="✅")
            if es_aproximacion:
                st.info(f"Velocidad media real (ráster GWA, coordenada {lat:.4f},{lon:.4f}): "
                        f"{media_confirmada:.2f} m/s -- forma prestada de San José.", icon="ℹ️")

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

            with st.expander("Hallazgo 20 -- perfil de viento por altura: dos rugosidades, y un cross-check independiente"):
                _r0 = resultados[0]
                _v_pot = wind_at_height_potencia(
                    media_confirmada, 10, _r0["altura_buje"], terreno="suburban", terreno_met="country")
                st.write(
                    f"El viento de referencia (10m, aeropuerto/GWA/EPW) y el sitio real donde va la "
                    f"turbina casi nunca tienen la misma rugosidad -- hasta Hallazgo 20 esta app usaba "
                    f"un solo z0 para los dos, lo que sobreestimaba la velocidad en buje 16-24% (según "
                    f"el método) en el caso de San José, y como P∝v³ eso es ~1.6-1.9x de más en energía. "
                    f"Ahora se usa z0 del sitio destino (seleccionable arriba, ver Parámetros avanzados) "
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

            tab_gen, tab_clima = st.tabs(["📈 Generación", "🌬️ Clima del sitio"])
            with tab_gen:
                kwh_mensual_total = pd.concat([r["kwh_mensual"] for r in resultados], axis=1).sum(axis=1)
                st.markdown("**Producción mensual (todos los clústers)**")
                st.bar_chart(kwh_mensual_total.rename("kWh"), color=VERDE)
                st.markdown("**Curva de duración anual (Requisito 3 -- detalle horario completo)**")
                st.pyplot(graficar_curva_duracion(serie_total_w))

            with tab_clima:
                if es_aproximacion:
                    st.caption("Rosa de vientos y patrón diurno: prestados de San José (forma), no del sitio nuevo.")
                cg1, cg2 = st.columns(2)
                cg1.pyplot(graficar_rosa_vientos(rosa_freq))
                cg2.pyplot(graficar_heatmap_clima(hm_json))

            st.caption(
                "Motor: `flower_turbines_curves.py` (validado Hallazgo 12) + corrección de densidad de aire "
                "por elevación (Hallazgo 17). Fuente climática: Global Wind Atlas -- NO NASA POWER "
                "(subestima ~3x en Costa Rica, Hallazgo 1)."
            )
    else:
        st.info("Configurá el proyecto a la izquierda y presioná **Calcular producción del proyecto**.")

st.divider()
st.caption(
    "ECO Consultor — Simulador en desarrollo (Fase 2). "
    "Pendiente: mapa de ubicación, DEM automático para elevación, PDF de cotización, "
    "registro de leads, despliegue a Cloud Run."
)
