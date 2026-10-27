"""Utilitários para arquivos de texto em formato fixo (colunas Fortran).

As colunas seguem a convenção dos manuais do CEPEL: começam em 1 e o
intervalo é fechado nos dois lados.
"""

from __future__ import annotations

import os
from pathlib import Path

# P-TXT-01: arquivos lidos como latin-1, aceitando CRLF e LF.
CODIFICACAO = "latin-1"


class ErroLeitura(ValueError):
    """Erro de formato num arquivo de entrada."""


def ler_bytes(origem: Path | bytes) -> bytes:
    """Conteúdo de um caminho, ou os próprios bytes (arquivos lidos de zip)."""
    if isinstance(origem, (bytes, bytearray)):
        return bytes(origem)
    return Path(origem).read_bytes()


def ler_linhas(caminho: Path | bytes) -> list[str]:
    """Lê um arquivo de texto e devolve as linhas sem o fim de linha."""
    dados = ler_bytes(caminho).decode(CODIFICACAO)
    linhas = dados.split("\n")
    if linhas and linhas[-1] == "":
        linhas.pop()
    return [l.rstrip("\r") for l in linhas]


def col(linha: str, c1: int, c2: int) -> str:
    """Trecho das colunas c1..c2 (base 1, inclusivas)."""
    return linha[c1 - 1 : c2]


def inteiro(linha: str, c1: int, c2: int, padrao: int | None = 0) -> int | None:
    """Campo Iw nas colunas c1..c2.

    P-TXT-02: campo em branco vale ``padrao`` (0, como a leitura formatada
    Fortran com brancos nulos).
    """
    t = col(linha, c1, c2).strip()
    if not t:
        return padrao
    try:
        return int(t)
    except ValueError as e:
        raise ErroLeitura(f"inteiro inválido nas colunas {c1}-{c2}: {linha!r}") from e


def real(linha: str, c1: int, c2: int, padrao: float | None = 0.0) -> float | None:
    t = col(linha, c1, c2).strip()
    if not t:
        return padrao
    try:
        return float(t)
    except ValueError as e:
        raise ErroLeitura(f"real inválido nas colunas {c1}-{c2}: {linha!r}") from e


def resolver(diretorio: Path, nome: str) -> Path | None:
    """Encontra ``nome`` em ``diretorio`` sem diferenciar maiúsculas.

    P-TXT-03: os decks públicos citam nomes em minúsculas (``dadger.rv0``,
    ``prevs.RV0``) para arquivos gravados em maiúsculas (``DADGER.RV0``).
    """
    diretorio = Path(diretorio)
    nome = nome.strip()
    if not nome:
        return None
    direto = diretorio / nome
    if direto.is_file():
        return direto
    alvo = nome.lower()
    for item in os.listdir(diretorio):
        if item.lower() == alvo and (diretorio / item).is_file():
            return diretorio / item
    return None
