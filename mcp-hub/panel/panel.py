"""Panel vivo del MCP mcp-hub: grafo de piezas + métricas + actividad en tiempo real.

Uso:  .venv\\Scripts\\python.exe panel\\panel.py      → http://127.0.0.1:8790
Solo escucha en 127.0.0.1. Lee el servidor por introspección (no lo arranca) y los eventos
de .actividad/eventos.jsonl. También vigila los ficheros del MCP: si alguien los edita, se ilumina.
"""
import importlib
import inspect
import json
import re
import statistics
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import networkx as nx

RAIZ = Path(__file__).resolve().parent.parent
ESTATICO = Path(__file__).resolve().parent / "static"
EVENTOS = RAIZ / ".actividad" / "eventos.jsonl"
PUERTO = 8790
sys.path.insert(0, str(RAIZ))


# ------------------------------------------------------------------ estructura
def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(RAIZ).as_posix()
    except ValueError:
        return str(p)


def construir_grafo() -> dict:
    """Nodos y aristas a partir del propio servidor (se recalcula si cambian los ficheros)."""
    for m in [k for k in sys.modules if k == "server" or k.startswith("herramientas")]:
        del sys.modules[m]
    srv = importlib.import_module("server")
    mods = {k.split(".", 1)[1]: v for k, v in sys.modules.items()
            if k.startswith("herramientas.") and k.count(".") == 1}
    nodos, aristas = {}, []

    def nodo(i, tipo, etiqueta, **kw):
        nodos.setdefault(i, {"id": i, "tipo": tipo, "etiqueta": etiqueta, **kw})

    nodo("server", "servidor", "server.py", fichero="server.py")
    for n, m in mods.items():
        nodo(f"mod:{n}", "modulo", f"{n}.py", fichero=f"herramientas/{n}.py")
        # Datos/externos: constantes Path del módulo y la imagen Docker
        for attr, val in vars(m).items():
            if attr.isupper() and isinstance(val, Path):
                r = _rel(val)
                ext = not r or ":" in r or r.startswith("/")
                i = f"dat:{r}"
                nodo(i, "externo" if ext else "datos",
                     (Path(r).name or r) if not ext else f"{val.parent.name}/{val.name}",
                     fichero=None if ext else r)
                aristas.append((f"mod:{n}", i))
            elif attr.isupper() and isinstance(val, str) and val.startswith("https://"):  # servicio de internet
                host = val.split("/")[2]
                nodo(f"ext:{host}", "externo", f"internet · {host}")
                aristas.append((f"mod:{n}", f"ext:{host}"))
        if getattr(m, "IMAGEN", None):
            nodo("ext:docker", "externo", f"Docker · {m.IMAGEN}")
            aristas.append((f"mod:{n}", "ext:docker"))

    patron = re.compile(r"\b(" + "|".join(mods) + r")\.")
    tm, rm, pm = srv.mcp._tool_manager, srv.mcp._resource_manager, srv.mcp._prompt_manager
    piezas = ([("herramienta", t.name, t.fn, t.description) for t in tm.list_tools()] +
              [("recurso", str(r.uri), r.fn, r.description) for r in rm.list_resources()] +
              [("prompt", p.name, p.fn, p.description) for p in pm.list_prompts()])
    clases = {t.name: ("consulta" if t.annotations and t.annotations.readOnlyHint else "ejecucion")
              for t in tm.list_tools()}
    for tipo, nombre, fn, desc in piezas:
        i = f"{tipo}:{nombre}"
        area = re.split(r"[_:/-]", nombre)[0]
        nodo(i, tipo, nombre, desc=(desc or "").strip().split("\n")[0], area=area,
             clase=clases.get(nombre, "consulta"))
        aristas.append(("server", i))
        fuente = inspect.getsource(inspect.unwrap(fn))
        for m in sorted(set(patron.findall(fuente))):
            aristas.append((i, f"mod:{m}"))
        for md in re.findall(r'leer_prompt\("([^"]+)"\)', fuente):
            nodo(f"lib:{md}", "datos", f"{md}.md", fichero=f"library/{md}.md")
            aristas.append((i, f"lib:{md}"))
        if "REGLAS" in fuente:
            nodo("dat:reglas", "datos", "REGLAS (CLAUDE.md)", fichero="herramientas/flujo.py")
            aristas.append((i, "dat:reglas"))
    for i in list(nodos):  # cada pieza instrumentada pasa por actividad
        if nodos[i]["tipo"] in ("herramienta", "recurso", "prompt") and "actividad" in mods:
            aristas.append((i, "mod:actividad"))
    aristas = sorted({(a, b) for a, b in aristas if a in nodos and b in nodos and a != b})
    return {"nodos": list(nodos.values()), "aristas": [{"source": a, "target": b} for a, b in aristas]}


# ------------------------------------------------------------------ métricas (solo las que ayudan a decidir)
INFRA = {"server", "mod:actividad"}


def _areas(g: dict, U: nx.Graph) -> dict:
    """Área de cada nodo: la declarada (herramientas, recursos, prompts), la del módulo, o la de quien lo usa."""
    area = {n["id"]: n["area"] for n in g["nodos"] if n.get("area")}
    area.update({n["id"]: n["id"][4:] for n in g["nodos"] if n["tipo"] == "modulo" and n["id"] not in INFRA})
    for x in U:
        if x not in area and x not in INFRA:
            vec = {area[v] for v in U[x] if v in area}
            area[x] = vec.pop() if len(vec) == 1 else "compartido"
    return area


def metricas(g: dict) -> dict:
    G = nx.DiGraph()
    G.add_nodes_from(n["id"] for n in g["nodos"])
    G.add_edges_from((a["source"], a["target"]) for a in g["aristas"])
    U = G.to_undirected()
    area = _areas(g, U)
    # Acoplamiento: aristas entre áreas distintas (sin contar server/actividad, que tocan todo a propósito)
    cruces = sorted([a, b] for a, b in G.edges()
                    if a not in INFRA and b not in INFRA and area.get(a) != area.get(b))
    huerfanos = sorted(x for x in U if U.degree(x) == 0)  # piezas que nada usa ni registra
    ciclos = [c for c in nx.simple_cycles(G) if len(c) > 1]
    areas = list(dict.fromkeys(n["area"] for n in g["nodos"] if n.get("area")))
    return {
        "piezas": sum(n["tipo"] in ("herramienta", "recurso", "prompt") for n in g["nodos"]),
        "nodos": G.number_of_nodes(), "aristas": G.number_of_edges(),
        "areas": areas, "area": area, "infra": sorted(INFRA & set(U)),
        "acoplamiento": cruces, "huerfanos": huerfanos,
        "ciclos": ciclos[:10], "n_ciclos": len(ciclos),
        "grado": dict(U.degree()),
    }


# ------------------------------------------------------------------ estado en vivo
def _vigilados() -> dict:
    fich = [RAIZ / "server.py", *RAIZ.glob("herramientas/*.py"), *RAIZ.glob("library/*.md")]
    return {_rel(p): p.stat().st_mtime for p in fich if p.is_file()}


def leer_eventos(desde: float = 0.0, maximo: int = 4000) -> list[dict]:
    if not EVENTOS.exists():
        return []
    with open(EVENTOS, encoding="utf-8") as fh:
        lineas = fh.readlines()[-maximo:]
    out = []
    for l in lineas:
        try:
            e = json.loads(l)
        except json.JSONDecodeError:
            continue
        if e.get("t", 0) > desde:
            out.append(e)
    return out


def estado() -> dict:
    ev = leer_eventos()
    ahora = time.time()
    abiertos, stats = {}, {}
    for e in ev:
        clave = f"{e['tipo']}:{e['nombre']}"
        s = stats.setdefault(clave, {"llamadas": 0, "errores": 0, "ms": [], "ultima": 0})
        if e["fase"] == "inicio":
            abiertos[e["id"]] = e
            s["ultima"] = e["t"]
        else:
            abiertos.pop(e["id"], None)
            s["llamadas"] += 1
            s["errores"] += e["fase"] == "error"
            if "ms" in e:
                s["ms"].append(e["ms"])
    resumen = {}
    for k, s in stats.items():
        ms = sorted(s["ms"])
        resumen[k] = {"llamadas": s["llamadas"], "errores": s["errores"], "ultima": s["ultima"],
                      "ms_medio": round(statistics.mean(ms), 1) if ms else None,
                      "ms_p95": ms[min(len(ms) - 1, int(0.95 * len(ms)))] if ms else None}
    ultimos5 = [e for e in ev if e["fase"] != "inicio" and ahora - e["t"] < 300]
    # Llamadas emparejadas (inicio→fin/error) de los últimos 10 min, para la línea de tiempo
    ini, llamadas = {}, []
    for e in ev:
        if ahora - e["t"] > 600:
            continue
        if e["fase"] == "inicio":
            ini[e["id"]] = e
        elif e["id"] in ini:
            a = ini.pop(e["id"])
            llamadas.append({"id": e["id"], "nodo": f"{e['tipo']}:{e['nombre']}", "nombre": e["nombre"],
                             "t0": a["t"], "t1": e["t"], "fase": e["fase"], "ms": e.get("ms")})
    llamadas += [{"id": k, "nodo": f"{a['tipo']}:{a['nombre']}", "nombre": a["nombre"], "t0": a["t"],
                  "t1": None, "fase": "en_curso"} for k, a in ini.items()]
    return {"ahora": ahora, "en_curso": [f"{e['tipo']}:{e['nombre']}" for e in abiertos.values()
                                         if ahora - e["t"] < 3600],
            "por_nodo": resumen, "ultimos": ev[-40:][::-1], "ficheros": _vigilados(), "llamadas": llamadas,
            "llamadas_5min": len(ultimos5), "errores_5min": sum(e["fase"] == "error" for e in ultimos5)}


# ------------------------------------------------------------------ servidor HTTP
_cache = {"firma": None, "grafo": None}
_candado = threading.Lock()  # reconstruir borra y reimporta módulos: una petición a la vez


def grafo_actual() -> dict:
    with _candado:
        firma = tuple(sorted(_vigilados().items()))
        if firma != _cache["firma"]:
            g = construir_grafo()
            g["metricas"] = metricas(g)
            _cache.update(firma=firma, grafo=g)
        return _cache["grafo"]


TIPOS = {".html": "text/html; charset=utf-8", ".js": "text/javascript", ".svg": "image/svg+xml",
         ".woff2": "font/woff2", ".json": "application/json"}


class Manejador(BaseHTTPRequestHandler):
    def _enviar(self, cuerpo: bytes, tipo: str, codigo: int = 200):
        self.send_response(codigo)
        self.send_header("Content-Type", tipo)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(cuerpo)

    def do_GET(self):
        ruta = self.path.split("?")[0]
        try:
            if ruta == "/":
                return self._enviar((Path(__file__).parent / "index.html").read_bytes(), TIPOS[".html"])
            if ruta == "/api/grafo":
                return self._enviar(json.dumps(grafo_actual(), ensure_ascii=False).encode(), TIPOS[".json"])
            if ruta == "/api/estado":
                return self._enviar(json.dumps(estado(), ensure_ascii=False).encode(), TIPOS[".json"])
            f = (ESTATICO / ruta.removeprefix("/static/")).resolve()
            if ruta.startswith("/static/") and f.parent == ESTATICO.resolve() and f.is_file():
                return self._enviar(f.read_bytes(), TIPOS.get(f.suffix, "application/octet-stream"))
            self._enviar(b"no encontrado", "text/plain", 404)
        except Exception as e:  # el panel no debe caerse por un fallo puntual
            self._enviar(json.dumps({"error": str(e)}).encode(), TIPOS[".json"], 500)

    def log_message(self, *a):
        pass


class _Servidor(ThreadingHTTPServer):
    # En Windows, reutilizar la dirección deja que DOS paneles escuchen en el mismo puerto. Se prohíbe.
    allow_reuse_address = sys.platform != "win32"

    def server_bind(self):
        import socket
        if sys.platform == "win32":
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_EXCLUSIVEADDRUSE, 1)
        super().server_bind()


def _ya_abierto(url: str) -> bool:
    import urllib.request
    try:
        urllib.request.urlopen(url + "/api/estado", timeout=3)
        return True
    except Exception:
        return False


if __name__ == "__main__":
    import webbrowser
    url = f"http://127.0.0.1:{PUERTO}"
    abrir = "--sin-navegador" not in sys.argv
    if _ya_abierto(url):
        print(f"El panel ya estaba abierto: {url}")
        if abrir:
            webbrowser.open(url)
        sys.exit(0)
    try:
        srv = _Servidor(("127.0.0.1", PUERTO), Manejador)
    except OSError:
        sys.exit(f"El puerto {PUERTO} lo usa otro programa. Ciérralo o cambia PUERTO en panel/panel.py.")
    print(f"Panel MCP en {url}  (cierra esta ventana o Ctrl+C para pararlo)")
    if abrir:  # el servidor ya escucha: el navegador no puede llegar antes
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    srv.serve_forever()
