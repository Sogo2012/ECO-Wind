"""
Atmosfera Estandar Internacional (ISA) -- densidad del aire por elevacion.

Pista A, Requisito 2 (Fase 2): los coeficientes k de flower_turbines_curves.py
estan calibrados contra la tabla oficial de Flower Turbines, que asume aire
estandar a nivel del mar (rho=1.225 kg/m^3). La mayoria de proyectos reales
van a estar en el Valle Central (900-1500+ msnm), donde la densidad real es
menor -- eso reduce la potencia real proporcionalmente (P ∝ rho) y sin esta
correccion el modelo lo sobre-estima.

OJO -- esto NO es lo mismo que el archivo powerDensity que exporta GWA (ese
es un indicador combinado de recurso eolico, velocidad Y densidad juntas,
pensado para comparar sitios entre si, no una correccion de densidad para
aplicar sobre una curva de potencia ya calibrada a otra densidad). No usar
uno como sustituto del otro.
"""
import numpy as np

RHO_ESTANDAR = 1.225  # kg/m^3, ISA a nivel del mar (15C, 101325 Pa) -- misma
                       # que ya usan dmst_model.py/rotor_combinado.py/etc.
T0_K = 288.15          # K, temperatura ISA a nivel del mar
LAPSE_K_POR_M = 0.0065  # K/m, gradiente termico ISA (troposfera, valido hasta 11km)
G0 = 9.80665            # m/s^2
R_ESPECIFICO_AIRE = 287.053  # J/(kg*K), R/M_aire

_EXPONENTE = G0 / (R_ESPECIFICO_AIRE * LAPSE_K_POR_M) - 1  # ~4.2559


def densidad_aire_isa(elevacion_m):
    """
    Densidad del aire (kg/m^3) segun la formula barometrica de la Atmosfera
    Estandar Internacional (ISA), valida en toda la troposfera (hasta 11km
    -- cubre de sobra la elevacion maxima de Costa Rica, Cerro Chirripo
    ~3821m).

        rho(h) = rho0 * (1 - L*h/T0)^(g0/(R*L) - 1)

    Verificado contra tabla de atmosfera estandar de referencia: a 1000m
    da ~1.112 kg/m^3 (tablas ISA publicadas: 1.1117 kg/m^3) -- coincide.
    """
    elevacion_m = np.asarray(elevacion_m, dtype=float)
    ratio_temperatura = 1 - LAPSE_K_POR_M * elevacion_m / T0_K
    return RHO_ESTANDAR * ratio_temperatura ** _EXPONENTE


def factor_correccion_densidad(elevacion_m):
    """
    Factor multiplicativo (rho_local/rho_estandar) para corregir la
    potencia de una curva calibrada a nivel del mar:

        P_real(v) = P_tabla(v) * factor_correccion_densidad(elevacion_m)

    Como P ∝ rho a igual v (ver docstring del modulo), este factor es
    directamente la razon de densidades -- siempre <=1 para elevaciones
    positivas (menos aire denso, menos potencia disponible a igual viento).
    """
    return densidad_aire_isa(elevacion_m) / RHO_ESTANDAR


if __name__ == "__main__":
    print("Verificacion contra tabla de atmosfera estandar de referencia (valores")
    print("publicados, ej. ICAO Doc 7488 / NASA ISA tables):")
    referencia = {0: 1.225, 1000: 1.1117, 2000: 1.0066, 3000: 0.9093, 5000: 0.7364}
    for h, rho_ref in referencia.items():
        rho_calc = float(densidad_aire_isa(h))
        err_pct = abs(rho_calc - rho_ref) / rho_ref * 100
        print(f"  h={h:5d}m  rho_calc={rho_calc:.4f}  rho_ref={rho_ref:.4f}  error={err_pct:.3f}%")

    print()
    print("Caso real: Aeropuerto Juan Santamaria, 921m (verificado AIP/DGAC Costa Rica):")
    h_sjo = 921.0
    rho_sjo = float(densidad_aire_isa(h_sjo))
    factor_sjo = float(factor_correccion_densidad(h_sjo))
    print(f"  Elevacion: {h_sjo:.0f} m")
    print(f"  Densidad local: {rho_sjo:.4f} kg/m^3 (vs {RHO_ESTANDAR} kg/m^3 a nivel del mar)")
    print(f"  Factor de correccion: {factor_sjo:.4f}  ->  la potencia real es "
          f"{(1-factor_sjo)*100:.1f}% MAS BAJA que la curva de catalogo sin corregir")
    print("  Magnitud fisicamente razonable: ~1% de perdida de densidad cada ~100m en el")
    print("  rango bajo -- 921m da ~9-10%, consistente con la heuristica de la industria.")
