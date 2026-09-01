#!/usr/bin/env python3
"""
Validación de Phase B (Simplificada): Comparar selección de estaciones
sin requerir raster GWA.

Valida solo la lógica de Gower distance vs Haversine.
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.formas_regionales import (
    cargar_formas_conocidas, vecino_mas_cercano, vecino_gower
)
from engine.terrain_classification import (
    query_worldcover_z0, query_koppen_classification, WORLDCOVER_NAMES
)
from engine.epw_real import _haversine_km

print("=" * 100)
print("VALIDACIÓN PHASE B (SIMPLIFICADA): Selección de Estaciones sin Raster")
print("=" * 100)

# Puntos de prueba en Costa Rica
test_points = [
    # (lat, lon, nombre, descripcion, terrain_esperado)
    (9.94, -84.08, "Centro de SJ", "Urbano denso (metro)", "urban"),
    (9.75, -84.90, "Cartago interior", "Bosque/montaña", "forest"),
    (10.50, -85.40, "Guanacaste norte", "Sabana seca", "grassland"),
    (9.70, -84.75, "Escazú", "Valle montañoso", "forest"),
    (10.05, -84.30, "Alajuela norte", "Zona mixta", "mixed"),
]

# Cargar formas
formas = cargar_formas_conocidas(usar_residuo=False)

print(f"\nEstaciones disponibles:")
for k, v in formas.items():
    print(f"  {k:20} {v['nombre']:40} (lat={v['lat']:.2f}, lon={v['lon']:.2f}, elev={v['elevacion_m']:.0f}m)")

print("\n" + "=" * 100)
print("TABLA COMPARATIVA: Selección Haversine vs Gower")
print("=" * 100)

resultados = []

for lat, lon, nombre, descripcion, terrain_esp in test_points:
    print(f"\n{'─' * 100}")
    print(f"{nombre} ({lat:.2f}, {lon:.2f}) - {descripcion}")

    # Metadatos del punto
    z0_pt, code_pt, _ = query_worldcover_z0(lat, lon)
    koppen_pt, _, _ = query_koppen_classification(lat, lon)
    landcover_pt = WORLDCOVER_NAMES.get(code_pt, "Unknown")

    print(f"  Punto → z0={z0_pt:.3f}m ({landcover_pt}), Köppen={koppen_pt}")
    print(f"  {'─' * 100}")

    # V1: Haversine (pure geographic distance)
    clave_hav, dist_hav = vecino_mas_cercano(lat, lon, formas)
    donante_hav = formas[clave_hav]

    print(f"\n[V1 - Haversine Distance]")
    print(f"  Seleccionada: {clave_hav:20} ({donante_hav['nombre']})")
    print(f"  Distancia: {dist_hav:.2f} km")
    print(f"  Elevación: {donante_hav['elevacion_m']:.0f} m")

    koppen_hav, _, _ = query_koppen_classification(donante_hav['lat'], donante_hav['lon'])
    print(f"  Köppen: {koppen_hav}")

    # Phase B: Gower (climate + elevation + distance)
    clave_gower, dist_gower = vecino_gower(lat, lon, formas)
    donante_gower = formas[clave_gower]

    print(f"\n[Phase B - Gower Distance]")
    print(f"  Seleccionada: {clave_gower:20} ({donante_gower['nombre']})")
    print(f"  Gower distance: {dist_gower:.4f}")
    print(f"  Elevación: {donante_gower['elevacion_m']:.0f} m")

    koppen_gower, _, _ = query_koppen_classification(donante_gower['lat'], donante_gower['lon'])
    print(f"  Köppen: {koppen_gower}")

    # Análisis
    coinciden = (clave_hav == clave_gower)
    print(f"\n[Análisis]")
    if coinciden:
        print(f"  ✓ COINCIDEN - Ambos métodos seleccionan la misma estación")
        print(f"  → Selección robusta (geografia y clima alineados)")
    else:
        print(f"  ⚠️  DIVERGEN - Métodos seleccionan estaciones diferentes")
        print(f"  Razón probable:")

            # Diagnóstico de por qué divergen
        if koppen_pt != koppen_hav and koppen_pt == koppen_gower:
            print(f"    - Gower respeta clima: Pt={koppen_pt}, Gower={koppen_gower} vs Hav={koppen_hav}")
        elev_diff_hav = abs(donante_hav['elevacion_m'] - donante_gower['elevacion_m'])
        if elev_diff_hav > 500:
            print(f"    - Elevación mismatch: Hav={donante_hav['elevacion_m']:.0f}m vs Gower={donante_gower['elevacion_m']:.0f}m")

    resultados.append({
        "Punto": nombre,
        "Lat": lat,
        "Lon": lon,
        "Terrain": landcover_pt,
        "Köppen_Pt": koppen_pt,
        "Est_Hav": clave_hav,
        "Dist_Hav_km": dist_hav,
        "Köppen_Hav": koppen_hav,
        "Est_Gower": clave_gower,
        "Gower_dist": dist_gower,
        "Köppen_Gower": koppen_gower,
        "Coinciden": "✓" if coinciden else "⚠️",
    })

# Resumen en tabla
print("\n" + "=" * 100)
print("TABLA RESUMEN")
print("=" * 100)

df = pd.DataFrame(resultados)

# Mostrar seleccionadas
print("\nSelecciones por método:")
print(f"{'Punto':20} {'Haversine':20} {'Gower':20} {'Coinciden':10}")
print(f"{'-'*70}")
for _, row in df.iterrows():
    match = "✓" if row["Coinciden"] == "✓" else "DIVERGE"
    print(f"{row['Punto']:20} {row['Est_Hav']:20} {row['Est_Gower']:20} {match:10}")

# Estadísticas
coincidencias = sum(1 for _, row in df.iterrows() if row["Coinciden"] == "✓")
total = len(df)

print(f"\n{'─' * 70}")
print(f"ESTADÍSTICAS:")
print(f"  Coincidencias: {coincidencias}/{total} ({coincidencias/total*100:.0f}%)")
print(f"  Divergencias: {total - coincidencias}/{total} ({(total-coincidencias)/total*100:.0f}%)")

# Análisis de divergencias
divergencias = df[df["Coinciden"] == "⚠️"]
if len(divergencias) > 0:
    print(f"\nDivergencias:")
    for _, row in divergencias.iterrows():
        elev_diff = abs(
            formas[row['Est_Hav']]['elevacion_m'] -
            formas[row['Est_Gower']]['elevacion_m']
        )
        clima_diff = "SÍ" if row['Köppen_Hav'] != row['Köppen_Gower'] else "NO"
        print(f"  {row['Punto']:20}")
        print(f"    Hav: {row['Est_Hav']:15} ({row['Köppen_Hav']}, elev={formas[row['Est_Hav']]['elevacion_m']:.0f}m)")
        print(f"    Gow: {row['Est_Gower']:15} ({row['Köppen_Gower']}, elev={formas[row['Est_Gower']]['elevacion_m']:.0f}m)")
        print(f"    Δ Elevación: {elev_diff:.0f}m | Δ Köppen: {clima_diff}")

# Conclusión
print(f"\n{'=' * 100}")
print(f"CONCLUSIÓN")
print(f"{'=' * 100}")

if coincidencias == total:
    print(f"""
✓ AMBOS MÉTODOS COINCIDEN EN TODOS LOS CASOS

Interpretación:
  - La geografía (Haversine) y la climatología (Gower) están alineadas en Costa Rica
  - Esto es esperado: el Valle Central, Guanacaste y Caribe tienen patrones de
    distancia y clima coherentes
  - Gower no cambia la selección pero proporciona mayor robustez en fronteras

Recomendación:
  → Mantener Haversine como método por defecto (más rápido)
  → Ofrecer Gower como opción avanzada para usuarios que quieran máxima precisión
  → Ambos son válidos para Costa Rica
""")
else:
    print(f"""
⚠️  DIVERGENCIAS ENCONTRADAS EN {total - coincidencias}/{total} CASOS

Interpretación:
  - En {total - coincidencias} punto(s), Gower selecciona una estación diferente
  - Esto ocurre cuando clima y geografía no están perfectamente alineados
  - Típicamente en fronteras climáticas (p.ej., entre Meseta Central y Caribe)

Recomendación:
  → Implementar Gower como método por defecto (más correcto climáticamente)
  → Proporciona mejor aislamiento en zonas de frontera climática
  → Evita transferencias de clima erróneo (Hallazgo 21)
""")

print(f"{'=' * 100}")
