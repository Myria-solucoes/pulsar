"""CASO.DAT, ARQUIVOS.DAT, GEVAZP.DAT e a lista de arquivos do DECOMP.

U19 §3 (CASO.DAT), §3.2 (lista de arquivos), §3.3 (dados gerais) e §4.1–4.4.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .texto import ErroLeitura, col, inteiro, ler_linhas

# P-CASO-01: rótulos dos registros da lista de arquivos (U19 §3.2; o 13º,
# INDICES.CSV, vem da nota secundária da versão 11).
CHAVES_ARQUIVOS = (
    "dados_gerais",
    "configuracao_hidraulica",
    "bacias",
    "tendencia",
    "historico_vazoes",
    "postos",
    "relatorio",
    "cenarios_totais",
    "cenarios_incrementais",
    "lista_decomp",
    "regras",
    "similaridade",
    "indices_eolicos",
)


def ler_caso(caminho: Path) -> str:
    """CASO.DAT: um registro com o nome da lista de arquivos (U19 §3)."""
    linhas = [l for l in ler_linhas(caminho) if l.strip()]
    if not linhas:
        raise ErroLeitura(f"{caminho}: CASO.DAT vazio")
    return linhas[0].strip()


def ler_arquivos(caminho: Path) -> dict[str, str]:
    """Lista de arquivos: nome em A12 nas colunas 31–42 (U19 §3.2)."""
    nomes: dict[str, str] = {}
    linhas = ler_linhas(caminho)
    for chave, linha in zip(CHAVES_ARQUIVOS, linhas):
        nome = col(linha, 31, 42).strip()
        if nome:
            nomes[chave] = nome
    return nomes


@dataclass
class DadosGerais:
    """GEVAZP.DAT (U19 §3.3). Campos ausentes ficam como None."""

    nome_caso: str
    registros: dict[int, int | None]
    aberturas: list[list[int]] = field(default_factory=list)

    def reg(self, n: int) -> int | None:
        return self.registros.get(n)

    @property
    def tipo_execucao(self) -> int | None:
        return self.reg(2)

    @property
    def ano_inicial_historico(self) -> int | None:
        return self.reg(16)

    @property
    def ordem_maxima(self) -> int | None:
        return self.reg(15)

    @property
    def numero_postos(self) -> int:
        # P-CASO-02: registro 17, 0 = 320 postos, 1 = 600 postos (U19 §3.3).
        return 600 if self.reg(17) == 1 else 320


def ler_gevazp_dat(caminho: Path) -> DadosGerais:
    """Dados gerais (U19 §3.3).

    Registro 1: A70; registros 2–10 e 15 em diante: inteiro nas colunas
    31–34; registros 11–12: comentário; 13–14: doze I4 nas colunas 12–15,
    17–20, …, 67–70. Os decks públicos podem trazer menos registros do que o
    manual lista (P-CASO-02b); os que faltam ficam None.
    """
    linhas = ler_linhas(caminho)
    if not linhas:
        raise ErroLeitura(f"{caminho}: GEVAZP.DAT vazio")
    nome = col(linhas[0], 1, 70).rstrip()
    regs: dict[int, int | None] = {}
    aberturas: list[list[int]] = []
    for n, linha in enumerate(linhas[1:], start=2):
        if n in (11, 12):
            continue
        if n in (13, 14):
            aberturas.append([inteiro(linha, 12 + 5 * k, 15 + 5 * k) for k in range(12)])
            continue
        if not linha.strip():
            continue
        regs[n] = inteiro(linha, 31, 34, padrao=None)
    return DadosGerais(nome_caso=nome, registros=regs, aberturas=aberturas)


@dataclass
class ListaDecomp:
    """Lista de arquivos do DECOMP (arquivo ``rvx``, U19 §4.4)."""

    dadger: str
    vazoes: str
    hidr: str
    mlt: str | None
    perdas: str | None
    extras: list[str]


def ler_lista_decomp(caminho: Path) -> ListaDecomp:
    """Cinco registros A12 nas colunas 1–12 (U19 §4.4).

    P-CASO-03: os decks públicos têm registros a mais (``dadgnl.rv0``,
    diretório); são guardados em ``extras`` e não usados.
    """
    linhas = ler_linhas(caminho)
    nomes = [col(l, 1, 12).strip() for l in linhas]
    if len(nomes) < 3 or not all(nomes[:3]):
        raise ErroLeitura(f"{caminho}: lista do DECOMP com menos de 3 registros")
    while len(nomes) < 5:
        nomes.append("")
    return ListaDecomp(
        dadger=nomes[0],
        vazoes=nomes[1],
        hidr=nomes[2],
        mlt=nomes[3] or None,
        perdas=nomes[4] or None,
        extras=[n for n in nomes[5:] if n],
    )
