"""La notación del MCP se cumple (ver NOTACION.md). Ejecutar: .venv\\Scripts\\python.exe tests\\test_notacion.py"""
import importlib
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import server  # noqa: E402

AREAS = {p.stem for p in (RAIZ / "herramientas").glob("*.py")} - {"__init__", "actividad"}


def test_herramientas_corresponden_1_a_1():
    for t in server.mcp._tool_manager.list_tools():
        assert re.fullmatch(r"[a-z0-9]+(_[a-z0-9]+)+", t.name), t.name
        area, _, fn = t.name.partition("_")
        assert area in AREAS, f"{t.name}: área desconocida"
        assert hasattr(importlib.import_module(f"herramientas.{area}"), fn), \
            f"{t.name} no tiene herramientas/{area}.py::{fn}"


def test_herramientas_declaran_consulta_o_ejecucion():
    for t in server.mcp._tool_manager.list_tools():
        assert t.annotations is not None and t.annotations.readOnlyHint is not None, t.name
        clase = "CONSULTA" if t.annotations.readOnlyHint else "EJECUCIÓN"
        assert (t.description or "").startswith(clase), f"{t.name}: la descripción debe empezar por {clase}"


def test_recursos_y_prompts():
    for r in server.mcp._resource_manager.list_resources():
        assert str(r.uri).split("://")[0] in AREAS, r.uri
    for p in server.mcp._prompt_manager.list_prompts():
        assert re.fullmatch(r"[a-z]+-\d\d-[a-z-]+", p.name) and p.name.split("-")[0] in AREAS, p.name


if __name__ == "__main__":
    for nombre, f in list(globals().items()):
        if nombre.startswith("test_"):
            f()
            print("OK ", nombre)
