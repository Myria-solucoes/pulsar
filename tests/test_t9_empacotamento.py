"""T9: empacotamento do VAZOES.RVx e do PROBVAZ.DAT (frente F7).

Entradas do gravador, por pacote completo (a revisão executada):
- configuração da F1 (DADGER + HIDR + MODIF) e bloco & VAZOES do DADGER;
- GEVAZP.OUT, vazoesia.out e PROBVAZ.DAT oficiais (transplante, 03 §3);
- registros determinísticos (blocos 5, 7, 9, 10). A F5, que os produz
  (T7), ainda não foi integrada; até lá eles são transplantados do espelho
  em texto VAZDCP.REL, como as séries geradas são transplantadas do
  GEVAZP.OUT. O gravador em si não lê VAZOES.RVx nem VAZDCP.REL
  (test_gravador_nao_le_vazoes_existente).

Critério: igual byte a byte ao VAZOES.RVx público (03 §4, T9).
"""

from __future__ import annotations

import re
import subprocess
import sys

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

import apoio
import colecao_ons
from base import COMPLETOS, DECKS, RAIZ, configuracao, deck
from pulsar import oraculos as O
from pulsar.empacotamento import (
    OpcoesEmpacotamento,
    RegistrosDeterministicos,
    codificar_versao,
    montar_arvore,
    nint,
    probabilidades_de_contagens,
    serializar_probvaz,
    serializar_vazoes_rvx,
)
from pulsar.oraculos import texto as T

NPOS = 320
RECL = NPOS * 4

# Famílias de títulos do VAZDCP.REL -> bloco (ordem: o mais longo primeiro).
_FAMILIAS = [
    ("VAZAO PREVISTA INCREMENTAL PARA CALCULO DA ENA SEMANA", "prevista_semanal_ena"),
    ("VAZAO PREVISTA INCREMENTAL SEMANA", "prevista_semanal"),
    ("VAZAO INCREMENTAL OBSERVADA MES", "observada_mensal"),
    ("VAZAO INCREMENTAL OBSERVADA SEMANA", "observada_semanal"),
]


def deterministicos_do_vazdcp(caminho) -> RegistrosDeterministicos:
    """Transplante dos blocos determinísticos a partir do VAZDCP.REL."""
    if not Path(caminho).is_file():  # nenhum dos 61 pacotes está sem ele
        pytest.skip(f"{caminho}: pacote sem VAZDCP.REL")
    blocos: dict[str, list[list[float]]] = {nome: [] for _, nome in _FAMILIAS}
    for r in T.ler_vazdcp(caminho):
        for prefixo, nome in _FAMILIAS:
            if r.titulo.startswith(prefixo):
                assert len(r.valores) == NPOS, (r.numero, len(r.valores))
                blocos[nome].append(r.valores)
                break

    def m(nome):
        v = np.array(blocos[nome], dtype=np.float64).reshape(-1, NPOS)
        assert (v == np.round(v)).all()
        return v.astype(np.int64)

    return RegistrosDeterministicos(**{nome: m(nome) for _, nome in _FAMILIAS})


def _revisao(nome, dadger):
    d = deck(nome, dadger)
    return d, d.dadger.vazoes, (dadger or d.lista_decomp.dadger).split(".")[-1].upper()


def arvore_do_pacote(nome, dadger=None, opcoes=None):
    d, v, rev = _revisao(nome, dadger)
    if opcoes is None:
        opcoes = apoio.opcoes_empacotamento(nome, rev)
    pasta = DECKS / nome
    return montar_arvore(
        configuracao(nome, dadger),
        v,
        d.n_postos,
        O.ler_incrementais_geradas(pasta / "GEVAZP.OUT").valores,
        O.ler_incrementais_artificiais(pasta / "vazoesia.out").valores,
        O.ler_probvaz(pasta / "PROBVAZ.DAT"),
        deterministicos_do_vazdcp(pasta / "VAZDCP.REL"),
        NPOS,
        opcoes,
    )


def palavras_por_bloco(gerado: bytes, oficial: bytes, a) -> dict[str, tuple[int, int]]:
    """(palavras iguais, palavras totais) por bloco, pelas fronteiras da árvore gravada."""
    nnos = len(a.probabilidades)
    tam = [("registro 1", 1), ("registro 2", 1), ("registro 3", 1), ("probabilidades", -(-nnos // NPOS))]
    tam += [(n, len(getattr(a, n))) for n in ("prevista_semanal", "gerada_mensal", "prevista_semanal_ena",
                                               "gerada_mensal_ena", "observada_mensal", "observada_semanal")]
    g = np.frombuffer(gerado, "<u4")
    o = np.frombuffer(oficial, "<u4")
    out, k = {}, 0
    for nome, n in tam:
        a_, b_ = g[k * NPOS:(k + n) * NPOS], o[k * NPOS:(k + n) * NPOS]
        out[nome] = (int((a_ == b_).sum()) if len(a_) == len(b_) else 0, n * NPOS)
        k += n
    return out


@pytest.mark.parametrize("nome,dadger", COMPLETOS)
def test_vazoes_rvx_byte_a_byte(nome, dadger):
    _, _, rev = _revisao(nome, dadger)
    a = arvore_do_pacote(nome, dadger)
    gerado = serializar_vazoes_rvx(a)
    oficial = (DECKS / nome / f"VAZOES.{rev}").read_bytes()
    contagem = palavras_por_bloco(gerado, oficial, a)
    print(nome, rev, contagem)
    assert len(gerado) == len(oficial)
    assert all(i == t for i, t in contagem.values()), contagem
    assert gerado == oficial


@pytest.mark.parametrize("nome,dadger", COMPLETOS)
def test_probvaz_byte_a_byte_a_partir_das_contagens(nome, dadger):
    """F7-PB-02: as folhas são contagem/50000 (F2-PB-04) em float32."""
    oficial = (DECKS / nome / "PROBVAZ.DAT").read_bytes()
    folhas = O.ler_probvaz(DECKS / nome / "PROBVAZ.DAT")
    contagens = np.rint(folhas.astype(np.float64) * 50000).astype(np.int64)
    p = probabilidades_de_contagens(contagens, 50000)
    assert serializar_probvaz(p, NPOS) == oficial
    # Variantes enumeradas (03 §3): divisão em float32 dá os mesmos bits;
    # multiplicação pelo inverso em float32 não.
    div32 = contagens.astype(np.float32) / np.float32(50000)
    assert serializar_probvaz(div32, NPOS) == oficial
    mul32 = contagens.astype(np.float32) * np.float32(1 / 50000)
    assert serializar_probvaz(mul32, NPOS) != oficial


def test_probvaz_varios_registros():
    """U19 §5.4: NNOT > NPOS ocupa ceil(NNOT/NPOS) registros, zeros no fim."""
    p = np.arange(1, 2 * NPOS + 6, dtype=np.float32)
    b = serializar_probvaz(p, NPOS)
    assert len(b) == 3 * RECL
    v = np.frombuffer(b, "<f4")
    assert (v[: len(p)] == p).all() and not v[len(p):].any()


@pytest.mark.parametrize("nome,dadger", COMPLETOS + [("202609", "DADGER.RV0")])
def test_registros_1_a_3_de_todas_as_revisoes(nome, dadger):
    """Cabeçalho, códigos e calendário só dependem da configuração e do
    DADGER; vale também para a RV0 de 202609, cujas séries geradas não estão
    no pacote (cenários e determinísticos de enchimento são irrelevantes)."""
    d, v, rev = _revisao(nome, dadger)
    nprev, nobs, ncen = v.semanas_nao_observadas, v.semanas_observadas, v.aberturas[0]
    z = lambda n: np.zeros((n, NPOS), dtype=np.int64)  # noqa: E731
    a = montar_arvore(
        configuracao(nome, dadger), v, d.n_postos,
        np.zeros((ncen, NPOS)), np.zeros((ncen, NPOS)), np.full(ncen, 1 / ncen, np.float32),
        RegistrosDeterministicos(z(nprev), z(nprev), z(11), z(nobs)), NPOS,
        apoio.opcoes_empacotamento(nome, rev),
    )
    oficial = (DECKS / nome / f"VAZOES.{rev}").read_bytes()
    assert serializar_vazoes_rvx(a)[: 3 * RECL] == oficial[: 3 * RECL]


def test_gravador_nao_le_vazoes_existente():
    """O gravador não depende dos leitores de VAZOES.RVx/VAZDCP.REL."""
    fontes = sorted((RAIZ / "src" / "pulsar" / "empacotamento").glob("*.py"))
    assert fontes
    for f in fontes:
        s = f.read_text(encoding="utf-8")
        assert not re.search(r"oraculos|ler_vazoes|vazdcp|open\([^)]*[\"']r", s, re.I), f
    codigo = (
        "import sys; import pulsar.empacotamento; "
        "print(any(m.startswith('pulsar.oraculos') for m in sys.modules))"
    )
    r = subprocess.run([sys.executable, "-c", codigo], capture_output=True, text=True,
                       env={"PYTHONPATH": str(RAIZ / "src")}, check=True)
    assert r.stdout.strip() == "False"


def test_versao_e_cauda_parametrizaveis():
    assert codificar_versao("11.0.2") == 110002
    nome, dadger = COMPLETOS[0]
    a = arvore_do_pacote(nome, dadger, OpcoesEmpacotamento(versao="11.1.0", cauda_registro3=b""))
    r3 = serializar_vazoes_rvx(a)[2 * RECL: 3 * RECL]
    assert np.frombuffer(r3[24:28], "<i4")[0] == 110100
    assert r3[28:] == bytes(RECL - 28)


def test_nint_recusa_nao_finitos():
    for x in (np.nan, np.inf, -np.inf):
        with pytest.raises(ValueError, match="não finito"):
            nint([1.0, x])


def test_nint_empate_longe_do_zero():
    assert nint([0.5, 1.5, -0.5, -1.5, 2.49, -2.51]).tolist() == [1, 2, -1, -2, 2, -3]
    # o maior float64 abaixo de 0.5 (floor(x + 0.5) daria 1)
    assert nint([0.49999999999999994, -0.49999999999999994, 2.5, -2.5]).tolist() == [0, 0, 3, -3]


@pytest.mark.parametrize("campo", ["semanas_nao_observadas", "semanas_observadas", "dias_excluidos"])
def test_campo_em_branco_do_bloco_vazoes(campo):
    """F7-VZ-11: campo em branco (None no leitor) grava 0 ou, com
    campo_em_branco="erro", é recusado. Os DADGER públicos têm os três
    campos preenchidos; aqui o branco é simulado."""
    import dataclasses
    nome, dadger = COMPLETOS[0]
    d, v, _ = _revisao(nome, dadger)
    v2 = dataclasses.replace(v, **{campo: None})
    ncen = v.aberturas[0]
    nprev = 0 if campo == "semanas_nao_observadas" else v.semanas_nao_observadas
    nobs = 0 if campo == "semanas_observadas" else v.semanas_observadas
    z = lambda n: np.zeros((n, NPOS), dtype=np.int64)  # noqa: E731
    args = (configuracao(nome, dadger), v2, d.n_postos, np.zeros((ncen, NPOS)), np.zeros((ncen, NPOS)),
            np.full(ncen, 1 / ncen, np.float32), RegistrosDeterministicos(z(nprev), z(nprev), z(11), z(nobs)), NPOS)
    a = montar_arvore(*args)
    r3 = np.frombuffer(serializar_vazoes_rvx(a)[2 * RECL: 2 * RECL + 28], "<i4")
    pos = {"semanas_nao_observadas": 0, "dias_excluidos": 1, "semanas_observadas": 5}[campo]
    assert r3[pos] == 0
    with pytest.raises(ValueError, match=campo):
        montar_arvore(*args, OpcoesEmpacotamento(campo_em_branco="erro"))


def _registro3(bloco, nome="202609", dadger=None):
    """Registro 3 gravado com o bloco & VAZOES dado. Os registros 1, 2 e os
    blocos de vazão não interessam aqui: usa-se a configuração de um pacote
    completo e séries nulas."""
    d, _, _ = _revisao(nome, dadger)
    ncen = bloco.aberturas[0]
    nprev, nobs = bloco.semanas_nao_observadas or 0, bloco.semanas_observadas or 0
    z = lambda n: np.zeros((n, NPOS), dtype=np.int64)  # noqa: E731
    a = montar_arvore(configuracao(nome, dadger), bloco, d.n_postos,
                      np.zeros((ncen, NPOS)), np.zeros((ncen, NPOS)), np.full(ncen, 1 / ncen, np.float32),
                      RegistrosDeterministicos(z(nprev), z(nprev), z(11), z(nobs)), NPOS)
    return np.frombuffer(serializar_vazoes_rvx(a)[2 * RECL: 2 * RECL + 28], "<i4")


def test_mes_inicial_em_branco_e_recusado():
    """F7-VZ-11: o mês inicial (reg. 4) não tem campo duplicado."""
    import dataclasses
    _, v, _ = _revisao(*COMPLETOS[0])
    with pytest.raises(ValueError, match="mes_inicial"):
        _registro3(dataclasses.replace(v, mes_inicial=None))


def test_ano_inicial_em_branco_usa_o_reg_6():
    """F7-VZ-12 (P-DADG-12): sem o ano no reg. 4 vale o do reg. 6; sem os
    dois, erro."""
    import dataclasses
    _, v, _ = _revisao(*COMPLETOS[0])
    r3 = _registro3(dataclasses.replace(v, ano_inicial=None, ano_inicial_estudo=2031))
    assert (r3[2], r3[3]) == (v.mes_inicial, 2031)
    with pytest.raises(ValueError, match="ano_inicial"):
        _registro3(dataclasses.replace(v, ano_inicial=None, ano_inicial_estudo=None))


@pytest.mark.skipif(not colecao_ons.disponivel(), reason="coleção de decks do ONS indisponível")
def test_ano_do_reg_6_contra_os_vazoes_rv_do_decomp():
    """F7-VZ-12 e F7-VZ-11 contra a coleção pública de decks do ONS (03 §1.2).

    Para cada DADGER do GEVAZP operacional com o ano do reg. 4 em branco, o
    registro 3 gravado tem (mês do reg. 4, ano do reg. 6), igual aos campos 3
    e 4 do registro 3 do vazoes.rvN publicado no deck DECOMP da mesma
    revisão (o resto do registro 3 desses arquivos segue um layout antigo e
    não é comparado). Conta também os DADGER com as semanas observadas em
    branco (2º campo do reg. 7)."""
    import struct

    from pulsar.entradas.dadger import ler_dadger

    zips = colecao_ons.zips_decomp()
    sem_ano = iguais = sem_deck = sem_semanas_obs = 0
    diferentes = []
    for c in colecao_ons.casos_gevazp():
        v = ler_dadger(c.dadger).vazoes
        if v is None:
            continue
        sem_semanas_obs += v.semanas_observadas is None
        if v.ano_inicial is not None:
            continue
        sem_ano += 1
        r3 = _registro3(v)
        assert (r3[2], r3[3]) == (v.mes_inicial, v.ano_inicial_estudo), c.nome
        z = zips.get((c.ano, c.mes, c.rev))
        dados = colecao_ons.vazoes_rv_do_zip(z) if z else None
        if dados is None:
            sem_deck += 1
            continue
        pub = struct.unpack_from("<4i", dados, 2 * RECL)
        if (pub[2], pub[3]) == (r3[2], r3[3]):
            iguais += 1
        else:
            diferentes.append((c.nome, pub, tuple(r3[:4])))
    print(f"ano em branco: {sem_ano}; iguais ao vazoes.rvN: {iguais}; sem deck DECOMP: {sem_deck}; "
          f"semanas observadas em branco: {sem_semanas_obs}")
    assert not diferentes, diferentes[:5]
    assert sem_ano > 0 and iguais > 0 and sem_semanas_obs > 0


def test_colisao_de_colunas():
    """Postos repetidos (posto 300 das PARTIF): com 'erro', valores
    diferentes na mesma coluna são recusados; nos pacotes públicos são todos
    zero e as duas opções dão o mesmo arquivo."""
    nome, dadger = COMPLETOS[0]
    a1 = serializar_vazoes_rvx(arvore_do_pacote(nome, dadger))
    a2 = serializar_vazoes_rvx(arvore_do_pacote(nome, dadger, replace(apoio.opcoes_empacotamento(nome), colisao="erro")))
    assert a1 == a2
    d, v, _ = _revisao(nome, dadger)
    c = configuracao(nome, dadger)
    i300 = [i for i, u in enumerate(c.completa) if u.posto == 300][:2]
    g = O.ler_incrementais_geradas(DECKS / nome / "GEVAZP.OUT").valores.copy()
    g[:, i300[0]] = 7.0
    with pytest.raises(ValueError, match="coluna 300"):
        montar_arvore(c, v, d.n_postos, g, g, O.ler_probvaz(DECKS / nome / "PROBVAZ.DAT"),
                      deterministicos_do_vazdcp(DECKS / nome / "VAZDCP.REL"), NPOS,
                      OpcoesEmpacotamento(colisao="erro"))


def test_rejeita_entradas_inconsistentes():
    nome, dadger = COMPLETOS[0]
    d, v, _ = _revisao(nome, dadger)
    det = deterministicos_do_vazdcp(DECKS / nome / "VAZDCP.REL")
    g = O.ler_incrementais_geradas(DECKS / nome / "GEVAZP.OUT").valores
    f = O.ler_probvaz(DECKS / nome / "PROBVAZ.DAT")
    c = configuracao(nome, dadger)
    with pytest.raises(ValueError):
        montar_arvore(c, v, d.n_postos, g[:-1], g, f, det, NPOS)
    with pytest.raises(ValueError):
        montar_arvore(c, v, d.n_postos, g, g, f,
                      RegistrosDeterministicos(det.prevista_semanal[:-1], det.prevista_semanal_ena,
                                               det.observada_mensal, det.observada_semanal), NPOS)
    flut = RegistrosDeterministicos(det.prevista_semanal.astype(float), det.prevista_semanal_ena,
                                    det.observada_mensal, det.observada_semanal)
    with pytest.raises(TypeError):
        serializar_vazoes_rvx(montar_arvore(c, v, d.n_postos, g, g, f, flut, NPOS))
