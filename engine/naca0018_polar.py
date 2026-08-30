"""
Polar NACA 0018 via teoria de perfil delgado + extrapolacion post-stall
Viterna-Corrigan. No hay acceso a datos experimentales/XFOIL reales desde
este sandbox (red bloqueada) -- esto es una aproximacion estandar de
ingenieria, no un polar medido.
"""
import numpy as np


def cl_cd_naca0018(alpha_deg, Re=2e5):
    """
    Cl, Cd aproximados para NACA 0018 en funcion del angulo de ataque (grados).

    Region lineal (|alpha| < ~12 grados, antes de stall):
      Cl = 2*pi*sin(alpha) * factor de correccion de espesor (~0.9 para 18% espesor)
      Cd = Cd0 (perfil, ~0.01-0.02 a este Re) + termino inducido pequenio

    Post-stall (|alpha| > alpha_stall): extrapolacion de Viterna-Corrigan,
    que hace tender Cl y Cd hacia el comportamiento de una placa plana a
    90 grados (Cd,max ~= 1.98 para placa plana infinita, formula estandar
    Cd_max = 1.11 + 0.018*AR; para perfil 2D (AR->inf) se usa ~1.98-2.0).
    """
    alpha = np.asarray(alpha_deg, dtype=float)
    alpha_rad = np.radians(alpha)

    # --- Region lineal ---
    alpha_stall = 12.0  # grados, tipico para NACA 0018 a Re~1e5-5e5
    cl_slope = 2 * np.pi * 0.90  # correccion ~10% por espesor finito (18%)
    cd0 = 0.014  # arrastre de perfil a alpha=0, Re~2e5 (orden de magnitud tipico NACA0018)

    cl_lin = cl_slope * np.sin(alpha_rad)
    cd_lin = cd0 + 0.02 * (alpha_rad ** 2)  # crecimiento suave de Cd con AoA (arrastre inducido aprox.)

    cl_stall_val = cl_slope * np.sin(np.radians(alpha_stall))
    cd_stall_val = cd0 + 0.02 * (np.radians(alpha_stall) ** 2)

    # --- Post-stall: Viterna-Corrigan ---
    cd_max = 1.98
    A1 = cd_max / 2
    B1 = cd_max
    A2 = (cl_stall_val - cd_max * np.sin(np.radians(alpha_stall)) * np.cos(np.radians(alpha_stall))) * \
         np.sin(np.radians(alpha_stall)) / (np.cos(np.radians(alpha_stall)) ** 2)
    B2 = (cd_stall_val - cd_max * (np.sin(np.radians(alpha_stall)) ** 2)) / np.cos(np.radians(alpha_stall))

    sign = np.sign(alpha)
    a_abs_rad = np.abs(alpha_rad)
    cl_post = sign * (A1 * np.sin(2 * a_abs_rad) + A2 * (np.cos(a_abs_rad) ** 2) / np.sin(np.maximum(a_abs_rad, 1e-6)))
    cd_post = B1 * (np.sin(a_abs_rad) ** 2) + B2 * np.cos(a_abs_rad)

    en_stall = np.abs(alpha) > alpha_stall
    cl = np.where(en_stall, cl_post, cl_lin)
    cd = np.where(en_stall, cd_post, cd_lin)
    return cl, cd


if __name__ == "__main__":
    for a in [0, 5, 10, 12, 15, 20, 30, 45, 60, 90]:
        cl, cd = cl_cd_naca0018(a)
        print(f"alpha={a:3d} deg   Cl={float(cl):7.3f}   Cd={float(cd):6.3f}")
