"""
Sistema de internacionalizacion (ES/EN) de ECO | Wind.

La app ahora le habla al cliente final, no solo al equipo de desarrollo -- todo
texto visible (pestanas, botones, captions, mensajes de error, graficos,
informe PDF) vive en este diccionario, con una entrada en espanol y otra en
ingles, y se selecciona con el toggle de idioma del sidebar.

t(clave, **kwargs)
    Para usar en app.py -- lee el idioma activo de
    st.session_state["idioma"] (por defecto "es") y devuelve el texto ya
    traducido. Si el texto tiene datos variables (numeros, nombres), se
    formatean en Python ANTES de llamar a t() (ej. f"{valor:,.0f}") y se
    pasan como kwargs -- la plantilla de traduccion solo tiene el texto y
    los {marcadores}, nunca el formato numerico, porque el orden de la
    oracion cambia entre espanol e ingles.

tr(clave, idioma, **kwargs)
    Misma tabla, pero con el idioma pasado explicito en vez de leido de
    session_state -- para modulos que no dependen de una sesion de
    Streamlit activa (engine/pdf_reporte.py), para que se puedan probar y
    usar de forma independiente.

Convencion de claves: "<seccion>_<descripcion_corta>" (ej. "clima_error_epw",
"financiero_metric_capex", "pdf_titulo_informe") -- cada seccion de la app
tiene su propio prefijo para que nunca choquen dos claves de secciones
distintas.

GLOSARIO tecnico (electromecanico) usado de forma consistente en toda la
app -- no traducir termino por termino fuera de esta lista, usar SIEMPRE
estos pares:
    velocidad de viento / wind speed          rosa de vientos / wind rose
    perfil logaritmico de viento / logarithmic wind profile
    rugosidad del terreno (z0) / terrain roughness (z0)
    altura de buje / hub height                densidad del aire / air density
    corrección por densidad / air-density correction
    curva de potencia / power curve            curva de duración / duration curve
    clúster / cluster                          bouquet / bouquet (no se traduce,
        término propio de fábrica de Flower Turbines)
    estación climática / weather station       archivo EPW / EPW file
    elevación / elevation                      velocidad de cut-in / cut-in speed
    CAPEX / CAPEX   OPEX / OPEX   Payback / Payback period   ROI / ROI
    NPV / NPV (NO se traduce a "VAN" -- la app y el cliente ya usan "NPV"
        también en la versión en español)
    tasa de descuento / discount rate          vida útil / useful life
    viabilidad económica / economic viability  tarifa eléctrica / electricity rate
    inversor / inverter    BESS / BESS (Battery Energy Storage System)
    bus de corriente continua / DC bus         controlador / controller
    tipo de cambio / exchange rate             N° de parte / Part number
    ficha técnica / technical datasheet        potencia pico / peak power
    energía anual / annual energy              producción mensual / monthly output
"""
import streamlit as st

IDIOMA_DEFAULT = "es"
IDIOMAS_DISPONIBLES = {"es": "Español", "en": "English"}

# Cada agente/sección agrega sus propias claves acá -- prefijo por sección
# (sidebar_, tabs_, chart_, modelo_, mes_, clima_, contexto_, equipos_,
# resultados_, financiero_, especificacion_, pdf_) para que nunca choquen.
TRANSLATIONS = {

    # --- Sidebar / menú lateral ---------------------------------------------------
    "sidebar_subtitulo_marca": {
        "es": "Simulador de microgeneración eólica",
        "en": "Wind micro-generation simulator",
    },
    "sidebar_elegido_hasta_ahora": {
        "es": "Elegido hasta ahora",
        "en": "Selected so far",
    },
    "sidebar_sin_sitio": {
        "es": "Sin sitio seleccionado todavía.",
        "en": "No site selected yet.",
    },
    "sidebar_resumen_clusters": {
        "es": "{n_clusters} clúster(es), {n_turbinas} turbina(s) en total.",
        "en": "{n_clusters} cluster(s), {n_turbinas} turbine(s) total.",
    },
    "sidebar_calculo_listo": {
        "es": "Cálculo de producción listo.",
        "en": "Production calculation ready.",
    },
    "sidebar_metric_tipo_cambio": {
        "es": "Tipo de cambio BCCR",
        "en": "BCCR exchange rate",
    },
    "sidebar_bccr_emergencia": {
        "es": "BCCR no disponible -- valor de emergencia, no del día.",
        "en": "BCCR unavailable -- fallback value, not today's rate.",
    },
    "sidebar_copyright": {
        "es": "© {anio} ECO Consultor. Todos los derechos reservados.",
        "en": "© {anio} ECO Consultor. All rights reserved.",
    },
    "sidebar_idioma_label": {
        "es": "Idioma / Language",
        "en": "Idioma / Language",
    },

    # --- Título de página / pestañas ------------------------------------------------
    "app_titulo_pagina": {
        "es": "ECO | Wind — Simulador",
        "en": "ECO | Wind — Simulator",
    },
    "tabs_clima": {"es": "Selección de clima", "en": "Climate selection"},
    "tabs_contexto": {"es": "Contexto climático", "en": "Climate context"},
    "tabs_config": {"es": "Equipos y configuración", "en": "Equipment & configuration"},
    "tabs_resultados": {"es": "Resultados", "en": "Results"},
    "tabs_financiero": {"es": "Análisis Financiero", "en": "Financial analysis"},
    "tabs_especificacion": {"es": "Especificación Técnica", "en": "Technical specification"},

    # --- Nombres de modelo de turbina (NOMBRES_MODELO) -----------------------------
    "modelo_small_tulip": {"es": "Small Tulip (1.15m pala)", "en": "Small Tulip (1.15m blade)"},
    "modelo_medium_tulip": {"es": "Medium Tulip (2m pala)", "en": "Medium Tulip (2m blade)"},
    "modelo_three_m_tulip": {"es": "3-M Tulip (3m pala)", "en": "3-M Tulip (3m blade)"},
    "modelo_large_tulip": {"es": "Large Tulip (5m pala)", "en": "Large Tulip (5m blade)"},
    "modelo_al13_2m": {"es": "AL13 Power Tower (2 módulos)", "en": "AL13 Power Tower (2 modules)"},
    "modelo_al13_4m": {"es": "AL13 Power Tower (4 módulos)", "en": "AL13 Power Tower (4 modules)"},
    "modelo_al13_6m": {"es": "AL13 Power Tower (6 módulos)", "en": "AL13 Power Tower (6 modules)"},
    "modelo_al13_8m": {"es": "AL13 Power Tower (8 módulos)", "en": "AL13 Power Tower (8 modules)"},

    # --- Meses (abreviados, para ejes de gráficos) ----------------------------------
    "mes_ene": {"es": "Ene", "en": "Jan"}, "mes_feb": {"es": "Feb", "en": "Feb"},
    "mes_mar": {"es": "Mar", "en": "Mar"}, "mes_abr": {"es": "Abr", "en": "Apr"},
    "mes_may": {"es": "May", "en": "May"}, "mes_jun": {"es": "Jun", "en": "Jun"},
    "mes_jul": {"es": "Jul", "en": "Jul"}, "mes_ago": {"es": "Ago", "en": "Aug"},
    "mes_sep": {"es": "Sep", "en": "Sep"}, "mes_oct": {"es": "Oct", "en": "Oct"},
    "mes_nov": {"es": "Nov", "en": "Nov"}, "mes_dic": {"es": "Dic", "en": "Dec"},

    # --- Helpers de clima (errores de carga de EPW) ---------------------------------
    "clima_error_descarga_estacion": {
        "es": "No se pudo descargar los datos de {nombre}. Verificá la conexión a internet e intentá de nuevo.",
        "en": "Could not download data for {nombre}. Check your internet connection and try again.",
    },
    "clima_error_epw_invalido": {
        "es": ("No se pudo leer el archivo como EPW válido: {error} -- confirmá que es un .epw real "
               "(formato EnergyPlus/climate.onebuilding.org, 8 líneas de encabezado + una fila por "
               "hora) y no un archivo renombrado o exportado de otra herramienta."),
        "en": ("Could not read the file as a valid EPW: {error} -- confirm it's a real .epw file "
               "(EnergyPlus/climate.onebuilding.org format, 8 header lines plus one row per hour), "
               "not a renamed file or an export from another tool."),
    },

    # --- Gráficos Plotly: curva de duración -----------------------------------------
    "chart_duracion_titulo": {
        "es": "Curva de duración -- resolución horaria completa",
        "en": "Duration curve -- full hourly resolution",
    },
    "chart_duracion_eje_x": {
        "es": "% de las 8,760 horas del año (ordenadas de mayor a menor producción)",
        "en": "% of the year's 8,760 hours (sorted from highest to lowest output)",
    },
    "chart_duracion_eje_y": {
        "es": "Potencia (W, total del proyecto)",
        "en": "Power (W, total project)",
    },
    # OJO -- estos 3 hover se llaman con t("clave") SIN kwargs (son estáticos,
    # no llevan datos de sesión), así que t()/tr() NO pasa por .format() acá
    # adentro -- van con llaves SIMPLES, la sintaxis literal de Plotly
    # (%{x:.1f}), no dobles. Los que sí se llaman CON kwargs (chart_rosa_hover,
    # chart_perfil_hover_marcado) sí necesitan %{{...}} para sobrevivir el
    # .format() y no perder la sintaxis de Plotly.
    "chart_duracion_hover": {
        "es": "<b>%{x:.1f}% de las horas</b><br>Potencia: %{y:,.0f} W<extra></extra>",
        "en": "<b>%{x:.1f}% of hours</b><br>Power: %{y:,.0f} W<extra></extra>",
    },

    # --- Gráficos Plotly: producción mensual ----------------------------------------
    "chart_mensual_titulo": {
        "es": "Producción mensual (todos los clústers)",
        "en": "Monthly output (all clusters)",
    },
    "chart_mensual_eje_x": {"es": "Mes", "en": "Month"},
    "chart_mensual_eje_y": {"es": "Energía (kWh)", "en": "Energy (kWh)"},
    "chart_mensual_hover": {
        "es": "<b>%{x}</b><br>Producción: %{y:,.0f} kWh<extra></extra>",
        "en": "<b>%{x}</b><br>Output: %{y:,.0f} kWh<extra></extra>",
    },

    # --- Gráficos Plotly: rosa de vientos --------------------------------------------
    "chart_rosa_titulo": {
        "es": "Rosa de vientos -- % de horas por dirección y velocidad (calma: {pct_calma}%)",
        "en": "Wind rose -- % of hours by direction and speed (calm: {pct_calma}%)",
    },
    "chart_rosa_leyenda_titulo": {"es": "Velocidad", "en": "Speed"},
    "chart_rosa_hover": {
        "es": "<b>%{{theta}}</b><br>{etiqueta}: %{{r:.1f}}% de las horas del año<extra></extra>",
        "en": "<b>%{{theta}}</b><br>{etiqueta}: %{{r:.1f}}% of the year's hours<extra></extra>",
    },

    # --- Gráficos Plotly: heatmap mensual/horario ------------------------------------
    "chart_heatmap_aviso_altura_baja": {
        "es": ("Altura elegida ({altura}m) por debajo de la rugosidad del terreno destino "
               "(z0={z0}m) -- el perfil logarítmico no es físicamente confiable ahí, mismo "
               "criterio que wind_at_height()."),
        "en": ("Chosen height ({altura}m) is below the target terrain's roughness length "
               "(z0={z0}m) -- the logarithmic profile is not physically reliable there, same "
               "criterion used by wind_at_height()."),
    },
    "chart_heatmap_hover": {
        "es": "<b>{mes}</b><br>Hora: {hora}:00<br>{velocidad} m/s a {altura}m (índice {indice})",
        "en": "<b>{mes}</b><br>Hour: {hora}:00<br>{velocidad} m/s at {altura}m (index {indice})",
    },
    "chart_heatmap_colorbar": {"es": "m/s", "en": "m/s"},
    "chart_heatmap_titulo": {
        "es": "Velocidad media real del viento a {altura}m (mes × hora)",
        "en": "Actual average wind speed at {altura}m (month × hour)",
    },
    "chart_heatmap_eje_x": {"es": "Hora del día", "en": "Hour of day"},
    "chart_heatmap_eje_y": {"es": "Mes", "en": "Month"},

    # --- Gráficos Plotly: perfil logarítmico de viento -------------------------------
    "chart_perfil_hover": {
        "es": "<b>%{y:.2f}m</b><br>Viento: %{x:.2f} m/s<extra></extra>",
        "en": "<b>%{y:.2f}m</b><br>Wind: %{x:.2f} m/s<extra></extra>",
    },
    "chart_perfil_hover_marcado": {
        "es": "<b>{altura}m</b><br>Viento: {velocidad} m/s<extra></extra>",
        "en": "<b>{altura}m</b><br>Wind: {velocidad} m/s<extra></extra>",
    },
    "chart_perfil_texto_marcado": {"es": "{velocidad} m/s", "en": "{velocidad} m/s"},
    "chart_perfil_titulo": {
        "es": "Perfil logarítmico de viento (z0 destino={z0} m)",
        "en": "Logarithmic wind profile (target z0={z0} m)",
    },
    "chart_perfil_eje_x": {"es": "Velocidad (m/s)", "en": "Wind speed (m/s)"},
    "chart_perfil_eje_y": {"es": "Altura (m)", "en": "Height (m)"},

    # --- Mapa de estaciones (Folium) --------------------------------------------------
    "mapa_popup_sitio": {
        "es": "Tu sitio: {lat}, {lon}",
        "en": "Your site: {lat}, {lon}",
    },
    "mapa_popup_estacion": {
        "es": "<b>{nombre}</b><br>{estado}<br>Distancia: {distancia} km",
        "en": "<b>{nombre}</b><br>{estado}<br>Distance: {distancia} km",
    },
    "mapa_no_disponible": {"es": "N/D", "en": "N/A"},

}


def tr(clave: str, idioma: str, **kwargs) -> str:
    """Traduce `clave` al `idioma` dado ("es"/"en"), explícito -- para módulos
    que no dependen de una sesión de Streamlit activa (ej. pdf_reporte.py)."""
    entrada = TRANSLATIONS.get(clave)
    if entrada is None:
        return f"[[{clave}]]"
    texto = entrada.get(idioma) or entrada.get(IDIOMA_DEFAULT) or f"[[{clave}]]"
    return texto.format(**kwargs) if kwargs else texto


def t(clave: str, **kwargs) -> str:
    """Traduce `clave` al idioma activo de la sesión de Streamlit
    (st.session_state["idioma"], por defecto "es") -- para usar en app.py."""
    idioma = st.session_state.get("idioma", IDIOMA_DEFAULT)
    return tr(clave, idioma, **kwargs)


def meses_abreviados(idioma: str = None) -> list:
    """Lista de 12 meses abreviados en el idioma dado (o el activo de sesión
    si no se pasa ninguno) -- mismo orden que engine/*.py que arma matrices
    mes×hora (Ene..Dic / Jan..Dec)."""
    claves = ["mes_ene", "mes_feb", "mes_mar", "mes_abr", "mes_may", "mes_jun",
              "mes_jul", "mes_ago", "mes_sep", "mes_oct", "mes_nov", "mes_dic"]
    if idioma is None:
        return [t(c) for c in claves]
    return [tr(c, idioma) for c in claves]
