# Fabián Hormigo — AI engineer

[Español](README.md)

## ▶ [View the portfolio](https://fabianhormigo.github.io/portfolio/en/)

AI and data products you can use and verify.

| Product | What it solves | Code |
|---|---|---|
| [Regulation research agent](https://fabianhormigo.github.io/portfolio/en/index.html#agente) | Answers over 7 official laws with article-and-page citations | [`agente`](agente) |
| [Public procurement dashboard](https://fabianhormigo.github.io/portfolio/en/index.html#licitaciones) | Where the money is and where competition is low | [`chat-analista`](chat-analista) |
| [Sensor file checker](https://fabianhormigo.github.io/portfolio/en/index.html#datos) | Gaps, frozen values, spikes and a report | [`portfolio.js`](portfolio.js) |
| [Tools for agents (MCP)](https://fabianhormigo.github.io/portfolio/en/index.html#herramientas) | The model looks up and computes with tested code | [`mcp-hub`](mcp-hub) |

Also: [`rag-real`](rag-real) (verbatim-quote RAG with evaluation) and [`etl-idempotente`](etl-idempotente) (duplicate-free integration).

## Quality
[![tests](https://github.com/fabianhormigo/portfolio/actions/workflows/tests.yml/badge.svg)](https://github.com/fabianhormigo/portfolio/actions)

[Metrics on the web](https://fabianhormigo.github.io/portfolio/en/index.html#calidad) · [Agent evaluation](agente/docs/EVALUATION.md) · [Design decisions (Spanish)](agente/docs/DECISIONES.md) · [Tests (Spanish)](docs/PRUEBAS.md) · `python pruebas.py`

## Run it on your machine
Requires [Ollama](https://ollama.com). Then open http://127.0.0.1:8800/en/index.html

```
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
python agente/ingesta.py
python vivo/servidor.py
```

The document and data demos can also run inside the browser (WebGPU) by downloading a small model.

Built with AI assistance.
