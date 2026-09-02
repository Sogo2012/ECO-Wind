# engine/sistema_eolico_completo.py
# =============================================================================
# Análisis Técnico y Financiero Integrado de Sistemas Eólicos
# Combina dimensionamiento + precios + análisis financiero
# =============================================================================

from typing import Dict, List, Optional
from engine.dimensionador_sistema_eolico import dimensionar_sistema_eolico_completo
from engine.financial_engine_eolico import FinancialEngineEolico
from engine.price_calculator import (
    calcular_precio_final,
    calcular_precio_kwh_instalado,
)


def analizar_sistema_eolico_completo(
    turbinas_seleccionadas: List[str],
    consumo_diario_kWh: float,
    energia_anual_kWh: float,
    horas_autonomia: int = 12,
    tarifa_kwh_USD: float = 0.15,
    sistema_tipo: str = "Standalone",
    costo_instalacion_pct: float = 0.35,
    vida_util_anos: int = 40,
    tasa_descuento_pct: float = 8.0,
) -> Dict:
    """
    Análisis técnico y financiero integrado de sistema eólico.

    Calcula:
    1. Dimensionamiento completo (turbinas + inversor + BESS si aplica)
    2. Costos de equipos con margen e importación
    3. Análisis financiero (CAPEX, OPEX, Payback, ROI, NPV)
    4. Indicadores de viabilidad económica

    Args:
        turbinas_seleccionadas  : Lista de CLAVES CANÓNICAS de turbinas -- las mismas
                                  que usa el resto de la app (ver
                                  engine/turbine_specs.py::SPECS_TURBINAS), p. ej.
                                  ['small_tulip', 'medium_tulip'], NO nombres
                                  completos de modelo.
        consumo_diario_kWh      : Consumo diario del usuario (kWh/día)
        energia_anual_kWh       : Energía anual generada por simulación (kWh/año)
        horas_autonomia         : Horas de respaldo para BESS (default 12)
        tarifa_kwh_USD          : Tarifa eléctrica ($/kWh; default $0.15)
        sistema_tipo            : "Standalone" (con BESS) o "Hybrid" (sin BESS)
        costo_instalacion_pct   : Costo instalación como % de equipos (default 35%)
        vida_util_anos          : Vida útil del proyecto (default 40)
        tasa_descuento_pct      : Tasa descuento para NPV (default 8%)

    Returns:
        dict con análisis técnico-financiero completo. Si el arreglo no tiene
        inversor Sol-Ark compatible en DC directo, o si falta el costo de fábrica de
        alguna turbina seleccionada, el análisis financiero NO se calcula (no hay
        CAPEX real con el que hacerlo) -- se devuelve la arquitectura técnica ya
        calculada más `pendiente_ingenieria_o_costo=True` y una nota explícita, en
        vez de adivinar un número o lanzar una excepción.
    """

    # PASO 1: Dimensionamiento técnico (incluye costo de turbinas -- ver
    # calcular_costo_arreglo_turbinas() en dimensionador_sistema_eolico.py, misma
    # fuente de verdad que el resto de la app, turbine_specs.py::SPECS_TURBINAS)
    arquitectura = dimensionar_sistema_eolico_completo(
        turbinas_seleccionadas=turbinas_seleccionadas,
        consumo_diario_kWh=consumo_diario_kWh,
        horas_autonomia=horas_autonomia,
        energia_anual_kWh=energia_anual_kWh,
    )

    potencia_pico = arquitectura["arreglo_turbinas"]["potencia_pico_total_W"]
    n_turbinas = arquitectura["arreglo_turbinas"]["cantidad"]
    costo_turbinas_total = arquitectura["arreglo_turbinas"]["costo_total_usd"]

    if not arquitectura["inversor_seleccionado"]["compatible"] or costo_turbinas_total is None:
        return {
            "resumen_ejecutivo": {
                "sistema_tipo": sistema_tipo,
                "potencia_pico_kw": round(potencia_pico / 1000, 2),
                "cantidad_turbinas": n_turbinas,
                "energia_anual_kwh": round(energia_anual_kWh, 0),
                "consumo_diario_kwh": consumo_diario_kWh,
            },
            "arquitectura_tecnica": arquitectura,
            "analisis_financiero": None,
            "pendiente_ingenieria_o_costo": True,
            "nota_pendiente": arquitectura.get("nota_pendiente") or (
                "Falta el costo de fábrica de al menos una turbina seleccionada "
                f"({arquitectura['arreglo_turbinas']['turbinas_sin_costo']}) -- no se "
                "puede calcular CAPEX real todavía."
            ),
        }

    costo_inversor_base = arquitectura["inversor_seleccionado"]["costo_USD"]
    costo_bess_base = arquitectura["bess_seleccionado"]["costo_total_USD"]

    # PASO 3: Aplicar margen y costo de importación
    costo_turbinas_con_margen = calcular_precio_final(costo_turbinas_total)
    costo_inversor_con_margen = calcular_precio_final(costo_inversor_base)
    if sistema_tipo == "Standalone":
        costo_bess_con_margen = calcular_precio_final(costo_bess_base)
    else:
        costo_bess_con_margen = 0.0

    # PASO 4: Análisis financiero
    fe = FinancialEngineEolico(
        tarifa_kwh_USD=tarifa_kwh_USD,
        costo_instalacion_pct=costo_instalacion_pct,
        vida_util_anos=vida_util_anos,
        tasa_descuento_pct=tasa_descuento_pct,
    )

    analisis_financiero = fe.calcular_punto_unico(
        potencia_pico_W=potencia_pico,
        n_turbinas=n_turbinas,
        energia_anual_kWh=energia_anual_kWh,
        costo_turbinas_USD=costo_turbinas_con_margen,
        costo_inversor_USD=costo_inversor_con_margen,
        costo_bess_USD=costo_bess_con_margen,
        sistema_tipo=sistema_tipo,
    )

    # PASO 5: Indicadores de viabilidad
    costo_por_kw = calcular_precio_kwh_instalado(
        precio_sistema_usd=analisis_financiero["capex"],
        potencia_pico_w=potencia_pico,
    )

    # Ratio de productividad (kWh anuales por kW instalado)
    productividad_kwh_por_kw_ano = energia_anual_kWh / (potencia_pico / 1000)

    # RESULTADO INTEGRADO
    return {
        "resumen_ejecutivo": {
            "sistema_tipo": sistema_tipo,
            "potencia_pico_kw": round(potencia_pico / 1000, 2),
            "cantidad_turbinas": n_turbinas,
            "energia_anual_kwh": round(energia_anual_kWh, 0),
            "consumo_diario_kwh": consumo_diario_kWh,
        },

        "arquitectura_tecnica": arquitectura,

        "costos_sin_margen": {
            "turbinas_usd": round(costo_turbinas_total, 2),
            "inversor_usd": round(costo_inversor_base, 2),
            "bess_usd": round(costo_bess_base, 2) if sistema_tipo == "Standalone" else 0.0,
            "total_equipos_usd": round(
                costo_turbinas_total + costo_inversor_base + (costo_bess_base if sistema_tipo == "Standalone" else 0),
                2,
            ),
        },

        "costos_con_margen_importacion": {
            "turbinas_usd": round(costo_turbinas_con_margen, 2),
            "inversor_usd": round(costo_inversor_con_margen, 2),
            "bess_usd": round(costo_bess_con_margen, 2),
            "total_equipos_usd": round(
                costo_turbinas_con_margen + costo_inversor_con_margen + costo_bess_con_margen,
                2,
            ),
        },

        "analisis_financiero": analisis_financiero,

        "indicadores_viabilidad": {
            "costo_por_kw_instalado_usd": costo_por_kw,
            "productividad_kwh_por_kw_ano": round(productividad_kwh_por_kw_ano, 1),
            "ahorro_anual_usd": round(
                energia_anual_kWh * tarifa_kwh_USD,
                2,
            ),
            "tasa_retorno_anual_pct": round(
                (energia_anual_kWh * tarifa_kwh_USD) / analisis_financiero["capex"] * 100, 2
            ) if analisis_financiero["capex"] > 0 else None,
            "viabilidad_economica": (
                "VIABLE" if analisis_financiero["roi_percentage"] and analisis_financiero["roi_percentage"] > 0
                else "NO VIABLE"
            ),
        },

        "recomendaciones": _generar_recomendaciones(
            analisis_financiero,
            potencia_pico,
            energia_anual_kWh,
            tarifa_kwh_USD,
            sistema_tipo,
        ),
    }


def _generar_recomendaciones(
    analisis: Dict,
    potencia_pico_w: int,
    energia_anual_kwh: float,
    tarifa_kwh_usd: float,
    sistema_tipo: str,
) -> List[str]:
    """Genera recomendaciones basadas en análisis financiero."""
    recomendaciones = []

    if sistema_tipo == "Standalone":
        recomendaciones.append(
            f"Sistema Standalone: Requiere banco de baterías para autonomía. "
            f"Capacidad dimensionada para 12 horas de respaldo."
        )
    else:
        recomendaciones.append(
            f"Sistema Hybrid: Integración con paneles solares existentes. "
            f"No requiere BESS pero puede beneficiarse de ella."
        )

    # Payback
    if analisis["payback_years"] is not None:
        if analisis["payback_years"] < 10:
            recomendaciones.append(
                f"✓ Payback atractivo: {analisis['payback_years']} años. "
                f"Inversión se recupera en {int(analisis['payback_years'])} años."
            )
        elif analisis["payback_years"] < 20:
            recomendaciones.append(
                f"⚠ Payback moderado: {analisis['payback_years']} años. "
                f"Considera reducir costo de instalación o aumentar generación."
            )
        else:
            recomendaciones.append(
                f"✗ Payback muy largo: {analisis['payback_years']} años. "
                f"Proyecto no es económicamente viable con parámetros actuales."
            )

    # ROI
    if analisis["roi_percentage"] is not None:
        if analisis["roi_percentage"] > 100:
            recomendaciones.append(
                f"✓ ROI excelente: {analisis['roi_percentage']:.1f}% en 40 años. "
                f"Proyecto altamente rentable."
            )
        elif analisis["roi_percentage"] > 0:
            recomendaciones.append(
                f"✓ ROI positivo: {analisis['roi_percentage']:.1f}% en 40 años. "
                f"Proyecto viable económicamente."
            )
        else:
            recomendaciones.append(
                f"✗ ROI negativo: {analisis['roi_percentage']:.1f}%. "
                f"Proyecto no es rentable."
            )

    # NPV
    if analisis["npv_usd"] is not None:
        if analisis["npv_usd"] > 0:
            recomendaciones.append(
                f"✓ NPV positivo: ${analisis['npv_usd']:,.0f} USD. "
                f"Proyecto crea valor económico."
            )
        else:
            recomendaciones.append(
                f"✗ NPV negativo: ${analisis['npv_usd']:,.0f} USD. "
                f"Considera aumentar tarifa proyectada o reducir costos."
            )

    # Productividad
    productividad = energia_anual_kwh / (potencia_pico_w / 1000)
    if productividad > 8000:
        recomendaciones.append(
            f"✓ Productividad excelente: {productividad:.0f} kWh/kW/año. "
            f"Ubicación con recursos eólicos muy buenos."
        )
    elif productividad > 4000:
        recomendaciones.append(
            f"✓ Productividad buena: {productividad:.0f} kWh/kW/año. "
            f"Ubicación con recursos eólicos moderados a buenos."
        )
    else:
        recomendaciones.append(
            f"⚠ Productividad baja: {productividad:.0f} kWh/kW/año. "
            f"Considerar aumentar número de turbinas o mejorar altura."
        )

    return recomendaciones


if __name__ == "__main__":
    # Ejemplo de uso -- claves canónicas (turbine_specs.py::SPECS_TURBINAS), no
    # nombres completos de modelo
    turbinas = ["small_tulip", "small_tulip", "medium_tulip", "medium_tulip"]

    resultado = analizar_sistema_eolico_completo(
        turbinas_seleccionadas=turbinas,
        consumo_diario_kWh=30,
        energia_anual_kWh=30000,
        horas_autonomia=12,
        tarifa_kwh_USD=0.15,
        sistema_tipo="Hybrid",
    )

    import json
    print(json.dumps(resultado, indent=2, default=str))
