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

    # --- Fichas técnicas de turbinas (SPECS_TURBINAS: tipo_rotor, tipo_generador, ---
    # --- cimentacion_requerida -- los 3 únicos campos de esa ficha que la app hoy --
    # --- muestra en pantalla; sistema_frenado/material_palas/material_chasis están --
    # --- en los datos pero no se despliegan todavía, se dejan en español hasta que --
    # --- se conecten a algún lugar visible) -----------------------------------------
    "specs_small_tulip_rotor": {"es": "VAWT (Eje Vertical, 2 Palas)", "en": "VAWT (Vertical Axis, 2 Blades)"},
    "specs_small_tulip_generador": {
        "es": "PMSG Imanes Permanentes (máx. 200W picos cortos)",
        "en": "PMSG Permanent Magnets (max. 200W short peaks)",
    },
    "specs_small_tulip_cimentacion": {
        "es": "Dado concreto 0.5x0.5x0.5m o lastre Eco-Roof",
        "en": "0.5x0.5x0.5m concrete block, or Eco-Roof ballast",
    },

    "specs_survival_unit_rotor": {
        "es": "VAWT Portátil sobre contenedor móvil",
        "en": "VAWT, portable on mobile container",
    },
    "specs_survival_unit_generador": {"es": "PMSG", "en": "PMSG"},
    "specs_survival_unit_cimentacion": {
        "es": "Sin cimentación (autoestable)",
        "en": "No foundation required (self-supporting)",
    },

    "specs_medium_tulip_rotor": {"es": "VAWT (Eje Vertical, 2 Palas)", "en": "VAWT (Vertical Axis, 2 Blades)"},
    "specs_medium_tulip_generador": {
        "es": "PMSG (Electrónica 1000W en grupos de 10)",
        "en": "PMSG (1000W electronics in groups of 10)",
    },
    "specs_medium_tulip_cimentacion": {
        "es": "Losa 2.1x2.1x0.25m o zapata 1.0x1.0x1.6m (12x M14)",
        "en": "2.1x2.1x0.25m slab, or 1.0x1.0x1.6m footing (12x M14)",
    },

    "specs_three_m_tulip_rotor": {"es": "VAWT (Eje Vertical, 2 Palas)", "en": "VAWT (Vertical Axis, 2 Blades)"},
    "specs_three_m_tulip_generador": {
        "es": "PMSG (Electrónica 1500W o 2000W en grupos >=10)",
        "en": "PMSG (1500W or 2000W electronics in groups >=10)",
    },
    "specs_three_m_tulip_cimentacion": {
        "es": "Base de concreto reforzada con pernos M14",
        "en": "Reinforced concrete base with M14 bolts",
    },

    "specs_large_tulip_rotor": {"es": "VAWT (Eje Vertical, 2 Palas)", "en": "VAWT (Vertical Axis, 2 Blades)"},
    "specs_large_tulip_generador": {"es": "PMSG Trifásico", "en": "Three-phase PMSG"},
    "specs_large_tulip_cimentacion": {
        "es": "Zapata 2.5x2.5x0.9m o 2.5x4.0x0.5m",
        "en": "2.5x2.5x0.9m footing, or 2.5x4.0x0.5m",
    },

    "specs_al13_2m_rotor": {
        "es": "VAWT Modular (Palas cruzadas a 90°)",
        "en": "Modular VAWT (blades crossed at 90°)",
    },
    "specs_al13_2m_generador": {
        "es": "PMSG Modular de 24V o 48V AC",
        "en": "Modular PMSG, 24V or 48V AC",
    },
    "specs_al13_2m_cimentacion": {
        "es": "Base de concreto 1.0x1.0x2.2m",
        "en": "1.0x1.0x2.2m concrete base",
    },

    "specs_al13_6m_rotor": {
        "es": "VAWT Modular (Palas cruzadas a 90°)",
        "en": "Modular VAWT (blades crossed at 90°)",
    },
    "specs_al13_6m_generador": {"es": "PMSG de 5 kW", "en": "5 kW PMSG"},
    "specs_al13_6m_cimentacion": {
        "es": "Zapata 2.5x2.5x0.9m + Anclaje para poste",
        "en": "2.5x2.5x0.9m footing + post anchor",
    },

    "specs_al13_8m_rotor": {
        "es": "VAWT Modular (Palas cruzadas a 90°)",
        "en": "Modular VAWT (blades crossed at 90°)",
    },
    "specs_al13_8m_generador": {"es": "PMSG de 10 kW", "en": "10 kW PMSG"},
    "specs_al13_8m_cimentacion": {
        "es": "Zapata 2.5x2.5x1.2m + Poste lateral a 1280 mm",
        "en": "2.5x2.5x1.2m footing + side post at 1280 mm",
    },

    "specs_ecoroof_flat_3_rotor": {
        "es": "3 Turbinas VAWT (1m) en plataforma plana",
        "en": "3 VAWT turbines (1m) on a flat platform",
    },
    "specs_ecoroof_flat_3_generador": {
        "es": "PMSG (Capacidad solar aprox: 2 x 100W)",
        "en": "PMSG (approx. solar capacity: 2 x 100W)",
    },
    "specs_ecoroof_flat_3_cimentacion": {
        "es": "Instalación sin perforaciones (Efecto Bouquet integrado)",
        "en": "Drilling-free installation (integrated Bouquet Effect)",
    },

    "specs_ecoroof_flat_5_rotor": {
        "es": "5 Turbinas VAWT (1m) en plataforma plana",
        "en": "5 VAWT turbines (1m) on a flat platform",
    },
    "specs_ecoroof_flat_5_generador": {
        "es": "PMSG (Capacidad solar aprox: 4 x 100W)",
        "en": "PMSG (approx. solar capacity: 4 x 100W)",
    },
    "specs_ecoroof_flat_5_cimentacion": {
        "es": "Instalación sin perforaciones",
        "en": "Drilling-free installation",
    },

    "specs_ecoroof_slanted_rotor": {
        "es": "Módulos de 3 Turbinas VAWT (1m) en techo inclinado",
        "en": "Modules of 3 VAWT turbines (1m) on a slanted roof",
    },
    "specs_ecoroof_slanted_generador": {
        "es": "PMSG (Capacidad solar aprox: 2x400W o 4x400W por módulo)",
        "en": "PMSG (approx. solar capacity: 2x400W or 4x400W per module)",
    },
    "specs_ecoroof_slanted_cimentacion": {
        "es": "Sin perforaciones. Ángulo máximo de techo: 3°",
        "en": "No drilling. Maximum roof angle: 3°",
    },

    # --- Meses (abreviados, para ejes de gráficos) ----------------------------------
    "mes_ene": {"es": "Ene", "en": "Jan"}, "mes_feb": {"es": "Feb", "en": "Feb"},
    "mes_mar": {"es": "Mar", "en": "Mar"}, "mes_abr": {"es": "Abr", "en": "Apr"},
    "mes_may": {"es": "May", "en": "May"}, "mes_jun": {"es": "Jun", "en": "Jun"},
    "mes_jul": {"es": "Jul", "en": "Jul"}, "mes_ago": {"es": "Ago", "en": "Aug"},
    "mes_sep": {"es": "Sep", "en": "Sep"}, "mes_oct": {"es": "Oct", "en": "Oct"},
    "mes_nov": {"es": "Nov", "en": "Nov"}, "mes_dic": {"es": "Dic", "en": "Dec"},

    # --- Tab: Selección de clima (tab_clima) -----------------------------------------
    "clima_caption_intro": {
        "es": ("Pega las coordenadas de tu sitio (ej: 9.999665, -84.123064). El sistema "
               "busca las estaciones climáticas reales más cercanas -- elegí una de la "
               "lista, o subí directo el EPW que quieras usar como referencia."),
        "en": ("Paste your site's coordinates (e.g. 9.999665, -84.123064). The system "
               "looks up the closest real weather stations -- pick one from the list, "
               "or upload the EPW file you want to use as a reference."),
    },
    "clima_spinner_buscando": {
        "es": "Buscando estaciones cercanas...",
        "en": "Searching for nearby stations...",
    },
    "clima_error_sin_estaciones": {
        "es": "No se encontraron estaciones para esta ubicación.",
        "en": "No stations were found for this location.",
    },
    "clima_input_coordenadas_label": {
        "es": "Coordenadas (latitud, longitud)",
        "en": "Coordinates (latitude, longitude)",
    },
    "clima_input_coordenadas_placeholder": {
        "es": "Ej: 9.999665, -84.123064",
        "en": "E.g.: 9.999665, -84.123064",
    },
    "clima_boton_buscar": {"es": "Buscar", "en": "Search"},
    "clima_error_formato_coordenadas": {
        "es": "Formato: latitud, longitud (ej: 9.999, -84.123)",
        "en": "Format: latitude, longitude (e.g. 9.999, -84.123)",
    },
    "clima_error_coordenadas_invalidas": {
        "es": "Coordenadas inválidas. Usa números separados por coma.",
        "en": "Invalid coordinates. Use numbers separated by a comma.",
    },
    "clima_sitio_activo": {
        "es": "Sitio activo: **{nombre}**",
        "en": "Active site: **{nombre}**",
    },
    "clima_subheader_mapa": {"es": "Mapa interactivo", "en": "Interactive map"},
    "clima_caption_estaciones_cercanas": {
        "es": "**Estaciones climáticas más cercanas:**",
        "en": "**Closest weather stations:**",
    },
    "clima_estacion_fila": {
        "es": "**{nombre}** — {estado} ({distancia} km)",
        "en": "**{nombre}** — {estado} ({distancia} km)",
    },
    "clima_boton_usar": {"es": "Usar", "en": "Use"},
    "clima_caption_estacion_lejana": {
        "es": ("La estación real más cercana está a {distancia} km -- si tenés el EPW "
               "real de un sitio más representativo (propio o de otro lugar), subilo "
               "abajo en vez de usar una estación tan lejana."),
        "en": ("The closest real station is {distancia} km away -- if you have the real "
               "EPW for a more representative site (your own or another location), "
               "upload it below instead of using such a distant station."),
    },
    "clima_caption_epw_pregunta": {
        "es": "**¿Tenés el EPW real de tu sitio (o de otro lugar que quieras usar como referencia)?**",
        "en": "**Do you have the real EPW for your site (or another location you'd like to use as a reference)?**",
    },
    "clima_uploader_epw_label": {"es": "Subir archivo .epw", "en": "Upload .epw file"},
    "clima_boton_usar_epw": {"es": "Usar este EPW", "en": "Use this EPW"},
    "clima_epw_subido_nombre": {
        "es": "EPW subido -- {nombre}",
        "en": "Uploaded EPW -- {nombre}",
    },

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
    "chart_rosa_dir_n": {"es": "N", "en": "N"},
    "chart_rosa_dir_ne": {"es": "NE", "en": "NE"},
    "chart_rosa_dir_e": {"es": "E", "en": "E"},
    "chart_rosa_dir_se": {"es": "SE", "en": "SE"},
    "chart_rosa_dir_s": {"es": "S", "en": "S"},
    "chart_rosa_dir_so": {"es": "SO", "en": "SW"},
    "chart_rosa_dir_o": {"es": "O", "en": "W"},
    "chart_rosa_dir_no": {"es": "NO", "en": "NW"},
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

    # --- Tab: Contexto climático (tab_contexto) --------------------------------------
    "contexto_info_sin_sitio": {
        "es": "Elegí primero un sitio en la pestaña \"Selección de clima\" para ver su contexto climático.",
        "en": "First pick a site in the \"Climate selection\" tab to see its climate context.",
    },
    "contexto_estacion_real": {
        "es": ("Estación real: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, lon={lon}, "
               "elevación={elevacion_m}m. Media anual real (10m): {media} m/s."),
        "en": ("Real station: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, lon={lon}, "
               "elevation={elevacion_m}m. Real annual average (10m): {media} m/s."),
    },
    "contexto_slider_altura_label": {
        "es": "Altura de buje a explorar (m)",
        "en": "Hub height to explore (m)",
    },
    "contexto_slider_altura_help": {
        "es": ("Mueve esta altura para ver cómo cambia la velocidad real del viento (heatmap y "
               "perfil de abajo) entre la altura de referencia del EPW (10m) y la altura real de "
               "buje de tu turbina -- misma fórmula y rugosidad que usa el cálculo de energía. "
               "Para una instalación en TECHO de un edificio, usá altura del edificio + altura del "
               "mástil sobre el techo -- ojo, la ley logarítmica extrapola la velocidad REGIONAL "
               "a esa altura, no el efecto aerodinámico local de estar encima de un edificio "
               "puntual (aceleración sobre el borde del techo, turbulencia)."),
        "en": ("Move this height to see how the real wind speed changes (heatmap and profile "
               "below) between the EPW reference height (10m) and your turbine's real hub "
               "height -- same formula and roughness used by the energy calculation. For a "
               "ROOFTOP installation, use building height + mast/support height above the roof "
               "-- note that the logarithmic law extrapolates the REGIONAL wind speed to that "
               "height, not the local aerodynamic effect of being on top of a specific building "
               "(edge acceleration, turbulence)."),
    },
    "contexto_caption_rugosidad": {
        "es": ("Rugosidad de destino usada abajo: z0={z0} m -- configurable en "
               "\"Equipos y configuración\" > Parámetros avanzados."),
        "en": ("Target roughness used below: z0={z0} m -- configurable in "
               "\"Equipment & configuration\" > Advanced parameters."),
    },

    # --- Tab: Equipos y configuración (tab_config) ------------------------------------
    "equipos_subheader_clusters": {"es": "Clústers del proyecto", "en": "Project clusters"},
    "equipos_label_modelo": {"es": "Modelo", "en": "Model"},
    "equipos_label_n": {"es": "N", "en": "N"},
    "equipos_label_buje": {"es": "Buje (m)", "en": "Hub (m)"},
    "equipos_help_buje": {
        "es": ("Para una instalación en TECHO (ej. azotea de un edificio de varios pisos): "
               "altura del edificio (m) + altura del mástil/soporte sobre el techo -- NO la "
               "cantidad de pisos. Un edificio de 15 pisos ronda 45-55m según la altura de "
               "entrepiso."),
        "en": ("For a ROOFTOP installation (e.g. a multi-story building's roof): building "
               "height (m) + mast/support height above the roof -- NOT the number of floors. "
               "A 15-story building runs about 45-55m depending on floor-to-floor height."),
    },
    "equipos_boton_quitar_cluster": {"es": "Quitar este clúster", "en": "Remove this cluster"},
    "equipos_label_articulo": {
        "es": "Artículo (precio EXWORKS real de fábrica)",
        "en": "Item (real EXWORKS factory price)",
    },
    "equipos_help_articulo": {
        "es": ("Elegí la variante exacta del catálogo real de Flower Turbines que vas a "
               "cotizar (unidad simple, bouquet, on/off-grid, con o sin accesorio) -- "
               "también define la capacidad de la electrónica que se usa para calcular "
               "la producción (pestaña \"Resultados\") y el costeo (pestaña \"Análisis "
               "Financiero\")."),
        "en": ("Pick the exact variant from Flower Turbines' real catalog that you're going "
               "to quote (single unit, bouquet, on/off-grid, with or without accessory) -- "
               "this also sets the electronics capacity used to calculate production (\"Results\" "
               "tab) and costing (\"Financial analysis\" tab)."),
    },
    "equipos_caption_precio": {
        "es": "Precio: \\${precio_unitario} c/u -- Total del clúster ({cantidad}x): \\${precio_total}",
        "en": "Price: \\${precio_unitario} each -- Cluster total ({cantidad}x): \\${precio_total}",
    },
    "equipos_caption_sin_precio": {
        "es": "Precio no disponible todavía (no hay artículo cargado en el catálogo para este modelo).",
        "en": "Price not available yet (no catalog item loaded for this model).",
    },
    "equipos_expander_ficha_tecnica": {
        "es": "Ficha técnica -- {nombre_modelo}",
        "en": "Technical datasheet -- {nombre_modelo}",
    },
    "equipos_caption_sin_ficha": {
        "es": "Sin ficha técnica cargada todavía para este modelo.",
        "en": "No technical datasheet loaded yet for this model.",
    },
    "equipos_caption_sin_imagen": {"es": "Sin imagen todavía.", "en": "No image yet."},
    "equipos_caption_numero_parte": {
        "es": "N° de parte: {numero_parte} -- {clase_iec}",
        "en": "Part number: {numero_parte} -- {clase_iec}",
    },
    "equipos_ficha_markdown": {
        "es": ("- **Potencia nominal:** {potencia_nominal_w} W a {viento_potencia_nominal_ms} m/s\n"
               "- **Cut-in / supervivencia:** {velocidad_cutin_ms} m/s / {velocidad_supervivencia_ms} m/s\n"
               "- **Generador:** {tipo_generador} ({polos_generador} polos)\n"
               "- **Salida:** {voltaje_salida}\n"
               "- **Dimensiones:** {altura_total_m} m altura total, {diametro_rotor_m} m diámetro "
               "de rotor, {peso_total_kg} kg\n"
               "- **Vida de diseño:** {vida_diseno_anos} años\n"
               "- **Cimentación requerida:** {cimentacion_requerida}"),
        "en": ("- **Rated power:** {potencia_nominal_w} W at {viento_potencia_nominal_ms} m/s\n"
               "- **Cut-in / survival:** {velocidad_cutin_ms} m/s / {velocidad_supervivencia_ms} m/s\n"
               "- **Generator:** {tipo_generador} ({polos_generador} poles)\n"
               "- **Output:** {voltaje_salida}\n"
               "- **Dimensions:** {altura_total_m} m total height, {diametro_rotor_m} m rotor "
               "diameter, {peso_total_kg} kg\n"
               "- **Design life:** {vida_diseno_anos} years\n"
               "- **Foundation required:** {cimentacion_requerida}"),
    },
    "equipos_boton_agregar_cluster": {"es": "+ Agregar clúster", "en": "+ Add cluster"},
    "equipos_expander_avanzados": {"es": "Parámetros avanzados", "en": "Advanced parameters"},
    "equipos_label_z0": {
        "es": "Rugosidad DEL SITIO donde va la turbina (z0)",
        "en": "Terrain roughness AT THE TURBINE SITE (z0)",
    },
    "equipos_help_z0": {
        "es": ("Rugosidad del sitio DESTINO (donde se instala la turbina), no la del sitio "
               "de referencia climática -- son dos valores distintos (ver el detalle en "
               "\"Resultados\")."),
        "en": ("Roughness of the DESTINATION site (where the turbine is installed), not the "
               "climate reference site's -- these are two different values (see the detail in "
               "\"Results\")."),
    },
    "equipos_z0_campo_abierto": {"es": "campo abierto", "en": "open field"},
    "equipos_z0_cultivos_bajos": {"es": "cultivos bajos", "en": "low crops"},
    "equipos_z0_suburbano": {"es": "suburbano (default)", "en": "suburban (default)"},
    "equipos_z0_urbano_denso": {"es": "urbano denso", "en": "dense urban"},
    "equipos_label_metodo_bouquet": {"es": "Modelo de Efecto Bouquet", "en": "Bouquet Effect model"},
    "equipos_metodo_real": {
        "es": "Real (exponencial, validado R²≥0.999996)",
        "en": "Real (exponential, validated R²≥0.999996)",
    },
    "equipos_metodo_lineal": {
        "es": "Lineal de marketing (solo referencia, subestima fuerte)",
        "en": "Marketing linear (reference only, strongly underestimates)",
    },
    "equipos_warning_sin_sitio": {
        "es": "Elegí un sitio en la pestaña \"Selección de clima\" antes de calcular.",
        "en": "Pick a site in the \"Climate selection\" tab before calculating.",
    },
    "equipos_boton_calcular": {
        "es": "Calcular producción del proyecto",
        "en": "Calculate project production",
    },

    # --- Tab: Resultados (tab_resultados) ---------------------------------------------
    "resultados_caption_intro": {
        "es": ("Producción de energía del proyecto -- el cálculo financiero (CAPEX, tarifa "
               "eléctrica, payback) está en la pestaña \"Análisis Financiero\"."),
        "en": ("Project energy production -- the financial calculation (CAPEX, electricity "
               "rate, payback) is in the \"Financial analysis\" tab."),
    },
    "resultados_error_sin_estacion": {
        "es": "Elegí primero una estación (o subí un EPW) en la pestaña \"Selección de clima\".",
        "en": "First pick a station (or upload an EPW) in the \"Climate selection\" tab.",
    },
    "resultados_metric_produccion_anual": {"es": "Producción anual total", "en": "Total annual production"},
    "resultados_metric_turbinas_totales": {"es": "Turbinas totales", "en": "Total turbines"},
    "resultados_metric_correccion_densidad": {
        "es": "Corrección por densidad (elevación)",
        "en": "Density correction (elevation)",
    },
    "resultados_metric_correccion_densidad_valor": {"es": "{pct}% menos", "en": "{pct}% less"},
    "resultados_metric_altura_buje": {"es": "Altura de buje", "en": "Hub height"},
    "resultados_subheader_detalle_cluster": {"es": "**Detalle por clúster**", "en": "**Detail by cluster**"},
    "resultados_col_modelo": {"es": "Modelo", "en": "Model"},
    "resultados_col_n": {"es": "N", "en": "N"},
    "resultados_col_buje": {"es": "Buje (m)", "en": "Hub (m)"},
    "resultados_col_kwh_anio": {"es": "kWh/año", "en": "kWh/year"},
    "resultados_col_v_media_buje": {"es": "V. medio buje (m/s)", "en": "Avg. hub speed (m/s)"},
    "resultados_col_pct_bajo_cutin": {"es": "% bajo cut-in", "en": "% below cut-in"},
    "resultados_col_pct_recorte": {"es": "% horas con recorte", "en": "% hours clipped"},
    "resultados_col_kwh_perdidos_recorte": {
        "es": "kWh/año perdidos por recorte",
        "en": "kWh/year lost to clipping",
    },
    "resultados_caption_recorte": {
        "es": ("\"Recorte\": horas donde el viento (+ Efecto Bouquet) le daría más energía a "
               "la turbina de la que su controlador/inversor puede procesar -- ese excedente "
               "se pierde, no se cuenta en el kWh/año. Depende de qué artículo (capacidad de "
               "electrónica) elegiste para cada clúster en \"Equipos y configuración\" -- sin "
               "elegir ninguno todavía, se asume el tamaño de fábrica del modelo, el más "
               "conservador."),
        "en": ("\"Clipping\": hours where the wind (+ Bouquet Effect) would give the turbine "
               "more energy than its controller/inverter can process -- that excess is lost, "
               "not counted in kWh/year. It depends on which item (electronics capacity) you "
               "chose for each cluster in \"Equipment & configuration\" -- if none was chosen "
               "yet, the model's factory size is assumed, the most conservative option."),
    },
    "resultados_expander_perfil_viento": {
        "es": "Perfil de viento por altura: dos rugosidades, y una verificación independiente",
        "en": "Wind profile by height: two roughness lengths, and an independent check",
    },
    "resultados_perfil_texto1": {
        "es": ("El viento de referencia (10m, aeropuerto/EPW) y el sitio real donde va la "
               "turbina casi nunca tienen la misma rugosidad. Por eso esta app usa z0 del "
               "sitio destino (seleccionable arriba en esta pestaña) **distinto** de z0 de "
               "referencia (0.1, clase \"country\"/aeropuerto -- fórmula logarítmica)."),
        "en": ("The reference wind (10m, airport/EPW) and the actual site where the turbine "
               "goes almost never share the same roughness. That's why this app uses the "
               "destination site's z0 (selectable above in this tab) **different** from the "
               "reference z0 (0.1, \"country\"/airport class -- logarithmic formula)."),
    },
    "resultados_perfil_texto2": {
        "es": ("**Verificación independiente** (ley de potencia que usa EnergyPlus por "
               "default, misma tabla de terrenos que ladybug-tools/ladybug, con el mismo "
               "**z0={z0}** elegido arriba -- internamente la clase con ese z0 tabulado se "
               "llama \"{terreno_dst}\" en la tabla original de EnergyPlus, aunque el nombre "
               "no siempre calce 1 a 1 con las etiquetas en español de esta app): {v_pot} m/s "
               "a {altura_buje}m de buje, vs. **{v_hub_medio} m/s** con la fórmula logarítmica "
               "usada arriba -- {conclusion}."),
        "en": ("**Independent check** (power law that EnergyPlus uses by default, same "
               "terrain table as ladybug-tools/ladybug, with the same **z0={z0}** chosen "
               "above -- internally the class with that tabulated z0 is called "
               "\"{terreno_dst}\" in the original EnergyPlus table, though the name doesn't "
               "always map 1-to-1 to this app's labels): {v_pot} m/s at {altura_buje}m hub, "
               "vs. **{v_hub_medio} m/s** with the logarithmic formula used above -- "
               "{conclusion}."),
    },
    "resultados_perfil_concuerdan": {"es": "concuerdan razonablemente", "en": "reasonably agree"},
    "resultados_perfil_difieren": {
        "es": "difieren más de lo esperado, revisar",
        "en": "differ more than expected, review",
    },
    "resultados_expander_horario_vs_media": {
        "es": "¿Por qué el cálculo es hora por hora, y no con la velocidad media?",
        "en": "Why is the calculation hour by hour, instead of using the average speed?",
    },
    "resultados_jensen_texto": {
        "es": ("Para el primer clúster: método correcto (P=k·v³ en cada una de las 8,760 "
               "horas) = **{kwh_correcto} kWh/año**. Método ingenuo (P evaluada en la "
               "velocidad media {v_media} m/s, ×8,760 horas) = **{kwh_ingenuo} kWh/año** -- el "
               "método ingenuo subestima **{razon}x**. Es la desigualdad de Jensen (P∝v³ es "
               "convexa, E[v³]≥(E[v])³): con un recurso variable, nunca es válido sustituir la "
               "velocidad media directo en la fórmula de potencia."),
        "en": ("For the first cluster: correct method (P=k·v³ at each of the 8,760 hours) = "
               "**{kwh_correcto} kWh/year**. Naive method (P evaluated at the average speed "
               "{v_media} m/s, ×8,760 hours) = **{kwh_ingenuo} kWh/year** -- the naive method "
               "underestimates by **{razon}x**. This is Jensen's inequality (P∝v³ is convex, "
               "E[v³]≥(E[v])³): with a variable resource, it's never valid to plug the average "
               "speed directly into the power formula."),
    },
    "resultados_caption_validado": {
        "es": ("Cálculo validado con datos de campo, con corrección por densidad de aire "
               "según elevación. Fuente climática: EPW real de la estación elegida o subida "
               "por el usuario."),
        "en": ("Calculation validated with field data, with air-density correction by "
               "elevation. Climate source: real EPW from the chosen station or the one "
               "uploaded by the user."),
    },
    "resultados_info_sin_calculo": {
        "es": ("Configurá el proyecto en la pestaña \"Equipos y configuración\" y presioná "
               "**Calcular producción del proyecto**."),
        "en": ("Configure the project in the \"Equipment & configuration\" tab and press "
               "**Calculate project production**."),
    },

    # --- Tab: Análisis Financiero (tab_financiero) -------------------------------------
    "financiero_caption_intro": {
        "es": ("Viabilidad económica del proyecto (CAPEX, Payback, ROI, NPV) -- usa las "
               "turbinas ya configuradas en \"Equipos y configuración\" y la producción ya "
               "calculada en \"Resultados\"."),
        "en": ("Project economic viability (CAPEX, Payback, ROI, NPV) -- uses the turbines "
               "already configured in \"Equipment & configuration\" and the production "
               "already calculated in \"Results\"."),
    },
    "financiero_toggle_label": {
        "es": "Activar módulo financiero (viabilidad económica)",
        "en": "Enable financial module (economic viability)",
    },
    "financiero_toggle_help": {
        "es": ("Apagalo si por ahora sólo te interesa el dimensionamiento técnico (pestaña "
               "\"Especificación Técnica\") y no necesitás calcular CAPEX/Payback/ROI todavía."),
        "en": ("Turn it off if for now you only care about the technical sizing (\"Technical "
               "specification\" tab) and don't need to calculate CAPEX/Payback/ROI yet."),
    },
    "financiero_info_desactivado": {
        "es": ("Módulo financiero desactivado. Activá el switch de arriba para ingresar costos "
               "reales y calcular Payback, ROI, NPV y viabilidad económica."),
        "en": ("Financial module disabled. Turn on the switch above to enter real costs and "
               "calculate Payback, ROI, NPV and economic viability."),
    },
    "financiero_info_sin_calculo": {
        "es": ("Configurá el proyecto en la pestaña \"Equipos y configuración\" y presioná "
               "**Calcular producción del proyecto** primero."),
        "en": ("Configure the project in the \"Equipment & configuration\" tab and press "
               "**Calculate project production** first."),
    },
    "financiero_subheader_tarifa": {"es": "**Tarifa eléctrica**", "en": "**Electricity rate**"},
    "financiero_label_modo_tarifa": {
        "es": "¿Cómo querés valorar el ahorro de electricidad?",
        "en": "How do you want to value the electricity savings?",
    },
    "financiero_help_modo_tarifa": {
        "es": ("La tarifa horaria cruza la producción REAL hora por hora de la turbina contra "
               "los periodos Punta/Valle/Nocturno de CNFL/ICE -- un kWh generado en horario "
               "Punta vale varias veces más que uno generado de noche, algo que una tarifa "
               "plana no puede reflejar. La tarifa comercial (T-CO) es para gimnasios/"
               "estadios/comercios -- precio plano por kWh según el consumo mensual del sitio, "
               "sin periodos horarios."),
        "en": ("The hourly rate crosses the turbine's REAL hour-by-hour production against "
               "CNFL/ICE's Peak/Off-peak/Night periods -- a kWh generated at peak time is "
               "worth several times more than one generated at night, something a flat rate "
               "can't reflect. The commercial rate (T-CO) is for gyms/stadiums/businesses -- a "
               "flat price per kWh based on the site's monthly consumption, no hourly periods."),
    },
    "financiero_tarifa_plana": {"es": "Tarifa plana (USD/kWh)", "en": "Flat rate (USD/kWh)"},
    "financiero_tarifa_aresep": {
        "es": "Tarifa horaria real de Costa Rica (ARESEP)",
        "en": "Real hourly Costa Rica rate (ARESEP)",
    },
    "financiero_tarifa_tco": {
        "es": "Tarifa comercial de Costa Rica (T-CO)",
        "en": "Costa Rica commercial rate (T-CO)",
    },
    "financiero_label_tarifa_plana_valor": {"es": "Tarifa eléctrica ($/kWh)", "en": "Electricity rate ($/kWh)"},
    "financiero_label_proveedor": {"es": "Proveedor", "en": "Provider"},
    "financiero_help_proveedor": {
        "es": "CNFL cubre el Gran Área Metropolitana; ICE el resto del país.",
        "en": "CNFL covers the Greater Metropolitan Area; ICE covers the rest of the country.",
    },
    "financiero_label_tramo": {"es": "Consumo mensual del sitio", "en": "Site's monthly consumption"},
    "financiero_help_tramo": {
        "es": ("Determina qué tarifa T-CO aplica -- gimnasios/estadios grandes normalmente "
               "caen en el tramo >3000 kWh/mes."),
        "en": ("Determines which T-CO rate applies -- large gyms/stadiums usually fall in the "
               ">3000 kWh/month bracket."),
    },
    "financiero_tramo_pequeno": {
        "es": "≤ 3000 kWh/mes (sin medidor de potencia)",
        "en": "≤ 3000 kWh/month (no demand meter)",
    },
    "financiero_tramo_grande": {
        "es": "> 3000 kWh/mes (con medidor de potencia)",
        "en": "> 3000 kWh/month (with demand meter)",
    },
    "financiero_label_tipo_cambio": {"es": "Tipo de cambio (₡ por USD)", "en": "Exchange rate (₡ per USD)"},
    "financiero_help_tipo_cambio": {
        "es": ("Precargado con el tipo de cambio de venta del día del Banco Central de Costa "
               "Rica (BCCR, ver sidebar) -- cambia a diario, es un punto de partida editable, "
               "no un valor fijo del sistema."),
        "en": ("Pre-filled with today's sell exchange rate from the Central Bank of Costa Rica "
               "(BCCR, see sidebar) -- it changes daily, it's an editable starting point, not a "
               "fixed system value."),
    },
    "financiero_caption_tco": {
        "es": "Tarifa T-CO: ₡{precio_crc_kwh}/kWh → \\${ahorro_usd}/año ({ahorro_crc} ₡/año).",
        "en": "T-CO rate: ₡{precio_crc_kwh}/kWh → \\${ahorro_usd}/year ({ahorro_crc} ₡/year).",
    },
    "financiero_info_tco_sin_demanda": {
        "es": ("Esta tarifa NO incluye el cargo por demanda máxima (kW) que T-CO también cobra "
               "en el tramo >3000 kWh -- calcularlo requeriría el perfil de demanda horaria del "
               "sitio (no sólo el consumo diario promedio) para saber si la turbina genera "
               "justo en el instante del pico. Este número es sólo el ahorro de energía, no el "
               "ahorro total de la factura."),
        "en": ("This rate does NOT include the peak demand charge (kW) that T-CO also bills in "
               "the >3000 kWh bracket -- calculating it would require the site's hourly demand "
               "profile (not just the average daily consumption) to know whether the turbine "
               "generates right at the peak instant. This number is only the energy savings, "
               "not the total bill savings."),
    },
    "financiero_label_tarifa_tou": {"es": "Tarifa", "en": "Rate"},
    "financiero_help_tarifa_tou": {
        "es": "T-REH/T-RH: residencial. T-MT: media tensión (proyectos más grandes).",
        "en": "T-REH/T-RH: residential. T-MT: medium voltage (larger projects).",
    },
    "financiero_caption_tou": {
        "es": ("Tarifa efectiva ponderada por producción real: \\${tarifa_efectiva}/kWh "
               "({ahorro_crc} ₡/año → \\${ahorro_usd}/año)."),
        "en": ("Effective rate weighted by real production: \\${tarifa_efectiva}/kWh "
               "({ahorro_crc} ₡/year → \\${ahorro_usd}/year)."),
    },
    "financiero_col_periodo": {"es": "Periodo", "en": "Period"},
    "financiero_col_kwh_anio": {"es": "kWh/año", "en": "kWh/year"},
    "financiero_col_precio_crc_kwh": {"es": "Precio (₡/kWh)", "en": "Price (₡/kWh)"},
    "financiero_col_valor_usd_anio": {"es": "Valor (USD/año)", "en": "Value (USD/year)"},
    "financiero_label_vida_util": {
        "es": "Vida útil del proyecto (años)",
        "en": "Project useful life (years)",
    },
    "financiero_label_tasa_descuento": {
        "es": "Tasa de descuento para NPV (%)",
        "en": "Discount rate for NPV (%)",
    },
    "financiero_subheader_equipo_elegido": {
        "es": "**Equipo elegido -- precio EXWORKS**",
        "en": "**Equipment chosen -- EXWORKS price**",
    },
    "financiero_caption_equipo_elegido": {
        "es": ("El artículo exacto del catálogo (unidad simple, bouquet, on/off-grid, con o "
               "sin accesorio) se elige por clúster en \"Equipos y configuración\" -- acá solo "
               "se muestra el precio resultante, de referencia para el costeo de abajo (no se "
               "usa solo para calcular Payback/ROI)."),
        "en": ("The exact catalog item (single unit, bouquet, on/off-grid, with or without "
               "accessory) is chosen per cluster in \"Equipment & configuration\" -- this only "
               "shows the resulting price, for reference in the costing below (it isn't used "
               "on its own to calculate Payback/ROI)."),
    },
    "financiero_caption_cluster_sin_precio": {
        "es": ("{nombre_modelo}: precio no disponible todavía (no hay artículo cargado en el "
               "catálogo, o no se eligió ninguno en \"Equipos y configuración\")."),
        "en": ("{nombre_modelo}: price not available yet (no catalog item loaded, or none was "
               "chosen in \"Equipment & configuration\")."),
    },
    "financiero_caption_cluster_precio": {
        "es": "{nombre_modelo} -- {articulo}: \\${precio_unitario} c/u -- Total del clúster ({cantidad}x): \\${precio_total}",
        "en": "{nombre_modelo} -- {articulo}: \\${precio_unitario} each -- Cluster total ({cantidad}x): \\${precio_total}",
    },
    "financiero_metric_precio_total": {
        "es": "Precio total del proyecto (equipos, EXWORKS)",
        "en": "Total project price (equipment, EXWORKS)",
    },
    "financiero_caption_precio_nota": {
        "es": ("Precio de venta de fábrica del artículo elegido en cada clúster. NO incluye "
               "flete, importación ni instalación -- eso lo agrega ECO Consultor aparte. Es el "
               "precio del artículo elegido × cantidad de turbinas del clúster -- si elegís un "
               "artículo de \"bouquet\" (varias turbinas con un solo inversor), revisá que la "
               "cantidad (N) del clúster tenga sentido con ese artículo."),
        "en": ("Factory sale price of the item chosen for each cluster. It does NOT include "
               "freight, import duties or installation -- ECO Consultor adds those separately. "
               "It's the chosen item's price × the cluster's turbine count -- if you pick a "
               "\"bouquet\" item (several turbines with a single inverter), check that the "
               "cluster's quantity (N) makes sense with that item."),
    },
    "financiero_caption_falta_articulo": {
        "es": " Al menos un modelo elegido todavía no tiene ningún artículo cargado.",
        "en": " At least one chosen model doesn't have any item loaded yet.",
    },
    "financiero_subheader_costeo_real": {
        "es": "**Costeo real del proyecto**",
        "en": "**Real project costing**",
    },
    "financiero_caption_costeo_real": {
        "es": ("En vez de estimar el CAPEX con costo de fábrica + margen + flete supuestos, "
               "ingresá acá los números reales de tu cotización: cuánto cuestan los equipos, a "
               "cuánto se los vas a vender al cliente, y cuánto vas a cobrar de mantenimiento "
               "al año. Payback, ROI, NPV y viabilidad se calculan directo de esos datos."),
        "en": ("Instead of estimating CAPEX with assumed factory cost + margin + freight, "
               "enter your quote's real numbers here: how much the equipment costs, what "
               "you'll sell it to the client for, and how much you'll charge for annual "
               "maintenance. Payback, ROI, NPV and viability are calculated directly from that "
               "data."),
    },
    "financiero_label_costo_equipos": {
        "es": "Costo de los equipos (turbinas + inversor + BESS, USD)",
        "en": "Equipment cost (turbines + inverter + BESS, USD)",
    },
    "financiero_help_costo_equipos": {
        "es": ("Lo que ECO Consultor paga por comprar/importar los equipos -- sólo "
               "informativo, para ver el margen (no entra en el cálculo de Payback)."),
        "en": ("What ECO Consultor pays to buy/import the equipment -- informational only, to "
               "see the margin (it doesn't enter the Payback calculation)."),
    },
    "financiero_label_precio_venta": {
        "es": "Precio de venta al cliente (USD)",
        "en": "Sale price to client (USD)",
    },
    "financiero_help_precio_venta": {
        "es": ("Precio final cotizado al cliente, llave en mano (equipos + instalación) -- "
               "este es el CAPEX real que se usa para Payback/ROI/NPV."),
        "en": ("Final turnkey price quoted to the client (equipment + installation) -- this is "
               "the real CAPEX used for Payback/ROI/NPV."),
    },
    "financiero_label_mantenimiento": {
        "es": "Mantenimiento anual (USD/año)",
        "en": "Annual maintenance (USD/year)",
    },
    "financiero_help_mantenimiento": {
        "es": ("Costo real esperado de mantenimiento al año -- reemplaza el % del CAPEX que se "
               "adivinaba antes."),
        "en": ("Real expected annual maintenance cost -- replaces the % of CAPEX that used to "
               "be guessed before."),
    },
    "financiero_caption_margen": {
        "es": "Margen sobre costo de equipos: ${margen_usd} ({margen_pct}%).",
        "en": "Margin over equipment cost: ${margen_usd} ({margen_pct}%).",
    },
    "financiero_info_falta_precio_venta": {
        "es": ("Ingresá el precio de venta al cliente para calcular Payback, ROI, NPV y "
               "viabilidad económica."),
        "en": ("Enter the sale price to the client to calculate Payback, ROI, NPV and economic "
               "viability."),
    },
    "financiero_info_error_tarifa_horaria": {
        "es": ("No se pudo calcular el ahorro con tarifa horaria (ver el error arriba) -- "
               "cambiá a \"Tarifa plana (USD/kWh)\" o revisá la selección de proveedor/tarifa."),
        "en": ("Could not calculate savings with the hourly rate (see the error above) -- "
               "switch to \"Flat rate (USD/kWh)\" or review the provider/rate selection."),
    },
    "financiero_info_error_tarifa_comercial": {
        "es": ("No se pudo calcular el ahorro con tarifa comercial (ver el error arriba) -- "
               "cambiá a \"Tarifa plana (USD/kWh)\" o revisá la selección de proveedor/tramo."),
        "en": ("Could not calculate savings with the commercial rate (see the error above) -- "
               "switch to \"Flat rate (USD/kWh)\" or review the provider/bracket selection."),
    },
    "financiero_metric_energia_generada": {"es": "Energía anual generada", "en": "Annual energy generated"},
    "financiero_metric_ahorro_anual": {
        "es": "Ahorro anual (electricidad no comprada)",
        "en": "Annual savings (electricity not purchased)",
    },
    "financiero_metric_mantenimiento_anual": {"es": "Mantenimiento anual", "en": "Annual maintenance"},
    "financiero_subheader_retorno": {
        "es": "**Retorno de la inversión**",
        "en": "**Return on investment**",
    },
    "financiero_metric_capex": {"es": "CAPEX (precio de venta)", "en": "CAPEX (sale price)"},
    "financiero_metric_payback": {"es": "Payback", "en": "Payback"},
    "financiero_valor_anos": {"es": "{val} años", "en": "{val} years"},
    "financiero_na": {"es": "N/A", "en": "N/A"},
    "financiero_metric_roi": {"es": "ROI (vida útil)", "en": "ROI (useful life)"},
    "financiero_metric_viabilidad": {"es": "Viabilidad", "en": "Viability"},
    "financiero_viable": {"es": "VIABLE", "en": "VIABLE"},
    "financiero_no_viable": {"es": "NO VIABLE", "en": "NOT VIABLE"},
    "financiero_caption_npv": {
        "es": "NPV a {anos} años, tasa de descuento {tasa}%: ${valor}",
        "en": "NPV over {anos} years, discount rate {tasa}%: ${valor}",
    },
    "financiero_caption_no_cubre_mantenimiento": {
        "es": ("El ahorro anual estimado en electricidad no alcanza a cubrir el mantenimiento "
               "anual ingresado (ahorro: \\${ahorro}/año vs. mantenimiento: "
               "\\${mantenimiento}/año) -- por eso Payback/ROI/NPV muestran N/A."),
        "en": ("The estimated annual electricity savings don't cover the annual maintenance "
               "entered (savings: \\${ahorro}/year vs. maintenance: \\${mantenimiento}/year) -- "
               "that's why Payback/ROI/NPV show N/A."),
    },
    "financiero_info_no_recupera_mantenimiento": {
        "es": ("Con el precio de venta y la tarifa eléctrica ingresados, este proyecto NO "
               "recupera el mantenimiento sólo con ahorro de electricidad. Si el objetivo del "
               "cliente es respaldo/resiliencia energética (no depender 100% de la red) en vez "
               "de recuperar la inversión sólo con el ahorro eléctrico, ese es el valor que hay "
               "que presentar -- este cálculo no lo cuantifica en dólares."),
        "en": ("With the sale price and electricity rate entered, this project does NOT "
               "recover maintenance from electricity savings alone. If the client's goal is "
               "energy backup/resilience (not depending 100% on the grid) rather than "
               "recovering the investment from electricity savings alone, that's the value to "
               "present -- this calculation doesn't quantify it in dollars."),
    },
    "resultados_subheader_viento": {
        "es": "**Desglose de producción por velocidad de viento**",
        "en": "**Production breakdown by wind speed**",
    },
    "resultados_caption_viento": {
        "es": ("La potencia crece con el cubo de la velocidad (P∝v³) -- por eso las horas de "
               "viento fuerte valen desproporcionadamente más que las de viento flojo. "
               "Calculado con la altura de buje del primer clúster (los clústers normalmente "
               "comparten la misma altura de instalación)."),
        "en": ("Power grows with the cube of speed (P∝v³) -- that's why strong-wind hours are "
               "worth disproportionately more than light-wind ones. Calculated using the first "
               "cluster's hub height (clusters usually share the same installation height)."),
    },
    "resultados_viento_leyenda_entregado": {"es": "Entregado (con recorte de electrónica)", "en": "Delivered (with electronics clipping)"},
    "resultados_viento_leyenda_perdido": {"es": "Perdido por el tope de electrónica", "en": "Lost to the electronics cap"},
    "resultados_viento_titulo_chart": {
        "es": "Energía entregada vs. perdida por tramo de {ancho} m/s",
        "en": "Energy delivered vs. lost, by {ancho} m/s bin",
    },
    "resultados_viento_eje_x": {"es": "Velocidad de viento en el buje (m/s)", "en": "Hub wind speed (m/s)"},
    "resultados_viento_eje_y": {"es": "Energía (kWh/año)", "en": "Energy (kWh/year)"},
    "resultados_viento_hover_entregado": {
        "es": "<b>%{x}</b><br>Entregado: %{y:,.0f} kWh<extra></extra>",
        "en": "<b>%{x}</b><br>Delivered: %{y:,.0f} kWh<extra></extra>",
    },
    "resultados_viento_hover_perdido": {
        "es": "<b>%{x}</b><br>Perdido por recorte: %{y:,.0f} kWh<extra></extra>",
        "en": "<b>%{x}</b><br>Lost to clipping: %{y:,.0f} kWh<extra></extra>",
    },
    "resultados_viento_expander_tabla": {"es": "Ver tabla completa", "en": "View full table"},
    "resultados_viento_col_bin": {"es": "Viento (m/s)", "en": "Wind (m/s)"},
    "resultados_viento_col_horas": {"es": "Horas", "en": "Hours"},
    "resultados_viento_col_pct_horas": {"es": "% horas", "en": "% hours"},
    "resultados_viento_col_kwh": {"es": "kWh entregado", "en": "kWh delivered"},
    "resultados_viento_col_pct_kwh": {"es": "% de la producción anual", "en": "% of annual production"},
    "resultados_viento_col_perdido": {"es": "kWh perdido (recorte)", "en": "kWh lost (clipping)"},
    "resultados_viento_anotacion_tope": {
        "es": "Tope de electrónica: {cap} W/turbina",
        "en": "Electronics cap: {cap} W/turbine",
    },
    "financiero_caption_footer": {
        "es": ("CAPEX, mantenimiento y precio de venta ingresados directo por el usuario. "
               "Tarifas horarias reales de CNFL/ICE cruzadas contra la producción hora por "
               "hora, en vez de una tarifa plana adivinada."),
        "en": ("CAPEX, maintenance and sale price entered directly by the user. Real CNFL/ICE "
               "hourly rates crossed against hour-by-hour production, instead of a guessed "
               "flat rate."),
    },

    # --- Tab: Especificación Técnica (tab_especificacion) ------------------------------
    "especificacion_caption_intro": {
        "es": ("Datos generales del sistema y ficha técnica de fábrica de las turbinas -- usa "
               "las turbinas ya configuradas en \"Equipos y configuración\" y la producción "
               "ya calculada en \"Resultados\"."),
        "en": ("General system data and the turbines' factory technical datasheet -- uses the "
               "turbines already configured in \"Equipment & configuration\" and the "
               "production already calculated in \"Results\"."),
    },
    "especificacion_info_sin_calculo": {
        "es": ("Configurá el proyecto en la pestaña \"Equipos y configuración\" y presioná "
               "Calcular producción del proyecto primero."),
        "en": ("Configure the project in the \"Equipment & configuration\" tab and press "
               "Calculate project production first."),
    },
    "especificacion_error_sin_resultado": {
        "es": "No se pudo leer el resultado de producción -- revisá la pestaña \"Resultados\".",
        "en": "Could not read the production result -- check the \"Results\" tab.",
    },
    "especificacion_subheader_datos_generales": {
        "es": "### Datos generales del sistema",
        "en": "### General system data",
    },
    "especificacion_metric_sitio": {"es": "Sitio", "en": "Site"},
    "especificacion_metric_potencia_pico": {"es": "Potencia pico instalada", "en": "Installed peak power"},
    "especificacion_metric_energia_anual": {"es": "Energía anual estimada", "en": "Estimated annual energy"},
    "especificacion_metric_elevacion": {"es": "Elevación del sitio", "en": "Site elevation"},
    "especificacion_texto_arquitectura": {
        "es": ("**Arquitectura eléctrica:** bus de corriente continua a {voltaje}V -- cada "
               "turbina entrega su salida a través de un controlador individual de fábrica; "
               "todos los controladores se conectan en paralelo al mismo bus, que alimenta "
               "directamente el puerto de batería del inversor (no el puerto solar/MPPT)."),
        "en": ("**Electrical architecture:** {voltaje}V DC bus -- each turbine delivers its "
               "output through an individual factory controller; all controllers connect in "
               "parallel to the same bus, which feeds directly into the inverter's battery "
               "port (not the solar/MPPT port)."),
    },
    "especificacion_subheader_turbinas": {"es": "### Turbinas eólicas", "en": "### Wind turbines"},
    "especificacion_turbina_titulo_cantidad": {
        "es": "{titulo} -- cantidad: {cantidad}",
        "en": "{titulo} -- quantity: {cantidad}",
    },
    "especificacion_caption_fabricante": {
        "es": "Fabricante: Flower Turbines -- N° de parte: {numero_parte}",
        "en": "Manufacturer: Flower Turbines -- Part number: {numero_parte}",
    },
    "especificacion_fila_potencia_nominal": {"es": "Potencia nominal (generador)", "en": "Rated power (generator)"},
    "especificacion_fila_velocidad_nominal": {
        "es": "Velocidad a potencia nominal",
        "en": "Speed at rated power",
    },
    "especificacion_fila_cutin": {"es": "Velocidad de arranque (cut-in)", "en": "Cut-in speed"},
    "especificacion_fila_supervivencia": {"es": "Velocidad de supervivencia", "en": "Survival speed"},
    "especificacion_fila_tipo_rotor": {"es": "Tipo de rotor", "en": "Rotor type"},
    "especificacion_fila_tipo_generador": {"es": "Tipo de generador", "en": "Generator type"},
    "especificacion_fila_diametro_rotor": {"es": "Diámetro del rotor", "en": "Rotor diameter"},
    "especificacion_fila_altura_pala": {"es": "Altura de pala", "en": "Blade height"},
    "especificacion_fila_peso": {"es": "Peso", "en": "Weight"},
    "especificacion_fila_cimentacion": {"es": "Cimentación requerida", "en": "Foundation required"},
    "especificacion_fila_capacidad_controlador": {
        "es": "Capacidad del controlador/inversor incluido",
        "en": "Included controller/inverter capacity",
    },
    "especificacion_col_especificacion": {"es": "Especificación", "en": "Specification"},
    "especificacion_col_valor": {"es": "Valor", "en": "Value"},
    "especificacion_caption_fuente": {
        "es": "Fuente de los datos: fichas técnicas oficiales de fábrica de Flower Turbines.",
        "en": "Data source: official Flower Turbines factory technical datasheets.",
    },
    "especificacion_subheader_informe": {"es": "### Informe ejecutivo", "en": "### Executive report"},
    "especificacion_caption_informe_resumen": {
        "es": ("Resumen de las 6 pestañas -- clima, equipos, producción y viabilidad "
               "financiera (si ya la completaste) -- en un solo PDF listo para imprimir o "
               "enviar al cliente."),
        "en": ("Summary of all 6 tabs -- climate, equipment, production and financial "
               "viability (if you already completed it) -- in a single PDF ready to print or "
               "send to the client."),
    },
    "especificacion_boton_generar_pdf": {
        "es": "Generar informe ejecutivo (PDF)",
        "en": "Generate executive report (PDF)",
    },
    "especificacion_spinner_generando": {
        "es": "Armando el informe ejecutivo...",
        "en": "Building the executive report...",
    },
    "especificacion_pdf_fuente_estacion": {
        "es": ("Estación real: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, lon={lon}, "
               "elevación={elevacion_m}m. Media anual real: {media} m/s."),
        "en": ("Real station: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, lon={lon}, "
               "elevation={elevacion_m}m. Real annual average: {media} m/s."),
    },
    "especificacion_pdf_fuente_generico": {
        "es": "Media anual real del viento en el sitio: {media} m/s.",
        "en": "Real annual average wind speed at the site: {media} m/s.",
    },
    "especificacion_error_generar_pdf": {
        "es": ("No se pudo generar el informe ejecutivo: {error} -- si el problema persiste, "
               "puede ser que falte un navegador Chrome/Chromium instalado en este entorno "
               "(hace falta para exportar los gráficos al PDF)."),
        "en": ("Could not generate the executive report: {error} -- if the problem persists, "
               "a Chrome/Chromium browser may be missing in this environment (needed to "
               "export the charts to the PDF)."),
    },
    "especificacion_caption_informe_sin_financiero": {
        "es": ("El informe no incluye CAPEX/Payback/ROI/NPV -- completá el precio de venta y "
               "la tarifa eléctrica en \"Análisis Financiero\" y volvé a generar el informe "
               "para sumarlos."),
        "en": ("The report doesn't include CAPEX/Payback/ROI/NPV -- fill in the sale price and "
               "electricity rate in \"Financial analysis\" and regenerate the report to add "
               "them."),
    },
    "especificacion_boton_descargar_pdf": {
        "es": "📄 Descargar informe ejecutivo (PDF)",
        "en": "📄 Download executive report (PDF)",
    },

    # --- Unidades sueltas reutilizadas en varios metric() -------------------------------
    "unidad_por_anio": {"es": "/año", "en": "/year"},

    # --- engine/pdf_reporte.py: generar_pdf_informe_ejecutivo() ------------------------
    # (no depende de sesión de Streamlit -- usa tr(clave, idioma, **kwargs), idioma
    # pasado explícito desde app.py al momento de generar el PDF)
    "pdf_titulo_informe": {"es": "Informe Ejecutivo", "en": "Executive Report"},
    "pdf_subtitulo": {
        "es": "Propuesta de microgeneración eólica -- {sitio} -- generado el {fecha}",
        "en": "Wind micro-generation proposal -- {sitio} -- generated on {fecha}",
    },
    "pdf_intro": {
        "es": ("Este informe resume la propuesta técnica y financiera de microgeneración "
               "eólica para <b>{sitio}</b>, calculada a partir de datos climáticos reales "
               "(EPW de la estación elegida) y especificaciones oficiales de fábrica de los "
               "equipos Flower Turbines."),
        "en": ("This report summarizes the technical and financial wind micro-generation "
               "proposal for <b>{sitio}</b>, calculated from real climate data (EPW of the "
               "chosen station) and Flower Turbines' official factory specifications."),
    },
    "pdf_kpi_potencia_pico": {"es": "Potencia pico instalada", "en": "Installed peak power"},
    "pdf_kpi_energia_anual": {"es": "Energía anual estimada", "en": "Estimated annual energy"},
    "pdf_kpi_turbinas_totales": {"es": "Turbinas totales", "en": "Total turbines"},
    "pdf_kpi_elevacion": {"es": "Elevación del sitio", "en": "Site elevation"},
    "pdf_kpi_capex_venta": {"es": "CAPEX (precio de venta)", "en": "CAPEX (sale price)"},
    "pdf_kpi_payback": {"es": "Payback", "en": "Payback"},
    "pdf_kpi_roi": {"es": "ROI (vida útil)", "en": "ROI (useful life)"},
    "pdf_kpi_viabilidad_economica": {"es": "Viabilidad económica", "en": "Economic viability"},
    "pdf_valor_anos": {"es": "{val} años", "en": "{val} years"},
    "pdf_na": {"es": "N/A", "en": "N/A"},
    "pdf_viable": {"es": "VIABLE", "en": "VIABLE"},
    "pdf_a_evaluar": {"es": "A EVALUAR", "en": "TO BE EVALUATED"},
    "pdf_seccion_contexto_climatico": {"es": "Contexto Climático", "en": "Climate Context"},
    "pdf_caption_rosa": {
        "es": "Rosa de vientos -- % de horas por dirección y velocidad",
        "en": "Wind rose -- % of hours by direction and speed",
    },
    "pdf_caption_heatmap": {
        "es": "Velocidad media del viento por mes y hora del día",
        "en": "Average wind speed by month and hour of day",
    },
    "pdf_caption_perfil": {
        "es": "Perfil logarítmico de viento -- velocidad real según la altura de instalación",
        "en": "Logarithmic wind profile -- real speed by installation height",
    },
    "pdf_seccion_equipos": {"es": "Equipos Configurados", "en": "Configured Equipment"},
    "pdf_texto_bus_dc": {
        "es": ("Bus de corriente continua a {voltaje}V -- cada turbina entrega su salida a "
               "través de un controlador individual de fábrica; todos los controladores se "
               "conectan en paralelo al mismo bus."),
        "en": ("{voltaje}V DC bus -- each turbine delivers its output through an individual "
               "factory controller; all controllers connect in parallel to the same bus."),
    },
    "pdf_turbina_titulo_cantidad": {"es": "{nombre} -- cantidad: {cantidad}", "en": "{nombre} -- quantity: {cantidad}"},
    "pdf_caption_fabricante": {
        "es": "Fabricante: Flower Turbines -- N° de parte: {numero_parte}",
        "en": "Manufacturer: Flower Turbines -- Part number: {numero_parte}",
    },
    "pdf_seccion_resultados": {"es": "Resultados de Producción", "en": "Production Results"},
    "pdf_kpi_produccion_anual": {"es": "Producción anual total", "en": "Total annual production"},
    "pdf_kpi_correccion_densidad": {
        "es": "Corrección por densidad (elevación)",
        "en": "Density correction (elevation)",
    },
    "pdf_valor_pct_menos": {"es": "{pct}% menos", "en": "{pct}% less"},
    "pdf_col_modelo": {"es": "Modelo", "en": "Model"},
    "pdf_col_n": {"es": "N", "en": "N"},
    "pdf_col_buje": {"es": "Buje (m)", "en": "Hub (m)"},
    "pdf_col_kwh_anio": {"es": "kWh/año", "en": "kWh/year"},
    "pdf_col_v_media_buje": {"es": "V. media buje (m/s)", "en": "Avg. hub speed (m/s)"},
    "pdf_col_pct_bajo_cutin": {"es": "% bajo cut-in", "en": "% below cut-in"},
    "pdf_caption_mensual": {
        "es": "Producción mensual (todos los clústers)",
        "en": "Monthly output (all clusters)",
    },
    "pdf_caption_duracion": {
        "es": "Curva de duración -- resolución horaria completa",
        "en": "Duration curve -- full hourly resolution",
    },
    "pdf_caption_viento": {
        "es": "Desglose de producción por velocidad de viento",
        "en": "Production breakdown by wind speed",
    },
    "pdf_texto_validado": {
        "es": ("Cálculo validado con datos de campo, con corrección por densidad de aire "
               "según elevación. Fuente climática: EPW real de la estación elegida o subida "
               "por el usuario."),
        "en": ("Calculation validated with field data, with air-density correction by "
               "elevation. Climate source: real EPW from the chosen station or the one "
               "uploaded by the user."),
    },
    "pdf_seccion_financiero": {"es": "Análisis Financiero", "en": "Financial Analysis"},
    "pdf_kpi_capex": {"es": "CAPEX", "en": "CAPEX"},
    "pdf_kpi_ahorro_anual": {"es": "Ahorro anual", "en": "Annual savings"},
    "pdf_kpi_mantenimiento_anual": {"es": "Mantenimiento anual", "en": "Annual maintenance"},
    "pdf_kpi_npv": {"es": "NPV", "en": "NPV"},
    "pdf_kpi_viabilidad": {"es": "Viabilidad", "en": "Viability"},
    "pdf_fila_modalidad_tarifa": {"es": "Modalidad de tarifa eléctrica", "en": "Electricity rate mode"},
    "pdf_fila_vida_util": {"es": "Vida útil del proyecto", "en": "Project useful life"},
    "pdf_fila_tasa_descuento": {"es": "Tasa de descuento (NPV)", "en": "Discount rate (NPV)"},
    "pdf_texto_footer_financiero": {
        "es": ("CAPEX, mantenimiento y precio de venta ingresados directo por el usuario en "
               "la app. Tarifas horarias reales de CNFL/ICE cruzadas contra la producción "
               "hora por hora cuando corresponde, en vez de una tarifa plana adivinada."),
        "en": ("CAPEX, maintenance and sale price entered directly by the user in the app. "
               "Real CNFL/ICE hourly rates crossed against hour-by-hour production when "
               "applicable, instead of a guessed flat rate."),
    },
    "pdf_caja_sin_financiero": {
        "es": ("Completá el precio de venta al cliente y la tarifa eléctrica en la pestaña "
               "\"Análisis Financiero\" de la app para incluir acá el CAPEX, Payback, ROI y "
               "NPV de este proyecto."),
        "en": ("Fill in the sale price to the client and the electricity rate in the "
               "\"Financial analysis\" tab of the app to include the CAPEX, Payback, ROI and "
               "NPV of this project here."),
    },
    "pdf_col_especificacion": {"es": "Especificación", "en": "Specification"},
    "pdf_col_valor": {"es": "Valor", "en": "Value"},
    "pdf_pie_copyright": {"es": "© {anio} ECO Consultor", "en": "© {anio} ECO Consultor"},
    "pdf_pie_titulo": {"es": "Informe Ejecutivo -- ECO | Wind", "en": "Executive Report -- ECO | Wind"},
    "pdf_pie_pagina": {"es": "Página {n}", "en": "Page {n}"},

    # --- engine/pdf_reporte.py: generar_pdf_lista_precios() (no llamado desde la app hoy,
    # se traduce igual por completitud del módulo) --------------------------------------
    "pdf_precios_titulo": {
        "es": "Lista de Precios de Referencia -- Turbinas Flower Turbines",
        "en": "Reference Price List -- Flower Turbines Turbines",
    },
    "pdf_precios_subtitulo": {
        "es": "ECO | Wind -- Simulador de microgeneración eólica -- generado el {fecha}",
        "en": "ECO | Wind -- Wind micro-generation simulator -- generated on {fecha}",
    },
    "pdf_precios_intro": {
        "es": ("Precio final = (costo de fábrica + flete estimado por unidad) &times; 1.30 "
               "de margen comercial. El flete asume pedir lo suficiente para llenar 1 pallet "
               "o 1 contenedor completo (lo que salga más barato por unidad) -- tarifas de "
               "mercado ($2,000 unidad / $3,500 pallet / $10,000 contenedor de 40'), NO una "
               "cotización de un forwarder real. Usar como orden de magnitud para el cliente, "
               "confirmar antes de cotizar en firme."),
        "en": ("Final price = (factory cost + estimated freight per unit) &times; 1.30 "
               "commercial margin. Freight assumes ordering enough to fill 1 pallet or 1 full "
               "container (whichever is cheaper per unit) -- market rates ($2,000 unit / "
               "$3,500 pallet / $10,000 40' container), NOT a real forwarder quote. Use as an "
               "order-of-magnitude figure for the client, confirm before quoting firmly."),
    },
    "pdf_precios_seccion_verificados": {
        "es": "Modelos con costo de fábrica verificado",
        "en": "Models with verified factory cost",
    },
    "pdf_precios_seccion_no_verificados": {
        "es": "Modelos con costo de fábrica NO verificado",
        "en": "Models with UNVERIFIED factory cost",
    },
    "pdf_precios_aviso_no_verificados": {
        "es": ("Vienen de una respuesta de chat tipo \"representante de Flower Turbines\", no "
               "de una cotización real -- usar sólo como referencia interna, no repetirlos "
               "como precio firme frente al cliente."),
        "en": ("These come from a chat response along the lines of a \"Flower Turbines "
               "representative\", not a real quote -- use only as internal reference, don't "
               "repeat them as a firm price to the client."),
    },
    "pdf_precios_col_modelo": {"es": "Modelo", "en": "Model"},
    "pdf_precios_col_costo_fabrica": {"es": "Costo fábrica", "en": "Factory cost"},
    "pdf_precios_col_flete": {"es": "Flete/unidad (est.)", "en": "Freight/unit (est.)"},
    "pdf_precios_col_precio_final": {"es": "Precio final (est.)", "en": "Final price (est.)"},
    "pdf_precios_col_fuente": {"es": "Fuente del costo", "en": "Cost source"},
    "pdf_precios_verificado": {"es": "Verificado", "en": "Verified"},
    "pdf_precios_no_verificado": {"es": "No verificado", "en": "Not verified"},
    "pdf_precios_nd": {"es": "N/D", "en": "N/A"},
    "pdf_precios_doc_titulo": {"es": "Lista de precios -- ECO | Wind", "en": "Price list -- ECO | Wind"},
    "pdf_precios_footer": {
        "es": ("Fuente de los datos: fichas técnicas oficiales de fábrica (Flower Turbines) "
               "para el costo base, `engine/price_calculator.py` para el flete y margen. ECO "
               "Consultor -- Energy Conservation Opportunities."),
        "en": ("Data source: official factory technical datasheets (Flower Turbines) for the "
               "base cost, `engine/price_calculator.py` for freight and margin. ECO Consultor "
               "-- Energy Conservation Opportunities."),
    },

    # --- Eco-Roof Energy Hub como producto de la cartera (selector "Modelo" de "Equipos y --
    # --- configuración", Especificación Técnica e informe PDF del proyecto) -----------------
    "equipos_label_n_equipos": {"es": "Equipos (N)", "en": "Units (N)"},
    "equipos_help_n_equipos": {
        "es": ("Cantidad de equipos Eco-Roof, no de turbinas sueltas: cada equipo ya trae su "
               "bouquet fijo de fábrica (3 o 5 turbinas Small Tulip de 1m) y se cotiza por "
               "unidad."),
        "en": ("Number of Eco-Roof units, not individual turbines: each unit already comes "
               "with its fixed factory bouquet (3 or 5 Small Tulip 1m turbines) and is priced "
               "per unit."),
    },
    "equipos_label_altura_techo": {"es": "Altura del techo (m)", "en": "Roof height (m)"},
    "equipos_help_altura_techo": {
        "es": ("Altura del techo sobre el terreno donde se instala el Eco-Roof. El buje queda a "
               "esta altura + 1.149 m (altura de pala del Small Tulip), y el viento se lleva a "
               "esa altura con el mismo perfil logarítmico que el resto de las turbinas. "
               "Aproximación: no modela la aceleración ni la turbulencia del flujo sobre el "
               "borde del edificio."),
        "en": ("Height of the roof above ground where the Eco-Roof is installed. The hub sits "
               "at this height + 1.149 m (Small Tulip blade height), and the wind is brought to "
               "that height with the same logarithmic profile used for the other turbines. "
               "Approximation: it does not model flow acceleration or turbulence over the "
               "building edge."),
    },
    "equipos_caption_buje_ecoroof": {
        "es": "Buje a {buje} m sobre el terreno (techo {techo} m + 1.149 m del equipo).",
        "en": "Hub at {buje} m above ground (roof {techo} m + 1.149 m of the unit).",
    },
    "equipos_caption_ecoroof_solar_si": {
        "es": ("Incluye paneles solares ({w} W por equipo): su producción se simula con "
               "EnergyPlus y se suma al proyecto."),
        "en": ("Includes solar panels ({w} W per unit): their output is simulated with "
               "EnergyPlus and added to the project."),
    },
    "equipos_caption_ecoroof_solar_no": {
        "es": "El artículo elegido no trae paneles solares: esta fila produce sólo energía eólica.",
        "en": "The chosen item has no solar panels: this row produces wind energy only.",
    },
    "ecoroof_spinner_solar": {
        "es": "Simulando producción solar con EnergyPlus real (puede tardar unos segundos)...",
        "en": "Simulating solar output with real EnergyPlus (this can take a few seconds)...",
    },
    "resultados_error_simulacion": {
        "es": "No se pudo simular la producción del proyecto: {error}",
        "en": "Could not simulate the project's output: {error}",
    },
    "resultados_col_kwh_eolico": {"es": "kWh/año eólico", "en": "Wind kWh/year"},
    "resultados_col_kwh_solar": {"es": "kWh/año solar", "en": "Solar kWh/year"},
    "resultados_caption_ecoroof": {
        "es": ("Eco-Roof: N es la cantidad de equipos (cada uno con 3 o 5 turbinas) y el buje "
               "es la altura del techo + 1.149 m. Su producción eólica sale de la tabla oficial "
               "de fábrica del producto (no del multiplicador Bouquet), sin recorte por "
               "electrónica, y la solar se suma sólo si el artículo elegido trae paneles. La "
               "curva de duración y el desglose por velocidad de viento muestran sólo la parte "
               "eólica."),
        "en": ("Eco-Roof: N is the number of units (each with 3 or 5 turbines) and the hub is "
               "the roof height + 1.149 m. Its wind output comes from the product's official "
               "factory table (not the Bouquet multiplier), with no electronics clipping, and "
               "solar is added only if the chosen item includes panels. The duration curve and "
               "the wind-speed breakdown show the wind part only."),
    },
    "especificacion_fila_turbinas_por_equipo": {
        "es": "Turbinas Small Tulip (1m) por equipo", "en": "Small Tulip (1m) turbines per unit",
    },
    "especificacion_fila_potencia_tabla": {
        "es": "Potencia por turbina (tabla oficial)", "en": "Power per turbine (official table)",
    },
    "especificacion_valor_potencia_tabla": {
        "es": "{w5} W a 5 m/s · {w11} W a 11 m/s · {w15} W a 15 m/s",
        "en": "{w5} W at 5 m/s · {w11} W at 11 m/s · {w15} W at 15 m/s",
    },
    "especificacion_valor_sin_solar": {
        "es": "No incluida en el artículo elegido", "en": "Not included in the chosen item",
    },
    "pdf_ecoroof_texto_preconfigurado": {
        "es": ("Producto preconfigurado de fábrica: cada equipo trae su bouquet fijo de turbinas "
               "Small Tulip (1m) y, según el artículo, paneles solares. La cantidad indicada es "
               "de equipos, no de turbinas sueltas."),
        "en": ("Preconfigured factory product: each unit comes with its fixed bouquet of Small "
               "Tulip (1m) turbines and, depending on the item, solar panels. The quantity shown "
               "is in units, not individual turbines."),
    },
    "pdf_ecoroof_fila_tipo_techo": {"es": "Tipo de instalación", "en": "Installation type"},
    "pdf_ecoroof_techo_plano": {"es": "Techo plano", "en": "Flat roof"},
    "pdf_ecoroof_techo_inclinado": {"es": "Techo inclinado", "en": "Slanted roof"},
    "pdf_ecoroof_fila_iec": {"es": "Clase IEC 61400 (turbina)", "en": "IEC 61400 class (turbine)"},
    "pdf_ecoroof_fila_peso": {"es": "Peso transmitido al techo", "en": "Weight transmitted to roof"},
    "pdf_ecoroof_fila_angulo_max": {"es": "Ángulo máximo de techo", "en": "Maximum roof angle"},
    "pdf_ecoroof_fila_capacidad_solar": {"es": "Paneles solares por equipo", "en": "Solar panels per unit"},
    "pdf_ecoroof_nota_potencia": {
        "es": ("La \"potencia nominal\" de fábrica no es un solo número representativo -- crece "
               "con la velocidad de viento igual que cualquier turbina. Se muestra la tabla "
               "oficial completa (no una fórmula genérica) en vez de un solo valor que "
               "mezclaría, sin decirlo, la capacidad del controlador con la del generador."),
        "en": ("Factory \"rated power\" is not a single representative number -- it grows with "
               "wind speed like any turbine. The full official table is shown (not a generic "
               "formula) instead of a single value that would silently mix controller capacity "
               "with generator output."),
    },
    "pdf_ecoroof_tabla_potencia_titulo": {
        "es": "Potencia por turbina según velocidad de viento (tabla oficial de fábrica)",
        "en": "Power per turbine by wind speed (official factory table)",
    },
    "pdf_ecoroof_col_velocidad": {"es": "Viento (m/s)", "en": "Wind (m/s)"},
    "pdf_ecoroof_col_potencia": {"es": "Potencia/turbina (W)", "en": "Power/turbine (W)"},
    "pdf_ecoroof_caja_advertencia_solar": {
        "es": ("PRODUCCIÓN SOLAR ESTIMADA: simulación real con el motor EnergyPlus 23.2 "
               "(generador Generator:PVWatts, vía Honeybee) hora por hora contra el EPW del "
               "sitio, pero con un panel GENÉRICO (eficiencia, área activa y pérdidas de sistema "
               "tipo PVWatts/NREL) -- no hay todavía una ficha de panel Eco-Roof específica de "
               "fábrica. No usar como cotización firme, sólo como orden de magnitud."),
        "en": ("ESTIMATED SOLAR OUTPUT: real hour-by-hour simulation with the EnergyPlus 23.2 "
               "engine (Generator:PVWatts, via Honeybee) against the site's EPW, but with a "
               "GENERIC panel (efficiency, active area and system losses per PVWatts/NREL "
               "defaults) -- no factory-specific Eco-Roof panel datasheet exists yet. Do not use "
               "as a firm quote, only as an order-of-magnitude estimate."),
    },

    # Nombres de los productos Eco-Roof en la cartera -- por clave de preset
    # (engine/eco_roof_catalog.py::ECO_ROOF_PRESETS), resueltos por idioma.
    "ecoroof_nombre_eco_roof_1m_3_flat": {
        "es": "Eco-Roof Energy Hub -- Flat, 3 turbinas", "en": "Eco-Roof Energy Hub -- Flat, 3 turbines",
    },
    "ecoroof_nombre_eco_roof_1m_5_flat": {
        "es": "Eco-Roof Energy Hub -- Flat, 5 turbinas", "en": "Eco-Roof Energy Hub -- Flat, 5 turbines",
    },
    "ecoroof_nombre_eco_roof_1m_3_sloped": {
        "es": "Eco-Roof Energy Hub -- Techo inclinado, 3 turbinas",
        "en": "Eco-Roof Energy Hub -- Slanted roof, 3 turbines",
    },
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
