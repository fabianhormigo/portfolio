"""MCP de ejemplo: herramientas reales para un agente (biblioteca con citas, incertidumbre y explorador).

Notación:
  herramientas  <área>_<verbo>[_<objeto>]   en español y snake_case
  clase         CONSULTA (solo lee)  ·  EJECUCIÓN (escribe o lanza algo)
Capas: motores/ (cálculo puro) · conocimiento/ (RAG) · herramientas/ + este fichero (interfaz fina)

Ejecutar:  python server.py            (stdio, para Claude Code / Desktop)
"""
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from herramientas import actividad, biblioteca, incertidumbre, proyectos

INSTRUCCIONES = """Documentación: biblioteca_consultar (cita documento y página; responde con el texto delante,
no de memoria). Incertidumbre de cualquier modelo: incertidumbre_* (GUM, Monte Carlo, malla, V&V 20).
Código del usuario: proyectos_* (solo lectura, dentro de PROYECTOS_ROOT)."""

mcp = FastMCP("mcp-hub", instructions=INSTRUCCIONES)

CONSULTA = ToolAnnotations(readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False)
EJECUCION = ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False)


# Cada pieza queda registrada en .actividad/eventos.jsonl (lo lee el panel).
def herramienta(clase: ToolAnnotations):
    return lambda fn: mcp.tool(annotations=clase)(actividad.instrumentar("herramienta", fn.__name__)(fn))


def recurso(uri: str):
    return lambda fn: mcp.resource(uri)(actividad.instrumentar("recurso", uri)(fn))


def prompt(nombre: str):
    return lambda fn: mcp.prompt(name=nombre)(actividad.instrumentar("prompt", nombre)(fn))


# ═══════════════════════════ biblioteca: recursos/
@herramienta(CONSULTA)
def biblioteca_listar(ruta: str = "", profundidad: int = 2) -> str:
    """CONSULTA · Lista la biblioteca central (recursos/).

    Args:
        ruta: subcarpeta dentro de recursos/ ("" = raíz).
        profundidad: niveles a mostrar.
    """
    return biblioteca.listar(ruta, profundidad)


@herramienta(CONSULTA)
def biblioteca_leer(ruta: str) -> str:
    """CONSULTA · Lee un fichero de texto de recursos/ (de un binario devuelve su ruta).

    Args:
        ruta: relativa a recursos/, p. ej. "ejemplo/mantenimiento.md".
    """
    return biblioteca.leer(ruta)


@herramienta(CONSULTA)
def biblioteca_buscar(patron: str, ruta: str = "", contexto: int = 1) -> str:
    """CONSULTA · Busca una regex en la biblioteca (recursos/).

    Args:
        patron: regex, p. ej. "recubrimiento".
        ruta: limita la búsqueda a una subcarpeta.
        contexto: líneas de alrededor.
    """
    return biblioteca.buscar(patron, ruta, contexto)


@herramienta(CONSULTA)
def biblioteca_consultar(pregunta: str, ruta: str = "", max_pasajes: int = 5) -> str:
    """CONSULTA · Pregunta a la biblioteca (documentos de recursos/): pasajes más relevantes CON CITA
    (documento · pág. o línea). Por términos (BM25), sin tildes ni plurales; para regex exacta, biblioteca_buscar.
    Avisa si hay documentos sin indexar (→ biblioteca_indexar).

    Args:
        pregunta: p. ej. "cada cuánto se calibra el sensor".
        ruta: limita a una carpeta o un documento.
        max_pasajes: 1–15.
    """
    return biblioteca.consultar(pregunta, ruta, max_pasajes)


@herramienta(EJECUCION)
def biblioteca_indexar(ruta: str = "", forzar: bool = False) -> dict:
    """EJECUCIÓN · Extrae el texto de la biblioteca (PDF por página, Markdown por bloques) a .texto/ para
    biblioteca_consultar. Solo procesa lo nuevo o modificado; borra el texto de lo que ya no existe.
    .texto/ es local: nunca va a git.

    Args:
        ruta: limita a una carpeta o fichero de recursos/.
        forzar: re-extrae aunque esté al día.
    """
    return biblioteca.indexar(ruta, forzar)


# ═══════════════════════════ proyectos: explorador de solo lectura
@herramienta(CONSULTA)
def proyectos_listar() -> str:
    """CONSULTA · Lista los proyectos de PROYECTOS_ROOT y si son repositorio git."""
    return proyectos.listar()


@herramienta(CONSULTA)
def proyectos_arbol(ruta: str = "", profundidad: int = 2) -> str:
    """CONSULTA · Árbol de carpetas de un proyecto (ruta relativa a PROYECTOS_ROOT)."""
    return proyectos.arbol(ruta, profundidad)


@herramienta(CONSULTA)
def proyectos_leer(ruta: str, inicio: int = 1, lineas: int = 400) -> str:
    """CONSULTA · Lee un fichero de texto de un proyecto por rango de líneas."""
    return proyectos.leer(ruta, inicio, lineas)


@herramienta(CONSULTA)
def proyectos_buscar(patron: str, ruta: str = "", extension: str = "") -> str:
    """CONSULTA · Busca una regex en tus proyectos.

    Args:
        patron: regex, p. ej. "def calcular_.*".
        ruta: subcarpeta relativa a PROYECTOS_ROOT ("" = todo).
        extension: filtra por extensión, p. ej. ".py".
    """
    return proyectos.buscar(patron, ruta, extension)


@herramienta(CONSULTA)
def proyectos_git(ruta: str, n: int = 15) -> str:
    """CONSULTA · git de un proyecto: estado (rama, cambios) y últimos n commits (máx. 100)."""
    return proyectos.git(ruta, n)


# ═══════════════════════════ incertidumbre: GUM, Monte Carlo, malla (GCI) y validación (V&V 20)
@herramienta(CONSULTA)
def incertidumbre_propagar(modelo: str, entradas: dict, correlaciones: dict | None = None, p: float = 0.95,
                           metodo: str = "ambos", ndig: int = 2, semilla: int = 0) -> dict:
    """CONSULTA · Propaga incertidumbre por Y = modelo(X). modelo: expresión, p. ej. "rho*c_l**2*t**3/12"
    (+ − * / **, sqrt, exp, log, log10, sin, cos…, pi). entradas: {"rho": {"valor": 2300, "u": 50,
    "distribucion": "normal|rectangular|triangular|arcoseno", "nu": grados de libertad (∞ si se omite)}}.
    correlaciones: {"a,b": r}. metodo gum | monte_carlo | ambos; con ambos dice si el marco GUM vale (JCGM 101, 8.2)."""
    return incertidumbre.propagar(modelo, entradas, correlaciones, p, metodo, ndig, semilla)


@herramienta(CONSULTA)
def incertidumbre_estimar_malla(f_fina: float, f_media: float, f_gruesa: float, r: float,
                                p_formal: float | None = None) -> dict:
    """CONSULTA · Error de discretización con tres mallas de razón r (Roache): orden observado, valor extrapolado,
    GCI y u_num para V&V 20. Avisa si la convergencia oscila o no está en rango asintótico."""
    return incertidumbre.estimar_malla(f_fina, f_media, f_gruesa, r, p_formal)


@herramienta(CONSULTA)
def incertidumbre_validar(S: float, D: float, u_num: float, u_input: float, u_D: float, k: float = 2.0) -> dict:
    """CONSULTA · Validación ASME V&V 20: simulación S frente a medida D. E = S − D, u_val = √(u_num²+u_input²+u_D²);
    dice si hay error de modelo detectable y qué incertidumbre domina."""
    return incertidumbre.validar(S, D, u_num, u_input, u_D, k)


if __name__ == "__main__":
    mcp.run()
