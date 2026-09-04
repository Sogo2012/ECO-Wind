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
from datetime import date

import folium
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulador_pista_a import (
    simular, comparar_metodo_ingenuo_vs_horario, wind_at_height, wind_at_height_potencia,
    terreno_mas_cercano_por_z0, Z0_DEFAULT, Z0_MET_DEFAULT,
)
from engine.flower_turbines_curves import CURVE_COEFFICIENTS
from engine.turbine_specs import SPECS_TURBINAS, RUTA_IMAGEN, LOGO_ECO, LOGO_FLOWER_TURBINES
from engine.epw_real import (
    SITIOS_EPW_REAL, cargar_epw_real, heatmap_json_desde_epw, rosa_vientos_detallada_desde_epw,
    obtener_estaciones_cercanas, geocode_name, descargar_y_extraer_epw, sitio_precacheado_cercano,
)
from engine.tipo_cambio_bccr import obtener_tipo_cambio_bccr
from engine.financial_engine_eolico import FinancialEngineEolico
from engine.tarifas_electricas_cr import calcular_ahorro_tarifa_horaria_usd, calcular_ahorro_tarifa_comercial_usd
from engine.precios_flower_turbines import get_articulos_disponibles, get_precio_exworks_usd
from engine.dimensionador_sistema_eolico import VOLTAJE_TURBINAS_V
from engine.pdf_reporte import generar_pdf_especificacion

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# --- Paleta corporativa ECO -- colores EXACTOS de libro_de_marca_de_Eco_consultor.pdf
# (Hallazgo 49), reemplazando los valores aproximados que traía la app desde antes
# (AZUL era #003C52, el real es #173D4A; VERDE era #4A7C2F, el real es #66913E; GRIS
# era #4A5568, el real es #414549). Significado de cada color según el manual: azul =
# "conservación del ambiente", verde = "confort y ahorro energético", gris = "obra gris".
AZUL = "#173D4A"    # Pantone 309 C
VERDE = "#66913E"   # Pantone 575 C
GRIS = "#414549"    # Pantone 432 C
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
    "al13_8m": "AL13 Power Tower (8 módulos)",
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


st.set_page_config(page_title="ECO | Wind — Simulador", page_icon=LOGO_ECO, layout="wide")

# Fondo y colores base de la app: los define .streamlit/config.toml (theme.backgroundColor,
# etc.) -- Streamlit los aplica solo, sin necesitar un ".stApp { background-color: ... }"
# a mano acá. Forzarlo con CSS (como estaba antes) pisaba ese mecanismo nativo sin ninguna
# ventaja real. Lo que sigue son estilos de componentes propios (menu lateral, header de
# marca) que Streamlit no cubre con su sistema de theme, así que sí necesitan CSS.
st.markdown(f"""
<style>
    /* Tipografía corporativa (libro_de_marca_de_Eco_consultor.pdf, Hallazgo 49): la
       fuente de marca es "Gotham", que es de pago y no está en Google Fonts -- se usa
       Montserrat como sustituto libre estándar (geometría muy similar, elección común
       para reemplazar Gotham). "Dosis" sí es la real y sí está en Google Fonts -- el
       manual la reserva para texto de descripción, no para títulos. */
    @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@400;500;700&family=Dosis:wght@400;500;700&display=swap');
    html, body, [class*="css"] {{ font-family: 'Montserrat', sans-serif; }}
    .eco-brand-sub, .eco-sidebar-section, [data-testid="stCaptionContainer"] {{ font-family: 'Dosis', sans-serif; }}
    h1, h2, h3 {{ color: {AZUL}; font-family: 'Montserrat', sans-serif; font-weight: 700; }}
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
    .eco-brand-logos {{ background: #FFFFFF; padding: 16px; display: flex; align-items: center; justify-content: center; }}
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
            f"No se pudo descargar los datos de {row['name']}. "
            "Verificá la conexión a internet e intentá de nuevo."
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
    except Exception as e:
        return dict(error=(
            f"No se pudo leer el archivo como EPW válido: {e} -- confirmá que es un .epw real "
            "(formato EnergyPlus/climate.onebuilding.org, 8 líneas de encabezado + una fila por "
            "hora) y no un archivo renombrado o exportado de otra herramienta."
        ))
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


def crear_heatmap_plotly(hm_json, media_anual, altura_m=10.0, z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT):
    """Heatmap interactivo (mes × hora) -- velocidad REAL en m/s, a la altura `altura_m`
    (default 10m, la altura de referencia meteorológica del EPW, WS10M).

    `hm_json` (heatmap_json_desde_epw()) trae el patrón como ÍNDICE relativo a la media
    anual A 10M (valor=1.0 en la media, 2.0 = el doble) -- formato compartido con
    generar_clima_gwa() en engine/simulador_pista_a.py (que sí necesita el índice, para
    escalarlo a distintas medias objetivo). Acá se multiplica por `media_anual` para
    tener la velocidad real a 10m, y LUEGO se lleva a `altura_m` con el mismo perfil
    logarítmico de dos rugosidades que usa `simular()` para el cálculo de energía real
    (`wind_at_height()`, Hallazgo 20) -- así el heatmap muestra la misma velocidad de
    buje que de verdad entra a la curva de potencia, no sólo la de 10m.

    Como `wind_at_height()` escala la velocidad por un factor que sólo depende de la
    altura (no del valor de v en sí -- es la misma razón logarítmica para cualquier
    hora), cambiar `altura_m` reescala el heatmap COMPLETO por una misma constante: el
    patrón (qué horas/meses son más ventosos que otros) no cambia, sólo la escala de
    colores -- es el resultado esperado de este modelo, no una limitación del gráfico.

    Si `altura_m` queda por debajo de `z0` (subcapa de rugosidad, perfil no confiable),
    devuelve (None, aviso) en vez de una figura -- mismo criterio que wind_at_height().

    El texto del hover se arma en Python (celda por celda), NO con `customdata` +
    `hovertemplate` -- se probó esa vía primero y el Plotly.js que trae Streamlit 1.35
    NO interpola `%{customdata}` en heatmaps (se confirmó en vivo con la app corriendo:
    el hover mostraba literalmente el texto `%{customdata:.2f}` sin reemplazar), así que
    se arma el texto ya resuelto por celda -- funciona en cualquier versión."""
    if altura_m <= z0:
        return None, (f"Altura elegida ({altura_m:.1f}m) por debajo de la rugosidad del "
                       f"terreno destino (z0={z0}m) -- el perfil logarítmico no es "
                       f"físicamente confiable ahí, mismo criterio que wind_at_height().")

    meses = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    # Parsear formato: lista de dicts con {month, hour, value=índice relativo a la media anual a 10m}
    data = json.loads(hm_json) if isinstance(hm_json, str) else hm_json
    indice = np.zeros((12, 24))
    for item in data:
        indice[item["month"] - 1, item["hour"]] = item["value"]
    grid_10m = indice * media_anual
    grid_ms = wind_at_height(grid_10m, 10, altura_m, z0=z0, z0_met=z0_met)

    texto = np.empty((12, 24), dtype=object)
    for m in range(12):
        for h in range(24):
            texto[m, h] = (f"<b>{meses[m]}</b><br>Hora: {h}:00<br>"
                            f"{grid_ms[m, h]:.2f} m/s a {altura_m:.1f}m "
                            f"(índice {indice[m, h]:.2f})")

    fig = go.Figure(data=go.Heatmap(
        z=grid_ms, x=list(range(24)), text=texto, hoverinfo='text',
        y=meses,
        colorscale='RdYlBu_r',
        colorbar=dict(title='m/s', thickness=15)
    ))
    fig.update_layout(
        title=f"Velocidad media real del viento a {altura_m:.1f}m (mes × hora)",
        xaxis_title="Hora del día", yaxis_title="Mes",
        height=450, font=dict(family="sans-serif", size=10),
        margin=dict(l=80, r=100, t=50, b=60),
        xaxis=dict(tickmode='linear', tick0=0, dtick=3),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig, None


def crear_perfil_viento_plotly(velocidad_10m, z0=Z0_DEFAULT, z0_met=Z0_MET_DEFAULT,
                                altura_max=10, altura_marcada=None):
    """Perfil logarítmico interactivo con Plotly (paleta azul) -- MISMA fórmula y
    rugosidades que `simular()` usa para el cálculo real de energía
    (`wind_at_height()`, log law con z0 de destino y z0_met de referencia
    meteorológica, Hallazgo 20).

    BUG REAL corregido acá: la versión anterior recibía un `z0_ref` que sólo se
    mostraba en el título -- el cálculo en sí ignoraba ese valor y usaba SIEMPRE la ley
    de potencia con terreno "suburban" fijo (z0=0.5m según TERRENOS_ENERGYPLUS), sin
    importar lo que dijera el título (que por default decía "z0=0.3 m", un valor
    DISTINTO al que realmente se estaba usando). Ahora `z0` se usa de verdad, con la
    misma ley logarítmica que ya usa el cálculo de producción -- no la ley de potencia
    (esa queda sólo para el cross-check explícito de Hallazgo 20 en Resultados).

    `altura_marcada`: si se da, agrega un punto + anotación en esa altura exacta (para
    que se vea el mismo valor que muestra el heatmap a esa altura, con el mismo z0)."""
    alturas = np.linspace(0.1, altura_max, 100)
    velocidades = wind_at_height(velocidad_10m, 10, alturas, z0=z0, z0_met=z0_met)
    AZUL_CLARO = '#4b6ba9'
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=velocidades, y=alturas,
        fill='tonextx',
        fillcolor='rgba(75, 107, 169, 0.15)',
        line=dict(color=AZUL_CLARO, width=2.5),
        hovertemplate='<b>%{y:.2f}m</b><br>Viento: %{x:.2f} m/s<extra></extra>',
        showlegend=False,
    ))
    if altura_marcada is not None:
        v_marcada = float(wind_at_height(velocidad_10m, 10, altura_marcada, z0=z0, z0_met=z0_met))
        fig.add_trace(go.Scatter(
            x=[v_marcada], y=[altura_marcada], mode='markers+text',
            marker=dict(color='#ea2600', size=10),
            text=[f"{v_marcada:.2f} m/s"], textposition='top center',
            hovertemplate=f'<b>{altura_marcada:.2f}m</b><br>Viento: {v_marcada:.2f} m/s<extra></extra>',
            showlegend=False,
        ))
    fig.update_layout(
        title=f"Perfil logarítmico de viento (z0 destino={z0} m)",
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
    # Sólo el logo de ECO en el header (antes compartía espacio con el de Flower
    # Turbines y ambos quedaban chicos) -- Flower Turbines es un proveedor de equipos,
    # no la marca de la aplicación; se sigue identificando por nombre en las fichas
    # técnicas de cada turbina (pestaña "Especificación Técnica").
    _logo_eco_html = _img_base64(LOGO_ECO, 170) if os.path.exists(LOGO_ECO) else ""
    st.markdown(f"""
    <div class="eco-brand">
        <div class="eco-brand-logos">{_logo_eco_html}</div>
        <div class="eco-brand-text">
            <div class="eco-brand-title">ECO | Wind</div>
            <div class="eco-brand-sub">Simulador de microgeneración eólica</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="eco-sidebar-section">Elegido hasta ahora</div>', unsafe_allow_html=True)
    if st.session_state.get("sitio_activo"):
        st.success(f"{st.session_state.get('sitio_nombre_activo')}")
    else:
        st.caption("Sin sitio seleccionado todavía.")
    _n_turbinas = sum(c["N"] for c in st.session_state.clusters)
    st.caption(f"{len(st.session_state.clusters)} clúster(es), {_n_turbinas} turbina(s) en total.")
    if st.session_state.get("calculo_listo"):
        st.caption("Cálculo de producción listo.")

    st.divider()
    # Una sola consulta al BCCR por sesión: obtener_tipo_cambio_bccr() ya
    # cachea a su propio nivel (archivo local), esto solo evita repetir la
    # llamada en cada rerun de Streamlit dentro de la misma sesión de usuario.
    if "tipo_cambio_bccr" not in st.session_state:
        st.session_state["tipo_cambio_bccr"] = obtener_tipo_cambio_bccr()
    _tipo_cambio, _tc_es_emergencia = st.session_state["tipo_cambio_bccr"]
    st.metric("💵 Tipo de cambio BCCR", f"₡{_tipo_cambio:,.2f}")
    if _tc_es_emergencia:
        st.caption("⚠️ BCCR no disponible -- valor de emergencia, no del día.")

    st.divider()
    st.markdown(f"""
    <div style="font-size:0.62rem; color:{GRIS}; line-height:1.6;">
        ECO Consultor
    </div>
    """, unsafe_allow_html=True)


# --- Área principal: TABS en la parte superior (patrón Skyplus) ---
# Clona la estructura real de Skyplus: 4 tabs navegables en la parte superior,
# cada uno con su contenido y controles. El sidebar es limpio (solo marca + resumen).

tab_clima, tab_contexto, tab_config, tab_resultados, tab_financiero, tab_especificacion = st.tabs([
    "Selección de clima",
    "Contexto climático",
    "Equipos y configuración",
    "Resultados",
    "Análisis Financiero",
    "Especificación Técnica",
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
        if st.button("Buscar"):
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
        st.success(f"Sitio activo: **{st.session_state.sitio_nombre_activo}**")

    st.divider()

    # Mapa interactivo del sitio y estaciones
    if st.session_state.sitio_cercanas is not None and not st.session_state.sitio_cercanas.empty:
        st.subheader("Mapa interactivo")
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
                f"La estación real más cercana está a {_dist_min:.0f} km -- si tenés el EPW real "
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
        st.info("Elegí primero un sitio en la pestaña \"Selección de clima\" para ver su contexto climático.")
    elif error_clima:
        st.error(error_clima)
    else:
        hm_json = resultado_clima["hm_json"]
        rosa_detallada = resultado_clima["rosa_detallada"]
        media_confirmada = resultado_clima["media"]

        if "meta" in resultado_clima:
            _meta = resultado_clima["meta"]
            st.success(f"Estación real: {_meta['estacion']} ({_meta['pais']}, WMO {_meta['wmo']}) -- "
                       f"lat={_meta['lat']:.4f}, lon={_meta['lon']:.4f}, elevación={_meta['elevacion_m']:.0f}m. "
                       f"Media anual real (10m): {media_confirmada:.2f} m/s.")

        st.divider()

        # Altura de buje a explorar (Hallazgo 39): un solo slider mueve tanto el heatmap
        # como el perfil de abajo, con la MISMA rugosidad de destino que se usa en el
        # cálculo real de energía (Equipos y configuración > Parámetros avanzados) --
        # si esa pestaña todavía no se visitó en esta sesión, cae al default de simular().
        z0_actual = st.session_state.get("z0_avanzado", Z0_DEFAULT)
        _altura_explorar = st.slider(
            "Altura de buje a explorar (m)", 0.5, 150.0, 10.0, 0.5, key="altura_explorar_slider",
            help="Mueve esta altura para ver cómo cambia la velocidad real del viento (heatmap y "
                 "perfil de abajo) entre la altura de referencia del EPW (10m) y la altura real de "
                 "buje de tu turbina -- misma fórmula y rugosidad que usa el cálculo de energía. "
                 "Para una instalación en TECHO de un edificio, usá altura del edificio + altura del "
                 "mástil sobre el techo -- ojo, la ley logarítmica extrapola la velocidad REGIONAL "
                 "a esa altura, no el efecto aerodinámico local de estar encima de un edificio "
                 "puntual (aceleración sobre el borde del techo, turbulencia).",
        )
        st.caption(
            f"Rugosidad de destino usada abajo: z0={z0_actual} m -- configurable en "
            f"\"Equipos y configuración\" > Parámetros avanzados."
        )

        col_g1, col_g2 = st.columns(2)
        with col_g1:
            st.plotly_chart(crear_rosa_vientos_plotly(rosa_detallada), use_container_width=True)
        with col_g2:
            _fig_heatmap, _aviso_heatmap = crear_heatmap_plotly(
                hm_json, media_anual=media_confirmada, altura_m=_altura_explorar, z0=z0_actual)
            if _aviso_heatmap:
                st.warning(_aviso_heatmap)
            else:
                st.plotly_chart(_fig_heatmap, use_container_width=True)

        st.divider()
        col_perfil = st.columns(1)[0]
        with col_perfil:
            _altura_max_perfil = max(_altura_explorar * 1.15, 10.0)
            st.plotly_chart(
                crear_perfil_viento_plotly(media_confirmada, z0=z0_actual,
                                            altura_max=_altura_max_perfil, altura_marcada=_altura_explorar),
                use_container_width=True)


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
            c["altura_buje"] = cc3.number_input(
                "Buje (m)", min_value=0.5, max_value=150.0,
                value=c["altura_buje"], step=0.5, key=f"h_{i}",
                help="Para una instalación en TECHO (ej. azotea de un edificio de varios pisos): "
                     "altura del edificio (m) + altura del mástil/soporte sobre el techo -- NO la "
                     "cantidad de pisos. Un edificio de 15 pisos ronda 45-55m según la altura de "
                     "entrepiso.",
            )
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
                 "de referencia climática -- son dos valores distintos (ver el detalle en "
                 "\"Resultados\").",
        )
        metodo_bouquet = st.radio(
            "Modelo de Efecto Bouquet", options=["real", "lineal"], key="metodo_bouquet_radio",
            format_func=lambda m: "Real (exponencial, validado R²≥0.999996)" if m == "real"
            else "Lineal de marketing (solo referencia, subestima fuerte)",
        )

    st.divider()

    if not st.session_state.get("sitio_activo"):
        st.warning("Elegí un sitio en la pestaña \"Selección de clima\" antes de calcular.")

    if st.button("Calcular producción del proyecto", type="primary"):
        st.session_state.calculo_listo = True
        st.session_state.seccion_activa = "resultados"
        st.rerun()


# --- Tab: Resultados -- por ahora, producción de energía (Hallazgo 12/17) ---

with tab_resultados:
    st.caption(
        "Producción de energía del proyecto -- el cálculo financiero (CAPEX, tarifa eléctrica, "
        "payback) está en la pestaña \"Análisis Financiero\"."
    )

    if st.session_state.get("calculo_listo"):
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")
        z0 = st.session_state.z0_avanzado
        metodo_bouquet = st.session_state.metodo_bouquet_radio

        if resultado_clima is None:
            st.error(
                "Elegí primero una estación (o subí un EPW) en la pestaña \"Selección de clima\".",
            )
        elif error:
            st.error(error)
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
            with st.expander("Perfil de viento por altura: dos rugosidades, y una verificación independiente"):
                _r0 = resultados[0]
                # El cross-check usa el MISMO z0 de destino que ya eligió el usuario arriba
                # (mapeado a la clase de TERRENOS_ENERGYPLUS más cercana) -- antes quedaba fijo
                # en "suburban" sin importar el z0 real seleccionado (Hallazgo 52: nada
                # hardcodeado, el tipo de terreno lo elige el usuario).
                _terreno_dst = terreno_mas_cercano_por_z0(z0)
                _v_pot = wind_at_height_potencia(
                    media_confirmada, 10, _r0["altura_buje"], terreno=_terreno_dst, terreno_met="country")
                st.write(
                    f"El viento de referencia (10m, aeropuerto/EPW) y el sitio real donde va la "
                    f"turbina casi nunca tienen la misma rugosidad. Por eso esta app usa z0 del "
                    f"sitio destino (seleccionable arriba en esta pestaña) **distinto** de z0 de "
                    f"referencia (0.1, clase \"country\"/aeropuerto -- fórmula logarítmica)."
                )
                st.write(
                    f"**Verificación independiente** (ley de potencia que usa EnergyPlus por default, "
                    f"misma tabla de terrenos que ladybug-tools/ladybug, con el mismo **z0={z0}** elegido "
                    f"arriba -- internamente la clase con ese z0 tabulado se llama \"{_terreno_dst}\" en "
                    f"la tabla original de EnergyPlus, aunque el nombre no siempre calce 1 a 1 con las "
                    f"etiquetas en español de esta app): "
                    f"{_v_pot:.2f} m/s a {_r0['altura_buje']:.1f}m de buje, vs. "
                    f"**{_r0['v_hub_medio']:.2f} m/s** con la fórmula logarítmica usada arriba -- "
                    f"{'concuerdan razonablemente' if abs(_v_pot/_r0['v_hub_medio']-1) < 0.15 else 'difieren más de lo esperado, revisar'}."
                )

            with st.expander("¿Por qué el cálculo es hora por hora, y no con la velocidad media?"):
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
                "Cálculo validado con datos de campo, con corrección por densidad de aire según "
                "elevación. Fuente climática: EPW real de la estación elegida o subida por el usuario."
            )
    else:
        st.info("Configurá el proyecto en la pestaña \"Equipos y configuración\" y presioná "
                 "**Calcular producción del proyecto**.")


# --- Tab: Análisis Financiero (Hallazgo 40-48) -- CAPEX, inversor/BESS recomendados, payback/ROI/NPV ---

with tab_financiero:
    st.caption(
        "Viabilidad económica del proyecto (CAPEX, Payback, ROI, NPV) -- usa las turbinas ya "
        "configuradas en \"Equipos y configuración\" y la producción ya calculada en \"Resultados\"."
    )

    modulo_financiero_activo = st.toggle(
        "Activar módulo financiero (viabilidad económica)",
        value=True,
        key="fin_modulo_activo",
        help="Apagalo si por ahora sólo te interesa el dimensionamiento técnico (pestaña "
             "\"Especificación Técnica\") y no necesitás calcular CAPEX/Payback/ROI todavía.",
    )

    if not modulo_financiero_activo:
        st.info(
            "Módulo financiero desactivado. Activá el switch de arriba para ingresar costos "
            "reales y calcular Payback, ROI, NPV y viabilidad económica."
        )
    elif not st.session_state.get("calculo_listo"):
        st.info("Configurá el proyecto en la pestaña \"Equipos y configuración\" y presioná "
                 "**Calcular producción del proyecto** primero.")
    else:
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")

        if resultado_clima is None:
            st.error(
                "Elegí primero una estación (o subí un EPW) en la pestaña \"Selección de clima\".",
            )
        elif error:
            st.error(error)
        else:
            df_clima = resultado_clima["df_clima"]
            elevacion_m = resultado_clima["elevacion_m"]
            z0 = st.session_state.z0_avanzado
            metodo_bouquet = st.session_state.metodo_bouquet_radio

            # Mismo cálculo de kWh/año que "Resultados" (Hallazgo 12/17), recalculado acá
            # para no depender de que el usuario haya visitado esa pestaña en esta sesión.
            # Se guarda también la serie horaria completa del proyecto (Hallazgo 54): la
            # tarifa horaria de Costa Rica necesita saber A QUÉ HORA se genera cada kWh, no
            # sólo el total anual -- serie_horaria_W_por_turbina es POR TURBINA, se escala
            # por N de cada clúster y se suman todos para tener el perfil horario del proyecto.
            resultados_clusters = [
                simular(df_clima, altura_buje=c["altura_buje"], modelo=c["modelo"], N=int(c["N"]),
                        elevacion_m=elevacion_m, z0=z0, metodo_bouquet=metodo_bouquet)
                for c in st.session_state.clusters
            ]
            kwh_anual_total = sum(r["kwh_anual"] for r in resultados_clusters)
            serie_horaria_kwh_total = sum(
                r["serie_horaria_W_por_turbina"] * int(c["N"]) / 1000.0
                for r, c in zip(resultados_clusters, st.session_state.clusters)
            )
            turbinas_seleccionadas = [
                c["modelo"] for c in st.session_state.clusters for _ in range(int(c["N"]))
            ]

            # Hallazgo 57: se dejó de dimensionar/costear el BESS acá -- consumo diario,
            # horas de autonomía y tipo de sistema quedaron sin efecto en Payback/ROI/NPV
            # (sistema_tipo es puramente informativo en FinancialEngineEolico, default
            # "Standalone"). Se sacan los inputs de la UI para no mostrar parámetros que
            # ya no dimensionan nada.
            sistema_tipo = "Standalone"

            st.markdown("**Tarifa eléctrica**")
            modo_tarifa = st.radio(
                "¿Cómo querés valorar el ahorro de electricidad?",
                ["Tarifa plana (USD/kWh)", "Tarifa horaria real de Costa Rica (ARESEP)",
                 "Tarifa comercial de Costa Rica (T-CO)"],
                horizontal=True,
                key="fin_modo_tarifa",
                help="La tarifa horaria cruza la producción REAL hora por hora de la turbina "
                     "contra los periodos Punta/Valle/Nocturno de CNFL/ICE -- un kWh generado "
                     "en horario Punta vale varias veces más que uno generado de noche, algo "
                     "que una tarifa plana no puede reflejar. La tarifa comercial (T-CO) es "
                     "para gimnasios/estadios/comercios -- precio plano por kWh según el "
                     "consumo mensual del sitio, sin periodos horarios.",
            )

            resultado_tou = None
            resultado_co = None
            if modo_tarifa == "Tarifa plana (USD/kWh)":
                tarifa_kwh_USD = st.number_input(
                    "Tarifa eléctrica ($/kWh)", min_value=0.01, value=0.15, step=0.01, format="%.2f",
                    key="fin_tarifa_kwh")
            elif modo_tarifa == "Tarifa comercial de Costa Rica (T-CO)":
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    proveedor_co = st.selectbox(
                        "Proveedor", ["CNFL", "ICE"], key="fin_co_proveedor",
                        help="CNFL cubre el Gran Área Metropolitana; ICE el resto del país.",
                    )
                with col_c2:
                    tramo_label = st.selectbox(
                        "Consumo mensual del sitio",
                        ["≤ 3000 kWh/mes (sin medidor de potencia)",
                         "> 3000 kWh/mes (con medidor de potencia)"],
                        key="fin_co_tramo",
                        help="Determina qué tarifa T-CO aplica -- gimnasios/estadios grandes "
                             "normalmente caen en el tramo >3000 kWh/mes.",
                    )
                tramo_co = "pequeno" if tramo_label.startswith("≤") else "grande"
                with col_c3:
                    tipo_cambio_crc_usd = st.number_input(
                        "Tipo de cambio (₡ por USD)", min_value=1.0, value=520.0, step=1.0,
                        key="fin_co_tipo_cambio",
                        help="Verificá el tipo de cambio de referencia del Banco Central de Costa "
                             "Rica (BCCR) antes de cotizar -- cambia a diario, este es sólo un punto "
                             "de partida editable, no un valor fijo del sistema.",
                    )

                try:
                    resultado_co = calcular_ahorro_tarifa_comercial_usd(
                        kwh_anual_total, proveedor_co, tramo_co, tipo_cambio_crc_usd,
                    )
                except ValueError as e:
                    st.error(str(e))

                if resultado_co:
                    st.caption(
                        f"Tarifa T-CO: ₡{resultado_co['precio_crc_kwh']:.2f}/kWh → "
                        f"\\${resultado_co['ahorro_anual_usd']:,.0f}/año "
                        f"({resultado_co['ahorro_anual_crc']:,.0f} ₡/año)."
                    )
                    st.info(
                        "Esta tarifa NO incluye el cargo por demanda máxima (kW) que T-CO "
                        "también cobra en el tramo >3000 kWh -- calcularlo requeriría el perfil "
                        "de demanda horaria del sitio (no sólo el consumo diario promedio) para "
                        "saber si la turbina genera justo en el instante del pico. Este número "
                        "es sólo el ahorro de energía, no el ahorro total de la factura."
                    )
            else:
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    proveedor_tou = st.selectbox(
                        "Proveedor", ["CNFL", "ICE"], key="fin_tou_proveedor",
                        help="CNFL cubre el Gran Área Metropolitana; ICE el resto del país.",
                    )
                opciones_tarifa_tou = {
                    "CNFL": ["T-REH (0-500 kWh)", "T-REH (>500 kWh)"],
                    "ICE": ["T-RH", "T-MT (Media Tensión Max)"],
                }[proveedor_tou]
                with col_t2:
                    tarifa_tou = st.selectbox(
                        "Tarifa", opciones_tarifa_tou, key="fin_tou_tarifa",
                        help="T-REH/T-RH: residencial. T-MT: media tensión (proyectos más grandes).",
                    )
                with col_t3:
                    tipo_cambio_crc_usd = st.number_input(
                        "Tipo de cambio (₡ por USD)", min_value=1.0, value=520.0, step=1.0,
                        key="fin_tipo_cambio",
                        help="Verificá el tipo de cambio de referencia del Banco Central de Costa "
                             "Rica (BCCR) antes de cotizar -- cambia a diario, este es sólo un punto "
                             "de partida editable, no un valor fijo del sistema.",
                    )

                try:
                    resultado_tou = calcular_ahorro_tarifa_horaria_usd(
                        serie_horaria_kwh_total, proveedor_tou, tarifa_tou, tipo_cambio_crc_usd,
                    )
                except ValueError as e:
                    st.error(str(e))

                if resultado_tou:
                    # Dos "$" en el mismo st.caption() arman un par que Streamlit interpreta
                    # como LaTeX ($...$) -- se escapan con "\$" (mismo bug real de Hallazgo 48).
                    st.caption(
                        f"Tarifa efectiva ponderada por producción real: "
                        f"\\${resultado_tou['tarifa_efectiva_usd_kwh']:.4f}/kWh "
                        f"({resultado_tou['ahorro_anual_crc']:,.0f} ₡/año → "
                        f"\\${resultado_tou['ahorro_anual_usd']:,.0f}/año)."
                    )
                    tabla_periodos = pd.DataFrame([
                        {"Periodo": periodo, "kWh/año": v["kwh"],
                         "Precio (₡/kWh)": v["precio_crc_kwh"], "Valor (USD/año)": v["usd"]}
                        for periodo, v in resultado_tou["desglose_por_periodo"].items()
                    ])
                    st.dataframe(
                        tabla_periodos.style.format({
                            "kWh/año": "{:,.0f}", "Precio (₡/kWh)": "{:,.2f}", "Valor (USD/año)": "${:,.0f}",
                        }),
                        hide_index=True,
                    )

            with st.expander("Parámetros avanzados"):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    vida_util_anos = st.number_input(
                        "Vida útil del proyecto (años)", min_value=1, value=40, step=1)
                with col_a2:
                    tasa_descuento_pct = st.number_input(
                        "Tasa de descuento para NPV (%)", min_value=0.0, value=8.0, step=0.5)

            # Hallazgo 57: se deja de dimensionar/costear el inversor Sol-Ark y el BESS acá --
            # por ahora la app sólo valora equipo Flower Turbines (turbinas), a pedido explícito
            # de Pablo. Sólo hace falta la potencia pico y la cantidad total de turbinas del
            # arreglo (el motor financiero las usa sólo como dato informativo, no cambian
            # Payback/ROI/NPV) -- eso no depende de qué inversor se use.
            _potencia_pico_total_W = sum(
                SPECS_TURBINAS[modelo]["potencia_nominal_w"] for modelo in turbinas_seleccionadas
            )
            _cantidad_turbinas_total = len(turbinas_seleccionadas)

            st.divider()
            st.markdown("**Selección de equipo -- precio EXWORKS**")
            st.caption(
                "Elegí acá, por clúster, el artículo exacto del catálogo real de Flower Turbines "
                "que vas a cotizar -- el grupo ya se filtra automático según el modelo elegido en "
                "\"Equipos y configuración\", vos elegís la variante (unidad simple, bouquet, "
                "on/off-grid, con o sin accesorio). Esto es sólo de referencia para llenar el "
                "costeo de abajo -- no se usa solo para calcular Payback/ROI."
            )
            _precio_total_proyecto = 0.0
            _algun_modelo_sin_precio = False
            for _i, _c in enumerate(st.session_state.clusters):
                _articulos_disponibles = get_articulos_disponibles(_c["modelo"])
                _nombre_modelo = NOMBRES_MODELO.get(_c["modelo"], _c["modelo"])
                if not _articulos_disponibles:
                    st.caption(
                        f"{_nombre_modelo}: precio no disponible todavía (no hay artículo cargado "
                        "en el catálogo)."
                    )
                    _algun_modelo_sin_precio = True
                    continue
                _opciones_articulo = [art for art, _ in _articulos_disponibles]
                _articulo_guardado = _c.get("articulo")
                _idx_articulo = (
                    _opciones_articulo.index(_articulo_guardado)
                    if _articulo_guardado in _opciones_articulo else 0
                )
                _c["articulo"] = st.selectbox(
                    f"Artículo -- {_nombre_modelo} ({int(_c['N'])}x)", options=_opciones_articulo,
                    index=_idx_articulo, key=f"articulo_fin_{_i}",
                    help="Precio de venta real de fábrica -- elegí la variante exacta que vas a "
                         "cotizar (unidad simple, bouquet, on/off-grid, con o sin accesorio).",
                )
                _precio_unitario = get_precio_exworks_usd(_c["modelo"], _c["articulo"])
                _precio_total_proyecto += _precio_unitario * _c["N"]
                # Dos "$" en el mismo st.caption() arman un par que Streamlit interpreta
                # como LaTeX ($...$) -- se escapan con "\$" (mismo bug real de Hallazgo 48).
                st.caption(
                    f"Precio: \\${_precio_unitario:,.0f} c/u -- "
                    f"Total del clúster ({int(_c['N'])}x): \\${_precio_unitario * _c['N']:,.0f}"
                )
            st.metric("Precio total del proyecto (equipos, EXWORKS)", f"${_precio_total_proyecto:,.0f}")
            st.caption(
                "Precio de venta de fábrica del artículo elegido en cada clúster. NO incluye "
                "flete, importación ni instalación -- eso lo agrega ECO Consultor aparte. Es el "
                "precio del artículo elegido × cantidad de turbinas del clúster -- si elegís un "
                "artículo de \"bouquet\" (varias turbinas con un solo inversor), revisá que la "
                "cantidad (N) del clúster tenga sentido con ese artículo."
                + (" Al menos un modelo elegido todavía no tiene ningún artículo cargado." if _algun_modelo_sin_precio else "")
            )

            st.divider()
            st.markdown("**Costeo real del proyecto**")
            st.caption(
                "En vez de estimar el CAPEX con costo de fábrica + margen + flete supuestos, "
                "ingresá acá los números reales de tu cotización: cuánto cuestan los equipos, a "
                "cuánto se los vas a vender al cliente, y cuánto vas a cobrar de mantenimiento al "
                "año. Payback, ROI, NPV y viabilidad se calculan directo de esos datos."
            )
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                costo_equipos_usd = st.number_input(
                    "Costo de los equipos (turbinas + inversor + BESS, USD)",
                    min_value=0.0, value=0.0, step=100.0, format="%.2f",
                    key="fin_costo_equipos",
                    help="Lo que ECO Consultor paga por comprar/importar los equipos -- sólo "
                         "informativo, para ver el margen (no entra en el cálculo de Payback).",
                )
            with col_c2:
                precio_venta_usd = st.number_input(
                    "Precio de venta al cliente (USD)",
                    min_value=0.0, value=0.0, step=100.0, format="%.2f",
                    key="fin_precio_venta",
                    help="Precio final cotizado al cliente, llave en mano (equipos + instalación) "
                         "-- este es el CAPEX real que se usa para Payback/ROI/NPV.",
                )
            with col_c3:
                mantenimiento_anual_usd = st.number_input(
                    "Mantenimiento anual (USD/año)",
                    min_value=0.0, value=0.0, step=50.0, format="%.2f",
                    key="fin_mantenimiento_anual",
                    help="Costo real esperado de mantenimiento al año -- reemplaza el % del "
                         "CAPEX que se adivinaba antes.",
                )

            if costo_equipos_usd > 0 and precio_venta_usd > 0:
                margen_usd = precio_venta_usd - costo_equipos_usd
                margen_pct = (margen_usd / costo_equipos_usd) * 100
                st.caption(f"Margen sobre costo de equipos: ${margen_usd:,.2f} ({margen_pct:.0f}%).")

            if precio_venta_usd <= 0:
                st.info(
                    "Ingresá el precio de venta al cliente para calcular Payback, ROI, NPV y "
                    "viabilidad económica."
                )
            elif modo_tarifa == "Tarifa horaria real de Costa Rica (ARESEP)" and resultado_tou is None:
                st.info(
                    "No se pudo calcular el ahorro con tarifa horaria (ver el error arriba) -- "
                    "cambiá a \"Tarifa plana (USD/kWh)\" o revisá la selección de proveedor/tarifa."
                )
            elif modo_tarifa == "Tarifa comercial de Costa Rica (T-CO)" and resultado_co is None:
                st.info(
                    "No se pudo calcular el ahorro con tarifa comercial (ver el error arriba) -- "
                    "cambiá a \"Tarifa plana (USD/kWh)\" o revisá la selección de proveedor/tramo."
                )
            else:
                if modo_tarifa == "Tarifa plana (USD/kWh)":
                    fe = FinancialEngineEolico(
                        tarifa_kwh_USD=tarifa_kwh_USD,
                        vida_util_anos=int(vida_util_anos),
                        tasa_descuento_pct=tasa_descuento_pct,
                    )
                    fin = fe.calcular_punto_capex_directo(
                        capex_usd=precio_venta_usd,
                        energia_anual_kWh=kwh_anual_total,
                        mantenimiento_anual_usd=mantenimiento_anual_usd,
                        potencia_pico_W=_potencia_pico_total_W,
                        n_turbinas=_cantidad_turbinas_total,
                        sistema_tipo=sistema_tipo,
                    )
                elif modo_tarifa == "Tarifa comercial de Costa Rica (T-CO)":
                    # Tarifa comercial T-CO (Hallazgo 55): precio plano por kWh, sin periodos
                    # horarios -- sólo el componente de energía (ver docstring de
                    # calcular_ahorro_tarifa_comercial_usd para qué NO incluye).
                    fe = FinancialEngineEolico(
                        tarifa_kwh_USD=resultado_co["precio_crc_kwh"] / resultado_co["tipo_cambio_crc_por_usd"],
                        vida_util_anos=int(vida_util_anos),
                        tasa_descuento_pct=tasa_descuento_pct,
                    )
                    fin = fe.calcular_ahorro_y_viabilidad(
                        capex_usd=precio_venta_usd,
                        ahorro_anual_usd=resultado_co["ahorro_anual_usd"],
                        mantenimiento_anual_usd=mantenimiento_anual_usd,
                        energia_anual_kWh=kwh_anual_total,
                        potencia_pico_W=_potencia_pico_total_W,
                        n_turbinas=_cantidad_turbinas_total,
                        sistema_tipo=sistema_tipo,
                    )
                else:
                    # Tarifa horaria real (Hallazgo 54): el ahorro ya viene calculado
                    # cruzando producción hora por hora contra los periodos Punta/Valle/
                    # Nocturno -- calcular_ahorro_y_viabilidad() lo recibe directo, sin
                    # volver a derivarlo de un $/kWh plano.
                    fe = FinancialEngineEolico(
                        tarifa_kwh_USD=resultado_tou["tarifa_efectiva_usd_kwh"] or 0.01,
                        vida_util_anos=int(vida_util_anos),
                        tasa_descuento_pct=tasa_descuento_pct,
                    )
                    fin = fe.calcular_ahorro_y_viabilidad(
                        capex_usd=precio_venta_usd,
                        ahorro_anual_usd=resultado_tou["ahorro_anual_usd"],
                        mantenimiento_anual_usd=mantenimiento_anual_usd,
                        energia_anual_kWh=kwh_anual_total,
                        potencia_pico_W=_potencia_pico_total_W,
                        n_turbinas=_cantidad_turbinas_total,
                        sistema_tipo=sistema_tipo,
                    )

                # Fila 1: qué genera el sistema en electricidad -- respuesta directa a
                # "esos kWh cuántos dólares representan" (ahorro de electricidad NO
                # comprada a la red, no el valor de venta del kWh al mercado).
                b1, b2, b3 = st.columns(3)
                b1.metric("Energía anual generada", f"{kwh_anual_total:,.0f} kWh/año")
                b2.metric("Ahorro anual (electricidad no comprada)",
                          f"${fin['ahorro_anual_USD']:,.0f}/año")
                b3.metric("Mantenimiento anual", f"${fin['mantenimiento_anual_USD']:,.0f}/año")

                st.markdown("**Retorno de la inversión**")
                c1, c2, c3, c4 = st.columns(4)
                c1.metric("CAPEX (precio de venta)", f"${fin['capex']:,.0f}")
                c2.metric("Payback",
                          f"{fin['payback_years']:.1f} años" if fin["payback_years"] is not None else "N/A")
                c3.metric("ROI (vida útil)",
                          f"{fin['roi_percentage']:.0f}%" if fin["roi_percentage"] is not None else "N/A")
                viabilidad_economica = (
                    "VIABLE" if fin["roi_percentage"] and fin["roi_percentage"] > 0 else "NO VIABLE"
                )
                c4.metric("Viabilidad", viabilidad_economica)

                if fin["npv_usd"] is not None:
                    st.caption(
                        f"NPV a {int(vida_util_anos)} años, tasa de descuento {tasa_descuento_pct:.1f}%: "
                        f"${fin['npv_usd']:,.0f}"
                    )

                if fin["opex_anual_neto"] <= 0:
                    # Nota (bug real encontrado con Playwright, Hallazgo 48): dos "$" en el mismo
                    # st.caption() arman un par que Streamlit interpreta como LaTeX ($...$) y
                    # rompe el texto -- se escapan con "\$" para que se muestren literales.
                    st.caption(
                        "El ahorro anual estimado en electricidad no alcanza a cubrir el "
                        f"mantenimiento anual ingresado (ahorro: \\${fin['ahorro_anual_USD']:,.0f}/año "
                        f"vs. mantenimiento: \\${fin['mantenimiento_anual_USD']:,.0f}/año) -- por eso "
                        "Payback/ROI/NPV muestran N/A."
                    )
                    st.info(
                        "Con el precio de venta y la tarifa eléctrica ingresados, este proyecto NO "
                        "recupera el mantenimiento sólo con ahorro de electricidad. Si el objetivo "
                        "del cliente es respaldo/resiliencia energética (no depender 100% de la red) "
                        "en vez de recuperar la inversión sólo con el ahorro eléctrico, ese es el "
                        "valor que hay que presentar -- este cálculo no lo cuantifica en dólares."
                    )

            st.caption(
                "CAPEX, mantenimiento y precio de venta ingresados directo por el usuario. "
                "Tarifas horarias reales de CNFL/ICE cruzadas contra la producción hora por "
                "hora, en vez de una tarifa plana adivinada."
            )


# --- Tab: Especificación Técnica (Hallazgo 49) -- datos generales + ficha de cada equipo,
# pensada para imprimir/exportar y llevar a una reunión con el cliente ---

with tab_especificacion:
    st.caption(
        "Datos generales del sistema y ficha técnica de fábrica de cada equipo que lo compone "
        "-- turbinas, inversor y banco de baterías. Usa las turbinas ya configuradas en "
        "\"Equipos y configuración\" y la producción ya calculada en \"Resultados\"."
    )

    if not st.session_state.get("calculo_listo"):
        st.info("Configurá el proyecto en la pestaña \"Equipos y configuración\" y presioná "
                 "Calcular producción del proyecto primero.")
    else:
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")

        if resultado_clima is None:
            st.error("Elegí primero una estación (o subí un EPW) en la pestaña \"Selección de clima\".")
        elif error:
            st.error(error)
        else:
            df_clima = resultado_clima["df_clima"]
            elevacion_m = resultado_clima["elevacion_m"]
            z0 = st.session_state.z0_avanzado
            metodo_bouquet = st.session_state.metodo_bouquet_radio

            kwh_anual_total = sum(
                simular(df_clima, altura_buje=c["altura_buje"], modelo=c["modelo"], N=int(c["N"]),
                        elevacion_m=elevacion_m, z0=z0, metodo_bouquet=metodo_bouquet)["kwh_anual"]
                for c in st.session_state.clusters
            )
            turbinas_seleccionadas = [
                c["modelo"] for c in st.session_state.clusters for _ in range(int(c["N"]))
            ]
            potencia_pico_W = sum(
                SPECS_TURBINAS[c["modelo"]]["potencia_nominal_w"] * int(c["N"])
                for c in st.session_state.clusters
            )

            # Va acumulando los mismos datos que se muestran en pantalla para poder
            # generar el PDF al final sin tener que volver a calcular nada (Hallazgo 49).
            _datos_pdf = {
                "sitio_nombre": st.session_state.get("sitio_nombre_activo") or "--",
                "potencia_pico_kw": potencia_pico_W / 1000,
                "energia_anual_kwh": kwh_anual_total,
                "elevacion_m": elevacion_m,
                "voltaje_bus_v": VOLTAJE_TURBINAS_V,
                "turbinas": [],
                "inversor": None,
                "inversor_no_compatible_msg": None,
                "bess": [],
            }

            st.markdown("### Datos generales del sistema")
            g1, g2, g3, g4 = st.columns(4)
            g1.metric("Sitio", st.session_state.get("sitio_nombre_activo") or "--")
            g2.metric("Potencia pico instalada", f"{potencia_pico_W / 1000:.2f} kW")
            g3.metric("Energía anual estimada", f"{kwh_anual_total:,.0f} kWh/año")
            g4.metric("Elevación del sitio", f"{elevacion_m:.0f} m")
            st.write(
                f"**Arquitectura eléctrica:** bus de corriente continua a {VOLTAJE_TURBINAS_V}V -- "
                "cada turbina entrega su salida a través de un controlador individual de fábrica; "
                "todos los controladores se conectan en paralelo al mismo bus, que alimenta "
                "directamente el puerto de batería del inversor (no el puerto solar/MPPT)."
            )

            st.divider()
            st.markdown("### Turbinas eólicas")
            _cantidad_por_modelo = {}
            for c in st.session_state.clusters:
                _cantidad_por_modelo[c["modelo"]] = _cantidad_por_modelo.get(c["modelo"], 0) + int(c["N"])

            for _clave, _cantidad in _cantidad_por_modelo.items():
                _specs = SPECS_TURBINAS[_clave]
                with st.container(border=True):
                    col_img, col_specs = st.columns([1, 3])
                    with col_img:
                        _ruta_img = RUTA_IMAGEN.get(_clave)
                        if _ruta_img and os.path.exists(_ruta_img):
                            st.image(_ruta_img, use_column_width=True)
                    with col_specs:
                        st.markdown(f"**{_specs['nombre']}** -- cantidad: {_cantidad}")
                        st.caption(f"Fabricante: Flower Turbines -- N° de parte: {_specs['numero_parte']}")
                        _costo = _specs.get("costo_usd")
                        _filas_turbina = [
                            ("Potencia nominal", f"{_specs['potencia_nominal_w']} W"),
                            ("Velocidad a potencia nominal", f"{_specs['viento_potencia_nominal_ms']} m/s"),
                            ("Velocidad de arranque (cut-in)", f"{_specs['velocidad_cutin_ms']} m/s"),
                            ("Velocidad de supervivencia", f"{_specs['velocidad_supervivencia_ms']} m/s"),
                            ("Tipo de rotor", _specs["tipo_rotor"]),
                            ("Tipo de generador", _specs["tipo_generador"]),
                            ("Diámetro del rotor", f"{_specs['diametro_rotor_m']} m"),
                            ("Altura de pala", f"{_specs['altura_pala_m']} m"),
                            ("Peso", f"{_specs['peso_total_kg']} kg"),
                            ("Vida de diseño", f"{_specs['vida_diseno_anos']} años"),
                            ("Cimentación requerida", _specs["cimentacion_requerida"]),
                            ("Costo de fábrica (unitario)",
                             f"${_costo:,.2f}" if _costo is not None else "No verificado todavía"),
                        ]
                        st.dataframe(
                            pd.DataFrame([{"Especificación": f, "Valor": v} for f, v in _filas_turbina]),
                            hide_index=True, use_container_width=True,
                        )
                        _datos_pdf["turbinas"].append({
                            "nombre": _specs["nombre"], "cantidad": _cantidad,
                            "numero_parte": _specs["numero_parte"], "filas": _filas_turbina,
                        })

            st.divider()
            st.markdown("### Inversor")
            _msg_inversor_fuera_alcance = (
                "Esta cotización cubre las turbinas Flower Turbines -- el inversor no se "
                "dimensiona ni se costea en esta sección."
            )
            st.info(_msg_inversor_fuera_alcance)
            _datos_pdf["inversor_no_compatible_msg"] = _msg_inversor_fuera_alcance

            st.divider()
            st.markdown("### Banco de baterías (BESS)")
            st.write("No aplica a esta cotización.")

            st.caption(
                "Fuente de los datos: fichas técnicas oficiales de fábrica de Flower Turbines."
            )

            st.divider()
            _pdf_bytes = generar_pdf_especificacion(_datos_pdf, logo_path=LOGO_ECO if os.path.exists(LOGO_ECO) else None)
            st.download_button(
                "Descargar ficha técnica en PDF",
                data=_pdf_bytes,
                file_name=f"ECO-Wind_especificacion_tecnica_{date.today().isoformat()}.pdf",
                mime="application/pdf",
                type="primary",
            )

