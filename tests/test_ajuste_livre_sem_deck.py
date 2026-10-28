"""Ferramenta de descoberta do limite inferior (ferramentas/ajuste_livre_limite.py,
P-LN3-09): o ajuste livre recupera M_t de cenários sintéticos com W na
imagem de uma matriz de posto incompleto, sem conhecer a regra nem os
momentos."""

import sys

import numpy as np

import base
from pulsar.estocastico.lognormal import parametros

sys.path.insert(0, str(base.RAIZ / "ferramentas"))
import ajuste_livre_limite as A  # noqa: E402


def _caso(semente=0, n=8, anos=6, folhas=120):
    rng = np.random.default_rng(semente)
    x = rng.standard_normal((anos, n))
    x = (x - x.mean(0)) / x.std(0)
    u = x.T @ x / anos  # posto anos - 1
    lam, a = np.linalg.eigh(u)
    d = (a * np.sqrt(np.clip(lam, 0, None))) @ a.T
    w = rng.standard_normal((folhas, n)) @ d.T
    cond = [(rng.uniform(2, 5), rng.uniform(5, 50), 0.0, rng.uniform(0.5, 0.9)) for _ in range(n)]
    m = np.array([sig * rng.uniform(0.2, 1.5) for _, sig, _, _ in cond])
    z = np.stack([sig * (c + parametros(c, sig, mu, sd, "inferida", limite_vazao=mt).ruido(w[:, i]))
                  for i, ((c, sig, mu, sd), mt) in enumerate(zip(cond, m))], 1)
    p = rng.integers(50, 300, folhas)
    return z, cond, a[:, lam < 1e-10], p, m


def test_recupera_m_com_os_momentos_certos():
    """O resíduo no M_t verdadeiro já é ~1e-8: √λ dos autovalores nulos com
    erro de arredondamento (~1e-16) deixa ~1e-8 de W no núcleo, o mesmo piso
    dos pacotes públicos (docs/limite-inferior.md)."""
    z, cond, k, p, m = _caso()
    a = A.Ajuste(z, cond, k, p)
    assert 1e-9 < a.residuo(m) < 1e-7
    m0 = np.minimum(0.0, a.zmin - 0.1 * a.sig)
    assert a.residuo(m0) > 1e-3
    mt, _ = a.ajustar_m(m0)
    assert a.residuo(mt) < 1e-7
    assert np.allclose(mt, m, rtol=1e-5)


def test_recupera_m_com_escala_e_deslocamento_livres():
    """Com momentos errados (σ_a 10% maior), o ajuste só de M_t não fecha;
    com escala e deslocamento livres, fecha e devolve o M_t verdadeiro."""
    z, cond, k, p, m = _caso(1)
    errado = [(c, s, mu, 1.1 * sd) for c, s, mu, sd in cond]
    a = A.Ajuste(z, errado, k, p)
    m0 = np.minimum(0.0, a.zmin - 0.1 * a.sig)
    mt, _ = a.ajustar_m(m0)
    (ml, al, be), _ = a.ajustar_livre(mt)
    assert a.residuo(ml, al, be) < 1e-7 < a.residuo(mt) * 1e-2
    assert np.allclose(ml, m, rtol=1e-5)


def test_corte_de_menor_erro():
    """O corte usado para derivar os limiares cai entre os dois grupos e
    tolera um caso do lado errado."""
    t, e = A.corte([0.1, 0.5, 0.99, 1.7], [1.01, 1.2, 1.9])
    assert e == 1 and 0.99 < t < 1.01
    t, e = A.corte([-3.5, -3.01], [-2.99, -2.0])
    assert e == 0 and -3.01 < t < -2.99
