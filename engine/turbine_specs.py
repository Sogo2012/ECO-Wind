"""
Fichas técnicas de las turbinas -- data frame que preparó Pablo, asociado a
las claves de modelo que ya usa la app (CURVE_COEFFICIENTS en
flower_turbines_curves.py). Solo datos/specs (dimensiones, cimentación,
generador, límites de operación) -- NO reemplaza ni toca la curva de
potencia validada (Hallazgo 12), es información complementaria para
mostrarla junto al selector de modelo y, más adelante, en el PDF de
cotización.

DOS DESAJUSTES REALES encontrados al asociar el data frame de Pablo con
las 8 claves que ya existen en la app -- documentados acá, no resueltos
en silencio:

1. La app tiene un modelo `al13_4m` (AL13 Power Tower, 4 módulos) con
   curva de potencia propia, pero el data frame de Pablo NO trae una fila
   para 4 módulos -- solo 2, 6 y 8. `SPECS_TURBINAS["al13_4m"]` no existe
   todavía -- si Pablo tiene esos datos, hace falta agregarlos.
2. El data frame trae 4 filas que NO tienen clave de modelo en la app
   todavía (nunca se les construyó curva de potencia, Pista A las
   modela): "Survival Unit", y las 3 variantes de "Eco-Roof Energy Hub"
   (Flat-3, Flat-5, Slanted). Se guardan igual bajo claves nuevas
   (`survival_unit`, `ecoroof_flat_3`, `ecoroof_flat_5`,
   `ecoroof_slanted`) para no perder el dato, pero OJO: `RUTA_IMAGEN` no
   tiene imagen para estos 4 (no hay archivo en Recursos Visuales/ para
   ellos), y no aparecen en el selector de modelo de la app (no tienen
   curva de potencia con la que simular). Decisión de Pablo si se
   necesita construir la curva de potencia para alguno de estos 4 antes
   de poder ofrecerlos como opción real.
"""
import os

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_CARPETA_IMAGENES = os.path.join(_BASE, "Recursos Visuales")

LOGO_ECO = os.path.join(_CARPETA_IMAGENES, "eco_logo.png")
LOGO_FLOWER_TURBINES = os.path.join(_CARPETA_IMAGENES, "logo flower turbines (1).png")

# Nombre de archivo dentro de Recursos Visuales/ -- None cuando no hay imagen todavía.
RUTA_IMAGEN = {
    "small_tulip": os.path.join(_CARPETA_IMAGENES, "small tulip.png"),
    "medium_tulip": os.path.join(_CARPETA_IMAGENES, "Medium Tulip.png"),
    "three_m_tulip": os.path.join(_CARPETA_IMAGENES, "3-M Turbine.png"),
    "large_tulip": os.path.join(_CARPETA_IMAGENES, "Large Tulip.png"),
    # Un solo render de AL13 en Recursos Visuales/ -- compartido por los 3 tamaños
    # (2/6/8 módulos) hasta que haya renders específicos por tamaño.
    "al13_2m": os.path.join(_CARPETA_IMAGENES, "AL 13 POWER TOWER.png"),
    "al13_4m": os.path.join(_CARPETA_IMAGENES, "AL 13 POWER TOWER.png"),
    "al13_6m": os.path.join(_CARPETA_IMAGENES, "AL 13 POWER TOWER.png"),
    "al13_8m": os.path.join(_CARPETA_IMAGENES, "AL 13 POWER TOWER.png"),
    "survival_unit": None,
    "ecoroof_flat_3": None,
    "ecoroof_flat_5": None,
    "ecoroof_slanted": None,
}

# Transcripción directa del data frame de Pablo, re-keyeado a las claves de modelo de
# la app donde existe una -- sin redondear ni reinterpretar ningún valor.
SPECS_TURBINAS = {
    "small_tulip": {
        "nombre": "Small Tulip Turbine (1m)",
        "numero_parte": "FT 1.15M Turbine",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT (Eje Vertical, 2 Palas)",
        "potencia_nominal_w": 100,
        "viento_potencia_nominal_ms": 14.5,
        "produccion_12ms_aislada_w": 62.2,
        "produccion_12ms_cluster5_total_w": 723.5,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico automático integrado",
        "tipo_generador": "PMSG Imanes Permanentes (máx. 200W picos cortos)",
        "polos_generador": 8,
        "voltaje_salida": "110V/220V (1 Fase) / 12V/24V/48V",
        "altura_total_m": 1.40,
        "altura_pala_m": 1.149,
        "diametro_rotor_m": 0.55,
        "peso_total_kg": 20.0,
        "material_palas": "Plástico ABS reciclable / Termoplástico",
        "material_chasis": "Acero con pintura en polvo",
        "vida_diseno_anos": 40,
        "cimentacion_requerida": "Dado concreto 0.5x0.5x0.5m o lastre Eco-Roof",
    },
    "survival_unit": {
        "nombre": "Survival Unit",
        "numero_parte": "FT 1.15M Survival Kit",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT Portátil sobre contenedor móvil",
        "potencia_nominal_w": 100,
        "viento_potencia_nominal_ms": 14.5,
        "produccion_12ms_aislada_w": 62.2,
        "produccion_12ms_cluster5_total_w": None,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico",
        "tipo_generador": "PMSG",
        "polos_generador": 8,
        "voltaje_salida": "12V (Integrada en hielera de uso rudo)",
        "altura_total_m": 2.08,
        "altura_pala_m": 1.15,
        "diametro_rotor_m": 0.68,
        "peso_total_kg": 35.0,
        "material_palas": "Termoplástico",
        "material_chasis": "Contenedor rotomoldeado móvil con ruedas",
        "vida_diseno_anos": 40,
        "cimentacion_requerida": "Sin cimentación (autoestable)",
    },
    "medium_tulip": {
        "nombre": "Medium Tulip Turbine (2m)",
        "numero_parte": "FT 2M-Lite Turbine",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT (Eje Vertical, 2 Palas)",
        "potencia_nominal_w": 500,
        "viento_potencia_nominal_ms": 11.0,
        "produccion_12ms_aislada_w": 622.1,
        "produccion_12ms_cluster5_total_w": 5735.0,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico programable + Freno mecánico manual",
        "tipo_generador": "PMSG (Electrónica 1000W en grupos de 10)",
        "polos_generador": 18,
        "voltaje_salida": "230VAC/1PH/50Hz o 240VAC/1PH/60Hz / 24V/48V",
        "altura_total_m": 2.62,
        "altura_pala_m": 2.00,
        "diametro_rotor_m": 1.18,
        "peso_total_kg": 227.25,
        "material_palas": "Plástico ABS / Termoplástico",
        "material_chasis": "Acero estructural (pedestal piramidal)",
        "vida_diseno_anos": 40,
        "cimentacion_requerida": "Losa 2.1x2.1x0.25m o zapata 1.0x1.0x1.6m (12x M14)",
    },
    "three_m_tulip": {
        "nombre": "3-Meter Tulip Turbine",
        "numero_parte": "FT 3M Turbine",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT (Eje Vertical, 2 Palas)",
        "potencia_nominal_w": 1000,
        "viento_potencia_nominal_ms": 11.0,
        "produccion_12ms_aislada_w": 1400.0,
        "produccion_12ms_cluster5_total_w": 15000.0,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico, mecánico simple y programación automática",
        "tipo_generador": "PMSG (Electrónica 1500W o 2000W en grupos >=10)",
        "polos_generador": 18,
        "voltaje_salida": "230VAC/1PH/50Hz o 240VAC/1PH/60Hz / 48V",
        "altura_total_m": 4.07,
        "altura_pala_m": 3.00,
        "diametro_rotor_m": 1.80,
        "peso_total_kg": 400.0,
        "material_palas": "Termoplástico",
        "material_chasis": "Acero estructural con base de anclaje",
        "vida_diseno_anos": 20,
        "cimentacion_requerida": "Base de concreto reforzada con pernos M14",
    },
    "large_tulip": {
        "nombre": "Large Tulip Turbine",
        "numero_parte": "FT 6M Turbine",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT (Eje Vertical, 2 Palas)",
        "potencia_nominal_w": 5000,
        "viento_potencia_nominal_ms": 11.5,
        "produccion_12ms_aislada_w": 5390.0,
        "produccion_12ms_cluster5_total_w": 62500.0,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico + Freno mecánico + Freno manual",
        "tipo_generador": "PMSG Trifásico",
        "polos_generador": 24,
        "voltaje_salida": "230VAC/3PH/60Hz o 110VAC/3PH/50Hz (Trifásico) / 48V",
        "altura_total_m": 6.00,
        "altura_pala_m": 5.00,
        "diametro_rotor_m": 2.45,
        "peso_total_kg": 1000.0,
        "material_palas": "Termoplástico aeroespacial",
        "material_chasis": "Pedestal de acero galvanizado pesado",
        "vida_diseno_anos": 20,
        "cimentacion_requerida": "Zapata 2.5x2.5x0.9m o 2.5x4.0x0.5m",
    },
    "al13_2m": {
        "nombre": "AL13 Power Tower (2 Mód)",
        "numero_parte": "FT AL13-2M",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT Modular (Palas cruzadas a 90°)",
        "potencia_nominal_w": 1000,
        "viento_potencia_nominal_ms": 12.0,
        "produccion_12ms_aislada_w": 700.0,
        "produccion_12ms_cluster5_total_w": 7000.0,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 40.0,
        "sistema_frenado": "Electrónico + Freno mecánico",
        "tipo_generador": "PMSG Modular de 24V o 48V AC",
        "polos_generador": 18,
        "voltaje_salida": "120V/240V AC / 24V/48V",
        "altura_total_m": 2.62,
        "altura_pala_m": 2.00,
        "diametro_rotor_m": 1.70,
        "peso_total_kg": 336.0,
        "material_palas": "Aluminio anodizado reciclable",
        "material_chasis": "Acero estructural A36 (Caja 1x1 m)",
        "vida_diseno_anos": 20,
        "cimentacion_requerida": "Base de concreto 1.0x1.0x2.2m",
    },
    "al13_6m": {
        "nombre": "AL13 Power Tower (6 Mód)",
        "numero_parte": "FT AL13-6M",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT Modular (Palas cruzadas a 90°)",
        "potencia_nominal_w": 5000,
        "viento_potencia_nominal_ms": 12.0,
        "produccion_12ms_aislada_w": 2100.0,
        "produccion_12ms_cluster5_total_w": 21000.0,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico + Freno mecánico",
        "tipo_generador": "PMSG de 5 kW",
        "polos_generador": 24,
        "voltaje_salida": "120V/240V o Trifásico / 48V",
        "altura_total_m": 7.50,
        "altura_pala_m": 6.00,
        "diametro_rotor_m": 1.70,
        "peso_total_kg": 588.0,
        "material_palas": "Aluminio anodizado reciclable",
        "material_chasis": "Acero A36 + Poste estabilizador (70 kg)",
        "vida_diseno_anos": 20,
        "cimentacion_requerida": "Zapata 2.5x2.5x0.9m + Anclaje para poste",
    },
    "al13_8m": {
        "nombre": "AL13 Power Tower (8 Mód)",
        "numero_parte": "FT AL13-8M",
        "clase_iec": "IEC 61400 Class IV",
        "tipo_rotor": "VAWT Modular (Palas cruzadas a 90°)",
        "potencia_nominal_w": 10000,
        "viento_potencia_nominal_ms": 13.5,
        "produccion_12ms_aislada_w": 3500.0,
        "produccion_12ms_cluster5_total_w": 35000.0,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico + Freno mecánico",
        "tipo_generador": "PMSG de 10 kW",
        "polos_generador": 24,
        "voltaje_salida": "240V / Trifásico / 48V",
        "altura_total_m": 9.50,
        "altura_pala_m": 8.00,
        "diametro_rotor_m": 1.70,
        "peso_total_kg": 714.0,
        "material_palas": "Aluminio anodizado reciclable",
        "material_chasis": "Acero A36 + Poste estabilizador reforzado",
        "vida_diseno_anos": 20,
        "cimentacion_requerida": "Zapata 2.5x2.5x1.2m + Poste lateral a 1280 mm",
    },
    "ecoroof_flat_3": {
        "nombre": "Eco-Roof Energy Hub (Flat - 3 Turbines)",
        "numero_parte": "FT EcoRoof-Flat-3",
        "clase_iec": "N/A",
        "tipo_rotor": "3 Turbinas VAWT (1m) en plataforma plana",
        "potencia_nominal_w": 300,
        "viento_potencia_nominal_ms": 14.5,
        "produccion_12ms_aislada_w": None,
        "produccion_12ms_cluster5_total_w": None,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico automático",
        "tipo_generador": "PMSG (Capacidad solar aprox: 2 x 100W)",
        "polos_generador": 8,
        "voltaje_salida": "Controladores híbridos o separados",
        "altura_total_m": None,
        "altura_pala_m": 1.149,
        "diametro_rotor_m": 0.55,
        "peso_total_kg": 196.5,  # carga transmitida kg/m2
        "material_palas": "Plástico ABS reciclable",
        "material_chasis": "Plataforma plana. Cajas contrapeso 300x315x150 mm",
        "vida_diseno_anos": 40,
        "cimentacion_requerida": "Instalación sin perforaciones (Efecto Bouquet integrado)",
    },
    "ecoroof_flat_5": {
        "nombre": "Eco-Roof Energy Hub (Flat - 5 Turbines)",
        "numero_parte": "FT EcoRoof-Flat-5",
        "clase_iec": "N/A",
        "tipo_rotor": "5 Turbinas VAWT (1m) en plataforma plana",
        "potencia_nominal_w": 500,
        "viento_potencia_nominal_ms": 14.5,
        "produccion_12ms_aislada_w": None,
        "produccion_12ms_cluster5_total_w": None,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico automático",
        "tipo_generador": "PMSG (Capacidad solar aprox: 4 x 100W)",
        "polos_generador": 8,
        "voltaje_salida": "Controladores híbridos o separados",
        "altura_total_m": None,
        "altura_pala_m": 1.149,
        "diametro_rotor_m": 0.55,
        "peso_total_kg": 185.3,  # carga transmitida kg/m2
        "material_palas": "Plástico ABS reciclable",
        "material_chasis": "Sistema de balancín para nivelación simétrica",
        "vida_diseno_anos": 40,
        "cimentacion_requerida": "Instalación sin perforaciones",
    },
    "ecoroof_slanted": {
        "nombre": "Eco-Roof Energy Hub (Slanted)",
        "numero_parte": "FT EcoRoof-Slanted",
        "clase_iec": "N/A",
        "tipo_rotor": "Módulos de 3 Turbinas VAWT (1m) en techo inclinado",
        "potencia_nominal_w": 300,
        "viento_potencia_nominal_ms": 14.5,
        "produccion_12ms_aislada_w": None,
        "produccion_12ms_cluster5_total_w": None,
        "velocidad_cutin_ms": 0.7,
        "velocidad_supervivencia_ms": 54.0,
        "sistema_frenado": "Electrónico automático",
        "tipo_generador": "PMSG (Capacidad solar aprox: 2x400W o 4x400W por módulo)",
        "polos_generador": 8,
        "voltaje_salida": "Controladores híbridos",
        "altura_total_m": None,
        "altura_pala_m": 1.149,
        "diametro_rotor_m": 0.55,
        "peso_total_kg": 207.0,  # carga transmitida kg/m2
        "material_palas": "Plástico ABS reciclable",
        "material_chasis": "Vigas conectadas, puntos de goma de alta fricción",
        "vida_diseno_anos": 40,
        "cimentacion_requerida": "Sin perforaciones. Ángulo máximo de techo: 3°",
    },
}


if __name__ == "__main__":
    try:
        from engine.flower_turbines_curves import CURVE_COEFFICIENTS
    except ImportError:
        from flower_turbines_curves import CURVE_COEFFICIENTS

    print("=" * 78)
    print("Chequeo cruzado: claves de CURVE_COEFFICIENTS (con curva de potencia) vs.")
    print("SPECS_TURBINAS (fichas técnicas del data frame de Pablo)")
    print("=" * 78)
    con_curva = set(CURVE_COEFFICIENTS)
    con_specs = set(SPECS_TURBINAS)
    print(f"Con curva pero SIN specs todavía: {sorted(con_curva - con_specs) or 'ninguna'}")
    print(f"Con specs pero SIN curva de potencia (no simulables hoy): {sorted(con_specs - con_curva)}")
    print(f"Con las dos cosas: {sorted(con_curva & con_specs)}")
    print()
    for clave in sorted(con_curva & con_specs):
        existe_img = RUTA_IMAGEN.get(clave) and os.path.exists(RUTA_IMAGEN[clave])
        print(f"  {clave:16s} imagen: {'OK' if existe_img else 'FALTA'} "
              f"({RUTA_IMAGEN.get(clave)})")
    print()
    print(f"Logo ECO: {'OK' if os.path.exists(LOGO_ECO) else 'FALTA'} ({LOGO_ECO})")
    print(f"Logo Flower Turbines: {'OK' if os.path.exists(LOGO_FLOWER_TURBINES) else 'FALTA'} "
          f"({LOGO_FLOWER_TURBINES})")
