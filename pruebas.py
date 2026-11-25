"""Ejecuta los tests de todos los proyectos, mide la cobertura del agente y genera docs/PRUEBAS.md y pruebas.json.

    python pruebas.py        (MCP_PYTHON: intérprete con `mcp` para mcp-hub; por defecto, el actual)
"""
from __future__ import annotations

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
PROYECTOS = ("agente", "vivo", "rag-real", "mcp-hub", "chat-analista", "etl-idempotente")
MODULOS = "agente.py,metricas.py,informe.py,ingesta.py,evaluar.py"


def correr(orden: list[str], carpeta: Path) -> str:
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1", "PYTHONIOENCODING": "utf-8"}
    r = subprocess.run(orden, cwd=carpeta, env=env, capture_output=True, text=True, encoding="utf-8", timeout=600)
    if r.returncode:
        raise SystemExit(f"Fallan los tests de {carpeta.name}:\n{r.stdout[-3000:]}{r.stderr[-1000:]}")
    return r.stdout


def descripcion(fichero: Path) -> str:
    doc = ast.get_docstring(ast.parse(fichero.read_text(encoding="utf-8"))) or ""
    return doc.strip().split("\n")[0]


def main() -> None:
    cov = Path(tempfile.mkdtemp()) / ".coverage"
    try:
        import coverage  # noqa: F401
        hay_cobertura = True
    except ImportError:
        hay_cobertura = False
    resumen, cobertura = [], None
    for p in PROYECTOS:
        py = os.environ.get("MCP_PYTHON", sys.executable) if p == "mcp-hub" else sys.executable
        medir = p == "agente" and hay_cobertura
        pytest = ["-m", "pytest", "-q", "-p", "no:cacheprovider"]
        orden = [py, "-m", "coverage", "run", f"--data-file={cov}", f"--include={MODULOS}", *pytest] if medir else [py, *pytest]
        salida = correr(orden, RAIZ / p)
        n = lambda clave: int(m.group(1)) if (m := re.search(rf"(\d+) {clave}", salida)) else 0  # noqa: E731
        ficheros = sorted((RAIZ / p).rglob("test_*.py"))
        resumen.append({"proyecto": p, "pasan": n("passed"), "saltados": n("skipped"),
                        "ficheros": [{"nombre": f.relative_to(RAIZ).as_posix(), "que": descripcion(f)} for f in ficheros]})
        if medir:
            informe = correr([py, "-m", "coverage", "report", f"--data-file={cov}"], RAIZ / p)
            cobertura = {l.split()[0]: l.split()[-1] for l in informe.splitlines() if l.endswith("%")}
        print(f"{p:18s} {resumen[-1]['pasan']} pasan, {resumen[-1]['saltados']} saltados", flush=True)
    total = sum(r["pasan"] for r in resumen)
    (RAIZ / "docs").mkdir(exist_ok=True)
    (RAIZ / "docs/pruebas.json").write_text(json.dumps({"total": total, "proyectos": resumen, "cobertura_agente": cobertura},
                                                       ensure_ascii=False, indent=1), encoding="utf-8")
    md = ["# Pruebas · Tests", "", "Generado por `python pruebas.py`. Se ejecutan también en GitHub Actions en cada cambio.", "",
          f"**{total} tests pasan.**", "", "| Proyecto | Pasan | Saltados |", "|---|---|---|",
          *(f"| {r['proyecto']} | {r['pasan']} | {r['saltados']} |" for r in resumen), "", "## Qué comprueba cada fichero", "",
          "| Fichero | Qué comprueba |", "|---|---|",
          *(f"| [`{f['nombre']}`](../{f['nombre']}) | {f['que']} |" for r in resumen for f in r["ficheros"])]
    if cobertura:
        md += ["", "## Cobertura de líneas del agente", "", "| Módulo | Cobertura |", "|---|---|",
               *(f"| {k} | {v} |" for k, v in cobertura.items())]
    md += ["", "## Estrategia", "",
           "- **Unitarios**: funciones puras (métricas, troceado, validación de citas) con resultados calculados a mano.",
           "- **Flujo**: el agente completo con un modelo simulado, para probar decisiones sin depender de Ollama.",
           "- **Integración**: sobre las normas reales descargadas (se saltan si no hay índice).",
           "- **Seguridad**: el servidor local rechaza otros orígenes, hosts, ficheros ocultos y cuerpos grandes.",
           "- **Evaluación**: la calidad con modelos reales se mide aparte, en [EVALUACION.md](../agente/docs/EVALUACION.md)."]
    (RAIZ / "docs/PRUEBAS.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    print(f"total: {total}")


if __name__ == "__main__":
    main()
