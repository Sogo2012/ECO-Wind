# engine/price_calculator.py
# =============================================================================
# Calculador de Precios para Turbinas Flower y Sistemas Sol-Ark
# Aplica márgenes comerciales e importación
# =============================================================================

from typing import Dict, List, Optional

# Sin decidir todavia (pendiente, Hallazgo 40/41): la lectura literal del plan aplica
# el fee de importacion POR SKU -- con un proyecto de varias lineas (turbinas +
# inversor + varios modulos de BESS) eso puede sumar $15,000-$20,000+ solo en
# "importacion" para un sistema residencial modesto, probablemente muy por encima de
# lo que cuesta de verdad un embarque consolidado real. Se deja como parametro
# explicito (MODO_IMPORTACION_DEFAULT), no hardcodeado en la formula, para poder
# recalcular todo el CAPEX con el otro modo en cuanto haya un dato real de flete/
# aduana consolidado -- "sensibilizar" el numero despues sin tocar la logica.
MODO_IMPORTACION_DEFAULT = "por_sku"  # o "por_proyecto"


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


def calcular_precio_venta_proyecto(costos_base_usd, costo_importacion_usd=IMPORT_COST_USD,
                                    margen_pct=MARGIN_PCT * 100,
                                    modo_importacion=MODO_IMPORTACION_DEFAULT):
    """
    Aplica calcular_precio_venta() a una LISTA de costos base (un proyecto completo:
    turbinas + inversor + BESS, cada uno su propio costo base) -- resuelve la
    pregunta pendiente de "importación por SKU o por proyecto" como un parámetro, no
    como una decisión definitiva enterrada en la fórmula.

    costos_base_usd: lista de costos base, uno por línea/componente del proyecto.

    modo_importacion:
      "por_sku"      (default, lectura literal del plan): cada línea paga su propio
                     costo_importacion_usd -- se llama calcular_precio_venta() una
                     vez por línea.
      "por_proyecto": un solo costo_importacion_usd para TODO el proyecto (un
                     embarque consolidado), repartido... no prorrateado por línea,
                     sino aplicado una sola vez sobre la SUMA de costos base.

    Devuelve (precios_por_linea, precio_total) -- precios_por_linea es None en modo
    "por_proyecto" porque ahí no tiene sentido un precio de venta por línea aislado
    (el fee de importación es del embarque, no de cada pieza).
    """
    if modo_importacion == "por_sku":
        precios_por_linea = [calcular_precio_venta(c, costo_importacion_usd, margen_pct)
                              for c in costos_base_usd]
        return precios_por_linea, sum(precios_por_linea)
    elif modo_importacion == "por_proyecto":
        precio_total = calcular_precio_venta(sum(costos_base_usd), costo_importacion_usd, margen_pct)
        return None, precio_total
    else:
        raise ValueError(f"modo_importacion debe ser 'por_sku' o 'por_proyecto', no {modo_importacion!r}")


if __name__ == "__main__":
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from engine.solark_specs import get_solark_df
    from engine.eg4_specs import get_eg4_df

    print("=" * 90)
    print("Verificación: importación por SKU vs. por proyecto -- mismo proyecto de")
    print("ejemplo (1 inversor 18K + 3 módulos EG4 LifePower4), las dos formas:")
    print("=" * 90)
    solark_18k = get_solark_df().query("Modelo == '18K-2P-LV (Residencial)'").iloc[0]
    modulo_eg4 = get_eg4_df().iloc[0]  # LifePower4, 5.12kWh c/u
    costos_proyecto = [solark_18k["Costo_USD"]] + [modulo_eg4["Costo_USD"]] * 3

    precios_sku, total_sku = calcular_precio_venta_proyecto(costos_proyecto, modo_importacion="por_sku")
    print(f"\nModo 'por_sku' (4 líneas, 4 fees de ${IMPORT_COST_USD:,.0f} = "
          f"${4 * IMPORT_COST_USD:,.0f} de importación):")
    print(f"  Total proyecto: ${total_sku:,.2f}")

    _, total_proyecto = calcular_precio_venta_proyecto(costos_proyecto, modo_importacion="por_proyecto")
    print(f"\nModo 'por_proyecto' (1 solo fee de ${IMPORT_COST_USD:,.0f} para todo el embarque):")
    print(f"  Total proyecto: ${total_proyecto:,.2f}")
    print(f"\nDiferencia: ${total_sku - total_proyecto:,.2f} -- por eso queda como parámetro, no")
    print("hardcodeado, hasta tener un dato real de flete/aduana consolidado.")
