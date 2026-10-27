"""Apoio do T12 (F9): revisões dos pacotes, VAZOES.RVx gerado pela cadeia da
CLI com as agregações em cache da F8 e estatísticas de 03 §5 sobre os blocos
inteiros do VAZOES.RVx.

As revisões de um pacote compartilham a agregação da semente quando têm as
mesmas usinas e o mesmo K (P-INT-01): o cache ``cache/f8/agr_<deck>_<s>``
serve às duas revisões do 202609.
"""

from __future__ import annotations

import functools

import numpy as np

import aceitacao_f8 as R
import apoio_f8
import base
from pulsar import oraculos as O
from pulsar.cli import ler_revisao
from pulsar.configuracao import montar_configuracao
from pulsar.empacotamento import serializar_vazoes_rvx
from pulsar.estocastico.geracao import OpcoesGeracao, gerar, montar_vazoes, preparar

NPOS = 320


def revisoes() -> list[tuple[str, str]]:
    """(deck, RVn) de cada VAZOES.RVx publicado nos pacotes completos."""
    out = []
    for nome, _ in base.ESTOCASTICOS:
        for p in sorted((base.DECKS / nome).glob("VAZOES.RV*")):
            out.append((nome, p.suffix.lstrip(".").upper()))
    return out


def com_saidas(nome: str, rev: str) -> bool:
    """A revisão cujas saídas intermediárias (GEVAZP.OUT…) estão no pacote."""
    return ler_revisao(base.DECKS / nome)[1] == rev


@functools.lru_cache(maxsize=None)
def deck(nome, rev):
    return ler_revisao(base.DECKS / nome, rev)[0]


@functools.lru_cache(maxsize=None)
def configuracao(nome, rev):
    return montar_configuracao(deck(nome, rev))


@functools.lru_cache(maxsize=None)
def preparo(nome, rev):
    return preparar(deck(nome, rev), configuracao(nome, rev), OpcoesGeracao(), apoio_f8.ajustes(nome))


@functools.lru_cache(maxsize=None)
def oficial(nome, rev):
    return O.ler_vazoes_decomp(base.DECKS / nome / f"VAZOES.{rev}")


def oficial_bytes(nome, rev) -> bytes:
    return (base.DECKS / nome / f"VAZOES.{rev}").read_bytes()


@functools.lru_cache(maxsize=None)
def gerado(nome, rev, semente):
    """(ArvoreVazoes, bytes do VAZOES.RVx, Resultado) da cadeia da CLI
    (``cli.executar``) com a agregação da semente em cache."""
    pr = preparo(nome, rev)
    ag = apoio_f8.agregacao(nome, semente)
    if ag.postos != tuple(pr.postos) or ag.contagens.size != pr.k:
        raise AssertionError(f"{nome} {rev}: agregação em cache de outra configuração")
    d, cfg = deck(nome, rev), configuracao(nome, rev)
    r = gerar(d, cfg, OpcoesGeracao(semente=semente), agregacao=ag, preparo=pr)
    a = montar_vazoes(d, cfg, r, NPOS)
    return a, serializar_vazoes_rvx(a), r


def folhas(v) -> np.ndarray:
    """Probabilidades das folhas (último estágio) do registro 4."""
    return np.asarray(v.probabilidades)[-v.aberturas[-1]:]


@functools.lru_cache(maxsize=None)
def colunas(nome, rev, bloco="gerada_mensal") -> list[int]:
    """Colunas do bloco com dispersão no VAZOES.RVx oficial."""
    g = np.asarray(getattr(oficial(nome, rev), bloco), float)
    return [j for j in range(g.shape[1]) if g[:, j].std() > 0]


@functools.lru_cache(maxsize=None)
def estatisticas_oficiais(nome, rev, bloco="gerada_mensal"):
    v = oficial(nome, rev)
    z = np.asarray(getattr(v, bloco), float)[:, colunas(nome, rev, bloco)]
    p = folhas(v)
    return R.estatisticas(z, p), R.correlacoes(z, p)


@functools.lru_cache(maxsize=None)
def estatisticas_sementes(nome, rev, bloco="gerada_mensal"):
    est, cor = [], []
    for s in apoio_f8.SEMENTES:
        a, _, _ = gerado(nome, rev, s)
        z = np.asarray(getattr(a, bloco), float)[:, colunas(nome, rev, bloco)]
        p = np.asarray(a.probabilidades)[-a.aberturas[-1]:]
        est.append(R.estatisticas(z, p))
        cor.append(R.correlacoes(z, p))
    return {k: np.array([e[k] for e in est]) for k in R.ESTATISTICAS}, np.array(cor)


def fracoes(nome, rev, bloco="gerada_mensal", faixa="minmax") -> dict[str, float]:
    """03 §5 sobre o VAZOES.RVx (P-INT-03): fração das colunas (e pares) em
    que a estatística oficial cai na faixa das 20 sementes."""
    eo, co = estatisticas_oficiais(nome, rev, bloco)
    es, cs = estatisticas_sementes(nome, rev, bloco)
    return R._fracoes(eo, co, es, cs, faixa)


def fracoes_referencia(nome, rev, bloco="gerada_mensal", faixa="minmax") -> dict[str, float]:
    """Cada semente no papel do oficial contra as outras 19 (média)."""
    es, cs = estatisticas_sementes(nome, rev, bloco)
    n = len(cs)
    acc = []
    for i in range(n):
        o = [j for j in range(n) if j != i]
        acc.append(R._fracoes({k: v[i] for k, v in es.items()}, cs[i], {k: v[o] for k, v in es.items()}, cs[o], faixa))
    return {k: float(np.mean([a[k] for a in acc])) for k in acc[0]}
