# Fabián Hormigo — AI engineer

[English](README.en.md)

## ▶ [Ver el portfolio](https://fabianhormigo.github.io/portfolio/) · [Demos ejecutables](https://fabianhormigo.github.io/portfolio/vivo.html)

Resuelvo problemas con IA y automatización, y compruebo que funcionan.

| Problema | Solución | Código |
|---|---|---|
| La IA responde desde la versión equivocada | RAG con filtro, cita literal y evaluación | [`rag-real`](rag-real) |
| El modelo adivina cuando debería calcular | Servidor MCP con herramientas probadas | [`mcp-hub`](mcp-hub) |
| Nadie puede preguntar a los datos | Chat con cifras calculadas y acciones validadas | [`chat-analista`](chat-analista) |
| Integraciones con duplicados y fallos silenciosos | ETL idempotente con reintentos | [`etl-idempotente`](etl-idempotente) |

Desarrollo asistido con IA.

## Ejecutarlo en el navegador

En la página «En vivo» se puede descargar un modelo pequeño (Qwen2.5, ~290 o ~880 MB, desde huggingface.co) y ejecutarlo con WebGPU. Cubre documentos y datos; el agente necesita el servidor local.

## Ejecutarlo en vivo

Necesita [Ollama](https://ollama.com). Después: http://127.0.0.1:8800/vivo.html

```
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
python vivo/servidor.py
```
