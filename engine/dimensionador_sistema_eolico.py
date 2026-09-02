"""
Dimensionador de Sistema Eólico Híbrido Flower Turbines + Sol-Ark

Flujo de diseño:
1. Usuario selecciona turbinas Flower Turbines (claves canónicas de la app, mismas
   que usa el resto de ECO-Wind -- ver engine/turbine_specs.py::SPECS_TURBINAS)
2. App calcula potencia pico del arreglo (la energía anual real, hora por hora,
   sigue viniendo de simular() -- ver más abajo, "DE DÓNDE SALE LA ENERGÍA REAL")
3. Controladores individuales (uno por turbina) se conectan en PARALELO → bus 48V DC
4. Función dimensiona Inversor Sol-Ark + BESS apropiados
5. Retorna arquitectura completa: voltajes, corrientes, compatibilidades, CAPEX

DE DÓNDE SALE LA ENERGÍA REAL (Hallazgo 41): este módulo NO recalcula kWh/año -- por
decisión explícita, la pestaña de Análisis Financiero debe leer el kWh/año que ya
calcula `simular()` (motor horario validado, Hallazgo 12/20) sobre los clústers reales
de `st.session_state.clusters`, no un número aparte basado en potencia nominal. Este
módulo sólo resuelve CAPEX de equipos (turbinas + inversor + BESS), no energía.

REGLA ELÉCTRICA CONFIRMADA CON AMBOS FABRICANTES (Hallazgo 40, no es una suposición
nuestra): el controlador de cada turbina entrega 48V CC regulados, que se conecta
SIEMPRE al bus/banco de baterías del inversor (nunca al puerto solar/MPPT -- el MPPT
no arranca por debajo de ~125-200V y further, el algoritmo de rastreo fotovoltaico no
tiene sentido con una fuente de tensión fija). Sólo la línea residencial de Sol-Ark
(hasta el 18K, 48V nominal) es compatible en DC directo -- el 30K/60K son de alta
tensión (160-800V) y necesitan convertidor DC-DC o acople en CA, ninguno de los dos
con precio propio confiable todavía (ver PAQUETES_INDUSTRIALES_AL13 más abajo para la
única excepción con precio cerrado real).

BESS de 48V: Sol-Ark confirmó que NO fabrica batería de litio propia para su línea
residencial (su único producto de batería, Serie L3, es exclusivamente de alta
tensión, ver solark_specs.py) -- el BESS de 48V sale de un tercero, hoy modelado con
EG4 (`eg4_specs.py`, precio retail, no de fábrica -- ver su docstring).
"""

import pandas as pd
from typing import List, Dict, Optional

from engine.turbine_specs import SPECS_TURBINAS
from engine.solark_specs import get_solark_inversores_df
from engine.eg4_specs import get_eg4_df
from engine.price_calculator import calcular_precio_venta_proyecto, MODO_IMPORTACION_DEFAULT

VOLTAJE_TURBINAS_V = 48  # fijo -- así lo entregan los controladores de fábrica, no es una opción de diseño

# Paquetes industriales AL13 Power Tower "todo incluido" (turbinas + BESS + inversor
# On-Grid) que Flower Turbines vende como oferta cerrada de fábrica -- la única forma
# de tener un CAPEX cerrado y confiable para arreglos que necesitarían un Sol-Ark
# 30K/60K (alta tensión), sin tener que cotizar un convertidor DC-DC o un acople en CA
# por separado.
#
# ADVERTENCIA DE FUENTE, no ocultarla: estos dos precios NO vienen de un datasheet ni
# de una cotización de fábrica verificada como las de Sol-Ark (Hallazgo 40) -- vienen
# de una respuesta de chat estilo "representante de Flower Turbines", mismo patrón que
# ya se marcó como no verificable de forma independiente. Usar como estimado de
# trabajo, no como precio para cotizar a un cliente real sin antes confirmarlo con una
# lista de precios oficial.
PAQUETES_INDUSTRIALES_AL13 = {
    "al13_6m_30kw": {
        "descripcion": "6x AL13 Power Tower (6 módulos c/u) On-Grid, ~30kW pico -- "
                        "inversor Sol-Ark 30K y BESS de alta tensión incluidos de fábrica",
        "modelo_turbina": "al13_6m",
        "cantidad_turbinas": 6,
        "potencia_pico_total_W": 30000,
        "precio_paquete_usd": 126100.00,
        "fuente": "respuesta de chat estilo Flower Turbines -- NO verificada contra datasheet/cotización real",
    },
    "al13_8m_60kw": {
        "descripcion": "6x AL13 Power Tower (8 módulos c/u) On-Grid, ~60kW pico -- "
                        "inversor Sol-Ark 60K y BESS de alta tensión incluidos de fábrica",
        "modelo_turbina": "al13_8m",
        "cantidad_turbinas": 6,
        "potencia_pico_total_W": 60000,
        "precio_paquete_usd": 188500.00,
        "fuente": "respuesta de chat estilo Flower Turbines -- NO verificada contra datasheet/cotización real",
    },
}


def calcular_costo_arreglo_turbinas(turbinas_seleccionadas: List[str]) -> Dict:
    """
    Costo de fábrica y potencia pico del arreglo de turbinas -- claves canónicas de
    la app (`small_tulip`, `al13_2m`, etc., ver SPECS_TURBINAS), no nombres completos.

    Sólo 4 de las 11 turbinas tienen costo de fábrica real hoy (small_tulip,
    medium_tulip, three_m_tulip, al13_2m) -- `costo_usd` viene en None para las demás,
    y se refleja en `costo_total_usd=None` si CUALQUIER turbina seleccionada no tiene
    precio, en vez de sumar como si fuera cero (eso escondería el hueco de dato).
    """
    turbinas_data = []
    potencia_pico_total_W = 0
    costos = []
    falta_costo = []

    for clave in turbinas_seleccionadas:
        if clave not in SPECS_TURBINAS:
            raise ValueError(f"Modelo de turbina '{clave}' no existe en SPECS_TURBINAS. "
                              f"Claves válidas: {sorted(SPECS_TURBINAS)}")
        specs = SPECS_TURBINAS[clave]
        potencia_pico_total_W += specs["potencia_nominal_w"]
        turbinas_data.append({"clave": clave, **specs})
        if specs.get("costo_usd") is not None:
            costos.append(specs["costo_usd"])
        else:
            falta_costo.append(clave)

    return {
        "potencia_pico_W": potencia_pico_total_W,
        "cantidad_turbinas": len(turbinas_seleccionadas),
        "turbinas_detalles": pd.DataFrame(turbinas_data),
        "voltaje_sistema_V": VOLTAJE_TURBINAS_V,
        "costos_individuales_usd": costos,
        "costo_total_usd": sum(costos) if not falta_costo else None,
        "turbinas_sin_costo": falta_costo,
    }


def calcular_corriente_total_dc(potencia_pico_W, voltaje_dc_V=VOLTAJE_TURBINAS_V) -> float:
    """I = P / V -- corriente DC total que entrega el arreglo de turbinas al bus."""
    return potencia_pico_W / voltaje_dc_V


def seleccionar_inversor_solark(potencia_pico_W, voltaje_sistema_V=VOLTAJE_TURBINAS_V) -> Dict:
    """
    Selecciona el inversor Sol-Ark compatible en DC DIRECTO con el bus de turbinas.

    CORREGIDO (Hallazgo 41 -- bug real de Hallazgo 40): la versión anterior usaba
    `Potencia_FV_Max_W` (capacidad del puerto SOLAR/MPPT) como límite, y un chequeo
    `if voltaje_sistema_V == 48` que era siempre verdadero (nunca comparaba de
    verdad el voltaje del inversor candidato) -- confirmado con ambos fabricantes
    que las turbinas van al puerto de BATERÍA, no al solar, así que el límite real es
    la potencia máxima de carga de batería (`Corriente_Carga_Descarga_Max_A` x
    `Voltaje_Nominal_CC_V`), y el filtro de voltaje debe comparar contra el voltaje
    NOMINAL DE BATERÍA real de cada inversor, no asumir que todos son 48V.

    De la línea Sol-Ark documentada (18K/30K/60K), sólo el 18K es 48V nominal -- 30K
    y 60K son de alta tensión (300V/600V) y NO son compatibles en DC directo sin un
    convertidor DC-DC o un acople en CA (ninguno de los dos con precio propio
    confiable hoy, ver PAQUETES_INDUSTRIALES_AL13 para la única excepción con precio
    cerrado real).

    Devuelve `compatible=False` (no lanza excepción) si no hay inversor de la línea
    residencial que alcance -- así el resto del CAPEX se puede seguir calculando en
    vez de frenar todo el cálculo (turbinas + BESS siguen siendo valores reales).
    """
    df_inversores = get_solark_inversores_df()
    candidatos = df_inversores[df_inversores["Voltaje_Nominal_CC_V"] == voltaje_sistema_V].copy()
    candidatos["capacidad_bateria_max_W"] = (
        candidatos["Corriente_Carga_Descarga_Max_A"] * candidatos["Voltaje_Nominal_CC_V"]
    )
    candidatos = candidatos[candidatos["capacidad_bateria_max_W"] >= potencia_pico_W]

    if candidatos.empty:
        return {
            "compatible": False,
            "razon": (
                f"Ningún inversor Sol-Ark de {voltaje_sistema_V}V nominal (línea residencial: "
                f"9K/12K/12K-LL/15K/18K) tiene capacidad de carga de batería suficiente para "
                f"{potencia_pico_W}W pico. Requiere convertidor DC-DC, acople en "
                f"CA, o revisar si el arreglo calza con un PAQUETE_INDUSTRIAL_AL13 (precio cerrado)."
            ),
        }

    # El más chico que alcanza -- no sobredimensionar de más si hay una opción más ajustada
    fila = candidatos.sort_values("capacidad_bateria_max_W").iloc[0]
    specs_verificadas = bool(fila.get("Specs_Verificadas", True))
    razon = (f"Arreglo {potencia_pico_W}W cabe en capacidad de carga de batería del "
             f"{fila['Modelo']} ({fila['capacidad_bateria_max_W']:.0f}W)")
    if not specs_verificadas:
        razon += (" -- OJO: este modelo todavía no tiene datasheet oficial verificado "
                   "(Hallazgo 43), la corriente de carga de batería usada acá es una "
                   "estimación, no un dato confirmado por Sol-Ark.")
    return {
        "compatible": True,
        "modelo": fila["Modelo"],
        "potencia_ca_salida_W": fila["Potencia_Salida_CA_Continua_W"],
        "costo_USD": fila["Costo_USD"],
        "voltaje_entrada_dc_V": fila["Voltaje_Nominal_CC_V"],
        "voltaje_salida_ca_V": fila["Voltaje_Salida_CA"],
        "capacidad_bateria_max_W": float(fila["capacidad_bateria_max_W"]),
        "factor_sobredimensionamiento": float(fila["capacidad_bateria_max_W"] / potencia_pico_W),
        "specs_verificadas": specs_verificadas,
        "razon": razon,
    }


def dimensionar_bess(consumo_diario_kWh: float, horas_autonomia: int = 12,
                      margen_ineficiencia: float = 0.15) -> Dict:
    """
    Capacidad de BESS requerida por autonomía -- sin cambios de fórmula (Hallazgo 40
    no encontró ningún problema acá, sólo en la SELECCIÓN del producto).

    Energía_almacenamiento = (consumo_diario_kWh x horas_autonomia / 24) x (1 + margen_ineficiencia)
    """
    energia_requerida = (consumo_diario_kWh * horas_autonomia) / 24
    capacidad_nominal = energia_requerida * (1 + margen_ineficiencia)
    return {
        "consumo_diario_kWh": consumo_diario_kWh,
        "horas_autonomia": horas_autonomia,
        "energia_requerida_kWh": energia_requerida,
        "margen_ineficiencia_pct": margen_ineficiencia * 100,
        "capacidad_nominal_kWh": capacidad_nominal,
    }


def seleccionar_bess_48v(capacidad_requerida_kWh: float) -> Dict:
    """
    Selecciona módulos EG4 (tercero, NO Sol-Ark -- ver eg4_specs.py) hasta cubrir la
    capacidad requerida, con la unidad de mayor capacidad primero (menos módulos,
    mejor costo por kWh que apilar sólo el módulo chico).

    Reemplaza a la vieja `seleccionar_bess_solark()`: esa función buscaba en el
    catálogo de Sol-Ark (Serie L3), que es 100% alta tensión -- ningún producto ahí
    es compatible con 48V (Hallazgo 40). El filtro viejo tenía además un bug real: el
    OR con `Ubicacion_Instalacion.isin(['Interior','Exterior'])` es cierto para las 3
    baterías de la Serie L3 sin importar el voltaje, así que en la práctica no
    filtraba nada -- podía "seleccionar" un banco de 410-614V para un bus de 48V.
    """
    df_eg4 = get_eg4_df()
    seleccionados = []
    capacidad_acumulada = 0.0

    for _, fila in df_eg4.sort_values("Capacidad_kWh", ascending=False).iterrows():
        if capacidad_acumulada >= capacidad_requerida_kWh:
            break
        seleccionados.append({
            "modelo": fila["Modelo"],
            "fabricante": fila["Fabricante"],
            "capacidad_kWh": fila["Capacidad_kWh"],
            "voltaje_V": fila["Voltaje_Nominal_CC_V"],
            "costo_USD": fila["Costo_USD"],
        })
        capacidad_acumulada += fila["Capacidad_kWh"]

    if not seleccionados:
        raise ValueError(f"No hay módulo EG4 disponible para capacidad requerida {capacidad_requerida_kWh}kWh")

    return {
        "bess_seleccionados": seleccionados,
        "capacidad_total_kWh": capacidad_acumulada,
        "cantidad_modulos": len(seleccionados),
        "costo_total_USD": sum(b["costo_USD"] for b in seleccionados),
        "voltaje_sistema_V": VOLTAJE_TURBINAS_V,
        "fuente": "EG4 (tercero, precio retail -- ver eg4_specs.py, no cotización de fábrica)",
    }


def dimensionar_sistema_eolico_completo(
    turbinas_seleccionadas: List[str],
    consumo_diario_kWh: float,
    horas_autonomia: int = 12,
    energia_anual_kWh: Optional[float] = None,
    modo_importacion: str = MODO_IMPORTACION_DEFAULT,
) -> Dict:
    """
    FUNCIÓN PRINCIPAL: dimensiona CAPEX de equipos (turbinas + inversor + BESS) --
    NO la energía anual, ver docstring del módulo. `turbinas_seleccionadas` usa las
    claves canónicas de la app (small_tulip, medium_tulip, three_m_tulip, al13_2m,
    etc. -- ver SPECS_TURBINAS).

    Si el arreglo NO cabe en la línea residencial Sol-Ark (48V, hoy sólo el 18K con
    datos completos), la función NO frena todo el cálculo (Hallazgo 41: "no dejemos
    de calcular") -- devuelve el costo de turbinas igual, marca
    `inversor_seleccionado.compatible=False`, y agrega una nota explícita pendiente
    de resolver con ingeniería de acople aparte (o con un PAQUETE_INDUSTRIAL_AL13 si
    el arreglo calza con uno de los dos paquetes de fábrica).

    modo_importacion: "por_sku" (default) aplica un fee de importación a CADA
    componente (cada turbina, el inversor, cada módulo de BESS); "por_proyecto"
    aplica un solo fee a todo el embarque. Ver price_calculator.py -- pregunta
    todavía sin resolver con un dato real de flete/aduana consolidado, se deja como
    parámetro explícito para poder recalcular sin tocar esta función.
    """
    arreglo = calcular_costo_arreglo_turbinas(turbinas_seleccionadas)
    corriente_dc_total = calcular_corriente_total_dc(arreglo["potencia_pico_W"], arreglo["voltaje_sistema_V"])
    inversor = seleccionar_inversor_solark(arreglo["potencia_pico_W"], arreglo["voltaje_sistema_V"])

    resultado = {
        "arquitectura_general": {
            "tipo_sistema": "Sistema Eólico Híbrido (Off-Grid / Backup)",
            "voltaje_dc_sistema_V": arreglo["voltaje_sistema_V"],
            "topologia_generacion": "Turbinas eólicas (AC) → Controladores individuales (DC) → Bus 48V paralelo",
        },
        "arreglo_turbinas": {
            "cantidad": arreglo["cantidad_turbinas"],
            "modelos": turbinas_seleccionadas,
            "potencia_pico_total_W": arreglo["potencia_pico_W"],
            "energia_anual_kWh": energia_anual_kWh,
            "corriente_total_dc_A": round(corriente_dc_total, 2),
            "costo_total_usd": arreglo["costo_total_usd"],
            "turbinas_sin_costo": arreglo["turbinas_sin_costo"],
        },
        "inversor_seleccionado": inversor,
    }

    if not inversor["compatible"]:
        paquete_match = next(
            (p for p in PAQUETES_INDUSTRIALES_AL13.values()
             if p["modelo_turbina"] in turbinas_seleccionadas
             and turbinas_seleccionadas.count(p["modelo_turbina"]) >= p["cantidad_turbinas"]),
            None,
        )
        resultado["pendiente_ingenieria_acople"] = True
        if paquete_match:
            resultado["paquete_industrial_sugerido"] = paquete_match
            resultado["nota_pendiente"] = (
                "El arreglo calza con un paquete industrial AL13 de fábrica (precio cerrado, "
                "ver 'paquete_industrial_sugerido') -- pero ese precio NO está verificado contra "
                "un datasheet/cotización real, sólo contra una respuesta de chat (Hallazgo 41)."
            )
        else:
            resultado["nota_pendiente"] = (
                "Este arreglo supera la línea residencial de Sol-Ark en DC directo (48V). "
                "Requiere convertidor DC-DC elevador o acople en CA hacia un inversor comercial "
                "(30K/60K) -- ninguno de los dos tiene precio propio confiable todavía. CAPEX de "
                "turbinas sí calculado; inversor y BESS quedan pendientes de ingeniería aparte."
            )
        return resultado

    bess_req = dimensionar_bess(consumo_diario_kWh, horas_autonomia)
    bess = seleccionar_bess_48v(bess_req["capacidad_nominal_kWh"])
    resultado["dimensionamiento_bess"] = bess_req
    resultado["bess_seleccionado"] = bess

    if arreglo["turbinas_sin_costo"]:
        resultado["precio_venta_equipos_usd"] = None
        resultado["nota_pendiente"] = (
            "Precio de venta incompleto: falta el costo de fábrica de al menos una turbina "
            f"seleccionada ({arreglo['turbinas_sin_costo']})."
        )
        return resultado

    # Una línea de costo por componente INDIVIDUAL (cada turbina, el inversor, cada
    # módulo de BESS) -- para que modo_importacion="por_sku" aplique el fee a cada
    # pieza real del pedido, no a 3 categorías agregadas (turbinas/inversor/BESS).
    costos_individuales = (
        arreglo["costos_individuales_usd"]
        + [inversor["costo_USD"]]
        + [b["costo_USD"] for b in bess["bess_seleccionados"]]
    )
    precios_por_linea, precio_total = calcular_precio_venta_proyecto(
        costos_individuales, modo_importacion=modo_importacion)
    resultado["modo_importacion"] = modo_importacion
    resultado["precios_por_linea_usd"] = precios_por_linea
    resultado["precio_venta_equipos_usd"] = precio_total
    return resultado


if __name__ == "__main__":
    import json

    print("=" * 90)
    print("Caso 1 -- arreglo chico, cabe en el 18K residencial (48V, DC directo)")
    print("=" * 90)
    resultado = dimensionar_sistema_eolico_completo(
        turbinas_seleccionadas=["small_tulip", "medium_tulip", "three_m_tulip"],
        consumo_diario_kWh=15,
        horas_autonomia=12,
    )
    print(json.dumps(resultado, indent=2, default=str, ensure_ascii=False))

    print()
    print("=" * 90)
    print("Caso 2 -- arreglo de 6x AL13 6-módulos (~30kW): supera el 18K, calza con el")
    print("paquete industrial de fábrica -- no se frena el cálculo, queda la nota.")
    print("=" * 90)
    resultado2 = dimensionar_sistema_eolico_completo(
        turbinas_seleccionadas=["al13_6m"] * 6,
        consumo_diario_kWh=100,
        horas_autonomia=12,
    )
    print(json.dumps(resultado2, indent=2, default=str, ensure_ascii=False))

    print()
    print("=" * 90)
    print("Caso 1, comparando modo_importacion 'por_sku' vs 'por_proyecto'")
    print("=" * 90)
    r_sku = dimensionar_sistema_eolico_completo(
        turbinas_seleccionadas=["small_tulip", "medium_tulip", "three_m_tulip"],
        consumo_diario_kWh=15, horas_autonomia=12, modo_importacion="por_sku")
    r_proy = dimensionar_sistema_eolico_completo(
        turbinas_seleccionadas=["small_tulip", "medium_tulip", "three_m_tulip"],
        consumo_diario_kWh=15, horas_autonomia=12, modo_importacion="por_proyecto")
    print(f"  por_sku      -> precio_venta_equipos_usd = ${r_sku['precio_venta_equipos_usd']:,.2f}")
    print(f"  por_proyecto -> precio_venta_equipos_usd = ${r_proy['precio_venta_equipos_usd']:,.2f}")
    print(f"  Diferencia: ${r_sku['precio_venta_equipos_usd'] - r_proy['precio_venta_equipos_usd']:,.2f}")
