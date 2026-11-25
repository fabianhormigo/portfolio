"""RAG local con filtro duro por norma/versión, tres recuperadores y salida validada.

Embeddings (nomic-embed-text) y LLM (qwen2.5) en Ollama, índice vectorial en ChromaDB. Nada sale del equipo.
El modelo debe devolver JSON {hay_evidencia, respuesta, id, cita}; la cita se acepta solo si es literal.
"""
from __future__ import annotations

import json
import re
import urllib.request
import uuid

import chromadb

from lexico import Fragmento, Indice

OLLAMA = "http://127.0.0.1:11434/api/"
EMBED, LLM = "nomic-embed-text", "qwen2.5:7b-instruct"
ESQUEMA = {"type": "object", "required": ["hay_evidencia", "respuesta", "id", "cita"], "properties": {
    "hay_evidencia": {"type": "boolean"}, "respuesta": {"type": "string"},
    "id": {"type": "string"}, "cita": {"type": "string"}}}
ESQUEMA_V2 = {**ESQUEMA, "required": ["hay_evidencia", "id", "cita", "respuesta"]}
ESQUEMA_V2["properties"] = {c: ESQUEMA["properties"][c] for c in ESQUEMA_V2["required"]}   # citar antes de responder
OBLIGA = (" Si hay_evidencia es true, el campo respuesta es OBLIGATORIO: contesta la pregunta en una frase corta "
          "que incluya el dato.")
SISTEMA = ("Respondes preguntas técnicas SOLO con los fragmentos dados. Si ningún fragmento contiene la respuesta "
           "exacta a lo preguntado, devuelve hay_evidencia=false y deja respuesta, id y cita vacíos. Si la contiene, "
           "da una respuesta breve, el id del fragmento y una cita copiada literalmente de ese fragmento.")


def _post(ruta: str, cuerpo: dict, timeout: int = 600) -> dict:
    req = urllib.request.Request(OLLAMA + ruta, json.dumps(cuerpo).encode(), {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def embeber(textos: list[str], tipo: str) -> list[list[float]]:
    """nomic-embed-text distingue consulta y documento mediante prefijo."""
    return _post("embed", {"model": EMBED, "input": [f"search_{tipo}: {t}" for t in textos]})["embeddings"]


def fusion_rrf(listas: list[list[str]], k: int = 60) -> list[str]:
    """Reciprocal Rank Fusion: suma 1/(k + posición) de cada lista."""
    p: dict[str, float] = {}
    for lista in listas:
        for pos, i in enumerate(lista, 1):
            p[i] = p.get(i, 0.0) + 1 / (k + pos)
    return sorted(p, key=lambda i: (-p[i], i))


class Rag:
    def __init__(self, corpus: list[dict]):
        self.frags = {d["id"]: Fragmento(**d) for d in corpus}
        self.bm25 = Indice(list(self.frags.values()))
        # una colección por instancia: dos índices en el mismo proceso no deben mezclar documentos
        self.cliente = chromadb.EphemeralClient()
        self.col = self.cliente.create_collection(f"corpus-{uuid.uuid4().hex}", metadata={"hnsw:space": "cosine"})
        self.col.upsert(ids=list(self.frags), embeddings=embeber([d["texto"] for d in corpus], "document"),
                        metadatas=[{"norma": d["norma"], "version": d["version"]} for d in corpus])

    def cerrar(self) -> None:
        self.cliente.delete_collection(self.col.name)

    def recuperar(self, pregunta: str, norma: str, version: str, modo: str = "hibrido", k: int = 3) -> list[str]:
        n = len(self.frags)
        lexico = [f.id for f in self.bm25.buscar(pregunta, norma, version, n)]
        if modo == "bm25":
            return lexico[:k]
        filtro = {"$and": [{"norma": norma}, {"version": version}]}
        vector = self.col.query(query_embeddings=embeber([pregunta], "query"), n_results=n, where=filtro)["ids"][0]
        if modo == "vector":
            return vector[:k]
        if modo == "hibrido":
            return fusion_rrf([lexico, vector])[:k]
        raise ValueError(f"modo desconocido: {modo}")

    def generar(self, pregunta: str, ids: list[str], version_prompt: int = 2) -> dict:
        contexto = "\n".join(f"[{i}] {self.frags[i].texto}" for i in ids)
        r = _post("chat", {"model": LLM, "stream": False, "format": ESQUEMA_V2 if version_prompt == 2 else ESQUEMA,
                           "options": {"temperature": 0, "seed": 0},
                           "messages": [{"role": "system", "content": SISTEMA + (OBLIGA if version_prompt == 2 else "")},
                                        {"role": "user", "content": f"Fragmentos:\n{contexto}\n\nPregunta: {pregunta}"}]})
        return json.loads(r["message"]["content"])

    def validar(self, salida: dict, ids: list[str]) -> str:
        """'sin_evidencia' | 'valida' | 'rechazada' (respuesta vacía, cita no literal o fragmento no recuperado)."""
        if not salida["hay_evidencia"]:
            return "sin_evidencia"
        i = salida["id"].strip("[] ")
        if i not in ids or not salida["cita"].strip() or not salida.get("respuesta", "x").strip():
            return "rechazada"
        limpio = lambda s: re.sub(r"\s+", " ", s).strip(" .\"«»")  # noqa: E731
        return "valida" if limpio(salida["cita"]) in limpio(self.frags[i].texto) else "rechazada"

    def preguntar(self, pregunta: str, norma: str, version: str, version_prompt: int = 2) -> dict:
        ids = self.recuperar(pregunta, norma, version)
        salida = self.generar(pregunta, ids, version_prompt)
        return {**salida, "estado": self.validar(salida, ids), "recuperados": ids}
