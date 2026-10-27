"""AC datado (P-DADG-10, P-DADG-11).

Evidência: decks DECOMP publicados de 202208 RV1-RV3, cujo DADGER traz
``AC 88 NPOSNW 305 ... AGO 1 2022``, data igual à 1ª semana do mês inicial
do estudo (08/2022; na rv1-rv3 essa semana já é observada). Nos blocos "considerando postos artificiais" do
vazoes.rvN, lidos com o leitor da F2 (docs/layout-VAZOES.RVx.md, inferido nos
pacotes de 2026; o controle abaixo e a validação estrutural do leitor dão
suporte ao uso em 2022), a usina 88 deixa a coluna do próprio posto e passa à
coluna 305, inclusive nos meses observados anteriores à data do AC. Na RV0 do
mesmo mês, sem o AC, a coluna ENA do posto 88 é igual à natural.

Não há AC de configuração datado depois da 1ª semana do mês inicial, nem
sem ano ou sem semana, na coleção; esses casos são ESCOLHA (P-DADG-12,
P-DADG-13, lacuna L14) e são testados só como parâmetro.
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import base  # noqa: F401
import colecao_ons
from pulsar.configuracao import montar_configuracao
from pulsar.entradas.binarios import ler_hidr
from pulsar.entradas.dadger import ler_dadger
from pulsar.entradas.deck import Deck

try:
    from pulsar.oraculos.vazoes_decomp import ler_vazoes_decomp
except ImportError:  # sem NumPy (Python do sistema)
    ler_vazoes_decomp = None


def _casos_com_vazoes():
    zips = colecao_ons.zips_decomp()
    for c in colecao_ons.casos_gevazp():
        z = zips.get((c.ano, c.mes, c.rev))
        if z is None or c.hidr is None or (c.ano, c.mes) < (2017, 1):
            continue
        yield c, z


@unittest.skipUnless(colecao_ons.disponivel(), "coleção de decks do ONS indisponível")
@unittest.skipIf(ler_vazoes_decomp is None, "NumPy indisponível (rode com ambiente/py)")
class TestACDatado(unittest.TestCase):
    def test_ac_npos_nw_datado_vale_para_a_configuracao_inteira(self):
        datados = 0
        controles = 0
        alvos: dict[tuple[int, int], set[int]] = {}
        casos = list(_casos_com_vazoes())
        for c, z in casos:
            dg = ler_dadger(c.dadger)
            for r in dg.ac:
                if r.mnemonico == "NPOSNW" and r.datado:
                    alvos.setdefault((c.ano, c.mes), set()).add(r.usina)
        self.assertTrue(alvos, "nenhum AC NPOSNW datado na coleção")
        for c, z in casos:
            if (c.ano, c.mes) not in alvos:
                continue
            dg = ler_dadger(c.dadger)
            h = ler_hidr(c.hidr)
            cfg = montar_configuracao(Deck(diretorio=c.diretorio, dadger=dg, hidr=h)).por_numero()
            with tempfile.TemporaryDirectory() as tmp:
                arq = Path(tmp) / "vazoes.rv"
                arq.write_bytes(colecao_ons.vazoes_rv_do_zip(z))
                v = ler_vazoes_decomp(arq)
            datado = {r.usina: r.valor for r in dg.ac if r.mnemonico == "NPOSNW" and r.datado}
            for usina in alvos[(c.ano, c.mes)]:
                col = cfg[usina].posto - 1
                with self.subTest(caso=c.nome, usina=usina):
                    if usina in datado:
                        art = datado[usina]
                        ac = next(r for r in dg.ac if r.usina == usina and r.mnemonico == "NPOSNW")
                        self.assertEqual((ac.mes, ac.semana, ac.ano), (8, 1, 2022))
                        inicio = (dg.vazoes.ano_inicial, dg.vazoes.mes_inicial)
                        self.assertEqual(inicio, (2022, 8))
                        # a evidência só cobre data igual ou anterior ao início
                        self.assertFalse(ac.posterior_ao_inicio(*inicio))
                        self.assertEqual(cfg[usina].posto_artificial, art)
                        # a coluna do próprio posto some dos blocos ENA,
                        # inclusive dos meses observados anteriores à data
                        for bloco in (v.prevista_semanal_ena, v.gerada_mensal_ena, v.observada_mensal):
                            self.assertFalse(bloco[:, col].any())
                        self.assertTrue(v.gerada_mensal[:, col].any())
                        self.assertTrue(v.gerada_mensal_ena[:, art - 1].any())
                        datados += 1
                    elif not any(r.usina == usina and r.mnemonico == "NPOSNW" for r in dg.ac):
                        # controle: sem NPOSNW, ENA = natural na coluna do posto
                        self.assertEqual(cfg[usina].posto_artificial, 0)
                        self.assertTrue((v.prevista_semanal_ena[:, col] == v.prevista_semanal[:, col]).all())
                        self.assertTrue((v.gerada_mensal_ena[:, col] == v.gerada_mensal[:, col]).all())
                        controles += 1
        self.assertGreaterEqual(datados, 3)
        self.assertGreaterEqual(controles, 1)


if __name__ == "__main__":
    unittest.main()
