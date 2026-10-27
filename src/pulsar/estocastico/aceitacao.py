"""Estatísticas de aceitação da árvore gerada (03 §5; M18 cap. 6; T10 e T11).

Todas as estatísticas usam as probabilidades das folhas. Proveniência:
P-ACE-01..07 em PROVENIENCIA.md.
"""

from __future__ import annotations

import math

import numpy as np

QUARTIS = (0.25, 0.50, 0.75)
# P-ACE-05: valores críticos a 5% (M18 eq. 6.15 e Tabela 6.2, N > 50).
T_CRITICO = 1.96
KS_COEFICIENTE = 1.36
# P-ACE-05: Cramér–von Mises, T crítico a 5% (M18 eq. 6.21 e Tabela 6.3).
CVM_CRITICO = 0.46
# P-ACE-05: valores-padrão do intervalo de 95% do desvio (M18 eq. 6.18 e
# Tabela 6.1): σ_n (parâmetro de forma da lognormal, σ_ξ) -> (inferior, superior).
VALORES_PADRAO = (
    (0.05, -1.9661, 1.9570),
    (0.07, -1.9650, 1.9648),
    (0.10, -1.9439, 1.9850),
    (0.30, -1.9311, 2.0045),
    (0.50, -1.8305, 2.0673),
    (0.70, -1.6777, 2.1220),
    (0.80, -1.5493, 2.0849),
    (0.90, -1.3965, 2.0005),
    (1.00, -1.1970, 1.8652),
    (1.10, -0.9889, 1.6254),
)


def pesos(p) -> np.ndarray:
    """Probabilidades das folhas (float32 do PROBVAZ.DAT) em float64."""
    return np.asarray(p, dtype=np.float32).astype(np.float64)


def media_desvio(x: np.ndarray, p) -> tuple[np.ndarray, np.ndarray]:
    """P-ACE-01 (F2-REL-01, INFERIDO): média = Σ p x e desvio =
    √(Σ p x² - μ²), p = probabilidades em float32 ("MEDIA GER"/"DESPAD GER"
    do TCOND.REL e do QUANTIL.CSV)."""
    w = pesos(p)
    mu = w @ x
    return mu, np.sqrt(np.maximum(w @ (x * x) - mu * mu, 0.0))


def assimetria(x: np.ndarray, p) -> np.ndarray:
    """P-ACE-02 (ESCOLHA): Σ p ((x - μ)/σ)³, sem correção de amostra."""
    w = pesos(p)
    mu = w @ x
    d = x - mu
    s = np.sqrt(w @ (d * d))
    with np.errstate(invalid="ignore", divide="ignore"):
        return (w @ d ** 3) / s ** 3


def quantis(x: np.ndarray, p, qs=QUARTIS) -> np.ndarray:
    """P-ACE-03 (INFERIDO, QUANTIL.CSV): quantil q = maior valor cuja
    probabilidade acumulada (valores em ordem crescente, probabilidades
    float32 somadas em float64) é menor que q; o menor valor se nenhuma for.
    ``x`` [K] ou [K, n]; devolve [len(qs)] ou [len(qs), n]."""
    w = pesos(p)
    x = np.asarray(x, dtype=np.float64)
    um = x.ndim == 1
    x2 = x[:, None] if um else x
    out = np.zeros((len(qs), x2.shape[1]))
    for j in range(x2.shape[1]):
        o = np.argsort(x2[:, j], kind="stable")
        cw = np.cumsum(w[o])
        for i, q in enumerate(qs):
            out[i, j] = x2[o[max(int(np.searchsorted(cw, q, side="left")) - 1, 0)], j]
    return out[:, 0] if um else out


def correlacao(x: np.ndarray, p) -> np.ndarray:
    """P-ACE-04: correlação ponderada entre colunas (03 §5; TESTES.REL,
    "CORRELACAO ESPACIAL SINTETICA ENTRE AS USINAS")."""
    w = pesos(p)
    d = x - w @ x
    cov = (d * w[:, None]).T @ d
    s = np.sqrt(np.diag(cov))
    with np.errstate(invalid="ignore", divide="ignore"):
        return cov / np.outer(s, s)


def t_media(media_ger, media_teo, desvio_teo, k: int):
    """M18 eq. 6.14–6.15: |média gerada - teórica| / (σ_teo/√K). INFERIDO:
    coluna "T-VALOR" da média no TCOND.REL (P-ACE-05)."""
    return np.abs(media_ger - media_teo) / (desvio_teo / math.sqrt(k))


def t_desvio(desvio_ger, desvio_teo, theta, k: int):
    """M18 eq. 6.17b: Var(s) = σ²(η⁸ + 6η⁶ + 15η⁴ + 16η² + 2)/(4N), η² = θ - 1
    o quadrado do coeficiente de variação da lognormal (P-ACE-05)."""
    e = np.asarray(theta) - 1.0
    v = desvio_teo ** 2 * (e ** 4 + 6 * e ** 3 + 15 * e ** 2 + 16 * e + 2) / (4 * k)
    return np.abs(desvio_ger - desvio_teo) / np.sqrt(v)


def valores_padrao(sigma_xi: float) -> tuple[float, float]:
    """VP inferior e superior da Tabela 6.1 do M18 para σ_n = σ_ξ, com
    interpolação linear entre as linhas e o valor da linha extrema fora da
    faixa 0,05–1,10 (P-ACE-05, ESCOLHA: a tabela não diz como interpolar)."""
    n = [r[0] for r in VALORES_PADRAO]
    return (float(np.interp(sigma_xi, n, [r[1] for r in VALORES_PADRAO])),
            float(np.interp(sigma_xi, n, [r[2] for r in VALORES_PADRAO])))


def desvio_rejeitado(desvio_ger, desvio_teo, sigma_xi: float, k: int) -> bool:
    """M18 eq. 6.18: o desvio gerado fica fora de
    [σ + VP_inf·√Var(s), σ + VP_sup·√Var(s)], Var(s) da eq. 6.17b com
    η² = e^{σ_ξ²} - 1 e VP da Tabela 6.1 (P-ACE-05)."""
    e = math.exp(sigma_xi * sigma_xi) - 1.0
    dp = math.sqrt(desvio_teo ** 2 * (e ** 4 + 6 * e ** 3 + 15 * e ** 2 + 16 * e + 2) / (4 * k))
    lo, hi = valores_padrao(sigma_xi)
    return not (desvio_teo + lo * dp <= desvio_ger <= desvio_teo + hi * dp)


def _phi(z):
    return 0.5 * (1.0 + np.vectorize(math.erf)(np.asarray(z) / math.sqrt(2.0)))


def cdf_ln3(z, sigma_m: float, c: float, delta: float, mu_xi: float, sigma_xi: float):
    """CDF teórica de Z_t = σ_m (c + Δ + e^ξ), ξ ~ N(μ_ξ, σ_ξ²) (L-LN3 eq. 26–27)."""
    u = np.asarray(z, dtype=np.float64) / sigma_m - c - delta
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(u > 0, _phi((np.log(np.where(u > 0, u, 1.0)) - mu_xi) / sigma_xi), 0.0)


def ks(x: np.ndarray, p, f0) -> float:
    """M18 eq. 6.19 com a função de distribuição empírica ponderada:
    D = máx |F_p(x) - F0(x)|, nos dois lados de cada salto."""
    w = pesos(p)
    o = np.argsort(x, kind="stable")
    xs, cw = x[o], np.cumsum(w[o])
    f = f0(xs)
    return float(max(np.max(np.abs(cw - f)), np.max(np.abs(cw - w[o] - f))))


def cvm(x: np.ndarray, p, f0) -> float:
    """Cramér–von Mises (M18 §6.2.3.2): W² da eq. 6.20 e T da eq. 6.21,
    T = (W² - 0,4/N + 0,6/N²)(1 + 1/N), N = número de folhas.

    Com folhas não equiprováveis (P-ACE-05, ESCOLHA), W² = N Σ_k p_k
    (F0(x_k) - S_k)² + 1/(12N), com S_k = acumulada até o meio do salto de
    x_k; com p_k = 1/N, S_k = (2k-1)/(2N) e a fórmula é a eq. 6.20."""
    w = pesos(p)
    n = len(x)
    o = np.argsort(x, kind="stable")
    xs, wk = x[o], w[o]
    meio = np.cumsum(wk) - wk / 2
    w2 = n * float(np.sum(wk * (f0(xs) - meio) ** 2)) + 1.0 / (12 * n)
    return (w2 - 0.4 / n + 0.6 / n ** 2) * (1.0 + 1.0 / n)


def ks_critico(k: int) -> float:
    return KS_COEFICIENTE / math.sqrt(k)


def dentro_da_faixa(sementes: np.ndarray, oficial: np.ndarray, inferior: float = 5.0,
                    superior: float = 95.0) -> np.ndarray:
    """03 §5 item 4: estatística oficial entre os percentis 5 e 95 das
    sementes (``sementes`` [S, ...], ``oficial`` [...]); NaN fica fora."""
    lo = np.nanpercentile(sementes, inferior, axis=0)
    hi = np.nanpercentile(sementes, superior, axis=0)
    return (oficial >= lo) & (oficial <= hi)
