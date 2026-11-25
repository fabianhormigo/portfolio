"""Funciones estadísticas sin dependencias externas: cuantiles de la t de Student.

Se usan para el factor de cobertura con grados de libertad efectivos
(GUM, JCGM 100:2008, anexo G, G.3 y G.6.4).

Implementación: función beta incompleta regularizada por fracción continua
(algoritmo de Lentz modificado) y bisección sobre la función de distribución.
Precisión de la bisección: 1e-12. Verificada en tests frente a valores tabulados.
"""

from __future__ import annotations

import math
from statistics import NormalDist


def _beta_cf(a: float, b: float, x: float) -> float:
    """Fracción continua de la beta incompleta (Lentz modificado)."""
    tiny = 1e-300
    qab, qap, qam = a + b, a + 1.0, a - 1.0
    c, d = 1.0, 1.0 - qab * x / qap
    d = 1.0 / (d if abs(d) > tiny else tiny)
    h = d
    for m in range(1, 10_000):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + aa / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-15:
            return h
    raise ArithmeticError("La fracción continua de la beta incompleta no converge.")


def beta_incompleta_regularizada(a: float, b: float, x: float) -> float:
    """I_x(a, b)."""
    if not 0.0 <= x <= 1.0:
        raise ValueError("x fuera de [0, 1]")
    if x in (0.0, 1.0):
        return x
    ln_bt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(x) + b * math.log1p(-x)
    bt = math.exp(ln_bt)
    if x < (a + 1.0) / (a + b + 2.0):
        return bt * _beta_cf(a, b, x) / a
    return 1.0 - bt * _beta_cf(b, a, 1.0 - x) / b


def cdf_t(t: float, nu: float) -> float:
    """P(T ≤ t) para la t de Student con ν grados de libertad."""
    if math.isinf(nu):
        return NormalDist().cdf(t)
    x = nu / (nu + t * t)
    cola = 0.5 * beta_incompleta_regularizada(nu / 2.0, 0.5, x)
    return 1.0 - cola if t >= 0 else cola


def factor_cobertura(nu: float, p: float) -> float:
    """k = t_p(ν): cuantil bilateral de la t de Student para probabilidad de cobertura p.

    GUM G.3.4 y tabla G.2. Si ν es infinito, cuantil de la normal.
    GUM G.6.4: ν_eff no entero → se trunca al entero inferior (se hace aquí).
    """
    if not 0.0 < p < 1.0:
        raise ValueError("p debe estar en (0, 1)")
    objetivo = 0.5 + p / 2.0
    if math.isinf(nu):
        return NormalDist().inv_cdf(objetivo)
    nu = math.floor(nu)
    if nu < 1:
        raise ValueError("ν_eff < 1: no se puede calcular el factor de cobertura.")
    lo, hi = 0.0, 1.0
    while cdf_t(hi, nu) < objetivo:
        hi *= 2.0
    while hi - lo > 1e-12:
        mid = 0.5 * (lo + hi)
        if cdf_t(mid, nu) < objetivo:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def grados_libertad_efectivos(contribuciones: list[tuple[float, float]]) -> float:
    """ν_eff = u_c⁴ / Σ (c_i·u_i)⁴ / ν_i  (fórmula de Welch–Satterthwaite, GUM G.4.1, ec. G.2b).

    contribuciones: lista de (|c_i·u_i|, ν_i). ν_i = inf para tipo B sin
    incertidumbre sobre su valor (GUM G.4.3, pág. 86).
    """
    u_c2 = sum(c * c for c, _ in contribuciones)
    denom = sum(c ** 4 / nu for c, nu in contribuciones if not math.isinf(nu) and c > 0)
    if denom == 0.0:
        return math.inf
    return u_c2 * u_c2 / denom
