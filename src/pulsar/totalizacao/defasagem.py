"""Total de usina com posto lateral pela defasagem linear (M18 §4.3.3.2,
alternativa (ii), eq. 4.21; L-TOT eq. 53–54):

    ZT(t) = β Σ ZT_mont(t-1) + (1-β) Σ ZT_mont(t) + Z_lat(t),  β = ndias/ndmes

No modo DECOMP o mês t é o estágio estocástico e t-1 é o fim do horizonte
semanal do PREVS.
"""

from __future__ import annotations

import calendar
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ..configuracao import Configuracao
from ..entradas.deck import Deck

# F6-DEF-03 (INFERIDO): semanas operativas de 7 dias.
DIAS_SEMANA = 7


@dataclass(frozen=True)
class MontanteDefasado:
    """Uma usina imediatamente a montante na eq. 4.21.

    ``soma_janela`` = Σ (dias × total semanal) nos ``ndias`` dias anteriores
    ao estágio estocástico (m³/s·dia), de modo que ZT_mont(t-1) =
    soma_janela/ndias e β·ZT_mont(t-1) = soma_janela/ndmes.
    """

    usina: int
    ndias: float
    soma_janela: float
    dias_estagio: int

    @property
    def beta(self) -> float:
        # F6-DEF-02 (DOC M18 eq. 4.21: β = ndias/ndmes; INFERIDO: ndmes =
        # dias do estágio estocástico).
        return self.ndias / self.dias_estagio


def total_defasado(
    lateral: np.ndarray,
    montantes: Sequence[MontanteDefasado],
    totais: Mapping[int, np.ndarray],
) -> np.ndarray:
    """Eq. 4.21 do M18 com β por usina de montante.

    F6-DEF-05 (INFERIDO no valor, ESCOLHA na ordem; lacuna L21): soma as
    parcelas do mês anterior (soma_janela/ndmes), depois as do mês corrente
    ((1-β)·ZT), na ordem da configuração, e por fim a lateral. A forma
    bit a bit oficial não foi identificada: esta variante está empatada no
    topo com a ``nd·P/ndmes`` entre as 1 348 formas de
    ferramentas/enumerar_defasagem.py ([223, 202] cenários iguais), e nenhuma
    fecha todos (docs/totalizacao-e-artificiais.md).
    """
    acc = 0.0
    for m in montantes:
        acc = acc + m.soma_janela / m.dias_estagio
    acc = np.full(np.shape(lateral), acc)
    for m in montantes:
        acc = acc + (1.0 - m.beta) * totais[m.usina]
    return lateral + acc


def soma_janela(semanas: Sequence[float], ndias: float) -> float:
    """F6-DEF-03 (INFERIDO): Σ (dias × vazão semanal) nos ``ndias`` últimos
    dias do horizonte semanal (a última semana termina na véspera do estágio
    estocástico), em semanas de 7 dias.

    F6-DEF-04 (ESCOLHA, lacuna L21): ``ndias`` não inteiro (tempo de viagem
    que não é múltiplo de 24 h) e janela maior que as semanas do PREVS (que
    exigiria o VSEMPAST, U19 §4.8) levantam erro explícito.
    """
    if ndias != int(ndias) or ndias < 0:
        raise NotImplementedError(f"janela de {ndias} dias: só dias inteiros têm exemplo público")
    resto = int(ndias)
    soma = 0.0
    for v in reversed(semanas):
        if resto <= 0:
            break
        d = min(DIAS_SEMANA, resto)
        soma += d * v
        resto -= d
    if resto > 0:
        raise NotImplementedError(f"janela de {ndias} dias maior que as {len(semanas)} semanas do PREVS")
    return soma


def dias_do_mes(ano: int, mes: int) -> int:
    """F6-DEF-06 (INFERIDO): calendário gregoriano, fevereiro bissexto com
    29 dias (pacote de jan/2024, mês estocástico fev/2024:
    test_t8_totalizacao.py::test_defasagem_linear_de_sobradinho). Ao
    contrário da média do mês inicial (P-TEND-02, 28 dias). Quem precisar de
    outra contagem passa ``dias_estagio`` a ``dados_defasagem``."""
    return calendar.monthrange(ano, mes)[1]


def dias_do_estagio_estocastico(mes_inicial: int, ano_inicial: int, dias_excluidos: int) -> int:
    """F6-DEF-02 (INFERIDO): dias do mês estocástico menos os dias dele que
    caem na última semana (& VAZOES reg. 8). O mês estocástico é o seguinte
    ao inicial, no ano seguinte quando o inicial é dezembro (F2-QP-03)."""
    mes = mes_inicial % 12 + 1
    ano = ano_inicial + (1 if mes_inicial == 12 else 0)
    return dias_do_mes(ano, mes) - dias_excluidos


def dados_defasagem(
    deck: Deck, cfg: Configuracao, dias_estagio: int | None = None
) -> dict[int, list[MontanteDefasado]]:
    """Dados da eq. 4.21 para cada usina com posto lateral e defasagem
    linear (campo 13 = 2, U19 §4.5 reg. 12).

    ndias = tempo de viagem da usina de montante (registro VI, horas) / 24
    (F6-DEF-02); ZT_mont(t-1) vem das vazões totais semanais do PREVS do
    posto da usina de montante (F6-DEF-03). ``dias_estagio`` substitui o
    ndmes calculado pelo calendário (F6-DEF-06).
    """
    v = deck.dadger.vazoes
    por_num = cfg.por_numero()
    saida: dict[int, list[MontanteDefasado]] = {}
    for u in cfg.usinas:
        if not (u.posto_lateral and u.defasagem == 2):
            continue
        ndmes = dias_estagio
        if ndmes is None:
            # P-DADG-12 / F7-VZ-12: sem o ano no reg. 4 do & VAZOES, o do reg. 6.
            ano = v.ano_inicial or v.ano_inicial_estudo
            if not v.mes_inicial or not ano:
                raise ValueError("& VAZOES sem mês ou ano inicial: ndmes da defasagem linear indefinido")
            # dias excluídos em branco valem 0 (P-TXT-02).
            ndmes = dias_do_estagio_estocastico(v.mes_inicial, ano, v.dias_excluidos or 0)
        lista = []
        for m in cfg.montante(u.numero):
            um = por_num[m]
            ndias = um.tempo_viagem / 24
            sem = deck.prevs[um.posto].semanas if ndias else []
            lista.append(MontanteDefasado(m, ndias, soma_janela(sem, ndias) if ndias else 0.0, ndmes))
        saida[u.numero] = lista
    return saida
