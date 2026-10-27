"""T1: configuração final reconstruída a partir de DADGER, HIDR e MODIF
(03 §4). Critério: config.out igual ao público byte a byte."""

from __future__ import annotations

import unittest

import base  # noqa: F401
import colecao_ons
import rel
from base import COMPLETOS, DECKS, configuracao, deck
from pulsar.config_out import TAMANHO_REGISTRO, gerar_config_out, ler_config_out
from pulsar.configuracao import OpcoesConfiguracao, montar_configuracao, nome_lateral
from pulsar.entradas.binarios import Hidr, UsinaHidr
from pulsar.entradas.dadger import BlocoVazoes, Dadger, RegistroAC, RegistroUH, RegistroVI
from pulsar.entradas.deck import Deck
from pulsar.entradas.prevs_modif import Modif


def _arquivo_lista_decomp(nome: str, dadger: str | None) -> str:
    return deck(nome, dadger).lista_decomp.vazoes


class TestConfigOut(unittest.TestCase):
    def test_config_out_byte_a_byte(self):
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                gerado = gerar_config_out(configuracao(nome, dadger))
                publico = (DECKS / nome / "config.out").read_bytes()
                self.assertEqual(len(gerado), len(publico))
                diferentes = [i // TAMANHO_REGISTRO for i in range(len(publico)) if gerado[i] != publico[i]]
                self.assertEqual(sorted(set(diferentes)), [], "registros diferentes")

    def test_leitura_do_publico_igual_a_configuracao(self):
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                cfg = configuracao(nome, dadger)
                b1, b2 = ler_config_out(DECKS / nome / "config.out")
                self.assertEqual([r["numero"] for r in b1], [u.numero for u in cfg.usinas])
                self.assertEqual([r["numero"] for r in b2], [u.numero for u in cfg.completa])
                self.assertTrue(all(r["resto"] == bytes(TAMANHO_REGISTRO - 66) for r in b1 + b2))

    def test_configuracao_igual_ao_rel(self):
        """Tabela "CONFIGURACAO DAS USINAS HIDRELETRICAS" campo a campo."""
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                cfg = configuracao(nome, dadger)
                tabela, totais = rel.configuracao_usinas(rel.linhas_rel(DECKS / nome / "GEVAZP.REL"))
                self.assertEqual(totais["TOTAL DE USINAS"], str(len(cfg.completa)))
                self.assertEqual(totais["TOTAL DE USINAS COM POSTO DE VAZAO LATERAL"], str(len(cfg.laterais)))
                self.assertEqual(totais["PERIODO HISTORICO COMUM A TODAS AS USINAS"], f"{cfg.ano_inicial_comum} - {cfg.ano_final_comum}")
                self.assertEqual(len(tabela), len(cfg.completa))
                for u, r in zip(cfg.completa, tabela):
                    meu = (u.numero, u.nome_str, u.posto, u.jusante, u.ano_inicial, u.ano_final, u.status.strip(),
                           u.ajuste_automatico, u.tempo_viagem, u.posto_lateral, u.defasagem, u.posto_artificial, u.bacia)
                    pub = (r.num, r.nome, r.posto, r.jusante, r.ano_inicial, r.ano_final, r.status,
                           r.aj, r.tvj, r.pl, r.defl, r.part, r.bacia)
                    self.assertEqual(meu, pub)

    def test_configuracao_decomp_igual_ao_rel(self):
        """Tabela "CONFIGURACAO UTILIZADA PELO DECOMP" com postos a montante."""
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                cfg = configuracao(nome, dadger)
                tabela = rel.configuracao_decomp(rel.linhas_rel(DECKS / nome / "GEVAZP.REL"))
                self.assertEqual(len(tabela), len(cfg.completa))
                for u, (_, num, nome_rel, posto, jus, mont) in zip(cfg.completa, tabela):
                    esperado_mont = [] if u.origem_lateral else cfg.postos_montante(u.numero)
                    self.assertEqual((u.numero, u.nome_str, u.posto, u.jusante, esperado_mont), (num, nome_rel, posto, jus, mont))

    def test_ordem_igual_ao_vazoes_rv_do_pacote(self):
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                arq = _arquivo_lista_decomp(nome, dadger)
                caminho = next(p for p in (DECKS / nome).iterdir() if p.name.lower() == arq.lower())
                self.assertEqual(configuracao(nome, dadger).ordem_vazoes_rv(), colecao_ons.codigos_vazoes_rv(caminho.read_bytes()))


def _deck_sintetico(uh, hidr, ac=(), vi=(), modif=(), ordenar=1):
    """Deck mínimo para testar regras isoladas da configuração."""
    h = Hidr(tamanho_registro=792, usinas={})
    for cod in range(1, 21):
        posto, jus = hidr.get(cod, (cod, 0))
        h.usinas[cod] = UsinaHidr(cod, f"U{cod}", f"U{cod}".ljust(12).encode(), posto, jus)
    v = BlocoVazoes(ordenacao_automatica=ordenar, defasagem_linear=2, ano_final_historico=2020)
    dg = Dadger(
        uh=[RegistroUH(u, 1, nw, 0) for u, nw in uh],
        ac=[RegistroAC(u, mn, val, False, 0) for u, mn, val in ac],
        vi=[RegistroVI(u, d, 0) for u, d in vi],
        vazoes=v,
    )
    return Deck(diretorio=None, dadger=dg, hidr=h, modif=[Modif(p, u, a, b, 0) for p, u, a, b in modif])


class TestRegrasConfiguracao(unittest.TestCase):
    def test_jusante_segue_cadeia_do_hidr(self):
        # 1 -> 2 (fora) -> 3 (fora) -> 4 (presente)
        d = _deck_sintetico([(1, False), (4, False)], {1: (1, 2), 2: (2, 3), 3: (3, 4)})
        self.assertEqual({u.numero: u.jusante for u in montar_configuracao(d).usinas}, {1: 4, 4: 0})

    def test_numjus_vale_tambem_no_meio_da_cadeia(self):
        d = _deck_sintetico([(1, False), (5, False), (4, False)], {1: (1, 2), 2: (2, 4)}, ac=[(2, "NUMJUS", 5)])
        self.assertEqual(montar_configuracao(d).por_numero()[1].jusante, 5)

    def test_ordenacao(self):
        uh = [(5, False), (2, True), (3, False)]
        self.assertEqual([u.numero for u in montar_configuracao(_deck_sintetico(uh, {})).usinas], [2, 3, 5])
        cfg = montar_configuracao(_deck_sintetico(uh, {}, ordenar=0))
        self.assertEqual([u.numero for u in cfg.usinas], [5, 2, 3])
        self.assertEqual(cfg.ordem_vazoes_rv(), [5, 3, 2])

    def test_vincr_e_nposnw(self):
        d = _deck_sintetico(
            [(7, False), (8, False)], {7: (7, 8)},
            ac=[(7, "NUMPOS", 6), (7, "NPOSNW", 7), (8, "NPOSNW", 18)],
            modif=[("VINCR", 7, 6, 7)],
        )
        cfg = montar_configuracao(d)
        u7 = cfg.por_numero()[7]
        self.assertEqual((u7.posto, u7.posto_lateral, u7.posto_artificial, u7.nposnw), (7, 6, 0, 7))
        self.assertEqual(cfg.por_numero()[8].posto_artificial, 18)
        (lat,) = cfg.laterais
        self.assertEqual((lat.numero, lat.posto, lat.jusante, lat.status, lat.nome), (6, 6, 0, "PL", b"U7_L        "))

    def test_status(self):
        d = _deck_sintetico([(1, True), (2, False), (3, True)], {}, modif=[("PARTIF", 2, 2, 0), ("PARTIF", 3, 3, 0)])
        self.assertEqual([u.status for u in montar_configuracao(d).usinas], ["NW", "PN", "NW"])
        # P-CFG-06 é ESCOLHA (L14): a precedência é parâmetro.
        cfg = montar_configuracao(d, OpcoesConfiguracao(prioridade_status="PN"))
        self.assertEqual([u.status for u in cfg.usinas], ["NW", "PN", "PN"])

    def test_nome_lateral(self):
        # INFERIDO (P-CFG-12): SOBRADINHO_L no config.out público.
        self.assertEqual(nome_lateral(b"SOBRADINHO  "), b"SOBRADINHO_L")
        # ESCOLHA (P-CFG-12, L13): o corte em 12 caracteres não tem evidência
        # pública; este caso só fixa o padrão atual, que é parâmetro.
        self.assertEqual(nome_lateral(b"FOZ R. CLARO"), b"FOZ R. CLARO")
        d = _deck_sintetico([(7, False)], {}, modif=[("VINCR", 7, 6, 7)])
        cfg = montar_configuracao(d, OpcoesConfiguracao(nome_lateral=lambda n: b"LATERAL".ljust(12)))
        self.assertEqual(cfg.laterais[0].nome, b"LATERAL     ")

    def test_ordem_dos_laterais(self):
        d = _deck_sintetico([(7, False), (9, False)], {}, modif=[("VINCR", 7, 8, 7), ("VINCR", 9, 5, 9)])
        self.assertEqual([u.numero for u in montar_configuracao(d).laterais], [8, 5])
        cfg = montar_configuracao(d, OpcoesConfiguracao(ordem_laterais="numero"))
        self.assertEqual([u.numero for u in cfg.laterais], [5, 8])

    def test_ac_datado_depois_do_inicio(self):
        """P-DADG-12 (ESCOLHA, L14): sem evidência pública; só o parâmetro."""
        d = _deck_sintetico([(1, False)], {})
        d.dadger.vazoes.mes_inicial, d.dadger.vazoes.ano_inicial = 8, 2022
        d.dadger.ac = [
            RegistroAC(1, "NPOSNW", 305, True, 0, mes=8, semana=1, ano=2022),
            RegistroAC(1, "NUMPOS", 77, True, 0, mes=9, semana=1, ano=2022),
        ]
        u = montar_configuracao(d).usinas[0]
        self.assertEqual((u.posto_artificial, u.posto), (305, 77))
        u = montar_configuracao(d, OpcoesConfiguracao(ac_datado_futuro="ignora")).usinas[0]
        # NPOSNW datado na 1ª semana do mês inicial vale sempre (P-DADG-10);
        # NUMPOS de
        # setembro é ignorado
        self.assertEqual((u.posto_artificial, u.posto), (305, 1))
        semana2 = RegistroAC(1, "NUMPOS", 77, True, 0, mes=8, semana=2, ano=2022)
        self.assertTrue(semana2.posterior_ao_inicio(2022, 8))

    def test_ac_datado_sem_ano_ou_sem_semana(self):
        """P-DADG-13 (ESCOLHA, L14): formatos `MMM  s` e `MMM` dos DADGER
        públicos, lidos de um DADGER sintético."""
        from pulsar.entradas.dadger import ler_dadger

        texto = (
            "UH    1  10\r\n"
            + "AC    1  NPOSNW      305" + " " * 45 + "AGO  1\r\n"
            + "AC    1  NUMPOS       77" + " " * 45 + "JAN\r\n"
        ).encode("latin-1")
        dg = ler_dadger(texto)
        ago, jan = dg.ac
        self.assertEqual((ago.mes, ago.semana, ago.ano), (8, 1, None))
        self.assertEqual((jan.mes, jan.semana, jan.ano), (1, None, None))
        # estudo de agosto/2022: AGO 1 é a 1ª semana; JAN (ano do estudo) é antes
        self.assertEqual(dg.ac_config("NPOSNW", inicio=(2022, 8), datado_futuro="ignora"), {1: 305})
        self.assertEqual(dg.ac_config("NUMPOS", inicio=(2022, 8), datado_futuro="ignora"), {1: 77})
        # "proximo": JAN vira janeiro de 2023, depois do início, e é ignorado
        self.assertEqual(dg.ac_config("NUMPOS", inicio=(2022, 8), datado_futuro="ignora", ano_ausente="proximo"), {})
        self.assertEqual(jan.data_completa(2022, 8), (2022, 1, 1))
        with self.assertRaises(ValueError):
            dg.ac_config("NUMPOS", inicio=(2022, 8), datado_futuro="ignora", ano_ausente="erro")
        # pela configuração, com as opções
        d = _deck_sintetico([(1, False)], {})
        d.dadger.vazoes.mes_inicial, d.dadger.vazoes.ano_inicial = 8, 2022
        d.dadger.ac = dg.ac
        op = OpcoesConfiguracao(ac_datado_futuro="ignora", ac_ano_ausente="proximo")
        self.assertEqual(montar_configuracao(d, op).usinas[0].posto, 1)
        self.assertEqual(montar_configuracao(d).usinas[0].posto, 77)

    def test_ac_repetido(self):
        d = _deck_sintetico([(1, False)], {}, ac=[(1, "NUMPOS", 11), (1, "NUMPOS", 12)])
        self.assertEqual(montar_configuracao(d).usinas[0].posto, 12)
        self.assertEqual(montar_configuracao(d, OpcoesConfiguracao(ac_repetido="primeiro")).usinas[0].posto, 11)

    def test_janela_de_anos(self):
        cfg = configuracao("202610", None)
        d = deck("202610", None)
        for anos in ("intersecao", "postos", "geral"):
            with self.subTest(anos=anos):
                alt = montar_configuracao(d, OpcoesConfiguracao(anos=anos))
                # nos pacotes disponíveis as três fontes coincidem (lacuna L1)
                self.assertEqual([(u.ano_inicial, u.ano_final) for u in alt.completa],
                                 [(u.ano_inicial, u.ano_final) for u in cfg.completa])

    def test_parametros_do_config_out(self):
        cfg = configuracao("202610", None)
        alt = gerar_config_out(cfg, cabecalho2=lambda c: (len(c.completa), len(c.usinas) + len(c.laterais) + 9, 1),
                               percentual=lambda x: bytes(4) + b"\x01\x00\x00\x00")
        pub = (DECKS / "202610" / "config.out").read_bytes()
        R = TAMANHO_REGISTRO
        self.assertNotEqual(alt[172 * R : 173 * R], pub[172 * R : 173 * R])
        self.assertEqual(alt[R + 32 : R + 36], b"\x01\x00\x00\x00")


if __name__ == "__main__":
    unittest.main()
