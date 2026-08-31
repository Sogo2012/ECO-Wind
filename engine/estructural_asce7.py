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

# Patrones de anclaje REALES, de los planos de base de concreto de Flower
# Turbines (Big/Small Pedestal Concrete Base ASSY, Power Tower Concrete
# Base ASSY). n_pernos: cantidad de varillas roscadas. diametro_perno:
# rosca de la varilla. ancho_patron_m: dimension exterior del patron
# cuadrado (m). peso_distribuido_kg: carga distribuida nominal indicada
# en el plano (no es capacidad de diseño de los pernos, es una referencia
# del propio plano).
#
# "Small Pedestal" (del plano) cubre Medium Tulip (2m) Y 3-M Tulip (3m)
# con el MISMO patron -- es un nombre de TAMAÑO DE BASE relativo a "Big
# Pedestal", no el producto "Small Tulip" (1.15m de pala). No hay plano
# de base documentado especificamente para el Small Tulip todavia.
PATRONES_ANCLAJE = {
    "large_tulip":       {"n_pernos": 12, "diametro_perno": "M18x2.5", "ancho_patron_m": 0.8744, "peso_distribuido_kg": 675},
    "al13_power_tower":  {"n_pernos": 12, "diametro_perno": "M18x2.5", "ancho_patron_m": 0.7744, "peso_distribuido_kg": 816},
    "medium_tulip":      {"n_pernos": 12, "diametro_perno": "M14x2",   "ancho_patron_m": 0.6025, "peso_distribuido_kg": 311},
    "three_m_tulip":     {"n_pernos": 12, "diametro_perno": "M14x2",   "ancho_patron_m": 0.6025, "peso_distribuido_kg": 311},
}


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


ESPACIAMIENTO_IDEAL_FACTOR = 1.25  # diametro x 1.25, eje a eje -- "Guidance on Spacing Flower
                                    # Turbines.pdf" (Hallazgo 11); rango aceptable 1.1-1.3x
SEPARACION_FILAS_FACTOR = 4.0      # diametro x 4 (punto medio del rango 3-5x recomendado en el
                                    # mismo documento) -- separacion entre filas de un cluster


def espaciamiento_cluster(diametro, factor=ESPACIAMIENTO_IDEAL_FACTOR):
    """
    Espaciamiento ideal eje-a-eje DENTRO de una fila, para el efecto
    Bouquet -- de "Guidance on Spacing Flower Turbines.pdf" (Hallazgo 11):
    diametro x 1.25 (funciona tambien en 1.1x-1.3x). Ese mismo documento
    tiene una inconsistencia aritmetica interna (dice tambien "diametro x
    0.1" en un ejemplo distinto, ver Hallazgo 11) -- se usa aqui la regla
    principal (1.25x), no la del ejemplo.
    """
    return diametro * factor


def separacion_filas(diametro, factor=SEPARACION_FILAS_FACTOR):
    """
    Separacion recomendada ENTRE filas de un cluster, para que el viento
    recupere velocidad antes de la siguiente fila -- ideal 5x diametro,
    minimo 3x (Hallazgo 11); se usa el punto medio (4x) como valor por
    defecto.
    """
    return diametro * factor


def cargas_viento_cluster_asce7(v_rafaga, altura_techo_m, diametro, altura_pala, cd_max,
                                 n_turbinas, Kz=1.0, Kzt=1.0, Kd=0.85, G=0.85, st=ST_CILINDRO,
                                 factor_espaciamiento=ESPACIAMIENTO_IDEAL_FACTOR):
    """
    Demanda estructural TOTAL de un cluster/bouquet de n_turbinas del
    mismo modelo, en una sola fila con el espaciamiento ideal de
    Hallazgo 11.

    SIMPLIFICACION IMPORTANTE, explicita: se suma la carga de cada
    turbina SIN ningun credito de apantallamiento aerodinamico (no se
    asume que las turbinas corriente abajo reciben menos empuje por
    estar en la estela de las de adelante) -- eso requeriria el modelo
    CFD de efecto cluster (Cilindro Actuador/OpenFOAM), que sigue sin
    construirse (ver Pendientes). Es una simplificacion CONSERVADORA
    para dimensionar una estructura de soporte compartida (marco,
    rieles, cimentacion comun) -- no un intento de predecir generacion
    de energia del cluster (eso ya lo cubre power_in_bouquet() en
    engine/flower_turbines_curves.py, con el Efecto Bouquet real medido
    por el fabricante, que va en la direccion CONTRARIA: mas potencia
    por turbina, no menos empuje por turbina -- son dos efectos fisicos
    distintos, no se debe confundir uno con el otro).

    Devuelve el diccionario de calcular_cargas_viento_asce7() para UNA
    turbina (bajo "individual"), mas la demanda total y la geometria del
    arreglo.
    """
    individual = calcular_cargas_viento_asce7(v_rafaga, altura_techo_m, diametro, altura_pala,
                                               cd_max, Kz, Kzt, Kd, G, st)
    espaciamiento = espaciamiento_cluster(diametro, factor_espaciamiento)
    ancho_fila_m = espaciamiento * (n_turbinas - 1) + diametro
    return {
        "individual": individual,
        "n_turbinas": n_turbinas,
        "Fw_total_N": individual["Fw_N"] * n_turbinas,
        "Mw_total_Nm": individual["Mw_Nm"] * n_turbinas,
        "espaciamiento_ideal_m": espaciamiento,
        "ancho_fila_aprox_m": ancho_fila_m,
    }


def tension_maxima_pernos(mw, n_pernos, ancho_patron_m):
    """
    Demanda de tension MAXIMA por perno de anclaje, a partir del momento
    de vuelco Mw, usando un patron de pernos REAL (ver PATRONES_ANCLAJE,
    de los planos "Big Pedestal Concrete Base ASSY" y "Power Tower
    Concrete Base ASSY" de Flower Turbines).

    SIMPLIFICACION CONSERVADORA, no un analisis de grupo de pernos
    riguroso: se trata el patron como una cupla pura en el ancho exterior
    del patron (brazo de palanca = ancho_patron_m), con la MITAD de los
    pernos resistiendo en tension del lado que se levanta. Un analisis
    real de grupo de anclajes (ACI 318 Apendice D o equivalente) usaria
    la posicion exacta de cada perno y el eje neutro real, no una cupla
    simple -- eso, y la capacidad admisible de cada varilla M18 (fluencia
    + arranque del concreto), es responsabilidad del ingeniero civil que
    los propios planos de Flower Turbines señalan explicitamente
    ("CONCRETE BASE DIMENSIONS AND OTHER PROPERTIES WILL BE PROVIDED BY A
    CIVIL ENGINEER, NOT IN RESPONSIBILITY OF FLOWER TURBINES"). Esta
    funcion calcula DEMANDA (cuanta tension pide el viento), NO evalua
    capacidad ni adecuacion de los pernos.

    Devuelve la tension (N) en el perno mas cargado.
    """
    n_pernos_tension = max(n_pernos // 2, 1)
    return mw / (ancho_patron_m * n_pernos_tension)


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

    print()
    print("=" * 78)
    print("Segundo chequeo de plausibilidad -- 3-meter AL13 Side Forces at 50 mps.pdf")
    print("(dato real: F=13,000 N, Torque=31,200 N*m a 50 m/s, area transversal ~5 m^2,")
    print("altura total 4.4 m). NO se fuerza a que coincida -- se reporta la comparacion tal cual:")
    cd_efectivo_al13 = 13000 / (0.5 * 1.225 * 5.0 * 50.0 ** 2)
    print(f"  Cd efectivo implicito (con A=5 m^2): {cd_efectivo_al13:.2f}")
    print("  Esto NO coincide con el Cd~2.2 efectivo encontrado en External Load Calculations")
    print("  2m&5m.pdf -- es mas cercano a un promedio de las dos caras (1.2 y 2.3 -> 1.75) que")
    print("  al peor caso solo. Posible causa: \"cross-sectional blade area\" en este documento no")
    print("  es necesariamente el mismo D*H usado en el resto de la Pista B (podria ser el area")
    print("  real proyectada de las palas, distinta de la caja envolvente diametro x altura).")
    print("  Diferencia real entre fuentes, documentada aqui, NO resuelta -- necesitaria la")
    print("  geometria CAD real de la pala para reconciliarse con confianza.")

    print()
    print("=" * 78)
    print("Demanda de tension en pernos de anclaje -- Large Tulip, con el patron REAL del plano")
    print("\"Big Pedestal Concrete Base ASSY\" (12x M18x2.5, patron 874.4x874.4mm):")
    r_large = calcular_cargas_viento_asce7(v_rafaga=40.0, altura_techo_m=0.0,
                                            diametro=2.50, altura_pala=5.0, cd_max=2.3)
    patron = PATRONES_ANCLAJE["large_tulip"]
    t_max = tension_maxima_pernos(r_large["Mw_Nm"], patron["n_pernos"], patron["ancho_patron_m"])
    print(f"  Mw (Large Tulip, rafaga 40 m/s, a nivel de piso): {r_large['Mw_Nm']/1000:.2f} kN*m")
    print(f"  Tension maxima estimada por perno (mitad de {patron['n_pernos']} en traccion,")
    print(f"  brazo={patron['ancho_patron_m']*1000:.0f}mm): {t_max:.0f} N ({t_max/1000:.2f} kN)")
    print("  ADVERTENCIA: esto es DEMANDA (lo que pide el viento), no una evaluacion de si el")
    print("  perno M18x2.5 aguanta -- esa capacidad (fluencia + arranque del concreto) es")
    print("  responsabilidad del ingeniero civil, tal como señalan los propios planos de")
    print("  Flower Turbines. No se afirma aqui que el anclaje sea adecuado o inadecuado.")

    print()
    print("=" * 78)
    print("Base de las turbinas PEQUEÑAS (Medium Tulip, 3-M Tulip) -- plano real")
    print("\"Small Pedestal Concrete Base ASSY\" (12x M14x2, patron 602.5x602.5mm):")
    r_3m = calcular_cargas_viento_asce7(v_rafaga=40.0, altura_techo_m=0.0,
                                         diametro=1.80, altura_pala=3.0, cd_max=2.3)
    patron_3m = PATRONES_ANCLAJE["three_m_tulip"]
    t_max_3m = tension_maxima_pernos(r_3m["Mw_Nm"], patron_3m["n_pernos"], patron_3m["ancho_patron_m"])
    print(f"  Mw (3-M Tulip, rafaga 40 m/s, a nivel de piso): {r_3m['Mw_Nm']/1000:.2f} kN*m")
    print(f"  Tension maxima estimada por perno: {t_max_3m:.0f} N ({t_max_3m/1000:.2f} kN)")
    print("  NOTA: \"Small Pedestal\" es el nombre de TAMAÑO DE BASE (vs. \"Big Pedestal\"), no el")
    print("  producto \"Small Tulip\" (0.55m diametro, 1.15m pala) -- cubre Medium y 3-M Tulip.")
    print("  No hay plano de base documentado todavia especificamente para el Small Tulip.")

    print()
    print("=" * 78)
    print("Tercer chequeo -- Calculation of forces.pdf, un diagrama de cuerpo libre real con")
    print("reacciones en la base (probable 3-M Tulip: W=3.9kN=400kg coincide con la ficha")
    print("tecnica; T aplicado a 2.35m coincide con la mitad de la altura de pala + pedestal):")
    print("  Datos del documento: T=1.08 kN a 30 m/s, W=3.9 kN, R1=1.44 kN, R2=5.34 kN")
    print(f"  Chequeo 1 -- equilibrio vertical simple, R1+R2 debe ser = W:")
    print(f"    R1+R2 = {1.44+5.34:.2f} kN  vs  W = 3.9 kN  -- NO COINCIDEN (diferencia 2.88 kN).")
    print("    No se fuerza una explicacion: R1/R2 podrian no ser reacciones verticales puras")
    print("    (la base es tipo tripode/patas, no la placa+pernos de los otros planos -- un")
    print("    diagrama 2D con 2 reacciones etiquetadas puede no equivaler a un simple balance")
    print("    de 2 apoyos verticales). Documentado como pregunta abierta, no resuelta aqui.")
    cd_calc_forces = 1080 / (0.5 * 1.225 * 1.8 * 3.0 * 30.0 ** 2)
    print(f"  Chequeo 2 -- Cd efectivo implicito en T=1.08kN (con A=D*H=5.4 m^2 del 3-M Tulip):")
    print(f"    Cd efectivo = {cd_calc_forces:.2f}  -- MUY por debajo de 2.3 (peor caso) o incluso")
    print("    del Cd~2.21 encontrado en External Load Calculations para el \"3m Turbine\"")
    print("    (cuyo Frotor a 30 m/s es 2.7 kN, 2.5x mas que este T=1.08 kN).")
    print("  Hipotesis mas probable (NO confirmada): este documento podria representar un caso")
    print("  de carga distinto -- empuje de OPERACION normal (rotor girando, generando")
    print("  sustentacion, no un cuerpo romo estatico) en vez del caso extremo de \"ambas palas")
    print("  totalmente cargadas\" que usa External Load Calculations. Discrepancia real entre")
    print("  documentos internos de Flower Turbines, documentada, no resuelta con los datos")
    print("  disponibles -- no se uso este valor de T en el modulo, se dejo como hallazgo.")

    print()
    print("=" * 78)
    print("Extension a mas modelos (Hallazgo 12) -- Small Tulip (D=0.55m, H=1.149m):")
    r_small = calcular_cargas_viento_asce7(v_rafaga=40.0, altura_techo_m=0.0,
                                            diametro=0.55, altura_pala=1.149, cd_max=2.3)
    print(f"  Fw: {r_small['Fw_N']:.1f} N   Mw: {r_small['Mw_Nm']:.1f} N*m   "
          f"fs: {r_small['fs_Hz']:.3f} Hz")
    print("  SIN demanda de anclaje: no existe todavia un plano de base de concreto con pernos")
    print("  para este modelo especifico (PATRONES_ANCLAJE no tiene entrada 'small_tulip').")
    print("  El 'EcoRoof Energy Hub' (Hallazgo 11) monta el Small Tulip SIN perforar/anclar --")
    print("  peso + friccion, un tipo de analisis distinto (presion de apoyo distribuida sobre")
    print("  el techo, 185-207 kg/m2 segun el propio manual) que este modulo no calcula todavia.")
    print("  Fw/Mw de arriba son utiles si en cambio se monta en poste (como el de Medium Tulip,")
    print("  0.1m dia x 2.44m, Hallazgo 11) -- no se asume cual instalacion aplica.")

    print()
    print("=" * 78)
    print("AL13 Power Tower -- stack de 4 modulos (donde empieza a llevar poste estabilizador),")
    print("D=1.7m (ancho FAQ; el propio manual tambien dice 1.6m en otra pagina -- Hallazgo 11,")
    print("no resuelto, se usa el mas ancho por ser conservador), H=4x1m=4.0m:")
    r_al13 = calcular_cargas_viento_asce7(v_rafaga=40.0, altura_techo_m=0.0,
                                           diametro=1.7, altura_pala=4.0, cd_max=2.3)
    patron_al13 = PATRONES_ANCLAJE["al13_power_tower"]
    t_max_al13 = tension_maxima_pernos(r_al13["Mw_Nm"], patron_al13["n_pernos"],
                                        patron_al13["ancho_patron_m"])
    print(f"  Fw: {r_al13['Fw_N']:.1f} N ({r_al13['Fw_N']/1000:.2f} kN)   "
          f"Mw: {r_al13['Mw_Nm']/1000:.2f} kN*m")
    print(f"  Tension maxima estimada por perno (patron 'Power Tower Concrete Base ASSY',")
    print(f"  12x M18x2.5, {patron_al13['ancho_patron_m']*1000:.0f}mm): "
          f"{t_max_al13:.0f} N ({t_max_al13/1000:.2f} kN)")
    print("  MISMA ADVERTENCIA que en los demas modelos: esto es demanda, no capacidad. Cd=2.3")
    print("  tampoco esta re-verificado especificamente para la pala de aluminio del AL13 --")
    print("  se hereda del mismo supuesto que Tulip por ser tambien VAWT de 2 palas.")

    print()
    print("=" * 78)
    print("Primera aproximacion a carga de CLUSTER (Hallazgo 11: reglas reales de espaciamiento,")
    print("SIN modelo CFD de apantallamiento -- ver docstring de cargas_viento_cluster_asce7):")
    r_cluster = cargas_viento_cluster_asce7(v_rafaga=40.0, altura_techo_m=10.0, diametro=1.18,
                                             altura_pala=2.0, cd_max=2.3, n_turbinas=5)
    print(f"  Bouquet de 5 Medium Tulip (D=1.18m) sobre techo a 10m, rafaga 40 m/s:")
    print(f"    Fw individual: {r_cluster['individual']['Fw_N']:.1f} N   "
          f"Fw TOTAL (5x, sin apantallamiento): {r_cluster['Fw_total_N']:.1f} N "
          f"({r_cluster['Fw_total_N']/1000:.2f} kN)")
    print(f"    Espaciamiento ideal eje-a-eje: {r_cluster['espaciamiento_ideal_m']:.2f} m "
          f"(=1.25 x diametro)")
    print(f"    Ancho aproximado de la fila completa: {r_cluster['ancho_fila_aprox_m']:.2f} m")
    print("  NOTA: Fw_total es conservador (suma simple, sin restar apantallamiento aerodinamico)")
    print("  -- correcto para dimensionar una estructura de soporte compartida, pero NO intenta")
    print("  predecir generacion de energia del cluster (eso lo cubre power_in_bouquet(), Efecto")
    print("  Bouquet real, que va en sentido contrario: MAS potencia por turbina, no menos).")
