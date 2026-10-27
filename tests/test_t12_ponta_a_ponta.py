"""T12: ponta a ponta (03 §4), frente F9.

- a CLI (``src/pulsar/cli.py``) escolhe a revisão e grava VAZOES.RVx e
  PROBVAZ.DAT (P-CLI-01..03);
- em cada VAZOES.RVx publicado (202609 RV0 e RV1, 202610 RV0), palavras
  iguais por bloco: registros 1–3 e blocos determinísticos iguais byte a
  byte, inclusive no 202609 RV0, cuja execução não tem saídas no pacote;
- a agregação oficial não depende da revisão (P-INT-01);
- transplante entre revisões (03 §3): o ruído W oficial do RV1, reconstruído
  do GEVAZP.OUT, com o condicionamento do RV0 reproduz o VAZOES.RV0 (P-INT-02);
- estatísticas de 03 §5 sobre os blocos inteiros do VAZOES.RVx (P-INT-03).

Usa as agregações em cache de tests/apoio_f8.py
(``./ambiente/py ferramentas/sementes_f8.py`` preenche cache/f8/).
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

import apoio_f8
import apoio_f9 as F
import base
from pulsar import cli
from pulsar import oraculos as O
from pulsar.empacotamento import montar_arvore, nint, serializar_vazoes_rvx
from pulsar.empacotamento.vazoes_rvx import RegistrosDeterministicos
from pulsar.entradas import ErroLeitura
from pulsar.estocastico import geracao as G
from pulsar.estocastico.lognormal import parametros
from pulsar.tendencia import tendencia
from pulsar.totalizacao import calcular_series, dados_defasagem
from pulsar.vazoes_deterministicos import montar_registros
from test_t8_totalizacao import _transplante
from test_t9_empacotamento import palavras_por_bloco

REVISOES = F.revisoes()
DETERMINISTICOS = ("registro 1", "registro 2", "registro 3", "prevista_semanal", "prevista_semanal_ena",
                   "observada_mensal", "observada_semanal")
GERADOS = ("probabilidades", "gerada_mensal", "gerada_mensal_ena")


def test_revisoes_publicadas():
    assert REVISOES == [("202609", "RV0"), ("202609", "RV1"), ("202610", "RV0")]


# ------------------------------------------------------------------ CLI


def test_revisao_da_cli():
    """P-CLI-01: sem revisão, a cadeia do ARQUIVOS.DAT (P-DECK-04); com
    revisão, a lista do DECOMP de mesmo nome (sem diferenciar maiúsculas)."""
    d609 = base.DECKS / "202609"
    assert cli.ler_revisao(d609)[1] == "RV1"
    for pedida, rev, prevs, semanas in (("RV0", "RV0", "PREVS.RV0", 5), ("rv1", "RV1", "PREVS.RV1", 4)):
        deck, r = cli.ler_revisao(d609, pedida)
        assert r == rev and deck.dadger.vazoes.arquivo_prevs == prevs
        assert deck.dadger.vazoes.semanas_nao_observadas == semanas
        assert deck.lista_decomp.dadger.upper() == f"DADGER.{rev}"
    assert cli.ler_revisao(base.DECKS / "202610", "RV0")[1] == "RV0"
    for ruim in ("RV2", "R0", "../RV0"):
        with pytest.raises(ErroLeitura):
            cli.ler_revisao(d609, ruim)


def test_argumentos_e_opcoes_padrao():
    """P-CLI-03: os padrões da CLI são os padrões das ESCOLHAS (P-GER-01,
    P-RUI-04, P-AGR-04, P-LN3-03, P-LN3-04)."""
    a = cli.argumentos(["deck", "--revisao", "RV0", "--saida", "x/VAZOES.RV0", "--semente", "7"])
    assert (a.deck, a.revisao, a.saida, a.semente) == ("deck", "RV0", "x/VAZOES.RV0", 7)
    op = cli.opcoes_de(cli.argumentos(["deck"]))
    assert op == G.OpcoesGeracao()


def test_executar_grava_vazoes_e_probvaz(tmp_path):
    """P-CLI-02: ``executar`` (o que a CLI chama) grava o VAZOES.RVx e o
    PROBVAZ.DAT no diretório da saída, iguais aos da cadeia em cache, com o
    tamanho dos públicos."""
    s = apoio_f8.SEMENTES[0]
    for nome, rev in REVISOES:
        saida = tmp_path / nome / f"VAZOES.{rev}"
        ex = cli.executar(base.DECKS / nome, rev, saida, G.OpcoesGeracao(semente=s),
                          agregacao=apoio_f8.agregacao(nome, s))
        _, b, r = F.gerado(nome, rev, s)
        assert ex.revisao == rev and saida.read_bytes() == b
        assert saida.stat().st_size == (base.DECKS / nome / f"VAZOES.{rev}").stat().st_size
        assert ex.probvaz == saida.parent / "PROBVAZ.DAT"
        assert np.array_equal(O.ler_probvaz(ex.probvaz), r.probabilidades)
        assert ex.probvaz.stat().st_size == (base.DECKS / nome / "PROBVAZ.DAT").stat().st_size


def test_nome_padrao_da_saida(tmp_path, monkeypatch):
    """P-CLI-02: sem ``--saida``, o VAZOES.RVx vai para o diretório corrente
    com o nome do registro 2 da lista do DECOMP da revisão (U19 §4.4) em
    maiúsculas. Divergência: as listas públicas dizem ``vazoes.rv0`` e
    ``vazoes.rv1``, e os pacotes trazem ``VAZOES.RV0`` e ``VAZOES.RV1``; vale
    o nome publicado. Sem a lista da revisão, ``VAZOES.<RVn>``."""
    for nome, rev in REVISOES:
        d = F.deck(nome, rev)
        assert d.lista_decomp.vazoes == f"vazoes.{rev.lower()}"  # o que a lista diz
        assert cli.nome_vazoes(d, rev) == f"VAZOES.{rev}"
        assert (base.DECKS / nome / f"VAZOES.{rev}").is_file()  # o que o pacote traz
    # lista de outra revisão (recaída de P-CLI-01): VAZOES.<RVn>
    assert cli.nome_vazoes(base.deck("202609"), "RV0") == "VAZOES.RV0"
    monkeypatch.chdir(tmp_path)
    s = apoio_f8.SEMENTES[0]
    ex = cli.executar(base.DECKS / "202609", "RV0", None, G.OpcoesGeracao(semente=s),
                      agregacao=apoio_f8.agregacao("202609", s))
    assert ex.saida == Path("VAZOES.RV0") and (tmp_path / "VAZOES.RV0").read_bytes() == F.gerado("202609", "RV0", s)[1]
    assert (tmp_path / "PROBVAZ.DAT").is_file()


def test_cli_completa_sem_cache(tmp_path):
    """A CLI de verdade (``main``, com o K-means; ~2–5 min) no 202610 com a
    semente 1 grava os mesmos bytes que a cadeia com a agregação em cache."""
    saida = tmp_path / "VAZOES.RV0"
    assert cli.main([str(base.DECKS / "202610"), "--revisao", "RV0", "--saida", str(saida), "--semente", "1"]) == 0
    _, b, r = F.gerado("202610", "RV0", 1)
    assert saida.read_bytes() == b
    assert np.array_equal(O.ler_probvaz(tmp_path / "PROBVAZ.DAT"), r.probabilidades)


# ----------------------------------------------------- palavras por bloco


@pytest.mark.parametrize("nome,rev", REVISOES)
def test_palavras_por_bloco(nome, rev):
    """03 §5 (último parágrafo): palavras iguais por bloco, semente 1. Os
    blocos determinísticos ficam iguais byte a byte em todas as revisões;
    os gerados e as probabilidades das folhas, não (lacunas L6–L8)."""
    a, b, _ = F.gerado(nome, rev, 1)
    o = F.oficial_bytes(nome, rev)
    assert len(b) == len(o)
    c = palavras_por_bloco(b, o, a)
    print(nome, rev, {k: f"{i}/{t}" for k, (i, t) in c.items()})
    for k in DETERMINISTICOS:
        assert c[k][0] == c[k][1], k
    for k in GERADOS:
        assert c[k][0] < c[k][1], k


# ------------------------------------------- agregação e transplante


def test_agregacao_oficial_nao_depende_da_revisao():
    """P-INT-01: as 259 probabilidades das folhas do VAZOES.RV0 e do
    VAZOES.RV1 oficiais do 202609 são iguais bit a bit (PREVS, semanas e
    tendência diferem), e os cenários das duas revisões têm correlação
    mediana > 0,999 por posto: a agregação oficial depende só da
    configuração, de K e da semente, como no Pulsar (P-RUI-01, P-AGR-01),
    que dá as mesmas probabilidades nas duas revisões."""
    v0, v1 = F.oficial("202609", "RV0"), F.oficial("202609", "RV1")
    assert np.array_equal(F.folhas(v0), F.folhas(v1))
    g0, g1 = np.asarray(v0.gerada_mensal, float), np.asarray(v1.gerada_mensal, float)
    cols = [j for j in range(g1.shape[1]) if g1[:, j].std() > 0 and g0[:, j].std() > 0]
    c = np.array([np.corrcoef(g0[:, j], g1[:, j])[0, 1] for j in cols])
    print("correlação RV0 x RV1:", np.round(np.percentile(c, [0, 5, 50]), 4))
    assert np.median(c) > 0.999 and c.min() > 0.8
    r0, r1 = F.gerado("202609", "RV0", 1)[2], F.gerado("202609", "RV1", 1)[2]
    assert np.array_equal(r0.probabilidades, r1.probabilidades)


def _condicionamento(pr, tend, s, m, f8=False):
    """Lognormal do período: a da F11 (regra P-LN3-09 e momentos históricos,
    P-LN3-04) ou, com ``f8``, a da primeira versão (M_t = 0, teóricos)."""
    aj = pr.ajustes[id(s)]
    zp, a = G.passado_da_serie(tend, s.posto, pr.mes)
    c = G.termo_condicional(aj, m, zp, a)
    mu, sd = G.momentos_do_ruido(aj, m, "teoricos" if f8 else "historicos")
    sig = float(aj.est.desvio[m])
    if f8:
        return aj, zp, a, c, sig, parametros(c, sig, mu, sd)
    return aj, zp, a, c, sig, parametros(c, sig, mu, sd, "inferida", limite_vazao=G.limite_do_mes(aj, m))


def transplante_entre_revisoes(nome="202609", origem="RV1", destino="RV0", f8=False):
    """W oficial reconstruído do GEVAZP.OUT de ``origem`` (com a NW tirada do
    VAZTOTGD.DAT, F6-TOT-05) invertendo a lognormal e a recorrência do
    Pulsar com o condicionamento de ``origem``; reaplicado com o de
    ``destino``; totalização (F6), registros determinísticos (F5) e
    gravação (F7) do ``destino`` com as probabilidades oficiais."""
    po, pd = F.preparo(nome, origem), F.preparo(nome, destino)
    do, dd = F.deck(nome, origem), F.deck(nome, destino)
    co, cd = F.configuracao(nome, origem), F.configuracao(nome, destino)
    assert [u.numero for u in co.completa] == [u.numero for u in cd.completa] and po.mes == pd.mes
    m = po.mes - 1
    to, td = tendencia(do, co), tendencia(dd, cd)
    inc_o = _transplante(nome)
    inc_d = np.zeros_like(inc_o)
    ident = np.zeros_like(inc_o)
    por_d = {(s.numero, s.status): s for s in pd.todas}
    ws = {}
    for s in po.todas:
        if s.nula:
            continue
        i = po.indice[id(s)]
        ajo, zpo, ao, cco, sig, lo = _condicionamento(po, to, s, m, f8)
        ajd, zpd, ad, ccd, _, ld = _condicionamento(pd, td, por_d[(s.numero, s.status)], m, f8)
        x = inc_o[:, i] / sig - cco - lo.delta
        # Todas as séries do 202609 RV1, SOBRADINHO inclusive, ficam acima do
        # limite da lognormal em todos os cenários; outro caso é erro.
        assert (x > 0).all(), s.nome
        w = (np.log(x) - lo.mu_xi) / lo.sigma_xi
        ws[s.posto] = w
        inc_d[:, i] = G.recorrencia(ajd, m, zpd, ad, ld.ruido(w))
        ident[:, i] = G.recorrencia(ajo, m, zpo, ao, lo.ruido(w))
    tot = calcular_series(inc_d, cd, dd.regras, pd.mes, pd.ano_estudo, dados_defasagem(dd, cd))
    r = montar_registros(dd, cd)
    det = RegistrosDeterministicos(r.prevista_semanal, r.prevista_semanal_ena, r.observada_mensal, r.observada_semanal)
    p = O.ler_probvaz(base.DECKS / nome / "PROBVAZ.DAT")
    a = montar_arvore(cd, dd.dadger.vazoes, dd.n_postos, tot.incrementais, tot.incrementais_artificiais, p, det, F.NPOS)
    return a, serializar_vazoes_rvx(a), inc_o, ident, ws


def test_transplante_entre_revisoes(tmp_path):
    """P-INT-02 (03 §3, transplante): com o W oficial do RV1 (lognormal da
    F11: M_t da P-LN3-09 e momentos históricos, P-LN3-04) e o
    condicionamento do RV0 (PREVS.RV0, 5 semanas previstas), o VAZOES.RV0
    do 202609 sai igual ao oficial byte a byte, inclusive as 82 880
    palavras de cada bloco gerado (6 e 8). Controle: reaplicar o
    condicionamento do próprio RV1 devolve o NINT do GEVAZP.OUT em 100%
    dos valores.

    Com a lognormal da primeira versão da F8 (M_t = 0, momentos teóricos)
    o mesmo transplante acertava 90,0% e 89,9% das palavras das colunas
    com dispersão (153 e 154), com erro de ±1 em 85% das diferentes, até
    18 m³/s, pior coluna JIRAU (11%), crescendo com |W|: era o erro de
    escala nos parâmetros da lognormal que a F11 corrigiu."""
    a, b, inc_o, ident, ws = transplante_entre_revisoes()
    assert np.array_equal(nint(ident), nint(inc_o))
    o = F.oficial_bytes("202609", "RV0")
    c = palavras_por_bloco(b, o, a)
    print("transplante RV1 -> RV0:", {k: f"{i}/{t}" for k, (i, t) in c.items()})
    assert b == o
    # controle: lognormal da primeira versão da F8
    a8, b8, *_ = transplante_entre_revisoes(f8=True)
    (tmp_path / "VAZOES.RV0").write_bytes(b8)
    meu = O.ler_vazoes_decomp(tmp_path / "VAZOES.RV0")
    of = F.oficial("202609", "RV0")
    for bloco, n_cols in (("gerada_mensal", 153), ("gerada_mensal_ena", 154)):
        cols = F.colunas("202609", "RV0", bloco)
        assert len(cols) == n_cols, bloco
        d = (np.asarray(getattr(meu, bloco), float) - np.asarray(getattr(of, bloco), float))[:, cols]
        print(bloco, "primeira versão, colunas com dispersão:", (d == 0).mean())
        assert 0.89 <= (d == 0).mean() < 0.91, bloco


# ------------------------------------------ estatísticas de 03 §5 no VAZOES


@pytest.mark.parametrize("nome,rev", REVISOES)
def test_aceitacao_no_vazoes_rvx(nome, rev):
    """P-INT-03 (03 §5 itens 2–4) sobre o bloco 6 (incrementais geradas
    inteiras) do VAZOES.RVx, com as probabilidades do registro 4 e os
    limiares do T11 (tests/test_t11_aceitacao.py::
    test_aceitacao_da_geracao_padrao): média, Q2 e correlação na faixa
    [mín, máx] das 20 sementes (P-ACE-06) em ≥ 0,87 das colunas, a árvore
    como um todo em ≥ 5 das 6 estatísticas (uma coluna só; na referência
    as seis ficam dentro em só metade das sementes), nenhuma estatística
    abaixo de 0,78 e média das frações ≥ 0,87. Com a F11: 202609 RV0 e RV1
    e 202610 RV0 com média 0,935 / 0,948 / 0,908, correlação 0,917 / 0,917 /
    0,899 e a árvore com as seis estatísticas na faixa (na F9: média 0,908 /
    0,941 / 0,908 e correlação 0,909 / 0,912 / 0,894). Inclui o 202609 RV0, uma execução oficial sem GEVAZP.OUT no
    pacote, que o T11 não cobre.

    Controle da referência (cada semente contra as outras 19): 0,90 ± 0,01
    em média, desvio, assimetria e correlação, como no T11; nos quartis a
    referência sobe para 0,94–0,96, porque os valores do VAZOES.RVx são
    inteiros e os empates alargam a faixa [mín, máx]; o teste exige
    0,90–0,97 neles."""
    f = F.fracoes(nome, rev)
    ref = F.fracoes_referencia(nome, rev)
    print(nome, rev, {k: round(x, 3) for k, x in f.items()}, "ref", {k: round(x, 3) for k, x in ref.items()})
    for k in ("media", "desvio", "assimetria", "correlacao"):
        assert abs(ref[k] - 0.9) < 0.01, k
    for k in ("q25", "q50", "q75"):
        assert 0.9 <= ref[k] <= 0.97, k
    for k in ("media", "q50", "correlacao"):
        assert f[k] >= 0.87, k
    assert f["arvore"] >= 5 / 6 - 1e-9
    assert min(f.values()) >= 0.78
    assert np.mean(list(f.values())) >= 0.87
