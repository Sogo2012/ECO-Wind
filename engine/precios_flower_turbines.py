"""
Precios de venta EXWORKS reales de Flower Turbines -- Hallazgo 56.

Reemplaza el costo de fábrica adivinado/estimado de `turbine_specs.py` (usado antes
en la cadena de CAPEX por %, ya en desuso desde Hallazgo 53) por precios de venta
REALES de un catálogo oficial que Pablo compartió (hoja "FLOWER_TURBINES I Costos y
Precios"). Ver Hallazgo 56 en avance-de-proyecto.md para el detalle completo.

FUENTE Y CRITERIO DE SELECCIÓN
-------------------------------
El precio de cada modelo es el precio de venta final ("Precio 3", columna S de la
hoja original) que Pablo indicó explícitamente usar. Ver Hallazgo 56 en
avance-de-proyecto.md para la trazabilidad completa de qué columna se tomó y por
qué.

CONFIDENCIALIDAD: la hoja original de Pablo trae, además de este precio, columnas
de costo de fábrica y de márgenes de utilidad que son confidenciales. Este módulo
NO las contiene ni las deriva -- sólo guarda el precio de venta final por modelo,
el único dato que Pablo autorizó a usar en la app.

BUG REAL ENCONTRADO Y CORREGIDO AL LEER EL ARCHIVO ORIGINAL: la hoja usa el PUNTO
como separador de miles (formato latino: los precios de miles de dólares llevan
un punto, no una coma) -- el script que Pablo ya tenía (hecho con Gemini) asumía
formato con coma de miles y hubiera dejado el punto como decimal, lo que habría
dejado todos los precios ~1000x más chicos de lo real. Se corrigió antes de tomar
ningún número de acá.

CADA PRECIO ES "TURBINA + INVERSOR/CARGADOR" YA INCLUIDO (variante "on grid with
inverter" del catálogo, unidad simple, no bouquet) -- NO es turbina sola. Esto
importa porque el resto de la app (dimensionador_sistema_eolico.py) selecciona y
cobra el inversor Sol-Ark POR SEPARADO según la potencia total del arreglo -- si se
usa este precio como "costo de la turbina" Y la app además suma el Sol-Ark aparte,
el inversor se cuenta dos veces. Pendiente de decisión de Pablo, ver Hallazgo 56.

TAMPOCO reflejan el descuento real por volumen de un bouquet: en el catálogo, un
bouquet de 3 turbinas de 1m cuesta $10,725, no 3×$5,850=$17,550 -- este módulo sólo
expone el precio de UNIDAD SIMPLE; multiplicar por N en la app sobreestima un poco
el valor real de un clúster grande (mismo pendiente que el punto anterior).

MODELOS SIN PRECIO EN EL CATÁLOGO: `ecoroof_slanted` y `survival_unit` no aparecen
en ninguna fila -- quedan en `None` hasta que Pablo confirme un precio real.
"""

from typing import Dict, Optional

PRECIOS_EXWORKS_USD: Dict[str, Optional[float]] = {
    "small_tulip": 5850.0,
    "medium_tulip": 17925.0,
    "three_m_tulip": 23985.0,
    "large_tulip": 52500.0,
    "al13_2m": 19500.0,
    "al13_4m": 25350.0,
    "al13_6m": 29738.0,
    "al13_8m": 45000.0,
    "ecoroof_flat_3": 16485.0,
    "ecoroof_flat_5": 20985.0,
    "ecoroof_slanted": None,
    "survival_unit": None,
}


def get_precio_exworks_usd(modelo: str) -> Optional[float]:
    """Precio de venta EXWORKS (USD) por unidad del modelo dado, o None si no hay
    dato real todavía (ver docstring del módulo)."""
    return PRECIOS_EXWORKS_USD.get(modelo)
