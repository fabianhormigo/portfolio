# Fabián Hormigo — AI engineer

[Español](README.md)

I solve problems with AI and automation, and prove it works.

| Problem | Solution | Code |
|---|---|---|
| AI answers from the wrong document version | RAG with filtering, verbatim quotes and evaluation | [`rag-real`](rag-real) |
| The model guesses when it should compute | MCP server with tested tools | [`mcp-hub`](mcp-hub) |
| Nobody can question the data | Chat with precomputed figures and validated actions | [`chat-analista`](chat-analista) |
| Integrations with duplicates and silent failures | Idempotent ETL with retries | [`etl-idempotente`](etl-idempotente) |

Built with AI assistance. Code and project docs are mostly in Spanish.

## Run it in the browser

The "Live" page can download a small model (Qwen2.5, ~290 or ~880 MB, from huggingface.co) and run it with WebGPU. It covers documents and data; the agent needs the local server.

## Run it live

Requires [Ollama](https://ollama.com). Then open http://127.0.0.1:8800/en/vivo.html

```
pip install -r requirements.txt
ollama pull qwen2.5:7b-instruct
ollama pull nomic-embed-text
python vivo/servidor.py
```
