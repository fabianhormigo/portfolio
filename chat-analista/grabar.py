"""Hace preguntas reales al modelo local sobre los agregados públicos del panel y guarda las respuestas.
Uso: python grabar.py ruta/al/demo.html"""
import json
import sys
import time
from pathlib import Path

import chat
from ia import cargar_config_ia

PREGUNTAS = [("¿Qué sector tiene menos competencia?", {}),
             ("¿Dónde hay más oferta única?", {}),
             ("Gráfico de volumen por año", {}),
             ("Filtra a Construccion/Obra civil desde 2020", {})]

html = Path(sys.argv[1]).read_text(encoding="utf-8")
ini = html.index("const DATOS = ") + len("const DATOS = ")
chat.AG = json.JSONDecoder().raw_decode(html, ini)[0]
chat.CFG = cargar_config_ia(proveedor="ollama", modelo="qwen2.5:7b-instruct")
salida = []
for q, filtro in PREGUNTAS:
    t0 = time.time()
    r = chat._chat({"mensaje": q, "filtro": filtro})
    salida.append({"pregunta": q, **r, "segundos": round(time.time() - t0, 1)})
    print(json.dumps(salida[-1], ensure_ascii=False), flush=True)
resumen = chat._resumen_filtrado({})
print(json.dumps({"por_sector": resumen["por_sector"], "totales": resumen["totales"]}, ensure_ascii=False))
Path("grabacion.json").write_text(json.dumps(salida, ensure_ascii=False, indent=2), encoding="utf-8")
