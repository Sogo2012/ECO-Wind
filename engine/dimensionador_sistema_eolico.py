"""
Dimensionador de Sistema Eólico Hybrid Flower Turbines + Sol-Ark

Flujo de diseño:
1. Usuario selecciona 4 turbinas Flower Turbines
2. App calcula potencia pico + energía anual del arreglo
3. Controladores individuales (uno por turbina) se conectan en PARALELO → bus 48V DC
4. Función dimensiona Inversor Sol-Ark + BESS apropiados
5. Retorna arquitectura completa: voltajes, corrientes, compatibilidades

Reglas técnicas:
- Arreglo eólico: Paralelo de corrientes a voltaje constante (48V DC estándar)
- Inversor Sol-Ark: Permite sobredimensionamiento 1.3x a 2x en entrada DC
- BESS: Debe estar en MISMO voltaje que arreglo (48V DC)
- Autonomía: Capacidad = (consumo_diario × horas_autonomia / 24) × factor_ineficiencia
"""

import pandas as pd
from typing import List, Dict, Tuple, Optional
from engine.flowerturbines_specs import get_flowerturbines_df
from engine.solark_specs import get_solark_df, get_solark_inversores_df, get_solark_bess_df


def calcular_energia_arreglo_eolico(turbinas_seleccionadas: List[str]) -> Dict:
    """
    Calcula potencia pico y energía anual del arreglo de turbinas.

    Args:
        turbinas_seleccionadas: Lista de modelos de turbinas (ej: ['FT 1.15M', 'FT 2M'])

    Returns:
        dict con:
        - potencia_pico_W: Suma de potencias nominales
        - energía_anual_kWh: (a proporcionar por app después del análisis mensual/horario)
        - turbinas_detalles: DataFrame con specs de cada turbina
    """
    df_specs = get_flowerturbines_df()

    turbinas_data = []
    potencia_pico_total_W = 0

    for modelo in turbinas_seleccionadas:
        fila = df_specs[df_specs['Modelo'] == modelo]
        if fila.empty:
            raise ValueError(f"Modelo de turbina '{modelo}' no encontrado en specs")

        potencia_W = fila['Potencia_Nominal_W'].values[0]
        potencia_pico_total_W += potencia_W
        turbinas_data.append(fila.iloc[0].to_dict())

    return {
        'potencia_pico_W': potencia_pico_total_W,
        'cantidad_turbinas': len(turbinas_seleccionadas),
        'turbinas_detalles': pd.DataFrame(turbinas_data),
        'voltaje_sistema_V': 48,  # Estándar para 4+ turbinas
        'conexion_controladores': 'Paralelo (suma de corrientes)'
    }


def calcular_corriente_total_dc(potencia_pico_W: int, voltaje_dc_V: int = 48) -> float:
    """
    Calcula corriente DC total del arreglo de turbinas.

    Formula: I = P / V

    Args:
        potencia_pico_W: Potencia pico total del arreglo en watts
        voltaje_dc_V: Voltaje DC del sistema (default 48V)

    Returns:
        Corriente en amperios
    """
    return potencia_pico_W / voltaje_dc_V


def seleccionar_inversor_solark(potencia_pico_W: int,
                                voltaje_sistema_V: int = 48) -> Dict:
    """
    Selecciona el inversor Sol-Ark más apropiado basado en potencia pico del arreglo.

    Criterio: El inversor debe poder MANEJAR la potencia DC de entrada
    Sol-Ark permite sobredimensionamiento 1.3x a 2x en entrada DC

    Ejemplo:
    - Arreglo eólico genera 18 kW pico
    - Sol-Ark 18K (18 kW CA) puede recibir hasta 28.8 kW DC
    - Por lo tanto, es compatible

    Args:
        potencia_pico_W: Potencia pico en watts
        voltaje_sistema_V: Voltaje DC (48V es estándar para eólico)

    Returns:
        dict con inversor seleccionado y análisis de compatibilidad
    """
    df_inversores = get_solark_inversores_df()

    # Mapeo de capacidad de entrada DC máxima por modelo
    capacidad_entrada_dc_max = {
        '18K-2P-LV (Residencial)': 32400,      # 1.8x sobredimensionamiento
        '30K-3P-208V (Comercial)': 39000,      # 1.3x sobredimensionamiento
        '60K-3P-480V (Comercial/Industrial)': 78000,  # 1.3x sobredimensionamiento
    }

    # Buscar inversor adecuado
    for idx, row in df_inversores.iterrows():
        modelo = row['Modelo']
        capacidad_max_dc = capacidad_entrada_dc_max.get(modelo)

        if capacidad_max_dc and potencia_pico_W <= capacidad_max_dc:
            # Verificar que voltaje 48V sea compatible
            if voltaje_sistema_V == 48:
                factor_sobrecap = potencia_pico_W / row['Potencia_Salida_CA_Continua_W']

                return {
                    'modelo': modelo,
                    'potencia_ca_salida_W': row['Potencia_Salida_CA_Continua_W'],
                    'costo_USD': row['Costo_USD'],
                    'voltaje_entrada_dc_V': voltaje_sistema_V,
                    'voltaje_salida_ca_V': row['Voltaje_Salida_CA'],
                    'capacidad_entrada_dc_max_W': capacidad_max_dc,
                    'factor_sobredimensionamiento': factor_sobrecap,
                    'compatible': True,
                    'razon': f"Arreglo {potencia_pico_W}W cabe en capacidad DC máx {capacidad_max_dc}W"
                }

    raise ValueError(
        f"No hay inversor Sol-Ark disponible para arreglo de {potencia_pico_W}W "
        f"en voltaje {voltaje_sistema_V}V. "
        f"Máximo soportado: 60 kW CA (78 kW DC entrada)"
    )


def dimensionar_bess(consumo_diario_kWh: float,
                     horas_autonomia: int = 12,
                     margen_ineficiencia: float = 0.15) -> Dict:
    """
    Dimensiona el banco de baterías (BESS) basado en consumo y autonomía.

    Formula:
    Energía_almacenamiento = (consumo_diario_kWh × horas_autonomia / 24) × (1 + margen_ineficiencia)

    Args:
        consumo_diario_kWh: Consumo diario en kWh (del usuario)
        horas_autonomia: Horas de respaldo sin generación (default 12h)
        margen_ineficiencia: Factor de pérdidas (0.15 = 15% adicional)

    Returns:
        dict con capacidad requerida y recomendación de BESS
    """
    # Cálculo de energía requerida
    energia_requerida = (consumo_diario_kWh * horas_autonomia) / 24

    # Aplicar margen de ineficiencia
    capacidad_nominal = energia_requerida * (1 + margen_ineficiencia)

    return {
        'consumo_diario_kWh': consumo_diario_kWh,
        'horas_autonomia': horas_autonomia,
        'energia_requerida_kWh': energia_requerida,
        'margen_ineficiencia_pct': margen_ineficiencia * 100,
        'capacidad_nominal_kWh': capacidad_nominal
    }


def seleccionar_bess_solark(capacidad_requerida_kWh: float,
                            voltaje_sistema_V: int = 48) -> Dict:
    """
    Selecciona el banco de baterías Sol-Ark más apropiado.

    El BESS debe estar en el MISMO voltaje que el arreglo eólico (48V).

    Args:
        capacidad_requerida_kWh: Capacidad mínima requerida en kWh
        voltaje_sistema_V: Voltaje DC del sistema (48V estándar)

    Returns:
        dict con BESS(s) recomendado(s)
    """
    df_bess = get_solark_bess_df()

    # Filtrar BESS compatible con voltaje 48V (interior o exterior)
    bess_48v = df_bess[
        (df_bess['Voltaje_Nominal_CC_V'] == 48) |
        (df_bess['Ubicacion_Instalacion'].isin(['Interior', 'Exterior']))
    ]

    # Encontrar opción más cercana por capacidad
    bess_seleccionados = []
    capacidad_acumulada = 0

    for idx, row in bess_48v.sort_values('Capacidad_kWh').iterrows():
        if capacidad_acumulada >= capacidad_requerida_kWh:
            break

        bess_seleccionados.append({
            'modelo': row['Modelo'],
            'capacidad_kWh': row['Capacidad_kWh'],
            'capacidad_usable_kWh': row['Capacidad_Usable_kWh'],
            'voltaje_V': row['Voltaje_Nominal_CC_V'],
            'costo_USD': row['Costo_USD'],
            'ubicacion': row['Ubicacion_Instalacion'],
            'corriente_max_A': row['Corriente_Carga_Max_A']
        })

        capacidad_acumulada += row['Capacidad_Usable_kWh']

    if not bess_seleccionados:
        raise ValueError(
            f"No hay BESS disponible para capacidad requerida {capacidad_requerida_kWh}kWh "
            f"en voltaje {voltaje_sistema_V}V"
        )

    return {
        'bess_seleccionados': bess_seleccionados,
        'capacidad_total_kWh': sum(b['Capacidad_Usable_kWh'] for b in bess_seleccionados),
        'cantidad_modulos': len(bess_seleccionados),
        'costo_total_USD': sum(b['Costo_USD'] for b in bess_seleccionados),
        'voltaje_sistema_V': voltaje_sistema_V
    }


def dimensionar_sistema_eolico_completo(
    turbinas_seleccionadas: List[str],
    consumo_diario_kWh: float,
    horas_autonomia: int = 12,
    energia_anual_kWh: Optional[float] = None
) -> Dict:
    """
    FUNCIÓN PRINCIPAL: Dimensiona todo el sistema eólico.

    Flujo:
    1. Calcula arreglo de turbinas (potencia, corriente)
    2. Selecciona inversor Sol-Ark compatible
    3. Dimensiona BESS según consumo + autonomía
    4. Retorna arquitectura completa

    Args:
        turbinas_seleccionadas: Lista de modelos de turbinas (ej: ['FT 1.15M', 'FT 2M', 'FT 3M', 'FT 1.15M'])
        consumo_diario_kWh: Consumo diario del usuario (kWh/día)
        horas_autonomia: Horas de respaldo deseadas (default 12h)
        energia_anual_kWh: Energía anual calculada por la app (opcional para validación)

    Returns:
        dict con arquitectura completa del sistema
    """

    # PASO 1: Calcular arreglo de turbinas
    arreglo = calcular_energia_arreglo_eolico(turbinas_seleccionadas)
    corriente_dc_total = calcular_corriente_total_dc(
        arreglo['potencia_pico_W'],
        arreglo['voltaje_sistema_V']
    )

    # PASO 2: Seleccionar inversor
    inversor = seleccionar_inversor_solark(
        arreglo['potencia_pico_W'],
        arreglo['voltaje_sistema_V']
    )

    # PASO 3: Dimensionar BESS
    bess_req = dimensionar_bess(consumo_diario_kWh, horas_autonomia)
    bess = seleccionar_bess_solark(
        bess_req['capacidad_nominal_kWh'],
        arreglo['voltaje_sistema_V']
    )

    # RESUMEN ARQUITECTURA
    return {
        'arquitectura_general': {
            'tipo_sistema': 'Sistema Eólico Híbrido (Off-Grid / Backup)',
            'voltaje_dc_sistema_V': arreglo['voltaje_sistema_V'],
            'frecuencia_ca_Hz': 50 if '50' in inversor['voltaje_salida_ca_V'] else 60,
            'topologia_generacion': 'Turbinas eólicas (AC) → Controladores individuales (DC) → Bus 48V paralelo'
        },

        'arreglo_turbinas': {
            'cantidad': arreglo['cantidad_turbinas'],
            'modelos': turbinas_seleccionadas,
            'potencia_pico_total_W': arreglo['potencia_pico_W'],
            'energia_anual_kWh': energia_anual_kWh or "Calculada por app",
            'voltaje_dc_V': arreglo['voltaje_sistema_V'],
            'corriente_total_dc_A': round(corriente_dc_total, 2),
            'configuracion_controladores': 'Individual por turbina (4x controladores) → Paralelo en bus 48V'
        },

        'inversor_seleccionado': {
            'modelo': inversor['modelo'],
            'potencia_ca_continua_W': inversor['potencia_ca_salida_W'],
            'voltaje_entrada_dc_V': inversor['voltaje_entrada_dc_V'],
            'voltaje_salida_ca_V': inversor['voltaje_salida_ca_V'],
            'capacidad_entrada_dc_max_W': inversor['capacidad_entrada_dc_max_W'],
            'factor_sobredimensionamiento_entrada': round(inversor['factor_sobredimensionamiento'], 2),
            'costo_USD': inversor['costo_USD'],
            'compatible': inversor['compatible'],
            'razon_compatibilidad': inversor['razon']
        },

        'bess_seleccionado': {
            'cantidad_modulos': bess['cantidad_modulos'],
            'modelos': [b['modelo'] for b in bess['bess_seleccionados']],
            'capacidad_total_usable_kWh': round(bess['capacidad_total_kWh'], 2),
            'voltaje_bess_V': bess['voltaje_sistema_V'],
            'costo_total_USD': bess['costo_total_USD'],
            'detalles_modulos': bess['bess_seleccionados']
        },

        'dimensionamiento_bess': {
            'consumo_diario_kWh': bess_req['consumo_diario_kWh'],
            'horas_autonomia': bess_req['horas_autonomia'],
            'energia_requerida_kWh': round(bess_req['energia_requerida_kWh'], 2),
            'margen_ineficiencia_pct': bess_req['margen_ineficiencia_pct'],
            'capacidad_nominal_calculada_kWh': round(bess_req['capacidad_nominal_kWh'], 2)
        },

        'costo_total_sistema_USD': inversor['costo_USD'] + bess['costo_total_USD'],

        'notas_tecnicas': [
            "✓ Arreglo eólico en 48V DC: controladores individuales en paralelo",
            "✓ Inversor Sol-Ark integra convertidor DC-DC interno",
            "✓ BESS en mismo voltaje que arreglo (48V DC)",
            "✓ Autolimitación del inversor si arreglo produce más que capacidad CA",
            "✓ Sistema listo para Off-Grid, Backup o Interconexión a red"
        ]
    }


if __name__ == "__main__":
    # Ejemplo de uso
    turbinas = ['Small Tulip Turbine (1m)', 'Medium Tulip Turbine (2m)',
                '3-Meter Tulip Turbine', 'Large Tulip Turbine']

    resultado = dimensionar_sistema_eolico_completo(
        turbinas_seleccionadas=turbinas,
        consumo_diario_kWh=30,
        horas_autonomia=12
    )

    print("=" * 80)
    print("DIMENSIONAMIENTO COMPLETO DEL SISTEMA EÓLICO")
    print("=" * 80)

    import json
    print(json.dumps(resultado, indent=2, default=str))
