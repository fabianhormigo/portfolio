import pytest

from crm_etl import Crm, con_reintentos, normalizar_nombre, normalizar_telefono


def test_normalizacion():
    assert normalizar_nombre("  José   PÉREZ ") == "jose perez"
    assert normalizar_telefono("+34 600-111-222") == "600111222"


def test_evento_duplicado_no_se_aplica_dos_veces():
    crm = Crm()
    p = {"nombre": "Ana Ruiz", "email": "ana@x.com", "estado": "nuevo"}
    assert crm.procesar_evento("ev1", p) == "aplicado"
    assert crm.procesar_evento("ev1", {**p, "estado": "ganado"}) == "duplicado"
    assert crm.clientes() == [("ana ruiz", "ana@x.com", "", "nuevo")]


def test_deduplica_por_email_o_telefono_con_variantes():
    crm = Crm()
    crm.procesar_evento("a", {"nombre": "José Pérez", "email": "JP@x.com"})
    crm.procesar_evento("b", {"nombre": "jose perez", "email": "jp@x.com", "telefono": "+34 600 111 222"})
    crm.procesar_evento("c", {"nombre": "J. Pérez", "telefono": "600111222", "estado": "contactado"})
    assert crm.clientes() == [("j. perez", "jp@x.com", "600111222", "contactado")]


def test_fallo_a_mitad_revierte_y_permite_reintento():
    crm = Crm()
    with pytest.raises(ValueError):
        crm.procesar_evento("ev9", {"nombre": "Luis", "email": "l@x.com", "estado": "inventado"})
    assert crm.clientes() == []
    assert crm.procesar_evento("ev9", {"nombre": "Luis", "email": "l@x.com"}) == "aplicado"


def test_backoff_exponencial_y_exito_tras_fallos_transitorios():
    esperas, llamadas = [], []

    def fn():
        llamadas.append(1)
        if len(llamadas) < 4:
            raise ConnectionError("red")
        return "ok"

    assert con_reintentos(fn, intentos=4, base=0.1, sleep=esperas.append) == "ok"
    assert esperas == pytest.approx([0.1, 0.2, 0.4])


def test_agota_reintentos_y_propaga():
    with pytest.raises(TimeoutError):
        con_reintentos(lambda: (_ for _ in ()).throw(TimeoutError()), intentos=3, sleep=lambda s: None)


def test_error_no_transitorio_no_se_reintenta():
    llamadas = []

    def fn():
        llamadas.append(1)
        raise ValueError("dato malo")

    with pytest.raises(ValueError):
        con_reintentos(fn, sleep=lambda s: None)
    assert len(llamadas) == 1
