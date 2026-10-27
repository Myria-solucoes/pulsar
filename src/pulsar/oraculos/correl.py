"""correli.out e correlt.out: estatísticas das séries incrementais e totais.

U19 §5.2 só cita os arquivos ("arquivos de dados para interface gráfica").
Layout inferido dos pacotes públicos; ver docs/layout-correli.out.md e
docs/layout-correlt.out.md. Resumo:

* acesso direto, RECL = 120 bytes (15 palavras de 8 bytes);
* registro 1: int32 N (séries no índice); registros 2..N+1: pares int32
  (NINT da série, registro inicial do seu bloco);
* um bloco de L registros por série do índice, na ordem do índice;
* dentro do bloco, posições calculadas com N (nl = 11 defasagens):

  correli: média, desvio, FAC[nl], FACP[nl], AR[12], hist[NH], média gerada,
  desvio gerado, FAC gerada[nl], sint[N], anual
  correlt: média, desvio, FAC[nl], hist[NH], média gerada, desvio gerado,
  FAC gerada[nl], sint[N], anual

* registros de estatística: 12 float64 (jan..dez);
* registro AR: int32 ordem p, seguido de p float64 a partir do byte 5;
* registros de correlação: int32 i, int32 j, 13 float64 (12 meses + anual);
* registro anual: 5 float64 (média, desvio, autocorrelação lag 1 das médias
  anuais do ano civil, e dois campos não identificados).

Há duas ordens de séries. A parte histórica do bloco (média, desvio, FAC,
FACP, AR e correlações históricas) é gravada no bloco de posição q da lista
H; no correli, H = índice + séries de incremental nula (157 contra 155), o
que desloca essa parte em relação ao ponteiro do índice e faz o arquivo
terminar no meio do bloco 157. A parte gerada (média, desvio e FAC gerados,
correlações sintéticas e registro anual) segue o índice. Como as posições
são calculadas com N, as duas últimas linhas de cada seção histórica caem
sobre a média e o desvio gerados e se perdem. O leitor usa as marcas (i, j)
de cada linha de correlação e devolve NaN para o que foi sobrescrito.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .acesso_direto import f8, i4, ler_bytes, numero_de_registros, registro

RECL = 120
MESES = 12
N_DEFASAGENS = 11


@dataclass(frozen=True)
class EstatisticaAnual:
    media: float
    desvio: float
    autocorrelacao_lag1: float
    campo4_nao_identificado: float
    campo5_nao_identificado: float


@dataclass(frozen=True)
class SerieCorrel:
    """Estatísticas de uma série. Os campos da parte gerada são None para as
    séries que estão em H mas não no índice (incremental nula)."""

    nint: int
    media: np.ndarray  # [12] média mensal histórica
    desvio: np.ndarray  # [12] desvio-padrão mensal histórico
    fac: np.ndarray  # [defasagem-1, mes-1] correlograma histórico
    facp: np.ndarray | None  # [defasagem-1, mes-1] FACP histórica (só correli)
    ordens: tuple[int, ...] | None  # ordem final do modelo por mês (só correli)
    coeficientes: tuple[np.ndarray, ...] | None  # phi_1..phi_p por mês
    media_gerada: np.ndarray | None  # [12], média ponderada pelas probabilidades
    desvio_gerado: np.ndarray | None  # [12]
    fac_gerada: np.ndarray | None  # [defasagem-1, mes-1]
    anual: EstatisticaAnual | None


@dataclass(frozen=True)
class Correl:
    tipo: str  # "incremental" ou "total"
    indice: tuple[int, ...]  # NINT das séries com bloco, na ordem dos blocos
    lista_historica: tuple[int, ...]  # lista H da seção histórica
    tamanho_bloco: int
    series: dict[int, SerieCorrel]
    corr_historica: dict[tuple[int, int], np.ndarray]  # [13]: 12 meses + anual
    corr_sintetica: dict[tuple[int, int], np.ndarray]

    def serie(self, nint: int) -> SerieCorrel:
        return self.series[nint]

    def correlacao_historica(self, i: int, j: int) -> np.ndarray:
        """Correlação espacial histórica mensal (12) e anual (1) entre i e j.
        NaN onde o arquivo perdeu o valor (linha sobrescrita)."""
        return self.corr_historica[(i, j)]

    def correlacao_sintetica(self, i: int, j: int) -> np.ndarray:
        return self.corr_sintetica[(i, j)]


def _posicoes(tipo: str, n: int, nl: int) -> dict[str, int]:
    p = {"media": 1, "desvio": 2, "fac": 3}
    k = 3 + nl
    if tipo == "incremental":
        p["facp"] = k
        k += nl
        p["ar"] = k
        k += MESES
    p["hist"] = k
    k += n
    p["media_gerada"] = k
    p["desvio_gerado"] = k + 1
    p["fac_gerada"] = k + 2
    k += 2 + nl
    p["sint"] = k
    k += n
    p["anual"] = k
    return p


def ler_correl(caminho, tipo: str, n_defasagens: int = N_DEFASAGENS) -> Correl:
    if tipo not in ("incremental", "total"):
        raise ValueError("tipo deve ser 'incremental' ou 'total'")
    dados = ler_bytes(caminho)
    nreg = numero_de_registros(dados, RECL, str(caminho))
    reg = lambda k: registro(dados, RECL, k)  # noqa: E731

    n = i4(reg(1))
    pares = [(i4(reg(k)), i4(reg(k), 4)) for k in range(2, n + 2)]
    indice = tuple(i for i, _ in pares)
    inicios = [p for _, p in pares]
    passos = set(np.diff(inicios))
    if len(passos) != 1:
        raise ValueError(f"{caminho}: blocos de tamanhos diferentes {passos}")
    tam = int(passos.pop())
    pos = _posicoes(tipo, n, n_defasagens)
    # F2-CI-10: o bloco é alocado para NH séries nas seções histórica e
    # sintética (L = 17 + 3·nl + 2·NH no correli, 5 + 2·nl + 2·NH no correlt),
    # mas as posições usam N; logo NH = N + (L - posição do anual)/2.
    folga = tam - pos["anual"]
    if folga < 0 or folga % 2:
        raise ValueError(f"{caminho}: bloco de {tam} registros incompatível com o layout")
    nh = n + folga // 2
    primeiro = inicios[0]

    def rb(q: int, off: int) -> bytes | None:
        k = primeiro + q * tam + off - 1
        return reg(k) if k <= nreg else None

    def meses(q, off, nlin=1):
        return np.array([f8(rb(q, off + t), MESES) for t in range(nlin)])

    def linha_corr(r):
        return i4(r), i4(r, 4), f8(r, MESES + 1, 8)

    # Lista H: marca i da primeira linha histórica de cada bloco q.
    lista_h = []
    for q in range(nh):
        r = rb(q, pos["hist"])
        if r is None:
            raise ValueError(f"{caminho}: arquivo termina antes do bloco histórico {q + 1}")
        lista_h.append(i4(r))
    if not set(indice) <= set(lista_h):
        raise ValueError(f"{caminho}: séries do índice fora da lista histórica")

    # Parte gerada: posição no índice.
    gerada = {}
    for q, nint in enumerate(indice):
        gerada[nint] = dict(
            media_gerada=meses(q, pos["media_gerada"])[0],
            desvio_gerado=meses(q, pos["desvio_gerado"])[0],
            fac_gerada=meses(q, pos["fac_gerada"], n_defasagens),
            anual=EstatisticaAnual(*map(float, f8(rb(q, pos["anual"]), 5))),
        )

    # Parte histórica: posição em H.
    series = {}
    vazio = dict(media_gerada=None, desvio_gerado=None, fac_gerada=None, anual=None)
    for q, nint in enumerate(lista_h):
        facp = ordens = coefs = None
        if tipo == "incremental":
            facp = meses(q, pos["facp"], n_defasagens)
            ords, cs = [], []
            for m in range(MESES):
                r = rb(q, pos["ar"] + m)
                pm = i4(r)
                ords.append(pm)
                cs.append(f8(r, pm, 4))
            ordens, coefs = tuple(ords), tuple(cs)
        series[nint] = SerieCorrel(
            nint=nint,
            media=meses(q, pos["media"])[0],
            desvio=meses(q, pos["desvio"])[0],
            fac=meses(q, pos["fac"], n_defasagens),
            facp=facp,
            ordens=ordens,
            coeficientes=coefs,
            **gerada.get(nint, vazio),
        )

    corr_h = {}
    for q, i in enumerate(lista_h):
        for t, j in enumerate(lista_h):
            r = rb(q, pos["hist"] + t)
            val = np.full(MESES + 1, np.nan)
            if r is not None:
                ii, jj, v = linha_corr(r)
                if (ii, jj) == (i, j):
                    val = v
            corr_h[(i, j)] = val

    corr_s = {}
    for q, i in enumerate(indice):
        for t, j in enumerate(indice):
            ii, jj, v = linha_corr(rb(q, pos["sint"] + t))
            if (ii, jj) != (i, j):
                raise ValueError(f"{caminho}: marca ({ii},{jj}) onde se esperava ({i},{j})")
            corr_s[(i, j)] = v

    return Correl(
        tipo=tipo,
        indice=indice,
        lista_historica=tuple(lista_h),
        tamanho_bloco=tam,
        series=series,
        corr_historica=corr_h,
        corr_sintetica=corr_s,
    )


def ler_correli(caminho, **kw) -> Correl:
    """correli.out: estatísticas das séries incrementais."""
    return ler_correl(caminho, "incremental", **kw)


def ler_correlt(caminho, **kw) -> Correl:
    """correlt.out: estatísticas das séries totais."""
    return ler_correl(caminho, "total", **kw)
