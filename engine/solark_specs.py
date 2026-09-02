"""
Especificaciones técnicas detalladas de equipos Sol-Ark.

Incluye:
- 3 inversores/cargadores (18K, 30K, 60K)
- 3 bancos de baterías LiFePO4 (40kWh, 60kWh interior/exterior)

Todos los datos incluyen parámetros eléctricos, mecánicos y operacionales
para submittal técnico de ingeniería (datasheet-level).

Voltajes soportados:
- Residencial: 48V CC, 120/240V CA (monofásico)
- Comercial: 300V CC, 120/208V CA (trifásico)
- Industrial: 600V CC, 277/480V CA (trifásico)
- BESS: 410V-614V CC (interior/exterior con climatización)
"""
import pandas as pd

SOLARK_SPECS = [
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
        "Notas_Tecnicas": "Firmware diseñado en EE. UU.; 36 kW de arranque (10s); Garantía 10 años",
        "Stackable": False
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
