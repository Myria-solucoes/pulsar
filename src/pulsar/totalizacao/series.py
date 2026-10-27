"""Cadeia da Figura 4.4 do M18 (passos 2 a 6) e gravação dos arquivos em
árvore: VAZTOTGD.DAT, GEVAZP.OUT, vazoesta.out e vazoesia.out.
"""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import numpy as np

from ..configuracao import Configuracao
from ..entradas.regras import Regras
from .artificiais import OpcoesArtificiais, totais_artificiais
from .cascata import OpcoesTotalizacao, incrementais_de_totais, totalizar
from .defasagem import MontanteDefasado


@dataclass(frozen=True)
class SeriesTotalizadas:
    """Matrizes float64 ``[cenário, usina]`` na ordem da configuração completa."""

    totais: np.ndarray  # VAZTOTGD.DAT
    incrementais: np.ndarray  # GEVAZP.OUT
    totais_artificiais: np.ndarray  # vazoesta.out
    incrementais_artificiais: np.ndarray  # vazoesia.out


def series_dos_totais(
    tot: np.ndarray,
    cfg: Configuracao,
    regras: Regras | None,
    mes: int,
    ano_estudo: int = 1,
    opcoes_artificiais: OpcoesArtificiais | None = None,
) -> SeriesTotalizadas:
    """Passos 4 a 6 da Figura 4.4 a partir dos totais.

    Sem posto artificial na configuração o REGRAS.DAT não é lido (U19
    §3.10, P-DECK-03) e os totais artificiais repetem os naturais.
    """
    if regras is None and any(u.posto_artificial for u in cfg.completa):
        raise ValueError("configuração com posto artificial exige o REGRAS.DAT")
    ta = totais_artificiais(tot, cfg, regras, mes, ano_estudo, opcoes_artificiais) if regras else tot.copy()
    return SeriesTotalizadas(
        totais=np.asarray(tot, dtype=np.float64)[:, : len(cfg.completa)].copy(),
        incrementais=incrementais_de_totais(tot, cfg, nw="absorve"),
        totais_artificiais=ta,
        incrementais_artificiais=incrementais_de_totais(ta, cfg, nw="propria"),
    )


def calcular_series(
    incrementais_geradas: np.ndarray,
    cfg: Configuracao,
    regras: Regras | None,
    mes: int,
    ano_estudo: int = 1,
    defasagem: Mapping[int, Sequence[MontanteDefasado]] | None = None,
    opcoes_totalizacao: OpcoesTotalizacao | None = None,
    opcoes_artificiais: OpcoesArtificiais | None = None,
) -> SeriesTotalizadas:
    """Passos 2 a 6 da Figura 4.4 do M18, das incrementais geradas aos
    quatro arquivos. ``mes`` = mês do calendário do estágio estocástico."""
    tot = totalizar(incrementais_geradas, cfg, defasagem, opcoes_totalizacao)
    return series_dos_totais(tot, cfg, regras, mes, ano_estudo, opcoes_artificiais)


def mes_e_ano_estocastico(mes_inicial: int) -> tuple[int, int]:
    """Mês do calendário do estágio estocástico (o seguinte ao inicial, F2-QP-03)
    e o ano do estudo dele (F6-ART-07, ESCOLHA, lacuna L16: 1 no ano inicial,
    2 quando o mês inicial é dezembro)."""
    return mes_inicial % 12 + 1, 2 if mes_inicial == 12 else 1


def serializar_series_arvore(valores: np.ndarray, npos: int) -> bytes:
    """F6-GRV-01 (DOC U19 §5.3.1.2; INFERIDO F2-ARV-01/02): um registro de
    NPOS float64 little-endian por cenário, coluna = NINT-1, colunas além do
    número de usinas com zero."""
    v = np.asarray(valores, dtype=np.float64)
    if v.ndim != 2 or v.shape[1] > npos:
        raise ValueError(f"forma {v.shape} não cabe em registros de {npos} valores")
    m = np.zeros((v.shape[0], npos), dtype="<f8")
    m[:, : v.shape[1]] = v
    return m.tobytes()


def gravar_series_arvore(caminho: str | os.PathLike, valores: np.ndarray, npos: int) -> None:
    with open(caminho, "wb") as f:
        f.write(serializar_series_arvore(valores, npos))


# F2-ARV-05: nomes dos arquivos nos pacotes públicos.
NOMES = {
    "totais": "VAZTOTGD.DAT",
    "incrementais": "GEVAZP.OUT",
    "totais_artificiais": "vazoesta.out",
    "incrementais_artificiais": "vazoesia.out",
}


def gravar_series(diretorio: str | os.PathLike, series: SeriesTotalizadas, npos: int) -> None:
    for campo, nome in NOMES.items():
        gravar_series_arvore(os.path.join(diretorio, nome), getattr(series, campo), npos)
