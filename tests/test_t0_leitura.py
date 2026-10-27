"""T0: leitura de todas as entradas (03 §4).

Critério: sem erro e contagens/valores iguais ao texto do GEVAZP.REL.
"""

from __future__ import annotations

import collections
import unittest

import base  # noqa: F401  (ajusta sys.path)
import colecao_ons
import rel
from base import COMPLETOS, DECKS, SO_LEITURA, configuracao, deck
from pulsar.configuracao import montar_configuracao
from pulsar.entradas.binarios import ler_hidr
from pulsar.entradas.dadger import ler_dadger
from pulsar.entradas.deck import Deck
from pulsar.entradas.regras import analisar, avaliar, ler_regras, postos_referenciados

SIM_NAO = {"SIM": 1, "NAO": 0}


class TestDecksCompletos(unittest.TestCase):
    def test_le_todas_as_entradas(self):
        for nome, dadger in COMPLETOS + SO_LEITURA:
            with self.subTest(deck=nome, dadger=dadger):
                d = deck(nome, dadger)
                for campo in ("caso", "arquivos", "gevazp", "lista_decomp", "dadger", "hidr", "prevs", "postos", "historico", "modif", "regras"):
                    self.assertIsNotNone(getattr(d, campo), campo)
                self.assertEqual(d.gevazp.tipo_execucao, 99)  # modo DECOMP (U19 §4.3)
                self.assertIsNotNone(d.dadger.vazoes)
                self.assertEqual(d.dadger.vazoes.ano_inicial, d.dadger.vazoes.ano_inicial_estudo)  # U19 §4.5
                self.assertEqual(d.hidr.tamanho_registro, 792)
                self.assertEqual(d.historico.n_meses % 12, 0)
                self.assertGreaterEqual(d.historico.ano_final, d.dadger.vazoes.ano_final_historico)

    def test_dados_gerais_iguais_ao_rel(self):
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                d = deck(nome, dadger)
                v = d.dadger.vazoes
                g = rel.dados_gerais(rel.linhas_rel(DECKS / nome / "GEVAZP.REL"))
                esperado = {
                    "ARQUIVO COM LISTA DE ARQUIVOS DO DECOMP": d.arquivos["lista_decomp"],
                    "NUMERO DE SEGMENTOS": str(v.aberturas[0]),
                    "ORDEM MAXIMA DO MODELO AUTOREGRESSIVO": str(v.ordem_maxima),
                    "ANO INICIAL DO HISTORICO DE VAZOES": str(d.gevazp.ano_inicial_historico),
                    "MES FINAL PARA A GERACAO DE SERIES": str(v.mes_final),
                    "TAMANHO DO REGISTRO DO ARQ. VAZOES HISTORICAS": str(d.n_postos),
                    "NUMERO DE SEMANAS DO 1o MES DO ESTUDO": str(v.semanas_nao_observadas),
                    "NUMERO DE SEMANAS JA OBSERVADAS NO 1o MES DO ESTUDO": str(v.semanas_observadas),
                    "NUMERO DE SEMANAS TOTAIS 1o MES DO ESTUDO": str(v.semanas_nao_observadas + v.semanas_observadas),
                    "NUMERO DE DIAS DO MES 2 NA ULTIMA SEMANA": str(v.dias_excluidos),
                }
                for k, val in esperado.items():
                    self.assertEqual(g[k], val, k)
                self.assertEqual(SIM_NAO[g["ADOCAO DA ORDENACAO AUTOMATICA"]], v.ordenacao_automatica)
                self.assertEqual(SIM_NAO[g["AJUSTA MODELO ESTOCASTICO A TODAS AS USINA"]], v.ajuste_todas)
                self.assertEqual(SIM_NAO[g["AJUSTA MODELO ESTOCASTICO PAR-A"]], v.modelo_par_a)
                self.assertEqual(SIM_NAO[g["CONSIDERACAO DO FENOMENO ENOS NO AJUSTE DOS PARAMETROS"]], v.ms_par)
                self.assertEqual(g["ADOCAO DA MATRIZ DE CORRELACAO CRUZADA"], "MENSAL" if v.matriz_mensal == 1 else "ANUAL")
                self.assertEqual(g["REPRESENTANTE NO PROCESSO DE AGREGACAO"], "CENTROIDE" if v.representante == 1 else "MAIS PROXIMO")

    def test_prevs_igual_ao_rel(self):
        """Previsões semanais totais do REL = PREVS, para usinas EX e NW."""
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                d = deck(nome, dadger)
                cfg = configuracao(nome, dadger)
                tabela = rel.previsoes_semanais(rel.linhas_rel(DECKS / nome / "GEVAZP.REL"))
                self.assertEqual(len(tabela), len(cfg.usinas))
                n = 0
                for u, (_, posto, nome_rel, status, nums) in zip(cfg.usinas, tabela):
                    self.assertEqual((u.posto, u.nome_str), (posto, nome_rel))
                    if u.status.strip() in ("", "NW"):
                        sem = d.prevs[u.posto].semanas
                        self.assertEqual(nums[:6], sem + [0] * (6 - len(sem)), u.numero)
                        n += 1
                self.assertGreater(n, 150)

    def test_vazoes_dat_igual_a_serie_do_rel(self):
        """Usinas de cabeceira: série incremental do REL = VAZOES.DAT do posto."""
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                d = deck(nome, dadger)
                cfg = configuracao(nome, dadger)
                linhas = rel.linhas_rel(DECKS / nome / "GEVAZP.REL")
                testadas = 0
                for u in cfg.usinas:
                    if u.status.strip() or cfg.montante(u.numero):
                        continue
                    try:
                        serie = rel.serie_incremental(linhas, u.nome_str)
                    except KeyError:
                        continue
                    for ano, vals in serie.items():
                        meses = [d.historico.vazao(u.posto, ano, m) for m in range(1, 13)]
                        self.assertEqual([float(x) for x in meses], vals, (u.numero, ano))
                    testadas += 1
                self.assertGreater(testadas, 30)

    def test_modif_e_postos(self):
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                d = deck(nome, dadger)
                tabela, totais = rel.configuracao_usinas(rel.linhas_rel(DECKS / nome / "GEVAZP.REL"))
                n_partif = sum(1 for m in d.modif if m.palavra == "PARTIF")
                n_vincr = sum(1 for m in d.modif if m.palavra == "VINCR")
                self.assertEqual(n_partif, sum(1 for r in tabela if r.status == "PN"))
                self.assertEqual(str(n_vincr), totais["TOTAL DE USINAS COM POSTO DE VAZAO LATERAL"])
                for r in tabela:
                    p = d.postos[r.posto]
                    self.assertEqual((p.ano_inicial, p.ano_final), (r.ano_inicial, r.ano_final), r.num)

    def test_regras(self):
        for nome, dadger in COMPLETOS:
            with self.subTest(deck=nome):
                d = deck(nome, dadger)
                cfg = configuracao(nome, dadger)
                declarados = d.regras.postos()
                for r in d.regras.regras:
                    for p in postos_referenciados(r.expressao):
                        self.assertTrue(1 <= p <= d.n_postos, (r.posto, p))
                # U19 §3.10: todo posto artificial da configuração tem regra
                # em todos os meses.
                for u in cfg.usinas:
                    if u.posto_artificial:
                        self.assertIn(u.posto_artificial, declarados)
                        for mes in range(1, 13):
                            d.regras.regra(u.posto_artificial, mes)


class TestEscolhasDeLeitura(unittest.TestCase):
    def test_modif_sem_9999(self):
        from pulsar.entradas.prevs_modif import ler_modif

        texto = b" P.CHAV USI\r\n XXXXXX XXX\r\n PARTIF 108 108 107\r\n"
        with self.assertRaises(ValueError):
            ler_modif(texto)
        self.assertEqual([m.usina for m in ler_modif(texto, exigir_fim=False)], [108])

    def test_regras_sem_9999(self):
        cab = b" POST   MES  CONF    FORMULA\r\n XXXX    XX     X    XXXX\r\n"
        sem_fim1 = cab + b"  116     0          VAZ(119)\r\n"
        sem_fim2 = cab + b"  116     0          VAZ(119)\r\n 9999\r\n C\r\n C\r\n C\r\n  292      0      1\r\n"
        for texto, n in ((sem_fim1, 0), (sem_fim2, 1)):
            with self.assertRaises(ValueError):
                ler_regras(texto)
            r = ler_regras(texto, exigir_fim=False)
            self.assertEqual(len(r.regras), 1)
            self.assertEqual(len(r.variantes_por_ano), n)

    def test_fonte_do_numero_de_postos(self):
        from pulsar.entradas import ler_deck

        for fonte in ("dadger", "gevazp"):
            with self.subTest(fonte=fonte):
                self.assertEqual(ler_deck(DECKS / "202610", fonte_n_postos=fonte).n_postos, 320)


class TestRegrasSintaxe(unittest.TestCase):
    def test_exemplos_do_manual(self):
        # U19 §3.10, exemplos 1 e 2.
        e1 = analisar("MAX(13900;VAZ(288)*1.2)")
        self.assertEqual(avaliar(e1, lambda p: 12000.0), 14400.0)
        self.assertEqual(avaliar(e1, lambda p: 1000.0), 13900.0)
        e2 = analisar("SE(VAZ(237)-100<=300;50;SE(VAZ(237)-100<=350;100;150))")
        self.assertEqual(avaliar(e2, lambda p: 400.0), 50.0)
        self.assertEqual(avaliar(e2, lambda p: 440.0), 100.0)
        self.assertEqual(avaliar(e2, lambda p: 500.0), 150.0)

    def test_simbolos_alternativos(self):
        v = {1: 5.0, 2: 7.0}.get
        self.assertEqual(avaliar(analisar("SE(VAZ(1)@5&VAZ(2)~7;1;0)"), v), 1.0)
        self.assertEqual(avaliar(analisar("SE(VAZ(1)!5|VAZ(2)=7;1;0)"), v), 1.0)
        self.assertEqual(avaliar(analisar("se(vaz(1)<>5 OU vaz(2)<7;1;0)"), v), 0.0)
        self.assertEqual(avaliar(analisar("-VAZ(1)+2*(VAZ(2)-1)/3"), v), -1.0)

    def test_parametros_de_selecao_e_precisao(self):
        from pulsar.entradas.regras import Regra, Regras

        r = lambda mes, var, txt: Regra(1, mes, var, txt, analisar(txt), 0)
        rg = Regras([r(0, 0, "1"), r(3, 0, "2"), r(0, 1, "3")], {1: [0, 1]})
        self.assertEqual(rg.regra(1, 3).texto, "2")
        self.assertEqual(rg.regra(1, 3, prioridade="zero").texto, "1")
        self.assertEqual(rg.regra(1, 5, ano_estudo=2).texto, "3")
        self.assertEqual(rg.regra(1, 5, ano_estudo=3).texto, "1")
        self.assertEqual(rg.regra(1, 5, ano_estudo=3, ano_alem_do_bloco2="ultima").texto, "3")
        e = analisar("VAZ(1)/3*3")
        self.assertEqual(avaliar(e, lambda p: 1.0), 1.0)
        self.assertNotEqual(avaliar(e, lambda p: 1.0, arredondar=lambda x: round(x, 2)), 1.0)

    def test_erros(self):
        for ruim in ("VAZ(1", "MAX(1)", "SE(1;2)", "1+", "VAZ(X)", "2 3"):
            with self.subTest(regra=ruim), self.assertRaises(ValueError):
                analisar(ruim)


# DADGER da coleção de decks do ONS que são recortes começando em "UH 2": falta o
# registro UH 1, que o vazoes.rvN publicado do mesmo caso inclui.
DADGER_NAS_SEM_UH1 = {"201307_rv2", "201503_rv0", "201607_rv4", "201609_rv0"}


@unittest.skipUnless(colecao_ons.disponivel(), "coleção de decks do ONS indisponível")
class TestColecaoONS(unittest.TestCase):
    """Coleção parcial de decks do ONS (DADGER, HIDR, REGRAS de 2012 a 2026)."""

    def test_le_todos_os_casos(self):
        casos = colecao_ons.casos_gevazp()
        por_ano = collections.Counter()
        sem_hidr: list[str] = []
        for c in casos:
            with self.subTest(caso=c.nome):
                dg = ler_dadger(c.dadger)
                self.assertTrue(dg.uh)
                self.assertIsNotNone(dg.vazoes)
                self.assertEqual(dg.vazoes.ano_inicial or dg.vazoes.ano_inicial_estudo, dg.vazoes.ano_inicial_estudo)
                self.assertTrue(dg.vazoes.aberturas)
                por_ano[c.ano] += 1
                if c.hidr is None:  # 201210 e 201211 não têm HIDR na coleção
                    sem_hidr.append(c.nome)
                    continue
                h = ler_hidr(c.hidr)
                cfg = montar_configuracao(Deck(diretorio=c.diretorio, dadger=dg, hidr=h))
                self.assertEqual(len(cfg.usinas), len({r.usina for r in dg.uh}))
                if c.regras is not None:
                    r = ler_regras(c.regras)
                    self.assertTrue(r.regras)
                    # Todo NPOSNW tem regra, exceto o de usina com posto
                    # lateral, que aponta o posto total (U19 §4.5). Sem
                    # MODIF.DAT na coleção, o posto total é reconhecido por
                    # ser o posto original do HIDR.
                    for u in cfg.usinas:
                        if u.posto_artificial and u.posto_artificial != h[u.numero].posto:
                            self.assertIn(u.posto_artificial, r.postos(), u.numero)
        self.assertGreaterEqual(sum(por_ano.values()), 30)
        self.assertGreaterEqual(len(por_ano), 10)
        self.assertLessEqual(len(sem_hidr), 2, sem_hidr)

    def test_ordem_igual_ao_vazoes_rv_do_decomp(self):
        """Conjunto e ordem das usinas = registro 2 do vazoes.rvN publicado
        no deck DECOMP do mesmo mês e revisão (U19 §5.3.4).

        De jan/2017 em diante a ordem é exata. Antes disso o arquivo público
        põe as usinas PARTIF no fim (MODIF.DAT da época não está na coleção)
        e tem lixo depois dos códigos; ali se confere só o conjunto, com a
        quantidade do 1º inteiro do registro 1.
        """
        zips = colecao_ons.zips_decomp()
        exatos = collections.Counter()
        conjunto = collections.Counter()
        for c in colecao_ons.casos_gevazp():
            z = zips.get((c.ano, c.mes, c.rev))
            if z is None or c.hidr is None:
                continue
            vazoes = colecao_ons.vazoes_rv_do_zip(z)
            if vazoes is None:
                continue
            with self.subTest(caso=c.nome):
                cfg = montar_configuracao(Deck(diretorio=c.diretorio, dadger=ler_dadger(c.dadger), hidr=ler_hidr(c.hidr)))
                codigos = colecao_ons.codigos_vazoes_rv(vazoes)
                if (c.ano, c.mes) >= (2017, 1):
                    self.assertEqual(cfg.ordem_vazoes_rv(), codigos)
                    exatos[c.ano] += 1
                else:
                    n = colecao_ons.registro1_vazoes_rv(vazoes)[0]
                    meus = sorted(cfg.ordem_vazoes_rv())
                    if c.nome in DADGER_NAS_SEM_UH1:
                        self.assertNotIn(1, meus)
                        meus = sorted(meus + [1])
                    self.assertEqual(meus, sorted(codigos[:n]))
                    conjunto[c.ano] += 1
        # Números da coleção em 26/10/2026 (P-CFG-16): se a coleção crescer,
        # atualize-os junto com a linha de proveniência.
        self.assertEqual(sum(exatos.values()), 503)
        self.assertEqual(sum(conjunto.values()), 226)
        self.assertGreaterEqual(len(exatos), 9)

if __name__ == "__main__":
    unittest.main()
