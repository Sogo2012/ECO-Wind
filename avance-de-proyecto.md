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
repo. Este patrón ya se usó con éxito para el EPW (`datos_clima/`) y es el que se va a
repetir para el Global Wind Atlas y, eventualmente, ERA5.

---

## 4. Fuentes de datos climáticos — estado comparativo

| Fuente | Resolución | Acceso desde este sandbox | Estado en el proyecto |
|---|---|---|---|
| NASA POWER (MERRA-2) | ~50-60 km | ❌ Bloqueado | Implementado, con sesgo confirmado y documentado. Solo respaldo. |
| EPW / estación real (ISD + ERA5 gap-fill) | Puntual (estación) | N/A — archivo local | ✅ Implementado y validado. Fuente primaria cuando existe estación cercana. |
| Global Wind Atlas (Weibull A/k, downscaling WAsP a 250m) | 250 m | ❌ Bloqueado | Código listo, **esperando A/k reales del sitio** (pendiente, sección 6) |
| ERA5 + bias correction (Copernicus CDS) | ~31 km + corrección | ❌ Bloqueado | No implementado. Necesita cuenta/API key de Copernicus. |

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

- [ ] **Conseguir A/k reales del Global Wind Atlas** para el aeropuerto Juan Santamaría
      (Pablo compartió el link del punto en el mapa; el sitio está bloqueado desde este
      sandbox, hace falta leer los valores manualmente desde la web o desde Colab).
- [ ] Decidir si se implementa la Pista C (ERA5 + quantile mapping) ahora o se pospone hasta
      que haga falta estructura horaria real.
- [ ] Confirmar si el sesgo de NASA POWER (~3x) se sostiene en otros puntos del Valle
      Central, o fue específico de esta coordenada.
- [ ] Conseguir EPWs de los sitios reales de proyectos según se vayan definiendo.
- [ ] Sensibilizar `z0` (rugosidad de superficie) — se usó 0.3 como default ilustrativo en
      toda la validación hecha hasta ahora.
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
