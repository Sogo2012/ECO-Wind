"""
Potencia máxima por turbina de un clúster de la cartera -- UNA sola regla para el
cálculo de energía (tope horario de simulador_pista_a.simular()) y para la
"Potencia pico instalada" de la app y del informe ejecutivo.

Por qué existe (correo de Daniel Farb, Flower Turbines, sobre el informe del Estadio
Heredia con cargadores de 3 kW): la página 1 decía 20 kW de potencia pico
(20 turbinas × 1,000 W de la ficha del generador) mientras la energía anual se
calculaba dejando que cada turbina llegue a los 3,000 W del controlador -- la
potencia MEDIA del año (216,781 kWh / 8,760 h = 24.7 kW) quedaba por encima de la
potencia PICO, algo físicamente imposible. Eran dos supuestos distintos en el mismo
documento. Con esta regla los dos números salen del mismo lugar y no pueden volver a
contradecirse, para ningún modelo (lo mismo pasaba con el Large Tulip + inversor de
10 kW, y al revés con el AL13 de 8 m + inversor de 5 kW).
"""
import numpy as np

from engine.flower_turbines_curves import power_in_bouquet
from engine.precios_flower_turbines import capacidad_controlador_articulo_w
from engine.turbine_specs import SPECS_TURBINAS


def potencia_max_turbina_w(modelo, articulo):
    """
    Potencia máxima (W) que puede entregar UNA turbina del clúster: la capacidad del
    controlador/inversor incluido en el artículo elegido, si el texto del artículo la
    trae ("... charger 3 kilowatts" -> 3000); si no, la potencia del generador de la
    ficha de fábrica. Es el mismo tope por electrónica que usa el cálculo de energía,
    así que la potencia pico del proyecto es exactamente el máximo horario que puede
    alcanzar la producción simulada.
    """
    return capacidad_controlador_articulo_w(articulo) or SPECS_TURBINAS[modelo]["potencia_nominal_w"]


def velocidad_a_potencia_ms(modelo, N, potencia_w, metodo_bouquet="real"):
    """
    Velocidad de viento (m/s, densidad de nivel del mar -- misma convención que la
    ficha) a la que una turbina dentro de un bouquet de N unidades llega a potencia_w,
    según la curva ya validada P(v) = k·v³ × M(N) (engine/flower_turbines_curves.py).

    Como P es proporcional a v³ por encima del cut-in, alcanza con evaluar la curva en
    una velocidad de referencia (10 m/s, por encima del cut-in de todos los modelos):
    v = 10 · (potencia_w / P(10 m/s)) ** (1/3). Puede dar más de 15 m/s, fuera del
    rango de la tabla oficial de la que sale la curva -- quien lo muestre debe decirlo.
    """
    v_ref = 10.0
    p_ref = float(power_in_bouquet(v_ref, modelo, N, metodo_bouquet))
    return float(v_ref * np.cbrt(potencia_w / p_ref))
