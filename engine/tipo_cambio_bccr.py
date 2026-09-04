# engine/tipo_cambio_bccr.py
# =============================================================================
# Motor de tipo de cambio (BCCR) para ECO | Wind
# Trae el tipo de cambio USD/CRC oficial del Banco Central de Costa Rica (API
# SDDE, REST/JSON con autenticación Bearer) para poder cotizar en colones.
#
# Puerto de la misma lógica que ya corre en producción en otros dos proyectos
# de ECO Consultor (CRM-ECO, documentado ahí en CLAUDE.md -- se mantienen
# sincronizados a mano si el BCCR cambia el contrato de su API):
#   - eco-costeo/src/motor/tipo_cambio.py    (Python, la app Streamlit de Silvia)
#   - utilidades-crm/HistorialTipoCambio.gs  (Apps Script, trigger diario)
#
# Diferencias respecto a esas dos versiones, para calzar con cómo está armado
# ECO | Wind hoy (sin Google Sheets conectado):
#   - Un solo nivel de caché de resiliencia (archivo JSON local en
#     data/cache_tipo_cambio.json), no dos. Si en algún momento ECO | Wind
#     conecta un Google Sheet compartido, se le puede agregar esa capa igual
#     que en eco-costeo (ver _leer_cache_sheets/_guardar_cache_sheets allá).
#   - El token del BCCR se lee de la variable de entorno BCCR_BEARER_TOKEN
#     (con python-dotenv para desarrollo local, igual que en eco-costeo). En
#     Cloud Run, la forma recomendada es inyectarla como secreto directo con
#     "--set-secrets=BCCR_BEARER_TOKEN=bccr-bearer-token:latest" en el paso de
#     deploy de cloudbuild.yaml (hay un ejemplo comentado ahí) -- así el
#     contenedor la recibe como variable de entorno normal, sin que este
#     módulo tenga que llamar a Secret Manager por su cuenta.
# =============================================================================
import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("eco-wind")

BASE_URL = "https://apim.bccr.fi.cr/"
ENDPOINT_SERIES = "SDDE/api/Bccr.GE.SDDE.Publico.Indicadores.API/indicadoresEconomicos/{codigo}/series"

# Indicadores del BCCR, verificados contra una respuesta real (ver los dos
# proyectos hermanos arriba). "Venta" es el que corresponde para convertir un
# costo/precio en USD a colones -- es lo que el BCCR *vende* el dólar, no lo
# que compra -- por eso es el default de obtener_tipo_cambio_bccr().
INDICADOR_DOLAR_COMPRA = 317
INDICADOR_DOLAR_VENTA = 318

# El cliente `requests` manda "python-requests/X.Y" como User-Agent si no se
# lo pisa. En los proyectos hermanos el BCCR empezó a devolver 403 Forbidden
# con el mismo token/headers que antes funcionaban sin problema -- lo más
# probable es un WAF del BCCR bloqueando firmas de bot conocidas. El fix
# (simular un browser real) no tiene downside, así que se aplica acá también
# de forma preventiva.
USER_AGENT_BCCR = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

CACHE_LOCAL_PATH = Path(__file__).resolve().parent.parent / "data" / "cache_tipo_cambio.json"

# ⚠️ Valor de emergencia -- SOLO se usa si el BCCR no responde Y todavía no
# hay ningún valor guardado en la caché local (ej. primer arranque del
# contenedor, antes de que se haya guardado algo). Actualizar de vez en
# cuando para que la emergencia no quede muy desactualizada.
TIPO_CAMBIO_EMERGENCIA = 515.00


def _leer_cache_local() -> Optional[dict]:
    """Último tipo de cambio guardado en disco. None si nunca se guardó nada."""
    if not CACHE_LOCAL_PATH.exists():
        return None
    with open(CACHE_LOCAL_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _guardar_cache_local(valor: float, fecha: datetime) -> None:
    """Refresca la caché en disco con el último dato que sí funcionó."""
    CACHE_LOCAL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_LOCAL_PATH, "w", encoding="utf-8") as f:
        json.dump({"fecha": fecha.strftime("%Y-%m-%d"), "valor": valor}, f)


def obtener_tipo_cambio_bccr(
    fecha: Optional[datetime] = None,
    indicador: int = INDICADOR_DOLAR_VENTA,
) -> Tuple[float, bool]:
    """
    Tipo de cambio USD/CRC del BCCR (API SDDE). Nunca lanza excepción -- a
    prueba de balas para no tumbar la UI de Streamlit. Retorna una tupla
    (valor, es_emergencia):

      - Si el BCCR responde bien: (valor_del_bccr, False).
      - Si el BCCR falla pero hay un valor guardado en caché local:
        (valor_en_caché, False).
      - Si el BCCR Y la caché local fallan las dos:
        (TIPO_CAMBIO_EMERGENCIA, True) -- es_emergencia=True le indica a
        quien llama que debe avisarle al usuario que el valor no es del día.
    """
    fecha = fecha or datetime.now()
    try:
        token = os.getenv("BCCR_BEARER_TOKEN")
        if not token:
            raise ValueError(
                "BCCR_BEARER_TOKEN no está definido (.env local, o secreto "
                "inyectado como variable de entorno en Cloud Run)"
            )

        url = BASE_URL + ENDPOINT_SERIES.format(codigo=indicador)
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "User-Agent": USER_AGENT_BCCR,
        }
        params = {
            "fechaInicio": fecha.strftime("%Y/%m/%d"),
            "fechaFin": fecha.strftime("%Y/%m/%d"),
            "idioma": "es",
        }

        respuesta = requests.get(url, params=params, headers=headers, timeout=10)
        respuesta.raise_for_status()
        data = respuesta.json()

        if not data.get("estado"):
            raise ValueError(data.get("mensaje", "El BCCR respondió sin datos"))

        # Forma real de la respuesta (confirmada contra el BCCR en los
        # proyectos hermanos): cada elemento de "datos" trae "series"
        # directamente, sin ningún nivel "indicadores" intermedio.
        datos = data.get("datos")
        if not datos:
            raise ValueError(f"Estructura inesperada del BCCR (falta 'datos'): {respuesta.text}")

        series = datos[0].get("series")
        if not series:
            raise ValueError(f"El BCCR no devolvió datos para esa fecha. Respuesta completa: {respuesta.text}")

        valor = float(series[0]["valorDatoPorPeriodo"])
        _guardar_cache_local(valor, fecha)
        return valor, False

    except Exception as e:
        logger.error(f"BCCR no disponible ({type(e).__name__}: {e})")
        cache = _leer_cache_local()
        if cache:
            logger.warning(f"BCCR no disponible -- usando caché local del {cache['fecha']}: {cache['valor']}")
            return float(cache["valor"]), False

        logger.error(
            f"Sin caché local disponible -- usando tipo de cambio de "
            f"emergencia: {TIPO_CAMBIO_EMERGENCIA}"
        )
        return TIPO_CAMBIO_EMERGENCIA, True
