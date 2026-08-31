"""
ECO | Wind -- Simulador de microgeneración eólica (Fase 2, MVP).

Arranque de la productización (plan-tecnico-eco-wind.md, seccion 5), sobre
el motor validado de Pista A (engine/simulador_pista_a.py +
engine/flower_turbines_curves.py, Hallazgo 12).

ALCANCE HONESTO DE ESTE MVP -- no todavia lo que describe el plan completo:
- Solo hay UN sitio con datos climaticos reales preparados (San José /
  Juan Santamaría, Global Wind Atlas). El flujo "cualquier coordenada ->
  pronóstico instantáneo" sigue pendiente -- GWA hoy es descarga manual
  por sitio, no una API en vivo (ver docstring de simulador_pista_a.py).
- Sin mapa, sin PDF, sin registro de leads todavía -- eso es lo que
  falta para llegar a la version completa del plan.
- Corre local por ahora; el despliegue a Cloud Run (Docker/Cloud Build,
  mismo patrón de Skyplus/DDP-Lite) es un paso aparte, pendiente.
"""
import os
import sys

import pandas as pd
import streamlit as st

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from engine.simulador_pista_a import (
    SITIOS_DISPONIBLES, cargar_gwa_json, generar_clima_gwa, simular,
)
from engine.flower_turbines_curves import CURVE_COEFFICIENTS

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
st.caption("Fase 1 (motor validado) → Fase 2 (este MVP). Ver avance-de-proyecto.md para el detalle técnico completo.")

st.warning(
    "**Alcance de este MVP:** solo cubre el sitio San José/Juan Santamaría con datos reales "
    "de Global Wind Atlas. Para un sitio nuevo, todavía hace falta descargar sus datos GWA "
    "manualmente y agregarlos — el flujo de coordenada arbitraria en vivo no está resuelto.",
    icon="⚠️",
)

col_config, col_resultado = st.columns([1, 2])

with col_config:
    st.subheader("Configuración del proyecto")

    sitio_key = st.selectbox(
        "Sitio", options=list(SITIOS_DISPONIBLES.keys()),
        format_func=lambda k: SITIOS_DISPONIBLES[k]["nombre"],
    )
    sitio = SITIOS_DISPONIBLES[sitio_key]

    modelo = st.selectbox(
        "Modelo de turbina", options=list(CURVE_COEFFICIENTS.keys()),
        format_func=lambda k: NOMBRES_MODELO.get(k, k),
        index=list(CURVE_COEFFICIENTS.keys()).index("medium_tulip"),
    )

    N = st.number_input("Número de turbinas en el bouquet", min_value=1, max_value=20, value=3, step=1)

    altura_buje = st.number_input("Altura de buje (m)", min_value=0.5, max_value=15.0, value=3.0, step=0.5)

    with st.expander("Parámetros avanzados"):
        z0 = st.selectbox(
            "Rugosidad del terreno (z0)",
            options=[0.03, 0.1, 0.3, 1.0],
            format_func=lambda z: {0.03: "0.03 — campo abierto", 0.1: "0.1 — cultivos bajos",
                                    0.3: "0.3 — suburbano (default)", 1.0: "1.0 — urbano denso"}[z],
            index=2,
        )
        metodo_bouquet = st.radio(
            "Modelo de Efecto Bouquet", options=["real", "lineal"],
            format_func=lambda m: "Real (exponencial, validado R²≥0.999996)" if m == "real"
            else "Lineal de marketing (solo referencia, subestima fuerte)",
        )

    calcular = st.button("Calcular producción anual", type="primary", use_container_width=True)

with col_resultado:
    st.subheader("Resultado")

    if calcular:
        ws_json, hm_json = cargar_gwa_json(os.path.join(BASE_DIR, sitio["carpeta_gwa"]))
        df_gwa, media_global = generar_clima_gwa(ws_json, hm_json)
        r = simular(df_gwa, altura_buje=altura_buje, modelo=modelo, N=int(N),
                    z0=z0, metodo_bouquet=metodo_bouquet)

        c1, c2, c3 = st.columns(3)
        c1.metric("Producción anual", f"{r['kwh_anual']:,.0f} kWh")
        c2.metric("Viento medio a la altura de buje", f"{r['v_hub_medio']:.2f} m/s")
        c3.metric("Horas bajo cut-in", f"{r['pct_horas_bajo_cutin']:.1f}%")

        st.caption(f"Viento medio confirmado a 10m (GWA, panel web): {media_global:.3f} m/s")

        st.markdown("**Producción mensual**")
        st.bar_chart(r["kwh_mensual"].rename("kWh"), color=VERDE)

        st.caption(
            "Motor: `flower_turbines_curves.py` (P=k·v³ × Efecto Bouquet, validado contra el "
            "calculador oficial de Flower Turbines, Hallazgo 12). Fuente climática: Global Wind "
            "Atlas (confirmado con datos reales a 10m, Hallazgo 3) — NO NASA POWER (subestima "
            "~3x en Costa Rica, Hallazgo 1)."
        )
    else:
        st.info("Configurá el proyecto a la izquierda y presioná **Calcular producción anual**.")

st.divider()
st.caption(
    "ECO Consultor — Simulador en desarrollo (Fase 2, MVP). "
    "Pendiente: mapa de ubicación, más sitios, PDF de cotización, registro de leads, despliegue a Cloud Run."
)
