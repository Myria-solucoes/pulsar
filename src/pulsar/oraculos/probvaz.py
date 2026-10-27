"""PROBVAZ.DAT: probabilidades dos nós da árvore.

Layout documentado em U19 §5.4: acesso direto, RECL = NPOS*4, os NNOT valores
em sequência, até NPOS por registro. Nos pacotes analisados os valores são
float32 e NNOT é o número de folhas do período estocástico (os nós semanais,
determinísticos, não entram). Ver docs/layout-PROBVAZ.DAT.md.
"""

from __future__ import annotations

import numpy as np

from .acesso_direto import NPOS_PADRAO, ler_bytes, numero_de_registros


def ler_probvaz(caminho, n_nos: int | None = None, npos: int = NPOS_PADRAO) -> np.ndarray:
    """Probabilidades (float32) dos nós.

    Sem `n_nos`, devolve o vetor sem os zeros finais de preenchimento.
    """
    dados = ler_bytes(caminho)
    numero_de_registros(dados, npos * 4, str(caminho))
    p = np.frombuffer(dados, "<f4").copy()
    if n_nos is None:
        nz = np.nonzero(p)[0]
        n_nos = int(nz[-1]) + 1 if len(nz) else 0
    if n_nos > len(p):
        raise ValueError(f"{caminho}: {n_nos} nós pedidos, arquivo tem {len(p)} valores")
    return p[:n_nos]
