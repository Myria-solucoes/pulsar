"""T11: fórmulas dos testes do M18 cap. 6 (P-ACE-05), sem deck."""

import math

import numpy as np
import pytest

import base  # noqa: F401
from pulsar.estocastico import aceitacao as A


def test_cramer_von_mises_eq_6_20_e_6_21():
    """Com folhas equiprováveis, W² = Σ (F0(x_i) - (2i-1)/(2N))² + 1/(12N)
    (eq. 6.20) e T = (W² - 0,4/N + 0,6/N²)(1 + 1/N) (eq. 6.21); crítico 0,46
    a 5% (Tabela 6.3)."""
    rng = np.random.default_rng(0)
    x = rng.random(57)
    n = len(x)
    f0 = lambda v: np.asarray(v)  # noqa: E731  uniforme(0, 1)
    xs = np.sort(x)
    w2 = np.sum((xs - (2 * np.arange(1, n + 1) - 1) / (2 * n)) ** 2) + 1 / (12 * n)
    t = (w2 - 0.4 / n + 0.6 / n ** 2) * (1 + 1 / n)
    assert A.cvm(x, np.full(n, 1 / n, dtype=np.float32), f0) == pytest.approx(t, rel=1e-6)
    assert A.CVM_CRITICO == 0.46
    # amostra da própria distribuição raramente rejeita; uma deslocada sempre
    rej = [A.cvm(rng.random(200), np.full(200, 1 / 200, np.float32), f0) > A.CVM_CRITICO for _ in range(400)]
    assert 0.02 < np.mean(rej) < 0.09
    assert A.cvm(rng.random(200) ** 3, np.full(200, 1 / 200, np.float32), f0) > A.CVM_CRITICO


def test_valores_padrao_da_tabela_6_1():
    """Linhas da Tabela 6.1 do M18 nos nós; interpolação linear entre eles e
    valor da linha extrema fora de 0,05–1,10."""
    assert A.valores_padrao(0.5) == (-1.8305, 2.0673)
    assert A.valores_padrao(1.0) == (-1.1970, 1.8652)
    lo, hi = A.valores_padrao(0.4)
    assert lo == pytest.approx((-1.9311 - 1.8305) / 2) and hi == pytest.approx((2.0045 + 2.0673) / 2)
    assert A.valores_padrao(0.01) == (-1.9661, 1.9570) and A.valores_padrao(3.0) == (-0.9889, 1.6254)


def test_desvio_rejeitado_eq_6_18():
    """Intervalo σ + VP·√Var(s), Var(s) da eq. 6.17b com η² = e^{σ_n²} - 1."""
    sx, s, k = 0.5, 10.0, 259
    e = math.exp(sx * sx) - 1
    dp = math.sqrt(s * s * (e ** 4 + 6 * e ** 3 + 15 * e ** 2 + 16 * e + 2) / (4 * k))
    assert not A.desvio_rejeitado(s + 2.06 * dp, s, sx, k)
    assert A.desvio_rejeitado(s + 2.07 * dp, s, sx, k)
    assert not A.desvio_rejeitado(s - 1.83 * dp, s, sx, k)
    assert A.desvio_rejeitado(s - 1.84 * dp, s, sx, k)
