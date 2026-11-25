"""Portafolio en vivo: sirve la web y conecta las demos con modelos de Ollama en este equipo.

    python vivo/servidor.py            -> http://127.0.0.1:8800/vivo.html
    python vivo/servidor.py --grabar   -> guarda ejecuciones reales para reproducirlas en la web pública

Solo escucha en 127.0.0.1. Variable MCP_PYTHON: intérprete con el paquete `mcp` (por defecto, el actual).
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import threading
import time
from collections.abc import Iterator
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(RAIZ / "rag-real"), str(RAIZ / "chat-analista")]

import chat  # noqa: E402
import rag as R  # noqa: E402
from datos import CORPUS  # noqa: E402
from ia import cargar_config_ia  # noqa: E402

MODELOS = ("qwen2.5:7b-instruct", "llama3.1:8b", "mistral:7b", "phi3:mini")  # los probados con estas demos
HERRAMIENTAS = ("biblioteca_listar", "biblioteca_consultar", "incertidumbre_propagar", "incertidumbre_estimar_malla",
                "incertidumbre_validar")  # solo consulta: el agente no escribe ni lee código
MAX_CUERPO = 60_000
GRABACIONES = RAIZ / "vivo" / "grabaciones.json"


def ms(t0: float) -> int:
    return round(1000 * (time.perf_counter() - t0))


def instalados() -> list[str]:
    import urllib.request
    try:
        with urllib.request.urlopen(R.OLLAMA + "tags", timeout=5) as r:
            nombres = [m["name"] for m in json.load(r)["models"]]
    except OSError:
        return []
    return nombres


def ollama_stream(cuerpo: dict) -> Iterator[dict]:
    import urllib.request
    req = urllib.request.Request(R.OLLAMA + "chat", json.dumps({**cuerpo, "stream": True}).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        for linea in r:
            yield json.loads(linea)


# ───────────────────────── 1 · RAG con cita validada
def trocear(texto: str) -> list[dict]:
    partes = [p.strip() for p in texto[:20_000].split("\n") if len(p.strip()) > 15]
    return [{"id": f"P{i}", "norma": "DOC", "version": "1", "fecha": "", "seccion": str(i), "texto": p}
            for i, p in enumerate(partes[:60], 1)]


def demo_rag(q: dict) -> Iterator[dict]:
    pregunta = str(q["pregunta"])[:500]
    t0 = time.perf_counter()
    if q.get("documento"):
        corpus, norma, version = trocear(str(q["documento"])), "DOC", "1"
        if not corpus:
            raise ValueError("El documento necesita al menos una línea de más de 15 caracteres.")
    else:
        corpus, norma, version = CORPUS, str(q["norma"]), str(q["version"])
    indice = R.Rag(corpus)
    try:
        candidatos = sum(d["norma"] == norma and d["version"] == version for d in corpus)
        if not candidatos:
            raise ValueError(f"No hay fragmentos de {norma} {version}.")
        yield {"paso": "filtro", "total": len(corpus), "candidatos": candidatos, "norma": norma, "version": version, "ms": ms(t0)}
        t0 = time.perf_counter()
        listas = {m: indice.recuperar(pregunta, norma, version, m, len(corpus)) for m in ("bm25", "vector", "hibrido")}
        ids = listas["hibrido"][:3]
        pos = lambda m, i: listas[m].index(i) + 1 if i in listas[m] else None  # noqa: E731
        yield {"paso": "recuperar", "ms": ms(t0), "fragmentos": [
            {"id": i, "texto": indice.frags[i].texto, "bm25": pos("bm25", i), "vector": pos("vector", i)} for i in ids]}
        t0 = time.perf_counter()
        idioma = " Answer in English; copy the quote verbatim in its original language." if q.get("idioma") == "en" else ""
        contexto = "\n".join(f"[{i}] {indice.frags[i].texto}" for i in ids)
        bruto = ""
        for trozo in ollama_stream({"model": q["modelo"], "format": R.ESQUEMA_V2, "options": {"temperature": 0, "seed": 0},
                                    "messages": [{"role": "system", "content": R.SISTEMA + R.OBLIGA + idioma},
                                                 {"role": "user", "content": f"Fragmentos:\n{contexto}\n\nPregunta: {pregunta}"}]}):
            t = trozo.get("message", {}).get("content", "")
            bruto += t
            if t:
                yield {"paso": "token", "t": t}
        yield {"paso": "generar", "ms": ms(t0), "modelo": q["modelo"]}
        t0 = time.perf_counter()
        salida = json.loads(bruto)
        yield {"paso": "validar", "estado": indice.validar(salida, ids), "salida": salida, "ms": ms(t0)}
    finally:
        indice.cerrar()


# ───────────────────────── 2 · agente que usa un servidor MCP real
class Mcp:
    """Cliente MCP mínimo por stdio (JSON-RPC, un mensaje por línea)."""

    def __init__(self):
        carpeta = RAIZ / "mcp-hub"
        self.p = subprocess.Popen([os.environ.get("MCP_PYTHON", sys.executable), "-B", "server.py"], cwd=carpeta,
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                                  text=True, encoding="utf-8")
        self.n, self.cerrojo = 0, threading.Lock()
        self.rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {},
                                "clientInfo": {"name": "portafolio", "version": "1"}})
        self._enviar({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.llamar("biblioteca_indexar", {})
        self.herramientas = [t for t in self.rpc("tools/list", {})["tools"] if t["name"] in HERRAMIENTAS]

    def _enviar(self, m: dict) -> None:
        self.p.stdin.write(json.dumps(m) + "\n")
        self.p.stdin.flush()

    def rpc(self, metodo: str, params: dict) -> dict:
        with self.cerrojo:
            self.n += 1
            self._enviar({"jsonrpc": "2.0", "id": self.n, "method": metodo, "params": params})
            while linea := self.p.stdout.readline():
                m = json.loads(linea)
                if m.get("id") == self.n:
                    if "error" in m:
                        raise RuntimeError(m["error"]["message"])
                    return m["result"]
        raise RuntimeError("El servidor MCP se ha cerrado. Revisa MCP_PYTHON (necesita `pip install mcp numpy`).")

    def llamar(self, nombre: str, args: dict) -> tuple[str, bool]:
        r = self.rpc("tools/call", {"name": nombre, "arguments": args})
        return "\n".join(c.get("text", "") for c in r["content"]), bool(r.get("isError"))


_mcp: Mcp | None = None
_mcp_cerrojo = threading.Lock()


def mcp() -> Mcp:
    global _mcp
    with _mcp_cerrojo:
        if _mcp is None or _mcp.p.poll() is not None:
            _mcp = Mcp()
    return _mcp


def resumir_resultado(texto: str) -> str:
    """Quita el histograma de Monte Carlo: es largo y no aporta al modelo."""
    try:
        d = json.loads(texto)
    except json.JSONDecodeError:
        return texto[:2000]
    if isinstance(d, dict) and isinstance(d.get("monte_carlo"), dict):
        d["monte_carlo"].pop("histograma", None)
        if "gum" in d:   # frase ya redactada por código: el modelo la copia en vez de etiquetar cifras por su cuenta
            g, mc = d["gum"], d["monte_carlo"]
            valido = d.get("gum_valido", {}).get("valido")
            nota = "" if valido else " La aproximación lineal (GUM) no supera el contraste: usar el intervalo Monte Carlo."
            d = {"frase_para_el_usuario": f"Resultado y = {g['y']:.6g}; incertidumbre expandida al 95 % U = {g['U']:.2g} "
                 f"(típica u = {g['u']:.2g}); intervalo Monte Carlo al 95 % [{mc['intervalo'][0]:.5g}, "
                 f"{mc['intervalo'][1]:.5g}].{nota}", **d}
    return json.dumps(d, ensure_ascii=False)[:2000]


def demo_agente(q: dict) -> Iterator[dict]:
    pregunta = str(q["pregunta"])[:800]
    t0 = time.perf_counter()
    m = mcp()
    yield {"paso": "herramientas", "lista": [t["name"] for t in m.herramientas], "ms": ms(t0)}
    tools = [{"type": "function", "function": {"name": t["name"], "description": t.get("description", ""),
                                               "parameters": t["inputSchema"]}} for t in m.herramientas]
    idioma = "Answer in English." if q.get("idioma") == "en" else "Responde en español."
    mensajes = [{"role": "system", "content":
                 "Eres un asistente técnico. Para documentación usa biblioteca_consultar y para incertidumbres usa las "
                 "herramientas incertidumbre_*; no calcules de memoria. Responde breve, solo con lo que devuelvan las "
                 "herramientas, y cita el documento si lo hay. En incertidumbre, u es la típica y U la expandida (95 %): "
                 "si el resultado trae frase_para_el_usuario, cópiala tal cual (traducida si hace falta), sin LaTeX. " + idioma},
                {"role": "user", "content": pregunta}]
    for _ in range(5):
        t0 = time.perf_counter()
        r = R._post("chat", {"model": q["modelo"], "messages": mensajes, "tools": tools, "stream": False,
                             "options": {"temperature": 0, "seed": 0}})["message"]
        llamadas = r.get("tool_calls") or []
        yield {"paso": "pensar", "ms": ms(t0), "modelo": q["modelo"], "pide": len(llamadas)}
        if not llamadas:
            yield {"paso": "respuesta", "texto": r.get("content", "").strip() or "(sin texto)"}
            return
        mensajes.append(r)
        for c in llamadas:
            nombre, args = c["function"]["name"], c["function"].get("arguments") or {}
            yield {"paso": "llamada", "nombre": nombre, "args": args}
            t0 = time.perf_counter()
            if nombre in HERRAMIENTAS:
                texto, error = m.llamar(nombre, args)
            else:
                texto, error = "Herramienta no disponible.", True
            texto = resumir_resultado(texto)
            yield {"paso": "resultado", "nombre": nombre, "texto": texto, "error": error, "ms": ms(t0)}
            mensajes.append({"role": "tool", "tool_name": nombre, "content": texto})
    yield {"paso": "respuesta", "texto": "El agente ha alcanzado el máximo de 5 pasos sin terminar."}


# ───────────────────────── 3 · preguntas sobre datos agregados
MEDIDAS = {"volumen": "volumen_eur", "volumen_eur": "volumen_eur", "n": "n", "competencia": "competencia_media",
           "competencia_media": "competencia_media", "pct_unico": "pct_oferta_unica",
           "pct_oferta_unica": "pct_oferta_unica", "baja_media": "baja_media_pct", "baja_media_pct": "baja_media_pct"}


def demo_datos(q: dict) -> Iterator[dict]:
    if not chat.AG:
        chat.AG = json.loads((RAIZ / "vivo" / "datos_agregados.json").read_text(encoding="utf-8"))
    pregunta = str(q["pregunta"])[:500]
    t0 = time.perf_counter()
    res = chat._resumen_filtrado({})
    yield {"paso": "calcular", "ms": ms(t0), "licitaciones": res["totales"]["licitaciones"], "sectores": len(res["por_sector"])}
    t0 = time.perf_counter()
    chat.CFG = cargar_config_ia(proveedor="ollama", modelo=q["modelo"])
    r = chat._chat({"mensaje": pregunta + (" (answer in English)" if q.get("idioma") == "en" else ""), "filtro": {}})
    yield {"paso": "generar", "ms": ms(t0), "modelo": q["modelo"]}
    a, grafico = r.get("accion"), None
    if a and a.get("tipo") == "chart":
        clave = MEDIDAS.get(a.get("medida"))
        filas = res.get(a.get("dataset"), [])
        eje = "sector" if a.get("dataset") == "por_sector" else "anio"
        datos = [[f[eje], f[clave]] for f in filas if clave and f.get(clave) is not None]
        if eje == "sector":
            datos.sort(key=lambda x: -x[1])
        grafico = {"titulo": a.get("titulo", ""), "medida": clave, "datos": datos} if datos else None
    yield {"paso": "respuesta", "texto": r["respuesta"], "accion": a, "grafico": grafico}


DEMOS = {"rag": demo_rag, "agente": demo_agente, "datos": demo_datos}


def ejecutar(nombre: str, q: dict) -> Iterator[dict]:
    disponibles = [m for m in MODELOS if m in instalados()]
    if not disponibles:
        raise RuntimeError("No encuentro Ollama o ningún modelo compatible. Ejecuta: ollama pull qwen2.5:7b-instruct")
    q = {**q, "modelo": q.get("modelo") if q.get("modelo") in disponibles else disponibles[0]}
    yield from DEMOS[nombre](q)


class Web(SimpleHTTPRequestHandler):
    def __init__(self, *a, **k):
        super().__init__(*a, directory=str(RAIZ), **k)

    def log_message(self, *a):
        pass

    def _local(self) -> bool:
        """Rechaza peticiones con otro Host u Origin (DNS rebinding y llamadas desde otras webs)."""
        puerto = self.server.server_address[1]
        validos = {f"127.0.0.1:{puerto}", f"localhost:{puerto}"}
        origen = self.headers.get("Origin")
        return self.headers.get("Host") in validos and (origen is None or origen.removeprefix("http://") in validos)

    def _json(self, codigo: int, obj) -> None:
        b = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def send_head(self):
        if not self._local() or any(p.startswith(".") for p in self.path.split("?")[0].split("/")):
            self.send_error(403)
            return None
        return super().send_head()

    def do_GET(self):
        if self.path.split("?")[0] == "/api/estado" and self._local():
            return self._json(200, {"modelos": [m for m in MODELOS if m in instalados()]})
        return super().do_GET()

    def do_POST(self):
        nombre = self.path.removeprefix("/api/")
        largo = int(self.headers.get("Content-Length") or 0)
        if (not self._local() or nombre not in DEMOS or not 0 < largo <= MAX_CUERPO
                or "application/json" not in (self.headers.get("Content-Type") or "")):
            return self._json(400, {"error": "petición no válida"})
        q = json.loads(self.rfile.read(largo))
        self.send_response(200)
        self.send_header("Content-Type", "application/x-ndjson; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            for ev in ejecutar(nombre, q):
                self.wfile.write((json.dumps(ev, ensure_ascii=False) + "\n").encode())
                self.wfile.flush()
        except (BrokenPipeError, ConnectionError):
            return
        except Exception as e:  # frontera del servidor: el error se muestra en la web, no se oculta
            print(f"ERROR en {nombre}: {type(e).__name__}: {e}", file=sys.stderr)
            self.wfile.write((json.dumps({"paso": "error", "texto": f"{type(e).__name__}: {e}"}) + "\n").encode())


# ───────────────────────── grabaciones para la web pública
DOC = ("El sensor de inclinación se calibra cada doce meses o después de un golpe.\n"
       "Las lecturas se toman en dos posiciones opuestas en cada profundidad.\n"
       "El equipo se almacena entre 5 y 35 grados, dentro de su maleta.\n"
       "El informe indica el desplazamiento acumulado con su incertidumbre.")
EJEMPLOS = {
    "rag": [{"pregunta": "¿Cuánto hormigón debe tapar como mínimo el acero?", "norma": "NT-HORMIGON", "version": "2025"},
            {"pregunta": "¿Cuánto hormigón debe tapar como mínimo el acero?", "norma": "NT-HORMIGON", "version": "2022"},
            {"pregunta": "¿Cuánto cuesta calibrar el sensor?", "norma": "NT-SENSOR", "version": "2025"}],
    "agente": [{"pregunta": "¿Cada cuánto se calibra el sensor de inclinación? Consulta la documentación."},
               {"pregunta": "Una placa mide a = 3.75 m (u = 0.01) y b = 2.65 m (u = 0.01). ¿Cuál es el área y su incertidumbre?"}],
    "datos": [{"pregunta": "¿Qué sector tiene menos competencia?"}, {"pregunta": "Gráfico de volumen por año"},
              {"pregunta": "¿Dónde hay más oferta única?"}],
}


def grabar() -> None:
    salida = {}
    for nombre, casos in EJEMPLOS.items():
        salida[nombre] = []
        for q in casos:
            eventos = []
            for ev in ejecutar(nombre, {**q, "modelo": MODELOS[0], "idioma": "es"}):
                if ev["paso"] == "token" and eventos and eventos[-1]["paso"] == "token" and len(eventos[-1]["t"]) < 12:
                    eventos[-1]["t"] += ev["t"]
                else:
                    eventos.append(ev)
            fin = eventos[-1]
            print(nombre, "|", q["pregunta"][:60], "->", fin.get("estado") or fin.get("texto", "")[:160], flush=True)
            salida[nombre].append({"q": q, "eventos": eventos})
    GRABACIONES.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--puerto", type=int, default=8800)
    ap.add_argument("--grabar", action="store_true", help="guarda ejecuciones reales y sale")
    a = ap.parse_args()
    if a.grabar:
        return grabar()
    srv = ThreadingHTTPServer(("127.0.0.1", a.puerto), Web)
    print(f"Portafolio en vivo: http://127.0.0.1:{a.puerto}/vivo.html   (modelos: {', '.join(instalados()) or 'Ollama no responde'})")
    srv.serve_forever()


if __name__ == "__main__":
    main()
