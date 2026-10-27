"""Leitores das entradas do modo DECOMP (U19 §3–4)."""

from .deck import Deck, ler_deck
from .texto import ErroLeitura

__all__ = ["Deck", "ErroLeitura", "ler_deck"]
