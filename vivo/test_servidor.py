"""Seguridad y contrato del servidor local, sin modelos: se levanta en un puerto libre."""
import http.client
import json
import threading

import pytest

import servidor


@pytest.fixture(scope="module")
def puerto():
    srv = servidor.ThreadingHTTPServer(("127.0.0.1", 0), servidor.Web)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield srv.server_address[1]
    srv.shutdown()


def pedir(puerto, ruta, metodo="GET", cuerpo=None, **cabeceras):
    c = http.client.HTTPConnection("127.0.0.1", puerto, timeout=20)
    c.request(metodo, ruta, cuerpo, cabeceras)
    r = c.getresponse()
    return r.status, r.read()


def test_sirve_la_web(puerto):
    assert pedir(puerto, "/index.html")[0] == 200


@pytest.mark.parametrize("ruta", ["/.gitignore", "/.git/config", "/agente/.oculto"])
def test_no_sirve_ficheros_ocultos(puerto, ruta):
    assert pedir(puerto, ruta)[0] == 403


def test_rechaza_otro_host(puerto):
    assert pedir(puerto, "/index.html", Host=f"malo.example:{puerto}")[0] == 403


@pytest.mark.parametrize("cabeceras", [
    {"Content-Type": "application/json", "Origin": "https://otra.example"},      # otra web
    {"Content-Type": "text/plain"},                                              # petición "simple" entre orígenes
])
def test_rechaza_post_ajeno(puerto, cabeceras):
    assert pedir(puerto, "/api/rag", "POST", '{"pregunta": "x"}', **cabeceras)[0] == 400


def test_rechaza_demo_inexistente_y_cuerpo_enorme(puerto):
    cab = {"Content-Type": "application/json"}
    assert pedir(puerto, "/api/borrar", "POST", "{}", **cab)[0] == 400
    assert pedir(puerto, "/api/rag", "POST", "x" * (servidor.MAX_CUERPO + 1), **cab)[0] == 400


def test_un_fallo_llega_a_la_web_como_evento(puerto, monkeypatch):
    def falla(nombre, q):
        raise RuntimeError("sin modelo")
        yield

    monkeypatch.setattr(servidor, "ejecutar", falla)
    codigo, cuerpo = pedir(puerto, "/api/rag", "POST", '{"pregunta": "x"}', **{"Content-Type": "application/json"})
    assert codigo == 200 and json.loads(cuerpo.decode().splitlines()[-1])["paso"] == "error"


def test_el_documento_pegado_se_trocea_con_limites():
    t = servidor.trocear("corta\n" + "\n".join(f"una línea suficientemente larga {n}" for n in range(200)))
    assert len(t) == 60 and t[0]["id"] == "P1" and all(d["norma"] == "DOC" for d in t)


def test_la_salida_de_monte_carlo_se_resume_y_trae_la_frase():
    d = {"gum": {"y": 10, "U": 0.28, "u": 0.14}, "monte_carlo": {"intervalo": [9.7, 10.3], "histograma": [1] * 999}}
    r = json.loads(servidor.resumir_resultado(json.dumps(d)))
    assert "histograma" not in r["monte_carlo"] and "U = 0.28" in r["frase_para_el_usuario"]
