"""
Curvas de potencia — Flower Turbines
=====================================
Ecuaciones extraídas por ingenieria inversa (ajuste numerico con
scipy.optimize.curve_fit) a partir de datos oficiales de Flower Turbines
compartidos por Pablo: tablas/graficas de Drive, y capturas del
calculador en linea oficial (bouquet-effect-calculator) para N=1 a 10.

FUENTES Y NIVEL DE CONFIANZA
----------------------------
1) Small / Medium / Large Tulip (turbina AISLADA) -> tabla oficial
   "Individual Output In Watts Per Hour", 31 puntos exactos de 0 a 15 m/s.
   Ajuste: P(v) = k * v^3  ->  R^2 = 1.00000 en los TRES modelos.
   Confianza: ALTA.

2) AL13 Power Tower -> leido aproximadamente de curvas suaves de un PDF
   (no hay tabla numerica publicada para este modelo).
   Confianza: MEDIA (lectura visual, no una tabla).

3) Multiplicador de Efecto Bouquet -> calculado directamente del
   calculador oficial de Flower Turbines, con la tabla COMPLETA de
   N=1 a N=10 en TODO el rango 0-15 m/s (matriz preparada por Pablo/
   Gemini a partir de las 10 corridas del calculador, verificada punto
   por punto contra capturas de pantalla independientes de N=10 — los
   16 valores de 0 a 15 m/s coinciden exactos). Resultado: es una curva
   EXPONENCIAL, NO lineal, y es la MISMA para los tres tamaños de
   turbina, Y ES CONSTANTE EN TODO EL RANGO DE VIENTO (no varía con v):

       M(N) = exp(0.21103 * (N-1))     R^2 = 1.000000

   (validado con 39 puntos por cada N, v=3 a 15 m/s, 3 modelos —
   desviación estándar < 0.03 en el peor caso, puro redondeo del
   calculador a 1 decimal, sin tendencia con la velocidad).

   Esto reemplaza el intento anterior (un multiplicador distinto por
   modelo, anclado a un solo punto de cada ficha técnica en PDF): ese
   anclaje resultó tener una errata real — la ficha del Medium Tulip
   decía "bouquet de 5 ≈ 1,147 W a 12 m/s", pero el dato correcto del
   calculador en ese mismo punto es 1,447.2 W (dígitos transpuestos en
   la ficha de marketing). Con el valor correcto, Medium encaja
   perfecto en la misma curva universal que Small y Large.

   El calculador mismo advierte: "figures ... based on field testing of
   up to 5 turbines. Any numbers thereafter are projections" — N=2 a 5
   son medición de campo real, N=6 a 10 son la proyección de Flower
   Turbines, y ambos tramos siguen la MISMA curva exponencial sin
   quiebre visible en N=5->6.

   Confianza: ALTA, validado en todo el rango 0-15 m/s.

BRECHA PENDIENTE (para la calibración real vs. campo)
-------------------------------------------------------
Las gráficas de dispersión de datos reales (Power_Curve_of_Medium_
Turbine.png, 3064 puntos; Power_Curve_of_Two_Small_Turbines.png)
muestran una nube más ruidosa y, en su masa central, algo por debajo de
la curva ideal P=k*v^3. Esa diferencia sigue siendo el factor de
calibración K(v) pendiente — estas ecuaciones son el modelo de catálogo
de Flower Turbines, ya bien confirmado, pero no el resultado final
calibrado contra viento turbulento real.
"""

import numpy as np


# ---------------------------------------------------------------------------
# 1. Curvas individuales (turbina aislada), P(v) = k * v^3   [W, v en m/s]
# ---------------------------------------------------------------------------

CURVE_COEFFICIENTS = {
    # modelo:        k (W / (m/s)^3),  v_cutin (m/s),  fuente
    "small_tulip":   dict(k=0.035963, v_cutin=0.7, fuente="tabla exacta (31 pts)"),
    "medium_tulip":  dict(k=0.360048, v_cutin=0.7, fuente="tabla exacta (31 pts)"),
    "three_m_tulip": dict(k=0.810200, v_cutin=0.7, fuente="1 punto oficial (12 m/s -> 1400 W)"),
    "large_tulip":   dict(k=3.120040, v_cutin=0.7, fuente="tabla exacta (31 pts)"),
    "al13_2m":       dict(k=0.881790, v_cutin=0.7, fuente="lectura aproximada de grafica PDF"),
    "al13_4m":       dict(k=1.806870, v_cutin=0.7, fuente="lectura aproximada de grafica PDF"),
    "al13_6m":       dict(k=3.095980, v_cutin=0.7, fuente="lectura aproximada de grafica PDF"),
    "al13_8m":       dict(k=4.037030, v_cutin=0.7, fuente="lectura aproximada de grafica PDF"),
}


def power_isolated(v, modelo):
    """
    Potencia de una turbina AISLADA (sin efecto clúster), en watts.

    v      : velocidad de viento en m/s (escalar o arreglo numpy)
    modelo : clave de CURVE_COEFFICIENTS, p.ej. "medium_tulip"

    P(v) = k * v^3 para v >= v_cutin, 0 por debajo del cut-in.
    Válido dentro de 0-15 m/s (rango de la fuente); más allá de eso es
    extrapolación.
    """
    if modelo not in CURVE_COEFFICIENTS:
        raise ValueError(f"Modelo desconocido: {modelo}. Opciones: {list(CURVE_COEFFICIENTS)}")
    coef = CURVE_COEFFICIENTS[modelo]
    v_arr = np.asarray(v, dtype=float)
    p = coef["k"] * v_arr ** 3
    return np.where(v_arr >= coef["v_cutin"], p, 0.0)


# ---------------------------------------------------------------------------
# 2. Multiplicador de Efecto Bouquet — potencia POR turbina en un clúster
#    de N unidades, relativo a la misma turbina aislada.
#
#    Ajustado y validado contra el calculador oficial en TODO el rango
#    0-15 m/s (N=1..10, Small/Medium/Large). Es una curva EXPONENCIAL,
#    no lineal, es la MISMA para los tres tamaños de turbina, y es
#    constante en velocidad de viento (R^2 = 1.000000):
#
#        M(N) = exp(K_BOUQUET * (N - 1))      con K_BOUQUET = 0.21103
#
#    Equivalente a decir que cada turbina adicional multiplica la
#    potencia por unidad en ~1.235 (un 23.5% de crecimiento COMPUESTO,
#    no un 25% aditivo plano como sugiere el texto de marketing de
#    Flower Turbines "25% por turbina").
# ---------------------------------------------------------------------------

K_BOUQUET = 0.21103  # regresión final, R^2=1.000000, N=1..10, v=3-15 m/s, 3 modelos


def bouquet_multiplier(N):
    """
    Multiplicador real M(N), verificado contra el calculador oficial de
    Flower Turbines para N=1..10 (mismo valor para Small/Medium/Large).

    M(1)=1.00  M(2)=1.24  M(3)=1.53  M(4)=1.88  M(5)=2.33
    M(6)=2.87  M(7)=3.55  M(8)=4.39  M(9)=5.42  M(10)=6.69
    """
    N_arr = np.asarray(N, dtype=float)
    return np.where(N_arr >= 1, np.exp(K_BOUQUET * (N_arr - 1)), 0.0)


def bouquet_multiplier_linear(N):
    """
    La fórmula lineal que Flower Turbines describe en su texto de
    marketing ("25% de incremento por cada turbina"): M(N) = 1 + 0.25*N.
    Se conserva solo como referencia/comparación — la real es
    bouquet_multiplier() de arriba. La lineal SUBESTIMA fuertemente a
    partir de N~6 (en N=10 dice 3.5x cuando la real da 6.7x).
    """
    N_arr = np.asarray(N, dtype=float)
    return np.where(N_arr >= 1, 1 + 0.25 * N_arr, 0.0)


def power_in_bouquet(v, modelo, N, metodo="real"):
    """
    Potencia POR TURBINA dentro de un clúster de N unidades del mismo modelo.

    metodo: "real"   (default) usa bouquet_multiplier() — la exponencial
                      verificada contra el calculador oficial
            "lineal" usa bouquet_multiplier_linear() — solo para comparar
    """
    base = power_isolated(v, modelo)
    m = bouquet_multiplier_linear(N) if metodo == "lineal" else bouquet_multiplier(N)
    return base * m


if __name__ == "__main__":
    print("Validación de la curva individual @ 12 m/s:")
    for modelo, oficial in [("small_tulip", 62.2), ("medium_tulip", 622.1),
                              ("three_m_tulip", 1400.0), ("large_tulip", 5391.4)]:
        calc = float(power_isolated(12, modelo))
        print(f"  {modelo:15s}  oficial={oficial:9.1f} W   calculado={calc:9.1f} W")

    print("\nMultiplicador de bouquet real (exponencial) vs. lineal de marketing:")
    for n in range(1, 11):
        print(f"  N={n:2d}   real={bouquet_multiplier(n):.3f}   lineal={bouquet_multiplier_linear(n):.3f}")

    print("\nPotencia por turbina, Medium Tulip, bouquet de 3, a 9 m/s:")
    print(f"  {float(power_in_bouquet(9, 'medium_tulip', 3)):.1f} W")

    print("\nValidación de que M(N) es constante en velocidad (dato real del")
    print("calculador, Medium Tulip, N=5 -- OJO: 1447.2 W es el valor correcto")
    print("del calculador; la ficha PDF de Medium Tulip trae una errata (1147)):")
    medium_n5_real = {3: 22.6, 6: 180.9, 9: 610.5, 12: 1447.2, 15: 2826.5}
    for vv, p_n5 in medium_n5_real.items():
        p_iso = float(power_isolated(vv, "medium_tulip"))
        print(f"  v={vv:2d} m/s   M medido = {p_n5/p_iso:.3f}   M fórmula = {float(bouquet_multiplier(5)):.3f}")
