"""Ajustes PAR(p)/PAR(p)-A e oráculos de texto, em cache por deck (T2–T4)."""

from __future__ import annotations

import functools
import math

import numpy as np

import apoio
import base
from conftest import deck as pacote_deck
from pulsar import historico, parp
from pulsar.oraculos import ler_vordem
from pulsar.oraculos import texto as T


@functools.lru_cache(maxsize=None)
def series(nome):
    """Séries incrementais (sem as PN) da configuração reconstruída pela F1."""
    d, c = base.deck(nome), base.configuracao(nome)
    return historico.series_incrementais(d.historico, c)


@functools.lru_cache(maxsize=None)
def ajustes(nome) -> dict[str, parp.AjustePAR]:
    d = base.deck(nome)
    op = parp.opcoes_do_deck(d)
    return {s.nome: parp.ajustar(s, op) for s in historico.series_ajustadas(series(nome))}


@functools.lru_cache(maxsize=None)
def residuos(nome) -> dict[str, parp.Residuos]:
    return {k: parp.residuos(a) for k, a in ajustes(nome).items()}


@functools.lru_cache(maxsize=None)
def vordem(nome):
    return ler_vordem(pacote_deck(nome).arq("vordem.out"))


@functools.lru_cache(maxsize=None)
def residuos_rel(nome):
    return T.ler_residuos(pacote_deck(nome).arq("GEVAZP.REL"))


def correli_da_serie(nome, serie_nome):
    return apoio.correli(nome).serie(apoio.nint_por_nome(nome)[serie_nome])


def tol_3_algarismos(impresso: float) -> float:
    """Meia unidade do 3º algarismo do formato 0.dddE±ee do GEVAZP.REL."""
    if impresso == 0.0:  # o formato E só imprime 0.000E+00 para o zero exato
        return 0.0
    e = math.floor(math.log10(abs(impresso))) + 1
    return 0.5 * 10.0 ** (e - 3) * (1 + 1e-9)


def confere_3_algarismos(calc, impresso) -> np.ndarray:
    """Máscara dos valores que arredondam para o texto impresso."""
    calc, impresso = np.asarray(calc, float), np.asarray(impresso, float)
    tol = np.vectorize(tol_3_algarismos, otypes=[float])(impresso)
    return np.abs(calc - impresso) <= tol
