# Decisiones de diseño y lo que falló

## 1. Trocear por artículo, no por tamaño fijo
La unidad que se cita en una norma es el artículo. Los largos se parten en trozos de unos 1300 caracteres en fin de
frase; cada trozo conserva artículo, título y página. Las páginas de índice se descartan: contienen todos los títulos y
ganaban las búsquedas. Comprobación: el RGPD da 99 artículos y el Reglamento de IA, 113 (test de integración).

## 2. Búsqueda híbrida dentro del sector
BM25 acierta con términos exactos y los vectores con paráfrasis; se fusionan por rango (RRF). Las cifras de cada una
por separado están en la [evaluación](EVALUACION.md).

## 3. Lectura aislada en vez de meter más fragmentos
Con 4096 tokens, 12 fragmentos llenan la ventana. Leer de uno en uno mantiene el pico bajo y permite verificar cada
cita. El precio es más llamadas.

## 4. Citar antes de juzgar (fallo encontrado)
Primera versión: el esquema JSON pedía `relevante` antes que `cita`. El modelo decidía antes de buscar la frase y
rechazaba fragmentos que sí contestaban. Medido en desarrollo: **8 de 15** aciertos, frente a 12 de 15 del RAG simple.
Cambio: el orden del esquema es `cita`, `dato`, `relevante`. En Ollama, el orden de las propiedades es el orden en que se
genera.

## 5. Redactar antes de decidir si hay respuesta (fallo encontrado)
Con la lectura arreglada seguían los fallos. La traza por etapas mostró la nota correcta guardada y la respuesta final
`sin_evidencia`: la última llamada tenía el mismo defecto. Cambio: `respuesta`, `notas`, `hay_respuesta`. Se aplicó
también a las líneas base, para comparar en igualdad.

## 6. Búsquedas cortas y artículos diversos
El plan devolvía a veces frases de cien palabras que empeoraban la búsqueda: ahora se piden palabras clave y se recortan
a 10. Un artículo largo podía ocupar todas las lecturas: máximo 2 trozos por artículo.

## 7. Evaluación reanudable
Una ejecución se interrumpió a mitad y se perdió. Cada pregunta se guarda al terminar y `--reanudar` continúa, siempre
que no hayan cambiado el código, las preguntas ni el modelo (huella).

## 8. Lo que dijo la medición completa
Con los cambios anteriores, las preguntas de desarrollo mejoran mucho, pero la mejora **no se traslada a las
reservadas**: ahí el agente no supera a las líneas base. La mayoría de sus fallos son de recuperación (el fragmento
correcto no llega a leerse), así que más trabajo en las instrucciones de lectura no ayudaría. Las cifras y la
conclusión, en la [evaluación](EVALUACION.md). No se ha ajustado nada mirando las reservadas después de esta medición.

También apareció un falso positivo del evaluador por patrón (un plazo correcto en número y equivocado en concepto),
descartado en la revisión manual: la métrica automática necesita un juez o patrones más estrictos.

## Pendiente
- Reordenador (reranker) antes de leer, para gastar menos lecturas.
- Juez automático además del patrón, y más preguntas por sector.
- Leer el trozo vecino cuando un artículo continúa.
