"""
Cadena de valor: costo de fábrica/lista -> precio de venta al cliente final.

Misma fórmula para los tres tipos de equipo (turbinas Flower Turbines, inversores
Sol-Ark, BESS -- de Sol-Ark o de terceros como EG4), confirmada en
PLAN_ANALISIS_FINANCIERO_ECO_WIND.md sección 1:

    Precio_Venta = (Costo_Base + Costo_Importacion) x (1 + Margen%)

Un solo lugar para esta regla -- para que cualquier componente nuevo que se agregue
(otra turbina, otro inversor, otro BESS) pase por la MISMA fórmula sin reimplementarla
ni improvisar una variante distinta por archivo.

OJO con la calidad del dato de entrada (`costo_base`): la fórmula es la misma para
todos los componentes, pero el ORIGEN del costo base no lo es -- los precios de
Sol-Ark y Flower Turbines vienen de cotización de fábrica/lista de precios real; los
de EG4 (`eg4_specs.py`) son precio de venta al público de distribuidores en EE.UU.
(retail, ya con margen de ese distribuidor incluido). Aplicarles esta misma fórmula
encima es matemáticamente consistente, pero el resultado para EG4 es menos confiable
que para Sol-Ark/Flower Turbines -- ver el docstring de `eg4_specs.py`.
"""

COSTO_IMPORTACION_USD_DEFAULT = 2500
MARGEN_VENTA_PCT_DEFAULT = 30

# Sin decidir todavia (pendiente, Hallazgo 40/41): la lectura literal del plan aplica
# el fee de importacion POR SKU -- con un proyecto de varias lineas (turbinas +
# inversor + varios modulos de BESS) eso puede sumar $15,000-$20,000+ solo en
# "importacion" para un sistema residencial modesto, probablemente muy por encima de
# lo que cuesta de verdad un embarque consolidado real. Se deja como parametro
# explicito (MODO_IMPORTACION_DEFAULT), no hardcodeado en la formula, para poder
# recalcular todo el CAPEX con el otro modo en cuanto haya un dato real de flete/
# aduana consolidado -- "sensibilizar" el numero despues sin tocar la logica.
MODO_IMPORTACION_DEFAULT = "por_sku"  # o "por_proyecto"


def calcular_precio_venta(costo_base_usd, costo_importacion_usd=COSTO_IMPORTACION_USD_DEFAULT,
                           margen_pct=MARGEN_VENTA_PCT_DEFAULT):
    """
    Precio_Venta = (Costo_Base + Costo_Importacion) x (1 + Margen/100)

    costo_base_usd: costo de fábrica o de lista del componente (turbina, inversor o
    BESS), SIN importación ni margen todavía.
    """
    return (costo_base_usd + costo_importacion_usd) * (1 + margen_pct / 100)


def calcular_precio_venta_proyecto(costos_base_usd, costo_importacion_usd=COSTO_IMPORTACION_USD_DEFAULT,
                                    margen_pct=MARGEN_VENTA_PCT_DEFAULT,
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
    print("Verificación: misma fórmula aplicada a un costo de FÁBRICA real (Sol-Ark)")
    print("vs. a un costo de RETAIL (EG4) -- para que la diferencia de origen del dato")
    print("quede visible en el precio final, no escondida.")
    print("=" * 90)

    solark_18k = get_solark_df().query("Modelo == '18K-2P-LV (Residencial)'").iloc[0]
    print(f"\nSol-Ark 18K (costo de fábrica real, cotización Q1136780):")
    print(f"  Costo base:      ${solark_18k['Costo_USD']:>10,.2f}")
    precio_18k = calcular_precio_venta(solark_18k["Costo_USD"])
    print(f"  + importación:   ${COSTO_IMPORTACION_USD_DEFAULT:>10,.2f}")
    print(f"  x 1.30 margen -> Precio de venta: ${precio_18k:>10,.2f}")

    for _, fila in get_eg4_df().iterrows():
        print(f"\nEG4 {fila['Modelo']} (costo RETAIL más bajo verificado, no de fábrica):")
        print(f"  Costo base:      ${fila['Costo_USD']:>10,.2f}")
        precio = calcular_precio_venta(fila["Costo_USD"])
        print(f"  + importación:   ${COSTO_IMPORTACION_USD_DEFAULT:>10,.2f}")
        print(f"  x 1.30 margen -> Precio de venta: ${precio:>10,.2f}  "
              f"(${precio / fila['Capacidad_kWh']:.0f}/kWh)")

    print()
    print("=" * 90)
    print("Pregunta pendiente: importación por SKU vs. por proyecto -- mismo proyecto")
    print("de ejemplo (1 inversor 18K + 3 módulos EG4 LifePower4), las dos formas:")
    print("=" * 90)
    modulo_eg4 = get_eg4_df().iloc[0]  # LifePower4, 5.12kWh c/u
    costos_proyecto = [solark_18k["Costo_USD"]] + [modulo_eg4["Costo_USD"]] * 3

    precios_sku, total_sku = calcular_precio_venta_proyecto(costos_proyecto, modo_importacion="por_sku")
    print(f"\nModo 'por_sku' (4 líneas, 4 fees de $2,500 = ${4 * COSTO_IMPORTACION_USD_DEFAULT:,.0f} de importación):")
    print(f"  Total proyecto: ${total_sku:,.2f}")

    _, total_proyecto = calcular_precio_venta_proyecto(costos_proyecto, modo_importacion="por_proyecto")
    print(f"\nModo 'por_proyecto' (1 solo fee de ${COSTO_IMPORTACION_USD_DEFAULT:,.0f} para todo el embarque):")
    print(f"  Total proyecto: ${total_proyecto:,.2f}")
    print(f"\nDiferencia: ${total_sku - total_proyecto:,.2f} -- por eso queda como parámetro, no")
    print("hardcodeado, hasta tener un dato real de flete/aduana consolidado.")
