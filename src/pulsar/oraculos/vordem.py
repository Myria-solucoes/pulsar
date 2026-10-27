"""vordem.out: rastro do tratamento de coeficientes negativos.

O U19 não descreve o arquivo. É texto; o layout e o significado de cada
linha foram inferidos dos pacotes públicos (docs/layout-vordem.out.md,
P-VORD-01..03):

* ``USINA: <nome A12> ->`` e as 12 ordens identificadas pela FACP;
* para cada mês: ``MES: <mês> -> AR(p)`` com a ordem usada, ``MES: <mês> ->
  AR(l)`` com o limite da busca, ``COEFS:`` com φ'_i = φ_i σ_m/σ_{m-i},
  ``PSI:`` com ψ' = ψ σ_m/σ^A_m e as linhas ``FUNC. DE <mês> :`` com as
  contribuições dos meses anteriores, até a primeira negativa;
* um bloco ``USINA:`` por iteração; o último é o modelo final.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

SIGLAS = ("JAN", "FEV", "MAR", "ABR", "MAI", "JUN", "JUL", "AGO", "SET", "OUT", "NOV", "DEZ")


@dataclass
class MesVordem:
    mes: int  # 1..12
    ordem: int  # ordem usada
    limite: int | None
    coefs: list[float]
    psi: float | None
    contribuicoes: list[tuple[int, float]]  # (mês 1..12, valor)


@dataclass
class IteracaoVordem:
    nome: str
    identificadas: list[int]
    meses: list[MesVordem]


_USINA = re.compile(r"USINA: (.{12}) ->((?:\s+\d+){12})\s*$")
_MES = re.compile(r"MES: (\w{3}) -> AR\(\s*(\d+)\)")
_FUNC = re.compile(r"\s+FUNC\. DE (\w{3}) :\s*(\S+)")


def ler_vordem(caminho) -> dict[str, list[IteracaoVordem]]:
    """{nome da usina: iterações na ordem do arquivo}."""
    out: dict[str, list[IteracaoVordem]] = {}
    it: IteracaoVordem | None = None
    mes: MesVordem | None = None
    with open(caminho, encoding="latin-1") as f:
        for linha in f:
            linha = linha.rstrip("\r\n")
            m = _USINA.match(linha)
            if m:
                it = IteracaoVordem(m[1].strip(), [int(x) for x in m[2].split()], [])
                out.setdefault(it.nome, []).append(it)
                mes = None
                continue
            if it is None:
                continue
            m = _MES.match(linha)
            if m:
                k = SIGLAS.index(m[1]) + 1
                if mes is not None and mes.mes == k and mes.limite is None:
                    mes.limite = int(m[2])
                else:
                    mes = MesVordem(k, int(m[2]), None, [], None, [])
                    it.meses.append(mes)
                continue
            if mes is None:
                continue
            if linha.startswith("COEFS:"):
                mes.coefs = [float(x) for x in linha[6:].split()]
            elif linha.startswith("PSI:"):
                mes.psi = float(linha[4:])
            else:
                m = _FUNC.match(linha)
                if m:
                    mes.contribuicoes.append((SIGLAS.index(m[1]) + 1, float(m[2])))
    return out
