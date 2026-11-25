# RAG local evaluado · Evaluated local RAG

**ES** · Recuperación con filtro duro por norma y versión (BM25, vectorial e híbrida RRF), generación en JSON con
Ollama, cita literal validada y banco de preguntas. Corpus **ficticio** de 36 fragmentos: mide el método,
no el rendimiento con documentos reales.

**EN** · Retrieval with a hard filter by standard and version (BM25, vector and RRF hybrid), JSON generation with Ollama,
verbatim-quote validation and a benchmark. **Fictional** 36-fragment corpus: it measures the method, not
performance on real documents. Corpus and questions are in Spanish.

## Resultados · Results

| Recuperación · Retrieval | hit@1 | hit@3 |
|---|---|---|
| bm25 | 48 % | 76 % |
| vector | 48 % | 90 % |
| hibrido | 62 % | 95 % |

Recuperación medida en las preguntas de desarrollo · measured on development questions.

| Preguntas · Questions | Prompt 1 | Prompt 2 | Negativas correctas · Correct refusals |
|---|---|---|---|
| Desarrollo · Development | 11/21 | 20/21 | 6/6 |
| Reservadas · Held-out | 8/10 | 10/10 | 3/3 |

El primer prompt citaba bien pero dejaba la respuesta vacía; el arreglo se hizo mirando solo las de desarrollo.
The first prompt quoted correctly but left answers empty; it was fixed by looking only at development questions.

## Uso · Usage
```
ollama pull nomic-embed-text
ollama pull qwen2.5:7b-instruct
pip install -r requirements.txt
python -m pytest -q      # sin modelos · no models needed
python evaluar.py        # evaluación completa · full evaluation
```
