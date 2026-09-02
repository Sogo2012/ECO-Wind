"""
ECO | Wind -- Simulador de microgeneración eólica (Fase 2).

Sobre el motor validado de Pista A (engine/simulador_pista_a.py +
engine/flower_turbines_curves.py, Hallazgo 12), extendido con clima
multi-sitio, corrección de densidad, multi-clúster y gráficos (Hallazgo 17
-- ver avance-de-proyecto.md).

ALCANCE HONESTO (Hallazgo 36 -- simplificación deliberada de Pablo, ver
avance-de-proyecto.md: "nos olvidamos de todas las fuentes, solo vamos a
usar EPW"):
- Un solo flujo de clima, homologado con DDP-lite/Skyplus (Hallazgo 19,
  v3): buscás tu sitio por nombre, coordenada o clic en el mapa, la app te
  muestra las estaciones climáticas REALES más cercanas (catálogo de
  climate.onebuilding.org, 5,276 estaciones, 20 países -- sin acotar a
  Costa Rica), y elegís una. No hay "modos" que elegir de antemano.
- San José, Nicoya, Liberia y Finca Favorita (Limón) ya están validados
  localmente con su propio EPW real (Hallazgo 18): si la búsqueda te
  devuelve una de estas 4 estaciones, la app sirve ese archivo local en
  vez de descargar de nuevo lo mismo -- invisible para vos, sigue siendo
  "elegí una estación real de la lista" (ver
  engine/epw_real.py::sitio_precacheado_cercano()).
- ¿Tu sitio no tiene una estación real cerca, o ya tenés el EPW de otro
  lugar que querés usar como referencia? Subilo directo -- misma pestaña,
  opción secundaria (mismo patrón que DDP-lite/Skyplus). No hay
  sensibilización espacial de magnitud por ninguna fuente externa (GWA,
  NASA POWER, ERA5, Köppen): esas vías se investigaron a fondo (Hallazgo
  21-30) y se descartaron por decisión de producto -- el ráster crudo de
  GWA a 10m resultó más ruidoso que la señal real que debía resolver
  (Hallazgo 35). Con datos limitados de verdad, un EPW real elegido a
  conciencia por el usuario es más confiable que un ajuste automático
  sobre una fuente que ya demostró fallar en Costa Rica.
- Lo único que SÍ se sensibiliza, y con una fuente propia: la velocidad
  del EPW (medida a 10m) se lleva a la altura real de buje de cada turbina
  con el perfil logarítmico de viento de ladybug-tools/ladybug
  (`engine/simulador_pista_a.py::wind_at_height()`, Hallazgo 20 -- fórmula
  y tabla de terrenos verificadas contra el código fuente real de
  ladybug.windprofile). Terreno de referencia meteorológica fijo en
  "country" (aeropuerto/EPW, z0=0.1m); terreno del sitio destino
  seleccionable por el usuario (Equipos y configuración > Parámetros
  avanzados).
- Elevación: siempre del encabezado del EPW real elegido o subido -- nunca
  tecleada a mano.
- Sin PDF, sin registro de leads todavía.
- Corre local; despliegue a Cloud Run sigue pendiente.
"""
import json
import os
import sys
import tempfile

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulador_pista_a import (
    simular, comparar_metodo_ingenuo_vs_horario, wind_at_height_potencia,
)
from engine.flower_turbines_curves import CURVE_COEFFICIENTS
from engine.turbine_specs import SPECS_TURBINAS, RUTA_IMAGEN, LOGO_ECO, LOGO_FLOWER_TURBINES
from engine.epw_real import (
    SITIOS_EPW_REAL, cargar_epw_real, heatmap_json_desde_epw, rosa_vientos_detallada_desde_epw,
    obtener_estaciones_cercanas, geocode_name, descargar_y_extraer_epw, sitio_precacheado_cercano,
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Paleta corporativa ECO (plan-tecnico-eco-wind.md, seccion 5) ---
AZUL = "#003C52"
VERDE = "#4A7C2F"
GRIS = "#4A5568"
FONDO = "#E8F0F3"

# --- Paleta de clima (10 colores para heatmaps y visualizaciones) ---
PALETA_CLIMA = ["#4b6ba9", "#5a7bc3", "#6b8dd4", "#7d9ee0", "#90aee8", "#a3beef", "#c9d8f0", "#f4e4a0", "#f5c455", "#ea2600"]

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


def _img_base64(path, max_width):
    """Incrusta una imagen como data-URI (necesario para el header del menú lateral,
    que va dentro de un bloque HTML -- st.image() no se puede mezclar ahí adentro).
    Mismo patrón que DDP-lite/Skyplus."""
    import base64
    with open(path, "rb") as f:
        data = base64.b64encode(f.read()).decode()
    ext = path.split(".")[-1].lower()
    mime = "image/png" if ext == "png" else "image/svg+xml" if ext == "svg" else "image/jpeg"
    return (f'<img src="data:{mime};base64,{data}" '
            f'style="max-width:{max_width}px; width:100%; height:auto; display:block;">')


st.set_page_config(page_title="ECO | Wind — Simulador", page_icon="🌬️", layout="wide")

st.markdown(f"""
<style>
    .stApp {{ background-color: {FONDO}; }}
    h1, h2, h3 {{ color: {AZUL}; }}
    .stButton>button, button[kind="primary"], button[kind="primaryFormSubmit"] {{
        background-color: {VERDE} !important; color: white !important; border: none !important;
    }}
    /* Menu lateral (Hallazgo 19 v4) -- misma estructura de DDP-lite/Skyplus: header de marca +
       navegador de secciones, para que la seleccion de clima y de equipos quede en un solo
       lugar visualmente ordenado en vez de competir por espacio horizontal en pestañas. */
    [data-testid="stSidebar"] {{ background-color: #FFFFFF; border-right: 1px solid #D8E2E7; }}
    [data-testid="stSidebar"] .stButton>button {{
        background-color: transparent !important; color: {GRIS} !important;
        border: none !important; text-align: left !important; justify-content: flex-start !important;
        font-weight: 500 !important; padding: 8px 10px !important; margin: 2px 0 !important;
    }}
    [data-testid="stSidebar"] .stButton>button:hover {{ background-color: {FONDO} !important; color: {AZUL} !important; }}
    .eco-brand {{ background: {AZUL}; margin: -1rem -1rem 1rem -1rem; padding: 0; border-bottom: 3px solid {VERDE}; }}
    .eco-brand-logos {{ background: #FFFFFF; padding: 12px 16px 8px 16px; display: flex; gap: 10px; align-items: center; justify-content: space-between; }}
    .eco-brand-text {{ padding: 8px 16px 12px 16px; }}
    .eco-brand-title {{ font-size: 1.05rem; font-weight: 700; color: white; }}
    .eco-brand-sub {{ font-size: 0.68rem; color: rgba(255,255,255,0.75); margin-top: 2px; }}
    .eco-sidebar-section {{
        font-size: 0.65rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em;
        color: {GRIS}; background: {FONDO}; border-left: 2px solid {AZUL}; padding: 5px 8px; margin: 10px 0 8px 0;
    }}
</style>
""", unsafe_allow_html=True)

if "clusters" not in st.session_state:
    st.session_state.clusters = [{"modelo": "medium_tulip", "N": 3, "altura_buje": 3.0}]

if "sitio_lat" not in st.session_state:
    st.session_state.sitio_lat, st.session_state.sitio_lon = 9.9, -84.0
    st.session_state.sitio_cercanas = None
    st.session_state.sitio_activo, st.session_state.sitio_nombre_activo = None, None

if "seccion_activa" not in st.session_state:
    st.session_state.seccion_activa = "clima"
if "calculo_listo" not in st.session_state:
    st.session_state.calculo_listo = False


# --- Helpers de clima/geometría ---

def _resultado_desde_epw(df_clima, meta):
    """Arma el dict unificado (mismo formato para las 2 rutas que terminan en un EPW
    real: estación de la lista -- precacheada o recién descargada -- y EPW subido por
    el usuario). Hallazgo 36: ya no existe una tercera ruta de "aproximación" -- toda
    esta app corre sobre EPW real, nunca sobre una fuente sensibilizada externamente."""
    hm_json = heatmap_json_desde_epw(df_clima)
    rosa_detallada = rosa_vientos_detallada_desde_epw(df_clima)
    return dict(df_clima=df_clima, media=float(df_clima["WS10M"].mean()), hm_json=hm_json,
                rosa_detallada=rosa_detallada, elevacion_m=meta["elevacion_m"], error=None, meta=meta)


def cargar_estacion_elegida(row):
    """
    Hallazgo 19 (v3): un solo camino para "el usuario eligió una estación real de la
    lista" -- mismo patrón que DDP-lite/Skyplus (obtener_estaciones_cercanas() +
    descargar_y_extraer_epw()). Si la estación elegida coincide (por proximidad, no por
    texto) con uno de los 4 sitios que ya tenemos con su EPW real ya descargado
    (Hallazgo 18/36), sirve ese archivo local en vez de descargar de nuevo lo mismo --
    invisible para el usuario, sigue siendo "elegí una estación real y ya".
    """
    clave = sitio_precacheado_cercano(row["lat"], row["lon"]) if pd.notna(row.get("lat")) else None
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
    """EPW propio subido por el usuario (Hallazgo 36) -- para un sitio sin estación real
    cercana, o para usar a propósito el EPW de otro lugar como referencia. Llega al mismo
    resultado unificado que elegir una estación de la lista, sin ningún ajuste de
    magnitud: la velocidad que trae el EPW es la que se usa, tal cual, a su altura de
    referencia (10m) -- sólo se sensibiliza por ALTURA (wind_at_height(), Hallazgo 20),
    nunca por ubicación."""
    try:
        df_clima, meta = cargar_epw_real(ruta)
    except (FileNotFoundError, ValueError, KeyError) as e:
        return dict(error=str(e))
    return _resultado_desde_epw(df_clima, meta)


# --- Helpers de gráficos ---


def crear_curva_duracion_plotly(serie_w):
    """Curva de duración interactiva con Plotly."""
    ordenado = np.sort(serie_w.values)[::-1]
    pct_horas = np.arange(1, len(ordenado) + 1) / len(ordenado) * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=pct_horas, y=ordenado,
        fill='tozeroy',
        fillcolor=f'rgba({int(VERDE[1:3], 16)}, {int(VERDE[3:5], 16)}, {int(VERDE[5:7], 16)}, 0.25)',
        line=dict(color=VERDE, width=2),
        hovertemplate='<b>%{x:.1f}% de las horas</b><br>Potencia: %{y:,.0f} W<extra></extra>'
    ))

    fig.update_layout(
        title="Curva de duración -- resolución horaria completa",
        xaxis_title="% de las 8,760 horas del año (ordenadas de mayor a menor producción)",
        yaxis_title="Potencia (W, total del proyecto)",
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=60, r=20, t=40, b=60),
        font=dict(family="sans-serif", size=11),
        xaxis=dict(gridcolor='#E8E8E8'),
        yaxis=dict(gridcolor='#E8E8E8'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig


def crear_produccion_mensual_plotly(kwh_mensual_total):
    """Producción mensual interactiva con Plotly."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=MESES,
        y=kwh_mensual_total.values,
        marker=dict(color=VERDE),
        hovertemplate='<b>%{x}</b><br>Producción: %{y:,.0f} kWh<extra></extra>',
        showlegend=False
    ))

    fig.update_layout(
        title="Producción mensual (todos los clústers)",
        xaxis_title="Mes",
        yaxis_title="Energía (kWh)",
        hovermode='x unified',
        template='plotly_white',
        height=400,
        margin=dict(l=60, r=20, t=40, b=60),
        font=dict(family="sans-serif", size=11),
        xaxis=dict(gridcolor='#E8E8E8'),
        yaxis=dict(gridcolor='#E8E8E8'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )

    return fig


def crear_rosa_vientos_plotly(rosa_detallada):
    """Rosa de vientos clásica -- dirección × velocidad apilada, mismo concepto que la
    que arma `ladybug.windrose.WindRose` (la librería que usa la app de referencia
    github.com/pollination-apps/weather-report, pedida explícitamente para que la rosa
    se entienda: no un solo color por frecuencia total (versión vieja), sino un color
    por rango de velocidad dentro de cada dirección -- así se ve, por ejemplo, si el
    viento del NE es sobre todo flojo o sobre todo fuerte, no sólo que "sopla del NE".

    8 puntos de compás (N/NE/E/SE/S/SO/O/NO) -- ver docstring de
    rosa_vientos_detallada_desde_epw() para por qué 8 y no 12 (con 12 sectores de 30°
    las etiquetas de 16 puntos, tipo NNE/ENE, quedan mal puestas)."""
    sectores = ['N', 'NE', 'E', 'SE', 'S', 'SO', 'O', 'NO'][:rosa_detallada["n_sectores"]]
    matriz = np.array(rosa_detallada["matriz"])
    bins_label = rosa_detallada["bins_label"]
    pct_calma = rosa_detallada["pct_calma"]

    # Paleta secuencial azul (flojo) -> rojo (fuerte), un color por bin de velocidad --
    # mismos colores extremos que la paleta vieja, ahora uno por bin en vez de por sector.
    paleta = ["#4b6ba9", "#7d9ee0", "#c9d8f0", "#f5c455", "#ea2600", "#a3243d"]

    fig = go.Figure()
    for i, etiqueta in enumerate(bins_label):
        fig.add_trace(go.Barpolar(
            r=matriz[i], theta=sectores, name=etiqueta,
            marker=dict(color=paleta[i % len(paleta)], line=dict(color='white', width=0.5)),
            hovertemplate=f'<b>%{{theta}}</b><br>{etiqueta}: %{{r:.1f}}% de las horas del año<extra></extra>',
        ))

    fig.update_layout(
        barmode='stack',
        title=f"Rosa de vientos -- % de horas por dirección y velocidad (calma: {pct_calma:.0f}%)",
        polar=dict(
            radialaxis=dict(visible=True, gridcolor='#D8D8D8', ticksuffix='%'),
            angularaxis=dict(rotation=90, direction='clockwise', gridcolor='#D8D8D8'),
            bgcolor='rgba(0,0,0,0)',
        ),
        legend=dict(title="Velocidad", orientation="h", yanchor="bottom", y=-0.25, x=0.1),
        height=550, font=dict(family="sans-serif", size=10),
        margin=dict(l=60, r=60, t=60, b=90),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def crear_heatmap_plotly(hm_json, media_anual):
    """Heatmap interactivo (mes × hora) -- muestra velocidad REAL en m/s a 10m (altura
    de referencia meteorológica del EPW, WS10M -- ni 0m ni la altura de buje de la
    turbina, eso sale del perfil logarítmico de abajo).

    `hm_json` (heatmap_json_desde_epw()) trae el patrón como ÍNDICE relativo a la media
    anual (valor=1.0 en la media, 2.0 = el doble) -- formato compartido con
    generar_clima_gwa() en engine/simulador_pista_a.py (que sí necesita el índice, para
    escalarlo a distintas medias objetivo). Acá se multiplica por `media_anual` (m/s
    real de la fuente elegida) ANTES de graficar, para mostrar velocidad real de una vez
    -- versión anterior mostraba el índice crudo (máximo visual ~2) y sólo agregaba los
    m/s en el hover; en un screenshot o print no hay hover, así que seguía sin
    entenderse (aclaración pedida después de Hallazgo 37, ver avance-de-proyecto.md).

    El texto del hover se arma en Python (celda por celda), NO con `customdata` +
    `hovertemplate` -- se probó esa vía primero y el Plotly.js que trae Streamlit 1.35
    NO interpola `%{customdata}` en heatmaps (se confirmó en vivo con la app corriendo:
    el hover mostraba literalmente el texto `%{customdata:.2f}` sin reemplazar), así que
    se arma el texto ya resuelto por celda -- funciona en cualquier versión."""
    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    # Parsear formato: lista de dicts con {month, hour, value=índice relativo a la media anual}
    data = json.loads(hm_json) if isinstance(hm_json, str) else hm_json
    indice = np.zeros((12, 24))
    for item in data:
        indice[item["month"] - 1, item["hour"]] = item["value"]
    grid_ms = indice * media_anual

    texto = np.empty((12, 24), dtype=object)
    for m in range(12):
        for h in range(24):
            texto[m, h] = (f"<b>{meses[m]}</b><br>Hora: {h}:00<br>"
                            f"{grid_ms[m, h]:.2f} m/s (índice {indice[m, h]:.2f})")

    fig = go.Figure(data=go.Heatmap(
        z=grid_ms, x=list(range(24)), text=texto, hoverinfo='text',
        y=meses,
        colorscale='RdYlBu_r',
        colorbar=dict(title='m/s', thickness=15)
    ))
    fig.update_layout(
        title="Velocidad media real del viento a 10m (mes × hora)",
        xaxis_title="Hora del día", yaxis_title="Mes",
        height=450, font=dict(family="sans-serif", size=10),
        margin=dict(l=80, r=100, t=50, b=60),
        xaxis=dict(tickmode='linear', tick0=0, dtick=3),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def crear_perfil_viento_plotly(velocidad_10m, z0_ref=0.3, altura_max=10):
    """Perfil logarítmico interactivo con Plotly (paleta azul)."""
    alturas = np.linspace(0.1, altura_max, 100)
    velocidades = wind_at_height_potencia(
        velocidad_10m, 10, alturas, terreno="suburban", terreno_met="country"
    )
    AZUL_CLARO = '#4b6ba9'
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=velocidades, y=alturas,
        fill='tonextx',
        fillcolor='rgba(75, 107, 169, 0.15)',
        line=dict(color=AZUL_CLARO, width=2.5),
        hovertemplate='<b>%{y:.2f}m</b><br>Viento: %{x:.2f} m/s<extra></extra>'
    ))
    fig.update_layout(
        title=f"Perfil logarítmico de viento (z0={z0_ref} m)",
        xaxis_title="Velocidad (m/s)", yaxis_title="Altura (m)",
        height=380, template='plotly_white',
        font=dict(family="sans-serif", size=10),
        margin=dict(l=80, r=60, t=50, b=60),
        xaxis=dict(gridcolor='#E8E8E8'), yaxis=dict(gridcolor='#E8E8E8'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def crear_mapa_estaciones(lat_sitio, lon_sitio, df_estaciones=None):
    """Crea un mapa interactivo Folium con el sitio y estaciones disponibles."""
    m = folium.Map(
        location=[lat_sitio, lon_sitio],
        zoom_start=6,
        tiles="OpenStreetMap"
    )

    # Marcador del sitio en rojo
    folium.CircleMarker(
        location=[lat_sitio, lon_sitio],
        radius=8,
        popup=f"Tu sitio: {lat_sitio:.4f}, {lon_sitio:.4f}",
        color=VERDE,
        fill=True,
        fillColor=VERDE,
        fillOpacity=0.8,
        weight=2,
        opacity=1.0
    ).add_to(m)

    # Estaciones como marcadores verdes
    if df_estaciones is not None and not df_estaciones.empty:
        for idx, row in df_estaciones.iterrows():
            folium.CircleMarker(
                location=[row["lat"], row["lon"]],
                radius=6,
                popup=f"<b>{row['name']}</b><br>{row.get('state', 'N/A')}<br>Distancia: {row['distancia_km']:.1f} km",
                color="#888888",
                fill=True,
                fillColor="#CCCCCC",
                fillOpacity=0.6,
                weight=1,
                opacity=0.8
            ).add_to(m)

    return m


# --- Menú lateral: header de marca + resumen de proyecto (patrón Skyplus) ---
# Clona la estructura real de Skyplus: sidebar es SOLO para marca + resumen de "elegido
# hasta ahora", navegación principal va en TABS en la parte superior. Las 4 secciones
# (Selección de clima, Contexto climático, Equipos y configuración, Resultados) son
# tabs, no botones de navegación que compiten por espacio.

with st.sidebar:
    _logos_html = "".join([
        _img_base64(LOGO_ECO, 90) if os.path.exists(LOGO_ECO) else "",
        _img_base64(LOGO_FLOWER_TURBINES, 90) if os.path.exists(LOGO_FLOWER_TURBINES) else "",
    ])
    st.markdown(f"""
    <div class="eco-brand">
        <div class="eco-brand-logos">{_logos_html}</div>
        <div class="eco-brand-text">
            <div class="eco-brand-title">🌬️ ECO | Wind</div>
            <div class="eco-brand-sub">Simulador de microgeneración eólica</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="eco-sidebar-section">Elegido hasta ahora</div>', unsafe_allow_html=True)
    if st.session_state.get("sitio_activo"):
        st.success(f"📍 {st.session_state.get('sitio_nombre_activo')}")
    else:
        st.caption("Sin sitio seleccionado todavía.")
    _n_turbinas = sum(c["N"] for c in st.session_state.clusters)
    st.caption(f"⚙️ {len(st.session_state.clusters)} clúster(es), {_n_turbinas} turbina(s) en total.")
    if st.session_state.get("calculo_listo"):
        st.caption("✅ Cálculo de producción listo.")

    st.divider()
    st.markdown(f"""
    <div style="font-size:0.62rem; color:{GRIS}; line-height:1.6;">
        Motor: flower_turbines_curves.py (Hallazgo 12)<br>
        Clima: EPW real, estación elegida o subida (Hallazgo 36)<br>
        ECO Consultor · Fase 2 -- avance-de-proyecto.md
    </div>
    """, unsafe_allow_html=True)


# --- Área principal: TABS en la parte superior (patrón Skyplus) ---
# Clona la estructura real de Skyplus: 4 tabs navegables en la parte superior,
# cada uno con su contenido y controles. El sidebar es limpio (solo marca + resumen).

tab_clima, tab_contexto, tab_config, tab_resultados = st.tabs([
    "📍 Selección de clima",
    "📊 Contexto climático",
    "⚙️ Equipos y configuración",
    "📈 Resultados",
])

with tab_clima:
    st.caption("Pega las coordenadas de tu sitio (ej: 9.999665, -84.123064). El sistema busca las estaciones climáticas reales más cercanas -- elegí una de la lista, o subí directo el EPW que quieras usar como referencia.")

    def _buscar_y_guardar(_lat, _lon):
        with st.spinner("Buscando estaciones cercanas..."):
            st.session_state.sitio_lat, st.session_state.sitio_lon = _lat, _lon
            df = obtener_estaciones_cercanas(_lat, _lon)
            st.session_state.sitio_cercanas = df
            if df is None or df.empty:
                st.error("No se encontraron estaciones para esta ubicación.")

    # Input minimalista: solo pegar coordenadas
    col1, col2 = st.columns([3, 1])
    with col1:
        _coords_input = st.text_input(
            "Coordenadas (latitud, longitud)",
            placeholder="Ej: 9.999665, -84.123064",
            key="coords_input"
        )
    with col2:
        st.write("")  # Espaciador
        if st.button("🔍 Buscar"):
            if _coords_input:
                try:
                    partes = [p.strip() for p in _coords_input.split(",")]
                    if len(partes) != 2:
                        st.error("Formato: latitud, longitud (ej: 9.999, -84.123)")
                    else:
                        _lat = float(partes[0])
                        _lon = float(partes[1])
                        _buscar_y_guardar(_lat, _lon)
                        st.rerun()
                except ValueError:
                    st.error("Coordenadas inválidas. Usa números separados por coma.")

    # Mostrar sitio activo si existe
    if st.session_state.sitio_activo:
        st.success(f"✅ Sitio activo: **{st.session_state.sitio_nombre_activo}**")

    st.divider()

    # Mapa interactivo del sitio y estaciones
    if st.session_state.sitio_cercanas is not None and not st.session_state.sitio_cercanas.empty:
        st.subheader("📍 Mapa interactivo")
        mapa = crear_mapa_estaciones(st.session_state.sitio_lat, st.session_state.sitio_lon, st.session_state.sitio_cercanas)
        mapa_html = mapa._repr_html_()
        components.html(mapa_html, height=500, scrolling=False)

    st.divider()

    # Mostrar estaciones disponibles
    _df_cerc = st.session_state.sitio_cercanas
    if _df_cerc is not None and not _df_cerc.empty:
        st.caption("**Estaciones climáticas más cercanas:**")
        for _i, _row in _df_cerc.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{_row['name']}** — {_row.get('state', '')} ({_row['distancia_km']:.0f} km)")
            with col2:
                if st.button("Usar", key=f"btn_est_{_i}"):
                    _res_est = cargar_estacion_elegida(_row)
                    if _res_est.get("error"):
                        st.error(_res_est["error"])
                    else:
                        st.session_state.sitio_activo = _res_est
                        st.session_state.sitio_nombre_activo = _row["name"]
                        st.rerun()

        _dist_min = float(_df_cerc["distancia_km"].min())
        if _dist_min > 40.0:
            st.caption(
                f"ℹ️ La estación real más cercana está a {_dist_min:.0f} km -- si tenés el EPW real "
                "de un sitio más representativo (propio o de otro lugar), subilo abajo en vez de "
                "usar una estación tan lejana."
            )

    st.divider()

    # EPW propio del usuario (Hallazgo 36) -- para un sitio sin estación real cercana, o para
    # usar a propósito el EPW de otro lugar como referencia. Reemplaza el mecanismo viejo de
    # "aproximación sensibilizada" (GWA/ERA5/NASA POWER, Hallazgo 21-30): esas fuentes se
    # descartaron por decisión de producto (Hallazgo 35) -- un EPW real elegido a conciencia es
    # más confiable que un ajuste automático sobre datos que ya demostraron fallar en Costa Rica.
    st.caption("**¿Tenés el EPW real de tu sitio (o de otro lugar que quieras usar como referencia)?**")
    _epw_subido = st.file_uploader("Subir archivo .epw", type=["epw"], key="epw_subido_uploader")
    if _epw_subido is not None:
        if st.button("Usar este EPW"):
            with tempfile.NamedTemporaryFile(suffix=".epw", delete=False) as _tmp:
                _tmp.write(_epw_subido.getvalue())
                _ruta_tmp = _tmp.name
            _res_subido = cargar_epw_subido(_ruta_tmp)
            os.remove(_ruta_tmp)
            if _res_subido.get("error"):
                st.error(_res_subido["error"])
            else:
                st.session_state.sitio_activo = _res_subido
                st.session_state.sitio_nombre_activo = f"EPW subido -- {_epw_subido.name}"
                st.rerun()


# --- Tab: Contexto climático -- rosa de vientos + heatmap, sin depender de "Calcular" ---

with tab_contexto:
    resultado_clima = st.session_state.get("sitio_activo")
    error_clima = None if resultado_clima is None else resultado_clima.get("error")

    if resultado_clima is None:
        st.info("Elegí primero un sitio en la pestaña \"📍 Selección de clima\" para ver su contexto climático.")
    elif error_clima:
        st.error(error_clima, icon="🚫")
    else:
        hm_json = resultado_clima["hm_json"]
        rosa_detallada = resultado_clima["rosa_detallada"]
        media_confirmada = resultado_clima["media"]

        if "meta" in resultado_clima:
            _meta = resultado_clima["meta"]
            st.success(f"Estación real: {_meta['estacion']} ({_meta['pais']}, WMO {_meta['wmo']}) -- "
                       f"lat={_meta['lat']:.4f}, lon={_meta['lon']:.4f}, elevación={_meta['elevacion_m']:.0f}m. "
                       f"Media anual real (10m): {media_confirmada:.2f} m/s.", icon="✅")

        st.divider()
        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(crear_rosa_vientos_plotly(rosa_detallada), use_container_width=True)
        with col_g2:
            st.plotly_chart(crear_heatmap_plotly(hm_json, media_anual=media_confirmada), use_container_width=True)

        st.divider()
        col_perfil = st.columns(1)[0]
        with col_perfil:
            _altura_perfil = st.slider("Altura máxima a mostrar", 1.0, 15.0, 10.0, 0.5, key="altura_perfil_slider")
            st.plotly_chart(crear_perfil_viento_plotly(media_confirmada, altura_max=_altura_perfil), use_container_width=True)


# --- Tab: Equipos y configuración -- turbinas, clústers, parámetros avanzados ---

with tab_config:
    st.subheader("Clústers del proyecto")
    for i, c in enumerate(st.session_state.clusters):
        with st.container():
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

            _specs = SPECS_TURBINAS.get(c["modelo"])
            _ruta_img = RUTA_IMAGEN.get(c["modelo"])
            with st.expander(f"Ficha técnica -- {NOMBRES_MODELO.get(c['modelo'], c['modelo'])}"):
                if not _specs:
                    st.caption("Sin ficha técnica cargada todavía para este modelo.")
                else:
                    col_img, col_specs = st.columns([1, 2])
                    with col_img:
                        if _ruta_img and os.path.exists(_ruta_img):
                            st.image(_ruta_img)
                        else:
                            st.caption("Sin imagen todavía.")
                    with col_specs:
                        st.caption(f"N° de parte: {_specs['numero_parte']} -- {_specs['clase_iec']}")
                        st.markdown(
                            f"- **Potencia nominal:** {_specs['potencia_nominal_w']} W "
                            f"a {_specs['viento_potencia_nominal_ms']} m/s\n"
                            f"- **Cut-in / supervivencia:** {_specs['velocidad_cutin_ms']} m/s / "
                            f"{_specs['velocidad_supervivencia_ms']} m/s\n"
                            f"- **Generador:** {_specs['tipo_generador']} ({_specs['polos_generador']} polos)\n"
                            f"- **Salida:** {_specs['voltaje_salida']}\n"
                            f"- **Dimensiones:** {_specs['altura_total_m']} m altura total, "
                            f"{_specs['diametro_rotor_m']} m diámetro de rotor, "
                            f"{_specs['peso_total_kg']} kg\n"
                            f"- **Vida de diseño:** {_specs['vida_diseno_anos']} años\n"
                            f"- **Cimentación requerida:** {_specs['cimentacion_requerida']}"
                        )

    if st.button("+ Agregar clúster"):
        st.session_state.clusters.append({"modelo": "medium_tulip", "N": 1, "altura_buje": 3.0})
        st.rerun()

    st.divider()

    with st.expander("Parámetros avanzados"):
        z0 = st.selectbox(
            "Rugosidad DEL SITIO donde va la turbina (z0)", options=[0.03, 0.1, 0.3, 1.0],
            format_func=lambda z: {0.03: "0.03 — campo abierto", 0.1: "0.1 — cultivos bajos",
                                    0.3: "0.3 — suburbano (default)", 1.0: "1.0 — urbano denso"}[z],
            index=2, key="z0_avanzado",
            help="Rugosidad del sitio DESTINO (donde se instala la turbina), no la del sitio "
                 "de referencia climática. Desde Hallazgo 20, esta app usa dos rugosidades "
                 "distintas -- ver la nota en Resultados.",
        )
        metodo_bouquet = st.radio(
            "Modelo de Efecto Bouquet", options=["real", "lineal"], key="metodo_bouquet_radio",
            format_func=lambda m: "Real (exponencial, validado R²≥0.999996)" if m == "real"
            else "Lineal de marketing (solo referencia, subestima fuerte)",
        )

    st.divider()

    if not st.session_state.get("sitio_activo"):
        st.warning("Elegí un sitio en la pestaña \"📍 Selección de clima\" antes de calcular.", icon="⚠️")

    if st.button("Calcular producción del proyecto", type="primary"):
        st.session_state.calculo_listo = True
        st.session_state.seccion_activa = "resultados"
        st.rerun()


# --- Tab: Resultados -- por ahora, producción de energía (Hallazgo 12/17) ---

with tab_resultados:
    st.caption(
        "Cálculo financiero (CAPEX, tarifa eléctrica, payback) todavía no está implementado -- "
        "por ahora esta sección muestra la producción de energía del proyecto (fase futura)."
    )

    if st.session_state.get("calculo_listo"):
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")
        z0 = st.session_state.z0_avanzado
        metodo_bouquet = st.session_state.metodo_bouquet_radio

        if resultado_clima is None:
            st.error(
                "Elegí primero una estación (o subí un EPW) en la pestaña \"📍 Selección de clima\".",
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

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Producción anual total", f"{kwh_total:,.0f} kWh")
            c2.metric("Turbinas totales", f"{n_total}")
            c3.metric("Corrección por densidad (elevación)",
                      f"{(1 - resultados[0]['factor_correccion_densidad']) * 100:.1f}% menos")
            c4.metric("Altura de buje", f"{resultados[0]['altura_buje']:.0f} m")

            st.markdown("**Detalle por clúster**")
            tabla = pd.DataFrame([{
                "Modelo": NOMBRES_MODELO.get(r["modelo"], r["modelo"]), "N": r["N"],
                "Buje (m)": r["altura_buje"], "kWh/año": round(r["kwh_anual"]),
                "V. medio buje (m/s)": round(r["v_hub_medio"], 2),
                "% bajo cut-in": round(r["pct_horas_bajo_cutin"], 1),
            } for r in resultados])
            st.dataframe(tabla, hide_index=True)

            media_confirmada = resultado_clima["media"]
            with st.expander("Hallazgo 20 -- perfil de viento por altura: dos rugosidades, y un cross-check independiente"):
                _r0 = resultados[0]
                _v_pot = wind_at_height_potencia(
                    media_confirmada, 10, _r0["altura_buje"], terreno="suburban", terreno_met="country")
                st.write(
                    f"El viento de referencia (10m, aeropuerto/EPW) y el sitio real donde va la "
                    f"turbina casi nunca tienen la misma rugosidad -- hasta Hallazgo 20 esta app usaba "
                    f"un solo z0 para los dos, lo que sobreestimaba la velocidad en buje 16-24% (según "
                    f"el método) en el caso de San José, y como P∝v³ eso es ~1.6-1.9x de más en energía. "
                    f"Ahora se usa z0 del sitio destino (seleccionable arriba en esta pestaña) "
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
            kwh_mensual_total = pd.concat([r["kwh_mensual"] for r in resultados], axis=1).sum(axis=1)
            st.plotly_chart(crear_produccion_mensual_plotly(kwh_mensual_total), use_container_width=True)
            st.plotly_chart(crear_curva_duracion_plotly(serie_total_w), use_container_width=True)

            st.caption(
                "Motor: `flower_turbines_curves.py` (validado Hallazgo 12) + corrección de densidad de aire "
                "por elevación (Hallazgo 17). Fuente climática: EPW real, estación elegida o subida por "
                "el usuario (Hallazgo 36) -- sin sensibilización espacial por GWA/NASA POWER/ERA5."
            )
    else:
        st.info("Configurá el proyecto en la pestaña \"⚙️ Equipos y configuración\" y presioná "
                 "**Calcular producción del proyecto**.")

st.divider()
st.caption(
    "ECO Consultor — Simulador en desarrollo (Fase 2). "
    "Pendiente: cálculo financiero (CAPEX, tarifa, payback), DEM automático para elevación, "
    "PDF de cotización, registro de leads, despliegue a Cloud Run."
)
