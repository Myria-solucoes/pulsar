"""Registros determinísticos do VAZOES.RVx (U19 §5.3.4; layout da F2 em
docs/layout-VAZOES.RVx.md).

Monta, sem ler nenhum VAZOES.RVx, os registros 1 a 3, o prefixo
determinístico do registro de probabilidades e os blocos de semanas
previstas (naturais e para ENA), meses observados e semanas observadas.
Os blocos gerados (6 e 8) e as probabilidades das folhas são das frentes
estocásticas. Proveniência: P-VZD-* e as linhas citadas da F2 (F2-VZ-*).
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .configuracao import NEWAVE, Configuracao
from .entradas.deck import Deck
from .entradas.texto import ErroLeitura
from .tendencia import (
    OpcoesTendencia,
    incrementais_ena,
    incrementais_naturais,
    meses_anteriores,
    n_meses_observados,
    periodo_historico,
    periodos_semanais,
)

# P-VZD-04 (INFERIDO): versão gravada no registro 3; a frente emula a
# versão dos pacotes públicos (11.0.2) com a codificação F2-VZ-04b.
VERSAO_PADRAO = (11, 0, 2)

# P-VZD-05 (INFERIDO): bytes 29-40 do registro 3, de significado não
# identificado, iguais nos 503 vazoes.rvN de 2017 a 2026 da coleção de decks do ONS e
# nos três arquivos dos pacotes.
BYTES_REG3_PADRAO = b"&10_..D$_H\x00\x00"


# P-VZD-08 (INFERIDO; limite exato ESCOLHA, lacuna L10): primeira versão
# observada com NPOS e nº de usinas NW no registro 1 (8.1.6); as versões
# 6.0.0, 7.0.0 e 8.0.0 gravam só nº de usinas, estágios e aberturas.
VERSAO_REGISTRO1_ESTENDIDO = (8, 1, 6)


def codigo_versao(versao: tuple[int, int, int]) -> int:
    """F2-VZ-04b: ``maior*10000 + menor*100 + revisão``."""
    maior, menor, rev = versao
    return maior * 10000 + menor * 100 + rev


@dataclass(frozen=True)
class OpcoesVazoes:
    versao: tuple[int, int, int] = VERSAO_PADRAO
    bytes_reg3: bytes = BYTES_REG3_PADRAO
    # P-VZD-08: None = decide pela versão; True/False força o layout.
    registro1_estendido: bool | None = None
    tendencia: OpcoesTendencia = field(default_factory=OpcoesTendencia)


@dataclass
class RegistrosDeterministicos:
    npos: int
    registro1: np.ndarray  # int32 [npos]
    registro2: np.ndarray  # int32 [npos]
    registro3: bytes  # 4*npos bytes
    probabilidades_semanais: np.ndarray  # float32, um 1.0 por estágio semanal
    prevista_semanal: np.ndarray  # int32 [semana prevista, posto-1]
    prevista_semanal_ena: np.ndarray  # int32 [semana prevista, coluna-1]
    observada_mensal: np.ndarray  # int32 [mês observado, coluna-1]
    meses_observados: list[tuple[int, int]]
    observada_semanal: np.ndarray  # int32 [semana observada, coluna-1]

    @staticmethod
    def _bytes(m: np.ndarray) -> bytes:
        return np.ascontiguousarray(m, dtype="<i4").tobytes()

    def bytes_cabecalho(self) -> bytes:
        """Registros 1-3."""
        return self._bytes(self.registro1) + self._bytes(self.registro2) + self.registro3

    def bytes_prevista_semanal(self) -> bytes:
        return self._bytes(self.prevista_semanal)

    def bytes_prevista_semanal_ena(self) -> bytes:
        return self._bytes(self.prevista_semanal_ena)

    def bytes_observada_mensal(self) -> bytes:
        return self._bytes(self.observada_mensal)

    def bytes_observada_semanal(self) -> bytes:
        return self._bytes(self.observada_semanal)


def _inteiros(x: np.ndarray) -> np.ndarray:
    """Os totais já são arredondados (P-ART-03); a conversão é exata."""
    r = np.asarray(x)
    if not np.all(r == np.round(r)):
        raise ValueError("incremental não inteira")
    return r.astype("<i4")


def _bloco_vazoes(deck: Deck):
    v = deck.dadger.vazoes if deck.dadger else None
    if v is None:
        raise ErroLeitura("DADGER sem o bloco & VAZOES")
    return v


def montar_cabecalho(deck: Deck, cfg: Configuracao, opcoes: OpcoesVazoes | None = None) -> tuple[np.ndarray, np.ndarray, bytes]:
    """Registros 1, 2 e 3; dependem só do DADGER, da configuração e da versão."""
    op = opcoes or OpcoesVazoes()
    v = _bloco_vazoes(deck)
    npos = deck.n_postos
    nprev = v.semanas_nao_observadas or 0
    nobs = v.semanas_observadas or 0
    # P-VZD-01 (INFERIDO, F2-VZ-02/09): estágios = semanas previstas (uma
    # abertura cada) + períodos estocásticos do & VAZOES reg. 9.
    aberturas = [a for a in v.aberturas if a]
    if not aberturas:
        raise ErroLeitura("& VAZOES sem estrutura da árvore")
    estagios = [1] * nprev + aberturas
    ordem = cfg.ordem_vazoes_rv()  # P-CFG-16
    n_nw = sum(1 for u in cfg.usinas if u.status == NEWAVE)

    # P-VZD-01: nº de usinas sem NW, estágios, aberturas, NPOS, nº de NW,
    # zeros (F2-VZ-02); sem NPOS e nº de NW antes da 8.1.6 (P-VZD-08).
    estendido = op.registro1_estendido
    if estendido is None:
        estendido = tuple(op.versao) >= VERSAO_REGISTRO1_ESTENDIDO
    r1 = np.zeros(npos, "<i4")
    cab = [len(ordem) - n_nw, len(estagios), *estagios] + ([npos, n_nw] if estendido else [])
    r1[: len(cab)] = cab
    r2 = np.zeros(npos, "<i4")  # P-VZD-02: zeros depois dos códigos
    r2[: len(ordem)] = ordem

    # P-VZD-03 (INFERIDO, F2-VZ-04a): semanas previstas, dias excluídos,
    # mês e ano iniciais, nº de postos, semanas observadas, versão.
    ano = v.ano_inicial or v.ano_inicial_estudo
    r3 = np.zeros(npos, "<i4")
    r3[:7] = [nprev, v.dias_excluidos or 0, v.mes_inicial, ano, npos, nobs, codigo_versao(op.versao)]
    b3 = bytearray(r3.tobytes())
    b3[28 : 28 + len(op.bytes_reg3)] = op.bytes_reg3
    return r1, r2, bytes(b3)


def montar_registros(deck: Deck, cfg: Configuracao, opcoes: OpcoesVazoes | None = None) -> RegistrosDeterministicos:
    op = opcoes or OpcoesVazoes()
    ot = op.tendencia
    v = _bloco_vazoes(deck)
    npos = deck.n_postos
    nprev = v.semanas_nao_observadas or 0
    nobs = v.semanas_observadas or 0
    ano = v.ano_inicial or v.ano_inicial_estudo
    r1, r2, r3 = montar_cabecalho(deck, cfg, op)

    # F2-VZ-10: probabilidade 1.0 em cada estágio semanal.
    prob = np.ones(nprev, "<f4")

    # Semanas: as observadas vêm primeiro no PREVS (P-VZD-06).
    sem = periodos_semanais(deck, cfg, ot)
    nat = [incrementais_naturais(p, cfg, npos, ot.arredondar) for p in sem]
    ena = [incrementais_ena(p, cfg, npos, ot.arredondar) for p in sem]
    vazio = np.zeros((0, npos), "<i4")
    prev_nat = _inteiros(np.array(nat[nobs:])) if nprev else vazio
    prev_ena = _inteiros(np.array(ena[nobs:])) if nprev else vazio
    obs_sem = _inteiros(np.array(ena[:nobs])) if nobs else vazio

    # Meses observados (P-VZD-07, F2-VZ-11): incremental para ENA dos meses
    # anteriores ao inicial, em ordem cronológica.
    meses = meses_anteriores(v.mes_inicial, ano, n_meses_observados(deck, ot))
    obs_m = [incrementais_ena(periodo_historico(deck, cfg, a, m, ot), cfg, npos, ot.arredondar) for a, m in meses]
    obs_mes = _inteiros(np.array(obs_m)) if obs_m else vazio

    return RegistrosDeterministicos(
        npos=npos,
        registro1=r1,
        registro2=r2,
        registro3=r3,
        probabilidades_semanais=prob,
        prevista_semanal=prev_nat,
        prevista_semanal_ena=prev_ena,
        observada_mensal=obs_mes,
        meses_observados=meses,
        observada_semanal=obs_sem,
    )
