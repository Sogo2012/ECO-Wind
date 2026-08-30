"""
DMST (Double-Streamtube) para un rotor VAWT de eje vertical, 2 palas.
Variante simplificada (un factor de induccion para todo el semicirculo
upwind, otro para todo el downwind) del metodo Multiple-Streamtube de
Paraschivoiu -- mas simple que el de muchos sub-streamtubes por azimut,
pero conserva el acoplamiento upwind/downwind (la fisica central del
metodo "double").
"""
import numpy as np

try:
    from engine.naca0018_polar import cl_cd_naca0018, RE_REF  # import como paquete (notebooks)
    from engine.polar_hibrido import cl_cd_hibrido
except ImportError:
    from naca0018_polar import cl_cd_naca0018, RE_REF  # ejecucion directa (python3 dmst_model.py)
    from polar_hibrido import cl_cd_hibrido

_trapz = getattr(np, "trapezoid", None) or np.trapz  # numpy >=2.0 renombro trapz

RHO_AIRE = 1.225  # kg/m^3, nivel del mar (ajustar despues por densidad/altitud CR)
NU_AIRE = 1.46e-5  # m^2/s, viscosidad cinematica del aire ~15-20C


def fuerzas_azimut(theta, u, Omega, R, c, rho=RHO_AIRE, cd_extra=0.0, nu=NU_AIRE,
                    re_dependiente=True, polar="naca"):
    """
    Fuerza tangencial (Ft, N/m de altura de pala) y fuerza en x (Fx, N/m)
    sobre UNA pala en la posicion azimutal theta, con velocidad axial local
    u en el disco (m/s).

    cd_extra: arrastre adicional sumado al Cd del perfil -- OJO, el atajo de
    usar esto para representar el componente Savonius da potencia negativa
    (ver notebook Pista B Paso 4); dejar en 0.0 salvo para reproducir ese
    hallazgo. Para el componente de arrastre real, usar polar="hibrido".

    re_dependiente: si es False, usa el polar "de libro" (Re=RE_REF fijo,
    sin la correccion de Reynolds) -- para poder comparar con/sin la
    correccion de forma limpia.

    polar: "naca" = NACA 0018 simetrico puro (solo sustentacion). "hibrido"
    = polar asimetrico (Cd->2.3 cara concava, Cd->1.2 cara convexa) que
    representa sustentacion Y arrastre tipo Savonius en el MISMO elemento
    de pala, en vez de sumar dos mecanismos separados.
    """
    t_hat = np.array([-np.sin(theta), np.cos(theta)])

    Wx = u + Omega * R * np.sin(theta)
    Wy = -Omega * R * np.cos(theta)
    W = np.hypot(Wx, Wy)
    W = max(W, 1e-6)
    W_hat = np.array([Wx / W, Wy / W])

    Wt = Wx * t_hat[0] + Wy * t_hat[1]
    Wn = Wx * np.cos(theta) + Wy * np.sin(theta)
    alpha = np.degrees(np.arctan2(Wn, -Wt))

    Re_local = (W * c / nu) if re_dependiente else RE_REF
    funcion_polar = cl_cd_hibrido if polar == "hibrido" else cl_cd_naca0018
    cl, cd = funcion_polar(alpha, Re=Re_local)
    cd = cd + cd_extra

    q = 0.5 * rho * W ** 2 * c
    D_vec = q * cd * W_hat
    L_hat = np.array([-W_hat[1], W_hat[0]])
    L_vec = q * cl * L_hat
    F = D_vec + L_vec

    Ft = F[0] * t_hat[0] + F[1] * t_hat[1]
    Fx = F[0]
    return Ft, Fx, alpha, W


def _thrust_media(u, Omega, R, c, N, thetas, rho=RHO_AIRE, cd_extra=0.0, re_dependiente=True,
                   polar="naca"):
    Fx_vals = np.array([fuerzas_azimut(th, u, Omega, R, c, rho, cd_extra,
                                        re_dependiente=re_dependiente, polar=polar)[1]
                         for th in thetas])
    return (N / (2 * np.pi)) * _trapz(Fx_vals, thetas)


def resolver_induccion(V_ref, Omega, R, c, N, thetas, rho=RHO_AIRE, cd_extra=0.0,
                        a0=0.2, tol=1e-4, max_iter=100, relax=0.3, re_dependiente=True,
                        polar="naca"):
    """Itera el factor de induccion 'a' para un semicirculo (upwind o downwind),
    balanceando el empuje de disco actuador (2*rho*A*V_ref^2*a(1-a)) contra el
    empuje derivado de las fuerzas de pala."""
    A = 2 * R  # ancho frontal (por unidad de altura); el area completa es A*H
    a = a0
    for _ in range(max_iter):
        u = V_ref * (1 - a)
        T_palas = _thrust_media(u, Omega, R, c, N, thetas, rho, cd_extra, re_dependiente, polar)
        T_momento_coef = T_palas / (0.5 * rho * A * V_ref ** 2) if V_ref > 0 else 0.0  # CT estandar = T/(0.5*rho*A*V^2)
        T_momento_coef = np.clip(T_momento_coef, 0.0, 0.9999)
        a_nuevo = 0.5 * (1 - np.sqrt(max(1 - T_momento_coef, 0.0)))
        a = a + relax * (a_nuevo - a)
        a = np.clip(a, 0.0, 0.49)
        if abs(a_nuevo - a) < tol:
            break
    return a


def resolver_dmst(V_inf, TSR, R, c, N=2, H=1.0, rho=RHO_AIRE, cd_extra=0.0, n_theta=72,
                   re_dependiente=True, polar="naca"):
    """
    Resuelve el DMST de doble tubo de corriente para un V_inf y TSR dados.
    Devuelve potencia (W), Cp, y los factores de induccion.

    re_dependiente: si es False, usa el polar "de libro" (Re=RE_REF fijo en
    todo el barrido) -- para comparar limpio con/sin la correccion de Reynolds.

    polar: "naca" (solo sustentacion, NACA0018 simetrico) o "hibrido" (Cd
    post-perdida asimetrico 2.3/1.2 -- sustentacion Y arrastre tipo Savonius
    en el mismo elemento de pala, ver engine/polar_hibrido.py).
    """
    Omega = TSR * V_inf / R
    thetas_up = np.linspace(-np.pi / 2, np.pi / 2, n_theta // 2)
    thetas_down = np.linspace(np.pi / 2, 3 * np.pi / 2, n_theta // 2)

    a_up = resolver_induccion(V_inf, Omega, R, c, N, thetas_up, rho, cd_extra,
                               re_dependiente=re_dependiente, polar=polar)
    u_up = V_inf * (1 - a_up)
    V_wake = V_inf * (1 - 2 * a_up)
    V_wake = max(V_wake, 0.05 * V_inf)  # evitar wake invertido a induccion muy alta

    a_down = resolver_induccion(V_wake, Omega, R, c, N, thetas_down, rho, cd_extra,
                                 re_dependiente=re_dependiente, polar=polar)
    u_down = V_wake * (1 - a_down)

    Ft_up = np.array([fuerzas_azimut(th, u_up, Omega, R, c, rho, cd_extra,
                                      re_dependiente=re_dependiente, polar=polar)[0]
                       for th in thetas_up])
    Ft_down = np.array([fuerzas_azimut(th, u_down, Omega, R, c, rho, cd_extra,
                                        re_dependiente=re_dependiente, polar=polar)[0]
                         for th in thetas_down])

    Q_up = (N / (2 * np.pi)) * _trapz(Ft_up, thetas_up) * R
    Q_down = (N / (2 * np.pi)) * _trapz(Ft_down, thetas_down) * R
    Q_total = Q_up + Q_down

    potencia = Q_total * Omega * H
    A_rotor = 2 * R * H
    Cp = potencia / (0.5 * rho * A_rotor * V_inf ** 3) if V_inf > 0 else 0.0

    return {"potencia_W": potencia, "Cp": Cp, "a_up": a_up, "a_down": a_down, "Omega": Omega}


if __name__ == "__main__":
    # --- Sanity check: rotor Darrieus/H simetrico "de libro" (sin cd_extra) ---
    # Solidez sigma = N*c/(2R); target ~0.15-0.20 para Cp,max en TSR~4-6 (tipico).
    R = 1.0
    N = 2
    sigma_objetivo = 0.18
    c = sigma_objetivo * 2 * R / N
    V_inf = 8.0

    print(f"Sanity check DMST -- rotor Darrieus NACA0018 puro (sin cd_extra), sigma={sigma_objetivo}")
    print(f"{'TSR':>5}  {'Cp':>7}  {'a_up':>6}  {'a_down':>6}")
    mejores = []
    for TSR in [1, 2, 3, 4, 5, 6, 7, 8]:
        r = resolver_dmst(V_inf, TSR, R, c, N, H=1.0)
        mejores.append((TSR, r["Cp"]))
        print(f"{TSR:5.1f}  {r['Cp']:7.4f}  {r['a_up']:6.3f}  {r['a_down']:6.3f}")

    tsr_opt, cp_max = max(mejores, key=lambda x: x[1])
    print(f"\nCp maximo = {cp_max:.4f} en TSR = {tsr_opt}")
    print("Referencia textbook para H-rotor Darrieus tipico: Cp,max ~0.35-0.40 en TSR~4-6")
