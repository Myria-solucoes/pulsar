"""T7: registros determinísticos do VAZOES.RVx iguais byte a byte em todas
as revisões dos pacotes (202609 RV0 e RV1, 202610 RV0).

O gravador não lê o VAZOES.RVx; o arquivo público só é aberto aqui, para a
comparação. As fatias são localizadas pelo leitor da F2 (F2-VZ-01..10).
Proveniência: P-VZD-*, P-INC-*, P-ART-*. Rodar com ``ambiente/py -m pytest``.
"""

from __future__ import annotations

import functools
from dataclasses import replace

import numpy as np
import pytest

from base import DECKS
from pulsar import tendencia as TD
from pulsar import vazoes_deterministicos as VD
from pulsar.configuracao import montar_configuracao
from pulsar.entradas import ler_deck
from pulsar.oraculos import ler_vazoes_decomp


def _revisoes():
    out = []
    for d in sorted(DECKS.iterdir()) if DECKS.is_dir() else []:
        for v in sorted(d.glob("VAZOES.RV*")):
            out.append((d.name, v.suffix[1:].upper()))
    return out


REVISOES = _revisoes()


@functools.lru_cache(maxsize=None)
def entrada(nome, rv):
    d = ler_deck(DECKS / nome, dadger=f"DADGER.{rv}")
    return d, montar_configuracao(d)


@functools.lru_cache(maxsize=None)
def montado(nome, rv, opcoes=None):
    d, c = entrada(nome, rv)
    return VD.montar_registros(d, c, opcoes)


@functools.lru_cache(maxsize=None)
def publico(nome, rv):
    caminho = DECKS / nome / f"VAZOES.{rv}"
    return caminho.read_bytes(), ler_vazoes_decomp(caminho)


def fatias(nome, rv):
    """{bloco: bytes do arquivo público} para os blocos determinísticos."""
    dados, vz = publico(nome, rv)
    R = 4 * vz.npos
    p = vz.primeiro_registro
    n_prev, n_obs_m, n_obs_s = vz.prevista_semanal.shape[0], vz.observada_mensal.shape[0], vz.observada_semanal.shape[0]

    def regs(primeiro, n):
        return dados[(primeiro - 1) * R : (primeiro - 1 + n) * R]

    return {
        "cabecalho": dados[: 3 * R],
        "probabilidades_semanais": dados[3 * R : 3 * R + 4 * (vz.n_estagios - 1)],
        "prevista_semanal": regs(p["prevista_semanal"], n_prev),
        "prevista_semanal_ena": regs(p["prevista_semanal_ena"], n_prev),
        "observada_mensal": regs(p["observada_mensal"], n_obs_m),
        "observada_semanal": regs(p["observada_semanal"], n_obs_s),
    }


def construidos(r: VD.RegistrosDeterministicos):
    return {
        "cabecalho": r.bytes_cabecalho(),
        "probabilidades_semanais": r.probabilidades_semanais.astype("<f4").tobytes(),
        "prevista_semanal": r.bytes_prevista_semanal(),
        "prevista_semanal_ena": r.bytes_prevista_semanal_ena(),
        "observada_mensal": r.bytes_observada_mensal(),
        "observada_semanal": r.bytes_observada_semanal(),
    }


def palavras_diferentes(a: bytes, b: bytes) -> int:
    if len(a) != len(b):
        return -1
    return int(np.count_nonzero(np.frombuffer(a, "<i4") != np.frombuffer(b, "<i4")))


@pytest.mark.parametrize("nome,rv", REVISOES)
@pytest.mark.parametrize(
    "bloco",
    ["cabecalho", "probabilidades_semanais", "prevista_semanal", "prevista_semanal_ena", "observada_mensal", "observada_semanal"],
)
def test_bloco_byte_a_byte(nome, rv, bloco):
    a = construidos(montado(nome, rv))[bloco]
    b = fatias(nome, rv)[bloco]
    assert len(a) == len(b), (len(a), len(b))
    assert a == b, f"{palavras_diferentes(a, b)} palavras diferentes de {len(b) // 4}"


def test_cobre_todas_as_revisoes():
    assert ("202609", "RV0") in REVISOES and ("202609", "RV1") in REVISOES and ("202610", "RV0") in REVISOES


@pytest.mark.parametrize("nome,rv", REVISOES)
def test_contagem_de_registros(nome, rv):
    """Semanas previstas = não observadas, observadas = reg. 7 do & VAZOES,
    meses observados = 11 (P-TEND-07, ordem máxima 11 nos dois decks)."""
    r = montado(nome, rv)
    _, vz = publico(nome, rv)
    assert r.prevista_semanal.shape == vz.prevista_semanal.shape
    assert r.observada_semanal.shape == vz.observada_semanal.shape
    assert r.observada_mensal.shape[0] == len(vz.meses_observados) == 11
    assert [m for _, m in r.meses_observados] == list(vz.meses_observados)


@pytest.mark.parametrize("nome,rv", REVISOES)
def test_sem_arredondar_totais_falha(nome, rv):
    """P-ART-03: sem arredondar os totais antes das incrementais (NINT só no
    fim), SLT.SANTIAGO (coluna 77, a jusante do artificial 75 com total de
    fração .5) fica com x,5 e sobe uma unidade: uma palavra errada por
    semana (blocos 7 e 10) e em 3 meses observados (bloco 9). No bloco
    natural (5) a variante não muda nada (o PREVS é inteiro)."""
    d, c = entrada(nome, rv)
    sem_arred = lambda x: x
    n = d.n_postos
    _, vz = publico(nome, rv)
    sem = TD.periodos_semanais(d, c)
    ena = np.array([[TD.nint(x) for x in TD.incrementais_ena(p, c, n, sem_arred)] for p in sem])
    pub = np.concatenate([vz.observada_semanal, vz.prevista_semanal_ena])
    dif = np.argwhere(ena != pub)
    assert [int(k) for k in dif[:, 1]] == [76] * len(sem) and len({int(k) for k in dif[:, 0]}) == len(sem)
    r = montado(nome, rv)
    meses = [TD.periodo_historico(d, c, a, m) for a, m in r.meses_observados]
    obs = np.array([[TD.nint(x) for x in TD.incrementais_ena(p, c, n, sem_arred)] for p in meses])
    dif = np.argwhere(obs != vz.observada_mensal)
    assert len(dif) == 3 and set(int(k) for k in dif[:, 1]) == {76}
    nobs = vz.observada_semanal.shape[0]
    nat = np.array([[TD.nint(x) for x in TD.incrementais_naturais(p, c, n, sem_arred)] for p in sem[nobs:]])
    assert np.array_equal(nat, vz.prevista_semanal)


def test_nw_fora_da_natural_e_dentro_da_ena():
    """P-INC-02 e P-INC-04 (202609 RV1, semana 2): FOZ DO PRATA (NW, posto 96)
    tem natural 0 e ENA 115 = total; MONTE CLARO (posto 97) desconta a NW só
    na ENA (natural 133, ENA 18), como na tabela de previsões do GEVAZP.REL."""
    r = montado("202609", "RV1")
    assert r.prevista_semanal[0, 95] == 0 and r.prevista_semanal_ena[0, 95] == 115
    assert r.prevista_semanal[0, 96] == 133 and r.prevista_semanal_ena[0, 96] == 18


def test_ultima_semana_usa_regra_do_mes_inicial():
    """P-ART-05: na última semana de set/2026 (26/09 a 02/10) PIMENTAL tem
    703 m3/s; a regra de setembro do posto 292 (limiar 750) dá ENA 703 na
    coluna 302 e a de outubro (limiar 700) daria 700."""
    d, c = entrada("202609", "RV1")
    sem = TD.periodos_semanais(d, c)
    ult = sem[-1]
    assert ult.fornecidos[287] == 703
    r = montado("202609", "RV1")
    assert r.prevista_semanal_ena[-1, 301] == 703
    outubro = replace(ult, mes_regra=10, artificiais=TD.calcular_artificiais(ult.fornecidos, d.regras, 10, TD.postos_artificiais(c)))
    assert TD.incrementais_ena(outubro, c, d.n_postos)[301] == 700


def test_lateral_recebe_o_proprio_total():
    """P-INC-03: coluna 168 (SOBRADINHO_L) = PREVS do posto 168 (453 na
    semana 1 de 202609 RV1, observada)."""
    r = montado("202609", "RV1")
    assert r.observada_semanal[0, 167] == 453


def test_posto_300_nulo_salvo_com_nposnw():
    """P-ART-04 (U19 Anexo B): coluna 300 nula; HENRY BORDEN (posto 300,
    NPOSNW 318) tem ENA pela regra na coluna 318."""
    r = montado("202609", "RV1")
    assert not r.prevista_semanal[:, 299].any() and not r.prevista_semanal_ena[:, 299].any()
    assert r.prevista_semanal_ena[:, 317].all()


def test_regra_aninhada_recalcula_posto_com_valor_fornecido():
    """P-ART-01: na semana 1 de 202609 RV1 o artificial 318 (HENRY BORDEN)
    usa VAZ(116), e o 116 tem regra (VAZ(119)-VAZ(301)) e valor no PREVS (7).
    Com a regra recalculada o total é 76,67 e a ENA gravada é 77; com o
    valor do PREVS seria 76,2 e a ENA 76."""
    from pulsar.entradas.regras import Regras

    d, c = entrada("202609", "RV1")
    sem = TD.periodos_semanais(d, c)[0]
    assert sem.fornecidos[115] == 7
    r = montado("202609", "RV1")
    assert r.observada_semanal[0, 317] == 77
    sem_116 = Regras([g for g in d.regras.regras if g.posto not in (116, 119)], d.regras.variantes_por_ano)
    t = TD.calcular_artificiais(sem.fornecidos, sem_116, sem.mes_regra, [318])[318]
    assert TD.nint(t) == 76 and abs(sem.total(318) - 76.668) < 1e-3


@pytest.mark.parametrize("nome,rv", [("202609", "RV1"), ("202610", "RV0")])
def test_integracao_com_o_gravador_da_f7(nome, rv):
    """Os blocos 5, 7, 9 e 10 da F5, com as séries geradas e as
    probabilidades oficiais transplantadas (03 §3), passam pelo gravador da
    F7 e dão o VAZOES.RVx público inteiro, byte a byte; os registros 1-3 da
    F5 são iguais aos da F7. Só a revisão executada tem GEVAZP.OUT."""
    from pulsar import oraculos as O
    from pulsar.empacotamento import montar_arvore, serializar_vazoes_rvx

    d, c = entrada(nome, rv)
    pasta = DECKS / nome
    r = montado(nome, rv)
    a = montar_arvore(
        c, d.dadger.vazoes, d.n_postos,
        O.ler_incrementais_geradas(pasta / "GEVAZP.OUT").valores,
        O.ler_incrementais_artificiais(pasta / "vazoesia.out").valores,
        O.ler_probvaz(pasta / "PROBVAZ.DAT"),
        r, d.n_postos,
    )
    gravado = serializar_vazoes_rvx(a)
    dados, _ = publico(nome, rv)
    assert gravado[: 3 * 4 * d.n_postos] == r.bytes_cabecalho()
    assert gravado == dados
