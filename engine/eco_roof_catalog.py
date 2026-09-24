"""
Catálogo FIJO de productos Eco-Roof Energy Hub -- módulo nuevo y separado del
motor de curvas del 3-M Tulip (engine/simulador_pista_a.py /
flower_turbines_curves.py, que no se tocan).

En la app, cada producto Eco-Roof es un modelo más de la cartera (selector
"Modelo" de "Equipos y configuración", ver PRESET_POR_MODELO más abajo), pero
A PROPÓSITO no es generalizable a cualquier N de turbinas: cada preset es un
producto de fábrica ya definido (turbina + turbinas por equipo + capacidad solar
+ peso/huella fijos) -- el N de la fila del proyecto es la cantidad de EQUIPOS,
no de turbinas sueltas. Si mañana Flower Turbines saca un producto nuevo con su
propia tabla de potencia oficial, se agrega acá como una entrada más, no
generalizando la interpolación a un N arbitrario sin tabla real detrás.

Cada preset reference dos claves YA existentes en engine/turbine_specs.py
(cargadas ahí desde antes de este módulo, con peso/huella/costo/cimentación
reales de la ficha de Pablo -- no se duplican esos valores acá):
  - specs_key: la ficha del PRODUCTO empacado (peso transmitido kg/m²,
    huella, costo EXWORKS, cimentación/instalación) -- "ecoroof_flat_3",
    "ecoroof_flat_5", "ecoroof_slanted".
  - turbina_key: la ficha de la TURBINA individual (cut-in, velocidad de
    supervivencia, clase IEC 61400) -- siempre "small_tulip" acá, es la
    turbina física detrás de los 3 productos Eco-Roof de 1m.
"""
from engine.eco_roof_curves import TABLA_N3, TABLA_N5

# Altura de pala del Small Tulip (engine/turbine_specs.py -- SPECS_TURBINAS["small_tulip"]
# ["altura_pala_m"]) -- se usa como altura del buje SOBRE EL TECHO porque el producto
# empacado (specs_key) no trae un valor de "altura de buje" separado del de la turbina
# individual; es la mejor aproximación disponible, no un dato inventado (mismo número que
# ya está en la ficha oficial). La altura del buje sobre el TERRENO, que es la que entra al
# perfil logarítmico de viento, es altura del techo + este valor (ver
# engine/eco_roof_simulador.py::simular_eco_roof(), parámetro altura_techo_m) -- sin sumar
# el techo, la turbina quedaría a ~1 m del suelo y el eólico se subestimaría del orden de
# 10 veces para un edificio real.
ALTURA_BUJE_ECO_ROOF_M = 1.149

ECO_ROOF_PRESETS = {
    "eco_roof_1m_3_flat": {
        "nombre": "Eco-Roof Energy Hub -- Flat, 3 turbinas",
        "specs_key": "ecoroof_flat_3",
        "turbina_key": "small_tulip",
        "N": 3,
        "tabla_potencia": TABLA_N3,
        "altura_buje_m": ALTURA_BUJE_ECO_ROOF_M,
        "capacidad_solar_kwp": 0.200,  # 2 x 100W, ficha ecoroof_flat_3 (turbine_specs.py)
        "tilt_deg": 0.0,               # techo plano
        "acimut_superficie_deg": 0.0,  # sin efecto con tilt_deg=0.0
        "tipo_techo": "flat",
        "angulo_max_techo_deg": None,  # sin límite documentado para la versión plana
        "status": "ok",
    },
    "eco_roof_1m_5_flat": {
        "nombre": "Eco-Roof Energy Hub -- Flat, 5 turbinas",
        "specs_key": "ecoroof_flat_5",
        "turbina_key": "small_tulip",
        "N": 5,
        "tabla_potencia": TABLA_N5,
        "altura_buje_m": ALTURA_BUJE_ECO_ROOF_M,
        "capacidad_solar_kwp": 0.400,  # 4 x 100W, ficha ecoroof_flat_5 (turbine_specs.py)
        "tilt_deg": 0.0,
        "acimut_superficie_deg": 0.0,
        "tipo_techo": "flat",
        "angulo_max_techo_deg": None,
        "status": "ok",
    },
    "eco_roof_1m_3_sloped": {
        "nombre": "Eco-Roof Energy Hub -- Techo inclinado, 3 turbinas",
        "specs_key": "ecoroof_slanted",
        "turbina_key": "small_tulip",
        "N": 3,  # misma tabla de potencia que la versión plana -- mismo bouquet de 3 turbinas
        "tabla_potencia": TABLA_N3,
        "altura_buje_m": ALTURA_BUJE_ECO_ROOF_M,
        # Ficha (turbine_specs.py, ecoroof_slanted): "2x400W o 4x400W por módulo" --
        # se usa la opción base (2x400W); 4x400W queda documentado como alternativa,
        # no se decide sola cuál aplica sin que el usuario elija el módulo real.
        "capacidad_solar_kwp": 0.800,
        "capacidad_solar_kwp_opcion_4x400w": 1.600,
        # Sin un valor real de pendiente de techo en la ficha -- se usa 0.0 (mismo
        # tratamiento que la versión plana) hasta tener el dato real del proyecto.
        # OJO al usar este preset: reemplazar por la pendiente real del techo del
        # sitio antes de reportar producción solar (no es una superficie plana de
        # verdad, es un placeholder documentado).
        "tilt_deg": 0.0,
        "acimut_superficie_deg": 0.0,
        "tipo_techo": "sloped",
        # 3° (no 5°): dato verificado en la ficha oficial ya cargada en el repo
        # (engine/i18n.py, "specs_ecoroof_slanted_cimentacion") -- corrige el 5° que
        # traía el prompt original, que no coincide con el dato ya validado acá.
        "angulo_max_techo_deg": 3.0,
        "status": "ok",
    },
    "eco_roof_2m_2": {
        "nombre": "Eco-Roof Energy Hub -- 2m, 2 turbinas (SIN TABLA OFICIAL)",
        "specs_key": None,
        "turbina_key": "medium_tulip",
        "N": 2,
        "tabla_potencia": None,
        "altura_buje_m": None,
        "capacidad_solar_kwp": None,
        "tilt_deg": None,
        "acimut_superficie_deg": None,
        "tipo_techo": "sloped",
        "angulo_max_techo_deg": None,
        # Bloqueado a propósito (punto 2/7 del prompt original): no hay tabla de
        # potencia oficial de Flower Turbines para esta variante todavía -- no se
        # inventa una. simular_eco_roof() (engine/eco_roof_simulador.py) revisa este
        # campo y se niega a devolver un número de energía para cualquier preset que
        # no sea "ok".
        "status": "sin_tabla_oficial",
    },
}


def preset_disponible(clave):
    """True solo si el preset tiene tabla de potencia oficial y puede simularse."""
    preset = ECO_ROOF_PRESETS.get(clave)
    return preset is not None and preset["status"] == "ok"


# Eco-Roof como producto más de la cartera (selector "Modelo" de "Equipos y
# configuración"): la cartera identifica cada producto por su clave de
# turbine_specs.py/precios_flower_turbines.py ("ecoroof_flat_3", ...), que es el
# specs_key de cada preset. Sólo entran los presets con tabla oficial --
# eco_roof_2m_2 no tiene specs_key y queda afuera de la cartera.
PRESET_POR_MODELO = {
    preset["specs_key"]: clave
    for clave, preset in ECO_ROOF_PRESETS.items()
    if preset["status"] == "ok"
}


def es_modelo_eco_roof(modelo):
    """True si la clave de la cartera es un producto Eco-Roof (tabla oficial), no
    una turbina del motor de curvas k·v³×M(N)."""
    return modelo in PRESET_POR_MODELO


def articulo_incluye_solar(articulo):
    """True si el artículo elegido del catálogo de precios trae paneles solares --
    los artículos Eco-Roof con paneles dicen "... plus solar panels" (ver
    engine/precios_flower_turbines.py). Sin artículo elegido (o un producto sin
    artículos en el catálogo, como ecoroof_slanted), no se asume que haya paneles."""
    return bool(articulo) and "solar" in articulo.lower()
