"""Área incertidumbre: GUM (JCGM 100), Monte Carlo (JCGM 101), error de malla (GCI de Roache) y validación (ASME V&V 20).
Adaptador fino de motores/nucleo_mcp/incertidumbre.py, que es puro y está verificado en tests/test_incertidumbre.py."""
import sys
from pathlib import Path

_MOTORES = str(Path(__file__).resolve().parent.parent / "motores")
if _MOTORES not in sys.path:
    sys.path.insert(0, _MOTORES)
from nucleo_mcp import incertidumbre as inc  # noqa: E402


def _r(v: float, cifras: int = 6) -> float:
    return float(f"{v:.{cifras}g}")


def propagar(modelo: str, entradas: dict, correlaciones: dict | None = None, p: float = 0.95,
             metodo: str = "ambos", ndig: int = 2, semilla: int = 0) -> dict:
    """modelo: expresión con los nombres de `entradas`; entradas: {nombre: {valor, u, distribucion?, nu?}}."""
    if metodo not in ("gum", "monte_carlo", "ambos"):
        raise ValueError("metodo: gum | monte_carlo | ambos")
    f = inc.modelo_desde_expresion(modelo, list(entradas))
    out = {"modelo": modelo, "p": p}
    if metodo in ("gum", "ambos"):
        g = inc.gum(f, entradas, correlaciones, p)
        var = g["contribucion"][0] ** 2
        out["gum"] = {"y": _r(g["y"][0]), "u": _r(g["u"][0]), "k": _r(g["k"][0], 4), "U": _r(g["U"][0]),
                      "nu_eff": g["nu_eff"][0] if g["nu_eff"][0] != float("inf") else "inf",
                      "contribuciones": {n: {"c": _r(c), "u_y": _r(uy), "porcentaje": round(100 * v / var.sum(), 1)
                                             if var.sum() > 0 else 0.0}
                                         for n, c, uy, v in zip(g["nombres"], g["sensibilidad"][0],
                                                                g["contribucion"][0], var)},
                      "nota": "porcentajes sin correlación" if g["correlacionado"] else ""}
    if metodo in ("monte_carlo", "ambos"):
        mc = inc.monte_carlo(f, entradas, correlaciones, p, ndig, semilla)
        out["monte_carlo"] = {"y": _r(mc["y"]), "u": _r(mc["u"]), "intervalo": [_r(v) for v in mc["intervalo"]],
                              "M": mc["M"], "estabilizado": mc["estabilizado"], "delta": mc["delta"],
                              "histograma": mc["histograma"]}
    if metodo == "ambos":
        v = inc.validar_gum(g, mc, ndig)
        out["gum_valido"] = {**{k: _r(x) for k, x in v.items() if k != "valido"}, "valido": v["valido"],
                             "lectura": "El marco GUM vale aquí (JCGM 101, 8.2)." if v["valido"] else
                             "El marco GUM NO vale aquí: usa el intervalo de Monte Carlo."}
    return out


def estimar_malla(f_fina: float, f_media: float, f_gruesa: float, r: float, p_formal: float | None = None) -> dict:
    return inc.gci(f_fina, f_media, f_gruesa, r, p_formal)


def validar(S: float, D: float, u_num: float, u_input: float, u_D: float, k: float = 2.0) -> dict:
    return inc.validacion_vv20(S, D, u_num, u_input, u_D, k)
