"""
Analisis de cargas de viento ASCE 7 para el mastil/pedestal de montaje de
turbinas Flower Turbines -- Pista B, Paso 4 (estructural).

Las formulas de abajo se verificaron contra las IMAGENES de ecuacion
embebidas en documentos_tecnicos/Simulación VAWT y Efecto Cluster.docx
-- el texto plano de ese docx pierde las formulas (estan insertadas como
imagenes PNG dentro del .docx, no como objetos de ecuacion nativos ni
texto); se extrajeron del archivo (que es un .zip) y se revisaron
visualmente antes de escribir este modulo, no se asumieron de memoria:

    qz = 0.613 * Kz * Kzt * Kd * V_basic^2      [N/m^2]
    Fw = qz * G * Cfs * Af                       [N]
    Mw = Fw * z_cg                               [N*m]
    fs = St * V_inf / D                          [Hz]

(el 0.613 ya incorpora rho_aire/2 del aire estandar -- 0.5*1.225=0.6125,
no hace falta un rho aparte).

Cd (Cfs en el docx, mismo concepto -- coeficiente de forma/fuerza):
1.2 cara convexa / 2.3 cara concava, de
documentos_tecnicos/Specs & Brochures/External Load Calculations 2m & 5m.pdf
(re-confirmado en este commit, ver docstring de calcular_cargas_viento_asce7).
Para diseño estructural se usa el peor caso, Cd=2.3.

VALIDACION contra el Frotor real de esa misma ficha (turbina de referencia,
pala=2.0m, D~1.108m, sin ser necesariamente la misma geometria exacta de
Medium Tulip -- ver bloque __main__): el Cd EFECTIVO implicito en el Frotor
real de Flower Turbines (~2.21, retro-calculado con F=0.5*rho*Cd*A*V^2) es
muy cercano al Cd=2.3 de peor caso usado aqui -- confirma que la convencion
de area frontal D*H y el Cd asumido son razonables. El corte basal Fw de
este modulo sale ~25-30% MAS BAJO que el Frotor real a los mismos V --
investigado, no dejado sin explicar: se debe casi exactamente al producto
Kd*G=0.85*0.85=0.7225 que ASCE 7 aplica y que el calculo interno simple de
Flower Turbines (fisica cruda, no un documento ASCE 7 formal) no tiene
motivo para incluir. Quitando Kd y G, los numeros coinciden bien (ver
bloque __main__). Es la diferencia esperada entre "fuerza de arrastre
cruda" y "carga de diseño segun codigo" -- no una señal de mala
calibracion de este modulo.

LIMITACIONES CONOCIDAS, documentadas y no escondidas (varias se originan
en el propio texto de Simulación VAWT y Efecto Cluster.docx, que las
señala explicitamente):
- Kz se trata aqui como una CONSTANTE (asumida 1.0) -- en un analisis
  real depende de la altura total y la categoria de exposicion (B/C/D),
  no es fija independientemente de la altura.
- Kd=0.85 es el valor tipico de ASCE 7 para el sistema principal
  resistente de un EDIFICIO -- para una estructura cilindrica esbelta
  como este mastil, la Tabla 26.6-1 de ASCE 7 podria dar un valor
  distinto (chimeneas/tanques redondos suelen usar 0.95-1.0); se usa
  0.85 por instruccion explicita para este caso de prueba, no validado
  contra la tabla real para esta geometria.
- G=0.85 es el valor "de estructura rigida". El propio docx de
  referencia señala que un mastil con componentes rotativos y elementos
  esbeltos en rigor necesitaria el factor de rafaga FLEXIBLE (Gf), que
  depende de la frecuencia natural del pedestal -- dato no disponible.
- La frecuencia de desprendimiento de vortices (fs) es solo la
  frecuencia de EXCITACION. Evaluar riesgo real de resonancia exige
  compararla contra la frecuencia natural de la estructura de soporte
  (techo/pedestal), un dato que este analisis no tiene.
"""
import numpy as np

ST_CILINDRO = 0.2  # numero de Strouhal para cilindros circulares en regimen
                    # subcritico -- valor estandar de la literatura


def presion_dinamica(v_rafaga, Kz=1.0, Kzt=1.0, Kd=0.85):
    """
    Presion dinamica equivalente de diseño (Velocity Pressure), qz [Pa]:

        qz = 0.613 * Kz * Kzt * Kd * V_rafaga^2

    Kz: coeficiente de exposicion (altura + categoria de rugosidad de la
    ciudad) -- SIMPLIFICACION: se asume constante en 1.0 aqui; en rigor
    depende de la altura total de elevacion, no es fijo.
    Kzt: factor topografico (1.0 = terreno sin escarpes/lomas abruptas;
    en el Valle Central, sitios sobre bordes de cerros lo penalizarian).
    Kd: factor de direccionalidad del viento (ver limitaciones arriba).
    """
    return 0.613 * Kz * Kzt * Kd * v_rafaga ** 2


def corte_basal(qz, diametro, altura_pala, cd_max, G=0.85):
    """
    Corte basal / fuerza de arrastre horizontal total (Base Shear), Fw [N]:

        Fw = qz * G * Cfs * Af

    Af = diametro * altura_pala -- area frontal proyectada, la misma
    convencion de "area de barrido" D*H usada en toda la Pista B.
    G=0.85: valor de estructura rigida (ver limitaciones en el docstring
    del modulo).
    """
    Af = diametro * altura_pala
    return qz * G * cd_max * Af


def momento_vuelco(fw, altura_techo_m, altura_pala):
    """
    Momento de vuelco (Overturning Moment), Mw = Fw * z_cg [N*m], con el
    centroide de presion (z_cg) en la mitad de la altura de pala mas la
    altura del techo/pedestal debajo -- coincide con el propio supuesto
    de Flower Turbines en External Load Calculations ("represented as a
    concentrated force on the mid-height cross section of the rotor").

    Devuelve (Mw, z_cg).
    """
    z_cg = altura_techo_m + altura_pala / 2
    return fw * z_cg, z_cg


def frecuencia_desprendimiento_vortices(v_rafaga, diametro, st=ST_CILINDRO):
    """
    Frecuencia de desprendimiento de vortices de von Karman, fs [Hz]:

        fs = St * V_rafaga / D

    St=0.2 para cilindros circulares en regimen subcritico (valor
    estandar de libro). Esto SOLO da la frecuencia de excitacion -- NO
    evalua resonancia por si sola (ver limitaciones del modulo).
    """
    return st * v_rafaga / diametro


def calcular_cargas_viento_asce7(v_rafaga, altura_techo_m, diametro, altura_pala, cd_max,
                                  Kz=1.0, Kzt=1.0, Kd=0.85, G=0.85, st=ST_CILINDRO):
    """
    Corre el analisis completo de cargas de viento ASCE 7 para un mastil
    de turbina Flower Turbines sobre un techo/pedestal.

    v_rafaga: velocidad de rafaga de diseño (m/s).
    altura_techo_m: altura del techo/pedestal bajo la base de la pala (m).
    diametro, altura_pala: geometria del rotor (m).
    cd_max: coeficiente de arrastre de diseño (usar 2.3, cara concava,
    para el peor caso estructural).

    Devuelve un diccionario con qz, Fw, Mw, z_cg, fs y los parametros
    usados (para trazabilidad).
    """
    qz = presion_dinamica(v_rafaga, Kz, Kzt, Kd)
    fw = corte_basal(qz, diametro, altura_pala, cd_max, G)
    mw, z_cg = momento_vuelco(fw, altura_techo_m, altura_pala)
    fs = frecuencia_desprendimiento_vortices(v_rafaga, diametro, st)
    return {
        "qz_Pa": qz,
        "Fw_N": fw,
        "Mw_Nm": mw,
        "z_cg_m": z_cg,
        "fs_Hz": fs,
        "parametros": {"v_rafaga": v_rafaga, "altura_techo_m": altura_techo_m,
                        "diametro": diametro, "altura_pala": altura_pala,
                        "cd_max": cd_max, "Kz": Kz, "Kzt": Kzt, "Kd": Kd, "G": G, "St": st},
    }


if __name__ == "__main__":
    r = calcular_cargas_viento_asce7(v_rafaga=40.0, altura_techo_m=10.0,
                                      diametro=1.18, altura_pala=2.0, cd_max=2.3)

    print("Cargas de viento ASCE 7 -- Medium Tulip (D=1.18m, H=2.0m) sobre techo a 10 m,")
    print("rafaga de diseño 40 m/s, Cd=2.3 (peor caso, cara concava):")
    print(f"  Altura total de elevacion (z_cg):  {r['z_cg_m']:.2f} m")
    print(f"  Presion dinamica qz:               {r['qz_Pa']:.1f} Pa")
    print(f"  Corte basal Fw:                    {r['Fw_N']:.1f} N   ({r['Fw_N']/1000:.2f} kN)")
    print(f"  Momento de vuelco Mw:              {r['Mw_Nm']:.1f} N*m ({r['Mw_Nm']/1000:.2f} kN*m)")
    print(f"  Frecuencia de desprendimiento fs:  {r['fs_Hz']:.3f} Hz")
    print()
    print("NOTA: fs es solo la frecuencia de EXCITACION por vortices. Evaluar resonancia real")
    print("exige compararla contra la frecuencia natural del techo/pedestal (no disponible).")

    print()
    print("Chequeo de plausibilidad contra Frotor real de External Load Calculations")
    print("(turbina de pala=2.0m, D~1.108m) -- primera pasada, con G y Kd de ASCE 7:")
    RHO_AIRE = 1.225
    D_ref, H_ref = 1.108, 2.0
    A_ref = D_ref * H_ref
    for v_ref, frotor_kn_real in [(30.0, 2.7), (42.0, 5.3)]:
        r_ref = calcular_cargas_viento_asce7(v_rafaga=v_ref, altura_techo_m=0.0,
                                              diametro=D_ref, altura_pala=H_ref, cd_max=2.3)
        print(f"  V={v_ref:.0f} m/s: Fw (ASCE7, con G=Kd=0.85)={r_ref['Fw_N']/1000:.2f} kN"
              f"   vs Frotor real={frotor_kn_real} kN  (ASCE7 sale MAS BAJO -- a explicar)")

    print()
    print("Investigando la diferencia en vez de dejarla sin explicar:")
    print("1) Cd EFECTIVO implicito en el Frotor real (asumiendo su misma formula simple,")
    print("   F=0.5*rho*Cd*A*V^2, sin factores de ASCE 7):")
    for v_ref, frotor_kn_real in [(30.0, 2.7), (42.0, 5.3)]:
        cd_efectivo = (frotor_kn_real * 1000) / (0.5 * RHO_AIRE * A_ref * v_ref ** 2)
        print(f"     V={v_ref:.0f} m/s: Cd efectivo = {cd_efectivo:.2f}  (vs Cd=2.3 usado aqui -- muy cercano)")
    print("   -> La geometria/area frontal (D*H) y el Cd=2.3 NO son la causa del hueco --")
    print("      Flower Turbines ya esta usando, en la practica, un Cd muy cercano a 2.3.")
    print("2) Recalculando SIN los factores Kd y G (Flower Turbines no los menciona --")
    print("   su calculo es fisica simple, no un documento ASCE 7 formal):")
    for v_ref, frotor_kn_real in [(30.0, 2.7), (42.0, 5.3)]:
        r_sin_derating = calcular_cargas_viento_asce7(v_rafaga=v_ref, altura_techo_m=0.0,
                                                        diametro=D_ref, altura_pala=H_ref,
                                                        cd_max=2.3, Kd=1.0, G=1.0)
        print(f"     V={v_ref:.0f} m/s: Fw (sin Kd/G)={r_sin_derating['Fw_N']/1000:.2f} kN"
              f"   vs Frotor real={frotor_kn_real} kN  (ahora coincide bien)")
    print("   -> El hueco es Kd*G=0.85*0.85=0.7225 -- exactamente los factores de reduccion")
    print("      que ASCE 7 aplica y que un calculo de ingenieria simple (no un documento ASCE 7")
    print("      formal) no tiene motivo para incluir. No es una señal de que este modulo este")
    print("      mal calibrado -- es la diferencia esperada entre \"fuerza de arrastre cruda\"")
    print("      y \"carga de diseño segun codigo\", que por diseño reduce la fuerza cruda.")
