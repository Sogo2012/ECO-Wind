"""
ECO | Wind -- Simulador de microgeneración eólica (Fase 2).

Sobre el motor validado de Pista A (engine/simulador_pista_a.py +
engine/flower_turbines_curves.py, Hallazgo 12), extendido con clima
multi-sitio, corrección de densidad, multi-clúster y gráficos (Hallazgo 17
-- ver avance-de-proyecto.md).

ALCANCE HONESTO:
- San José (Juan Santamaría) tiene datos GWA reales y completos (curva de
  excedencia + patrón diurno propios). Cualquier OTRA coordenada de Costa
  Rica usa la velocidad media real del ráster de GWA (si está descargado
  en datos_clima/gwa_costa_rica_10m.tif -- ver engine/gwa_raster.py) con
  la FORMA prestada de San José, escalada a esa media -- una aproximación
  declarada, no datos propios del sitio nuevo.
- El ráster de Costa Rica no se pudo descargar en este entorno de
  desarrollo (globalwindatlas.info bloqueado, Hallazgo 2) -- si no existe
  el archivo, la app lo dice claramente en vez de fallar oscuro.
- Elevación: para San José ya está confirmada (921m, AIP/DGAC). Para
  coordenadas nuevas se pide manual por ahora -- la búsqueda automática
  por DEM queda pendiente (Hallazgo 17).
- Sin mapa, sin PDF, sin registro de leads todavía.
- Corre local; despliegue a Cloud Run sigue pendiente.
"""
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulador_pista_a import (
    SITIOS_DISPONIBLES, cargar_gwa_json, generar_clima_gwa, cargar_wind_rose_lib,
    simular, comparar_metodo_ingenuo_vs_horario,
)
from engine.flower_turbines_curves import CURVE_COEFFICIENTS
from engine.gwa_raster import generar_clima_sitio_nuevo, RUTA_RASTER_CR_DEFAULT

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

def cargar_clima_sitio(modo, sitio_key, lat, lon, elevacion_m):
    """Devuelve (df_clima, media_confirmada, ws_json, hm_json, es_aproximacion, error)."""
    if modo == "San José (datos completos)":
        sitio = SITIOS_DISPONIBLES[sitio_key]
        ws_json, hm_json = cargar_gwa_json(os.path.join(BASE_DIR, sitio["carpeta_gwa"]))
        df_clima, media = generar_clima_gwa(ws_json, hm_json)
        return df_clima, media, ws_json, hm_json, False, None
    else:
        if not os.path.exists(RUTA_RASTER_CR_DEFAULT):
            return None, None, None, None, True, (
                f"No existe el ráster de Costa Rica ({os.path.basename(RUTA_RASTER_CR_DEFAULT)}). "
                "Hay que descargarlo primero desde un entorno con internet real (Colab) -- "
                "ver engine/gwa_raster.py, descargar_raster_costa_rica(). No se puede calcular "
                "para una coordenada nueva sin ese archivo."
            )
        try:
            df_clima, media = generar_clima_sitio_nuevo(lat, lon)
        except (FileNotFoundError, ValueError, KeyError) as e:
            return None, None, None, None, True, str(e)
        sitio_forma = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
        ws_json, hm_json = cargar_gwa_json(os.path.join(BASE_DIR, sitio_forma["carpeta_gwa"]))
        return df_clima, media, ws_json, hm_json, True, None


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
    modo_sitio = st.radio("Fuente de datos", options=["San José (datos completos)", "Coordenada personalizada"])

    if modo_sitio == "San José (datos completos)":
        sitio_key = "san_jose_juan_santamaria"
        sitio = SITIOS_DISPONIBLES[sitio_key]
        lat, lon = sitio["lat"], sitio["lon"]
        elevacion_m = sitio["elevacion_m"]
        st.caption(f"lat={lat}, lon={lon}, elevación={elevacion_m:.0f}m (AIP/DGAC)")
    else:
        sitio_key = None
        st.warning(
            "Aproximación (Requisito 1, Hallazgo 17): magnitud real del ráster de GWA, forma "
            "(variabilidad, estacionalidad) prestada de San José. No son datos propios del sitio.",
            icon="⚠️",
        )
        lat = st.number_input("Latitud", value=9.9, min_value=8.0, max_value=11.3, format="%.4f")
        lon = st.number_input("Longitud", value=-84.0, min_value=-86.0, max_value=-82.5, format="%.4f")
        elevacion_m = st.number_input("Elevación (m sobre el nivel del mar)", value=800.0, min_value=0.0,
                                       max_value=3800.0, step=50.0,
                                       help="Búsqueda automática por DEM pendiente (Hallazgo 17) -- por ahora, manual.")

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
            "Rugosidad del terreno (z0)", options=[0.03, 0.1, 0.3, 1.0],
            format_func=lambda z: {0.03: "0.03 — campo abierto", 0.1: "0.1 — cultivos bajos",
                                    0.3: "0.3 — suburbano (default)", 1.0: "1.0 — urbano denso"}[z],
            index=2,
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
        df_clima, media_confirmada, ws_json, hm_json, es_aproximacion, error = cargar_clima_sitio(
            modo_sitio, sitio_key, lat, lon, elevacion_m)

        if error:
            st.error(error, icon="🚫")
        else:
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
                ruta_lib = os.path.join(BASE_DIR, SITIOS_DISPONIBLES["san_jose_juan_santamaria"]["carpeta_gwa"],
                                         "gwc_point_1_10m.lib")
                rosa = cargar_wind_rose_lib(ruta_lib)
                cg1, cg2 = st.columns(2)
                cg1.pyplot(graficar_rosa_vientos(rosa["freq"]))
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
