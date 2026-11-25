# Evaluación del agente investigador

Generado por `informe.py` a partir de `resultados/evaluacion.json`.

- Fecha: 2026-11-25 · Windows AMD64
- Modelo: qwen2.5:7b-instruct (temperature 0, seed 0) · embeddings nomic-embed-text
- Ventana: 4096 tokens · 2192 fragmentos de 7 normas oficiales
- Huella de código y preguntas: `c2e46f523ef91335`

## Conclusión
- Reservadas: agente 4/8, RAG simple 4/8, volcado 6/8. El agente no supera a las líneas base: no se puede afirmar que acierte más.
- Desarrollo: agente 12/15, RAG simple 10/15, volcado 10/15. Son las preguntas con las que se ajustó el agente.
- Cuello de botella en reservadas: la recuperación (3 de 4 fallos).
- Lo que sí cumple: pico de 525 tokens de ventana frente a 3703 del volcado y 1455 del RAG simple.
- El precio: 3.3 veces más tokens y 4.7 veces más tiempo (p50) que el RAG simple.
- Errores confiados del agente en reservadas: 3. Que la cita sea literal no garantiza que sea del artículo adecuado.

## Revisión manual
Se leyeron las respuestas dadas por correctas. Las tablas muestran la puntuación automática; la conclusión usa la revisada.
- Pregunta 3, agente: Da el plazo para aprobar la certificación (30 días desde la entrega), no el de pago (30 días desde la aprobación). La cifra coincide por casualidad y el patrón la dio por buena.

## Cómo se mide
- **Fragmento de oro**: pertenece al artículo de referencia y contiene el dato esperado (comprobado en el texto oficial).
- **Acierto**: respuesta respaldada por citas y que contiene el dato (expresión regular). Sin respuesta en la norma: negarse.
- **Error confiado**: se presenta como respaldada y es incorrecta.
- **Atribución de fallos**: primera etapa que perdió el fragmento de oro (recuperación, lectura o respuesta).
- **Reservadas**: no se usaron para ajustar instrucciones. Sus resultados de una ejecución intermedia sí llegaron a verse.

## Preguntas reservadas

### Calidad de la respuesta
| Método | Aciertos | Cita el artículo correcto | Se niega bien | Negativas falsas | Errores confiados |
|---|---|---|---|---|---|
| RAG simple (4 fragmentos) | 4/8 | 50 % | 2/2 | 2 | 2 |
| Volcado (12 fragmentos) | 6/8 | 62 % | 2/2 | 1 | 1 |
| Agente con notas | 4/8 | 50 % | 2/2 | 1 | 3 |

### Coste: ventana, tokens y latencia
| Método | Pico de ventana | Tokens por pregunta | Llamadas | p50 (s) | p95 (s) |
|---|---|---|---|---|---|
| RAG simple (4 fragmentos) | 1455 / 4096 | 1236 | 1.0 | 4.2 | 5.4 |
| Volcado (12 fragmentos) | 3703 / 4096 | 3296 | 1.0 | 13.9 | 17.4 |
| Agente con notas | 525 / 4096 | 4104 | 8.7 | 19.9 | 35.2 |

### Recuperación (fragmento que contiene la respuesta)
| Búsqueda | hit@1 | hit@4 | hit@6 | hit@12 | MRR |
|---|---|---|---|---|---|
| bm25 | 25 % | 62 % | 62 % | 75 % | 0.38 |
| vector | 12 % | 62 % | 75 % | 88 % | 0.36 |
| hibrido | 50 % | 62 % | 75 % | 75 % | 0.56 |

### Embudo del agente
| Etapa del agente | Preguntas que conservan la evidencia |
|---|---|
| Con respuesta en la norma | 8 |
| El fragmento correcto llega a leerse | 5 |
| Sobrevive como nota con cita literal | 4 |
| Respuesta final correcta | 4 |

Lecturas: 70. Notas descartadas por cita no literal: 2.

### Dónde se pierden los fallos
| Método | recuperación | lectura | respuesta |
|---|---|---|---|
| RAG simple (4 fragmentos) | 3 | 0 | 1 |
| Volcado (12 fragmentos) | 1 | 0 | 1 |
| Agente con notas | 3 | 1 | 0 |

## Preguntas de desarrollo

### Calidad de la respuesta
| Método | Aciertos | Cita el artículo correcto | Se niega bien | Negativas falsas | Errores confiados |
|---|---|---|---|---|---|
| RAG simple (4 fragmentos) | 10/15 | 67 % | 3/3 | 1 | 4 |
| Volcado (12 fragmentos) | 10/15 | 67 % | 3/3 | 2 | 3 |
| Agente con notas | 13/15 | 87 % | 3/3 | 2 | 0 |

### Coste: ventana, tokens y latencia
| Método | Pico de ventana | Tokens por pregunta | Llamadas | p50 (s) | p95 (s) |
|---|---|---|---|---|---|
| RAG simple (4 fragmentos) | 1817 / 4096 | 1258 | 1.0 | 4.2 | 7.3 |
| Volcado (12 fragmentos) | 3878 / 4096 | 3216 | 1.0 | 14.0 | 20.7 |
| Agente con notas | 736 / 4096 | 4281 | 8.7 | 23.0 | 50.1 |

### Recuperación (fragmento que contiene la respuesta)
| Búsqueda | hit@1 | hit@4 | hit@6 | hit@12 | MRR |
|---|---|---|---|---|---|
| bm25 | 47 % | 67 % | 80 % | 80 % | 0.58 |
| vector | 53 % | 87 % | 87 % | 87 % | 0.66 |
| hibrido | 53 % | 80 % | 87 % | 87 % | 0.68 |

### Embudo del agente
| Etapa del agente | Preguntas que conservan la evidencia |
|---|---|
| Con respuesta en la norma | 15 |
| El fragmento correcto llega a leerse | 13 |
| Sobrevive como nota con cita literal | 13 |
| Respuesta final correcta | 13 |

Lecturas: 125. Notas descartadas por cita no literal: 2.

### Dónde se pierden los fallos
| Método | recuperación | lectura | respuesta |
|---|---|---|---|
| RAG simple (4 fragmentos) | 3 | 0 | 2 |
| Volcado (12 fragmentos) | 2 | 0 | 3 |
| Agente con notas | 2 | 0 | 0 |

## Fallos concretos del agente
| Pregunta (en español) | Referencia | Etapa | Qué respondió |
|---|---|---|---|
| ¿Cuál es la multa máxima por incumplir la prohibición de prácticas de IA? | art. 99 | recuperación | (se negó) |
| ¿Desde qué fecha se aplican las prohibiciones y la alfabetización en materia de IA? | art. 113 | recuperación | (se negó) |
| ¿Cuál es el plazo máximo de duración de un contrato de servicios de prestación sucesiva? | art. 29 | recuperación | El plazo máximo de duración de un contrato de servicios de prestación sucesiva es de nueve meses. |
| ¿Cuál es la multa máxima por las infracciones más graves en protección de datos? | art. 83 | recuperación | La multa máxima por las infracciones más graves en protección de datos es de 10 000 000 EUR o, para una empres |
| ¿En qué plazo hay que contestar a una persona que ejerce sus derechos sobre sus datos? | art. 12 | recuperación | (se negó) |
| ¿Qué aislamiento mínimo a ruido aéreo se exige a cada cerramiento de una medianería entre dos edificios? | apdo. 2.1.1 | lectura | El aislamiento acústico a ruido aéreo, DnT,A, no será menor que 50 dBA. |

## Límites de esta evaluación
Pocas preguntas y un solo modelo: sirve para comparar variantes y localizar fallos, no como garantía estadística. La
corrección se comprueba por patrón, no por un juez humano ni por un modelo evaluador.
