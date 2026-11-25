# Pruebas · Tests

Generado por `python pruebas.py`. Se ejecutan también en GitHub Actions en cada cambio.

**98 tests pasan.**

| Proyecto | Pasan | Saltados |
|---|---|---|
| agente | 48 | 0 |
| vivo | 11 | 0 |
| rag-real | 9 | 0 |
| mcp-hub | 18 | 0 |
| chat-analista | 5 | 0 |
| etl-idempotente | 7 | 0 |

## Qué comprueba cada fichero

| Fichero | Qué comprueba |
|---|---|
| [`agente/test_agente.py`](../agente/test_agente.py) | Tests sin modelos ni PDF: troceado, verificación de citas, candidatos y validación de la respuesta. |
| [`agente/test_evaluar.py`](../agente/test_evaluar.py) | La evaluación y la ingesta con dobles de prueba: sin modelos ni PDF. |
| [`agente/test_flujo.py`](../agente/test_flujo.py) | El agente de principio a fin con un modelo simulado, y la búsqueda con un índice pequeño en disco. |
| [`agente/test_integracion.py`](../agente/test_integracion.py) | Integración con el índice real (normas descargadas). Se salta si no se ha ejecutado ingesta.py. |
| [`agente/test_metricas.py`](../agente/test_metricas.py) | Tests de las métricas y del informe, con casos de resultado conocido. |
| [`vivo/test_servidor.py`](../vivo/test_servidor.py) | Seguridad y contrato del servidor local, sin modelos: se levanta en un puerto libre. |
| [`rag-real/test_rag.py`](../rag-real/test_rag.py) | Tests sin modelos: corpus coherente, fusión, validación de citas y corrección de respuestas. |
| [`mcp-hub/tests/test_conocimiento.py`](../mcp-hub/tests/test_conocimiento.py) | RAG pequeño (capa 2): con textos inventados. |
| [`mcp-hub/tests/test_incertidumbre.py`](../mcp-hub/tests/test_incertidumbre.py) | Motor de incertidumbre (motores/nucleo_mcp/incertidumbre.py) frente a casos con solución exacta. |
| [`mcp-hub/tests/test_notacion.py`](../mcp-hub/tests/test_notacion.py) | La notación del MCP se cumple (ver NOTACION.md). Ejecutar: .venv\Scripts\python.exe tests\test_notacion.py |
| [`chat-analista/test_chat.py`](../chat-analista/test_chat.py) |  |
| [`etl-idempotente/test_crm_etl.py`](../etl-idempotente/test_crm_etl.py) |  |

## Cobertura de líneas del agente

| Módulo | Cobertura |
|---|---|
| agente.py | 97% |
| evaluar.py | 65% |
| informe.py | 97% |
| ingesta.py | 72% |
| metricas.py | 98% |
| TOTAL | 86% |

## Estrategia

- **Unitarios**: funciones puras (métricas, troceado, validación de citas) con resultados calculados a mano.
- **Flujo**: el agente completo con un modelo simulado, para probar decisiones sin depender de Ollama.
- **Integración**: sobre las normas reales descargadas (se saltan si no hay índice).
- **Seguridad**: el servidor local rechaza otros orígenes, hosts, ficheros ocultos y cuerpos grandes.
- **Evaluación**: la calidad con modelos reales se mide aparte, en [EVALUACION.md](../agente/docs/EVALUACION.md).
