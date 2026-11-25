"""resultados/evaluacion.json -> docs/EVALUACION.md y docs/EVALUATION.md. Las cifras nunca se copian a mano.

    python agente/informe.py
"""
from __future__ import annotations

import json
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DOCS = AQUI / "docs"
MODOS = {"simple": ("RAG simple (4 fragmentos)", "Simple RAG (4 fragments)"),
         "volcado": ("Volcado (12 fragmentos)", "Stuffing (12 fragments)"), "agente": ("Agente con notas", "Agent with notes")}
CONJUNTOS = {"reservado": ("Preguntas reservadas", "Held-out questions"), "desarrollo": ("Preguntas de desarrollo", "Development questions")}
ETAPAS = {"recuperacion": ("recuperación", "retrieval"), "lectura": ("lectura", "reading"), "respuesta": ("respuesta", "answering")}


def pct(x: float | None) -> str:
    return "—" if x is None else f"{100 * x:.0f} %"


def tabla(cab: list[str], filas: list[list]) -> str:
    return "\n".join(["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab), *("| " + " | ".join(map(str, f)) + " |" for f in filas)])


def revision(d: dict) -> list[dict]:
    """Aciertos automáticos descartados a mano; solo valen para la ejecución con la misma huella."""
    f = AQUI / "resultados" / "revision.json"
    if not f.exists():
        return []
    r = json.loads(f.read_text(encoding="utf-8"))
    return r["descartados"] if r["huella"] == d["huella"] else []


def revisados(d: dict, conj: str, modo: str) -> int:
    """Aciertos tras la revisión manual."""
    fuera = {(x["n"], x["modo"]) for x in revision(d)}
    n = sum((x.get("n"), x["modo"]) in fuera and x.get("conjunto") == conj and x["modo"] == modo for x in d["detalle"])
    return d["resumen"][conj][modo]["correctas"] - n


def conclusion(d: dict, i: int) -> list[str]:
    """Frases calculadas a partir de las cifras: dicen lo mismo gane o pierda el agente."""
    T = lambda es, en: en if i else es  # noqa: E731
    r, d_ = d["resumen"]["reservado"], d["resumen"]["desarrollo"]
    n, nd = r["agente"]["con_respuesta"], d_["agente"]["con_respuesta"]
    a, s, v = (revisados(d, "reservado", m) for m in ("agente", "simple", "volcado"))
    da, ds, dv = (revisados(d, "desarrollo", m) for m in ("agente", "simple", "volcado"))
    mejor = max(s, v)
    juicio = (T("El agente es el mejor.", "The agent is best.") if a > mejor else
              T("El agente iguala a la mejor línea base.", "The agent ties the best baseline.") if a == mejor else
              T("El agente no supera a las líneas base: no se puede afirmar que acierte más.", "The agent does not beat the baselines: higher accuracy cannot be claimed."))
    out = [T(f"Reservadas: agente {a}/{n}, RAG simple {s}/{n}, volcado {v}/{n}. {juicio}", f"Held-out: agent {a}/{n}, simple RAG {s}/{n}, stuffing {v}/{n}. {juicio}"),
           T(f"Desarrollo: agente {da}/{nd}, RAG simple {ds}/{nd}, volcado {dv}/{nd}. Son las preguntas con las que se ajustó el agente.",
             f"Development: agent {da}/{nd}, simple RAG {ds}/{nd}, stuffing {dv}/{nd}. These are the questions the agent was tuned on.")]
    fallos = r["agente"]["fallos"]
    total = sum(fallos.values())
    if total:
        etapa = max(fallos, key=fallos.get)
        out.append(T(f"Cuello de botella en reservadas: la {ETAPAS[etapa][0]} ({fallos[etapa]} de {total} fallos).",
                     f"Held-out bottleneck: {ETAPAS[etapa][1]} ({fallos[etapa]} of {total} failures)."))
    ag, si, vo = r["agente"], r["simple"], r["volcado"]
    out.append(T(f"Lo que sí cumple: pico de {ag['max_entrada']} tokens de ventana frente a {vo['max_entrada']} del volcado y {si['max_entrada']} del RAG simple.",
                 f"What does hold: a {ag['max_entrada']}-token peak window versus {vo['max_entrada']} for stuffing and {si['max_entrada']} for simple RAG."))
    out.append(T(f"El precio: {ag['tokens_medios'] / si['tokens_medios']:.1f} veces más tokens y {ag['segundos_p50'] / si['segundos_p50']:.1f} veces más tiempo (p50) que el RAG simple.",
                 f"The price: {ag['tokens_medios'] / si['tokens_medios']:.1f}x the tokens and {ag['segundos_p50'] / si['segundos_p50']:.1f}x the time (p50) of simple RAG."))
    if ag["errores_confiados"]:
        out.append(T(f"Errores confiados del agente en reservadas: {ag['errores_confiados']}. Que la cita sea literal no garantiza que sea del artículo adecuado.",
                     f"Agent confident errors on held-out: {ag['errores_confiados']}. A verbatim quote does not guarantee it comes from the right article."))
    return out


def seccion(d: dict, conj: str, i: int) -> str:
    T = lambda es, en: en if i else es  # noqa: E731
    r = d["resumen"][conj]
    e = r["embudo"]
    gen = tabla([T("Método", "Method"), T("Aciertos", "Correct"), T("Cita el artículo correcto", "Cites the right article"),
                 T("Se niega bien", "Correct refusals"), T("Negativas falsas", "False refusals"), T("Errores confiados", "Confident errors")],
                [[MODOS[m][i], f"{r[m]['correctas']}/{r[m]['con_respuesta']}", pct(r[m]["cita_articulo"]),
                  f"{r[m]['negativas']}/{r[m]['sin_respuesta']}", r[m]["negativas_falsas"], r[m]["errores_confiados"]] for m in MODOS])
    coste = tabla([T("Método", "Method"), T("Pico de ventana", "Peak window"), T("Tokens por pregunta", "Tokens per question"),
                   T("Llamadas", "Calls"), "p50 (s)", "p95 (s)"],
                  [[MODOS[m][i], f"{r[m]['max_entrada']} / {d['num_ctx']}", r[m]["tokens_medios"], r[m]["llamadas_medias"],
                    r[m]["segundos_p50"], r[m]["segundos_p95"]] for m in MODOS])
    rec = tabla([T("Búsqueda", "Search"), "hit@1", "hit@4", "hit@6", "hit@12", "MRR"],
                [[m, *(pct(v[f"hit@{k}"]) for k in (1, 4, 6, 12)), f"{v['mrr']:.2f}"] for m, v in r["recuperacion"].items()])
    fallos = tabla([T("Método", "Method"), *(ETAPAS[x][i] for x in ETAPAS)], [[MODOS[m][i], *(r[m]["fallos"][x] for x in ETAPAS)] for m in MODOS])
    embudo = tabla([T("Etapa del agente", "Agent stage"), T("Preguntas que conservan la evidencia", "Questions keeping the evidence")],
                   [[T("Con respuesta en la norma", "Answerable"), e["preguntas"]],
                    [T("El fragmento correcto llega a leerse", "Right fragment gets read"), e["recuperada"]],
                    [T("Sobrevive como nota con cita literal", "Survives as a verbatim-quote note"), e["anotada"]],
                    [T("Respuesta final correcta", "Correct final answer"), e["correcta"]]])
    return f"""## {CONJUNTOS[conj][i]}

### {T("Calidad de la respuesta", "Answer quality")}
{gen}

### {T("Coste: ventana, tokens y latencia", "Cost: window, tokens and latency")}
{coste}

### {T("Recuperación (fragmento que contiene la respuesta)", "Retrieval (fragment containing the answer)")}
{rec}

### {T("Embudo del agente", "Agent funnel")}
{embudo}

{T("Lecturas", "Reads")}: {e["citas_leidas"]}. {T("Notas descartadas por cita no literal", "Notes dropped for non-verbatim quote")}: {e["citas_no_literales"]}.

### {T("Dónde se pierden los fallos", "Where failures happen")}
{fallos}
"""


def fallos_concretos(d: dict, i: int) -> str:
    T = lambda es, en: en if i else es  # noqa: E731
    f = [x for x in d["detalle"] if x["modo"] == "agente" and not x["correcta"]]
    if not f:
        return T("Sin fallos del agente en esta ejecución.", "No agent failures in this run.")
    return tabla([T("Pregunta (en español)", "Question (in Spanish)"), T("Referencia", "Reference"), T("Etapa", "Stage"), T("Qué respondió", "What it answered")],
                 [[x["q"], x["ref"] or "—", ETAPAS[x["etapa"]][i] if x["etapa"] else T("no se negó", "did not refuse"),
                   (x["respuesta"][:110].replace("|", "/").replace("\n", " ") or T("(sin respuesta)", "(no answer)")) if x["estado"] == "respaldada" else T("(se negó)", "(refused)")] for x in f])


def redactar(d: dict, i: int) -> str:
    T = lambda es, en: en if i else es  # noqa: E731
    return f"""# {T("Evaluación del agente investigador", "Research agent evaluation")}

{T("Generado por `informe.py` a partir de `resultados/evaluacion.json`.", "Generated by `informe.py` from `resultados/evaluacion.json`.")}

- {T("Fecha", "Date")}: {d["fecha"]} · {d["equipo"]}
- {T("Modelo", "Model")}: {d["modelo"]} (temperature 0, seed 0) · embeddings {d["embeddings"]}
- {T("Ventana", "Window")}: {d["num_ctx"]} tokens · {d["fragmentos"]} {T("fragmentos de 7 normas oficiales", "fragments from 7 official laws")}
- {T("Huella de código y preguntas", "Code and question fingerprint")}: `{d["huella"]}`

## {T("Conclusión", "Conclusion")}
{chr(10).join("- " + f for f in conclusion(d, i))}

## {T("Revisión manual", "Manual review")}
{T("Se leyeron las respuestas dadas por correctas. Las tablas muestran la puntuación automática; la conclusión usa la revisada.", "Answers scored as correct were read. Tables show automatic scores; the conclusion uses reviewed ones.")}
{chr(10).join(f"- {T('Pregunta', 'Question')} {x['n'] + 1}, {x['modo']}: {x.get('motivo_en' if i else 'motivo', x['motivo'])}" for x in revision(d)) or T("- Sin descartes.", "- Nothing discarded.")}

## {T("Cómo se mide", "How it is measured")}
{T('''- **Fragmento de oro**: pertenece al artículo de referencia y contiene el dato esperado (comprobado en el texto oficial).
- **Acierto**: respuesta respaldada por citas y que contiene el dato (expresión regular). Sin respuesta en la norma: negarse.
- **Error confiado**: se presenta como respaldada y es incorrecta.
- **Atribución de fallos**: primera etapa que perdió el fragmento de oro (recuperación, lectura o respuesta).
- **Reservadas**: no se usaron para ajustar instrucciones. Sus resultados de una ejecución intermedia sí llegaron a verse.''',
'''- **Gold fragment**: belongs to the reference article and contains the expected fact (checked in the official text).
- **Correct**: answer backed by quotes and containing the fact (regular expression). If the law lacks it: refuse.
- **Confident error**: presented as backed, but wrong.
- **Failure attribution**: first stage that lost the gold fragment (retrieval, reading or answering).
- **Held-out**: not used to tune prompts. Their results from an intermediate run were seen.''')}

{seccion(d, "reservado", i)}
{seccion(d, "desarrollo", i)}
## {T("Fallos concretos del agente", "Agent failures, one by one")}
{fallos_concretos(d, i)}

## {T("Límites de esta evaluación", "Limits of this evaluation")}
{T('''Pocas preguntas y un solo modelo: sirve para comparar variantes y localizar fallos, no como garantía estadística. La
corrección se comprueba por patrón, no por un juez humano ni por un modelo evaluador.''',
'''Few questions and a single model: useful to compare variants and locate failures, not a statistical guarantee. Correctness
is checked by pattern, not by a human or model judge.''')}
"""


def escribir(d: dict) -> None:
    DOCS.mkdir(exist_ok=True)
    (DOCS / "EVALUACION.md").write_text(redactar(d, 0), encoding="utf-8")
    (DOCS / "EVALUATION.md").write_text(redactar(d, 1), encoding="utf-8")


if __name__ == "__main__":
    escribir(json.loads((AQUI / "resultados" / "evaluacion.json").read_text(encoding="utf-8")))
