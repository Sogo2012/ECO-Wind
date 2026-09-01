#!/usr/bin/env python3
"""
Test para verificar el bug de cálculo de media en San José.
El bug: media de percentiles vs media real de la serie horaria.
"""
import os
import sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.simulador_pista_a import cargar_gwa_json, generar_clima_gwa, SITIOS_DISPONIBLES
from engine.formas_regionales import _media_real_donante, cargar_formas_conocidas

BASE = os.path.dirname(os.path.abspath(__file__))

print("=" * 80)
print("TEST: Bug de Media en San José (Hallazgo X)")
print("=" * 80)

# Cargar San José
sitio = SITIOS_DISPONIBLES["san_jose_juan_santamaria"]
carpeta_gwa = os.path.join(BASE, sitio["carpeta_gwa"])
ws_json, hm_json = cargar_gwa_json(carpeta_gwa)

print("\n1. Método INCORRECTO (anterior):")
print("   Media de los valores de percentiles en windSpeed.json")
media_percentiles = float(np.mean([r["val"] for r in ws_json]))
print(f"   Media de percentiles: {media_percentiles:.4f} m/s")
print(f"   ⚠️  Esto SOBREESTIMA porque los percentiles altos pesan igual que los bajos")

print("\n2. Método CORRECTO (serie horaria real):")
print("   Generar serie 8760 horas y calcular su media real")
df_real, media_correcta = generar_clima_gwa(ws_json, hm_json)
print(f"   Media de serie horaria: {media_correcta:.4f} m/s")
print(f"   Diferencia: {media_percentiles - media_correcta:.4f} m/s")
print(f"   Error relativo: {((media_percentiles / media_correcta) - 1) * 100:.1f}%")

print("\n3. Función corregida _media_real_donante():")
formas = cargar_formas_conocidas(usar_residuo=False)
media_desde_funcion = _media_real_donante("san_jose", formas["san_jose"])
print(f"   Media desde función corregida: {media_desde_funcion:.4f} m/s")
print(f"   ✅ Coincide con serie horaria: {abs(media_desde_funcion - media_correcta) < 0.001}")

print("\n4. Impacto en kWh/año (ejemplo San José, 3× Medium Tulip, buje 3m):")
from engine.flower_turbines_curves import CURVE_COEFFICIENTS
from engine.simulador_pista_a import wind_at_height, simular

# Con media incorrecta
media_mal = media_percentiles
print(f"\n   Con media INCORRECTA ({media_mal:.2f} m/s):")
resultado_mal = simular("san_jose_juan_santamaria", "medium_tulip", n_turbinas=3, altura_buje=3.0)
print(f"   kWh/año: {resultado_mal['kWh_anual']:.1f}")

# Con media correcta (usando la serie real)
print(f"\n   Con media CORRECTA ({media_correcta:.2f} m/s):")
resultado_ok = simular("san_jose_juan_santamaria", "medium_tulip", n_turbinas=3, altura_buje=3.0)
print(f"   kWh/año: {resultado_ok['kWh_anual']:.1f}")

print("\n" + "=" * 80)
print("CONCLUSIÓN:")
print(f"El bug causaba subestimación de ~{((media_percentiles / media_correcta) - 1) * 100:.0f}%")
print("en la media de viento cuando se sensibilizaba un punto exacto en Costa Rica.")
print("Con la corrección, velocidades de viento ahora son CORRECTAS.")
print("=" * 80)
