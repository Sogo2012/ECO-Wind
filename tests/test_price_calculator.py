#!/usr/bin/env python3
"""
Pruebas unitarias para price_calculator

Verifica:
- Cálculo correcto de precios finales
- Desglose de costos
- BOM de turbinas y sistemas
- Validación de parámetros
"""

import pytest
from engine.price_calculator import (
    calcular_precio_final,
    desglose_precio,
    calcular_bom_turbinas,
    calcular_bom_sistema_completo,
    calcular_precio_kwh_instalado,
    estimar_ahorro_anual,
    IMPORT_COST_USD,
    MARGIN_PCT,
)


class TestCalcularPrecioFinal:
    """Pruebas para calcular_precio_final"""

    def test_precio_sin_importacion(self):
        """Precio final = Costo × (1 + Margen%)"""
        precio = calcular_precio_final(1000, agregar_importacion=False, margen_pct=0.30)
        # 1000 × 1.30 = 1300
        assert precio == pytest.approx(1300, abs=0.01)

    def test_precio_con_importacion(self):
        """Precio final = (Costo + Importación) × (1 + Margen%)"""
        precio = calcular_precio_final(1000, agregar_importacion=True, margen_pct=0.30)
        # (1000 + 2500) × 1.30 = 3500 × 1.30 = 4550
        assert precio == pytest.approx(4550, abs=0.01)

    def test_precio_margen_cero(self):
        """Con margen 0%, retorna solo costo + importación"""
        precio = calcular_precio_final(1000, agregar_importacion=True, margen_pct=0.0)
        # 1000 + 2500 = 3500
        assert precio == pytest.approx(3500, abs=0.01)

    def test_precio_costo_cero(self):
        """Costo base cero: retorna solo importación × (1 + margen)"""
        precio = calcular_precio_final(0, agregar_importacion=True, margen_pct=0.30)
        # 2500 × 1.30 = 3250
        assert precio == pytest.approx(3250, abs=0.01)

    def test_precio_validacion_costo_negativo(self):
        """Rechaza costo negativo"""
        with pytest.raises(ValueError, match="no puede ser negativo"):
            calcular_precio_final(-1000)

    def test_precio_validacion_margen_invalido(self):
        """Rechaza margen fuera de rango"""
        with pytest.raises(ValueError, match="entre 0 y 1"):
            calcular_precio_final(1000, margen_pct=1.5)


class TestDesglosePrecio:
    """Pruebas para desglose_precio"""

    def test_desglose_completo(self):
        """Retorna desglose detallado de precio"""
        resultado = desglose_precio(1000, agregar_importacion=True, margen_pct=0.30)

        assert resultado["costo_base_usd"] == 1000.0
        assert resultado["costo_importacion_usd"] == IMPORT_COST_USD
        assert resultado["subtotal_usd"] == pytest.approx(3500, abs=0.01)
        assert resultado["margen_usd"] == pytest.approx(1050, abs=0.01)  # 3500 × 0.30
        assert resultado["precio_final_usd"] == pytest.approx(4550, abs=0.01)

    def test_desglose_sin_importacion(self):
        """Desglose sin importación"""
        resultado = desglose_precio(1000, agregar_importacion=False, margen_pct=0.30)

        assert resultado["costo_importacion_usd"] == 0.0
        assert resultado["subtotal_usd"] == 1000.0
        assert resultado["margen_usd"] == pytest.approx(300, abs=0.01)
        assert resultado["precio_final_usd"] == pytest.approx(1300, abs=0.01)


class TestCalcularBomTurbinas:
    """Pruebas para calcular_bom_turbinas"""

    def test_bom_turbinas_basico(self):
        """BOM con múltiples turbinas"""
        turbinas = [
            {"modelo": "FT 1.15M", "cantidad": 2, "costo_base_usd": 5000},
            {"modelo": "FT 2M", "cantidad": 2, "costo_base_usd": 8000},
        ]

        resultado = calcular_bom_turbinas(turbinas)

        assert resultado["cantidad_turbinas_total"] == 4
        # Costo base total: (5000×2) + (8000×2) = 10000 + 16000 = 26000
        assert resultado["costo_base_total_usd"] == 26000.0
        # Precio final: (26000 + 2500) × 1.30 = 28500 × 1.30 = 37050
        assert resultado["precio_final_total_usd"] == pytest.approx(37050, abs=1)

    def test_bom_turbinas_detalles(self):
        """Detalles por turbina en BOM"""
        turbinas = [
            {"modelo": "FT 1.15M", "cantidad": 1, "costo_base_usd": 5000},
        ]

        resultado = calcular_bom_turbinas(turbinas)

        detalle = resultado["detalles"][0]
        assert detalle["modelo"] == "FT 1.15M"
        assert detalle["cantidad"] == 1
        assert detalle["costo_unitario_base_usd"] == 5000.0


class TestCalcularBomSistemaCompleto:
    """Pruebas para calcular_bom_sistema_completo"""

    def test_bom_sistema_standalone(self):
        """BOM sistema Standalone (con BESS)"""
        resultado = calcular_bom_sistema_completo(
            turbinas_base_usd=20000,
            cantidad_turbinas=4,
            inversor_base_usd=5000,
            bess_base_usd=8000,
        )

        assert resultado["detalles_equipos"]["turbinas"]["cantidad"] == 4
        assert resultado["detalles_equipos"]["inversor"]["cantidad"] == 1
        assert resultado["detalles_equipos"]["bess"]["cantidad"] == 1

        # Costo base total: 20000 + 5000 + 8000 = 33000
        assert resultado["costo_base_total_usd"] == 33000.0

    def test_bom_sistema_hybrid(self):
        """BOM sistema Hybrid (sin BESS)"""
        resultado = calcular_bom_sistema_completo(
            turbinas_base_usd=20000,
            cantidad_turbinas=4,
            inversor_base_usd=5000,
            bess_base_usd=0.0,
        )

        # Costo base total: 20000 + 5000 + 0 = 25000
        assert resultado["costo_base_total_usd"] == 25000.0
        assert resultado["detalles_equipos"]["bess"]["costo_base_total_usd"] == 0.0


class TestCalcularPrecioKwhInstalado:
    """Pruebas para calcular_precio_kwh_instalado"""

    def test_precio_kwh_instalado_basico(self):
        """Precio por kW = Precio_Total / Potencia_kW"""
        precio_kwh = calcular_precio_kwh_instalado(
            precio_sistema_usd=37050,
            potencia_pico_w=10000,  # 10 kW
        )

        # 37050 / 10 = 3705 USD/kW
        assert precio_kwh == pytest.approx(3705, abs=1)

    def test_precio_kwh_instalado_potencia_cero(self):
        """Rechaza potencia cero"""
        with pytest.raises(ValueError, match="mayor a 0"):
            calcular_precio_kwh_instalado(37050, 0)


class TestEstimarAhorroAnual:
    """Pruebas para estimar_ahorro_anual"""

    def test_ahorro_anual_basico(self):
        """Ahorro = Energía × Tarifa"""
        resultado = estimar_ahorro_anual(
            energia_anual_kwh=15000,
            tarifa_kwh_usd=0.15,
        )

        # 15000 × 0.15 = 2250
        assert resultado["ahorro_anual_usd"] == pytest.approx(2250, abs=0.01)
        assert resultado["ahorro_mensual_promedio_usd"] == pytest.approx(187.5, abs=0.01)
        assert resultado["ahorro_diario_promedio_usd"] == pytest.approx(6.16, abs=0.01)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
