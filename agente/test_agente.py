"""Tests sin modelos ni PDF: troceado, verificación de citas, candidatos y validación de la respuesta."""
import pytest

import agente
from ingesta import MAX_CHARS, secciones, trocear

FRAG = {"id": "x:art.1#1", "ref": "art. 1", "corto": "Ley X", "titulo": "Plazos", "pagina": 3, "url": "u#page=3",
        "texto": "La notificación se hará en un plazo de 72 horas desde que se tenga cons­tancia."}


def test_secciones_boe_y_diario_europeo():
    boe = [(1, "Artículo 4.  Régimen."), (1, "Texto del cuatro.")]
    assert [(s["ref"], s["titulo"]) for s in secciones(boe, "articulos")] == [("art. 4", "Régimen")]
    ue = [(1, "(1) Considerando."), (2, "HAN ADOPTADO EL PRESENTE REGLAMENTO:"), (2, "Artículo 5"), (2, "Prácticas prohibidas"), (2, "Quedan prohibidas.")]
    assert [(s["ref"], s["titulo"]) for s in secciones(ue, "articulos")] == [("art. 5", "Prácticas prohibidas")]


def test_trocear_respeta_tamano_une_palabras_cortadas_y_guarda_pagina():
    trozos = trocear({"lineas": [(7, "La obli-"), (7, "gación es clara.")] + [(8, "Frase de relleno bastante larga para llenar.")] * 60})
    assert trozos[0][0] == 7 and "obligación" in trozos[0][1]
    assert len(trozos) > 1 and all(len(t) <= MAX_CHARS * 1.3 for _, t in trozos)


@pytest.mark.parametrize("respuesta,motivo", [
    ({"relevante": True, "cita": "en un plazo de 72 horas desde que se tenga constancia", "dato": "72 h"}, "nota"),
    ({"relevante": True, "cita": "en un plazo de 48 horas", "dato": "48 h"}, "cita no literal"),
    ({"relevante": True, "cita": "", "dato": "algo"}, "cita no literal"),
    ({"relevante": False, "cita": "en un plazo de 72 horas", "dato": ""}, "no contesta"),
    ({}, "no contesta"),
])
def test_solo_sobreviven_citas_literales(monkeypatch, respuesta, motivo):
    monkeypatch.setattr(agente, "llamar", lambda *a, **k: (respuesta, {"entrada": 1, "salida": 1}))
    nota, _, m = agente.leer("m", "¿plazo?", FRAG)
    assert m == motivo and (nota is not None) == (motivo == "nota")


@pytest.mark.parametrize("respuesta,estado", [
    ({"hay_respuesta": True, "respuesta": "72 horas", "notas": [1]}, "respaldada"),
    ({"hay_respuesta": True, "respuesta": "72 horas", "notas": [9]}, "rechazada"),
    ({"hay_respuesta": True, "respuesta": " ", "notas": [1]}, "rechazada"),
    ({"hay_respuesta": False, "respuesta": "", "notas": []}, "sin_evidencia"),
])
def test_la_respuesta_debe_apoyarse_en_notas_existentes(monkeypatch, respuesta, estado):
    monkeypatch.setattr(agente, "llamar", lambda *a, **k: (respuesta, {}))
    nota = {"ref": "art. 1", "titulo": "Plazos", "cita": "72 horas"}
    assert agente.responder("m", "¿plazo?", [nota], "es")[0]["estado"] == estado


def test_candidatos_no_deja_que_un_articulo_acapare():
    class Falso:
        por_id = {f"a{i}": {"ref": "art. 1"} for i in range(5)} | {"b": {"ref": "art. 2"}}

        def buscar(self, *_):
            return ["a0", "a1", "a2", "a3", "a4", "b"]

    assert agente.candidatos(Falso(), ["q"], "s") == ["a0", "a1", "b"]
