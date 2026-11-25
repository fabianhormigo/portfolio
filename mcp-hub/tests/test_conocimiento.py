"""RAG pequeño (capa 2): con textos inventados."""
import json

import pytest

from conocimiento import indice
from conocimiento.busqueda import Pasaje, ordenar
from conocimiento.texto import fragmento, normalizar, tokens, trocear_texto


def _p(fuente, texto):
    return Pasaje(fuente, "pág. 1", texto, " ".join(tokens(texto)))


def test_normaliza_tildes_plurales_y_codigos():
    assert normalizar("Acústica ÁREA") == "acustica area"
    assert tokens("los recintos") == ["recinto"]
    assert tokens("reverberaciones") == tokens("reverberación")
    assert {"16283-1", "16283", "1"} <= set(tokens("ISO 16283-1"))
    assert "de" not in tokens("tiempo de reverberación")


def test_bm25_ordena_por_relevancia_y_dice_que_coincide():
    pasajes = [_p("a.pdf", "El ruido de fondo se corrige con la fórmula 14 cuando la diferencia es de 6 a 10 dB."),
               _p("b.pdf", "Posiciones de micrófono en el recinto emisor."),
               _p("c.pdf", "Ruido de tráfico rodado.")]
    r = ordenar("corrección por ruido de fondo", pasajes, 3)
    assert r[0].pasaje.fuente == "a.pdf" and set(r[0].coinciden) == {"ruido", "fondo"}
    assert "b.pdf" not in [x.pasaje.fuente for x in r]          # sin términos en común: no sale
    assert ordenar("", pasajes) == [] and ordenar("ruido", []) == []


def test_trocea_markdown_con_linea_de_inicio():
    md = "# Uno\n" + "texto largo. " * 20 + "\n\n# Dos\nmás texto aquí dentro\n"
    trozos = trocear_texto(md, objetivo=100)
    assert [l for l, _ in trozos] == [1, 4] and trozos[1][1].startswith("# Dos")


def test_fragmento_elige_la_ventana_con_los_terminos():
    texto = "\n".join(["relleno sin interés"] * 60 + ["aquí está el tiempo de reverberación"] + ["relleno"] * 60)
    assert "reverberación" in fragmento(texto, set(tokens("reverberación")), largo=120)


def test_indexar_y_cargar_en_carpeta_temporal(tmp_path, monkeypatch):
    rec, txt = tmp_path / "recursos", tmp_path / ".texto"
    (rec / "sub").mkdir(parents=True)
    (rec / "sub" / "nota.md").write_text("# Absorción\nEl coeficiente de absorción sonora αs.\n", encoding="utf-8")
    monkeypatch.setattr(indice, "RECURSOS", rec)
    monkeypatch.setattr(indice, "TEXTO", txt)

    r = indice.indexar()
    assert len(r["extraidos"]) == 1 and not r["errores"]
    assert indice.indexar()["al_dia"] == 1                      # segunda vez: nada que hacer
    pasajes, pendientes = indice.cargar()
    assert not pendientes and pasajes[0].fuente == "sub/nota.md" and pasajes[0].sitio == "línea 1"
    assert json.loads((txt / "sub" / "nota.md.json").read_text(encoding="utf-8"))["pasajes"]

    (rec / "sub" / "otra.txt").write_text("texto nuevo sin indexar", encoding="utf-8")
    assert indice.cargar()[1] == ["sub/otra.txt"]                # avisa de lo pendiente
    (rec / "sub" / "nota.md").unlink()
    assert indice.indexar()["borrados"] == 1                     # el texto de lo borrado se va


def test_no_sale_de_recursos():
    with pytest.raises(ValueError):
        indice.cargar("../")
