"""T11: aceitação estatística da geração completa (03 §5), 20 sementes por
deck, e escolha das variantes das lacunas L6, L7 e L8 (P-ACE-06, P-AGR-04,
P-LN3-03, P-RUI-04).

Lento sem cache: cada semente faz um K-means de 50 000 × 155 (~2 min);
``./ambiente/py ferramentas/sementes_f8.py -j 14 --simetria nenhuma antitetica``
e ``... --lateral-na-agregacao nao`` (variante "sem_lateral_na_agregacao")
preenchem cache/f8/ em paralelo. ``python -c "import aceitacao_f8 as a;
a.relatorio()"`` (com tests/ e src/ no caminho) imprime a tabela completa.

Resultado (faixa [mín, máx] das 20 sementes, P-ACE-06; a referência de um
gerador idêntico é 0,90), com a lognormal da F11 (P-LN3-04, P-LN3-09) e o
lateral da P-LAT-02/04, e na primeira versão da F8 (variante "f8": M_t = 0,
momentos teóricos, lateral com a correlação anual e ruído próprio):

========  ======  =====  ======  =====  =====  =====  =====  ======  ======
deck      versão  média  desvio  assim  Q1     Q2     Q3     correl  árvore
========  ======  =====  ======  =====  =====  =====  =====  ======  ======
202609    F11     0,929  0,929   0,851  0,916  0,903  0,935  0,915   1,000
202609    F8      0,922  0,909   0,857  0,890  0,870  0,909  0,908   1,000
202610    F11     0,916  0,877   0,844  0,890  0,896  0,870  0,896   1,000
202610    F8      0,909  0,851   0,805  0,883  0,890  0,792  0,893   1,000
========  ======  =====  ======  =====  =====  =====  =====  ======  ======

A "árvore" é uma coluna só (a soma) com seis estatísticas: uma fora já dá
0,833 (como na variante "sem_lateral_na_agregacao" do 202609, com o Q3 da
soma 0,4% abaixo da faixa). Diferenças de até ~0,05 entre variantes são o
ruído de duas frações em ~154 postos (2σ). Com P5–P95 (o exemplo de 03 §5) as frações caem para 0,72–0,86, o mesmo
nível da referência (0,82): o critério de 90% não é atingível com 20
sementes por essa faixa.
"""

import numpy as np
import pytest

import aceitacao_f8 as R
import apoio_f8

ESTATISTICAS = R.ESTATISTICAS + ("correlacao", "arvore")


def test_aceitacao_da_geracao_padrao(pacote):
    """03 §5 item 4 com a faixa [mín, máx] (P-ACE-06): média, Q2 e
    correlação espacial ficam em ≥ 0,87 dos postos nos dois decks
    (referência 0,90), a árvore como um todo em ≥ 5 das 6 estatísticas
    (uma coluna só: na referência, cada semente contra as outras 19, as 6
    ficam dentro em só 9 a 13 das 20 sementes), nenhuma estatística abaixo
    de 0,83 e a média das frações ≥ 0,89. Com a F11 a assimetria e o Q3
    do 202610 sobem de 0,805 e 0,792 (primeira versão) para 0,844 e 0,870
    (::test_primeira_versao_da_f8)."""
    f = R.fracoes(pacote.nome)
    ref = R.fracoes_referencia(pacote.nome)
    print(pacote.nome, {k: round(v, 3) for k, v in f.items()})
    assert all(abs(ref[k] - 0.9) < 0.01 for k in R.ESTATISTICAS)
    for k in ("media", "q50", "correlacao"):
        assert f[k] >= 0.87, k
    assert f["arvore"] >= 5 / 6 - 1e-9
    assert min(f.values()) >= 0.83
    assert np.mean(list(f.values())) >= 0.89


def test_primeira_versao_da_f8(pacote):
    """L8/L11 (frente F11): comparação com a primeira versão da F8 (M_t = 0,
    momentos teóricos, lateral anual com ruído próprio). A F11 não perde
    mais de 0,01 em nenhuma estatística por posto, e no 202610 a forma da
    distribuição, que era a pendência da L7, melhora: desvio 0,851 → 0,877,
    assimetria 0,805 → 0,844 e Q3 0,792 → 0,870 (o ganho no Q3 está acima
    do ruído de ~0,05; o da assimetria, no limite). O ganho vem do M_t: só
    M_t = 0, com o resto da F11, deixa a assimetria e o Q3 do 202610 em
    0,805 e 0,799 (variante "zero")."""
    b, v = R.fracoes(pacote.nome), R.fracoes(pacote.nome, "f8")
    print(pacote.nome, "F11", {k: round(x, 3) for k, x in b.items()}, "F8", {k: round(x, 3) for k, x in v.items()})
    assert all(b[k] >= v[k] - 0.01 for k in ESTATISTICAS if k != "arvore")
    if pacote.nome == "202610":
        assert b["assimetria"] - v["assimetria"] >= 0.03 and b["q75"] - v["q75"] >= 0.06
        z = R.fracoes(pacote.nome, "zero")
        assert b["assimetria"] - z["assimetria"] >= 0.03 and b["q75"] - z["q75"] >= 0.06


def test_vereditos_do_m18_cap6(pacote):
    """03 §5 item 4, 2ª parte (P-ACE-05): fração das 153 séries rejeitadas a
    5% no GEVAZP.OUT oficial e nas sementes (mín–máx). t da média: eq. 6.15;
    desvio: eq. 6.18 com os valores-padrão da Tabela 6.1; KS: Tabela 6.2;
    CvM: eq. 6.20–6.21 e Tabela 6.3.

    ========  ===================  ===================  ===================  ===================
    deck      t da média           desvio               KS                   CvM
    ========  ===================  ===================  ===================  ===================
    202609    0,013 (0,013–0,020)  0,026 (0,020–0,065)  0,013 (0,013–0,026)  0,013 (0,013–0,020)
    202610    0,013 (0,013–0,026)  0,046 (0,020–0,118)  0,020 (0,020–0,026)  0,020 (0,020)
    ========  ===================  ===================  ===================  ===================

    O veredito é o mesmo (rejeição rara, < 6% no oficial e na mediana das
    sementes); com a F11 o oficial fica dentro da faixa das sementes nos
    quatro testes (na primeira versão, até 2 séries acima em KS e CvM). Uma
    semente do 202610 rejeita 11,8% no teste do desvio."""
    of, sem = R.oficial_e_sementes(pacote.nome, R.rejeicoes)
    print(pacote.nome, of)
    for t in R.TESTES:
        v = [s[t] for s in sem]
        assert min(v) - 1e-9 <= of[t] <= max(v) + 1e-9, (t, of[t], min(v), max(v))
        assert of[t] < 0.06 and np.median(v) < 0.06


@pytest.mark.parametrize("variante", ["desvio_simples", "desvio_amostral", "desvio_zero", "por_usina"])
def test_variantes_l7(pacote, variante):
    """P-AGR-04/05 (lacuna L7): as variantes de σ_i e o fator por usina dão
    frações por posto a ±0,05 da padrão, o ruído de duas frações em ~154
    postos (não se separam nos dados públicos)."""
    b, v = R.fracoes(pacote.nome), R.fracoes(pacote.nome, variante)
    # a árvore (uma coluna, seis estatísticas) varia de 1/6 por acaso
    assert all(abs(b[k] - v[k]) <= 0.05 for k in ESTATISTICAS if k != "arvore"), (variante, v)


def test_fator_das_variantes_l7(pacote):
    """P-AGR-04: na semente 1 os FC das variantes de σ_i diferem < 0,3%:
    202609 3,6602 / 3,6585 / 3,6514 / 3,6598 e 202610 3,7417 / 3,7396 /
    3,7313 / 3,7412 (ponderado / simples / amostral / zero), com o vetor
    agregado das séries da carga e do lateral (P-AGR-07, 155 componentes).
    Sem o lateral no vetor (variante "sem_lateral_na_agregacao", 154):
    3,6485 / 3,6464 / 3,6394 / 3,6480 e 3,7331 / 3,7312 / 3,7230 / 3,7327."""
    from pulsar.estocastico.agregacao import compensar

    esperado = {("202609", True): (3.6602, 3.6585, 3.6514, 3.6598),
                ("202610", True): (3.7417, 3.7396, 3.7313, 3.7412),
                ("202609", False): (3.6485, 3.6464, 3.6394, 3.6480),
                ("202610", False): (3.7331, 3.7312, 3.7230, 3.7327)}
    for lat in (True, False):
        a = apoio_f8.agregacao(pacote.nome, 1, "nenhuma", lat)
        assert len(a.postos) == (155 if lat else 154)
        fc = {d: float(compensar(a, d, "escalar").fator) for d in ("ponderado", "simples", "amostral", "zero")}
        assert np.allclose(list(fc.values()), esperado[(pacote.nome, lat)], atol=6e-5)
        assert (max(fc.values()) - min(fc.values())) / fc["ponderado"] < 0.003


def test_sem_fator_de_compensacao_falha(pacote):
    """P-AGR-05 (R3383 eq. 2.2): sem o fator a média, o desvio e os quartis
    extremos dos cenários oficiais ficam fora da faixa em mais de 90% dos
    postos."""
    f = R.fracoes(pacote.nome, "sem_fator")
    assert max(f["media"], f["desvio"], f["q25"], f["q75"]) < 0.1 and f["arvore"] == 0


@pytest.mark.parametrize("variante", ["cubica_residuos", "cubica_vazoes", "quantis"])
def test_rotas_l8(pacote, variante):
    """P-LN3-03 (lacuna L8): as cúbicas e os quantis perdem para a regra
    inferida (P-LN3-09) ≥ 0,05 na média das frações (0,06 a 0,13) e ≥ 0,1
    na assimetria e no Q3."""
    b, v = R.fracoes(pacote.nome), R.fracoes(pacote.nome, variante)
    assert np.mean(list(b.values())) - np.mean(list(v.values())) >= 0.05, v
    assert b["assimetria"] - v["assimetria"] >= 0.1 and b["q75"] - v["q75"] >= 0.1


def test_momentos_e_lateral_nao_se_separam(pacote):
    """P-LN3-04, P-LAT-02, P-LAT-04, P-AGR-07: os momentos teóricos, a
    correlação anual do lateral, o ruído próprio do lateral e o vetor
    agregado sem o lateral dão frações a ±0,05 das da F11 por posto (o
    ruído de duas frações): o T11 não separa essas escolhas; as três
    primeiras vêm dos testes de núcleo exatos
    (test_oraculo_limite_inferior.py, test_oraculo_laterais.py)."""
    b = R.fracoes(pacote.nome)
    for var in ("momentos_teoricos", "lateral_anual", "lateral_proprio", "sem_lateral_na_agregacao"):
        v = R.fracoes(pacote.nome, var)
        assert all(abs(b[k] - v[k]) <= 0.05 for k in ESTATISTICAS if k != "arvore"), (var, v)


def test_simetria(pacote):
    """P-RUI-04 (lacuna L6): com a amostra antitética a média gerada fica
    perto demais da teórica: a fração da média cai de 0,929 para 0,851
    (202609) e de 0,916 para 0,818 (202610); a amostra aleatória simples
    fica (na primeira versão da F8: 0,922 → 0,825 e 0,909 → 0,760)."""
    b, v = R.fracoes(pacote.nome), R.fracoes(pacote.nome, "antitetica")
    print(pacote.nome, "antitética", {k: round(x, 3) for k, x in v.items()})
    assert b["media"] - v["media"] >= 0.05  # 0,929 → 0,851 e 0,916 → 0,818
    assert len(apoio_f8.SEMENTES) == 20
