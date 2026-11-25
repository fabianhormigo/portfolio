"""Tests sin modelos: corpus coherente, fusión, validación de citas y corrección de respuestas."""
import pytest

from datos import CORPUS, PREGUNTAS, RESERVADAS
from evaluar import acierta
from lexico import Fragmento
from rag import Rag, fusion_rrf

IDS = {d["id"] for d in CORPUS}


def test_corpus_y_preguntas_coherentes():
    assert len(IDS) == len(CORPUS)
    for p in PREGUNTAS + RESERVADAS:
        if p["gold"]:
            d = next(d for d in CORPUS if d["id"] == p["gold"])
            assert (d["norma"], d["version"]) == (p["norma"], p["version"])
            assert p["esperado"] in d["texto"].lower()


def test_rrf_premia_lo_que_sale_arriba_en_ambas_listas():
    assert fusion_rrf([["a", "b", "c"], ["b", "c", "a"]])[0] == "b"


@pytest.fixture
def rag():
    r = Rag.__new__(Rag)   # sin Ollama ni Chroma: solo validación
    r.frags = {d["id"]: Fragmento(**d) for d in CORPUS}
    return r


@pytest.mark.parametrize("salida,estado", [
    ({"hay_evidencia": False, "id": "", "cita": ""}, "sin_evidencia"),
    ({"hay_evidencia": True, "id": "S-2025-3.1", "cita": "se calibrará cada 9 meses"}, "valida"),
    ({"hay_evidencia": True, "id": "S-2025-3.1", "cita": "se calibrará cada 6 meses"}, "rechazada"),
    ({"hay_evidencia": True, "id": "S-2022-3.1", "cita": "cada 12 meses"}, "rechazada"),  # no recuperado
    ({"hay_evidencia": True, "id": "S-2025-3.1", "cita": ""}, "rechazada"),
    ({"hay_evidencia": True, "id": "S-2025-3.1", "cita": "cada 9 meses", "respuesta": "  "}, "rechazada"),
])
def test_validacion_de_citas(rag, salida, estado):
    assert rag.validar(salida, ["S-2025-3.1"]) == estado


def test_acierto_no_confunde_numeros():
    assert acierta("5", "al menos 5 días") and not acierta("5", "0,55") and not acierta("5", "15 días")
