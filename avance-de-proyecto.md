# ECO | Wind — Avance de Proyecto

**Documento de referencia (alcance):** [`plan-tecnico-eco-wind.md`](./plan-tecnico-eco-wind.md)
**Última actualización:** 31 de agosto, 2026 (Hallazgo 16 — arranca Fase 2: MVP de Streamlit sobre Pista A, con dos límites reales del MVP comunicados explícitamente)
**Propósito:** comparar el alcance planeado contra el avance real, y dejar constancia de los
hallazgos que no estaban previstos en el plan original. Se actualiza en cada avance
significativo — no es una foto única.

---

## 1. Estado general

| Fase / Pista | Estado |
|---|---|
| **Fase 1 — Pista A** (motor empírico) | 🟢 Sólida — mecánica y fuentes de datos climáticos (EPW + GWA) validadas con datos reales; z0/afinación fina quedó pendiente para más adelante (decisión del Director del Proyecto) |
| **Fase 1 — Pista B** (motor físico DMST + CFD) | 🟡 Aerodinámica congelada (vía agotada, sobre-predicción sigue abierta, Hallazgo 8); curvas de potencia re-verificadas contra el calculador oficial, sin dudas reales (Hallazgo 12) — módulo estructural ASCE 7 con demanda de anclaje para 5 modelos y carga de clúster conservadora (Hallazgos 9-10, 13); Cilindro Actuador implementado y validado, pero no reproduce el Efecto Bouquet real todavía (Hallazgo 15) |
| **Fase 2** (productización: Streamlit + Cloud Run) | 🟡 MVP arrancado — app de Streamlit funcional corriendo local sobre Pista A, un sitio real (San José). Falta: más sitios/coordenada arbitraria, mapa, PDF, leads, despliegue a Cloud Run (Hallazgo 16) |

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

---

## 6. Pendientes activos / bloqueos

- [x] ~~Conseguir A/k reales del Global Wind Atlas~~ — resuelto, y con datos más ricos de lo
      esperado (curva empírica completa + estacionalidad real + wind rose). Ver Hallazgo 3.
- [ ] Decidir si se implementa la Pista C (ERA5 + quantile mapping) ahora o se pospone —
      menor prioridad ahora que GWA y EPW ya concuerdan razonablemente entre sí (~9%).
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
- [ ] Desplegar `app/` a Cloud Run (Docker + Cloud Build, mismo patrón de Skyplus/DDP-Lite) — hoy
      solo corre local (Hallazgo 16).
- [ ] Agregar al MVP: mapa de ubicación, PDF de cotización, registro de leads (Sheets vs.
      Airtable, todavía sin decidir) (Hallazgo 16, plan sección 5).

## 7. Cómo navegar el repositorio en este punto

```
ECO-Wind/
├── plan-tecnico-eco-wind.md          ← alcance (este documento lo compara contra avance real)
├── avance-de-proyecto.md             ← este documento
├── app/                               ← Fase 2, MVP de Streamlit (Hallazgo 16)
│   ├── app.py                         ← interfaz, corre local con `streamlit run app/app.py`
│   └── requirements.txt
├── engine/
│   ├── flower_turbines_curves.py     ← motor de curvas de potencia, validado (Hallazgo 12)
│   ├── simulador_pista_a.py          ← simular()/wind_at_height()/GWA, extraído del notebook (Hallazgo 16)
│   ├── dmst_model.py, rotor_combinado.py, polar_hibrido.py, naca0018_polar.py  ← Pista B aerodinámica
│   ├── estructural_asce7.py          ← Pista B estructural, ASCE 7 (Hallazgos 9-10, 13-14)
│   └── actuator_cylinder.py          ← Pista B efecto clúster, Cilindro Actuador (Hallazgo 15)
├── notebooks/
│   ├── pista_a_motor_empirico.ipynb  ← sandbox Pista A completo, corre en Colab o local
│   └── pista_b_motor_fisico.ipynb    ← sandbox Pista B, aerodinámica
├── datos_clima/
│   ├── *.epw                          ← EPWs de estación real (por ahora: aeropuerto Juan Santamaría)
│   └── gwa_juan_santamaria/           ← export real del Global Wind Atlas (único sitio preparado)
└── documentos_tecnicos/               ← research, fichas técnicas, insumos originales
```
