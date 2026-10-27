"""Totais dos postos artificiais pelas regras do REGRAS.DAT (M18 §4.3.4,
Figura 4.4 passo 5; U19 §3.10).

A gramática e o avaliador escalar estão em ``pulsar.entradas.regras``
(P-REG-01..08); aqui ficam a ordem de cálculo entre postos, a origem dos
valores de ``VAZ(n)`` e a precisão numérica (lacuna L9).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from ..configuracao import Configuracao
from ..entradas.regras import Regras, avaliar


def _float32(x: float) -> float:
    return float(np.float32(x))


@dataclass(frozen=True)
class OpcoesArtificiais:
    # F6-ART-03 (INFERIDO, lacuna L9): todo VAZ(n), de posto natural ou
    # artificial, é lido em precisão simples; operações e constantes em
    # precisão dupla; o resultado gravado é o da regra, em precisão dupla.
    # ``ler_vaz=None`` lê em precisão dupla.
    ler_vaz: Callable[[float], float] | None = _float32
    # P-REG-04: arredondamento de cada valor e resultado intermediário
    # dentro da regra (None = nenhum).
    arredondar: Callable[[float], float] | None = None
    # F6-ART-05 (ESCOLHA, lacuna L16): posto natural de mais de uma usina
    # referenciado por VAZ(n) (as PARTIF de posto 300, por exemplo): "erro"
    # quando os valores diferem; "primeiro" usa a primeira usina na ordem
    # da configuração.
    posto_repetido: str = "erro"
    # F6-ART-06 (ESCOLHA, lacuna L16): VAZ(n) com n declarado no REGRAS.DAT
    # e também posto natural de uma usina da configuração: "artificial" usa
    # a regra; "natural", o total da usina; "erro" interrompe. Só a
    # referência por VAZ(n) muda: a regra do posto continua calculada e
    # gravada nas usinas NPOSNW (F6-ART-01, F6-ART-04).
    numero_repetido: str = "artificial"
    # P-REG-05 e P-REG-07 (ESCOLHA, lacuna L16), repassados a Regras.regra.
    prioridade: str = "mes"
    ano_alem_do_bloco2: str = "zero"

    def __post_init__(self):
        if self.posto_repetido not in ("erro", "primeiro"):
            raise ValueError(self.posto_repetido)
        if self.numero_repetido not in ("artificial", "natural", "erro"):
            raise ValueError(self.numero_repetido)


class ErroRegra(ValueError):
    pass


def valores_artificiais(
    vaz_natural: Callable[[int], float],
    regras: Regras,
    mes: int,
    ano_estudo: int = 1,
    opcoes: OpcoesArtificiais | None = None,
) -> dict[int, float]:
    """Valor de todos os postos declarados no REGRAS.DAT num cenário.

    F6-ART-01 (DOC, U19 §3.10): todas as regras declaradas são calculadas;
    uma regra pode usar outro posto artificial (U19 §9, versão 5.4.1 item
    5), na ordem das dependências; referência circular (versão 5.4.2 item 2),
    regra ausente no mês e posto inexistente interrompem a execução.
    ``vaz_natural(posto)`` devolve o total natural do posto (F6-ART-02) e
    levanta ``KeyError`` se ele não existe.
    """
    op = opcoes or OpcoesArtificiais()
    ler = op.ler_vaz or float
    postos = regras.postos()
    memo: dict[int, float] = {}
    em_calculo: list[int] = []

    def calc(p: int) -> float:
        if p in memo:
            return memo[p]
        if p in em_calculo:
            raise ErroRegra(f"referência circular nas regras: {em_calculo[em_calculo.index(p):] + [p]}")
        try:
            r = regras.regra(p, mes, ano_estudo, op.prioridade, op.ano_alem_do_bloco2)
        except KeyError:
            raise ErroRegra(f"posto artificial {p} sem regra para o mês {mes} (ano do estudo {ano_estudo})") from None
        em_calculo.append(p)
        memo[p] = avaliar(r.expressao, vaz, op.arredondar)
        em_calculo.pop()
        return memo[p]

    def natural(p: int) -> float | None:
        try:
            return vaz_natural(p)
        except KeyError:
            return None

    def vaz(p: int) -> float:
        if p in postos:
            # F6-ART-06: número da regra que também é posto natural.
            if op.numero_repetido != "artificial" and (v := natural(p)) is not None:
                if op.numero_repetido == "erro":
                    raise ErroRegra(f"posto {p} tem regra no REGRAS.DAT e é posto natural de uma usina")
                return ler(v)
            return ler(calc(p))
        try:
            return ler(vaz_natural(p))
        except KeyError:
            raise ErroRegra(f"regra usa o posto {p}, que não está na configuração nem no REGRAS.DAT") from None

    for p in sorted(postos):
        calc(p)
    return memo


def totais_artificiais(
    tot: np.ndarray,
    cfg: Configuracao,
    regras: Regras,
    mes: int,
    ano_estudo: int = 1,
    opcoes: OpcoesArtificiais | None = None,
) -> np.ndarray:
    """Totais considerando os postos artificiais (vazoesta.out).

    F6-ART-04 (INFERIDO): usina com posto artificial (campo 14, AC NPOSNW)
    recebe o valor da regra desse posto; as demais repetem o total natural.
    F6-ART-02 (DOC M18 §4.3.4 "a partir destas regras e dos cenários de
    vazões naturais totais"; INFERIDO): VAZ(n) de posto natural = total da
    usina cujo posto é n, na configuração completa (inclui postos laterais).
    """
    op = opcoes or OpcoesArtificiais()
    usinas = cfg.completa
    tot = np.asarray(tot, dtype=np.float64)
    colunas: dict[int, list[int]] = {}
    for i, u in enumerate(usinas):
        colunas.setdefault(u.posto, []).append(i)
    ta = tot[:, : len(usinas)].copy()
    alvos = [(i, u.posto_artificial) for i, u in enumerate(usinas) if u.posto_artificial]
    if not alvos:
        return ta
    for s in range(tot.shape[0]):
        linha = tot[s]

        def vaz_natural(p: int) -> float:
            cols = colunas[p]  # KeyError: posto fora da configuração
            if len(cols) > 1 and op.posto_repetido == "erro" and len({linha[c] for c in cols}) > 1:
                raise ErroRegra(f"posto {p} em mais de uma usina com valores diferentes")
            return float(linha[cols[0]])

        val = valores_artificiais(vaz_natural, regras, mes, ano_estudo, op)
        for i, p in alvos:
            if p not in val:
                raise ErroRegra(f"usina {usinas[i].numero}: posto artificial {p} sem regra no REGRAS.DAT")
            ta[s, i] = val[p]
    return ta
