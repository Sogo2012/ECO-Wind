"""
Rotor combinado sustentacion + arrastre, siguiendo la arquitectura real
descrita en la patente US9255567B2/CA2800765C ("Two-Bladed Vertical Axis
Wind Turbines", Farb et al.): NO es un solo perfil hibrido con Cd asimetrico
(ver engine/polar_hibrido.py -- esa fue la primera hipotesis de este
proyecto, verificada como estructuralmente inerte en el TSR optimo del
DMST, ver Pista B Paso 5c/Hallazgo 5), sino DOS niveles de pala en el MISMO
eje: un nivel de arrastre (tipo Savonius) y un nivel de sustentacion (tipo
NACA0018), girando a la MISMA velocidad angular.

Cita textual de US9255567B2 (columna 7-8, reivindicaciones):
  "An internal set of drag blades... An external set of lift blades,
  wherein the maximally efficient rpm of the two sets are within 20% of
  each other."
  "A generator, when the wind is at a speed of 10 meters per second,
  operating most efficiently at a rpm plus or minus 25% of 10 divided by
  the product of 'pi' and the turbine diameter."

Esa formula de rpm objetivo, expresada como TSR (lambda = Omega*R/V), da
lambda = 1.0 independiente del diametro (verificado con el ejemplo numerico
de la propia patente: turbina de arrastre D=2.5m a 76 rpm y palas de
sustentacion a 86 rpm, ambas ~TSR=1.0, ver avance-de-proyecto.md).

LIMITACION IMPORTANTE (encontrada y NO escondida): este modulo suma las dos
potencias como si cada nivel viera el viento V_inf SIN perturbar -- dos
discos actuadores independientes, sin acoplamiento de induccion entre
ellos. Esto es Betz-compatible en TSR=1.0 (Cp combinado ~0.50), pero
**rompe el limite de Betz en TSR=1.25** (borde superior de la tolerancia
+-25% que la propia patente declara), porque el termino de sustentacion
sigue creciendo con TSR mientras el termino de arrastre se mantiene fijo
(Cp=0.34 constante, no se modela su propia dependencia de TSR por falta de
una curva Cp(TSR) completa de la patente). Un modelo mas riguroso
necesitaria resolver una induccion conjunta entre ambos niveles en vez de
sumar dos discos actuadores independientes -- queda como trabajo futuro,
no resuelto en este modulo.
"""
import numpy as np

try:
    from engine.dmst_model import resolver_dmst, RHO_AIRE
    from engine.savonius_model import potencia_savonius
except ImportError:
    from dmst_model import resolver_dmst, RHO_AIRE
    from savonius_model import potencia_savonius

TSR_OBJETIVO = 1.0  # de la formula de rpm objetivo de US9255567B2, ver docstring


def potencia_combinada(V_inf, diametro, H, R=None, c=None, N=2, rho=RHO_AIRE,
                        tsr=TSR_OBJETIVO, cp_savonius=None):
    """
    Potencia combinada (W) de un rotor de dos niveles (arrastre + sustentacion)
    en el mismo eje, evaluados ambos al TSR compartido `tsr` (por defecto
    TSR_OBJETIVO=1.0, el valor que se desprende de la formula de rpm de
    US9255567B2). Suma simple de dos discos actuadores independientes --
    ver limitacion en el docstring del modulo (no Betz-robusto lejos de
    TSR=1.0).

    R, c: radio y cuerda del nivel de sustentacion. Si no se dan, se derivan
    de `diametro` (R=diametro/2) y CTDR=0.35 (c=0.35*diametro), el mismo
    valor usado en el resto de la Pista B.

    cp_savonius: si se da, sobreescribe el Cp=0.34 de la patente para el
    nivel de arrastre (para pruebas de sensibilidad).
    """
    if R is None:
        R = diametro / 2
    if c is None:
        c = 0.35 * diametro
    kwargs_savonius = {} if cp_savonius is None else {"cp": cp_savonius}
    p_lift = resolver_dmst(V_inf, tsr, R, c, N, H, rho=rho, re_dependiente=False)["potencia_W"]
    p_drag = potencia_savonius(V_inf, diametro, H, rho=rho, **kwargs_savonius)
    return {"potencia_W": p_lift + p_drag, "potencia_sustentacion_W": p_lift,
            "potencia_arrastre_W": p_drag}


if __name__ == "__main__":
    RHO = RHO_AIRE
    print("Chequeo de Betz del modelo combinado, D=1.18m (Medium Tulip), V=9 m/s:")
    print(f"{'TSR':>5} {'Cp combinado':>13}")
    D, H = 1.18, 2.0
    A = D * H
    for tsr in [0.75, 1.0, 1.25]:
        r = potencia_combinada(9.0, D, H, tsr=tsr)
        cp = r["potencia_W"] / (0.5 * RHO * A * 9.0 ** 3)
        marca = "  <-- ROMPE BETZ" if cp > 0.593 else ""
        print(f"{tsr:5.2f} {cp:13.4f}{marca}")
