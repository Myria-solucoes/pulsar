"""Gerações da F8 em cache, por deck, semente e variante (T10, T11).

A agregação (amostra de 50 mil objetos e K-means) é o passo caro (~2 min) e
não depende das variantes da lognormal nem do fator de compensação; ela é
guardada em ``cache/f8/`` e reaproveitada. ``ferramentas/sementes_f8.py``
preenche o cache em paralelo.
"""

from __future__ import annotations

import functools
import os
from dataclasses import replace
from pathlib import Path

import numpy as np

import base
from pulsar import historico, parp
from pulsar.estocastico.agregacao import Agregacao, OpcoesAgregacao, agregar
from pulsar.estocastico.geracao import OpcoesGeracao, gerar, preparar

CACHE = base.RAIZ / "cache" / "f8"
# 03 §5 item 1: 20 sementes por deck.
SEMENTES = tuple(range(1, 21))

# Variantes avaliadas no T11 (lacunas L6, L7 e L8). "base" = padrão.
VARIANTES = {
    "base": OpcoesGeracao(),
    "desvio_simples": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="simples")),
    "desvio_amostral": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="amostral")),
    "desvio_zero": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="zero")),
    "por_usina": OpcoesGeracao(agregacao=OpcoesAgregacao(aplicacao="por_usina")),
    "sem_fator": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="nenhum")),
    "cubica_residuos": OpcoesGeracao(rota_limite="cubica_residuos"),
    "cubica_vazoes": OpcoesGeracao(rota_limite="cubica_vazoes"),
    "quantis": OpcoesGeracao(rota_limite="quantis"),
    "momentos_historicos": OpcoesGeracao(momentos="historicos"),
    "antitetica": OpcoesGeracao(agregacao=OpcoesAgregacao(simetria="antitetica")),
}


@functools.lru_cache(maxsize=None)
def preparo(nome):
    return preparar(base.deck(nome), base.configuracao(nome), OpcoesGeracao(), ajustes(nome))


@functools.lru_cache(maxsize=None)
def ajustes(nome):
    d, c = base.deck(nome), base.configuracao(nome)
    ss = historico.series_incrementais(d.historico, c)
    op = parp.opcoes_do_deck(d)
    return [parp.ajustar(s, op) for s in historico.series_ajustadas(ss, d.dadger.vazoes.ajuste_todas)]


def _arq(*partes) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / ("_".join(str(p) for p in partes) + ".npz")


def agregacao(nome: str, semente: int, simetria: str = "nenhuma") -> Agregacao:
    """Agregação da geração de ``nome`` com a semente; calculada uma vez."""
    f = _arq("agr", nome, semente, simetria)
    if not f.exists() and os.environ.get("PULSAR_SO_CACHE"):
        # varredura dos 61 pacotes (ferramentas/revalidacao.py --so-cache):
        # não recalcula agregações; o teste é pulado e aparece no resumo
        import pytest
        pytest.skip(f"agregação {nome}/semente {semente} fora do cache (PULSAR_SO_CACHE)")
    if f.exists():
        z = np.load(f)
        return Agregacao(tuple(int(p) for p in z["postos"]), z["centroides"], z["contagens"], int(z["n"]),
                         z["desvios"], z["fator"], z["ruidos"], int(z["iteracoes"]), int(z["ifault"]))
    pr = preparo(nome)
    a = agregar(pr.postos, pr.k, semente, OpcoesAgregacao(simetria=simetria))
    tmp = f.with_suffix(".tmp.npz")
    np.savez(tmp, postos=np.array(a.postos), centroides=a.centroides, contagens=a.contagens, n=a.n_objetos,
             desvios=a.desvios, fator=a.fator, ruidos=a.ruidos, iteracoes=a.iteracoes, ifault=a.ifault)
    os.replace(tmp, f)
    return a


@functools.lru_cache(maxsize=None)
def arvore(nome: str, semente: int, variante: str = "base"):
    """(incrementais do GEVAZP.OUT [K, usinas], probabilidades float32,
    Resultado) da variante com a semente."""
    op = replace(VARIANTES[variante], semente=semente)
    ag = agregacao(nome, semente, op.agregacao.simetria)
    r = gerar(base.deck(nome), base.configuracao(nome), op, agregacao=ag, preparo=preparo(nome))
    return r.totalizadas.incrementais, r.probabilidades, r
