"""
Precios de venta EXWORKS reales de Flower Turbines -- Hallazgo 56/57.

Reemplaza el costo de fábrica adivinado/estimado de `turbine_specs.py` (usado antes
en la cadena de CAPEX por %, ya en desuso desde Hallazgo 53) por precios de venta
REALES de un catálogo oficial que Pablo compartió (hoja "FLOWER_TURBINES I Costos y
Precios"). Ver Hallazgo 56/57 en avance-de-proyecto.md para el detalle completo.

FUENTE Y CRITERIO DE SELECCIÓN
-------------------------------
El precio de cada artículo es el precio de venta final ("Precio 3", columna S de la
hoja original) que Pablo indicó explícitamente usar.

CONFIDENCIALIDAD: la hoja original de Pablo trae, además de este precio, columnas
de costo de fábrica y de márgenes de utilidad que son confidenciales. Este módulo
NO las contiene ni las deriva -- sólo guarda, por cada artículo, el texto exacto de
la columna "Artículo" y su precio de venta final, los dos únicos datos (además del
grupo) que Pablo autorizó a usar en la app.

BUG REAL ENCONTRADO Y CORREGIDO AL LEER EL ARCHIVO ORIGINAL: la hoja usa el PUNTO
como separador de miles (formato latino), no la coma -- un script que Pablo ya
tenía (hecho con otra IA) asumía formato con coma de miles y hubiera dejado el
punto como decimal, lo que habría dejado todos los precios ~1000x más chicos de lo
real. Se corrigió antes de tomar ningún número de acá.

CÓMO SE ORGANIZA (Hallazgo 57 -- "el usuario elige el artículo, no la app")
----------------------------------------------------------------------------
El catálogo de Pablo agrupa varios artículos bajo un mismo "Grupo/Cantidad" (ej.
"2mtulip" trae la unidad simple, la versión off-grid, un bouquet de 2, y dos
accesorios). Pablo pidió que el GRUPO se filtre automático según el modelo que el
usuario ya eligió en "Equipos y configuración", pero que el ARTÍCULO específico
(unidad simple vs. bouquet, on-grid vs. off-grid, con o sin accesorio) lo elija el
cliente a mano -- la app ya no adivina cuál usar.

`CATALOGO_FLOWER_TURBINES` guarda, por cada modelo de la app (misma clave que
`turbine_specs.SPECS_TURBINAS`), la lista de artículos reales de su grupo
correspondiente, en el orden en que se muestran -- el PRIMERO de cada lista es el
que se usa por default (la unidad simple "on grid with inverter", el mismo precio
que ya se usaba en Hallazgo 56, para no cambiarle el número a nadie que no toque
nada). El texto de "Artículo" queda tal cual está en el catálogo (en inglés), para
que el cliente pueda leer exactamente qué está cotizando.

No se incluyen las filas de descuento por volumen del catálogo (grupos "20", "50",
"100", "20 and above", "50 and above", "100 and above" -- precios especiales para
pedidos de 20+/50+/100+ unidades de una vez) -- son un eje distinto (tamaño total
del pedido, no de qué modelo/clúster se trata) que este selector por clúster no
cubre todavía.

MODELOS SIN NINGÚN ARTÍCULO EN EL CATÁLOGO: `ecoroof_slanted` y `survival_unit` no
tienen fila correspondiente -- lista vacía hasta que Pablo confirme un precio real.
"""

from typing import Dict, List, Optional, Tuple

# (Artículo, Precio_3 USD) -- el primero de cada lista es el default (unidad
# simple, on-grid con inversor incluido).
CATALOGO_FLOWER_TURBINES: Dict[str, List[Tuple[str, float]]] = {
    "small_tulip": [
        ("1-meter tulip on grid with inverter", 5850.0),
        ("1-meter tulip off grid with charger", 2475.0),
        ("1-meter tulip on grid bouquet of 2 with inverter", 8250.0),
        ("1-meter tulip on grid bouquet of 3 with inverter", 10725.0),
        ("1-meter tulip on grid bouquet of 4 with inverter", 13200.0),
        ("1-meter tulip on grid bouquet of 5 with inverter", 15675.0),
        ("1-meter tulip on grid bouquet of 6 with inverter", 15900.0),
        ("1-meter tulip 1-meter pole", 300.0),
        ("1-meter tulip 2 meter pole", 375.0),
        ("1m foundation. Full assembly 1050x500", 630.0),
    ],
    "medium_tulip": [
        ("2-meter on grid with inverter", 17925.0),
        ("2-meter tulip off grid with charger", 16185.0),
        ("2-meter on grid with inverter bouquet of 2", 34425.0),
        ("2-meter heat reduction system per turbine", 1200.0),
        ("2-meter extra anti-corrosion measures per turbine", 450.0),
    ],
    "three_m_tulip": [
        ("3-meter tulip on grid with inverter 1 kilowatt", 23985.0),
        ("3-meter tulip off grid with charger 1 kilowatt", 22485.0),
        ("3-meter tulip on grid with inverter 3 kilowatts", 26985.0),
        ("3-meter tulip off grid with charger 3 kilowatts", 25485.0),
        ("3-meter tulip hurricane reinforcements per blade set", 1800.0),
        ("3-meter extra anti-corrosion measures per turbine", 600.0),
    ],
    "large_tulip": [
        ("5-meter tulip on grid with inverter 5 kilowatts", 52500.0),
        ("5-meter tulip off grid with charger 5 kilowatts", 45000.0),
        ("5-meter tulip on grid with inverter 10 kilowatts", 60000.0),
    ],
    "al13_2m": [
        ("2-meter blade height turbine on grid with inverter 1 kilowatt", 19500.0),
    ],
    "al13_4m": [
        ("4-meter blade height turbine on grid with inverter 3 kilowatts", 25350.0),
    ],
    "al13_6m": [
        ("6-meter blade height turbine on grid with inverter 5 kilowatts", 29738.0),
    ],
    "al13_8m": [
        ("8-meter blade height turbine on grid with inverter 10 kilowatts", 45000.0),
        ("8-meter blade height turbine on grid with inverter 5 kilowatts", 37500.0),
    ],
    "ecoroof_flat_3": [
        ("ecoroof with 3 1-meter turbines on grid with inverter", 16485.0),
        ("ecoroof with 3 1-meter turbines off grid with chargers", 12225.0),
        ("ecoroof with 3 1-meter turbines on grid with inverter plus solar panels", 17985.0),
        ("ecoroof with 3 1-meter turbines off grid with chargers plus solar panels", 13725.0),
    ],
    "ecoroof_flat_5": [
        ("ecoroof with 5 1-meter turbines on grid with inverter", 20985.0),
        ("ecoroof with 5 1-meter turbines off grid with chargers", 17985.0),
        ("ecoroof with 5 1-meter turbines on grid with inverter plus solar panels", 22485.0),
        ("ecoroof with 5 1-meter turbines off grid with chargers plus solar panels", 19485.0),
    ],
    "ecoroof_slanted": [],
    "survival_unit": [],
}


def get_articulos_disponibles(modelo: str) -> List[Tuple[str, float]]:
    """Artículos reales del catálogo para el modelo dado, en el orden en que se
    muestran -- el primero es el que se usa por default. Lista vacía si el modelo
    no tiene ningún artículo cargado todavía."""
    return CATALOGO_FLOWER_TURBINES.get(modelo, [])


def get_precio_exworks_usd(modelo: str, articulo: Optional[str] = None) -> Optional[float]:
    """Precio de venta EXWORKS (USD) del artículo elegido para ese modelo.

    Si no se pasa `articulo` (o no coincide con ninguno de la lista), devuelve el
    precio del primero -- el default de unidad simple on-grid. None si el modelo no
    tiene ningún artículo cargado (ver docstring del módulo)."""
    filas = CATALOGO_FLOWER_TURBINES.get(modelo, [])
    if not filas:
        return None
    if articulo is not None:
        for art, precio in filas:
            if art == articulo:
                return precio
    return filas[0][1]
