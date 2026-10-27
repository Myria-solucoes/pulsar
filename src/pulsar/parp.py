"""Ajuste PAR(p) e PAR(p)-A das séries incrementais históricas (02 §4, §5).

Etapas, para cada série (L-PAR, L-PARA, M18 §4.2, R1416 §3):

1. estatísticas mensais e correlograma (``estatisticas``);
2. componente anual ``A_{t-1}`` e sua correlação com a série
   (``componente_anual``, só no PAR(p)-A);
3. FACP de cada mês (``facp``);
4. identificação da ordem pelo intervalo de confiança de 95% com N anos,
   estimação por Yule-Walker e tratamento de coeficientes negativos
   (``ajustar``);
5. resíduos históricos e seus momentos (``residuos``).

As somas são sequenciais em float64, na ordem indicada em cada função: a
ordem das operações foi inferida dos valores float64 gravados no
correli.out (ver PROVENIENCIA.md, P-EST-*, P-ANU-*, P-FACP-*, P-LIN-*).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np

from .historico import SerieIncremental

MESES = 12
# P-EST-05: número de defasagens do correlograma e da FACP (U19 §7,
# "Ordem máxima para FAC do modelo par(p) 11"; L-PAR: "número de meses do
# ano menos 1, ou seja, 11").
DEFASAGENS = 11
# P-ORD-01: ordem máxima quando nem o DADGER (& VAZOES reg. 11) nem o
# GEVAZP.DAT (reg. 15) informam (U19 §7, "Ordem máxima para o modelo par(p)
# 11"; L-PAR, 11).
ORDEM_MAXIMA = 11
# P-ORD-02: quantil da Normal do intervalo de confiança de 95% (M18 eq. 6.15).
Z_95 = 1.96


class ErroAjuste(ValueError):
    pass


@dataclass(frozen=True)
class OpcoesPAR:
    """Opções do ajuste. ``anual`` liga o PAR(p)-A (DADGER ``MODELO PAR-A``)."""

    anual: bool = True
    ordem_maxima: int = ORDEM_MAXIMA
    defasagens: int = DEFASAGENS
    z: float = Z_95
    # P-ORD-03: ordem quando nenhum lag é significativo (INFERIDO no
    # vordem.out; o R27063 é só contexto).
    ordem_minima: int = 1
    # P-FACP-02 (ESCOLHA, lacuna L19): FACP do ramo PAR(p), "yw" = último
    # coeficiente do Yule-Walker de ordem k (M18 §4.2.1; R1416 §2.3) ou
    # "parcial" = correlação parcial (R1416 eq. 9, sem a componente anual).
    facp_parp: str = "yw"
    # P-EST-03 (ESCOLHA, lacuna L19): ordem da soma ("direta" = do 1º ao
    # último ano, "reversa") e forma do cubo ("potencia" = d**3, "produto" =
    # d*d*d) na assimetria da série histórica, sem oráculo público.
    soma_assimetria: str = "direta"
    cubo_assimetria: str = "potencia"
    # P-EST-06 (ESCOLHA, lacuna L19): mês com desvio nulo numa série não
    # nula (ou componente anual de desvio nulo): "erro" interrompe;
    # "ordem_zero" trata a variável padronizada desse mês como 0 (correlações
    # nulas) e força a ordem 0 no mês; com σ^A = 0 só zera as correlações
    # com A no mês (ψ = 0), sem mudar a ordem.
    desvio_nulo: str = "erro"
    # P-LIN-02 (ESCOLHA, lacuna L19): pivô nulo no Gauss-Jordan sem pivô:
    # "erro" ou "lapack" (inversa com pivoteamento parcial do NumPy).
    pivo_nulo: str = "erro"
    # P-LIN-03: solver do Yule-Walker no ramo PAR(p), "cholesky" (INFERIDO
    # nos pacotes de 2022; matriz não positiva definida é erro),
    # "cholesky_ou_gauss_jordan" (nesse caso cai na P-LIN-01; ESCOLHA, sem
    # caso público) ou "gauss_jordan" (o do PAR(p)-A, P-LIN-01).
    solver_parp: str = "cholesky"
    # P-ORD-04: a busca da ordem para antes da primeira defasagem com
    # |φ_kk| > 1 ("corta", INFERIDO nos pacotes de 2022), com |φ_kk| ≥ 1
    # ("corta_igual", ESCOLHA: nenhum φ_kk público é ±1) ou não ("ignora").
    facp_maior_que_1: str = "corta"
    # P-RES-04 (ESCOLHA não discriminável): ordem das somas nos momentos e no
    # correlograma dos resíduos, "direta" ou "reversa".
    soma_residuos: str = "direta"

    def __post_init__(self):
        if self.facp_parp not in ("yw", "parcial"):
            raise ValueError(self.facp_parp)
        for nome, ok in (("soma_assimetria", ("direta", "reversa")), ("cubo_assimetria", ("potencia", "produto")),
                         ("desvio_nulo", ("erro", "ordem_zero")), ("pivo_nulo", ("erro", "lapack")),
                         ("soma_residuos", ("direta", "reversa")),
                         ("solver_parp", ("cholesky", "cholesky_ou_gauss_jordan", "gauss_jordan")),
                         ("facp_maior_que_1", ("corta", "corta_igual", "ignora"))):
            if getattr(self, nome) not in ok:
                raise ValueError(f"{nome}={getattr(self, nome)!r}")
        if not 0 <= self.ordem_maxima <= self.defasagens:
            raise ValueError("ordem máxima fora de 0..defasagens")
        if self.ordem_minima not in (0, 1):
            raise ValueError(self.ordem_minima)


def soma(valores) -> float:
    """Soma sequencial em float64, do primeiro ao último."""
    s = 0.0
    for v in valores:
        s += v
    return s


def _soma_ordem(valores, ordem: str) -> float:
    v = list(valores)
    return soma(v[::-1] if ordem == "reversa" else v)


def _padroniza(x: float, mu: float, sd: float) -> float:
    """(x-μ)/σ; σ = 0 só chega aqui com ``desvio_nulo="ordem_zero"`` (P-EST-06)."""
    return (x - mu) / sd if sd != 0.0 else 0.0


# --------------------------------------------------------------------------
# Estatísticas (02 §4)


@dataclass(frozen=True)
class Estatisticas:
    n_anos: int
    media: np.ndarray  # [12]
    desvio: np.ndarray  # [12]
    assimetria: np.ndarray  # [12]
    fac: np.ndarray  # [k, m-1], k = 0..defasagens; fac[0] = 1


def estatisticas(z: np.ndarray, defasagens: int = DEFASAGENS, opcoes: OpcoesPAR | None = None) -> Estatisticas:
    """Média, desvio, assimetria e correlograma mensais de ``z[ano, mes]``.

    P-EST-01: média = soma sequencial dos anos / N (L-PAR eq. 8).
    P-EST-02: desvio = sqrt(Σ (z-μ)·(z-μ) / N), soma sequencial (L-PAR
    eq. 9; denominador N).
    P-EST-03: assimetria = N/((N-1)(N-2)) Σ ((z-μ)/σ)³ (L-PAR eq. 10), soma
    e cubo conforme ``OpcoesPAR``; NaN quando σ = 0 (P-EST-06).
    P-EST-04: correlograma, ver ``correlograma``.
    P-EST-07: N < 3 é erro (o fator N/((N-1)(N-2)) da eq. 10 não existe).
    """
    op = opcoes or OpcoesPAR()
    n = z.shape[0]
    if n < 3:
        raise ErroAjuste("histórico com menos de 3 anos")
    cols = [z[:, m].tolist() for m in range(MESES)]
    media = [soma(c) / n for c in cols]
    desvio = []
    for m, c in enumerate(cols):
        mu = media[m]
        desvio.append(math.sqrt(soma((v - mu) * (v - mu) for v in c) / n))
    assim = []
    for m, c in enumerate(cols):
        mu, sd = media[m], desvio[m]
        if sd == 0.0:
            assim.append(float("nan"))
            continue
        d = [(v - mu) / sd for v in c]
        cubos = [x ** 3 for x in d] if op.cubo_assimetria == "potencia" else [x * x * x for x in d]
        assim.append(n / ((n - 1) * (n - 2)) * _soma_ordem(cubos, op.soma_assimetria))
    fac = correlograma(z, media, desvio, defasagens)
    return Estatisticas(n, np.array(media), np.array(desvio), np.array(assim), fac)


def correlograma(z: np.ndarray, media, desvio, defasagens: int = DEFASAGENS) -> np.ndarray:
    """P-EST-04: ρ_k^m = [Σ (z_{i,m}-μ_m)(z_{i,m-k}-μ_{m-k})] / N / (σ_m σ_{m-k}).

    A soma percorre os anos do último para o primeiro e omite os pares cujo
    lag cai antes do início do histórico; o divisor continua N (lacuna L2;
    L-PAR eq. 11 escreve 1/N). INFERIDO: bits do correli.out."""
    n = z.shape[0]
    x = z.reshape(-1).tolist()
    fac = np.zeros((defasagens + 1, MESES))
    fac[0] = 1.0
    for k in range(1, defasagens + 1):
        for m in range(MESES):
            mk = (m - k) % MESES
            s = 0.0
            for i in range(n - 1, -1, -1):
                t = MESES * i + m
                if t - k < 0:
                    continue
                s += (x[t] - media[m]) * (x[t - k] - media[mk])
            den = desvio[m] * desvio[mk]
            fac[k, m] = s / n / den if den != 0.0 else 0.0  # σ = 0: P-EST-06
    return fac


# --------------------------------------------------------------------------
# Componente anual do PAR(p)-A (R1416 §3; L-PARA)


@dataclass(frozen=True)
class ComponenteAnual:
    serie: np.ndarray  # [ano, mes-1]: A_{t-1} no mês de t; 1º ano = 0 (indefinido)
    media: np.ndarray  # [12] por mês de t
    desvio: np.ndarray  # [12]
    correlacao: np.ndarray  # [k, m-1] = corr(A_{t-1}, Z_{t-k}), k = 0..defasagens


def componente_anual(z: np.ndarray, est: Estatisticas, defasagens: int = DEFASAGENS,
                     opcoes: OpcoesPAR | None = None) -> ComponenteAnual:
    """P-ANU-01: A_{t-1} = (Σ_{τ=1..12} Z_{t-τ}) / 12, soma do mais antigo ao
    mais recente (R1416 eq. 11; L-PARA eq. 32). No 1º ano não há 12 meses
    anteriores e A fica indefinida (gravada como 0, como na tabela "SERIE DE
    MEDIA ULTIMOS 12 MESES" do GEVAZP.REL).

    P-ANU-02: μ^A e σ^A de cada mês sobre os N-1 anos em que A existe
    (denominador N-1). Divergência com R1416 eq. 17–18 (1/N Σ_{i=1..N}):
    vale o arquivo público.

    P-ANU-03: ρ_{Z,A}(k) = [Σ ((A-μ^A)/σ^A)((Z_{t-k}-μ)/σ)] / N, soma do
    último ano ao 2º, divisor N (R1416 eq. 19 escreve 1/N). k = 0 é a
    correlação com Z_t (eq. 15) e k ≥ 1 com Z_{t-k} (eq. 13).

    μ^A e σ^A usam soma sequencial do 2º ao último ano e o produto d*d, como
    a P-EST-01/02 (INFERIDO pelos bits da FACP, test_facp_bit_a_bit)."""
    op = opcoes or OpcoesPAR()
    n = z.shape[0]
    x = z.reshape(-1).tolist()
    a = [0.0] * len(x)
    for t in range(MESES, len(x)):
        a[t] = soma(x[t - MESES:t]) / MESES
    serie = np.array(a).reshape(n, MESES)
    media, desvio = [], []
    for m in range(MESES):
        c = serie[1:, m].tolist()
        mu = soma(c) / (n - 1)
        media.append(mu)
        desvio.append(math.sqrt(soma((v - mu) * (v - mu) for v in c) / (n - 1)))
    if min(desvio) == 0.0 and op.desvio_nulo == "erro":
        raise ErroAjuste("componente anual com desvio nulo")  # P-EST-06
    mz, sz = est.media, est.desvio
    corr = np.zeros((defasagens + 1, MESES))
    for k in range(defasagens + 1):
        for m in range(MESES):
            mk = (m - k) % MESES
            s = 0.0
            for i in range(n - 1, 0, -1):
                t = MESES * i + m
                s += _padroniza(a[t], media[m], desvio[m]) * _padroniza(x[t - k], mz[mk], sz[mk])
            corr[k, m] = s / n
    return ComponenteAnual(serie, np.array(media), np.array(desvio), corr)


# --------------------------------------------------------------------------
# Álgebra linear


def inversa(a: list[list[float]], pivo_nulo: str = "erro") -> list[list[float]]:
    """P-LIN-01: inversa por Gauss-Jordan sem pivoteamento, no lugar: a linha
    do pivô é dividida pelo pivô (com o elemento do pivô trocado por 1 antes)
    e eliminada das demais linhas. INFERIDO: bits de φ e da FACP no
    correli.out. Divergência: M18 §4.2.2 e L-PAR dizem Cholesky; vale o
    arquivo público.

    P-LIN-02: pivô nulo é erro, ou, com ``pivo_nulo="lapack"``, a inversa
    vem do NumPy (pivoteamento parcial)."""
    n = len(a)
    orig = a
    a = [list(map(float, linha)) for linha in a]
    for i in range(n):
        piv = a[i][i]
        if piv == 0.0:
            if pivo_nulo == "lapack":
                return np.linalg.inv(np.array(orig, dtype=float)).tolist()
            raise ErroAjuste("pivô nulo no Gauss-Jordan sem pivoteamento")
        a[i][i] = 1.0
        a[i] = [v / piv for v in a[i]]
        for r in range(n):
            if r != i:
                f = a[r][i]
                a[r][i] = 0.0
                a[r] = [a[r][j] - a[i][j] * f for j in range(n)]
    return a


def cholesky(a: list[list[float]], b: list[float]) -> list[float]:
    """P-LIN-03: solução de a x = b por Cholesky, a = L L': L por linhas
    (L_ij = (a_ij - Σ_{k<j} L_ik L_jk) / L_jj, L_ii = sqrt(a_ii - Σ L_ik²)),
    substituição direta L y = b e retroativa L' x = y, somas sequenciais em
    k crescente (M18 §4.2.2 e L-PAR: "resolvido por Cholesky"). INFERIDO:
    bits de φ no correli.out dos pacotes de 2022 (ramo PAR(p))."""
    n = len(b)
    lo = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = a[i][j]
            for k in range(j):
                s -= lo[i][k] * lo[j][k]
            if i == j:
                if s <= 0.0:
                    raise ErroAjuste("matriz não positiva definida no Cholesky")
                lo[i][i] = math.sqrt(s)
            else:
                lo[i][j] = s / lo[j][j]
    y = [0.0] * n
    for i in range(n):
        s = b[i]
        for k in range(i):
            s -= lo[i][k] * y[k]
        y[i] = s / lo[i][i]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = y[i]
        for k in range(i + 1, n):
            s -= lo[k][i] * x[k]
        x[i] = s / lo[i][i]
    return x


def _produto(a: list[list[float]], b: list[list[float]]) -> list[list[float]]:
    return [[soma(a[i][l] * b[l][j] for l in range(len(b))) for j in range(len(b[0]))] for i in range(len(a))]


def _matriz(est: Estatisticas, anual: ComponenteAnual | None, m: int, k: int) -> list[list[float]]:
    """Correlações entre (Z_t, Z_{t-1}, ..., Z_{t-k}[, A_{t-1}]), t no mês m
    (0..11). corr(Z_{t-i}, Z_{t-j}) = ρ^{m-i}_{j-i} (L-PAR eq. 16; R1416
    eq. 5); corr(A_{t-1}, Z_{t-j}) = ρ_{Z,A}(j) (R1416 eq. 13, 15, 16)."""
    nz = k + 1
    n = nz + (anual is not None)
    s = [[1.0] * n for _ in range(n)]
    for i in range(nz):
        for j in range(nz):
            if i != j:
                lo, hi = min(i, j), max(i, j)
                s[i][j] = est.fac[hi - lo, (m - lo) % MESES]
        if anual is not None:
            s[i][nz] = s[nz][i] = anual.correlacao[i, m]
    return s


def facp(est: Estatisticas, anual: ComponenteAnual | None, defasagens: int = DEFASAGENS,
         forma_parp: str = "yw", pivo_nulo: str = "erro", solver_parp: str = "cholesky") -> np.ndarray:
    """FACP [k-1, m-1], k = 1..defasagens.

    P-FACP-01 (PAR(p)-A): correlação parcial entre Z_t e Z_{t-k} condicionada
    a Z_{t-1}..Z_{t-k+1} e A_{t-1} (R1416 §3.3, eq. 20–21):
    Σ̄ = Σ11 - (Σ12 Σ22⁻¹) Σ21 e φ_kk = Σ̄12 / (sqrt(Σ̄11) sqrt(Σ̄22)), com a
    inversa da P-LIN-01 e as condicionantes na ordem Z_{t-1}, ..., A_{t-1}.
    INFERIDO: bits do correli.out.

    P-FACP-02 (PAR(p), ESCOLHA, lacuna L19): ``forma_parp`` "yw" = último
    coeficiente do Yule-Walker de ordem k (M18 §4.2.1, eq. 4.5; R1416 §2.3)
    ou "parcial" = a correlação parcial acima sem A_{t-1}."""
    out = np.zeros((defasagens, MESES))
    for k in range(1, defasagens + 1):
        for m in range(MESES):
            if anual is None and forma_parp == "yw":
                out[k - 1, m] = yule_walker(est, None, m, k, pivo_nulo, solver_parp)[0][-1]
                continue
            s = _matriz(est, anual, m, k)
            o1 = [0, k]
            o2 = [i for i in range(len(s)) if i not in o1]
            s11 = [[s[i][j] for j in o1] for i in o1]
            s12 = [[s[i][j] for j in o2] for i in o1]
            s21 = [[s[i][j] for j in o1] for i in o2]
            s22 = [[s[i][j] for j in o2] for i in o2]
            p = _produto(_produto(s12, inversa(s22, pivo_nulo)), s21) if o2 else [[0.0, 0.0], [0.0, 0.0]]
            b = [[s11[i][j] - p[i][j] for j in range(2)] for i in range(2)]
            out[k - 1, m] = b[0][1] / (math.sqrt(b[0][0]) * math.sqrt(b[1][1]))
    return out


def yule_walker(est: Estatisticas, anual: ComponenteAnual | None, m: int, p: int,
                pivo_nulo: str = "erro", solver_parp: str = "cholesky") -> tuple[tuple[float, ...], float | None]:
    """P-YW-01: coeficientes φ_1..φ_p (e ψ no PAR(p)-A) do mês m (0..11) pelo
    sistema de Yule-Walker (L-PAR eq. 16; PAR(p)-A: R1416 eq. 16, L-PARA
    eq. 37), resolvido como x = M⁻¹ b com a inversa da P-LIN-01 e o produto
    em soma sequencial. INFERIDO: bits de φ no correli.out.

    P-LIN-03: no ramo PAR(p) (sem componente anual) o sistema é resolvido por
    Cholesky (``solver_parp="cholesky"``, INFERIDO nos pacotes de 2022)."""
    if p == 0:
        return (), (0.0 if anual is not None else None)
    s = _matriz(est, anual, m, p)
    o = list(range(1, len(s)))
    mat = [[s[i][j] for j in o] for i in o]
    b = [s[i][0] for i in o]
    if anual is None and solver_parp.startswith("cholesky"):
        try:
            return tuple(cholesky(mat, b)), None
        except ErroAjuste:
            if solver_parp != "cholesky_ou_gauss_jordan":
                raise
    inv = inversa(mat, pivo_nulo)
    x = [soma(inv[i][j] * b[j] for j in range(len(b))) for i in range(len(b))]
    if anual is None:
        return tuple(x), None
    return tuple(x[:p]), x[p]


# --------------------------------------------------------------------------
# Identificação, estimação e coeficientes negativos


@dataclass(frozen=True)
class ModeloMes:
    ordem: int
    phi: tuple[float, ...]
    psi: float | None  # None no PAR(p); 0 no PAR(p)-A de ordem 0


@dataclass
class Iteracao:
    """Um passo do tratamento de coeficientes negativos (espelha um bloco
    "USINA:" do vordem.out)."""

    identificadas: list[int]  # ordem identificada pela FACP (P-ORD-03)
    limites: list[int]  # limite da busca na FACP que produziu a ordem
    modelos: list[ModeloMes]  # ordem usada (P-NEG-03) e coeficientes
    fisicos: list[tuple[float, ...]]  # φ'_i (P-NEG-01)
    psi_fisico: list[float]  # ψ' (P-NEG-01)
    contribuicoes: list[list[float]]  # P-NEG-04, lags 1..max(p, 1)
    negativos: list[int]  # meses (0..11) com contribuição negativa


@dataclass
class AjustePAR:
    serie: SerieIncremental
    opcoes: OpcoesPAR
    est: Estatisticas
    anual: ComponenteAnual | None
    facp: np.ndarray
    limiar: float
    iteracoes: list[Iteracao] = field(default_factory=list)

    @property
    def modelos(self) -> list[ModeloMes]:
        return self.iteracoes[-1].modelos

    @property
    def ordens(self) -> tuple[int, ...]:
        return tuple(md.ordem for md in self.modelos)


def limiar_significancia(n_anos: int, z: float = Z_95) -> float:
    """P-ORD-02: |φ_kk| > z/sqrt(N), N = número de anos do histórico (M18
    §4.2.1: variância 1/N; L-PAR: IC de 95% com amostra igual ao número de
    anos)."""
    return z / math.sqrt(n_anos)


def limite_valido(facp_m, limite: int, igual: bool = False) -> int:
    """P-ORD-04: a busca não passa da defasagem anterior à primeira com
    |φ_kk| > 1 (com ``igual``, ≥ 1). No ramo PAR(p) o último coeficiente do
    Yule-Walker de ordem k (P-FACP-02) não é uma correlação e pode passar de
    1; o vordem.out de 2022 mostra que a ordem identificada é sempre menor
    que essa defasagem. INFERIDO:
    test_t4_parp.py::test_ordem_para_antes_da_facp_maior_que_1."""
    for k in range(1, limite + 1):
        v = abs(facp_m[k - 1])
        if v > 1.0 or (igual and v == 1.0):
            return k - 1
    return limite


def identificar(facp_m, limite: int, limiar: float, minimo: int = 1, corte: bool | str = False) -> int:
    """P-ORD-03: maior k ≤ limite com |φ_kk| > limiar (M18 §4.2.1); sem
    nenhum, ``minimo`` (1, INFERIDO no vordem.out; R27063). Limite 0 dá 0.
    Com ``corte`` ("corta" ou True: > 1; "corta_igual": ≥ 1) o limite é
    antes reduzido pela P-ORD-04."""
    if corte and corte != "ignora":
        limite = limite_valido(facp_m, limite, igual=corte == "corta_igual")
    for k in range(limite, 0, -1):
        if abs(facp_m[k - 1]) > limiar:
            return k
    return min(minimo, limite)


def _fisicos(est: Estatisticas, anual: ComponenteAnual | None, m: int, md: ModeloMes):
    """P-NEG-01: φ'_i = φ_i σ_m / σ_{m-i} e ψ' = ψ σ_m / σ^A_m (coeficientes em
    unidades da vazão, como impressos no vordem.out)."""
    def razao(num, den):  # den = 0 só com desvio_nulo="ordem_zero" (P-EST-06)
        return num / den if den != 0.0 else 0.0

    phi = tuple(razao(md.phi[i - 1] * est.desvio[m], est.desvio[(m - i) % MESES]) for i in range(1, md.ordem + 1))
    psi = razao(md.psi * est.desvio[m], anual.desvio[m]) if (anual is not None and md.ordem) else 0.0
    return phi, psi


def _combinados(phi_f, psi_f, n: int) -> list[float]:  # n ≥ 12
    """P-NEG-02: coeficiente de Z_{t-i}, i = 1..n, que combina o PAR(p) e o
    termo anual: φ'_i + ψ'/12 para i ≤ 12, pois A_{t-1} é a média de Z_{t-1}..
    Z_{t-12} (L-PAR "coeficiente ... que combina"; INFERIDO no vordem.out)."""
    c = [0.0] * (n + 1)
    for i, v in enumerate(phi_f, start=1):
        c[i] = v
    if psi_f:
        for i in range(1, MESES + 1):
            c[i] += psi_f / MESES
    return c


def contribuicoes(modelos: list[ModeloMes], fisicos, psi_fisico) -> list[list[float]]:
    """P-NEG-04: contribuição de Z_{t-j} em Z_t, j = 1..max(p_m, 1), após
    substituir Z_{t-1}, ..., Z_{t-j+1} pelos modelos dos seus meses sem os
    resíduos (M18 §6.3, exemplo de fevereiro). INFERIDO: "FUNC. DE <mês>"
    do vordem.out."""
    # Cada substituição alcança no máximo 12 meses além do lag substituído
    # (ordem ≤ 11 e termo anual de 12 meses): 3 anos bastam.
    n = 3 * MESES
    comb = [_combinados(fisicos[m], psi_fisico[m], n) for m in range(MESES)]
    out = []
    for m, md in enumerate(modelos):
        c = comb[m][:]
        f = []
        for j in range(1, max(md.ordem, 1) + 1):
            f.append(c[j])
            if j < md.ordem:
                d = comb[(m - j) % MESES]
                for i in range(1, n - j + 1):
                    c[j + i] += c[j] * d[i]
        out.append(f)
    return out


def ajustar(serie: SerieIncremental, opcoes: OpcoesPAR | None = None) -> AjustePAR:
    """Ajuste completo de uma série não nula (P-HIST-03)."""
    op = opcoes or OpcoesPAR()
    if serie.nula:
        raise ErroAjuste(f"{serie.nome}: incremental nula não recebe modelo")
    z = serie.valores
    est = estatisticas(z, op.defasagens, op)
    if min(est.desvio) == 0.0 and op.desvio_nulo == "erro":
        # P-EST-06 (ESCOLHA, lacuna L19): não aparece nos pacotes públicos.
        raise ErroAjuste(f"{serie.nome}: desvio mensal nulo")
    anual = componente_anual(z, est, op.defasagens, op) if op.anual else None
    fp = facp(est, anual, op.defasagens, op.facp_parp, op.pivo_nulo, op.solver_parp)
    lim_sig = limiar_significancia(est.n_anos, op.z)
    aj = AjustePAR(serie, op, est, anual, fp, lim_sig)

    limites = [op.ordem_maxima] * MESES
    corta = op.facp_maior_que_1
    ident = [identificar(fp[:, m], limites[m], lim_sig, op.ordem_minima, corta) for m in range(MESES)]
    while True:
        modelos, fis, psif = [], [], []
        for m in range(MESES):
            p = 0 if est.desvio[m] == 0.0 else ident[m]  # P-EST-06, "ordem_zero"
            md = ModeloMes(p, *yule_walker(est, anual, m, p, op.pivo_nulo, op.solver_parp))
            phi_f, psi_f = _fisicos(est, anual, m, md)
            # P-NEG-03: ordem 1 com coeficiente combinado de ordem 1 negativo
            # vira ordem 0, sem termo anual (INFERIDO no vordem.out, "AR( 0)"
            # com "PSI: 0.00000"; R27063 "COEFICIENTE DE ORDEM 1 EH NEGATIVO
            # ... MODELO AR(0)"). Divergência: a L-PAR diz "é zero".
            if md.ordem == 1 and phi_f[0] + psi_f / MESES < 0:
                md = ModeloMes(0, (), 0.0 if anual is not None else None)
                phi_f, psi_f = (), 0.0
            modelos.append(md)
            fis.append(phi_f)
            psif.append(psi_f)
        contr = contribuicoes(modelos, fis, psif)
        neg = [m for m in range(MESES) if min(contr[m]) < 0]
        aj.iteracoes.append(Iteracao(list(ident), list(limites), modelos, fis, psif, contr, neg))
        if not neg:
            return aj
        # Guarda (P-NEG-05): cada iteração reduz a ordem de ao menos um mês,
        # então não há mais de ordem_maxima·12 reduções; não muda resultado.
        if len(aj.iteracoes) > op.ordem_maxima * MESES + 1:
            raise ErroAjuste(f"{serie.nome}: tratamento de negativos não convergiu")
        # P-NEG-05: só os meses com contribuição negativa voltam à FACP,
        # procurando o próximo lag significativo abaixo da ordem atual (M18
        # §6.3); os demais mantêm a ordem. INFERIDO no vordem.out.
        for m in neg:
            limites[m] = ident[m] - 1
            ident[m] = identificar(fp[:, m], limites[m], lim_sig, op.ordem_minima, corta)


# --------------------------------------------------------------------------
# Resíduos históricos (L-PAR eq. 17; 02 §5, §9)


@dataclass(frozen=True)
class Residuos:
    valores: np.ndarray  # [ano, mes-1]; 0 onde o resíduo não existe
    validos: np.ndarray  # [ano, mes-1] bool
    media: np.ndarray
    desvio: np.ndarray
    assimetria: np.ndarray
    fac: np.ndarray  # [k-1, m-1], k = 1..defasagens


def residuos(aj: AjustePAR) -> Residuos:
    """P-RES-01: a_t = (Z_t-μ_m)/σ_m - Σ φ_i (Z_{t-i}-μ_{m-i})/σ_{m-i}
    - ψ (A_{t-1}-μ^A_m)/σ^A_m (L-PAR eq. 17; L-PARA eq. 31). No 1º ano, o
    resíduo do mês cuja ordem alcança antes do início do histórico não
    existe (gravado 0) e o termo anual é omitido (A indefinida). INFERIDO:
    "SERIE DE RUIDOS" do GEVAZP.REL.

    P-RES-02: média, desvio (denominador n) e assimetria n/((n-1)(n-2)) de
    cada mês sobre os n resíduos existentes. INFERIDO: "MEDIA/DESVIO
    PADRAO/ASSIMETRIA DA SERIE DE RUIDOS".

    P-RES-03: correlograma com todos os pares (inclusive os resíduos 0 do 1º
    ano) dividido por N, padronizado com a média e o desvio da P-RES-02.
    INFERIDO: "CORRELOGRAMA DA SERIE DE RUIDOS"."""
    z = aj.serie.valores
    n = z.shape[0]
    x = z.reshape(-1).tolist()
    mu, sd = aj.est.media, aj.est.desvio
    an = aj.anual
    a = an.serie.reshape(-1).tolist() if an is not None else None
    r = [0.0] * len(x)
    ok = [False] * len(x)
    for t in range(len(x)):
        m = t % MESES
        md = aj.modelos[m]
        if t - md.ordem < 0:
            continue
        v = _padroniza(x[t], mu[m], sd[m])
        for i in range(1, md.ordem + 1):
            mi = (m - i) % MESES
            v -= md.phi[i - 1] * _padroniza(x[t - i], mu[mi], sd[mi])
        if an is not None and md.ordem and t >= MESES:
            v -= md.psi * _padroniza(a[t], an.media[m], an.desvio[m])
        r[t], ok[t] = v, True
    val = np.array(r).reshape(n, MESES)
    vok = np.array(ok).reshape(n, MESES)
    ordem = aj.opcoes.soma_residuos  # P-RES-04
    media, desvio, assim = [], [], []
    for m in range(MESES):
        c = val[vok[:, m], m].tolist()
        k = len(c)
        if k < 3:
            # P-EST-07: a assimetria (L-PAR eq. 10) não existe com menos de 3
            # resíduos no mês (N = 3 e ordem que alcança antes do início).
            raise ErroAjuste(f"{aj.serie.nome}: mês {m + 1} com {k} resíduos")
        mm = _soma_ordem(c, ordem) / k
        ss = math.sqrt(_soma_ordem([(v - mm) * (v - mm) for v in c], ordem) / k)
        media.append(mm)
        desvio.append(ss)
        # P-RES-02; NaN com desvio nulo (P-EST-06)
        assim.append(k / ((k - 1) * (k - 2)) * _soma_ordem([((v - mm) / ss) ** 3 for v in c], ordem)
                     if ss else float("nan"))
    nl = aj.opcoes.defasagens
    fac = np.zeros((nl, MESES))
    for k in range(1, nl + 1):
        for m in range(MESES):
            mk = (m - k) % MESES
            p = [(r[MESES * i + m] - media[m]) * (r[MESES * i + m - k] - media[mk])
                 for i in range(n) if MESES * i + m - k >= 0]
            den = desvio[m] * desvio[mk]
            fac[k - 1, m] = _soma_ordem(p, ordem) / n / den if den else float("nan")
    return Residuos(val, vok, np.array(media), np.array(desvio), np.array(assim), fac)


# --------------------------------------------------------------------------
# Deck inteiro


def opcoes_do_deck(deck, par_a_outros: str = "parp", fonte_ordem_maxima: str = "dadger",
                   ordem_maxima_zero: str = "vale") -> OpcoesPAR:
    """Opções do ajuste a partir do deck.

    P-PAR-01: PAR(p)-A quando o & VAZOES traz ``MODELO PAR-A`` = 1 (rótulo
    INFERIDO, P-DADG-08; REL "AJUSTA MODELO ESTOCASTICO PAR-A SIM"); registro
    ausente ou 0 dá PAR(p). Outro valor: ``par_a_outros`` = "parp" ou "erro"
    (ESCOLHA, lacuna L19).

    P-ORD-01: ordem máxima = & VAZOES reg. 11 (U19 §4.5) ou GEVAZP.DAT reg.
    15 (U19 §3.3); com os dois preenchidos vale ``fonte_ordem_maxima``
    ("dadger" ou "gevazp"); sem nenhum, 11 (U19 §7). Um 0 explícito vale como
    ordem máxima 0 (``ordem_maxima_zero="vale"``) ou como ausente
    ("ausente"). ESCOLHAs da lacuna L19."""
    if par_a_outros not in ("parp", "erro") or fonte_ordem_maxima not in ("dadger", "gevazp") \
            or ordem_maxima_zero not in ("vale", "ausente"):
        raise ValueError("opção inválida")
    v = deck.dadger.vazoes if deck.dadger is not None else None
    flag = v.modelo_par_a if v is not None else None
    if flag not in (None, 0, 1) and par_a_outros == "erro":
        raise ErroAjuste(f"MODELO PAR-A = {flag}")
    anual = flag == 1

    def valor(x):
        return None if (x is None or (x == 0 and ordem_maxima_zero == "ausente")) else x

    do_dadger = valor(v.ordem_maxima if v is not None else None)
    gd = getattr(deck, "gevazp", None)
    do_gevazp = valor(gd.ordem_maxima if gd is not None else None)
    fontes = (do_dadger, do_gevazp) if fonte_ordem_maxima == "dadger" else (do_gevazp, do_dadger)
    ordem = next((x for x in fontes if x is not None), ORDEM_MAXIMA)
    return OpcoesPAR(anual=anual, ordem_maxima=ordem)


def ajustar_deck(deck, config, opcoes: OpcoesPAR | None = None, sem_reg16: str = "mesma") -> list[AjustePAR]:
    """Ajusta todas as séries selecionadas pela P-HIST-03 na ordem da
    configuração; ``sem_reg16`` é o parâmetro da P-HIST-03."""
    from .historico import series_ajustadas, series_incrementais

    op = opcoes or opcoes_do_deck(deck)
    v = deck.dadger.vazoes if deck.dadger is not None else None
    reg16 = v.ajuste_todas if v is not None else None
    series = series_ajustadas(series_incrementais(deck.historico, config), reg16, sem_reg16)
    return [ajustar(s, op) for s in series]
