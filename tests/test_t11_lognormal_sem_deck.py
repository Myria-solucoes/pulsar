"""T11: lognormal de três parâmetros (P-LN3-01..08) e condicional do lateral (P-LAT-01), sem deck."""

import math

import numpy as np
import pytest

import base  # noqa: F401
from pulsar.estocastico import lognormal as L
from pulsar.estocastico.geracao import condicional_lateral


@pytest.mark.parametrize("c,mu_a,sd_a", [(3.0, 0.0, 0.8), (1.2, 0.0, 0.95), (0.4, 0.05, 0.6)])
def test_momentos_preservados(c, mu_a, sd_a):
    """P-LN3-01 (L-LN3 eq. 22–27): com W ~ N(0, 1), a_t = e^{σ_ξ W + μ_ξ} + Δ
    tem média μ_a e desvio σ_a (fórmulas fechadas da lognormal)."""
    p = L.parametros(c, 10.0, mu_a, sd_a, "zero")
    assert p.delta == -c
    media = p.delta + math.exp(p.mu_xi + p.sigma_xi ** 2 / 2)
    var = math.exp(2 * p.mu_xi + p.sigma_xi ** 2) * (math.exp(p.sigma_xi ** 2) - 1)
    assert media == pytest.approx(mu_a, abs=1e-12)
    assert math.sqrt(var) == pytest.approx(sd_a, rel=1e-12)
    a = p.ruido(np.random.default_rng(0).standard_normal(400_000))
    assert a.min() > p.delta  # Z_t = σ_m (c + a_t) > 0 na rota "zero"
    assert abs(a.mean() - mu_a) < 0.01 and abs(a.std() - sd_a) < 0.01


@pytest.mark.parametrize("gama", [0.3, 1.0, 2.5])
def test_cubica_da_assimetria(gama):
    """P-LN3-03 (L-LN3 eq. 25): θ = 1 + η² é a raiz real de θ³ + 3θ² - (4 + γ²)
    e a lognormal resultante tem assimetria γ; Δ = μ_a - σ_a/η."""
    eta = L.eta_da_assimetria(gama)
    th = 1 + eta * eta
    assert th ** 3 + 3 * th ** 2 - (4 + gama ** 2) == pytest.approx(0, abs=1e-9)
    assert (th + 2) * math.sqrt(th - 1) == pytest.approx(gama, rel=1e-12)
    p = L.parametros(5.0, 1.0, 0.0, 0.7, "cubica_residuos", gama=gama)
    assert p.delta == pytest.approx(-0.7 / eta)
    assert math.exp(p.sigma_xi ** 2) == pytest.approx(th, rel=1e-12)
    with pytest.raises(L.ErroLognormal):
        L.eta_da_assimetria(-0.1)
    # sem assimetria positiva a rota cúbica recai na "zero"
    assert L.parametros(5.0, 1.0, 0.0, 0.7, "cubica_vazoes", gama=-0.2).delta == -5.0


def test_limite_por_quantis_e_rota():
    """P-LN3-03: estimador de Stedinger (1980) recupera o limite de uma
    amostra lognormal deslocada; Δ = M/σ_m - c (Z > M, L-LN3 eq. 18)."""
    rng = np.random.default_rng(1)
    x = 40.0 + np.exp(rng.normal(3.0, 0.5, 20_001))
    tau = L.limite_por_quantis(x)
    assert abs(tau - 40.0) < 1.0
    assert L.limite_por_quantis(np.array([1.0, 2.0, 3.0])) is None  # simétrica
    p = L.parametros(6.0, 10.0, 0.0, 0.5, "quantis", limite_vazao=tau)
    assert p.delta == pytest.approx(tau / 10.0 - 6.0)
    assert L.parametros(4.0, 10.0, 0.0, 0.5, "quantis", limite_vazao=None).delta == -4.0


def test_sem_lognormal():
    """P-LN3-06: com μ_a - Δ < 0 (média condicional negativa na rota "zero")
    o padrão "quadrado" segue a eq. 24 com (μ_a - Δ)²: Z = σ_m e^ξ > 0 com
    média σ_m |c|; "erro" recusa; "normal" usa a_t = μ_a + σ_a W. μ_a = Δ
    exato e σ_a ≤ 0 são sempre erro."""
    p = L.parametros(-0.2, 1.0, 0.0, 0.5)
    assert not p.normal and p.delta == 0.2
    assert p.delta + math.exp(p.mu_xi + p.sigma_xi ** 2 / 2) == pytest.approx(0.2 + 0.2)
    with pytest.raises(L.ErroLognormal):
        L.parametros(-0.2, 1.0, 0.0, 0.5, sem_lognormal="erro")
    p = L.parametros(-0.2, 1.0, 0.0, 0.5, sem_lognormal="normal")
    assert p.normal and np.allclose(p.ruido(np.array([0.0, 1.0])), [0.0, 0.5])
    for variante in ("quadrado", "erro", "normal"):
        with pytest.raises(L.ErroLognormal):
            L.parametros(0.0, 1.0, 0.0, 0.5, sem_lognormal=variante)
    with pytest.raises(L.ErroLognormal):
        L.parametros(1.0, 1.0, 0.0, 0.0)


def test_condicional_do_lateral():
    """P-LAT-01 (M18 eq. 4.19–4.20): com um principal, W1 = ρ W2 + √(1-ρ²) b1;
    com dois, o coeficiente é Σ12 Σ22⁻¹ e E² = 1 - Σ12 Σ22⁻¹ Σ12'."""
    g, e = condicional_lateral(np.array([0.9]), np.array([[1.0]]))
    assert g.tolist() == [0.9] and e == pytest.approx(math.sqrt(1 - 0.81))
    s12 = np.array([0.6, 0.5])
    s22 = np.array([[1.0, 0.3], [0.3, 1.0]])
    g, e = condicional_lateral(s12, s22)
    assert np.allclose(s22 @ g, s12) and e * e == pytest.approx(1 - s12 @ np.linalg.solve(s22, s12))
    rng = np.random.default_rng(2)
    w2 = rng.standard_normal((200_000, 2)) @ np.linalg.cholesky(s22).T
    w1 = w2 @ g + e * rng.standard_normal(200_000)
    assert abs(w1.std() - 1) < 0.01
    assert np.allclose([np.corrcoef(w1, w2[:, j])[0, 1] for j in range(2)], s12, atol=0.01)


def _momentos(x):
    x = np.asarray(x, float)
    n, mu, sd = x.size, x.mean(), x.std()
    return mu, sd, n / ((n - 1) * (n - 2)) * (((x - mu) / sd) ** 3).sum()


def test_limite_inferido_ramos():
    """P-LN3-09..13: fração do menor valor não negativo por faixa de
    assimetria, cúbica no lugar da base com 2 ≤ γ < 4, piso μ - 3σ e
    μ - 3σ direto com mais de 15% de negativos."""
    r = L.RegraLimite()
    assert [r.fracao(g) for g in (-0.5, 0.999, 1.0, 1.999, 2.0, 3.999, 4.0, 9.0)] == \
        [0.15, 0.15, 0.35, 0.35, 0.5, 0.5, 0.6, 0.6]
    assert L.RegraLimite(limiar_inclusivo=False).fracao(1.0) == 0.15
    # fração do mínimo (piso bem abaixo)
    assert L.limite_inferido(np.array([10.0, 30.0]), 50.0, 30.0, 0.5) == pytest.approx(1.5)
    assert L.limite_inferido(np.array([10.0, 30.0]), 50.0, 30.0, 1.5) == pytest.approx(3.5)
    assert L.limite_inferido(np.array([10.0, 30.0]), 50.0, 30.0, 5.0) == pytest.approx(6.0)
    # menor valor não negativo
    assert L.limite_inferido(np.array([-5.0, 0.5, 8.0] + [9.0] * 20), 50.0, 30.0, 0.5) == pytest.approx(0.075)
    # piso μ - 3σ
    assert L.limite_inferido(np.array([10.0, 30.0]), 50.0, 5.0, 0.5) == pytest.approx(35.0)
    # cúbica τ = μ - σ/η(γ) em (0, mínimo) com 2 ≤ γ < 4: base = τ
    g = 2.5
    tau = 50.0 - 30.0 / L.eta_da_assimetria(g)
    assert 0 < tau < 40.0
    assert L.limite_inferido(np.array([40.0, 90.0]), 50.0, 30.0, g) == pytest.approx(0.5 * tau)
    assert L.limite_inferido(np.array([5.0, 90.0]), 50.0, 30.0, g) == pytest.approx(2.5)  # τ > mínimo
    # mais de 15% de negativos: μ - 3σ direto, mesmo abaixo da fração
    x = np.array([-1.0] * 16 + [3.0] * 84)
    mu, sd, gm = _momentos(x)
    assert L.limite_inferido(x, mu, sd, gm) == pytest.approx(mu - 3 * sd)
    x = np.array([-1.0] * 15 + [3.0] * 85)
    mu, sd, gm = _momentos(x)
    assert L.limite_inferido(x, mu, sd, gm) == pytest.approx(max(L.RegraLimite().fracao(gm) * 3.0, mu - 3 * sd))
    # sem valor não negativo: base 0 (P-LN3-13, ESCOLHA)
    assert L.limite_inferido(np.array([-1.0, -2.0]), -1.5, 0.5, 0.0, L.RegraLimite(limiar_negativos=1.0)) == 0.0
