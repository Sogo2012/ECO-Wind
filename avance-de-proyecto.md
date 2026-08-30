# ECO | Wind — Avance de Proyecto

**Documento de referencia (alcance):** [`plan-tecnico-eco-wind.md`](./plan-tecnico-eco-wind.md)
**Última actualización:** 30 de agosto, 2026
**Propósito:** comparar el alcance planeado contra el avance real, y dejar constancia de los
hallazgos que no estaban previstos en el plan original. Se actualiza en cada avance
significativo — no es una foto única.

---

## 1. Estado general

| Fase / Pista | Estado |
|---|---|
| **Fase 1 — Pista A** (motor empírico) | 🟡 En desarrollo activo — mecánica completa y validada; fuente de datos climáticos en revisión |
| **Fase 1 — Pista B** (motor físico DMST + CFD) | ⚪ No iniciada |
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

⚪ **No iniciada.** Recordatorio de los 4 pasos del plan (sección 3):

1. DMST (Paraschivoiu) para turbina aislada, usando la geometría de las patentes
   CA2800765C/US9255567B2 y ES2970155T3 (NACA 0018 para el componente de sustentación).
2. Pérdida dinámica a TSR bajo (Leishman-Beddoes).
3. Efecto clúster vía Cilindro Actuador (RANS-AC, OpenFOAM, offline/batch).
4. Estructural (ASCE 7, con los Cd de pala ya conocidos: 1.2 convexa / 2.3 cóncava).

Acordado con Pablo: se arranca Pista B solo después de que la Pista A esté sólida
(secuencial, no en paralelo — recomendación del plan, confirmada).

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
      valores distintos y habría que decidir cuál aplica a cada sitio real.
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
