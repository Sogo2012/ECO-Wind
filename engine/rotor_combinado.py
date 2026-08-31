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

LIMITACION IMPORTANTE de potencia_combinada() (encontrada y NO escondida):
suma las dos potencias como si cada nivel viera el viento V_inf SIN
perturbar -- dos discos actuadores independientes, sin acoplamiento de
induccion entre ellos. Esto es Betz-compatible en TSR=1.0 (Cp combinado
~0.50), pero **rompe el limite de Betz en TSR=1.25** (borde superior de la
tolerancia +-25% que la propia patente declara), porque el termino de
sustentacion sigue creciendo con TSR mientras el termino de arrastre se
mantiene fijo (Cp=0.34 constante).

ACTUALIZACION -- induccion conjunta implementada y validada
(potencia_combinada_induccion_conjunta(), ver mas abajo): resuelve UN solo
factor de induccion compartido entre ambos niveles. Resultado honesto:
- Corrige la violacion de Betz encontrada en TSR=1.25 (Cp baja de ~0.61 a
  ~0.54, dentro del limite).
- Reduce la sobre-prediccion contra los 4 modelos reales de forma
  consistente (Small 5.39x->4.61x, Medium 2.01x->1.72x, 3M 2.04x->1.75x,
  Large 1.23x->1.05x -- este ultimo casi exacto).
- PERO el factor de induccion queda pegado en el techo numerico (a=0.49)
  en los 4 modelos reales al TSR objetivo -- señal de que el sistema esta
  en la zona de induccion alta donde la teoria de momento simple (sin
  correccion de Glauert) deja de ser confiable. La mejora es real, pero
  ocurre en un regimen que en rigor necesitaria esa correccion para
  confirmarse -- sigue como el siguiente paso natural, no resuelto aqui.
"""
import numpy as np

try:
    from engine.dmst_model import resolver_dmst, fuerzas_azimut, _trapz, RHO_AIRE
    from engine.savonius_model import potencia_savonius, CP_PATENTE
except ImportError:
    from dmst_model import resolver_dmst, fuerzas_azimut, _trapz, RHO_AIRE
    from savonius_model import potencia_savonius, CP_PATENTE

TSR_OBJETIVO = 1.0  # de la formula de rpm objetivo de US9255567B2, ver docstring
CP_BETZ = 16 / 27  # 0.5926 -- limite ideal de disco actuador (a=1/3)


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


def potencia_combinada_induccion_conjunta(V_inf, diametro, H, R=None, c=None, N=2,
                                           rho=RHO_AIRE, tsr=TSR_OBJETIVO,
                                           cp_savonius=CP_PATENTE, n_theta=72,
                                           a0=0.2, tol=1e-4, max_iter=100, relax=0.3):
    """
    Version con INDUCCION CONJUNTA de potencia_combinada(): en vez de sumar
    dos discos actuadores independientes (cada uno viendo V_inf sin
    perturbar), resuelve UN solo factor de induccion 'a' compartido, a
    partir del empuje TOTAL (sustentacion + arrastre) sobre el mismo disco.

    Simplificacion respecto al DMST de doble tubo de corriente (upwind/
    downwind) usado en el resto de la Pista B: aqui se integra la fuerza de
    sustentacion en UNA sola pasada de 0 a 2*pi (un solo tubo de corriente),
    no dos. Se eligio asi a proposito -- partir el empuje de arrastre entre
    upwind/downwind exigiria inventar una regla de reparto sin datos que la
    respalden (el Cp=0.34 del Savonius es un solo numero agregado, no esta
    descompuesto por azimut), y hacerlo de forma arbitraria seria peor que
    no hacerlo. Un solo tubo de corriente evita esa suposicion adicional,
    a costa de perder el acoplamiento upwind/downwind que si tiene el DMST
    puro. Por eso NO es directamente el mismo numero que resolver_dmst().

    Nivel de arrastre (Savonius): no hay una curva Cp(a) medida, solo el
    pico reportado por la patente (Cp=0.34 a su TSR optimo). Se modela como
    un disco actuador ideal ESCALADO por un factor de eficiencia
    eta = 0.34 / (16/27) ~ 0.573 respecto al limite de Betz -- es decir,
    Cp_arrastre(a) = eta * 4*a*(1-a)^2  y  CT_arrastre(a) = eta * 4*a*(1-a).
    Por construccion, el pico de esa curva escalada es exactamente 0.34 en
    a=1/3 (el mismo punto donde un disco ideal alcanza su propio pico) --
    una aproximacion de ingenieria razonable pero NO validada con datos
    propios del Savonius a otros valores de 'a', documentada aqui como tal.

    Devuelve el mismo formato que potencia_combinada(), mas 'a' (el factor
    de induccion conjunto convergido).
    """
    if R is None:
        R = diametro / 2
    if c is None:
        c = 0.35 * diametro
    A = diametro * H
    Omega = tsr * V_inf / R
    thetas = np.linspace(0, 2 * np.pi, n_theta)
    eta_drag = cp_savonius / CP_BETZ

    a = a0
    for _ in range(max_iter):
        u = V_inf * (1 - a)
        Fx_vals = np.array([fuerzas_azimut(th, u, Omega, R, c, rho, re_dependiente=False)[1]
                             for th in thetas])
        T_lift = (N / (2 * np.pi)) * _trapz(Fx_vals, thetas) * H
        T_drag = eta_drag * 4 * a * (1 - a) * 0.5 * rho * A * V_inf ** 2
        T_total = T_lift + T_drag
        CT = np.clip(T_total / (0.5 * rho * A * V_inf ** 2), 0.0, 0.9999) if V_inf > 0 else 0.0
        a_nuevo = 0.5 * (1 - np.sqrt(max(1 - CT, 0.0)))
        a = a + relax * (a_nuevo - a)
        a = np.clip(a, 0.0, 0.49)
        if abs(a_nuevo - a) < tol:
            break

    u = V_inf * (1 - a)
    Ft_vals = np.array([fuerzas_azimut(th, u, Omega, R, c, rho, re_dependiente=False)[0]
                         for th in thetas])
    Q_lift = (N / (2 * np.pi)) * _trapz(Ft_vals, thetas) * R
    p_lift = Q_lift * Omega * H
    p_drag = eta_drag * 4 * a * (1 - a) ** 2 * 0.5 * rho * A * V_inf ** 3

    return {"potencia_W": p_lift + p_drag, "potencia_sustentacion_W": p_lift,
            "potencia_arrastre_W": p_drag, "a": a}


if __name__ == "__main__":
    RHO = RHO_AIRE
    D, H = 1.18, 2.0  # Medium Tulip
    A = D * H

    print("Discos independientes vs induccion conjunta, D=1.18m (Medium Tulip), V=9 m/s:")
    print(f"{'TSR':>5} {'Cp independiente':>17} {'Cp conjunto':>12} {'a conjunto':>10}")
    for tsr in [0.75, 1.0, 1.25, 1.5]:
        r1 = potencia_combinada(9.0, D, H, tsr=tsr)
        r2 = potencia_combinada_induccion_conjunta(9.0, D, H, tsr=tsr)
        cp1 = r1["potencia_W"] / (0.5 * RHO * A * 9.0 ** 3)
        cp2 = r2["potencia_W"] / (0.5 * RHO * A * 9.0 ** 3)
        m1 = "  <-- ROMPE BETZ" if cp1 > 0.593 else ""
        m2 = "  <-- ROMPE BETZ" if cp2 > 0.593 else ""
        print(f"{tsr:5.2f} {cp1:14.4f}{m1:>3} {cp2:12.4f}{m2:>3} {r2['a']:10.4f}")
