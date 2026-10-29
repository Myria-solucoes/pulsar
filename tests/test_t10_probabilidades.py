"""T10: probabilidades, saídas no layout público e entrega à F7 (P-AGR-03,
P-GER-06, P-GER-07, P-RUI-02).

Usa as agregações em cache de tests/apoio_f8.py (ferramentas/sementes_f8.py
preenche o cache; sem ele cada semente leva ~2 min).
"""

import numpy as np

import apoio
import apoio_f8
import base
from pulsar.empacotamento.vazoes_rvx import serializar_vazoes_rvx
from pulsar.estocastico.geracao import gravar, montar_vazoes
from pulsar.oraculos import ler_incrementais_geradas, ler_probvaz
from test_t9_empacotamento import palavras_por_bloco


def test_numero_de_grupos_e_denominador(pacote):
    """K = aberturas do período estocástico (P-AGR-01) e probabilidades =
    contagem/50 000 em float32 (P-AGR-03, P-RUI-02), como no PROBVAZ.DAT."""
    k = base.deck(pacote.nome).dadger.vazoes.aberturas[0]
    _, p, r = apoio_f8.arvore(pacote.nome, 1)
    assert len(p) == k == len(apoio.probvaz(pacote.nome))
    assert r.agregacao.contagens.sum() == 50_000 and r.agregacao.n_objetos == 50_000
    assert p.dtype == np.float32 and np.array_equal(p, (r.agregacao.contagens / 50_000).astype(np.float32))


def test_distribuicao_dos_tamanhos_de_grupo(pacote):
    """T10 (03 §4): mínimo, máximo e desvio das contagens dos grupos
    oficiais (contagem = probabilidade × 50 000) contra a faixa [mín, máx]
    das 20 sementes (P-ACE-06), com o lateral fora (padrão, P-AGR-07) e
    dentro do vetor agregado. Com um gerador idêntico ao oficial, cada
    estatística cai fora da faixa com probabilidade 2/21; o critério é no
    máximo uma das três fora (P-ACE-08 (a), lacuna L24; até a F11, as três
    dentro com folga de 1 contagem). As duas formas passam e não se separam: sem o
    lateral, só o menor grupo oficial do 202609 (168) fica fora (acima da
    faixa 156–166); com ele, o desvio oficial fica abaixo da faixa nos dois
    decks (10,32 contra 10,53–11,96 e 11,68 contra 11,74–13,04)."""
    of = np.rint(np.asarray(apoio.probvaz(pacote.nome), float) * 50_000).astype(int)
    assert of.sum() == 50_000
    for lateral in (False, True):
        sem = [apoio_f8.agregacao(pacote.nome, s, lateral=lateral).contagens for s in apoio_f8.SEMENTES]
        fora = []
        for f in (np.min, np.max, np.std):
            v = np.array([f(c) for c in sem])
            if not v.min() <= f(of) <= v.max():
                fora.append((f.__name__, f(of), v.min(), v.max()))
        print(pacote.nome, "com" if lateral else "sem", "lateral: fora da faixa", fora)
        assert len(fora) <= 1, (lateral, fora)


def test_saidas_no_layout_publico(pacote, tmp_path):
    """P-GER-06: GEVAZP.OUT, VAZTOTGD.DAT, vazoesta.out, vazoesia.out e
    PROBVAZ.DAT com o tamanho dos públicos e legíveis pelos oráculos da F2."""
    _, _, r = apoio_f8.arvore(pacote.nome, 1)
    gravar(tmp_path, r, 320)
    for nome in ("GEVAZP.OUT", "VAZTOTGD.DAT", "vazoesta.out", "vazoesia.out", "PROBVAZ.DAT"):
        assert (tmp_path / nome).stat().st_size == apoio.deck(pacote.nome).arq(nome).stat().st_size, nome
    g = ler_incrementais_geradas(tmp_path / "GEVAZP.OUT").valores
    assert np.array_equal(g[:, : r.totalizadas.incrementais.shape[1]], r.totalizadas.incrementais)
    assert np.array_equal(ler_probvaz(tmp_path / "PROBVAZ.DAT"), r.probabilidades)
    # usinas sem dispersão no oficial (PN, NW absorvidas, nulas) também são constantes aqui
    of = apoio.gevazp_out(pacote.nome).valores[:, : g.shape[1]]
    assert np.array_equal(of.std(0) == 0, g[:, : of.shape[1]].std(0) == 0)


def test_vazoes_rvx_ponta_a_ponta(pacote):
    """P-GER-07: a F7 grava o VAZOES.RVx com esta geração; os registros
    1–3 e os blocos determinísticos (F5) são iguais byte a byte aos do
    pacote, e os blocos gerados e as probabilidades das folhas diferem (a
    parte estocástica é avaliada no T11)."""
    nome = pacote.nome
    d, cfg = base.deck(nome), base.configuracao(nome)
    _, _, r = apoio_f8.arvore(nome, 1)
    a = montar_vazoes(d, cfg, r, 320, apoio.opcoes_empacotamento(pacote.nome))
    gerado = serializar_vazoes_rvx(a)
    oficial = pacote.vazoes.read_bytes()
    assert len(gerado) == len(oficial)
    blocos = palavras_por_bloco(gerado, oficial, a)
    print(nome, {k: f"{i}/{t}" for k, (i, t) in blocos.items()})
    for k in ("registro 1", "registro 2", "registro 3", "prevista_semanal", "prevista_semanal_ena",
              "observada_mensal", "observada_semanal"):
        assert blocos[k][0] == blocos[k][1], k
    for k in ("gerada_mensal", "gerada_mensal_ena"):
        assert blocos[k][0] < blocos[k][1]


def test_cache_igual_ao_recalculo():
    """O cache de tests/apoio_f8.py não está obsoleto: a agregação do 202609
    com a semente 1, refeita do zero (~3 min), tem contagens, centroides e
    iterações bit a bit iguais às gravadas em cache/f8/."""
    from pulsar.estocastico.agregacao import OpcoesAgregacao, agregar

    c = apoio_f8.agregacao("202609", 1)
    pr = apoio_f8.preparo("202609")
    n = agregar(pr.postos, pr.k, 1, OpcoesAgregacao())
    assert n.postos == c.postos and n.iteracoes == c.iteracoes
    assert np.array_equal(n.contagens, c.contagens) and np.array_equal(n.centroides, c.centroides)
