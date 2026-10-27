"""Registro dos pacotes GEVAZP completos usados como oráculo (03 §1.1, §1.1b).

Cada pacote tem um nome curto: o nome da pasta (``202609`` em
``decks/ons-pacote-gevazp/``, ``202402_rev2`` em ``decks/ons-sintegre/``).

A seleção vem de ``PULSAR_DECKS`` (ou da opção ``--decks`` do pytest, que a
define):

* ``amostra`` (padrão): os dois pacotes originais e quatro do SINtegre que
  cobrem o ramo PAR(p), a revisão de fevereiro bissexto e as versões 10 e 11;
* ``todos``: os 61 pacotes;
* ``originais``: só os dois de ``ons-pacote-gevazp``;
* uma lista separada por vírgulas de nomes.
"""

from __future__ import annotations

import functools
import os
from pathlib import Path, PosixPath

RAIZ = Path(__file__).resolve().parents[1]
ORIGINAIS = RAIZ / "decks" / "ons-pacote-gevazp"
SINTEGRE = RAIZ / "decks" / "ons-sintegre"

AMOSTRA = ("202609", "202610", "202201_pmo", "202402_rev2", "202507_pmo", "202605_pmo")


@functools.lru_cache(maxsize=None)
def todos() -> dict[str, Path]:
    """{nome: pasta} de todos os pacotes com GEVAZP.REL, SINtegre primeiro."""
    out: dict[str, Path] = {}
    for raiz in (SINTEGRE, ORIGINAIS):
        if raiz.is_dir():
            for d in sorted(raiz.iterdir()):
                if (d / "GEVAZP.REL").is_file():
                    out[d.name] = d
    return out


def selecionados() -> list[str]:
    sel = os.environ.get("PULSAR_DECKS", "amostra").strip() or "amostra"
    t = todos()
    if sel == "todos":
        return list(t)
    if sel == "amostra":
        nomes = list(AMOSTRA)
    elif sel == "originais":
        nomes = [n for n, p in t.items() if p.parent == ORIGINAIS]
    else:
        nomes = [n.strip() for n in sel.split(",") if n.strip()]
        faltam = [n for n in nomes if n not in t]
        if faltam:
            raise ValueError(f"PULSAR_DECKS: pacotes desconhecidos {faltam}")
    return [n for n in nomes if n in t]


class PastaPacote(PosixPath):
    """Pasta de um pacote: ``pasta / "VAZOES.RV0"`` acha o arquivo sem
    diferenciar maiúsculas, como a leitura das entradas (P-TXT-03); alguns
    pacotes gravam ``vazoes.rv0`` ou ``vazdcp.rel``."""

    def __truediv__(self, nome):
        p = Path(super().__truediv__(nome))
        if not p.exists():
            alvo = str(nome).lower()
            alt = next((q for q in Path(self).iterdir() if q.name.lower() == alvo), None)
            if alt is not None:
                return alt
        return p


def pasta(nome: str) -> Path:
    try:
        return PastaPacote(todos()[nome])
    except KeyError:
        raise KeyError(f"pacote {nome!r} não está em decks/") from None


class Pastas:
    """Raiz virtual dos pacotes: ``DECKS / nome`` dá a pasta do pacote, e
    ``iterdir`` percorre os pacotes selecionados."""

    def __truediv__(self, nome: str) -> Path:
        return pasta(nome)

    def is_dir(self) -> bool:
        return bool(todos())

    def iterdir(self):
        return (pasta(n) for n in selecionados())


DECKS = Pastas()
