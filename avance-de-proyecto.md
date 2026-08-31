# ECO | Wind — Avance de Proyecto

**Documento de referencia (alcance):** [`plan-tecnico-eco-wind.md`](./plan-tecnico-eco-wind.md)
**Última actualización:** 31 de agosto, 2026 (Hallazgo 19 v3 — consolidado en UN SOLO flujo de búsqueda de clima, igual que DDP-lite/Skyplus: sin selector de modos, estación real siempre, aproximación como fallback automático sólo cuando hace falta; Hallazgo 20 — corrección real en el perfil de viento por altura, z0 de referencia distinto de z0 destino; Hallazgo 21 — vecino más cercano validado por leave-one-out, con un artefacto real de `generar_clima_gwa()` encontrado en el camino; quantile mapping probado (mecánica) y acceso a ERA5/CDS investigado; Hallazgo 22 — mitigación parcial de ese artefacto vía curva de excedencia por residuos: Liberia ya muestra una mejora clara y real con el vecino más cercano)
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
a Costa Rica) y subida de EPW propio, y arquitectura para cualquier otra coordenada (ráster+forma prestada, error ya cuantificado -44%/+18%, pendiente el archivo real). Falta: PDF, leads, despliegue a Cloud Run (Hallazgos 16-20) |

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
- [ ] **Nuevo, de Hallazgo 21:** conseguir una serie horaria real de NASA POWER (de una corrida en
      Colab con internet, o que Pablo la provea) o acceso a ERA5 (registro CDS, gratuito, ver
      Hallazgo 21) para validar quantile mapping contra un sesgo real — hoy sólo está probada la
      mecánica del método contra un sesgo sintético (aunque la magnitud del sesgo sí es real,
      Hallazgo 1).
- [ ] Cuando exista el ráster real, decidir si vale la pena pedir también capacity-factor
      (`/api/gis/country/CRI/capacity-factor_IEC{1,2,3}`) del mismo endpoint oficial, como
      dato adicional (Hallazgo 17).
- [ ] **Nuevo, de Hallazgo 19:** probar el mapa + búsqueda por nombre + descarga de estaciones de
      punta a punta con internet real (Docker local de Pablo o Cloud Run) — en este sandbox sólo
      se pudo verificar la lógica (búsqueda Haversine + fallback bbox, lista, manejo de error),
      no la geocodificación, el mapa visual, ni una descarga real exitosa (`nominatim.
      openstreetmap.org`, `photon.komoot.io`, `cdn.jsdelivr.net` y `climate.onebuilding.org`
      bloqueados acá).
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

## 7. Cómo navegar el repositorio en este punto

```
ECO-Wind/
├── plan-tecnico-eco-wind.md          ← alcance (este documento lo compara contra avance real)
├── avance-de-proyecto.md             ← este documento
├── Dockerfile, .dockerignore          ← Docker local (Hallazgo 16) -- build sin verificar en
│                                         este entorno, ver adenda de Hallazgo 16
├── app/                               ← Fase 2, MVP de Streamlit (Hallazgos 16-20)
│   ├── app.py                         ← interfaz, multi-clúster + gráficos + mapa, corre local con
│   │                                     `streamlit run app/app.py`
│   └── requirements.txt               ← incluye folium/streamlit-folium desde Hallazgo 19
├── engine/
│   ├── flower_turbines_curves.py     ← motor de curvas de potencia, validado (Hallazgo 12)
│   ├── simulador_pista_a.py          ← simular()/wind_at_height()/GWA/wind rose/Jensen/ley de
│   │                                     potencia EnergyPlus (Hallazgos 16-17, 20)
│   ├── atmosfera_estandar.py         ← densidad ISA por elevación (Hallazgo 17)
│   ├── gwa_raster.py                 ← clima para cualquier coordenada de CR, ráster+forma prestada (Hallazgo 17)
│   ├── epw_real.py                   ← parser EPW propio + 3 sitios reales (Nicoya/Liberia/Finca
│   │                                     Favorita, Hallazgo 18) + búsqueda/geocodificación/
│   │                                     descarga de estaciones, 20 países, homologado con
│   │                                     DDP-lite/Skyplus (Hallazgo 19)
│   ├── formas_regionales.py          ← investigación, NO conectado a app.py: vecino más cercano +
│   │                                     leave-one-out entre los 4 sitios reales (Hallazgo 21) +
│   │                                     curva de excedencia por residuos, usar_residuo=True (Hallazgo 22)
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
│                                         necesitan internet real (NASA POWER, CDS) están marcadas
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
