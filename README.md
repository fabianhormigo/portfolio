# Fabián Hormigo — AI engineer

[English](README.en.md)

## ▶ [Ver el portfolio](https://fabianhormigo.github.io/portfolio/)

Productos de IA y datos que se pueden usar y comprobar.

| Producto | Qué resuelve | Código |
|---|---|---|
| [Agente investigador de normativa](https://fabianhormigo.github.io/portfolio/index.html#agente) | Responde sobre 7 normas oficiales citando artículo y página | [`agente`](agente) |
| [Panel de contratación pública](https://fabianhormigo.github.io/portfolio/index.html#licitaciones) | Dónde está el dinero y dónde se compite poco | [`chat-analista`](chat-analista) |
| [Revisor de ficheros de sensores](https://fabianhormigo.github.io/portfolio/index.html#datos) | Huecos, valores congelados, picos e informe | [`portfolio.js`](portfolio.js) |
| [Herramientas para agentes (MCP)](https://fabianhormigo.github.io/portfolio/index.html#herramientas) | El modelo consulta y calcula con código probado | [`mcp-hub`](mcp-hub) |

Además: [`rag-real`](rag-real) (RAG con cita literal y evaluación) y [`etl-idempotente`](etl-idempotente) (integración sin duplicados).

## Calidad
[![tests](https://github.com/fabianhormigo/portfolio/actions/workflows/tests.yml/badge.svg)](https://github.com/fabianhormigo/portfolio/actions)

[Métricas en la web](https://fabianhormigo.github.io/portfolio/index.html#calidad) · [Evaluación del agente](agente/docs/EVALUACION.md) · [Decisiones y fallos](agente/docs/DECISIONES.md) · [Pruebas](docs/PRUEBAS.md) · `python pruebas.py`

## Ejecutarlo en tu equipo
Necesita [Ollama](https://ollama.com). Después abre http://127.0.0.1:8800/

```
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
python agente/ingesta.py
python vivo/servidor.py
```

Las demos de documentos y datos pueden ejecutarse también dentro del navegador (WebGPU), descargando un modelo pequeño.

Desarrollo asistido con IA.
