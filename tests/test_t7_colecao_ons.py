"""T7 nos decks DECOMP da coleção do ONS: registros 1, 2 e 3 do vazoes.rvN de 2017 a
2026 reconstruídos a partir do DADGER e do HIDR da coleção GEVAZP
operacional (03 §1.2). Os decks da coleção do ONS não trazem PREVS nem VAZOES.DAT;
os blocos de vazões só são testados nos pacotes (test_t7_vazoes_deterministicos.py).

A versão do GEVAZP (campo 7 do registro 3) muda com o tempo e não está no
DADGER: o teste a lê do arquivo público e a passa como opção (ela decide o
layout do registro 1, P-VZD-08); a codificação é conferida pela F2-VZ-04b.
Também conta os meses observados (bloco 9) e a ordem máxima do DADGER
(P-TEND-07, lacuna L17). Proveniência: P-VZD-01..05, P-VZD-08 e P-TEND-07. Rodar com ``ambiente/py -m pytest``.
"""

from __future__ import annotations

import collections
import struct
import unittest

import numpy as np

import colecao_ons
from pulsar import vazoes_deterministicos as VD
from pulsar.oraculos.vazoes_decomp import numero_de_nos
from pulsar.configuracao import montar_configuracao
from pulsar.entradas.binarios import ler_hidr
from pulsar.entradas.dadger import ler_dadger
from pulsar.entradas.deck import Deck


def meses_observados(dados: bytes, R: int) -> int:
    """Nº de registros do bloco 9 (F2-VZ-09): o que sobra depois dos
    registros 1-3, das probabilidades, dos blocos 5-8 e das semanas
    observadas. As aberturas ficam nas posições 3.. do registro 1 nos dois
    layouts (P-VZD-08)."""
    r1 = struct.unpack_from(f"<{R // 4}i", dados, 0)
    r3 = struct.unpack_from(f"<{R // 4}i", dados, 2 * R)
    nest = r1[1]
    aberturas = r1[2 : 2 + nest]
    assert all(a == 1 for a in aberturas[:-1]), aberturas
    nnos = numero_de_nos(aberturas)
    nprev, nger = nest - 1, nnos - (nest - 1)
    return len(dados) // R - 3 - (-(-nnos // (R // 4))) - 2 * (nprev + nger) - r3[5]


@unittest.skipUnless(colecao_ons.disponivel(), "coleção de decks do ONS indisponível")
class TestCabecalhoColecaoONS(unittest.TestCase):
    def test_registros_1_a_3(self):
        zips = colecao_ons.zips_decomp()
        n = 0
        por_layout = collections.Counter()
        meses_e_ordem = collections.Counter()
        falhas: list[str] = []
        versoes: dict[int, set[int]] = collections.defaultdict(set)
        for c in colecao_ons.casos_gevazp():
            if c.ano < 2017 or c.hidr is None:
                continue
            z = zips.get((c.ano, c.mes, c.rev))
            if z is None:
                continue
            dados = colecao_ons.vazoes_rv_do_zip(z)
            if dados is None:
                continue
            deck = Deck(diretorio=c.diretorio, dadger=ler_dadger(c.dadger), hidr=ler_hidr(c.hidr))
            cfg = montar_configuracao(deck)
            R = 4 * deck.n_postos
            versao = struct.unpack_from("<i", dados, 2 * R + 24)[0]
            # a versão emulada é dado de entrada (não está no DADGER)
            op = VD.OpcoesVazoes(versao=(versao // 10000, versao // 100 % 100, versao % 100))
            r1, r2, r3 = VD.montar_cabecalho(deck, cfg, op)
            versoes[c.ano].add(versao)
            pub3 = dados[2 * R : 3 * R]
            if r1.tobytes() != dados[:R]:
                falhas.append(f"{c.nome}: registro 1 {list(np.frombuffer(dados[:R], '<i4')[:10])} != {list(r1[:10])}")
            elif r2.tobytes() != dados[R : 2 * R]:
                falhas.append(f"{c.nome}: registro 2")
            elif bytes(pub3) != r3:
                falhas.append(f"{c.nome}: registro 3 {list(np.frombuffer(bytes(pub3), '<i4')[:7])}")
            n += 1
            por_layout[versao >= 80106] += 1
            meses_e_ordem[(meses_observados(dados, R), deck.dadger.vazoes.ordem_maxima)] += 1
        self.assertGreater(n, 450)
        self.assertGreater(min(por_layout[True], por_layout[False]), 200)
        self.assertEqual(falhas, [], f"{len(falhas)} de {n}: {falhas[:10]}")
        # P-TEND-07 / lacuna L17: todos os vazoes.rvN têm 11 meses observados
        # e o DADGER correspondente tem ordem máxima 11.
        self.assertEqual(dict(meses_e_ordem), {(11, 11): n})
        self.assertEqual((n, por_layout[False], por_layout[True]), (503, 261, 242))
        # F2-VZ-04b: todos os códigos públicos têm a forma maior*10000 +
        # menor*100 + revisão com menor e revisão < 100.
        for ano, cods in versoes.items():
            for v in cods:
                self.assertEqual(VD.codigo_versao((v // 10000, v // 100 % 100, v % 100)), v, (ano, v))


@unittest.skipUnless(colecao_ons.disponivel(), "coleção de decks do ONS indisponível")
class TestOrdemMaximaColecaoONS(unittest.TestCase):
    def test_ordem_maxima_dos_dadger_de_2017_em_diante(self):
        """P-TEND-07: os 504 DADGER de 2017-2026 da coleção GEVAZP têm ordem
        máxima 11 (inclusive os sem vazoes.rvN ou sem HIDR)."""
        ordens = collections.Counter(
            ler_dadger(c.dadger).vazoes.ordem_maxima for c in colecao_ons.casos_gevazp() if c.ano >= 2017
        )
        self.assertEqual(dict(ordens), {11: 504})
