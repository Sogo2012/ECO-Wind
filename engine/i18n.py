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

    # --- Tab: Selección de clima (sitio, estaciones, EPW propio) --------------------
    "clima_caption_intro": {
        "es": ("Pega las coordenadas de tu sitio (ej: 9.999665, -84.123064). El sistema busca "
               "las estaciones climáticas reales más cercanas -- elegí una de la lista, o subí "
               "directo el EPW que quieras usar como referencia."),
        "en": ("Paste your site's coordinates (e.g., 9.999665, -84.123064). The system looks up "
               "the nearest real weather stations -- pick one from the list, or upload directly "
               "the EPW file you want to use as a reference."),
    },
    "clima_spinner_buscando": {
        "es": "Buscando estaciones cercanas...",
        "en": "Searching for nearby weather stations...",
    },
    "clima_error_sin_estaciones": {
        "es": "No se encontraron estaciones para esta ubicación.",
        "en": "No weather stations were found for this location.",
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
        "en": "Format: latitude, longitude (e.g., 9.999, -84.123)",
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
        "en": "**Nearest weather stations:**",
    },
    "clima_estacion_fila": {
        "es": "**{nombre}** — {estado} ({distancia} km)",
        "en": "**{nombre}** — {estado} ({distancia} km)",
    },
    "clima_boton_usar": {"es": "Usar", "en": "Use"},
    "clima_caption_estacion_lejana": {
        "es": ("La estación real más cercana está a {distancia} km -- si tenés el EPW real de "
               "un sitio más representativo (propio o de otro lugar), subilo abajo en vez de "
               "usar una estación tan lejana."),
        "en": ("The nearest real weather station is {distancia} km away -- if you have the real "
               "EPW file for a more representative site (your own or elsewhere), upload it below "
               "instead of using such a distant station."),
    },
    "clima_caption_epw_pregunta": {
        "es": "**¿Tenés el EPW real de tu sitio (o de otro lugar que quieras usar como referencia)?**",
        "en": "**Do you have the real EPW file for your site (or another location you want to use as a reference)?**",
    },
    "clima_uploader_epw_label": {"es": "Subir archivo .epw", "en": "Upload .epw file"},
    "clima_boton_usar_epw": {"es": "Usar este EPW", "en": "Use this EPW file"},
    "clima_epw_subido_nombre": {
        "es": "EPW subido -- {nombre}",
        "en": "Uploaded EPW -- {nombre}",
    },

    # --- Sección: tab_contexto (Contexto climático) ---
    "contexto_info_elegir_sitio": {
        "es": "Elegí primero un sitio en la pestaña \"Selección de clima\" para ver su contexto climático.",
        "en": "First choose a site in the \"Weather selection\" tab to see its climate context.",
    },
    "contexto_success_estacion_real": {
        "es": ("Estación real: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, lon={lon}, "
               "elevación={elevacion}m. Media anual real (10m): {media} m/s."),
        "en": ("Real weather station: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, lon={lon}, "
               "elevation={elevacion}m. Real annual average (10m): {media} m/s."),
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
        "en": ("Move this height to see how the actual wind speed changes (heatmap and profile "
               "below) between the EPW reference height (10m) and your turbine's real hub "
               "height -- same formula and roughness used in the energy calculation. For a "
               "ROOFTOP installation, use building height + mast height above the roof -- note "
               "that the logarithmic profile extrapolates the REGIONAL wind speed to that "
               "height, not the local aerodynamic effect of sitting atop a specific building "
               "(acceleration over the roof edge, turbulence)."),
    },
    "contexto_caption_rugosidad_destino": {
        "es": ("Rugosidad de destino usada abajo: z0={z0} m -- configurable en "
               "\"Equipos y configuración\" > Parámetros avanzados."),
        "en": ("Target roughness used below: z0={z0} m -- configurable in "
               "\"Equipment & configuration\" > Advanced parameters."),
    },

    # --- Sección: tab_config (Equipos y configuración) ---
    "equipos_subheader_clusters": {
        "es": "Clústers del proyecto",
        "en": "Project clusters",
    },
    "equipos_label_modelo": {"es": "Modelo", "en": "Model"},
    "equipos_label_cantidad": {"es": "N", "en": "N"},
    "equipos_label_altura_buje": {
        "es": "Buje (m)",
        "en": "Hub height (m)",
    },
    "equipos_help_altura_buje": {
        "es": ("Para una instalación en TECHO (ej. azotea de un edificio de varios pisos): "
               "altura del edificio (m) + altura del mástil/soporte sobre el techo -- NO la "
               "cantidad de pisos. Un edificio de 15 pisos ronda 45-55m según la altura de "
               "entrepiso."),
        "en": ("For a ROOFTOP installation (e.g., the roof of a multi-story building): "
               "building height (m) + mast/support height above the roof -- NOT the "
               "number of floors. A 15-story building is roughly 45-55 m depending on "
               "floor-to-floor height."),
    },
    "equipos_help_quitar_cluster": {
        "es": "Quitar este clúster",
        "en": "Remove this cluster",
    },
    "equipos_expander_ficha_tecnica": {
        "es": "Ficha técnica -- {modelo}",
        "en": "Technical datasheet -- {modelo}",
    },
    "equipos_caption_sin_ficha": {
        "es": "Sin ficha técnica cargada todavía para este modelo.",
        "en": "No technical datasheet loaded yet for this model.",
    },
    "equipos_caption_sin_imagen": {
        "es": "Sin imagen todavía.",
        "en": "No image yet.",
    },
    "equipos_caption_numero_parte": {
        "es": "N° de parte: {parte} -- {clase}",
        "en": "Part number: {parte} -- {clase}",
    },
    "equipos_ficha_specs_markdown": {
        "es": ("- **Potencia nominal:** {potencia_w} W a {viento_ms} m/s\n"
               "- **Cut-in / supervivencia:** {cutin_ms} m/s / {supervivencia_ms} m/s\n"
               "- **Generador:** {generador} ({polos} polos)\n"
               "- **Salida:** {voltaje}\n"
               "- **Dimensiones:** {altura_total} m altura total, {diametro_rotor} m "
               "diámetro de rotor, {peso} kg\n"
               "- **Vida de diseño:** {vida_anos} años\n"
               "- **Cimentación requerida:** {cimentacion}"),
        "en": ("- **Rated power:** {potencia_w} W at {viento_ms} m/s\n"
               "- **Cut-in / survival speed:** {cutin_ms} m/s / {supervivencia_ms} m/s\n"
               "- **Generator:** {generador} ({polos} poles)\n"
               "- **Output:** {voltaje}\n"
               "- **Dimensions:** {altura_total} m total height, {diametro_rotor} m "
               "rotor diameter, {peso} kg\n"
               "- **Design life:** {vida_anos} years\n"
               "- **Required foundation:** {cimentacion}"),
    },
    "equipos_boton_agregar_cluster": {
        "es": "+ Agregar clúster",
        "en": "+ Add cluster",
    },
    "equipos_expander_parametros_avanzados": {
        "es": "Parámetros avanzados",
        "en": "Advanced parameters",
    },
    "equipos_label_z0": {
        "es": "Rugosidad DEL SITIO donde va la turbina (z0)",
        "en": "Terrain roughness AT THE TURBINE SITE (z0)",
    },
    "equipos_help_z0": {
        "es": ("Rugosidad del sitio DESTINO (donde se instala la turbina), no la del sitio "
               "de referencia climática -- son dos valores distintos (ver el detalle en "
               "\"Resultados\")."),
        "en": ("Roughness of the DESTINATION site (where the turbine will be installed), "
               "not the climate reference site -- these are two different values (see the "
               "details in \"Results\")."),
    },
    "equipos_z0_campo_abierto": {
        "es": "0.03 — campo abierto",
        "en": "0.03 — open country",
    },
    "equipos_z0_cultivos_bajos": {
        "es": "0.1 — cultivos bajos",
        "en": "0.1 — low crops",
    },
    "equipos_z0_suburbano": {
        "es": "0.3 — suburbano (default)",
        "en": "0.3 — suburban (default)",
    },
    "equipos_z0_urbano_denso": {
        "es": "1.0 — urbano denso",
        "en": "1.0 — dense urban",
    },
    "equipos_label_metodo_bouquet": {
        "es": "Modelo de Efecto Bouquet",
        "en": "Bouquet Effect model",
    },
    "equipos_bouquet_real": {
        "es": "Real (exponencial, validado R²≥0.999996)",
        "en": "Real (exponential, validated R²≥0.999996)",
    },
    "equipos_bouquet_lineal": {
        "es": "Lineal de marketing (solo referencia, subestima fuerte)",
        "en": "Marketing linear (reference only, strongly underestimates)",
    },
    "equipos_warning_elegir_sitio": {
        "es": "Elegí un sitio en la pestaña \"Selección de clima\" antes de calcular.",
        "en": "Select a site in the \"Climate selection\" tab before calculating.",
    },
    "equipos_boton_calcular": {
        "es": "Calcular producción del proyecto",
        "en": "Calculate project output",
    },

    # --- Tab: Resultados -----------------------------------------------------------
    "resultados_caption_intro": {
        "es": "Producción de energía del proyecto -- el cálculo financiero (CAPEX, tarifa "
              "eléctrica, payback) está en la pestaña \"{tab}\".",
        "en": "Project energy output -- the financial calculation (CAPEX, electricity rate, "
              "payback) is in the \"{tab}\" tab.",
    },
    "resultados_error_sin_estacion": {
        "es": "Elegí primero una estación (o subí un EPW) en la pestaña \"{tab}\".",
        "en": "First select a weather station (or upload an EPW file) in the \"{tab}\" tab.",
    },
    "resultados_metric_produccion_anual": {
        "es": "Producción anual total",
        "en": "Total annual output",
    },
    "resultados_metric_turbinas_totales": {
        "es": "Turbinas totales",
        "en": "Total turbines",
    },
    "resultados_metric_correccion_densidad": {
        "es": "Corrección por densidad (elevación)",
        "en": "Air-density correction (elevation)",
    },
    "resultados_metric_correccion_densidad_valor": {
        "es": "{pct}% menos",
        "en": "{pct}% less",
    },
    "resultados_metric_altura_buje": {
        "es": "Altura de buje",
        "en": "Hub height",
    },
    "resultados_subtitulo_detalle_cluster": {
        "es": "**Detalle por clúster**",
        "en": "**Cluster detail**",
    },
    "resultados_col_modelo": {"es": "Modelo", "en": "Model"},
    "resultados_col_n": {"es": "N", "en": "N"},
    "resultados_col_buje": {"es": "Buje (m)", "en": "Hub (m)"},
    "resultados_col_kwh_anio": {"es": "kWh/año", "en": "kWh/yr"},
    "resultados_col_v_media_buje": {
        "es": "V. medio buje (m/s)",
        "en": "Avg. hub wind speed (m/s)",
    },
    "resultados_col_pct_bajo_cutin": {
        "es": "% bajo cut-in",
        "en": "% below cut-in",
    },
    "resultados_expander_perfil_viento_titulo": {
        "es": "Perfil de viento por altura: dos rugosidades, y una verificación independiente",
        "en": "Wind profile by height: two roughness values, and an independent cross-check",
    },
    "resultados_texto_perfil_viento_intro": {
        "es": "El viento de referencia (10m, aeropuerto/EPW) y el sitio real donde va la "
              "turbina casi nunca tienen la misma rugosidad. Por eso esta app usa el z0 del "
              "sitio destino (seleccionable arriba en esta pestaña) **distinto** del z0 de "
              "referencia (0.1, clase \"country\"/aeropuerto -- fórmula logarítmica).",
        "en": "The reference wind speed (10m, airport/EPW) and the actual site where the "
              "turbine will be installed almost never share the same terrain roughness. "
              "That's why this app uses the destination site's z0 (selectable above, in this "
              "tab) **different** from the reference z0 (0.1, \"country\"/airport class -- "
              "logarithmic formula).",
    },
    "resultados_texto_verificacion_independiente": {
        "es": "**Verificación independiente** (ley de potencia que usa EnergyPlus por "
              "defecto, misma tabla de terrenos que ladybug-tools/ladybug, con el mismo "
              "**z0={z0}** elegido arriba -- internamente la clase con ese z0 tabulado se "
              "llama \"{terreno}\" en la tabla original de EnergyPlus, aunque ese nombre "
              "interno no siempre coincide con las etiquetas de esta app): {v_pot} m/s a "
              "{altura_buje}m de buje, vs. **{v_hub_medio} m/s** con la fórmula logarítmica "
              "usada arriba -- {conclusion}.",
        "en": "**Independent cross-check** (power law used by EnergyPlus by default, same "
              "terrain table as ladybug-tools/ladybug, with the same **z0={z0}** selected "
              "above -- internally the class for that tabulated z0 is called \"{terreno}\" "
              "in the original EnergyPlus table, though that internal name does not always "
              "match this app's own labels): {v_pot} m/s at {altura_buje}m hub height, vs. "
              "**{v_hub_medio} m/s** from the logarithmic formula used above -- {conclusion}.",
    },
    "resultados_texto_verificacion_concuerda": {
        "es": "concuerdan razonablemente",
        "en": "agree reasonably well",
    },
    "resultados_texto_verificacion_discrepa": {
        "es": "difieren más de lo esperado, revisar",
        "en": "differ more than expected, review",
    },
    "resultados_expander_horario_titulo": {
        "es": "¿Por qué el cálculo es hora por hora, y no con la velocidad media?",
        "en": "Why is the calculation done hour-by-hour, rather than using the mean wind speed?",
    },
    "resultados_texto_metodo_horario": {
        "es": "Para el primer clúster: método correcto (P=k·v³ en cada una de las 8.760 "
              "horas) = **{kwh_correcto} kWh/año**. Método ingenuo (P evaluada en la "
              "velocidad media {v_media} m/s, ×8.760 horas) = **{kwh_ingenuo} kWh/año** -- "
              "el método ingenuo subestima **{razon}x**. Es la desigualdad de Jensen (P∝v³ "
              "es convexa, E[v³]≥(E[v])³): con un recurso variable, nunca es válido "
              "sustituir la velocidad media directo en la fórmula de potencia.",
        "en": "For the first cluster: correct method (P=k·v³ for each of the 8,760 hours) = "
              "**{kwh_correcto} kWh/year**. Naive method (P evaluated at the mean wind speed "
              "{v_media} m/s, ×8,760 hours) = **{kwh_ingenuo} kWh/year** -- the naive method "
              "underestimates by **{razon}x**. This is Jensen's inequality (P∝v³ is convex, "
              "E[v³]≥(E[v])³): with a variable resource, it is never valid to plug the mean "
              "wind speed directly into the power formula.",
    },
    "resultados_caption_footer": {
        "es": "Cálculo validado con datos de campo, con corrección por densidad de aire "
              "según elevación. Fuente climática: EPW real de la estación elegida o subida "
              "por el usuario.",
        "en": "Calculation validated against field data, including air-density correction "
              "based on elevation. Weather data source: the actual EPW file for the "
              "selected station, or the one uploaded by the user.",
    },
    "resultados_info_configurar_primero": {
        "es": "Configurá el proyecto en la pestaña \"{tab}\" y presioná **{boton}**.",
        "en": "Set up the project in the \"{tab}\" tab, then click **{boton}**.",
    },

    # --- Sección: tab_financiero (Análisis Financiero) -----------------------------
    "financiero_caption_intro": {
        "es": "Viabilidad económica del proyecto (CAPEX, Payback, ROI, NPV) -- usa las "
              "turbinas ya configuradas en \"Equipos y configuración\" y la producción "
              "ya calculada en \"Resultados\".",
        "en": "Economic viability of the project (CAPEX, Payback, ROI, NPV) -- uses the "
              "turbines already configured in \"Equipment & configuration\" and the "
              "output already calculated in \"Results\".",
    },
    "financiero_toggle_modulo_activo": {
        "es": "Activar módulo financiero (viabilidad económica)",
        "en": "Enable financial module (economic viability)",
    },
    "financiero_toggle_modulo_activo_help": {
        "es": "Apagalo si por ahora sólo te interesa el dimensionamiento técnico "
              "(pestaña \"Especificación Técnica\") y no necesitás calcular "
              "CAPEX/Payback/ROI todavía.",
        "en": "Turn it off if for now you're only interested in the technical sizing "
              "(\"Technical specification\" tab) and don't need to calculate "
              "CAPEX/Payback/ROI yet.",
    },
    "financiero_info_modulo_desactivado": {
        "es": "Módulo financiero desactivado. Activá el switch de arriba para ingresar "
              "costos reales y calcular Payback, ROI, NPV y viabilidad económica.",
        "en": "Financial module disabled. Turn on the switch above to enter actual "
              "costs and calculate Payback, ROI, NPV, and economic viability.",
    },
    "financiero_info_configurar_primero": {
        "es": "Configurá el proyecto en la pestaña \"Equipos y configuración\" y "
              "presioná **Calcular producción del proyecto** primero.",
        "en": "Set up the project in the \"Equipment & configuration\" tab, then click "
              "**Calculate project output** first.",
    },
    "financiero_error_sin_estacion": {
        "es": "Elegí primero una estación (o subí un EPW) en la pestaña \"Selección de "
              "clima\".",
        "en": "Select a weather station first (or upload an EPW file) in the "
              "\"Climate selection\" tab.",
    },
    "financiero_titulo_tarifa_electrica": {
        "es": "Tarifa eléctrica",
        "en": "Electricity rate",
    },
    "financiero_opcion_tarifa_plana": {
        "es": "Tarifa plana (USD/kWh)",
        "en": "Flat rate (USD/kWh)",
    },
    "financiero_opcion_tarifa_horaria": {
        "es": "Tarifa horaria real de Costa Rica (ARESEP)",
        "en": "Costa Rica real-time hourly rate (ARESEP)",
    },
    "financiero_opcion_tarifa_comercial": {
        "es": "Tarifa comercial de Costa Rica (T-CO)",
        "en": "Costa Rica commercial rate (T-CO)",
    },
    "financiero_radio_modo_tarifa": {
        "es": "¿Cómo querés valorar el ahorro de electricidad?",
        "en": "How do you want to value the electricity savings?",
    },
    "financiero_radio_modo_tarifa_help": {
        "es": "La tarifa horaria cruza la producción REAL hora por hora de la turbina "
              "contra los periodos Punta/Valle/Nocturno de CNFL/ICE -- un kWh generado "
              "en horario Punta vale varias veces más que uno generado de noche, algo "
              "que una tarifa plana no puede reflejar. La tarifa comercial (T-CO) es "
              "para gimnasios/estadios/comercios -- precio plano por kWh según el "
              "consumo mensual del sitio, sin periodos horarios.",
        "en": "The hourly rate cross-references the turbine's ACTUAL hour-by-hour "
              "output against CNFL/ICE's Peak/Off-peak/Night periods -- a kWh "
              "generated during Peak hours is worth several times more than one "
              "generated at night, something a flat rate cannot reflect. The "
              "commercial rate (T-CO) is for gyms/stadiums/businesses -- a flat price "
              "per kWh based on the site's monthly consumption, with no time-of-use "
              "periods.",
    },
    "financiero_number_tarifa_plana": {
        "es": "Tarifa eléctrica ($/kWh)",
        "en": "Electricity rate ($/kWh)",
    },
    "financiero_selectbox_proveedor": {
        "es": "Proveedor",
        "en": "Utility provider",
    },
    "financiero_help_proveedor": {
        "es": "CNFL cubre el Gran Área Metropolitana; ICE el resto del país.",
        "en": "CNFL covers the Greater Metropolitan Area; ICE covers the rest of the "
              "country.",
    },
    "financiero_selectbox_consumo_mensual": {
        "es": "Consumo mensual del sitio",
        "en": "Site's monthly consumption",
    },
    "financiero_help_consumo_mensual": {
        "es": "Determina qué tarifa T-CO aplica -- gimnasios/estadios grandes "
              "normalmente caen en el tramo >3000 kWh/mes.",
        "en": "Determines which T-CO rate applies -- large gyms/stadiums typically "
              "fall into the >3000 kWh/month bracket.",
    },
    "financiero_opcion_tramo_pequeno": {
        "es": "≤ 3000 kWh/mes (sin medidor de potencia)",
        "en": "≤ 3000 kWh/month (no demand meter)",
    },
    "financiero_opcion_tramo_grande": {
        "es": "> 3000 kWh/mes (con medidor de potencia)",
        "en": "> 3000 kWh/month (with demand meter)",
    },
    "financiero_number_tipo_cambio": {
        "es": "Tipo de cambio (₡ por USD)",
        "en": "Exchange rate (₡ per USD)",
    },
    "financiero_help_tipo_cambio": {
        "es": "Precargado con el tipo de cambio de venta del día del Banco Central de "
              "Costa Rica (BCCR, ver sidebar) -- cambia a diario, es un punto de "
              "partida editable, no un valor fijo del sistema.",
        "en": "Pre-filled with today's selling exchange rate from the Central Bank of "
              "Costa Rica (BCCR, see sidebar) -- it changes daily; this is an editable "
              "starting point, not a fixed system value.",
    },
    "financiero_caption_tco_resultado": {
        "es": "Tarifa T-CO: ₡{precio}/kWh → \\${ahorro_usd}/año ({ahorro_crc} ₡/año).",
        "en": "T-CO rate: ₡{precio}/kWh → \\${ahorro_usd}/year ({ahorro_crc} ₡/year).",
    },
    "financiero_info_tco_sin_demanda": {
        "es": "Esta tarifa NO incluye el cargo por demanda máxima (kW) que T-CO "
              "también cobra en el tramo >3000 kWh -- calcularlo requeriría el perfil "
              "de demanda horaria del sitio (no sólo el consumo diario promedio) para "
              "saber si la turbina genera justo en el instante del pico. Este número "
              "es sólo el ahorro de energía, no el ahorro total de la factura.",
        "en": "This rate does NOT include the peak-demand charge (kW) that T-CO also "
              "bills in the >3000 kWh bracket -- calculating it would require the "
              "site's hourly demand profile (not just its average daily consumption) "
              "to know whether the turbine generates right at the peak instant. This "
              "figure is only the energy savings, not the total bill savings.",
    },
    "financiero_selectbox_tarifa": {
        "es": "Tarifa",
        "en": "Rate",
    },
    "financiero_help_tarifa": {
        "es": "T-REH/T-RH: residencial. T-MT: media tensión (proyectos más grandes).",
        "en": "T-REH/T-RH: residential. T-MT: medium voltage (larger projects).",
    },
    "financiero_caption_tou_resultado": {
        "es": "Tarifa efectiva ponderada por producción real: \\${tarifa}/kWh "
              "({ahorro_crc} ₡/año → \\${ahorro_usd}/año).",
        "en": "Effective rate weighted by actual output: \\${tarifa}/kWh "
              "({ahorro_crc} ₡/year → \\${ahorro_usd}/year).",
    },
    "financiero_col_periodo": {
        "es": "Periodo",
        "en": "Period",
    },
    "financiero_col_kwh_anio": {
        "es": "kWh/año",
        "en": "kWh/year",
    },
    "financiero_col_precio_crc_kwh": {
        "es": "Precio (₡/kWh)",
        "en": "Price (₡/kWh)",
    },
    "financiero_col_valor_usd_anio": {
        "es": "Valor (USD/año)",
        "en": "Value (USD/year)",
    },
    "financiero_periodo_punta": {
        "es": "Punta",
        "en": "Peak",
    },
    "financiero_periodo_valle": {
        "es": "Valle",
        "en": "Off-peak",
    },
    "financiero_periodo_nocturno": {
        "es": "Nocturno",
        "en": "Night",
    },
    "financiero_expander_parametros_avanzados": {
        "es": "Parámetros avanzados",
        "en": "Advanced parameters",
    },
    "financiero_number_vida_util": {
        "es": "Vida útil del proyecto (años)",
        "en": "Useful life of the project (years)",
    },
    "financiero_number_tasa_descuento": {
        "es": "Tasa de descuento para NPV (%)",
        "en": "Discount rate for NPV (%)",
    },
    "financiero_titulo_seleccion_equipo": {
        "es": "Selección de equipo -- precio EXWORKS",
        "en": "Equipment selection -- EXWORKS price",
    },
    "financiero_caption_seleccion_equipo": {
        "es": "Elegí acá, por clúster, el artículo exacto del catálogo real de Flower "
              "Turbines que vas a cotizar -- el grupo ya se filtra automático según el "
              "modelo elegido en \"Equipos y configuración\", vos elegís la variante "
              "(unidad simple, bouquet, on/off-grid, con o sin accesorio). Esto es "
              "sólo de referencia para llenar el costeo de abajo -- no se usa solo "
              "para calcular Payback/ROI.",
        "en": "Here, for each cluster, pick the exact item from Flower Turbines' real "
              "catalog that you're going to quote -- the group is already filtered "
              "automatically based on the model chosen in \"Equipment & "
              "configuration\"; you choose the variant (single unit, bouquet, "
              "on/off-grid, with or without accessory). This is for reference only, "
              "to help fill in the costing below -- by itself it isn't used to "
              "calculate Payback/ROI.",
    },
    "financiero_caption_sin_precio": {
        "es": "{modelo}: precio no disponible todavía (no hay artículo cargado en el "
              "catálogo).",
        "en": "{modelo}: price not available yet (no catalog item loaded).",
    },
    "financiero_selectbox_articulo": {
        "es": "Artículo -- {modelo} ({n}x)",
        "en": "Item -- {modelo} ({n}x)",
    },
    "financiero_help_articulo": {
        "es": "Precio de venta real de fábrica -- elegí la variante exacta que vas a "
              "cotizar (unidad simple, bouquet, on/off-grid, con o sin accesorio).",
        "en": "Actual factory sale price -- choose the exact variant you're going to "
              "quote (single unit, bouquet, on/off-grid, with or without accessory).",
    },
    "financiero_caption_precio_unitario": {
        "es": "Precio: \\${precio_unitario} c/u -- Total del clúster ({n}x): "
              "\\${total_cluster}",
        "en": "Price: \\${precio_unitario} each -- Cluster total ({n}x): "
              "\\${total_cluster}",
    },
    "financiero_metric_precio_total_proyecto": {
        "es": "Precio total del proyecto (equipos, EXWORKS)",
        "en": "Total project price (equipment, EXWORKS)",
    },
    "financiero_caption_precio_total_detalle": {
        "es": "Precio de venta de fábrica del artículo elegido en cada clúster. NO "
              "incluye flete, importación ni instalación -- eso lo agrega ECO "
              "Consultor aparte. Es el precio del artículo elegido × cantidad de "
              "turbinas del clúster -- si elegís un artículo de \"bouquet\" (varias "
              "turbinas con un solo inversor), revisá que la cantidad (N) del clúster "
              "tenga sentido con ese artículo.",
        "en": "Factory sale price of the item selected for each cluster. Does NOT "
              "include freight, import duties, or installation -- ECO Consultor adds "
              "those separately. It is the price of the selected item × the number of "
              "turbines in the cluster -- if you pick a \"bouquet\" item (several "
              "turbines sharing one inverter), check that the cluster's turbine count "
              "(N) makes sense for that item.",
    },
    "financiero_texto_falta_articulo": {
        "es": "Al menos un modelo elegido todavía no tiene ningún artículo cargado.",
        "en": "At least one selected model does not have a catalog item loaded yet.",
    },
    "financiero_titulo_costeo_real": {
        "es": "Costeo real del proyecto",
        "en": "Actual project costing",
    },
    "financiero_caption_costeo_real": {
        "es": "En vez de estimar el CAPEX con costo de fábrica + margen + flete "
              "supuestos, ingresá acá los números reales de tu cotización: cuánto "
              "cuestan los equipos, a cuánto se los vas a vender al cliente, y cuánto "
              "vas a cobrar de mantenimiento al año. Payback, ROI, NPV y viabilidad se "
              "calculan directo de esos datos.",
        "en": "Instead of estimating CAPEX from assumed factory cost + margin + "
              "freight, enter the actual numbers from your quote here: how much the "
              "equipment costs, how much you're going to sell it to the client for, "
              "and how much you'll charge for maintenance per year. Payback, ROI, NPV, "
              "and viability are calculated directly from that data.",
    },
    "financiero_number_costo_equipos": {
        "es": "Costo de los equipos (turbinas + inversor + BESS, USD)",
        "en": "Equipment cost (turbines + inverter + BESS, USD)",
    },
    "financiero_help_costo_equipos": {
        "es": "Lo que ECO Consultor paga por comprar/importar los equipos -- sólo "
              "informativo, para ver el margen (no entra en el cálculo de Payback).",
        "en": "What ECO Consultor pays to purchase/import the equipment -- for "
              "reference only, to show the margin (it does not enter the Payback "
              "calculation).",
    },
    "financiero_number_precio_venta": {
        "es": "Precio de venta al cliente (USD)",
        "en": "Sale price to the client (USD)",
    },
    "financiero_help_precio_venta": {
        "es": "Precio final cotizado al cliente, llave en mano (equipos + "
              "instalación) -- este es el CAPEX real que se usa para Payback/ROI/NPV.",
        "en": "Final turnkey price quoted to the client (equipment + installation) -- "
              "this is the actual CAPEX used for Payback/ROI/NPV.",
    },
    "financiero_number_mantenimiento_anual": {
        "es": "Mantenimiento anual (USD/año)",
        "en": "Annual maintenance (USD/year)",
    },
    "financiero_help_mantenimiento_anual": {
        "es": "Costo real esperado de mantenimiento al año -- reemplaza el % del "
              "CAPEX que se adivinaba antes.",
        "en": "Actual expected maintenance cost per year -- replaces the guessed % of "
              "CAPEX used before.",
    },
    "financiero_caption_margen": {
        "es": "Margen sobre costo de equipos: ${margen} ({pct}%).",
        "en": "Margin over equipment cost: ${margen} ({pct}%).",
    },
    "financiero_info_falta_precio_venta": {
        "es": "Ingresá el precio de venta al cliente para calcular Payback, ROI, NPV "
              "y viabilidad económica.",
        "en": "Enter the sale price to the client to calculate Payback, ROI, NPV, and "
              "economic viability.",
    },
    "financiero_info_error_tarifa_horaria": {
        "es": "No se pudo calcular el ahorro con tarifa horaria (ver el error arriba) "
              "-- cambiá a \"{opcion}\" o revisá la selección de proveedor/tarifa.",
        "en": "The hourly-rate savings could not be calculated (see the error above) "
              "-- switch to \"{opcion}\" or check the provider/rate selection.",
    },
    "financiero_info_error_tarifa_comercial": {
        "es": "No se pudo calcular el ahorro con tarifa comercial (ver el error "
              "arriba) -- cambiá a \"{opcion}\" o revisá la selección de "
              "proveedor/tramo.",
        "en": "The commercial-rate savings could not be calculated (see the error "
              "above) -- switch to \"{opcion}\" or check the provider/bracket "
              "selection.",
    },
    "financiero_metric_energia_anual": {
        "es": "Energía anual generada",
        "en": "Annual energy generated",
    },
    "financiero_valor_kwh_anio": {
        "es": "{kwh} kWh/año",
        "en": "{kwh} kWh/year",
    },
    "financiero_metric_ahorro_anual": {
        "es": "Ahorro anual (electricidad no comprada)",
        "en": "Annual savings (electricity not purchased)",
    },
    "financiero_valor_monto_por_anio": {
        "es": "${monto}/año",
        "en": "${monto}/year",
    },
    "financiero_metric_mantenimiento_anual": {
        "es": "Mantenimiento anual",
        "en": "Annual maintenance",
    },
    "financiero_titulo_retorno_inversion": {
        "es": "Retorno de la inversión",
        "en": "Return on investment",
    },
    "financiero_metric_capex": {
        "es": "CAPEX (precio de venta)",
        "en": "CAPEX (sale price)",
    },
    "financiero_metric_payback": {
        "es": "Payback",
        "en": "Payback period",
    },
    "financiero_valor_anos": {
        "es": "{n} años",
        "en": "{n} years",
    },
    "financiero_no_disponible": {
        "es": "N/D",
        "en": "N/A",
    },
    "financiero_metric_roi": {
        "es": "ROI (vida útil)",
        "en": "ROI (useful life)",
    },
    "financiero_metric_viabilidad": {
        "es": "Viabilidad",
        "en": "Viability",
    },
    "financiero_valor_viable": {
        "es": "VIABLE",
        "en": "VIABLE",
    },
    "financiero_valor_no_viable": {
        "es": "NO VIABLE",
        "en": "NOT VIABLE",
    },
    "financiero_caption_npv": {
        "es": "NPV a {anos} años, tasa de descuento {tasa}%: ${npv}",
        "en": "NPV over {anos} years, discount rate {tasa}%: ${npv}",
    },
    "financiero_caption_opex_negativo": {
        "es": "El ahorro anual estimado en electricidad no alcanza a cubrir el "
              "mantenimiento anual ingresado (ahorro: \\${ahorro}/año vs. "
              "mantenimiento: \\${mantenimiento}/año) -- por eso Payback/ROI/NPV "
              "muestran {na}.",
        "en": "The estimated annual electricity savings do not cover the maintenance "
              "cost entered (savings: \\${ahorro}/year vs. maintenance: "
              "\\${mantenimiento}/year) -- that is why Payback/ROI/NPV show {na}.",
    },
    "financiero_info_opex_negativo_contexto": {
        "es": "Con el precio de venta y la tarifa eléctrica ingresados, este proyecto "
              "NO recupera el mantenimiento sólo con ahorro de electricidad. Si el "
              "objetivo del cliente es respaldo/resiliencia energética (no depender "
              "100% de la red) en vez de recuperar la inversión sólo con el ahorro "
              "eléctrico, ese es el valor que hay que presentar -- este cálculo no lo "
              "cuantifica en dólares.",
        "en": "Given the sale price and electricity rate entered, this project does "
              "NOT recover its maintenance cost from electricity savings alone. If "
              "the client's goal is energy backup/resilience (not depending 100% on "
              "the grid) rather than recovering the investment purely through "
              "electricity savings, that is the value proposition to present -- this "
              "calculation does not quantify it in dollars.",
    },
    "financiero_caption_footer": {
        "es": "CAPEX, mantenimiento y precio de venta ingresados directo por el "
              "usuario. Tarifas horarias reales de CNFL/ICE cruzadas contra la "
              "producción hora por hora, en vez de una tarifa plana adivinada.",
        "en": "CAPEX, maintenance, and sale price entered directly by the user. "
              "Actual CNFL/ICE hourly rates cross-referenced against hour-by-hour "
              "output, instead of a guessed flat rate.",
    },

    # --- Sección: tab_especificacion (Especificación Técnica) ----------------------
    "especificacion_caption_intro": {
        "es": "Datos generales del sistema y ficha técnica de fábrica de las turbinas "
              "-- usa las turbinas ya configuradas en \"{tab_config}\" y la producción "
              "ya calculada en \"{tab_resultados}\".",
        "en": "General system data and the turbines' factory technical datasheet -- "
              "uses the turbines already configured in \"{tab_config}\" and the "
              "output already calculated in \"{tab_resultados}\".",
    },
    "especificacion_error_sin_resultado": {
        "es": "No se pudo leer el resultado de producción -- revisá la pestaña "
              "\"{tab}\".",
        "en": "Could not read the production result -- check the \"{tab}\" tab.",
    },
    "especificacion_titulo_datos_generales": {
        "es": "Datos generales del sistema",
        "en": "General system data",
    },
    "especificacion_metric_sitio": {
        "es": "Sitio",
        "en": "Site",
    },
    "especificacion_metric_potencia_pico": {
        "es": "Potencia pico instalada",
        "en": "Installed peak power",
    },
    "especificacion_metric_energia_anual": {
        "es": "Energía anual estimada",
        "en": "Estimated annual energy",
    },
    "especificacion_valor_energia_anual": {
        "es": "{kwh} kWh/año",
        "en": "{kwh} kWh/year",
    },
    "especificacion_metric_elevacion": {
        "es": "Elevación del sitio",
        "en": "Site elevation",
    },
    "especificacion_arquitectura_electrica": {
        "es": "**Arquitectura eléctrica:** bus de corriente continua a {voltaje}V -- "
              "cada turbina entrega su salida a través de un controlador individual "
              "de fábrica; todos los controladores se conectan en paralelo al mismo "
              "bus, que alimenta directamente el puerto de batería del inversor (no "
              "el puerto solar/MPPT).",
        "en": "**Electrical architecture:** {voltaje}V DC bus -- each turbine feeds "
              "its output through an individual factory controller; all controllers "
              "connect in parallel to the same bus, which feeds directly into the "
              "inverter's battery port (not the solar/MPPT port).",
    },
    "especificacion_titulo_turbinas": {
        "es": "Turbinas eólicas",
        "en": "Wind turbines",
    },
    "especificacion_turbina_titulo_cantidad": {
        "es": "**{nombre}** -- cantidad: {cantidad}",
        "en": "**{nombre}** -- quantity: {cantidad}",
    },
    "especificacion_turbina_fabricante": {
        "es": "Fabricante: Flower Turbines -- N° de parte: {parte}",
        "en": "Manufacturer: Flower Turbines -- Part number: {parte}",
    },
    "especificacion_campo_potencia_nominal": {
        "es": "Potencia nominal",
        "en": "Rated power",
    },
    "especificacion_campo_velocidad_nominal": {
        "es": "Velocidad a potencia nominal",
        "en": "Wind speed at rated power",
    },
    "especificacion_campo_velocidad_cutin": {
        "es": "Velocidad de arranque (cut-in)",
        "en": "Cut-in speed",
    },
    "especificacion_campo_velocidad_supervivencia": {
        "es": "Velocidad de supervivencia",
        "en": "Survival speed",
    },
    "especificacion_campo_tipo_rotor": {
        "es": "Tipo de rotor",
        "en": "Rotor type",
    },
    "especificacion_campo_tipo_generador": {
        "es": "Tipo de generador",
        "en": "Generator type",
    },
    "especificacion_campo_diametro_rotor": {
        "es": "Diámetro del rotor",
        "en": "Rotor diameter",
    },
    "especificacion_campo_altura_pala": {
        "es": "Altura de pala",
        "en": "Blade height",
    },
    "especificacion_campo_peso": {
        "es": "Peso",
        "en": "Weight",
    },
    "especificacion_campo_cimentacion": {
        "es": "Cimentación requerida",
        "en": "Required foundation",
    },
    "especificacion_col_campo": {
        "es": "Especificación",
        "en": "Specification",
    },
    "especificacion_col_valor": {
        "es": "Valor",
        "en": "Value",
    },
    "especificacion_caption_fuente_datos": {
        "es": "Fuente de los datos: fichas técnicas oficiales de fábrica de Flower "
              "Turbines.",
        "en": "Data source: Flower Turbines' official factory technical datasheets.",
    },
    "especificacion_titulo_informe_ejecutivo": {
        "es": "Informe ejecutivo",
        "en": "Executive report",
    },
    "especificacion_caption_informe_resumen": {
        "es": "Resumen de las 6 pestañas -- clima, equipos, producción y viabilidad "
              "financiera (si ya la completaste) -- en un solo PDF listo para "
              "imprimir o enviar al cliente.",
        "en": "Summary of all 6 tabs -- climate, equipment, output, and financial "
              "viability (if you've already filled it in) -- in a single PDF ready "
              "to print or send to the client.",
    },
    "especificacion_boton_generar_informe": {
        "es": "Generar informe ejecutivo (PDF)",
        "en": "Generate executive report (PDF)",
    },
    "especificacion_spinner_armando_informe": {
        "es": "Armando el informe ejecutivo...",
        "en": "Building the executive report...",
    },
    "especificacion_pdf_fuente_estacion_real": {
        "es": "Estación real: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, lon={lon}, "
              "elevación={elevacion}m. Media anual real: {media} m/s.",
        "en": "Real weather station: {estacion} ({pais}, WMO {wmo}) -- lat={lat}, "
              "lon={lon}, elevation={elevacion}m. Real annual average: {media} m/s.",
    },
    "especificacion_pdf_fuente_media_sitio": {
        "es": "Media anual real del viento en el sitio: {media} m/s.",
        "en": "Real annual average wind speed at the site: {media} m/s.",
    },
    "especificacion_error_generar_informe": {
        "es": "No se pudo generar el informe ejecutivo: {error} -- si el problema "
              "persiste, puede ser que falte un navegador Chrome/Chromium instalado "
              "en este entorno (hace falta para exportar los gráficos al PDF).",
        "en": "Could not generate the executive report: {error} -- if the problem "
              "persists, this environment may be missing a Chrome/Chromium browser "
              "(needed to export the charts to the PDF).",
    },
    "especificacion_caption_informe_sin_financiero": {
        "es": "El informe no incluye CAPEX/Payback/ROI/NPV -- completá el precio de "
              "venta y la tarifa eléctrica en \"{tab}\" y volvé a generar el informe "
              "para sumarlos.",
        "en": "The report does not include CAPEX/Payback/ROI/NPV -- fill in the sale "
              "price and the electricity rate in \"{tab}\" and regenerate the report "
              "to add them.",
    },
    "especificacion_boton_descargar_informe": {
        "es": "📄 Descargar informe ejecutivo (PDF)",
        "en": "📄 Download executive report (PDF)",
    },
    "especificacion_pdf_nombre_archivo_base": {
        "es": "ECO-Wind_informe_ejecutivo",
        "en": "ECO-Wind_executive_report",
    },

    # --- Sección: pdf_reporte.py (informe ejecutivo + lista de precios) --------
    # Traducción de los 3 valores internos de `modo_tarifa` (app.py los guarda
    # SIEMPRE en español -- son claves de comparación == en tab_financiero,
    # traducirlos ahí rompería esas comparaciones) -- pdf_reporte.py los pasa
    # por MODO_TARIFA_A_CLAVE_PDF antes de mostrarlos, para que el informe en
    # inglés no muestre ese único campo en español.
    "pdf_modo_tarifa_plana": {"es": "Tarifa plana (USD/kWh)", "en": "Flat rate (USD/kWh)"},
    "pdf_modo_tarifa_comercial": {
        "es": "Tarifa comercial de Costa Rica (T-CO)",
        "en": "Costa Rica commercial rate (T-CO)",
    },
    "pdf_modo_tarifa_horaria": {
        "es": "Tarifa horaria real de Costa Rica (ARESEP)",
        "en": "Costa Rica real hourly rate (ARESEP)",
    },
    'pdf_titulo_informe': {'es': 'Informe Ejecutivo', 'en': 'Executive Report'},
    'pdf_meta_titulo_informe': {'es': 'Informe Ejecutivo -- ECO | Wind', 'en': 'Executive Report -- ECO | Wind'},
    'pdf_subtitulo_informe': {'es': 'Propuesta de microgeneración eólica -- {sitio_nombre} -- generado el {fecha}', 'en': 'Wind micro-generation proposal -- {sitio_nombre} -- generated on {fecha}'},
    'pdf_intro_resumen': {'es': 'Este informe resume la propuesta técnica y financiera de microgeneración eólica para <b>{sitio_nombre}</b>, calculada a partir de datos climáticos reales (EPW de la estación elegida) y especificaciones oficiales de fábrica de los equipos Flower Turbines.', 'en': 'This report summarizes the technical and financial proposal for wind micro-generation at <b>{sitio_nombre}</b>, calculated from real climate data (EPW file from the selected weather station) and official factory specifications for the Flower Turbines equipment.'},
    'pdf_kpi_potencia_pico': {'es': 'Potencia pico instalada', 'en': 'Installed peak power'},
    'pdf_kpi_energia_anual': {'es': 'Energía anual estimada', 'en': 'Estimated annual energy'},
    'pdf_kpi_turbinas_totales': {'es': 'Turbinas totales', 'en': 'Total turbines'},
    'pdf_kpi_elevacion_sitio': {'es': 'Elevación del sitio', 'en': 'Site elevation'},
    'pdf_kpi_capex_precio_venta': {'es': 'CAPEX (precio de venta)', 'en': 'CAPEX (sale price)'},
    'pdf_kpi_payback': {'es': 'Payback', 'en': 'Payback period'},
    'pdf_kpi_roi_vida_util': {'es': 'ROI (vida útil)', 'en': 'ROI (useful life)'},
    'pdf_kpi_viabilidad_economica': {'es': 'Viabilidad económica', 'en': 'Economic viability'},
    'pdf_kpi_viabilidad': {'es': 'Viabilidad', 'en': 'Viability'},
    'pdf_valor_anos': {'es': '{n} años', 'en': '{n} years'},
    'pdf_valor_pct_menos': {'es': '{pct}% menos', 'en': '{pct}% less'},
    'pdf_valor_viable': {'es': 'VIABLE', 'en': 'VIABLE'},
    'pdf_valor_a_evaluar': {'es': 'A EVALUAR', 'en': 'TO BE ASSESSED'},
    'pdf_no_disponible': {'es': 'N/D', 'en': 'N/A'},
    'pdf_titulo_contexto_climatico': {'es': 'Contexto Climático', 'en': 'Climate Context'},
    'pdf_caption_rosa_vientos': {'es': 'Rosa de vientos -- % de horas por dirección y velocidad', 'en': 'Wind rose -- % of hours by direction and speed'},
    'pdf_caption_heatmap_mensual': {'es': 'Velocidad media del viento por mes y hora del día', 'en': 'Average wind speed by month and hour of day'},
    'pdf_caption_perfil_viento': {'es': 'Perfil logarítmico de viento -- velocidad real según la altura de instalación', 'en': 'Logarithmic wind profile -- actual speed based on installation height'},
    'pdf_titulo_equipos': {'es': 'Equipos Configurados', 'en': 'Configured Equipment'},
    'pdf_equipos_texto_bus': {'es': 'Bus de corriente continua a {voltaje}V -- cada turbina entrega su salida a través de un controlador individual de fábrica; todos los controladores se conectan en paralelo al mismo bus.', 'en': 'DC bus at {voltaje}V -- each turbine feeds its output through an individual factory controller; all controllers connect in parallel to the same bus.'},
    'pdf_equipo_nombre_cantidad': {'es': '{nombre} -- cantidad: {cantidad}', 'en': '{nombre} -- quantity: {cantidad}'},
    'pdf_equipo_fabricante_parte': {'es': 'Fabricante: Flower Turbines -- N° de parte: {numero_parte}', 'en': 'Manufacturer: Flower Turbines -- Part number: {numero_parte}'},
    'pdf_tabla_header_especificacion': {'es': 'Especificación', 'en': 'Specification'},
    'pdf_tabla_header_valor': {'es': 'Valor', 'en': 'Value'},
    'pdf_titulo_resultados_produccion': {'es': 'Resultados de Producción', 'en': 'Production Results'},
    'pdf_kpi_produccion_anual_total': {'es': 'Producción anual total', 'en': 'Total annual output'},
    'pdf_kpi_correccion_densidad': {'es': 'Corrección por densidad (elevación)', 'en': 'Air-density correction (elevation)'},
    'pdf_prod_header_modelo': {'es': 'Modelo', 'en': 'Model'},
    'pdf_prod_header_n': {'es': 'N', 'en': 'N'},
    'pdf_prod_header_buje': {'es': 'Buje (m)', 'en': 'Hub height (m)'},
    'pdf_prod_header_kwh_anio': {'es': 'kWh/año', 'en': 'kWh/year'},
    'pdf_prod_header_v_media_buje': {'es': 'V. media buje (m/s)', 'en': 'Avg. hub wind speed (m/s)'},
    'pdf_prod_header_pct_cutin': {'es': '% bajo cut-in', 'en': '% below cut-in speed'},
    'pdf_caption_produccion_mensual': {'es': 'Producción mensual (todos los clústers)', 'en': 'Monthly output (all clusters)'},
    'pdf_caption_curva_duracion': {'es': 'Curva de duración -- resolución horaria completa', 'en': 'Duration curve -- full hourly resolution'},
    'pdf_texto_validacion_calculo': {'es': 'Cálculo validado con datos de campo, con corrección por densidad de aire según elevación. Fuente climática: EPW real de la estación elegida o subida por el usuario.', 'en': 'Calculation validated against field data, with air-density correction for elevation. Climate source: real EPW file from the selected weather station or uploaded by the user.'},
    'pdf_titulo_analisis_financiero': {'es': 'Análisis Financiero', 'en': 'Financial Analysis'},
    'pdf_kpi_ahorro_anual': {'es': 'Ahorro anual', 'en': 'Annual savings'},
    'pdf_kpi_mantenimiento_anual': {'es': 'Mantenimiento anual', 'en': 'Annual maintenance'},
    'pdf_spec_modalidad_tarifa': {'es': 'Modalidad de tarifa eléctrica', 'en': 'Electricity rate type'},
    'pdf_spec_vida_util_proyecto': {'es': 'Vida útil del proyecto', 'en': 'Useful life of the project'},
    'pdf_spec_tasa_descuento': {'es': 'Tasa de descuento (NPV)', 'en': 'Discount rate (NPV)'},
    'pdf_texto_financiero_metodologia': {'es': 'CAPEX, mantenimiento y precio de venta ingresados directo por el usuario en la app. Tarifas horarias reales de CNFL/ICE cruzadas contra la producción hora por hora cuando corresponde, en vez de una tarifa plana adivinada.', 'en': 'CAPEX, maintenance cost and sale price entered directly by the user in the app. Real hourly CNFL/ICE electricity rates are matched against hour-by-hour output where applicable, instead of an assumed flat rate.'},
    'pdf_caja_info_falta_financiero': {'es': 'Completá el precio de venta al cliente y la tarifa eléctrica en la pestaña "Análisis Financiero" de la app para incluir acá el CAPEX, Payback, ROI y NPV de este proyecto.', 'en': 'Fill in the client sale price and the electricity rate in the app\'s "Financial Analysis" tab to include the CAPEX, Payback period, ROI and NPV for this project here.'},
    'pdf_pie_copyright': {'es': '© {anio} ECO Consultor', 'en': '© {anio} ECO Consultor'},
    'pdf_pie_numero_pagina': {'es': 'Página {n}', 'en': 'Page {n}'},
    'pdf_precios_titulo': {'es': 'Lista de Precios de Referencia -- Turbinas Flower Turbines', 'en': 'Reference Price List -- Flower Turbines'},
    'pdf_precios_meta_titulo': {'es': 'Lista de precios -- ECO | Wind', 'en': 'Price list -- ECO | Wind'},
    'pdf_precios_subtitulo': {'es': 'ECO | Wind -- Simulador de microgeneración eólica -- generado el {fecha}', 'en': 'ECO | Wind -- Wind micro-generation simulator -- generated on {fecha}'},
    'pdf_precios_texto_formula': {'es': "Precio final = (costo de fábrica + flete estimado por unidad) &times; 1.30 de margen comercial. El flete asume pedir lo suficiente para llenar 1 pallet o 1 contenedor completo (lo que salga más barato por unidad) -- tarifas de mercado ($2,000 unidad / $3,500 pallet / $10,000 contenedor de 40'), NO una cotización de un forwarder real. Usar como orden de magnitud para el cliente, confirmar antes de cotizar en firme.", 'en': "Final price = (factory cost + estimated freight per unit) &times; 1.30 commercial margin. Freight assumes ordering enough to fill 1 full pallet or 1 full container (whichever is cheaper per unit) -- market rates ($2,000 per unit / $3,500 per pallet / $10,000 per 40' container), NOT a real freight-forwarder quote. Use as an order-of-magnitude estimate for the client; confirm before quoting a firm price."},
    'pdf_precios_header_modelo': {'es': 'Modelo', 'en': 'Model'},
    'pdf_precios_header_costo_fabrica': {'es': 'Costo fábrica', 'en': 'Factory cost'},
    'pdf_precios_header_flete_unidad': {'es': 'Flete/unidad (est.)', 'en': 'Freight/unit (est.)'},
    'pdf_precios_header_precio_final': {'es': 'Precio final (est.)', 'en': 'Final price (est.)'},
    'pdf_precios_header_fuente_costo': {'es': 'Fuente del costo', 'en': 'Cost source'},
    'pdf_precios_valor_verificado': {'es': 'Verificado', 'en': 'Verified'},
    'pdf_precios_valor_no_verificado': {'es': 'No verificado', 'en': 'Not verified'},
    'pdf_precios_seccion_verificados': {'es': 'Modelos con costo de fábrica verificado', 'en': 'Models with verified factory cost'},
    'pdf_precios_seccion_no_verificados': {'es': 'Modelos con costo de fábrica NO verificado', 'en': 'Models with unverified factory cost'},
    'pdf_precios_texto_no_verificado_advertencia': {'es': 'Vienen de una respuesta de chat tipo "representante de Flower Turbines", no de una cotización real -- usar sólo como referencia interna, no repetirlos como precio firme frente al cliente.', 'en': 'These come from a chat-style response from a "Flower Turbines representative", not a real quote -- use for internal reference only, do not repeat them as a firm price to the client.'},
    'pdf_precios_pie_fuente': {'es': 'Fuente de los datos: fichas técnicas oficiales de fábrica (Flower Turbines) para el costo base, `engine/price_calculator.py` para el flete y margen. ECO Consultor -- Energy Conservation Opportunities.', 'en': 'Data source: official factory technical datasheets (Flower Turbines) for the base cost, `engine/price_calculator.py` for freight and margin. ECO Consultor -- Energy Conservation Opportunities.'},
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


_MODO_TARIFA_A_CLAVE = {
    "Tarifa plana (USD/kWh)": "pdf_modo_tarifa_plana",
    "Tarifa comercial de Costa Rica (T-CO)": "pdf_modo_tarifa_comercial",
    "Tarifa horaria real de Costa Rica (ARESEP)": "pdf_modo_tarifa_horaria",
}


def tr_modo_tarifa(modo_tarifa_es: str, idioma: str) -> str:
    """Traduce el valor de `modo_tarifa` -- que app.py SIEMPRE guarda en
    español porque es una clave de comparación == en tab_financiero, no un
    texto de traducción directa -- para mostrarlo en el idioma del informe
    PDF. Si el valor no es ninguno de los 3 conocidos, se devuelve tal cual
    (mejor mostrar el dato real que romper el informe)."""
    clave = _MODO_TARIFA_A_CLAVE.get(modo_tarifa_es)
    return tr(clave, idioma) if clave else modo_tarifa_es


def meses_abreviados(idioma: str = None) -> list:
    """Lista de 12 meses abreviados en el idioma dado (o el activo de sesión
    si no se pasa ninguno) -- mismo orden que engine/*.py que arma matrices
    mes×hora (Ene..Dic / Jan..Dec)."""
    claves = ["mes_ene", "mes_feb", "mes_mar", "mes_abr", "mes_may", "mes_jun",
              "mes_jul", "mes_ago", "mes_sep", "mes_oct", "mes_nov", "mes_dic"]
    if idioma is None:
        return [t(c) for c in claves]
    return [tr(c, idioma) for c in claves]
