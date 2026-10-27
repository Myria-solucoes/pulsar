"""Caminhos e casos comuns aos testes."""

from __future__ import annotations

import sys
from functools import lru_cache
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

from pulsar.configuracao import montar_configuracao  # noqa: E402
from pulsar.entradas import ler_deck  # noqa: E402

import pacotes  # noqa: E402

DECKS = pacotes.DECKS

# Pacotes completos selecionados (tests/pacotes.py). ``None`` segue a cadeia
# CASO.DAT -> ARQUIVOS.DAT -> lista do DECOMP, que é a execução cujas saídas
# estão no pacote (202609: RV1).
COMPLETOS = [(nome, None) for nome in pacotes.selecionados()]
# T11/T12 (parte estocástica): só os pacotes originais selecionados.
ESTOCASTICOS = [(n, d) for n, d in COMPLETOS if n in pacotes.originais([n])]
# Outras revisões do mesmo pacote, só para leitura (T0).
SO_LEITURA = [("202609", "DADGER.RV0")] if "202609" in pacotes.selecionados() else []


@lru_cache(maxsize=None)
def deck(nome: str, dadger: str | None = None):
    return ler_deck(DECKS / nome, dadger=dadger)


@lru_cache(maxsize=None)
def configuracao(nome: str, dadger: str | None = None):
    return montar_configuracao(deck(nome, dadger))
