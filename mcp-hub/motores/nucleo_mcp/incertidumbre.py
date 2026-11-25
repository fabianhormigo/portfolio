"""Incertidumbre de modelos (también simulaciones FEM): GUM lineal, Monte Carlo y validación V&V 20. Puro (sin I/O).

Fuentes:
  - GUM, JCGM 100:2008 (PDF local en PROYECTOS/PROPAGACIÓN DE ERRORES ACÚSTICA/normativa):
      ley de propagación 5.1.2 ec. (10) y, con correlación, 5.2.2 ec. (13); Welch–Satterthwaite G.4.1 ec. (G.2b);
      k = t_p(ν_eff) G.3 (piezas de estadistica.py).
  - JCGM 101:2008 (Suplemento 1, Monte Carlo) — NO está en local; aplicado de memoria y verificado con casos exactos:
      intervalo más corto 7.7.2, procedimiento adaptativo 7.9 (tolerancia numérica δ a partir de ndig cifras de u),
      validación del marco GUM 8.2 (d_low, d_high ≤ δ).
  - Roache, P.J. (1994) J. Fluids Eng. 116:405–413 y (1998) Verification and Validation in Computational Science and
    Engineering: orden observado y GCI (Fs = 1,25 con tres mallas; Fs = 3 con dos o sin orden fiable).
  - ASME V&V 20-2009 (no está en local; de memoria): E = S − D, u_val = √(u_num² + u_input² + u_D²),
    δ_model ∈ [E − k u_val, E + k u_val]; u_num = GCI/1,15 con Fs = 1,25 (criterio conservador del estándar).
Unidades: las del modelo (el núcleo no las toca).
"""
from __future__ import annotations

import ast
import math
import operator

import numpy as np

from nucleo_mcp.estadistica import factor_cobertura, grados_libertad_efectivos

DISTRIBUCIONES = ("normal", "rectangular", "triangular", "arcoseno")
"""Todas se dan por su valor x y su incertidumbre típica u (desviación típica), como en la GUM."""

# ─────────────────────────────── modelo escrito como expresión (seguro: solo aritmética y funciones NumPy listadas)
_OPS = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv,
        ast.Pow: operator.pow, ast.USub: operator.neg, ast.UAdd: operator.pos}
_FUNCIONES = {f: getattr(np, f) for f in ("sqrt", "exp", "log", "log10", "sin", "cos", "tan", "arcsin", "arccos",
                                          "arctan", "arctan2", "sinh", "cosh", "tanh", "abs", "minimum", "maximum",
                                          "radians", "degrees", "hypot")}
_CONSTANTES = {"pi": math.pi, "e": math.e}


def modelo_desde_expresion(expresion: str, nombres: list[str]):
    """Y = f(X₁…Xₙ) escrito como texto, p. ej. "rho*c_l**2*t**3/12". Solo admite + − × / **, números, las variables
    de `nombres`, pi, e y las funciones de _FUNCIONES: no hay eval. → f(dict nombre→array) → array."""
    arbol = ast.parse(expresion, mode="eval").body

    def comprobar(n):
        if isinstance(n, ast.BinOp) and type(n.op) in _OPS:
            comprobar(n.left), comprobar(n.right)
        elif isinstance(n, ast.UnaryOp) and type(n.op) in _OPS:
            comprobar(n.operand)
        elif isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id in _FUNCIONES and not n.keywords:
            for a in n.args:
                comprobar(a)
        elif isinstance(n, ast.Name):
            if n.id not in nombres and n.id not in _CONSTANTES:
                raise ValueError(f"Variable desconocida en el modelo: {n.id} (entradas: {nombres})")
        elif not (isinstance(n, ast.Constant) and isinstance(n.value, (int, float))):
            raise ValueError(f"Expresión no admitida en el modelo: {ast.unparse(n)}")
    comprobar(arbol)

    def evaluar(n, x):
        if isinstance(n, ast.BinOp):
            return _OPS[type(n.op)](evaluar(n.left, x), evaluar(n.right, x))
        if isinstance(n, ast.UnaryOp):
            return _OPS[type(n.op)](evaluar(n.operand, x))
        if isinstance(n, ast.Call):
            return _FUNCIONES[n.func.id](*(evaluar(a, x) for a in n.args))
        if isinstance(n, ast.Name):
            return x[n.id] if n.id in x else _CONSTANTES[n.id]
        return float(n.value)
    def f(x):
        with np.errstate(all="ignore"):             # los no finitos se detectan y se explican fuera
            return np.asarray(evaluar(arbol, x), float)
    return f


# ─────────────────────────────── entradas
def _entradas(entradas: dict) -> tuple[list[str], np.ndarray, np.ndarray]:
    nombres = list(entradas)
    if not nombres:
        raise ValueError("Sin entradas")
    x = np.array([float(entradas[n]["valor"]) for n in nombres])
    u = np.array([float(entradas[n]["u"]) for n in nombres])
    for n in nombres:
        d = entradas[n].get("distribucion", "normal")
        if d not in DISTRIBUCIONES:
            raise ValueError(f"{n}: distribución «{d}» no admitida ({DISTRIBUCIONES})")
    if not (np.isfinite(x).all() and np.isfinite(u).all()) or (u < 0).any():
        raise ValueError("Valores y u deben ser finitos y u ≥ 0")
    return nombres, x, u


def _correlacion(nombres: list[str], correlaciones: dict | None) -> np.ndarray:
    """correlaciones: {"a,b": r}. → matriz R validada (simétrica, |r| ≤ 1, semidefinida positiva)."""
    R = np.eye(len(nombres))
    for clave, r in (correlaciones or {}).items():
        a, b = (s.strip() for s in clave.split(","))
        if a not in nombres or b not in nombres or a == b:
            raise ValueError(f"Correlación «{clave}»: nombres no válidos")
        if not -1 <= r <= 1:
            raise ValueError(f"Correlación «{clave}» = {r} fuera de [−1, 1]")
        i, j = nombres.index(a), nombres.index(b)
        R[i, j] = R[j, i] = r
    if np.linalg.eigvalsh(R).min() < -1e-12:
        raise ValueError("La matriz de correlación no es semidefinida positiva")
    return R


def muestrear(entradas: dict, M: int, rng: np.random.Generator, correlaciones: dict | None = None) -> dict:
    """M muestras de cada entrada (JCGM 101, 6.4). Con correlaciones, todas las correlacionadas deben ser normales
    (normal multivariante por Cholesky, 6.4.8). → dict nombre → array (M,)."""
    nombres, x, u = _entradas(entradas)
    R = _correlacion(nombres, correlaciones)
    dist = [entradas[n].get("distribucion", "normal") for n in nombres]
    corr = np.abs(R - np.eye(len(nombres))).sum(axis=1) > 0
    if any(c and d != "normal" for c, d in zip(corr, dist)):
        raise ValueError("Solo se admiten correlaciones entre entradas normales")
    z = rng.standard_normal((M, len(nombres)))
    if corr.any():
        L = np.linalg.cholesky(R + 1e-15 * np.eye(len(nombres)))
        z = z @ L.T
    out = {}
    for i, (n, d) in enumerate(zip(nombres, dist)):
        if d == "normal":
            out[n] = x[i] + u[i] * z[:, i]
        elif d == "rectangular":                    # semiancho a = √3 u
            out[n] = x[i] + np.sqrt(3) * u[i] * rng.uniform(-1, 1, M)
        elif d == "triangular":                     # simétrica, semiancho a = √6 u
            out[n] = x[i] + np.sqrt(6) * u[i] * (rng.uniform(0, 1, M) - rng.uniform(0, 1, M))
        else:                                       # arcoseno (forma de U), semiancho a = √2 u
            out[n] = x[i] + np.sqrt(2) * u[i] * np.sin(2 * np.pi * rng.uniform(0, 1, M))
    return out


# ─────────────────────────────── GUM (JCGM 100)
def gum(f, entradas: dict, correlaciones: dict | None = None, p: float = 0.95) -> dict:
    """Marco GUM: estimación y = f(x), sensibilidades por diferencias centradas (paso 10⁻³·u_i), ley de propagación con
    correlaciones, ν_eff por Welch–Satterthwaite (solo sin correlación) y k = t_p(ν_eff). f puede devolver un escalar o
    un vector (n_y,): u se da por componente. ν de cada entrada: entradas[n]["nu"] (por defecto ∞, tipo B)."""
    nombres, x, u = _entradas(entradas)
    R = _correlacion(nombres, correlaciones)
    base = dict(zip(nombres, x))
    y = np.atleast_1d(f(base)).astype(float)
    if not np.isfinite(y).all():
        raise ValueError("El modelo no es finito en la estimación de las entradas")
    C = np.zeros((y.size, len(nombres)))
    for i, n in enumerate(nombres):
        if u[i] == 0:
            continue
        h = 1e-3 * u[i]
        mas, menos = dict(base), dict(base)
        mas[n], menos[n] = x[i] + h, x[i] - h
        C[:, i] = (np.atleast_1d(f(mas)) - np.atleast_1d(f(menos))) / (2 * h)
    Cu = C * u                                                  # (n_y, n_x): c_i u_i
    uc = np.sqrt(np.einsum("yi,ij,yj->y", Cu, R, Cu).clip(min=0))
    nu_i = np.array([float(entradas[n].get("nu", math.inf)) for n in nombres])
    con_corr = not np.allclose(R, np.eye(len(nombres)))
    nu_eff = [math.inf if con_corr else grados_libertad_efectivos([(abs(c), v) for c, v in zip(fila, nu_i)])
              for fila in Cu]
    k = np.array([factor_cobertura(v, p) for v in nu_eff])
    return {"y": y, "u": uc, "k": k, "U": k * uc, "nu_eff": np.array(nu_eff), "p": p, "nombres": nombres,
            "sensibilidad": C, "contribucion": np.abs(Cu), "correlacionado": con_corr}


# ─────────────────────────────── Monte Carlo (JCGM 101)
def intervalo_mas_corto(muestras: np.ndarray, p: float) -> tuple[float, float]:
    """Intervalo de cobertura más corto con probabilidad p (JCGM 101, 7.7.2)."""
    s = np.sort(muestras)
    M = s.size
    q = int(p * M + 0.5)
    if q < 1 or q >= M:
        raise ValueError("Muy pocas muestras para esa probabilidad de cobertura")
    anchos = s[q - 1:] - s[:M - q + 1]
    r = int(np.argmin(anchos))
    return float(s[r]), float(s[r + q - 1])


def tolerancia_numerica(u: float, ndig: int = 2) -> float:
    """δ = ½·10^l con u = c·10^l y c entero de ndig cifras (JCGM 101, 7.9.2)."""
    if u <= 0:
        return 0.0
    l = math.floor(math.log10(u)) - ndig + 1
    return 0.5 * 10.0 ** l


def monte_carlo(f, entradas: dict, correlaciones: dict | None = None, p: float = 0.95, ndig: int = 2,
                semilla: int = 0, M_max: int = 2_000_000, bins: int = 60) -> dict:
    """Método de Monte Carlo adaptativo (JCGM 101, 7.9) para una salida escalar: tandas de
    M₀ = max(⌈100/(1−p)⌉, 10⁴) hasta que 2·s de y, u, y_low e y_high entre tandas ≤ δ (ndig cifras de u).
    Semilla fija: reproducible. → y (media), u, intervalo más corto, M, histograma y si se estabilizó."""
    rng = np.random.default_rng(semilla)
    M0 = max(math.ceil(100 / (1 - p)), 10_000)
    tandas, muestras = [], []
    while True:
        ys = np.asarray(f(muestrear(entradas, M0, rng, correlaciones)), float).reshape(-1)
        if ys.size != M0:
            raise ValueError("Monte Carlo solo para salida escalar: el modelo debe devolver (M,) para M muestras")
        if not np.isfinite(ys).all():
            raise ValueError("El modelo da valores no finitos para algunas muestras: revisa distribuciones/dominio")
        muestras.append(ys)
        tandas.append((ys.mean(), ys.std(ddof=1), *intervalo_mas_corto(ys, p)))
        h = len(tandas)
        if h >= 2:
            s = np.std(np.array(tandas), axis=0, ddof=1) / np.sqrt(h)
            delta = tolerancia_numerica(np.mean([t[1] for t in tandas]), ndig)
            if (2 * s <= delta).all():
                estable = True
                break
        if h * M0 >= M_max:
            estable = False
            break
    todas = np.concatenate(muestras)
    lo, hi = intervalo_mas_corto(todas, p)
    cuentas, bordes = np.histogram(todas, bins=bins)
    return {"y": float(todas.mean()), "u": float(todas.std(ddof=1)), "intervalo": (lo, hi), "p": p, "M": todas.size,
            "estabilizado": estable, "delta": tolerancia_numerica(float(todas.std(ddof=1)), ndig),
            "histograma": {"cuentas": cuentas.tolist(), "bordes": bordes.tolist()}}


def validar_gum(g: dict, mc: dict, ndig: int = 2) -> dict:
    """¿Vale el marco GUM? (JCGM 101, 8.2): d_low = |y − U − y_low|, d_high = |y + U − y_high| ≤ δ.
    Usa la primera salida de `g` y el intervalo de Monte Carlo."""
    y, U = float(g["y"][0]), float(g["U"][0])
    lo, hi = mc["intervalo"]
    d_low, d_high = abs(y - U - lo), abs(y + U - hi)
    delta = tolerancia_numerica(mc["u"], ndig)
    return {"d_low": d_low, "d_high": d_high, "delta": delta, "valido": d_low <= delta and d_high <= delta}


# ─────────────────────────────── error numérico (Roache) y validación (V&V 20)
def gci(f_fina: float, f_media: float, f_gruesa: float, r: float, p_formal: float | None = None) -> dict:
    """Índice de convergencia de malla (Roache) con tres mallas de razón de refinamiento constante r > 1.
    p = ln((f₃−f₂)/(f₂−f₁))/ln r;  f_ext = f₁ + (f₁−f₂)/(r^p − 1);  GCI_fina = Fs·|(f₁−f₂)/f₁|/(r^p − 1).
    Convergencia oscilante o monótona fuera de rango asintótico → aviso; con p_formal se usa ese orden y Fs = 3."""
    if r <= 1:
        raise ValueError("r debe ser > 1 (malla gruesa / malla fina)")
    e21, e32 = f_fina - f_media, f_media - f_gruesa
    if f_fina == 0:
        raise ValueError("f_fina = 0: el GCI es relativo, usa una magnitud no nula")
    aviso, Fs = "", 1.25
    if e21 == 0:
        return {"p": math.inf, "f_ext": f_fina, "gci": 0.0, "u_num": 0.0, "Fs": Fs,
                "aviso": "Mallas fina y media dan lo mismo: ¿la magnitud es exacta en esta discretización?"}
    ratio = e32 / e21
    if ratio <= 0:
        aviso = "Convergencia oscilante: el orden observado no es fiable."
        p = None
    else:
        p = math.log(ratio) / math.log(r)
        if p_formal is not None and not 0.5 * p_formal <= p <= 1.5 * p_formal:
            aviso = f"Orden observado {p:.2f} lejos del formal {p_formal}: mallas fuera del rango asintótico."
    if aviso:
        if p_formal is None:
            raise ValueError(aviso + " Pasa p_formal para estimar el GCI con Fs = 3.")
        p_uso, Fs = p_formal, 3.0
    else:
        p_uso = p
    f_ext = f_fina + e21 / (r ** p_uso - 1)
    g = Fs * abs(e21 / f_fina) / (r ** p_uso - 1)
    return {"p": p, "p_usado": p_uso, "f_ext": f_ext, "gci": g, "u_num": g * abs(f_fina) / 1.15 if Fs == 1.25
            else g * abs(f_fina) / 2, "Fs": Fs, "aviso": aviso}


def validacion_vv20(S: float, D: float, u_num: float, u_input: float, u_D: float, k: float = 2.0) -> dict:
    """ASME V&V 20: error de comparación E = S − D y su incertidumbre de validación u_val.
    El error de modelo δ_model está en [E − k u_val, E + k u_val]. Si |E| ≤ k u_val, el modelo no se distingue de la
    medida con esta incertidumbre (no es «validado»: es que no se puede afinar más)."""
    for n, v in (("u_num", u_num), ("u_input", u_input), ("u_D", u_D)):
        if not v >= 0:
            raise ValueError(f"{n} debe ser ≥ 0")
    E = S - D
    u_val = math.sqrt(u_num ** 2 + u_input ** 2 + u_D ** 2)
    detectable = abs(E) > k * u_val
    return {"E": E, "u_val": u_val, "k": k, "delta_model": (E - k * u_val, E + k * u_val),
            "error_de_modelo_detectable": detectable,
            "lectura": (f"El modelo se desvía {E:+.4g}: es error de modelo, mayor que k·u_val = {k * u_val:.4g}."
                        if detectable else
                        f"|E| = {abs(E):.4g} ≤ k·u_val = {k * u_val:.4g}: no se distingue error de modelo; "
                        "reducir u_val (malla, entradas o medida) para afinar."),
            "dominante": max((("u_num", u_num), ("u_input", u_input), ("u_D", u_D)), key=lambda t: t[1])[0]}
