"""T8: totalização, postos laterais e postos artificiais (frente F6).

Duas entradas por transplante (03 §3):
- a partir do VAZTOTGD.DAT oficial: passos 4 a 6 da Figura 4.4 do M18
  (GEVAZP.OUT, vazoesta.out, vazoesia.out) byte a byte;
- a partir do GEVAZP.OUT oficial: os quatro arquivos iguais após o
  arredondamento final e os blocos mensais do VAZOES.RVx byte a byte.

O GEVAZP.OUT grava a incremental recalculada dos totais (F6-INC-01), não a
incremental gerada antes da totalização, que não é pública; por isso o
caminho a partir dele só fecha bit a bit em ~99% dos valores. A coluna das
usinas NW é nula no GEVAZP.OUT (F2-REL-02); a incremental delas é tirada do
VAZTOTGD.DAT (F6-TOT-05) e as colunas NW ficam fora da contagem bit a bit.
"""

from __future__ import annotations

import numpy as np
import pytest

import apoio
from base import COMPLETOS, DECKS, configuracao, deck
from pulsar import oraculos as O
from pulsar.configuracao import NEWAVE
from pulsar.empacotamento import montar_arvore, nint, serializar_vazoes_rvx
from pulsar.entradas.regras import analisar, postos_referenciados
from pulsar.totalizacao import (
    ErroRegra,
    OpcoesArtificiais,
    OpcoesTotalizacao,
    calcular_series,
    dados_defasagem,
    dias_do_estagio_estocastico,
    incrementais_de_totais,
    mes_e_ano_estocastico,
    serializar_series_arvore,
    series_dos_totais,
    soma_janela,
    totais_artificiais,
    totalizar,
    valores_artificiais,
)
from test_t9_empacotamento import deterministicos_do_vazdcp, palavras_por_bloco

NPOS = 320
NOMES = [n for n, _ in COMPLETOS]


def _oficiais(nome):
    p = DECKS / nome
    n = len(configuracao(nome).completa)
    return {
        "totais": O.ler_totais_gerados(p / "VAZTOTGD.DAT").valores[:, :n],
        "incrementais": O.ler_incrementais_geradas(p / "GEVAZP.OUT").valores[:, :n],
        "totais_artificiais": O.ler_totais_artificiais(p / "vazoesta.out").valores[:, :n],
        "incrementais_artificiais": O.ler_incrementais_artificiais(p / "vazoesia.out").valores[:, :n],
    }


ARQUIVO = {
    "totais": "VAZTOTGD.DAT",
    "incrementais": "GEVAZP.OUT",
    "totais_artificiais": "vazoesta.out",
    "incrementais_artificiais": "vazoesia.out",
}


def _mes(nome):
    return mes_e_ano_estocastico(deck(nome).dadger.vazoes.mes_inicial)


def _dos_totais(nome, **kw):
    mes, ano = _mes(nome)
    return series_dos_totais(_oficiais(nome)["totais"], configuracao(nome), deck(nome).regras, mes, ano, **kw)


# ------------------------------------------------- a partir do VAZTOTGD.DAT


@pytest.mark.parametrize("nome", NOMES)
def test_arquivos_dos_totais_byte_a_byte(nome):
    """F6-INC-01..03, F6-ART-01..04, F6-GRV-01: do VAZTOTGD.DAT oficial,
    GEVAZP.OUT, vazoesta.out e vazoesia.out iguais byte a byte, e o próprio
    VAZTOTGD.DAT regravado igual."""
    s = _dos_totais(nome)
    for campo, arq in ARQUIVO.items():
        oficial = (DECKS / nome / arq).read_bytes()
        assert serializar_series_arvore(getattr(s, campo), NPOS) == oficial, arq


@pytest.mark.parametrize("nome", NOMES)
def test_incremental_gravada_subtrai_na_ordem_da_configuracao(nome):
    """F6-INC-01 discrimina: outras ordens da subtração erram bits."""
    cfg = configuracao(nome)
    of = _oficiais(nome)
    tot, inc = of["totais"], of["incrementais"]
    idx = {u.numero: i for i, u in enumerate(cfg.completa)}
    erra_inversa = erra_soma = 0
    for i, u in enumerate(cfg.completa):
        mont = [idx[m] for m in cfg.montante(u.numero) if cfg.completa[idx[m]].status != NEWAVE] if u.status != "PL" else []
        if len(mont) < 2:
            continue
        s = tot[:, i].copy()
        for m in mont[::-1]:
            s = s - tot[:, m]
        erra_inversa += int((s != inc[:, i]).sum())
        soma = tot[:, mont[0]].copy()
        for m in mont[1:]:
            soma = soma + tot[:, m]
        erra_soma += int((tot[:, i] - soma != inc[:, i]).sum())
    assert erra_inversa > 100 and erra_soma > 100, (erra_inversa, erra_soma)


@pytest.mark.parametrize("nome", NOMES)
def test_nw_absorvida_no_gevazp_out_e_propria_no_vazoesia(nome):
    """F6-INC-02/03: trocar o tratamento das NW quebra os dois arquivos."""
    cfg = configuracao(nome)
    of = _oficiais(nome)
    nw = [i for i, u in enumerate(cfg.completa) if u.status == NEWAVE]
    if not nw:
        pytest.skip("configuração sem usina NW")
    inc_p = incrementais_de_totais(of["totais"], cfg, nw="propria")
    assert not (inc_p == of["incrementais"]).all(0)[nw].any()
    ia_a = incrementais_de_totais(of["totais_artificiais"], cfg, nw="absorve")
    assert not (ia_a == of["incrementais_artificiais"]).all(0)[nw].any()


def _colunas_artificiais(nome):
    return [i for i, u in enumerate(configuracao(nome).completa) if u.posto_artificial]


@pytest.mark.parametrize("nome", NOMES)
def test_precisao_das_regras(nome):
    """F6-ART-03 (lacuna L9): VAZ(n) em float32, operações em float64,
    resultado em float64. As variantes vizinhas erram colunas inteiras."""
    of = _oficiais(nome)["totais_artificiais"]
    cols = _colunas_artificiais(nome)
    originais = nome in ("202609", "202610")
    assert cols and (not originais or len(cols) == 26)
    f32 = lambda x: float(np.float32(x))

    def colunas_iguais(op):
        ta = _dos_totais(nome, opcoes_artificiais=op).totais_artificiais
        return int((ta == of).all(0)[cols].sum())

    assert colunas_iguais(OpcoesArtificiais()) == len(cols)
    em_64 = colunas_iguais(OpcoesArtificiais(ler_vaz=None))  # tudo em float64
    em_32 = colunas_iguais(OpcoesArtificiais(arredondar=f32))  # operações em float32
    assert em_64 < len(cols) and em_32 < len(cols)
    if originais:
        assert (em_64, em_32) == (6, 9)
    # artificiais referenciados por outra regra em float64 (só naturais em float32)
    mes, ano = _mes(nome)
    cfg = configuracao(nome)
    regras = deck(nome).regras
    tot = _oficiais(nome)["totais"]
    colunas = {u.posto: i for i, u in reversed(list(enumerate(cfg.completa)))}
    iguais, falham = 0, set()
    for i in cols:
        p = cfg.completa[i].posto_artificial
        v = np.array([_hibrido(tot[s], colunas, regras, mes, ano, p) for s in range(tot.shape[0])])
        if (v == of[:, i]).all():
            iguais += 1
        else:
            falham.add(p)
    # as que falham usam outro artificial (2026: 318, 126, 299, 131, 306, 303)
    com_artificial = {cfg.completa[i].posto_artificial for i in cols
                      if postos_referenciados(regras.regra(cfg.completa[i].posto_artificial, mes, ano).expressao)
                      & regras.postos()}
    assert falham and falham <= com_artificial
    if originais:
        assert iguais == 20 and falham == {318, 126, 299, 131, 306, 303}


def _hibrido(linha, colunas, regras, mes, ano, p):
    """Naturais lidos em float32, artificiais referenciados em float64."""
    from pulsar.entradas.regras import avaliar

    memo = {}
    postos = regras.postos()

    def vaz(q):
        if q in postos:
            if q not in memo:
                memo[q] = avaliar(regras.regra(q, mes, ano).expressao, vaz)
            return memo[q]
        return float(np.float32(linha[colunas[q]]))

    return vaz(p)


@pytest.mark.parametrize("nome", NOMES)
def test_regra_do_mes_estocastico(nome):
    """F6-ART-01: a regra mensal usada é a do mês estocástico; com o mês
    seguinte, HENRY BORDEN (posto 318, que depende do 119 mensal) erra."""
    cfg = configuracao(nome)
    mes, ano = _mes(nome)
    of = _oficiais(nome)
    i = next(i for i, u in enumerate(cfg.completa) if u.posto_artificial == 318)
    ta = totais_artificiais(of["totais"], cfg, deck(nome).regras, mes % 12 + 1, ano)
    assert not (ta[:, i] == of["totais_artificiais"][:, i]).any()
    # Controle: com o mês inicial (o do horizonte semanal) também erra.
    ta0 = totais_artificiais(of["totais"], cfg, deck(nome).regras, deck(nome).dadger.vazoes.mes_inicial, ano)
    cols = _colunas_artificiais(nome)
    assert not (ta0 == of["totais_artificiais"]).all(0)[cols].all()


# ------------------------------------------------- defasagem linear (eq. 4.21)


def _dias_do_mes_seguinte(mes, ano):
    """Calendário gregoriano da biblioteca padrão (controle independente)."""
    import calendar
    return calendar.monthrange(ano + (mes == 12), mes % 12 + 1)[1]


@pytest.mark.parametrize("nome", NOMES)
def test_defasagem_linear_de_sobradinho(nome):
    """F6-DEF-01..03: o total de SOBRADINHO menos a lateral é exatamente
    afim na soma dos totais de montante no mês, com inclinação 1-β,
    β = 15 dias / (dias do mês estocástico - dias excluídos), e intercepto
    β·ZT_mont(t-1), ZT_mont(t-1) = média dos totais semanais do PREVS
    (TRES MARIAS 156 + QUEIMADO 158) nos 15 dias anteriores ao estágio."""
    cfg = configuracao(nome)
    dk = deck(nome)
    v = dk.dadger.vazoes
    tot = _oficiais(nome)["totais"]
    idx = {u.numero: i for i, u in enumerate(cfg.completa)}
    y = tot[:, idx[169]] - tot[:, idx[168]]
    s = tot[:, idx[156]] + tot[:, idx[162]]
    (incl, inter), res, *_ = np.linalg.lstsq(np.vstack([s, np.ones_like(s)]).T, y, rcond=None)
    assert res[0] < 1e-20 * float(y @ y)  # afim, sem resíduo além do arredondamento
    ndmes = dias_do_estagio_estocastico(v.mes_inicial, v.ano_inicial, v.dias_excluidos)
    assert ndmes == _dias_do_mes_seguinte(v.mes_inicial, v.ano_inicial) - v.dias_excluidos  # 202609: 31 - 2
    beta = 15 / ndmes
    assert abs((1 - incl) - beta) < 1e-12
    anterior = (soma_janela(dk.prevs[156].semanas, 15) + soma_janela(dk.prevs[158].semanas, 15)) / 15
    assert abs(inter - beta * anterior) < 1e-9
    # Controle: β com o mês inteiro (sem descontar os dias excluídos) não
    # serve; sem dias excluídos as duas formas coincidem.
    if v.dias_excluidos:
        assert abs((1 - incl) - 15 / (ndmes + v.dias_excluidos)) > 1e-3


@pytest.mark.parametrize("nome", NOMES)
def test_total_defasado_a_menos_de_2_ulp(nome):
    """F6-DEF-05: a forma implementada fica a menos de 2 ulp do oficial em
    todos os cenários (a forma bit a bit é a lacuna L21)."""
    cfg = configuracao(nome)
    of = _oficiais(nome)
    tot = totalizar(of["incrementais"], cfg, dados_defasagem(deck(nome), cfg))
    i = next(i for i, u in enumerate(cfg.completa) if u.numero == 169)
    o = of["totais"][:, i]
    assert (np.abs(tot[:, i] - o) <= 2 * np.spacing(o)).all()
    iguais = int((tot[:, i] == o).sum())
    print(nome, "SOBRADINHO bit a bit:", iguais, "/", len(o))


def test_soma_janela():
    """F6-DEF-03/04: semanas de 7 dias contadas do fim."""
    assert soma_janela([192, 184, 195], 15) == 7 * 195 + 7 * 184 + 192
    with pytest.raises(NotImplementedError):  # F6-DEF-04: dia fracionário
        soma_janela([10, 20], 3.5)
    with pytest.raises(NotImplementedError):
        soma_janela([10, 20], 15)


# ------------------------------------------------- a partir do GEVAZP.OUT


def _transplante(nome):
    """Incrementais de entrada da totalização a partir do GEVAZP.OUT oficial.

    F6-TOT-05: a coluna NW do GEVAZP.OUT é nula e a incremental dela está
    somada na jusante (F2-REL-02); a incremental da NW sai do VAZTOTGD.DAT
    (total menos montantes) e é retirada da coluna da jusante."""
    cfg = configuracao(nome)
    of = _oficiais(nome)
    inc = of["incrementais"].copy()
    tot = of["totais"]
    idx = {u.numero: i for i, u in enumerate(cfg.completa)}
    for i, u in enumerate(cfg.completa):
        if u.status == NEWAVE:
            r = tot[:, i].copy()
            for m in cfg.montante(u.numero):
                r = r - tot[:, idx[m]]
            inc[:, i] = r
            if u.jusante in idx:  # JURUENA (NW de 2025) não tem jusante
                inc[:, idx[u.jusante]] -= r
    return inc


def _series_do_gevazp_out(nome, ordem="inversa"):
    cfg = configuracao(nome)
    mes, ano = _mes(nome)
    return calcular_series(
        _transplante(nome), cfg, deck(nome).regras, mes, ano,
        dados_defasagem(deck(nome), cfg), OpcoesTotalizacao(ordem=ordem),
    )


@pytest.mark.parametrize("nome", NOMES)
@pytest.mark.parametrize("ordem", ["inversa", "configuracao"])
def test_t8_do_gevazp_out_iguais_apos_arredondamento(nome, ordem):
    """T8: os quatro arquivos iguais ao oficial após o arredondamento final
    (NINT do VAZOES.RVx, F7-VZ-07, e 2 casas dos CSV/REL, U19 §9 v5.4.3)."""
    s = _series_do_gevazp_out(nome, ordem)
    cfg = configuracao(nome)
    nw = [i for i, u in enumerate(cfg.completa) if u.status == NEWAVE]
    for campo, of in _oficiais(nome).items():
        meu = getattr(s, campo)
        assert (nint(meu) == nint(of)).all(), campo
        assert (np.round(meu, 2) == np.round(of, 2)).all(), campo
        assert np.abs(meu - of).max() < 1e-11, campo
        sem_nw = np.delete(meu == of, nw if campo == "totais" else [], axis=1)
        print(nome, ordem, ARQUIVO[campo], "bit a bit:", int(sem_nw.sum()), "/", sem_nw.size)


@pytest.mark.parametrize("nome", NOMES)
def test_t8_blocos_mensais_do_vazoes_rvx(nome):
    """T8: com o GEVAZP.OUT e o vazoesia.out calculados (a partir do
    GEVAZP.OUT oficial), os blocos 6 e 8 do VAZOES.RVx ficam iguais
    byte a byte e o arquivo inteiro também."""
    s = _series_do_gevazp_out(nome)
    d = deck(nome)
    rev = d.lista_decomp.dadger.split(".")[-1].upper()
    a = montar_arvore(
        configuracao(nome), d.dadger.vazoes, d.n_postos,
        s.incrementais, s.incrementais_artificiais,
        O.ler_probvaz(DECKS / nome / "PROBVAZ.DAT"),
        deterministicos_do_vazdcp(DECKS / nome / "VAZDCP.REL"), NPOS,
        apoio.opcoes_empacotamento(nome, rev),
    )
    gerado = serializar_vazoes_rvx(a)
    oficial = (DECKS / nome / f"VAZOES.{rev}").read_bytes()
    c = palavras_por_bloco(gerado, oficial, a)
    print(nome, rev, c)
    assert c["gerada_mensal"][0] == c["gerada_mensal"][1]
    assert c["gerada_mensal_ena"][0] == c["gerada_mensal_ena"][1]
    assert gerado == oficial


# ------------------------------------------------- unidades


def _cfg_mini():
    from pulsar.configuracao import Configuracao, UsinaConfig

    u = [
        UsinaConfig(numero=1, nome=b"A", posto=1, jusante=3, bacia=1),
        UsinaConfig(numero=2, nome=b"B", posto=2, jusante=3, bacia=1, status=NEWAVE),
        UsinaConfig(numero=3, nome=b"C", posto=3, jusante=4, bacia=1),
        UsinaConfig(numero=4, nome=b"D", posto=300, jusante=0, bacia=1, status="PN", posto_artificial=40),
    ]
    return Configuracao(usinas=u)


def test_totalizar_cascata_nw_e_pn():
    """F6-TOT-01/02: NW entra na jusante; PN tem incremental nula."""
    cfg = _cfg_mini()
    inc = np.array([[1.0, 2.0, 4.0, 99.0]])
    tot = totalizar(inc, cfg)
    assert tot.tolist() == [[1.0, 2.0, 7.0, 7.0]]
    assert totalizar(inc, cfg, opcoes=OpcoesTotalizacao(zerar_pn=False)).tolist() == [[1.0, 2.0, 7.0, 106.0]]
    assert incrementais_de_totais(tot, cfg, "absorve").tolist() == [[1.0, 0.0, 6.0, 0.0]]
    assert incrementais_de_totais(tot, cfg, "propria").tolist() == [[1.0, 2.0, 4.0, 0.0]]


def test_lateral_sem_defasagem_usa_a_cascata():
    """F6-DEF-01: com defasagem = 1 (não usa), a usina com posto lateral
    soma a sua incremental aos totais de montante (alternativa (i))."""
    from dataclasses import replace

    from pulsar.configuracao import LATERAL, Configuracao, UsinaConfig

    a = UsinaConfig(numero=1, nome=b"A", posto=1, jusante=2, bacia=1, tempo_viagem=360)
    b = UsinaConfig(numero=2, nome=b"B", posto=2, jusante=0, bacia=1, posto_lateral=5, defasagem=1)
    lat = replace(b, numero=5, posto=5, status=LATERAL, posto_lateral=0, origem_lateral=2)
    cfg = Configuracao(usinas=[a, b], laterais=[lat])
    inc = np.array([[10.0, 3.0, 1.0]])
    assert totalizar(inc, cfg).tolist() == [[10.0, 13.0, 1.0]]
    cfg2 = Configuracao(usinas=[a, replace(b, defasagem=2)], laterais=[lat])
    with pytest.raises(ValueError):
        totalizar(inc, cfg2)


def _regras(*linhas):
    from pulsar.entradas.regras import Regra, Regras

    return Regras([Regra(p, m, 0, t, analisar(t), 0) for p, m, t in linhas])


def test_avaliador_dependencias_e_erros():
    """F6-ART-01: todas as regras, em ordem de dependência; ciclo, regra
    ausente no mês e posto inexistente interrompem."""
    nat = {1: 10.0, 2: 0.1}.__getitem__
    r = _regras((40, 0, "VAZ(41)+VAZ(1)"), (41, 0, "VAZ(2)*3"), (42, 5, "VAZ(1)"))
    with pytest.raises(ErroRegra, match="sem regra"):
        valores_artificiais(nat, r, 1)
    v = valores_artificiais(nat, r, 5)
    f32 = float(np.float32(0.1))
    assert v[41] == f32 * 3 and v[40] == float(np.float32(f32 * 3)) + 10.0 and v[42] == 10.0
    with pytest.raises(ErroRegra, match="circular"):
        valores_artificiais(nat, _regras((40, 0, "VAZ(41)"), (41, 0, "VAZ(40)+1")), 1)
    with pytest.raises(ErroRegra, match="posto 7"):
        valores_artificiais(nat, _regras((40, 0, "VAZ(7)")), 1)


def test_posto_repetido():
    """F6-ART-05: VAZ de posto de duas usinas com valores diferentes."""
    from pulsar.configuracao import Configuracao, UsinaConfig

    cfg = Configuracao(usinas=[
        UsinaConfig(numero=1, nome=b"A", posto=300, jusante=0, bacia=1),
        UsinaConfig(numero=2, nome=b"B", posto=300, jusante=0, bacia=1),
        UsinaConfig(numero=3, nome=b"C", posto=3, jusante=0, bacia=1, posto_artificial=40),
    ])
    r = _regras((40, 0, "VAZ(300)"))
    tot = np.array([[1.0, 2.0, 5.0]])
    with pytest.raises(ErroRegra):
        totais_artificiais(tot, cfg, r, 1)
    op = OpcoesArtificiais(posto_repetido="primeiro")
    assert totais_artificiais(tot, cfg, r, 1, opcoes=op).tolist() == [[1.0, 2.0, 1.0]]


def test_numero_da_regra_que_e_posto_natural():
    """F6-ART-06: VAZ(n) com n de regra e de usina, nas três opções."""
    nat = {1: 10.0, 40: 7.0}
    def vn(p):
        return nat[p]
    r = _regras((40, 0, "VAZ(1)*2"), (41, 0, "VAZ(40)+1"))
    assert valores_artificiais(vn, r, 1)[41] == 21.0
    assert valores_artificiais(vn, r, 1, opcoes=OpcoesArtificiais(numero_repetido="natural"))[41] == 8.0
    with pytest.raises(ErroRegra):
        valores_artificiais(vn, r, 1, opcoes=OpcoesArtificiais(numero_repetido="erro"))
    with pytest.raises(ValueError):
        OpcoesArtificiais(numero_repetido="x")


@pytest.mark.parametrize("nome", NOMES)
def test_dias_do_estagio_parametrizavel(nome):
    """F6-DEF-06: ndmes do calendário ou fornecido; sem ano, erro explícito."""
    from dataclasses import replace

    cfg = configuracao(nome)
    dk = deck(nome)
    v = dk.dadger.vazoes
    assert dados_defasagem(dk, cfg)[169][0].dias_estagio == _dias_do_mes_seguinte(v.mes_inicial, v.ano_inicial) - v.dias_excluidos
    assert dados_defasagem(dk, cfg, dias_estagio=20)[169][0].dias_estagio == 20
    sem_ano = replace(dk, dadger=replace(dk.dadger, vazoes=replace(dk.dadger.vazoes, ano_inicial=None, ano_inicial_estudo=None)))
    with pytest.raises(ValueError):
        dados_defasagem(sem_ano, cfg)
    assert dias_do_estagio_estocastico(12, 2023, 0) == 31  # janeiro do ano seguinte
    assert dias_do_estagio_estocastico(1, 2024, 3) == 29 - 3  # fevereiro bissexto


def test_mes_e_ano_estocastico():
    assert mes_e_ano_estocastico(9) == (10, 1)
    assert mes_e_ano_estocastico(12) == (1, 2)
