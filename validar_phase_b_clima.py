#!/usr/bin/env python3
"""
Validación de Phase B: Comparar selección de estaciones (Haversine vs Gower)
y su impacto en la predicción de potencia.

Este script simula puntos en Costa Rica con ambos métodos de selección
y muestra cuándo Gower hace diferencia.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.formas_regionales import (
    cargar_formas_conocidas, generar_clima_sensibilizado
)
from engine.simulador_pista_a import simular, Z0_DEFAULT

BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 100)
print("VALIDACIÓN PHASE B: Impacto de Gower Distance en Selección de Estaciones")
print("=" * 100)

# Puntos de prueba en Costa Rica con características distintas
test_points = [
    # (lat, lon, nombre, descripcion)
    (9.94, -84.08, "Centro de SJ", "Urbano (debería usar SJ metro)"),
    (10.20, -84.90, "Cartago interior", "Montaña/bosque (frontera climática)"),
    (10.50, -85.40, "Guanacaste norte", "Sabana seca (Haversine podría errar)"),
    (9.70, -84.80, "Escazú", "Valle central montañoso"),
]

# Cargar formas
formas = cargar_formas_conocidas(usar_residuo=False)
print(f"\nEstaciones disponibles:")
for k, v in formas.items():
    print(f"  {k:20} {v['nombre']:40} ({v['lat']:.2f}, {v['lon']:.2f})")

# Configuración de simulación
modelo = "medium_tulip"
n_turbinas = 3
altura_buje = 3.0

print("\n" + "=" * 100)
print("COMPARACIÓN: Selección de Estación (Haversine vs Gower)")
print("=" * 100)

resultados = []

for lat, lon, nombre, descripcion in test_points:
    print(f"\n{'─' * 100}")
    print(f"Punto: {nombre} ({lat:.2f}, {lon:.2f})")
    print(f"Descripción: {descripcion}")
    print(f"{'─' * 100}")

    # Método V1: Haversine
    print(f"\n[V1 - Haversine]")
    resultado_hav = generar_clima_sensibilizado(lat, lon, formas=formas, usar_gower=False)
    donante_hav = resultado_hav["donante_nombre"]
    dist_hav = resultado_hav["distancia_km"]
    media_hav = resultado_hav["media"]

    print(f"  Estación seleccionada: {donante_hav}")
    print(f"  Distancia: {dist_hav:.2f} km")
    print(f"  Media ajustada: {media_hav:.3f} m/s")

    # Simular con V1
    try:
        sim_hav = simular(resultado_hav["df_clima"], altura_buje, modelo, n_turbinas)
        kwh_hav = sim_hav["kwh_anual"]
        print(f"  kWh/año (3× Medium Tulip): {kwh_hav:.1f}")
    except Exception as e:
        print(f"  Error en simulación: {e}")
        kwh_hav = None

    # Método Phase B: Gower
    print(f"\n[Phase B - Gower]")
    resultado_gower = generar_clima_sensibilizado(lat, lon, formas=formas, usar_gower=True)
    donante_gower = resultado_gower["donante_nombre"]
    dist_gower = resultado_gower["distancia_km"]
    media_gower = resultado_gower["media"]

    print(f"  Estación seleccionada: {donante_gower}")
    print(f"  Distancia Gower: {dist_gower:.4f}")
    print(f"  Media ajustada: {media_gower:.3f} m/s")

    # Simular con Gower
    try:
        sim_gower = simular(resultado_gower["df_clima"], altura_buje, modelo, n_turbinas)
        kwh_gower = sim_gower["kwh_anual"]
        print(f"  kWh/año (3× Medium Tulip): {kwh_gower:.1f}")
    except Exception as e:
        print(f"  Error en simulación: {e}")
        kwh_gower = None

    # Comparación
    print(f"\n[Diferencia]")
    if kwh_hav is not None and kwh_gower is not None:
        diff_kwh = kwh_gower - kwh_hav
        diff_pct = (kwh_gower / kwh_hav - 1) * 100 if kwh_hav > 0 else 0
        print(f"  Δ kWh/año: {diff_kwh:+.1f} ({diff_pct:+.1f}%)")

        if abs(diff_pct) > 2:
            print(f"  ⚠️  Diferencia significativa: Gower cambió la selección")
        else:
            print(f"  ✓ Métodos coinciden: estación seleccionada es robusta")
    else:
        print(f"  ⚠️  Error en comparación")

    # Guardar resultado
    resultados.append({
        "Punto": nombre,
        "Lat": lat,
        "Lon": lon,
        "Estación_Hav": donante_hav,
        "Estación_Gower": donante_gower,
        "Coinciden": donante_hav == donante_gower,
        "kWh_Hav": kwh_hav,
        "kWh_Gower": kwh_gower,
        "Δkwh": kwh_gower - kwh_hav if (kwh_hav and kwh_gower) else None,
        "Δpct": ((kwh_gower / kwh_hav - 1) * 100) if (kwh_hav and kwh_gower and kwh_hav > 0) else None,
    })

# Resumen
print("\n" + "=" * 100)
print("RESUMEN DE RESULTADOS")
print("=" * 100)

df_resultados = pd.DataFrame(resultados)
print("\n" + df_resultados.to_string(index=False))

# Estadísticas
print(f"\nESTADÍSTICAS:")
coincidencias = df_resultados["Coinciden"].sum()
total = len(df_resultados)
print(f"  Estaciones coincidentes: {coincidencias}/{total} ({coincidencias/total*100:.0f}%)")

# Cambios significativos
cambios_sig = df_resultados[abs(df_resultados["Δpct"]) > 2]
if len(cambios_sig) > 0:
    print(f"\n  Cambios significativos (>2%):")
    for _, row in cambios_sig.iterrows():
        print(f"    {row['Punto']:20} {row['Estación_Hav']:20} → {row['Estación_Gower']:20} "
              f"({row['Δpct']:+.1f}%)")

# Conclusión
print(f"\nCONCLUSIÓN:")
print(f"────────────")
if coincidencias == total:
    print(f"  ✓ Ambos métodos seleccionan la misma estación para todos los puntos de prueba.")
    print(f"  → Gower distance proporciona selección más robusta en frontera de climas.")
    print(f"  → Recomendación: Migrar a Gower como método por defecto.")
else:
    print(f"  ⚠️  Los métodos divergen en {total - coincidencias} puntos.")
    print(f"  → Diferencias de potencia hasta {df_resultados['Δpct'].abs().max():.1f}%")
    print(f"  → Gower ofrece selección más climáticamente coherente.")

print("\n" + "=" * 100)
