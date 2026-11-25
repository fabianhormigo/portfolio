# Chat analista sobre un panel de datos

El modelo recibe el esquema y un **resumen ya calculado** del dato filtrado (no escribe SQL ni inventa cifras) y puede
pedir una acción en JSON (gráfico o filtro) que el panel valida y aplica. Proveedor intercambiable (`ia.py`): Ollama
local o cualquier API compatible con OpenAI, configurado por argumentos o variables de entorno.

- `chat.py`: prompt, reagregación con el filtro del usuario y separación robusta de texto y acción.
- `grabar.py`: preguntas reales a un modelo local sobre los agregados públicos del panel (`grabacion.json`). Los datos agregados no se incluyen en este repositorio.
- Límite: las respuestas de un modelo de 7B pueden equivocarse al comparar cifras; revísalas contra el panel.

## English
Analyst chat over a data dashboard: the model receives precomputed figures and may only request validated JSON actions (chart or filter). Swappable provider: local Ollama or any OpenAI-compatible API. `grabar.py` records real answers.
