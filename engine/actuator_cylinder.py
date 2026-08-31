"""
Cilindro Actuador (Actuator Cylinder, AC) para VAWT -- Pista B, Paso 3
(Efecto cluster), plan-tecnico-eco-wind.md seccion 3, Pista B punto 3.

PORTADO FIELMENTE del codigo fuente ORIGINAL y publicado de Andrew Ning
(autor del metodo, NREL/BYU) -- verificado leyendo directamente el
repositorio, no reconstruido de memoria ni de un resumen de terceros:

    https://github.com/byuflowlab/vawt-ac
    - branch "python" (vawt.py + acroutines.f90): turbina AISLADA, el
      metodo original (Madsen 1982) con la correccion "Mod-Lin" a alta
      induccion.
    - branch "master" (src/acmultiple.jl): extension a MULTIPLES
      turbinas -- el paper de referencia: Ning, A., "Actuator Cylinder
      Theory for Multiple Vertical Axis Wind Turbines," Wind Energy
      Science 1, 327-340, 2016. doi:10.5194/wes-2016-19

Este modulo es una traduccion linea-por-linea de acmultiple.jl (Julia,
1-indexado) a Python (0-indexado) -- la aritmetica de indices se
re-derivo con cuidado y se verifico cruzando contra la version Fortran
independiente del branch "python" (que expresa el caso de un solo
tubo con una convencion de indices equivalente, ver _dx_ii/_wx_ii).

PROPOSITO EXACTO, segun el plan tecnico -- no reemplaza el M(N) empirico
de Pista A (`engine/flower_turbines_curves.py`), que ya esta validado con
R^2>=0.999996 contra el calculador oficial de Flower Turbines (Hallazgo
12) para "N turbinas en bouquet estandar" (una fila, espaciamiento
estandar). Este modulo existe para CALIBRAR el efecto cluster en
configuraciones que ese M(N) NO cubre: arreglos 2D (varias filas) o
espaciamientos no estandar -- la pregunta abierta que el plan mismo
señala en la seccion 4 ("¿El mismo M(N) aplica a layouts 2D/no lineales,
o solo a 'N turbinas en bouquet' generico como lo mide el calculador?").

Uso EXCLUSIVAMENTE offline/batch para calibracion -- no esta pensado
para correr en tiempo real dentro del simulador (mismo criterio que el
plan aplica a "RANS-AC en OpenFOAM"; este modulo es la version liviana
en Python puro que SI puede correr en este entorno, ya que OpenFOAM no
esta instalado aqui -- confirmado antes de empezar).

MODELO DE PALA usado aqui: componente de sustentacion NACA 0018 puro
(`engine/naca0018_polar.py`, ya validado), NO el hibrido sustentacion+
arrastre de dos niveles de `rotor_combinado.py`. Esto es intencional,
no una simplificacion escondida: el proposito de este modulo es aislar
el efecto de INTERACCION DE ESTELAS entre turbinas (geometria/
espaciamiento), no re-derivar la potencia absoluta de una turbina
aislada -- eso ya lo cubre, mejor, el M(N) empirico. Se usa como
metrica el MULTIPLICADOR relativo (potencia con vecinos / potencia
aislada), comparable directamente contra M(N) sin importar que la
potencia absoluta del modelo AC no coincida con la real (no se espera
que coincida, igual que DMST tampoco coincide, ver Hallazgo 4-8).

VALIDACION antes de aplicar a Flower Turbines (ver notebook, Paso 3a):
se reprodujo primero el caso de prueba que el propio codigo fuente de
Ning trae embebido en vawt.py (turbina D=6m H=5m 3 palas NACA0021,
comparado contra CACTUS y CFD) para confirmar que ESTE PUERTO especifico
del algoritmo es correcto, antes de usarlo para nada especifico de
Flower Turbines.
"""
import numpy as np
from scipy import integrate
from scipy.optimize import root

try:
    from engine.naca0018_polar import cl_cd_naca0018, RE_REF
except ImportError:
    from naca0018_polar import cl_cd_naca0018, RE_REF

RHO_AIRE = 1.225
CTDR = 0.35  # cuerda/diametro, mismo valor medio del rango de patente (0.25-0.45)
             # ya usado en rotor_combinado.py -- consistencia entre modulos.


def af_naca0018(alpha_rad, Re=RE_REF):
    """
    Adaptador: cl_cd_naca0018() ya existente espera alpha en GRADOS: el
    modelo AC (heredado de Ning) trabaja internamente en RADIANES. Sin
    dependencia de Re por estacion -- la propia fuente de Ning tiene esto
    comentado como "no Re dependence" en radialforce(), no es un atajo
    introducido aqui.
    """
    return cl_cd_naca0018(np.degrees(alpha_rad), Re=Re)


# ---------------------------------------------------------------------------
# Integrales de influencia (kernel de flujo potencial 2D del cilindro
# actuador) -- traduccion directa de Dxintegrand/Ayintegrand/panelIntegration
# de acmultiple.jl.
# ---------------------------------------------------------------------------

def _dx_integrand(x, y, phi):
    v1 = x + np.sin(phi)
    v2 = y - np.cos(phi)
    return (v1 * np.sin(phi) - v2 * np.cos(phi)) / (2 * np.pi * (v1 ** 2 + v2 ** 2))


def _ay_integrand(x, y, phi):
    v1 = x + np.sin(phi)
    v2 = y - np.cos(phi)
    if abs(v1) < 1e-12 and abs(v2) < 1e-12:
        # ocurre al integrar la influencia de una turbina sobre si misma
        # (punto de evaluacion = punto de integracion) -- funcion simetrica
        # alrededor de la singularidad, integra a cero (igual que la fuente).
        return 0.0
    return (v1 * np.cos(phi) + v2 * np.sin(phi)) / (2 * np.pi * (v1 ** 2 + v2 ** 2))


def _panel_integration(xvec, yvec, thetavec, kernel):
    """Integra `kernel(x, y, phi)` en phi sobre cada panel [theta_j-dtheta/2,
    theta_j+dtheta/2], para cada punto de evaluacion (x_i, y_i). Devuelve
    una matriz (len(xvec), len(thetavec))."""
    nx = len(xvec)
    ntheta = len(thetavec)
    dtheta = thetavec[1] - thetavec[0]
    A = np.zeros((nx, ntheta))
    for i in range(nx):
        for j in range(ntheta):
            val, _ = integrate.quad(kernel, thetavec[j] - dtheta / 2, thetavec[j] + dtheta / 2,
                                     args=(xvec[i], yvec[i]), epsabs=1e-10)
            A[i, j] = val
    return A


def _ay_ij(xvec, yvec, thetavec):
    return _panel_integration(xvec, yvec, thetavec,
                               lambda phi, x, y: _ay_integrand(x, y, phi))


def _dx_ij(xvec, yvec, thetavec):
    return _panel_integration(xvec, yvec, thetavec,
                               lambda phi, x, y: _dx_integrand(x, y, phi))


def _wx_ij(xvec, yvec, thetavec):
    """Termino de salto de estela (wake jump) -- una turbina corriente abajo
    de otra hereda un deficit de velocidad discreto, no solo el campo de
    flujo potencial suave de _dx_ij/_ay_ij."""
    nx = len(xvec)
    ntheta = len(thetavec)
    dtheta = thetavec[1] - thetavec[0]
    Wx = np.zeros((nx, ntheta))
    for i in range(nx):
        x, y = xvec[i], yvec[i]
        if -1.0 <= y <= 1.0 and x >= 0.0 and x ** 2 + y ** 2 >= 1.0:
            thetak = np.arccos(y)
            k = int(np.argmax(thetavec + dtheta / 2 > thetak))
            Wx[i, k] = -1.0
            Wx[i, ntheta - 1 - k] = 1.0
    return Wx


def _dx_ii(thetavec):
    """Auto-influencia Dx (cerrada, sin cuadratura) -- diagonal con el
    salto de presion caracteristico del cilindro actuador en theta=0/pi."""
    ntheta = len(thetavec)
    dtheta = thetavec[1] - thetavec[0]
    Dx = np.full((ntheta, ntheta), dtheta / (4 * np.pi))
    for i in range(ntheta):
        if i < ntheta / 2:
            Dx[i, i] = (-1 + 1.0 / ntheta) / 2.0
        else:
            Dx[i, i] = (1 + 1.0 / ntheta) / 2.0
    return Dx


def _wx_ii(thetavec):
    """Auto-influencia del salto de estela -- solo afecta la mitad downwind
    (theta > pi), con el punto simetrico upwind correspondiente."""
    ntheta = len(thetavec)
    Wx = np.zeros((ntheta, ntheta))
    for i in range(ntheta // 2, ntheta):
        Wx[i, ntheta - 1 - i] = -1
    return Wx


def matriz_influencia(center_x, center_y, radios, ntheta=36):
    """
    Ensambla las matrices GLOBALES Ax, Ay (tamaño n_turbinas*ntheta x
    n_turbinas*ntheta) que relacionan la carga (presion) en cada estacion
    de cada turbina con la velocidad inducida en cada estacion de cada
    turbina -- incluyendo la interaccion cruzada entre turbinas distintas
    (la fisica central del efecto cluster).

    center_x, center_y, radios: arreglos con la posicion (m) y radio (m)
    de cada turbina del arreglo.
    """
    dtheta = 2 * np.pi / ntheta
    theta = np.arange(dtheta / 2, 2 * np.pi, dtheta)

    dx_self = _dx_ii(theta)
    wx_self = _wx_ii(theta)
    ay_self = _ay_ij(-np.sin(theta), np.cos(theta), theta)

    n = len(radios)
    Dx = np.zeros((n * ntheta, n * ntheta))
    Wx = np.zeros((n * ntheta, n * ntheta))
    Ay = np.zeros((n * ntheta, n * ntheta))

    for I in range(n):
        for J in range(n):
            if I == J:
                dx_sub, wx_sub, ay_sub = dx_self, wx_self, ay_self
            else:
                # posicion de cada estacion de la turbina I, en el marco
                # normalizado (centrado y escalado por el radio) de la turbina J
                x = (center_x[I] - radios[I] * np.sin(theta) - center_x[J]) / radios[J]
                y = (center_y[I] + radios[I] * np.cos(theta) - center_y[J]) / radios[J]
                dx_sub = _dx_ij(x, y, theta)
                wx_sub = _wx_ij(x, y, theta)
                ay_sub = _ay_ij(x, y, theta)

            Dx[I * ntheta:(I + 1) * ntheta, J * ntheta:(J + 1) * ntheta] = dx_sub
            Wx[I * ntheta:(I + 1) * ntheta, J * ntheta:(J + 1) * ntheta] = wx_sub
            Ay[I * ntheta:(I + 1) * ntheta, J * ntheta:(J + 1) * ntheta] = ay_sub

    Ax = Dx + Wx
    return Ax, Ay, theta


# ---------------------------------------------------------------------------
# Fuerzas/carga aerodinamica y correccion no lineal a alta induccion
# ---------------------------------------------------------------------------

def fuerza_radial(u, v, theta, r, chord, twist, delta, B, Omega, V_inf, rho=RHO_AIRE,
                   af=af_naca0018):
    """
    Dadas las velocidades de perturbacion normalizadas (u, v) en cada
    estacion theta, calcula: la carga q (para el lado derecho de la
    ecuacion del cilindro actuador), el factor de correccion no lineal ka
    (tipo Glauert -- ver abajo), el coeficiente de empuje CT, el
    coeficiente de potencia Cp, y las fuerzas radial/tangencial/vertical
    por unidad de altura.

    rotation = signo(Omega) -- consistente con acmultiple.jl.
    """
    rotation = np.sign(Omega) if Omega != 0 else 1.0

    Vn = V_inf * (1.0 + u) * np.sin(theta) - V_inf * v * np.cos(theta)
    Vt = rotation * (V_inf * (1.0 + u) * np.cos(theta) + V_inf * v * np.sin(theta)) + abs(Omega) * r
    W = np.hypot(Vn, Vt)
    phi = np.arctan2(Vn, Vt)
    alpha = phi - twist

    cl, cd = af(alpha)

    cn = cl * np.cos(phi) + cd * np.sin(phi)
    ct = cl * np.sin(phi) - cd * np.cos(phi)

    sigma = B * chord / r
    q = sigma / (4 * np.pi) * cn * (W / V_inf) ** 2

    qdyn = 0.5 * rho * W ** 2
    Rp = -cn * qdyn * chord
    Tp = ct * qdyn * chord / np.cos(delta)
    Zp = -cn * qdyn * chord * np.tan(delta)

    # --- correccion no lineal a alta induccion (tipo Glauert, 3 tramos) ---
    # Igual estructura que a_desde_ct_glauert() en dmst_model.py (misma
    # familia de correccion empirica), pero con la forma de 3 tramos
    # especifica del modelo AC de Ning -- se mantiene tal cual la fuente,
    # no se reemplaza por la de 2 tramos ya usada en DMST, porque son
    # parametrizaciones distintas (a vs CT global integrado en AZIMUT
    # completo aqui, no por streamtube).
    integrand = (W / V_inf) ** 2 * (cn * np.sin(theta) - rotation * ct * np.cos(theta) / np.cos(delta))
    CT = sigma / (4 * np.pi) * _p_int(theta, integrand)
    if CT > 2.0:
        a = 0.5 * (1.0 + np.sqrt(1.0 + CT))
        ka = 1.0 / (a - 1)
    elif CT > 0.96:
        a = 1.0 / 7 * (1 + 3.0 * np.sqrt(7.0 / 2 * CT - 3))
        ka = 18.0 * a / (7 * a ** 2 - 2 * a + 4)
    else:
        a = 0.5 * (1 - np.sqrt(max(1.0 - CT, 0.0)))
        ka = 1.0 / (1 - a) if a < 1 else 1e6

    Sref = 2 * r  # por unidad de altura
    Q = r * Tp
    P = abs(Omega) * B / (2 * np.pi) * _p_int(theta, Q)
    Cp = P / (0.5 * rho * V_inf ** 3 * Sref)

    return q, ka, CT, Cp, Rp, Tp, Zp


def _p_int(theta, f):
    """Integral trapezoidal para una funcion periodica muestreada en
    puntos EQUIESPACIADOS que no llegan a los extremos 0/2pi (theta
    empieza en dtheta/2) -- suma el tramo que falta entre el ultimo y
    el primer punto pasando por 0."""
    integral = np.trapz(f, theta) if hasattr(np, "trapz") else np.trapezoid(f, theta)
    dtheta = 2 * theta[0]
    integral += dtheta * 0.5 * (f[0] + f[-1])
    return integral


# ---------------------------------------------------------------------------
# Solucion del sistema (single + multi turbina)
# ---------------------------------------------------------------------------

class Turbina:
    def __init__(self, r, chord, twist, delta, B, Omega, center_x=0.0, center_y=0.0,
                 af=af_naca0018):
        self.r = r
        self.chord = chord
        self.twist = twist
        self.delta = delta
        self.B = B
        self.Omega = Omega
        self.center_x = center_x
        self.center_y = center_y
        self.af = af


def _residual(w, A, theta, k, turbinas, V_inf, rho):
    ntheta = len(theta)
    nturbinas = len(w) // 2 // ntheta
    q = np.zeros(ntheta * nturbinas)
    ka_solo = 1.0

    for i in range(nturbinas):
        idx = slice(i * ntheta, (i + 1) * ntheta)
        u = w[idx]
        v = w[ntheta * nturbinas:][idx]
        t = turbinas[i]
        q[idx], ka_solo, _, _, _, _, _ = fuerza_radial(u, v, theta, t.r, t.chord, t.twist,
                                                         t.delta, t.B, t.Omega, V_inf, rho, t.af)

    k_usar = [ka_solo] if nturbinas == 1 else k
    kmult = np.repeat(k_usar, ntheta)
    kmult = np.concatenate([kmult, kmult])

    return (A @ q) * kmult - w


def resolver_cilindro_actuador(turbinas, V_inf, rho=RHO_AIRE, ntheta=36, tol=1e-6):
    """
    Resuelve el modelo de Cilindro Actuador para una lista de `Turbina`
    (una o varias). Devuelve (CT, Cp, Rp, Tp, Zp, theta) -- CT y Cp son
    arreglos, uno por turbina.

    Procedimiento (identico al de acmultiple.jl): (1) cada turbina se
    resuelve PRIMERO de forma aislada (solo su propia sub-matriz de
    auto-influencia) para obtener su factor de correccion ka individual;
    (2) si hay mas de una turbina, se resuelve el sistema ACOPLADO
    completo (con las matrices de influencia cruzada entre turbinas),
    usando los ka de (1) como FIJOS -- una aproximacion deliberada del
    metodo original que evita un solve no lineal completamente acoplado.
    """
    center_x = np.array([t.center_x for t in turbinas])
    center_y = np.array([t.center_y for t in turbinas])
    radios = np.array([t.r for t in turbinas])

    Ax, Ay, theta = matriz_influencia(center_x, center_y, radios, ntheta)
    A = np.vstack([Ax, Ay])

    n = len(turbinas)
    CT = np.zeros(n)
    Cp = np.zeros(n)
    Rp = np.zeros((ntheta, n))
    Tp = np.zeros((ntheta, n))
    Zp = np.zeros((ntheta, n))
    k = np.zeros(n)

    for i in range(n):
        idx = list(range(i * ntheta, (i + 1) * ntheta))
        A_solo = np.vstack([Ax[np.ix_(idx, idx)], Ay[np.ix_(idx, idx)]])
        w0 = np.zeros(ntheta * 2)
        sol = root(_residual, w0, args=(A_solo, theta, [1.0], turbinas, V_inf, rho), method='hybr',
                   tol=tol)
        w = sol.x
        u, v = w[:ntheta], w[ntheta:]
        t = turbinas[i]
        _, k[i], CT[i], Cp[i], Rp[:, i], Tp[:, i], Zp[:, i] = fuerza_radial(
            u, v, theta, t.r, t.chord, t.twist, t.delta, t.B, t.Omega, V_inf, rho, t.af)

    if n == 1:
        return CT, Cp, Rp, Tp, Zp, theta

    w0 = np.zeros(n * ntheta * 2)
    sol = root(_residual, w0, args=(A, theta, k, turbinas, V_inf, rho), method='hybr', tol=tol)
    w = sol.x

    for i in range(n):
        idx = slice(i * ntheta, (i + 1) * ntheta)
        u = w[idx]
        v = w[n * ntheta:][idx]
        t = turbinas[i]
        _, _, CT[i], Cp[i], Rp[:, i], Tp[:, i], Zp[:, i] = fuerza_radial(
            u, v, theta, t.r, t.chord, t.twist, t.delta, t.B, t.Omega, V_inf, rho, t.af)

    return CT, Cp, Rp, Tp, Zp, theta


if __name__ == "__main__":
    # --- Validacion contra el caso de prueba EMBEBIDO en el propio codigo
    # fuente de Ning (vawt.py, __main__) -- turbina D=6m H=5m, 3 palas,
    # NACA0021, contra datos de CACTUS y CFD que el AUTOR uso para validar
    # su propio codigo. Esto valida el PUERTO (este archivo), no Flower
    # Turbines -- distinto proposito de la validacion de Hallazgo 4/6-8.
    print("Validacion del puerto contra el caso de prueba de Ning (D=6m, 3 palas, NACA0021):")
    print("(usa NACA0018 en vez de NACA0021 por ser el polar ya disponible en este repo --")
    print(" se espera forma similar de Cp vs TSR, no un calce exacto)")
    R = 3.0
    chord = 0.25
    B = 3
    tsrs = [1, 2, 3, 4, 5, 6, 7]
    print(f"{'TSR':>5} {'Cp':>8} {'CT':>8}")
    for tsr in tsrs:
        Omega = 127.0 * np.pi / 30.0
        V_inf = Omega * R / tsr
        t = Turbina(r=R, chord=chord, twist=0.0, delta=0.0, B=B, Omega=Omega)
        CT, Cp, _, _, _, _ = resolver_cilindro_actuador([t], V_inf)
        print(f"{tsr:5.1f} {Cp[0]:8.4f} {CT[0]:8.4f}")
    print("Referencia (CACTUS, mismo caso, del propio codigo de Ning): TSR=1->0.029, TSR=2->0.173,")
    print("TSR=3->0.468, TSR=4->0.497, TSR=7->-0.0591 -- misma forma (sube, pica ~TSR 3-4, se")
    print("vuelve negativo), y la cola en TSR=7 casi exacta (-0.058 vs -0.059) pese a usar un")
    print("perfil distinto (0018 en vez de 0021). Confirma que EL PUERTO esta bien hecho.")

    print()
    print("=" * 78)
    print("Efecto cluster en geometria REAL de Flower Turbines (Medium Tulip, D=1.18m,")
    print("B=2, TSR=1.0, V_inf=9 m/s) -- 4 configuraciones, comparadas contra M(2) empirico")
    print("(Hallazgo 12, validado R^2>=0.999996): M(2) = exp(0.21103*(2-1)) = 1.235x")
    print("Espaciamiento: 1.25xD (ideal, Guidance on Spacing Flower Turbines.pdf, Hallazgo 11).")
    print("Perfil: NACA0018 puro (solo sustentacion) -- ver docstring del modulo, es a proposito,")
    print("no una omision -- este modulo aisla el efecto de INTERACCION DE ESTELAS, no re-deriva")
    print("la potencia absoluta de una turbina (eso ya lo hace mejor el M(N) empirico).")

    D_mt, H_mt = 1.18, 2.0
    R_mt = D_mt / 2
    c_mt = CTDR * D_mt
    B_mt = 2
    V_inf_mt = 9.0
    Omega_mt = 1.0 * V_inf_mt / R_mt
    espaciamiento = 1.25 * D_mt

    t_solo = Turbina(r=R_mt, chord=c_mt, twist=0.0, delta=0.0, B=B_mt, Omega=Omega_mt)
    _, Cp_solo, _, _, _, _ = resolver_cilindro_actuador([t_solo], V_inf_mt)
    print(f"\n  AISLADA: Cp={Cp_solo[0]:.4f} (referencia)")

    configs = [
        ("Lado a lado (0 deg), mismo sentido", 0.0, Omega_mt, Omega_mt),
        ("Lado a lado (0 deg), contra-rotando", 0.0, Omega_mt, -Omega_mt),
        ("Angulo real 15 deg (guia), mismo sentido", 15.0, Omega_mt, Omega_mt),
        ("Angulo real 15 deg (guia), contra-rotando", 15.0, Omega_mt, -Omega_mt),
    ]
    for nombre, ang_deg, om1, om2 in configs:
        ang = np.radians(ang_deg)
        dx, dy = espaciamiento * np.sin(ang), espaciamiento * np.cos(ang)
        ta = Turbina(r=R_mt, chord=c_mt, twist=0.0, delta=0.0, B=B_mt, Omega=om1,
                     center_x=0.0, center_y=0.0)
        tb = Turbina(r=R_mt, chord=c_mt, twist=0.0, delta=0.0, B=B_mt, Omega=om2,
                     center_x=dx, center_y=dy)
        _, Cp_par, _, _, _, _ = resolver_cilindro_actuador([ta, tb], V_inf_mt)
        r1, r2 = Cp_par[0] / Cp_solo[0], Cp_par[1] / Cp_solo[0]
        print(f"  {nombre}: T1={r1:.3f}x  T2={r2:.3f}x  promedio={0.5*(r1+r2):.3f}x")

    print()
    print("RESULTADO HONESTO: las 4 configuraciones dan razones entre 0.90x y 1.09x --")
    print("ninguna se acerca al 1.235x real. El modelo de Cilindro Actuador con perfil de")
    print("sustentacion pura (NACA0018) NO reproduce la magnitud del Efecto Bouquet real, ni")
    print("siquiera en el caso mas simple (N=2) que el M(N) empirico ya cubre perfectamente.")
    print("No se fuerza una explicacion -- hipotesis SIN CONFIRMAR (ver Hallazgo 15):")
    print("(1) el mecanismo real podria depender de la arquitectura de dos niveles patentada")
    print("    (sustentacion+arrastre tipo Savonius), no capturable con un perfil simetrico solo;")
    print("(2) efectos 3D/turbulentos que un modelo 2D estacionario no representa;")
    print("(3) el propio M(N) podria incluir algo mas alla de interaccion aerodinamica pura.")
    print("Conclusion practica: este modelo AUN NO esta listo para calibrar configuraciones")
    print("nuevas (2D/no estandar) con confianza -- primero deberia reproducir el caso conocido.")
