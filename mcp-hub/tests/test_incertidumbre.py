"""Motor de incertidumbre (motores/nucleo_mcp/incertidumbre.py) frente a casos con solución exacta.

  - Suma de 4 normales u = 1 (JCGM 101, ej. 9.2.2): Y ~ N(0, 2²), intervalo 95 % = ±1,95996·2. GUM exacto y validado.
  - Suma de 2 rectangulares iguales (u = 1, a = √3): Y triangular de semiancho 2a; intervalo 95 % más corto
    ±2a(1 − √0,05) = ±2,690 frente a ±2,772 de la GUM → la GUM NO se valida con 2 cifras (δ = 0,005).
  - Y = X², X ~ N(0, 1): la GUM lineal da u = 0 (derivada nula); la exacta es √2 (χ² con 1 g.l.).
  - Welch–Satterthwaite: una sola entrada con ν = 4 → ν_eff = 4 y k = t₀,₉₇₅(4) = 2,7764 (GUM tabla G.2).
  - GCI: f(h) = 1 + 0,3h² con h = 0,4/0,2/0,1 → p = 2 y f_ext = 1 exactos.
"""
import math

import numpy as np
import pytest

from nucleo_mcp import incertidumbre as inc

N = lambda v, u, **kw: {"valor": v, "u": u, **kw}                                    # noqa: E731


def test_suma_de_normales():
    ent = {f"x{i}": N(0.0, 1.0) for i in range(4)}
    f = inc.modelo_desde_expresion("x0 + x1 + x2 + x3", list(ent))
    g, mc = inc.gum(f, ent), inc.monte_carlo(f, ent)
    assert g["u"][0] == pytest.approx(2.0, rel=1e-9)
    assert g["U"][0] == pytest.approx(1.959964 * 2, rel=1e-6)
    assert mc["estabilizado"]
    assert mc["u"] == pytest.approx(2.0, abs=2 * mc["delta"])
    lo, hi = mc["intervalo"]
    assert hi == pytest.approx(3.92, abs=0.05) and lo == pytest.approx(-3.92, abs=0.05)
    assert inc.validar_gum(g, mc)["valido"]


def test_suma_de_rectangulares_gum_no_valida():
    ent = {"a": N(0.0, 1.0, distribucion="rectangular"), "b": N(0.0, 1.0, distribucion="rectangular")}
    f = inc.modelo_desde_expresion("a + b", list(ent))
    g, mc = inc.gum(f, ent), inc.monte_carlo(f, ent)
    exacto = 2 * math.sqrt(3) * (1 - math.sqrt(0.05))
    assert mc["intervalo"][1] == pytest.approx(exacto, abs=0.02)
    assert mc["u"] == pytest.approx(math.sqrt(2), abs=0.01)
    assert not inc.validar_gum(g, mc)["valido"]


def test_no_lineal_gum_falla():
    ent = {"x": N(0.0, 1.0)}
    f = inc.modelo_desde_expresion("x**2", ["x"])
    assert inc.gum(f, ent)["u"][0] == pytest.approx(0.0, abs=1e-9)
    mc = inc.monte_carlo(f, ent)
    assert mc["u"] == pytest.approx(math.sqrt(2), rel=0.02)
    assert mc["y"] == pytest.approx(1.0, rel=0.02)


def test_correlacion_total_se_cancela():
    ent = {"a": N(10.0, 1.0), "b": N(10.0, 1.0)}
    f = inc.modelo_desde_expresion("a - b", ["a", "b"])
    g = inc.gum(f, ent, {"a,b": 1.0})
    assert g["u"][0] == pytest.approx(0.0, abs=1e-6) and g["correlacionado"]
    assert inc.gum(f, ent, {"a,b": 0.0})["u"][0] == pytest.approx(math.sqrt(2))
    with pytest.raises(ValueError, match="semidefinida"):
        inc.gum(inc.modelo_desde_expresion("a+b+c", list("abc")),
                {k: N(0, 1) for k in "abc"}, {"a,b": 0.9, "b,c": 0.9, "a,c": -0.9})


def test_welch_satterthwaite_y_salida_vectorial():
    ent = {"a": N(1.0, 1.0, nu=4), "b": N(2.0, 0.0)}
    g = inc.gum(lambda x: np.array([x["a"] + x["b"], 3 * x["a"]]), ent)
    assert g["nu_eff"][0] == pytest.approx(4)
    assert g["k"][0] == pytest.approx(2.7764, abs=1e-4)
    np.testing.assert_allclose(g["u"], [1.0, 3.0], rtol=1e-9)


def test_expresion_segura():
    for mala in ("__import__('os')", "x.real", "open('a')", "[x]", "x if x else 1", "lambda: 1"):
        with pytest.raises((ValueError, SyntaxError)):
            inc.modelo_desde_expresion(mala, ["x"])
    with pytest.raises(ValueError, match="desconocida"):
        inc.modelo_desde_expresion("x + y", ["x"])
    f = inc.modelo_desde_expresion("sqrt(x)*pi + exp(0)", ["x"])
    assert float(f({"x": 4.0})) == pytest.approx(2 * math.pi + 1)


def test_entradas_invalidas():
    f = inc.modelo_desde_expresion("x", ["x"])
    with pytest.raises(ValueError):
        inc.gum(f, {"x": N(1.0, -1.0)})
    with pytest.raises(ValueError, match="distribución"):
        inc.gum(f, {"x": N(1.0, 1.0, distribucion="cauchy")})
    with pytest.raises(ValueError, match="no finitos"):
        inc.monte_carlo(inc.modelo_desde_expresion("log(x)", ["x"]), {"x": N(0.1, 1.0)})


def test_gci_exacto_y_oscilante():
    f = [1 + 0.3 * h ** 2 for h in (0.1, 0.2, 0.4)]
    r = inc.gci(*f, r=2.0)
    assert r["p"] == pytest.approx(2.0) and r["f_ext"] == pytest.approx(1.0)
    assert r["gci"] == pytest.approx(1.25 * abs(f[0] - f[1]) / f[0] / 3)
    with pytest.raises(ValueError, match="oscilante"):
        inc.gci(1.0, 1.1, 0.95, r=2.0)
    assert inc.gci(1.0, 1.1, 0.95, r=2.0, p_formal=2)["Fs"] == 3.0


def test_vv20():
    v = inc.validacion_vv20(S=52.0, D=48.0, u_num=0.5, u_input=1.0, u_D=0.8)
    assert v["E"] == 4.0
    assert v["u_val"] == pytest.approx(math.sqrt(0.25 + 1 + 0.64))
    assert v["error_de_modelo_detectable"] and v["dominante"] == "u_input"
    assert not inc.validacion_vv20(50.2, 50.0, 0.1, 0.1, 0.1)["error_de_modelo_detectable"]
