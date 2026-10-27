"""Leitores dos arquivos públicos do pacote GEVAZP usados como oráculos.

Cada leitor devolve estruturas nomeadas. Layouts e evidências em
docs/layout-<arquivo>.md; proveniência em PROVENIENCIA.md (ids F2-*).
"""

from .correl import Correl, SerieCorrel, ler_correli, ler_correlt
from .probvaz import ler_probvaz
from .qpast import Tendencia, ler_qpast
from .series_arvore import (
    SeriesArvore,
    ler_incrementais_artificiais,
    ler_incrementais_geradas,
    ler_media_anual_anterior,
    ler_totais_artificiais,
    ler_totais_gerados,
)
from .vazoes_decomp import VazoesDecomp, ler_vazoes_decomp, numero_de_nos
from .vordem import IteracaoVordem, MesVordem, ler_vordem

__all__ = [
    "Correl",
    "SerieCorrel",
    "SeriesArvore",
    "Tendencia",
    "VazoesDecomp",
    "IteracaoVordem",
    "MesVordem",
    "ler_correli",
    "ler_correlt",
    "ler_incrementais_artificiais",
    "ler_incrementais_geradas",
    "ler_media_anual_anterior",
    "ler_probvaz",
    "ler_qpast",
    "ler_totais_artificiais",
    "ler_totais_gerados",
    "ler_vazoes_decomp",
    "ler_vordem",
    "numero_de_nos",
]
