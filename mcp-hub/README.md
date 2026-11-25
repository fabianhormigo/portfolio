# mcp-hub: herramientas reales para un agente (Model Context Protocol)

Servidor MCP en Python que da a un modelo (Claude u otro cliente MCP) herramientas deterministas, para que consulte y
calcule en vez de responder de memoria. Es la parte publicable de mi servidor de trabajo.

| Área | Herramientas | Qué hace |
|---|---|---|
| `biblioteca_*` | 5 | Recuperación BM25 sobre documentos propios **con cita** (documento y página o línea) |
| `incertidumbre_*` | 3 | GUM, Monte Carlo (JCGM 101), error de malla (GCI) y validación V&V 20 |
| `proyectos_*` | 5 | Explorador de código de solo lectura, encerrado en `PROYECTOS_ROOT` |

## Decisiones de diseño
- Cada herramienta declara si es **CONSULTA** o **EJECUCIÓN** (anotaciones MCP) y un test lo exige.
- Capas: `motores/` (cálculo puro) · `conocimiento/` (troceo y ranking) · `herramientas/` y `server.py` (interfaz fina).
- Las rutas fuera de la raíz permitida se rechazan.
- Cada llamada queda registrada y un **panel en vivo** muestra el grafo de piezas y su actividad.

## Uso
```
pip install -r requirements.txt
python demo_agente.py      # cliente MCP con guion fijo (sin LLM ni claves)
python -m pytest -q        # 18 tests
python panel/panel.py      # panel en http://127.0.0.1:8790
claude mcp add mcp-hub -- python /ruta/absoluta/server.py
```

## Límites
La recuperación es léxica (BM25), sin embeddings. Los documentos de `recursos/ejemplo/` son ficticios. No se incluyen
las normas con licencia ni las áreas de trabajo privadas del servidor original.

## English
A Model Context Protocol server in Python giving an agent deterministic tools: document retrieval with citations (BM25), uncertainty propagation (GUM, Monte Carlo, mesh GCI, V&V 20) and a read-only code explorer, plus a live panel. `python demo_agente.py` runs a scripted client (no LLM). Example documents are fictional.
