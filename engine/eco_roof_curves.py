"""
Curvas de potencia oficiales del Eco-Roof Energy Hub (Small Tulip, 1m) -- Pista
Eco-Roof, módulo nuevo y separado del motor de 3-M Tulip (engine/flower_turbines_curves.py).

ORIGEN DE LOS DATOS: documentación oficial de Flower Turbines específica de este
producto ("Flat Eco-Roof Quick Start Guide" y "Specs_2025") -- tablas de potencia
REALES por turbina, medidas en campo para el bouquet completo (N=3 y N=5), no una
fórmula genérica. Se transcriben tal cual, sin suavizar ni reajustar a una curva
continua.

POR QUÉ NO SE USA power_in_bouquet()/CURVE_COEFFICIENTS DE flower_turbines_curves.py:
el multiplicador de Efecto Bouquet ahí (M(N) = e^(0.21103×(N-1))) se calibró contra
la línea 2M/3M/6M de Flower Turbines -- es un ajuste empírico propio de ESA línea de
producto, no una constante física universal. Estas tablas del Eco-Roof (Small Tulip)
ya traen el Efecto Bouquet de su propio N implícito en los valores medidos -- aplicar
además el multiplicador universal sería contarlo dos veces, y con el multiplicador
equivocado. Por eso este módulo interpola tabla-a-tabla, sin ningún `k` ni `M(N)`.
"""
import numpy as np

# Watts POR TURBINA (ya con el Efecto Bouquet de ESE N implícito en el dato medido),
# pasos de 0.5 m/s, 0.0 a 15.0 m/s. Bouquet de 3 turbinas Small Tulip -- eco_roof_1m_3_*.
TABLA_N3 = {
    0.0: 0.0, 0.5: 0.0, 1.0: 0.1, 1.5: 0.2, 2.0: 0.5, 2.5: 1.0, 3.0: 1.7, 3.5: 2.7, 4.0: 4.0,
    4.5: 5.7, 5.0: 7.9, 5.5: 10.5, 6.0: 13.6, 6.5: 17.3, 7.0: 21.6, 7.5: 26.6, 8.0: 32.3,
    8.5: 38.7, 9.0: 45.9, 9.5: 54.0, 10.0: 63.0, 10.5: 72.9, 11.0: 83.9, 11.5: 95.8,
    12.0: 108.9, 12.5: 123.0, 13.0: 138.4, 13.5: 155.0, 14.0: 172.9, 14.5: 192.1, 15.0: 212.6,
}

# Bouquet de 5 turbinas Small Tulip -- eco_roof_1m_5_*.
TABLA_N5 = {
    0.0: 0.0, 0.5: 0.0, 1.0: 0.1, 1.5: 0.3, 2.0: 0.7, 2.5: 1.3, 3.0: 2.2, 3.5: 3.5, 4.0: 5.3,
    4.5: 7.5, 5.0: 10.3, 5.5: 13.7, 6.0: 17.7, 6.5: 22.5, 7.0: 28.2, 7.5: 34.6, 8.0: 42.0,
    8.5: 50.4, 9.0: 59.8, 9.5: 70.4, 10.0: 82.1, 10.5: 95.0, 11.0: 109.2, 11.5: 124.8,
    12.0: 141.8, 12.5: 160.3, 13.0: 180.3, 13.5: 201.9, 14.0: 225.2, 14.5: 250.2, 15.0: 277.0,
}

# Incluida por completitud aunque hoy ningún producto Eco-Roof usa N=10 -- ver
# docstring del prompt original: útil si en el futuro se modela la unión de dos
# módulos de 5 turbinas. No referenciada por ningún preset en eco_roof_catalog.py.
TABLA_N10 = {
    0.0: 0.0, 0.5: 0.0, 1.0: 0.2, 1.5: 0.5, 2.0: 1.3, 2.5: 2.5, 3.0: 4.4, 3.5: 6.9, 4.0: 10.4,
    4.5: 14.8, 5.0: 20.3, 5.5: 27.0, 6.0: 35.0, 6.5: 44.5, 7.0: 55.6, 7.5: 68.3, 8.0: 82.9,
    8.5: 99.5, 9.0: 118.1, 9.5: 138.9, 10.0: 162.0, 10.5: 187.5, 11.0: 215.6, 11.5: 246.4,
    12.0: 279.9, 12.5: 316.4, 13.0: 355.9, 13.5: 398.6, 14.0: 444.5, 14.5: 493.9, 15.0: 546.8,
}

TABLAS_POR_N = {3: TABLA_N3, 5: TABLA_N5, 10: TABLA_N10}


def potencia_tabla_w(v_ms, tabla):
    """
    Interpolación LINEAL entre los puntos dados de la tabla oficial -- no se
    ajusta ninguna curva continua encima. Velocidades fuera de 0-15 m/s usan el
    valor del extremo más cercano (sin extrapolar la pendiente): np.interp ya
    hace exactamente esto por default (clampea a fp[0]/fp[-1] fuera del rango
    de xp), así que no hace falta lógica de clamp aparte.

    v_ms: escalar o arreglo (velocidad de viento en el buje, m/s).
    tabla: uno de TABLA_N3/TABLA_N5/TABLA_N10 (o cualquier dict velocidad->W
    con el mismo formato).

    Devuelve W por turbina (float si v_ms es escalar, ndarray si es arreglo).
    """
    velocidades = np.array(sorted(tabla.keys()))
    potencias = np.array([tabla[v] for v in velocidades])
    escalar = np.isscalar(v_ms) or (hasattr(v_ms, "ndim") and np.ndim(v_ms) == 0)
    resultado = np.interp(np.asarray(v_ms, dtype=float), velocidades, potencias)
    return float(resultado) if escalar else resultado
