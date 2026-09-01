# Plan: paleta y gráficos de `weather-report` para "CONTEXTO CLIMÁTICO"

> Documento generado por Claude a pedido de Pablo, a partir de investigar
> `pollination-apps/weather-report` (Ladybug Tools / Pollination) como
> referencia visual para la pestaña "CONTEXTO CLIMÁTICO" de `app/app.py`.
> Es solo un plan -- todavía no se implementó nada de esto en el código.

## 1. Qué es `weather-report`

App de Streamlit de Pollination/Ladybug Tools. Carga un `.epw` con
`ladybug.epw.EPW` y delega toda la generación de gráficos a
`ladybug` + `ladybug-comfort` + `ladybug-charts` (Plotly por debajo).
`app.py`/`helper.py` son casi puro glue code -- cada gráfico es una llamada
a un método de `ladybug` (`epw.diurnal_average_chart()`, `WindRose(...).plot()`,
`PsychrometricChart(...).plot()`, etc.), no hay lógica de dibujo propia.

Repo: https://github.com/pollination-apps/weather-report

## 2. Inventario de visuales de la app de referencia (11)

| # | Visual | Qué muestra | Datos EPW que necesita |
|---|---|---|---|
| 1 | Mapa de ubicación | Punto lat/lon del sitio | lat/lon |
| 2 | Diurnal average chart (todas las variables) | Grid mes × hora, día "promedio" por mes, para cualquier variable | Cualquier campo EPW |
| 3 | Hourly data heatmap | Heatmap 8760h (día del año × hora), variable + filtro condicional y rango de fechas | Cualquier campo EPW |
| 4 | Bar chart multi-variable | Barras mensuales/diarias, promedio o total, varias variables | Cualquier campo EPW |
| 5 | Hourly line chart | Línea de las 8760h de una variable | Cualquier campo EPW |
| 6 | Diurnal average chart (una variable) | "Día típico" -- promedio por hora a lo largo del año | Cualquier campo EPW |
| 7 | Daily chart | Barra/línea con el promedio diario (365 puntos) | Cualquier campo EPW |
| 8 | Sunpath | Diagrama de trayectoria solar, opcional coloreado por variable | lat/lon/timezone |
| 9 | Degree days | Grados-día de calefacción/enfriamiento, mensual | Dry Bulb Temperature |
| 10 | Windrose | Rosa de vientos con filtro de rango de fechas/horas | Wind Speed + Wind Direction |
| 11 | Psychrometric chart | Temp. vs humedad, polígonos de confort por estrategia pasiva | Dry Bulb Temperature + Relative Humidity |

## 3. Lo que ECO-Wind realmente tiene hoy (el cuello de botella)

`df_clima` en ECO-Wind **nunca es un EPW completo** -- es un DataFrame
reducido a 2-3 columnas, y varía según el origen del clima:

| Origen del sitio | Columnas en `df_clima` | Notas |
|---|---|---|
| EPW real descargado/subido/3 sitios precacheados (Nicoya, Liberia, Finca Favorita) | `WS10M`, `WD10`, `T2M` | El parser propio (`engine/epw_real.py::cargar_epw_real`, líneas 111-113) solo lee 3 campos del `.epw` -- el archivo en disco SÍ tiene humedad, radiación, cobertura de nubes, etc., pero hoy no se extraen. |
| San José (`engine/simulador_pista_a.py::generar_clima_gwa`, export de GWA) | `WS10M`, `T2M` (constante = 22.0 todas las horas) | No hay `WD10` real -- la rosa de vientos sale de una tabla de frecuencias estática (`.lib` de GWA). La "temperatura" es un placeholder, no un dato. |
| Aproximación por ráster (`engine/gwa_raster.py::generar_clima_sitio_nuevo`) | Igual que San José (reusa `generar_clima_gwa` con la forma prestada) | Mismas limitaciones que San José. |

**Para 2 de los 4 caminos climáticos de la app (San José y la aproximación
por ráster) solo existe viento** -- ni humedad, ni temperatura real, ni
radiación. El camino de EPW real sí tiene el archivo completo en disco,
solo que hoy no se parsea más que esas 3 columnas.

## 4. Matriz de factibilidad (de la investigación original)

| Visual | Factible hoy sin nueva dependencia | Requiere `ladybug`/`ladybug-charts` | Limitación por fuente de clima |
|---|---|---|---|
| Windrose | ✅ ya existe, le falta filtro de fechas | No | San José/aproximación: frecuencia estática, no filtrable |
| Heatmap mes×hora (1 variable) | ✅ ya existe para viento | No | San José/aproximación: T2M constante → heatmap plano |
| Diurnal average (día típico, 1 variable) | ✅ con pandas `groupby(hour).mean()` | No | Igual que arriba |
| Daily chart / bar chart mensual | ✅ con pandas `resample` | No | Igual que arriba |
| Hourly line chart | ✅ trivial | No | Ninguna, aunque poco útil con 8760 puntos |
| Degree days (HDD/CDD) | ⚠️ fórmula simple, portable a mano | No | Solo tiene sentido con EPW real (San José da HDD=CDD=0 siempre) |
| Sunpath | ⚠️ con `pvlib` (no con `ladybug` completo) | Alternativa liviana existe | Ninguna, solo necesita lat/lon |
| Psychrometric chart | ❌ | Sí (`ladybug-comfort`) | Falta Relative Humidity, ni se parsea hoy |

## 5. El hallazgo de diseño (lo que define este plan)

Corrí la app de verdad (tuve que parchear 3 incompatibilidades de versión
-- renombres de API de `ladybug-core` y un downgrade a `pandas<2.2` -- para
que renderizara) y extraje los colores exactos que usa. **No es una app
con un montón de paletas distintas: es UNA sola escala de 10 colores
("original" de Ladybug) que se reusa en todo**, tomando los extremos para
series binarias y el gradiente completo para heatmaps/rosa de vientos:

```
PALETA_CLIMA = [
    "#4b6ba9", "#7393ca", "#aac8f7", "#c1d5d0", "#f5ef67",
    "#fce64a", "#ef9c15", "#ea7b00", "#ea4a00", "#ea2600",
]
#   (frío/azul) ────────────────────────────────────→ (calor/rojo)
```

- Heatmap y rosa de vientos: los 10 tonos completos como gradiente.
- Series de a dos (temp. seca/húmeda, calefacción/enfriamiento, Dry
  Bulb/Humedad): extremo azul (`#4b6ba9`) para una serie, extremo rojo
  (`#ea2600`) para la otra.
- Fondo blanco, grilla gris clara, título centrado en negrita, ejes en
  gris -- eso es el default de Plotly, no algo que Ladybug agregue.

Capturas reales (en `Recursos Visuales/referencia-weather-report/`):
- `windrose.png` -- rosa de vientos con gradiente de 10 colores por bin de velocidad.
- `dia-tipico.png` -- diurnal average chart (líneas de temperatura + banda de radiación).
- `barras-mensuales-y-heatmap.png` -- heatmap de temperatura + barras mensuales de 2 variables.
- `grafico-diario.png` -- radiación diaria + cobertura de nubes diaria.

**No hace falta instalar `ladybug`/`ladybug-charts`** (que solo funciona
si hay un EPW completo -- cosa que San José y la aproximación por ráster
no tienen). Lo que se busca -- el look -- sale de dos cosas livianas:
**Plotly** (en vez de matplotlib) + esos 10 hex codes como constantes
propias, reimplementando los tipos de gráfico con pandas puro sobre
`df_clima`.

## 6. Qué migrar, gráfico por gráfico

| Hoy (matplotlib) | Se convierte en | Datos que usa | Esfuerzo |
|---|---|---|---|
| Rosa de vientos (verde sólido, `graficar_rosa_vientos`) | Rosa de vientos Plotly con gradiente de los 10 colores por bin de velocidad | `rosa_freq` (ya existe) | Bajo -- reescribir la misma función con `plotly.graph_objects.Barpolar` |
| Heatmap mensual (verde, `graficar_heatmap_clima`) | Heatmap Plotly con el gradiente azul→rojo de 10 stops | `hm_json` (ya existe) | Bajo -- mismo dato, cambia `plt.imshow` por `go.Heatmap` |
| *(no existe)* | **Día típico** (diurnal average): una línea por variable, sombreado del rango si hay min/max | `WS10M`/`T2M` agrupado por hora con pandas `groupby` | Medio |
| *(no existe)* | **Barras mensuales** de viento promedio (y temperatura si hay EPW real) | `resample('M')` sobre `df_clima` | Bajo |
| *(no existe, baja prioridad)* | Gráfico diario (365 puntos) | `resample('D')` | Bajo, pero aporta poco a un simulador eólico |

**No se incluyen** psicrométrico ni degree-days por ahora: dependen de
humedad relativa (no la tenemos) y de temperatura real (San José y la
aproximación por ráster tienen T2M constante = 22°C, un placeholder, no
un dato) -- meterlos ahora sería mostrar un gráfico vacío o falso en 2 de
los 4 caminos climáticos de la app.

## 7. Implementación propuesta

1. **Agregar `plotly` a `app/requirements.txt`** (única dependencia nueva
   -- sin `ladybug`, sin `ladybug-charts`).
2. **Nuevo módulo `engine/paleta_charts.py`** (o constantes en
   `app/app.py`) con `PALETA_CLIMA` (los 10 hex codes de arriba), para no
   depender de la librería Ladybug por 10 strings.
3. **Reescribir `graficar_rosa_vientos` y `graficar_heatmap_clima`** de
   matplotlib a Plotly, mismo dato de entrada, nueva paleta y estilo
   (fondo blanco, grilla fina, título centrado).
4. **Agregar 2 gráficos nuevos** a "CONTEXTO CLIMÁTICO": día típico y
   barras mensuales, con guardas para cuando solo hay `WS10M` (San
   José/aproximación) vs. cuando también hay `T2M` real (EPW real) --
   mostrando solo viento en el primer caso.
5. **Mantener la marca ECO (AZUL `#003C52`/VERDE `#4A7C2F`) en la
   interfaz** (pestañas, botones, headers) -- la paleta térmica
   azul→rojo es específicamente para los datos climáticos, no reemplaza
   la identidad de marca del resto de la app. Es la práctica estándar:
   color de marca para la interfaz, escala de datos separada para los
   gráficos.
6. **Validar en navegador** con San José (sin internet real) y, si es
   posible, un sitio con EPW real para ver ambos casos.

## 8. Estado

Esto es un plan, no una implementación. La rama de trabajo activa es
`claude/refactor-ui-tabs-layout-hmc5wt` (PR
[#2](https://github.com/Sogo2012/ECO-Wind/pull/2)), que ya tiene el
refactor de pestañas hecho. Este plan es el siguiente paso propuesto
sobre esa base.
