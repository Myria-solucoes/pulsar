"""Utilitários para arquivos Fortran de acesso direto não formatado.

Esses arquivos não têm marcadores de registro: são uma sequência de registros
de tamanho fixo (RECL bytes), little-endian. Ver docs/layout-*.md.
"""

from __future__ import annotations

import os
import struct

import numpy as np

# Número de postos do arquivo de vazões históricas: 320 ou 600.
# DOC: U19 §5.3.1.2 e §5.4 ("ZPOS/NPOS = total de postos ... (320 ou 600)").
NPOS_PADRAO = 320


def ler_bytes(caminho: str | os.PathLike) -> bytes:
    with open(caminho, "rb") as f:
        return f.read()


def numero_de_registros(dados: bytes, recl: int, caminho: str = "") -> int:
    if len(dados) % recl:
        raise ValueError(
            f"{caminho}: tamanho {len(dados)} não é múltiplo do registro {recl}"
        )
    return len(dados) // recl


def registro(dados: bytes, recl: int, k: int) -> bytes:
    """Registro k (numeração Fortran, a partir de 1)."""
    if k < 1 or k * recl > len(dados):
        raise IndexError(f"registro {k} fora do arquivo")
    return dados[recl * (k - 1) : recl * k]


def matriz_f8(dados: bytes, ncol: int) -> np.ndarray:
    """Arquivo inteiro como matriz float64 (nreg x ncol)."""
    return np.frombuffer(dados, "<f8").reshape(-1, ncol).copy()


def matriz_i4(dados: bytes, ncol: int) -> np.ndarray:
    return np.frombuffer(dados, "<i4").reshape(-1, ncol).copy()


def i4(buf: bytes, deslocamento: int = 0) -> int:
    return struct.unpack_from("<i", buf, deslocamento)[0]


def f8(buf: bytes, n: int, deslocamento: int = 0) -> np.ndarray:
    return np.frombuffer(buf, "<f8", count=n, offset=deslocamento).copy()
