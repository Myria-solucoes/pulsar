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


def mes_estocastico(nome) -> int:
    """Mês do calendário do período estocástico (o seguinte ao mês inicial)."""
    return vazoes(nome).calendario.mes_inicial % 12 + 1
