# engine/sistema_eolico_completo.py
# =============================================================================
# Análisis Técnico y Financiero Integrado de Sistemas Eólicos
# Combina dimensionamiento + precios + análisis financiero
# =============================================================================

from typing import Dict, List, Optional
from engine.dimensionador_sistema_eolico import dimensionar_sistema_eolico_completo
from engine.financial_engine_eolico import FinancialEngineEolico
from engine.price_calculator import (
    calcular_precio_venta_proyecto,
    calcular_precio_kwh_instalado,
    IMPORT_COST_USD,
    MARGIN_PCT,
    MODO_IMPORTACION_DEFAULT,
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
    modo_importacion: str = MODO_IMPORTACION_DEFAULT,
    costo_mantenimiento_pct_anual: float = 0.02,
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
        modo_importacion        : "por_sku" (default) o "por_proyecto" -- ver
                                  price_calculator.py. Acá se aplica a nivel de
                                  CATEGORÍA de equipo (turbinas/inversor/BESS como 3
                                  líneas), no por unidad física individual como hace
                                  `dimensionador_sistema_eolico.py::precio_venta_equipos_usd`
                                  -- son dos granularidades distintas del mismo
                                  parámetro, ambas expuestas (ver
                                  `arquitectura_tecnica.precio_venta_equipos_usd` para
                                  la versión por unidad).
        costo_mantenimiento_pct_anual: Mantenimiento anual como % del CAPEX (default
                                  2%) -- antes quedaba fijo en `FinancialEngineEolico`
                                  sin exponerse acá; es el parámetro que más pesa en
                                  si un proyecto sale "VIABLE" o no (Hallazgo 49), así
                                  que se deja ajustable en vez de escondido.

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
        modo_importacion=modo_importacion,
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
    costo_bess_base_efectivo = costo_bess_base if sistema_tipo == "Standalone" else 0.0

    # PASO 3: Aplicar margen y costo de importación -- 2 o 3 líneas (turbinas/inversor,
    # y BESS sólo si el sistema es Standalone) vía la MISMA función que ya resuelve
    # por_sku/por_proyecto en el resto de la app (price_calculator.py).
    #
    # OJO (bug real encontrado con Playwright, Hallazgo 48): en Hybrid, el BESS no
    # existe -- si se pasa como un costo de $0 en la lista, calcular_precio_venta()
    # igual le suma el fee de importación completo a esa línea (cobra "importar algo de
    # $0"), inflando el CAPEX en el valor de un fee fantasma. Se excluye la línea de
    # BESS por completo del cálculo cuando no aplica, en vez de pasarla como cero.
    costos_categorias = [costo_turbinas_total, costo_inversor_base]
    if sistema_tipo == "Standalone":
        costos_categorias.append(costo_bess_base_efectivo)

    precios_por_categoria, _ = calcular_precio_venta_proyecto(
        costos_categorias, modo_importacion=modo_importacion)

    if precios_por_categoria is None:
        # modo "por_proyecto": un solo fee de importación para todo el embarque, sin
        # desglose por línea -- se reparte proporcionalmente al costo base de cada
        # categoría para poder seguir mostrando Turbinas/Inversor/(BESS) por separado
        # sin cambiar el total del proyecto (la suma de las líneas de abajo da
        # exactamente el mismo total que calcular_precio_venta_proyecto ya calculó).
        suma_base = sum(costos_categorias)
        margen_pct = MARGIN_PCT * 100
        if suma_base > 0:
            precios_por_categoria = [
                (c + IMPORT_COST_USD * (c / suma_base)) * (1 + margen_pct / 100)
                for c in costos_categorias
            ]
        else:
            precios_por_categoria = [0.0] * len(costos_categorias)

    if sistema_tipo == "Standalone":
        costo_turbinas_con_margen, costo_inversor_con_margen, costo_bess_con_margen = precios_por_categoria
    else:
        costo_turbinas_con_margen, costo_inversor_con_margen = precios_por_categoria
        costo_bess_con_margen = 0.0

    # PASO 4: Análisis financiero
    fe = FinancialEngineEolico(
        tarifa_kwh_USD=tarifa_kwh_USD,
        costo_instalacion_pct=costo_instalacion_pct,
        costo_mantenimiento_pct_anual=costo_mantenimiento_pct_anual,
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
            "bess_usd": round(costo_bess_base_efectivo, 2),
            "total_equipos_usd": round(
                costo_turbinas_total + costo_inversor_base + costo_bess_base_efectivo, 2
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
            horas_autonomia,
        ),
    }


def _generar_recomendaciones(
    analisis: Dict,
    potencia_pico_w: int,
    energia_anual_kwh: float,
    tarifa_kwh_usd: float,
    sistema_tipo: str,
    horas_autonomia: int = 12,
) -> List[str]:
    """Genera recomendaciones basadas en análisis financiero."""
    recomendaciones = []

    if sistema_tipo == "Standalone":
        recomendaciones.append(
            f"Sistema Standalone: requiere banco de baterías para autonomía. "
            f"Capacidad dimensionada para {horas_autonomia} horas de respaldo."
        )
    else:
        recomendaciones.append(
            "Sistema Hybrid: integración con paneles solares existentes. "
            "No requiere BESS pero puede beneficiarse de ella."
        )

    # Payback
    if analisis["payback_years"] is not None:
        if analisis["payback_years"] < 10:
            recomendaciones.append(
                f"Payback atractivo: {analisis['payback_years']} años. "
                f"Inversión se recupera en {int(analisis['payback_years'])} años."
            )
        elif analisis["payback_years"] < 20:
            recomendaciones.append(
                f"Payback moderado: {analisis['payback_years']} años. "
                f"Considera reducir costo de instalación o aumentar generación."
            )
        else:
            recomendaciones.append(
                f"Payback muy largo: {analisis['payback_years']} años. "
                f"Proyecto no es económicamente viable con parámetros actuales."
            )

    # ROI
    if analisis["roi_percentage"] is not None:
        if analisis["roi_percentage"] > 100:
            recomendaciones.append(
                f"ROI excelente: {analisis['roi_percentage']:.1f}% en la vida útil del proyecto. "
                f"Proyecto altamente rentable."
            )
        elif analisis["roi_percentage"] > 0:
            recomendaciones.append(
                f"ROI positivo: {analisis['roi_percentage']:.1f}% en la vida útil del proyecto. "
                f"Proyecto viable económicamente."
            )
        else:
            recomendaciones.append(
                f"ROI negativo: {analisis['roi_percentage']:.1f}%. Proyecto no es rentable."
            )

    # NPV
    if analisis["npv_usd"] is not None:
        if analisis["npv_usd"] > 0:
            recomendaciones.append(
                f"NPV positivo: ${analisis['npv_usd']:,.0f} USD. Proyecto crea valor económico."
            )
        else:
            recomendaciones.append(
                f"NPV negativo: ${analisis['npv_usd']:,.0f} USD. "
                f"Considera aumentar tarifa proyectada o reducir costos."
            )

    # Productividad -- del SISTEMA COMPLETO (energía anual total / potencia pico total del
    # arreglo), no de una sola turbina; aclarado explícitamente (confusión real de Pablo,
    # Hallazgo 49) porque el texto anterior no lo distinguía.
    productividad = energia_anual_kwh / (potencia_pico_w / 1000)
    if productividad > 8000:
        recomendaciones.append(
            f"Productividad del sistema completo excelente: {productividad:.0f} kWh/kW/año "
            f"(no es de una sola turbina, es el total del arreglo). Ubicación con recursos "
            f"eólicos muy buenos."
        )
    elif productividad > 4000:
        recomendaciones.append(
            f"Productividad del sistema completo buena: {productividad:.0f} kWh/kW/año "
            f"(no es de una sola turbina, es el total del arreglo). Ubicación con recursos "
            f"eólicos moderados a buenos."
        )
    else:
        recomendaciones.append(
            f"Productividad del sistema completo baja: {productividad:.0f} kWh/kW/año "
            f"(no es de una sola turbina, es el total del arreglo). Considerar aumentar "
            f"número de turbinas o mejorar altura de buje."
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
