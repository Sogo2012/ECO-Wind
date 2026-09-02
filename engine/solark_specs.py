"""
Especificaciones técnicas detalladas de equipos Sol-Ark LATAM.

Incluye:
- 7 inversores/cargadores (9K, 12K, 12K-LL, 15K, 18K, 30K, 60K) - LATAM 2P/3P
- 3 bancos de baterías LiFePO4 (40kWh, 60kWh interior/exterior)

Todos los datos incluyen parámetros eléctricos, mecánicos y operacionales
para submittal técnico de ingeniería (datasheet-level).

Voltajes soportados:
- Residencial: 48V CC, 120/240V CA (monofásico) - Modelos 2P
- Comercial: 300V CC, 120/208V CA (trifásico) - Modelo 30K
- Industrial: 600V CC, 277/480V CA (trifásico) - Modelo 60K
- BESS: 410V-614V CC (interior/exterior con climatización)

RESUELTO (Hallazgo 44): los 4 modelos LATAM (9K, 12K, 12K-2P-LL, 15K) que Hallazgo 43
había marcado `Specs_Verificadas=False` (specs fabricadas -- dimensiones idénticas al
18K, corriente de batería escalada linealmente) ya se verificaron contra datasheets
reales de Sol-Ark que Pablo consiguió (PS-00034 Rev.3, SK150-0003 Rev.3, PS-00060 v1.1,
PS-00001 Rev.7) -- se reemplazaron todos los campos técnicos por los valores reales de
cada datasheet, la bandera `Specs_Verificadas` ya no aplica (se quita de las 4 filas).
Los 4 son físicamente distintos entre sí (dimensiones, peso, corrientes de batería y
de passthrough todas diferentes -- no hay ningún patrón de escalado lineal en los
datos reales, a diferencia de los que se habían descartado).
"""
import pandas as pd

SOLARK_SPECS = [
    {
        # Verificado (Hallazgo 44) contra datasheet real PS-00034 Rev.3 (6/jun/2025),
        # "Limitless 9K-LV", SKU 9K-2P.
        "Modelo": "9K-2P-N (Residencial)",
        "Tipo_Equipo": "Inversor/Cargador",
        "Costo_USD": 2926.83,
        "Potencia_FV_Max_W": 13000,
        "Entrada_FV_Corriente_A": 26,
        "Entrada_FV_Corriente_CC_A": 44,
        "MPPT_Cantidad": 2,
        "Voltaje_FV_Max_V": 500,
        "Potencia_Salida_CA_Continua_W": 9000,
        "Potencia_Arranque_W": 24000,
        "Voltaje_Salida_CA": "120/240V",
        "Voltaje_Salida_CA_Alternativo": "120/208V",
        "Frecuencia_CA_Hz": "50/60",
        "Corriente_Max_Salida_CA_A": 37.5,
        "Corriente_Passthrough_A": 200,
        "Voltaje_Nominal_CC_V": 48,
        "Voltaje_Operativo_CC_Min_V": 43,
        "Voltaje_Operativo_CC_Max_V": 63,
        "Corriente_Carga_Descarga_Max_A": 185,
        "Capacidad_BESS_kWh": None,
        "Altura_mm": 807,
        "Ancho_mm": 494,
        "Profundidad_mm": 306,
        "Peso_kg": 61.2,
        "Garantia_Anos": 10,
        "Firmware_Diseño": None,
        "Notas_Tecnicas": "Pico 24,000VA/10s y 30,000VA/100ms fuera de red; apilable hasta 12 en paralelo; "
                          "compatible Litio y Plomo-Ácido",
        "Stackable": True
    },
    {
        # Verificado (Hallazgo 44) contra datasheet real PS-00060-01.1 v1.1 (may/2026),
        # "Inversor Híbrido Limitless 12K", modelo 12K-2P-LL.
        "Modelo": "12K-2P-LL (Residencial)",
        "Tipo_Equipo": "Inversor/Cargador",
        "Costo_USD": 3657.32,
        "Potencia_FV_Max_W": 19200,
        "Entrada_FV_Corriente_A": 32,
        "Entrada_FV_Corriente_CC_A": 60,
        "MPPT_Cantidad": 3,
        "Voltaje_FV_Max_V": 500,
        "Potencia_Salida_CA_Continua_W": 12000,
        "Potencia_Arranque_W": 24000,
        "Voltaje_Salida_CA": "120/240V",
        "Voltaje_Salida_CA_Alternativo": "208V",
        "Frecuencia_CA_Hz": "50/60",
        "Corriente_Max_Salida_CA_A": 50.0,
        "Corriente_Passthrough_A": 100,
        "Voltaje_Nominal_CC_V": 48,
        "Voltaje_Operativo_CC_Min_V": 43,
        "Voltaje_Operativo_CC_Max_V": 59,
        "Corriente_Carga_Descarga_Max_A": 220,
        "Capacidad_BESS_kWh": None,
        "Altura_mm": 654,
        "Ancho_mm": 452,
        "Profundidad_mm": 254,
        "Peso_kg": 29.5,
        "Garantia_Anos": 10,
        "Firmware_Diseño": None,
        "Notas_Tecnicas": "12,000W continua sólo con red (grid-tied); 10,000W continua sólo con baterías "
                          "(41A@240V); puerto GEN hasta 14,000W; apilable hasta 12 en paralelo; "
                          "compatible Plomo-Ácido y Ion-Litio",
        "Stackable": True
    },
    {
        # Verificado (Hallazgo 44) contra datasheet real SK150-0003 Rev.3 (18/jun/2025),
        # "Limitless 12K-LV", SKU 12K-2P (modelo estándar, distinto del -LL).
        "Modelo": "12K-2P-N (Residencial)",
        "Tipo_Equipo": "Inversor/Cargador",
        "Costo_USD": 3926.83,
        "Potencia_FV_Max_W": 12000,
        "Entrada_FV_Corriente_A": 20,
        "Entrada_FV_Corriente_CC_A": None,  # no viene un valor de cortocircuito separado en este datasheet
        "MPPT_Cantidad": 2,
        "Voltaje_FV_Max_V": 500,
        "Potencia_Salida_CA_Continua_W": 9000,
        "Potencia_Arranque_W": 16000,
        "Voltaje_Salida_CA": "120/240V",
        "Voltaje_Salida_CA_Alternativo": "120/208V",
        "Frecuencia_CA_Hz": "50/60",
        "Corriente_Max_Salida_CA_A": 37.5,
        "Corriente_Passthrough_A": 63,
        "Voltaje_Nominal_CC_V": 48,
        "Voltaje_Operativo_CC_Min_V": 43,
        "Voltaje_Operativo_CC_Max_V": 63,
        "Corriente_Carga_Descarga_Max_A": 185,
        "Capacidad_BESS_kWh": None,
        "Altura_mm": 750,
        "Ancho_mm": 450,
        "Profundidad_mm": 254,
        "Peso_kg": 35.4,
        "Garantia_Anos": 10,
        "Firmware_Diseño": None,
        "Notas_Tecnicas": "Nameplate 12K = 9,000W CA continua (cargas/venta a red) + 3,000W CC de "
                          "baterías; sólo compatible con batería de Litio (no Plomo-Ácido); apilable "
                          "hasta 9 en paralelo",
        "Stackable": True
    },
    {
        # Verificado (Hallazgo 44) contra datasheet real PS-00001 Rev.7 (16/jul/2026),
        # "Limitless 15K", modelo 15K-2P-LV.
        "Modelo": "15K-2P-LV (Residencial)",
        "Tipo_Equipo": "Inversor/Cargador",
        "Costo_USD": 4756.10,
        "Potencia_FV_Max_W": 23400,
        "Entrada_FV_Corriente_A": 26,
        "Entrada_FV_Corriente_CC_A": 44,
        "MPPT_Cantidad": 3,
        "Voltaje_FV_Max_V": 500,
        "Potencia_Salida_CA_Continua_W": 15000,
        "Potencia_Arranque_W": 24000,
        "Voltaje_Salida_CA": "120/240V",
        "Voltaje_Salida_CA_Alternativo": "120/208V",
        "Frecuencia_CA_Hz": "50/60",
        "Corriente_Max_Salida_CA_A": 62.5,
        "Corriente_Passthrough_A": 200,
        "Voltaje_Nominal_CC_V": 48,
        "Voltaje_Operativo_CC_Min_V": 43,
        "Voltaje_Operativo_CC_Max_V": 59,
        "Corriente_Carga_Descarga_Max_A": 275,
        "Capacidad_BESS_kWh": None,
        "Altura_mm": 838,
        "Ancho_mm": 494,
        "Profundidad_mm": 306,
        "Peso_kg": 61.2,
        "Garantia_Anos": 10,
        "Firmware_Diseño": "EE. UU.",
        "Notas_Tecnicas": "15,000W continua sólo con red (62.5A@240V); 12,000W continua sólo con "
                          "baterías/off-grid (240V, 10,400W a 208V); puerto GEN hasta 80A/19,200W; "
                          "apilable hasta 12 en paralelo; compatible Plomo-Ácido y Litio",
        "Stackable": True
    },
    {
        "Modelo": "18K-2P-LV (Residencial)",
        "Tipo_Equipo": "Inversor/Cargador",
        "Costo_USD": 5613.41,
        "Potencia_FV_Max_W": 32400,
        "Entrada_FV_Corriente_A": 36,
        "Entrada_FV_Corriente_CC_A": 54,
        "MPPT_Cantidad": 3,
        "Voltaje_FV_Max_V": 500,
        "Potencia_Salida_CA_Continua_W": 18000,
        "Potencia_Arranque_W": 36000,
        "Voltaje_Salida_CA": "120/240V",
        "Voltaje_Salida_CA_Alternativo": "208V",
        "Frecuencia_CA_Hz": "50/60",
        "Corriente_Max_Salida_CA_A": 75.0,
        "Corriente_Passthrough_A": 200,
        "Voltaje_Nominal_CC_V": 48,
        "Voltaje_Operativo_CC_Min_V": 41,
        "Voltaje_Operativo_CC_Max_V": 63,
        "Corriente_Carga_Descarga_Max_A": 350,
        "Capacidad_BESS_kWh": None,
        "Altura_mm": 863,
        "Ancho_mm": 464,
        "Profundidad_mm": 282,
        "Peso_kg": 62.14,
        "Garantia_Anos": 10,
        "Firmware_Diseño": "EE. UU.",
        "Notas_Tecnicas": "Firmware diseñado en EE. UU.; 36 kW de arranque (10s); Garantía 10 años; "
                          "apilable hasta 12 en paralelo",
        "Stackable": True  # corregido (Hallazgo 44): el datasheet PS-00044 Rev.2 dice "Apilable en Paralelo: Yes; Max 12"
    },
    {
        "Modelo": "30K-3P-208V (Comercial)",
        "Tipo_Equipo": "Inversor/Cargador",
        "Costo_USD": 9090.90,
        "Potencia_FV_Max_W": 39000,
        "Entrada_FV_Corriente_A": 36,
        "Entrada_FV_Corriente_CC_A": 55,
        "MPPT_Cantidad": 4,
        "Voltaje_FV_Max_V": 550,
        "Potencia_Salida_CA_Continua_W": 30000,
        "Voltaje_Salida_CA": "120/208V Trifásico",
        "Voltaje_Salida_CA_Alternativo": None,
        "Frecuencia_CA_Hz": "50/60",
        "Corriente_Max_Salida_CA_A": 83.4,
        "Corriente_Passthrough_A": 200,
        "Corriente_Passthrough_Continua_A": 180,
        "Voltaje_Nominal_CC_V": 300,
        "Voltaje_Operativo_CC_Min_V": 160,
        "Voltaje_Operativo_CC_Max_V": 500,
        "Corriente_Carga_Descarga_Max_A": 100,
        "Corriente_Carga_Descarga_Entrada_Max_A": 50,
        "Capacidad_BESS_kWh": None,
        "Altura_mm": 894,
        "Ancho_mm": 528,
        "Profundidad_mm": 295,
        "Peso_kg": 80.00,
        "Eficiencia_CEC": 0.965,
        "Microgrid_Controller": True,
        "Stackable": True,
        "Max_Stack_Unidades": 10,
        "Notas_Tecnicas": "Microgrid controller integrado; Eficiencia CEC 96.5%; Stackable hasta 10 unidades"
    },
    {
        "Modelo": "60K-3P-480V (Comercial/Industrial)",
        "Tipo_Equipo": "Inversor/Cargador",
        "Costo_USD": 10568.18,
        "Potencia_FV_Max_W": 78000,
        "Entrada_FV_Corriente_A": 36,
        "Entrada_FV_Corriente_CC_A": 55,
        "MPPT_Cantidad": 4,
        "Voltaje_FV_Max_V": 1000,
        "Potencia_Salida_CA_Continua_W": 60000,
        "Voltaje_Salida_CA": "277/480V (Wye) o 480V (Delta)",
        "Voltaje_Salida_CA_Alternativo": None,
        "Frecuencia_CA_Hz": "50/60",
        "Corriente_Max_Salida_CA_A": 72.3,
        "Corriente_Passthrough_A": 200,
        "Corriente_Passthrough_Continua_A": 180,
        "Voltaje_Nominal_CC_V": 600,
        "Voltaje_Operativo_CC_Min_V": 160,
        "Voltaje_Operativo_CC_Max_V": 700,
        "Corriente_Carga_Descarga_Max_A": 100,
        "Corriente_Carga_Descarga_Entrada_Max_A": 50,
        "Capacidad_BESS_kWh": None,
        "Altura_mm": 894,
        "Ancho_mm": 528,
        "Profundidad_mm": 295,
        "Peso_kg": 80.00,
        "Eficiencia_CEC": 0.965,
        "Microgrid_Controller": True,
        "Stackable": True,
        "Max_Stack_Unidades": 10,
        "Notas_Tecnicas": "Microgrid controller integrado; Eficiencia CEC 96.5%; Stackable hasta 10 unidades"
    },
    {
        "Modelo": "L3-HV-40KWH (BESS Interior)",
        "Tipo_Equipo": "Banco de Baterías (LiFePO4)",
        "Costo_USD": 16255.55,
        "Capacidad_kWh": 40.96,
        "Capacidad_Usable_kWh": 36.86,
        "Potencia_Inversor_Compatible_W": 30000,
        "Tipo_Celda": "Prismática LiFePO4",
        "Ubicacion_Instalacion": "Interior",
        "IP_Rating": "IP20",
        "Voltaje_Nominal_CC_V": 410,
        "Voltaje_Operativo_CC_Min_V": 392,
        "Voltaje_Operativo_CC_Max_V": 448,
        "Corriente_Carga_Max_A": 100,
        "Corriente_Descarga_Max_A": 100,
        "Corriente_Recomendada_A": 50,
        "Corriente_Passthrough_A": 200,
        "Altura_cm": 58,
        "Ancho_cm": 58,
        "Profundidad_cm": 163,
        "Peso_kg": 434.00,
        "Supresion_Fuego": True,
        "Climatizacion": "No incluida",
        "Notas_Tecnicas": "Celda Prismática LiFePO4; Interior IP20; Supresión de fuego integrada en packs"
    },
    {
        "Modelo": "L3-HV-60KWH (BESS Interior)",
        "Tipo_Equipo": "Banco de Baterías (LiFePO4)",
        "Costo_USD": 22953.33,
        "Capacidad_kWh": 61.44,
        "Capacidad_Usable_kWh": 55.30,
        "Potencia_Inversor_Compatible_W": 60000,
        "Tipo_Celda": "Prismática LiFePO4",
        "Ubicacion_Instalacion": "Interior",
        "IP_Rating": "IP20",
        "Voltaje_Nominal_CC_V": 614.4,
        "Voltaje_Operativo_CC_Min_V": 588,
        "Voltaje_Operativo_CC_Max_V": 672,
        "Corriente_Carga_Max_A": 100,
        "Corriente_Descarga_Max_A": 100,
        "Corriente_Recomendada_A": 50,
        "Corriente_Passthrough_A": 200,
        "Altura_cm": 58,
        "Ancho_cm": 58,
        "Profundidad_cm": 218,
        "Peso_kg": 773.00,
        "Supresion_Fuego": True,
        "Climatizacion": "No incluida",
        "Notas_Tecnicas": "Celda Prismática LiFePO4; Interior IP20; Supresión de fuego integrada en packs"
    },
    {
        # Renombrado (Hallazgo 42): "L3-HVR-60KWH" es el mismo SKU/precio para DOS
        # configuraciones de voltaje distintas, según con qué inversor se empareje --
        # confirmado comparando los dos datasheets reales (PS-00019 Rev.11 480V y
        # PS-00020 Rev.13 208V). Esta fila es la variante de 614.4V (con el 60K); la
        # de 307V (con el 30K) es la fila siguiente -- antes sólo estaba esta.
        "Modelo": "L3-HVR-60KWH (BESS Exterior, 614.4V con 60K-3P-480V)",
        "Tipo_Equipo": "Banco de Baterías (LiFePO4)",
        "Costo_USD": 34424.44,
        "Capacidad_kWh": 61.44,
        "Capacidad_Usable_kWh": 55.30,
        "Potencia_Inversor_Compatible_W": 60000,
        "Tipo_Celda": "Prismática LiFePO4",
        "Ubicacion_Instalacion": "Exterior",
        "IP_Rating": "IP55",
        "Voltaje_Nominal_CC_V": 614.4,
        "Voltaje_Operativo_CC_Min_V": 588,
        "Voltaje_Operativo_CC_Max_V": 672,
        "Corriente_Carga_Max_A": 100,
        "Corriente_Descarga_Max_A": 100,
        "Corriente_Recomendada_A": 50,
        "Corriente_Passthrough_A": 200,
        "Altura_cm": 76,
        "Ancho_cm": 107,
        "Profundidad_cm": 226,
        "Peso_kg": 950.00,
        "Supresion_Fuego": True,
        "Climatizacion": "Aire acondicionado integrado",
        "Control_Temperatura": True,
        "Notas_Tecnicas": "Celda Prismática LiFePO4; Exterior IP55; Aire acondicionado integrado para control temp."
    },
    {
        # Variante de 307V (Hallazgo 42) -- mismo SKU y precio que la de arriba, pero
        # empareja con el Sol-Ark 30K-3P-208V en vez del 60K-3P-480V. Datos extraídos
        # directo de PS-00020 Rev.13 (208V), columna "Outdoor" -- no es una estimación.
        "Modelo": "L3-HVR-60KWH (BESS Exterior, 307V con 30K-3P-208V)",
        "Tipo_Equipo": "Banco de Baterías (LiFePO4)",
        "Costo_USD": 34424.44,
        "Capacidad_kWh": 61.44,
        "Capacidad_Usable_kWh": 55.30,
        "Potencia_Inversor_Compatible_W": 30000,
        "Tipo_Celda": "Prismática LiFePO4",
        "Ubicacion_Instalacion": "Exterior",
        "IP_Rating": "IP55",
        "Voltaje_Nominal_CC_V": 307,
        "Voltaje_Operativo_CC_Min_V": 294,
        "Voltaje_Operativo_CC_Max_V": 336,
        "Corriente_Carga_Max_A": 100,
        "Corriente_Descarga_Max_A": 100,
        "Corriente_Recomendada_A": 100,
        "Corriente_Passthrough_A": 200,
        "Altura_cm": 76,
        "Ancho_cm": 107,
        "Profundidad_cm": 226,
        "Peso_kg": 628.00,
        "Supresion_Fuego": True,
        "Climatizacion": "Aire acondicionado integrado",
        "Control_Temperatura": True,
        "Notas_Tecnicas": "Celda Prismática LiFePO4; Exterior IP55; config. de pack 6s6p (vs. 12s1p de la "
                          "variante 614.4V) -- mismo módulo base de 5.12kWh/51.2V, mismo peso de fábrica "
                          "distinto (628kg vs 950kg) según el propio datasheet, no es un error de transcripción."
    }
]

def get_solark_df():
    """Retorna el DataFrame unificado de especificaciones Sol-Ark."""
    return pd.DataFrame(SOLARK_SPECS)

def get_solark_inversores_df():
    """Retorna solo los inversores/cargadores."""
    df = pd.DataFrame(SOLARK_SPECS)
    return df[df['Tipo_Equipo'] == 'Inversor/Cargador'].reset_index(drop=True)

def get_solark_bess_df():
    """Retorna solo los bancos de baterías."""
    df = pd.DataFrame(SOLARK_SPECS)
    return df[df['Tipo_Equipo'] == 'Banco de Baterías (LiFePO4)'].reset_index(drop=True)

if __name__ == "__main__":
    df = get_solark_df()
    print("Todos los equipos Sol-Ark:")
    print(df[['Modelo', 'Tipo_Equipo', 'Costo_USD']])

    print("\nInversores:")
    print(get_solark_inversores_df()[['Modelo', 'Potencia_Salida_CA_Continua_W', 'Costo_USD']])

    print("\nBancos de Baterías:")
    print(get_solark_bess_df()[['Modelo', 'Capacidad_kWh', 'Costo_USD']])
