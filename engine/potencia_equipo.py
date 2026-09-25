"""
Potencia de un equipo de la cartera según su ficha y el artículo elegido.

- potencia_max_turbina_w(): tope horario por turbina del cálculo de energía
  (simulador_pista_a.simular()) -- el cargador/inversor del artículo, o el generador.
- velocidad_a_potencia_ms(): velocidad a la que un bouquet llega a una potencia dada,
  desde la curva validada.

La "Potencia pico instalada" de la app y del informe NO sale de acá: es la potencia
nominal del generador de la ficha × turbinas (capacidad instalada). Contexto (correo de
Daniel Farb, Flower Turbines, sobre el informe del Estadio Heredia): la ficha decía
1,000 W por generador y la página 1 daba 20 kW, mientras la energía dejaba llegar cada
turbina a los 3,000 W del cargador -- la potencia media del año (216,781 kWh / 8,760 h
= 24.7 kW) quedaba por encima de la "pico". Con el generador corregido a 3,000 W, la
potencia instalada es 60 kW y ningún cargador del catálogo del 3-M Tulip la supera.
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
    ficha de fábrica. Es el tope por electrónica del cálculo de energía (el recorte
    horario), no la potencia pico instalada.
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
