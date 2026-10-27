"""Gravação dos arquivos entregues ao DECOMP: VAZOES.RVx e PROBVAZ.DAT (F7, T9).

Os gravadores recebem dados tipados (configuração da F1, bloco & VAZOES do
DADGER, séries geradas, probabilidades e registros determinísticos da F5) e
não leem nenhum VAZOES.RVx existente.
"""

from .probvaz import gravar_probvaz, probabilidades_de_contagens, serializar_probvaz
from .vazoes_rvx import (
    ArvoreVazoes,
    OpcoesEmpacotamento,
    RegistrosDeterministicos,
    codificar_versao,
    gravar_vazoes_rvx,
    montar_arvore,
    nint,
    serializar_vazoes_rvx,
)

__all__ = [
    "ArvoreVazoes",
    "OpcoesEmpacotamento",
    "RegistrosDeterministicos",
    "codificar_versao",
    "gravar_probvaz",
    "gravar_vazoes_rvx",
    "montar_arvore",
    "nint",
    "probabilidades_de_contagens",
    "serializar_probvaz",
    "serializar_vazoes_rvx",
]
