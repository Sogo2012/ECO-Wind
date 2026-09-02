# engine/price_calculator.py
# =============================================================================
# Calculador de Precios para Turbinas Flower y Sistemas Sol-Ark
# Aplica márgenes comerciales e importación
# =============================================================================

from typing import Dict, List, Optional


# Parámetros globales de pricing
IMPORT_COST_USD = 2500.0  # Costo fijo de importación (USD)
MARGIN_PCT = 0.30  # Margen comercial (30%)


def calcular_precio_final(costo_base_usd: float,
                         agregar_importacion: bool = True,
                         margen_pct: float = MARGIN_PCT) -> float:
    """
    Calcula precio final incluyendo importación y margen.

    Fórmula: Precio_Final = (Costo_Base + Importación) × (1 + Margen%)

    Args:
        costo_base_usd      : Costo base del equipo (USD)
        agregar_importacion : Si True, suma IMPORT_COST_USD
        margen_pct          : Margen comercial (0.30 = 30%)

    Returns:
        float: Precio final en USD
    """
    if costo_base_usd < 0:
        raise ValueError("Costo base no puede ser negativo")
    if margen_pct < 0 or margen_pct > 1:
        raise ValueError("Margen debe estar entre 0 y 1")

    # Aplicar importación
    costo_con_import = costo_base_usd
    if agregar_importacion:
        costo_con_import += IMPORT_COST_USD

    # Aplicar margen
    precio_final = costo_con_import * (1 + margen_pct)

    return round(precio_final, 2)


def desglose_precio(costo_base_usd: float,
                   agregar_importacion: bool = True,
                   margen_pct: float = MARGIN_PCT) -> Dict[str, float]:
    """
    Retorna desglose completo de precio (base, importación, margen, total).

    Args:
        costo_base_usd      : Costo base del equipo (USD)
        agregar_importacion : Si True, suma IMPORT_COST_USD
        margen_pct          : Margen comercial

    Returns:
        dict con: costo_base, costo_importacion, subtotal,
                  margen_usd, precio_final, margen_pct_aplicado
    """
    costo_import = IMPORT_COST_USD if agregar_importacion else 0.0
    subtotal = costo_base_usd + costo_import
    margen_usd = subtotal * margen_pct
    precio_final = subtotal + margen_usd

    return {
        "costo_base_usd": round(costo_base_usd, 2),
        "costo_importacion_usd": round(costo_import, 2),
        "subtotal_usd": round(subtotal, 2),
        "margen_usd": round(margen_usd, 2),
        "margen_pct": round(margen_pct * 100, 2),
        "precio_final_usd": round(precio_final, 2),
    }


def calcular_bom_turbinas(turbinas_list: List[Dict]) -> Dict:
    """
    Calcula precio total de BOM (Bill of Materials) de turbinas.

    Args:
        turbinas_list: Lista de dicts con estructura:
                      {"modelo": str, "cantidad": int, "costo_base_usd": float}

    Returns:
        dict con desglose total y por turbina
    """
    detalles = []
    costo_base_total = 0.0

    for turbina in turbinas_list:
        modelo = turbina.get("modelo")
        cantidad = turbina.get("cantidad", 1)
        costo_base = turbina.get("costo_base_usd", 0)

        subtotal_base = costo_base * cantidad
        costo_base_total += subtotal_base

        detalles.append({
            "modelo": modelo,
            "cantidad": cantidad,
            "costo_unitario_base_usd": round(costo_base, 2),
            "subtotal_base_usd": round(subtotal_base, 2),
            "precio_unitario_final_usd": round(
                calcular_precio_final(costo_base), 2
            ),
            "subtotal_final_usd": round(
                calcular_precio_final(costo_base) * cantidad, 2
            ),
        })

    # Precio final total
    precio_total = calcular_precio_final(costo_base_total)

    return {
        "costo_base_total_usd": round(costo_base_total, 2),
        "detalles": detalles,
        "cantidad_turbinas_total": sum(t.get("cantidad", 1) for t in turbinas_list),
        "precio_final_total_usd": precio_total,
        "desglose": desglose_precio(costo_base_total),
    }


def calcular_bom_sistema_completo(
    turbinas_base_usd: float,
    cantidad_turbinas: int,
    inversor_base_usd: float,
    bess_base_usd: float = 0.0,
) -> Dict:
    """
    Calcula precio total de sistema completo (turbinas + inversor + BESS).

    Args:
        turbinas_base_usd   : Costo base total de turbinas (USD, ya incluye cantidad)
        cantidad_turbinas   : Número de turbinas (para referencia)
        inversor_base_usd   : Costo base de inversor (USD)
        bess_base_usd       : Costo base de BESS (USD); default 0

    Returns:
        dict con desglose de sistema completo
    """
    # Turbinas: turbinas_base_usd ya es el total, no multiplicar por cantidad
    # Inversor y BESS: precios unitarios (cantidad = 1)
    equipos = {
        "turbinas": {
            "costo_base_total": turbinas_base_usd,
            "cantidad": cantidad_turbinas,
        },
        "inversor": {
            "costo_base_unitario": inversor_base_usd,
            "cantidad": 1,
        },
        "bess": {
            "costo_base_unitario": bess_base_usd,
            "cantidad": 1,
        },
    }

    detalles = {}
    costo_total_base = 0.0

    # Turbinas (tratamiento especial: total ya incluido)
    turb_specs = equipos["turbinas"]
    costo_turb_total = turb_specs["costo_base_total"]
    detalles["turbinas"] = {
        "cantidad": turb_specs["cantidad"],
        "costo_base_unitario_usd": round(costo_turb_total / turb_specs["cantidad"] if turb_specs["cantidad"] > 0 else 0, 2),
        "costo_base_total_usd": round(costo_turb_total, 2),
        "precio_final_unitario_usd": round(calcular_precio_final(costo_turb_total / turb_specs["cantidad"]) if turb_specs["cantidad"] > 0 else 0, 2),
        "precio_final_total_usd": round(calcular_precio_final(costo_turb_total), 2),
    }
    costo_total_base += costo_turb_total

    # Inversor y BESS (precios unitarios)
    for equipo_tipo in ["inversor", "bess"]:
        specs = equipos[equipo_tipo]
        costo_base_unit = specs["costo_base_unitario"]
        cantidad = specs["cantidad"]
        costo_base_total = costo_base_unit * cantidad

        precio_final_unit = calcular_precio_final(costo_base_unit)
        precio_final_total = precio_final_unit * cantidad

        detalles[equipo_tipo] = {
            "cantidad": cantidad,
            "costo_base_unitario_usd": round(costo_base_unit, 2),
            "costo_base_total_usd": round(costo_base_total, 2),
            "precio_final_unitario_usd": round(precio_final_unit, 2),
            "precio_final_total_usd": round(precio_final_total, 2),
        }

        costo_total_base += costo_base_total

    # Precio final total
    precio_final_total = calcular_precio_final(costo_total_base)

    return {
        "detalles_equipos": detalles,
        "costo_base_total_usd": round(costo_total_base, 2),
        "precio_final_total_usd": round(precio_final_total, 2),
        "desglose_general": desglose_precio(costo_total_base),
    }


def calcular_precio_kwh_instalado(
    precio_sistema_usd: float,
    potencia_pico_w: int,
) -> float:
    """
    Calcula costo por kW de capacidad instalada.

    Args:
        precio_sistema_usd : Precio total del sistema (USD)
        potencia_pico_w    : Potencia pico del sistema (W)

    Returns:
        float: Precio por kW (USD/kW)
    """
    potencia_kw = potencia_pico_w / 1000
    if potencia_kw <= 0:
        raise ValueError("Potencia debe ser mayor a 0")

    precio_por_kw = precio_sistema_usd / potencia_kw
    return round(precio_por_kw, 2)


def estimar_ahorro_anual(
    energia_anual_kwh: float,
    tarifa_kwh_usd: float,
) -> Dict[str, float]:
    """
    Estima ahorro anual en facturas eléctricas.

    Args:
        energia_anual_kwh : Energía anual generada (kWh)
        tarifa_kwh_usd    : Tarifa eléctrica ($/kWh)

    Returns:
        dict con ahorros estimados
    """
    ahorro_anual = energia_anual_kwh * tarifa_kwh_usd

    return {
        "energia_anual_kwh": energia_anual_kwh,
        "tarifa_kwh_usd": tarifa_kwh_usd,
        "ahorro_anual_usd": round(ahorro_anual, 2),
        "ahorro_mensual_promedio_usd": round(ahorro_anual / 12, 2),
        "ahorro_diario_promedio_usd": round(ahorro_anual / 365, 2),
    }


def calcular_precio_venta(costo_base_usd, costo_importacion_usd=IMPORT_COST_USD,
                           margen_pct=MARGIN_PCT*100):
    """
    Precio_Venta = (Costo_Base + Costo_Importacion) x (1 + Margen/100)

    Wrapper compatible con la versión anterior de PR #18.
    costo_base_usd: costo de fábrica o de lista del componente (turbina, inversor o
    BESS), SIN importación ni margen todavía.
    """
    return (costo_base_usd + costo_importacion_usd) * (1 + margen_pct / 100)
