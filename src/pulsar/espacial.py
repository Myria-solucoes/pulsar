"""Correlação espacial das incrementais e matriz de carga D (02 §6).

Etapas (M18 §4.3.2; L-CORR eq. 28–30; L-RUID):

1. correlação espacial lag zero das **vazões** incrementais históricas, por
   mês e anual (``correlacao_espacial``), com as séries e a janela da F3;
2. seleção das séries que recebem ruído pela matriz de carga
   (``series_da_carga``, lacuna L4);
3. decomposição espectral pelo método de Jacobi (``jacobi``, Numerical
   Recipes §11.1, ref. [16] do M18) e ``D = A √V A'`` (``matriz_de_carga``),
   com A = autovetores e V = autovalores.

As somas da correlação são sequenciais em float64, do primeiro ao último
ano, como as da F3: a ordem foi inferida dos float64 gravados no
correli.out (P-ESP-*).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from .configuracao import LATERAL
from .historico import SerieIncremental

MESES = 12
ANUAL = 12  # índice da matriz anual em CorrelacaoEspacial.matriz
# P-ESP-06: número máximo de varreduras do Jacobi (NR §11.1, "Too many
# iterations in routine jacobi" depois de 50).
VARREDURAS_MAXIMAS = 50


class ErroCorrelacao(ValueError):
    pass


# --------------------------------------------------------------------------
# Correlação espacial (T5)


@dataclass(frozen=True)
class CorrelacaoEspacial:
    """Correlações lag zero entre as séries, na ordem de ``nomes``.

    ``matriz[m]`` (m = 0..11) é a do mês m+1; ``matriz[ANUAL]`` a das médias
    do ano civil. Diagonal 1; pares com série de desvio nulo valem 0."""

    numeros: tuple[int, ...]
    nomes: tuple[str, ...]
    matriz: np.ndarray  # [13, n, n]

    def mes(self, m: int) -> np.ndarray:
        """Matriz do mês m do calendário (1..12)."""
        return self.matriz[m - 1]

    @property
    def anual(self) -> np.ndarray:
        return self.matriz[ANUAL]

    def restrita(self, numeros) -> CorrelacaoEspacial:
        """Submatriz das séries ``numeros`` (na ordem dada)."""
        pos = {n: k for k, n in enumerate(self.numeros)}
        idx = [pos[n] for n in numeros]
        return CorrelacaoEspacial(tuple(numeros), tuple(self.nomes[k] for k in idx),
                                  self.matriz[:, idx][:, :, idx])


def _soma_anos(x: np.ndarray) -> np.ndarray:
    """Soma sequencial ao longo do eixo 0 (anos), do primeiro ao último.

    Vetorizada nas outras dimensões: cada elemento é somado na mesma ordem
    que ``parp.soma`` faria, então os bits são os mesmos."""
    s = np.zeros(x.shape[1:])
    for k in range(x.shape[0]):
        s = s + x[k]
    return s


def _correlacao(x: np.ndarray, nulas: np.ndarray, desvio_nulo: str = "erro") -> np.ndarray:
    """x[ano, série] -> matriz de correlação [série, série].

    P-ESP-01: ρ_ij = [Σ (x_i-μ_i)(x_j-μ_j)] / N / (σ_i σ_j), anos do primeiro ao
    último, com μ e σ (denominador N) de P-EST-01/02.
    P-ESP-02: diagonal = 1 exato.
    P-ESP-03: par com série de incremental identicamente nula (``nulas``) vale
    0; σ = 0 numa série não nula segue ``desvio_nulo``: "erro" (padrão, como
    a P-EST-06) ou "zero" (pares desse mês valem 0)."""
    n = x.shape[0]
    mu = _soma_anos(x) / n
    d = x - mu
    sd = np.sqrt(_soma_anos(d * d) / n)
    if np.any((sd == 0.0) & ~nulas) and desvio_nulo == "erro":
        raise ErroCorrelacao("desvio nulo numa série não nula (P-ESP-03, desvio_nulo='erro')")
    s = np.zeros((x.shape[1], x.shape[1]))
    for k in range(n):
        s = s + np.multiply.outer(d[k], d[k])
    den = np.multiply.outer(sd, sd)
    with np.errstate(divide="ignore", invalid="ignore"):
        r = np.where(den != 0.0, s / n / den, 0.0)
    np.fill_diagonal(r, 1.0)
    return r


def medias_anuais(z: np.ndarray) -> np.ndarray:
    """P-ESP-04: média do ano civil = soma sequencial de jan a dez / 12."""
    s = np.zeros(z.shape[0])
    for m in range(MESES):
        s = s + z[:, m]
    return s / MESES


def correlacao_espacial(series: list[SerieIncremental], desvio_nulo: str = "erro") -> CorrelacaoEspacial:
    """Correlação espacial histórica mensal e anual das séries dadas (mesma
    janela de anos em todas, P-HIST-02). ``desvio_nulo``: ver P-ESP-03 em
    ``_correlacao`` (ESCOLHA, lacuna L19)."""
    if desvio_nulo not in ("erro", "zero"):
        raise ValueError(desvio_nulo)
    if not series:
        raise ErroCorrelacao("nenhuma série")
    anos = series[0].anos
    if any(s.anos != anos for s in series):
        raise ErroCorrelacao("séries com janelas de anos diferentes")
    if len(anos) < 2:
        raise ErroCorrelacao("histórico com menos de 2 anos")
    z = np.stack([s.valores for s in series], axis=-1)  # [ano, mes, serie]
    nulas = np.array([s.nula for s in series])
    mats = [_correlacao(z[:, m, :], nulas, desvio_nulo) for m in range(MESES)]
    mats.append(_correlacao(np.stack([medias_anuais(s.valores) for s in series], axis=-1), nulas, desvio_nulo))
    return CorrelacaoEspacial(tuple(s.numero for s in series), tuple(s.nome for s in series), np.array(mats))


# --------------------------------------------------------------------------
# Séries que entram na matriz de carga (lacuna L4)


def series_da_carga(series: list[SerieIncremental], laterais: str = "fora") -> list[SerieIncremental]:
    """P-ESP-05: séries correlacionadas pela matriz de carga.

    Partem das séries com modelo (P-HIST-03: sem PN e sem incremental nula).
    O posto lateral (status PL) recebe ruído condicionado aos principais
    depois da matriz de carga (M18 §4.3.3.1, eq. 4.19–4.20; L-VIAG eq.
    55–56); ``laterais="fora"`` o exclui, ``"dentro"`` o mantém."""
    if laterais not in ("fora", "dentro"):
        raise ValueError(laterais)
    com_modelo = [s for s in series if not s.nula]
    if laterais == "dentro":
        return com_modelo
    return [s for s in com_modelo if s.status != LATERAL]


# --------------------------------------------------------------------------
# Decomposição espectral pelo método de Jacobi (NR §11.1)


@dataclass(frozen=True)
class Espectro:
    autovalores: np.ndarray  # [n], na ordem das colunas de autovetores (sem ordenar)
    autovetores: np.ndarray  # [n, n], coluna k = autovetor k
    rotacoes: int
    varreduras: int


def jacobi(a, varreduras_maximas: int = VARREDURAS_MAXIMAS) -> Espectro:
    """P-ESP-06: rotina ``jacobi`` do Numerical Recipes in Fortran 77 (2ª ed.,
    §11.1), citada pelo M18 §4.3.2 [16]: varreduras cíclicas pelo triângulo
    superior; limiar 0,2·S/n² nas três primeiras varreduras e 0 depois (S =
    soma dos |a_pq| fora da diagonal); depois da 4ª, elementos desprezíveis
    diante das duas entradas da diagonal são zerados sem rotação; a diagonal
    é atualizada pelo acumulador z ao fim de cada varredura; para quando S
    é exatamente 0; erro depois de ``varreduras_maximas``. S é somado em
    sequência, linha a linha do triângulo superior (laço em p e depois em q),
    como no NR.

    Guarda do Pulsar, não do NR (que só lê o triângulo superior): matriz que
    não seja simétrica bit a bit é recusada (P-ESP-06).

    As atualizações de linhas e colunas de uma rotação são vetorizadas: cada
    elemento depende só do seu par (a_j,p, a_j,q) anterior à rotação, então
    o resultado é o mesmo do laço em j do NR."""
    a = np.array(a, dtype=np.float64, copy=True)
    n = a.shape[0]
    if a.shape != (n, n):
        raise ErroCorrelacao("matriz não quadrada")
    if not np.array_equal(a, a.T):
        raise ErroCorrelacao("matriz não simétrica")
    v = np.eye(n)
    b = np.diag(a).copy()
    d = b.copy()
    z = np.zeros(n)
    nrot = 0
    triu = np.triu_indices(n, 1)
    for i in range(1, varreduras_maximas + 1):
        sm = 0.0
        for x in np.abs(a[triu]).tolist():  # triu_indices: ordem p, q do NR
            sm += x
        if sm == 0.0:
            return Espectro(d, v, nrot, i - 1)
        tresh = 0.2 * sm / (n * n) if i < 4 else 0.0
        for ip in range(n - 1):
            for iq in range(ip + 1, n):
                apq = a[ip, iq]
                g = 100.0 * abs(apq)
                if i > 4 and abs(d[ip]) + g == abs(d[ip]) and abs(d[iq]) + g == abs(d[iq]):
                    a[ip, iq] = 0.0
                elif abs(apq) > tresh:
                    h = d[iq] - d[ip]
                    if abs(h) + g == abs(h):
                        t = apq / h
                    else:
                        theta = 0.5 * h / apq
                        t = 1.0 / (abs(theta) + math.sqrt(1.0 + theta * theta))
                        if theta < 0.0:
                            t = -t
                    c = 1.0 / math.sqrt(1.0 + t * t)
                    s = t * c
                    tau = s / (1.0 + c)
                    h = t * apq
                    z[ip] -= h
                    z[iq] += h
                    d[ip] -= h
                    d[iq] += h
                    a[ip, iq] = 0.0
                    # j < ip: a(j,ip), a(j,iq)
                    gg, hh = a[:ip, ip].copy(), a[:ip, iq].copy()
                    a[:ip, ip] = gg - s * (hh + gg * tau)
                    a[:ip, iq] = hh + s * (gg - hh * tau)
                    # ip < j < iq: a(ip,j), a(j,iq)
                    gg, hh = a[ip, ip + 1:iq].copy(), a[ip + 1:iq, iq].copy()
                    a[ip, ip + 1:iq] = gg - s * (hh + gg * tau)
                    a[ip + 1:iq, iq] = hh + s * (gg - hh * tau)
                    # j > iq: a(ip,j), a(iq,j)
                    gg, hh = a[ip, iq + 1:].copy(), a[iq, iq + 1:].copy()
                    a[ip, iq + 1:] = gg - s * (hh + gg * tau)
                    a[iq, iq + 1:] = hh + s * (gg - hh * tau)
                    # autovetores
                    gg, hh = v[:, ip].copy(), v[:, iq].copy()
                    v[:, ip] = gg - s * (hh + gg * tau)
                    v[:, iq] = hh + s * (gg - hh * tau)
                    nrot += 1
        b = b + z
        d = b.copy()
        z = np.zeros(n)
    raise ErroCorrelacao(f"Jacobi sem convergência em {varreduras_maximas} varreduras")


# --------------------------------------------------------------------------
# Matriz de carga


@dataclass(frozen=True)
class MatrizDeCarga:
    numeros: tuple[int, ...]
    d: np.ndarray  # [n, n], W = D b
    espectro: Espectro
    autovalores_usados: np.ndarray  # V depois do tratamento (P-ESP-07)


def raiz_dos_autovalores(lam: np.ndarray, nao_positivos: str = "zero") -> np.ndarray:
    """P-ESP-07 (ESCOLHA, lacuna L4): autovalores negativos. Uma correlação
    amostral com mais séries que anos é semidefinida positiva de posto ≤
    N-1; os autovalores "nulos" saem do Jacobi como ±1e-15. "zero" (padrão)
    usa √max(λ, 0); "abs" usa √|λ|; "erro" recusa λ < 0."""
    if nao_positivos == "zero":
        return np.sqrt(np.maximum(lam, 0.0))
    if nao_positivos == "abs":
        return np.sqrt(np.abs(lam))
    if nao_positivos == "erro":
        if np.any(lam < 0.0):
            raise ErroCorrelacao(f"autovalor negativo {float(lam.min())!r}")
        return np.sqrt(lam)
    raise ValueError(nao_positivos)


def matriz_de_carga(u: np.ndarray, numeros=(), nao_positivos: str = "zero",
                    varreduras_maximas: int = VARREDURAS_MAXIMAS, soma_produto: str = "numpy") -> MatrizDeCarga:
    """P-ESP-08: D = A √V A' (M18 eq. 4.17–4.18; L-CORR eq. 30), A = autovetores
    (colunas) e V = autovalores de U pelo Jacobi; D_ij = Σ_k (A_ik √V_k) A_jk.

    ``soma_produto`` (ESCOLHA, sem oráculo; lacuna L22): "numpy" (padrão,
    produto de matrizes do NumPy) ou "sequencial" (k crescente, em float64)."""
    if soma_produto not in ("numpy", "sequencial"):
        raise ValueError(soma_produto)
    esp = jacobi(u, varreduras_maximas)
    r = raiz_dos_autovalores(esp.autovalores, nao_positivos)
    a = esp.autovetores
    ar = a * r
    if soma_produto == "numpy":
        d = ar @ a.T
    else:
        d = np.zeros_like(a)
        for k in range(a.shape[1]):
            d = d + np.multiply.outer(ar[:, k], a[:, k])
    return MatrizDeCarga(tuple(numeros), d, esp, r * r)


def matriz_do_estudo(corr: CorrelacaoEspacial, mes_estocastico: int, flag_correlacao: int | None) -> np.ndarray:
    """P-ESP-09: U do período estocástico. & VAZOES reg. 13 (U19 §4.5) = 1:
    matriz do mês do calendário do período estocástico; 0: matriz anual,
    decomposta também pelo Jacobi (não parametrizada: nenhuma fonte pública
    descreve outro método; lacuna L22). Ausente ou outro valor: recusa
    explícita (``ErroCorrelacao``), como a P-TEND-08 na lacuna L18."""
    if flag_correlacao == 1:
        return corr.mes(mes_estocastico)
    if flag_correlacao == 0:
        return corr.anual
    raise ErroCorrelacao(f"flag da matriz de correlação cruzada = {flag_correlacao!r}")
