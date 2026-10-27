"""Totalização, postos laterais e postos artificiais (F6, T8; M18 §4.3.3–4.3.4).

Das incrementais geradas aos quatro arquivos em árvore: VAZTOTGD.DAT
(totais), GEVAZP.OUT (incrementais recalculadas dos totais), vazoesta.out e
vazoesia.out (considerando os postos artificiais). Regras e evidências em
docs/totalizacao-e-artificiais.md; proveniência F6-* em PROVENIENCIA.md.
"""

from .artificiais import ErroRegra, OpcoesArtificiais, totais_artificiais, valores_artificiais
from .cascata import OpcoesTotalizacao, incrementais_de_totais, totalizar
from .defasagem import MontanteDefasado, dados_defasagem, dias_do_estagio_estocastico, dias_do_mes, soma_janela, total_defasado
from .series import (
    NOMES,
    SeriesTotalizadas,
    calcular_series,
    gravar_series,
    gravar_series_arvore,
    mes_e_ano_estocastico,
    serializar_series_arvore,
    series_dos_totais,
)

__all__ = [
    "NOMES",
    "ErroRegra",
    "MontanteDefasado",
    "OpcoesArtificiais",
    "OpcoesTotalizacao",
    "SeriesTotalizadas",
    "calcular_series",
    "dados_defasagem",
    "dias_do_estagio_estocastico",
    "dias_do_mes",
    "gravar_series",
    "gravar_series_arvore",
    "incrementais_de_totais",
    "mes_e_ano_estocastico",
    "serializar_series_arvore",
    "series_dos_totais",
    "soma_janela",
    "total_defasado",
    "totais_artificiais",
    "totalizar",
    "valores_artificiais",
]
