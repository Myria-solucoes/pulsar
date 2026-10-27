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

# Variantes avaliadas no T11 (lacunas L6, L7, L8 e L11). "base" = padrão.
# "f8" = padrão da primeira versão da F8 (antes da F11): M_t = 0, momentos
# teóricos, lateral com a correlação anual e ruído próprio.
F8 = OpcoesGeracao(rota_limite="zero", momentos="teoricos", correlacao_lateral="anual", ruido_lateral="proprio")
VARIANTES = {
    "base": OpcoesGeracao(),
    "f8": F8,
    "desvio_simples": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="simples")),
    "desvio_amostral": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="amostral")),
    "desvio_zero": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="zero")),
    "por_usina": OpcoesGeracao(agregacao=OpcoesAgregacao(aplicacao="por_usina")),
    "sem_fator": OpcoesGeracao(agregacao=OpcoesAgregacao(desvio="nenhum")),
    "cubica_residuos": OpcoesGeracao(rota_limite="cubica_residuos"),
    "cubica_vazoes": OpcoesGeracao(rota_limite="cubica_vazoes"),
    "quantis": OpcoesGeracao(rota_limite="quantis"),
    "zero": OpcoesGeracao(rota_limite="zero"),
    "momentos_teoricos": OpcoesGeracao(momentos="teoricos"),
    "lateral_anual": OpcoesGeracao(correlacao_lateral="anual"),
    "lateral_proprio": OpcoesGeracao(ruido_lateral="proprio"),
    "antitetica": OpcoesGeracao(agregacao=OpcoesAgregacao(simetria="antitetica")),
}


@functools.lru_cache(maxsize=None)
def preparo(nome, correlacao_lateral="mensal", ruido_lateral="nenhum"):
    op = OpcoesGeracao(correlacao_lateral=correlacao_lateral, ruido_lateral=ruido_lateral)
    return preparar(base.deck(nome), base.configuracao(nome), op, ajustes(nome))


@functools.lru_cache(maxsize=None)
def ajustes(nome):
    d, c = base.deck(nome), base.configuracao(nome)
    ss = historico.series_incrementais(d.historico, c)
    op = parp.opcoes_do_deck(d)
    return [parp.ajustar(s, op) for s in historico.series_ajustadas(ss, d.dadger.vazoes.ajuste_todas)]


def _arq(*partes) -> Path:
    CACHE.mkdir(parents=True, exist_ok=True)
    return CACHE / ("_".join(str(p) for p in partes) + ".npz")


def _so_cache(nome: str) -> bool:
    """Não recalcular agregações: na varredura (``PULSAR_SO_CACHE``) e, no
    modo rápido (amostra padrão), nos pacotes que não são os originais,
    onde 20 sementes levariam horas."""
    import pacotes
    sel = os.environ.get("PULSAR_DECKS", "amostra").strip() or "amostra"
    return bool(os.environ.get("PULSAR_SO_CACHE")) or (sel == "amostra" and not pacotes.originais([nome]))


def agregacao(nome: str, semente: int, simetria: str = "nenhuma", ruido_lateral: str = "nenhum") -> Agregacao:
    """Agregação da geração de ``nome`` com a semente; calculada uma vez.
    Com ``ruido_lateral="proprio"`` o vetor agregado tem uma componente a
    mais por posto lateral (P-AGR-07)."""
    f = _arq("agr", nome, semente, simetria, ruido_lateral)
    if not f.exists() and _so_cache(nome):
        # varredura dos 61 pacotes (ferramentas/revalidacao.py --so-cache):
        # não recalcula agregações; o teste é pulado e aparece no resumo
        import pytest
        pytest.skip(f"agregação {nome}/semente {semente} fora do cache (PULSAR_SO_CACHE ou amostra)")
    if f.exists():
        z = np.load(f)
        return Agregacao(tuple(int(p) for p in z["postos"]), z["centroides"], z["contagens"], int(z["n"]),
                         z["desvios"], z["fator"], z["ruidos"], int(z["iteracoes"]), int(z["ifault"]))
    pr = preparo(nome, ruido_lateral=ruido_lateral)
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
    ag = agregacao(nome, semente, op.agregacao.simetria, op.ruido_lateral)
    pr = preparo(nome, op.correlacao_lateral, op.ruido_lateral)
    r = gerar(base.deck(nome), base.configuracao(nome), op, agregacao=ag, preparo=pr)
    return r.totalizadas.incrementais, r.probabilidades, r
