"""VAZOES.RVx (VAZOES.XXX): árvore de vazões entregue ao DECOMP.

Layout (U19 §5.3.4, confirmado e completado em docs/layout-VAZOES.RVx.md):
acesso direto, RECL = NPOS*4. Registros, na ordem:

1. int32: nº de usinas, nº de estágios NEST, aberturas[NEST], NPOS, nº de usinas NW
2. int32: códigos das usinas (as NW no fim)
3. int32: semanas previstas, dias excluídos, mês inicial, ano inicial, nº de
   postos, semanas observadas, código da versão (110002 nos pacotes, impresso
   "11.0.2" no VAZDCP.REL; a fórmula geral é ESCOLHA); bytes 29-40 não
   identificados
4. float32: probabilidades dos nós, ceil(NNOS/NPOS) registros
5. int32 por posto: incrementais semanais previstas (NEST-1 registros)
6. int32 por posto: incrementais mensais geradas (um por cenário)
7. int32: semanais previstas considerando artificiais (coluna do posto
   artificial quando a usina tem um, senão do posto)
8. int32: mensais geradas considerando artificiais (mesma regra de coluna)
9. int32: incrementais mensais observadas (meses anteriores ao inicial),
   na mesma convenção de colunas e grandeza dos blocos 7-8
10. int32: incrementais semanais observadas (uma por semana observada)

Todos os valores de vazão são o inteiro mais próximo do float64 de origem.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from .acesso_direto import NPOS_PADRAO, ler_bytes, numero_de_registros


@dataclass(frozen=True)
class Calendario:
    semanas_previstas: int
    dias_excluidos: int
    mes_inicial: int
    ano_inicial: int
    n_postos: int
    semanas_observadas: int
    versao: str
    versao_codigo: int
    bytes_nao_identificados: bytes = field(repr=False)


@dataclass(frozen=True)
class VazoesDecomp:
    n_usinas: int
    n_estagios: int
    aberturas: tuple[int, ...]
    npos: int
    n_usinas_nw: int
    codigos: tuple[int, ...]
    calendario: Calendario
    probabilidades: np.ndarray  # float32, um valor por nó
    prevista_semanal: np.ndarray  # [semana, posto-1]
    gerada_mensal: np.ndarray  # [cenario, posto-1]
    prevista_semanal_ena: np.ndarray  # [semana, coluna-1]
    gerada_mensal_ena: np.ndarray  # [cenario, coluna-1]
    observada_mensal: np.ndarray  # [k, coluna-1]
    meses_observados: tuple[int, ...]
    observada_semanal: np.ndarray  # [semana, coluna-1]
    primeiro_registro: dict[str, int]

    @property
    def n_nos(self) -> int:
        return len(self.probabilidades)

    @property
    def n_cenarios(self) -> int:
        return self.gerada_mensal.shape[0]

    def gerada(self, cenario: int, posto: int) -> int:
        """Incremental mensal gerada (m3/s inteiros) do posto no cenário (1..)."""
        return int(self.gerada_mensal[cenario - 1, posto - 1])

    def observada(self, mes: int, coluna: int) -> int:
        """Incremental observada no mês do calendário `mes` (convenção ENA)."""
        return int(self.observada_mensal[self.meses_observados.index(mes), coluna - 1])


def numero_de_nos(aberturas) -> int:
    """Nós da árvore: soma, por estágio, do produto das aberturas até ele."""
    total, prod = 0, 1
    for a in aberturas:
        prod *= a
        total += prod
    return total


def versao_padrao(codigo: int) -> str:
    """ESCOLHA F2-VZ-04b: `maior*10000 + menor*100 + revisão`.

    Só há uma amostra pública (110002 <-> "11.0.2"), que também caberia em
    outras codificações; por isso a função é parâmetro do leitor.
    """
    return f"{codigo // 10000}.{(codigo // 100) % 100}.{codigo % 100}"


def ler_vazoes_decomp(
    caminho,
    npos: int = NPOS_PADRAO,
    decodificar_versao: Callable[[int], str] = versao_padrao,
) -> VazoesDecomp:
    dados = ler_bytes(caminho)
    recl = npos * 4
    nreg = numero_de_registros(dados, recl, str(caminho))
    m = np.frombuffer(dados, "<i4").reshape(nreg, npos)

    r1 = m[0]
    n_usinas, nest = int(r1[0]), int(r1[1])
    aberturas = tuple(int(x) for x in r1[2 : 2 + nest])
    npos_arq, n_nw = int(r1[2 + nest]), int(r1[3 + nest])
    if npos_arq != npos:
        raise ValueError(f"{caminho}: NPOS do cabeçalho {npos_arq} != {npos}")
    codigos = tuple(int(x) for x in m[1][: n_usinas + n_nw])

    r3 = m[2]
    cal = Calendario(
        semanas_previstas=int(r3[0]),
        dias_excluidos=int(r3[1]),
        mes_inicial=int(r3[2]),
        ano_inicial=int(r3[3]),
        n_postos=int(r3[4]),
        semanas_observadas=int(r3[5]),
        versao=decodificar_versao(int(r3[6])),
        versao_codigo=int(r3[6]),
        bytes_nao_identificados=dados[2 * recl + 28 : 2 * recl + 40],
    )

    n_nos = numero_de_nos(aberturas)
    nregp = -(-n_nos // npos)
    prob = np.frombuffer(dados[3 * recl : (3 + nregp) * recl], "<f4")[:n_nos].copy()

    # F2-VZ-09: só verificado com uma abertura em cada estágio semanal e um
    # único estágio estocástico no fim; outra árvore seria lida errado.
    if any(a != 1 for a in aberturas[:-1]):
        raise ValueError(
            f"{caminho}: aberturas {aberturas} fora do layout verificado "
            "(estágios semanais com uma abertura e um estágio estocástico no fim)"
        )
    nprev = nest - 1
    nger = n_nos - nprev
    nobs_sem = cal.semanas_observadas
    k = 3 + nregp
    resto = nreg - k - 2 * (nprev + nger) - nobs_sem
    if resto < 0:
        raise ValueError(f"{caminho}: {nreg} registros não comportam o layout")
    primeiro = {}

    def bloco(nome, n):
        nonlocal k
        primeiro[nome] = k + 1
        b = m[k : k + n].copy()
        k += n
        return b

    prev = bloco("prevista_semanal", nprev)
    ger = bloco("gerada_mensal", nger)
    prev_ena = bloco("prevista_semanal_ena", nprev)
    ger_ena = bloco("gerada_mensal_ena", nger)
    obs_m = bloco("observada_mensal", resto)
    obs_s = bloco("observada_semanal", nobs_sem)
    meses = tuple(((cal.mes_inicial - 1 - resto + i) % 12) + 1 for i in range(resto))

    return VazoesDecomp(
        n_usinas=n_usinas,
        n_estagios=nest,
        aberturas=aberturas,
        npos=npos_arq,
        n_usinas_nw=n_nw,
        codigos=codigos,
        calendario=cal,
        probabilidades=prob,
        prevista_semanal=prev,
        gerada_mensal=ger,
        prevista_semanal_ena=prev_ena,
        gerada_mensal_ena=ger_ena,
        observada_mensal=obs_m,
        meses_observados=meses,
        observada_semanal=obs_s,
        primeiro_registro=primeiro,
    )
