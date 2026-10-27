"""Tendência hidrológica (QPAST.DAT) e vazões determinísticas por período.

Monta, a partir do deck (PREVS, VAZOES.DAT, REGRAS.DAT) e da configuração
da F1, os totais de cada posto por período (semanas do mês inicial, mês
inicial ponderado e meses anteriores), os totais dos postos artificiais
pelas regras e as incrementais natural e "para ENA" de cada usina.

Fontes: U19 §4.7 (média do mês inicial ponderada pelos dias da primeira e
da última semana; meses anteriores do histórico atualizado), U19 Anexo B
(origem das vazões por representação da usina), L-INC eq. 1 (incremental) e
os arquivos públicos (QPAST.DAT, VAZOES.RVx, GEVAZP.REL). Proveniência:
P-TEND-*, P-INC-*, P-ART-* em PROVENIENCIA.md.
"""

from __future__ import annotations

import calendar
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from .configuracao import LATERAL, NEWAVE, NULO, Configuracao, UsinaConfig
from .entradas.deck import Deck
from .entradas.regras import Regras, avaliar
from .entradas.texto import ErroLeitura

# P-ART-04: posto que, associado a um PARTIF, anula a incremental também nas
# semanas e nos meses observados (U19 §4.11 e Anexo B).
POSTO_NULO = 300

# P-TEND-07 (ESCOLHA, lacuna L17): meses observados quando o DADGER não traz
# a ordem máxima (ordem máxima padrão do PAR(p), L-PAR).
MESES_OBSERVADOS_PADRAO = 11


def nint(x: float) -> float:
    """Inteiro mais próximo, empate para longe do zero (NINT do Fortran).

    P-ART-03: empate positivo para cima é INFERIDO (posto 75, totais com
    fração .5); o empate negativo não aparece nos decks (ESCOLHA, lacuna L9).
    """
    return float(np.floor(x + 0.5)) if x >= 0 else float(np.ceil(x - 0.5))


def precisao_simples(x: float) -> float:
    """P-ART-02: valor lido por ``VAZ(n)`` nas regras, em precisão simples."""
    return float(np.float32(x))


@dataclass(frozen=True)
class OpcoesTendencia:
    """Escolhas que os dados públicos não decidem (e as variantes inferidas,
    expostas para teste)."""

    # P-TEND-07 (ESCOLHA, lacuna L17): nº de meses observados gravados no
    # VAZOES.RVx. None = ordem máxima do PAR(p) do DADGER (& VAZOES reg. 11);
    # um inteiro fixa o número.
    meses_observados: int | None = None
    # P-ART-02 (INFERIDO): leitura de VAZ(n) nas regras.
    leitura_regras: Callable[[float], float] = precisao_simples
    # P-ART-02: arredondamento das operações das regras (``avaliar``,
    # P-REG-04); None = precisão dupla (a variante que reproduz o QPAST).
    operacoes_regras: Callable[[float], float] | None = None
    # P-ART-03 (INFERIDO/ESCOLHA): arredondamento dos totais antes das
    # incrementais nas semanas e nos meses observados.
    arredondar: Callable[[float], float] = nint
    # P-ART-07 (ESCOLHA, lacuna L16): ano do estudo (base 1) usado para a
    # variante do bloco 2 do REGRAS.DAT nas semanas e em todos os meses
    # passados, inclusive os do ano anterior ao inicial.
    ano_estudo_regras: int = 1
    # P-TEND-02 (INFERIDO, lacuna L5): dias de fevereiro na média do mês
    # inicial; 28 também nos anos bissextos. None = calendário gregoriano.
    dias_fevereiro: int | None = 28


# ------------------------------------------------------------- calendário

# P-TEND-02: fevereiro com 28 dias na média ponderada do mês inicial, mesmo
# em ano bissexto (INFERIDO nas quatro revisões de fev/2024).
DIAS_FEVEREIRO = 28


def dias_no_mes(ano: int, mes: int, dias_fevereiro: int | None = DIAS_FEVEREIRO) -> int:
    """P-TEND-02: calendário gregoriano, exceto fevereiro, que tem
    ``dias_fevereiro`` dias (28, INFERIDO no QPAST de fev/2024); com None,
    29 nos anos bissextos."""
    if mes == 2 and dias_fevereiro is not None:
        return dias_fevereiro
    return calendar.monthrange(ano, mes)[1]


def pesos_semanais(ano: int, mes: int, n_semanas: int, dias_excluidos: int,
                   dias_fevereiro: int | None = DIAS_FEVEREIRO) -> list[int]:
    """Dias do mês inicial em cada semana (U19 §4.7: "é levado em conta o
    número de dias do mês em questão na primeira e na última semana").

    P-TEND-01: semanas intermediárias com 7 dias; a última com
    ``7 - dias_excluidos`` (DADGER & VAZOES reg. 8: dias do mês seguinte na
    última semana); a primeira com o que sobra do mês. Com uma semana só
    (mês cheio, U19 §4.7) o peso é o mês inteiro.
    """
    dm = dias_no_mes(ano, mes, dias_fevereiro)
    if n_semanas < 1:
        raise ErroLeitura(f"número de semanas inválido: {n_semanas}")
    if n_semanas == 1:
        return [dm]
    ultima = 7 - dias_excluidos
    primeira = dm - 7 * (n_semanas - 2) - ultima
    if not (1 <= primeira <= 7 and 1 <= ultima <= 7):
        raise ErroLeitura(
            f"{n_semanas} semanas com {dias_excluidos} dias excluídos não cabem em {mes:02d}/{ano} ({dm} dias)"
        )
    return [primeira] + [7] * (n_semanas - 2) + [ultima]


def media_ponderada(semanas, pesos: list[int]) -> float:
    """P-TEND-03 (INFERIDO): soma dos produtos peso × vazão na ordem das
    semanas, dividida pelo número de dias do mês."""
    s = 0.0
    for p, q in zip(pesos, semanas, strict=True):
        s += p * q
    return s / sum(pesos)


# ---------------------------------------------------- postos artificiais


def postos_artificiais(cfg: Configuracao) -> list[int]:
    """Postos calculados por regra: os ``NPOSNW`` das usinas (P-ART-01)."""
    vistos: list[int] = []
    for u in cfg.usinas:
        if u.posto_artificial and u.posto_artificial not in vistos:
            vistos.append(u.posto_artificial)
    return vistos


def calcular_artificiais(
    valores: np.ndarray,
    regras: Regras,
    mes: int,
    alvos,
    leitura: Callable[[float], float] = precisao_simples,
    ano_estudo: int = 1,
    operacoes: Callable[[float], float] | None = None,
) -> dict[int, float]:
    """Totais dos postos ``alvos`` pelas regras do mês ``mes``.

    ``valores[posto-1]`` = vazão total fornecida do período.
    P-ART-01: só os postos artificiais associados por NPOSNW são calculados
    pela regra; dentro de uma regra, ``VAZ(n)`` de um posto que tem regra é
    a regra desse posto, recalculada, mesmo que o posto tenha valor
    fornecido (INFERIDO: postos 116 e 119, que estão no PREVS e no
    histórico).
    P-ART-02 (INFERIDO): ``VAZ(n)`` devolve o valor em precisão simples
    (``leitura``) e as operações são em precisão dupla; o resultado de cada
    alvo é guardado em precisão dupla. ``operacoes`` (variante rejeitada)
    arredonda cada número, leitura e resultado intermediário (P-REG-04).
    P-ART-07 (ESCOLHA, lacuna L16): ``ano_estudo`` escolhe a variante do
    bloco 2 do REGRAS.DAT (``Regras.regra``).
    """
    com_regra = regras.postos()
    lidos: dict[int, float] = {}
    pilha: list[int] = []

    def resultado(p: int) -> float:
        if p in pilha:
            raise ErroLeitura(f"regras circulares: {pilha + [p]}")
        pilha.append(p)
        try:
            return avaliar(regras.regra(p, mes, ano_estudo).expressao, vaz, operacoes)
        finally:
            pilha.pop()

    def vaz(p: int) -> float:
        if p not in lidos:
            if p in com_regra:
                lidos[p] = leitura(resultado(p))
            else:
                # P-ART-06 (ESCOLHA, lacuna L15): posto fora de 1..NPOS é erro.
                if not 1 <= p <= len(valores):
                    raise ErroLeitura(f"regra cita o posto {p}, fora de 1..{len(valores)}")
                lidos[p] = leitura(float(valores[p - 1]))
        return lidos[p]

    return {p: resultado(p) for p in alvos}


# ------------------------------------------------------------- períodos


@dataclass
class Periodo:
    """Totais de todos os postos num período (semana ou mês)."""

    rotulo: str
    mes_regra: int  # mês do calendário usado na escolha da regra
    fornecidos: np.ndarray  # float64 [posto-1], valores de entrada
    artificiais: dict[int, float]  # postos NPOSNW calculados pela regra

    def total(self, posto: int) -> float:
        if posto in self.artificiais:
            return self.artificiais[posto]
        return float(self.fornecidos[posto - 1])

    def totais(self) -> np.ndarray:
        t = self.fornecidos.copy()
        for p, v in self.artificiais.items():
            t[p - 1] = v
        return t


def _periodo(rotulo, mes, fornecidos, deck: Deck, cfg: Configuracao, op: OpcoesTendencia) -> Periodo:
    alvos = postos_artificiais(cfg)
    art = {}
    if alvos:
        if deck.regras is None:
            raise ErroLeitura("há postos NPOSNW e não há REGRAS.DAT")
        art = calcular_artificiais(fornecidos, deck.regras, mes, alvos, op.leitura_regras, op.ano_estudo_regras, op.operacoes_regras)
    return Periodo(rotulo=rotulo, mes_regra=mes, fornecidos=fornecidos, artificiais=art)


def _bloco(deck: Deck):
    v = deck.dadger.vazoes if deck.dadger else None
    if v is None or not v.mes_inicial:
        raise ErroLeitura("DADGER sem o bloco & VAZOES com o mês inicial")
    if v.arquivo_vsempast:
        # P-TEND-08 (ESCOLHA, lacuna L18): a combinação PREVS + VSEMPAST da
        # propagação linear (U19 §4.8, Anexo B nota *) não tem deck público.
        raise NotImplementedError("VSEMPAST (propagação linear no 1º mês) não implementado")
    if v.tendencia_editavel:
        # U19 §4.5 reg. 21: tendência lida de arquivo formatado; sem deck público.
        raise NotImplementedError("tendência hidrológica por arquivo editável não implementada")
    return v


def _ano_inicial(v) -> int:
    # P-DADG-12: ano do & VAZOES reg. 4; sem ele, o reg. 6.
    ano = v.ano_inicial or v.ano_inicial_estudo
    if not ano:
        raise ErroLeitura("DADGER sem ano inicial do estudo")
    return ano


def periodos_semanais(deck: Deck, cfg: Configuracao, op: OpcoesTendencia | None = None) -> list[Periodo]:
    """Uma entrada por semana do mês inicial (observadas primeiro).

    P-PREVS-03: semanas = não observadas + observadas. P-ART-05 (INFERIDO):
    a regra de todas as semanas é a do mês inicial, inclusive na última,
    que avança no mês seguinte (posto 292, regra mensal, 202609).
    """
    op = op or OpcoesTendencia()
    v = _bloco(deck)
    n = (v.semanas_nao_observadas or 0) + (v.semanas_observadas or 0)
    if deck.prevs is None:
        raise ErroLeitura("deck sem PREVS")
    saida = []
    for s in range(n):
        f = np.zeros(deck.n_postos)
        for p, pr in deck.prevs.items():
            f[p - 1] = pr.semanas[s]
        saida.append(_periodo(f"S{s + 1}", v.mes_inicial, f, deck, cfg, op))
    return saida


def meses_anteriores(mes_inicial: int, ano_inicial: int, n: int) -> list[tuple[int, int]]:
    """(ano, mês) dos ``n`` meses anteriores ao inicial, em ordem cronológica."""
    saida = []
    for k in range(n, 0, -1):
        m = mes_inicial - k
        a = ano_inicial + (m - 1) // 12
        saida.append((a, (m - 1) % 12 + 1))
    return saida


def periodo_historico(deck: Deck, cfg: Configuracao, ano: int, mes: int, op: OpcoesTendencia | None = None) -> Periodo:
    """Mês anterior ao inicial: totais do histórico atualizado (U19 §4.7)."""
    op = op or OpcoesTendencia()
    h = deck.historico
    if h is None:
        raise ErroLeitura("deck sem histórico de vazões")
    f = np.array([float(h.vazao(p, ano, mes)) for p in range(1, deck.n_postos + 1)])
    return _periodo(f"{mes:02d}/{ano}", mes, f, deck, cfg, op)


def periodo_mes_inicial(deck: Deck, cfg: Configuracao, op: OpcoesTendencia | None = None) -> Periodo:
    """Mês inicial: média das semanas do PREVS ponderada pelos dias do mês
    (U19 §4.7; P-TEND-01..03). Postos sem PREVS ficam com zero (P-TEND-04)."""
    op = op or OpcoesTendencia()
    v = _bloco(deck)
    ano = _ano_inicial(v)
    n = (v.semanas_nao_observadas or 0) + (v.semanas_observadas or 0)
    pesos = pesos_semanais(ano, v.mes_inicial, n, v.dias_excluidos or 0, op.dias_fevereiro)
    f = np.zeros(deck.n_postos)
    for p, pr in deck.prevs.items():
        f[p - 1] = media_ponderada(pr.semanas, pesos)
    return _periodo(f"{v.mes_inicial:02d}/{ano}", v.mes_inicial, f, deck, cfg, op)


# ------------------------------------------------------------ incrementais


def _mapa(cfg: Configuracao) -> dict[int, UsinaConfig]:
    return cfg.por_numero()


def coluna_ena(u: UsinaConfig) -> int:
    """P-INC-05 (F2-VZ-07): coluna "considerando artificiais" = posto NPOSNW
    se houver, senão o posto."""
    return u.posto_artificial or u.posto


def _gravar(saida: np.ndarray, gravadas: set[int], col: int, valor: float, quem: str):
    """P-INC-06 (ESCOLHA, lacuna L18): duas usinas na mesma coluna com
    valores diferentes é erro (não acontece nos decks públicos)."""
    if col in gravadas and saida[col - 1] != valor:
        raise ErroLeitura(f"coluna {col} recebe dois valores diferentes ({quem})")
    gravadas.add(col)
    saida[col - 1] = valor


def incrementais_naturais(per: Periodo, cfg: Configuracao, n_postos: int, arred=nint) -> np.ndarray:
    """Incremental natural de cada usina na coluna do seu posto (blocos 5 do
    VAZOES.RVx), a partir dos totais arredondados (P-ART-03). ``n_postos`` é
    obrigatório: o nº de postos do deck (``Deck.n_postos``, P-DECK-02).

    P-INC-01: incremental = total do posto - totais dos postos imediatamente a
    montante (L-INC eq. 1), sem as usinas NW a montante (P-INC-02).
    P-INC-02 (INFERIDO): usina NW tem incremental nula.
    P-ART-04 (DOC, U19 Anexo B): PARTIF com posto 300, nula; PARTIF sem
    posto 300 usa o PREVS como as demais.
    P-INC-03 (INFERIDO): posto lateral recebe o próprio total.
    """
    por = _mapa(cfg)
    T = lambda p: arred(per.total(p))
    out = np.zeros(n_postos)
    feitas: set[int] = set()
    for u in cfg.completa:
        if u.status == LATERAL:
            _gravar(out, feitas, u.posto, T(u.posto), u.nome_str)
            continue
        if u.status == NEWAVE or (u.status == NULO and u.posto == POSTO_NULO):
            continue
        mont = [por[n] for n in cfg.montante(u.numero) if por[n].status != NEWAVE]
        _gravar(out, feitas, u.posto, T(u.posto) - sum(T(m.posto) for m in mont), u.nome_str)
    return out


def incrementais_ena(per: Periodo, cfg: Configuracao, n_postos: int, arred=nint) -> np.ndarray:
    """Incremental "para ENA" na coluna ENA (blocos 7, 9 e 10 do VAZOES.RVx).
    ``n_postos`` é obrigatório: o nº de postos do deck (``Deck.n_postos``).

    P-INC-04 (INFERIDO): total da coluna ENA da usina - totais das colunas
    ENA das usinas imediatamente a montante, incluídas as NW; a usina NW tem
    a própria incremental.
    P-ART-04 (DOC, U19 Anexo B): coluna 300 (PARTIF com posto 300 sem
    NPOSNW) é nula; com NPOSNW vale a regra.
    P-INC-03 (INFERIDO): posto lateral recebe o próprio total.
    """
    por = _mapa(cfg)
    T = lambda p: arred(per.total(p))
    out = np.zeros(n_postos)
    feitas: set[int] = set()
    for u in cfg.completa:
        if u.status == LATERAL:
            _gravar(out, feitas, u.posto, T(u.posto), u.nome_str)
            continue
        col = coluna_ena(u)
        if col == POSTO_NULO:
            continue
        mont = [por[n] for n in cfg.montante(u.numero)]
        _gravar(out, feitas, col, T(col) - sum(T(coluna_ena(m)) for m in mont), u.nome_str)
    return out


# ------------------------------------------------------------------ QPAST


@dataclass
class TendenciaCalculada:
    incremental: np.ndarray  # [mes-1, posto-1], meses do calendário
    total: np.ndarray  # [mes-1, posto-1]
    meses: list[tuple[int, int]]  # (ano, mês) em ordem cronológica

    def bytes_qpast(self) -> bytes:
        """P-TEND-06 (F2-QP-01..02): 24 registros de NPOS float64; 1-12
        incrementais jan..dez, 13-24 totais jan..dez."""
        m = np.concatenate([self.incremental, self.total]).astype("<f8")
        return m.tobytes()


def incrementais_tendencia(totais: np.ndarray, cfg: Configuracao) -> np.ndarray:
    """P-TEND-05 (INFERIDO): incremental do QPAST = total do posto - totais
    dos postos das usinas imediatamente a montante, incluídas as NW, sem
    arredondamento; nas usinas PN e nas colunas que não são posto de usina
    repete o total (F2-QP-04)."""
    por = _mapa(cfg)
    inc = totais.copy()
    for u in cfg.usinas:
        if u.status == NULO:
            continue
        x = totais[u.posto - 1]
        for n in cfg.montante(u.numero):
            x = x - totais[por[n].posto - 1]
        inc[u.posto - 1] = x
    return inc


def tendencia(deck: Deck, cfg: Configuracao, op: OpcoesTendencia | None = None) -> TendenciaCalculada:
    """QPAST.DAT: os 12 meses que terminam no mês inicial (F2-QP-03).

    Totais: P-TEND-04 (INFERIDO): todo posto com o valor do período
    (histórico ou média ponderada do PREVS); os postos NPOSNW com a regra do
    mês (P-ART-01, P-ART-02), sem arredondamento.
    """
    op = op or OpcoesTendencia()
    v = _bloco(deck)
    ano = _ano_inicial(v)
    n = deck.n_postos
    total = np.zeros((12, n))
    inc = np.zeros((12, n))
    meses = meses_anteriores(v.mes_inicial, ano, 11) + [(ano, v.mes_inicial)]
    for a, m in meses:
        per = periodo_mes_inicial(deck, cfg, op) if (a, m) == (ano, v.mes_inicial) else periodo_historico(deck, cfg, a, m, op)
        t = per.totais()
        total[m - 1] = t
        inc[m - 1] = incrementais_tendencia(t, cfg)
    return TendenciaCalculada(incremental=inc, total=total, meses=meses)


def n_meses_observados(deck: Deck, op: OpcoesTendencia | None = None) -> int:
    op = op or OpcoesTendencia()
    if op.meses_observados is not None:
        return op.meses_observados
    v = _bloco(deck)
    return v.ordem_maxima or MESES_OBSERVADOS_PADRAO


def gravar_qpast(caminho, tend: TendenciaCalculada):
    with open(caminho, "wb") as f:
        f.write(tend.bytes_qpast())


__all__ = [
    "OpcoesTendencia",
    "Periodo",
    "TendenciaCalculada",
    "calcular_artificiais",
    "coluna_ena",
    "dias_no_mes",
    "gravar_qpast",
    "incrementais_ena",
    "incrementais_naturais",
    "incrementais_tendencia",
    "media_ponderada",
    "meses_anteriores",
    "n_meses_observados",
    "nint",
    "periodo_historico",
    "periodo_mes_inicial",
    "periodos_semanais",
    "pesos_semanais",
    "postos_artificiais",
    "precisao_simples",
    "tendencia",
]
