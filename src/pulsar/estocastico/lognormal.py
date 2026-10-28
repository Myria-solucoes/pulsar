"""Lognormal de três parâmetros dos ruídos do PAR(p)/PAR(p)-A (02 §9; lacuna L8).

L-LN3 eq. 18–27 e M18 §4.3.1, eq. 4.10–4.15: com o passado fixo, o ruído
``a_t`` é lognormal com deslocamento ``Δ_t`` (limite inferior de ``a_t``):

- ``a_t = e^{ξ_t} + Δ_t`` e ``ξ_t = σ_ξ W_t + μ_ξ`` (eq. 26–27), W_t o ruído
  normal padrão já correlacionado espacialmente (L-RUID);
- ``θ = 1 + σ_a² / (μ_a - Δ_t)²``, ``σ_ξ² = ln θ`` e
  ``μ_ξ = ½ ln(σ_a² / (θ² - θ))`` (eq. 22–24), que preservam a média μ_a e o
  desvio σ_a de ``a_t``.

O limite inferior ``M_t`` das vazões (L-LN3: "pode ser igual a zero, ou pode
ser um valor estimado com base na distribuição") foi identificado nos
cenários publicados (frente F11): ``limite_inferido`` dá M_t em função só do
histórico do mês (P-LN3-09..13).

Proveniência: P-LN3-01..13 em PROVENIENCIA.md.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

# P-LN3-03 (lacuna L8): rotas para o limite inferior; "inferida" = P-LN3-09.
ROTAS = ("inferida", "zero", "cubica_residuos", "cubica_vazoes", "quantis")
# P-LN3-04: momentos μ_a, σ_a usados no ajuste ("historicos" INFERIDO na F11).
MOMENTOS = ("historicos", "teoricos")
# P-LN3-06: o que fazer quando μ_a - Δ_t ≤ 0 (a média do ruído não fica
# acima do limite): "quadrado" usa a eq. 24 como escrita, com (μ_a - Δ_t)²
# (INFERIDO no 202610); "erro"; "normal" (a_t = μ_a + σ_a W).
SEM_LOGNORMAL = ("quadrado", "erro", "normal")


class ErroLognormal(ValueError):
    pass


@dataclass(frozen=True)
class ParametrosLN3:
    delta: float  # Δ_t, limite inferior de a_t
    mu_xi: float
    sigma_xi: float
    mu_a: float
    sigma_a: float
    normal: bool = False  # True: a_t = μ_a + σ_a W (P-LN3-06, "normal")

    def ruido(self, w: np.ndarray) -> np.ndarray:
        """a_t a partir do ruído normal padrão correlacionado W (eq. 26–27)."""
        w = np.asarray(w, dtype=np.float64)
        if self.normal:
            return self.mu_a + self.sigma_a * w
        return np.exp(self.sigma_xi * w + self.mu_xi) + self.delta

    def inversa(self, a: np.ndarray) -> np.ndarray:
        """Inversa de ``ruido``: W a partir de a_t (a_t > Δ_t)."""
        a = np.asarray(a, dtype=np.float64)
        if self.normal:
            return (a - self.mu_a) / self.sigma_a
        return (np.log(a - self.delta) - self.mu_xi) / self.sigma_xi


def eta_da_assimetria(gama: float) -> float:
    """Raiz real η = √(θ - 1) da cúbica da eq. 25 da L-LN3,
    θ³ + 3θ² - (4 + γ²) = 0, que equivale a η³ + 3η = γ (assimetria da
    lognormal: γ = (θ + 2)√(θ - 1)); fórmula de Cardano, única raiz real.
    Só existe lognormal com γ > 0 (L-LN3: "só é possível para distribuições
    que possuam assimetria positiva")."""
    if not gama > 0:
        raise ErroLognormal(f"assimetria {gama!r} não positiva")
    r = math.sqrt(gama * gama + 4.0)
    return math.cbrt((gama + r) / 2.0) + math.cbrt((gama - r) / 2.0)


@dataclass(frozen=True)
class RegraLimite:
    """Parâmetros da regra do limite inferior M_t (P-LN3-09..13).

    ``fracoes[k]`` vale para a assimetria γ abaixo de ``limiares[k]`` (e a
    última fração acima do último limiar); ``limiar_inclusivo`` diz se γ
    igual ao limiar já passa para a fração seguinte (só importa no empate
    exato, que nenhum pacote público mostra). ``faixa_cubica``: faixa de γ em
    que a base é min(mínimo, cúbica) quando a cúbica está em (0, mínimo);
    ``cubica_extremos`` diz se cada extremo da faixa entra (padrão: γ = 2
    entra, γ = 4 não, como os limiares com ``limiar_inclusivo``; nenhum
    pacote público tem γ exatamente nesses valores). ``limiar_negativos``: acima dessa fração de valores negativos no mês,
    M_t = μ - k σ direto. ``k_desvios``: piso μ - k σ."""

    fracoes: tuple[float, ...] = (0.15, 0.35, 0.5, 0.6)
    limiares: tuple[float, ...] = (1.0, 2.0, 4.0)
    limiar_inclusivo: bool = True
    faixa_cubica: tuple[float, float] = (2.0, 4.0)
    cubica_extremos: tuple[bool, bool] = (True, False)
    limiar_negativos: float = 0.15
    k_desvios: float = 3.0

    def fracao(self, gama: float) -> float:
        for f, t in zip(self.fracoes, self.limiares):
            if gama < t or (gama == t and not self.limiar_inclusivo):
                return f
        return self.fracoes[len(self.limiares)]

    def na_faixa_cubica(self, gama: float) -> bool:
        lo, hi = self.faixa_cubica
        (ilo, ihi) = self.cubica_extremos
        return (lo < gama or (ilo and gama == lo)) and (gama < hi or (ihi and gama == hi))


def limite_inferido(x: np.ndarray, media: float, desvio: float, gama: float,
                    regra: RegraLimite | None = None) -> float:
    """M_t das vazões do mês (lacuna L8), INFERIDO nos 61 pacotes públicos
    (P-LN3-09..13), a partir das vazões históricas ``x`` do mês (incrementais
    da janela da F3) e da média, do desvio (denominador N) e da assimetria
    dessas vazões (P-EST-01..03):

    1. se a fração de valores negativos passa de ``limiar_negativos``,
       M_t = μ - 3σ (P-LN3-12);
    2. base = menor valor não negativo (0 se não houver); com 2 ≤ γ < 4 e a
       raiz da cúbica da eq. 25 nas vazões, τ = μ - σ/η(γ), em (0, base),
       base = τ (P-LN3-11);
    3. M_t = f(γ) · base, f = 0,15 / 0,35 / 0,5 / 0,6 para γ < 1 / < 2 / < 4
       / ≥ 4 (P-LN3-10);
    4. M_t = max(M_t, μ - 3σ) (P-LN3-12)."""
    r = regra or RegraLimite()
    x = np.asarray(x, dtype=np.float64)
    piso = media - r.k_desvios * desvio
    if np.count_nonzero(x < 0) / x.size > r.limiar_negativos:
        return float(piso)
    nao_neg = x[x >= 0]
    base = float(nao_neg.min()) if nao_neg.size else 0.0  # P-LN3-13 (ESCOLHA sem valor ≥ 0)
    if r.na_faixa_cubica(gama):
        tau = media - desvio / eta_da_assimetria(gama)
        if 0.0 < tau < base:
            base = tau
    return float(max(r.fracao(gama) * base, piso))


def limite_por_quantis(x: np.ndarray) -> float | None:
    """Estimador do limite inferior da lognormal de três parâmetros pelos
    quantis extremos e mediano (Stedinger, 1980, WRR 16(3), "Fitting log
    normal distributions to hydrologic data"):
    τ = (x_min x_max - x_med²) / (x_min + x_max - 2 x_med). Devolve None se
    o denominador não for positivo ou se τ ≥ x_min (estimativa inválida)."""
    x = np.sort(np.asarray(x, dtype=np.float64))
    lo, hi, med = float(x[0]), float(x[-1]), float(np.median(x))
    den = lo + hi - 2.0 * med
    if not den > 0:
        return None
    tau = (lo * hi - med * med) / den
    return tau if tau < lo else None


def parametros(c: float, sigma_m: float, mu_a: float, sigma_a: float, rota: str = "zero",
               gama: float | None = None, limite_vazao: float | None = None,
               sem_lognormal: str = "quadrado") -> ParametrosLN3:
    """Parâmetros da lognormal no período, com ``c`` = μ_m/σ_m + Σ φ_i
    (Z_{t-i} - μ_{m-i})/σ_{m-i} (+ ψ (A_{t-1} - μ^A)/σ^A no PAR(p)-A): a
    vazão gerada é Z_t = σ_m (c + a_t) (M18 eq. 4.9a; L-LN3 eq. 18).

    Rotas para o limite inferior (P-LN3-03, lacuna L8):

    - "inferida" (padrão em ``OpcoesGeracao``): M_t = ``limite_vazao``,
      dado por ``limite_inferido`` (P-LN3-09); Δ_t = M_t/σ_m - c;
    - "zero": M_t = 0 em Z (L-LN3, "pode ser igual a zero"): Δ_t = -c
      (eq. 21 com M = 0), isto é, Z_t > 0;
    - "cubica_residuos" / "cubica_vazoes": θ da cúbica da eq. 25 com a
      assimetria ``gama`` (dos resíduos do mês ou das vazões do mês, como
      escreve a L-LN3), e Δ_t = μ_a - σ_a/√(θ - 1), o limite inferior da
      lognormal com média μ_a, desvio σ_a e assimetria γ (Burges et al.,
      1975; Charbeneau, 1978). Sem assimetria positiva, a rota "zero";
    - "quantis": M_t = ``limite_vazao`` (estimativa do limite inferior das
      vazões do mês, ``limite_por_quantis``); Δ_t = M_t/σ_m - c, com Z_t > M_t
      (eq. 18). Sem estimativa válida, a rota "zero".

    P-LN3-06: com μ_a - Δ_t ≤ 0 não há lognormal com média μ_a acima do
    limite. ``sem_lognormal="quadrado"`` (padrão, INFERIDO: TRES IRMAOS e
    SAO MANOEL no 202610, média teórica negativa no TCOND.REL e cenários
    todos positivos no GEVAZP.OUT) aplica a eq. 24 com (μ_a - Δ_t)², o que
    dá à parte lognormal média |μ_a - Δ_t|; "erro" recusa; "normal" usa
    a_t = μ_a + σ_a W. Com μ_a - Δ_t = 0 exato, sempre erro."""
    if rota not in ROTAS:
        raise ValueError(rota)
    if sem_lognormal not in SEM_LOGNORMAL:
        raise ValueError(sem_lognormal)
    if not sigma_a > 0:
        raise ErroLognormal(f"desvio do ruído {sigma_a!r} não positivo")
    delta = -c
    if rota.startswith("cubica") and gama is not None and gama > 0:
        delta = mu_a - sigma_a / eta_da_assimetria(gama)
    elif rota in ("quantis", "inferida") and limite_vazao is not None:
        delta = limite_vazao / sigma_m - c
    if not math.isfinite(delta):
        # limite inferior infinito ou indefinido: não há lognormal.
        raise ErroLognormal(f"limite {delta!r} não finito")
    folga = mu_a - delta
    if folga == 0.0:
        # P-LN3-06: θ indefinido (divisão por zero na eq. 24) em qualquer variante.
        raise ErroLognormal(f"média do ruído {mu_a!r} igual ao limite {delta!r}")
    if folga < 0 and sem_lognormal != "quadrado":
        if sem_lognormal == "erro":
            raise ErroLognormal(f"média do ruído {mu_a!r} não fica acima do limite {delta!r}")
        return ParametrosLN3(delta, float("nan"), float("nan"), mu_a, sigma_a, normal=True)
    theta = 1.0 + sigma_a * sigma_a / (folga * folga)
    sigma_xi = math.sqrt(math.log(theta))
    mu_xi = 0.5 * math.log(sigma_a * sigma_a / (theta * theta - theta))
    return ParametrosLN3(delta, mu_xi, sigma_xi, mu_a, sigma_a)
