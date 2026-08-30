"""
Estimacion de potencia tipo Savonius clasico, usando la geometria y el Cp
reportados en la patente ES2970155T3 ("Savonius Wind Turbine", prioridad
2018, otorgada 2024) para el componente de arrastre de Flower Turbines.

NO se combina (suma) con el modelo DMST de sustentacion de dmst_model.py --
la forma exacta en que ambos componentes coexisten en la misma pala hibrida
sigue sin resolverse (ver notebook Pista B). Esto se deja como una
estimacion INDEPENDIENTE, para ver si "es basicamente un Savonius" es una
hipotesis razonable en cuanto a orden de magnitud, no como una pieza mas de
un modelo combinado que todavia no esta validado.
"""
import numpy as np

RHO_AIRE = 1.225

# Geometria de la patente ES2970155T3, normalizada al diametro del eje (d_eje):
RATIO_DISTANCIA_BORDES = 3.5
RATIO_SUPERPOSICION = 0.2
RATIO_CUERDA = 6.6
RATIO_DIAMETRO_TOTAL = 9.7   # diametro_total_savonius / diametro_del_eje

CP_PATENTE = 0.34     # Cp reportado en la patente
TSR_OPT_PATENTE = 0.5  # TSR optimo reportado


def geometria_savonius(diametro_rotor):
    """
    Deriva las dimensiones de la geometria Savonius a partir del diametro
    total del rotor (asumiendo que "diametro total" en la patente se
    refiere al diametro completo del rotor, no a una sub-pieza en el eje --
    ver docstring del modulo, es una interpretacion, no esta confirmada
    con el texto completo de la patente).
    """
    d_eje = diametro_rotor / RATIO_DIAMETRO_TOTAL
    return {
        "diametro_eje": d_eje,
        "distancia_bordes": RATIO_DISTANCIA_BORDES * d_eje,
        "superposicion": RATIO_SUPERPOSICION * d_eje,
        "cuerda": RATIO_CUERDA * d_eje,
    }


def potencia_savonius(V_inf, diametro_rotor, H, rho=RHO_AIRE, cp=CP_PATENTE):
    """
    Potencia estimada (W) de un rotor tipo Savonius puro de este diametro y
    altura, usando el Cp reportado en la patente (no derivado de primeros
    principios -- es un dato de la patente, tomado tal cual).
    """
    A = diametro_rotor * H
    return cp * 0.5 * rho * A * V_inf ** 3


if __name__ == "__main__":
    geo = geometria_savonius(1.18)  # Medium Tulip
    print("Geometria Savonius derivada para Medium Tulip (D=1.18m):")
    for k, v in geo.items():
        print(f"  {k}: {v:.4f} m")

    print()
    print(f"{'V (m/s)':>8}  {'P Savonius (W)':>15}")
    for V in [3, 6, 9, 12, 15]:
        print(f"{V:8.1f}  {potencia_savonius(V, 1.18, 2.0):15.1f}")
