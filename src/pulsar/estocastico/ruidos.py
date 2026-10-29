"""Amostra original de ruídos normais independentes (02 §8; lacuna L6).

Uma coluna por número de posto: a coluna do posto ``p`` é gerada por um
fluxo próprio, derivado da semente e de ``p``, então ela não muda quando
usinas entram, saem ou mudam de ordem no deck (versão 11 do GEVAZP,
R3031 e U11: semente associada ao número do posto).
Proveniência: P-RUI-01..05 em PROVENIENCIA.md.
"""

from __future__ import annotations

import numpy as np

# P-RUI-02: amostra original de 50 mil objetos (R3383 cap. 5 e conclusões;
# INFERIDO pelos denominadores do PROBVAZ.DAT, F2-PB-04, e pelo TESTES.REL,
# "N. SEGMENTOS GERADOS P/ CLUSTER : 50000").
N_OBJETOS = 50_000
# P-RUI-01 (ESCOLHA, lacuna L6): fluxo reservado ao sorteio dos centros
# iniciais do K-means; postos começam em 1.
FLUXO_CENTROS = 0
# P-LAT-04 (ESCOLHA, lacuna L6): subfluxo do ruído individual do posto
# lateral, separado do fluxo da coluna do posto na amostra original.
SUBFLUXO_INDIVIDUAL = 1
SIMETRIAS = ("nenhuma", "antitetica")


def _gerador(semente: int, fluxo: int, subfluxo: int | None = None) -> np.random.Generator:
    """P-RUI-01 (ESCOLHA, lacuna L6): PCG64 do NumPy (O'Neill 2014), um
    fluxo por chave ``(semente, fluxo)`` pela ``SeedSequence``; com
    ``subfluxo``, a chave ``(semente, fluxo, subfluxo)``."""
    if semente < 0 or fluxo < 0 or (subfluxo is not None and subfluxo < 0):
        raise ValueError("semente e fluxo devem ser não negativos")
    chave = (fluxo,) if subfluxo is None else (fluxo, subfluxo)
    return np.random.Generator(np.random.PCG64(np.random.SeedSequence(entropy=semente, spawn_key=chave)))


def amostra_original(postos, semente: int, n_objetos: int = N_OBJETOS, simetria: str = "nenhuma",
                     dtype=np.float64) -> np.ndarray:
    """Matriz [n_objetos, len(postos)] de ruídos N(0, 1) independentes.

    P-RUI-03: coluna do posto ``p`` = ``standard_normal`` do fluxo ``p``
    (ziggurat do NumPy). P-RUI-04 (ESCOLHA, lacuna L6): ``simetria`` =
    "nenhuma" (amostra aleatória simples) ou "antitetica" (a segunda metade
    é a primeira com o sinal trocado), uma leitura possível de "ruído
    simétrico" (U19 §3.3 reg. 4 = 2; GEVAZP.REL "CONSIDERANDO RUIDOS
    SIMETRICOS"), que nenhuma fonte pública define."""
    postos = [int(p) for p in postos]
    if len(set(postos)) != len(postos):
        raise ValueError("posto repetido na amostra de ruídos")
    if min(postos, default=1) < 1:
        raise ValueError("postos começam em 1")
    if simetria not in SIMETRIAS:
        raise ValueError(simetria)
    if simetria == "antitetica" and n_objetos % 2:
        raise ValueError("amostra antitética exige número par de objetos")
    meio = n_objetos // 2 if simetria == "antitetica" else n_objetos
    out = np.empty((n_objetos, len(postos)), dtype=dtype)
    for j, p in enumerate(postos):
        x = _gerador(semente, p).standard_normal(meio)
        if simetria == "antitetica":
            x = np.concatenate([x, -x])
        out[:, j] = x
    return out


def sorteia_centros(n_objetos: int, k: int, semente: int) -> np.ndarray:
    """P-RUI-05 (DOC M18 §5.1.4 e NT 42 no R13612: centros iniciais são
    objetos da amostra sorteados; ESCOLHA, lacuna L6: K índices distintos
    sorteados sem reposição pelo fluxo ``FLUXO_CENTROS``, na ordem do
    sorteio)."""
    if not 1 <= k <= n_objetos:
        raise ValueError(f"K = {k} fora de 1..{n_objetos}")
    return _gerador(semente, FLUXO_CENTROS).choice(n_objetos, size=k, replace=False)


def ruido_individual(posto: int, k: int, semente: int) -> np.ndarray:
    """P-LAT-04: ruído próprio b1 do posto lateral, sorteado nó a nó fora da
    amostra agregada (R23954 §2: o ruído de cada posto lateral é gerado
    depois do dos principais e individualmente). O valor do nó j é o j-ésimo
    N(0, 1) do subfluxo ``(posto, SUBFLUXO_INDIVIDUAL)``: não depende de K
    nem da agregação, como nos pacotes das versões 8.1.6 e 10.0.0
    (INFERIDO). Gerador e subfluxo: ESCOLHA (lacuna L6)."""
    if int(posto) < 1:
        raise ValueError("postos começam em 1")
    if k < 1:
        raise ValueError(f"K = {k} < 1")
    return _gerador(semente, int(posto), SUBFLUXO_INDIVIDUAL).standard_normal(k)
