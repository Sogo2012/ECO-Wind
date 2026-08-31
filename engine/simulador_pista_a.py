"""
Pista A -- Motor empirico de simulacion (ECO | Wind).

Extraido de notebooks/pista_a_motor_empirico.ipynb (Pasos 2c-4) a un
modulo importable, para poder usarlo desde la app de Fase 2 (Streamlit)
sin depender del notebook. Misma logica, sin cambios de fondo -- ver el
notebook para el desarrollo/validacion paso a paso (Hallazgo de Pista A,
z0/GWA confirmado con datos reales a 10m).

FUENTE CLIMATICA: Global Wind Atlas (GWA), no NASA POWER. Dos razones,
ya documentadas en avance-de-proyecto.md:
1) NASA POWER subestima el viento real en el Valle Central (~3x, Hallazgo 1).
2) NASA POWER no es alcanzable desde este entorno de desarrollo (bloqueado
   por el proxy de red, confirmado 31/ago/2026) -- sin verificar todavia si
   aplica igual al entorno de produccion (Cloud Run).
GWA si esta confirmado con datos reales (Hallazgo 3).

LIMITACION IMPORTANTE, no escondida: la ingesta de GWA aqui es un export
manual del panel web (carpeta con windSpeed.json + heatmapData.json por
sitio) -- NO es una API en vivo para cualquier coordenada arbitraria.
Hoy solo existe un sitio preparado (San Jose / Juan Santamaria,
datos_clima/gwa_juan_santamaria/). El flujo "coordenada -> pronostico
instantaneo" del plan (seccion 5) para un sitio nuevo cualquiera sigue
sin resolverse -- pendiente real de Fase 2, no de esta sesion.
"""
import calendar
import json

import numpy as np
import pandas as pd

try:
    from engine.flower_turbines_curves import power_in_bouquet, CURVE_COEFFICIENTS
except ImportError:
    from flower_turbines_curves import power_in_bouquet, CURVE_COEFFICIENTS

Z0_DEFAULT = 0.3  # rugosidad suburbana/urbana baja -- ver wind_at_height()


def wind_at_height(v_ref, h_ref, h_target, z0=Z0_DEFAULT):
    """
    Perfil logaritmico de viento: v(h) = v_ref * ln(h_target/z0) / ln(h_ref/z0)

    h_ref   : altura del dato de referencia (10 para GWA/WS10M).
    h_target: altura real de buje de la turbina.
    z0      : longitud de rugosidad (m) -- 0.03 campo abierto, 0.1 cultivos
              bajos, 0.3 suburbano (default), 1.0 urbano denso. Las
              turbinas Flower Turbines son muy bajas (buje 1-6m), casi
              siempre POR DEBAJO de los 10m de referencia -- la correccion
              casi siempre REDUCE la velocidad respecto al dato crudo.
    """
    v_ref = np.asarray(v_ref, dtype=float)
    return v_ref * np.log(h_target / z0) / np.log(h_ref / z0)


def cargar_gwa_json(carpeta):
    """Carga windSpeed.json (curva de excedencia empirica) y
    heatmapData.json (indice real mes x hora) de un export de plot data
    del Global Wind Atlas (panel web, descarga manual por sitio)."""
    with open(f"{carpeta}/windSpeed.json") as f:
        ws = json.load(f)
    with open(f"{carpeta}/heatmapData.json") as f:
        hm = json.load(f)
    return ws, hm


def generar_clima_gwa(windspeed_json, heatmap_json, year=2023, seed=42):
    """
    Serie horaria de viento a partir del export real del Global Wind Atlas.
    Ver notebooks/pista_a_motor_empirico.ipynb Paso 2c para el desarrollo
    completo -- resumen: transformada inversa sobre la curva de excedencia
    real (sin asumir Weibull) + indice real mes x hora para reproducir
    estacionalidad y ciclo diurno reales.
    """
    perc = np.array([r["perc"] for r in windspeed_json], dtype=float)
    val = np.array([r["val"] for r in windspeed_json], dtype=float)
    orden = np.argsort(perc)
    perc_ord, val_ord = perc[orden], val[orden]
    media_global = val_ord.mean()

    idx_lookup = {(r["month"], r["hour"]): r["value"] for r in heatmap_json}

    n_horas = 8784 if calendar.isleap(year) else 8760
    idx_dt = pd.date_range(f"{year}-01-01", periods=n_horas, freq="h")
    rng = np.random.default_rng(seed)

    u = rng.uniform(0, 1, size=n_horas)
    perc_objetivo = 100 * (1 - u)
    r_normalizado = np.interp(perc_objetivo, perc_ord, val_ord) / media_global

    factores = np.array([idx_lookup[(m, h)] for m, h in zip(idx_dt.month, idx_dt.hour)])
    ws = r_normalizado * media_global * factores

    return pd.DataFrame({"WS10M": ws, "T2M": 22.0}, index=idx_dt), media_global


def simular(df_clima, altura_buje, modelo, N, h_ref=10, z0=Z0_DEFAULT, metodo_bouquet="real"):
    """
    Ensambla la serie horaria de potencia del cluster y la agrega a kWh
    mensual/anual, usando P(v)=k*v^3 x M(N) del motor empirico
    (engine/flower_turbines_curves.py, validado Hallazgo 12).

    df_clima: DataFrame con indice datetime horario y columna 'WS10M' (m/s).
    """
    v_hub = wind_at_height(df_clima["WS10M"].values, h_ref, altura_buje, z0=z0)
    potencia_w_por_turbina = power_in_bouquet(v_hub, modelo, N, metodo=metodo_bouquet)

    serie = pd.Series(potencia_w_por_turbina, index=df_clima.index,
                       name="potencia_W_por_turbina")
    energia_cluster_kwh = serie * N / 1000.0
    return {
        "serie_horaria_W_por_turbina": serie,
        "kwh_mensual": energia_cluster_kwh.resample("MS").sum(),
        "kwh_anual": float(energia_cluster_kwh.sum()),
        "v_hub_medio": float(np.mean(v_hub)),
        "pct_horas_bajo_cutin": float(np.mean(v_hub < CURVE_COEFFICIENTS[modelo]["v_cutin"]) * 100),
    }


SITIOS_DISPONIBLES = {
    "san_jose_juan_santamaria": {
        "nombre": "San José (Aeropuerto Juan Santamaría)",
        "carpeta_gwa": "datos_clima/gwa_juan_santamaria",
        "lat": 10.0034, "lon": -84.2033,
    },
}


if __name__ == "__main__":
    import os
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
    ws_json, hm_json = cargar_gwa_json(os.path.join(base, sitio["carpeta_gwa"]))
    df_gwa, media_global = generar_clima_gwa(ws_json, hm_json)
    print(f"Sitio: {sitio['nombre']} -- media GWA confirmada: {media_global:.3f} m/s")

    r = simular(df_gwa, altura_buje=3.0, modelo="medium_tulip", N=3)
    print(f"Medium Tulip x3, buje 3.0m: {r['kwh_anual']:.1f} kWh/año "
          f"(v_hub medio={r['v_hub_medio']:.2f} m/s, {r['pct_horas_bajo_cutin']:.1f}% horas bajo cut-in)")
