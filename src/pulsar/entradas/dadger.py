"""DADGER.RVx: registros UH, AC (NUMPOS, NUMJUS, NPOSNW), VI e o bloco
comentado ``& VAZOES`` (U19 §4.5).

O U19 descreve o bloco ``& VAZOES`` mas não o layout dos registros do
DECOMP; as colunas de UH, AC e VI vêm das linhas-máscara de comentário dos
próprios DADGER públicos (ver PROVENIENCIA.md, P-DADG-*).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from .texto import ErroLeitura, col, inteiro, ler_linhas

MNEMONICOS_CONFIG = ("NUMPOS", "NUMJUS", "NPOSNW")


@dataclass
class RegistroUH:
    usina: int
    ree: int
    nw: bool  # usina do NEWAVE fora do horizonte do DECOMP ("NW" na col. 72)
    linha: int


@dataclass
class RegistroAC:
    usina: int
    mnemonico: str
    valor: int
    datado: bool  # col. 70–80 preenchidas (P-DADG-11)
    linha: int
    # P-DADG-11: data do AC datado: mês col. 70–72, semana col. 75 e ano
    # col. 77–80; semana e ano são opcionais nos DADGER públicos (None).
    mes: int | None = None
    semana: int | None = None
    ano: int | None = None

    def data_completa(self, ano_inicial: int, mes_inicial: int, ano_ausente: str = "estudo") -> tuple[int, int, int]:
        """(ano, mês, semana) do AC, completando o que falta.

        P-DADG-13 (ESCOLHA, lacuna L14): semana ausente vale 1; ano ausente
        vale o ano inicial do estudo (``ano_ausente="estudo"``), o ano que
        põe o mês no início do estudo ou depois dele (``"proximo"``, por
        exemplo JAN num estudo de dezembro de 2025 vira 2026), ou é erro
        (``"erro"``).
        """
        if ano_ausente not in ("estudo", "proximo", "erro"):
            raise ValueError(ano_ausente)
        ano = self.ano
        if ano is None:
            if ano_ausente == "erro":
                raise ValueError(f"AC datado sem ano (linha {self.linha})")
            ano = ano_inicial
            if ano_ausente == "proximo" and self.mes < mes_inicial:
                ano += 1
        return (ano, self.mes, self.semana or 1)

    def posterior_ao_inicio(self, ano_inicial: int, mes_inicial: int, ano_ausente: str = "estudo") -> bool:
        """Data depois da 1ª semana do mês inicial do estudo."""
        if not self.datado:
            return False
        return self.data_completa(ano_inicial, mes_inicial, ano_ausente) > (ano_inicial, mes_inicial, 1)


# P-DADG-11: siglas dos meses nos registros datados do DADGER.
MESES = ("JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")


@dataclass
class RegistroVI:
    usina: int
    duracao: int  # tempo de viagem em horas
    linha: int


@dataclass
class BlocoVazoes:
    """Registros do bloco ``& VAZOES`` na ordem do U19 §4.5 (reg. 1–21) mais
    o reg. 22 (``MODELO PAR-A``) dos decks atuais."""

    arquivo_prevs: str = ""
    arquivo_vsempast: str = ""
    ano_final_historico: int | None = None
    arquivo_historico: str = ""
    arquivo_postos: str = ""
    numero_postos: int | None = None
    mes_inicial: int | None = None
    ano_inicial: int | None = None
    mes_final: int | None = None
    ano_final: int | None = None
    ano_inicial_estudo: int | None = None
    semanas_nao_observadas: int | None = None
    semanas_observadas: int | None = None
    dias_excluidos: int | None = None
    aberturas: list[int] = field(default_factory=list)
    agregacao: str = ""
    ordem_maxima: int | None = None
    defasagem_linear: int | None = None
    matriz_mensal: int | None = None
    ordenacao_automatica: int | None = None
    representante: int | None = None
    ajuste_todas: int | None = None
    ms_par: int | None = None
    prospectivo: int | None = None
    arquivo_prospectivo: str = ""
    imprime_prevs: int | None = None
    arquivo_imprime_prevs: str = ""
    imprime_vazpast: int | None = None
    arquivo_imprime_vazpast: str = ""
    tendencia_editavel: int | None = None
    modelo_par_a: int | None = None
    n_registros: int = 0
    rotulos: list[str] = field(default_factory=list)


@dataclass
class Dadger:
    uh: list[RegistroUH]
    ac: list[RegistroAC]
    vi: list[RegistroVI]
    vazoes: BlocoVazoes | None

    def ac_config(
        self,
        mnemonico: str,
        repetido: str = "ultimo",
        inicio: tuple[int, int] | None = None,
        datado_futuro: str = "vale",
        ano_ausente: str = "estudo",
    ) -> dict[int, int]:
        """Valor de cada usina para um mnemônico de configuração.

        P-DADG-10 (INFERIDO): AC com data igual ou anterior à 1ª semana do
        mês inicial do estudo vale para a configuração inteira, como o não
        datado.
        P-DADG-12 (ESCOLHA, lacuna L14): AC com data posterior à 1ª semana do
        mês inicial (``inicio`` = (ano, mês) inicial do estudo) vale do mesmo
        jeito (``datado_futuro="vale"``) ou é ignorado (``"ignora"``). Sem
        ``inicio``, nenhum AC é tratado como posterior. Semana e ano
        ausentes: P-DADG-13 (``ano_ausente``).
        P-DADG-05 (ESCOLHA, lacuna L14): havendo repetição para a mesma
        usina, vale o último registro do arquivo (``repetido="ultimo"``) ou o
        primeiro (``"primeiro"``).
        """
        if repetido not in ("ultimo", "primeiro"):
            raise ValueError(repetido)
        if datado_futuro not in ("vale", "ignora"):
            raise ValueError(datado_futuro)
        saida: dict[int, int] = {}
        for r in self.ac:
            if r.mnemonico == mnemonico:
                if datado_futuro == "ignora" and inicio is not None and r.posterior_ao_inicio(*inicio, ano_ausente):
                    continue
                if repetido == "primeiro" and r.usina in saida:
                    continue
                saida[r.usina] = r.valor
        return saida


def _data_ac(linha: str, n: int) -> dict[str, int | None]:
    """P-DADG-11: mês (sigla, col. 70–72), semana (col. 75), ano (col. 77–80)."""
    if not col(linha, 70, 80).strip():
        return {}
    sigla = col(linha, 70, 72).strip().upper()
    # P-DADG-11: sigla fora de JAN…DEZ é erro (ESCOLHA, lacuna L15).
    if sigla not in MESES:
        raise ErroLeitura(f"linha {n}: mês {sigla!r} inválido no AC datado: {linha!r}")
    return {
        "mes": MESES.index(sigla) + 1,
        "semana": inteiro(linha, 75, 75, padrao=None),
        "ano": inteiro(linha, 77, 80, padrao=None),
    }


_INICIO_VAZOES = re.compile(r"^&\s*VAZOES\b")


def _registro_vazoes(linha: str) -> bool:
    # P-DADG-06: linha de dados do bloco = comentário com "=>" antes da col. 40.
    return linha.startswith("&") and "=>" in col(linha, 2, 39)


def _ler_bloco_vazoes(linhas: list[str]) -> BlocoVazoes:
    b = BlocoVazoes(n_registros=len(linhas))
    b.rotulos = [col(l, 2, 36).strip() for l in linhas]

    def r(n: int) -> str | None:
        return linhas[n - 1] if n <= len(linhas) else None

    def i4(n: int, c1: int = 40, c2: int = 43) -> int | None:
        l = r(n)
        return None if l is None else inteiro(l, c1, c2, padrao=None)

    def a(n: int, c1: int, c2: int) -> str:
        l = r(n)
        return "" if l is None else col(l, c1, c2).strip()

    # P-DADG-07: colunas de cada registro conforme U19 §4.5.
    b.arquivo_prevs = a(1, 40, 51)
    b.arquivo_vsempast = a(1, 53, 64)
    b.ano_final_historico = i4(2)
    b.arquivo_historico = a(2, 44, 73)
    b.arquivo_postos = a(3, 40, 51)
    b.numero_postos = i4(3, 52, 55)
    b.mes_inicial = i4(4)
    b.ano_inicial = i4(4, 45, 48)
    b.mes_final = i4(5)
    b.ano_final = i4(5, 45, 48)
    b.ano_inicial_estudo = i4(6)
    b.semanas_nao_observadas = i4(7)
    b.semanas_observadas = i4(7, 45, 48)
    b.dias_excluidos = i4(8)
    if r(9) is not None:
        ab = [inteiro(r(9), 40 + 5 * k, 43 + 5 * k, padrao=None) for k in range(11)]
        b.aberturas = [x for x in ab if x is not None]
    b.agregacao = a(10, 40, 41)
    b.ordem_maxima = i4(11)
    b.defasagem_linear = i4(12)
    b.matriz_mensal = i4(13)
    b.ordenacao_automatica = i4(14)
    b.representante = i4(15)
    b.ajuste_todas = i4(16)
    b.ms_par = i4(17)
    b.prospectivo = i4(18)
    b.arquivo_prospectivo = a(18, 45, 57)
    b.imprime_prevs = i4(19)
    b.arquivo_imprime_prevs = a(19, 45, 57)
    b.imprime_vazpast = i4(20)
    b.arquivo_imprime_vazpast = a(20, 45, 57)
    b.tendencia_editavel = i4(21)
    # P-DADG-08: registro 22 (MODELO PAR-A), presente nos decks desde 2023.
    b.modelo_par_a = i4(22)
    return b


def ler_dadger(caminho: Path) -> Dadger:
    linhas = ler_linhas(caminho)
    uh: list[RegistroUH] = []
    ac: list[RegistroAC] = []
    vi: list[RegistroVI] = []
    bloco: list[str] | None = None
    vazoes: BlocoVazoes | None = None
    for n, linha in enumerate(linhas, start=1):
        if bloco is not None:
            if _registro_vazoes(linha):
                bloco.append(linha)
                continue
            vazoes = _ler_bloco_vazoes(bloco)
            bloco = None
        if _INICIO_VAZOES.match(linha):
            if vazoes is not None:
                raise ErroLeitura(f"{caminho}:{n}: segundo bloco & VAZOES")
            bloco = []
            continue
        reg = linha[:2]
        if reg == "UH":
            # P-DADG-01: UH usina col. 5–7, REE col. 10–11, "NW" col. 72–73.
            uh.append(
                RegistroUH(
                    usina=inteiro(linha, 5, 7),
                    ree=inteiro(linha, 10, 11),
                    nw=col(linha, 72, 73).strip().upper() == "NW",
                    linha=n,
                )
            )
        elif reg == "AC":
            # P-DADG-02: AC usina col. 5–7, mnemônico col. 10–15, valor
            # inteiro col. 20–49 para NUMPOS/NUMJUS/NPOSNW; mês, semana e
            # ano nas col. 70–80 (P-DADG-11).
            mn = col(linha, 10, 15).strip().upper()
            if mn in MNEMONICOS_CONFIG:
                ac.append(
                    RegistroAC(
                        usina=inteiro(linha, 5, 7),
                        mnemonico=mn,
                        valor=inteiro(linha, 20, 49),
                        datado=bool(col(linha, 70, 80).strip()),
                        linha=n,
                        **_data_ac(linha, n),
                    )
                )
        elif reg == "VI":
            # P-DADG-03: VI usina col. 5–7, duração (h) col. 10–12.
            vi.append(RegistroVI(usina=inteiro(linha, 5, 7), duracao=inteiro(linha, 10, 12), linha=n))
    if bloco is not None:
        vazoes = _ler_bloco_vazoes(bloco)
    return Dadger(uh=uh, ac=ac, vi=vi, vazoes=vazoes)
