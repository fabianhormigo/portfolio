"""Chat analista sobre datos agregados: el modelo responde con las cifras que se le pasan y puede pedir una acción
(gráfico o filtro) en JSON, que el panel aplica. Proveedor intercambiable (ia.py): Ollama u OpenAI-compatible."""
import json
import re
import unicodedata
from collections import defaultdict

from ia import generar_texto

# los rellena quien usa el módulo: datos agregados y configuración del modelo (None = chat desactivado)
AG: dict = {}
CFG = None

SISTEMA = """Eres el analista de datos integrado en un panel de licitaciones públicas
españolas (PLACSP). Conoces EXACTAMENTE estos datos y su estructura; no inventes
cifras: usa solo las que te paso. Responde en español, breve y concreto.

Puedes además EJECUTAR una acción sobre el panel añadiendo AL FINAL de tu respuesta
un bloque ```json con la forma {"accion": {...}}. Tipos de acción:
- Gráfico: {"accion":{"tipo":"chart","chart":"hbar|bar|line","dataset":"por_sector|por_anio|por_region","medida":"volumen|n|competencia|pct_unico|baja_media","titulo":"..."}}
- Filtro:  {"accion":{"tipo":"filter","anio_min":2020,"anio_max":2025,"sectores":["..."],"region":"..."}}
Usa nombres de sector EXACTOS de los que te paso. Si el usuario solo pregunta, no
pongas acción. Si pide "gráfico/pinta/muestra" usa chart; si pide "filtra/limita" usa filter.

ESQUEMA:
__ESQUEMA__

RESUMEN DEL DATO (según el filtro actual del usuario):
__RESUMEN__
"""


def _resumen_filtrado(filtro):
    """Reagrega la tabla de hechos con el filtro del cliente para dar cifras
    reales a la IA (por sector y por año) + totales."""
    amin = str(filtro.get("anioMin") or "0")
    amax = str(filtro.get("anioMax") or "9999")
    secs = set(filtro.get("sectores") or [])
    region = filtro.get("region") or "(todas)"
    por_sector = defaultdict(lambda: {"n": 0, "vol": 0.0, "of_sum": 0.0, "of_cnt": 0, "unico": 0, "baja_sum": 0.0, "baja_cnt": 0})
    por_anio = defaultdict(lambda: {"n": 0, "vol": 0.0})
    # por_sector: tabla EXPLOTADA (respeta filtro de sector)
    for h in AG["hechos"]:
        if h["anio"] == "?" or h["anio"] < amin or h["anio"] > amax:
            continue
        if secs and h["sector"] not in secs:
            continue
        if region != "(todas)" and h["region"] != region:
            continue
        s = por_sector[h["sector"]]
        s["n"] += h["n"]; s["vol"] += h["vol"]; s["of_sum"] += h["of_sum"]
        s["of_cnt"] += h["of_cnt"]; s["unico"] += h["unico"]
        s["baja_sum"] += h["baja_sum"]; s["baja_cnt"] += h["baja_cnt"]
    # por_anio y totales: tabla SIN explotar (cifras exactas, ignora sector)
    for h in AG.get("hechos_tot", []):
        if h["anio"] == "?" or h["anio"] < amin or h["anio"] > amax:
            continue
        if region != "(todas)" and h["region"] != region:
            continue
        a = por_anio[h["anio"]]; a["n"] += h["n"]; a["vol"] += h["vol"]

    def _sec(s, d):
        return {"sector": s, "n": d["n"], "volumen_eur": round(d["vol"]),
                "competencia_media": round(d["of_sum"] / d["of_cnt"], 1) if d["of_cnt"] else None,
                "pct_oferta_unica": round(100 * d["unico"] / d["of_cnt"], 1) if d["of_cnt"] else None,
                "baja_media_pct": round(d["baja_sum"] / d["baja_cnt"], 1) if d["baja_cnt"] else None}
    sectores = sorted((_sec(s, d) for s, d in por_sector.items()), key=lambda x: -x["n"])
    anios = [{"anio": a, "n": d["n"], "volumen_eur": round(d["vol"])} for a, d in sorted(por_anio.items())]
    total_n = sum(d["n"] for d in por_anio.values())          # sin explotar (exacto)
    total_vol = round(sum(d["vol"] for d in por_anio.values()))
    return {"filtro": {"anio_min": amin, "anio_max": amax, "region": region,
                       "sectores": sorted(secs) if secs else "todos"},
            "totales": {"licitaciones": total_n, "volumen_eur": total_vol},
            "por_sector": sectores, "por_anio": anios}


def _buscar_json(txt):
    """Encuentra el PRIMER objeto JSON balanceado que contenga 'accion' o 'tipo'
    y parsee, esté donde esté (con o sin fence ```). Devuelve (obj, ini, fin)."""
    for m in re.finditer(r"\{", txt):
        i = m.start()
        depth = 0
        for j in range(i, len(txt)):
            ch = txt[j]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    frag = txt[i:j + 1]
                    if '"accion"' in frag or '"tipo"' in frag:
                        try:
                            return json.loads(frag), i, j + 1
                        except Exception:
                            pass
                    break  # este { no cierra en objeto útil; probar el siguiente
    return None, None, None


def _partir_respuesta(txt):
    """Separa la prosa de la acción JSON (tolerante a que venga sin fence)."""
    obj, i, j = _buscar_json(txt)
    accion = None
    if obj is not None:
        accion = obj.get("accion", obj if obj.get("tipo") else None)
        # quita el JSON y los restos de fence (```json ... ```)
        txt = (txt[:i] + txt[j:])
    txt = re.sub(r"```(?:json)?", "", txt).strip()
    return txt, accion


def _plano(s):
    return "".join(c for c in unicodedata.normalize("NFKD", str(s).lower()) if not unicodedata.combining(c)).strip()


def validar_accion(accion, sectores_validos):
    """Los nombres de sector deben existir: se corrigen tildes y mayúsculas; si alguno no existe, no hay acción."""
    if not accion or not accion.get("sectores"):
        return accion
    mapa = {_plano(s): s for s in sectores_validos}
    nombres = [mapa.get(_plano(s)) for s in accion["sectores"]]
    return None if None in nombres else {**accion, "sectores": nombres}


def _chat(payload):
    if CFG is None:
        return {"respuesta": "El chat IA está desactivado (--no-ia). Los datos y filtros del panel siguen funcionando.", "accion": None}
    resumen = _resumen_filtrado(payload.get("filtro") or {})
    sistema = (SISTEMA
               .replace("__ESQUEMA__", json.dumps(AG["esquema"], ensure_ascii=False))
               .replace("__RESUMEN__", json.dumps(resumen, ensure_ascii=False)))
    historial = payload.get("historial") or []
    try:
        txt = generar_texto(CFG, sistema, payload.get("mensaje") or "", historial=historial, temperature=0.2)
    except Exception as e:
        return {"respuesta": f"No pude consultar el modelo ({type(e).__name__}). Revisa que Ollama esté arrancado.", "accion": None}
    prosa, accion = _partir_respuesta(txt)
    while True:   # el modelo a veces repite el bloque: se limpia del texto
        prosa, otra = _partir_respuesta(prosa)
        if otra is None:
            break
    validos = {h["sector"] for h in AG.get("hechos", [])}
    pedida, accion = accion, validar_accion(accion, validos)
    if pedida and accion is None:
        prosa = (prosa + " No he aplicado la acción: pide un sector que no existe.").strip()
    return {"respuesta": prosa or "(sin texto)", "accion": accion}
