"""PROBVAZ.DAT: probabilidades das folhas da árvore.

U19 §5.4 (F7-PB-01): acesso direto, RECL = NPOS*4, NREGP = NNOT/NPOS
arredondado para cima, até NPOS valores por registro. Nos pacotes públicos
os valores são float32 little-endian, o fim do último registro é zero e NNOT
é o número de folhas do estágio estocástico (F2-PB-02, F2-PB-03).
"""

from __future__ import annotations

import os

import numpy as np


def probabilidades_de_contagens(contagens, n_objetos: int) -> np.ndarray:
    """F7-PB-02: probabilidade do grupo = contagem/N (M18 eq. 5.9), dividida
    em float64 e guardada em float32 (iguais em bits aos PROBVAZ.DAT
    públicos)."""
    k = np.asarray(contagens, dtype=np.int64)
    if (k < 0).any() or k.sum() != n_objetos:
        raise ValueError(f"contagens somam {k.sum()}, esperado {n_objetos}")
    return (k / float(n_objetos)).astype(np.float32)


def serializar_probvaz(probabilidades, npos: int) -> bytes:
    """Bytes do PROBVAZ.DAT pelo laço do U19 §5.4."""
    p = np.asarray(probabilidades)
    if p.dtype != np.float32:
        raise TypeError(f"probabilidades devem ser float32, não {p.dtype}")
    nnot = len(p)
    nregp = -(-nnot // npos)
    buf = np.zeros(nregp * npos, dtype="<f4")
    buf[:nnot] = p
    return buf.tobytes()


def gravar_probvaz(caminho: str | os.PathLike, probabilidades, npos: int) -> None:
    with open(caminho, "wb") as f:
        f.write(serializar_probvaz(probabilidades, npos))
