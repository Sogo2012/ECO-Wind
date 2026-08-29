# INFORME TÉCNICO Y PLAN DE DESARROLLO
## Simulador Web de Microgeneración Eólica Urbana (Flower Turbines)

**Documento:** DT-FT-SIM-2026-01  
**Dirigido a:** Equipo de Desarrollo de Software, Ingenieros de Proyectos e Inversionistas  
**Estado:** Especificación Técnica y Arquitectura de Software  

---

### 1. RESUMEN EJECUTIVO Y OBJETIVOS

El presente informe establece las especificaciones funcionales, la arquitectura de software y el motor matemático para el desarrollo de una aplicación web interactiva destinada a simular el comportamiento de turbinas eólicas de eje vertical (VAWT) en entornos urbanos y techos de edificios.

La aplicación tiene como objetivo principal resolver la incertidumbre técnica de arquitectos, ingenieros eléctricos y desarrolladores inmobiliarios al dimensionar proyectos de microgeneración eólica, permitiendo:
1. Determinar el número óptimo de turbinas instalables en una longitud o superficie determinada.
2. Modelar el **Efecto Bouquet™ (Cluster Effect)**, una innovación aerodinámica patentada en la que turbinas adyacentes canalizan el viento creando un efecto túnel que incrementa el rendimiento del sistema entre un **20% y más del 200%**.
3. Interpolar la producción energética instantánea y acumulada (kWh/mes y kWh/año) a partir del recurso eólico local.
4. Entregar un análisis financiero preliminar (ahorro en factura eléctrica y periodo de retorno de inversión - ROI).

---

### 2. BASE DE CONOCIMIENTO TÉCNICO (CATÁLOGO OFICIAL)

El motor de cálculo opera sobre los parámetros oficiales de la familia de productos Flower Turbines:

| Parámetro | Small Tulip | Medium Tulip | 3-M Tulip | Large Tulip | AL13 Power Tower™ |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Potencia Nominal** | 100 W | 500 W | 1,000 W (1 kW) | 5,000 W (5 kW) | 500 W – 10 kW (Modular) |
| **Velocidad Arranque (Cut-in)** | 1.2 m/s (hasta 0.7 m/s) | 0.7 m/s | 0.7 m/s | 0.7 m/s (o 1.2 m/s) | 0.7 m/s |
| **Velocidad Máxima (Cut-out)** | 54.0 m/s | 54.0 m/s | 54.0 m/s | 54.0 m/s | 54.0 m/s |
| **Diámetro / Ancho ($D$)** | 0.55 m | 1.18 m | 1.80 m | 2.40 m | 0.545 m |
| **Altura Total** | 1.4 m – 2.0 m | 2.9 m – 3.0 m | 4.07 m | 6.00 m | Modular (2.6 m base) |
| **Material de Palas** | Termoplástico | Termoplástico | Termoplástico | Termoplástico | Aluminio Anodizado |
| **Vida Útil de Diseño** | 40 años | 40 años | 40 años | 20 años | 20 años |

---

### 3. FORMULACIÓN MATEMÁTICA Y REGLAS DE INGENIERÍA

#### A. Espaciamiento Físico y Capacidad Lineal
Las turbinas tradicionales de eje horizontal (HAWT) requieren de 5 a 10 diámetros de separación para evitar pérdidas por estela turbulenta. En contraste, las Flower Turbines aprovechan el viento de proximidad.
* **Distancia entre ejes ($S$):** Se define como $S = 1.25 \times D$ (rango permisible de $1.1 \times D$ a $1.3 \times D$).
* **Fórmula de Capacidad en Longitud Lineal ($L$):**
  Dado que la primera turbina ocupa un radio hacia el inicio y la última ocupa un radio al final, la longitud mínima para $N$ turbinas en línea es:
  $$L_{min} = D + (N - 1) \times S = D + (N - 1) \times 1.25 \times D$$
  Despejando el número máximo de turbinas enteras que caben en un espacio $L$:
  $$N = \left\lfloor \frac{L - D}{1.25 \times D} \right\rfloor + 1 \quad (\text{para } L \ge D)$$

#### B. Factor Multiplicador del Efecto Bouquet™ ($M_{cluster}$)
Cuando las turbinas operan en proximidad estrecha, la aceleración del flujo entre los perfiles genera una ganancia neta de potencia:
* $N = 1$ (Aislada): Multiplicador base = $1.00$ ($100\%$ de la curva individual).
* $N = 2$: Multiplicador = $1.20$ a $1.35$ ($+20\%$ a $+35\%$ por unidad).
* $N = 3 \text{ a } 4$: Multiplicador = $1.50$ a $2.00$ (4 turbinas en clúster generan la energía de 8 unidades separadas).
* $N \ge 5$: Multiplicador = $2.28$ (5 turbinas en clúster generan un $+228\%$ frente a 5 turbinas individuales aisladas).

#### C. Extrapolación de Energía Mensual y Anual (kWh)
A partir de la velocidad media del viento mensual $\bar{v}_m$ (m/s), la potencia total instantánea del sistema es:
$$P_{total}(v) = P_{curva}(v) \times N \times M_{cluster}(N)$$
La producción mensual de energía ($E_m$) en kilovatios-hora considera las horas del mes ($H_m \approx 720 \text{ h}$ o $744 \text{ h}$):
$$E_m = \frac{P_{total}(\bar{v}_m) \times H_m}{1000} \quad [\text{kWh}]$$
La energía anual estimada es la suma de los 12 meses:
$$E_{anual} = \sum_{m=1}^{12} E_m$$

---

### 4. ARQUITECTURA DE SOFTWARE RECOMENDADA

La aplicación se estructurará en tres capas desacopladas:
1. **Presentation Layer (Frontend):** Next.js (React) + Tailwind CSS + Three.js / Canvas 2D para la simulación visual de azoteas y vectores de flujo eólico.
2. **Business & Simulation Engine:** Módulo puro en TypeScript/JavaScript ejecutable tanto en cliente como en microservicios backend.
3. **Data Integration Layer:** Conexión con APIs meteorológicas abiertas (*Open-Meteo* o *Global Wind Atlas*) para autocompletar la velocidad de viento promedio local por coordenadas GPS.

---

### 5. CÓDIGO FUENTE COMPLETO DEL MOTOR DE CÁLCULO (JavaScript / TypeScript)

El siguiente módulo implementa la lógica completa de simulación, parametrización y cálculo financiero:

```javascript
/**
 * Flower Turbines - Urban Wind Simulation Engine
 * Archivo: FlowerTurbinesSimulator.js
 * Compatible con Node.js, navegadores web y entornos TypeScript.
 */

// 1. Catálogo Técnico y Curvas de Potencia Base (Watts a velocidades de viento en m/s)
export const TURBINE_CATALOG = {
  small_tulip: {
    id: "small_tulip",
    name: "Small Tulip",
    nominalPowerW: 100,
    rotorDiameterM: 0.55,
    heightM: 1.4,
    weightKg: 20,
    cutInSpeedMs: 1.2,
    cutOutSpeedMs: 54.0,
    designLifeYears: 40,
    bladeMaterial: "Termoplástico",
    // Curva de potencia base unitaria (Watts generados por velocidad m/s)
    powerCurve: {
      0: 0, 1: 0, 2: 4, 3: 12, 4: 25, 5: 48, 6: 80, 7: 100, 8: 100, 9: 100, 10: 100
    }
  },
  medium_tulip: {
    id: "medium_tulip",
    name: "Medium Tulip",
    nominalPowerW: 500,
    rotorDiameterM: 1.18,
    heightM: 2.92,
    weightKg: 200,
    cutInSpeedMs: 0.7,
    cutOutSpeedMs: 54.0,
    designLifeYears: 40,
    bladeMaterial: "Termoplástico",
    powerCurve: {
      0: 0, 1: 5, 2: 25, 3: 65, 4: 140, 5: 260, 6: 420, 7: 500, 8: 500, 9: 500, 10: 500
    }
  },
  three_m_tulip: {
    id: "three_m_tulip",
    name: "3-M Tulip",
    nominalPowerW: 1000,
    rotorDiameterM: 1.80,
    heightM: 4.07,
    weightKg: 400,
    cutInSpeedMs: 0.7,
    cutOutSpeedMs: 54.0,
    designLifeYears: 40,
    bladeMaterial: "Termoplástico",
    powerCurve: {
      0: 0, 1: 10, 2: 50, 3: 130, 4: 280, 5: 520, 6: 840, 7: 1000, 8: 1000, 9: 1000, 10: 1000
    }
  },
  large_tulip: {
    id: "large_tulip",
    name: "Large Tulip",
    nominalPowerW: 5000,
    rotorDiameterM: 2.40,
    heightM: 6.00,
    weightKg: 1000,
    cutInSpeedMs: 0.7,
    cutOutSpeedMs: 54.0,
    designLifeYears: 20,
    bladeMaterial: "Termoplástico",
    powerCurve: {
      0: 0, 1: 50, 2: 250, 3: 650, 4: 1400, 5: 2600, 6: 4200, 7: 5000, 8: 5000, 9: 5000, 10: 5000
    }
  },
  al13_power_tower: {
    id: "al13_power_tower",
    name: "AL13 Power Tower™ (4 Módulos)",
    nominalPowerW: 2000,
    rotorDiameterM: 0.545,
    heightM: 2.62,
    weightKg: 431,
    cutInSpeedMs: 0.7,
    cutOutSpeedMs: 54.0,
    designLifeYears: 20,
    bladeMaterial: "Aluminio Anodizado",
    powerCurve: {
      0: 0, 1: 20, 2: 100, 3: 260, 4: 560, 5: 1040, 6: 1680, 7: 2000, 8: 2000, 9: 2000, 10: 2000
    }
  }
};

/**
 * 2. Cálculo de Espaciamiento y Distribución en Línea
 */
export function calculatePlacement(lengthMeters, modelKey) {
  const model = TURBINE_CATALOG[modelKey];
  if (!model) throw new Error(`Modelo no encontrado: ${modelKey}`);

  const D = model.rotorDiameterM;
  const optimalSpacingM = D * 1.25; // Distancia de centro de eje a centro de eje

  if (lengthMeters < D) {
    return {
      maxTurbines: 0,
      optimalSpacingM,
      totalLengthRequiredM: 0,
      fitsInLength: false
    };
  }

  // Número de turbinas que caben físicamente
  const maxTurbines = Math.floor((lengthMeters - D) / optimalSpacingM) + 1;
  const totalLengthRequiredM = D + (maxTurbines - 1) * optimalSpacingM;

  return {
    maxTurbines,
    optimalSpacingM: Number(optimalSpacingM.toFixed(3)),
    totalLengthRequiredM: Number(totalLengthRequiredM.toFixed(3)),
    fitsInLength: true
  };
}

/**
 * 3. Cálculo del Multiplicador por Efecto Bouquet™
 */
export function getBouquetMultiplier(turbinesCount) {
  if (turbinesCount <= 0) return 0;
  if (turbinesCount === 1) return 1.0;       // 1 turbina sola: sin efecto túnel
  if (turbinesCount === 2) return 1.25;      // 2 turbinas: +25% de eficiencia promedio
  if (turbinesCount <= 4) return 2.00;       // 3-4 turbinas: el doble de energía por unidad
  return 2.28;                              // 5 o más turbinas: +228% documentado
}

/**
 * 4. Interpolación Lineal de la Curva de Potencia Base
 */
export function getUnitPowerWatts(modelKey, windSpeedMs) {
  const model = TURBINE_CATALOG[modelKey];
  if (!model) return 0;

  if (windSpeedMs < model.cutInSpeedMs || windSpeedMs > model.cutOutSpeedMs) {
    return 0;
  }

  const speedFloor = Math.floor(windSpeedMs);
  const speedCeil = Math.ceil(windSpeedMs);

  const powerFloor = model.powerCurve[speedFloor] ?? model.nominalPowerW;
  const powerCeil = model.powerCurve[speedCeil] ?? model.nominalPowerW;

  if (speedFloor === speedCeil) return powerFloor;

  // Interpolación entre escalones de velocidad
  const fraction = windSpeedMs - speedFloor;
  return powerFloor + fraction * (powerCeil - powerFloor);
}

/**
 * 5. Simulación Anual y Análisis Financiero Completo
 */
export function runSimulation({
  modelKey,
  availableLengthMeters,
  monthlyWindSpeedsMs, // Array de 12 valores numéricos (uno por cada mes)
  electricityRatePerKwh = 0.18, // Tarifa local en USD o moneda local por kWh
  estimatedCostPerTurbineUSD = 3500 // Costo estimado de inversión (CAPEX)
}) {
  const placement = calculatePlacement(availableLengthMeters, modelKey);
  const count = placement.maxTurbines;

  if (count === 0) {
    return {
      success: false,
      message: "El espacio disponible es menor al diámetro físico de una sola turbina."
    };
  }

  const bouquetMultiplier = getBouquetMultiplier(count);
  const monthHours = [744, 672, 744, 720, 744, 720, 744, 744, 720, 744, 720, 744]; // Horas estándar por mes
  const monthNames = [
    "Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio",
    "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"
  ];

  let totalAnnualKwh = 0;
  const monthlyResults = [];

  for (let m = 0; m < 12; m++) {
    const windSpeed = monthlyWindSpeedsMs[m] || 0;
    const unitWatts = getUnitPowerWatts(modelKey, windSpeed);
    
    // Potencia del clúster aplicando el Efecto Bouquet
    const totalClusterWatts = unitWatts * count * bouquetMultiplier;
    
    // Generación mensual en kWh
    const monthlyKwh = (totalClusterWatts * monthHours[m]) / 1000;
    totalAnnualKwh += monthlyKwh;

    monthlyResults.push({
      month: monthNames[m],
      averageWindMs: windSpeed,
      unitPowerWatts: Number(unitWatts.toFixed(1)),
      clusterPowerWatts: Number(totalClusterWatts.toFixed(1)),
      generationKwh: Number(monthlyKwh.toFixed(1)),
      economicSavingsUSD: Number((monthlyKwh * electricityRatePerKwh).toFixed(2))
    });
  }

  const annualSavingsUSD = totalAnnualKwh * electricityRatePerKwh;
  const totalInvestmentCAPEX = count * estimatedCostPerTurbineUSD;
  const simpleRoiYears = annualSavingsUSD > 0 
    ? Number((totalInvestmentCAPEX / annualSavingsUSD).toFixed(1)) 
    : Infinity;

  // Validación de capacidad de inversor de red recomendado (5 kW mínimo estándar americano)
  const totalNominalCapacityKw = (TURBINE_CATALOG[modelKey].nominalPowerW * count) / 1000;
  const meetsStandard5KwInverter = totalNominalCapacityKw >= 5.0;

  return {
    success: true,
    modelDetails: TURBINE_CATALOG[modelKey],
    layout: {
      lengthAvailableM: availableLengthMeters,
      turbinesInstalled: count,
      optimalSpacingM: placement.optimalSpacingM,
      totalLengthOccupiedM: placement.totalLengthRequiredM,
      bouquetEfficiencyBonusPercent: Number(((bouquetMultiplier - 1) * 100).toFixed(0))
    },
    electricalProfile: {
      totalNominalCapacityKw: Number(totalNominalCapacityKw.toFixed(2)),
      meetsStandard5KwInverter,
      gridTieRecommendation: meetsStandard5KwInverter 
        ? "Apto para inversor central estándar de 5 kW" 
        : "Requiere microinversores dedicados o agregar más unidades"
    },
    energyGeneration: {
      totalAnnualKwh: Number(totalAnnualKwh.toFixed(1)),
      monthlyBreakdown: monthlyResults
    },
    financialAnalysis: {
      totalInvestmentUSD: totalInvestmentCAPEX,
      annualSavingsUSD: Number(annualSavingsUSD.toFixed(2)),
      simplePaybackPeriodYears: simpleRoiYears
    }
  };
}
```

---

### 6. PLAN DE TRABAJO Y ENTREGABLES (SPRINT ROADMAP)

* **Sprint 1 (Semanas 1-2): Core Engine & Unit Tests**
  * Empaquetado del módulo matemático en una librería NPM interna.
  * Pruebas unitarias de bordes (espacios reducidos, vientos cero, velocidades de corte).
* **Sprint 2 (Semanas 3-4): Interfaz Gráfica (UI) y Controles Dinámicos**
  * Implementación de la vista de diseño: sliders para longitud y viento, selector visual de turbinas.
  * Gráficas reactivas de generación mensual con Chart.js o Recharts.
* **Sprint 3 (Semanas 5-6): Visualizador 2D de Azotea y Efecto Bouquet**
  * Canvas dinámico que renderiza las turbinas a escala y colorea el flujo de viento entre ellas para evidenciar la aceleración del Efecto Bouquet.
* **Sprint 4 (Semanas 7-8): Exportación Ejecutiva y Presupuestador**
  * Generador automático de cotizaciones en PDF con especificaciones, plano y retorno de inversión para el cliente final.

---

### 7. CONCLUSIÓN Y RECOMENDACIÓN TÉCNICA

El simulador proporciona una herramienta de venta y dimensionamiento de alta fidelidad. Al modelar con precisión matemática la ganancia del **Efecto Bouquet™**, los clientes podrán constatar de inmediato por qué un clúster de unidades compactas supera en rendimiento y estética a soluciones eólicas convencionales en azoteas y entornos corporativos.
