"""
Costos de fábrica para turbinas eólicas Flower Turbines.

Precios en USD (Off-Grid, sin instalación ni transporte).
Datos de lista de precios oficial.
"""
import pandas as pd

FLOWERTURBINES_COSTOS = [
    {"SKU": "Small Tulip Wind Turbine (Off-Grid)", "Precio_Regular_USD": 1153.36},
    {"SKU": "Medium Tulip Wind Turbine (Off-Grid)", "Precio_Regular_USD": 9349.26},
    {"SKU": "3-M Tulip Wind Turbine (Off-Grid)", "Precio_Regular_USD": 12905.75},
    {"SKU": "2M AL13 Power Tower™ (Off-Grid)", "Precio_Regular_USD": 8929.05}
]

def get_flowerturbines_costos_df():
    """Retorna el DataFrame de costos de Flower Turbines."""
    return pd.DataFrame(FLOWERTURBINES_COSTOS)

if __name__ == "__main__":
    df = get_flowerturbines_costos_df()
    print(df)
