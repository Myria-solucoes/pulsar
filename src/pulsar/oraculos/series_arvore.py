"""Séries geradas no formato árvore: GEVAZP.OUT, VAZTOTGD.DAT, vazoesia.out,
vazoesta.out e vazaoanual.out.

Layout (docs/layout-GEVAZP.OUT.md e irmãos): acesso direto, RECL = NPOS*8,
um registro por cenário (folha do período estocástico), cada registro com
NPOS float64 na ordem NINT da configuração (coluna NINT-1); colunas além do
número de usinas valem zero. No modo DECOMP dos pacotes analisados só o mês
estocástico é gravado.
"""

from __future__ import annotations

import os
from dataclasses import dataclass

import numpy as np

from .acesso_direto import NPOS_PADRAO, ler_bytes, matriz_f8, numero_de_registros


@dataclass(frozen=True)
class SeriesArvore:
    """valores[cenario, nint-1] em m3/s, float64 exatamente como gravado."""

    grandeza: str
    valores: np.ndarray

    @property
    def n_cenarios(self) -> int:
        return self.valores.shape[0]

    def usina(self, nint: int) -> np.ndarray:
        """Vetor de cenários da usina de índice NINT (1 = primeira da configuração)."""
        return self.valores[:, nint - 1]

    def cenario(self, s: int) -> np.ndarray:
        """Valores de todas as usinas no cenário s (1 = primeiro)."""
        return self.valores[s - 1]


def _ler(caminho: str | os.PathLike, grandeza: str, npos: int) -> SeriesArvore:
    dados = ler_bytes(caminho)
    numero_de_registros(dados, npos * 8, str(caminho))
    return SeriesArvore(grandeza, matriz_f8(dados, npos))


def ler_incrementais_geradas(caminho, npos: int = NPOS_PADRAO) -> SeriesArvore:
    """GEVAZP.OUT: vazão incremental mensal gerada de cada usina, por cenário."""
    return _ler(caminho, "incremental gerada", npos)


def ler_totais_gerados(caminho, npos: int = NPOS_PADRAO) -> SeriesArvore:
    """VAZTOTGD.DAT: vazão total mensal gerada (incrementais somadas na cascata)."""
    return _ler(caminho, "total gerada", npos)


def ler_incrementais_artificiais(caminho, npos: int = NPOS_PADRAO) -> SeriesArvore:
    """vazoesia.out: incremental considerando os postos artificiais."""
    return _ler(caminho, "incremental considerando artificiais", npos)


def ler_totais_artificiais(caminho, npos: int = NPOS_PADRAO) -> SeriesArvore:
    """vazoesta.out: total considerando os postos artificiais."""
    return _ler(caminho, "total considerando artificiais", npos)


def ler_media_anual_anterior(caminho, npos: int = NPOS_PADRAO) -> SeriesArvore:
    """vazaoanual.out: média das 12 incrementais anteriores ao mês gerado
    (A_{t-1} do PAR(p)-A), por cenário e usina. Zero nas usinas PN."""
    return _ler(caminho, "media das 12 incrementais anteriores", npos)
