"""
ECO | Wind -- Simulador de microgeneración eólica.

Motor validado de Pista A (engine/simulador_pista_a.py +
engine/flower_turbines_curves.py), extendido con clima multi-sitio,
corrección de densidad de aire, multi-clúster, gráficos interactivos,
análisis financiero (CAPEX/OPEX/Payback/ROI/NPV), informe ejecutivo en PDF
y toggle de idioma ES/EN (engine/i18n.py) -- ver avance-de-proyecto.md
para el detalle de cada decisión de diseño.

ALCANCE:
- Un solo flujo de clima: buscás tu sitio por nombre, coordenada o clic en
  el mapa, la app muestra las estaciones climáticas REALES más cercanas
  (catálogo de climate.onebuilding.org, 5,276 estaciones, 20 países), y
  elegís una -- o subís directo tu propio archivo EPW como referencia. No
  hay sensibilización espacial de magnitud por ninguna fuente externa
  (GWA, NASA POWER, ERA5, Köppen); con datos limitados de verdad, un EPW
  real elegido a conciencia es más confiable que un ajuste automático
  sobre una fuente que demostró fallar en Costa Rica.
- Lo único que sí se sensibiliza, con una fuente propia: la velocidad del
  EPW (medida a 10m) se lleva a la altura real de buje de cada turbina con
  el perfil logarítmico de viento de ladybug-tools/ladybug
  (`engine/simulador_pista_a.py::wind_at_height()`). Terreno de referencia
  meteorológica fijo en "country" (aeropuerto/EPW, z0=0.1m); terreno del
  sitio destino seleccionable por el usuario (Equipos y configuración >
  Parámetros avanzados).
- Elevación: siempre del encabezado del EPW real elegido o subido -- nunca
  tecleada a mano.
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
from engine.precios_flower_turbines import (
    get_articulos_disponibles, get_precio_exworks_usd, capacidad_controlador_articulo_w,
)
from engine.dimensionador_sistema_eolico import VOLTAJE_TURBINAS_V
from engine.pdf_reporte import generar_pdf_informe_ejecutivo, generar_pdf_informe_eco_roof
from engine.eco_roof_catalog import ECO_ROOF_PRESETS, preset_disponible
from engine.eco_roof_curves import potencia_tabla_w
from engine.eco_roof_simulador import simular_eco_roof


@st.cache_data(show_spinner=False)
def _simular_eco_roof_cacheado(clave_preset, df_clima, ruta_epw, elevacion_m, z0):
    """Cachea la corrida de simular_eco_roof() por (preset, EPW, elevación, z0) --
    ahora incluye una simulación REAL de EnergyPlus (unos segundos, ver
    engine/eco_roof_solar.py), y Streamlit ejecuta el cuerpo de TODAS las pestañas en
    cada rerun (cualquier clic en cualquier pestaña) -- sin este cache la app se
    volvería inutilizable, recorriendo EnergyPlus en cada interacción."""
    return simular_eco_roof(clave_preset, df_clima, ruta_epw, elevacion_m, z0=z0)
from engine.i18n import t, tr, meses_abreviados, IDIOMA_DEFAULT, IDIOMAS_DISPONIBLES

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Idioma activo de la sesión -- se inicializa ACÁ (antes de set_page_config y de
# cualquier otro uso de t()) para que el título de la pestaña del navegador y
# todo el resto de la app ya lo respeten desde el primer render. El widget que
# lo cambia (toggle Español/English) se dibuja más abajo, en el sidebar.
if "idioma" not in st.session_state:
    st.session_state.idioma = IDIOMA_DEFAULT

# --- Paleta corporativa ECO -- colores EXACTOS de libro_de_marca_de_Eco_consultor.pdf
# (Hallazgo 49), reemplazando los valores aproximados que traía la app desde antes
# (AZUL era #003C52, el real es #173D4A; VERDE era #4A7C2F, el real es #66913E; GRIS
# era #4A5568, el real es #414549). Significado de cada color según el manual: azul =
# "conservación del ambiente", verde = "confort y ahorro energético", gris = "obra gris".
AZUL = "#173D4A"    # Pantone 309 C
VERDE = "#66913E"   # Pantone 575 C
GRIS = "#414549"    # Pantone 432 C
AMBAR = "#B7791F"   # mismo tono que engine/pdf_reporte.py -- energía perdida por recorte
FONDO = "#E8F0F3"

# --- Paleta de clima (10 colores para heatmaps y visualizaciones) ---
PALETA_CLIMA = ["#4b6ba9", "#5a7bc3", "#6b8dd4", "#7d9ee0", "#90aee8", "#a3beef", "#c9d8f0", "#f4e4a0", "#f5c455", "#ea2600"]

# Los nombres se resuelven por función (no dict fijo) porque dependen del
# idioma activo de la sesión -- NOMBRES_MODELO queda como función para no
# tener que cambiar cada `NOMBRES_MODELO[modelo]` por `NOMBRES_MODELO()[modelo]`
# en el resto del archivo; se llama igual, sigue siendo indexable.
def _nombres_modelo():
    return {
        "small_tulip": t("modelo_small_tulip"),
        "medium_tulip": t("modelo_medium_tulip"),
        "three_m_tulip": t("modelo_three_m_tulip"),
        "large_tulip": t("modelo_large_tulip"),
        "al13_2m": t("modelo_al13_2m"),
        "al13_4m": t("modelo_al13_4m"),
        "al13_6m": t("modelo_al13_6m"),
        "al13_8m": t("modelo_al13_8m"),
    }


class _NombresModelo:
    """Envoltorio indexable (NOMBRES_MODELO["small_tulip"]) que resuelve el
    nombre en el idioma activo en el momento de cada acceso, no una vez al
    importar el módulo -- así respeta el toggle de idioma en cada rerun."""
    def __getitem__(self, clave):
        return _nombres_modelo()[clave]

    def get(self, clave, default=None):
        return _nombres_modelo().get(clave, default)


NOMBRES_MODELO = _NombresModelo()


class _Meses:
    """Lista de meses abreviados que se resuelve en el idioma activo en cada
    acceso (indexado o iterado) -- mismo motivo que _NombresModelo."""
    def __getitem__(self, i):
        return meses_abreviados()[i]

    def __iter__(self):
        return iter(meses_abreviados())

    def __len__(self):
        return 12


MESES = _Meses()


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


st.set_page_config(page_title=t("app_titulo_pagina"), page_icon=LOGO_ECO, layout="wide")

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

def _resultado_desde_epw(df_clima, meta, ruta_epw, es_temporal=False):
    """Arma el dict unificado (mismo formato para las 2 rutas que terminan en un EPW
    real: estación de la lista -- precacheada o recién descargada -- y EPW subido por
    el usuario). Hallazgo 36: ya no existe una tercera ruta de "aproximación" -- toda
    esta app corre sobre EPW real, nunca sobre una fuente sensibilizada externamente.

    ruta_epw: ruta del archivo .epw real en disco que se acaba de cargar -- se guarda
    acá (no sólo df_clima/meta) porque el bloque solar del Eco-Roof
    (engine/eco_roof_solar.py) necesita el ARCHIVO real para correr EnergyPlus, no le
    alcanza con las columnas ya extraídas en df_clima.
    es_temporal: True sólo para el EPW subido por el usuario (tempfile.NamedTemporaryFile
    propio de esta sesión, seguro de borrar cuando se reemplaza) -- False para las
    estaciones precacheadas/descargadas, cuyo archivo puede seguir sirviendo a otras
    sesiones y nunca se borra desde acá."""
    hm_json = heatmap_json_desde_epw(df_clima)
    rosa_detallada = rosa_vientos_detallada_desde_epw(df_clima)
    return dict(df_clima=df_clima, media=float(df_clima["WS10M"].mean()), hm_json=hm_json,
                rosa_detallada=rosa_detallada, elevacion_m=meta["elevacion_m"], error=None, meta=meta,
                ruta_epw=ruta_epw, es_temporal=es_temporal)


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
        ruta = SITIOS_EPW_REAL[clave]["ruta_epw"]
        df_clima, meta = cargar_epw_real(ruta)
        return _resultado_desde_epw(df_clima, meta, ruta)
    try:
        ruta = descargar_y_extraer_epw(row["url"])
        df_clima, meta = cargar_epw_real(ruta)
        return _resultado_desde_epw(df_clima, meta, ruta)
    except Exception as e:
        return dict(error=t("clima_error_descarga_estacion", nombre=row["name"]))


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
        return dict(error=t("clima_error_epw_invalido", error=str(e)))
    return _resultado_desde_epw(df_clima, meta, ruta, es_temporal=True)


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
        hovertemplate=t("chart_duracion_hover")
    ))

    fig.update_layout(
        title=t("chart_duracion_titulo"),
        xaxis_title=t("chart_duracion_eje_x"),
        yaxis_title=t("chart_duracion_eje_y"),
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


def calcular_desglose_por_viento(v_hub, kwh_entregado_por_hora, kwh_perdido_por_hora, ancho_bin=1.0):
    """
    Agrupa la producción horaria del proyecto (post-recorte, más lo perdido por el tope
    de electrónica) en tramos de `ancho_bin` m/s de viento en el buje -- pedido de
    Flower Turbines (correo del proyecto Estadio Heredia): un desglose más granular que
    un solo promedio anual, porque P∝v³ hace que las horas de viento fuerte valgan
    desproporcionadamente más.

    v_hub, kwh_entregado_por_hora, kwh_perdido_por_hora: arreglos del mismo largo
    (8760 u 8784 horas). Devuelve un DataFrame con una fila por tramo que sí tuvo
    horas -- vacío si v_hub está vacío.
    """
    v_hub = np.asarray(v_hub, dtype=float)
    n_horas = len(v_hub)
    if n_horas == 0:
        return pd.DataFrame()

    v_max = float(v_hub.max())
    bordes = np.arange(0.0, v_max + ancho_bin, ancho_bin)
    if bordes[-1] <= v_max:
        bordes = np.append(bordes, bordes[-1] + ancho_bin)

    total_kwh = float(np.sum(kwh_entregado_por_hora))
    filas = []
    for i in range(len(bordes) - 1):
        mask = (v_hub >= bordes[i]) & (v_hub < bordes[i + 1])
        horas = int(mask.sum())
        if horas == 0:
            continue
        kwh_bin = float(np.sum(kwh_entregado_por_hora[mask]))
        filas.append({
            "bin_label": f"{bordes[i]:.0f}-{bordes[i+1]:.0f}",
            "bin_ini": bordes[i],
            "horas": horas,
            "pct_horas": horas / n_horas * 100,
            "kwh": kwh_bin,
            "pct_kwh": (kwh_bin / total_kwh * 100) if total_kwh > 0 else 0.0,
            "kwh_perdido": float(np.sum(kwh_perdido_por_hora[mask])),
        })
    return pd.DataFrame(filas)


def crear_desglose_viento_plotly(tabla_desglose, ancho_bin=1.0, capacidad_electronica_w=None):
    """Barras apiladas: energía entregada (post-recorte) + energía perdida por el tope
    de electrónica, una barra por tramo de velocidad de viento.

    capacidad_electronica_w: tope de potencia (W, por turbina) que causa el recorte --
    si se pasa, se anota en el gráfico para que quede claro DE DÓNDE sale la barra
    "perdido" (ej. controlador/inversor de 1000 W)."""
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=tabla_desglose["bin_label"], y=tabla_desglose["kwh"],
        name=t("resultados_viento_leyenda_entregado"),
        marker=dict(color=VERDE),
        hovertemplate=t("resultados_viento_hover_entregado"),
    ))
    fig.add_trace(go.Bar(
        x=tabla_desglose["bin_label"], y=tabla_desglose["kwh_perdido"],
        name=t("resultados_viento_leyenda_perdido"),
        marker=dict(color=AMBAR, opacity=0.6),
        hovertemplate=t("resultados_viento_hover_perdido"),
    ))
    fig.update_layout(
        barmode="stack",
        title=t("resultados_viento_titulo_chart", ancho=f"{ancho_bin:.0f}"),
        xaxis_title=t("resultados_viento_eje_x"),
        yaxis_title=t("resultados_viento_eje_y"),
        template="plotly_white",
        height=440,
        # b=110 (en vez de 60): dejar espacio para la leyenda, que se movió abajo del
        # eje X -- ver comentario en el legend= de más abajo.
        margin=dict(l=60, r=20, t=50, b=110),
        font=dict(family="sans-serif", size=11),
        # type="category" explícito: sin esto, Plotly detecta el eje X como fecha --
        # etiquetas como "6-7" o "10-11" calzan con su heurística de fecha corta
        # (día-mes) y el eje termina mostrando años en vez de tramos de viento.
        xaxis=dict(type="category", gridcolor="#E8E8E8"),
        yaxis=dict(gridcolor="#E8E8E8"),
        # Leyenda ABAJO (mismo patrón que crear_rosa_vientos_plotly): con y=1.02 (arriba)
        # se solapaba con el título -- ambos caen en la misma franja angosta sobre el
        # área del gráfico.
        legend=dict(orientation="h", yanchor="top", y=-0.32, x=0),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
    )
    if capacidad_electronica_w:
        fig.add_annotation(
            text=t("resultados_viento_anotacion_tope", cap=f"{capacidad_electronica_w:,.0f}"),
            xref="paper", yref="paper", x=0.99, y=0.97, xanchor="right", yanchor="top",
            showarrow=False, font=dict(size=11, color=AMBAR),
            bgcolor="rgba(255,255,255,0.8)", bordercolor=AMBAR, borderwidth=1, borderpad=4,
        )
    return fig


def crear_produccion_mensual_plotly(kwh_mensual_total):
    """Producción mensual interactiva con Plotly."""
    fig = go.Figure()

    fig.add_trace(go.Bar(
        # list(MESES), no MESES directo: MESES es una instancia de _Meses (se
        # resuelve al idioma activo en cada acceso, ver la clase arriba), no
        # una lista/tupla/ndarray real. Plotly valida el tipo de "x" en forma
        # estricta (isinstance) y no acepta un objeto solo "iterable" -- sin
        # este list(...), esto rompe con
        # "Invalid value of type '...._Meses' received for the 'x' property".
        x=list(MESES),
        y=kwh_mensual_total.values,
        marker=dict(color=VERDE),
        hovertemplate=t("chart_mensual_hover"),
        showlegend=False
    ))

    fig.update_layout(
        title=t("chart_mensual_titulo"),
        xaxis_title=t("chart_mensual_eje_x"),
        yaxis_title=t("chart_mensual_eje_y"),
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
    sectores = [t("chart_rosa_dir_n"), t("chart_rosa_dir_ne"), t("chart_rosa_dir_e"), t("chart_rosa_dir_se"),
                t("chart_rosa_dir_s"), t("chart_rosa_dir_so"), t("chart_rosa_dir_o"),
                t("chart_rosa_dir_no")][:rosa_detallada["n_sectores"]]
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
            hovertemplate=t("chart_rosa_hover", etiqueta=etiqueta),
        ))

    fig.update_layout(
        barmode='stack',
        title=t("chart_rosa_titulo", pct_calma=f"{pct_calma:.0f}"),
        polar=dict(
            radialaxis=dict(visible=True, gridcolor='#D8D8D8', ticksuffix='%'),
            angularaxis=dict(rotation=90, direction='clockwise', gridcolor='#D8D8D8'),
            bgcolor='rgba(0,0,0,0)',
        ),
        legend=dict(title=t("chart_rosa_leyenda_titulo"), orientation="h", yanchor="bottom", y=-0.25, x=0.1),
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
        return None, t("chart_heatmap_aviso_altura_baja", altura=f"{altura_m:.1f}", z0=z0)

    meses = meses_abreviados()
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
            texto[m, h] = t(
                "chart_heatmap_hover", mes=meses[m], hora=h,
                velocidad=f"{grid_ms[m, h]:.2f}", altura=f"{altura_m:.1f}",
                indice=f"{indice[m, h]:.2f}",
            )

    fig = go.Figure(data=go.Heatmap(
        z=grid_ms, x=list(range(24)), text=texto, hoverinfo='text',
        y=meses,
        colorscale='RdYlBu_r',
        colorbar=dict(title=t("chart_heatmap_colorbar"), thickness=15)
    ))
    fig.update_layout(
        title=t("chart_heatmap_titulo", altura=f"{altura_m:.1f}"),
        xaxis_title=t("chart_heatmap_eje_x"), yaxis_title=t("chart_heatmap_eje_y"),
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
        hovertemplate=t("chart_perfil_hover"),
        showlegend=False,
    ))
    if altura_marcada is not None:
        v_marcada = float(wind_at_height(velocidad_10m, 10, altura_marcada, z0=z0, z0_met=z0_met))
        fig.add_trace(go.Scatter(
            x=[v_marcada], y=[altura_marcada], mode='markers+text',
            marker=dict(color='#ea2600', size=10),
            text=[t("chart_perfil_texto_marcado", velocidad=f"{v_marcada:.2f}")],
            textposition='top center',
            hovertemplate=t("chart_perfil_hover_marcado",
                             altura=f"{altura_marcada:.2f}", velocidad=f"{v_marcada:.2f}"),
            showlegend=False,
        ))
    fig.update_layout(
        title=t("chart_perfil_titulo", z0=z0),
        xaxis_title=t("chart_perfil_eje_x"), yaxis_title=t("chart_perfil_eje_y"),
        height=380, template='plotly_white',
        font=dict(family="sans-serif", size=10),
        margin=dict(l=80, r=60, t=50, b=60),
        xaxis=dict(gridcolor='#E8E8E8'), yaxis=dict(gridcolor='#E8E8E8'),
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
    )
    return fig


def fig_a_png(fig, ancho_px=1000, alto_px=560, escala=2):
    """Exporta una figura Plotly a bytes PNG (vía kaleido) para embeberla en el PDF
    ejecutivo -- fondo blanco explícito (los gráficos en pantalla usan fondo
    transparente para calzar con el tema de Streamlit; en el PDF necesitan fondo
    sólido). Clona el layout antes de tocarlo para no alterar la figura que ya se
    mostró en pantalla con `st.plotly_chart`."""
    fig_export = go.Figure(fig)
    fig_export.update_layout(paper_bgcolor='white', plot_bgcolor='white')
    return fig_export.to_image(format="png", width=ancho_px, height=alto_px, scale=escala)


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
        popup=t("mapa_popup_sitio", lat=f"{lat_sitio:.4f}", lon=f"{lon_sitio:.4f}"),
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
                popup=t("mapa_popup_estacion", nombre=row["name"],
                        estado=row.get("state", t("mapa_no_disponible")),
                        distancia=f"{row['distancia_km']:.1f}"),
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
    # Toggle de idioma -- lo primero del sidebar, siempre visible sin importar
    # la pestaña activa, porque cambia el texto de TODA la app (sidebar, tabs,
    # gráficos, informe PDF). st.radio con key ligado a session_state.idioma
    # actualiza el idioma solo en el siguiente rerun al tocarlo.
    _opciones_idioma = list(IDIOMAS_DISPONIBLES.values())
    _claves_idioma = list(IDIOMAS_DISPONIBLES.keys())
    _idx_idioma_actual = _claves_idioma.index(st.session_state.idioma)
    _idioma_elegido = st.radio(
        t("sidebar_idioma_label"), _opciones_idioma, index=_idx_idioma_actual,
        horizontal=True, label_visibility="collapsed", key="_idioma_radio",
    )
    st.session_state.idioma = _claves_idioma[_opciones_idioma.index(_idioma_elegido)]

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
            <div class="eco-brand-sub">{t("sidebar_subtitulo_marca")}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f'<div class="eco-sidebar-section">{t("sidebar_elegido_hasta_ahora")}</div>', unsafe_allow_html=True)
    if st.session_state.get("sitio_activo"):
        st.success(f"{st.session_state.get('sitio_nombre_activo')}")
    else:
        st.caption(t("sidebar_sin_sitio"))
    _n_turbinas = sum(c["N"] for c in st.session_state.clusters)
    st.caption(t("sidebar_resumen_clusters", n_clusters=len(st.session_state.clusters), n_turbinas=_n_turbinas))
    if st.session_state.get("calculo_listo"):
        st.caption(t("sidebar_calculo_listo"))

    st.divider()
    # Una sola consulta al BCCR por sesión: obtener_tipo_cambio_bccr() ya
    # cachea a su propio nivel (archivo local), esto solo evita repetir la
    # llamada en cada rerun de Streamlit dentro de la misma sesión de usuario.
    if "tipo_cambio_bccr" not in st.session_state:
        st.session_state["tipo_cambio_bccr"] = obtener_tipo_cambio_bccr()
    _tipo_cambio, _tc_es_emergencia = st.session_state["tipo_cambio_bccr"]
    st.metric(t("sidebar_metric_tipo_cambio"), f"₡{_tipo_cambio:,.2f}")
    if _tc_es_emergencia:
        st.caption(t("sidebar_bccr_emergencia"))

    st.divider()
    st.markdown(f"""
    <div style="font-size:0.62rem; color:{GRIS}; line-height:1.6;">
        {t("sidebar_copyright", anio=date.today().year)}
    </div>
    """, unsafe_allow_html=True)


# --- Área principal: TABS en la parte superior (patrón Skyplus) ---
# Clona la estructura real de Skyplus: 4 tabs navegables en la parte superior,
# cada uno con su contenido y controles. El sidebar es limpio (solo marca + resumen).

(tab_clima, tab_contexto, tab_config, tab_resultados, tab_financiero, tab_especificacion,
 tab_eco_roof) = st.tabs([
    t("tabs_clima"),
    t("tabs_contexto"),
    t("tabs_config"),
    t("tabs_resultados"),
    t("tabs_financiero"),
    t("tabs_especificacion"),
    t("tabs_eco_roof"),
])

with tab_clima:
    st.caption(t("clima_caption_intro"))

    def _buscar_y_guardar(_lat, _lon):
        with st.spinner(t("clima_spinner_buscando")):
            st.session_state.sitio_lat, st.session_state.sitio_lon = _lat, _lon
            df = obtener_estaciones_cercanas(_lat, _lon)
            st.session_state.sitio_cercanas = df
            if df is None or df.empty:
                st.error(t("clima_error_sin_estaciones"))

    # Input minimalista: solo pegar coordenadas
    col1, col2 = st.columns([3, 1])
    with col1:
        _coords_input = st.text_input(
            t("clima_input_coordenadas_label"),
            placeholder=t("clima_input_coordenadas_placeholder"),
            key="coords_input"
        )
    with col2:
        st.write("")  # Espaciador
        if st.button(t("clima_boton_buscar")):
            if _coords_input:
                try:
                    partes = [p.strip() for p in _coords_input.split(",")]
                    if len(partes) != 2:
                        st.error(t("clima_error_formato_coordenadas"))
                    else:
                        _lat = float(partes[0])
                        _lon = float(partes[1])
                        _buscar_y_guardar(_lat, _lon)
                        st.rerun()
                except ValueError:
                    st.error(t("clima_error_coordenadas_invalidas"))

    # Mostrar sitio activo si existe
    if st.session_state.sitio_activo:
        st.success(t("clima_sitio_activo", nombre=st.session_state.sitio_nombre_activo))

    st.divider()

    # Mapa interactivo del sitio y estaciones
    if st.session_state.sitio_cercanas is not None and not st.session_state.sitio_cercanas.empty:
        st.subheader(t("clima_subheader_mapa"))
        mapa = crear_mapa_estaciones(st.session_state.sitio_lat, st.session_state.sitio_lon, st.session_state.sitio_cercanas)
        mapa_html = mapa._repr_html_()
        components.html(mapa_html, height=500, scrolling=False)

    st.divider()

    # Mostrar estaciones disponibles
    _df_cerc = st.session_state.sitio_cercanas
    if _df_cerc is not None and not _df_cerc.empty:
        st.caption(t("clima_caption_estaciones_cercanas"))
        for _i, _row in _df_cerc.iterrows():
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(t(
                    "clima_estacion_fila",
                    nombre=_row['name'],
                    estado=_row.get('state', ''),
                    distancia=f"{_row['distancia_km']:.0f}",
                ))
            with col2:
                if st.button(t("clima_boton_usar"), key=f"btn_est_{_i}"):
                    _res_est = cargar_estacion_elegida(_row)
                    if _res_est.get("error"):
                        st.error(_res_est["error"])
                    else:
                        st.session_state.sitio_activo = _res_est
                        st.session_state.sitio_nombre_activo = _row["name"]
                        st.rerun()

        _dist_min = float(_df_cerc["distancia_km"].min())
        if _dist_min > 40.0:
            st.caption(t("clima_caption_estacion_lejana", distancia=f"{_dist_min:.0f}"))

    st.divider()

    # EPW propio del usuario (Hallazgo 36) -- para un sitio sin estación real cercana, o para
    # usar a propósito el EPW de otro lugar como referencia. Reemplaza el mecanismo viejo de
    # "aproximación sensibilizada" (GWA/ERA5/NASA POWER, Hallazgo 21-30): esas fuentes se
    # descartaron por decisión de producto (Hallazgo 35) -- un EPW real elegido a conciencia es
    # más confiable que un ajuste automático sobre datos que ya demostraron fallar en Costa Rica.
    st.caption(t("clima_caption_epw_pregunta"))
    _epw_subido = st.file_uploader(t("clima_uploader_epw_label"), type=["epw"], key="epw_subido_uploader")
    if _epw_subido is not None:
        if st.button(t("clima_boton_usar_epw")):
            # Antes de escribir el nuevo archivo, borrar el EPW temporal de una subida
            # ANTERIOR (si la hubo) -- si no, cada "Usar este EPW" deja un .epw huérfano en
            # el disco del contenedor (nunca se borra solo, la sesión de Streamlit puede
            # vivir horas). Sólo se borra si es_temporal=True (nuestro propio tempfile) --
            # nunca el .epw de una estación precacheada/descargada, que no es nuestro.
            _sitio_previo = st.session_state.get("sitio_activo")
            if _sitio_previo and _sitio_previo.get("es_temporal") and _sitio_previo.get("ruta_epw"):
                try:
                    os.remove(_sitio_previo["ruta_epw"])
                except OSError:
                    pass
            with tempfile.NamedTemporaryFile(suffix=".epw", delete=False) as _tmp:
                _tmp.write(_epw_subido.getvalue())
                _ruta_tmp = _tmp.name
            # NO se borra _ruta_tmp acá (antes sí, apenas se leía df_clima) -- el bloque
            # solar del Eco-Roof (engine/eco_roof_solar.py) necesita el ARCHIVO real más
            # adelante en la sesión, para correr EnergyPlus, no le alcanza con df_clima.
            _res_subido = cargar_epw_subido(_ruta_tmp)
            if _res_subido.get("error"):
                st.error(_res_subido["error"])
                try:
                    os.remove(_ruta_tmp)
                except OSError:
                    pass
            else:
                st.session_state.sitio_activo = _res_subido
                st.session_state.sitio_nombre_activo = t("clima_epw_subido_nombre", nombre=_epw_subido.name)
                st.rerun()


# --- Tab: Contexto climático -- rosa de vientos + heatmap, sin depender de "Calcular" ---

with tab_contexto:
    resultado_clima = st.session_state.get("sitio_activo")
    error_clima = None if resultado_clima is None else resultado_clima.get("error")

    if resultado_clima is None:
        st.info(t("contexto_info_sin_sitio"))
    elif error_clima:
        st.error(error_clima)
    else:
        hm_json = resultado_clima["hm_json"]
        rosa_detallada = resultado_clima["rosa_detallada"]
        media_confirmada = resultado_clima["media"]

        if "meta" in resultado_clima:
            _meta = resultado_clima["meta"]
            st.success(t(
                "contexto_estacion_real",
                estacion=_meta["estacion"], pais=_meta["pais"], wmo=_meta["wmo"],
                lat=f"{_meta['lat']:.4f}", lon=f"{_meta['lon']:.4f}",
                elevacion_m=f"{_meta['elevacion_m']:.0f}", media=f"{media_confirmada:.2f}",
            ))

        st.divider()

        # Altura de buje a explorar (Hallazgo 39): un solo slider mueve tanto el heatmap
        # como el perfil de abajo, con la MISMA rugosidad de destino que se usa en el
        # cálculo real de energía (Equipos y configuración > Parámetros avanzados) --
        # si esa pestaña todavía no se visitó en esta sesión, cae al default de simular().
        z0_actual = st.session_state.get("z0_avanzado", Z0_DEFAULT)
        _altura_explorar = st.slider(
            t("contexto_slider_altura_label"), 0.5, 150.0, 10.0, 0.5, key="altura_explorar_slider",
            help=t("contexto_slider_altura_help"),
        )
        st.caption(t("contexto_caption_rugosidad", z0=z0_actual))

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
    st.subheader(t("equipos_subheader_clusters"))
    for i, c in enumerate(st.session_state.clusters):
        with st.container():
            cc1, cc2, cc3, cc4 = st.columns([2, 1, 1, 0.4])
            c["modelo"] = cc1.selectbox(
                t("equipos_label_modelo"), options=list(CURVE_COEFFICIENTS.keys()),
                format_func=lambda k: NOMBRES_MODELO.get(k, k),
                index=list(CURVE_COEFFICIENTS.keys()).index(c["modelo"]), key=f"modelo_{i}",
            )
            c["N"] = cc2.number_input(t("equipos_label_n"), min_value=1, max_value=20, value=c["N"], step=1, key=f"n_{i}")
            c["altura_buje"] = cc3.number_input(
                t("equipos_label_buje"), min_value=0.5, max_value=150.0,
                value=c["altura_buje"], step=0.5, key=f"h_{i}",
                help=t("equipos_help_buje"),
            )
            if cc4.button("✕", key=f"del_{i}", help=t("equipos_boton_quitar_cluster")) and len(st.session_state.clusters) > 1:
                st.session_state.clusters.pop(i)
                st.rerun()

            _articulos_disponibles = get_articulos_disponibles(c["modelo"])
            if _articulos_disponibles:
                _opciones_articulo = [art for art, _ in _articulos_disponibles]
                _articulo_guardado = c.get("articulo")
                _idx_articulo = (
                    _opciones_articulo.index(_articulo_guardado)
                    if _articulo_guardado in _opciones_articulo else 0
                )
                c["articulo"] = st.selectbox(
                    t("equipos_label_articulo"), options=_opciones_articulo,
                    index=_idx_articulo, key=f"articulo_{i}",
                    help=t("equipos_help_articulo"),
                )
                _precio_unitario = get_precio_exworks_usd(c["modelo"], c["articulo"])
                st.caption(t(
                    "equipos_caption_precio",
                    precio_unitario=f"{_precio_unitario:,.0f}", cantidad=int(c["N"]),
                    precio_total=f"{_precio_unitario * c['N']:,.0f}",
                ))
            else:
                c["articulo"] = None
                st.caption(t("equipos_caption_sin_precio"))

            _specs = SPECS_TURBINAS.get(c["modelo"])
            _ruta_img = RUTA_IMAGEN.get(c["modelo"])
            with st.expander(t("equipos_expander_ficha_tecnica",
                                nombre_modelo=NOMBRES_MODELO.get(c["modelo"], c["modelo"]))):
                if not _specs:
                    st.caption(t("equipos_caption_sin_ficha"))
                else:
                    col_img, col_specs = st.columns([1, 2])
                    with col_img:
                        if _ruta_img and os.path.exists(_ruta_img):
                            st.image(_ruta_img)
                        else:
                            st.caption(t("equipos_caption_sin_imagen"))
                    with col_specs:
                        st.caption(t("equipos_caption_numero_parte",
                                      numero_parte=_specs["numero_parte"], clase_iec=_specs["clase_iec"]))
                        st.markdown(t(
                            "equipos_ficha_markdown",
                            potencia_nominal_w=_specs["potencia_nominal_w"],
                            viento_potencia_nominal_ms=_specs["viento_potencia_nominal_ms"],
                            velocidad_cutin_ms=_specs["velocidad_cutin_ms"],
                            velocidad_supervivencia_ms=_specs["velocidad_supervivencia_ms"],
                            tipo_generador=t(_specs["tipo_generador"]), polos_generador=_specs["polos_generador"],
                            voltaje_salida=_specs["voltaje_salida"], altura_total_m=_specs["altura_total_m"],
                            diametro_rotor_m=_specs["diametro_rotor_m"], peso_total_kg=_specs["peso_total_kg"],
                            vida_diseno_anos=_specs["vida_diseno_anos"],
                            cimentacion_requerida=t(_specs["cimentacion_requerida"]),
                        ))

    if st.button(t("equipos_boton_agregar_cluster")):
        st.session_state.clusters.append({"modelo": "medium_tulip", "N": 1, "altura_buje": 3.0})
        st.rerun()

    st.divider()

    with st.expander(t("equipos_expander_avanzados")):
        z0 = st.selectbox(
            t("equipos_label_z0"), options=[0.03, 0.1, 0.3, 1.0],
            format_func=lambda z: f"{z} — " + {
                0.03: t("equipos_z0_campo_abierto"), 0.1: t("equipos_z0_cultivos_bajos"),
                0.3: t("equipos_z0_suburbano"), 1.0: t("equipos_z0_urbano_denso"),
            }[z],
            index=2, key="z0_avanzado",
            help=t("equipos_help_z0"),
        )
        metodo_bouquet = st.radio(
            t("equipos_label_metodo_bouquet"), options=["real", "lineal"], key="metodo_bouquet_radio",
            format_func=lambda m: t("equipos_metodo_real") if m == "real" else t("equipos_metodo_lineal"),
        )

    st.divider()

    if not st.session_state.get("sitio_activo"):
        st.warning(t("equipos_warning_sin_sitio"))

    if st.button(t("equipos_boton_calcular"), type="primary"):
        st.session_state.calculo_listo = True
        st.session_state.seccion_activa = "resultados"
        st.rerun()


# --- Tab: Resultados -- por ahora, producción de energía (Hallazgo 12/17) ---

with tab_resultados:
    st.caption(t("resultados_caption_intro"))

    # Se resetea acá y sólo se sobreescribe en el camino exitoso de abajo -- así el
    # informe ejecutivo (pestaña "Especificación Técnica") nunca arrastra un resultado
    # de una configuración anterior si algo en el medio dejó de ser válido.
    st.session_state["ultimo_resultado_produccion"] = None

    if st.session_state.get("calculo_listo"):
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")
        z0 = st.session_state.z0_avanzado
        metodo_bouquet = st.session_state.metodo_bouquet_radio

        if resultado_clima is None:
            st.error(t("resultados_error_sin_estacion"))
        elif error:
            st.error(error)
        else:
            df_clima = resultado_clima["df_clima"]
            elevacion_m = resultado_clima["elevacion_m"]

            resultados = []
            serie_total_w = None
            serie_perdido_total_kwh = None
            for c in st.session_state.clusters:
                # Recorte por electrónica (correo Estadio Heredia, Flower Turbines):
                # sin este tope, kWh/año asume que TODA la energía aerodinámica se
                # aprovecha, sin importar qué controlador/inversor se compró -- eso
                # sobreestima la producción real en sitios de viento fuerte. Si el
                # clúster todavía no tiene artículo elegido (pestaña Equipos y
                # configuración), cae al valor de fábrica del modelo -- nunca al
                # recorte más grande, para no estimar de más.
                _capacidad_w = (capacidad_controlador_articulo_w(c.get("articulo"))
                                or SPECS_TURBINAS[c["modelo"]]["potencia_nominal_w"])
                r = simular(df_clima, altura_buje=c["altura_buje"], modelo=c["modelo"], N=int(c["N"]),
                            elevacion_m=elevacion_m, z0=z0, metodo_bouquet=metodo_bouquet,
                            capacidad_electronica_w=_capacidad_w)
                resultados.append({**c, **r})
                serie_cluster_w = r["serie_horaria_W_por_turbina"] * c["N"]
                serie_total_w = serie_cluster_w if serie_total_w is None else serie_total_w + serie_cluster_w
                serie_cluster_kwh_perdido = r["serie_horaria_kwh_perdido_por_turbina"] * c["N"]
                serie_perdido_total_kwh = (serie_cluster_kwh_perdido if serie_perdido_total_kwh is None
                                            else serie_perdido_total_kwh + serie_cluster_kwh_perdido)

            kwh_total = sum(r["kwh_anual"] for r in resultados)
            n_total = sum(c["N"] for c in st.session_state.clusters)

            c1, c2, c3, c4 = st.columns(4)
            c1.metric(t("resultados_metric_produccion_anual"), f"{kwh_total:,.0f} kWh")
            c2.metric(t("resultados_metric_turbinas_totales"), f"{n_total}")
            c3.metric(t("resultados_metric_correccion_densidad"), t(
                "resultados_metric_correccion_densidad_valor",
                pct=f"{(1 - resultados[0]['factor_correccion_densidad']) * 100:.1f}",
            ))
            c4.metric(t("resultados_metric_altura_buje"), f"{resultados[0]['altura_buje']:.0f} m")

            st.markdown(t("resultados_subheader_detalle_cluster"))
            tabla = pd.DataFrame([{
                t("resultados_col_modelo"): NOMBRES_MODELO.get(r["modelo"], r["modelo"]),
                t("resultados_col_n"): r["N"],
                t("resultados_col_buje"): r["altura_buje"],
                t("resultados_col_kwh_anio"): round(r["kwh_anual"]),
                t("resultados_col_v_media_buje"): round(r["v_hub_medio"], 2),
                t("resultados_col_pct_bajo_cutin"): round(r["pct_horas_bajo_cutin"], 1),
                t("resultados_col_pct_recorte"): round(r["pct_horas_con_recorte"], 1),
                t("resultados_col_kwh_perdidos_recorte"): round(r["energia_perdida_por_recorte_kwh"]),
            } for r in resultados])
            st.dataframe(tabla, hide_index=True)
            if any(r["energia_perdida_por_recorte_kwh"] > 0 for r in resultados):
                st.caption(t("resultados_caption_recorte"))

            media_confirmada = resultado_clima["media"]
            with st.expander(t("resultados_expander_perfil_viento")):
                _r0 = resultados[0]
                # El cross-check usa el MISMO z0 de destino que ya eligió el usuario arriba
                # (mapeado a la clase de TERRENOS_ENERGYPLUS más cercana) -- antes quedaba fijo
                # en "suburban" sin importar el z0 real seleccionado (Hallazgo 52: nada
                # hardcodeado, el tipo de terreno lo elige el usuario).
                _terreno_dst = terreno_mas_cercano_por_z0(z0)
                _v_pot = wind_at_height_potencia(
                    media_confirmada, 10, _r0["altura_buje"], terreno=_terreno_dst, terreno_met="country")
                st.write(t("resultados_perfil_texto1"))
                st.write(t(
                    "resultados_perfil_texto2", z0=z0, terreno_dst=_terreno_dst, v_pot=f"{_v_pot:.2f}",
                    altura_buje=f"{_r0['altura_buje']:.1f}", v_hub_medio=f"{_r0['v_hub_medio']:.2f}",
                    conclusion=t("resultados_perfil_concuerdan") if abs(_v_pot / _r0['v_hub_medio'] - 1) < 0.15
                    else t("resultados_perfil_difieren"),
                ))

            with st.expander(t("resultados_expander_horario_vs_media")):
                cmp = comparar_metodo_ingenuo_vs_horario(
                    df_clima, altura_buje=resultados[0]["altura_buje"], modelo=resultados[0]["modelo"],
                    N=int(resultados[0]["N"]), elevacion_m=elevacion_m, z0=z0, metodo_bouquet=metodo_bouquet)
                st.write(t(
                    "resultados_jensen_texto",
                    kwh_correcto=f"{cmp['kwh_anual_correcto']:.0f}", v_media=f"{cmp['v_media']:.2f}",
                    kwh_ingenuo=f"{cmp['kwh_anual_ingenuo']:.0f}",
                    razon=f"{cmp['razon_correcto_sobre_ingenuo']:.2f}",
                ))

            st.divider()
            kwh_mensual_total = pd.concat([r["kwh_mensual"] for r in resultados], axis=1).sum(axis=1)
            st.plotly_chart(crear_produccion_mensual_plotly(kwh_mensual_total), use_container_width=True)
            st.plotly_chart(crear_curva_duracion_plotly(serie_total_w), use_container_width=True)

            st.markdown(t("resultados_subheader_viento"))
            st.caption(t("resultados_caption_viento"))
            tabla_desglose_viento = calcular_desglose_por_viento(
                resultados[0]["v_hub"], (serie_total_w / 1000.0).values,
                serie_perdido_total_kwh.values, ancho_bin=1.0)
            if not tabla_desglose_viento.empty:
                st.plotly_chart(
                    crear_desglose_viento_plotly(
                        tabla_desglose_viento, ancho_bin=1.0,
                        capacidad_electronica_w=resultados[0]["capacidad_electronica_w"]),
                    use_container_width=True)
                with st.expander(t("resultados_viento_expander_tabla")):
                    tabla_viento_mostrar = pd.DataFrame({
                        t("resultados_viento_col_bin"): tabla_desglose_viento["bin_label"],
                        t("resultados_viento_col_horas"): tabla_desglose_viento["horas"],
                        t("resultados_viento_col_pct_horas"): tabla_desglose_viento["pct_horas"].round(1),
                        t("resultados_viento_col_kwh"): tabla_desglose_viento["kwh"].round(0),
                        t("resultados_viento_col_pct_kwh"): tabla_desglose_viento["pct_kwh"].round(1),
                        t("resultados_viento_col_perdido"): tabla_desglose_viento["kwh_perdido"].round(0),
                    })
                    st.dataframe(tabla_viento_mostrar, hide_index=True)

            st.caption(t("resultados_caption_validado"))

            # Mismos datos que se acaban de calcular y mostrar arriba, disponibles para
            # el informe ejecutivo en "Especificación Técnica" sin volver a simular nada.
            st.session_state["ultimo_resultado_produccion"] = {
                "resultados": resultados, "serie_total_w": serie_total_w,
                "kwh_total": kwh_total, "n_total": n_total,
                "kwh_mensual_total": kwh_mensual_total,
                "correccion_densidad_pct": (1 - resultados[0]["factor_correccion_densidad"]) * 100,
                "tabla_desglose_viento": tabla_desglose_viento,
            }
    else:
        st.info(t("resultados_info_sin_calculo"))


# --- Tab: Análisis Financiero (Hallazgo 40-48) -- CAPEX, inversor/BESS recomendados, payback/ROI/NPV ---

with tab_financiero:
    st.caption(t("financiero_caption_intro"))

    # Igual que en "Resultados": se resetea acá y sólo se sobreescribe si el cálculo
    # financiero termina en un resultado válido, para que el informe ejecutivo nunca
    # muestre un CAPEX/Payback de una configuración vieja.
    st.session_state["ultimo_resultado_financiero"] = None

    modulo_financiero_activo = st.toggle(
        t("financiero_toggle_label"),
        value=True,
        key="fin_modulo_activo",
        help=t("financiero_toggle_help"),
    )

    if not modulo_financiero_activo:
        st.info(t("financiero_info_desactivado"))
    elif not st.session_state.get("calculo_listo"):
        st.info(t("financiero_info_sin_calculo"))
    else:
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")

        if resultado_clima is None:
            st.error(t("resultados_error_sin_estacion"))
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
            # Mismo recorte por electrónica que en "Resultados" (correo Estadio
            # Heredia, Flower Turbines) -- si acá diera un kWh/año distinto al de esa
            # pestaña por no aplicar el mismo tope, Payback/ROI/NPV terminarían
            # calculados contra una energía que la pestaña Resultados ya no muestra.
            resultados_clusters = [
                simular(df_clima, altura_buje=c["altura_buje"], modelo=c["modelo"], N=int(c["N"]),
                        elevacion_m=elevacion_m, z0=z0, metodo_bouquet=metodo_bouquet,
                        capacidad_electronica_w=(capacidad_controlador_articulo_w(c.get("articulo"))
                                                  or SPECS_TURBINAS[c["modelo"]]["potencia_nominal_w"]))
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

            st.markdown(t("financiero_subheader_tarifa"))
            _opciones_modo_tarifa = ["Tarifa plana (USD/kWh)", "Tarifa horaria real de Costa Rica (ARESEP)",
                                      "Tarifa comercial de Costa Rica (T-CO)"]
            _modo_tarifa_t = {
                "Tarifa plana (USD/kWh)": t("financiero_tarifa_plana"),
                "Tarifa horaria real de Costa Rica (ARESEP)": t("financiero_tarifa_aresep"),
                "Tarifa comercial de Costa Rica (T-CO)": t("financiero_tarifa_tco"),
            }
            modo_tarifa = st.radio(
                t("financiero_label_modo_tarifa"), _opciones_modo_tarifa,
                format_func=lambda o: _modo_tarifa_t[o],
                horizontal=True,
                key="fin_modo_tarifa",
                help=t("financiero_help_modo_tarifa"),
            )

            resultado_tou = None
            resultado_co = None
            if modo_tarifa == "Tarifa plana (USD/kWh)":
                tarifa_kwh_USD = st.number_input(
                    t("financiero_label_tarifa_plana_valor"), min_value=0.01, value=0.15, step=0.01,
                    format="%.2f", key="fin_tarifa_kwh")
            elif modo_tarifa == "Tarifa comercial de Costa Rica (T-CO)":
                col_c1, col_c2, col_c3 = st.columns(3)
                with col_c1:
                    proveedor_co = st.selectbox(
                        t("financiero_label_proveedor"), ["CNFL", "ICE"], key="fin_co_proveedor",
                        help=t("financiero_help_proveedor"),
                    )
                with col_c2:
                    _opciones_tramo = ["≤ 3000 kWh/mes (sin medidor de potencia)",
                                        "> 3000 kWh/mes (con medidor de potencia)"]
                    _tramo_t = {
                        _opciones_tramo[0]: t("financiero_tramo_pequeno"),
                        _opciones_tramo[1]: t("financiero_tramo_grande"),
                    }
                    tramo_label = st.selectbox(
                        t("financiero_label_tramo"), _opciones_tramo,
                        format_func=lambda o: _tramo_t[o],
                        key="fin_co_tramo",
                        help=t("financiero_help_tramo"),
                    )
                tramo_co = "pequeno" if tramo_label.startswith("≤") else "grande"
                with col_c3:
                    tipo_cambio_crc_usd = st.number_input(
                        t("financiero_label_tipo_cambio"), min_value=1.0, value=_tipo_cambio, step=1.0,
                        key="fin_co_tipo_cambio",
                        help=t("financiero_help_tipo_cambio"),
                    )

                try:
                    resultado_co = calcular_ahorro_tarifa_comercial_usd(
                        kwh_anual_total, proveedor_co, tramo_co, tipo_cambio_crc_usd,
                    )
                except ValueError as e:
                    st.error(str(e))

                if resultado_co:
                    st.caption(t(
                        "financiero_caption_tco",
                        precio_crc_kwh=f"{resultado_co['precio_crc_kwh']:.2f}",
                        ahorro_usd=f"{resultado_co['ahorro_anual_usd']:,.0f}",
                        ahorro_crc=f"{resultado_co['ahorro_anual_crc']:,.0f}",
                    ))
                    st.info(t("financiero_info_tco_sin_demanda"))
            else:
                col_t1, col_t2, col_t3 = st.columns(3)
                with col_t1:
                    proveedor_tou = st.selectbox(
                        t("financiero_label_proveedor"), ["CNFL", "ICE"], key="fin_tou_proveedor",
                        help=t("financiero_help_proveedor"),
                    )
                opciones_tarifa_tou = {
                    "CNFL": ["T-REH (0-500 kWh)", "T-REH (>500 kWh)"],
                    "ICE": ["T-RH", "T-MT (Media Tensión Max)"],
                }[proveedor_tou]
                with col_t2:
                    tarifa_tou = st.selectbox(
                        t("financiero_label_tarifa_tou"), opciones_tarifa_tou, key="fin_tou_tarifa",
                        help=t("financiero_help_tarifa_tou"),
                    )
                with col_t3:
                    tipo_cambio_crc_usd = st.number_input(
                        t("financiero_label_tipo_cambio"), min_value=1.0, value=_tipo_cambio, step=1.0,
                        key="fin_tipo_cambio",
                        help=t("financiero_help_tipo_cambio"),
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
                    st.caption(t(
                        "financiero_caption_tou",
                        tarifa_efectiva=f"{resultado_tou['tarifa_efectiva_usd_kwh']:.4f}",
                        ahorro_crc=f"{resultado_tou['ahorro_anual_crc']:,.0f}",
                        ahorro_usd=f"{resultado_tou['ahorro_anual_usd']:,.0f}",
                    ))
                    _col_periodo, _col_kwh, _col_precio, _col_valor = (
                        t("financiero_col_periodo"), t("financiero_col_kwh_anio"),
                        t("financiero_col_precio_crc_kwh"), t("financiero_col_valor_usd_anio"),
                    )
                    tabla_periodos = pd.DataFrame([
                        {_col_periodo: periodo, _col_kwh: v["kwh"],
                         _col_precio: v["precio_crc_kwh"], _col_valor: v["usd"]}
                        for periodo, v in resultado_tou["desglose_por_periodo"].items()
                    ])
                    st.dataframe(
                        tabla_periodos.style.format({
                            _col_kwh: "{:,.0f}", _col_precio: "{:,.2f}", _col_valor: "${:,.0f}",
                        }),
                        hide_index=True,
                    )

            with st.expander(t("equipos_expander_avanzados")):
                col_a1, col_a2 = st.columns(2)
                with col_a1:
                    vida_util_anos = st.number_input(
                        t("financiero_label_vida_util"), min_value=1, value=40, step=1)
                with col_a2:
                    tasa_descuento_pct = st.number_input(
                        t("financiero_label_tasa_descuento"), min_value=0.0, value=8.0, step=0.5)

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
            st.markdown(t("financiero_subheader_equipo_elegido"))
            st.caption(t("financiero_caption_equipo_elegido"))
            _precio_total_proyecto = 0.0
            _algun_modelo_sin_precio = False
            for _c in st.session_state.clusters:
                _nombre_modelo = NOMBRES_MODELO.get(_c["modelo"], _c["modelo"])
                _articulo = _c.get("articulo")
                if not _articulo:
                    st.caption(t("financiero_caption_cluster_sin_precio", nombre_modelo=_nombre_modelo))
                    _algun_modelo_sin_precio = True
                    continue
                _precio_unitario = get_precio_exworks_usd(_c["modelo"], _articulo)
                _precio_total_proyecto += _precio_unitario * _c["N"]
                # Dos "$" en el mismo st.caption() arman un par que Streamlit interpreta
                # como LaTeX ($...$) -- se escapan con "\$" (mismo bug real de Hallazgo 48).
                st.caption(t(
                    "financiero_caption_cluster_precio",
                    nombre_modelo=_nombre_modelo, articulo=_articulo,
                    precio_unitario=f"{_precio_unitario:,.0f}", cantidad=int(_c["N"]),
                    precio_total=f"{_precio_unitario * _c['N']:,.0f}",
                ))
            st.metric(t("financiero_metric_precio_total"), f"${_precio_total_proyecto:,.0f}")
            st.caption(
                t("financiero_caption_precio_nota")
                + (t("financiero_caption_falta_articulo") if _algun_modelo_sin_precio else "")
            )

            st.divider()
            st.markdown(t("financiero_subheader_costeo_real"))
            st.caption(t("financiero_caption_costeo_real"))
            col_c1, col_c2, col_c3 = st.columns(3)
            with col_c1:
                costo_equipos_usd = st.number_input(
                    t("financiero_label_costo_equipos"),
                    min_value=0.0, value=0.0, step=100.0, format="%.2f",
                    key="fin_costo_equipos",
                    help=t("financiero_help_costo_equipos"),
                )
            with col_c2:
                precio_venta_usd = st.number_input(
                    t("financiero_label_precio_venta"),
                    min_value=0.0, value=0.0, step=100.0, format="%.2f",
                    key="fin_precio_venta",
                    help=t("financiero_help_precio_venta"),
                )
            with col_c3:
                mantenimiento_anual_usd = st.number_input(
                    t("financiero_label_mantenimiento"),
                    min_value=0.0, value=0.0, step=50.0, format="%.2f",
                    key="fin_mantenimiento_anual",
                    help=t("financiero_help_mantenimiento"),
                )

            if costo_equipos_usd > 0 and precio_venta_usd > 0:
                margen_usd = precio_venta_usd - costo_equipos_usd
                margen_pct = (margen_usd / costo_equipos_usd) * 100
                st.caption(t("financiero_caption_margen", margen_usd=f"{margen_usd:,.2f}", margen_pct=f"{margen_pct:.0f}"))

            if precio_venta_usd <= 0:
                st.info(t("financiero_info_falta_precio_venta"))
            elif modo_tarifa == "Tarifa horaria real de Costa Rica (ARESEP)" and resultado_tou is None:
                st.info(t("financiero_info_error_tarifa_horaria"))
            elif modo_tarifa == "Tarifa comercial de Costa Rica (T-CO)" and resultado_co is None:
                st.info(t("financiero_info_error_tarifa_comercial"))
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
                b1.metric(t("financiero_metric_energia_generada"),
                          f"{kwh_anual_total:,.0f} {t('financiero_col_kwh_anio')}")
                b2.metric(t("financiero_metric_ahorro_anual"),
                          f"${fin['ahorro_anual_USD']:,.0f}{t('unidad_por_anio')}")
                b3.metric(t("financiero_metric_mantenimiento_anual"),
                          f"${fin['mantenimiento_anual_USD']:,.0f}{t('unidad_por_anio')}")

                st.markdown(t("financiero_subheader_retorno"))
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(t("financiero_metric_capex"), f"${fin['capex']:,.0f}")
                c2.metric(t("financiero_metric_payback"),
                          t("financiero_valor_anos", val=f"{fin['payback_years']:.1f}")
                          if fin["payback_years"] is not None else t("financiero_na"))
                c3.metric(t("financiero_metric_roi"),
                          f"{fin['roi_percentage']:.0f}%" if fin["roi_percentage"] is not None else t("financiero_na"))
                # viabilidad_economica queda en español fijo -- es el valor interno que se
                # guarda en session_state y compara pdf_reporte.py (fin["viable"]), no un
                # texto para mostrar; la traducción va aparte, solo en el metric de abajo.
                viabilidad_economica = (
                    "VIABLE" if fin["roi_percentage"] and fin["roi_percentage"] > 0 else "NO VIABLE"
                )
                c4.metric(t("financiero_metric_viabilidad"),
                          t("financiero_viable") if viabilidad_economica == "VIABLE" else t("financiero_no_viable"))

                # Mismo resultado que se acaba de mostrar arriba, disponible para el
                # informe ejecutivo en "Especificación Técnica" sin recalcular nada.
                st.session_state["ultimo_resultado_financiero"] = {
                    "capex": fin["capex"], "payback_years": fin["payback_years"],
                    "roi_percentage": fin["roi_percentage"], "npv_usd": fin["npv_usd"],
                    "ahorro_anual_USD": fin["ahorro_anual_USD"],
                    "mantenimiento_anual_USD": fin["mantenimiento_anual_USD"],
                    "viable": viabilidad_economica == "VIABLE",
                    "modo_tarifa": modo_tarifa, "vida_util_anos": int(vida_util_anos),
                    "tasa_descuento_pct": tasa_descuento_pct,
                }

                if fin["npv_usd"] is not None:
                    st.caption(t(
                        "financiero_caption_npv", anos=int(vida_util_anos),
                        tasa=f"{tasa_descuento_pct:.1f}", valor=f"{fin['npv_usd']:,.0f}",
                    ))

                if fin["opex_anual_neto"] <= 0:
                    # Nota (bug real encontrado con Playwright, Hallazgo 48): dos "$" en el mismo
                    # st.caption() arman un par que Streamlit interpreta como LaTeX ($...$) y
                    # rompe el texto -- se escapan con "\$" para que se muestren literales.
                    st.caption(t(
                        "financiero_caption_no_cubre_mantenimiento",
                        ahorro=f"{fin['ahorro_anual_USD']:,.0f}",
                        mantenimiento=f"{fin['mantenimiento_anual_USD']:,.0f}",
                    ))
                    st.info(t("financiero_info_no_recupera_mantenimiento"))

            st.caption(t("financiero_caption_footer"))


# --- Tab: Especificación Técnica (Hallazgo 49) -- datos generales + ficha de cada equipo,
# pensada para imprimir/exportar y llevar a una reunión con el cliente ---

with tab_especificacion:
    st.caption(t("especificacion_caption_intro"))

    if not st.session_state.get("calculo_listo"):
        st.info(t("especificacion_info_sin_calculo"))
    else:
        resultado_clima = st.session_state.sitio_activo
        error = None if resultado_clima is None else resultado_clima.get("error")

        if resultado_clima is None:
            st.error(t("resultados_error_sin_estacion"))
        elif error:
            st.error(error)
        elif not st.session_state.get("ultimo_resultado_produccion"):
            # Misma condición de arriba (calculo_listo + sitio válido) ya corrió en
            # "Resultados" en este mismo rerun -- si igual no hay nada guardado, algo
            # puntual falló ahí (revisar esa pestaña) en vez de repetir el cálculo acá.
            st.error(t("especificacion_error_sin_resultado"))
        else:
            _prod = st.session_state["ultimo_resultado_produccion"]
            elevacion_m = resultado_clima["elevacion_m"]
            kwh_anual_total = _prod["kwh_total"]
            turbinas_seleccionadas = [
                c["modelo"] for c in st.session_state.clusters for _ in range(int(c["N"]))
            ]
            # Potencia del GENERADOR (ficha de fábrica) -- no cambia según qué
            # controlador/inversor se haya elegido para el clúster (ver docstring de
            # capacidad_controlador_articulo_w: son dos componentes eléctricos
            # distintos, se corrigió acá una confusión real entre ambos).
            potencia_pico_W = sum(
                SPECS_TURBINAS[c["modelo"]]["potencia_nominal_w"] * int(c["N"])
                for c in st.session_state.clusters
            )

            # Va acumulando los mismos datos que se muestran en pantalla (más los gráficos,
            # exportados a PNG) para armar el informe ejecutivo completo al final.
            _datos_pdf = {
                "sitio_nombre": st.session_state.get("sitio_nombre_activo") or "--",
                "potencia_pico_kw": potencia_pico_W / 1000,
                "energia_anual_kwh": kwh_anual_total,
                "elevacion_m": elevacion_m,
                "n_turbinas_total": len(turbinas_seleccionadas),
                "voltaje_bus_v": VOLTAJE_TURBINAS_V,
                "turbinas": [],
            }

            st.markdown(t("especificacion_subheader_datos_generales"))
            g1, g2, g3, g4 = st.columns(4)
            g1.metric(t("especificacion_metric_sitio"), st.session_state.get("sitio_nombre_activo") or "--")
            g2.metric(t("especificacion_metric_potencia_pico"), f"{potencia_pico_W / 1000:.2f} kW")
            g3.metric(t("especificacion_metric_energia_anual"),
                      f"{kwh_anual_total:,.0f} {t('financiero_col_kwh_anio')}")
            g4.metric(t("especificacion_metric_elevacion"), f"{elevacion_m:.0f} m")
            st.write(t("especificacion_texto_arquitectura", voltaje=VOLTAJE_TURBINAS_V))

            st.divider()
            st.markdown(t("especificacion_subheader_turbinas"))
            # Se agrupa por (modelo, artículo) -- no solo por modelo -- para que dos
            # clústers del mismo modelo con distinto controlador/inversor elegido (ej.
            # "...1 kilowatt" vs. "...3 kilowatts") aparezcan como filas separadas, cada
            # una con su propia potencia nominal real, en vez de mezclarse en una sola
            # fila con la ficha genérica del modelo.
            _cantidad_por_config = {}
            for c in st.session_state.clusters:
                _clave_config = (c["modelo"], c.get("articulo"))
                _cantidad_por_config[_clave_config] = _cantidad_por_config.get(_clave_config, 0) + int(c["N"])

            for (_clave, _articulo), _cantidad in _cantidad_por_config.items():
                _specs = SPECS_TURBINAS[_clave]
                _capacidad_controlador_w = capacidad_controlador_articulo_w(_articulo)
                with st.container(border=True):
                    col_img, col_specs = st.columns([1, 3])
                    with col_img:
                        _ruta_img = RUTA_IMAGEN.get(_clave)
                        if _ruta_img and os.path.exists(_ruta_img):
                            st.image(_ruta_img, use_column_width=True)
                    with col_specs:
                        _titulo = f"**{_specs['nombre']}**" + (f" -- {_articulo}" if _articulo else "")
                        st.markdown(t("especificacion_turbina_titulo_cantidad", titulo=_titulo, cantidad=_cantidad))
                        st.caption(t("especificacion_caption_fabricante", numero_parte=_specs["numero_parte"]))
                        _filas_turbina = [
                            (t("especificacion_fila_potencia_nominal"), f"{_specs['potencia_nominal_w']:.0f} W"),
                            (t("especificacion_fila_velocidad_nominal"), f"{_specs['viento_potencia_nominal_ms']} m/s"),
                            (t("especificacion_fila_cutin"), f"{_specs['velocidad_cutin_ms']} m/s"),
                            (t("especificacion_fila_supervivencia"), f"{_specs['velocidad_supervivencia_ms']} m/s"),
                            (t("especificacion_fila_tipo_rotor"), t(_specs["tipo_rotor"])),
                            (t("especificacion_fila_tipo_generador"), t(_specs["tipo_generador"])),
                            (t("especificacion_fila_diametro_rotor"), f"{_specs['diametro_rotor_m']} m"),
                            (t("especificacion_fila_altura_pala"), f"{_specs['altura_pala_m']} m"),
                            (t("especificacion_fila_peso"), f"{_specs['peso_total_kg']} kg"),
                            (t("especificacion_fila_cimentacion"), t(_specs["cimentacion_requerida"])),
                        ]
                        if _capacidad_controlador_w is not None:
                            # Dato del controlador/inversor incluido en ESE artículo --
                            # distinto de la potencia del generador de arriba, no se
                            # suman ni se reemplazan entre sí (ver docstring de
                            # capacidad_controlador_articulo_w).
                            _filas_turbina.insert(
                                1, (t("especificacion_fila_capacidad_controlador"), f"{_capacidad_controlador_w:.0f} W")
                            )
                        _col_espec, _col_val = t("especificacion_col_especificacion"), t("especificacion_col_valor")
                        st.dataframe(
                            pd.DataFrame([{_col_espec: f, _col_val: v} for f, v in _filas_turbina]),
                            hide_index=True, use_container_width=True,
                        )
                        _datos_pdf["turbinas"].append({
                            "nombre": _titulo.replace("**", ""), "cantidad": _cantidad, "clave": _clave,
                            "numero_parte": _specs["numero_parte"], "filas": _filas_turbina,
                        })

            st.divider()
            st.caption(t("especificacion_caption_fuente"))

            st.divider()
            st.markdown(t("especificacion_subheader_informe"))
            st.caption(t("especificacion_caption_informe_resumen"))

            # BUG REAL corregido acá: esto generaba los gráficos (vía kaleido, que
            # necesita un navegador Chrome/Chromium real) SIN estar detrás de un botón --
            # Streamlit ejecuta el cuerpo de TODAS las pestañas en cada rerun (no sólo la
            # que se está mirando), así que esto corría de nuevo cada vez que se apretaba
            # CUALQUIER botón en CUALQUIER pestaña (ej. "Calcular producción del
            # proyecto"). Si kaleido/Chrome no estaban disponibles en el entorno, esto
            # tumbaba TODA la app con un error crudo en cada rerun posterior -- no dejaba
            # ni navegar a otras pestañas sin perder los datos cargados. Ahora sólo corre
            # cuando el usuario aprieta este botón, y una falla acá ya no rompe el resto
            # de la app.
            if st.button(t("especificacion_boton_generar_pdf")):
                try:
                    with st.spinner(t("especificacion_spinner_generando")):
                        # Contexto climático: mismos gráficos que la pestaña "Contexto
                        # climático", generados de nuevo acá (no reutiliza el objeto ya
                        # mostrado en pantalla) para poder exportarlos a PNG sin tocar lo
                        # que el usuario está viendo.
                        _media_confirmada = resultado_clima["media"]
                        _z0_actual = st.session_state.get("z0_avanzado", Z0_DEFAULT)
                        _altura_explorar = max(st.session_state.get("altura_explorar_slider", 10.0), 1.0)

                        if "meta" in resultado_clima:
                            _meta = resultado_clima["meta"]
                            _fuente_texto = t(
                                "especificacion_pdf_fuente_estacion",
                                estacion=_meta["estacion"], pais=_meta["pais"], wmo=_meta["wmo"],
                                lat=f"{_meta['lat']:.4f}", lon=f"{_meta['lon']:.4f}",
                                elevacion_m=f"{_meta['elevacion_m']:.0f}", media=f"{_media_confirmada:.2f}",
                            )
                        else:
                            _fuente_texto = t("especificacion_pdf_fuente_generico", media=f"{_media_confirmada:.2f}")

                        _fig_heatmap_pdf, _ = crear_heatmap_plotly(
                            resultado_clima["hm_json"], media_anual=_media_confirmada,
                            altura_m=_altura_explorar, z0=_z0_actual,
                        )

                        _datos_pdf["clima"] = {
                            "fuente_texto": _fuente_texto,
                            "img_rosa": fig_a_png(crear_rosa_vientos_plotly(resultado_clima["rosa_detallada"])),
                            "img_heatmap": fig_a_png(_fig_heatmap_pdf) if _fig_heatmap_pdf else None,
                            "img_perfil": fig_a_png(crear_perfil_viento_plotly(
                                _media_confirmada, z0=_z0_actual,
                                altura_max=max(_altura_explorar * 1.15, 10.0), altura_marcada=_altura_explorar,
                            )),
                        }

                        _datos_pdf["produccion"] = {
                            "filas_tabla": [
                                (NOMBRES_MODELO.get(r["modelo"], r["modelo"]), r["N"], r["altura_buje"],
                                 f"{r['kwh_anual']:,.0f}", f"{r['v_hub_medio']:.2f}",
                                 f"{r['pct_horas_bajo_cutin']:.1f}")
                                for r in _prod["resultados"]
                            ],
                            "correccion_densidad_pct": _prod["correccion_densidad_pct"],
                            "img_mensual": fig_a_png(crear_produccion_mensual_plotly(_prod["kwh_mensual_total"])),
                            "img_duracion": fig_a_png(crear_curva_duracion_plotly(_prod["serie_total_w"])),
                            "img_viento": (
                                fig_a_png(crear_desglose_viento_plotly(
                                    _prod["tabla_desglose_viento"], ancho_bin=1.0,
                                    capacidad_electronica_w=_prod["resultados"][0]["capacidad_electronica_w"]))
                                if not _prod["tabla_desglose_viento"].empty else None
                            ),
                        }

                        _datos_pdf["financiero"] = st.session_state.get("ultimo_resultado_financiero")

                        st.session_state["informe_ejecutivo_pdf"] = generar_pdf_informe_ejecutivo(
                            _datos_pdf, logo_path=LOGO_ECO if os.path.exists(LOGO_ECO) else None,
                            idioma=st.session_state.get("idioma", IDIOMA_DEFAULT))
                        st.session_state["informe_ejecutivo_sin_financiero"] = not _datos_pdf["financiero"]
                except Exception as e:
                    st.session_state["informe_ejecutivo_pdf"] = None
                    st.error(t("especificacion_error_generar_pdf", error=e))

            if st.session_state.get("informe_ejecutivo_pdf"):
                if st.session_state.get("informe_ejecutivo_sin_financiero"):
                    st.caption(t("especificacion_caption_informe_sin_financiero"))
                st.download_button(
                    t("especificacion_boton_descargar_pdf"),
                    data=st.session_state["informe_ejecutivo_pdf"],
                    file_name=f"ECO-Wind_informe_ejecutivo_{date.today().isoformat()}.pdf",
                    mime="application/pdf",
                    type="primary",
                )


# --- Tab: Eco-Roof Energy Hub -- producto de fábrica preconfigurado (Small Tulip, ---
# --- 1m), motor y catálogo separados del sistema de clústers libres (Pista A) -------
# --- (engine/eco_roof_*.py) -- NO toca simular()/power_in_bouquet() ni ningún -------
# --- resultado ya calculado para el Estadio Heredia o el business case de CNFL. -----

with tab_eco_roof:
    st.caption(t("ecoroof_caption_intro"))

    if not st.session_state.get("sitio_activo") or st.session_state.sitio_activo.get("error"):
        st.info(t("ecoroof_info_sin_clima"))
    else:
        resultado_clima_er = st.session_state.sitio_activo
        df_clima_er = resultado_clima_er["df_clima"]
        meta_er = resultado_clima_er["meta"]
        elevacion_er = resultado_clima_er["elevacion_m"]
        ruta_epw_er = resultado_clima_er["ruta_epw"]

        _opciones_er = {clave: t(f"ecoroof_nombre_{clave}") for clave in ECO_ROOF_PRESETS
                         if preset_disponible(clave)}
        _clave_er = st.selectbox(t("ecoroof_selectbox_producto"), options=list(_opciones_er.keys()),
                                  format_func=lambda k: _opciones_er[k])
        preset_er = ECO_ROOF_PRESETS[_clave_er]
        specs_producto_er = SPECS_TURBINAS[preset_er["specs_key"]]
        specs_turbina_er = SPECS_TURBINAS[preset_er["turbina_key"]]
        z0_er = st.session_state.get("z0_avanzado", Z0_DEFAULT)

        # El bloque solar corre una simulación REAL de EnergyPlus (unos segundos) --
        # _simular_eco_roof_cacheado() evita repetirla en cada rerun de Streamlit. Esto
        # corre SIN botón (a diferencia del PDF de abajo) apenas hay un sitio activo, así
        # que sí necesita su propio try/except -- una falla real de EnergyPlus (binario
        # ausente, EPW corrupto, etc.) no debe tumbar toda la pestaña con una traza cruda.
        idioma_er = st.session_state.get("idioma", IDIOMA_DEFAULT)
        resultado_er = None
        try:
            with st.spinner(t("ecoroof_spinner_solar")):
                resultado_er = _simular_eco_roof_cacheado(
                    _clave_er, df_clima_er, ruta_epw_er, elevacion_er, z0_er,
                )
        except Exception as e:
            st.error(t("especificacion_error_generar_pdf", error=e))

        if resultado_er is not None:
            c1, c2, c3 = st.columns(3)
            c1.metric(t("ecoroof_metric_eolica"), f"{resultado_er['kwh_anual_eolico']:,.0f} kWh")
            c2.metric(t("ecoroof_metric_solar"), f"{resultado_er['kwh_anual_solar']:,.0f} kWh")
            c3.metric(t("ecoroof_metric_total"), f"{resultado_er['kwh_anual_total']:,.0f} kWh")
            # tr() con el mismo texto/clave que ya usa el PDF (pdf_ecoroof_caja_advertencia_solar)
            # -- antes esto mostraba resultado_er["solar"]["advertencia"] crudo, siempre en
            # español, sin importar el idioma elegido en el toggle ES/EN.
            st.caption(tr("pdf_ecoroof_caja_advertencia_solar", idioma_er))

            st.divider()
            st.markdown(t("pdf_ecoroof_subheader_produccion_eolica"))
            st.plotly_chart(crear_produccion_mensual_plotly(resultado_er["kwh_mensual_eolico"]),
                             use_container_width=True, key="ecoroof_chart_mensual_eolico")
            st.markdown(t("pdf_ecoroof_subheader_produccion_solar"))
            st.plotly_chart(crear_produccion_mensual_plotly(resultado_er["solar"]["kwh_mensual"]),
                             use_container_width=True, key="ecoroof_chart_mensual_solar")

            st.divider()
            st.markdown(t("pdf_ecoroof_tabla_potencia_titulo"))
            st.caption(t("pdf_ecoroof_nota_potencia"))
            st.dataframe(pd.DataFrame({
                t("pdf_ecoroof_col_velocidad"): [f"{v} m/s" for v in range(16)],
                t("pdf_ecoroof_col_potencia"): [
                    f"{potencia_tabla_w(float(v), preset_er['tabla_potencia']):.1f} W" for v in range(16)
                ],
            }), hide_index=True, use_container_width=True)

            st.divider()
            st.markdown(t("especificacion_subheader_informe"))
            # Mismo patrón que el informe del 3-M Tulip (ver comentario ahí): SOLO corre
            # detrás de un botón explícito -- Streamlit ejecuta el cuerpo de todas las
            # pestañas en cada rerun, generar esto sin botón tumbaría la app entera si
            # kaleido/Chrome no están disponibles, cada vez que se aprieta cualquier botón
            # en cualquier pestaña.
            if st.button(t("especificacion_boton_generar_pdf"), key="ecoroof_boton_generar_pdf"):
                try:
                    with st.spinner(t("especificacion_spinner_generando")):
                        if "meta" in resultado_clima_er:
                            _fuente_texto_er = t(
                                "especificacion_pdf_fuente_estacion",
                                estacion=meta_er["estacion"], pais=meta_er["pais"], wmo=meta_er["wmo"],
                                lat=f"{meta_er['lat']:.4f}", lon=f"{meta_er['lon']:.4f}",
                                elevacion_m=f"{meta_er['elevacion_m']:.0f}",
                                media=f"{resultado_clima_er['media']:.2f}",
                            )
                        else:
                            _fuente_texto_er = t("especificacion_pdf_fuente_generico",
                                                  media=f"{resultado_clima_er['media']:.2f}")

                        _fig_heatmap_er, _ = crear_heatmap_plotly(
                            resultado_clima_er["hm_json"], media_anual=resultado_clima_er["media"],
                            altura_m=preset_er["altura_buje_m"], z0=z0_er,
                        )

                        _datos_pdf_er = {
                            "sitio_nombre": st.session_state.get("sitio_nombre_activo") or "--",
                            "elevacion_m": elevacion_er,
                            "preset": {
                                "nombre": t(f"ecoroof_nombre_{_clave_er}"), "n_turbinas": preset_er["N"],
                                "numero_parte": specs_producto_er["numero_parte"],
                                "clase_iec": specs_turbina_er["clase_iec"],
                                "tipo_techo": preset_er["tipo_techo"],
                                "peso_kg_m2": specs_producto_er["peso_total_kg"],
                                "cimentacion_texto": t(specs_producto_er["cimentacion_requerida"]),
                                "angulo_max_techo_deg": preset_er["angulo_max_techo_deg"],
                                "tabla_potencia_w": preset_er["tabla_potencia"],
                                "capacidad_solar_kwp": preset_er["capacidad_solar_kwp"],
                                "ruta_imagen": RUTA_IMAGEN.get(preset_er["specs_key"]),
                            },
                            "clima": {
                                "fuente_texto": _fuente_texto_er,
                                "img_rosa": fig_a_png(crear_rosa_vientos_plotly(
                                    resultado_clima_er["rosa_detallada"])),
                                "img_heatmap": fig_a_png(_fig_heatmap_er) if _fig_heatmap_er else None,
                                "img_perfil": fig_a_png(crear_perfil_viento_plotly(
                                    resultado_clima_er["media"], z0=z0_er,
                                    altura_max=max(preset_er["altura_buje_m"] * 1.15, 10.0),
                                    altura_marcada=preset_er["altura_buje_m"],
                                )),
                            },
                            "produccion": {
                                "kwh_anual_eolico": resultado_er["kwh_anual_eolico"],
                                "kwh_anual_solar": resultado_er["kwh_anual_solar"],
                                "kwh_anual_total": resultado_er["kwh_anual_total"],
                                "img_mensual_eolico": fig_a_png(
                                    crear_produccion_mensual_plotly(resultado_er["kwh_mensual_eolico"])),
                                "img_mensual_solar": fig_a_png(
                                    crear_produccion_mensual_plotly(resultado_er["solar"]["kwh_mensual"])),
                            },
                            # CAPEX sin módulo financiero propio para Eco-Roof todavía --
                            # None acá muestra la misma caja "completá estos datos" que ya
                            # usa el informe del 3-M Tulip cuando falta, nunca se inventa
                            # un CAPEX.
                            "financiero": None,
                        }
                        st.session_state["informe_eco_roof_pdf"] = generar_pdf_informe_eco_roof(
                            _datos_pdf_er, logo_path=LOGO_ECO if os.path.exists(LOGO_ECO) else None,
                            idioma=idioma_er)
                except Exception as e:
                    st.session_state["informe_eco_roof_pdf"] = None
                    st.error(t("especificacion_error_generar_pdf", error=e))

            if st.session_state.get("informe_eco_roof_pdf"):
                st.download_button(
                    t("especificacion_boton_descargar_pdf"),
                    data=st.session_state["informe_eco_roof_pdf"],
                    file_name=f"ECO-Wind_informe_eco_roof_{date.today().isoformat()}.pdf",
                    mime="application/pdf",
                    type="primary",
                    key="ecoroof_boton_descargar_pdf",
                )

