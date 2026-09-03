# ECO | Wind — Avance de Proyecto

**Documento de referencia (alcance):** [`plan-tecnico-eco-wind.md`](./plan-tecnico-eco-wind.md)
**Última actualización:** 1 de setiembre, 2026 (Hallazgo 31 — la sensibilización validada
(Hallazgo 21-30) por fin se conecta a `app.py`, reemplazando el mecanismo viejo; Hallazgo 32 —
fichas técnicas de las 11 turbinas + imágenes de producto y logos integrados a la app, con dos
gaps reales flageados (`al13_4m` sin ficha, 4 modelos sin curva de potencia); Hallazgo 33 — bug
real de Dockerfile en producción corregido (`COPY . .`, mismo patrón de DDP-lite/Skyplus), sin
verificar con un build real en este sandbox; Hallazgo 34 — menú lateral que clona la estructura
real de DDP-lite/Skyplus (navegador de secciones, no los 4 tabs), verificado de punta a punta con
Chromium/Playwright real. Hallazgo 19 v3 — consolidado en UN SOLO flujo de búsqueda de clima, igual que DDP-lite/Skyplus: sin selector de modos, estación real siempre, aproximación como fallback automático sólo cuando hace falta; Hallazgo 20 — corrección real en el perfil de viento por altura, z0 de referencia distinto de z0 destino; Hallazgo 21 — vecino más cercano validado por leave-one-out, con un artefacto real de `generar_clima_gwa()` encontrado en el camino; quantile mapping probado (mecánica) y acceso a ERA5/CDS investigado; Hallazgo 22 — mitigación parcial de ese artefacto vía curva de excedencia por residuos: Liberia ya muestra una mejora clara y real con el vecino más cercano; Hallazgo 23 — validación REAL (Colab, no sintética) de quantile mapping contra NASA POWER: mejora real pero más modesta que la prueba sintética; Hallazgo 24 — corrección de rumbo: app internacional, sin anclar a San José, catálogo global de 5,276 estaciones/20 países probado y auto-pivotable en 6 países reales; Hallazgo 25 — NASA POWER descartado como ajuste espacial (falla al revés en terreno accidentado, confirmado con datos reales); GWA generalizado a cualquier país como reemplazo candidato; Hallazgo 26 — validación real de GWA: mucho mejor que NASA POWER pero mixto, el problema está en el ráster crudo de GWA en San José/Finca Favorita, no en el mecanismo de razón; credencial CDS movida a Colab Secrets tras compartirse un token real en el chat; Hallazgo 27 — Köppen-Geiger encuadrado como filtro de selección de donante, no como cuarto candidato al mecanismo de razón de ajuste de magnitud; Hallazgo 28 — validación real de ERA5/CDS: mejor que NASA POWER pero no le gana a GWA en ningún sitio, ~1 hora de cola por congestión real de CDS; Open-Meteo/ERA5-Land agregado como quinta vía sin fricción de acceso; Hallazgo 29 — Limón, 2.8x más cerca de Finca Favorita que San José, resulta un donante PEOR por exposición local, no por distancia; Hallazgo 30 — calibración real de GWA contra 8 estaciones de EEUU: ni elevación ni categorías simples de terreno explican el error, ~±20-35% de ruido sin patrón corregible claro con lo que hay hoy)
**Propósito:** comparar el alcance planeado contra el avance real, y dejar constancia de los
hallazgos que no estaban previstos en el plan original. Se actualiza en cada avance
significativo — no es una foto única.

---

## 1. Estado general

| Fase / Pista | Estado |
|---|---|
| **Fase 1 — Pista A** (motor empírico) | 🟢 Sólida — mecánica y fuentes de datos climáticos (EPW + GWA) validadas con datos reales; z0/afinación fina quedó pendiente para más adelante (decisión del Director del Proyecto) |
| **Fase 1 — Pista B** (motor físico DMST + CFD) | 🟡 Aerodinámica congelada (vía agotada, sobre-predicción sigue abierta, Hallazgo 8); curvas de potencia re-verificadas contra el calculador oficial, sin dudas reales (Hallazgo 12) — módulo estructural ASCE 7 con demanda de anclaje para 5 modelos y carga de clúster conservadora (Hallazgos 9-10, 13); Cilindro Actuador implementado y validado, pero no reproduce el Efecto Bouquet real todavía (Hallazgo 15) |
| **Fase 2** (productización: Streamlit + Cloud Run) | 🟡 Multi-clúster, corrección de densidad, cálculo horario probado (Jensen), perfil de viento por altura corregido (z0 de referencia ≠ z0 destino, Hallazgo 20), gráficos (rosa de vientos, heatmap, curva de duración), 4 sitios con datos climáticos reales propios (San José + Nicoya/Liberia/Finca Favorita) más mapa de búsqueda de estaciones (5,276 en 20 países, por nombre/coordenada/mapa, sin acotar
a Costa Rica) y subida de EPW propio; la sensibilización del punto exacto AHORA usa el mecanismo validado GWA (Hallazgo 31, sin ráster real para el número final), fichas técnicas + imágenes de las 11 turbinas integradas (Hallazgo 32), menú lateral tipo DDP-lite/Skyplus en vez de tabs (Hallazgo 34), y el bug de Dockerfile que rompía la búsqueda en producción está corregido (Hallazgo 33, sin verificar con build real). Falta: PDF, leads, despliegue a Cloud Run, confirmar Hallazgos 31/33 en un entorno con red real (Hallazgos 16-20, 31-34) |

---

## 2. Pista A — Motor empírico, paso a paso vs. el plan

| # | Paso (según el plan, sección 3) | Estado | Notas |
|---|---|---|---|
| 1 | Empaquetar `flower_turbines_curves.py` como módulo base | ✅ Completo | `engine/flower_turbines_curves.py`, importable, autotest reproduce los valores oficiales (Medium Tulip @ 12 m/s: 622.2 W calculado vs. 622.1 W oficial) |
| 2 | Ingesta climática NASA POWER Hourly, validar 8,760 h | ✅ Técnicamente completo, ⚠️ **descartado como fuente primaria** | Ver Hallazgo 1 abajo |
| 3 | Corrección de altura (perfil logarítmico) | ✅ Completo | `wind_at_height()`, autotesteado (en h_target=h_ref da v_ref exacto) |
| 4 | Ensamblar `simular(lat, lon, altura_buje, modelo, N) -> kWh_anual` | ✅ Completo | Validado de punta a punta con datos reales de estación (no solo sintéticos) |
| 5 | Sanity check contra referencia de mercado (Kilowatts UK) | ✅ Completo, **funcionando como se diseñó** | Marcó correctamente el resultado de NASA POWER como fuera de rango — fue la señal que disparó la investigación del Hallazgo 1 |

**No estaba en el plan original, se agregó durante la validación:**

| Agregado | Estado | Por qué |
|---|---|---|
| `load_epw_wind()` — ingesta de archivos EPW/TMYx de estación real | ✅ Completo y validado | Fuente primaria de facto ahora mismo; ver Hallazgo 1 |
| `generar_clima_weibull(A, k)` — reconstrucción estadística vía Global Wind Atlas | 🟡 Código completo y verificado; **datos de entrada (A, k) todavía ilustrativos, no reales** | Ruta para sitios sin EPW cercano; ver Hallazgo 2 |
| Pista C (ERA5 + corrección de sesgo / quantile mapping) | ⚪ Documentada, no implementada | Necesaria solo cuando se requiera estructura horaria real (correlación con demanda de edificio, Fase 2) |

---

## 3. Hallazgos relevantes (no anticipados en el plan)

### Hallazgo 1 — NASA POWER subestima el viento real en el Valle Central (~3x)

Comparación en la **misma coordenada exacta** (Aeropuerto Juan Santamaría, 10.00342327565566,
-84.20332993360161):

| Fuente | Viento medio anual (10m) | % horas bajo cut-in (0.7 m/s) | kWh/año* |
|---|---|---|---|
| NASA POWER (Hourly, `community=SB`, 2023) | 1.30 m/s | 18.8% | 16.5 |
| EPW estación real (TMYx, 15 años, WMO 787620) | 4.03 m/s | 3.3% | 606.8 |

*Escenario de prueba: 3× Medium Tulip en bouquet, buje a 3.0 m.

~3.1x de diferencia en la media de viento se traduce en ~37x en energía anual, por la
relación cúbica de potencia (P ∝ v³).

**Causa raíz (diagnosticada, no solo observada):** NASA POWER deriva del reanálisis
MERRA-2, con celdas de ~50-60 km. Esa resolución promedia/aplana la topografía del Valle
Central (Cordillera Volcánica Central, Cerros de Escazú) y es ciega a la canalización
orográfica que acelera el viento en sitios como el aeropuerto. El EPW, en cambio, ancla a
observaciones reales de estación (NCEI ISD) y usa ERA5 (rejilla más fina, ~31km) solo para
rellenar huecos — por eso captura mejor el clima local.

**Consecuencia arquitectónica (ya adoptada en el notebook):** NASA POWER queda degradado a
respaldo de último recurso, y solo con cautela explícita. La fuente primaria pasa a ser un
EPW de estación real cuando exista uno cerca del sitio.

### Hallazgo 2 — El sandbox de desarrollo no tiene salida a casi ningún host externo

Confirmado directamente (no es un supuesto) que este entorno bloquea, por política de
organización del proxy de red:

- `power.larc.nasa.gov` (NASA POWER)
- `globalwindatlas.info` (Global Wind Atlas)
- `cds.climate.copernicus.eu` (Copernicus CDS / ERA5)
- `help.emd.dk`, `en.wikipedia.org` (investigación general)
- `climate.onebuilding.org` (confirmado 31/ago/2026, dos métodos independientes -- curl y
  WebFetch, ambos con rechazo explícito de política, no un error de configuración. Ver
  Hallazgo 18: Pablo bajó los EPW él mismo con internet real y los subió al chat, mismo patrón
  que EPW/GWA-San José.)
- `www.ladybug.tools` (confirmado 31/ago/2026, mismo patrón -- ver Hallazgo 18)
- `wind-data.ch` (confirmado 31/ago/2026 vía WebFetch, mismo patrón -- ver Hallazgo 20)
- `nominatim.openstreetmap.org`, `photon.komoot.io` (confirmado 31/ago/2026 con curl,
  `connect_rejected` -- geocodificación directa e inversa, ver Hallazgo 19)

**Nota aparte, mismo patrón pero otro tipo de recurso (Hallazgo 19):** no sólo APIs/datos --
también un CDN de JavaScript de terceros queda bloqueado para un navegador real dentro de este
sandbox: `cdn.jsdelivr.net` (Leaflet.js, usado por `folium`) no cargó en una prueba con
Playwright/Chromium real (`net::ERR_TUNNEL_CONNECTION_FAILED`), aunque el HTML/iframe del
componente sí se generó y montó correctamente. El mapa interactivo por eso no se pudo probar
visualmente en este sandbox -- sí se probó todo lo demás (búsqueda Haversine, lista de
estaciones, botones, manejo de error de descarga) sin necesitar el mapa en sí, ver Hallazgo 19.

**Consecuencia práctica:** cualquier fuente de datos que dependa de una llamada de red en
vivo tiene que escribirse y probarse "a ciegas" acá, y validarse recién en Google Colab (que
sí tiene internet normal) o con archivos que alguien con acceso baja manualmente y sube al
repo. Este patrón ya se usó con éxito para el EPW (`datos_clima/`) y se repitió para el
Global Wind Atlas (ver Hallazgo 3).

### Hallazgo 3 — Global Wind Atlas confirmado con datos reales (10m); dos formatos de export no concuerdan entre sí

Pablo exportó del panel del GWA para el punto exacto del aeropuerto, confirmado a 10m: la
curva de excedencia empírica de viento y el mapa mes×hora real, más el archivo `.lib`
(formato WAsP nativo, detalle por rugosidad/altura/sector).

| Fuente | Viento medio (10m) | kWh/año* |
|---|---|---|
| NASA POWER (real) | 1.30 m/s | 16.5 |
| **GWA — panel web (real, confirmado 10m)** | **3.67 m/s** | **387.9** |
| EPW estación real (15 años, TMYx) | 4.03 m/s | 606.8 |
| GWA — `.lib` WAsP, z0=0.030, 10m (referencia, no usado para magnitud) | 5.37 m/s | *(no usado)* |

*Mismo escenario de prueba: 3× Medium Tulip en bouquet, buje a 3.0 m.

GWA (panel web) y el EPW concuerdan razonablemente (~9% de diferencia en la media de
viento) — ambos son fuentes utilizables, y quedan en el mismo orden de magnitud de energía.
Pero el archivo `.lib` da una media ~46% más alta que el panel web para la misma coordenada.
Lectura de trabajo (sin confirmar con documentación oficial del GWA, que sigue bloqueada
desde este sandbox): el `.lib` es el clima "generalizado" reexpuesto a una rugosidad
idealizada uniforme — pensado como insumo para un cálculo de micrositing completo en WAsP
con el terreno real alrededor — mientras que el panel web ya hace ese downscaling específico
para el punto exacto. Por eso el proyecto usa el panel web para la magnitud, y el `.lib`
solo para el wind rose direccional (sectores dominantes: 90°-150°, ~50% del tiempo
combinado — útil más adelante para orientación de bouquets).

---

## 4. Fuentes de datos climáticos — estado comparativo

| Fuente | Resolución | Acceso desde este sandbox | Estado en el proyecto |
|---|---|---|---|
| NASA POWER (MERRA-2) | ~50-60 km | ❌ Bloqueado | Implementado, con sesgo confirmado y documentado. Solo respaldo. |
| EPW / estación real (ISD + ERA5 gap-fill) | Puntual (estación) | N/A — archivo local | ✅ Implementado y validado. Fuente primaria cuando existe estación cercana. |
| Global Wind Atlas (panel web — curva empírica + mes×hora real) | 250 m | ❌ Bloqueado (se usa vía archivos exportados) | ✅ Implementado y validado con datos reales confirmados a 10m. Concuerda razonablemente con EPW. |
| Global Wind Atlas — `.lib` WAsP (rose direccional) | 250 m | ❌ Bloqueado | ✅ Implementado — solo para dirección/sectores, no para magnitud (ver Hallazgo 3) |
| ERA5 + bias correction (Copernicus CDS) | ~31 km + corrección | ❌ Bloqueado | No implementado. Necesita cuenta/API key de Copernicus. Menor prioridad ahora que GWA y EPW ya concuerdan razonablemente entre sí. |

---

## 5. Pista B — Motor físico (DMST + CFD)

🟡 **Primer avance.** Recordatorio de los 4 pasos del plan (sección 3), y estado de cada uno:

| # | Paso | Estado |
|---|---|---|
| 1 | DMST turbina aislada (patentes CA2800765C/US9255567B2, ES2970155T3/AU2019380766B2) | 🟡 Sustentación (NACA 0018) y arrastre (Savonius) construidos y validados por separado; combinados con la arquitectura real de dos niveles de pala (`engine/rotor_combinado.py`) y verificados (Betz + 4 modelos) — combinar bien no resuelve la sobre-predicción, ver Hallazgo 6 |
| 2 | Pérdida dinámica a TSR bajo (Leishman-Beddoes) | ⚪ No iniciado |
| 3 | Efecto clúster (Cilindro Actuador, OpenFOAM offline) | 🟡 Implementado y validado el puerto (`engine/actuator_cylinder.py`, código fuente real de Ning) — pero NO reproduce el Efecto Bouquet real en N=2 (resultado honesto, no forzado). Ver Hallazgo 15 |
| 4 | Estructural (ASCE 7) | 🟡 Módulo construido y validado (`engine/estructural_asce7.py`) — presión dinámica, corte basal, momento de vuelco, frecuencia de vórtices. Demanda de anclaje con patrones reales para 4 modelos + carga de viento (sin anclaje) para Small Tulip; primera aproximación conservadora a carga de clúster. Ver Hallazgos 9, 10 y 13 |

**Lo construido:** `engine/dmst_model.py` (solver DMST de doble tubo de corriente —
simplificado, un factor de inducción por semicírculo upwind/downwind, no multi-tubo por
azimut) + `engine/naca0018_polar.py` (polar aproximado: teoría de perfil delgado +
extrapolación Viterna-Corrigan post-stall; no hay datos XFOIL/experimentales reales
accesibles desde este sandbox). Notebook: `notebooks/pista_b_motor_fisico.ipynb`.

**Bug real encontrado y corregido en el mismo pase:** la primera versión del solver violaba
el límite de Betz (Cp llegó a 1.48, imposible — el máximo teórico es 0.593) por un factor de
4 mal puesto en el coeficiente de empuje del balance de momento. Corregido; el chequeo de
Betz quedó como test explícito en el notebook para que no vuelva a pasar desapercibido.

**Resultado de validación (Medium Tulip, solo sustentación, contra la curva empírica ya
validada de la Pista A):** el DMST predice consistentemente **~2.02x** la potencia empírica
en todo el rango de viento probado (3 a 15 m/s) — misma forma funcional (P~v³), magnitud
razonable para un primer modelo aerodinámico puro sin pérdidas 3D/punta de pala ni
corrección de alta inducción (Glauert).

**Lo que NO funcionó (documentado, no escondido):** el intento más simple de representar el
componente de arrastre tipo Savonius — sumar un Cd extra constante a todos los ángulos de
ataque — da **potencia negativa** (no físico). Penaliza también los ángulos donde el flujo ya
generaba torque limpio, sin capturar la asimetría cóncava/convexa real que sí produce torque
neto a TSR bajo.

### Hallazgo 4 — Validación cruzada en los 4 modelos reales: el ratio DMST/empírico no es constante, y el Savonius solo (patente) ajusta mejor que la sustentación pura

Validando el DMST (solo sustentación) contra los 4 tamaños reales de la línea de producto
(no solo Medium Tulip):

| Modelo | Diámetro | Ratio DMST/empírico (sin corrección Re) | Ratio DMST/empírico (con corrección Re) | Ratio Savonius solo (Cp=0.34 de la patente) |
|---|---|---|---|---|
| Small Tulip | 0.55 m | 5.43x | 6.68x | 3.66x |
| Medium Tulip | 1.18 m | 2.02x | 3.21x | 1.37x |
| 3-M Tulip | 1.80 m | 2.06x | 3.76x | 1.39x |
| Large Tulip | 2.50 m | 1.24x | 2.52x | 0.83x (subestima) |

**El ratio cae con el tamaño** — patrón consistente con Reynolds (a mayor diámetro, mayor
cuerda, mayor Re, el perfil real se acerca más al comportamiento ideal de la teoría de perfil
delgado).

**Corrección por Reynolds:** implementada (`Cd0(Re) ~ Re^-0.5`, reducción de Cl_max/stall a
Re bajo). Resultado honesto: reduce la dispersión *relativa* entre modelos (el spread entre
el más y el menos afectado baja de ~4.4x a ~2.65x) pero **empeora el ajuste absoluto en los
4 modelos**. Confirma que el efecto es real/plausible, pero calibrarlo con confianza necesita
un polar NACA 0018 medido (XFOIL o túnel de viento) a los Reynolds reales del producto
(3×10⁵ a 1.6×10⁶ según el tamaño) — no disponible desde este sandbox. **No se activa por
default** (`re_dependiente=False` es el comportamiento por defecto en `resolver_dmst()`).

**Componente Savonius, geometría propia de la patente ES2970155T3** (distancia entre
bordes=3.5×diámetro del eje, superposición=0.2×diámetro del eje, cuerda=6.6×diámetro del eje,
diámetro total=9.7×diámetro del eje, **Cp=0.34 ya reportado en la patente, usado tal cual sin
ajustar**): queda **más cerca de la curva empírica que el modelo de sustentación pura en los
4 modelos** (incluso en Large, donde subestima — el error absoluto es igual de menor). Sugiere
que el mecanismo de arrastre pesa más de lo que un análisis de sustentación aislado captura,
sobre todo a escala chica. No se suma al resultado del DMST — se deja como estimación
independiente, ya que en ese momento **seguía sin resolverse cómo combinar ambos
componentes** en el modelo de la pala híbrida real. Ver Hallazgo 5 para el intento de
resolverlo.

**Próximos pasos de Pista B fuera del alcance de este ciclo:** pérdida dinámica a TSR bajo
(Leishman-Beddoes), efecto clúster vía Cilindro Actuador (RANS-AC, OpenFOAM, offline/batch),
y estructural (ASCE 7, con los Cd de pala ya conocidos: 1.2 convexa / 2.3 cóncava).

Acordado con Pablo: se arranca Pista B solo después de que la Pista A esté sólida
(secuencial, no en paralelo — recomendación del plan, confirmada).

### Hallazgo 5 — Combinar sustentación y arrastre en un polar único: la fórmula ya no era el problema, el régimen de TSR sí

Pablo pidió continuar con la pieza central pendiente de Hallazgo 4: cómo combinar el
componente de sustentación (DMST) y el de arrastre (Savonius) sin simplemente sumarlos (el
atajo de un `Cd` extra uniforme ya había dado potencia negativa, no físico).

**Lo construido:** `engine/polar_hibrido.py` — un único polar para la pala real, no dos
mecanismos separados. Idéntico al NACA 0018 simétrico en sustentación (región lineal Y
post-pérdida). El arrastre post-pérdida es **asimétrico**: Cd→2.3 cuando la cara cóncava
enfrenta el flujo, Cd→1.2 cuando enfrenta la convexa (ambos valores de la ficha *External
Load Calculations 2m & 5m.pdf* de Pablo), seleccionado por el signo del ángulo de ataque
local — supuesto de convención de signo no confirmado contra el CAD real de la pala.

**Bug real encontrado y corregido en el mismo pase:** la primera versión metía el `Cd_max`
asimétrico dentro de la fórmula completa de Viterna-Corrigan (Cl y Cd juntos). Esa fórmula
liga la sustentación post-pérdida al `Cd_max` usado — subir `Cd_max` a 2.3 no solo agregaba
arrastre, también **inflaba la sustentación post-pérdida ~10-15%**, empeorando la
sobre-predicción en vez de corregirla (verificado numéricamente antes de descartar el
enfoque). Corregido: la sustentación post-pérdida ahora se calcula igual que en el NACA0018
puro; solo el arrastre usa la asimetría.

**Verificación 1 — Betz:** con el polar híbrido ya corregido, en el rotor "de libro" del
Paso 2, Cp máximo = 0.514 en TSR=3 (referencia NACA puro: 0.522 en TSR=3) — dentro del
límite de 0.593 en ambos casos.

**Verificación 2 — los 4 modelos reales:** con `re_dependiente=False` (config por defecto,
igual que el baseline de Hallazgo 4), el polar híbrido da **exactamente los mismos números
que el DMST de sustentación pura** en los 4 modelos (5.43x / 2.02x / 2.06x / 1.24x, bit a
bit idénticos) — el mecanismo de arrastre asimétrico no cambió nada.

No es casualidad numérica — se investigó la causa en vez de asumirla. Diagnóstico directo:
en el TSR que el propio modelo elige como óptimo (TSR=3 para Small Tulip), el ángulo de
ataque máximo alcanzado durante toda la revolución es 9.8°, por debajo del ángulo de pérdida
del polar (12°) — **la pala nunca entra en pérdida**, que es la única región donde el
arrastre asimétrico actúa por diseño. Barriendo TSR completo (0.3 a 4.0) se confirma que el
mecanismo de arrastre sí cambia el Cp en TSR bajo (0.3–2.0, con diferencias reales tanto
positivas como negativas), pero incluso su mejor punto ahí (TSR≈0.7, Cp≈0.085) queda muy por
debajo del Cp de sustentación pura en TSR≈3 (Cp≈0.50).

**Conclusión honesta:** esto no era un problema de fórmula del polar (esa parte ya quedó
corregida, verificada y Betz-compatible) — es que sustentación y arrastre dominan en
regímenes de TSR distintos y casi disjuntos: la sustentación necesita TSR medio-alto
(~3-4) para mantenerse antes de pérdida, mientras que el mecanismo tipo Savonius necesita
pérdida profunda y sostenida a TSR bajo (la propia patente ES2970155T3 reporta
TSR_óptimo≈0.5). Una búsqueda de "máximo Cp posible sobre TSR" — que es lo que este solver
hace — elige siempre el régimen de sustentación, porque da un Cp mayor en el papel; nunca
"mezcla" ambos mecanismos en un punto intermedio real.

**Lo que falta no es más ajuste de polar — es la curva de par-velocidad (o el RPM operativo
típico) del generador/carga eléctrica real del producto.** Sin ese dato, el modelo no tiene
forma de saber en qué TSR opera de verdad la turbina, y por tanto tampoco de saber si el
comportamiento real está dominado por sustentación, por arrastre, o por una mezcla real de
ambos en algún punto intermedio — que es justamente lo que se necesitaría para calibrar la
combinación con confianza. Esto se deja como el bloqueo identificado, no como una pregunta
abierta sin explorar.

### Hallazgo 6 — Las patentes reales (no el repo) muestran que la combinación es de dos niveles de pala, no un polar híbrido; y que combinarla bien no resuelve la sobre-predicción

Pablo compartió directamente los PDFs reales de las tres patentes clave (`US9255567B2`,
`CA2800765C`, `AU2019380766B2`) al notar que el repo solo tenía placeholders de 11 bytes en
`documentos_tecnicos/` (ver más abajo). Leerlas completas cambió el entendimiento de esta
pista en dos formas:

**1) Todas las cifras usadas hasta ahora quedaron verificadas palabra por palabra contra el
documento real** — sin discrepancias de fondo: Cd=1.2 convexa/2.3 cóncava (`External Load
Calculations 2m & 5m.pdf`, leído vía Drive), CTDR=0.25-0.35 (3 palas) / 0.25-0.45 (2 palas),
y los cuatro ratios de geometría Savonius (distancia=3.5×eje, superposición=0.2×eje,
cuerda=6.6×eje, diámetro total=9.7×eje) confirmados exactos contra el ejemplo numérico
propio de la patente (eje=100mm → 350/20/660/970mm). Único ajuste de precisión: el
TSR óptimo del Savonius es **0.511** (no 0.5 como se venía redondeando), y la patente
aclara que ese óptimo **escala con el tamaño absoluto de la turbina** (≈1.22 para un rotor
del doble de diámetro) — un dato de calibración que no se tenía antes.

**2) La arquitectura real para combinar sustentación y arrastre no es un polar híbrido de un
solo elemento** (la hipótesis explorada en Hallazgo 5) — es **dos niveles de pala en el
mismo eje**: un nivel de arrastre (interno) y uno de sustentación (externo), girando a la
misma velocidad angular. Cita textual de `US9255567B2` (reivindicación 11): *"An internal
set of drag blades... An external set of lift blades, wherein the maximally efficient rpm
of the two sets are within 20% of each other."* Y la fórmula de rpm objetivo del generador:
*"operating most efficiently at a rpm plus or minus 25% of 10 divided by the product of
'pi' and the turbine diameter"* (a V=10 m/s) — que expresada como TSR da **λ≈1.0,
independiente del diámetro**, verificado contra el propio ejemplo numérico de la patente
(turbina de arrastre D=2.5m a 76 rpm + palas de sustentación a 86 rpm, ambas ~TSR=1.0).

Implementado en `engine/rotor_combinado.py`: sustentación (DMST) evaluada en TSR=1.0 fijo
(no en su propio TSR óptimo) + arrastre (Savonius, Cp=0.34) sumados. **Resultado honesto:**
la sobre-predicción prácticamente no cambia — 5.39x/2.01x/2.04x/1.23x (Small/Medium/3M/
Large), casi idéntico al 5.43x/2.02x/2.06x/1.24x de sustentación sola en su propio óptimo
(Hallazgo 4). Combinar los dos mecanismos correctamente **no resuelve la brecha** — apunta a
que la causa dominante de la sobre-predicción no es un mecanismo aerodinámico faltante, sino
algo que afecta a ambos por igual (pérdidas 3D/de punta de pala que escalan con el tamaño, y
posiblemente pérdidas electromecánicas de generador/controlador que ningún cálculo de esta
pista incluye todavía).

**Límite real encontrado, no escondido:** sumar los dos niveles como discos actuadores
independientes es compatible con Betz en TSR=1.0 (Cp≈0.50), pero **rompe Betz en TSR=1.25**
(borde superior de la tolerancia ±25% que la propia patente declara; Cp≈0.61 > 0.593) — el
término de sustentación sigue creciendo con TSR mientras el de arrastre se mantiene
constante (Cp=0.34 fijo, sin curva Cp(TSR) completa disponible para ese nivel). Documentado
como limitación explícita del modelo: una versión más rigurosa necesitaría resolver una
inducción conjunta entre ambos niveles, no sumarlos de forma independiente.

**Problema de datos real encontrado en el repo (separado del hallazgo anterior), ya
resuelto:** cada PDF/DOCX/PNG/JPG en `documentos_tecnicos/` (91 archivos) era un placeholder
de 11 bytes, no el contenido real — causado por el commit `e53ebf5` ("Add files via upload",
Pablo, 29/ago), donde el subidor web de GitHub no llevó el contenido binario. Resincronizado
desde el Drive del proyecto (90 de 91 — falta solo el manual de instalación de SolArk,
~6.5MB, documentación de un inversor de terceros, no de Flower Turbines. **Decisión del
Director del Proyecto (30/ago/2026): no es necesario por ahora, se deja pendiente sin
prioridad.**). Cada archivo se emparejó verificando el contenido contra la carpeta del repo,
no solo el nombre — Drive tiene archivos duplicados con el mismo nombre en carpetas
distintas (ej. "Medium Tulip Turbine.pdf" existe como ficha técnica, como declaración CE, y
como guía de inicio rápido).

**Verificación adicional de la Matriz Maestra de Potencia (N=1-10, bouquet):** Pablo compartió
directamente la tabla completa (390 puntos: 3 modelos × 10 tamaños de clúster × 13 velocidades
de viento, 3-15 m/s) para confirmar que se estaba hablando de la misma fuente. Verificado
punto por punto contra `bouquet_multiplier()`: peor error relativo 2.9% (puro redondeo a 1
decimal en la tabla origen, consistente con lo que ya documentaba el código). Confirma que es
exactamente la misma matriz que ya validó la fórmula M(N)=exp(0.21103·(N-1)) — no había nada
nuevo que incorporar.

**Con el contenido real ya disponible, verificación cruzada de las fichas técnicas:**
diámetros de Small/Medium/3-M/Large Tulip (0.55/1.18/1.80/2.50m) confirmados exactos contra
`flower_turbines_curves.py` en las fichas técnicas Y en `Turbine Diameters.pdf`(tercera
fuente independiente) — **el diámetro del Large Tulip queda confirmado en 2.50m** (no 2.40m,
ver más abajo). El AL13 Power Tower ahora tiene ficha técnica real por primera vez: 1.7m de
diámetro de pala (antes sin dato confiable), 1kW con 2 módulos hasta 5kW con 8, ≈350W por
módulo a 12 m/s. **Discrepancia real encontrada:** el coeficiente `al13_2m` ya en
`flower_turbines_curves.py` predice 1523.7W a 12 m/s — más del doble de lo que implica la
ficha real (~700-1000W para un stack de 2 módulos). El comentario original en el código ya
avisaba que esos coeficientes eran "leídos aproximadamente de curvas suaves de un PDF" — con
la ficha real ya disponible, los 4 coeficientes AL13 (`al13_2m/4m/6m/8m`) necesitan
recalibrarse. No se tocó el motor todavía — queda como pendiente explícito.

**Aclaración sobre `informe-plan-simulador-web-vawt.md`:** este documento (ya real, antes
placeholder) incluye un motor de simulación en JavaScript completo y distinto al usado en
Pista A/B — curvas de potencia por tabla de interpolación (no P=k·v³ continuo) y un
multiplicador de bouquet escalonado (1.0/1.25/2.00/2.28, no la exponencial suave ya
validada). También lista el diámetro del Large Tulip como 2.40m. Consultado con Pablo:
**`flower_turbines_curves.py` es el vigente** ("es lo que comunica el fabricante en su sitio
web") — el informe .md queda como documento de planificación/exploración, no como fuente de
verdad; su cifra de 2.40m para el Large Tulip es un error de ese documento, no del motor
usado hasta aquí (que sigue en 2.50m, ahora triple-confirmado).

### Hallazgo 7 — Inducción conjunta: mejora real y consistente, con una limitación nueva y honesta

De las dos hipótesis que dejó Hallazgo 6 para la sobre-predicción residual (pérdidas
electromecánicas, e inducción conjunta entre los dos niveles de pala), se atacó la segunda
por ser la más directamente implementable sin datos externos nuevos.

**Lo construido:** `potencia_combinada_induccion_conjunta()` en `engine/rotor_combinado.py`
— en vez de sumar dos discos actuadores independientes (cada uno asumiendo que ve el viento
V_inf sin perturbar, como en Hallazgo 6), resuelve **un solo factor de inducción compartido**
a partir del empuje total (sustentación + arrastre) sobre el mismo disco. Simplificación
deliberada respecto al DMST de doble tubo de corriente: aquí se usa un solo tubo (integración
0 a 2π en una sola pasada) porque partir el empuje de arrastre entre upwind/downwind
exigiría una regla de reparto sin datos que la respalden — mejor una asunción menos que una
arbitraria. El nivel de arrastre se modela como un disco actuador ideal escalado por un
factor de eficiencia η=0.34/(16/27)≈0.573 (para que su pico coincida exactamente con el
Cp=0.34 de la patente en a=1/3) — una aproximación de ingeniería explícita, no una medición
directa de cómo varía el Cp del Savonius con la inducción.

**Resultado honesto — mejora real y consistente en los 4 modelos:**

| Modelo | Razón (discos independientes) | Razón (inducción conjunta) |
|---|---|---|
| Small Tulip | 5.39x | 4.61x |
| Medium Tulip | 2.01x | 1.72x |
| 3-M Tulip | 2.04x | 1.75x |
| Large Tulip | 1.23x | **1.05x** (casi exacto) |

También corrige la violación de Betz que Hallazgo 6 encontró en TSR=1.25 (Cp baja de ~0.61 a
~0.54, dentro del límite).

**Pero con una limitación nueva, encontrada y no escondida:** el factor de inducción queda
pegado en el techo numérico del modelo (a=0.49) en los 4 modelos reales al TSR objetivo —
señal de que el sistema combinado opera en la zona de inducción alta donde la teoría de
momento simple (Cp=4a(1-a)², sin corrección de Glauert) deja de ser confiable. La mejora es
real y consistente, pero ocurre en un régimen que en rigor necesitaría esa corrección para
confirmarse con confianza fuera del rango TSR 0.75–1.25 (donde sí se mantiene Betz-compatible
en todo momento; por encima, TSR≥1.5, vuelve a romper Betz por la misma causa).

**Conclusión (de este paso — ver Hallazgo 8 para la corrección):** la inducción conjunta
parecía ser la pieza que faltaba — no resolvía del todo la brecha pero la reducía de forma
consistente, y exponía con evidencia concreta que la corrección de Glauert era el siguiente
paso necesario.

### Hallazgo 8 — Con Glauert implementado correctamente, la mejora de Hallazgo 7 resulta ser un artefacto: la sobre-predicción empeora, no mejora

Se implementó la corrección empírica de Glauert a alta inducción (estándar, ver Hansen
*Aerodynamics of Wind Turbines* o Manwell et al. *Wind Energy Explained*: para a≤0.2,
CT=4a(1-a) igual que antes; para a>0.2, CT=4[0.04+0.6a], una recta continua en valor y
pendiente con la parábola en a=0.2, que sigue creciendo con `a` sin techo — ya no hace falta
el recorte artificial en a=0.49 que traía Hallazgo 7). Nota de precisión: una fuente externa
sugirió `ac=1/3` como umbral — eso es un número distinto (el `a` del pico de Cp del disco
ideal), no el umbral de Glauert; se implementó el valor estándar (ac=0.2), verificado con
ida-y-vuelta a→CT→a exacta y continuidad de valor y pendiente en el punto de empalme antes de
confiar en los resultados.

**Con la inducción resuelta correctamente (no recortada), el resultado honesto revierte el de
Hallazgo 7:**

| Modelo | Discos independientes (H6) | Inducción conjunta, recortada (H7) | Inducción conjunta + Glauert (H8) |
|---|---|---|---|
| Small Tulip | 5.39x | 4.61x | 5.68x |
| Medium Tulip | 2.01x | 1.72x | 2.12x |
| 3-M Tulip | 2.04x | 1.75x | 2.15x |
| Large Tulip | 1.23x | 1.05x | 1.29x |

El "casi exacto" de Large Tulip (1.05x) de Hallazgo 7 era un artefacto del recorte artificial
en a=0.49, que suprimía potencia de forma no física — no una mejora real. Con Glauert, la
sobre-predicción es peor que con discos independientes en los 4 modelos.

**Lo que sí es una mejora real y verificada:** Betz se respeta ahora en todo el rango de TSR
probado (0.3 a 5.0), sin ninguna excepción — antes rompía en TSR=1.25 (H6) y de nuevo en
TSR≥1.5 (H7, por el recorte). Ese problema queda genuinamente cerrado.

**Conclusión:** la vía aerodinámica (combinar los dos niveles, resolver la inducción
conjunta, corregir a alta inducción con Glauert) está agotada — cada pieza se implementó
correctamente y se verificó, y ninguna cierra la brecha de sobre-predicción; de hecho, la
versión más rigurosa (con Glauert) da el peor ajuste de todos los intentados. Esto aumenta la
confianza en que la causa dominante no es aerodinámica sin resolver, sino la otra hipótesis
de Hallazgo 6 que sigue sin explorar: pérdidas electromecánicas de generador y controlador de
carga.

### Hallazgo 9 — Primer módulo estructural ASCE 7, validado contra cargas reales de Flower Turbines

Con la aerodinámica congelada (Hallazgo 8), se arrancó el Paso 4 de la Pista B: cargas de
viento estructurales según ASCE 7-16/22, sobre el mástil/pedestal de montaje.

**Verificación de fuentes antes de implementar (no se asumieron las fórmulas de memoria):**
`documentos_tecnicos/documentos de referencia/Simulación VAWT y Efecto Cluster.docx` describe
el marco teórico ASCE 7, pero sus fórmulas están insertadas como **imágenes PNG dentro del
.docx**, no como texto ni objetos de ecuación nativos — el texto plano las pierde por
completo (aparecen como huecos vacíos). Se extrajeron las imágenes del archivo (un .docx es
un .zip) y se revisaron visualmente antes de escribir una sola línea de código. Las cuatro
fórmulas confirmadas coinciden exactamente con lo esperado de ASCE 7 estándar:

- $q_z = 0.613 \cdot K_z \cdot K_{zt} \cdot K_d \cdot V_{basic}^2$ (Pa)
- $F_w = q_z \cdot G \cdot C_{fs} \cdot A_f$ (N)
- $M_w = F_w \times z_{cg}$ (N·m)
- $f_s = St \cdot V_\infty / D$ (Hz)

**Lo construido:** `engine/estructural_asce7.py`, con `calcular_cargas_viento_asce7()`
implementando las cuatro fórmulas de arriba, usando Cd=2.3 (cara cóncava, peor caso, de
`External Load Calculations 2m & 5m.pdf`, re-confirmado en este mismo commit) y St=0.2 para
cilindros circulares.

**Validación honesta contra el Frotor real de la propia ficha de Flower Turbines** (turbina
de referencia con pala de 2.0m, D≈1.108m — geometría similar a Medium Tulip, no idéntica):
el corte basal calculado salía **25-30% más bajo** que el Frotor real reportado a las mismas
velocidades (2.03 vs 2.7 kN a 30 m/s; 3.98 vs 5.3 kN a 42 m/s) — investigado en vez de
dejado sin explicar:

1. El **Cd efectivo implícito** en el Frotor real (retro-calculado con la física simple
   F=0.5·ρ·Cd·A·V²) es ≈2.21 — muy cercano al Cd=2.3 de peor caso usado aquí. Confirma que
   la convención de área frontal (D×H, la misma del resto de la Pista B) y el Cd asumido son
   razonables — el hueco no viene de ahí.
2. Quitando los factores Kd y G de ASCE 7 (que el cálculo interno simple de Flower Turbines
   no tiene motivo para incluir, al no ser un documento ASCE 7 formal), los números
   coinciden bien: 2.81 vs 2.7 kN, 5.51 vs 5.3 kN.

**Conclusión:** el hueco es exactamente Kd·G=0.85·0.85=0.72 — la diferencia esperada y
correcta entre "fuerza de arrastre cruda" (lo que reporta la ficha del fabricante) y "carga
de diseño según código" (lo que exige ASCE 7, con sus factores de reducción por
direccionalidad y promediado de ráfaga). No es una señal de mala calibración del módulo.

**Limitaciones conocidas, ya documentadas en el propio código:** Kz se trata como constante
1.0 (en rigor depende de la altura y la categoría de exposición); Kd=0.85 es el valor típico
para edificios, no confirmado contra la tabla ASCE 7 real para una estructura cilíndrica
esbelta como este mástil; G=0.85 es el valor de "estructura rígida" — el propio documento de
referencia señala que un mástil con componentes rotativos necesitaría el factor de ráfaga
flexible (Gf), que depende de la frecuencia natural del pedestal, dato no disponible; la
frecuencia de vórtices (fs) solo da la frecuencia de excitación, no evalúa resonancia real
sin la frecuencia natural de la estructura de soporte.

**Actualización — Pablo compartió 3 documentos reales adicionales que no se habían revisado
todavía** (subidos antes pero no abiertos hasta este punto — corregido en cuanto se detectó):

- **`3 meter AL13 Side Forces at 50 mps.pdf`:** dato real independiente — F=13,000 N,
  Torque=31,200 N·m a 50 m/s, "área transversal de pala" ≈5 m², altura total 4.4m. El Cd
  efectivo implícito (≈1.70) **no coincide** con el ≈2.21 encontrado en External Load
  Calculations — es más cercano a un promedio de las dos caras (1.2/2.3→1.75) que al peor
  caso solo. Diferencia real entre fuentes, documentada, **no resuelta**: podría deberse a
  que "área transversal de pala" en este documento no sea la misma convención D×H (caja
  envolvente) usada en el resto de la Pista B, sino el área real proyectada de las palas —
  necesitaría geometría CAD real para reconciliarse con confianza.
- **`Big Pedestal Concrete Base ASSY` (Large Tulip) y `Power Tower Concrete Base ASSY`
  (AL13):** planos reales de la base de concreto — patrones de anclaje con varillas roscadas
  M18×2.5 (12 unidades, patrón cuadrado 874.4×874.4mm para Large Tulip, 774.4×774.4mm para
  AL13, más un patrón circular de 6 unidades para un accesorio de poste de soporte separado,
  explícitamente no usado en instalaciones standalone del Power Tower). **Nota importante de
  alcance, del propio plano:** *"CONCRETE BASE DIMENSIONS AND OTHER PROPERTIES WILL BE
  PROVIDED BY A CIVIL ENGINEER, NOT IN RESPONSIBILITY OF FLOWER TURBINES"* — Flower Turbines
  solo especifica el patrón de anclaje, no diseña la base de concreto completa.

**Agregado a `engine/estructural_asce7.py`:** `tension_maxima_pernos()`, usando los patrones
reales de anclaje (`PATRONES_ANCLAJE`). Da la **demanda** de tensión en el perno más cargado
a partir del momento de vuelco — NO evalúa si el perno M18×2.5 aguanta (eso requiere la
capacidad admisible del perno y del concreto, responsabilidad del ingeniero civil según los
propios planos). Caso de prueba: Large Tulip a 40 m/s ráfaga, a nivel de piso →
Mw=50.93 kN·m → tensión estimada ≈9.71 kN en el perno más cargado (cálculo simplificado de
cupla en el ancho exterior del patrón, no un análisis riguroso de grupo de anclajes tipo ACI
318 Apéndice D).

### Hallazgo 10 — Base de las turbinas pequeñas: plano real incorporado, y una discrepancia real sin resolver entre dos documentos internos de Flower Turbines

Pablo pidió analizar la base de las turbinas pequeñas, compartiendo 3 documentos — 2 nuevos
sin revisar todavía (`Small Pedestal Concrete Base ASSY`, `Calculation of forces.pdf`) y
`Turbine Diameters.pdf` (re-confirmado, idéntico a lo ya usado).

**`Small Pedestal Concrete Base ASSY` — plano real, incorporado a `PATRONES_ANCLAJE`:** cubre
Medium Tulip (2m) y 3-M Tulip (3m) con el **mismo patrón** — 12 varillas roscadas M14×2 (más
delgadas que las M18×2.5 de Large Tulip/AL13), patrón cuadrado 602.5×602.5mm, espaciado
370mm, empotramiento 80mm, 311kg de peso distribuido de referencia. **Aclaración de nombres,
importante:** "Small Pedestal" es un nombre de *tamaño de base* (relativo a "Big Pedestal"),
**no** el producto "Small Tulip" (0.55m diámetro, 1.15m de pala) — no hay plano de base
documentado todavía específicamente para ese modelo, el más pequeño de la línea. Caso de
prueba con este patrón: 3-M Tulip a 40 m/s ráfaga → Mw=13.20 kN·m → tensión estimada
≈3.65 kN en el perno más cargado.

**`Calculation of forces.pdf` — diagrama de cuerpo libre real, con una discrepancia real no
resuelta.** El documento reporta (probablemente para 3-M Tulip: W=3.9kN≈400kg coincide con la
ficha técnica, y la altura de aplicación de T, 2.35m, coincide con la mitad de la altura de
pala más el pedestal): T=1.08 kN a 30 m/s, W=3.9 kN, R1=1.44 kN, R2=5.34 kN. Verificado antes
de usarlo, no aceptado tal cual:

1. **Equilibrio vertical simple no cierra:** R1+R2=6.78 kN ≠ W=3.9 kN (diferencia de 2.88 kN).
   No se fuerza una explicación — la base en este documento es tipo trípode/patas (no la
   placa+pernos de los otros planos), así que R1/R2 podrían no ser reacciones verticales
   puras en el sentido simple que se asumió al chequear. Pregunta abierta, no resuelta.
2. **Cd efectivo implícito en T=1.08kN (≈0.36, con A=D×H=5.4m² del 3-M Tulip) está muy por
   debajo** tanto del peor caso (2.3) como del Cd≈2.21 ya validado en `External Load
   Calculations` para lo que parece ser la misma turbina (cuyo Frotor a 30 m/s es 2.7 kN —
   2.5 veces más que este T=1.08 kN).

**Hipótesis más probable, no confirmada:** este documento podría representar un caso de carga
distinto — empuje de **operación normal** (rotor girando, generando sustentación) en vez del
caso extremo de "ambas palas totalmente cargadas" (cuerpo romo estático) que usa `External
Load Calculations`. Es una discrepancia real entre dos documentos internos de Flower
Turbines, documentada honestamente — **no se usó este valor de T en el módulo**, queda como
hallazgo abierto en vez de forzarse a encajar.

### Hallazgo 11 — Revisión completa de 9 manuales de Flower Turbines: una corrección real en las curvas del AL13, contaminación de plantilla explicada, y varias discrepancias reales sin forzar

Pablo compartió los manuales completos ("Quick Start Guide 2025") de los 5 modelos (Medium
Tulip, AL13 Power Tower, Small Tulip, Large Tulip, 3-M Tulip — 18 a 23 páginas cada uno) y
pidió revisar qué más se podía extraer. Se procesaron en paralelo con 5 agentes (uno por
documento, lectura completa página por página), y luego, en un segundo envío, 4 documentos
más: dos hojas "Specs_2025" de una sola página (Medium y 3-M Tulip — fichas técnicas limpias,
distintas de los Quick Start Guides), `Guidance on Spacing Flower Turbines.pdf` (5 páginas) y
`Installation Manual for the ZW-Pole.pdf` (1 página). Dos hallazgos de los agentes se
verificaron a mano releyendo las páginas originales antes de actuar sobre ellos (ver abajo).

**Corrección real, verificada, aplicada al código — coeficientes del AL13 (`engine/flower_turbines_curves.py`).**
El manual del AL13 sí trae una tabla numérica oficial (Tabla 2, pág. 5, "Power Output of A
Single Turbine by Wind Speed", 31 puntos de 0 a 15 m/s, columnas 2m/4m/6m/8m de altura de
montaje) — antes solo se tenía una lectura aproximada de una gráfica (confianza MEDIA). Al
releer la tabla directamente se encontró que **dos de sus columnas están corruptas por un
error de generación/copiado en el PDF fuente**: la columna "Wind Speed (mph)" resultó ser una
copia exacta de la columna "8m (height)" de esa misma tabla (no una conversión real de
unidades — a 8.5 m/s dice "483.4 mph", imposible), y la columna "Power Output (Watts)" es una
copia exacta de la columna "2m (height)". Como consecuencia colateral, la columna "8m
(height)" en esta tabla específica queda con valores **físicamente imposibles** (más bajos que
"6m" al mismo viento — la potencia no puede bajar al subir la altura de montaje), así que
tampoco es utilizable. Las columnas "2m", "4m" y "6m", en cambio, son limpias y ajustan
EXACTO a P=k·v³ en los 31 puntos (verificado en varios puntos independientes, no solo el
extremo). Con eso se corrigieron `al13_2m` (k: 0.881790→1.612800), `al13_4m` (k: 1.806870→
2.476800) y `al13_6m` (k: 3.095980→3.456000) — un cambio grande, ~1.8x más potencia que antes
para 2m/4m. `al13_8m` se dejó SIN TOCAR (sigue con la lectura aproximada anterior, confianza
MEDIA) porque su única fuente limpia disponible resultó corrupta — sigue pendiente conseguir
un dato confiable para esa altura. Validado corriendo el módulo (`python3
engine/flower_turbines_curves.py`): las 6 comparaciones nuevas (2m/4m/6m a 8.5 y 15 m/s)
calzan exactas contra la tabla oficial.

**Hallazgo transversal que explica varias "contradicciones" como una sola causa raíz:** los 5
Quick Start Guides comparten una plantilla, y varios párrafos NO se personalizaron por modelo
— texto genérico copiado sin actualizar. Ejemplos concretos encontrados por los agentes: el
manual de Medium Tulip describe el generador como "100W nominal, 200W pico" (p.11) — el mismo
texto EXACTO aparece en los manuales de Small Tulip Y Large Tulip, pese a que sus curvas de
potencia reales llegan a ~121W, ~2,770W y ~10,125W respectivamente a 15 m/s (una diferencia de
83x entre Small y Large que un mismo generador de 100W no podría explicar). Las nuevas hojas
"Specs_2025" (más confiables, de una sola página, sin relleno de plantilla) confirman esto:
Medium Tulip = **500W nominal** (no 100W), 3-M Tulip = **1000W nominal**. Mismo patrón en
otros lugares: la tabla de grasas del manual del AL13 está titulada "Medium Tulip Turbines"
(p.16); la lista de hardware del AL13 menciona "Large Tulip Turbine" (p.13); el manual de
Large Tulip titula sus propias tablas de potencia "single Small Tulip turbine" en un punto
(p.5); la tabla de grasas de Small Tulip dice "3m Tulip Turbines" (p.14); y el foundation
Table 4 de Medium Tulip se titula "Large Flower Turbine" en el texto pero "Medium Tulip
Turbines" en la tabla misma. Conclusión práctica: cuando un dato de un Quick Start Guide
parece un outlier o contradice el sentido común del modelo, conviene sospechar primero de
contaminación de plantilla antes que de un error de medición real — y preferir, cuando exista,
la hoja "Specs_2025" de una sola página sobre el Quick Start Guide para ese mismo dato.

**Validaciones cruzadas positivas (sin cambios necesarios, solo más confianza):** las hojas
Specs_2025 confirman de forma independiente varios números ya usados en el código — diámetro
de Medium Tulip 1.18m (igual al usado en `rotor_combinado.py`/notebook), diámetro de 3-M Tulip
1.8m y altura total 4.07m y peso 400kg (iguales a los usados en Hallazgo 10), y el patrón de
anclaje 12×M14×2 del 3-M Tulip (plano de apéndice del propio Quick Start Guide, coincide con
`Small Pedestal Concrete Base ASSY` ya incorporado). El plano de apéndice del Large Tulip
(12×M18×2.5, patrón 874.4×874.4mm) también confirma exactamente `Big Pedestal Concrete Base
ASSY` ya incorporado. La tabla completa de 31 puntos del 3-M Tulip (recién extraída) ajusta
exacta al coeficiente que ya estaba en el código (antes anclado a un solo punto oficial, ahora
con tabla completa — confianza sube de MEDIA a ALTA, sin cambiar el valor de k).

**Datos nuevos de valor, no incorporados aún al código (para cuando se retomen esas líneas):**
- `Guidance on Spacing Flower Turbines.pdf`: llena directamente el pendiente del "efecto
  clúster". Regla de espaciamiento ideal: diámetro×1.25 (centro de eje a centro de eje),
  aceptable 1.1–1.3×; ángulo ideal respecto al viento predominante 15° (funciona de 0° a 30-45°
  según la página del propio documento — hay una inconsistencia menor entre páginas ahí
  mismo); separación entre filas ideal 5×diámetro, mínimo 3×diámetro; dos filas adyacentes solo
  recomendadas con viento ≥5 m/s (o ≥5.5 m/s en una config. de 4 filas — también inconsistente
  entre páginas del propio documento). Un ejemplo del documento da una regla de espaciado
  mínimo dentro de una fila como "diámetro×0.1", pero el ejemplo numérico que sigue (10
  turbinas de 1m diámetro con 0.9m de espacio entre ellas) implica en realidad 0.9×diámetro, no
  0.1× — otra inconsistencia aritmética real dentro del propio documento del fabricante,
  reportada tal cual, sin intentar adivinar cuál de las dos es la correcta.
- Especificación eléctrica de salida grid-tie confirmada en las hojas Specs_2025: **240VAC
  /1PH/60Hz o 230VAC/1PH/50Hz** — dato nuevo, relevante para cuando se retome la investigación
  de pérdidas electromecánicas (pendiente abierto).
- Velocidad de corte operacional del 3-M Tulip: "el charge controller frena alrededor de 12
  m/s" (Specs_2025) — dato nuevo, el modelo actual no modela ningún cut-out, solo cut-in.
- `Installation Manual for the ZW-Pole.pdf`: describe un producto distinto — un poste híbrido
  solar+eólico (fundación 450×450×1060mm, 8×M16, con brazos para paneles solares y una turbina
  pequeña en la punta). No es una de las bases estructurales de los 5 modelos principales;
  queda documentado por separado como un producto relacionado, no mezclado con el análisis de
  anclaje de Hallazgo 9/10.

**Discrepancias reales, verificadas, no forzadas a encajar:**
- **Velocidad de supervivencia inconsistente entre tipos de documento**: las hojas Specs_2025
  dicen 45 m/s ("when reinforced") para Medium y 3-M Tulip; los Quick Start Guide de esos
  mismos modelos dicen 54 m/s. Es una diferencia sistemática (no ruido de un solo dato) entre
  los dos tipos de documento — no está claro cuál es la vigente, ni si "reinforced" se refiere
  a una opción distinta. No resuelto.
- **Curva de potencia del Large Tulip, dos fuentes oficiales distintas no coinciden en ~4%**:
  el coeficiente ya en el código (`k=3.120040`) viene del calculador en línea oficial,
  validado en su momento con capturas independientes. La tabla propia del Quick Start Guide
  (recién extraída, 31 puntos) da sistemáticamente ~4% menos en todo el rango (p.ej. 5,184.0 W
  vs 5,391.4 W a 12 m/s). Ambas fuentes son oficiales de Flower Turbines; no se sabe cuál
  refleja el diseño vigente. Se deja el coeficiente actual sin cambiar (fuente más rigurosamente
  validada en su momento) y se documenta la diferencia como abierta.
- **Pesos internamente inconsistentes dentro del propio Quick Start Guide**: Large Tulip da
  798.5 kg junto a la imagen de la turbina montada (p.2) y 1000 kg en el FAQ (p.18) para lo que
  debería ser la misma cosa. AL13 da 588 kg (Tabla 1) vs 557 kg (FAQ) para un stack de 6
  módulos — y ni siquiera el FAQ es internamente consistente (336/462 kg para 2/4 módulos
  implican un incremento lineal de 63 kg/módulo que predice 588 kg para 6, no los 557 kg que el
  mismo FAQ afirma). No se elige un valor sobre otro — se documentan ambos.
- **Plano de apéndice ambiguo, compartido entre dos manuales distintos**: tanto el manual del
  AL13 como el del 3-M Tulip incluyen, como apéndice, un dibujo técnico que parece ser el
  MISMO documento genérico (mismo gabinete de acero con puerta y ventilación circular en la
  tapa, mismo patrón de agujeros, mismo bloque de título con "S235, 8mm" y un texto en verde
  poco legible que podría decir "Base Pivot") — no una placa de anclaje de hormigón como los
  planos "Concrete Base ASSY" ya incorporados. Es decir, es probablemente un componente
  genérico (¿un gabinete eléctrico? ¿un pivote?), no la cimentación real de ninguno de los dos
  modelos. Se verificó visualmente (releyendo ambas páginas directamente) antes de decidir
  **no** incorporar sus varillas M16 a `PATRONES_ANCLAJE` — hacerlo hubiera sido usar un dato
  de un componente que no se sabe con certeza qué es, para reemplazar planos ya confirmados
  (`Big/Small Pedestal Concrete Base ASSY`). Queda como pregunta abierta para Pablo: si sabe
  qué es este componente, podría aclarar si aplica a algo del análisis estructural.

**Adenda — segundo envío ("revisa estos otros manuales"):** de 5 documentos compartidos, 4
(Large Tulip, Medium Tulip, AL13, Small Tulip) resultaron ser el MISMO archivo, byte a byte
(checksum idéntico), a los Quick Start Guide ya procesados arriba — no se reprocesaron. Solo
`EcoRoof Energy Hub For Slanted Roof Tops.pdf` (19 páginas) era nuevo, y se leyó completo:

- Es un producto de montaje distinto a todo lo visto hasta ahora: turbinas Small Tulip (1m) en
  módulos de 3, sobre una plataforma **sin perforar el techo** — se sostiene por peso, balance
  y puntos de fricción alta de hule, no por pernos de anclaje a concreto. Los brazos que se
  extienden a los lados sostienen paneles solares y, en la versión de techo plano, cajas de
  lastre (300×315×150mm, ya conocidas de Hallazgo 11). Es decir, es un sistema de carga
  distribuida sobre el techo, no un problema de tensión de pernos — un tipo de análisis
  estructural distinto al ya cubierto en `estructural_asce7.py` (que asume anclaje con
  pernos). No se tocó el código; queda como contexto nuevo para si se decide modelar este caso.
- **Cargas distribuidas reales sobre el techo (dato nuevo, útil para cuando se evalúe este tipo
  de instalación):** versión plana de 3 turbinas = 196.5 kg/m²; de 5 turbinas = 185.3 kg/m²; de
  2 turbinas de 2m de pala = 207 kg/m²; versión de techo inclinado (con 2 filas de paneles
  solares por lado) = 207 kg/m².
- **Ángulo máximo de techo: 3°** — pese al nombre "for Slanted Rooftops", este modelo específico
  solo tolera techos casi planos (3° de inclinación máxima).
- Confirma con más precisión el hallazgo de contaminación de plantilla de arriba: aquí el
  "generador de 100W, 200W pico" SÍ es coherente (la propia tabla de este documento para Small
  Tulip da máximo ~213-395W incluso en bouquets de 9, dentro de rango de ese generador) — es
  decir, el texto del generador de 100W es CORRECTO quizás solo para Small Tulip, y fue el
  copy-paste hacia Medium/Large Tulip (con curvas 10-80x más grandes) lo que generó la
  contradicción, no un error en el texto del 100W en sí.
- **Inconsistencia nueva, menor:** el rango de temperatura de este documento dice "-4°F to
  122°F (20°C to 50°C)" (p.17) — pero -4°F equivale a -20°C, no +20°C como dice el paréntesis
  (y ni -20°C ni +20°C coinciden con el "-15°C a 50°C" que repiten todos los demás documentos
  de Flower Turbines ya revisados). Reportado tal cual, sin asumir cuál cifra es la errónea.

Pablo indicó antes que enviaría más fichas "Specs_2025" de los modelos restantes (Small Tulip,
Large Tulip, AL13) — todavía no han llegado; este hallazgo se extenderá cuando lleguen.

### Hallazgo 12 — Curvas de potencia re-verificadas contra 5 capturas nuevas del calculador oficial: sin dudas reales pendientes

Pablo expresó preocupación de que aún hubiera dudas sin resolver sobre las curvas de
desempeño, y compartió 5 capturas de pantalla nuevas del "Bouquet Effect Calculator" oficial de
Flower Turbines (N=1, 7, 8, 9 y 10 turbinas — antes solo se tenía una captura propia de N=10).
Se comparó cada celda de cada tabla (31 puntos de viento × 3 modelos × 5 valores de N = 465
puntos) contra `power_isolated()`/`power_in_bouquet()` tal como ya estaban en el código, sin
tocar ningún coeficiente antes de medir el ajuste. Resultado: **R²≥0.999996 en los 15 pares
(modelo, N)**, error máximo por debajo de 1% en todo el rango 0–15 m/s. La única señal que en un
primer chequeo automático marcó "100% de error" resultó ser ruido irrelevante muy cerca del
cero: en las 5 capturas, Large Tulip muestra un valor pequeño no-nulo (0.4 a 2.6 W) ya en
v=0.5 m/s — por debajo del cut-in nominal de 0.7 m/s que sí tienen Small y Medium (0.0 en esa
misma fila, en las 5 capturas) — y el modelo actual, con un cut-in duro en 0.7 m/s, da 0 ahí.
Es un patrón consistente en las 5 fuentes (no ruido de una sola captura), pero de una magnitud
tan pequeña que no cambia ninguna conclusión ni justifica modificar el modelo. Conclusión
honesta: no se encontró ninguna duda real sobre las curvas base ni sobre el multiplicador de
Efecto Bouquet — el ajuste ya construido predice datos frescos del calculador, incluyendo las
"proyecciones" (N=6 a 10, que el propio calculador distingue de la "medición de campo" de N=2 a
5), con los que no fue entrenado. No se modificó ningún coeficiente en `flower_turbines_curves.py`
— solo se documentó la verificación adicional en el docstring del módulo.

### Hallazgo 13 — ASCE 7 extendido a Small Tulip y AL13, y primera aproximación (conservadora) a carga de clúster

Con las curvas de potencia confirmadas (Hallazgo 12), Pablo pidió seguir con la parte
estructural pendiente, específicamente extender `estructural_asce7.py` a más modelos —no
conseguir capacidad de pernos ni el plano del Small Tulip, que quedan pendientes y dependen de
datos que él tiene que aportar.

**Small Tulip (D=0.55m, H=1.149m):** se calculan `Fw`/`Mw`/`fs` igual que los demás modelos,
pero **sin** demanda de anclaje — no existe un plano de base de concreto con pernos para este
modelo (`PATRONES_ANCLAJE` no tiene entrada `small_tulip`), y el único sistema de montaje
documentado hasta ahora (`EcoRoof Energy Hub`, Hallazgo 11) no usa pernos en absoluto: es peso +
fricción, un problema de presión de apoyo distribuida sobre el techo (185-207 kg/m², ya
documentado), no de tensión puntual — un tipo de análisis que este módulo todavía no cubre. No
se asumió cuál instalación aplica a un caso real.

**AL13 Power Tower (stack de 4 módulos, D=1.7m, H=4.0m):** se calcula `Fw`/`Mw` y la demanda de
tensión en pernos usando el patrón ya existente en `PATRONES_ANCLAJE` (`Power Tower Concrete
Base ASSY`, 12×M18×2.5, 774.4mm). Dos supuestos declarados explícitamente, no escondidos: (1)
el ancho D=1.7m se tomó del FAQ del manual, que en otra página del mismo documento dice 1.6m —
discrepancia ya documentada en Hallazgo 11, no resuelta, se usó el valor más ancho por ser
conservador; (2) Cd=2.3 se heredó sin re-verificación específica para la pala de aluminio del
AL13 (mismo supuesto que Tulip, por ser también VAWT de 2 palas).

**Primera aproximación a carga de clúster**, usando las reglas reales de espaciamiento del
Hallazgo 11 (`espaciamiento_cluster()`, `separacion_filas()`, `cargas_viento_cluster_asce7()`):
para un bouquet de 5 Medium Tulip a 40 m/s sobre techo a 10m, la demanda estructural total (suma
simple de 5 turbinas, **sin ningún crédito de apantallamiento aerodinámico**) da 19.23 kN, con
un espaciamiento ideal de 1.47m eje-a-eje y una fila de ~7.08m de ancho. Esto es
deliberadamente conservador para dimensionar una estructura de soporte compartida — **no** es
un intento de modelar el efecto clúster aerodinámico real (que sigue sin construirse, ver
Pendientes) y se documentó explícitamente que no debe confundirse con el Efecto Bouquet de
`power_in_bouquet()`, que va en la dirección contraria (más potencia por turbina agrupada, no
menos empuje).

### Hallazgo 14 — Capacidad de anclaje (demanda vs oferta de mercado): implementada, con una discrepancia real de norma de acero detectada antes de aceptar los datos

Pablo pidió cruzar la demanda de tensión ya calculada contra capacidades reales de mercado en
Costa Rica, reemplazando el "acero genérico" por varillas ASTM A193 Grado B7, con capacidades
dadas: M12=54kN, 5/8"(~M16)=98kN, 3/4"(~M20)=146kN, y concreto CSCR f'c=21MPa.

**Verificación antes de implementar (no se aceptaron los datos tal cual):** ASTM A193 B7
(Fy=105 ksi=724 MPa) y "Grado 8.8" (ISO 898-1, Fy=640 MPa=93 ksi) **no son el mismo acero ni
son equivalentes** — son normas distintas, con ~13% menos capacidad en Grado 8.8. Esto importa
porque los planos reales de Flower Turbines ya leídos en este proyecto (Hallazgos 9-11)
especifican varillas Grado 8.8 (DIN 975/976) para los 5 modelos, **no** A193 B7. Calculando
capacidad de fluencia (área de tracción × Fy) para ambas normas: el valor de M12 dado (54.0 kN)
coincide casi exacto con Grado 8.8 (640 MPa×84.3mm²=53.95 kN) y **no** con A193 B7 (724
MPa×84.3mm²=61.0 kN); el de 5/8" (98.0 kN) también cae más cerca de Grado 8.8 (100.5 kN con
M16) que de A193 B7 (113.7 kN). Sugiere que los 3 valores podrían venir de tablas de Grado 8.8,
aunque se etiquetaron como A193 B7 al pedirlos — vale la pena confirmarlo contra la ficha
técnica real del proveedor en Costa Rica antes de usar esto en una decisión de compra real. **Se
implementó con los valores exactos que Pablo dio**, sin sustituirlos, pero con esta advertencia
documentada en el código y aquí.

**Otro dato no confirmado:** el "dado de concreto mínimo de 0.5×0.5×0.5m" mencionado para Small
Tulip no aparece en ningún documento revisado hasta ahora en este proyecto. El único plano de
cimentación real y verificado para instalación de Small Tulip en poste (`Installation Manual
for the ZW-Pole`, Hallazgo 11) da **450×450×1060mm** — una profundidad más del doble (1060mm
vs 500mm). Se usó el dato verificado en el mensaje de advertencia del código en vez del
0.5×0.5×0.5m, sin forzar que coincidan.

**Implementado en `engine/estructural_asce7.py`:** `evaluar_capacidad_anclaje()`, con la fórmula
de demanda exacta que dio Pablo (`Torque/(0.5×n_pernos×radio_base)`). Nota de consistencia
declarada: esa fórmula usa el RADIO de la base como brazo de palanca, mientras
`tension_maxima_pernos()` (ya existente en el módulo) usa el ANCHO completo del patrón — para
la misma geometría, la nueva función da el doble de tensión demandada (más conservadora, no
menos segura, pero es una convención distinta, documentada para no comparar ambos números como
si fueran la misma cantidad). También: los tamaños 5/8"/3/4" no coinciden exactamente con los
pernos M14/M18 reales ya usados en `PATRONES_ANCLAJE` — son tamaños vecinos, no el mismo.

**Caso de prueba pedido** (Small Tulip en poste de 3m, ráfaga 40 m/s, 4×M12, base de brida
0.3m): Mw=3.68 kN·m → demanda 12.27 kN por perno → cumple fluencia del acero con factor de
seguridad 4.40x. La función NO calcula capacidad de arranque del concreto (cone breakout) —
solo advierte que falta, consistente con el resto del módulo (demanda de acero, no capacidad
final de concreto, que sigue siendo responsabilidad del ingeniero civil).

### Hallazgo 15 — Pista B Paso 3 arranca: Cilindro Actuador implementado y validado, pero NO reproduce el Efecto Bouquet real (resultado honesto, no forzado)

Pablo pidió continuar con el efecto clúster (Cilindro Actuador), el hueco más grande que quedaba
en Pista B. El plan técnico aclara que su función es **calibrar el efecto clúster para layouts
2D/espaciamientos no estándar** — el M(N) empírico ya está resuelto para "bouquet estándar"
(Hallazgo 12). OpenFOAM no está instalado en este entorno (confirmado antes de empezar,
consistente con que el plan ya lo esperaba "offline/batch", fuera de este sandbox).

**Metodología:** en vez de improvisar la formulación matemática del Cilindro Actuador de
memoria, se buscó y clonó el código fuente **original y publicado** de Andrew Ning (autor del
método, NREL/BYU): [`github.com/byuflowlab/vawt-ac`](https://github.com/byuflowlab/vawt-ac) —
branch `python` (turbina aislada, Fortran+Python) y branch `master` (`src/acmultiple.jl`,
extensión a múltiples turbinas, el paper "Actuator Cylinder Theory for Multiple Vertical Axis
Wind Turbines," Wind Energy Science 2016). Se leyó el código real (no un resumen de terceros —
el PDF del paper en wes.copernicus.org estaba bloqueado por el proxy de red del entorno) y se
portó línea por línea a `engine/actuator_cylinder.py`, con especial cuidado en la aritmética de
índices (Julia 1-indexado → Python 0-indexado, verificada cruzando contra la versión Fortran
independiente del branch `python`, que coincidió).

**Validación del puerto** (antes de aplicar nada a Flower Turbines): se reprodujo el caso de
prueba que el propio código de Ning trae embebido (turbina D=6m, 3 palas, NACA0021, comparado
contra datos de CACTUS y CFD que el autor usó para validar su propio código). Usando NACA0018
(el polar ya disponible en este repo, no exactamente el mismo perfil), la forma de la curva
Cp-vs-TSR coincide bien — sube, pica alrededor de TSR 3-4, se vuelve negativa — y el punto de
cola en TSR=7 casi exacto (−0.058 calculado vs −0.059 de CACTUS). Esto da confianza en que el
puerto en sí está bien hecho, independiente de si aplica bien a Flower Turbines.

**Aplicación a Flower Turbines — resultado honesto:** con geometría real de Medium Tulip
(D=1.18m, TSR=1.0, B=2, perfil NACA0018 puro por sustentación — deliberado, no una omisión: el
propósito de este módulo es aislar la interacción de estelas, no re-derivar la potencia
absoluta de una turbina, eso ya lo hace mejor el M(N) empírico), se probaron **4
configuraciones** de 2 turbinas con el espaciamiento ideal real (1.25×D, `Guidance on Spacing
Flower Turbines.pdf`, Hallazgo 11): lado a lado (0°) y al ángulo real de la guía (15° respecto
a la perpendicular al viento), cada una con mismo sentido de giro y contra-rotando. Las 4 dieron
razones de potencia entre **0.90x y 1.09x** (promedio de las dos turbinas) — **ninguna cerca
del 1.235x real** que da M(2), ya validado con R²≥0.999996 contra el calculador oficial. El
modelo de Cilindro Actuador, con un perfil de sustentación pura, **no reproduce ni siquiera el
caso más simple (N=2)** que el M(N) empírico ya cubre perfectamente.

**No se fuerza una explicación — hipótesis sin confirmar, en orden de plausibilidad:**
1. El mecanismo real del Efecto Bouquet podría depender específicamente de la arquitectura
   patentada de dos niveles (sustentación + arrastre tipo Savonius, Hallazgo 6) — un perfil
   simétrico de sustentación pura no tiene la geometría cóncava que produciría un efecto de
   canalización/bloqueo entre turbinas vecinas.
2. Efectos 3D/turbulentos reales que un modelo 2D estacionario (RANS-like, sin turbulencia) no
   representa.
3. El propio M(N) medido por Flower Turbines podría incluir algo más allá de interacción
   aerodinámica pura entre rotores.

**Conclusión práctica:** este modelo, tal como está, **no está listo todavía** para calibrar
configuraciones nuevas (arreglos 2D, espaciamientos no estándar) con confianza — antes debería
poder reproducir el caso YA conocido (bouquet estándar), y no lo hace. Es un resultado negativo
real, del mismo tipo que Hallazgo 7-8 (varios intentos de refinamiento aerodinámico que tampoco
cerraron la brecha de sobre-predicción) — se documenta completo, no se descarta silenciosamente
ni se sigue iterando buscando una configuración que "sí calce" sin justificación física real.

### Hallazgo 16 — Arranca Fase 2: MVP de Streamlit sobre Pista A, con dos límites reales detectados antes de prometer más de lo que hay

Pablo, con presión de entregar algo el mismo día, decidió congelar la Pista B (Cilindro
Actuador) para más adelante y avanzar con Fase 2 (productización) usando Pista A como motor.
Antes de decir "sí, listos" se verificó Pista A de punta a punta (no solo se confió en el
checklist previo) corriendo `notebooks/pista_a_motor_empirico.ipynb` completo — sin errores,
pero reveló dos cosas reales que Pablo necesitaba saber antes de avanzar:

1. **NASA POWER no es alcanzable desde este entorno de desarrollo** (`ProxyError... 403
   Forbidden`) — el notebook cayó automáticamente a datos sintéticos para esa fuente. Sin
   verificar todavía si esto es una restricción específica de este sandbox o si aplicaría igual
   en producción (Cloud Run).
2. **Global Wind Atlas (la fuente real y ya validada, Hallazgo 3) no es una API en vivo para
   cualquier coordenada** — es una descarga manual del panel web, por sitio. Hoy solo existe UN
   sitio preparado (San José/Juan Santamaría, `datos_clima/gwa_juan_santamaria/`). El flujo
   "coordenada → pronóstico instantáneo" del plan (sección 5) para un sitio nuevo cualquiera
   sigue sin resolverse — no es un bloqueo para entregar algo hoy (se puede usar el sitio ya
   preparado), pero sí una limitación real del MVP, comunicada explícitamente en la app misma,
   no escondida.

Dado esto, se usó **GWA** (no NASA POWER) como fuente climática del MVP — coherente con
Hallazgo 1 (NASA POWER subestima ~3x en el Valle Central) y con lo que ya estaba validado.

**Trabajo hecho:**
- `engine/simulador_pista_a.py` — se extrajo `simular()`, `wind_at_height()` y la carga/generación
  de clima desde GWA del notebook a un módulo importable (el notebook las tenía solo como celdas
  de Jupyter, no reusables desde una app). Verificado que da el mismo resultado exacto que el
  notebook para el mismo escenario (387.9 kWh/año, Medium Tulip×3, buje 3m).
- `app/app.py` — primer MVP de Streamlit: selector de sitio (solo San José por ahora), modelo de
  turbina, N, altura de buje, parámetros avanzados (z0, método de bouquet real/lineal), botón de
  cálculo, resultado (kWh/año, viento medio a la altura de buje, % horas bajo cut-in) y gráfico
  mensual. Paleta corporativa ECO aplicada (azul #003C52, verde #4A7C2F). Corrida localmente y
  probada con Playwright (clic real en el botón, captura de pantalla) — no solo "arrancó sin
  error", se verificó que el resultado se ve y calcula bien.
- `app/requirements.txt` — dependencias para el futuro Dockerfile/Cloud Build.

**Lo que este MVP explícitamente NO tiene todavía** (para no prometer de más): mapa de
ubicación, más de un sitio, PDF de cotización, registro de leads, ni despliegue a Cloud Run —
corre local por ahora. La app misma lo dice en un aviso visible, no queda implícito.

**Adenda — Docker local, pedido explícito de Pablo:** se creó `Dockerfile` y `.dockerignore` en
la raíz del repo (build de contexto = raíz, porque la app necesita `engine/` y `datos_clima/`,
que están fuera de `app/`). Respeta `$PORT` (default 8501 para Docker local) para que la misma
imagen sirva sin cambios el día que se despliegue a Cloud Run — no es funcionalidad de más, es
el destino que el propio plan ya señala para esto.

**No se pudo verificar el build completo en este entorno** — `docker build` falló al intentar
bajar la imagen base (`python:3.11-slim`): `production.cloudfront.docker.com` (CDN de Docker
Hub) está bloqueado por la política de red de esta sesión (denegación de política, 403 —
confirmado en el estado del proxy, no un error de certificado/configuración). Por instrucción
explícita del entorno, una denegación de política no se debe intentar rodear, así que no se
buscó un mirror alternativo ni ninguna otra vía. Se verificó en cambio todo lo que SÍ se podía
verificar sin red: la lógica de rutas del Dockerfile (dónde queda cada archivo dentro del
contenedor vs. dónde lo busca `app.py`, coincide), y la sintaxis exacta del `CMD` (con
`${PORT:-8501}` y flags en formato `--flag=valor`) corriendo streamlit directo con `PORT=8502`
de prueba — funcionó igual que en el `CMD`. Falta la verificación final: correr `docker build -t
eco-wind-app .` y `docker run -p 8501:8501 eco-wind-app` en una máquina con salida a internet
normal (la tuya) para confirmar el build de punta a punta.

### Hallazgo 17 — Clima multi-sitio, densidad por elevación, cálculo horario probado (Jensen), multi-clúster y gráficos

Pablo pidió 5 extensiones sobre la Pista A/MVP ya validados, con instrucción explícita de
investigar antes de picar código en el Requisito 1 (multi-sitio). Resumen por requisito:

**Requisito 1 — clima real para cualquier coordenada de Costa Rica.** Investigación previa
(no se improvisó): Global Wind Atlas SÍ tiene una API oficial documentada, pero es de
**rásters por país**, no de consulta puntual con distribución completa —
`globalwindatlas.info/api/gis/country/{ISO3}/wind-speed/{altura}`, devuelve un GeoTIFF de
velocidad media (~250m de resolución). Verificado leyendo el código fuente real del paquete de
R `energyRt/globalwindatlas` (que ya usa este endpoint en producción), no de un resumen de
búsqueda sin confirmar — `globalwindatlas.info` sigue bloqueado en este sandbox (Hallazgo 2)
para probarlo directo. Con esto confirmado, Pablo eligió la opción recomendada: **ráster de
Costa Rica completo (velocidad media real) + forma prestada de San José** (curva de excedencia
normalizada + patrón diurno/estacional), escalada a la media real de cada coordenada nueva —
aproximación declarada explícitamente en el código y en la UI, no presentada como si fuera tan
buena como datos propios del sitio. Implementado en `engine/gwa_raster.py`. **No se pudo
descargar el ráster real en este entorno** (mismo bloqueo de red que NASA POWER/GWA-San José,
Hallazgo 2) — la función de descarga está lista pero debe correrse en Colab. Se verificó todo
lo posible sin el archivo real: muestreo de un GeoTIFF sintético de prueba (interpolación e
indexado correctos), y que `generar_clima_gwa(media_objetivo=...)` reproduce EXACTO (diferencia
0.0) el resultado real de San José cuando se le da su propia media exacta — prueba matemática
de que el escalado de forma es correcto, la mejor validación posible sin el archivo real.

**Requisito 2 — corrección de densidad de aire por elevación.** Nuevo módulo
`engine/atmosfera_estandar.py`, fórmula barométrica ISA estándar. Verificado contra tabla de
atmósfera estándar publicada: error <0.04% en todo el rango 0-5000m. Caso real (Aeropuerto
Juan Santamaría, 921m, verificado AIP/DGAC vía búsqueda — múltiples fuentes coinciden en
920-921m): factor de corrección 0.9145, **8.5% menos producción** que si se ignorara la
elevación — magnitud físicamente razonable (~1%/100m en ese rango). Aclarado explícitamente en
el código: esto NO es lo mismo que el `powerDensity` que exporta GWA (ese es un indicador
combinado de recurso, no una corrección de densidad aplicable a una curva ya calibrada a otra
densidad).

**Requisito 3 — cálculo horario real, no promedio.** Verificado (no solo afirmado): `simular()`
YA aplicaba P=k·v³ sobre el arreglo horario completo (8760 valores), no sobre la velocidad
media — esto ya era correcto desde Hallazgo 16, simplemente no estaba probado ni explicado
explícitamente. Se agregó `comparar_metodo_ingenuo_vs_horario()` para cuantificarlo con datos
reales: para San José (Medium Tulip×3, buje 3m), el método correcto da 354.7 kWh/año; el
método ingenuo (potencia evaluada en la velocidad media, ×8760 horas) da solo 187.6 kWh/año —
*(corrección, Hallazgo 20: estos dos números venían de una fórmula de perfil de viento con un
error real, ya corregido -- el valor actualizado del método correcto es 156.4 kWh/año. La
RAZÓN 1.89x de este hallazgo sigue siendo válida, el mecanismo de Jensen no cambia; lo que
cambió es la magnitud absoluta de ambos números.)* **el método ingenuo subestima 1.89x**, una
diferencia grande, no un matiz menor, consecuencia
directa de la desigualdad de Jensen (E[v³]≥(E[v])³) sobre un recurso con variabilidad real. La
serie horaria completa ahora se expone en la UI vía una curva de duración anual (ver
Requisito 5), no solo en el diccionario de retorno interno.

**Requisito 4 — multi-clúster.** La app ahora permite agregar/quitar clústers independientes
(cada uno con su propio modelo/N/altura de buje) al mismo proyecto, con producción total
agregada y una tabla de detalle por clúster — mismo patrón que Kilowatts UK (varios bouquets
independientes por sitio).

**Requisito 5 — gráficos.** Clima: rosa de vientos direccional (parseada del `.lib` real de
San José — 12 sectores, frecuencia + Weibull A/k por sector, ya confirmaba en Hallazgo 3 los
sectores dominantes 90°-150°) y heatmap mes×hora del patrón diurno/estacional real. Generación:
gráfico mensual (ya existía) + **curva de duración anual** (las 8760 horas ordenadas de mayor a
menor producción) — se eligió esta forma en vez de graficar las 8760 horas directo (ilegible)
porque es el estándar de la industria para mostrar un recurso horario completo en un gráfico
legible, y conecta directamente con el hallazgo del Requisito 3 (muestra visualmente cuánta
energía viene de relativamente pocas horas de alta producción).

**Validado con Playwright** (clics reales, no solo "arrancó sin error"): flujo completo de San
José con 2 clústers agregados, las 4 pestañas/secciones de gráficos, y el camino de coordenada
personalizada mostrando el mensaje de error claro (no un traceback) cuando falta el ráster.

### Hallazgo 18 — 3 sitios EPW reales de climate.onebuilding.org: la forma prestada de San José falla entre -44% y +18% según el sitio; patrón de DDP-lite revisado; UWG descartado con evidencia de código, no de docs

Pablo pidió tres cosas en paralelo: (1) bajar los EPW de Costa Rica de climate.onebuilding.org,
(2) revisar cómo el proyecto hermano DDP-lite (`Sogo2012/DDP-lite`, "Prodex DDP") resuelve la
extracción de clima y la opción de EPW personalizado, y (3) si se lograban los EPW, comparar
esos datos reales contra lo que da la app.

**(1) climate.onebuilding.org bloqueado, igual que los demás.** Confirmado con dos métodos
independientes (`curl` y `WebFetch`) que el dominio está bloqueado por política del sandbox —
ver Hallazgo 2, ahora extendido a 6 hosts. Pablo bajó él mismo, con internet real, 3 EPW reales
de climate.onebuilding.org y los subió al chat: **Nicoya A.P.** (Guanacaste, Pacífico seco, WMO
787550), **Daniel Oduber/Liberia Intl. A.P.** (Guanacaste, Pacífico, WMO 787740) y **Finca
Favorita** (Limón, Caribe, WMO 749033) — mismo patrón ya usado para el EPW/GWA de San José.

**(2) Patrón de DDP-lite, revisado en el código real (no de memoria).** `weather_utils.py`
resuelve "clima real por sitio" con un catálogo estático pre-scrapeado
(`epw_catalog_global.json`, 5,276 estaciones, USA/CAN/MEX + 17 países LATAM) + búsqueda
geodésica Haversine + geocodificación inversa como fallback — búsqueda <100ms, sin red en
runtime. Ese catálogo completo queda fuera de alcance por ahora (no se construyó uno análogo
para Costa Rica). Lo que SÍ se adoptó, ya en código: el patrón de **"EPW personalizado"**
(`app.py` líneas ~1259-1298 de DDP-lite): un toggle "¿Usar archivo EPW personalizado?" +
`st.file_uploader` que guarda el .epw subido, lo parsea con `ladybug.epw.EPW`, y reemplaza la
fuente climática activa. ECO-Wind no depende de `ladybug` (evita esa dependencia pesada) —
`engine/epw_real.py` implementa un parser EPW propio, liviano, basado en el formato estándar de
EnergyPlus (8 líneas de encabezado + CSV horario, campo 21=dirección, campo 22=velocidad a
10m), y la app ahora tiene el mismo toggle+uploader que DDP-lite.

**(3) Comparación cuantificada — el hallazgo real.** Se simuló Medium Tulip×3, buje 3m, en cada
sitio, dos veces: (a) con el EPW real completo de ese sitio, y (b) con el enfoque actual de la
app para "coordenada nueva" (Requisito 1, Hallazgo 17): forma de San José reescalada a la media
real de ese sitio (usando la propia media real del EPW en vez del ráster, que sigue sin
descargarse — la mejor prueba posible de la aproximación en sí).

| Sitio | Media real (10m) | kWh/año real (EPW) | kWh/año forma-SJ | Diferencia | Razón estacional real (máx/mín mensual) |
|---|---|---|---|---|---|
| Nicoya (Guanacaste) | 2.09 m/s | 119.6 | 70.6 | **-41.0%** | 4.37x (ene=4.41 m/s, sep=1.01 m/s) |
| Liberia (Guanacaste) | 3.63 m/s | 660.5 | 372.5 | **-43.6%** | 3.66x (feb=6.52 m/s, sep=1.78 m/s) |
| Finca Favorita (Limón) | 1.41 m/s | 18.0 | 21.4 | **+18.4%** | 1.51x (nov=1.72 m/s, sep=1.14 m/s) |
| *San José (referencia, forma que se presta)* | 3.67 m/s | — | — | — | 3.85x |

**Lectura honesta: la aproximación de Hallazgo 17 NO es confiable fuera del Valle Central.**
El caso más claro es Liberia: su media real (3.63 m/s) es casi idéntica a la de San José (3.67
m/s) — si el error viniera solo de la magnitud, debería ser mínimo. Aun así la producción sale
43.6% distinta, porque la FORMA (estacionalidad + ciclo diurno) es la que de verdad importa
cuando P∝v³ es convexa (mismo mecanismo del Hallazgo 17 Requisito 3/Jensen, aplicado ahora a un
error de forma, no solo de cálculo ingenuo vs. horario). Guanacaste tiene el corredor seco del
Pacífico (vientos alisios/Papagayo muy estacionales, dic-abr fuertes, may-nov casi calmos —
razón estacional real 3.7-4.4x) mientras Limón (Caribe) es casi lo opuesto: la más plana de los
4 sitios (1.51x) — San José, en el medio, no representa bien a ninguno de los dos extremos.
Efecto práctico: Guanacaste es, además, la zona de mejor recurso eólico real de Costa Rica (ahí
operan los parques eólicos reales del país) — es justo donde más importa no subestimar 41-44%.

**Implementado en código, no solo documentado:** `engine/epw_real.py` (parser EPW +
`SITIOS_EPW_REAL` con los 3 sitios + `heatmap_json_desde_epw()`/`rosa_frecuencia_desde_epw()`
para que la rosa de vientos y el heatmap de clima salgan de datos reales de cada sitio, no
prestados). `app/app.py`: selector de sitio ahora lista los 4 sitios con datos propios (San
José + los 3 EPW reales) además de "coordenada personalizada" (aproximación, con la advertencia
ahora cuantificada con estos números), más el toggle+uploader de EPW propio. Probado extremo a
extremo (los 4 sitios, `simular()` completo) y con `streamlit run` arrancando sin errores
(HTTP 200, sin traceback). *(Corrección, Hallazgo 19 v3: este selector de modos se eliminó --
los 4 sitios y la aproximación siguen existiendo, pero como parte de un solo flujo de búsqueda,
no como opciones separadas que elegir de entrada. Ver Hallazgo 19 v3 más abajo.)*

**UWG (Urban Weather Generator, ladybug-tools) — evaluado y descartado, con evidencia de
código fuente, no de documentación.** `ladybug.tools`/`www.ladybug.tools` está bloqueado en
este sandbox (mismo Hallazgo 2), así que en vez de los docs se clonó y leyó el repo real,
`ladybug-tools/uwg` (commit `ddedeac`). Hallazgo concreto en `uwg/uwg.py`: UWG sí calcula
internamente una velocidad de viento de cañón urbano (`UCM.canWind`, a partir de altura de
edificio/cobertura del sitio/ancho de calle), pero **`write_epw()` escribe en la columna de
viento del EPW de salida la velocidad RURAL de entrada sin tocar** (`self.forc.wind`, línea
~1406) — la línea que sí escribiría el viento de cañón (`Uforc.wind =
copy.copy(self.UCM.canWind)`, línea ~1370) está **comentada en el código**, con una nota propia
del equipo de UWG: el modelo de difusión urbana experimental da **logaritmo de dominio negativo
para edificios ≥40m** y por eso quedó deshabilitado. Es decir: **correr UWG sobre nuestros datos
de viento (GWA o EPW real) y tomar su EPW de salida nos devolvería exactamente el mismo viento
que entró — cero efecto, por diseño del código tal cual está hoy**, sin importar qué geometría
urbana le diéramos. (Aparte, y a favor de ser justos: UWG en sí es liviano —
`requirements.txt` vacío, sin depender de Honeybee/EnergyPlus; esa pila pesada es de DDP-lite
para simulación térmica completa, no de UWG. El costo real de integrarlo no sería de peso de
dependencia, sino de tener que pedirle al usuario datos de geometría urbana -altura de
edificio, cobertura del sitio, ancho de calle, uso de HVAC de referencia- que la app no
recolecta hoy, para un resultado que hoy no cambiaría el viento en absoluto.) Esto confirma con
evidencia de código, no solo de intuición, la decisión que ya tenía el plan original
(`plan-tecnico-eco-wind.md`, líneas 36 y 49: "sin pasar por UWG si sólo interesa el viento") —
**no se integra UWG para el cálculo de viento.** Si en el futuro ECO Consultor necesita el lado
térmico (temperatura/humedad de isla de calor urbana, no viento) para otro producto, esa parte
de UWG sí está implementada y probada -- sería una evaluación aparte, no relacionada con este
simulador de viento.

### Hallazgo 19 — Módulo de búsqueda de clima + mapa homologado con DDP-lite y Skyplus: catálogo completo (5,276 estaciones, 20 países), búsqueda por nombre/coordenada/mapa, sin acotar a Costa Rica

Pablo pidió portar el módulo de búsqueda de clima y mapa que ya tienen DDP-lite y Skyplus, y
preguntó si hacía falta que subiera todo el proyecto. No hizo falta: `Sogo2012/DDP-lite` ya
estaba clonado en esta sesión (Hallazgo 18); se agregó `Sogo2012/Skyplus` (lectura) como segunda
referencia. Los dos comparten literalmente el mismo `weather_utils.py` (`diff` sin diferencias
en la lógica de búsqueda, sólo branding) -- confirma que ese módulo es el patrón real y estable
de ECO Consultor para esto, no una implementación particular de un solo producto.

**v1 (primera versión de este Hallazgo) fue una simplificación incorrecta, que Pablo corrigió
explícitamente.** La primera pasada recortó el catálogo a sólo las 12 estaciones de Costa Rica y
eliminó la geocodificación, asumiendo que ECO-Wind "ya está acotado a Costa Rica" -- Pablo pidió
explícitamente deshacer eso: *"no me hardcodes ninguna estación ni me limites a costa rica...
necesito la misma cosa"* que DDP-lite/Skyplus. Corregido: esta es la v2, un port fiel y completo.

**Qué se portó, fiel al original, sin recortes:**
- `datos_clima/epw_catalog_global.json` -- el catálogo COMPLETO (5,276 estaciones, 20 países:
  USA/CAN/MEX + 17 LATAM), copiado tal cual de DDP-lite/Skyplus (idéntico byte a byte entre
  ambos). Ya no existe una versión recortada a Costa Rica.
- `engine/epw_real.py::obtener_estaciones_cercanas()` -- port completo de la función real
  (mismo nombre): geocodificación inversa (Photon, luego Nominatim) para inferir el país de
  cualquier coordenada del mundo, con fallback a bounding box (sin red) si la geocodificación
  falla; búsqueda en ese país; si hay pocas estaciones, expande a países vecinos; si aún hay
  pocas, busca en los 20 países completos. Nada de esto asume Costa Rica -- probado con Ciudad
  de México, Buenos Aires y Bogotá además de San José, cada uno devolviendo estaciones reales de
  su propio país (ver tabla abajo).
- `engine/epw_real.py::geocode_name()` -- geocodificación directa (buscar por nombre de ciudad/
  país), puerto fiel del mismo nombre de función.
- `app/app.py` -- el modo "🗺️ Buscar estación en el mapa" ahora tiene los 3 caminos reales de
  DDP-lite/Skyplus: **buscar por nombre** (texto libre + geocodificación), **buscar por
  coordenada** (lat/lon manual), y **clic en el mapa** -- los 3 llaman a la misma
  `obtener_estaciones_cercanas()`.

**Verificado sin red (Haversine + fallback por bounding box, ninguno de los dos necesita
geocodificación para funcionar) contra 4 países distintos, no sólo Costa Rica:**

| Búsqueda | País inferido (fallback bbox) | Estación más cercana real | Distancia |
|---|---|---|---|
| Ciudad de México (19.4326, -99.1332) | Mexico | Fes Cuautitlan | 29.6 km |
| Buenos Aires (-34.6037, -58.3816) | Argentina | El Palomar A.P. | 19.7 km |
| Bogotá (4.7110, -74.0721) | Colombia | Las Gaviotas | 84.7 km |
| San José, CR (9.9937, -84.2088) | Costa Rica | San José Santamaría Intl. A.P. | 0.0 km |

**Discrepancia real encontrada al portar esto (no ignorada, documentada en el propio código):**
el catálogo ubica Finca Favorita en (9.8833, -83.9167), pero el EPW real que Pablo subió
(Hallazgo 18) trae en su propio encabezado LOCATION (9.517, -82.650) -- casi 50 km de
diferencia. El catálogo es sólo una posición aproximada para el mapa y el orden por distancia
ANTES de descargar; la metadata que de verdad se usa (lat/lon/elevación) siempre sale del
encabezado del EPW ya descargado, nunca del catálogo -- no afecta ningún resultado ya calculado.

**Bloqueado en este sandbox, mismo patrón de siempre (Hallazgo 2, extendido):**
`nominatim.openstreetmap.org` y `photon.komoot.io` (geocodificación, tanto directa como
inversa) -- confirmado con curl, `connect_rejected`. Como el fallback por bounding box no
necesita red, la búsqueda por coordenada funciona igual de bien aunque la geocodificación esté
caída (para eso está el fallback). La búsqueda por NOMBRE sí depende 100% de la geocodificación
-- en este sandbox falla limpio (`geocode_name()` devuelve `(None, None)`, la app muestra un
error claro, no un traceback) y sólo se puede probar de verdad con internet real. `climate.
onebuilding.org` sigue bloqueado también -- `descargar_y_extraer_epw()` probada contra una URL
real del catálogo de Argentina: falla con `ProxyError` de forma limpia y capturable. El **mapa
visual en sí** tampoco se pudo probar con Playwright/Chromium real: `cdn.jsdelivr.net` (de donde
`folium` carga Leaflet.js) está bloqueado (`net::ERR_TUNNEL_CONNECTION_FAILED`) -- el iframe del
componente sí se genera y monta, pero el mapa queda en blanco sin la librería.

**Verificado con `streamlit.testing.v1.AppTest`** (sin necesitar navegador, para no depender del
mapa visual): seleccionar el modo, poblar `session_state` con resultados reales de
`obtener_estaciones_cercanas()` para Buenos Aires (Argentina, NO Costa Rica) y confirmar que
aparecen las 5 estaciones argentinas con su botón "Usar", y que al hacer clic el error de red
(climate.onebuilding.org bloqueado) se muestra correctamente sin traceback.

**Alcance honesto:** este mapa funciona sólo con internet real (Docker local de Pablo, Cloud
Run) -- ni la geocodificación, ni el mapa visual, ni una descarga real de EPW se pueden
verificar de punta a punta en este sandbox de desarrollo. Lo que sí se puede afirmar con
evidencia: la lógica de búsqueda es correcta y NO está limitada a Costa Rica (probado con 4
países), la app no se rompe cuando la red falla, y el patrón de UI es fiel al de DDP-lite/Skyplus.

**Hallazgo 19 (v3) — corrección real: la v2 seguía siendo 4 modos paralelos, no un solo
flujo.** Pablo corrigió esto explícitamente: la v2 (arriba) sí portó el catálogo completo y la
geocodificación, pero la UI seguía teniendo un selector de 6 opciones (San José, 3 EPW, mapa,
coordenada) que el usuario tenía que elegir de antemano -- exactamente lo que DDP-lite/Skyplus
NO hacen. Se revisó el `app.py` REAL de ambos (ya clonados en esta sesión, no sólo
`weather_utils.py`) para confirmar la pantalla exacta antes de tocar código: en los dos, la
búsqueda (nombre/coordenada, en el sidebar) y el mapa+lista de estaciones (una sola pantalla,
"Selección de Clima") son un solo flujo continuo, sin modos.

**Consolidación real, no cosmética:**
- El selector de 6 opciones desapareció. Ahora hay un solo buscador (nombre / coordenada / clic
  en el mapa -- las 3 formas de indicar ubicación no se tocaron, ya estaban bien) que siempre
  muestra estaciones reales cercanas para elegir.
- San José y los 3 EPW reales (Hallazgo 18) ya NO son opciones de un menú -- son una
  optimización interna invisible: `engine/epw_real.py::sitio_precacheado_cercano(lat, lon)`
  detecta por PROXIMIDAD (no por texto del nombre) cuando la estación que devolvió la búsqueda
  es una de estas 4, y sirve el dato local ya validado en vez de descargar de nuevo lo mismo.
  Verificado: buscar por la coordenada real de San José devuelve "San Jose Santamaria Intl AP"
  a 0.0 km, y al elegir esa estación carga el GWA local al instante (sin intentar red) --
  reproduce exacto el benchmark ya establecido (156 kWh/año, medium_tulip×3, buje 3m).
- La aproximación (ráster GWA + forma de San José, Hallazgo 17-18) ya NO es un modo que se
  elige de entrada -- es un fallback automático que la app ofrece SÓLO cuando la estación real
  más cercana queda a más de `UMBRAL_APROXIMACION_KM` (**40 km -- decisión de producto
  documentada explícitamente en el código, no un valor medido**: Costa Rica es topográficamente
  compartimentada, cordilleras separan microclimas a distancias cortas, así que 40 km ya es
  generoso) Y el punto cae dentro de Costa Rica Y el ráster existe localmente. Aparece como una
  tarjeta dentro de la MISMA pantalla de resultados de búsqueda, con la advertencia cuantificada
  de Hallazgo 18 (-41% a -44% Guanacaste, +18% Limón) ahí mismo -- no en una pantalla aparte.
- Subir un EPW propio sigue existiendo, pero como opción secundaria discreta (mismo patrón real
  de DDP-lite/Skyplus, confirmado en su `app.py`), no como modo de nivel superior.

**Verificado con `streamlit.testing.v1.AppTest`** (los 5 casos, todos sin excepción ni
traceback): (1) arranque limpio; (2) "Calcular" sin haber elegido sitio → error claro, no
crash; (3) buscar San José → coincide con el sitio precacheado, carga local, "Calcular" produce
156 kWh (idéntico al benchmark de Hallazgo 20); (4) buscar un punto real de Costa Rica lejos de
toda estación (Golfito, zona sur, ~147 km de la más cercana) con un ráster de prueba presente →
aparece la tarjeta de aproximación; (5) buscar Buenos Aires (fuera de Costa Rica) → la
aproximación NO aparece aunque esté "lejos", porque el ráster sólo cubre Costa Rica. En el
estado real de este sandbox (sin el ráster descargado, Hallazgo 2) la tarjeta de aproximación no
aparece nunca -- comportamiento correcto: mejor que la opción no aparezca a que aparezca rota.

### Hallazgo 20 — Perfil de viento por altura: un error real (un solo z0 para referencia y destino) encontrado al revisar wind-data.ch y el código fuente de ladybug-tools

Pablo pidió investigar dos fuentes para el perfil de viento vs. altura, porque otros intentos no
habían dado resultados: `wind-data.ch/tools/profile.php` (bloqueado, confirmado con WebFetch --
7mo host de Hallazgo 2) y el componente `LB Wind Profile` de `ladybug-tools/ladybug-grasshopper`
(GitHub, sí accesible). Revisando ese componente se encontró que su lógica real vive en el
paquete núcleo `ladybug-tools/ladybug` (`ladybug/windprofile.py`, clase `WindProfile`) -- se
clonaron ambos repos (sólo lectura) y se leyó el código fuente real, no un resumen de terceros.

**El hallazgo: `wind_at_height()` tenía un error real.** La fórmula usaba UN SOLO valor de z0
tanto para el sitio de referencia (donde se midió el viento -- normalmente un aeropuerto, GWA o
EPW a 10m) como para el sitio destino (donde va la turbina) -- pero son sitios distintos con
rugosidad distinta casi siempre. `ladybug-tools/ladybug` SÍ distingue esto explícitamente:
`WindProfile.calculate_wind()` con `log_law=True` usa `met_roughness_length` (rugosidad del
sitio de referencia, default "country"/aeropuerto) Y `roughness_length` (rugosidad del sitio
destino) como dos parámetros separados. Su tabla `TERRAIN_PARAMETERS` (confirmada en el código,
no de memoria) también trae una **ley de potencia alternativa** -- la que usa EnergyPlus por
default, con exponente y altura de capa límite por clase de terreno:

| Terreno | Altura capa límite (m) | Exponente α | z0 (m) |
|---|---|---|---|
| water | 210 | 0.10 | 0.03 |
| country (aeropuertos -- default meteorológico) | 270 | 0.14 | 0.1 |
| suburban | 370 | 0.22 | 0.5 |
| city | 460 | 0.33 | 1.0 |

**Cuantificado con datos reales (San José, v_ref=3.669 m/s a 10m, buje 3m, destino suburbano):**

| Método | v_hub (m/s) | vs. fórmula vieja (un solo z0=0.3) |
|---|---|---|
| Fórmula vieja (un solo z0, sin distinguir referencia/destino) | 2.409 | -- |
| Log corregida (z0_met=0.1 país/aeropuerto, z0=0.3 destino) | 1.835 | **-23.9%** |
| Ley de potencia EnergyPlus (country→suburban, cross-check independiente) | 2.018 | **-16.2%** |

Como P∝v³, una sobreestimación de 16-24% en velocidad es **1.57x a 1.90x de más en energía** --
no una diferencia menor. Con la corrección aplicada, el benchmark de San José (medium_tulip×3,
buje 3m, con corrección de densidad) baja de 354.7 a **156.4 kWh/año** -- los números de
Hallazgo 16-18 quedan desactualizados por este cambio real, no por un ajuste cosmético.

**Implementado y verificado:** `wind_at_height()` ahora recibe `z0` (destino, default 0.3, sin
cambios) Y `z0_met` (referencia, default 0.1 -- clase "country" de EnergyPlus/ladybug-tools, que
ladybug-tools documenta explícitamente como "typical of most airports where wind measurements
are taken", coincide con nuestra situación real). Se agregó `wind_at_height_potencia()` como
cross-check independiente (misma tabla de terrenos). Regresión verificada: con `z0 == z0_met`
(mismo valor en ambos), la fórmula nueva reproduce EXACTO (diferencia 0.0) el resultado de la
fórmula vieja -- el cambio es aditivo, no reescribe la física del caso ya validado. Caso límite
`h_target <= z0` devuelto como 0 explícito (mismo criterio que ladybug-tools), no un error
silencioso. `simular()` y `comparar_metodo_ingenuo_vs_horario()` actualizados para pasar
`z0_met`. La app ahora muestra un cross-check de la ley de potencia junto al resultado, y aclara
en la ayuda del selector de z0 que es la rugosidad del sitio DESTINO, no la de referencia.
Probado de punta a punta: `streamlit run` arranca sin errores (HTTP 200).

---

### Hallazgo 21 — Vecino más cercano validado por leave-one-out: la idea de fondo funciona, pero un artefacto real de `generar_clima_gwa()` la tapa hoy; quantile mapping probado (mecánica) y acceso a ERA5/CDS investigado

Pablo pidió tres cosas en paralelo: (1) probar "Alternativa 4" (prestar la forma del vecino real
más cercano entre los 4 sitios conocidos, en vez de tener a San José fijo) con una validación
leave-one-out, sin necesitar el ráster todavía; (2) investigar qué hace falta para acceder a ERA5
vía Copernicus CDS; (3) probar la MECÁNICA de quantile mapping hoy mismo, sin esperar a (2).
Explícito: nada de esto se conecta a `app.py` hasta tener los números.

**Todo lo de este hallazgo y de Hallazgo 22 (más abajo) está también en
[`notebooks/pista_c_forma_regional_y_quantile_mapping.ipynb`](./notebooks/pista_c_forma_regional_y_quantile_mapping.ipynb)**,
corrible de punta a punta en Colab o local (mismo patrón que `pista_a_motor_empirico.ipynb` y
`pista_b_motor_fisico.ipynb`) -- las tablas y números de abajo son exactamente los que produce ese
notebook, no un resumen aparte. Las dos celdas que necesitan internet real (prueba de conectividad
a CDS, e intento de descarga real de NASA POWER) están marcadas explícitamente y sólo dan resultado
nuevo corriendo el notebook en un entorno con internet normal.

**Parte 1 — Vecino más cercano + leave-one-out (`engine/formas_regionales.py`, nuevo)**

`excedencia_json_desde_epw()` construye una curva de excedencia desde un EPW real en el MISMO
formato que el `windSpeed.json` real de GWA (verificado directo contra el archivo real: 50 puntos,
`perc`=2,4,...,100, convención de excedencia confirmada: `val(perc)` = percentil estándar
`100-perc`) — necesario porque Nicoya/Liberia/Finca Favorita sólo tienen EPW, no export de GWA.
`vecino_mas_cercano()` usa Haversine (la misma función de `epw_real.py`) sobre los 4 sitios
conocidos, con soporte de exclusión para la prueba leave-one-out. `validar_leave_one_out()` tapa
la forma real de cada sitio por turno, predice con su propia media real + la forma prestada del
vecino más cercano de los OTROS 3, y compara contra su producción real conocida — recalculando
también, con el mismo pipeline de hoy (post-Hallazgo 20), el escenario "siempre San José" para
comparar en igualdad de condiciones (los números de Hallazgo 18 son de antes de esa corrección).

**Números reales (medium_tulip×3, buje 3.0m):**

| Sitio evaluado | Media real (m/s) | kWh real | Vecino más cercano (de los otros 3) | Distancia | kWh con vecino | Error nuevo | kWh con San José | Error viejo |
|---|---|---|---|---|---|---|---|---|
| San José | 3.67 | 156.4 | Nicoya | 137.5 km | 595.9 | **+280.9%** | — | — |
| Nicoya | 2.09 | 52.4 | Liberia | 50.3 km | 122.7 | **+134.2%** | 30.7 | -41.5% |
| Liberia | 3.63 | 291.5 | Nicoya | 50.3 km | 625.7 | **+114.7%** | 164.3 | -43.7% |
| Finca Favorita | 1.41 | 7.4 | San José (única opción real) | 178.6 km | 8.9 | +19.2% | 8.9 | +19.2% |

El escenario "siempre San José" recalculado reproduce casi exacto lo ya documentado en Hallazgo 18
(-41.5% vs -41.0%, -43.7% vs -43.6%, +19.2% vs +18.4% — la pequeña diferencia es consistente con
la corrección de Hallazgo 20), buena señal de que el pipeline está bien invocado. Pero el
resultado pedido — **reportar el número real, no asumirlo** — es que el vecino más cercano da
error MUCHO PEOR que siempre-San-José para los 3 sitios donde hay una alternativa real, no mejor
como se esperaba para Nicoya↔Liberia (misma zona, Guanacaste). Para Finca Favorita, tal como Pablo
anticipó, no hay una segunda opción real en su zona (Caribe) — el vecino más cercano de los otros
3 es San José (178.6 km) y no Guanacaste (338.7 km, verificado con Haversine exacto), así que el
resultado es idéntico al viejo por construcción. Esto no se esconde: es el único de los 4 casos
sin una alternativa real que probar.

**No se quedó en ese número — se investigó la causa, y NO es que la idea de fondo esté mal.**
Con self-reconstrucción (reconstruir la forma de un sitio a partir de SU PROPIA curva+heatmap
derivados de EPW, sin pedir prestado a nadie) se aisló el problema: `generar_clima_gwa()` dibuja
un percentil aleatorio independiente por hora desde la curva de excedencia MARGINAL (que ya
contiene todo el desvío del año, incluida la variación diurna/estacional) y lo multiplica por un
índice de heatmap mes×hora APARTE — reinyectando esa misma variación diurna/estacional una segunda
vez. Esto infla la varianza (y sobre todo `E[v³]/media³`, la cifra que de verdad pesa en una ley
de potencia cúbica) muy por encima de la real:

| Sitio (self-reconstrucción, sin vecinos) | E[v³]/media³ real (serie horaria cruda) | E[v³]/media³ reconstruido de su propia forma EPW-derivada |
|---|---|---|
| Nicoya | 3.25 | 6.71 (+106%) |
| Liberia | 3.41 | 6.99 (+105%) |
| San José | 2.26 | 3.41 (+51%) |
| Finca Favorita | 1.62 | 1.85 (+14%) |

Para San José se pudo comparar además contra su forma NATIVA de GWA (la del panel, no derivada de
EPW): esa reconstrucción da `E[v³]/media³`=1.89 — **subestima** ligeramente lo real (2.26), al
revés que la forma EPW-derivada. Esto confirma que el artefacto es específico de combinar una
curva de excedencia Y un heatmap derivados AMBOS de la misma serie horaria cruda (probablemente
porque el export nativo de GWA viene de un modelo/climatología ya suavizados, no de una serie
horaria observada) — no es un bug en `excedencia_json_desde_epw()` en sí (su aproximación de la
media, verificada aparte, sólo se desvía 2-4% de la media real de 8760h) ni un problema del
concepto de "vecino más cercano".

Separado de la mecánica rota, se probó el CONCEPTO puro: `E[v³]/media³` real (de la serie horaria
cruda, sin reconstrucción sintética de por medio) de Nicoya y Liberia difiere sólo 4.7% entre sí,
contra 43.6%/50.7% de diferencia contra San José — confirma fuerte que sitios de la misma zona
climática SÍ tienen forma real parecida. Finca Favorita, además, tiene su forma real más parecida
a San José (28.6% de diferencia) que a Liberia (52.6%) — coincide con que Haversine también elige
San José como su vecino más cercano real. Dos señales independientes (distancia geográfica y forma
real) apuntan en la misma dirección para Finca Favorita.

**Conclusión honesta de la Parte 1:** la idea de "prestar del vecino real más cercano" está bien
fundada en los datos reales — el problema es que `generar_clima_gwa()`, tal como reconstruye una
serie horaria desde una curva+heatmap derivados de EPW, no puede aprovecharla todavía. No se
resolvió esa parte con este pedido (era cuantificar el error, no arreglar el motor de reconstrucción) — pero
antes de decidir si Alternativa 4 reemplaza la aproximación actual hace falta resolver esto.
Direcciones posibles, NO implementadas, para que Pablo decida: (a) construir la curva de excedencia
de RESIDUOS (después de restar el patrón mes×hora), no de la serie cruda completa, para no repetir
la misma variación dos veces; (b) amortiguar el heatmap EPW-derivado antes de combinarlo; (c)
remuestrear bloques reales de horas (bootstrap por bloques) en vez de percentil+heatmap
independientes, que por construcción no puede duplicar varianza. `formas_regionales.py` sigue sin
conectarse a `app.py`, como se pidió.

**Parte 2 — Acceso a ERA5 vía Copernicus CDS (investigado, no implementado)**

`cds.climate.copernicus.eu` sigue bloqueado en este sandbox (confirmado de nuevo con curl:
`CONNECT tunnel failed`, error 403 del proxy — mismo host ya listado en Hallazgo 2). Investigado
qué hace falta (no asumido): registro gratuito (nombre, email, país, sector — sin mención de nivel
pago para el acceso estándar), después un "Personal Access Token" en la página de perfil de la
cuenta, que se guarda en `$HOME/.cdsapirc` (`url: https://cds.climate.copernicus.eu/api` /
`key: <TOKEN>`); acceso programático vía el paquete oficial `cdsapi` (pip); hay que aceptar los
Términos y Condiciones de cada dataset (ERA5 incluido) antes de poder descargarlo, un paso aparte
del registro general. Nada de esto pide tarjeta ni facturación según lo encontrado. Como ERA5
(~31km) es más fino que NASA POWER (~50-60km) pero usa el MISMO método de corrección (quantile
mapping, ver Parte 3) que ya se probó y funciona, perseguir el registro tiene sentido cuando haya
un sitio concreto que lo necesite — no es bloqueante para seguir probando el método con NASA POWER,
que ya es accesible en producción (sólo bloqueado en este sandbox).

Fuentes: [CDSAPI setup - Climate Data Store](https://cds.climate.copernicus.eu/how-to-api),
[ecmwf/cdsapi (GitHub)](https://github.com/ecmwf/cdsapi).

**Parte 3 — Quantile mapping: mecánica probada y funciona (`engine/quantile_mapping.py`, nuevo)**

Limitación real confirmada antes de probar nada: la corrida real de NASA POWER de Hallazgo 1 (San
José, 1.30 m/s vs 4.03 m/s del EPW real — re-verificado en la celda de resumen de
`notebooks/pista_a_motor_empirico.ipynb`, no de memoria) se hizo en Colab y su serie horaria cruda
nunca se guardó en el repo — sólo sobrevive la media y el kWh derivado. No se puede probar la
corrección contra NASA POWER real todavía; se probó la MECÁNICA del método con un sesgo sintético
controlado sobre el EPW real de San José: magnitud reducida por el factor real (1.30/4.03=0.3226,
Hallazgo 1) + forma comprimida hacia la media (imita que NASA POWER promedia una celda de
~50-60km — esta parte SÍ es una construcción sintética, marcada como tal en el código, no medida).

Diseño anti-tautológico: la tabla de mapeo se ajusta SÓLO con enero-junio; la comparación se hace
en julio-diciembre, que el ajuste nunca vio.

| Versión (semestre de prueba, jul-dic) | Media (m/s) | CV | E[v³]/media³ | kWh del semestre | Error vs. verdad |
|---|---|---|---|---|---|
| VERDAD (EPW real) | 3.432 | 0.624 | 2.356 | 79.11 | — |
| Sesgada cruda (sin corregir) | 1.204 | 0.287 | 1.265 | 1.05 | **-98.7%** |
| Corregida naive (sólo razón de medias) | 3.996 | 0.287 | 1.265 | 67.15 | **-15.1%** |
| Corregida quantile mapping (percentil a percentil) | 3.432 | 0.624 | 2.356 | 79.11 | **-0.003%** |

Quantile mapping recupera la media, el CV, `E[v³]/media³` y el kWh casi exactos, FUERA de muestra
(nunca vio julio-diciembre durante el ajuste). La corrección naive (equivalente a lo que ya hace
`media_objetivo` en `generar_clima_gwa()`) sólo arregla la media — como el sesgo sintético también
achata la forma, se queda en -15.1% de error. Esto demuestra que el método está bien implementado y
generaliza fuera de muestra bajo un sesgo sintético ESTACIONARIO (mismo factor todo el año) — no
todavía que el sesgo real de NASA POWER se comporte así de limpio (podría ser más ruidoso o variar
por estación). Confirmar eso necesita datos reales pareados (NASA POWER crudo real de Pablo, o
correr esto de nuevo en Colab, o los datos de ERA5 de la Parte 2).

**Qué sigue, sin decidir todavía:** con la mecánica de quantile mapping ya validada y el acceso a
CDS ya mapeado, el siguiente paso natural es conseguir una serie horaria real (NASA POWER de una
corrida en Colab, o ERA5 vía CDS) para validar el método contra un sesgo real, no sintético. Para
Alternativa 4, el siguiente paso es decidir si vale la pena arreglar el artefacto de
`generar_clima_gwa()` encontrado en la Parte 1 antes de reintentar la validación leave-one-out.
Ninguna de las dos cosas se implementó en este hallazgo — quedan como decisión de Pablo.

---

### Hallazgo 22 — Mitigación parcial del artefacto de Hallazgo 21: curva de excedencia por residuos, y el primer caso claro donde el vecino más cercano gana

Continuación directa de Hallazgo 21: de las 3 direcciones propuestas para el artefacto de doble
conteo de varianza, se implementó y probó la (a) — construir la curva de excedencia desde
RESIDUOS (`v(t)` dividido entre el factor de heatmap de su propio mes×hora) en vez de la serie
cruda, para que `generar_clima_gwa()` no vuelva a inyectar el patrón diurno/estacional una segunda
vez al multiplicar por el heatmap. Nueva función `excedencia_json_desde_epw_residual()` en
`engine/formas_regionales.py`; `cargar_formas_conocidas()` y `validar_leave_one_out()` ahora
aceptan `usar_residuo=True/False` (default `False`, para que los números ya documentados en
Hallazgo 21 sigan siendo reproducibles exactos sin este cambio).

**No es un arreglo completo, pero es una mejora real y grande.** Repitiendo la prueba de
self-reconstrucción de Hallazgo 21 (reconstruir la forma de un sitio desde sí mismo, sin vecinos):

| Sitio | Inflación de `E[v³]/media³` SIN residuo (Hallazgo 21) | Inflación CON residuo |
|---|---|---|
| Nicoya | +106% | +14% |
| Liberia | +105% | +30% |
| Finca Favorita | +14% | +7% |

Queda inflación residual (7-30%, no 0%) porque dividir por un promedio de 288 casillas mes×hora es
una manera gruesa de quitar la estacionalidad -- probablemente la VARIANZA (no sólo la media) del
viento también cambia por mes/hora, y una corrección puramente de razón de medias no lo captura.
No se investigó más a fondo (fuera del alcance de esto).

**Con la corrección, se repitió la validación leave-one-out completa:**

| Sitio evaluado | Error nuevo SIN residuo (Hallazgo 21) | Error nuevo CON residuo | Error viejo (San José) |
|---|---|---|---|
| San José (dona Nicoya) | +280.9% | **+105.7%** | — |
| Nicoya (dona Liberia) | +134.2% | **+47.6%** | -41.5% |
| Liberia (dona Nicoya) | +114.7% | **+15.9%** | -43.7% |
| Finca Favorita (dona San José) | +19.2% | +19.2% (sin cambio -- el donante es San José, forma nativa de GWA, no EPW-derivada) | +19.2% |

Lectura honesta, sin forzarla: **Liberia ya tiene un caso claro y real donde el vecino más cercano
gana** -- +15.9% de error nuevo contra -43.7% del viejo, una mejora de casi 3x en magnitud. Es la
primera confirmación limpia (no sólo en la forma real, como en Hallazgo 21, sino en la validación
completa) de que prestar de la misma zona climática ayuda. Nicoya (donante Liberia) mejoró mucho
en términos absolutos (+134%→+48%) pero queda en el mismo orden de magnitud que el error viejo
(-41.5%) -- ya no es claramente peor, pero tampoco es todavía una victoria clara. San José, sin un
vecino real de su propia zona entre los otros 3, se sigue prediciendo mal (+105.7%) -- esperable,
no es una falla del método.

**Conclusión:** vale la pena seguir con esta línea (Alternativa 4) para sitios que sí tengan un
vecino real de su misma zona -- Liberia ya lo demuestra. No se declara resuelto ni se conecta a
`app.py` todavía: falta terminar de cerrar la inflación residual (7-30%) y, sobre todo, tener más
de 4 sitios reales para que la validación leave-one-out deje de depender de un solo par
Nicoya-Liberia. `usar_residuo=True` queda disponible en el código para seguir iterando.

---

### Hallazgo 23 — Validación REAL (no sintética) de quantile mapping contra NASA POWER: corrido en Colab, mejora real pero más modesta que la prueba sintética

Pablo corrió `notebooks/pista_c_forma_regional_y_quantile_mapping.ipynb` completo en Colab (con
internet real) el 31 de agosto de 2026. Dos resultados que en el sandbox de desarrollo sólo podían
quedar como "pendiente de internet real" (Hallazgo 21/22) ya están confirmados con datos reales.

**CDS/ERA5 (Parte 2):** `cds.climate.copernicus.eu/how-to-api` respondió **200 OK** desde Colab —
no está bloqueado ahí, sólo en el sandbox de desarrollo (Hallazgo 2). No hay impedimento técnico
para que Pablo registre la cuenta cuando haga falta un sitio concreto que lo justifique.

**NASA POWER real (Parte 3):** se descargaron las 8760 horas reales de 2023 en la coordenada exacta
del EPW de San José. Media real: 1.301 m/s — coincide con el 1.30 m/s ya citado en Hallazgo 1 — 
contra 4.034 m/s del EPW real (coincide con el 4.03 m/s citado); razón 0.322, casi idéntica al
factor 0.3226 que se había usado para la magnitud del sesgo sintético. Mismo diseño anti-tautológico
(ajuste ene-jun, evaluación jul-dic, nunca vista por el ajuste):

| Versión (jul-dic, real) | Media (m/s) | E[v³]/media³ | kWh del semestre | Error vs. verdad |
|---|---|---|---|---|
| VERDAD (EPW real) | 3.432 | 2.356 | 79.107 | — |
| NASA POWER cruda (sin corregir) | 1.140 | 1.875 | 1.786 | **-97.7%** |
| Corregida naive (razón de medias) | 3.615 | 1.875 | 73.606 | **-6.95%** |
| Corregida quantile mapping | 3.473 | 2.212 | 77.031 | **-2.62%** |

**Comparación honesta con la prueba sintética de Hallazgo 21 (no forzarla a coincidir):** la mejora
de quantile mapping sobre la corrección naive es real y va en la misma dirección que predijo la
prueba sintética, pero **más modesta en magnitud**. El sesgo real de NASA POWER resultó menos
"achatado" en forma de lo que se había construido sintéticamente: `E[v³]/media³` crudo real es
1.875, sólo 20% debajo de la verdad (2.356) — contra 46% debajo en la construcción sintética
(`factor_compresion=0.5`, elegido a propósito para mostrar el mecanismo con claridad, marcado como
tal en `engine/quantile_mapping.py`, nunca medido). No es que la prueba sintética estuviera mal —
el parámetro fue una ilustración explícita, y ahora que hay dato real se sabe que fue más
pesimista que la realidad en San José 2023. Con datos reales, quantile mapping sigue siendo mejor
que naive (error absoluto ~2.65x más chico: -2.62% vs -6.95%), pero la ganancia (4.3 puntos
porcentuales) es bastante más chica que la que sugería lo sintético (15 puntos).

**Vale la pena que Pablo pese esto, no es una recomendación cerrada:** la corrección naive sola (lo
que ya hace `media_objetivo` en `generar_clima_gwa()`, sin código nuevo) ya deja un error manejable
(-7%) para NASA POWER en San José. Si ese nivel ya es aceptable frente a otras incertidumbres del
pipeline (la inflación residual de 7-30% de Hallazgo 22, o la incertidumbre propia del modelo de
clúster/Bouquet), quantile mapping capaz no justifica todavía la complejidad extra de mantener una
distribución de referencia por sitio. Si se necesita exprimir cada punto porcentual, sí ayuda y no
cuesta datos adicionales (usa la misma fuente NASA POWER + el mismo EPW real que ya hay).

**Limitación honesta:** n=1 — un sitio, un año (San José, 2023). No se sabe todavía si esta
magnitud de mejora se sostiene en Nicoya/Liberia/Finca Favorita, donde el sesgo real de NASA POWER
podría comportarse distinto (terreno costero, elevación). Probarlo ahí, ahora que se confirmó que
la descarga real funciona en Colab, es el siguiente paso natural — no implementado en este hallazgo.

---

### Hallazgo 24 — Corrección de rumbo de Pablo: la app es internacional, no debe anclarse a San José; el catálogo global ya resuelve la mayoría de los puntos con una estación real cercana

Pablo corrigió el enfoque de Hallazgo 21-22 directamente: ECO | Wind es una app internacional, no
debería estar comparando ni prestando forma climática de San José para resolver un sitio nuevo — la
"muestra de 4" (San José, Nicoya, Liberia, Finca Favorita) es pobre, y el pedido fue "olvidémonos de
los archivos base" y probar que el algoritmo se puede "auto-pivotar" a cualquier punto dentro del
alcance del catálogo global, igual que Skyplus.

**El catálogo global (`datos_clima/epw_catalog_global.json`, ya en el repo desde Hallazgo 19) es
mucho más grande de lo que este hallazgo venía tratando:** 5,276 estaciones reales en 20 países —
USA 2,969, Canadá 914, Brasil 667, México 173, Argentina 116, Chile 69, Colombia 46, Ecuador 45,
Perú 39, Bolivia 39, Venezuela 37, Paraguay 29, Panamá 28, Uruguay 21, Rep. Dominicana 19,
Honduras 18, Guatemala 17, **Costa Rica 12 (0.2% del total)**, Nicaragua 11, El Salvador 7. Todo el
trabajo de Hallazgo 21-22 (vecino más cercano ENTRE 4 sitios conocidos, prestando forma) estaba
resolviendo un problema mucho más chico del que hace falta: con un catálogo de este tamaño, para
casi cualquier punto de interés hay una estación real cerca — no hace falta prestar nada.

**Construido y probado: `notebooks/prueba_internacional_estacion_mas_cercana.ipynb`.** Reutiliza el
mismo mecanismo que ya usa el camino principal de la app (`obtener_estaciones_cercanas()` +
`descargar_y_extraer_epw()`, Hallazgo 19, mismo patrón que Skyplus/DDP-lite) sobre 6 puntos reales
en 6 países distintos — sin ninguna referencia a San José en la lógica. Corrido en este sandbox
(la búsqueda de estación no necesita red — usa el catálogo local + un fallback sin red para inferir
el país; sólo la descarga del EPW en sí necesita internet real, Colab):

| Punto consultado | Estación real encontrada | País | Distancia |
|---|---|---|---|
| San José, Costa Rica | San Jose La Sabana | CRI | 2.1 km |
| Bogotá, Colombia | Las Gaviotas | COL | 84.6 km |
| Ciudad de México, México | Fes Cuautitlán | MEX | 29.6 km |
| Buenos Aires, Argentina | El Palomar A.P. | ARG | 19.7 km |
| São Paulo, Brasil | Sao Paulo | BRA | 0.02 km |
| Ciudad de Panamá, Panamá | Ft Sherman Rocob | PAN | 23.3 km |

Cada punto se resolvió solo, con su propia estación real más cercana — el algoritmo se auto-pivota
de verdad, confirmado con datos reales en 6 países, no sólo en teoría. La descarga real de cada EPW
(el paso siguiente) falló con el mismo bloqueo de red ya documentado (Hallazgo 2) — funciona en
Colab, no en este sandbox, mismo patrón que todo lo demás.

**Esto no invalida el hallazgo técnico de Hallazgo 21-22** (el artefacto real de doble conteo de
varianza en `generar_clima_gwa()` sigue siendo cierto si algún día hace falta prestar forma) — pero
sí cambia su importancia: si la mayoría de los puntos reales tienen una estación real cerca, el caso
en el que hace falta prestar forma (sin estación real a menos de `UMBRAL_APROXIMACION_KM`) debería
ser la EXCEPCIÓN, no lo que se estaba probando como caso principal.

**Pendiente, decisión de Pablo, no tomada acá:** correr el notebook en Colab para confirmar que las
8 descargas reales funcionan (mismo paso pendiente que ya existía); y reconsiderar si vale la pena
seguir invirtiendo en arreglar el artefacto de Hallazgo 22 para la aproximación de respaldo
(`cargar_aproximacion()`, `engine/gwa_raster.py`) ahora que debería ser un caso mucho más raro, o si
alcanza con dejarla como está (ya declarada como aproximación, con su error ya conocido) para los
pocos puntos donde de verdad no hay ninguna estación real cerca.

---

### Hallazgo 25 — NASA POWER descartado como ajuste espacial (falla al revés en terreno accidentado); GWA generalizado a cualquier país como reemplazo

Continuación de la Parte 3 del plan de "sensibilizar el punto exacto" (ver mensaje de Pablo en el
chat, y `notebooks/sensibilizar_punto_exacto.ipynb`): usar una fuente de cobertura continua para
ajustar la magnitud de la forma real de la estación donante al punto exacto del cliente, sin anclar
nada a San José. Pablo corrió la validación en Colab con NASA POWER — el resultado es un hallazgo
real y negativo, no un bug.

**Números reales (leave-one-out, sin usar la media real ya conocida del sitio como atajo):**

| Sitio | Donante | Factor de ajuste NASA POWER | kWh ajustado | Error vs. verdad |
|---|---|---|---|---|
| San José | Nicoya | 0.365 | 2.3 | **-98.5%** |
| Nicoya | Liberia | 0.963 | 363.3 | **+593.4%** |
| Liberia | Nicoya | 1.038 | 71.8 | **-75.4%** |
| Finca Favorita | San José | 1.880 | 1,137.0 | **+15,184.0%** (153x la producción real) |

**Diagnóstico verificado con cálculo, no es un error de fórmula:** el mecanismo asume que la razón
entre dos puntos cercanos de la misma fuente cancela su sesgo sistemático — pero NASA POWER da la
razón San José/Finca Favorita **literalmente al revés** (dice que Finca Favorita es 1.88x más
ventosa; la realidad es que tiene sólo 38.5% del viento de San José), y ni siquiera distingue Nicoya
de Liberia (50km, terreno similar, diferencia real de 1.74x que NASA POWER no ve, factor 0.96-1.04).
Su sesgo depende del terreno (Hallazgo 1: subestima ~3x específicamente en el valle complejo de San
José) — la razón no cancela nada cuando el sesgo mismo varía según qué tan complejo es el terreno de
cada punto. **Conclusión: NASA POWER queda descartado como corrector espacial para este terreno —
no es cuestión de afinar el método, hace falta otra fuente.**

**GWA generalizado como reemplazo candidato.** Pablo confirmó con una captura de pantalla de la
página real "GIS files & API access" de globalwindatlas.info: **no existe una API de consulta por
punto separada** — "the provided URL can also be used as an API service" se refiere a la MISMA URL
de descarga de ráster por país (confirmada desde Hallazgo 17 leyendo el código fuente del paquete
de R `energyRt/globalwindatlas`, y ahora re-confirmada con la página real), con la advertencia
explícita "not to be used for bulk downloads of all countries or datasets" — bajar un país está
bien, scriptear los 20 en bulk no. `engine/gwa_raster.py::descargar_raster_pais(pais_iso3, altura)`
generaliza `descargar_raster_costa_rica()` a cualquiera de los 20 países del catálogo, y
`factor_ajuste_gwa()` replica el mismo mecanismo de ajuste espacial que
`factor_ajuste_nasa_power()`, pero leyendo 2 píxeles del ráster de 250m (con `rasterio`, ya
validado con un GeoTIFF sintético) en vez de 2 llamadas a NASA POWER — mucho más fino, debería poder
resolver la diferencia real de microclima que NASA POWER no puede.

**Estado:** `factor_ajuste_gwa()` construido y probado con datos sintéticos (calcula la razón
correcta entre 2 píxeles conocidos); la Parte 3 del notebook está lista y validada lógicamente (0
errores no capturados con `jupyter execute`), pero el ráster real de Costa Rica todavía no se
descargó en ningún entorno (sigue bloqueado en este sandbox) — pendiente que Pablo lo corra en
Colab para tener el número real de GWA y compararlo contra esta tabla.

**Nota de proceso, para no repetir el error:** durante este hallazgo, correr el notebook (su celda
de bootstrap hace `git reset --hard origin/main`) borró las funciones nuevas de
`engine/gwa_raster.py` porque todavía no estaban commiteadas — tuvieron que rehacerse. Lección: de
ahora en adelante, commitear cualquier cambio a `engine/` ANTES de ejecutar un notebook que
sincroniza el repo, no después.

---

### Hallazgo 26 — Validación real de GWA como ajuste espacial: mucho mejor que NASA POWER, pero mixto — el problema no está en el mecanismo de razón, está en el ráster crudo

Continuación de Hallazgo 25: Pablo corrió el notebook completo en Colab con el bug de `ruta_raster`
ya corregido. Dos hallazgos reales, con datos, no sintéticos.

**Diagnóstico crudo (antes de cualquier ajuste) — el ráster de GWA solo en la propia coordenada de
cada sitio, comparado contra la media real ya conocida:**

| Sitio | Media real | GWA crudo | Diferencia |
|---|---|---|---|
| Nicoya | 2.091 | 2.252 | **+7.7%** |
| Liberia | 3.629 | 3.390 | **-6.6%** |
| San José | 3.669 | 2.088 | **-43.1%** |
| Finca Favorita | 1.413 | 0.180 | **-87.2%** |

Guanacaste (Nicoya, Liberia) sale razonablemente cerca de la realidad. San José y Finca Favorita se
alejan mucho — **antes de aplicar ningún ajuste todavía**. San José tiene un precedente real ya
documentado (Hallazgo 3): el archivo `.lib` (WAsP nativo) de GWA da 5.37 m/s contra 3.67 m/s del
panel web — una brecha de +46% entre dos productos de GWA en el mismo punto, YA conocida antes de
este hallazgo. Esta brecha nueva (ráster/API vs. panel, -43%) es del mismo orden de magnitud —
consistente con que GWA simplemente tiene varios productos que no concuerdan entre sí para este
sitio, sin ser necesariamente un problema nuevo. Es una hipótesis razonable, no confirmada. Finca
Favorita (-87%) es un caso aparte, sin explicación confirmada — podría ser que el modelo de
downscaling de GWA resuelva mal el terreno costero/boscoso del Caribe a 250m, distinto del problema
de NASA POWER (que era resolución gruesa, no tipo de terreno).

**Validación leave-one-out real con `factor_ajuste_gwa()` (el número que de verdad importa):**

| Sitio | Donante | Factor GWA | kWh ajustado | Error |
|---|---|---|---|---|
| San José | Nicoya | 0.927 | 46.9 | **-70.0%** |
| Nicoya | Liberia | 0.664 | 118.8 | **+126.7%** |
| Liberia | Nicoya | 1.506 | 220.5 | **-24.4%** |
| Finca Favorita | San José | 0.086 | ~0.0 | **-100.0%** |

**Comparación completa contra todo lo ya documentado:**

| Sitio | Siempre San José (H21) | Vecino+residuo, verdad conocida (H22) | Vecino+NASA POWER (H25) | Vecino+GWA (este hallazgo) |
|---|---|---|---|---|
| San José | — | — | -98.5% | -70.0% |
| Nicoya | -41.5% | +47.6% | +593.4% | +126.7% |
| Liberia | -43.7% | +15.9% | -75.4% | **-24.4%** |
| Finca Favorita | +19.2% | +19.2% | +15,184.0% | -100.0% |

**El -100% de Finca Favorita se verificó con cálculo, no es un bug nuevo — es la propagación
directa del diagnóstico crudo.** La razón de los valores crudos de GWA (Finca Favorita/San José =
0.180/2.088 = 0.0863) coincide exacta con el `factor_ajuste_gwa` reportado (0.0863). Esa razón,
aplicada a la media real de San José (3.669 m/s), implica una media ajustada de apenas 0.317 m/s —
muy por debajo del cut-in de cualquier modelo de Flower Turbines, así que la producción sale
prácticamente cero. El mecanismo de razón no inventa un error nuevo: hereda (y en este caso,
amplifica) el error que ya tenía el dato crudo de GWA en los dos sitios donde el crudo ya fallaba.

**Lectura honesta, sin forzar una conclusión limpia:** GWA es sustancialmente mejor que NASA POWER
(nada de miles de por ciento) y para Liberia específicamente da el segundo mejor resultado de los 4
métodos comparados (sólo detrás de Hallazgo 22, que usa una ventaja injusta: la media real ya
conocida del sitio). Pero no es una victoria limpia — funciona bien donde el ráster crudo de GWA ya
era confiable (Guanacaste) y falla donde no lo era (San José, Finca Favorita), sin que el mecanismo
de razón en sí pueda arreglar eso. **El problema real a investigar no es "la razón entre dos puntos
no cancela el sesgo" (eso sí funciona, a diferencia de NASA POWER) — es por qué el ráster de GWA se
aleja tanto de la realidad específicamente en San José y Finca Favorita.**

**Pendiente, decisión de Pablo:** investigar la causa de la brecha del ráster crudo en San José y
Finca Favorita (¿otra altura? ¿otro producto de GWA? ¿limitación real del downscaling en esos
terrenos?), o pasar en paralelo a probar Köppen/polígonos climáticos (Alternativa 2 original, nunca
investigada) o ERA5 como fuente continua para el mismo mecanismo de razón (nunca construido para
este uso específico, distinto del quantile mapping ya probado en Hallazgo 23).

### Hallazgo 27 — Köppen-Geiger no es un cuarto candidato al mecanismo de razón: es un eje distinto (selección de donante, no ajuste de magnitud)

Mientras la validación real de ERA5 corría en Colab (Hallazgo 26/28, en curso), Pablo pidió arrancar
Köppen en paralelo — con la limitante explícita de que la app internacional necesita alternativas
sin costo y sin depender de un solo tipo de fuente meteorológica. Antes de construir nada, valía la
pena confirmar qué problema resuelve Köppen realmente, porque no es el mismo que NASA POWER/GWA/
ERA5.

Esos tres dan una fuente CONTINUA de viento en cualquier punto, así que sirven para el mecanismo de
razón `fuente(punto_exacto) / fuente(estación_donante)` que reescala la MAGNITUD de una forma real
prestada. Köppen-Geiger (Beck et al. 2018) da una ETIQUETA categórica de zona climática derivada de
temperatura/precipitación, no de viento — no puede alimentar ese mismo mecanismo. Lo que sí puede
mejorar es el paso anterior: `vecino_mas_cercano()` elige de qué estación tomar prestada la FORMA de
la curva de excedencia por pura distancia geográfica (Haversine), lo que puede fallar cuando el
punto más cercano en línea recta cae en un régimen climático distinto (barlovento/sotavento, costa/
interior) — relevante para una app internacional (Hallazgo 24) y posiblemente parte de por qué el
ráster crudo de GWA falla tan fuerte en algunos sitios (Hallazgo 26). La idea concreta: usar la zona
Köppen como filtro/desempate en la selección de donante (preferir la misma zona aunque esté un poco
más lejos), no como una cuarta fuente de ajuste de magnitud.

Fuente elegida por encajar con el pedido de Pablo (no meteorológica en el sentido de reanálisis/cola
de procesamiento, sin registro ni pago): Beck et al. 2018, raster global de 1km publicado en
Figshare, descarga directa. Notebook nuevo `notebooks/koppen_seleccion_donante.ipynb` con la
explicación de encuadre, una celda de verificación de acceso real (API pública de Figshare, sin
adivinar nombres de archivo — `api.figshare.com` está bloqueado en este sandbox igual que GWA/CDS,
así que esa celda todavía no se corrió con red real) y un boceto sin terminar de
`vecino_mas_cercano_por_zona()` — sin integrar a `engine/`, sin regla de desempate decidida, sin
validación leave-one-out todavía.

**Estado:** en investigación, no validado. Complementario al trabajo de ajuste de magnitud, no un
sustituto — atacan preguntas distintas del mismo problema más grande.

**Adenda — acceso real confirmado y primer sanity check (mismo día):** Pablo corrió la Parte 1 en
Colab. La API de Figshare respondió con el archivo real (`Beck_KG_V1.zip`, 71.0 MB); adentro hay 14
archivos (presente/futuro × 3 resoluciones × clasificación/confianza) — el que corresponde es
`Beck_KG_V1_present_0p0083.tif` (presente, 1km, clasificación). Sanity check contra los 4 sitios
conocidos:

| Sitio | Zona Köppen | ¿Tiene sentido? |
|---|---|---|
| San José | `Am` (tropical monzónico) | Sí — confirmado por fuera (temp. media anual ~19.5°C, nunca baja de 18°C incluso en el mes más frío); mi supuesto de "templado por la elevación" en el comentario del notebook era simplemente incorrecto, no reveló un bug. |
| Nicoya | `Aw` (tropical sabana) | Sí, tropical seco como se esperaba de Guanacaste. |
| Liberia | `Aw` (tropical sabana) | Sí, ídem. |
| Finca Favorita | `Af` (tropical lluvioso) | Sí, tropical húmedo como se esperaba del Caribe. |

**El hallazgo que de verdad importa:** se calculó si un filtro por zona habría cambiado alguno de
los 4 donantes ya elegidos por distancia pura (Hallazgo 25/26) — **no cambia ninguno**. San José y
Finca Favorita no comparten zona con ningún otro de los 4 sitios conocidos, así que el filtro cae
de nuevo a distancia pura. Nicoya y Liberia ya comparten zona (`Aw`) Y ya eran vecinos por
distancia — coinciden por las dos razones a la vez, no porque el filtro haya cambiado algo. Con
solo 4 sitios, el filtro por zona estructuralmente no puede demostrar si ayuda o no — hace falta
correrlo contra el catálogo completo (5,276 estaciones), donde sí hay margen real para que la
selección por zona difiera de la selección por distancia pura. Eso queda pendiente.

---

### Hallazgo 28 — ERA5/CDS real: mejor que NASA POWER, pero no le gana a GWA en ningún sitio; Open-Meteo agregado como quinta vía sin la fricción de CDS

Pablo corrió la Parte 4 completa en Colab. Entre el primer pedido (23:36) y el último resultado
(00:28) pasó casi una hora — cada consulta individual tardó entre ~30 segundos y ~12 minutos en la
cola de CDS, sin patrón previsible. Confirmado con el dashboard en vivo de CDS
(`cds.climate.copernicus.eu/live`) que era congestión real del servicio en ese momento (~4,361
pedidos en cola contra ~435 corriendo, `reanalysis-era5-single-levels` siendo el 2º dataset más
pedido de todo CDS) — no un problema de esta cuenta ni de nuestro código.

**Validación leave-one-out real con `factor_ajuste_era5()`:**

| Sitio | Donante | Factor ERA5 | kWh ajustado | Error |
|---|---|---|---|---|
| San José | Nicoya | 0.673 | 17.4 | **-88.9%** |
| Nicoya | Liberia | 0.876 | 273.5 | **+422.0%** |
| Liberia | Nicoya | 1.141 | 95.6 | **-67.2%** |
| Finca Favorita | San José | 0.762 | 75.3 | **+912.5%** |

**Comparación completa contra todo lo ya documentado:**

| Sitio | Siempre SJ (H21) | Vecino+residuo (H22) | NASA POWER (H25) | GWA (H26) | ERA5 (este hallazgo) |
|---|---|---|---|---|---|
| San José | — | — | -98.5% | **-70.0%** | -88.9% |
| Nicoya | -41.5% | +47.6% | +593.4% | **+126.7%** | +422.0% |
| Liberia | -43.7% | +15.9% | -75.4% | **-24.4%** | -67.2% |
| Finca Favorita | +19.2% | +19.2% | +15,184.0% | **-100.0%** | +912.5% |

**Veredicto honesto, no el que se esperaba:** ERA5 gana claramente contra NASA POWER (grilla más
fina, ~31km vs ~50-60km, menos sesgo por terreno) pero **no le gana a GWA en ningún sitio de los
4** — GWA sigue siendo el mejor ajuste de magnitud real que tenemos, pese a que ERA5 tiene mejor
base termodinámica. La fricción de CDS (cuenta, token, licencia, ~1 hora de cola) no compró mejor
precisión que GWA, que responde casi al instante.

**Por qué, verificado con cálculo, no solo reportado:** se comparó la razón que ERA5 implica entre
cada par de sitios contra la razón real (medias ya conocidas de Hallazgo 26):

| Sitio | Donante | Razón real | Razón ERA5 | ¿Dirección correcta? |
|---|---|---|---|---|
| San José | Nicoya | 1.755 | 0.673 | **Invertida** (como NASA POWER, Hallazgo 25) |
| Nicoya | Liberia | 0.576 | 0.876 | Correcta, magnitud aplastada hacia 1.0 |
| Liberia | Nicoya | 1.736 | 1.141 | Correcta, magnitud aplastada hacia 1.0 |
| Finca Favorita | San José | 0.385 | 0.762 | Correcta, magnitud aplastada a la mitad |

Solo 1 de 4 casos es una inversión real de dirección — los otros 3 sí aciertan el sentido del
gradiente, pero lo aplastan sistemáticamente hacia 1.0 (relaciones reales de 1.7-0.4 se vuelven
1.1-0.9 en ERA5). Consistente con seguir promediando terreno complejo incluso a 31km. Aplicando
pura escala v³ a la media ajustada resultante se recupera el orden de magnitud del error real
observado en los 4 casos (ej. San José: -94.4% solo por v³ vs -88.9% real) — confirma que el
mecanismo de razón en sí funciona correctamente; el problema es que el valor de ERA5 en estos 4
puntos de Costa Rica no preserva bien la variabilidad espacial real.

**Dato que cruza los tres métodos:** Finca Favorita falla catastróficamente con los TRES ajustes de
magnitud probados — NASA POWER (+15,184%), GWA (-100%), ERA5 (+912.5%) — en direcciones opuestas
entre sí. Ninguna fuente continua, sin importar su resolución, da un resultado usable ahí. Apunta a
que el problema puede ser el DONANTE (San José, a 178.6km, el único disponible hoy) más que la
fuente de ajuste — trabajo de Hallazgo 27 (selección por zona Köppen), no de este mecanismo.

**Quinta vía agregada mientras CDS seguía en cola:** Pablo trajo un informe de investigación
externo evaluando alternativas de cero fricción. La más directamente aplicable: **Open-Meteo**
(`archive-api.open-meteo.com`) sirve ERA5-Land (~9km/0.1°, más fino que el ERA5 estándar de CDS a
~31km/0.25°) sin API key, sin registro, sin cola — confirmado por WebSearch contra la documentación
oficial, no adivinado. `engine/open_meteo_client.py` (mismo mecanismo de razón, probado con una
respuesta JSON sintética) y la Parte 5 del notebook quedaron listos — sin verificar en vivo todavía
(bloqueado en este sandbox). El mismo informe también propone mejorar la selección de donante
combinando Köppen + elevación + distancia con una distancia de Gower (extiende Hallazgo 27, no
arrancado) y un downscaling topográfico más grande (TPI, índice de Winstral, factor de orografía
EN 1991-1-4, rugosidad vía ESA WorldCover) — real y creíble pero un desarrollo de semanas, no
arrancado, pendiente de que Pablo decida si vale la pena.

**Pendiente, decisión de Pablo:** correr la Parte 5 (Open-Meteo) para saber si de verdad hay una
fuente que le gane a GWA, o si la conclusión práctica es dejar de buscar una cuarta/quinta fuente
continua y volver al pendiente de Hallazgo 26 (por qué el ráster crudo de GWA falla en San
José/Finca Favorita).

---

### Hallazgo 29 — Limón, geográficamente 2.8x más cerca de Finca Favorita, resulta un donante PEOR que San José: la exposición local pesa más que la distancia

Pablo decidió ir con GWA (Hallazgo 25/26/28 — le gana a NASA POWER y ERA5 en los 4 sitios) y pidió
arrancar por el pendiente de selección de donante para Finca Favorita, el caso que falla con las
tres fuentes de ajuste probadas. Bajó las 8 estaciones de Costa Rica que faltaban en el catálogo
local (`descargar_estaciones_cr.ipynb`, ya construido en Hallazgo 21-22) y compartió el resultado
real — Limón es la más relevante, en el mismo Caribe que Finca Favorita.

**Hipótesis antes de medir:** Limón, mucho más cerca (misma costa), debería ser mejor donante que
San José (178.6km, otro lado de la cordillera). **Resultado real, verificado con cálculo, no el
esperado:**

| | Distancia a Finca Favorita | Error (vecino + verdad conocida, media real fija) |
|---|---|---|
| San José (donante actual) | 178.6 km | **+19.2%** |
| Limón (candidato nuevo) | 63.8 km (2.8x más cerca) | **+72.8%** |

Con Limón agregado al conjunto de sitios conocidos, `vecino_mas_cercano()` lo elegiría
automáticamente por pura distancia — y sería un donante PEOR, no mejor. La prueba usa el mismo
método de "verdad conocida" de Hallazgo 22 (forma real del donante, escalada a la media real YA
CONOCIDA de Finca Favorita), así que la diferencia es puramente de FORMA, no de magnitud.

**Por qué, verificado con E[v³]/media³ (EPF) y fracción de horas de calma:**

| Sitio | Media real | EPF | % horas < 1.0 m/s |
|---|---|---|---|
| Finca Favorita | 1.413 m/s | 1.617 | 25.2% |
| Limón | 2.152 m/s | 2.515 (+55.6%) | 15.7% |
| San José (curva GWA, aprox.) | 3.669 m/s | 1.077 (-33.4%) | N/A (curva, no serie horaria) |

Finca Favorita es un sitio bastante calmo/protegido (25.2% de horas casi sin viento) — consistente
con la hipótesis ya documentada en Hallazgo 26 de terreno costero-boscoso. Limón es un aeropuerto
abierto directo sobre la costa: más ventoso, más variable, menos horas de calma. San José, pese a
estar en un régimen climático totalmente distinto y mucho más lejos, tiene una forma más
"amortiguada" — más parecida, en ese sentido puntual, a la de un sitio protegido como Finca
Favorita que la de un aeropuerto costero expuesto como Limón.

**Conclusión honesta:** la cercanía geográfica — incluso compartir el mismo tramo de costa y
probablemente la misma zona Köppen — no garantiza una forma parecida. La EXPOSICIÓN local (abierto
vs. protegido/con cobertura vegetal) pesa más acá que la distancia. Esto es exactamente el tipo de
señal que el downscaling topográfico del informe externo de Pablo (TPI, rugosidad vía WorldCover,
Hallazgo 28) apunta a capturar — confirma que ese problema es real en al menos un caso conocido, no
que ya esté resuelto con más estaciones cercanas o con Köppen solamente (Hallazgo 27 tampoco lo
habría arreglado: Limón y Finca Favorita casi con certeza comparten zona Köppen, y aun así Limón
resultó peor donante).

San José sigue siendo el mejor donante real disponible para Finca Favorita entre los sitios
conocidos hoy. El EPW real de Limón quedó guardado en `datos_clima/epw_real/` (fuera del catálogo
`SITIOS_EPW_REAL` todavía — no se integró como sitio "conocido" oficial, dado que no resolvió el
problema que se estaba probando). Las otras 7 estaciones descargadas por Pablo (Chacarita-
Puntarenas, Palmar Sur, Parrita, Paso Canoas, Puntarenas, San José-Bolaños, San José-La Sabana)
están pendientes de análisis — podrían servir para otros puntos, o marginalmente para Finca
Favorita, pero no se probaron todavía.

**Vale la pena notar:** Finca Favorita produce apenas 7.4 kWh/año real — recurso eólico muy pobre
en términos absolutos (1.413 m/s de media). Cualquier recomendación real para un cliente ahí ya
diría "recurso insuficiente" sin importar el error porcentual exacto del modelo — pendiente que
Pablo decida si seguir afinando la precisión en este sitio específico es la mejor inversión de
tiempo ahora, frente al pendiente de Hallazgo 26 (por qué el ráster crudo de GWA falla en San José,
que sí tiene recurso real: 3.669 m/s, 156 kWh/año).

---

### Hallazgo 30 — Calibración de GWA contra 8 estaciones reales de EEUU: ni la elevación ni una categoría simple de terreno explican el error; dos bugs reales de memoria encontrados en el camino

Pablo propuso un pivote (en vez de seguir explicando San José/Finca Favorita como casos aislados,
calibrar el patrón de error de GWA contra una muestra más grande con ground-truth más confiable —
la red ASOS de EEUU) — ver `notebooks/calibracion_gwa_usa.ipynb`. Se probaron 8 aeropuertos elegidos
por diversidad de terreno (llanura abierta, costa abierta, desierto, valle de montaña, llanura alta
junto a las Rocosas, valle forestal, costa compleja, urbano).

**Dos bugs reales encontrados y corregidos antes de tener el número final** (no en la lógica de
negocio, en la infraestructura):

1. `descargar_raster_pais()` siempre re-descargaba el ráster aunque ya existiera en disco — con
   Costa Rica (chico) no importaba; agregado `forzar=False` (default) que salta la descarga si el
   archivo ya está — necesario para que el notebook sobreviva un reinicio de runtime sin re-bajar
   cientos de MB.
2. **Más serio:** `muestrear_velocidad_media()` cargaba la banda COMPLETA del ráster a memoria
   (`src.read(1)`) para leer un solo pixel. Con Costa Rica nunca se notó. Con el ráster de EEUU
   (843.7 MB en disco a 10m, bastante más ya descomprimido en memoria) agotaba la RAM del runtime
   de Colab — el **kernel crasheaba y se reiniciaba solo** a mitad del diagnóstico (confirmado con
   el log de crash real del kernel, no solo sospechado), dejando celdas corriendo contra una sesión
   nueva y vacía — producía un `NameError` engañoso que parecía un problema de orden de ejecución
   pero era memoria. Arreglado con una ventana de rasterio (lee 1 pixel, no la banda entera) — este
   bug no era específico de EEUU, cualquier país grande en el catálogo lo habría disparado.

**Resultado real, las 8 estaciones:**

| Estación | Media real | GWA 10m | Diferencia | Elevación |
|---|---|---|---|---|
| Chicago O'Hare (IL) | 4.300 | 3.924 | **-8.7%** | 201.8 m |
| Dodge City (KS) | 5.747 | 4.947 | -13.9% | 789.7 m |
| Phoenix Sky Harbor (AZ) | 2.725 | 2.321 | -14.8% | 337.4 m |
| Reno Tahoe (NV) | 2.676 | 2.231 | -16.6% | 1344.2 m |
| Corpus Christi (TX) | 5.194 | 4.124 | -20.6% | 15.3 m |
| Denver Intl (CO) | 4.558 | 3.264 | -28.4% | 1650.2 m |
| Monterey (CA) | 2.566 | 1.691 | **-34.1%** | 80.0 m |
| Eugene (OR) | 2.708 | 3.683 | **+36.0%** | 107.6 m |

**Correlación real calculada (no a ojo):** elevación vs. |error| → r=-0.094 — prácticamente cero.
Denver (1650m) y Reno (1344m) son las dos estaciones más altas, con errores muy distintos entre sí
(-28.4% vs -16.6%); Corpus Christi (15m) y Monterey (80m) están entre las más bajas y aun así entre
las peores. La hipótesis "elevación = terreno complejo = error grande", con la que se eligieron las
estaciones, no se sostiene.

Hay una señal cualitativa, no una relación limpia: los 3 peores (Eugene, Monterey, Denver) comparten
terreno regional complejo o cobertura forestal densa cerca; los 3 mejores (Phoenix, Dodge City,
Chicago) están en regiones abiertas de relieve bajo. Pero con excepciones reales — Corpus Christi
(costa abierta, "debería" ser fácil) sale peor de lo esperado; Reno (valle de montaña, análogo
directo a San José) sale mejor de lo esperado. Y la dirección del error es inconsistente entre
países para el mismo tipo de cobertura: Eugene (forestal) SOBRE-estima (+36.0%), Finca Favorita en
Costa Rica (también forestal, Hallazgo 26) SUB-estima fuerte (-87.2%) — cobertura boscosa por sí
sola no predice ni la dirección del error.

**Conclusión honesta, con 12 sitios reales combinados (8 EEUU + 4 CR):** no hay una variable simple
(elevación, "es costero", "tiene bosque") que explique el patrón de error de GWA de forma limpia.
Clasificar sitios a ojo no alcanza. Hace falta una métrica de terreno CALCULADA (TPI real desde un
DEM, cobertura de suelo real desde ESA WorldCover — lo que ya proponía el informe externo de Pablo,
Hallazgo 28) para saber si existe un patrón corregible, o si el error de GWA es, en la práctica,
ruido del orden de ±20-35% que conviene aceptar y comunicar como incertidumbre en vez de intentar
modelar con lo que hay hoy.

**Pendiente, decisión de Pablo:** ¿vale la pena invertir en calcular TPI/land-cover real (trabajo
nuevo, no arrancado) para buscar el patrón en serio, o se acepta el ±20-35% como la incertidumbre
real de GWA a 10m y se cierra esta fase de investigación con eso documentado?

---

### Hallazgo 31 — La sensibilización validada (Hallazgo 21-30) se conecta por fin a `app.py`

Con GWA confirmado como la mejor fuente de ajuste (Hallazgo 25/26/28), `cargar_aproximacion()` en
`app.py` deja de usar el mecanismo viejo (`generar_clima_sitio_nuevo()` — siempre forma de San José
+ valor crudo del ráster) y pasa a llamar `generar_clima_sensibilizado()`, nuevo en
`engine/formas_regionales.py`: vecino más cercano real para la FORMA (estacionalidad + ciclo
diurno, no siempre San José) + razón GWA(punto exacto)/GWA(donante) aplicada a la media REAL del
donante para la MAGNITUD. Requirió dos helpers nuevos, `_media_real_donante()` y
`_rosa_freq_donante()`, porque San José es el único de los 4 sitios conocidos que no tiene un EPW
real (usa el export de GWA) — sin ellos, tratar los 4 donantes igual rompía si el donante elegido
era San José.

Sin ráster real en este sandbox (Hallazgo 2), se verificó el ensamblaje con
`factor_ajuste_gwa()` mockeado (`unittest.mock`): con factor=1.0 la media generada coincide exacto
con la media real del donante (Nicoya), y con factor=1.5 escala proporcionalmente — confirma que el
ensamblaje es correcto, no que el ajuste en sí lo sea (eso ya está validado con datos reales en
Hallazgo 25/26/28). La dirección del viento (rosa) sigue siendo la del donante sin ajuste — no
existe mecanismo de razón para dirección, sólo para magnitud; documentado explícitamente en el
docstring de `generar_clima_sensibilizado()` y en el ALCANCE HONESTO de `app.py` como límite
aceptado, no un bug. **Pendiente:** Pablo debe correr esto contra el ráster real de Costa Rica en su
propio entorno (con internet real) para confirmar el número final en un punto sin estación cercana.

---

### Hallazgo 32 — Fichas técnicas de las 11 turbinas + imágenes/logos integrados a la app

Pablo compartió un DataFrame de pandas con specs de 11 modelos (Small/Medium/3-M/Large Tulip,
AL13 2/4/6/8m, Survival Unit, 3 variantes de EcoRoof Energy Hub) y la carpeta `Recursos Visuales/`
con imágenes de producto y los logos de ECO Consultor y Flower Turbines. Nuevo
`engine/turbine_specs.py`: `SPECS_TURBINAS` (11 entradas asociadas a las claves de modelo que ya
usa `flower_turbines_curves.py`), `RUTA_IMAGEN` (las 3 variantes de AL13 comparten una imagen
genérica; Survival Unit y los 3 EcoRoof no tienen imagen todavía), `LOGO_ECO`/`LOGO_FLOWER_TURBINES`.

**Dos gaps reales encontrados, flageados en vez de inventados:** `al13_4m` no tiene fila de specs en
el DataFrame de Pablo (los otros 3 AL13 sí); y Survival Unit + las 3 variantes EcoRoof tienen ficha
técnica pero ningún coeficiente en `CURVE_COEFFICIENTS` — no son simulables en la app todavía, sólo
mostrables. `app.py` ahora muestra los logos en el header y, por clúster configurado, un expander
"Ficha técnica" con imagen + specs (potencia nominal, cut-in/supervivencia, generador, dimensiones,
vida de diseño, cimentación) cuando existen. Se estuvo a punto de agregar "Distribuidor autorizado
de Flower Turbines en Costa Rica" al caption del header — se sacó antes de commitear por no tener
base real para esa afirmación de negocio.

---

### Hallazgo 33 — Bug real de Dockerfile en producción: búsqueda fallaba con `FileNotFoundError` fuera de los 4 sitios precacheados

Pablo reportó un `FileNotFoundError` real en su despliegue Docker al buscar "Heredia, Costa Rica":
`/app/datos_clima/epw_catalog_global.json` no existía dentro del contenedor. Comparando el
`Dockerfile` contra el de DDP-lite/Skyplus (mismo problema ya resuelto ahí, "no reinventar"),
la causa raíz fue que `Dockerfile` copiaba con una lista manual de carpetas (`engine/`, `app/`,
sólo `datos_clima/gwa_juan_santamaria/`) que quedó desactualizada apenas se agregaron el catálogo
global y los EPW reales (Hallazgo 18/19) — nunca copiaba `epw_catalog_global.json` ni
`datos_clima/epw_real/`, así que cualquier sitio que no fuera uno de los 4 ya precacheados fallaba
en producción, aunque funcionara siempre en local (donde esos archivos ya están en disco fuera de
Docker). Corregido al mismo patrón de DDP-lite/Skyplus: `COPY . .` completo + un único
`.dockerignore` como lista de exclusiones (en vez de dos listas — incluir y excluir — que se pueden
desincronizar). De paso, `.dockerignore` se corrigió: la exclusión vieja de `datos_clima/*.epw` ya
no era correcta (la app hoy sí necesita esos archivos en runtime).

**No se pudo verificar con un build real en este sandbox** — `docker build` falla al bajar la imagen
base (`python:3.11-slim`), Docker Hub bloqueado por la política de red del entorno (403), aunque
`dockerd` sí arrancó. **Pendiente real: Pablo debe reconstruir la imagen y volver a probar Heredia
(y otros puntos) para confirmar que el fix funciona en su entorno.**

---

### Hallazgo 34 — Menú lateral: clona la estructura real de DDP-lite/Skyplus (no los 4 tabs)

Pedido explícito de Pablo: "clona la estructura de UX que tiene la app DDP lite... usa un menu
lateral para colocar los menos de seleccion de clima y equipos". Investigando el sidebar real de
DDP-lite (`app.py`, líneas 827-985) antes de tocar nada: **no son los controles de entrada en sí**
— es un NAVEGADOR de secciones (header de marca con logo, lista numerada de pasos con 3 estados
visuales — actual resaltado, completado clickeable, futuro atenuado —, botón de reconfigurar,
resumen de "elegido hasta ahora", pie técnico). Los controles de entrada reales siguen viviendo en
el área principal, por paso. Se clonó ese patrón, no la lectura literal de la frase.

Implementado en `app.py`: las 4 pestañas (`st.tabs`) pasan a ser un menú lateral con navegador de
4 secciones (Selección de clima / Contexto climático / Equipos y configuración / Resultados),
header de marca con los logos ECO + Flower Turbines (antes en 3 columnas del área principal, ahora
en el sidebar), y un resumen "Elegido hasta ahora" (sitio activo, cantidad de clústers/turbinas, si
ya hay un cálculo listo) — todas las secciones quedan siempre clickeables, sin el bloqueo lineal
tipo wizard de DDP-lite, porque acá elegir clima y elegir equipos son pasos independientes, no
secuenciales.

**Cambio de comportamiento real que forzó, no cosmético:** con `st.tabs()`, Streamlit ejecuta el
cuerpo de las 4 pestañas en cada corrida del script (sólo oculta visualmente las no activas) — el
botón "Calcular" viejo (`calcular = st.button(...)`) dependía de eso: su valor, aunque definido en
la pestaña de configuración, se leía más abajo en la pestaña de resultados dentro de la MISMA
corrida. Con secciones `if/elif` dirigidas por el menú, sólo la sección activa se ejecuta — ese
patrón se rompe. Corregido: el botón ahora guarda el resultado en `st.session_state.calculo_listo`
y cambia `seccion_activa` a "resultados" con `st.rerun()`; los widgets de `z0` y `metodo_bouquet`
(antes sin `key=`, porque no lo necesitaban con tabs) ahora lo tienen, para sobrevivir el cambio de
sección. Efecto colateral bueno: de paso corrige un bug menor preexistente (con tabs, los resultados
desaparecían si navegabas a otra pestaña y volvías, porque `calcular` era un booleano transitorio de
esa corrida) — ahora el resultado persiste correctamente hasta que se recalcula.

**Verificado end-to-end con Chromium real (Playwright), no sólo HTTP 200:** las 4 secciones cargan
sin excepción visible; la navegación por el menú funciona; el flujo completo con un sitio 100% local
(San José, que no necesita red) — elegir estación → Contexto climático (rosa de vientos + heatmap
reales) → Equipos y configuración → Calcular → Resultados (métricas, tabla por clúster, producción
mensual, curva de duración) — se probó de punta a punta con capturas de pantalla en cada paso. La
búsqueda de estaciones que sí necesitan descarga real (ej. Finca Favorita) sigue bloqueada en este
sandbox por la misma limitación de red ya documentada (Hallazgo 2) — confirmado que es la limitación
de siempre y no una regresión de este cambio (mismo mensaje de error `HTTPSConnectionPool` de
siempre, manejado con un `st.error` legible, sin crashear).

---

### Hallazgo 35 — El ráster real de GWA (ya en el repo) confirma y agrava Hallazgo 26: en el Valle Central no sólo tiene sesgo, tiene ruido espacial más grande que la señal real, e invierte el orden Santamaría/La Sabana

Pendiente directo de Hallazgo 31 ("correr `generar_clima_sensibilizado()` contra el ráster real de
Costa Rica... no se pudo verificar en este sandbox, sólo con mock"). El archivo
`datos_clima/gwa_costa_rica_10m.tif` se agregó el 1/sep (commit `2413ff6`, bajado con
`notebooks/Descargar_GWA_Costa_Rica.ipynb` en un entorno con internet real). Esta vez sí hay ráster
real en el sandbox -- se instaló `rasterio` y se leyó directo con `muestrear_velocidad_media()` y
`generar_clima_sensibilizado()`, el código real de producción, no un mock.

**Primero, confirmar que es el mismo dato de Hallazgo 26 (no una descarga corrompida):** muestreando
el ráster en las coordenadas exactas que ya usa el código (`meta["lat"]/meta["lon"]` que lee cada
EPW real, no las coordenadas redondeadas del catálogo global -- Finca Favorita en particular tiene
una entrada con coordenada equivocada en `datos_clima/epw_catalog_global.json`, 9.8833/-83.9167,
~140 km de la coordenada real de su propio EPW, 9.517/-82.65 -- bug menor aparte, no afecta a
`generar_clima_sensibilizado()` porque ese usa `meta`, no el catálogo):

| Sitio | Ráster (este archivo, hoy) | Ráster (Hallazgo 26, documentado) | Media real |
|---|---|---|---|
| Nicoya | 2.252 | 2.252 | 2.091 |
| Liberia | 3.390 | 3.390 | 3.629 |
| San José (Santamaría) | 2.088 | 2.088 | 3.669 |
| Finca Favorita | 0.180 | 0.180 | 1.413 |

Coincide exacto en los cuatro sitios -- es el mismo producto de GWA, el sesgo de -43.1% en San José
y -87.2% en Finca Favorita que Hallazgo 26 dejó "pausado, decisión de Pablo" sigue ahí, confirmado
con el archivo real, no es algo que se arregló solo al conseguir el .tif.

**Pregunta A/B del pedido -- ¿el ráster ve la diferencia real entre Santamaría (3.67 m/s) y La
Sabana (1.43 m/s), a 11 km?** Se muestreó La Sabana con su coordenada real del catálogo (9.9368,
-84.1077): el ráster da **3.523 m/s** -- más alto que su propia lectura en Santamaría (2.088 m/s).
El ráster no "no ve" la diferencia (eso sería el caso menos grave) -- la ve, pero **al revés**: para
el ráster, La Sabana es más ventosa que Santamaría; en la realidad es lo opuesto por un factor de
2.5x. Responde directo la pregunta del pedido: no es que el escalado esté roto (la razón se calcula
y se aplica bien, ver Hallazgo 31) -- es que el dato de entrada, en este punto específico, no tiene
la relación correcta ni siquiera en el orden relativo, no sólo en la magnitud absoluta.

**Qué tan fino es el ruido -- mismo aeropuerto, tres coordenadas "oficiales" distintas:** Juan
Santamaría tiene tres coordenadas publicadas en este repo, todas referidas al mismo aeropuerto
(pista única, ~3 km de largo), separadas entre sí por 1.2-2.3 km -- la de `SITIOS_DISPONIBLES`
(10.0034, -84.2033), la del catálogo global (9.9937, -84.2088) y la del encabezado del propio EPW
(9.9892, -84.2183). El ráster da 2.088, 3.272 y 4.712 m/s respectivamente en esas tres -- **+126%
entre la más baja y la más alta, dentro del mismo aeropuerto.** Para contexto de escala: un barrido
sistemático de una grilla 25×25 sobre el Valle Central (lat 9.85-10.05°, lon -84.35 a -83.95°, ~20×40
km) da media=1.94 m/s, **desvío estándar=1.52 m/s (78% de la media)**, mínimo=0.08, máximo=12.0 m/s.
Ese nivel de varianza pixel a pixel, en un valle mayormente plano y habitado (no una cordillera), no
es un gradiente físico real de viento -- es ruido del producto, consistente con (y peor de lo que
sugería) el ±20-35% que Hallazgo 30 ya había estimado con los 12 sitios EEUU+CR.

**Por qué la sensibilización da "1.6 m/s máximo" cerca de San José:** dentro del Valle Central, el
único donante real disponible es siempre San José (Nicoya/Liberia quedan a ~130 km, Finca Favorita a
~140 km, todos fuera de cualquier punto del valle) -- `vecino_mas_cercano()` elige bien, ése no es el
problema. El problema es el factor: `factor_ajuste_gwa() = ráster(punto)/ráster(Santamaría=2.088)`,
aplicado a la media real de Santamaría (3.669 m/s). Con la grilla de arriba, el factor resultante
promedia 0.93 pero con desvío enorme (0.04 a 5.8x); la media_ajustada resultante tiene mediana=2.71
m/s y en **39% de la grilla cae por debajo de 2.0 m/s**. Se corrió `generar_clima_sensibilizado()`
real (no simulado) en 6 puntos del Valle Central (Santamaría exacto, La Sabana, Escazú, Heredia,
Cartago, Alajuela): salió entre 1.58 y 4.07 m/s según el punto exacto -- no hay un techo fijo de 1.6,
pero la mayoría de los puntos que un usuario probaría a mano en o cerca de San José caen en ese rango
bajo, porque el ráster ahí está sesgado hacia abajo Y es ruidoso, las dos cosas a la vez.

**Pregunta C, confirmada por lectura de código, no es un bug nuevo:** `_rosa_freq_donante()` y el
docstring de `generar_clima_sensibilizado()` (Hallazgo 31) ya declaran esto como límite honesto: la
rosa de vientos es siempre la del donante (San José en este caso) sin ningún ajuste geográfico -- no
existe mecanismo de razón para dirección, sólo para magnitud. Confirma la preocupación C del pedido,
pero no es algo que este hallazgo cambie: ya estaba documentado y aceptado como aproximación.

**Lectura honesta:** el mecanismo de razón (Hallazgo 25/26) y la selección de donante (Hallazgo
21/22) están haciendo lo que se diseñó que hicieran. Lo que falla es el ingrediente de entrada -- el
ráster crudo de GWA a 10m, específicamente en Valle Central y costa Caribe (Hallazgo 26/29) -- que
acá se confirma no sólo sesgado sino más ruidoso que la señal real que se le pide resolver (una
diferencia de terreno a escala de km). "¿El ráster es inútil?" -- para esta zona puntual, con esta
resolución/altura descargada, la evidencia de este hallazgo dice que sí, al menos para diferenciar
puntos a esta escala; en Guanacaste (Nicoya/Liberia, +7.7%/-6.6%) el mismo ráster fue razonablemente
confiable, así que "inútil" no es una conclusión pareja para todo el país.

**Pendiente, decisión de Pablo (reabre el pendiente pausado de Hallazgo 26, con evidencia nueva y
más fuerte):**
- Aceptar la incertidumbre y comunicarla explícitamente en la UI cuando el punto sensibilizado caiga
  en una zona ya conocida como no confiable (Valle Central, costa Caribe), en vez de mostrar un
  número único sin advertencia.
- Probar candidatos aún no probados de Hallazgo 26: otra altura del ráster (50/100m en vez de 10m),
  u otro producto de GWA para el mismo punto (ver también la brecha ya conocida panel-web vs `.lib`
  WAsP de Hallazgo 3).
- Invertir en el downscaling topográfico real (TPI vía DEM, rugosidad vía ESA WorldCover) que
  Hallazgo 28/30 ya identificaron como el camino más creíble para explicar el patrón de error, en
  vez de seguir tratando cada sitio como un caso aislado.
- Como paliativo de producto sin esperar lo anterior: restringir la sensibilización de punto exacto
  a zonas donde el ráster ya se validó razonable (p.ej. Guanacaste) y, fuera de ellas, ofrecer sólo
  la estación real más cercana (aunque esté a más de `UMBRAL_APROXIMACION_KM`) con su distancia real
  mostrada, en vez de un número sensibilizado que puede estar invertido.

---

### Hallazgo 36 — Simplificación de producto: se descarta toda sensibilización espacial de magnitud (GWA/NASA POWER/ERA5/Köppen); la app corre 100% sobre EPW real, con upload manual agregado

Decisión directa de Pablo tras Hallazgo 35: "nos olvidamos de todas las fuentes, solo vamos a usar
EPW, el usuario escoge cuál estación referenciar... no tenemos tiempo para más investigaciones
erráticas". Corta de raíz la línea de investigación de Hallazgo 21-30 (vecino más cercano + razón de
magnitud vía GWA/NASA POWER/ERA5/Köppen) en vez de seguir afinándola -- consistente con Hallazgo 35,
que ya había encontrado que el ráster crudo de GWA a 10m es más ruidoso que la señal real que debía
resolver en el Valle Central.

**Cambios reales en `app/app.py`:**
- Eliminados: `cargar_aproximacion()`, `_resultado_san_jose()`, `_rosa_y_heatmap_san_jose()`,
  `UMBRAL_APROXIMACION_KM`, el checkbox de Gower, el input manual de elevación para la aproximación,
  y el bloque de UI que mostraba factor de ajuste/donante en la pestaña "Contexto climático". San
  José deja de tener una ruta especial vía el export del panel de GWA (Hallazgo 3, `windSpeed.json` +
  `heatmapData.json` + `.lib`) -- ahora usa su propio EPW real (`SITIOS_EPW_REAL["san_jose"]`, mismo
  aeropuerto Juan Santamaría) exactamente igual que Nicoya/Liberia/Finca Favorita. Verificado con la
  app corriendo de verdad (Streamlit + Playwright, no sólo lectura de código): la media anual pasa de
  3.67 m/s (curva de GWA) a 4.03 m/s (EPW real, WMO 787620) -- ambas son datos reales del mismo sitio,
  simplemente de dos fuentes distintas; se elige la fuente más simple y homogénea con el resto de la
  app.
- Agregado (no existía conectado a la UI, aunque `cargar_epw_subido()` ya estaba escrito): un
  `st.file_uploader` en la pestaña "📍 Selección de clima" para subir un `.epw` propio -- para un
  sitio sin estación real cercana, o para usar a propósito el EPW de otro lugar como referencia.
  Mismo resultado unificado que elegir una estación de la lista (`_resultado_desde_epw()`), sin
  ningún ajuste de magnitud.
- La única sensibilización que queda es por ALTURA, no por ubicación: `wind_at_height()`
  (`engine/simulador_pista_a.py`, Hallazgo 20) ya implementa el perfil logarítmico de
  ladybug-tools/ladybug con dos rugosidades (referencia meteorológica vs. sitio destino) -- se
  confirmó de nuevo, leyendo `ladybug/windprofile.py` real (`TERRAIN_PARAMETERS`, fórmula log y de
  potencia), que la tabla `TERRENOS_ENERGYPLUS` y las fórmulas de `wind_at_height()` /
  `wind_at_height_potencia()` ya en este repo coinciden exactas con el código fuente real de
  ladybug-tools -- no hacía falta reescribir nada de esa parte, sólo mantenerla como el único
  mecanismo de sensibilización de velocidad de la app.

**Verificado end-to-end con Chromium real (Playwright), no sólo lectura de código:** búsqueda de
estaciones → elegir San José de la lista (ahora vía su EPW real) → pestaña Contexto climático (rosa
+ heatmap + perfil de viento, sin ningún texto de "aproximación") → Equipos y configuración →
Calcular → Resultados (245 kWh/año, 3 turbinas, corrección de densidad 8.5%) -- sin excepciones. Se
probó también el flujo nuevo de upload manual (subiendo el mismo EPW de San José como archivo propio):
"Sitio activo: EPW subido -- ...epw", mismo resultado que elegirlo de la lista.

**Qué queda sin usar, no borrado:** `engine/gwa_raster.py`, `engine/formas_regionales.py`,
`engine/era5_client.py`, `engine/open_meteo_client.py`, `engine/terrain_classification.py` (Gower/
Köppen/WorldCover) y el ráster `datos_clima/gwa_costa_rica_10m.tif` quedan en el repo como historial
de la investigación (Hallazgo 21-30, 35) pero ya no los importa `app.py`. Los scripts de validación
que sí los usan (`validar_phase_b_clima.py`, `validar_phase_b_simple.py`, `test_phase_b.py`,
`test_bug_media_san_jose.py`) tampoco se tocaron -- documentan una línea de investigación cerrada,
no código de producción.

**Pendiente:** decidir si vale la pena borrar ese código muerto ahora o dejarlo como referencia
histórica; no bloquea nada del flujo actual.

---

### Hallazgo 37 — Aclaraciones de UI post-Hallazgo 36: el heatmap no mostraba m/s reales, y la rosa de vientos vieja no se entendía (12 sectores mal etiquetados, un solo color)

Dos pedidos directos después de ver la app con datos reales de San José (EPW, Hallazgo 36):

**1) El heatmap mes×hora mostraba un índice relativo, no velocidad -- se confundía con m/s.**
El color va de 0 a ~2 porque `heatmap_json_desde_epw()` calcula `valor = media(mes,hora) /
media_anual` (índice adimensional centrado en 1.0), no velocidad -- un valor de 2.0 significa
"el doble de la media anual" (con San José a 4.03 m/s, eso es ~8 m/s reales), nunca "2 m/s". El
gráfico no estaba mal, sólo el hover no aclaraba la conversión. Se agregó la velocidad real al
hover de `crear_heatmap_plotly()` (`app/app.py`).

**Bug real encontrado al implementarlo:** el primer intento usó `customdata` + `%{customdata:.2f}`
en el `hovertemplate` (patrón estándar de Plotly) -- funcionaba perfecto en un HTML standalone
generado con el paquete `plotly` de Python, pero **NO en la app real**: verificado con Streamlit
corriendo + Chromium real (Playwright), el hover mostraba literalmente el texto sin resolver,
`%{customdata:.2f}`, en vez del número. Causa real: la versión de Plotly.js que Streamlit 1.35
trae empaquetada (independiente de la versión del paquete `pip install plotly`) no interpola
`customdata` en trazas `Heatmap`. Arreglado armando el texto del hover ya resuelto en Python,
celda por celda (`text=... , hoverinfo='text'`), sin depender de `customdata` -- funciona en
cualquier versión. **Lección para cualquier gráfico Plotly futuro en esta app:** probar el hover
en la app real (Streamlit + navegador), no sólo con `fig.write_html()` -- las dos rutas pueden
usar versiones distintas de Plotly.js con soporte distinto de features.

**2) La rosa de vientos no se entendía.** Pedido explícito: algo como la rosa de
`github.com/pollination-apps/weather-report` (usa `ladybug.windrose.WindRose`). Dos problemas
reales en la versión vieja: (a) 12 sectores de 30° etiquetados con nombres de compás de 16 puntos
(NNE, ENE, SSO, OSO...), que sólo son correctos a múltiplos de 22.5° -- las etiquetas no
correspondían a los ángulos reales; (b) un solo color por sector, codificando sólo frecuencia
total de esa dirección, sin distinguir viento flojo de fuerte.

Reemplazada por una rosa clásica dirección × velocidad (mismo concepto que
`ladybug.windrose.WindRose`, reimplementado directo con Plotly -- `go.Barpolar` apilado por
`barmode='stack'` -- en vez de agregar `ladybug` como dependencia nueva sólo para un gráfico):
`engine/epw_real.py::rosa_vientos_detallada_desde_epw()` calcula, para 8 sectores de compás
correctos (N/NE/E/SE/S/SO/O/NO, cada uno exacto a 45°) × 5 bins de velocidad (0-2, 2-4, 4-6, 6-8,
>8 m/s), el % de horas del año en cada combinación, más el % de calma (≤0.5 m/s, sin dirección
definida) reportado aparte en el título. Verificado con datos reales de San José: la matriz suma
96.7% + 3.3% de calma = 100% exacto, y confirma un patrón físicamente coherente con la geografía
real (el 50% de las horas del año el viento viene del Este -- consistente con el corredor de
vientos alisios del Valle Central que ya se documentó en hallazgos anteriores), no un artefacto.

**Verificado end-to-end con Streamlit + Playwright real** (San José, ambos gráficos): el heatmap
muestra "Sep Hora: 14:00 Índice: 1.17 (4.72 m/s)"; la rosa nueva muestra N arriba, sentido horario,
8 sectores correctos, leyenda "Velocidad: 0-2 m/s ... >8 m/s", sin ninguna excepción. De paso se
eliminó `graficar_rosa_vientos()` (versión matplotlib vieja, dead code -- no se llamaba desde
ningún lado, sobrevivió al rediseño a Plotly de hace unos commits).

---

### Hallazgo 38 — El heatmap pasa a mostrar m/s reales directo (no un índice), y los gráficos exportan con fondo transparente

Dos pedidos directos después de ver el heatmap nuevo del Hallazgo 37 en un screenshot real (donde
no hay hover): "¿por qué el máximo es sólo 2 m/s?" -- la respuesta seguía sin verse porque el
Hallazgo 37 sólo agregó los m/s reales al HOVER, y un screenshot o imagen exportada no tiene hover.
El gráfico en sí seguía mostrando el índice crudo (máximo visual ~2, etiqueta "Índice de viento").

**Arreglo real, no otro parche al hover:** `crear_heatmap_plotly()` ahora multiplica el índice por
`media_anual` ANTES de graficar y usa ese resultado (m/s reales) como los valores de color del
heatmap -- título "Velocidad media real del viento a 10m (mes × hora)", colorbar en "m/s" (rango
real ~2-8 m/s con San José), hover con el m/s Y el índice entre paréntesis para quien lo quiera. El
dato subyacente (`heatmap_json_desde_epw()`, el índice relativo) no cambió -- sigue siendo el mismo
formato que usa `generar_clima_gwa()` en el código no conectado de Hallazgo 21-30 -- sólo cambió
qué se grafica en `app.py`.

**Aclaración de la otra pregunta del pedido ("¿es a 0m?"):** no, el heatmap (como toda la app desde
Hallazgo 36) es siempre a 10m -- la altura de referencia meteorológica estándar del EPW (columna
`WS10M`), la misma que ya se muestra en "Media anual real (10m): X m/s" en el cintillo verde de la
pestaña. Ni 0m ni la altura de buje de la turbina (eso lo muestra el "Perfil logarítmico de viento"
aparte, más abajo en la misma pestaña).

**Fondo transparente en las exportaciones PNG:** se agregó `paper_bgcolor='rgba(0,0,0,0)'` +
`plot_bgcolor='rgba(0,0,0,0)'` (y el `bgcolor` del área polar de la rosa) a los 5 gráficos Plotly de
la app. Verificado descargando de verdad el PNG del heatmap con el botón de cámara del gráfico
(Playwright) y leyendo los píxeles con Pillow: la imagen exportada es RGBA, con las esquinas en
`(0,0,0,0)` (transparente total) y el área de datos opaca -- confirma que funciona, no sólo que se
puso el parámetro. En pantalla no cambia nada (los gráficos ya viven sobre una tarjeta blanca en la
UI), sólo afecta la imagen descargada.

**Limpieza de paso:** se eliminaron 3 funciones matplotlib más que quedaron sin usar del rediseño a
Plotly de hace unos commits -- `graficar_heatmap_clima()`, `graficar_curva_duracion()`,
`graficar_perfil_viento()` (mismo patrón que `graficar_rosa_vientos()`, ya eliminada en Hallazgo
37) -- y los imports `matplotlib.pyplot` y `plotly.express`, ninguno de los dos usado ya en
`app.py`.

**Pendiente, no resuelto en este hallazgo:** el "Perfil logarítmico de viento" de esta misma pestaña
(`crear_perfil_viento_plotly()`) usa un terreno destino fijo ("suburban") sin importar el z0 que el
usuario elija después en "Equipos y configuración" -- por eso su valor a 10m (~3 m/s) no coincide
con la media real de la estación (4.03 m/s): ya está aplicando de entrada una rugosidad de destino
que reduce la velocidad, antes de que el usuario haya elegido nada. No es un bug (`simular()`, el
cálculo real de producción, sí usa el z0 que el usuario elige) -- es sólo que este gráfico de vista
previa no lo refleja. Si genera confusión real, es un cambio chico (pasarle el z0 elegido en vez de
un valor fijo).

---

### Hallazgo 39 — Slider de altura de buje: el heatmap (y el perfil) ahora muestran la velocidad real a CUALQUIER altura, no sólo a los 10m del EPW; bug real de vectorización encontrado y corregido en `wind_at_height()`

Pedido directo: "quiero ver cómo varía la velocidad del aire no sólo en el perfil sino también en el
heatmap -- quiero que el heatmap cambie con la altura". Antes del Hallazgo 38, el heatmap sólo podía
mostrar la velocidad a 10m (la altura de referencia del EPW); el perfil logarítmico de abajo era la
única vista a otras alturas, y encima con dos problemas reales propios (ver más abajo).

**Un solo slider, "Altura de buje a explorar (m)" (0.5-15m), mueve ahora los dos gráficos a la vez:**
- El heatmap recalcula la velocidad real a esa altura con `wind_at_height()` -- la MISMA fórmula
  logarítmica de dos rugosidades que `simular()` usa para el cálculo real de energía (Hallazgo 20),
  no una aproximación aparte. Título y colorbar cambian con la altura (ej. "...a 3.0m").
- El perfil logarítmico de abajo (ya existía) ahora marca con un punto rojo la velocidad exacta en
  esa misma altura, para comparar visualmente los dos gráficos.
- Los dos usan la MISMA rugosidad de destino (z0) que el usuario elige en "Equipos y configuración >
  Parámetros avanzados" -- antes el perfil ignoraba por completo ese valor (ver bug de abajo).

**Aclaración física importante, no una limitación del gráfico:** como `wind_at_height()` escala la
velocidad por un factor que sólo depende de la altura (misma razón logarítmica para cualquier hora
del año), mover el slider reescala el heatmap COMPLETO por una misma constante -- el patrón (qué
horas/meses son más ventosos que otros) no cambia, sólo la escala de colores. Es el comportamiento
correcto de este modelo de perfil de viento, no algo a corregir.

**Bug real #1, encontrado al implementar esto, no antes:** `wind_at_height()` nunca soportó un
arreglo de alturas -- sólo alturas escalares (un buje real) o arreglos de VELOCIDAD (las 8760 horas).
El perfil logarítmico necesita evaluar 100 alturas a la vez para dibujar la curva completa, y el
`if h_target <= z0:` de la función (comparación de Python normal, no vectorizada) reventaba con
`ValueError: The truth value of an array with more than one element is ambiguous` en cuanto se le
pasó un arreglo de alturas -- confirmado en vivo con Streamlit + Playwright, no en una prueba
sintética. Arreglado vectorizando con `np.where()` en vez de un `if` de Python -- retrocompatible
100% con el uso normal (altura escalar), ahora también acepta un arreglo de alturas.

**Bug real #2, preexistente, encontrado al tocar `crear_perfil_viento_plotly()`:** el parámetro
`z0_ref` de esa función sólo se usaba para el TÍTULO del gráfico ("z0=0.3 m") -- el cálculo en sí
ignoraba `z0_ref` por completo y usaba siempre la ley de potencia con terreno fijo `"suburban"`
(z0=0.5m según `TERRENOS_ENERGYPLUS`, NO 0.3m). El título mentía sobre qué rugosidad se estaba
usando de verdad, y encima no era la que el usuario elegía en "Parámetros avanzados". Arreglado:
ahora usa `wind_at_height()` (la misma ley logarítmica del cálculo real, no la de potencia -- esa
queda sólo para el cross-check explícito de Hallazgo 20) con el `z0` que de verdad se le pasa.

**Verificado end-to-end con Streamlit + Playwright real:** bajando el slider a 3m con San José (z0=0.3
default), el heatmap muestra ~2-4.5 m/s (antes 2-8 m/s a 10m) y el perfil marca "2.02 m/s" en altura
3m -- coincide exacto con `v_hub_medio` que ya calcula `simular()` para ese mismo caso (Hallazgo
anterior sobre cómo se calcula el kWh). También se probó el caso límite (altura por debajo de z0,
ej. z0=1.0 urbano denso + altura=1.0m): la app muestra un aviso explícito en vez de un heatmap
degenerado en ceros o una excepción.

---

### Hallazgo 40 — Arranca la pestaña "Análisis Financiero": auditoría de lo que trajo la sesión "Eco Wind 2" (Flower Turbines + Sol-Ark), dos bugs eléctricos reales confirmados con datasheets, y un hueco de BESS 48V resuelto con dato de mercado (no de fábrica)

Pablo pidió una nueva pestaña "Análisis Financiero" a partir de un plan externo
(`PLAN_ANALISIS_FINANCIERO_ECO_WIND.md`) y de trabajo ya hecho en otra sesión ("Eco Wind
2", PRs #12/#15 de la rama `claude/eco-wind-audit-velocidades-7fv1sy`, ya mergeadas):
`engine/flowerturbines_specs.py`, `engine/flowerturbines_costos.py`,
`engine/solark_specs.py`, `engine/dimensionador_sistema_eolico.py`. Ninguno de los
cuatro está conectado a `app.py` todavía -- es 100% trabajo de integración nuevo, sin
nada que romper.

**Duplicación real encontrada:** `flowerturbines_specs.py` es un duplicado exacto de
los datos que ya vivían en `engine/turbine_specs.py::SPECS_TURBINAS` (Hallazgo 32, ya
usado por `app.py` para las fichas técnicas) -- mismos 11 modelos, mismos valores, pero
con las filas indexadas por el nombre completo del modelo ("Small Tulip Turbine (1m)")
en vez de las claves internas que ya usa la app (`small_tulip`). Dos fuentes de verdad
para el mismo dato, con esquemas de clave incompatibles.

**Dos bugs eléctricos reales confirmados con datasheets, no solo con la palabra de un
"representante"** (ver más abajo la aclaración sobre la fiabilidad de esas respuestas):
`dimensionador_sistema_eolico.py::seleccionar_inversor_solark()` usa
`Potencia_FV_Max_W` (capacidad del puerto SOLAR/MPPT) como límite para dimensionar el
arreglo eólico -- pero las turbinas Flower Turbines (salida regulada 48V CC) se
conectan al puerto de BATERÍA, no al solar (confirmado por dos fuentes independientes,
y es la única lectura que tiene sentido eléctrico: el MPPT de los inversores Sol-Ark
tiene voltaje de arranque de 125-200V, muy por encima de 48V fijos). El límite correcto
es la corriente máxima de carga de batería (`Corriente_Carga_Descarga_Max_A`) por el
voltaje del bus -- para el 18K eso da **16,800W (350A×48V), menos de la mitad** de los
32,400W que usa hoy el código. Segundo bug: `seleccionar_bess_solark()` filtra con un
`or` que es cierto para las 3 baterías del catálogo sin importar el voltaje, así que en
la práctica no filtra nada -- y ninguna de esas 3 baterías (Serie L3, 307-614V) es
compatible con el bus de 48V de todos modos.

**Verificado con datasheets reales (PS-00019 Rev.11 480V, PS-00020 Rev.13 208V, y
cotización de fábrica Q1136780 Miami Greentech/Sol-Ark, 28/ago/2026), no solo con la
respuesta en texto de "Sol-Ark":** los 6 precios ya cargados en `solark_specs.py`
(18K/30K/60K inversores + 3 BESS Serie L3) coinciden EXACTOS con la cotización real, y
todas las specs técnicas (voltajes, corrientes, dimensiones, peso) coinciden con los
datasheets. Dos hallazgos nuevos de esa verificación: (1) la cotización trae 4
inversores residenciales más baratos (9K $2,926.83, 12K $3,926.83, 12K-LL $3,657.32,
15K $4,756.10) que no están cargados todavía -- justo la línea que SÍ es compatible en
DC directo con el bus de 48V; (2) el SKU `L3-HVR-60KWH` es en realidad DOS baterías
físicamente distintas según con qué inversor se empareje (307V con el 30K-208V, 614.4V
con el 60K-480V, mismo precio) -- `solark_specs.py` sólo tiene cargada la variante de
614.4V.

**Aviso de calidad de fuente, aplicado con la misma vara a ambos "fabricantes":** las
respuestas en texto atribuidas a "Sol-Ark" y "Flower Turbines" en esta conversación no
son documentos oficiales -- la de "Flower Turbines" en particular traía pegado un
reporte de estado de otra sesión de Claude Code (checkmarks y un link a PR), lo que
indica que es una respuesta generada por IA simulando al fabricante, no una
comunicación real. Se trató como hipótesis razonable pero no verificada, igual que se
hizo con el "$11,200 de turbinas" inventado del plan original. La respuesta de Sol-Ark
sí resultó consistente con los datasheets reales donde se pudo cruzar (naming
18K-2P-N/LV, arquitectura de puertos) pero tampoco es un documento oficial -- por
ejemplo, la lista de socios de batería de 48V que dio no menciona a EG4, que en la
práctica real del mercado es uno de los socios más comunes de Sol-Ark (misma
distribuidora en EE.UU., Signature Solar) -- una señal de que la lista podría no ser
completa.

**Hueco real resuelto (parcialmente): no existe una batería Sol-Ark de 48V.** Sol-Ark
confirmó (de nuevo, sin datasheet propio, sólo por texto) que no fabrica batería de
litio propia para la línea residencial de 48V -- su único producto de batería con
marca propia (Serie L3) es exclusivamente de alta tensión. Se agregó
`engine/eg4_specs.py` (EG4 LifePower4 5.12kWh y WallMount 14.3kWh, tercero, NO
Sol-Ark) con datos reales del datasheet del fabricante + precio de mercado (el más
bajo verificado entre varios distribuidores de EE.UU. en una búsqueda web del
02/sep/2026) -- **diferencia importante declarada en el propio archivo:** este precio
es RETAIL (ya con margen del distribuidor puesto), no una cotización de fábrica como
la de Sol-Ark -- son datos de calidad distinta, no deben tratarse igual de firmes.

**Se creó `engine/price_calculator.py`** con la fórmula de cadena de valor del plan
(`Precio_Venta = (Costo_Base + $2,500) × 1.30`) en un solo lugar, para aplicarla igual
a cualquier componente nuevo. Al aplicarla de verdad al módulo EG4 más chico (costo
base $1,199) salió **$939/kWh** -- muy por encima de lo razonable para LiFePO4
(~$300-500/kWh típico) porque el fee fijo de $2,500 de importación, pensado para un
componente grande (turbina/inversor/banco completo), más que duplica el costo de un
módulo de batería chico si se aplica por unidad. **Esto expone una pregunta real sobre
la fórmula que el plan nunca probó con un componente barato: el fee de importación,
¿es por SKU o por embarque/proyecto completo?** Con la lectura literal (por SKU), un
proyecto típico de varias líneas (turbinas + inversor + varios módulos de batería)
pagaría múltiples fees de $2,500 -- $20,000+ solo en "importación" para un sistema
residencial modesto, casi seguro muy por encima de la realidad de un solo envío
consolidado.

**Pendiente en el momento de escribir esto -- ver Hallazgo 41, que resuelve las cuatro
primeras decisiones de esta lista:**
- [x] ~~¿El fee de importación de $2,500 es por SKU o por proyecto/embarque
      completo?~~ -- resuelto (Hallazgo 41): se deja como parámetro
      (`modo_importacion`), no se hardcodea ninguno de los dos.
- [x] ~~Corregir los dos bugs eléctricos de `dimensionador_sistema_eolico.py`~~ --
      resuelto (Hallazgo 41): capacidad real del puerto de batería, y BESS de 48V
      movido a EG4 en vez de buscar en el catálogo HV de Sol-Ark.
- [x] ~~Decidir la arquitectura de datos de turbinas~~ -- resuelto (Hallazgo 41):
      `turbine_specs.py` como única fuente, `flowerturbines_specs.py`/`_costos.py`
      eliminados.
- [x] ~~Cómo tratar en la pestaña financiera los sistemas que necesiten 30K/60K
      (HV)~~ -- resuelto en parte (Hallazgo 41): paquetes de fábrica AL13 (30kW/60kW)
      cuando el arreglo calza exacto; nota pendiente explícita (no bloqueo) para
      arreglos personalizados que no calzan con ningún paquete.
- [ ] Agregar los 4 inversores residenciales que sí tienen precio real
      (9K/12K/12K-LL/15K) pero les falta ficha técnica completa (sólo tenemos precio
      de la cotización, no datasheet) -- todavía no agregados a `solark_specs.py`.
- [ ] Agregar la variante de 307V del BESS `L3-HVR-60KWH` (falta, ver Hallazgo 40).
- [ ] Conseguir una cotización de fábrica/mayorista real de EG4 (o de cualquiera de los
      otros socios de 48V) para reemplazar el precio retail por uno de la misma calidad
      que Sol-Ark.
- [ ] Verificar Flower Turbines contra un datasheet o cotización real -- todavía no se
      pudo, a diferencia de Sol-Ark (y la respuesta de Hallazgo 41 sobre los paquetes
      AL13 tampoco está verificada contra una fuente primaria).

---

### Hallazgo 41 — Se resuelven las cuatro decisiones pendientes de Hallazgo 40: cadena de valor parametrizada, dos bugs eléctricos corregidos, specs de turbinas unificadas, y ruta de acople HV con paquete de fábrica AL13

Pablo resolvió las cuatro preguntas abiertas del Hallazgo 40:

1. **Fee de importación por SKU vs. por proyecto: no se decide, se parametriza.** "Es
   necesario sensibilizar todos los datos, deja los números no hardcodeados pero sí
   con un valor para poder hacer recálculos después." `engine/price_calculator.py`
   agrega `calcular_precio_venta_proyecto(costos_base, modo_importacion="por_sku" |
   "por_proyecto")` -- ninguno de los dos modos se borra, los dos quedan disponibles
   como parámetro explícito de `dimensionar_sistema_eolico_completo()`. Con el caso de
   ejemplo (3 turbinas + inversor + BESS, 5 líneas): "por_sku" da $57,488 de precio de
   venta, "por_proyecto" da $44,488 -- $13,000 de diferencia, confirma que la elección
   sí importa y no se puede dejar sin decidir para una cotización real, pero mientras
   tanto la app puede correr con cualquiera de los dos sin reescribir código.

2. **Los dos bugs eléctricos de Hallazgo 40 -- corregidos en `dimensionador_sistema_eolico.py`:**
   - `seleccionar_inversor_solark()` ahora calcula la capacidad real desde el puerto de
     BATERÍA (`Corriente_Carga_Descarga_Max_A × Voltaje_Nominal_CC_V`, leído directo de
     `solark_specs.py`) en vez del puerto solar (`Potencia_FV_Max_W`) -- para el 18K
     esto baja el límite real de 32,400W a 16,800W. También filtra de verdad por
     `Voltaje_Nominal_CC_V == voltaje_sistema_V` (antes el chequeo `if voltaje_sistema_V
     == 48` era tautológico, siempre verdadero, nunca comparaba nada).
   - `seleccionar_bess_solark()` se reemplaza por `seleccionar_bess_48v()`, que ya no
     busca en el catálogo Sol-Ark (100% alta tensión, ningún producto ahí es 48V) sino
     en `eg4_specs.py` -- consistente con lo que confirmó Sol-Ark en Hallazgo 40 (no
     fabrican batería de litio propia para su línea residencial).
   - Ninguna de las dos funciones lanza excepción si no hay match: devuelven
     `compatible: False` con la razón, para que el resto del CAPEX se siga calculando
     (turbinas + lo que sí se pudo dimensionar) en vez de frenar todo -- "no dejemos de
     calcular", el mismo criterio que ya se venía aplicando en toda la sesión.

3. **Specs de turbinas unificadas, sin duplicado.** Se agregó `costo_usd` (real, de
   `flowerturbines_costos.py`) a las 4 filas de `engine/turbine_specs.py::SPECS_TURBINAS`
   que ya tenían precio de lista (small_tulip, medium_tulip, three_m_tulip, al13_2m) --
   `None` en las otras 7. Se eliminan `engine/flowerturbines_specs.py` y
   `engine/flowerturbines_costos.py` -- eran datos duplicados con un esquema de claves
   incompatible con el resto de la app (nombres completos en vez de las claves
   canónicas `small_tulip`/`al13_2m`/etc.). `turbine_specs.py` queda como única fuente
   de verdad, tal como ya estaba conectado a `app.py` desde Hallazgo 32.

4. **Ruta de acople para 30K/60K: no se bloquea, se usa el paquete de fábrica AL13
   cuando aplica.** Flower Turbines confirmó (misma cautela de fuente que el resto de
   las respuestas de chat, no verificado contra datasheet/cotización real) que venden
   paquetes On-Grid "todo incluido" -- 6x AL13 de 6 módulos (~30kW, $126,100) o 6x AL13
   de 8 módulos (~60kW, $188,500) -- con inversor y BESS de alta tensión ya integrados
   de fábrica, evitando el problema de acople DC que un arreglo personalizado sí tiene.
   `PAQUETES_INDUSTRIALES_AL13` en `dimensionador_sistema_eolico.py`: si el arreglo
   seleccionado calza exacto con uno de los dos paquetes, se sugiere ese precio cerrado
   (con la advertencia de fuente); si no calza (arreglo personalizado que igual supera
   la línea residencial), se deja `pendiente_ingenieria_acople=True` con una nota
   explícita -- nunca una excepción que corte el cálculo.

**Verificado con dos casos reales corridos end-to-end** (`python3 -m
engine.dimensionador_sistema_eolico`): un arreglo chico (3 turbinas distintas) resuelve
completo con el 18K + un módulo EG4, precio de venta calculado con las líneas
individuales; un arreglo de 6x AL13-6m (30kW) no encuentra inversor residencial
compatible, no revienta, y sugiere el paquete industrial correcto automáticamente.

**Sigue pendiente, no resuelto en este hallazgo:** cotización de fábrica/mayorista real
de EG4 (hoy es precio retail), verificación de Flower Turbines contra datasheet propio,
y agregar los 4 inversores residenciales nuevos (9K/12K/12K-LL/15K) que salieron en la
cotización de Sol-Ark pero sin datasheet técnico completo todavía.

---

### Hallazgo 42 — El BESS "L3-HVR-60KWH" no es un solo producto: son dos configuraciones de voltaje distintas (614.4V y 307V) según con qué inversor se empareje, resuelto sin pregunta nueva porque el dato ya estaba en un datasheet ya leído

Al revisar `engine/solark_specs.py` para responder la pregunta de los 4 inversores
residenciales faltantes (ver más abajo), apareció algo que no se había notado antes: la
única fila de BESS de 60kWh (`"L3-HVR-60KWH (BESS Exterior)"`) tenía `Voltaje_Nominal_CC_V
= 614.4`, un voltaje que sólo es compatible con el inversor **60K-3P-480V** — pero el
mismo módulo también se vende para emparejar con el **30K-3P-208V**, a un voltaje CC
distinto (307V), porque el pack interno se arma con la misma celda de 5.12kWh/51.2V en
una configuración diferente (12s1p para 614.4V, 6s6p para 307V — en paralelo en vez de en
serie, por eso el mismo número de celdas da voltajes tan distintos).

Este dato NO requirió una pregunta nueva a Sol-Ark: ya estaba en el datasheet PS-00020
Rev.13 (208V) leído en el Hallazgo 40 para verificar el 30K, columna "Outdoor" — sólo no
se había extraído la fila de BESS de esa columna en ese momento porque el foco era el
inversor, no la batería.

**Cambio hecho en `engine/solark_specs.py`:**
- La fila existente se renombra a `"L3-HVR-60KWH (BESS Exterior, 614.4V con
  60K-3P-480V)"` — mismo `Costo_USD` (34,424.44) y misma capacidad, sin otro cambio.
- Se agrega una fila nueva `"L3-HVR-60KWH (BESS Exterior, 307V con 30K-3P-208V)"`: mismo
  SKU y precio, pero `Voltaje_Nominal_CC_V=307` (rango operativo 294-336V),
  `Potencia_Inversor_Compatible_W=30000`, mismo peso de fábrica (628kg, vs. 950kg de la
  variante 614.4V — dato real del datasheet, no un error de transcripción).

Verificado que ningún otro archivo dependía del string exacto anterior (`grep` sin
resultados fuera de `solark_specs.py`), que el módulo compila, y que
`get_solark_bess_df()` ahora devuelve 4 filas de BESS todas con voltaje/potencia
compatible distintos entre sí (antes había una ambigüedad silenciosa: la única fila de
60kWh no dejaba claro que era 60K-only, `seleccionar_bess_solark()` — ya reemplazada en
Hallazgo 41 de todas formas — no la habría podido usar para el 30K).

**Pregunta enviada a Pablo (pendiente de respuesta), en texto plano para copiar y llevar
a soporte técnico de Sol-Ark:** los 4 inversores residenciales de la cotización real
(9K-2P, 12K-2P, 12K-2P-LL, 15K-2P) sólo tienen precio confirmado, no datasheet técnico
completo — falta especialmente la corriente máxima de carga/descarga del puerto de
batería (el dato que más importa para `seleccionar_inversor_solark()`, ya que ese es el
puerto real donde se conecta la salida de 48V de Flower Turbines, no el puerto solar/
MPPT — ver Hallazgo 40). Se le preguntó a Pablo si puede conseguir el datasheet oficial
o soporte técnico real, o si mientras tanto prefiere que se carguen con una estimación
explícita (corriente escalada proporcionalmente desde el 18K según potencia CA, marcada
como no verificada) para no dejar bloqueada la pestaña financiera en sistemas residenciales
chicos. Sin resolver todavía.

---

### Hallazgo 43 — Se mergeó a `main` la rama de la sesión "Eco Wind 2" sin pasar por PR #19: reconciliación completa, dos hallazgos reales de datos fabricados encontrados y corregidos

Pablo mergeó directamente a `main` la rama `claude/eco-wind-audit-velocidades-7fv1sy` (6
commits de otra sesión, corrida en Claude Haiku 4.5) antes de que este chat terminara de
revisarla, y pidió cerrar el otro chat y limpiar `main` para poder desplegar a Cloud Run.
Como esa rama era vieja (se separó de `main` 15 commits atrás, antes del pivote a EPW-only
y antes de Hallazgo 41/42), el merge dejó `main` sin los dos hallazgos anteriores -- hubo
que reconciliar todo en esta sesión.

**Dos hallazgos reales de datos fabricados, encontrados ANTES de aceptarlos (mismo
criterio de todo el chat: verificar contra la fuente, no contra lo que dice el commit):**

1. **Los 4 inversores Sol-Ark LATAM nuevos (9K, 12K, 12K-2P-LL, 15K) tienen specs técnicas
   fabricadas, no de datasheet real.** El commit dice "complete technical specifications
   from QuotesReport PDF" -- pero una cotización no trae peso ni dimensiones ni corriente
   de batería. Prueba concreta: las 4 filas comparten EXACTAMENTE las mismas dimensiones
   que el 18K real (863x464x282mm) y el peso/corriente de carga escalan en pasos
   perfectamente lineales (200/250/250/300A, 55/58/58/60kg) desde el 18K -- patrón de
   estimación por extrapolación, no 4 productos medidos por separado. Una respuesta de
   "Sol-Ark" que Pablo pegó en el chat para estos mismos 4 modelos lo confirma: se
   contradice a sí misma (una tabla dice `[TBD per Datasheet]` para 9K/15K mientras el
   texto de arriba da números "confirmados" para esos mismos modelos) y da dimensiones
   DISTINTAS (748.5x465x254mm, 35kg) a las del commit para el mismo 12K -- dos "fuentes
   oficiales" no dan medidas físicas distintas para la misma caja. **Corrección:** se
   agregó `Specs_Verificadas: False` a las 4 filas en `solark_specs.py` (con la
   advertencia completa en el docstring del módulo), y `seleccionar_inversor_solark()`
   ahora propaga esa bandera (`specs_verificadas`) y agrega el aviso al texto de `razon`
   cuando selecciona uno de estos 4 -- el precio (sí parece real, no sigue un patrón
   sospechoso) se mantiene, lo técnico queda marcado como no confiable. Pregunta con el
   datasheet real sigue pendiente con Pablo (ver arriba).

2. **Los precios nuevos de Flower Turbines para los 4 modelos YA verificados
   (small_tulip, medium_tulip, three_m_tulip, al13_2m) son exactamente 5.263% (=1/0.95)
   más altos que los ya verificados contra `flowerturbines_costos.py`, sin excepción en
   las 4 líneas.** Ninguna cotización real de mercado cae en la misma razón exacta para 4
   productos de precio tan distinto ($1,153 a $12,905) por casualidad -- es
   matemáticamente el mismo número con un +5.26% aplicado, no dos cotizaciones
   independientes. **Corrección:** se descartaron esos 4 precios alternativos, se
   mantienen los ya verificados. Los OTROS 5 precios que trajo esa misma rama, para
   modelos que antes no tenían ninguno (large_tulip $24,700, al13_6m $20,215, al13_8m
   $25,545, ecoroof_flat_3 $9,295, ecoroof_flat_5 $12,545), sí se incorporaron a
   `turbine_specs.py` -- pero con `costo_usd_fuente: "no_verificado"` (documentado en el
   docstring del módulo), a diferencia de los 4 con `"verificado"`. Mejor tener el número
   marcado que no tenerlo, pero sin fingir la misma confianza.

**Reconciliación de arquitectura (Hallazgo 41/42 nunca habían llegado a `main` -- PR #19
seguía abierto sin mergear cuando Pablo mergeó la otra rama):**
- Se hizo `git merge origin/main` sobre la rama de este chat (que sí tenía Hallazgo
  41/42) en vez de al revés, para no perder ninguna de las dos líneas de trabajo.
- `flowerturbines_specs.py`/`flowerturbines_costos.py` (duplicados, Hallazgo 41) se
  volvieron a borrar -- la otra rama los había modificado (por eso hubo un conflicto de
  "modify/delete" real al mergear), pero ya se habían rescatado sus 5 precios nuevos
  hacia `turbine_specs.py` antes de borrar.
- `price_calculator.py`: conflicto real (las dos ramas habían creado el archivo por
  separado). Se conservaron las funciones nuevas de la otra rama (`calcular_bom_*`,
  `estimar_ahorro_anual`, `calcular_precio_kwh_instalado`) y se reincorporó
  `calcular_precio_venta_proyecto()` (el `modo_importacion` que Pablo pidió parametrizar
  en Hallazgo 41) que se había perdido por completo en el merge que hizo la otra sesión.
- `sistema_eolico_completo.py` (nuevo, de la otra rama -- integra dimensionamiento +
  `FinancialEngineEolico`, capa que este chat todavía no había construido, sí
  aprovechable): tenía un bug real -- si una turbina seleccionada no tenía precio en
  `flowerturbines_specs.py`, sumaba `+= 10000` en silencio ("Default para turbina
  media"), sin ninguna nota visible en el resultado. Corregido: ahora reusa
  `arquitectura["arreglo_turbinas"]["costo_total_usd"]` (ya calculado por
  `dimensionador_sistema_eolico.py` desde `turbine_specs.py`, la única fuente de verdad)
  y, si falta el costo de alguna turbina o el inversor no es compatible, devuelve un
  resultado parcial con `pendiente_ingenieria_o_costo=True` y una nota explícita en vez
  de adivinar un número o lanzar una excepción. También se actualizó para recibir claves
  canónicas (`small_tulip`, etc.) en vez de nombres completos de modelo, consistente con
  el resto de la app.
- `financial_engine_eolico.py` (motor CAPEX/OPEX/Payback/ROI/NPV) se mantiene tal cual
  vino -- se revisó la fórmula, no se encontró ningún error, y parametriza bien lo que
  Pablo pidió (% instalación, % mantenimiento, tasa de descuento, vida útil).
- `app/requirements.txt` (archivo huérfano desde antes del pivote a EPW-only, con
  `rasterio`/`geopy` de la era GWA que ya no se usa, y una versión de streamlit
  incompatible con la que realmente se usa en `Dockerfile`/`requirements.txt`) se borró
  -- no lo usaba ni el Dockerfile ni `cloudbuild.yaml`, sólo podía confundir a quien
  fuera a desplegar.
- El Dockerfile/`cloudbuild.yaml`/`app/cloud_secrets.py` que trajo la otra rama (fix de
  puerto dinámico para Cloud Run) se revisaron y no tienen ningún secreto real
  hardcodeado -- son aprovechables tal cual para el deploy que pidió Pablo.

**Verificado antes de dar por cerrado este hallazgo:** `py_compile` limpio en todo
`engine/`/`app/`; las 32 pruebas existentes (`tests/test_price_calculator.py`,
`tests/test_financial_engine_eolico.py`) pasan; `python3 -m engine.dimensionador_sistema_eolico`
y `python3 -m engine.sistema_eolico_completo` corren end-to-end sin error; la app real
(`streamlit run app/app.py`) arranca y responde 200 sin ningún error en el log --
`app/app.py` no fue tocado por ninguna de las dos ramas en conflicto, así que el pivote a
EPW-only y todo el trabajo de UI (Hallazgo 36-39) llegó intacto a este punto.

---

### Hallazgo 44 — Pablo consiguió los 5 datasheets reales de Sol-Ark: los 4 inversores residenciales quedan con specs verificadas, y una confirmación adicional del 18K

Pablo subió 5 PDFs oficiales de Sol-Ark: PS-00034 Rev.3 (9K), SK150-0003 Rev.3 (12K
estándar), PS-00060 v1.1 (12K-2P-LL), PS-00001 Rev.7 (15K), y PS-00044 Rev.2 (18K, para
recontrastar el que ya se tenía). Se leyeron con `pymupdf` (los otros 4 se habían leído
directo con el lector de PDF; el del 18K, de 17 páginas nominales pero 2 páginas de
contenido real, necesitó extracción de texto porque `pdftoppm`/poppler-utils no está
disponible en este sandbox — apt-get bloqueado por la política de red).

**Se confirma que los datos que Hallazgo 43 había marcado `Specs_Verificadas=False`
efectivamente estaban fabricados, con diferencias reales grandes** — no un simple
redondeo:

| Campo | 9K (fabricado → real) | 12K-LL (fab. → real) | 12K está. (fab. → real) | 15K (fab. → real) |
|---|---|---|---|---|
| Potencia FV máx. | 18,000 → **13,000W** | 24,000 → **19,200W** | 24,000 → **12,000W** | 30,000 → **23,400W** |
| Corriente carga/descarga bat. | 200 → **185A** | 250 → **220A** | 250 → **185A** | 300 → **275A** |
| Passthrough | 200 → 200A (ok) | 200 → **100A** | 200 → **63A** | 200 → 200A (ok) |
| Dimensiones (mm) | 863x464x282 → **807x494x306** | 863x464x282 → **654x452x254** | 863x464x282 → **750x450x254** | 863x464x282 → **838x494x306** |
| Peso | 55 → **61.2kg** | 58 → **29.5kg** | 58 → **35.4kg** | 60 → **61.2kg** |
| Rango voltaje batería | 41-63V → **43-63V** | 41-63V → **43-59V** | 41-63V → **43-63V** | 41-63V → **43-59V** |

Los 4 modelos son físicamente distintos entre sí en los datos reales (dimensiones,
peso y corrientes todos diferentes) — confirma la sospecha de Hallazgo 43 de que el
patrón de escalado lineal que tenían los datos fabricados no correspondía a 4
productos reales medidos por separado. El **precio** de los 4 (único dato que
Hallazgo 43 había aceptado) no cambió — sigue siendo el de la cotización real.

**Otros hallazgos menores del lote de PDFs:**
- El "12K" en realidad son DOS productos distintos con el mismo número: el "12K-2P-N"
  estándar (SK150-0003) y el "12K-2P-LL" Limitless (PS-00060) — no una variante de
  firmware del mismo hardware. Ya estaban separados como dos filas desde Hallazgo 43
  (por precio), y ahora también tienen specs técnicas propias y distintas.
- El "12K" estándar tiene una particularidad de nameplate real: su potencia nominal de
  9,000W CA continua + 3,000W CC de baterías = 12,000W "total" -- no son 12,000W de
  salida CA continua como en los otros modelos. Documentado en `Notas_Tecnicas`.
  También es el único de los 4 que sólo admite batería de Litio (no Plomo-Ácido).
- Se corrige de paso un error real que ya traía el 18K desde antes de este hallazgo
  (no introducido por Hallazgo 43): `Stackable=False` contradecía al propio datasheet
  PS-00044 Rev.2 ("Apilable en Paralelo: Yes; Max 12"). Corregido a `True`.

**Verificado:** `py_compile` limpio, las 32 pruebas existentes siguen pasando,
`dimensionador_sistema_eolico.py` y `sistema_eolico_completo.py` corren end-to-end y
seleccionan correctamente el inversor más chico que alcanza según la nueva capacidad
real de cada uno (ej.: un arreglo de 1,600W ahora resuelve con el 9K real, 8,880W de
capacidad de batería, en vez de con datos fabricados).

**Pendiente, no resuelto en este hallazgo:** la reconciliación del PDF del 18K arrastró
una ambigüedad de extracción de texto (una tabla a 3 columnas hizo aparecer un valor
suelto "275A" que no correspondía a ningún campo del 18K) — se resolvió por
triangulación (5 valores del bloque de batería calzan exactamente con las 5 etiquetas
en el orden correcto, dando 350A, que además coincide con el dato ya verificado antes)
pero no se guardó el PDF renderizado a imagen para confirmarlo visualmente. Si en algún
momento hay dudas sobre el 18K, vale la pena revisar esa página con un lector de PDF
que sí renderice imagen (este sandbox no pudo, ver arriba).

---

### Hallazgo 45 — Deploy a Cloud Run falla con "STARTUP TCP probe... DEADLINE_EXCEEDED": imagen de Docker con ~105MB de datos que la app en producción no usa, más ajuste de memoria/CPU de arranque

Pablo reportó (captura del Explorador de registros de Cloud Run) que la revisión
`eco-wind-00006-2pq` fallaba al arrancar: *"Default STARTUP TCP probe failed... The
instance was not started. Connection failed with status DEADLINE_EXCEEDED"* — el
contenedor nunca llegó a escuchar en el puerto 8080 dentro del tiempo que Cloud Run le
da al arranque. Esto pasó DESPUÉS del fix de la otra sesión (commit `747382b`, unificar
ENTRYPOINT+CMD) — o sea, ese fix no alcanzó solo.

**Auditoría del código primero** (antes de tocar config de Cloud Run a ciegas): se
revisó todo lo que `app.py` importa, directa e indirectamente, buscando trabajo pesado
a nivel de módulo (que corre una sola vez al arrancar, antes de que Streamlit levante
el servidor) — no se encontró ningún catálogo ni archivo grande leído en el momento del
`import` (el catálogo de 5,276 estaciones y los EPW se leen dentro de funciones, no al
importar el módulo). El código de la app en sí arranca rápido — confirmado localmente
otra vez con `streamlit run app/app.py` (Hallazgo 43), responde 200 en unos 10s.

**El problema real encontrado: la imagen de Docker carga ~105MB de datos que la app
jamás usa en producción**, lo que hace más lento el "cold pull" de la imagen en cada
arranque de instancia nueva (justo la ventana de tiempo que el probe de arranque está
midiendo):
- `documentos_tecnicos/` (83MB, los 91 manuales técnicos de Flower Turbines/Sol-Ark) —
  sólo lo referencia `engine/estructural_asce7.py`, un módulo de investigación de la
  Pista B/estructural que `app.py` NO importa (confirmado: ningún import, directo ni
  transitivo, lo alcanza).
- `datos_clima/gwa_costa_rica_10m.tif` (22MB) y `datos_clima/gwa_juan_santamaria/`
  (92KB) — el ráster real de GWA de la línea de investigación que Hallazgo 36 decidió
  abandonar por completo (EPW-only). Confirmado con `grep` que ya no queda ningún
  `import rasterio` en todo el repo — este dato ya no lo usa nada.

**Corrección:** se agregan ambas rutas a `.dockerignore` — los archivos NO se borran
del repositorio (siguen disponibles para consulta/investigación en git), sólo dejan de
viajar dentro de la imagen que se despliega. Además, dos ajustes de resiliencia en
`cloudbuild.yaml` que no cuestan más en régimen normal pero sí ayudan directamente
contra un arranque lento: memoria 1Gi → 2Gi (Streamlit + pandas + numpy + plotly +
folium es una pila de imports pesada; si el proceso se queda sin memoria durante el
arranque, Cloud Run lo ve exactamente igual que un timeout, porque el contenedor nunca
llega a abrir el puerto) y `--cpu-boost` (CPU completa sólo durante el arranque, se
apaga después).

**Bug real encontrado de paso, no relacionado al timeout pero sí a Hallazgo 43:**
`requirements.txt` (el que de verdad usa el `Dockerfile`) no tenía `geopy` — la
librería que `engine/epw_real.py` usa para geocodificación por nombre (`Nominatim`,
`Photon`). El import está protegido con `try/except ImportError` así que no rompe nada,
pero en producción la búsqueda de sitio "por nombre" quedaría silenciosamente
deshabilitada sin ningún aviso. Se agrega `geopy` a `requirements.txt`. De paso se
quitan `matplotlib` y `scipy`: confirmado con `grep` que ningún módulo que `app.py`
alcanza (directa o transitivamente) los importa de verdad — sólo aparecían en un
comentario/docstring de `flower_turbines_curves.py` mencionando que `scipy.optimize`
se usó para AJUSTAR los coeficientes durante el desarrollo, no en tiempo de ejecución.

**Pendiente:** esto no se pudo probar contra el Cloud Run real de Pablo (sin acceso a
su proyecto de GCP desde este sandbox) — es la corrección más probable según la
auditoría del código y el patrón de falla reportado (imagen pesada + probe de TCP que
se agota), pero si el siguiente deploy sigue fallando, el log de Cloud Build (no sólo
el de Cloud Run) durante el `docker build` diría si el problema está en otro lado.

---

### Hallazgo 46 — El log de Cloud BUILD (no el de Cloud Run) revela el verdadero bloqueo: el heredoc de `config.toml` nunca llegó a construir la imagen

Pablo pegó el log de Cloud **Build** (el paso de `docker build`, distinto del log de
Cloud Run de Hallazgo 45) y ahí aparece el error real, uno anterior a todo lo demás:

```
Error response from daemon: dockerfile parse error line 31: unknown instruction: [SERVER]
```

La línea 31 es `[server]`, el encabezado de sección del `RUN cat > ~/.streamlit/config.toml
<< 'EOF' ... EOF` (heredoc) que ya traía el Dockerfile desde antes de Hallazgo 45 (de
hecho desde el commit `7b2f262`, y el fix `747382b` de la otra sesión sólo unificó
ENTRYPOINT+CMD, no tocó este heredoc). **La imagen nunca llegó a construirse** en
ningún deploy hasta ahora -- el `DEADLINE_EXCEEDED` de Hallazgo 45 y este error de
parseo son dos síntomas de la misma raíz, pero el de Hallazgo 45 alcanzó a levantar
*alguna* imagen vieja cacheada; este último ya ni eso.

**Causa real:** un heredoc dentro de un Dockerfile (`<< 'EOF'`) es una función de
BuildKit, no de Docker clásico -- necesita que el motor de Docker que ejecuta el build
tenga BuildKit activo para interpretarlo como "contenido de archivo" en vez de leer
cada línea como si fuera una instrucción de Dockerfile normal. El builder que usa Cloud
Build (`gcr.io/cloud-builders/docker`) no lo tiene activo por defecto, y agregar
`# syntax=docker/dockerfile:1` arriba del archivo (que sí estaba, desde el fix de la
otra sesión) NO alcanza para forzarlo si el motor por debajo no corre con BuildKit --
por eso Docker leyó `[server]` línea por línea y lo interpretó como una instrucción
`[SERVER]` que no existe.

**Corrección, sin heredoc (0% dependiente de BuildKit):** se crea `.streamlit/config.toml`
como archivo normal del repositorio (mismo contenido que tenía el heredoc, sin el
`port = 8080` hardcodeado -- el puerto real siempre lo define `$PORT` vía la bandera
`--server.port` de la línea `CMD`, tenerlo también en el TOML sólo confundía) y el
Dockerfile ahora sólo hace `COPY . .` (que ya trae el archivo, `.dockerignore` no lo
excluye) -- Streamlit encuentra la configuración de proyecto sola en
`<directorio de trabajo>/.streamlit/config.toml` sin necesitar ninguna instrucción
extra. `COPY` es una instrucción clásica de Dockerfile, funciona igual con o sin
BuildKit. Se quita también el `# syntax=docker/dockerfile:1` (ya no hace falta nada
de BuildKit en este Dockerfile).

**Verificado:** el TOML nuevo parsea limpio (`tomllib.load`), `streamlit run app/app.py`
sigue arrancando y respondiendo 200 con la config nueva en su lugar. No se pudo correr
`docker build` real en este sandbox (el daemon de Docker no está corriendo acá, sólo el
binario) -- el Dockerfile resultante usa únicamente instrucciones clásicas
(`FROM/WORKDIR/RUN/COPY/ENV/EXPOSE/HEALTHCHECK/CMD`), sin heredocs ni ninguna otra
sintaxis que dependa de BuildKit, así que no hay ningún elemento nuevo que el builder
de Cloud Build no sepa interpretar.

---

### Hallazgo 47 — Revisión de identidad visual (Antigravity/Gemini): favicon y fondo forzado corregidos, un hallazgo de la otra IA estaba desactualizado

Pablo le pidió a otra herramienta de IA (Antigravity, sobre Gemini, sacando su propio
clon del repositorio) que auditara `app.py` contra unos lineamientos de identidad
corporativa de ECO Consultor. Reportó 4 incumplimientos. Se verificó cada uno contra el
estado real del repo (no se aceptó el reporte a ciegas, mismo criterio de todo este
proyecto) antes de tocar nada:

- **Favicon con emoji** (`page_icon="🌬️"`) -- confirmado real. Corregido a
  `page_icon=LOGO_ECO` (`Recursos Visuales/eco_logo.png`, 800x800 con transparencia, ya
  importado en `app.py` desde Hallazgo 32) -- verificado con Playwright que el navegador
  ahora sirve ese PNG como favicon real, no el emoji.
- **Fondo forzado que rompe modo oscuro** (`.stApp {{ background-color: {FONDO}; }}`
  inyectado a mano) -- confirmado real. Se quita esa única regla; el fondo ahora lo
  aplica Streamlit de forma nativa desde `.streamlit/config.toml::theme.backgroundColor`
  (que ya existe desde Hallazgo 46, aunque se agregó por una razón distinta -- arreglar
  el build de Docker, no este tema de diseño). Verificado con Playwright: el color de
  fondo del `body` sigue siendo exactamente `#E8F0F3`, mismo resultado visual, screenshot
  comparado sin ninguna diferencia -- sólo cambió QUIÉN lo aplica (Streamlit vs. CSS a
  mano con `!important`).
- **Sin tipografía propia** -- confirmado real, sin resolver todavía: no hay una fuente
  de marca definida por Pablo/ECO Consultor para importar (queda pendiente, es una
  decisión de marca, no algo que se pueda inventar).
- **`.streamlit/config.toml` no existe** -- este hallazgo de Antigravity estaba
  DESACTUALIZADO: el archivo ya existe en el repo desde Hallazgo 46 (el clon que usó
  Antigravity debe haber sido de antes de ese merge). Aclarado con Pablo antes de actuar
  sobre el resto del reporte, para no perseguir un problema que ya no existía.

El resto de estilos en el bloque CSS (header de marca, botones del menú lateral,
etiquetas de sección) NO se tocan -- son componentes propios de la app que el sistema
de `theme` de Streamlit no cubre (sólo controla primaryColor/backgroundColor/
secondaryBackgroundColor/textColor/font, nada de clases custom), así que sí necesitan
CSS igual que antes; no había nada más redundante con `config.toml` que quitar.

**Pendiente, explícitamente no resuelto:** el documento de "Lineamientos de Identidad
Corporativa" que propuso Antigravity como mejora deja huecos a propósito (nombre de
fuente, familia de iconos) que son decisiones de marca de ECO Consultor, no técnicas --
no se completan por cuenta propia.

**Verificado:** `py_compile` limpio, las 32 pruebas existentes pasan, `streamlit run
app/app.py` arranca y responde 200; captura de pantalla con Playwright confirma que la
apariencia visual es idéntica a antes del cambio (logos, colores, layout), sólo cambia
el mecanismo interno.

---

### Hallazgo 48 — Se conecta por fin la pestaña "💰 Análisis Financiero" a `app.py`, y se encuentran 2 bugs reales probando en vivo con Playwright

Toda la capa de datos/lógica de Hallazgo 40-47 (`price_calculator.py`, `eg4_specs.py`,
`dimensionador_sistema_eolico.py`, `financial_engine_eolico.py`,
`sistema_eolico_completo.py`, `turbine_specs.py`/`solark_specs.py` unificados) llevaba
horas lista pero sin ninguna pantalla que la mostrara -- Pablo corrió la app localmente
con Docker y no encontró nada nuevo, lo cual expuso que nunca se había comunicado con
suficiente claridad que ese trabajo era sólo "backend". Se agrega la 5ta pestaña.

**Qué hace la pestaña:** reutiliza los clústers ya configurados en "⚙️ Equipos y
configuración" y recalcula el kWh/año (mismo cálculo que "📈 Resultados", Hallazgo
12/17, para no depender de que esa pestaña ya se haya visitado). Pide 3 parámetros
financieros arriba (consumo diario, horas de autonomía, tarifa eléctrica) + un radio
Standalone/Hybrid, y dentro de "Parámetros avanzados": % de instalación, vida útil,
tasa de descuento, y el modo de importación (`por_sku`/`por_proyecto`, parametrizado
desde Hallazgo 41, ahora por fin expuesto en la UI). Llama a
`analizar_sistema_eolico_completo()` y muestra CAPEX/Payback/ROI/Viabilidad, la
arquitectura elegida (inversor + BESS, con aviso si el inversor todavía no tiene specs
verificadas -- Hallazgo 43/44), el desglose de costos, y las recomendaciones.

**2 bugs reales encontrados probando en vivo con Playwright (subiendo el EPW real de
San José y recorriendo los 4 combos Standalone/Hybrid × por_sku/por_proyecto) --
ninguno se habría visto sólo revisando el código:**

1. **Texto roto por `$` sin escapar.** Un `st.caption()` con dos signos `$` en el mismo
   texto (`"...ahorro: $X/año vs. mantenimiento: $Y/año..."`) se renderizaba con partes
   en una tipografía itálica rara y el texto cortado -- Streamlit interpreta un PAR de
   `$...$` en cualquier texto markdown (`st.caption`, `st.write`, `st.warning`, etc.)
   como fórmula LaTeX, no como texto literal. Corregido escapando a `\$`. Ni
   `st.metric()` ni las tablas de pandas (`st.dataframe`) tienen este problema -- sólo
   texto libre con 2+ signos `$` en la misma llamada.
2. **BESS cobraba un fee de importación fantasma en modo Hybrid.** Al armar el
   desglose de costos por categoría (turbinas/inversor/BESS) para pasarlo a
   `calcular_precio_venta_proyecto()`, en modo Hybrid (sin BESS) se pasaba el costo del
   BESS como `$0` en vez de excluir la línea -- y la fórmula igual le sumaba el fee de
   importación completo a esa línea ($0 + $2,500 fee) × margen = **$3,250 cobrados por
   "importar nada"**. Se corrige excluyendo la línea de BESS por completo del cálculo
   cuando el sistema es Hybrid, en vez de pasarla como cero (`sistema_eolico_completo.py`).
   Verificado numéricamente antes y después del fix, y visualmente con Playwright en
   los 4 combos.

**Verificado:** `py_compile` limpio, las 32 pruebas existentes pasan, flujo completo
probado en vivo con Playwright (subir EPW real → configurar 3 turbinas → calcular
producción → pestaña financiera → los 4 combos Standalone/Hybrid × por_sku/por_proyecto,
con capturas de pantalla comparadas) -- los números cierran matemáticamente en los 4
casos (verificado a mano la diferencia exacta entre por_sku y por_proyecto).

**Pendiente, no resuelto en este hallazgo:** con los parámetros por default (tarifa
$0.15/kWh, arreglo pequeño en San José) el resultado da "NO VIABLE" -- el mantenimiento
anual (2% del CAPEX) supera el ahorro eléctrico. Es un resultado honesto del motor, no
un bug, pero valdría la pena en algún momento sensibilizar ese 2% con un dato real de
mantenimiento en vez del valor por default de `financial_engine_eolico.py`.

---

### Hallazgo 49 — Reunión con cliente al día siguiente: 6ta pestaña "Especificación Técnica" + PDF corporativo, identidad de marca real (libro de marca), y se confirma que "NO VIABLE" es economía real, no un bug del 2% de mantenimiento

Pablo compartió el libro de marca oficial de ECO Consultor (`libro_de_marca_de_Eco_consultor.pdf`)
y pidió, para una reunión con cliente al día siguiente: (1) una 6ta pestaña con la ficha
técnica completa de cada equipo del sistema, exportable a PDF con el tono corporativo de
ECO; (2) quitar todos los emojis y darle más protagonismo al logo de ECO (quitando el
co-branding con Flower Turbines, decisión de producto de Pablo, no del libro de marca);
(3) resolver una queja concreta sobre la pestaña financiera: no se veía en grande cuánto
dinero (no kWh) ahorra el sistema, y el texto de recomendaciones no aclaraba si "990
kWh/kW/año" era de una turbina o del arreglo completo.

**1. Identidad de marca real (del libro de marca, no aproximada).** Los 3 colores
corporativos son Pantone 309 C `#173D4A` (azul), Pantone 575 C `#66913E` (verde) y
Pantone 432 C `#414549` (gris) -- los que usaba la app hasta ahora (`#003C52`, `#4A7C2F`,
`#4A5568`) eran aproximaciones a ojo. Actualizados en `app.py` y `.streamlit/config.toml`.
La tipografía de marca es Gotham (de pago, no está en Google Fonts -- se usa Montserrat
como sustituto estándar) + Dosis para texto secundario/"descripción" (ésta sí es real y
gratuita) -- cargadas vía `@import` de Google Fonts en el CSS de `app.py`, porque el
`[theme]` de Streamlit en `config.toml` sólo acepta `sans serif`/`serif`/`monospace`, no
un nombre de fuente propio. Cierra el pendiente de Hallazgo 47 sobre tipografía.

**2. Emojis eliminados y logo de ECO con más protagonismo.** Se quitaron todos los emojis
de `app.py` (títulos de pestaña, mensajes, headers) vía reemplazo directo de los
caracteres Unicode, verificado después con un escaneo por rango Unicode que confirmó cero
emojis restantes (se conservó "✕", el símbolo de la "x" para borrar un clúster, por ser
tipográfico funcional, no decorativo). El logo de Flower Turbines se quita del header
(decisión de Pablo: "puede eliminar el logo de Flower turbines y dar mas protagonismo a
l logo de eco") y el logo de ECO pasa de 90px a 170px, solo, centrado.

**3. Pestaña financiera: 2 correcciones de presentación (no de cálculo).** El dato ya
existía (`fin['ahorro_anual_USD']`) pero estaba en una nota chica -- se agregó un
`st.metric()` grande y prominente para "Ahorro anual (electricidad no comprada)" junto a
la energía anual generada y el mantenimiento anual estimado, antes del bloque de
CAPEX/Payback/ROI. El texto de "Productividad kWh/kW/año" se reescribió explícito: **"no
es de una sola turbina, es el total del arreglo"** -- se verificó en el código
(`productividad = energia_anual_kwh / (potencia_pico_w / 1000)`) que el cálculo YA usaba
los valores totales del sistema; el problema real era que el texto no lo aclaraba y
generaba la duda razonable de Pablo.

**4. Se sensibilizó el % de mantenimiento (Hallazgo 48) y se investigó a fondo el "NO
VIABLE".** `FinancialEngineEolico` ya soportaba `costo_mantenimiento_pct_anual` como
parámetro, pero `analizar_sistema_eolico_completo()` nunca lo exponía -- quedaba
hardcodeado en 2%. Se agrega como parámetro de punta a punta (motor → función → slider en
"Parámetros avanzados", 0-5%). Con eso ya sensibilizable, se probó bajarlo hasta 0% con
un arreglo real (5× three_m_tulip, costo de fábrica real $12,905.75/turbina) en San José:
**el payback seguía siendo ≈171 años.** Conclusión honesta, no un bug: para arreglos
chicos, el costo de fábrica de las turbinas domina tanto el CAPEX que ni eliminando el
mantenimiento el sistema compite por ahorro puro de factura eléctrica -- se agregó un
`st.info()` en la pestaña financiera que se lo dice así de claro a Pablo, con la
sugerencia de presentar el valor como respaldo/resiliencia energética en vez de ahorro
puro (ese valor todavía no se cuantifica en dólares en esta app).

**5. Pestaña "Especificación Técnica" (nueva, 6ta pestaña).** Reutiliza los clústers de
"Equipos y configuración" y el consumo/horas de autonomía ya cargados en "Análisis
Financiero" (vía `st.session_state`, claves `fin_consumo_diario`/`fin_horas_autonomia`,
con default de 20 kWh/día y 12h si esa pestaña no se visitó todavía). Llama a
`dimensionar_sistema_eolico_completo()` y muestra: datos generales (sitio, potencia pico,
energía anual, elevación, arquitectura del bus DC a 48V), una ficha por cada modelo de
turbina distinto (imagen + tabla completa de specs, vía `SPECS_TURBINAS`), la ficha del
inversor (tabla completa vía `get_solark_df().query(...)`) y la de cada módulo BESS (vía
`get_eg4_df().query(...)`).

**3 bugs reales encontrados probando en vivo con Playwright (no se habrían visto solo
revisando el código):**

1. **`st.image(..., use_container_width=True)` no existe en Streamlit 1.35.0** (la
   versión fijada en `requirements.txt`) -- ese parámetro se agregó en una versión más
   nueva de Streamlit. Tiraba `TypeError: ImageMixin.image() got an unexpected keyword
   argument 'use_container_width'` y rompía toda la pestaña. Corregido a
   `use_column_width=True`, el mismo patrón que ya usaba el resto de `app.py`.
2. **Datos "nan" mostrados crudos al cliente.** Algunas filas de `solark_specs.py` (ej.
   los inversores comerciales 30K/60K, sin `Garantia_Anos` todavía) y de `eg4_specs.py`
   (el EG4 WallMount Indoor, sin `Corriente_BMS_Max_A`/`Ciclos_80pct_DoD`/dimensiones/peso
   todavía) tienen campos sin dato -- pandas los deja en `NaN`, y la tabla se los mostraba
   tal cual ("nan A", "nan kg") en un reporte que se supone profesional. Se agregaron 3
   helpers (`_ndv`, `_ndv_rango`, `_ndv_dims`) que muestran "No verificado todavía" en su
   lugar, mismo criterio que ya se usaba para `costo_usd=None` en `turbine_specs.py`.
3. **El PDF desbordaba el margen con un nombre de sitio largo.** El nombre de un EPW
   subido por el usuario (ej. `CRI_AL_San.Jose-Santamaria.Intl.AP.787620_TMYx.2007-
   2021.epw`) es una cadena sin espacios -- en la tabla del PDF (`reportlab`) el texto
   plano no envuelve dentro de la columna y se salía de la página. Corregido envolviendo
   cada celda en un `Paragraph` con `wordWrap="CJK"` (que sí rompe una palabra larga sin
   espacios), en vez de texto plano.

**6. Exportación a PDF corporativo (`engine/pdf_reporte.py`, nuevo).** Usa `reportlab`
(agregado a `requirements.txt`) -- puro Python, sin binarios del sistema, mismo criterio
que el resto de las dependencias. El PDF usa los 3 colores exactos de marca, el logo de
ECO al inicio, y el mismo contenido que la pestaña (datos generales + fichas de turbinas,
inversor y BESS). **Limitación conocida, no resuelta:** usa las tipografías estándar de
reportlab (Helvetica), no Montserrat/Dosis -- para eso se necesitaría el archivo `.ttf`
real de esas fuentes (Montserrat es gratis y se puede bajar de Google Fonts; Dosis
también), que hoy no está en el repositorio. Los colores sí son los de marca exactos. Se
agrega un botón "Descargar ficha técnica en PDF" (`st.download_button`) al final de la
pestaña.

**Verificado:** `py_compile` limpio en los 3 archivos tocados, las 32 pruebas existentes
siguen pasando, flujo completo probado en vivo con Playwright (subir el EPW real de San
José → configurar clústers → calcular → recorrer las 6 pestañas → descargar el PDF real
generado por el botón y confirmarlo visualmente página por página) -- sin tracebacks ni
"nan" visibles en ningún punto del flujo.

**Pendiente, no resuelto en este hallazgo:**
- Fuente real de marca (Montserrat/Dosis) en el PDF -- hoy usa Helvetica, sólo los
  colores son de marca.
- Cuantificar en dólares el valor de respaldo/resiliencia energética (mencionado en el
  punto 4) -- hoy es una recomendación en texto, no un número.
- Si la pestaña "Análisis Financiero" nunca se visitó en la sesión, "Especificación
  Técnica" arma el inversor/BESS con un consumo/autonomía por default (20 kWh/día, 12h)
  sin avisarle al usuario que son valores por default y no los que él configuró.

---

### Hallazgo 50 — El fee de importación plano de $2,500/línea sobreestimaba el flete real hasta ~300x: reemplazado por un modelo de flete consolidado por peso (unidad/pallet/contenedor)

Pablo, revisando los resultados financieros para su reunión, señaló que el CAPEX no
podía estar bien: "un contenedor de 40 pies de EE.UU. a Costa Rica no va a costar más
de $10,000". Dio 3 tarifas de mercado (no cotización de forwarder, pero sí un dato real
de referencia, corregido en la conversación de $35,000→$5,000→**$3,500** para el
pallet tras detectar él mismo la inconsistencia con su propio ejemplo numérico):

- **Unidad** (envío suelto, carga chica): $2,000
- **Pallet**: $3,500
- **Contenedor de 40'**: $10,000

**El problema real que esto exponía:** desde Hallazgo 40/41, `price_calculator.py`
tenía un `IMPORT_COST_USD=$2,500` FIJO aplicado por cada LÍNEA del pedido (modo
"por_sku": cada turbina individual, el inversor, y cada módulo de BESS pagaban su
propio fee de $2,500) o por todo el proyecto (modo "por_proyecto", 1 solo fee). Ninguno
de los dos modos tenía relación con el flete real: una Small Tulip de 20kg pagaba el
mismo fee que un contenedor entero. Verificado con las 4 turbinas de costo real
verificado: el fee plano sobreestimaba el flete real entre **16x (3-Meter Tulip) y
~300x (Small Tulip)**.

**Solución implementada:** nuevo modelo de flete CONSOLIDADO por peso real del
embarque, en `engine/price_calculator.py`:
- `calcular_flete_consolidado_usd(peso_total_kg)`: dado el peso total de un embarque
  (turbinas + inversor + BESS juntos), elige el modo más barato entre 1 unidad suelta
  (≤200kg, techo razonable), N pallets (≤1,000kg c/u) o N contenedores (≤26,000kg
  c/u) -- los 3 límites de peso son supuestos de ingeniería (peso como factor
  limitante, no volumen; válido si la fábrica embarca las turbinas
  desarmadas/en secciones, típico para mástiles/torres, pero NO verificado con una
  ficha de empaque real de Flower Turbines).
- `calcular_precio_venta_proyecto_por_peso(costos, pesos)`: reemplaza
  `calcular_precio_venta_proyecto()` en los 2 lugares donde de verdad se usaba
  (`dimensionador_sistema_eolico.py` a nivel de unidad física, y
  `sistema_eolico_completo.py` a nivel de categoría turbinas/inversor/BESS) --
  calcula el flete UNA vez sobre el peso total y lo reparte proporcional al costo
  base de cada línea, igual que ya hacía el viejo modo "por_proyecto" pero con el
  costo real en vez del fee inventado.
- Se agregó `peso_kg`/`peso_total_kg` a `seleccionar_inversor_solark()`,
  `seleccionar_bess_48v()` y `calcular_costo_arreglo_turbinas()` (de
  `solark_specs.py`/`eg4_specs.py`/`turbine_specs.py`, ya existían esos datos, sólo no
  se exponían) -- un peso en `None` (ej. EG4 WallMount Indoor sin ficha completa,
  Hallazgo 49) se trata como 0kg, subestima un poco el flete en vez de inventar un dato.
- **Se elimina el parámetro `modo_importacion`** ("por_sku"/"por_proyecto") de
  `dimensionar_sistema_eolico_completo()` y `analizar_sistema_eolico_completo()`, y
  el radio button correspondiente en la pestaña "Análisis Financiero" -- ya no hay
  ambigüedad que sensibilizar, el modelo de peso reemplaza a los dos modos viejos.
  `IMPORT_COST_USD`/`MODO_IMPORTACION_DEFAULT`/`calcular_precio_venta_proyecto()`
  quedan en el archivo sólo por compatibilidad con las funciones viejas de PR #18
  (`calcular_precio_final`, `calcular_bom_turbinas`, etc.) que ya no forman parte del
  cálculo real de la app -- sus pruebas existentes siguen intactas.
- La app ahora le muestra a Pablo, en el desglose de costos de "Análisis Financiero",
  qué modo de flete se usó y cuánto costó ("Flete de importación incluido arriba: modo
  **pallet** (1 -- $3,500 total)...").

**Resultado verificado** (mismo caso default, 3× Medium Tulip en San José): el CAPEX
total baja de **$72,261 a $65,241** (−9.7%) con el mismo arreglo -- sigue "NO VIABLE"
(el costo de fábrica de las turbinas sigue dominando, ver Hallazgo 49), pero es un
número más honesto. Probado también con un arreglo grande (20× 3-Meter Tulip, cae en
modo "contenedor" con múltiples unidades) y en modo Hybrid (sin BESS) -- ningún caso
rompe ni da un flete negativo/fantasma.

**Verificado:** `py_compile` limpio en los 3 archivos de motor + `app.py`, las 32
pruebas existentes siguen pasando sin modificarlas, y pruebas manuales de los límites
de peso (`calcular_flete_consolidado_usd` en 50/200/500/1000/1500/5000/26000/30000/
60000 kg) confirman que siempre elige el modo más barato, incluyendo el caso donde
un pallet parcial sale más caro que consolidar en un contenedor. Flujo completo
probado en vivo con Playwright (EPW real → clústers → calcular → Financiero →
Especificación Técnica → descarga de PDF) sin tracebacks.

**Pendiente, no resuelto en este hallazgo:**
- Las 3 tarifas de flete y los 2 límites de peso (pallet/contenedor) son datos de
  mercado dados por Pablo, NO una cotización de un forwarder real -- confirmar antes
  de cotizar en firme a un cliente.
- Los límites de peso asumen que las turbinas se embarcan desarmadas/en secciones
  (razonable para mástiles de varios metros, pero no confirmado con una ficha de
  empaque real de Flower Turbines) -- si el volumen real es el factor limitante en
  vez del peso, estos números podrían quedar cortos.
- El "modo unidad" (≤200kg) es un supuesto propio, no un techo real de ningún
  forwarder consultado.

**Seguimiento del mismo día:** Pablo pidió una lista de precios en PDF para llevar a
la reunión sin depender de la app en vivo. Se agrega `generar_pdf_lista_precios()` en
`engine/pdf_reporte.py`: una tabla por modelo de turbina (costo de fábrica + flete
estimado + margen, misma fórmula y mismas tarifas de flete que ya usa el resto de la
app desde este Hallazgo), separando los 4 modelos con costo verificado de los 5 con
costo NO verificado (con advertencia explícita de no repetirlos como precio firme). El
flete por modelo asume pedir lo suficiente para llenar 1 pallet o 1 contenedor
completo (lo que salga más barato por unidad) -- referencia de orden de magnitud, no
el flete de un pedido puntual real (para eso, `calcular_flete_consolidado_usd()` con
el peso real del proyecto, que es lo que usa el resto de la app). PDF entregado
directo a Pablo, generado y verificado visualmente (`pymupdf`) antes de enviarlo.

---

### Hallazgo 51 — Se sube el límite de altura de buje de 15m a 150m para poder evaluar instalación en techo de edificios altos, y se descubre que las turbinas "Eco-Roof" no son seleccionables en el simulador

Pablo preguntó si se podía ampliar el perfil de viento a 60m, para evaluar poner
turbinas en el techo de un edificio de 15 pisos.

**Respuesta técnica, antes de tocar código:** sí, sin necesitar ningún dato nuevo del
EPW. El EPW sólo trae viento medido a 10m -- la extrapolación a cualquier otra altura
(3m o 60m, da lo mismo) ya la hace `wind_at_height()` (ley logarítmica, Hallazgo 20),
que no tiene ningún límite matemático en la altura destino; el techo de 15m era sólo
un límite puesto a mano en los widgets de Streamlit, no una limitación de la fórmula
ni del dato. Verificado con el cross-check independiente que la app ya tenía (ley de
potencia de EnergyPlus, `wind_at_height_potencia()`): entre 10m y 100m los dos métodos
se mantienen consistentes entre sí (6-10% de diferencia en todo el rango, sin
dispararse) -- no hay señal de que la extrapolación se vuelva absurda a 60m.

**Cambio real:** se sube `max_value` de 15.0 a 150.0 en 2 widgets de `app.py` -- el
slider "Altura de buje a explorar" (Contexto climático, sólo visual/exploratorio) y el
`number_input` "Buje (m)" de cada clúster (Equipos y configuración, el que sí alimenta
el cálculo real de energía). Se agrega ayuda explícita en ambos: para una instalación
en techo, la altura de buje = altura del edificio + altura del mástil sobre el techo
(NO la cantidad de pisos) -- un edificio de 15 pisos ronda 45-55m según la altura de
entrepiso.

**Salvedad honesta, no resuelta:** la ley logarítmica con un z0 regional (el mismo que
ya usa la app para el sitio destino) da la velocidad REGIONAL esperada a esa altura --
es la extrapolación estándar de un primer análisis de recurso eólico, pero NO modela el
efecto aerodinámico LOCAL de estar encima de un edificio puntual (aceleración del flujo
sobre el borde del techo, turbulencia por parapetos/equipos de HVAC, estela de
edificios vecinos más altos) -- esos efectos están bien documentados en la literatura
de turbinas integradas a edificios (BIWT) y pueden tanto ayudar como perjudicar el
resultado real frente a esta extrapolación "limpia". Modelarlos requeriría datos
específicos del edificio (CFD, túnel de viento, o factores de corrección publicados)
que este proyecto no tiene todavía.

**Hallazgo colateral, sin resolver:** las turbinas "Eco-Roof Energy Hub" (3 modelos en
`turbine_specs.py`: `ecoroof_flat_3`, `ecoroof_flat_5`, `ecoroof_slanted`) -- el
producto que Flower Turbines vende específicamente para techo, sin cimentación -- NO
están en `CURVE_COEFFICIENTS` (`flower_turbines_curves.py`), así que el selector
"Modelo" de "Equipos y configuración" no las puede elegir: tienen ficha técnica y costo
completos, pero ningún cálculo de energía las puede simular. Mismo problema para
`survival_unit`. Workaround inmediato usado con Pablo: para el caso de techo, usar un
modelo Tulip existente (ej. `small_tulip`, que es literalmente la turbina individual
que arma el Eco-Roof Flat-3/5 en plataforma) con la altura de buje = altura del
edificio + mástil -- la curva de potencia es por MODELO de turbina, no por tipo de
montaje, así que es válido físicamente aunque no aparezca como "Eco-Roof" en la
interfaz.

**Verificado:** `py_compile` limpio, las 32 pruebas existentes siguen pasando, y
prueba en vivo con Playwright (EPW real de San José, slider a 60m, clúster con buje
55m, calcular producción) -- sin errores, y el punto marcado en el gráfico (4.64 m/s a
60m) coincide exacto con el cálculo hecho a mano en Python antes de tocar la UI.

**Pendiente, no resuelto en este hallazgo:**
- Agregar coeficientes de curva de potencia para `ecoroof_flat_3`, `ecoroof_flat_5`,
  `ecoroof_slanted` y `survival_unit` a `CURVE_COEFFICIENTS` para que sean
  seleccionables de verdad en "Equipos y configuración" -- hoy existen en
  `turbine_specs.py` pero son inertes en el simulador.
- Cuantificar (o al menos documentar con una fuente publicada) el efecto aerodinámico
  local de un techo de edificio (aceleración/turbulencia) en vez de usar sólo la
  extrapolación regional limpia.

---

### Hallazgo 52 — Se cierra (con evidencia, no por decisión sin probar) el intento de resucitar el ajuste espacial vía GWA-50m/ERA5-Land/Köppen-Gower/TPI; se corrige el último valor hardcodeado del cross-check de altura

Pablo trajo dos pistas nuevas para el problema de fondo de Hallazgo 35/36 (viento
confiable por punto exacto en Costa Rica): un ráster real de GWA a **50m** (en vez de
10m) para Heredia, y un documento técnico ("Alternativas Simulador Viento Global")
proponiendo resucitar el mecanismo de razón de escala con 4 mejoras: selección de
donante por Distancia de Gower + Köppen-Geiger, ERA5-Land (9km) vía Open-Meteo en vez
de GWA, corrección orográfica TPI/EN 1991-1-4, y rugosidad z0 dinámica vía ESA
WorldCover. Se investigaron las dos pistas a fondo, con pruebas reales, no sólo teoría.

**GWA a 50m para Heredia (lat=9.9996, lon=-84.1231):** mejora medible pero no resuelve
el problema. Contra los mismos 3 chequeos que hundieron la versión de 10m
(Hallazgo 35): el ruido por coordenada dentro del mismo aeropuerto Santamaría bajó de
+126% a +30%, y el ruido espacial del barrido 25x25 del Valle Central bajó de 78% a
36% de la media -- una mejora real, pero el orden relativo Santamaría/La Sabana sigue
sin resolverse de forma consistente (depende de qué coordenada "oficial" de Santamaría
se use). Aparte: el EPW "EstadioHerediahour.epw" que Pablo subió resultó ser sintético
(encabezado `fuente=MN8, WMO=999`, no una estación real) y su propia media a 10m
(5.31 m/s) diverge +32% de la estación real de Santamaría a sólo 11km -- el mismo
síntoma de "Valle Central sin dato confiable" pero en una tercera fuente distinta.

**Evaluación de "ECO-Wind V2" (el documento con Gower/Köppen/ERA5-Land/TPI/WorldCover):
ninguna de las 4 piezas sobrevive el contraste con datos reales.**
1. *Köppen + Gower para elegir donante* -- irrelevante por geometría, no por código: la
   estación no-costarricense más cercana a Heredia está a 147-168 km (35x más lejos
   que las opciones locales) sobre las 5,276 estaciones del catálogo completo. Ningún
   filtro climático cambia un donante que ya está a 150km de cualquier alternativa
   (confirma y cierra el pendiente de Hallazgo 27, que sólo lo había probado con 4
   sitios).
2. *ERA5-Land vía Open-Meteo* -- no se pudo probar: `archive-api.open-meteo.com` y
   `api.open-meteo.com` están bloqueados en este sandbox (confirmado por 3 vías
   independientes). Se encontró que esto ya se había intentado antes (notebook
   `sensibilizar_punto_exacto.ipynb`, Parte 5, para los 4 sitios conocidos) con el
   mismo error, sin llegar nunca a documentarse como Hallazgo -- queda formalmente
   pendiente, no descartado ni confirmado.
3. *Corrección orográfica TPI/EN 1991-1-4* -- no aplica al problema real. El propio
   Eurocódigo exige pendiente >3° para activarse; la pendiente real entre Santamaría/
   La Sabana/Heredia da 1.0-2.1° con las elevaciones reales conocidas. El ruido de
   ±126% dentro del mismo aeropuerto (Hallazgo 35) no puede ser orográfico -- es la
   misma pista plana. (Sí es válida en Guanacaste real -- Tilarán, Papagayo Jet -- pero
   no en el Valle Central).
4. *Rugosidad z0 vía ESA WorldCover* -- el acceso SÍ funciona (bucket público AWS S3,
   sin fricción), pero reproduce el mismo patrón de ruido de GWA en otra variable: las
   3 coordenadas de Santamaría dan z0 entre 0.03 y 0.55-1.0 (18-30x de salto), y en
   Heredia el píxel exacto cae en "cuerpo de agua" (z0≈0.0005) pese a que el 90% de la
   ventana de 210x210m alrededor es zona urbana.
5. Extra probado de paso: subir GWA de 10m a 50m (sin las otras 3 piezas) empeoró el
   error en los 7 de 7 sitios conocidos -- consistente con que el problema no es de
   qué altura del ráster se usa.

**Conclusión, sin ambigüedad:** el problema no es la fuente de datos (GWA, WorldCover,
o -- si algún día se puede probar -- ERA5-Land) sino que cualquier dato remoto de
resolución moderada leído en un punto exacto tiene ruido de píxel/registro mayor que
la variación física real del viento en el Valle Central urbano-mixto. La única salida
real es medición local (anemómetro en sitio + correlación contra Santamaría,
"measure-correlate-predict"), no una fuente o corrección matemática mejor. **No se
retoma ninguna de las 4 líneas de V2** -- se cierra con este hallazgo documentado en
vez de dejarlo abierto para que alguien lo reintente sin esta evidencia.

**Decisión de producto de Pablo, aplicada en código:** "si coloco un EPW del sitio,
respetamos lo que dice aunque sea sintético -- la altura de las turbinas y el tipo de
terreno los selecciona el usuario, no quiero nada hardcodeado." Confirmado que la app
ya cumple esto en casi todo (ningún EPW se trata distinto por su fuente/WMO; altura de
buje y z0 ya eran inputs del usuario desde antes) -- **con una excepción real
encontrada y corregida:** el cross-check de ley de potencia en "Resultados" (expander
"Hallazgo 20") tenía `terreno="suburban"` fijo en el código, sin importar qué z0 
eligiera el usuario arriba. Se agrega `terreno_mas_cercano_por_z0()` en
`engine/simulador_pista_a.py`, que mapea el z0 numérico elegido a la clase de
`TERRENOS_ENERGYPLUS` más cercana **en escala logarítmica** (no lineal -- con distancia
lineal, z0=0.3 queda exactamente empatado entre "country" y "suburban" y el desempate
de `min()` caía silenciosamente en la clase equivocada). El texto de la UI ahora
también refleja el z0 real usado, no un valor fijo.

**Verificado:** `py_compile` limpio, las 32 pruebas existentes siguen pasando, mapeo
verificado para los 4 z0 del selector (0.03→water, 0.1→country, 0.3→suburban,
1.0→city -- los 4 dan el resultado físicamente correcto), y prueba en vivo con
Playwright cambiando z0 a "urbano denso" y confirmando que el cross-check usa "city"
y el z0=1.0 correcto en el texto mostrado, sin errores.

---

### Hallazgo 53 — "Dejemos de adivinar": el módulo financiero pasa de estimar el CAPEX con costo de fábrica + margen + flete supuestos a pedir el precio de venta real, y se agrega un switch para apagarlo entero

Pablo pidió reestructurar el análisis financiero: "vamos a dejar de adivinar" -- un
switch para encender/apagar todo el módulo financiero, y adentro, campos para meter
directo el costo de los equipos, el precio de venta al cliente y la tarifa eléctrica,
para que Payback/ROI/NPV/Viabilidad salgan de datos reales en vez de la cadena de
supuestos (costo de fábrica de `turbine_specs.py` + flete por peso de Hallazgo 50 +
margen de importación fijo del 35%) que la app venía adivinando desde Hallazgo 40.

**Qué SÍ se sigue calculando automático, y por qué:** la arquitectura técnica
(selección de inversor Sol-Ark y banco EG4 vía
`dimensionador_sistema_eolico_completo()`) sigue siendo automática -- es selección de
equipo compatible según la electricidad real del arreglo (regla de voltaje/corriente
confirmada con ambos fabricantes, Hallazgo 40/41), no un precio inventado. Lo único
que se adivinaba, y ahora se pide directo al usuario, es el PRECIO del proyecto.

**Cambios en el motor (`engine/financial_engine_eolico.py`):**
- Se extrae `_calcular_viabilidad(capex, ahorro_anual_usd, mantenimiento_anual_usd,
  vida_util_anos, tasa_descuento_pct)`: el núcleo de Payback/ROI/NPV que antes vivía
  sólo dentro de `_calcular_punto_financiero()` (la ruta basada en % de instalación/
  mantenimiento), ahora es una función compartida. `_calcular_punto_financiero()` se
  reescribió para llamarla en vez de duplicar el cálculo -- su comportamiento externo
  (y las 32 pruebas que lo verifican con inputs basados en %) queda idéntico, no se
  tocó ninguna de las dos ramas de retorno temprano (capex/n_turbinas inválidos, u
  opex neto ≤0).
- Se agrega `FinancialEngineEolico.calcular_punto_capex_directo(capex_usd,
  energia_anual_kWh, mantenimiento_anual_usd, potencia_pico_W=0, n_turbinas=0,
  sistema_tipo="Standalone")`: calcula el ahorro anual (`energia_anual_kWh × tarifa`)
  y llama a `_calcular_viabilidad()` con el CAPEX y el mantenimiento que el usuario
  ingresó directo en dólares -- sin pasar por costo de fábrica, flete ni margen.
  Devuelve el mismo diccionario (mismas llaves: `capex`, `ahorro_anual_USD`,
  `payback_years`, `roi_percentage`, `npv_usd`, etc.) que el método viejo
  `calcular_punto_unico()`, para que la UI no tenga que distinguir entre los dos.

**Cambios en la UI (`app/app.py`, pestaña "Análisis Financiero"):**
- Nuevo `st.toggle("Activar módulo financiero", value=True)`: apagado, la pestaña
  muestra sólo un mensaje informativo y no calcula nada -- para cuando a Pablo sólo le
  interesa el dimensionamiento técnico (pestaña "Especificación Técnica") todavía.
- La pestaña ya NO llama a `analizar_sistema_eolico_completo()` (la función que
  encadenaba costo de fábrica → flete consolidado → margen → `calcular_punto_unico()`)
  -- ahora llama directo a `dimensionar_sistema_eolico_completo()` sólo para mostrar
  "Arquitectura del sistema" (inversor + BESS), y a
  `calcular_punto_capex_directo()` para la viabilidad.
- 3 campos nuevos, todos en dólares reales (no %): "Costo de los equipos" (turbinas +
  inversor + BESS -- sólo informativo, para ver el margen), "Precio de venta al
  cliente" (este SÍ es el CAPEX real que entra al cálculo de Payback/ROI/NPV), y
  "Mantenimiento anual (USD/año)" -- reemplaza el slider de "% del CAPEX" que
  admitía en su propio texto de ayuda no venir de un dato real verificado.
  Se muestra el margen (precio de venta − costo de equipos) como referencia.
- Se eliminan de "Parámetros avanzados" los sliders "Costo de instalación (% de
  equipos)" y "Mantenimiento anual (% del CAPEX)" -- ya no aplican, el precio de venta
  ingresado por el usuario ya es el precio llave en mano. Se mantienen "Vida útil" y
  "Tasa de descuento para NPV": son supuestos financieros estándar (no un costo
  adivinado) y siguen siendo ajustables.
- Se elimina la tabla "Desglose de costos" (basada en `costos_con_margen_importacion`
  y el `flete` de Hallazgo 50) y el expander de "Recomendaciones" (generaba texto a
  partir del mismo pipeline de % que se está reemplazando) -- ver Pendiente abajo.

**Nada del backend de costeo por %/flete/margen se borró** -- `sistema_eolico_completo.py`,
`price_calculator.py` y `_calcular_punto_financiero()`/`calcular_punto_unico()` siguen
intactos y con sus pruebas pasando; sólo dejaron de ser la ruta que usa esta pestaña.

**Verificado:** `py_compile` limpio en los archivos modificados, las 32 pruebas
existentes siguen pasando sin tocarlas, cálculo manual de un caso (CAPEX=$300,
mantenimiento=$10/año, ahorro≈$26.7/año con el arreglo default) confirma Payback=11.2
años, ROI=257%, NPV=$19 a 40 años/8% -- coincide con la fórmula. Probado en vivo con
Playwright: switch apagado oculta todo el módulo sin errores; con datos reales (costo
equipos $10,000, precio de venta $15,000, mantenimiento $300/año) muestra margen 50%
($5,000) y "NO VIABLE" con N/A correctamente cuando el mantenimiento supera el ahorro
anual; modo Hybrid muestra "BESS: no aplica" igual que antes; la pestaña
"Especificación Técnica" (que ya usaba `dimensionar_sistema_eolico_completo()` por su
cuenta desde Hallazgo 49) sigue funcionando sin cambios.

**Pendiente, no resuelto en este hallazgo:**
- Se quitó el texto de "Recomendaciones" (payback/ROI/NPV interpretados en prosa) al
  quitar `analizar_sistema_eolico_completo()` -- si Pablo lo quiere de vuelta, hay que
  adaptar `_generar_recomendaciones()` (hoy privada en `sistema_eolico_completo.py`)
  para que reciba el diccionario de `calcular_punto_capex_directo()`.
- No hay validación cruzada entre "costo de los equipos" y "precio de venta" más allá
  de mostrar el margen -- si el usuario mete un precio de venta MENOR al costo de
  equipos (margen negativo), la app no avisa, sólo muestra un margen en rojo... en
  realidad ni siquiera eso, sólo el número negativo sin resaltar.
- El campo "Costo de los equipos" es puramente informativo hoy (no entra en ningún
  cálculo de viabilidad) -- si más adelante Pablo quiere ver el margen como % de
  utilidad sobre el precio de venta (en vez de sobre el costo), hay que agregar ese
  segundo cálculo.

---

### Hallazgo 54 — Tarifas eléctricas reales de Costa Rica (CNFL/ICE) con horarios Punta/Valle/Nocturno, cruzadas contra la producción hora por hora de la turbina, en vez de una tarifa plana

Pablo pasó 4 tablas de tarifas reales de CNFL/ICE (horarias residenciales, escalonadas,
media tensión + excedentes de generación distribuida, y comerciales) y pidió
integrarlas en vez de seguir usando una tarifa plana ($/kWh) para calcular el ahorro
-- y, específicamente, "planifica los horarios de las tarifas con los potenciales de
producción de los equipos según el análisis de potencia horaria": cruzar A QUÉ HORA
del día genera la turbina contra los periodos Punta/Valle/Nocturno reales, no sólo
sumar kWh/año y multiplicar por un promedio.

**Investigación previa (Hallazgo 54, antes de programar nada):** los pliegos primarios
de ARESEP/ICE/CNFL están bloqueados por la política de red de este entorno (403/
EGRESS_BLOCKED en aresep.go.cr, grupoice.com, cnfl.go.cr) -- se investigó vía búsqueda
web (que sí funciona) para (1) confirmar el horario exacto de cada periodo y (2)
verificar los valores CRC/kWh que dio Pablo contra la fuente oficial más reciente.
Resultado, con fuentes citadas en el código (`engine/tarifas_electricas_cr.py`):

- **Horario, idéntico para T-RH (ICE), T-REH (CNFL) y T-MT (ICE, sólo la parte de
  energía)** -- confirmado por múltiples búsquedas independientes que coinciden entre
  sí (confianza alta para el rango horario, no se pudo abrir el PDF primario letra por
  letra):
  - Punta: 10:00-12:30 y 17:30-20:00, **sólo Lunes a Viernes**.
  - Valle: 06:00-10:00 y 12:30-17:30 en L-V; **fin de semana completo (sábado y
    domingo) las ventanas de Punta se reclasifican como Valle** -- queda un solo
    bloque 06:00-20:00 los sábados/domingos.
  - Nocturno: 20:00-06:00 (cruza medianoche), todos los días por igual, sin excepción
    de fin de semana.
  - No se encontró variación estacional (verano/invierno, seco/lluvioso) en ninguna
    fuente. Feriados: ninguna fuente los menciona explícitamente -- se asume que se
    tratan como fin de semana (sin Punta), **sin confirmar**.
- **Valores CRC/kWh que dio Pablo:** los de CNFL (T-REH 0-500/>500, T-RE escalonada
  completa, T-CO ≤3000 kWh) coinciden EXACTOS con el pliego "Tarifas Vigentes" de CNFL
  vigente desde el 1/ene/2026. Los de ICE T-RE (bloques 0-140 y 141-195) son
  consistentes -- casi al colón -- con aplicar la rebaja de -14.92% que ARESEP fijó
  para la tarifa residencial de ICE en 2026 sobre la base 2024/2025. El resto (ICE
  T-RH horaria, ICE T-MT, ICE T-CO, T-A, bloques altos de T-RE de ICE, CNFL T-CO
  >3000 kWh completo, y el valor nocturno de T-TCVE) no se pudo confirmar cifra a
  cifra por el bloqueo de red -- no hay evidencia de que estén mal, sólo no se
  verificaron. Dato importante: **2026 trajo una rebaja tarifaria general en Costa
  Rica** (ICE residencial -14.92%, CNFL residencial -14.55%) -- cualquier tarifa 2025
  que se tuviera guardada está entre 5% y 17% por encima de la vigente.

**Qué se conectó al cálculo real (motor nuevo: `engine/tarifas_electricas_cr.py`):**
- Las 4 tablas de Pablo se guardaron tal cual (`TARIFAS_HORARIAS_CR`,
  `TARIFAS_ESCALONADAS_CR`, `TARIFAS_MT_GD_CR`, `TARIFAS_COMERCIALES_CR`) con
  `get_..._df()` para cada una, siguiendo el mismo patrón que `solark_specs.py`/
  `eg4_specs.py`.
- `clasificar_periodo(timestamp, proveedor, tarifa)`: dado un timestamp y el horario
  ARESEP de `PERIODOS_HORARIOS_CR`, devuelve "Punta"/"Valle"/"Nocturno" -- maneja
  rangos que cruzan medianoche (Nocturno) y reglas separadas por día de semana/fin de
  semana.
- `calcular_ahorro_tarifa_horaria_usd(serie_horaria_kwh, proveedor, tarifa,
  tipo_cambio_crc_por_usd)`: clasifica CADA HORA de la serie horaria real de
  producción del proyecto (no un promedio), la valora al precio CRC/kWh del periodo
  correspondiente, suma, y convierte a USD -- devuelve el ahorro total y el desglose
  kWh/₡/USD por periodo (Punta/Valle/Nocturno), para que se vea de dónde sale el
  número, no sólo el total.
- `FinancialEngineEolico.calcular_ahorro_y_viabilidad(capex_usd, ahorro_anual_usd,
  mantenimiento_anual_usd, ...)`: nuevo método público, extraído de
  `calcular_punto_capex_directo()` (que ahora es un wrapper de 3 líneas sobre este) --
  recibe el ahorro anual YA resuelto en dólares, sin importar si vino de tarifa plana
  o de la tarifa horaria real. `_calcular_punto_financiero()` y
  `calcular_punto_unico()` (Hallazgo 40-53, basados en % de instalación/mantenimiento)
  quedan intactos, ninguna prueba existente se tocó.
- `app.py`, pestaña "Análisis Financiero": nueva sección "Tarifa eléctrica" con un
  radio "Tarifa plana (USD/kWh)" vs "Tarifa horaria real de Costa Rica (ARESEP)". En
  modo horario: selector de Proveedor (CNFL/ICE) x Tarifa (T-REH 0-500/>500, T-RH,
  T-MT), campo de tipo de cambio ₡/USD editable, tabla de desglose por periodo, y
  caption con la tarifa efectiva ponderada por la producción real (para comparar
  contra el modo plano). La serie horaria del proyecto se arma sumando
  `serie_horaria_W_por_turbina × N / 1000` de cada clúster (ya la devuelve `simular()`
  por turbina, sólo faltaba escalarla y sumarla entre clústers).

**Qué NO se conectó todavía, y por qué (honesto, no "adivinar" un mecanismo dudoso):**
- **T-RE (escalonada, CNFL/ICE):** se guardó como dato de referencia, no se calculó
  ningún ahorro con ella. No se pudo confirmar con la fuente oficial si el cargo
  fijo/tarifa de cada bloque se cobra de forma progresiva (como un bracket de
  impuesto) o como categoría (todo el consumo del mes a la tarifa del bloque más alto
  alcanzado) -- son mecánicas de facturación distintas que dan resultados distintos, y
  calcular un "ahorro" adivinando cuál es exactamente el error que este hallazgo
  existe para evitar.
- **T-TCVE (excedentes de generación distribuida) y T-A:** guardadas como referencia.
  T-TCVE es lo que ICE paga por el excedente que el sistema INYECTA a la red cuando
  genera más de lo que el sitio consume en ese instante -- vale mucho menos (~19-27
  ₡/kWh) que la energía autoconsumida (~55-166 ₡/kWh según periodo). Calcularla de
  verdad requiere un perfil de CONSUMO horario del sitio (hoy la app sólo pide un
  kWh/día promedio, no una curva de carga horaria) para saber en qué horas hay
  excedente real -- trabajo futuro explícito, no un cálculo que se pueda improvisar
  con lo que la app ya pide hoy.
- **T-CO (comercial, gimnasios/estadios):** guardada como referencia. Tiene cargos por
  DEMANDA MÁXIMA (kW, no kWh) que requieren saber en qué instante ocurre el pico de
  demanda del sitio -- un cálculo de "reducción de demanda pico" distinto al de
  "ahorro de energía" que ya hace el resto de la app, no modelado.
- El tipo de cambio CRC→USD es un campo editable con un valor por defecto (₡520 por
  USD) -- **no hardcodeado como una constante confiable**: cambia a diario, y la
  recomendación de la investigación es usar el Tipo de Cambio de Referencia que
  publica el BCCR (bccr.fi.cr) antes de cotizar en firme, no el valor por defecto.

**Verificado:** `py_compile` limpio en los 3 archivos modificados; las 32 pruebas
existentes (`_calcular_punto_financiero`/`calcular_punto_unico`, basadas en tarifa
plana/%) siguen pasando sin tocarlas. Mecánica de clasificación horaria verificada a
mano con una semana sintética de 1 kWh/hora: de las 168 horas, 25 caen en Punta, 73 en
Valle y 70 en Nocturno -- coincide exacto con el conteo manual (5 horas Punta/día ×
5 días L-V, 9 horas Valle/día × 5 días + 14 horas/día × 2 días de fin de semana, 10
horas Nocturno/día × 7 días). Probado en vivo con Playwright: modo plano sin cambios
(regresión limpia); modo horario con CNFL T-REH y con ICE T-RH -- la tabla de
desglose reparte los 245 kWh/año del caso default en Punta/Valle/Nocturno sumando
exacto el total, cambiar de proveedor recalcula todo (CNFL daba $28/año de ahorro,
ICE $42/año, consistente con que las tarifas Valle/Nocturno de ICE son más altas); un
caso de prueba con números chicos (CAPEX=$300, mantenimiento=$10) dio Payback=839.4
años/ROI=-95%/NPV=-$14,787, verificado a mano con la fórmula exacta. Se encontró y
corrigió en el camino el mismo bug de Hallazgo 48 (dos "\$" en un `st.caption()` se
interpretan como LaTeX) en el caption nuevo de tarifa efectiva.

**Pendiente, no resuelto en este hallazgo:**
- Ninguno de los rangos horarios ni de los valores no confirmados de esta sección se
  verificó contra el PDF primario de ARESEP/ICE/CNFL (bloqueado por red en este
  entorno) -- alguien con acceso sin restricciones debería confirmar línea por línea
  antes de cotizar en firme a un cliente con la tarifa horaria (ver la lista completa
  de "no confirmados" arriba).
- El tratamiento de feriados (¿cuentan como fin de semana, sin Punta?) es una
  suposición razonable, no una cifra confirmada en ningún pliego.
- T-RE (escalonada), T-TCVE, T-A y T-CO quedan como datos de referencia sin cálculo de
  ahorro conectado -- ver la sección de arriba para el motivo de cada una.
- El desglose por periodo redondea cada fila de forma independiente antes de sumar
  (ej. $11+$13+$3 puede mostrar $27 en la tabla mientras el total real, con más
  decimales, es $28) -- es un artefacto de presentación, no un error de cálculo (el
  ahorro real usado en Payback/ROI/NPV es el total sin redondear por fila).

---

## 6. Pendientes activos / bloqueos

- [x] ~~Conseguir A/k reales del Global Wind Atlas~~ — resuelto, y con datos más ricos de lo
      esperado (curva empírica completa + estacionalidad real + wind rose). Ver Hallazgo 3.
- [x] ~~Decidir si se implementa la Pista C (ERA5 + quantile mapping) ahora o se pospone~~ —
      investigado (Hallazgo 21): acceso a CDS/ERA5 mapeado (registro gratuito + token, sin pago),
      y la MECÁNICA de quantile mapping ya se probó y funciona (fuera de muestra, sesgo sintético)
      contra el EPW real de San José. Sigue pendiente conseguir una serie horaria real (NASA POWER
      o ERA5) para validar el método contra un sesgo real, no sintético — ver Hallazgo 21.
- [ ] Confirmar si el sesgo de NASA POWER (~3x) y la brecha GWA-vs-EPW (~9%) se sostienen en
      otros puntos del Valle Central, o fueron específicos de esta coordenada.
- [ ] Entender mejor la discrepancia entre el `.lib` de WAsP (5.37 m/s) y el panel web del
      GWA (3.67 m/s) para la misma coordenada — la lectura actual (Hallazgo 3) es una
      hipótesis razonable, no una confirmación oficial.
- [ ] Conseguir EPWs/exports de GWA de los sitios reales de proyectos según se vayan
      definiendo.
- [ ] Unificar `z0` — `wind_at_height()` usa 0.3 (suburbano) como default ilustrativo, pero
      el `.lib` del GWA para este sitio se leyó con z0=0.030 (pasto corto/aeropuerto); son
      valores distintos y habría que decidir cuál aplica a cada sitio real. **Decisión del
      Director del Proyecto (30/ago/2026): queda pendiente, se afina más adelante — no
      bloquea seguir a la Pista B.**
- [x] ~~Modelar el componente de arrastre Savonius con geometría propia~~ — resuelto como
      estimación independiente con el Cp=0.34 de la patente ES2970155T3 (ver Hallazgo 4);
      ajusta mejor que la sustentación pura en los 4 modelos.
- [x] ~~Validar el ratio DMST/empírico contra otros tamaños~~ — resuelto (Hallazgo 4): el
      ratio NO es constante (5.43x Small a 1.24x Large), consistente con efecto Reynolds.
- [ ] Conseguir un polar NACA 0018 real (XFOIL o experimental) para calibrar la corrección de
      Reynolds con confianza (la versión actual empeora el ajuste absoluto aunque mejora la
      dispersión relativa — ver Hallazgo 4).
- [x] ~~Resolver cómo combinar el componente de sustentación (DMST) y el de arrastre
      (Savonius) en un solo modelo de la pala híbrida real~~ — polar híbrido construido,
      corregido (bug real: inflaba también la sustentación) y verificado con las dos
      verificaciones pedidas (Betz + 4 modelos). Ver Hallazgo 5: el resultado honesto es que
      el bloqueo no era la fórmula, sino no saber en qué TSR real opera la turbina.
- [x] ~~Conseguir la curva de par-velocidad real / RPM operativo típico~~ — resuelto sin
      necesitar más datos: la propia patente US9255567B2 da la fórmula del rpm objetivo del
      generador (equivalente a TSR≈1.0), usada en el modelo combinado. Ver Hallazgo 6.
- [x] ~~Combinar sustentación y arrastre con la arquitectura real (no el polar híbrido)~~ —
      implementado en `engine/rotor_combinado.py` y verificado (Betz + 4 modelos). Resultado
      honesto: combinar bien **no** resuelve la sobre-predicción — sigue siendo el problema
      abierto de la Pista B. Ver Hallazgo 6.
- [ ] **Investigar pérdidas electromecánicas (generador, rectificador/controlador de
      carga)** — con la vía aerodinámica agotada (inducción conjunta + Glauert, Hallazgo 8,
      sin cerrar la brecha, de hecho empeorándola), esta es ahora la hipótesis principal para
      la sobre-predicción residual en los 4 modelos. Ningún cálculo de esta pista las incluye
      todavía.
- [x] ~~Resolver una inducción conjunta entre los dos niveles de pala~~ — implementado y
      verificado (Hallazgo 7); la mejora que mostró resultó ser un artefacto del recorte
      numérico, corregido en el siguiente punto (Hallazgo 8).
- [x] ~~Agregar corrección de Glauert a alta inducción~~ — implementado y verificado
      (ida-y-vuelta a→CT→a exacta, continuidad en el punto de empalme). Cierra genuinamente
      el problema de Betz en todo el rango de TSR probado, pero revierte la mejora de
      Hallazgo 7: la sobre-predicción empeora, no mejora. Ver Hallazgo 8.
- [x] ~~Resincronizar `documentos_tecnicos/` con el contenido real desde Drive~~ — resuelto,
      90 de 91 archivos. El manual de SolArk (inversor de terceros) queda fuera de alcance por
      decisión del Director del Proyecto — no bloquea nada. Ver Hallazgo 6.
- [ ] Recalibrar los coeficientes `al13_2m/4m/6m/8m` en `flower_turbines_curves.py` — con la
      ficha técnica real del AL13 ya disponible (1.7m diámetro, ≈350W/módulo a 12 m/s), el
      coeficiente actual de `al13_2m` predice más del doble de eso (1523.7W) — se leyó
      aproximadamente de una gráfica sin la ficha real a mano. Ver Hallazgo 6.
- [ ] Validar la calibración K(v) contra datos de campo reales (catálogo Flower Turbines
      vs. dispersión real) — necesita el CSV detrás de los gráficos de dispersión, no solo
      las imágenes PNG.
- [ ] Extender Pista B (DMST/Savonius/modelo combinado) a los modelos AL13 Power Tower — ya
      tienen ficha técnica real (1.7m, módulos de 1m apilables), pero ningún cálculo de
      Pista B los cubre todavía; toda la Pista B hecha hasta ahora es sobre la línea Tulip.
- [ ] Confirmar el `Kd` correcto de la Tabla 26.6-1 de ASCE 7 para una estructura cilíndrica
      esbelta (mástil de VAWT) — se usó 0.85 (valor típico de edificios) en el primer módulo
      estructural; chimeneas/tanques redondos suelen usar 0.95-1.0 (Hallazgo 9).
- [ ] Calcular el factor de ráfaga flexible (Gf) en vez de G=0.85 fijo — requiere la
      frecuencia natural del pedestal/mástil, dato no disponible todavía (Hallazgo 9).
- [ ] Conseguir la frecuencia natural del techo/pedestal para poder evaluar riesgo real de
      resonancia por desprendimiento de vórtices (Strouhal) — el módulo estructural solo
      calcula la frecuencia de excitación, no puede evaluar resonancia sin ese dato
      (Hallazgo 9).
- [ ] Extender el análisis estructural ASCE 7 a los otros 3 modelos Tulip y AL13 (solo
      Medium Tulip probado hasta ahora) y a la carga de un clúster completo, no solo una
      turbina aislada.
- [ ] Reconciliar el Cd efectivo discrepante entre `External Load Calculations` (≈2.21) y
      `3 meter AL13 Side Forces at 50 mps.pdf` (≈1.70) — probablemente distintas convenciones
      de área frontal (caja envolvente D×H vs. área real proyectada de pala); necesita
      geometría CAD real para resolverse con confianza (Hallazgo 9).
- [ ] Conseguir la capacidad admisible de las varillas M18×2.5 y M14×2 (fluencia + arranque
      del concreto) para poder evaluar adecuación de los anclajes, no solo la demanda de
      tensión ya calculada — responsabilidad del ingeniero civil según los propios planos de
      Flower Turbines (Hallazgo 9/10).
- [ ] Conseguir el plano de base real del Small Tulip (0.55m/1.15m) — el plano "Small
      Pedestal" existente cubre Medium y 3-M Tulip, no el modelo más pequeño de la línea
      (Hallazgo 10).
- [ ] Reconciliar la discrepancia real entre `Calculation of forces.pdf` (T=1.08 kN a 30 m/s)
      y `External Load Calculations` (Frotor=2.7 kN a 30 m/s) para lo que parece ser la misma
      turbina — hipótesis principal: distintos casos de carga (operación normal vs. parked
      worst-case), no confirmada. También pendiente entender por qué R1+R2≠W en el diagrama
      de cuerpo libre de ese documento (Hallazgo 10).
- [ ] Decidir registro de leads para la Fase 2 (Sheets vs. Airtable — abierto en el plan,
      sección 7).
- [ ] Conseguir dato limpio para `al13_8m` — la única fuente disponible (columna "8m" de la
      Tabla 2 del manual AL13) resultó corrupta; sigue con la lectura aproximada anterior
      (confianza MEDIA) (Hallazgo 11).
- [ ] Reconciliar la velocidad de supervivencia 45 m/s (hojas Specs_2025) vs. 54 m/s (Quick
      Start Guides) para Medium y 3-M Tulip — diferencia sistemática entre tipos de documento,
      no ruido de un solo dato (Hallazgo 11).
- [ ] Reconciliar la curva de potencia del Large Tulip: calculador oficial (k=3.120040) vs.
      tabla propia del Quick Start Guide, ~4% más baja en todo el rango — ambas fuentes son
      oficiales (Hallazgo 11).
- [ ] Preguntarle a Pablo qué es el componente del plano de apéndice compartido entre los
      manuales de AL13 y 3-M Tulip (gabinete de acero, posible "Base Pivot") — no se incorporó
      a `PATRONES_ANCLAJE` por no saberse con certeza qué representa (Hallazgo 11).
- [ ] Incorporar la guía de espaciamiento de clúster (`Guidance on Spacing Flower Turbines.pdf`)
      cuando se retome el efecto clúster (CFD/Cilindro Actuador) — reglas ya documentadas en
      Hallazgo 11, todavía no llevadas a código.
- [ ] Modelar el cut-out operacional (~12 m/s para 3-M Tulip, vía charge controller) — el
      modelo actual solo tiene cut-in, no cut-out (Hallazgo 11).
- [ ] Procesar las fichas "Specs_2025" restantes (Small Tulip, Large Tulip, AL13) cuando Pablo
      las comparta — ya se procesaron las de Medium y 3-M Tulip (Hallazgo 11).
- [ ] Modelar presión de apoyo distribuida (peso + fricción, sin pernos) para instalaciones tipo
      `EcoRoof Energy Hub` — hoy `estructural_asce7.py` solo calcula tensión puntual en pernos de
      anclaje, un tipo de carga distinto (Hallazgo 13).
- [ ] Confirmar el ancho real del AL13 (1.6m vs 1.7m, discrepancia entre páginas del mismo
      manual, Hallazgo 11) antes de tomar como definitivo el caso de prueba de Hallazgo 13.
- [ ] Extender el modelo de Cilindro Actuador con la arquitectura real de dos niveles (perfil
      híbrido sustentación+arrastre, `polar_hibrido.py`) en vez de NACA0018 puro, para probar la
      hipótesis 1 de Hallazgo 15 (el mecanismo del Efecto Bouquet podría depender de la
      geometría cóncava del componente Savonius) — actualmente sin confirmar.
- [ ] Probar más configuraciones del Cilindro Actuador (otros TSR/velocidades de viento, N=3+,
      efecto 3D con altura de pala) antes de descartar el enfoque por completo (Hallazgo 15).
- [ ] Cuando se construya el modelo CFD de efecto clúster (Cilindro Actuador/OpenFOAM), decidir
      si `cargas_viento_cluster_asce7()` debe incorporar crédito de apantallamiento aerodinámico
      en vez de la suma simple conservadora actual (Hallazgo 13).
- [ ] Confirmar contra la ficha técnica real del proveedor en Costa Rica si las capacidades
      dadas para `evaluar_capacidad_anclaje()` (M12/5-8"/3-4") corresponden a ASTM A193 Grado
      B7 o a Grado 8.8 — los números coinciden más con Grado 8.8 en la verificación hecha
      (Hallazgo 14).
- [ ] Conseguir capacidad de M14/M18 (los pernos REALES ya usados en `PATRONES_ANCLAJE`) en la
      misma norma que finalmente se confirme — hoy `evaluar_capacidad_anclaje()` solo cubre
      M12/5-8"/3-4", que no son tamaños exactos para Medium/3-M Tulip (M14) ni Large
      Tulip/AL13 (M18) (Hallazgo 14).
- [ ] Confirmar o descartar el dado de concreto "0.5×0.5×0.5m" para Small Tulip — no aparece en
      ningún documento revisado; el único plano real verificado (poste ZW) da 450×450×1060mm
      (Hallazgo 14).
- [ ] Calcular capacidad real de arranque del concreto (cone breakout, ACI 318 Apéndice D) con
      la profundidad de empotramiento real — `evaluar_capacidad_anclaje()` solo advierte que
      falta, no la calcula (Hallazgo 14).
- [ ] Verificar si NASA POWER es alcanzable desde el entorno de producción (Cloud Run) — en este
      entorno de desarrollo está bloqueado por el proxy de red (Hallazgo 16).
- [ ] Conseguir datos GWA reales para más sitios (hoy solo hay uno preparado, San José/Juan
      Santamaría) o resolver una ingesta automática por coordenada — bloquea el flujo
      "coordenada → pronóstico instantáneo" del plan, sección 5 (Hallazgo 16).
- [ ] Correr `docker build -t eco-wind-app .` y `docker run -p 8501:8501 eco-wind-app` en una
      máquina con salida a internet normal — no se pudo verificar el build completo en este
      entorno (Docker Hub bloqueado por la política de red del sandbox, Hallazgo 16).
- [ ] Desplegar `app/` a Cloud Run (Docker + Cloud Build, mismo patrón de Skyplus/DDP-Lite) — hoy
      solo corre local (Hallazgo 16).
- [ ] Agregar al MVP: mapa de ubicación, PDF de cotización, registro de leads (Sheets vs.
      Airtable, todavía sin decidir) (Hallazgo 16, plan sección 5).
- [ ] Descargar el ráster real de Costa Rica (`datos_clima/gwa_costa_rica_10m.tif`) desde un
      entorno con internet real (Colab) usando `descargar_raster_costa_rica()` — sin esto, el
      camino de "coordenada personalizada" de la app sigue siendo una aproximación con error
      ya cuantificado de -44% a +18% (Hallazgo 18), no un cálculo confiable (Hallazgo 17).
- [ ] Resolver búsqueda automática de elevación por DEM — hoy es manual en la app para
      coordenadas nuevas (Hallazgo 17).
- [x] ~~Validar la aproximación de "forma prestada de San José" contra datos reales de al menos
      un segundo sitio con export propio~~ — resuelto contra 3 sitios reales (Nicoya, Liberia,
      Finca Favorita): error de -41% a -44% en Guanacaste, +18% en Limón. La aproximación NO es
      confiable fuera del Valle Central — ver Hallazgo 18.
- [x] ~~Nuevo, de Hallazgo 18: con el error de la forma prestada ya cuantificado y grande (hasta
      44%), evaluar si conviene tener más de una "forma de referencia" regional~~ — probado con
      leave-one-out (Hallazgo 21): el concepto SÍ está bien fundado (la forma real de Nicoya y
      Liberia difiere sólo 4.7% entre sí, vs. 44-51% contra San José), pero la validación como tal
      salió peor que prestar siempre San José (+114% a +281% de error) por un artefacto real de
      `generar_clima_gwa()` — no por el concepto en sí. Ver el siguiente pendiente.
- [x] ~~Nuevo, de Hallazgo 21: `generar_clima_gwa()` infla `E[v³]/media³` (~2x en Nicoya/Liberia)~~
      — mitigado (no resuelto del todo) con curva de excedencia por residuos (Hallazgo 22):
      inflación baja de ~105% a 14-30%. Liberia ya muestra una mejora clara y real (+15.9% nuevo
      vs -43.7% viejo). Sigue pendiente: cerrar el 7-30% de inflación residual, y conseguir más de
      4 sitios reales antes de que la validación leave-one-out sea un veredicto sólido para
      Alternativa 4 — sigue sin conectarse a `app.py`.
- [x] ~~Nuevo, de Hallazgo 21: conseguir una serie horaria real de NASA POWER... para validar
      quantile mapping contra un sesgo real~~ — resuelto para San José (Hallazgo 23, corrido en
      Colab): quantile mapping sí mejora sobre la corrección naive con datos reales (-2.6% vs
      -6.95% de error), pero menos que lo que sugería la prueba sintética. Sigue pendiente probarlo
      en Nicoya/Liberia/Finca Favorita, y decidir si la mejora justifica la complejidad extra
      frente a la corrección naive que ya existe.
- [ ] **Nuevo, de Hallazgo 23:** probar la validación real de quantile mapping (NASA POWER vs. EPW)
      en Nicoya, Liberia y Finca Favorita — hoy sólo está confirmado con datos reales para San José
      (2023). El sesgo de NASA POWER podría comportarse distinto en sitios costeros/de otra
      elevación.
- [ ] Cuando exista el ráster real, decidir si vale la pena pedir también capacity-factor
      (`/api/gis/country/CRI/capacity-factor_IEC{1,2,3}`) del mismo endpoint oficial, como
      dato adicional (Hallazgo 17).
- [ ] **Nuevo, de Hallazgo 19:** probar el mapa + búsqueda por nombre + descarga de estaciones de
      punta a punta con internet real (Docker local de Pablo o Cloud Run) — en este sandbox sólo
      se pudo verificar la lógica (búsqueda Haversine + fallback bbox, lista, manejo de error),
      no la geocodificación, el mapa visual, ni una descarga real exitosa (`nominatim.
      openstreetmap.org`, `photon.komoot.io`, `cdn.jsdelivr.net` y `climate.onebuilding.org`
      bloqueados acá).
- [ ] **Nuevo, de Hallazgo 27:** correr en Colab la Parte 1 de `koppen_seleccion_donante.ipynb`
      (acceso real al raster de Beck et al. 2018 vía la API pública de Figshare, bloqueada en este
      sandbox) y, si responde bien, decidir la regla de desempate y terminar
      `vecino_mas_cercano_por_zona()` + validación leave-one-out contra la selección por distancia
      pura (mismo patrón de Hallazgo 21/22).
- [ ] **Nuevo, de Hallazgo 19:** el catálogo (5,276 estaciones, 20 países) es el de DDP-lite/
      Skyplus tal cual — algunas estaciones no traen coordenada en el catálogo (se excluyen de
      la búsqueda por distancia, mismo comportamiento que el original). Si hace falta ampliar el
      catálogo a más países o completar coordenadas faltantes, es un scraping aparte de
      climate.onebuilding.org — no algo para inventar sin la fuente real.
- [ ] **Nuevo, de Hallazgo 20:** el default `z0_met=0.1` ("country"/aeropuerto) es el más
      defendible con lo que se sabe hoy (así lo documenta ladybug-tools/EnergyPlus para datos de
      aeropuerto), pero no está validado contra producción real de una turbina instalada. Si en
      algún momento hay datos de producción real de un proyecto, es el punto más directo para
      validar (o ajustar) tanto `z0_met` como la elección entre ley logarítmica y de potencia.
- [x] ~~Nuevo, de Hallazgo 25: correr `descargar_raster_pais("CRI")` en Colab y repetir la
      validación leave-one-out con `factor_ajuste_gwa()`~~ — resuelto (Hallazgo 26): resultado
      mixto, mucho mejor que NASA POWER pero no una victoria limpia (bien en Guanacaste, mal en San
      José/Finca Favorita). Ver el siguiente pendiente.
- [x] ~~Reabierto por Hallazgo 35: investigar por qué el ráster crudo de GWA se aleja tanto de la
      realidad en San José (-43%) y Finca Favorita (-87%), e invierte el orden Santamaría/La
      Sabana~~ — **cerrado por decisión de producto (Hallazgo 36), no resuelto técnicamente:** Pablo
      decidió abandonar toda sensibilización espacial de magnitud (GWA/NASA POWER/ERA5/Köppen) en vez
      de seguir afinándola. La app ahora corre 100% sobre EPW real (estación de la lista o subida por
      el usuario); el código de esta línea de investigación queda en el repo sin usar, no borrado.
- [x] ~~Nuevo, de Hallazgo 26/27: correr la Parte 4 de
      `notebooks/sensibilizar_punto_exacto.ipynb` en Colab para tener el número real de ERA5~~ —
      cerrado sin correr, por decisión de producto (Hallazgo 36): se abandonó toda la línea de ajuste
      espacial por fuente externa (GWA/NASA POWER/ERA5/Köppen), no sólo ERA5.
- [x] ~~Nuevo, de Hallazgo 31: correr `generar_clima_sensibilizado()` contra el ráster real de
      Costa Rica~~ — resuelto (Hallazgo 35): el ráster real ya está en el repo, se corrió con el
      código de producción real (no mock) contra varios puntos del Valle Central y contra los 4
      sitios ya conocidos. El número final confirma el problema que Hallazgo 26 ya sospechaba, no lo
      descarta.
- [ ] **Nuevo, de Hallazgo 32:** conseguir specs de `al13_4m` (falta en el DataFrame de Pablo) y
      decidir si vale la pena construir curvas de potencia para Survival Unit y las 3 variantes de
      EcoRoof Energy Hub (hoy tienen ficha técnica mostrable pero no son simulables).
- [ ] **Nuevo, de Hallazgo 33:** Pablo debe reconstruir la imagen Docker (`docker build` +
      `docker run`) en un entorno con salida a internet normal y confirmar que Heredia (y otros
      puntos fuera de los 4 sitios precacheados) ya buscan bien — no se pudo verificar el build en
      este sandbox (Docker Hub bloqueado).
- [ ] **Nuevo, de Hallazgo 34:** el menú lateral se verificó de punta a punta con Chromium
      automatizado (Playwright) en este sandbox — falta que Pablo lo vea y lo use él mismo para
      confirmar que el criterio de diseño ("mejor orden visual") quedó resuelto a su gusto, y no
      sólo funcionalmente correcto.
- [x] ~~Nuevo, de Hallazgo 41/42/43: conseguir datasheet técnico real para los 4 inversores
      residenciales de la cotización (9K-2P, 12K-2P, 12K-2P-LL, 15K-2P)~~ — resuelto (Hallazgo
      44): Pablo consiguió los 5 PDFs oficiales de Sol-Ark (incluyendo uno nuevo del 18K para
      recontrastar); `solark_specs.py` reemplazado con los valores reales de cada datasheet,
      confirmando que los datos fabricados (Hallazgo 43) tenían errores grandes, no sólo de
      redondeo (ej.: potencia FV del 12K estándar 24,000W fabricado vs. 12,000W real).
- [ ] **Nuevo, de Hallazgo 41:** conseguir cotización de fábrica/mayorista real de EG4 (hoy el
      costo base usado en `eg4_specs.py` es precio retail de distribuidor en EE.UU., no de
      fábrica como Sol-Ark/Flower Turbines) — afecta la confiabilidad del precio de venta
      calculado para BESS de 48V.
- [ ] **Nuevo, de Hallazgo 41/43:** verificar contra un datasheet o cotización propia (no una
      respuesta de chat) los precios de Flower Turbines marcados `costo_usd_fuente:
      "no_verificado"` en `turbine_specs.py` (large_tulip, al13_6m, al13_8m, ecoroof_flat_3,
      ecoroof_flat_5) y el paquete industrial AL13 de 30kW/60kW en `dimensionador_sistema_eolico.py`.
- [x] ~~Nuevo, de Hallazgo 40/41/42/43: construir la pestaña "Análisis Financiero" en
      `app.py`~~ — resuelto (Hallazgo 48): conectada, con 2 bugs reales encontrados y
      corregidos probando en vivo con Playwright (texto roto por `$` sin escapar en
      markdown; BESS cobrando un fee de importación fantasma en modo Hybrid).
- [x] ~~Nuevo, de Hallazgo 48: sensibilizar el % de mantenimiento anual por default de
      `financial_engine_eolico.py` (2%)~~ — resuelto (Hallazgo 49): expuesto como slider
      0-5% en "Parámetros avanzados". Probado hasta 0% con un arreglo real: el "NO VIABLE"
      se sostiene (payback ≈171 años) — confirma que el 2% no era la causa, es el costo de
      fábrica de las turbinas vs. el ahorro eléctrico de arreglos chicos.
- [x] ~~Nuevo, de Hallazgo 47: definir la tipografía de marca de ECO Consultor~~ — resuelto
      (Hallazgo 49): Montserrat + Dosis, confirmadas en el libro de marca oficial, cargadas
      vía Google Fonts. Pendiente nuevo: el PDF exportado todavía usa Helvetica (ver
      Hallazgo 49) por no tener el `.ttf` real en el repositorio.
- [ ] **Nuevo, de Hallazgo 49:** embeber la fuente real de marca (Montserrat/Dosis, `.ttf`)
      en el PDF de `engine/pdf_reporte.py` — hoy usa Helvetica estándar, sólo los colores
      son de marca.
- [ ] **Nuevo, de Hallazgo 49:** cuantificar en dólares el valor de respaldo/resiliencia
      energética que se le sugiere a Pablo presentar cuando el sistema da "NO VIABLE" por
      ahorro puro — hoy es sólo una recomendación en texto en la pestaña financiera.
- [x] ~~Nuevo, de Hallazgo 49: sensibilizar el fee de importación plano de $2,500/línea,
      muy por encima del flete real~~ — resuelto (Hallazgo 50): reemplazado por un modelo
      de flete consolidado por peso (unidad $2,000/pallet $3,500/contenedor $10,000).
- [ ] **Nuevo, de Hallazgo 50:** confirmar con un forwarder real (no un dato de mercado
      dado de memoria) las 3 tarifas de flete y los límites de peso por pallet/contenedor
      usados en `price_calculator.py::calcular_flete_consolidado_usd()`.
- [ ] **Nuevo, de Hallazgo 50:** confirmar con Flower Turbines si las turbinas se
      embarcan desarmadas/en secciones (supuesto usado para tratar el peso como el único
      factor limitante) — si el volumen real limita antes que el peso, los límites de
      pallet/contenedor podrían estar sobrestimando cuántas unidades entran.
- [ ] **Nuevo, de Hallazgo 51:** agregar coeficientes de curva de potencia para
      `ecoroof_flat_3`, `ecoroof_flat_5`, `ecoroof_slanted` y `survival_unit` a
      `CURVE_COEFFICIENTS` (`flower_turbines_curves.py`) — hoy tienen ficha técnica y
      costo en `turbine_specs.py` pero no son seleccionables en "Equipos y
      configuración", así que ningún cálculo de energía las puede usar.
- [ ] **Nuevo, de Hallazgo 51:** documentar o cuantificar el efecto aerodinámico LOCAL
      de un techo de edificio (aceleración sobre el borde, turbulencia por
      parapetos/HVAC, estela de edificios vecinos) para instalaciones tipo Eco-Roof —
      hoy sólo se extrapola la velocidad REGIONAL a la altura del techo, sin ese
      efecto local (ver literatura de turbinas integradas a edificios, BIWT).
- [x] ~~Nuevo, de Hallazgo 51: investigar si GWA a 50/100m o ERA5-Land resuelve el
      ruido espacial del Valle Central~~ — cerrado con evidencia (Hallazgo 52): GWA-50m
      mejora el ruido a la mitad pero no lo resuelve, ERA5-Land sigue bloqueado de red
      y sin poder probarse, y las 3 correcciones adicionales evaluadas (Gower/Köppen,
      TPI/EN1991-1-4, WorldCover z0) no atacan la causa real o reproducen el mismo
      ruido en otra variable. No se retoma ninguna línea de ajuste espacial remoto —
      la salida real es medición local (measure-correlate-predict).
- [ ] **Nuevo, de Hallazgo 52:** si en algún momento se puede probar ERA5-Land vía
      Open-Meteo desde un entorno con internet real (Colab, como ya se hizo para CDS) —
      el notebook `sensibilizar_punto_exacto.ipynb` (Parte 5) ya está escrito y listo
      para correr, sólo bloqueado por red en este sandbox de desarrollo.
- [ ] **Nuevo, de Hallazgo 52:** la coordenada de "Puntarenas" en
      `datos_clima/epw_catalog_global.json` está mal (a 4.5-9.4 km de Heredia cuando la
      ciudad real está a ~70-80 km) — mismo tipo de error ya conocido en Finca Favorita
      (Hallazgo 35), confirmar y corregir la coordenada real del catálogo.

## 7. Cómo navegar el repositorio en este punto

```
ECO-Wind/
├── plan-tecnico-eco-wind.md          ← alcance (este documento lo compara contra avance real)
├── avance-de-proyecto.md             ← este documento
├── Dockerfile, .dockerignore          ← Docker local (Hallazgo 16); `COPY . .` + un solo
│                                         `.dockerignore` (Hallazgo 33) en vez de lista manual --
│                                         build sin verificar con red real en este entorno
├── Recursos Visuales/                 ← imágenes de producto + logos ECO/Flower Turbines
│                                         (Hallazgo 32)
├── app/                               ← Fase 2, MVP de Streamlit (Hallazgos 16-20, 31-34)
│   ├── app.py                         ← interfaz: menú lateral (navegador de 4 secciones, clona
│   │                                     estructura DDP-lite/Skyplus, Hallazgo 34) + multi-clúster
│   │                                     + fichas técnicas/imágenes (Hallazgo 32) + gráficos + mapa,
│   │                                     corre local con `streamlit run app/app.py`
│   └── requirements.txt               ← incluye folium/streamlit-folium desde Hallazgo 19
├── engine/
│   ├── flower_turbines_curves.py     ← motor de curvas de potencia, validado (Hallazgo 12)
│   ├── turbine_specs.py              ← fichas técnicas (11 modelos) + rutas de imagen/logos
│   │                                     (Hallazgo 32); al13_4m sin ficha, gap real de Pablo
│   ├── simulador_pista_a.py          ← simular()/wind_at_height()/GWA/wind rose/Jensen/ley de
│   │                                     potencia EnergyPlus (Hallazgos 16-17, 20)
│   ├── atmosfera_estandar.py         ← densidad ISA por elevación (Hallazgo 17)
│   ├── gwa_raster.py                 ← clima para cualquier coordenada de CR, ráster+forma prestada
│   │                                     (Hallazgo 17) + descargar_raster_pais()/factor_ajuste_gwa(),
│   │                                     generalizado a cualquier país (Hallazgo 25) -- pausado,
│   │                                     resultado mixto (Hallazgo 26)
│   ├── era5_client.py                ← ajuste espacial vía ERA5 (Hallazgo 25/26), la apuesta actual
│   │                                     -- necesita cuenta+token de Copernicus CDS de Pablo
│   ├── epw_real.py                   ← parser EPW propio + 3 sitios reales (Nicoya/Liberia/Finca
│   │                                     Favorita, Hallazgo 18) + búsqueda/geocodificación/
│   │                                     descarga de estaciones, 20 países, homologado con
│   │                                     DDP-lite/Skyplus (Hallazgo 19)
│   ├── formas_regionales.py          ← CONECTADO a app.py desde Hallazgo 31: vecino más cercano +
│   │                                     leave-one-out entre los 4 sitios reales (Hallazgo 21) +
│   │                                     curva de excedencia por residuos, usar_residuo=True
│   │                                     (Hallazgo 22) + generar_clima_sensibilizado(), el punto de
│   │                                     entrada real que usa app.py (Hallazgo 31)
│   ├── quantile_mapping.py           ← investigación, NO conectado a app.py: quantile mapping
│   │                                     genérico + prueba de mecánica contra EPW real (Hallazgo 21)
│   ├── dmst_model.py, rotor_combinado.py, polar_hibrido.py, naca0018_polar.py  ← Pista B aerodinámica
│   ├── estructural_asce7.py          ← Pista B estructural, ASCE 7 (Hallazgos 9-10, 13-14)
│   └── actuator_cylinder.py          ← Pista B efecto clúster, Cilindro Actuador (Hallazgo 15)
├── notebooks/
│   ├── pista_a_motor_empirico.ipynb  ← sandbox Pista A completo, corre en Colab o local
│   ├── pista_b_motor_fisico.ipynb    ← sandbox Pista B, aerodinámica
│   └── pista_c_forma_regional_y_quantile_mapping.ipynb  ← vecino más cercano + leave-one-out +
│                                         acceso a ERA5/CDS + quantile mapping (Hallazgo 21-22),
│                                         corre de punta a punta en Colab o local; las celdas que
│   │                                     necesitan internet real (NASA POWER, CDS) están marcadas
│   ├── descargar_estaciones_cr.ipynb  ← descarga automatizada de las 8 estaciones de Costa Rica
│   │                                     que faltaban en el catálogo local (Hallazgo 21-22) +
│   │                                     análisis real de Limón como donante para Finca Favorita
│   │                                     (Hallazgo 29: geográficamente más cerca, pero peor forma)
│   ├── prueba_internacional_estacion_mas_cercana.ipynb  ← auto-pivota a la estación real más
│   │                                     cercana en cualquiera de los 20 países del catálogo, sin
│   │                                     anclar nada a San José -- probado en 6 países (Hallazgo 24)
│   ├── sensibilizar_punto_exacto.ipynb  ← ajuste espacial de la estación donante al punto exacto:
│   │                                     NASA POWER descartado (Hallazgo 25), GWA mixto/pausado
│   │                                     (Hallazgo 26), ERA5 la apuesta actual (Parte 4, pendiente
│   │                                     de correr con cuenta CDS real)
│   └── koppen_seleccion_donante.ipynb  ← eje distinto: filtro de zona Köppen para elegir QUÉ
│                                         estación donar, no ajuste de magnitud (Hallazgo 27) --
│                                         boceto, acceso al raster (Figshare) sin verificar en
│                                         Colab todavía
├── datos_clima/
│   ├── *.epw                          ← EPWs de estación real (aeropuerto Juan Santamaría)
│   ├── gwa_juan_santamaria/           ← export real del Global Wind Atlas
│   ├── epw_real/                      ← 3 EPW reales de climate.onebuilding.org (Hallazgo 18):
│   │                                     Nicoya, Liberia, Finca Favorita
│   ├── epw_catalog_global.json         ← catálogo completo (5,276 estaciones, 20 países),
│   │                                     idéntico al de DDP-lite/Skyplus (Hallazgo 19)
│   └── gwa_costa_rica_10m.tif          ← (falta) ráster de todo el país, ver pendientes Hallazgo 17
└── documentos_tecnicos/               ← research, fichas técnicas, insumos originales
```
