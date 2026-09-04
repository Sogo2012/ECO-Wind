#!/usr/bin/env python3
"""
Pruebas unitarias para engine/tipo_cambio_bccr.py

Ninguna de estas pruebas llama al BCCR real -- requests.get() siempre se
mockea. Verifica:
- El llamado real manda el header User-Agent de navegador (evita el 403 del
  WAF del BCCR, ver comentario en tipo_cambio_bccr.py).
- Camino feliz: el BCCR responde y se guarda en caché local.
- Si el BCCR falla pero hay caché local, se usa la caché (no es emergencia).
- Si el BCCR y la caché local fallan las dos, se usa el valor de emergencia.
"""
from datetime import datetime
from unittest import mock

import pytest

from engine import tipo_cambio_bccr


def _respuesta_ok(valor="530.10"):
    return mock.Mock(
        status_code=200,
        json=lambda: {
            "estado": True,
            "datos": [{"series": [{"valorDatoPorPeriodo": valor}]}],
        },
        raise_for_status=lambda: None,
        text="",
    )


@pytest.fixture
def cache_local_temporal(tmp_path, monkeypatch):
    """Aísla cada prueba en su propio archivo de caché, no en el real del repo."""
    ruta = tmp_path / "cache_tipo_cambio.json"
    monkeypatch.setattr(tipo_cambio_bccr, "CACHE_LOCAL_PATH", ruta)
    return ruta


@pytest.fixture(autouse=True)
def token_bccr_falso(monkeypatch):
    """Todas las pruebas necesitan BCCR_BEARER_TOKEN definido en el entorno."""
    monkeypatch.setenv("BCCR_BEARER_TOKEN", "token-de-prueba")


class TestLlamadaAlBCCR:
    def test_manda_user_agent_de_navegador(self, cache_local_temporal):
        with mock.patch("engine.tipo_cambio_bccr.requests.get", return_value=_respuesta_ok()) as get:
            tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        headers = get.call_args.kwargs["headers"]
        assert headers["User-Agent"] == tipo_cambio_bccr.USER_AGENT_BCCR
        assert "python-requests" not in headers["User-Agent"]

    def test_usa_el_indicador_de_venta_por_defecto(self, cache_local_temporal):
        with mock.patch("engine.tipo_cambio_bccr.requests.get", return_value=_respuesta_ok()) as get:
            tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        url_llamada = get.call_args.args[0]
        assert str(tipo_cambio_bccr.INDICADOR_DOLAR_VENTA) in url_llamada

    def test_el_bccr_responde_bien_y_no_es_emergencia(self, cache_local_temporal):
        with mock.patch("engine.tipo_cambio_bccr.requests.get", return_value=_respuesta_ok("530.10")):
            valor, es_emergencia = tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        assert valor == 530.10
        assert es_emergencia is False

    def test_falta_el_token_no_lanza_excepcion(self, cache_local_temporal, monkeypatch):
        monkeypatch.delenv("BCCR_BEARER_TOKEN", raising=False)
        valor, es_emergencia = tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        assert valor == tipo_cambio_bccr.TIPO_CAMBIO_EMERGENCIA
        assert es_emergencia is True


class TestCacheLocal:
    def test_se_escribe_y_se_relee(self, cache_local_temporal):
        tipo_cambio_bccr._guardar_cache_local(516.20, datetime(2026, 9, 4))

        assert cache_local_temporal.exists()
        assert tipo_cambio_bccr._leer_cache_local() == {"fecha": "2026-09-04", "valor": 516.20}

    def test_una_llamada_exitosa_al_bccr_refresca_la_cache(self, cache_local_temporal):
        with mock.patch("engine.tipo_cambio_bccr.requests.get", return_value=_respuesta_ok("530.10")):
            tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        assert tipo_cambio_bccr._leer_cache_local() == {"fecha": "2026-09-04", "valor": 530.10}

    def test_si_el_bccr_falla_pero_hay_cache_local_no_es_emergencia(self, cache_local_temporal):
        tipo_cambio_bccr._guardar_cache_local(518.00, datetime(2026, 9, 3))

        with mock.patch("engine.tipo_cambio_bccr.requests.get", side_effect=ConnectionError("403")):
            valor, es_emergencia = tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        assert valor == 518.00
        assert es_emergencia is False


class TestValorDeEmergencia:
    def test_si_el_bccr_y_la_cache_local_fallan_las_dos(self, cache_local_temporal):
        with mock.patch("engine.tipo_cambio_bccr.requests.get", side_effect=ConnectionError("403")):
            valor, es_emergencia = tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        assert valor == tipo_cambio_bccr.TIPO_CAMBIO_EMERGENCIA
        assert es_emergencia is True

    def test_respuesta_sin_series_cae_a_emergencia_sin_lanzar(self, cache_local_temporal):
        respuesta_vacia = mock.Mock(
            status_code=200,
            json=lambda: {"estado": True, "datos": [{"series": []}]},
            raise_for_status=lambda: None,
            text="",
        )
        with mock.patch("engine.tipo_cambio_bccr.requests.get", return_value=respuesta_vacia):
            valor, es_emergencia = tipo_cambio_bccr.obtener_tipo_cambio_bccr(datetime(2026, 9, 4))

        assert valor == tipo_cambio_bccr.TIPO_CAMBIO_EMERGENCIA
        assert es_emergencia is True
