"""Fixtures comuns: um caso por pacote GEVAZP completo selecionado
(tests/pacotes.py: ``--decks amostra|todos|originais|<lista>``)."""

from __future__ import annotations

import functools
import re
from pathlib import Path

import os
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pacotes  # noqa: E402

RAIZ = pacotes.RAIZ


def pytest_addoption(parser):
    parser.addoption("--decks", default=None,
                     help="pacotes: amostra (padrão), todos, originais ou lista separada por vírgulas")


def pytest_configure(config):
    sel = config.getoption("--decks")
    if sel:
        os.environ["PULSAR_DECKS"] = sel


def _decks() -> list[str]:
    return pacotes.selecionados()


class Deck:
    """Um pacote GEVAZP publicado e a revisão que gerou as suas saídas."""

    def __init__(self, nome: str):
        self.nome = nome
        self.dir = pacotes.pasta(nome)

    def __repr__(self):
        return f"Deck({self.nome})"

    def arq(self, nome: str) -> Path:
        p = self.dir / nome
        if not p.is_file():
            # Como P-TXT-03: alguns pacotes gravam em minúsculas (202301:
            # vazoes.rv0, VAZDCP.REL ausente ou vazdcp.rel).
            p = next((q for q in self.dir.iterdir() if q.name.lower() == nome.lower()), None)
        if p is None or not p.is_file():
            pytest.skip(f"{self.nome}: {nome} ausente")
        return p

    @functools.cached_property
    def revisao(self) -> str:
        """Revisão executada (as saídas do pacote são desta), lida do GEVAZP.REL."""
        with open(self.arq("GEVAZP.REL"), encoding="latin-1") as f:
            for linha in f:
                m = re.search(r"ARQUIVO DE REVISAO DO PMO\s*:\s*(RV\d+)", linha)
                if m:
                    return m[1]
        raise AssertionError("revisão não encontrada no GEVAZP.REL")

    @functools.cached_property
    def vazoes(self) -> Path:
        return self.arq(f"VAZOES.{self.revisao}")

    def revisoes_vazoes(self) -> list[Path]:
        return sorted(p for p in self.dir.iterdir() if p.name.upper().startswith("VAZOES.RV"))


@functools.lru_cache(maxsize=None)
def deck(nome: str) -> Deck:
    return Deck(nome)


def pytest_generate_tests(metafunc):
    # Parametriza depois do pytest_configure, para respeitar --decks.
    if "pacote" in metafunc.fixturenames:
        nomes = _decks()
        if metafunc.module.__name__.startswith(("test_t11", "test_t12")):
            nomes = pacotes.originais(nomes)
        metafunc.parametrize("pacote", nomes or [pytest.param(None, marks=pytest.mark.skip("sem decks"))],
                             indirect=True)


@pytest.fixture
def pacote(request) -> Deck:
    return deck(request.param)
