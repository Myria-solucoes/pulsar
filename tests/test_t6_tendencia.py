"""T6: tendência hidrológica reconstruída igual ao QPAST.DAT público.

Proveniência: P-TEND-*, P-ART-01..03. Rodar com ``ambiente/py -m pytest``.
"""

from __future__ import annotations

import functools

import numpy as np
import pytest

from base import configuracao, deck
from conftest import deck as pacote_deck
from pulsar import tendencia as TD

import pacotes

DECKS = pacotes.selecionados()
ORIGINAIS = ("202609", "202610")


@functools.lru_cache(maxsize=None)
def calculada(nome, **kw):
    return TD.tendencia(deck(nome), configuracao(nome), TD.OpcoesTendencia(**kw))


def publico(nome) -> bytes:
    return pacote_deck(nome).arq("QPAST.DAT").read_bytes()


@pytest.mark.parametrize("nome", DECKS)
def test_qpast_byte_a_byte(nome):
    """T6: os 24 registros, todos os postos, todos os bits."""
    b = calculada(nome).bytes_qpast()
    p = publico(nome)
    assert len(b) == len(p)
    if b != p:
        a = np.frombuffer(b, "<f8").reshape(24, -1)
        q = np.frombuffer(p, "<f8").reshape(24, -1)
        dif = np.argwhere(a != q)
        pytest.fail(f"{len(dif)} valores diferentes, por exemplo (registro, posto) {[(int(r) + 1, int(c) + 1) for r, c in dif[:5]]}")


@pytest.mark.parametrize("nome", DECKS)
def test_pesos_do_mes_inicial(nome):
    """P-TEND-01: 202609 (set/2026, 5 semanas, 2 dias de outubro na última)
    pesa 4,7,7,7,5; 202610 (out/2026, 6 semanas, 6 dias de novembro) 2,7,7,7,7,1."""
    v = deck(nome).dadger.vazoes
    n = v.semanas_nao_observadas + v.semanas_observadas
    pesos = TD.pesos_semanais(v.ano_inicial, v.mes_inicial, n, v.dias_excluidos)
    if nome in ORIGINAIS:
        assert pesos == {"202609": [4, 7, 7, 7, 5], "202610": [2, 7, 7, 7, 7, 1]}[nome]
    # controle pelo calendário da biblioteca padrão: as semanas operativas
    # começam no sábado; a 1ª pega os dias do mês até a 1ª sexta, as do meio
    # 7 e a última 7 menos os dias excluídos; a soma é o número de dias
    # (fevereiro: 28 dias mesmo em ano bissexto, P-TEND-02)
    import calendar
    import datetime
    dias = 28 if v.mes_inicial == 2 else calendar.monthrange(v.ano_inicial, v.mes_inicial)[1]
    primeira = (4 - datetime.date(v.ano_inicial, v.mes_inicial, 1).weekday()) % 7 + 1  # dias até a sexta
    bissexto = v.mes_inicial == 2 and calendar.isleap(v.ano_inicial)
    assert pesos[0] == primeira - bissexto and pesos[-1] == 7 - v.dias_excluidos
    assert all(p == 7 for p in pesos[1:-1]) and sum(pesos) == dias


def test_pesos_calendario():
    """P-TEND-02: fevereiro tem 28 dias também em ano bissexto (padrão
    INFERIDO); com ``dias_fevereiro=None``, 29. Combinações que não cabem no
    mês são erro."""
    assert TD.pesos_semanais(2028, 2, 5, 3) == [3, 7, 7, 7, 4]
    assert TD.pesos_semanais(2028, 2, 5, 3, dias_fevereiro=None) == [4, 7, 7, 7, 4]
    assert TD.pesos_semanais(2024, 2, 5, 1) == [1, 7, 7, 7, 6]
    assert TD.pesos_semanais(2027, 2, 4, 0) == [7, 7, 7, 7]
    assert TD.pesos_semanais(2026, 9, 1, 0) == [30]
    with pytest.raises(Exception):
        TD.pesos_semanais(2026, 9, 3, 2)


@pytest.mark.parametrize("nome", DECKS)
def test_fevereiro_bissexto_com_28_dias(nome):
    """P-TEND-02 (lacuna L5): em fev/2024 (PMO e RV1–RV3) o mês inicial do
    QPAST só fecha com fevereiro de 28 dias, pesos (1, 7, 7, 7, 6): a 1ª
    semana (27/01 a 02/02) entra com 1 dia, não com os 2 do calendário. Com
    29 dias quase nenhum posto com PREVS fecha (só os de semanas iguais)."""
    import calendar
    d = deck(nome)
    v = d.dadger.vazoes
    if not (v.mes_inicial == 2 and calendar.isleap(v.ano_inicial)):
        pytest.skip("mês inicial não é fevereiro bissexto")
    q = np.frombuffer(publico(nome), "<f8").reshape(24, -1)[12 + 1]
    iguais = {dias: sum(calculada(nome, dias_fevereiro=dias).total[1][p - 1] == q[p - 1] for p in d.prevs)
              for dias in (28, None)}
    assert iguais[28] == len(d.prevs)
    assert iguais[None] < 0.05 * len(d.prevs), iguais


@pytest.mark.parametrize("nome", DECKS)
def test_media_divide_pelos_dias(nome):
    """P-TEND-03: soma peso × vazão / dias do mês reproduz os bits do mês
    inicial; multiplicar pelo inverso dos dias não reproduz."""
    d = deck(nome)
    v = d.dadger.vazoes
    q = np.frombuffer(publico(nome), "<f8").reshape(24, -1)
    n = v.semanas_nao_observadas + v.semanas_observadas
    pesos = TD.pesos_semanais(v.ano_inicial, v.mes_inicial, n, v.dias_excluidos)
    dm = sum(pesos)
    iguais_div = iguais_inv = 0
    for p, pr in d.prevs.items():
        alvo = q[12 + v.mes_inicial - 1, p - 1]
        iguais_div += TD.media_ponderada(pr.semanas, pesos) == alvo
        iguais_inv += sum(w * x for w, x in zip(pesos, pr.semanas)) * (1.0 / dm) == alvo
    assert iguais_div == len(d.prevs)
    assert iguais_inv < len(d.prevs)


@pytest.mark.parametrize("nome", DECKS)
def test_regras_leem_precisao_simples(nome):
    """P-ART-02: só a variante "leitura de VAZ(n) em simples, operações e
    resultado em dupla" reproduz os totais do QPAST. Valores diferentes do
    público (registros 13-24), separados em meses passados e artificiais do
    mês inicial:

    * "dupla": VAZ(n) lido em dupla (``leitura_regras=float``);
    * "simples": VAZ(n) em simples e, além disso, cada número, leitura e
      resultado intermediário arredondado a simples (``avaliar`` com
      ``arredondar=precisao_simples``, P-REG-04), resultado final em simples.
    """
    q = np.frombuffer(publico(nome), "<f8").reshape(24, -1)[12:]
    mi = deck(nome).dadger.vazoes.mes_inicial
    passados = [m for m in range(12) if m != mi - 1]
    art = [p - 1 for p in TD.postos_artificiais(configuracao(nome))]
    assert art and (nome not in ORIGINAIS or len(art) == 26)
    esperado = {
        ("202609", "dupla"): (38, 19), ("202610", "dupla"): (35, 18),
        ("202609", "simples"): (105, 12), ("202610", "simples"): (106, 12),
    }
    for rotulo, kw in (("dupla", {"leitura_regras": float}), ("simples", {"operacoes_regras": TD.precisao_simples})):
        t = calculada(nome, **kw).total
        obtido = (int(np.count_nonzero(t[passados] != q[passados])), int(np.count_nonzero(t[mi - 1, art] != q[mi - 1, art])))
        if nome in ORIGINAIS:
            assert obtido == esperado[(nome, rotulo)], rotulo
        else:
            assert sum(obtido) > 0, rotulo
    assert np.array_equal(calculada(nome).total, q)


@pytest.mark.parametrize("nome", DECKS)
def test_postos_com_regra_sem_nposnw_ficam_com_o_historico(nome):
    """P-ART-01: postos com regra que não são NPOSNW de usina (116, 119, 127,
    298, 315, 316) ficam com o valor fornecido no QPAST; com a regra, não."""
    d, c = deck(nome), configuracao(nome)
    alvos = set(TD.postos_artificiais(c))
    outros = sorted(d.regras.postos() - alvos)
    assert outros and (nome not in ORIGINAIS or {116, 119, 298}.issubset(outros))
    q = np.frombuffer(publico(nome), "<f8").reshape(24, -1)[12:]
    v = d.dadger.vazoes
    difere = 0
    for a, m in TD.meses_anteriores(v.mes_inicial, v.ano_inicial, 11):
        per = TD.periodo_historico(d, c, a, m)
        np.testing.assert_array_equal(q[m - 1, [p - 1 for p in outros]], per.fornecidos[[p - 1 for p in outros]])
        pela_regra = TD.calcular_artificiais(per.fornecidos, d.regras, m, outros)
        difere += sum(pela_regra[p] != q[m - 1, p - 1] for p in outros)
    assert difere > 0


@pytest.mark.parametrize("nome", DECKS)
def test_incremental_inclui_nw_a_montante(nome):
    """P-TEND-05: a incremental do QPAST desconta as usinas NW a montante
    (SALTO, posto 294, desconta ESTRELA, NW); sem descontar, difere."""
    c = configuracao(nome)
    t = calculada(nome)
    por = c.por_numero()
    salto = next(u for u in c.usinas if u.posto == 294)
    nw = [por[n] for n in c.montante(salto.numero) if por[n].status == "NW"]
    if not nw:
        pytest.skip("SALTO sem usina NW a montante nesta configuração")
    q = np.frombuffer(publico(nome), "<f8").reshape(24, -1)
    sem_nw = t.total[:, 293] - sum(t.total[:, por[n].posto - 1] for n in c.montante(salto.numero) if por[n].status != "NW")
    assert not np.array_equal(sem_nw, q[:12, 293])
    np.testing.assert_array_equal(t.incremental[:, 293], q[:12, 293])


def test_regra_com_posto_fora_do_historico_e_erro():
    """P-ART-06 (ESCOLHA): VAZ(n) com n fora de 1..NPOS é erro, não zero."""
    from pulsar.entradas.regras import Regra, Regras, analisar
    from pulsar.entradas.texto import ErroLeitura

    r = Regras([Regra(posto=5, mes=0, variante=0, texto="VAZ(321)+1", expressao=analisar("VAZ(321)+1"), linha=1)])
    with pytest.raises(ErroLeitura):
        TD.calcular_artificiais(np.zeros(320), r, 1, [5])
    r = Regras([Regra(posto=5, mes=0, variante=0, texto="VAZ(320)+1", expressao=analisar("VAZ(320)+1"), linha=1)])
    assert TD.calcular_artificiais(np.zeros(320), r, 1, [5]) == {5: 1.0}


def test_ano_do_estudo_das_regras_e_parametro():
    """P-ART-07 (ESCOLHA): a variante do bloco 2 é a do ano do estudo
    ``ano_estudo`` (padrão 1, em todas as semanas e meses passados)."""
    from pulsar.entradas.regras import Regra, Regras, analisar

    def regra(variante, texto):
        return Regra(posto=5, mes=0, variante=variante, texto=texto, expressao=analisar(texto), linha=1)

    r = Regras([regra(0, "VAZ(1)"), regra(1, "VAZ(1)*2")], variantes_por_ano={5: [1, 0]})
    v = np.zeros(320)
    v[0] = 10
    assert TD.calcular_artificiais(v, r, 3, [5]) == {5: 20.0}
    assert TD.calcular_artificiais(v, r, 3, [5], ano_estudo=2) == {5: 10.0}
    assert TD.OpcoesTendencia().ano_estudo_regras == 1


def test_postos_citados_nas_regras_publicas():
    """P-ART-06: nos REGRAS.DAT públicos (pacotes e coleção de decks do ONS) nenhuma
    regra cita posto acima de 320; o maior é 318."""
    import colecao_ons
    from pulsar.entradas.regras import ler_regras, postos_referenciados

    arquivos = [deck(n).diretorio / "REGRAS.DAT" for n in DECKS]
    n_pacotes = len(arquivos)
    if colecao_ons.disponivel():
        arquivos += [c.regras for c in colecao_ons.casos_gevazp() if c.regras is not None]
    maior, lidos = 0, 0
    for a in arquivos:
        try:
            r = ler_regras(a)
        except Exception:
            continue
        lidos += 1
        for g in r.regras:
            maior = max(maior, g.posto, *postos_referenciados(g.expressao), 0)
    assert maior == 318
    if colecao_ons.disponivel():
        assert lidos - n_pacotes == 504  # REGRAS.DAT da coleção de decks do ONS
