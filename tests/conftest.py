"""Fixtures comuns: um caso por pacote GEVAZP completo em decks/ons-pacote-gevazp/."""

from __future__ import annotations

import functools
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[1]
PACOTES = RAIZ / "decks" / "ons-pacote-gevazp"


def _decks() -> list[str]:
    if not PACOTES.is_dir():
        return []
    return sorted(d.name for d in PACOTES.iterdir() if (d / "GEVAZP.REL").is_file())


class Deck:
    """Um pacote GEVAZP publicado e a revisão que gerou as suas saídas."""

    def __init__(self, nome: str):
        self.nome = nome
        self.dir = PACOTES / nome

    def __repr__(self):
        return f"Deck({self.nome})"

    def arq(self, nome: str) -> Path:
        p = self.dir / nome
        if not p.is_file():
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
        return sorted(self.dir.glob("VAZOES.RV*"))


@functools.lru_cache(maxsize=None)
def deck(nome: str) -> Deck:
    return Deck(nome)


@pytest.fixture(params=_decks() or [pytest.param(None, marks=pytest.mark.skip("sem decks"))])
def pacote(request) -> Deck:
    return deck(request.param)
