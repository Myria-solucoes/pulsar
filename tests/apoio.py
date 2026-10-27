"""Carregamentos em cache por deck, compartilhados pelos testes de oráculos."""

from __future__ import annotations

import functools

import numpy as np

from conftest import deck
from pulsar import oraculos as O
from pulsar.oraculos import texto as T


def nint(x):
    """Inteiro mais próximo, empate para longe do zero (NINT do Fortran)."""
    x = np.asarray(x, dtype=np.float64)
    return np.where(x >= 0, np.floor(x + 0.5), np.ceil(x - 0.5)).astype(np.int64)


@functools.lru_cache(maxsize=None)
def config(nome):
    return T.ler_configuracao(deck(nome).arq("GEVAZP.REL"))


@functools.lru_cache(maxsize=None)
def nint_por_nome(nome):
    return {u.nome: u.nint for u in config(nome)}


@functools.lru_cache(maxsize=None)
def series_rel(nome):
    return T.ler_series_incrementais(deck(nome).arq("GEVAZP.REL"))


@functools.lru_cache(maxsize=None)
def correlacoes_rel(nome, tabela):
    return T.ler_correlacoes(deck(nome).arq("GEVAZP.REL"), tabela)


@functools.lru_cache(maxsize=None)
def estat_geradas_rel(nome, secao):
    return T.ler_estatisticas_geradas(deck(nome).arq("GEVAZP.REL"), secao)


@functools.lru_cache(maxsize=None)
def tendencia_rel(nome):
    return T.ler_tendencia(deck(nome).arq("GEVAZP.REL"))


@functools.lru_cache(maxsize=None)
def previsoes_rel(nome):
    return T.ler_previsoes(deck(nome).arq("GEVAZP.REL"))


@functools.lru_cache(maxsize=None)
def correli(nome):
    return O.ler_correli(deck(nome).arq("correli.out"))


@functools.lru_cache(maxsize=None)
def correlt(nome):
    return O.ler_correlt(deck(nome).arq("correlt.out"))


@functools.lru_cache(maxsize=None)
def vazoes(nome):
    return O.ler_vazoes_decomp(deck(nome).vazoes)


@functools.lru_cache(maxsize=None)
def qpast(nome):
    return O.ler_qpast(deck(nome).arq("QPAST.DAT"))


@functools.lru_cache(maxsize=None)
def probvaz(nome):
    return O.ler_probvaz(deck(nome).arq("PROBVAZ.DAT"))


@functools.lru_cache(maxsize=None)
def gevazp_out(nome):
    return O.ler_incrementais_geradas(deck(nome).arq("GEVAZP.OUT"))


@functools.lru_cache(maxsize=None)
def versao_emulada(nome, rev=None) -> str:
    """Versão do GEVAZP que gravou o VAZOES.RVx do pacote ("8.1.6" no 9_L,
    "10.0.0", "11.0.0", "11.0.2"), decodificada do registro 3 oficial pela
    F2-VZ-04b. A versão gravada é parâmetro do Pulsar (P-VZD-04, F7-VZ-03):
    é a identidade do programa, não sai das entradas; os testes byte a byte
    emulam a do pacote (P-VZD-09)."""
    d = deck(nome)
    v = O.ler_vazoes_decomp(d.vazoes if rev is None else d.arq(f"VAZOES.{rev}"))
    c = v.calendario.versao_codigo
    return f"{c // 10000}.{c // 100 % 100}.{c % 100}"


def opcoes_empacotamento(nome, rev=None, **kw):
    from pulsar.empacotamento import OpcoesEmpacotamento
    return OpcoesEmpacotamento(versao=versao_emulada(nome, rev), **kw)


def opcoes_vazoes(nome, rev=None, **kw):
    from pulsar import vazoes_deterministicos as VD
    return VD.OpcoesVazoes(versao=tuple(int(x) for x in versao_emulada(nome, rev).split(".")), **kw)


def mes_estocastico(nome) -> int:
    """Mês do calendário do período estocástico (o seguinte ao mês inicial)."""
    return vazoes(nome).calendario.mes_inicial % 12 + 1
