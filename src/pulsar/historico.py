"""Séries incrementais históricas das usinas da configuração (02 §3).

``Zinc(i,t) = Ztot(i,t) - Σ Ztot(m,t)`` sobre as usinas imediatamente a
montante de i (L-INC eq. 1; M18 §4.3.3), na janela comum de anos da
configuração (lacuna L1).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .configuracao import LATERAL, NULO, Configuracao, UsinaConfig
from .entradas.binarios import HistoricoVazoes
from .entradas.texto import ErroLeitura

MESES = 12


@dataclass(frozen=True)
class SerieIncremental:
    """Série incremental histórica de uma usina da configuração completa."""

    numero: int
    nome: str
    posto: int
    status: str
    anos: tuple[int, ...]
    valores: np.ndarray  # [ano, mes-1], float64

    @property
    def nula(self) -> bool:
        """Incremental identicamente nula (por exemplo ITUTINGA e
        PARANAPANEMA nos pacotes de 2026, sem seção "PROCESSO PAR(P)")."""
        return not np.any(self.valores)


def _serie_posto(h: HistoricoVazoes, posto: int, anos) -> np.ndarray:
    return np.array([[h.vazao(posto, a, m) for m in range(1, MESES + 1)] for a in anos], dtype=np.int64)


def janela(config: Configuracao) -> tuple[int, ...]:
    """P-HIST-02: anos do histórico usados no ajuste = período comum da
    configuração (P-CFG-08), que nos pacotes é 1931–2024 com o VAZOES.DAT
    indo até 2026 (INFERIDO: anos das seções "SERIE DE VAZOES INCREMENTAIS"
    do GEVAZP.REL; lacuna L1)."""
    if not config.ano_inicial_comum or config.ano_final_comum < config.ano_inicial_comum:
        raise ErroLeitura("configuração sem período histórico comum")
    return tuple(range(config.ano_inicial_comum, config.ano_final_comum + 1))


def serie_incremental(h: HistoricoVazoes, config: Configuracao, usina: UsinaConfig,
                      anos: tuple[int, ...] | None = None) -> SerieIncremental:
    """P-HIST-01: total do posto da usina menos os totais dos postos das
    usinas imediatamente a montante (L-INC eq. 1, montante pela P-CFG-17).
    O posto lateral (status PL, P-CFG-11) é a série do próprio posto: ele
    não tem usinas a montante na configuração. A diferença é feita em
    inteiros (o VAZOES.DAT é int32, P-BIN-04) e convertida para float64."""
    anos = janela(config) if anos is None else anos
    z = _serie_posto(h, usina.posto, anos)
    if usina.status != LATERAL:
        for p in config.postos_montante(usina.numero):
            z = z - _serie_posto(h, p, anos)
    return SerieIncremental(
        numero=usina.numero,
        nome=usina.nome_str,
        posto=usina.posto,
        status=usina.status,
        anos=tuple(anos),
        valores=z.astype(np.float64),
    )


def series_incrementais(h: HistoricoVazoes, config: Configuracao) -> list[SerieIncremental]:
    """Todas as usinas da configuração completa (base + laterais), exceto as
    PN, na ordem da configuração: são as seções "SERIE DE VAZOES
    INCREMENTAIS" do GEVAZP.REL (lista H do correli, F2-CI-03)."""
    anos = janela(config)
    return [serie_incremental(h, config, u, anos) for u in config.completa if u.status != NULO]


def series_ajustadas(series: list[SerieIncremental], ajuste_todas: int | None = 1,
                     sem_reg16: str = "mesma") -> list[SerieIncremental]:
    """P-HIST-03: séries que recebem modelo PAR(p)/PAR(p)-A = as não nulas,
    na ordem da configuração (índice do correli, F2-CI-03; ordem das usinas
    no vordem.out), com o & VAZOES reg. 16 (``AJUSTE PARP A TODAS UHES``) = 1.

    Com o reg. 16 ≠ 1 ou ausente (ESCOLHA, lacuna L19): ``sem_reg16`` =
    "mesma" aplica a mesma regra; "erro" recusa o deck."""
    if sem_reg16 not in ("mesma", "erro"):
        raise ValueError(sem_reg16)
    if ajuste_todas != 1 and sem_reg16 == "erro":
        raise ErroLeitura(f"AJUSTE PARP A TODAS UHES = {ajuste_todas}: seleção de séries sem exemplo público")
    return [s for s in series if not s.nula]
