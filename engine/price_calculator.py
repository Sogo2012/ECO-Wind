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


def calcular_precio_venta(costo_base_usd, costo_importacion_usd=COSTO_IMPORTACION_USD_DEFAULT,
                           margen_pct=MARGEN_VENTA_PCT_DEFAULT):
    """
    Precio_Venta = (Costo_Base + Costo_Importacion) x (1 + Margen/100)

    costo_base_usd: costo de fábrica o de lista del componente (turbina, inversor o
    BESS), SIN importación ni margen todavía.
    """
    return (costo_base_usd + costo_importacion_usd) * (1 + margen_pct / 100)


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
