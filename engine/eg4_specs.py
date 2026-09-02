"""
Especificaciones de banco de baterías EG4 (LiFePO4, 48V) -- tercero, NO Sol-Ark.

POR QUÉ ESTE ARCHIVO EXISTE (no es un capricho de nomenclatura): Sol-Ark confirmó
explícitamente que NO fabrica ni vende una batería de litio propia para su línea
residencial de 48V (9K a 18K, la línea compatible en DC directo con el bus de 48V de
las turbinas Flower Turbines) -- su único producto de batería de marca propia es la
Serie L3, que es exclusivamente de alta tensión (307-614V) para los inversores
comerciales 30K/60K (ver `solark_specs.py`, verificado contra los datasheets reales
PS-00019 Rev.11 y PS-00020 Rev.13). Para 48V, Sol-Ark deriva a socios certificados vía
"Custom Battery Mode" (BMS por Modbus RTU/RS-485 o CANBus) -- EG4 es la opción más
documentada públicamente del mercado (misma distribuidora que Sol-Ark en EE.UU.,
Signature Solar), preferida sobre otras opciones sugeridas (Renon Power, Fortress,
HomeGrid, Pylontech, SimpliPhi) porque tiene múltiples fuentes públicas independientes
con precio verificable -- las otras no se pudieron verificar con la misma solidez.

DIFERENCIA IMPORTANTE con los datos de Sol-Ark (`solark_specs.py`): esos precios salen
de una COTIZACIÓN DE FÁBRICA real a un distribuidor (Q1136780, Miami Greentech/
International, 28/ago/2026) -- son precio de lista al por mayor. Los precios de EG4 acá
son precio DE VENTA AL PÚBLICO de varios distribuidores/instaladores de EE.UU.
(retail, no mayorista/fábrica) -- ya traen el margen de ESE distribuidor incluido. Si se
les aplica encima el mismo `calcular_precio_venta()` (import + margen 30%,
price_calculator.py) que a un costo de fábrica real, el resultado sobreestima el precio
final más que con Sol-Ark/Flower Turbines -- declarado explícito, no oculto. Conseguir
una cotización de fábrica/mayorista real de EG4 (o de cualquiera de los otros socios
sugeridos) sigue pendiente para reemplazar esto por un dato de la misma calidad que
Sol-Ark.

Fuentes (búsqueda web, 02/sep/2026 -- varios listados independientes, sin cotización
de fábrica propia todavía):
- EG4 LifePower4 48V spec sheet (EG4 Electronics, fabricante):
  https://eg4electronics.com/wp-content/uploads/2024/04/EG4-LifePower4-48V-Spec-Sheet.pdf
- Precio LifePower4 V2, rango observado $1,199-$1,477 en distintos distribuidores:
  https://www.wattbuild.com/products/292/EG4/LiFePower4-V2-48V-100AH ($1,199, el más bajo verificado)
  https://offgridstores.com/products/eg4-lifepower4-v2-48v-100ah-lithium-server-rack-batteries-2-6-battery-bundles ($1,476.99)
  https://www.thesolarlab.com/review/eg4-48v-100ah-v2-lifepower4-battery-review (~$1,150-1,200 con descuento)
- Precio WallMount Indoor 14.3kWh, rango observado $2,700-$3,849.95:
  https://diysolarforum.com/threads/eg4-wallmount-indoor-14-3kwh-2-700.128372/ ($2,700, caída de precio puntual en Signature Solar)
  https://www.langstonsalternativepower.com/... ($2,900)
  https://offgridstores.com/products/eg4-48v-280ah-wallmount-indoor-battery ($3,849.95)

Se usó el precio MÁS BAJO verificado de cada modelo como `Costo_USD` -- una elección
conservadora explícita (mejor subestimar el costo base y que la cotización final salga
un poco optimista, que sobreestimarlo con el precio más alto encontrado), no un
promedio ni el precio más común.
"""
import pandas as pd

EG4_SPECS = [
    {
        "Modelo": "EG4 LifePower4 V2 (48V 100Ah)",
        "Fabricante": "EG4 Electronics (tercero, NO Sol-Ark)",
        "Tipo_Equipo": "Módulo de Batería (LiFePO4)",
        "Costo_USD": 1199.00,
        "Fuente_Precio": "retail EE.UU., precio más bajo verificado -- NO cotización de fábrica",
        "Capacidad_kWh": 5.12,
        "Capacidad_Ah": 100,
        "Voltaje_Nominal_CC_V": 51.2,
        "Corriente_BMS_Max_A": 100,
        "Max_Unidades_Paralelo": 64,
        "Ciclos_80pct_DoD": 6000,
        "Comunicacion": "Modbus RTU/RS-485 o CAN -- compatible cerrado con Sol-Ark, Schneider, Growatt, EG4",
        "Altura_cm": 47.0,
        "Ancho_cm": 44.2,
        "Profundidad_cm": 15.5,
        "Peso_kg": 45.2,
        "Garantia_Anos": 10,
        "Notas_Tecnicas": "Módulo pequeño (misma capacidad que un módulo individual de la Serie L3 "
                          "de Sol-Ark, 5.12kWh) -- para sistemas chicos o para ajustar capacidad fina "
                          "apilando varios en paralelo.",
    },
    {
        "Modelo": "EG4 WallMount Indoor (48V 280Ah)",
        "Fabricante": "EG4 Electronics (tercero, NO Sol-Ark)",
        "Tipo_Equipo": "Banco de Baterías (LiFePO4)",
        "Costo_USD": 2700.00,
        "Fuente_Precio": "retail EE.UU., precio más bajo verificado -- NO cotización de fábrica",
        "Capacidad_kWh": 14.3,
        "Capacidad_Ah": 280,
        "Voltaje_Nominal_CC_V": 51.2,
        "Ubicacion_Instalacion": "Interior",
        "Certificaciones": "UL1973, UL9540A",
        "Garantia_Anos": 10,
        "Notas_Tecnicas": "Unidad más grande, mejor costo por kWh que apilar módulos LifePower4 -- "
                          "building block más práctico para sistemas residenciales medianos/grandes "
                          "(equivalente en espíritu a los bancos de 40/60kWh de la Serie L3 de Sol-Ark, "
                          "pero a 48V en vez de alta tensión).",
    },
]


def get_eg4_df():
    """DataFrame de especificaciones EG4 -- ver docstring del módulo para el aviso
    completo sobre por qué estos precios son de origen distinto (retail) a los de
    Sol-Ark/Flower Turbines (cotización de fábrica)."""
    return pd.DataFrame(EG4_SPECS)


if __name__ == "__main__":
    df = get_eg4_df()
    print(df[["Modelo", "Tipo_Equipo", "Capacidad_kWh", "Costo_USD"]])
