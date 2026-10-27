"""Amostragem seletiva nos ruídos normais independentes (02 §8; lacunas L7 e L12).

R3383 §2.1: amostra original de ruídos N(0, 1) independentes, agregação por
K-means (Hartigan e Wong, ref. [17]), centroide como representante e fator de
compensação do desvio-padrão aplicado aos vetores agregados (eq. 2.2):
``FC = (Σ_{i=1..N_UHE} 1/σ_i) / N_UHE``, σ_i o desvio dos ruídos agregados da
usina i. Probabilidade do grupo ``P_k = NO_k / N`` (M18 eq. 5.9; NT 42, eq. 6,
no anexo do R13612). Proveniência: P-AGR-01..07 em PROVENIENCIA.md.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

import numpy as np

from .kmeans import ITERACOES, kmns
from .ruidos import N_OBJETOS, amostra_original, sorteia_centros

# P-AGR-04 (lacuna L7): como σ_i é calculado.
#   "ponderado": Σ_k P_k (r_ki - r̄_i)², r̄_i = Σ_k P_k r_ki
#   "simples":   (1/K) Σ_k (r_ki - r̄_i)², r̄_i média simples dos K vetores
#   "amostral":  1/(K-1) no lugar de 1/K
#   "zero":      Σ_k P_k r_ki² (em torno da média 0 da população)
#   "nenhum":    sem compensação (FC = 1)
DESVIOS = ("ponderado", "simples", "amostral", "zero", "nenhum")
# P-AGR-05 (lacuna L7): "escalar" = um FC para todas as usinas (R3383 eq.
# 2.2); "por_usina" = cada componente dividida pelo próprio σ_i.
APLICACOES = ("escalar", "por_usina")


@dataclass(frozen=True)
class OpcoesAgregacao:
    n_objetos: int = N_OBJETOS
    simetria: str = "nenhuma"
    desvio: str = "ponderado"
    aplicacao: str = "escalar"
    iteracoes: int = ITERACOES
    distancia: str = "blas"
    dtype: str = "float64"

    def __post_init__(self):
        if self.desvio not in DESVIOS:
            raise ValueError(self.desvio)
        if self.aplicacao not in APLICACOES:
            raise ValueError(self.aplicacao)


@dataclass(frozen=True)
class Agregacao:
    postos: tuple[int, ...]  # chave de cada coluna (número do posto)
    centroides: np.ndarray  # [K, n] antes do fator
    contagens: np.ndarray  # [K]
    n_objetos: int
    desvios: np.ndarray  # σ_i [n] dos centroides (variante de ``desvio``)
    fator: np.ndarray  # escalar (forma ()) ou [n]
    ruidos: np.ndarray  # [K, n] = fator × centroides
    iteracoes: int
    ifault: int

    @property
    def probabilidades(self) -> np.ndarray:
        """P_k = NO_k / N em float64 (M18 eq. 5.9)."""
        return self.contagens / float(self.n_objetos)


def desvios_dos_centroides(c: np.ndarray, p: np.ndarray, desvio: str) -> np.ndarray:
    """σ_i dos K centroides pela variante ``desvio`` (P-AGR-04)."""
    k = c.shape[0]
    if desvio == "ponderado":
        mu = p @ c
        return np.sqrt(p @ (c - mu) ** 2)
    if desvio in ("simples", "amostral"):
        mu = c.mean(axis=0)
        return np.sqrt(((c - mu) ** 2).sum(axis=0) / (k if desvio == "simples" else k - 1))
    if desvio == "zero":
        return np.sqrt(p @ c ** 2)
    return np.ones(c.shape[1])


def fator_de_compensacao(sigmas: np.ndarray, aplicacao: str) -> np.ndarray:
    """R3383 eq. 2.2: FC = (Σ 1/σ_i)/N_UHE (``aplicacao="escalar"``), com
    N_UHE = número de componentes do vetor agregado; ``"por_usina"`` devolve
    1/σ_i (P-AGR-05)."""
    if np.any(~(sigmas > 0)):
        raise ValueError("desvio nulo nos ruídos agregados")
    inv = 1.0 / sigmas
    return np.asarray(inv.mean()) if aplicacao == "escalar" else inv


def compensar(ag: Agregacao, desvio: str, aplicacao: str) -> Agregacao:
    """Refaz σ_i, o fator e os ruídos de uma agregação com outra variante
    (P-AGR-04, P-AGR-05); os centroides e as contagens não mudam."""
    if ag.contagens.size == 1:
        return ag
    sig = desvios_dos_centroides(ag.centroides, ag.probabilidades, desvio)
    fc = fator_de_compensacao(sig, aplicacao)
    return replace(ag, desvios=sig, fator=fc, ruidos=ag.centroides * fc)


def agregar(postos, k: int, semente: int, opcoes: OpcoesAgregacao | None = None) -> Agregacao:
    """Amostra original (uma coluna por posto), K-means com K grupos,
    centroides e fator de compensação."""
    op = opcoes or OpcoesAgregacao()
    postos = tuple(int(p) for p in postos)
    a = amostra_original(postos, semente, op.n_objetos, op.simetria, dtype=np.dtype(op.dtype))
    if k == 1:
        # P-AGR-06 (ESCOLHA): uma abertura (AS 136 exige K ≥ 2, IFAULT 3):
        # o representante é a média da amostra e não há compensação.
        c = a.mean(axis=0, keepdims=True).astype(np.float64)
        cont = np.array([op.n_objetos])
        sig = np.ones(len(postos))
        return Agregacao(postos, c, cont, op.n_objetos, sig, np.asarray(1.0), c.copy(), 0, 0)
    ini = sorteia_centros(op.n_objetos, k, semente)
    r = kmns(a, a[ini], op.iteracoes, op.distancia)
    c = r.centros.astype(np.float64)
    p = r.contagens / float(op.n_objetos)
    sig = desvios_dos_centroides(c, p, op.desvio)
    fc = fator_de_compensacao(sig, op.aplicacao)
    return Agregacao(postos, c, r.contagens.copy(), op.n_objetos, sig, fc, c * fc, r.iteracoes, r.ifault)
