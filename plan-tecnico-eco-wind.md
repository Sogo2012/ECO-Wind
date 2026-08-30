# ECO | Wind — Plan Técnico de Desarrollo

**Repositorio:** github.com/Sogo2012/ECO-Wind
**Para:** Claude Code (implementación) — dirigido por Pablo / ECO Consultor
**Objetivo final:** SaaS de dimensionamiento y venta consultiva de clústeres Flower Turbines (mismo patrón que Skyplus y DDP-Lite), empezando por un sandbox de validación física en Colab.

---

## 1. Qué estamos construyendo

Un simulador de microgeneración eólica urbana para turbinas de eje vertical Flower Turbines, que:

1. Toma una coordenada + una configuración de clúster (modelo, N turbinas, altura de buje) y entrega producción horaria/mensual/anual estimada.
2. Modela con precisión el **Efecto Bouquet** (la ventaja competitiva central de Flower Turbines).
3. Eventualmente entrega un análisis financiero (ahorro, ROI) y una cotización en PDF — la misma función comercial que Skyplus cumple para Sunoptics.

Dos fases, en el orden que ya definiste:

- **Fase 1 (ahora):** sandbox en Colab — validar el motor físico/de datos, sin preocuparnos de interfaz ni despliegue.
- **Fase 2 (después):** Streamlit + Docker + Cloud Build, replicando la arquitectura de Skyplus/DDP-Lite (Cloud Run Service para la interfaz + Cloud Run Job para lo pesado).

No hay nada que cambiar en esa secuencia — es la correcta y la que ya te ha funcionado dos veces. Lo que sí propongo es cómo **subdividir la Fase 1**, porque "probar los motores de clima y de CFD" junto son dos tareas de madurez muy distinta, y separarlas te da algo útil mucho más rápido.

---

## 2. Estado actual — lo que ya no hay que investigar

Esto ya está resuelto y validado contra fuentes primarias; Claude Code debe partir de aquí, no repetir el trabajo:

- **Curva individual por modelo:** P(v) = k·v³, exacta (R²=1.00000) para Small/Medium/Large Tulip, contra la tabla oficial de 31 puntos. 3-M Tulip con un punto de anclaje. AL13 aproximado (confianza media). Todo esto vive en `flower_turbines_curves.py` (adjunto en `documentos de referencia/`).
- **Multiplicador de Efecto Bouquet:** M(N) = e^(0.21103·(N−1)) — exponencial, no lineal, **igual para los tres tamaños de turbina**, y constante en todo el rango 0–15 m/s (R²=1.000000, validado contra el calculador oficial de Flower Turbines para N=1 a 10). Misma fuente.
- **Catálogo real de dimensiones/specs** (diámetros, cut-in 0.7 m/s en todos los modelos, velocidad máx. de supervivencia por modelo —no es uniforme, va de 40 a 54 m/s—, vida útil, clase IEC) — en las fichas técnicas de `documentos de referencia/Specs & Brochures/`. Diámetros de Large (2.5 m) y AL13 (1.7 m) confirmados por tres fuentes independientes.
- **Regla oficial de espaciamiento** (documento "Turbine Diameters", Flower Turbines): separación entre bordes de turbinas entre 10% y 30% del diámetro — equivalente a 1.10D–1.30D centro a centro, coincide con lo estimado antes por otra vía.
- **Advertencia sobre el tipo de rotor:** el corte CAD de la pala (curvo, tipo media luna) y la descripción de su propia simulación CFD ("el viento entra y revierte dirección para golpear la segunda pala") sugieren un perfil **cambrado**, posiblemente con comportamiento híbrido sustentación-arrastre — no un perfil simétrico delgado tipo Darrieus clásico. Ver nota en la Pista B.
- **Coeficientes de arrastre de pala** (Cd=1.2 convexa, 2.3 cóncava) y algunas fuerzas de referencia (Frotor/Fbase a 30 y 42 m/s para modelos de 3m y 6m) — en `External Load Calculations 2m & 5m.pdf`.
- **Factibilidad del pipeline climático:** confirmado que la API Hourly de NASA POWER puede entregar un EPW completo por coordenada arbitraria (`community=SB`, `format=EPW`), sin necesitar un EPW base preexistente ni pasar por UWG si solo interesa el viento.
- **Brecha pendiente, ya identificada:** las curvas de arriba son el modelo de catálogo/teórico de Flower Turbines. Las gráficas de dispersión reales que compartiste (3,064 puntos de la Medium; la de dos Small) muestran que el campo real cae algo por debajo y con más ruido. Ese factor de calibración K(v) sigue sin resolver — necesita el CSV/hoja de cálculo detrás de esas gráficas, no solo la imagen.

---

## 3. Fase 1 — Sandbox en Colab, en dos pistas

### Pista A — Motor empírico (primero, porque ya tiene datos reales)

Objetivo: un pipeline completo y funcional lo antes posible, usando el catálogo ya validado. Esto es lo que te da "algo útil" para pasar a Fase 2 sin esperar a que la Pista B esté lista.

1. Empaquetar `flower_turbines_curves.py` como el módulo base del notebook.
2. Ingesta climática: pull de NASA POWER Hourly (point, `community=SB`) para una coordenada real de prueba (sugiero una del Valle Central, ya que ahí vivirán la mayoría de tus proyectos). Validar que se pueden armar las 8,760 horas del año.
3. Corrección de altura: perfil logarítmico simple (z0/rugosidad, altura de buje) para pasar de viento macro (NASA POWER) a viento a la altura real de la turbina — sin necesidad de UWG completo en esta pista.
4. Ensamblar: coordenada + altura de buje + modelo de turbina + N → serie horaria de potencia por turbina → kWh mes/año, usando P(v)=k·v³ × M(N).
5. Sanity check contra referencias de otros mercados (ej. Kilowatts UK cita 1,000–5,000 kWh/año típico para turbinas pequeñas en Reino Unido) — no para copiar el número, sino para confirmar que el orden de magnitud del resultado en Costa Rica tiene sentido.

Al final de la Pista A tienes una función `simular(lat, lon, altura_buje, modelo, N) -> kWh_anual` completamente trazable a fuentes oficiales. Eso ya es un MVP defendible.

### Pista B — Motor físico DMST + CFD (en paralelo o inmediatamente después)

Objetivo: generalizar más allá de lo que el catálogo de Flower Turbines cubre — layouts no lineales, espaciamientos no estándar, mezclas de modelos, direccionalidad del viento — y eventualmente explicar *por qué* funciona la curva exponencial de la Pista A.

1. DMST (Paraschivoiu) para la turbina aislada — **Resuelto con patentes de Flower Turbines, no con sustituto genérico.** La patente CA2800765C/US9255567B2 (2010) confirma que el diseño es un híbrido arrastre (tipo Savonius, pala de doble curva) + sustentación, y da la receta del componente de sustentación: perfil **NACA 0018 simétrico**, CTDR (cuerda/diámetro) de 0.25–0.45 para 2 palas, TSR de diseño ≈1 (velocidad de punta = velocidad del viento) para el componente de arrastre. La patente más reciente **ES2970155T3 "Savonius Wind Turbine" (prioridad 2018, otorgada 2024)** da la geometría exacta del componente de arrastre: distancia entre bordes internos = 3.5×diámetro del eje, superposición = 0.2×diámetro del eje, cuerda = 6.6×diámetro del eje, diámetro total = 9.7×diámetro del eje, con Cp=0.34 reportado y TSR óptimo ≈0.5 (escala con el diámetro del eje). Con esto, la Pista B parte de proporciones patentadas y su propio Cp de referencia, no de un perfil sustituto de la literatura — el DMST solo hace falta para el componente de sustentación (NACA 0018), y el componente de arrastre se modela con las relaciones geométricas de esta patente en vez de con teoría de perfil aerodinámico. El CFD sigue siendo valioso para validar la interacción entre ambos componentes y el efecto clúster.
2. Pérdida dinámica a TSR bajo (Leishman-Beddoes, EDOs vía `scipy.integrate`).
3. Efecto clúster vía modelo de Cilindro Actuador (RANS-AC en OpenFOAM) — **uso exclusivamente offline/batch**, nunca en tiempo real. Su función aquí es calibrar el factor de aceleración para configuraciones que el M(N) de la Pista A no cubre (el M(N) que ya tenemos es válido para "N turbinas en bouquet estándar"; no sabemos si aplica igual a un arreglo 2D o a espaciamientos no estándar).
4. Estructural: ASCE 7 (velocidad de presión con Kz/Kzt/Kd/Ke, corte basal, resonancia por desprendimiento de vórtices/Strouhal) usando los Cd de pala que ya tenemos. Nota: Ke (factor de elevación) importa para Costa Rica por la altitud del Valle Central.

---

## 4. Variables a explorar en el camino

Lista abierta — cosas que la Pista A/B van a ir resolviendo sobre la marcha, no bloqueantes para arrancar:

- Calibración K(v): catálogo teórico vs. dato de campo real (pendiente el CSV de las gráficas de dispersión).
- ¿El M(N) exponencial se sostiene más allá de N=10? (no hay dato del calculador ahí).
- ¿El mismo M(N) aplica a layouts 2D/no lineales, o solo a "N turbinas en bouquet" genérico como lo mide el calculador?
- Fuente climática: NASA POWER (ya validado, resolución ~50-60 km) vs. estaciones del IMN Costa Rica (posible mejor resolución local, no explorado aún).
- Curvas del AL13 (hoy son lectura aproximada de gráfica, no tabla exacta).

---

## 5. Fase 2 — Productización (cuando la Pista A esté sólida)

Réplica directa del patrón de Skyplus/DDP-Lite — no hay que reinventar nada aquí:

- Frontend Streamlit.
- Cloud Run Service (interfaz + Pista A, que es rápida) + Cloud Run Job (Pista B/estructural/PDF, si aplica, igual que el job de EnergyPlus de Skyplus).
- Docker + Cloud Build, dominio propio bajo ecoconsultor.com.
- Paleta corporativa ECO ya definida (azul #003C52, verde #4A7C2F, gris #4A5568, fondo #E8F0F3).
- Flujo de UX de referencia (visto en Kilowatts UK, el distribuidor de Reino Unido): coordenada → confirmar ubicación en mapa → armar el layout (permite varios bouquets independientes por sitio, no solo uno; altura de buje como input explícito) → pronóstico instantáneo (velocidad promedio, generación anual, densidad de aire, elevación) → datos de contacto → PDF descargable.
- Registro de leads: a definir (Google Sheets como Skyplus, o Airtable como DDP-Lite).

---

## 6. Estructura de repositorio propuesta

```
ECO-Wind/
├── documentos de referencia/     (ya existe — investigación, fichas, este plan)
├── notebooks/                    (sandbox de Colab, Pista A y Pista B por separado)
├── engine/                       (flower_turbines_curves.py y lo que se derive)
└── app/                          (Fase 2: Streamlit + Dockerfile + cloudbuild.yaml)
```

---

## 7. Decisiones abiertas para vos y Claude Code

- Confirmar orden Pista A → Pista B (mi recomendación) vs. hacerlas en paralelo.
- Registro de leads: Sheets o Airtable.
