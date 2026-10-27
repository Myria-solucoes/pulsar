"""Totalização em cascata e incrementais recalculadas (M18 §4.3.4, Figura 4.4,
passos 2 a 4; L-INC eq. 1).

Matrizes ``[cenário, usina]`` com as usinas na ordem da configuração completa
(``Configuracao.completa``: base + postos laterais, P-CFG-11), a mesma ordem
das colunas dos arquivos em árvore (F2-ARV-02).
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ..configuracao import LATERAL, NEWAVE, NULO, Configuracao
from .defasagem import MontanteDefasado, total_defasado

# F6-TOT-03 (ESCOLHA, lacuna L20): ordem da soma dos totais de montante.
# "configuracao": inc + T(m1) + T(m2) + ..., montantes na ordem da
# configuração; "inversa": inc + T(mk) + ... + T(m1), a inversa exata da
# subtração de F6-INC-01 (usada no transplante a partir do GEVAZP.OUT).
ORDENS = ("configuracao", "inversa")


@dataclass(frozen=True)
class OpcoesTotalizacao:
    ordem: str = "configuracao"
    # F6-TOT-02 (DOC, U19 §4.11): usinas PARTIF (status PN) têm incremental
    # nula no mês estocástico; com True a incremental de entrada é ignorada.
    zerar_pn: bool = True

    def __post_init__(self):
        if self.ordem not in ORDENS:
            raise ValueError(self.ordem)


def _indices(cfg: Configuracao) -> dict[int, int]:
    return {u.numero: i for i, u in enumerate(cfg.completa)}


def _coluna_lateral(cfg: Configuracao, numero: int) -> int:
    for i, u in enumerate(cfg.completa):
        if u.status == LATERAL and u.origem_lateral == numero:
            return i
    raise ValueError(f"usina {numero}: posto lateral sem coluna na configuração completa")


def totalizar(
    incrementais: np.ndarray,
    cfg: Configuracao,
    defasagem: Mapping[int, Sequence[MontanteDefasado]] | None = None,
    opcoes: OpcoesTotalizacao | None = None,
) -> np.ndarray:
    """Vazões totais a partir das incrementais geradas (M18 Figura 4.4,
    passos 2 e 3; M18 §4.3.3.2).

    ``incrementais[:, i]`` é a incremental gerada da i-ésima usina da
    configuração completa; na coluna de um posto lateral (status PL), a
    vazão lateral gerada.

    - F6-TOT-01 (DOC, L-INC eq. 1; M18 §4.3.3.2 alternativa (i)): total =
      incremental + Σ totais das usinas imediatamente a montante, inclusive
      as NW (F2-REL-02: a incremental da NW entra na jusante).
    - F6-TOT-04 (INFERIDO): posto lateral: total = vazão lateral gerada.
    - F6-DEF-01: usina com posto lateral e defasagem linear (campo 13 = 2)
      usa a alternativa (ii), eq. 4.21 do M18, com os dados de
      ``defasagem[numero]``.
    """
    op = opcoes or OpcoesTotalizacao()
    usinas = cfg.completa
    inc = np.asarray(incrementais, dtype=np.float64)
    if inc.ndim != 2 or inc.shape[1] < len(usinas):
        raise ValueError(f"incrementais com forma {inc.shape} para {len(usinas)} usinas")
    idx = _indices(cfg)
    tot = np.zeros((inc.shape[0], len(usinas)))
    feito = [False] * len(usinas)
    pilha: set[int] = set()

    def calc(i: int):
        if feito[i]:
            return
        u = usinas[i]
        if i in pilha:
            raise ValueError(f"ciclo de jusantes na usina {u.numero}")
        pilha.add(i)
        if u.status == LATERAL:
            t = inc[:, i].copy()
        else:
            mont = [idx[m] for m in cfg.montante(u.numero)]
            for m in mont:
                calc(m)
            if u.posto_lateral and u.defasagem == 2:
                # F6-DEF-01 (DOC M18 §4.3.3.2 (ii) e eq. 4.21; U19 §4.5
                # reg. 12: 2 = usa a defasagem linear).
                if defasagem is None or u.numero not in defasagem:
                    raise ValueError(f"usina {u.numero}: defasagem linear sem dados da janela anterior")
                lat = inc[:, _coluna_lateral(cfg, u.numero)]
                t = total_defasado(lat, defasagem[u.numero], {m.usina: tot[:, idx[m.usina]] for m in defasagem[u.numero]})
            else:
                t = np.zeros(inc.shape[0]) if (op.zerar_pn and u.status == NULO) else inc[:, i].copy()
                for m in (mont if op.ordem == "configuracao" else mont[::-1]):
                    t = t + tot[:, m]
        tot[:, i] = t
        feito[i] = True
        pilha.discard(i)

    for i in range(len(usinas)):
        calc(i)
    return tot


def incrementais_de_totais(tot: np.ndarray, cfg: Configuracao, nw: str) -> np.ndarray:
    """Incrementais de todas as usinas a partir dos totais (M18 Figura 4.4,
    passos 4 e 6).

    F6-INC-01 (INFERIDO): incremental = total − T(m1) − T(m2) − ...,
    subtração sequencial com os montantes na ordem da configuração; posto
    lateral: incremental = total. Tratamento das usinas NW:

    - ``nw="absorve"`` (GEVAZP.OUT, F6-INC-02): a coluna da NW é nula e o
      total dela não é subtraído na jusante, que fica com a incremental da NW;
    - ``nw="propria"`` (vazoesia.out, F6-INC-03): a NW é uma usina comum.
    """
    if nw not in ("absorve", "propria"):
        raise ValueError(nw)
    usinas = cfg.completa
    tot = np.asarray(tot, dtype=np.float64)
    idx = _indices(cfg)
    inc = np.zeros_like(tot)
    for i, u in enumerate(usinas):
        if u.status == LATERAL:
            inc[:, i] = tot[:, i]
            continue
        if u.status == NEWAVE and nw == "absorve":
            continue
        s = tot[:, i].copy()
        for m in cfg.montante(u.numero):
            if nw == "absorve" and usinas[idx[m]].status == NEWAVE:
                continue
            s = s - tot[:, idx[m]]
        inc[:, i] = s
    return inc
