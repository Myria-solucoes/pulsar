"""Comando único do Pulsar (F9): diretório de deck -> VAZOES.RVx e PROBVAZ.DAT.

Uso::

    python -m pulsar.cli <deck> [--revisao RVn] [--saida VAZOES.RVn] [--semente n]
                         [--intermediarios <dir>] [opções das lacunas L6–L8]

Cadeia (02 §1): leitura e configuração (F1), histórico e PAR(p)-A (F3),
matriz de carga (F4), tendência e registros determinísticos (F5), geração
estocástica (F8), totalização e artificiais (F6), gravação (F7).

Proveniência: P-CLI-01..03 em PROVENIENCIA.md; as opções expostas são as
ESCOLHAS já registradas (P-GER-01, P-RUI-04, P-AGR-04, P-LN3-03, P-LN3-04).
"""

from __future__ import annotations

import argparse
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path

if __name__ == "__main__" and not __package__:
    # Chamado como ``python src/pulsar/cli.py``: roda o módulo do pacote.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from pulsar.cli import main

    sys.exit(main())

from .configuracao import Configuracao, montar_configuracao
from .empacotamento import ArvoreVazoes, gravar_probvaz, gravar_vazoes_rvx
from .entradas import Deck, ErroLeitura, ler_deck
from .entradas.texto import resolver
from .estocastico.agregacao import DESVIOS, OpcoesAgregacao
from .estocastico.geracao import SEMENTE_PADRAO, OpcoesGeracao, Resultado, gerar, gravar, montar_vazoes
from .estocastico.lognormal import MOMENTOS, ROTAS
from .estocastico.ruidos import SIMETRIAS

# U19 §5.4: nome do arquivo de probabilidades.
NOME_PROBVAZ = "PROBVAZ.DAT"


@dataclass
class Execucao:
    deck: Deck
    cfg: Configuracao
    revisao: str
    resultado: Resultado
    arvore: ArvoreVazoes
    saida: Path
    probvaz: Path


def ler_revisao(diretorio, revisao: str | None = None) -> tuple[Deck, str]:
    """Deck da revisão pedida e o nome dela (``RVn``).

    P-CLI-01: sem ``revisao``, a cadeia CASO.DAT -> ARQUIVOS.DAT reg. 10 ->
    lista do DECOMP (P-DECK-04). Com ``revisao``, a lista do DECOMP de nome
    ``revisao`` no diretório (os pacotes trazem ``RV0`` e ``RV1``, cada uma
    com o seu ``dadger.rvN``); sem essa lista, o ``DADGER.<revisao>``. A
    revisão devolvida é a extensão do DADGER lido, em maiúsculas."""
    d = Path(diretorio)
    if revisao is None:
        deck = ler_deck(d)
        if deck.lista_decomp is None:
            raise ErroLeitura(f"{d}: sem lista do DECOMP; informe a revisão")
        nome = deck.lista_decomp.dadger
    else:
        if not re.fullmatch(r"RV\d+", revisao, re.IGNORECASE):
            raise ErroLeitura(f"revisão {revisao!r} fora da forma RVn")
        if resolver(d, revisao) is not None:
            deck = ler_deck(d, lista_decomp=revisao)
            nome = deck.lista_decomp.dadger
        else:
            nome = f"DADGER.{revisao}"
            deck = ler_deck(d, dadger=nome)
    rev = nome.rsplit(".", 1)[-1].upper()
    if revisao is not None and rev != revisao.upper():
        raise ErroLeitura(f"lista {revisao} aponta o DADGER {nome}")
    return deck, rev


def nome_vazoes(deck: Deck, rev: str) -> str:
    """P-CLI-02: nome padrão do VAZOES.RVx = registro 2 da lista do DECOMP da
    revisão (U19 §4.4, "arquivo de vazões geradas para DECOMP") em
    maiúsculas, como os arquivos publicados (as listas dizem ``vazoes.rv0``,
    o pacote traz ``VAZOES.RV0``); sem a lista da revisão, ``VAZOES.<RVn>``."""
    lista = deck.lista_decomp
    if lista is not None and lista.vazoes and lista.dadger.rsplit(".", 1)[-1].upper() == rev:
        return lista.vazoes.upper()
    return f"VAZOES.{rev}"


def opcoes_de(args) -> OpcoesGeracao:
    return OpcoesGeracao(
        semente=args.semente,
        agregacao=OpcoesAgregacao(simetria=args.simetria, desvio=args.desvio_fc),
        rota_limite=args.rota_limite,
        momentos=args.momentos,
    )


def executar(diretorio, revisao: str | None = None, saida=None, opcoes: OpcoesGeracao | None = None,
             intermediarios=None, agregacao=None, npos: int | None = None) -> Execucao:
    """Lê o deck, gera os cenários e grava o VAZOES.RVx e o PROBVAZ.DAT.

    P-CLI-02: ``saida`` padrão ``nome_vazoes`` no diretório corrente;
    o PROBVAZ.DAT vai para o diretório da ``saida``. ``intermediarios``
    grava também GEVAZP.OUT, VAZTOTGD.DAT, vazoesta.out e vazoesia.out
    (P-GER-06). ``agregacao`` reaproveita uma agregação já feita com a
    mesma semente (testes)."""
    deck, rev = ler_revisao(diretorio, revisao)
    cfg = montar_configuracao(deck)
    npos = npos or deck.n_postos
    res = gerar(deck, cfg, opcoes or OpcoesGeracao(), agregacao=agregacao)
    arvore = montar_vazoes(deck, cfg, res, npos)
    saida = Path(saida) if saida else Path(nome_vazoes(deck, rev))
    saida.parent.mkdir(parents=True, exist_ok=True)
    probvaz = saida.parent / NOME_PROBVAZ
    gravar_vazoes_rvx(saida, arvore)
    gravar_probvaz(probvaz, res.probabilidades, npos)
    if intermediarios:
        gravar(intermediarios, res, npos)
    return Execucao(deck, cfg, rev, res, arvore, saida, probvaz)


def argumentos(argv=None):
    ap = argparse.ArgumentParser(prog="pulsar", description="Gera VAZOES.RVx e PROBVAZ.DAT a partir de um deck GEVAZP (modo DECOMP).")
    ap.add_argument("deck", help="diretório do deck (com CASO.DAT)")
    ap.add_argument("--revisao", help="revisão RVn (padrão: a lista do DECOMP do ARQUIVOS.DAT)")
    ap.add_argument("--saida", help="arquivo VAZOES.RVx (padrão: o nome da lista do DECOMP em maiúsculas, no diretório corrente); "
                                    "o PROBVAZ.DAT vai para o mesmo diretório")
    ap.add_argument("--semente", type=int, default=SEMENTE_PADRAO, help="semente dos ruídos (P-GER-01, lacuna L6)")
    ap.add_argument("--intermediarios", help="diretório para GEVAZP.OUT, VAZTOTGD.DAT, vazoesta.out e vazoesia.out")
    ap.add_argument("--simetria", choices=SIMETRIAS, default="nenhuma", help="P-RUI-04, lacuna L6")
    ap.add_argument("--desvio-fc", choices=DESVIOS, default="ponderado", help="σ_i do fator de compensação, P-AGR-04, lacuna L7")
    ap.add_argument("--rota-limite", choices=ROTAS, default="inferida", help="limite inferior da lognormal, P-LN3-03/09, lacuna L8")
    ap.add_argument("--momentos", choices=MOMENTOS, default="historicos", help="momentos do ruído, P-LN3-04")
    return ap.parse_args(argv)


def main(argv=None) -> int:
    args = argumentos(argv)
    t0 = time.monotonic()
    try:
        ex = executar(args.deck, args.revisao, args.saida, opcoes_de(args), args.intermediarios)
    except (ErroLeitura, NotImplementedError, ValueError) as e:
        print(f"pulsar: {e}", file=sys.stderr)
        return 1
    r = ex.resultado
    print(f"{ex.revisao}: {len(r.probabilidades)} cenários do mês {r.mes:02d}, semente {args.semente}, "
          f"{r.agregacao.iteracoes} iterações do K-means, {time.monotonic() - t0:.0f} s")
    print(f"gravados {ex.saida} e {ex.probvaz}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
