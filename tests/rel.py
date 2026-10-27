"""Leitura das seções de texto do GEVAZP.REL usadas como oráculo em T0/T1."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path


def linhas_rel(caminho: Path) -> list[str]:
    t = Path(caminho).read_bytes().decode("latin-1")
    return [l.rstrip("\r").replace("\f", "") for l in t.split("\n")]


def _secao(linhas: list[str], titulo: str, fim: re.Pattern | None = None) -> list[str]:
    for i, l in enumerate(linhas):
        if titulo in l:
            saida = []
            for m in linhas[i + 1 :]:
                if fim is not None and fim.search(m):
                    break
                saida.append(m)
            return saida
    raise KeyError(titulo)


_DADO_GERAL = re.compile(r"^     (\S.*?\S)\s{2,}(\S.*?)\s*$")


def dados_gerais(linhas: list[str]) -> dict[str, str]:
    """Pares rótulo/valor do início do relatório (até a tabela de aberturas)."""
    saida: dict[str, str] = {}
    for l in linhas[:200]:
        if "NUMERO DE ABERTURAS" in l:
            break
        m = _DADO_GERAL.match(l)
        if m:
            saida[m.group(1).rstrip(" :")] = m.group(2)
    return saida


@dataclass
class LinhaConfig:
    nint: int
    num: int
    nome: str
    posto: int
    jusante: int
    ano_inicial: int
    ano_final: int
    status: str
    aj: int
    tvj: int
    tvt: int
    pl: int
    defl: int
    part: int
    fator: float
    bacia: int


_CFG = re.compile(r"^\s+(\d+)\s+(\d+)  (.{12})(.*BACIA_(\d+))\s*$")


def configuracao_usinas(linhas: list[str]) -> tuple[list[LinhaConfig], dict[str, str]]:
    """Tabela "CONFIGURACAO DAS USINAS HIDRELETRICAS" e os totais abaixo dela."""
    sec = _secao(linhas, "CONFIGURACAO DAS USINAS HIDRELETRICAS", re.compile("CONFIGURACAO UTILIZADA PELO DECOMP"))
    tabela = []
    totais: dict[str, str] = {}
    for l in sec:
        m = _CFG.match(l)
        if m:
            t = m.group(4).split()[:-1]  # sem BACIA_xxx
            if len(t) == 12:
                status = t.pop(4)
            else:
                status = ""
            posto, jus, ini, fim, aj, tvj, tvt, pl, defl, part = (int(x) for x in t[:10])
            tabela.append(
                LinhaConfig(
                    nint=int(m.group(1)), num=int(m.group(2)), nome=m.group(3).rstrip(),
                    posto=posto, jusante=jus, ano_inicial=ini, ano_final=fim, status=status,
                    aj=aj, tvj=tvj, tvt=tvt, pl=pl, defl=defl, part=part, fator=float(t[10]),
                    bacia=int(m.group(5)),
                )
            )
        elif ":" in l and ("TOTAL DE USINAS" in l or "PERIODO HISTORICO" in l):
            k, v = l.split(":", 1)
            totais[k.strip()] = v.strip()
    return tabela, totais


_DEC = re.compile(r"^\s+(\d+)\s+(\d+) (.{12})((?:\s+-?\d+)+)\s*$")


def configuracao_decomp(linhas: list[str]) -> list[tuple[int, int, str, int, int, list[int]]]:
    """Tabela "CONFIGURACAO UTILIZADA PELO DECOMP": (nint, num, nome, posto,
    jusante, postos a montante)."""
    sec = _secao(linhas, "CONFIGURACAO UTILIZADA PELO DECOMP", re.compile("VAZOES FORNECIDAS PARA A TENDENCIA"))
    saida = []
    for l in sec:
        m = _DEC.match(l)
        if m:
            nums = [int(x) for x in m.group(4).split()]
            saida.append((int(m.group(1)), int(m.group(2)), m.group(3).rstrip(), nums[0], nums[1], nums[2:]))
    return saida


_PREV = re.compile(r"^\s+(\d+)\s+(\d+)   (.{17})(.{7})((?:\s+-?\d+)+)\s*$")


def previsoes_semanais(linhas: list[str]) -> list[tuple[int, int, str, str, list[int]]]:
    """Tabela "CONFIGURACAO INICIAL UHES": (nint, posto, nome, status,
    18 números: totais S1–S6, incrementais S1–S6, incrementais ENA S1–S6)."""
    sec = _secao(linhas, "CONFIGURACAO INICIAL UHES", re.compile(r"CONFIGURACAO DAS USINAS HIDRELETRICAS"))
    saida = []
    for l in sec:
        m = _PREV.match(l)
        if m:
            saida.append((int(m.group(1)), int(m.group(2)), m.group(3).rstrip(), m.group(4).strip(), [int(x) for x in m.group(5).split()]))
    return saida


def serie_incremental(linhas: list[str], nome: str) -> dict[int, list[float]]:
    """Primeira tabela "SERIE DE VAZOES INCREMENTAIS DO POSTO <nome>"."""
    alvo = f"SERIE  DE  VAZOES  INCREMENTAIS  DO  POSTO  {nome}"
    for i, l in enumerate(linhas):
        if alvo in l and l.rstrip().endswith(nome.rstrip()):
            saida: dict[int, list[float]] = {}
            for m in linhas[i + 1 :]:
                t = m.split()
                if len(t) == 13 and t[0].isdigit() and len(t[0]) == 4:
                    saida[int(t[0])] = [float(x) for x in t[1:]]
                elif saida and not m.strip():
                    continue
                elif saida:
                    break
            return saida
    raise KeyError(nome)
