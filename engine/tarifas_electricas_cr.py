"""
Tarifas eléctricas reales de Costa Rica (CNFL / ICE) -- Hallazgo 54.

Reemplaza la tarifa plana ($/kWh) que usaba "Análisis Financiero" como única opción
por las tarifas REALES publicadas por los dos distribuidores que cubren la mayoría
del país (CNFL en el Gran Área Metropolitana, ICE en el resto), para que el ahorro
de un sistema eólico se calcule contra lo que el cliente de verdad paga -- incluyendo
tarifas HORARIAS (Punta/Valle/Nocturno), donde el valor de un kWh generado depende de
A QUÉ HORA DEL DÍA lo genera la turbina, no sólo de cuántos kWh/año produce.

Todos los valores de esta tabla fueron dados por Pablo/ECO Consultor (fuente: pliegos
tarifarios de CNFL/ICE que él consultó) -- ver Hallazgo 54 en avance-de-proyecto.md
para el resultado de la verificación cruzada contra las fuentes oficiales de ARESEP.
Las tarifas de Costa Rica se revisan trimestral (ajuste por combustible) o
semestralmente (ajuste ordinario) -- estos números se vencen, no son una constante de
ingeniería. Antes de cotizar en firme a un cliente, confirmar contra el pliego
tarifario vigente en www.aresep.go.cr / www.grupoice.com / www.cnfl.go.cr.

CÓMO SE USAN LOS 4 GRUPOS DE TARIFA (honesto sobre lo que SÍ y lo que NO calcula la app):

1. TARIFAS_HORARIAS_CR (T-REH CNFL, T-RH ICE) y TARIFAS_MT_GD_CR["T-MT"] (ICE, media
   tensión) -- SÍ están conectadas al cálculo de ahorro real: tienen periodos Punta/
   Valle/Nocturno definidos por hora del día (ver PERIODOS_HORARIOS_CR), así que se
   pueden cruzar directo contra la serie horaria de producción de la turbina
   (`simular()["serie_horaria_W_por_turbina"]`) para saber cuántos kWh se generan en
   cada periodo y a qué precio -- exactamente lo que pidió Pablo ("planifica los
   horarios de las tarifas con los potenciales de producción... según el análisis de
   potencia horaria"). Ver `calcular_ahorro_tarifa_horaria_usd()`.

2. TARIFAS_ESCALONADAS_CR (T-RE, CNFL/ICE) -- guardada como dato de referencia, NO
   conectada todavía a ningún cálculo de ahorro. Es una tarifa por BLOQUE de consumo
   mensual (no por hora del día), y no se pudo confirmar con la fuente oficial si el
   cargo fijo/tarifa de cada bloque se cobra de forma progresiva (como un bracket de
   impuesto: cada bloque paga su propia tarifa sólo por los kWh dentro de ese rango) o
   como categoría (todo el consumo del mes se cobra a la tarifa del bloque más alto
   alcanzado) -- calcular un "ahorro" con el mecanismo equivocado daría un número
   confiado pero incorrecto, así que se deja pendiente en vez de adivinar cuál es
   (Hallazgo 54).

3. TARIFAS_MT_GD_CR["T-TCVE"] (excedentes de generación distribuida) y ["T-A"] (tarifa
   de acceso) -- guardadas como referencia, NO conectadas. T-TCVE es lo que ICE paga
   por la energía EXCEDENTE que un generador distribuido (ej. este mismo sistema
   eólico) inyecta a la red cuando genera más de lo que el sitio consume en ese
   instante -- para calcularla de verdad se necesita un perfil de CONSUMO horario del
   sitio (no sólo un kWh/día promedio, que es todo lo que la app pide hoy) para saber
   en qué horas hay excedente real. Queda como trabajo futuro explícito.

4. TARIFAS_COMERCIALES_CR (T-CO, gimnasios/estadios/comercios) -- guardada como
   referencia, NO conectada. Tiene cargos por DEMANDA MÁXIMA (kW, no kWh) que
   requieren saber en qué instante ocurre el pico de demanda del sitio y si la
   turbina está generando en ese momento (reducción de demanda pico) -- un cálculo
   distinto al de "ahorro de energía" que ya hace el resto de la app, no modelado
   todavía.
"""

import math
from typing import Dict, List, Optional

import numpy as np
import pandas as pd


# ---------------------------------------------------------------------------
# 1. TARIFAS HORARIAS RESIDENCIALES (T-REH CNFL / T-RH ICE) -- SÍ conectadas
# ---------------------------------------------------------------------------
TARIFAS_HORARIAS_CR = [
    {"Proveedor": "CNFL", "Tarifa": "T-REH (0-500 kWh)", "Periodo": "Punta", "Costo_Energia_CRC_kWh": 134.62},
    {"Proveedor": "CNFL", "Tarifa": "T-REH (0-500 kWh)", "Periodo": "Valle", "Costo_Energia_CRC_kWh": 55.19},
    {"Proveedor": "CNFL", "Tarifa": "T-REH (0-500 kWh)", "Periodo": "Nocturno", "Costo_Energia_CRC_kWh": 23.10},
    {"Proveedor": "CNFL", "Tarifa": "T-REH (>500 kWh)", "Periodo": "Punta", "Costo_Energia_CRC_kWh": 166.46},
    {"Proveedor": "CNFL", "Tarifa": "T-REH (>500 kWh)", "Periodo": "Valle", "Costo_Energia_CRC_kWh": 67.17},
    {"Proveedor": "CNFL", "Tarifa": "T-REH (>500 kWh)", "Periodo": "Nocturno", "Costo_Energia_CRC_kWh": 31.09},
    {"Proveedor": "ICE", "Tarifa": "T-RH", "Periodo": "Punta", "Costo_Energia_CRC_kWh": 129.80},
    {"Proveedor": "ICE", "Tarifa": "T-RH", "Periodo": "Valle", "Costo_Energia_CRC_kWh": 89.19},
    {"Proveedor": "ICE", "Tarifa": "T-RH", "Periodo": "Nocturno", "Costo_Energia_CRC_kWh": 65.07},
]


# ---------------------------------------------------------------------------
# 2. TARIFAS ESCALONADAS RESIDENCIALES (T-RE) -- referencia, NO conectada (ver docstring)
# ---------------------------------------------------------------------------
TARIFAS_ESCALONADAS_CR = [
    {"Proveedor": "CNFL", "Bloque_Consumo_kWh": "0 - 30", "Cargo_Fijo_CRC": 1744.80, "Costo_Energia_CRC_kWh": 0.0},
    {"Proveedor": "CNFL", "Bloque_Consumo_kWh": "31 - 200", "Cargo_Fijo_CRC": 0.0, "Costo_Energia_CRC_kWh": 58.16},
    {"Proveedor": "CNFL", "Bloque_Consumo_kWh": "201 - 300", "Cargo_Fijo_CRC": 0.0, "Costo_Energia_CRC_kWh": 89.24},
    {"Proveedor": "CNFL", "Bloque_Consumo_kWh": "> 300", "Cargo_Fijo_CRC": 0.0, "Costo_Energia_CRC_kWh": 92.27},
    {"Proveedor": "ICE", "Bloque_Consumo_kWh": "0 - 140", "Cargo_Fijo_CRC": 1147.43, "Costo_Energia_CRC_kWh": 56.14},
    {"Proveedor": "ICE", "Bloque_Consumo_kWh": "141 - 195", "Cargo_Fijo_CRC": 2163.73, "Costo_Energia_CRC_kWh": 63.47},
    {"Proveedor": "ICE", "Bloque_Consumo_kWh": "196 - 250", "Cargo_Fijo_CRC": 3208.13, "Costo_Energia_CRC_kWh": 73.79},
    {"Proveedor": "ICE", "Bloque_Consumo_kWh": "251 - 370", "Cargo_Fijo_CRC": 3943.42, "Costo_Energia_CRC_kWh": 85.78},
    {"Proveedor": "ICE", "Bloque_Consumo_kWh": "> 371", "Cargo_Fijo_CRC": 7924.29, "Costo_Energia_CRC_kWh": 99.70},
]


# ---------------------------------------------------------------------------
# 3. MEDIA TENSIÓN Y EXCEDENTES DE GENERACIÓN DISTRIBUIDA (ICE)
#    T-MT SÍ conectada (tiene periodos horarios); T-TCVE/T-A de referencia.
# ---------------------------------------------------------------------------
TARIFAS_MT_GD_CR = [
    {"Tarifa": "T-MT (Media Tensión Max)", "Periodo": "Punta", "Costo_Energia_CRC_kWh": 51.82,
     "Cargo_Potencia_Demanda_CRC_kW": 8408.21},
    {"Tarifa": "T-MT (Media Tensión Max)", "Periodo": "Valle", "Costo_Energia_CRC_kWh": 19.25,
     "Cargo_Potencia_Demanda_CRC_kW": 5870.73},
    {"Tarifa": "T-MT (Media Tensión Max)", "Periodo": "Nocturno", "Costo_Energia_CRC_kWh": 11.85,
     "Cargo_Potencia_Demanda_CRC_kW": 3760.33},
    {"Tarifa": "T-TCVE (Excedentes GD)", "Periodo": "Punta", "Costo_Energia_CRC_kWh": 27.40,
     "Cargo_Potencia_Demanda_CRC_kW": 0.0},
    {"Tarifa": "T-TCVE (Excedentes GD)", "Periodo": "Valle", "Costo_Energia_CRC_kWh": 27.40,
     "Cargo_Potencia_Demanda_CRC_kW": 0.0},
    {"Tarifa": "T-TCVE (Excedentes GD)", "Periodo": "Nocturno", "Costo_Energia_CRC_kWh": 19.04,
     "Cargo_Potencia_Demanda_CRC_kW": 0.0},
    {"Tarifa": "T-A (Tarifa Acceso)", "Periodo": "Plano", "Costo_Energia_CRC_kWh": 25.00,
     "Cargo_Potencia_Demanda_CRC_kW": 0.0},
]


# ---------------------------------------------------------------------------
# 4. TARIFA COMERCIO Y SERVICIOS (T-CO) -- referencia, NO conectada (ver docstring)
# ---------------------------------------------------------------------------
TARIFAS_COMERCIALES_CR = [
    {"Proveedor": "CNFL", "Subcategoria_Consumo": "<= 3000 kWh (Sin medidor de potencia)",
     "Costo_Energia_CRC_kWh": 98.28, "Cargo_Fijo_Energia_CRC": 0.0,
     "Cargo_Potencia_Demanda_CRC_kW": 0.0, "Cargo_Fijo_Potencia_CRC": 0.0},
    {"Proveedor": "CNFL", "Subcategoria_Consumo": "> 3000 kWh (Bloque base 0-3000 kWh)",
     "Costo_Energia_CRC_kWh": 0.0, "Cargo_Fijo_Energia_CRC": 177540.0,
     "Cargo_Potencia_Demanda_CRC_kW": 9862.06, "Cargo_Fijo_Potencia_CRC": 78896.48},
    {"Proveedor": "CNFL", "Subcategoria_Consumo": "> 3000 kWh (Exceso sobre 3000 kWh)",
     "Costo_Energia_CRC_kWh": 59.18, "Cargo_Fijo_Energia_CRC": 0.0,
     "Cargo_Potencia_Demanda_CRC_kW": 0.0, "Cargo_Fijo_Potencia_CRC": 0.0},
    {"Proveedor": "ICE", "Subcategoria_Consumo": "<= 3000 kWh (Sin medidor de potencia)",
     "Costo_Energia_CRC_kWh": 99.70, "Cargo_Fijo_Energia_CRC": 0.0,
     "Cargo_Potencia_Demanda_CRC_kW": 0.0, "Cargo_Fijo_Potencia_CRC": 0.0},
    {"Proveedor": "ICE", "Subcategoria_Consumo": "> 3000 kWh (Abonado con potencia)",
     "Costo_Energia_CRC_kWh": 59.67, "Cargo_Fijo_Energia_CRC": 0.0,
     "Cargo_Potencia_Demanda_CRC_kW": 9861.68, "Cargo_Fijo_Potencia_CRC": 0.0},
]


def get_tarifas_horarias_df() -> pd.DataFrame:
    return pd.DataFrame(TARIFAS_HORARIAS_CR)


def get_tarifas_escalonadas_df() -> pd.DataFrame:
    return pd.DataFrame(TARIFAS_ESCALONADAS_CR)


def get_tarifas_mt_gd_df() -> pd.DataFrame:
    return pd.DataFrame(TARIFAS_MT_GD_CR)


def get_tarifas_comerciales_df() -> pd.DataFrame:
    return pd.DataFrame(TARIFAS_COMERCIALES_CR)


def tarifas_horarias_disponibles() -> List[str]:
    """Claves 'Proveedor|Tarifa' de las tarifas horarias SÍ conectadas al cálculo
    (T-REH CNFL, T-RH ICE, T-MT ICE) -- para poblar un selector en la UI."""
    claves = [f"{r['Proveedor']}|{r['Tarifa']}" for r in TARIFAS_HORARIAS_CR]
    claves += [f"ICE|{r['Tarifa']}" for r in TARIFAS_MT_GD_CR if r["Tarifa"].startswith("T-MT")]
    vistos = []
    for c in claves:
        if c not in vistos:
            vistos.append(c)
    return vistos


def _tabla_precios_horarios(proveedor: str, tarifa: str) -> Dict[str, float]:
    """{"Punta": crc_kwh, "Valle": crc_kwh, "Nocturno": crc_kwh} para una tarifa horaria dada."""
    filas = [r for r in TARIFAS_HORARIAS_CR if r["Proveedor"] == proveedor and r["Tarifa"] == tarifa]
    if not filas:
        filas = [r for r in TARIFAS_MT_GD_CR if r["Tarifa"] == tarifa]
    if not filas:
        raise ValueError(f"Tarifa horaria no encontrada: proveedor={proveedor!r}, tarifa={tarifa!r}")
    return {r["Periodo"]: r["Costo_Energia_CRC_kWh"] for r in filas}


# ---------------------------------------------------------------------------
# Horarios ARESEP de cada periodo (Punta/Valle/Nocturno) -- CRÍTICO para poder
# cruzar la tarifa horaria contra la producción real hora por hora de la turbina.
#
# Investigado (Hallazgo 54, ver avance-de-proyecto.md para el detalle y las fuentes):
# la definición horaria es IDÉNTICA para T-RH (ICE), T-REH (CNFL) y T-MT (ICE, sólo la
# parte de ENERGÍA -- el cargo por potencia/demanda de T-MT no está modelado, ver
# docstring del módulo):
#   Punta   : 10:00-12:30 y 17:30-20:00, sólo Lunes a Viernes.
#   Valle   : 06:00-10:00 y 12:30-17:30 en L-V; TODO el bloque 06:00-20:00 en fin de
#             semana (las ventanas de Punta entre semana se reclasifican como Valle).
#   Nocturno: 20:00-06:00 (cruza medianoche), TODOS los días por igual.
# Los boletines oficiales escriben los límites como "10:01", "12:31", etc. -- es la
# convención legal de sumar 1 minuto al inicio de cada bloque para no traslaparlo con
# el minuto exacto en que termina el bloque anterior (ej. Punta termina "a las 12:30",
# Valle empieza "a las 12:31"). Para datos HORARIOS (un valor por hora en punto, que es
# toda la resolución que tiene el EPW/GWA de este proyecto) se usa el límite real sin
# el "+1 minuto" (12:30, no 12:31) -- a esa resolución da exactamente la regla de
# mayoría: una hora en punto queda del lado del periodo que ocupa más de esa hora.
#
# NO se pudo verificar esto último contra el PDF primario de ARESEP/ICE/CNFL (bloqueado
# por política de red del entorno de investigación) -- se confirmó por 2 vías de
# búsqueda independientes que SÍ coinciden entre sí en el rango horario, pero no se leyó
# el documento oficial letra por letra. Tampoco se encontró mención de feriados (sólo
# "sábados y domingos") -- se asume aquí que un feriado se trata como fin de semana
# (sin Punta), pendiente de confirmar. Ver Hallazgo 54, sección "Pendiente".
#
# Formato: {(proveedor, tarifa): [{"periodo": ..., "horas": [("HH:MM","HH:MM"), ...],
#                                   "dias": "todos"|"L-V"|"S-D"}, ...]}
# evaluado EN ORDEN -- la primera regla que hace match gana. Un rango puede cruzar
# medianoche (ej. ("20:00","06:00")); clasificar_periodo() lo maneja explícitamente.
# ---------------------------------------------------------------------------
_RULESET_HORARIA_ESTANDAR_CR: List[dict] = [
    {"periodo": "Punta", "horas": [("10:00", "12:30"), ("17:30", "20:00")], "dias": "L-V"},
    {"periodo": "Valle", "horas": [("06:00", "10:00"), ("12:30", "17:30")], "dias": "L-V"},
    {"periodo": "Valle", "horas": [("06:00", "20:00")], "dias": "S-D"},
    {"periodo": "Nocturno", "horas": [("20:00", "06:00")], "dias": "todos"},
]

PERIODOS_HORARIOS_CR: Dict[tuple, List[dict]] = {
    ("CNFL", "T-REH (0-500 kWh)"): _RULESET_HORARIA_ESTANDAR_CR,
    ("CNFL", "T-REH (>500 kWh)"): _RULESET_HORARIA_ESTANDAR_CR,
    ("ICE", "T-RH"): _RULESET_HORARIA_ESTANDAR_CR,
    ("ICE", "T-MT (Media Tensión Max)"): _RULESET_HORARIA_ESTANDAR_CR,
}


def clasificar_periodo(timestamp: pd.Timestamp, proveedor: str, tarifa: str) -> str:
    """
    Devuelve "Punta"/"Valle"/"Nocturno" para una hora concreta (pd.Timestamp), según
    el horario ARESEP de la tarifa dada en PERIODOS_HORARIOS_CR.
    """
    clave = (proveedor, tarifa)
    if clave not in PERIODOS_HORARIOS_CR:
        raise ValueError(
            f"No hay horario ARESEP cargado para proveedor={proveedor!r}, tarifa={tarifa!r} -- "
            f"disponibles: {list(PERIODOS_HORARIOS_CR)}"
        )
    hora = timestamp.hour * 60 + timestamp.minute
    es_finde = timestamp.dayofweek >= 5  # 5=sábado, 6=domingo

    for regla in PERIODOS_HORARIOS_CR[clave]:
        dias = regla["dias"]
        if dias == "L-V" and es_finde:
            continue
        if dias == "S-D" and not es_finde:
            continue
        if regla["horas"] is None:
            return regla["periodo"]
        for hi, hf in regla["horas"]:
            hi_min = int(hi[:2]) * 60 + int(hi[3:])
            hf_min = int(hf[:2]) * 60 + int(hf[3:])
            if hi_min <= hf_min:
                if hi_min <= hora < hf_min:
                    return regla["periodo"]
            else:
                # Rango que cruza medianoche (ej. 20:00-06:00 del día siguiente).
                if hora >= hi_min or hora < hf_min:
                    return regla["periodo"]
    raise RuntimeError(
        f"Ninguna regla de horario hizo match para {timestamp} (proveedor={proveedor}, "
        f"tarifa={tarifa}) -- falta una regla catch-all en PERIODOS_HORARIOS_CR."
    )


def calcular_ahorro_tarifa_horaria_usd(
    serie_horaria_kwh: pd.Series,
    proveedor: str,
    tarifa: str,
    tipo_cambio_crc_por_usd: float,
) -> dict:
    """
    Cruza la serie horaria REAL de producción del proyecto (kWh por hora, indexada
    por datetime -- típicamente `sum(serie_horaria_W_por_turbina * N / 1000)` de cada
    clúster, ver `simular()`) contra el horario ARESEP de periodos de la tarifa dada,
    para valorar cada kWh generado al precio del periodo en el que realmente se
    generó -- no un promedio ni una tarifa plana adivinada.

    Devuelve: ahorro_anual_usd, ahorro_anual_crc, tarifa_efectiva_usd_kwh (promedio
    ponderado por producción real -- útil para comparar contra el modo de tarifa
    plana), y el desglose kWh/CRC/USD por periodo (Punta/Valle/Nocturno).
    """
    if tipo_cambio_crc_por_usd <= 0:
        raise ValueError("El tipo de cambio CRC->USD debe ser positivo.")

    precios = _tabla_precios_horarios(proveedor, tarifa)
    periodos = pd.Series(
        [clasificar_periodo(ts, proveedor, tarifa) for ts in serie_horaria_kwh.index],
        index=serie_horaria_kwh.index,
    )

    desglose = {}
    total_crc = 0.0
    for periodo, precio_crc_kwh in precios.items():
        kwh_periodo = float(serie_horaria_kwh[periodos == periodo].sum())
        crc_periodo = kwh_periodo * precio_crc_kwh
        total_crc += crc_periodo
        desglose[periodo] = {
            "kwh": round(kwh_periodo, 1),
            "precio_crc_kwh": precio_crc_kwh,
            "crc": round(crc_periodo, 2),
            "usd": round(crc_periodo / tipo_cambio_crc_por_usd, 2),
        }

    kwh_total = float(serie_horaria_kwh.sum())
    ahorro_usd = total_crc / tipo_cambio_crc_por_usd

    return {
        "proveedor": proveedor,
        "tarifa": tarifa,
        "tipo_cambio_crc_por_usd": tipo_cambio_crc_por_usd,
        "kwh_total": round(kwh_total, 1),
        "ahorro_anual_crc": round(total_crc, 2),
        "ahorro_anual_usd": round(ahorro_usd, 2),
        "tarifa_efectiva_usd_kwh": round(ahorro_usd / kwh_total, 4) if kwh_total > 0 else 0.0,
        "desglose_por_periodo": desglose,
    }


if __name__ == "__main__":
    idx = pd.date_range("2023-01-01", periods=24, freq="h")
    serie = pd.Series(np.full(24, 10.0), index=idx)  # 10 kWh cada hora, parejo, sólo para probar la mecánica
    print(get_tarifas_horarias_df().to_string(index=False))
