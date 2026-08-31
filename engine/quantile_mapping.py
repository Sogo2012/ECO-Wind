"""
Quantile mapping (corrección estadística de sesgo por distribución
completa, no sólo la media) -- Alternativa 3, Parte 3b del pedido de
Pablo: probar el MÉTODO hoy mismo, sin esperar acceso a ERA5/Copernicus
CDS (ver Hallazgo 21 para el estado de ese acceso, Parte 3a).

POR QUÉ NASA POWER PARA PROBAR EL MÉTODO, NO ERA5 TODAVÍA: NASA POWER es
exactamente el tipo de fuente que quantile mapping está pensado para
corregir -- gruesa (~50-60km) y con sesgo ya confirmado (Hallazgo 1: en
San José, misma coordenada exacta, media real 4.03 m/s (EPW estación real)
vs NASA POWER real 1.30 m/s -- un factor ~3.1x de subestimación, número
re-verificado en notebooks/pista_a_motor_empirico.ipynb, celda de resumen)
-- y para San José tenemos verdad de terreno (el EPW real) para chequear
si la corrección funciona.

LIMITACIÓN HONESTA (no esconder, Pablo fue explícito sobre esto en otros
hallazgos): no quedó guardada en ningún lado del repo la serie horaria
CRUDA real de NASA POWER de esa corrida -- sólo sobrevive la media (1.30
m/s) y el kWh derivado (16.5) en la celda markdown de resumen del
notebook; la corrida real se hizo en Colab (con internet) y ese resultado
horario no se exportó a un archivo. Por eso esta prueba NO usa datos
horarios reales de NASA POWER -- construye una fuente SINTÉTICA con sesgo
controlado, a partir del EPW real de San José, que imita (no reproduce) el
patrón de sesgo de NASA POWER de dos maneras:
  1. Magnitud: escalada por el factor REAL confirmado (1.30/4.03 = 0.322).
  2. Forma: comprimida hacia la media, para imitar que NASA POWER surge de
     una celda de reanálisis/satélite de ~50-60km que promedia y suaviza
     la variabilidad horaria puntual real -- ESTO es una construcción
     sintética (parámetro elegido, no medido), porque no hay una serie
     horaria real de NASA POWER contra la cual calibrar cuánto comprime
     realmente.

Esta prueba mide la MECÁNICA del método -- ¿corregir percentil a percentil
recupera mejor la forma real (y por lo tanto la producción) que sólo
reescalar la media, cuando el sesgo no es puramente de magnitud? -- no
valida todavía una corrección real de NASA POWER. Eso necesita o bien que
Pablo provea datos crudos de una corrida real de NASA POWER, o correr esto
de nuevo en Colab (con internet real) contra la respuesta real de la API.

Diseño anti-tautológico: el ajuste (fit) de la tabla de mapeo usa sólo la
primera mitad del año (enero-junio); la comparación final se hace en la
segunda mitad (julio-diciembre), que el ajuste NUNCA vio. Si se ajustara y
evaluara en el mismo período, quantile mapping "ganaría" por construcción
(por definición iguala las distribuciones que ve) y la prueba no diría
nada real sobre si el método generaliza.
"""
import os

import numpy as np
import pandas as pd

try:
    from engine.epw_real import cargar_epw_real
    from engine.simulador_pista_a import simular
except ImportError:
    from epw_real import cargar_epw_real
    from simulador_pista_a import simular

_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FACTOR_MAGNITUD_NASA_POWER_SAN_JOSE = 1.30 / 4.03  # Hallazgo 1, real, re-verificado en el notebook


def ajustar_quantile_mapping(fuente_entrenamiento, verdad_entrenamiento, n_cuantiles=100):
    """
    Ajusta la tabla de mapeo cuantil-a-cuantil a partir de un par (fuente
    sesgada, verdad real) del MISMO período (p.ej. mismo semestre, mismo
    sitio). Devuelve (cuantiles_fuente, cuantiles_verdad) -- monótonos
    crecientes, listos para np.interp.
    """
    qs = np.linspace(0, 100, n_cuantiles + 1)
    return np.percentile(fuente_entrenamiento, qs), np.percentile(verdad_entrenamiento, qs)


def aplicar_quantile_mapping(valores, cuantiles_fuente, cuantiles_verdad):
    """
    Aplica una tabla de mapeo YA AJUSTADA a valores nuevos -- típicamente
    datos fuera de muestra (otro período, u otro sitio que comparte la
    misma fuente sesgada) para los que no se conoce la verdad real.
    """
    return np.interp(valores, cuantiles_fuente, cuantiles_verdad)


def _construir_fuente_sintetica_sesgada(ws_real, factor_magnitud, factor_compresion, seed=7):
    """
    Ver docstring del módulo -- construcción SINTÉTICA (no datos reales de
    NASA POWER): comprime la serie real hacia su propia media (imita el
    suavizado de una celda de reanálisis/satélite gruesa) y después
    escala por el factor de magnitud real confirmado (Hallazgo 1).
    `seed` no se usa para aleatoriedad (la transformación es determinista)
    -- queda como parámetro por si a futuro se agrega ruido, no se agrega
    ahora para no inventar una textura de ruido sin base real.
    """
    media = ws_real.mean()
    comprimido = media + (ws_real - media) * (1 - factor_compresion)
    return comprimido * factor_magnitud


def probar_quantile_mapping_sintetico(ruta_epw, factor_magnitud=FACTOR_MAGNITUD_NASA_POWER_SAN_JOSE,
                                       factor_compresion=0.5, n_cuantiles=100,
                                       modelo="medium_tulip", N=3, altura_buje=3.0, elevacion_m=921.0):
    """
    La prueba completa (ver docstring del módulo para el diseño
    anti-tautológico entrenar-en-H1/evaluar-en-H2). Devuelve un DataFrame
    con 4 filas -- verdad, sesgada cruda, corregida naive (sólo razón de
    medias), corregida por quantile mapping -- comparando media, CV,
    "factor de patrón de energía" (E[v^3]/media^3, lo que realmente pesa
    en una ley de potencia cúbica) y kWh del período de PRUEBA (Jul-Dic,
    nunca visto por el ajuste), todo relativo a la verdad real de ese
    mismo período.
    """
    df_real, meta = cargar_epw_real(ruta_epw)
    ws_real = df_real["WS10M"]

    ws_sesgada_valores = _construir_fuente_sintetica_sesgada(ws_real.values, factor_magnitud, factor_compresion)
    ws_sesgada = pd.Series(ws_sesgada_valores, index=ws_real.index)

    train = ws_real.index.month <= 6
    test = ~train

    cuantiles_fuente, cuantiles_verdad = ajustar_quantile_mapping(
        ws_sesgada[train].values, ws_real[train].values, n_cuantiles=n_cuantiles)
    factor_naive = ws_real[train].mean() / ws_sesgada[train].mean()

    ws_test_real = ws_real[test]
    ws_test_sesgada = ws_sesgada[test]
    ws_test_naive = ws_test_sesgada * factor_naive
    ws_test_qm = pd.Series(aplicar_quantile_mapping(ws_test_sesgada.values, cuantiles_fuente, cuantiles_verdad),
                            index=ws_test_sesgada.index)

    kwh_real_periodo = simular(pd.DataFrame({"WS10M": ws_test_real, "T2M": 22.0}), altura_buje, modelo, N,
                                elevacion_m=elevacion_m)["kwh_anual"]

    def resumen(ws, etiqueta):
        media = ws.mean()
        epf = float(np.mean(ws.values ** 3) / media ** 3)
        r = simular(pd.DataFrame({"WS10M": ws, "T2M": 22.0}), altura_buje, modelo, N, elevacion_m=elevacion_m)
        kwh = r["kwh_anual"]
        return dict(version=etiqueta, media_m_s=media, cv=ws.std() / media, epf=epf,
                    kwh_periodo_prueba=kwh, error_kwh_pct=(kwh / kwh_real_periodo - 1) * 100)

    filas = [
        resumen(ws_test_real, "VERDAD (EPW real, jul-dic, nunca vista por el ajuste)"),
        resumen(ws_test_sesgada, "SESGADA cruda (sin corregir)"),
        resumen(ws_test_naive, "Corregida NAIVE (solo razon de medias, ajustada en ene-jun)"),
        resumen(ws_test_qm, "Corregida QUANTILE MAPPING (percentil a percentil, ajustada en ene-jun)"),
    ]
    return pd.DataFrame(filas)


if __name__ == "__main__":
    pd.set_option("display.width", 220)
    pd.set_option("display.float_format", lambda x: f"{x:.3f}")

    ruta_epw_sj = os.path.join(_BASE, "datos_clima",
                                "CRI_AL_San.Jose-Santamaria.Intl.AP.787620_TMYx.2007-2021.epw")
    print("=" * 100)
    print("Prueba de MECANICA de quantile mapping -- sesgo sintetico controlado sobre el EPW real de San Jose")
    print("(ver docstring del modulo: NO hay serie horaria real de NASA POWER guardada en el repo)")
    print("=" * 100)
    print(f"Factor de magnitud usado (real, Hallazgo 1): {FACTOR_MAGNITUD_NASA_POWER_SAN_JOSE:.4f} "
          f"(= 1.30 / 4.03 m/s)")
    resultado = probar_quantile_mapping_sintetico(ruta_epw_sj)
    print(resultado.to_string(index=False))
