"""QPAST.DAT: vazões da tendência hidrológica.

Layout (docs/layout-QPAST.DAT.md): acesso direto, RECL = NPOS*8, 24 registros
de NPOS float64 indexados por posto (coluna posto-1):

* registros 1-12: incrementais, um por mês do calendário (1 = janeiro);
* registros 13-24: totais, idem.

Os 12 meses são os 12 anteriores ao mês estocástico (os meses de número
maior ou igual a ele são do ano anterior). Para postos que não são de usina
principal (postos de regras, artificiais, usinas PN) o registro "incremental"
repete o total.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .acesso_direto import NPOS_PADRAO, ler_bytes, matriz_f8, numero_de_registros


@dataclass(frozen=True)
class Tendencia:
    incremental: np.ndarray  # [mes-1, posto-1]
    total: np.ndarray  # [mes-1, posto-1]

    def incremental_mensal(self, posto: int, mes: int) -> float:
        """Incremental do posto no mês do calendário (1..12)."""
        return float(self.incremental[mes - 1, posto - 1])

    def total_mensal(self, posto: int, mes: int) -> float:
        return float(self.total[mes - 1, posto - 1])

    def incrementais_do_posto(self, posto: int) -> np.ndarray:
        """Vetor jan..dez de incrementais do posto."""
        return self.incremental[:, posto - 1]

    def totais_do_posto(self, posto: int) -> np.ndarray:
        return self.total[:, posto - 1]


def ler_qpast(caminho, npos: int = NPOS_PADRAO) -> Tendencia:
    dados = ler_bytes(caminho)
    n = numero_de_registros(dados, npos * 8, str(caminho))
    if n != 24:
        raise ValueError(f"{caminho}: esperados 24 registros, achados {n}")
    m = matriz_f8(dados, npos)
    return Tendencia(incremental=m[:12], total=m[12:])
