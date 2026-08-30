"""
Polar hibrido para la pala real de Flower Turbines: UN solo perfil (curvo,
tipo "media luna" segun el corte CAD que describe el plan), no dos
mecanismos separados. La asimetria concava/convexa de la pala se modela
como un Cd de post-perdida ASIMETRICO -- Cd tiende a 2.3 (cara concava,
Cd de la ficha External Load Calculations) cuando el flujo pega de un
lado, y a 1.2 (cara convexa) cuando pega del otro -- en vez de sumar un
"componente Savonius" aparte (que en dmst_model.py con cd_extra uniforme
daba potencia negativa, ver notebook Pista B Paso 4).

Convencion de signo (SUPUESTO, no confirmado con el CAD real de la pala):
alpha > 0 -> cara concava enfrenta el flujo (Cd hacia 2.3)
alpha < 0 -> cara convexa enfrenta el flujo (Cd hacia 1.2)
Como la pala gira, ambos signos de alpha ocurren naturalmente durante una
revolucion -- esto reproduce el mecanismo de "el viento pega, cede el
paso, pega del otro lado" sin necesitar un segundo cuerpo/fuerza aparte.

La region lineal (sustentacion) se deja igual que el NACA 0018 simetrico
-- no hay forma de estimar el corrimiento de angulo de sustentacion nula
por camber sin mas datos del perfil real, asi que esa parte sigue siendo
una simplificacion conocida.

NOTA (correccion tras el primer intento, ver Pista B Paso 5c del notebook):
la primera version de este modulo metia el Cd_max asimetrico DENTRO de la
formula de Viterna-Corrigan completa (Cl y Cd), pero esa formula liga Cl_post
a Cd_max (el termino A2 crece con Cd_max) -- subir Cd_max a 2.3 no solo
sumaba arrastre, tambien INFLABA la sustentacion post-perdida ~10-15%,
empeorando la sobre-prediccion en vez de corregirla (validado: peor en los
4 modelos reales que el DMST de solo-sustentacion). Fisicamente no tiene
sentido que la sustentacion en perdida profunda (dominada por el
desprendimiento de flujo, no por la forma fina del perfil) dependa de cual
cara es concava -- solo el arrastre de forma (Cd) deberia diferir entre
caras. Por eso Cl_post ahora se calcula IGUAL que en el NACA0018 puro
(reutilizando cl_cd_naca0018), y solo Cd_post usa el Cd_max asimetrico.
"""
import numpy as np

try:
    from engine.naca0018_polar import cl_cd_naca0018, RE_REF
except ImportError:
    from naca0018_polar import cl_cd_naca0018, RE_REF

CD_CONCAVA = 2.3   # de External Load Calculations 2m & 5m.pdf
CD_CONVEXA = 1.2   # de External Load Calculations 2m & 5m.pdf


def cl_cd_hibrido(alpha_deg, Re=RE_REF, cd_concava=CD_CONCAVA, cd_convexa=CD_CONVEXA):
    """
    Cl, Cd del perfil hibrido, en funcion de alpha (grados) y Re.

    Cl: identico a cl_cd_naca0018() en todo el rango (region lineal Y
    post-perdida) -- la sustentacion no se modela como dependiente de la
    asimetria concava/convexa (ver nota de correccion arriba).

    Cd: identico a cl_cd_naca0018() en la region lineal (pre-perdida, sin
    separacion de flujo, la asimetria de forma no aplica todavia). En
    post-perdida usa Viterna-Corrigan solo para el termino de arrastre, con
    Cd_max ASIMETRICO: 2.3 para alpha>0 (cara concava), 1.2 para alpha<0
    (cara convexa) -- en vez del Cd_max=1.98 (placa plana) simetrico del
    NACA 0018 puro. Este es el mecanismo tipo Savonius: mas arrastre
    cuando la cara concava recibe el viento, menos cuando es la convexa.
    """
    alpha = np.asarray(alpha_deg, dtype=float)
    alpha_rad = np.radians(alpha)
    Re = np.maximum(np.asarray(Re, dtype=float), 1e3)

    cl, _ = cl_cd_naca0018(alpha, Re=Re)

    factor_re = np.clip((Re / RE_REF) ** 0.5, 0.55, 1.0)
    alpha_stall = 12.0 * (0.7 + 0.3 * factor_re)
    cd0 = 0.014 * (Re / RE_REF) ** -0.5

    cd_lin = cd0 + 0.02 * (alpha_rad ** 2)
    cd_stall_val = cd0 + 0.02 * (np.radians(alpha_stall) ** 2)

    a_abs_rad = np.abs(alpha_rad)
    a_stall_rad = np.radians(alpha_stall)

    cd_max = np.where(alpha >= 0, cd_concava, cd_convexa)
    B1 = cd_max
    B2 = (cd_stall_val - cd_max * (np.sin(a_stall_rad) ** 2)) / np.cos(a_stall_rad)
    cd_post = B1 * (np.sin(a_abs_rad) ** 2) + B2 * np.cos(a_abs_rad)

    en_stall = np.abs(alpha) > alpha_stall
    cd = np.where(en_stall, cd_post, cd_lin)
    return cl, cd


if __name__ == "__main__":
    print("Comparacion simetrico (NACA0018 puro) vs hibrido (Cd asimetrico 2.3/1.2):")
    print(f"{'alpha':>6}  {'Cd concava(+)':>14}  {'Cd convexa(-)':>14}")
    for a in [10, 20, 30, 45, 60, 90]:
        _, cd_pos = cl_cd_hibrido(a)
        _, cd_neg = cl_cd_hibrido(-a)
        print(f"{a:6d}  {float(cd_pos):14.3f}  {float(cd_neg):14.3f}")
