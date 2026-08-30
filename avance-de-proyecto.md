# ECO | Wind — Avance de Proyecto

**Documento de referencia (alcance):** [`plan-tecnico-eco-wind.md`](./plan-tecnico-eco-wind.md)
**Última actualización:** 30 de agosto, 2026 (Hallazgo 5 — combinación sustentación+arrastre)
**Propósito:** comparar el alcance planeado contra el avance real, y dejar constancia de los
hallazgos que no estaban previstos en el plan original. Se actualiza en cada avance
significativo — no es una foto única.

---

## 1. Estado general

| Fase / Pista | Estado |
|---|---|
| **Fase 1 — Pista A** (motor empírico) | 🟢 Sólida — mecánica y fuentes de datos climáticos (EPW + GWA) validadas con datos reales; z0/afinación fina quedó pendiente para más adelante (decisión del Director del Proyecto) |
| **Fase 1 — Pista B** (motor físico DMST + CFD) | 🟡 Primer avance — DMST de turbina aislada construido y validado; polar híbrido sustentación+arrastre construido, corregido y verificado (Betz + 4 modelos), pero bloqueado en combinar ambos componentes por falta de la curva par-velocidad real del producto (Hallazgo 5) |
| **Fase 2** (productización: Streamlit + Cloud Run) | ⚪ No iniciada |

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
| 1 | DMST turbina aislada (patentes CA2800765C/US9255567B2, ES2970155T3) | 🟡 Sustentación (NACA 0018) y arrastre (Savonius, patente ES2970155T3) construidos y validados por separado; combinación en un polar único construida y verificada (Betz + 4 modelos), pero bloqueada por falta de dato real (TSR/RPM de operación) — ver Hallazgo 5 |
| 2 | Pérdida dinámica a TSR bajo (Leishman-Beddoes) | ⚪ No iniciado |
| 3 | Efecto clúster (Cilindro Actuador, OpenFOAM offline) | ⚪ No iniciado |
| 4 | Estructural (ASCE 7) | ⚪ No iniciado |

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
- [ ] Conseguir la curva de par-velocidad real del generador/carga eléctrica, o al menos el
      RPM operativo típico, de al menos un modelo Flower Turbines — es el dato que falta para
      cerrar la combinación sustentación+arrastre (Hallazgo 5), ahora el bloqueo central de
      la Pista B.
- [ ] Validar la calibración K(v) contra datos de campo reales (catálogo Flower Turbines
      vs. dispersión real) — necesita el CSV detrás de los gráficos de dispersión, no solo
      las imágenes PNG.
- [ ] Decidir registro de leads para la Fase 2 (Sheets vs. Airtable — abierto en el plan,
      sección 7).

## 7. Cómo navegar el repositorio en este punto

```
ECO-Wind/
├── plan-tecnico-eco-wind.md          ← alcance (este documento lo compara contra avance real)
├── avance-de-proyecto.md             ← este documento
├── engine/
│   └── flower_turbines_curves.py     ← motor de curvas de potencia, validado
├── notebooks/
│   └── pista_a_motor_empirico.ipynb  ← sandbox Pista A completo, corre en Colab o local
├── datos_clima/
│   └── *.epw                          ← EPWs de estación real (por ahora: aeropuerto Juan Santamaría)
└── documentos_tecnicos/               ← research, fichas técnicas, insumos originales
```
