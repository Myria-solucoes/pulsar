"""VAZOES.RVx e PROBVAZ.DAT contra VAZDCP.REL, PROBVAZ.REL, GEVAZP.REL e as
séries em árvore.

Proveniência: F2-VZ-01..12, F2-PB-01..04.
"""

import re

import numpy as np
import pytest

from apoio import config, gevazp_out, mes_estocastico, nint, previsoes_rel, probvaz, vazoes
from pulsar import oraculos as O
from pulsar.oraculos import texto as T

MESES = "JAN FEV MAR ABR MAI JUN JUL AGO SET OUT NOV DEZ".split()


def _ints(s):
    return [int(x) for x in re.findall(r"-?\d+", s)]


def test_todos_os_registros_iguais_ao_vazdcp(pacote):
    """Cada 'REGISTRO No.' do VAZDCP.REL contra o mesmo registro do binário."""
    v = vazoes(pacote.nome)
    rel = T.ler_vazdcp(pacote.arq("VAZDCP.REL"))
    nreg = len(open(pacote.vazoes, "rb").read()) // (v.npos * 4)
    assert len(rel) == nreg and [r.numero for r in rel] == list(range(1, nreg + 1))

    r1 = rel[0].titulo
    assert int(re.search(r"NUM USINAS:\s+(\d+)", r1)[1]) == v.n_usinas
    assert int(re.search(r"NUM ESTAGIOS :\s+(\d+)", r1)[1]) == v.n_estagios
    ab = _ints(re.search(r"ABERTURAS:(.*)NPOS", r1)[1])
    assert tuple(ab[: v.n_estagios]) == v.aberturas and not any(ab[v.n_estagios:])
    assert int(re.search(r"NPOS:\s+(\d+)", r1)[1]) == v.npos
    nw = re.search(r"NUM USINAS NW:\s+(\d+)", r1)  # o VAZDCP do 9_L não imprime
    assert nw is None or int(nw[1]) == v.n_usinas_nw

    assert tuple(_ints(rel[1].titulo.split(":", 1)[1])) == v.codigos

    r3, c = rel[2].titulo, v.calendario
    assert int(re.search(r"NSEM PREV:\s+(\d+)", r3)[1]) == c.semanas_previstas
    assert int(re.search(r"NDIAS :\s+(\d+)", r3)[1]) == c.dias_excluidos
    mes, ano = re.search(r"PERIODO INICIAL:\s+(\w+)/(\d+)", r3).groups()
    assert (MESES.index(mes) + 1, int(ano)) == (c.mes_inicial, c.ano_inicial)
    assert int(re.search(r"NPOSTOS:\s+(\d+)", r3)[1]) == c.n_postos
    assert int(re.search(r"NSEM OBS:\s+(\d+)", r3)[1]) == c.semanas_observadas
    # F2-VZ-04c: o 9_L grava 80106 e imprime só "9"; o 11 grava 110000 e
    # imprime "11"
    impressa = re.search(r"VERSAO GEVAZP:\s+(\S+)", r3)[1]
    assert impressa == c.versao or (c.versao_codigo, impressa) in {(80106, "9"), (110000, "11")}

    # F2-VZ-05: ceil(NNOS/NPOS) registros de probabilidades (2 com 513
    # aberturas, 202206 e 202207)
    nprob = -(-len(v.probabilidades) // v.npos)
    assert all(r.titulo == "PROBABILIDADE DOS NOS" for r in rel[3:3 + nprob])
    impressas = np.concatenate([r.valores for r in rel[3:3 + nprob]])[: len(v.probabilidades)]
    np.testing.assert_array_equal(np.round(v.probabilidades.astype(np.float64), 6), impressas)

    blocos = [
        ("VAZAO PREVISTA INCREMENTAL SEMANA", v.prevista_semanal),
        ("VAZAO INCREMENTAL GERADA NO", v.gerada_mensal),
        ("VAZAO PREVISTA INCREMENTAL PARA CALCULO DA ENA SEMANA", v.prevista_semanal_ena),
        ("VAZAO INCREMENTAL GERADA PARA CALCULO DA ENA NO", v.gerada_mensal_ena),
        ("VAZAO INCREMENTAL OBSERVADA MES", v.observada_mensal),
        ("VAZAO INCREMENTAL OBSERVADA SEMANA", v.observada_semanal),
    ]
    k = 3 + nprob
    for titulo, bloco in blocos:
        for linha in bloco:
            r = rel[k]
            assert re.sub(r"\s+\d+$", "", r.titulo) == titulo, (k + 1, r.titulo)
            np.testing.assert_array_equal(linha, r.valores, err_msg=f"registro {k + 1}")
            k += 1
    assert k == nreg
    # rótulos dos meses observados
    meses_rel = [int(r.titulo.split()[-1]) for r in rel if r.titulo.startswith("VAZAO INCREMENTAL OBSERVADA MES")]
    assert tuple(meses_rel) == v.meses_observados


def test_estrutura_de_todas_as_revisoes(pacote):
    """Também as revisões sem saídas no pacote (202609 RV0) fecham o layout."""
    for arq in pacote.revisoes_vazoes():
        v = O.ler_vazoes_decomp(arq)
        # F2-VZ-04a/04c: os quatro códigos observados (9_L, 10.0.0, 11, 11.0.2)
        assert (v.calendario.versao_codigo, v.calendario.versao) in {
            (80106, "8.1.6"), (100000, "10.0.0"), (110000, "11.0.0"), (110002, "11.0.2")}
        assert v.n_estagios - 1 == v.prevista_semanal.shape[0] == v.prevista_semanal_ena.shape[0]
        assert v.aberturas[:-1] == (1,) * (v.n_estagios - 1)
        assert v.n_cenarios == v.aberturas[-1] == v.gerada_mensal_ena.shape[0]
        assert len(v.codigos) == v.n_usinas + v.n_usinas_nw
        assert v.observada_semanal.shape[0] == v.calendario.semanas_observadas
        assert v.observada_mensal.shape[0] == 11
        assert np.all(v.probabilidades[: v.n_estagios - 1] == 1.0)
        assert abs(v.probabilidades[v.n_estagios - 1 :].astype(np.float64).sum() - 1) < 1e-5


def test_rejeita_arvore_fora_do_layout_verificado(pacote, tmp_path):
    """F2-VZ-09: com mais de uma abertura num estágio anterior ao último, o
    leitor não adivinha o layout e levanta erro."""
    dados = bytearray(open(pacote.vazoes, "rb").read())
    np.frombuffer(dados, "<i4")[2] = 2  # aberturas[0] = 2
    arq = tmp_path / "VAZOES.TST"
    arq.write_bytes(bytes(dados))
    with pytest.raises(ValueError, match="fora do layout verificado"):
        O.ler_vazoes_decomp(arq)


def test_gerada_e_nint_do_gevazp_out_por_posto(pacote):
    v = vazoes(pacote.nome)
    g = gevazp_out(pacote.nome)
    for u in config(pacote.nome):
        np.testing.assert_array_equal(v.gerada_mensal[:, u.posto - 1], nint(g.usina(u.nint)), err_msg=u.nome)


def test_gerada_ena_e_nint_do_vazoesia_na_coluna_ena(pacote):
    v = vazoes(pacote.nome)
    a = O.ler_incrementais_artificiais(pacote.arq("vazoesia.out"))
    cols = set()
    for u in config(pacote.nome):
        cols.add(u.coluna_ena)
        np.testing.assert_array_equal(v.gerada_mensal_ena[:, u.coluna_ena - 1], nint(a.usina(u.nint)), err_msg=u.nome)
    fora = [k + 1 for k in range(v.npos) if v.gerada_mensal_ena[:, k].any() and k + 1 not in cols]
    assert fora == []


def test_semanas_iguais_a_tabela_de_previsoes_do_rel(pacote):
    """Blocos semanais contra 'PREVISOES INCREMENTAIS' e '... PARA ENA' do REL."""
    v = vazoes(pacote.nome)
    cfg = {u.nint: u for u in config(pacote.nome)}
    nobs = v.calendario.semanas_observadas
    for p in previsoes_rel(pacote.nome):
        u = cfg[p.nint]
        if p.posto != u.posto:  # linha PL do posto lateral (P-REL-03)
            continue
        for w in range(v.prevista_semanal.shape[0]):
            assert v.prevista_semanal[w, u.posto - 1] == p.incremental[nobs + w], u.nome
            assert v.prevista_semanal_ena[w, u.coluna_ena - 1] == p.incremental_ena[nobs + w], u.nome
        for w in range(nobs):
            assert v.observada_semanal[w, u.coluna_ena - 1] == p.incremental_ena[w], u.nome


def test_observada_mensal_nas_usinas_sem_artificial(pacote):
    """Observados mensais em convenção ENA: usinas com posto artificial têm a
    coluna do próprio posto zerada; CAMARGOS repete a tendência do QPAST."""
    v = vazoes(pacote.nome)
    q = O.ler_qpast(pacote.arq("QPAST.DAT"))
    usadas = {u.coluna_ena for u in config(pacote.nome)}
    for u in config(pacote.nome):
        if u.posto_artificial and u.posto not in usadas:
            assert not v.observada_mensal[:, u.posto - 1].any(), u.nome
    for m in v.meses_observados:
        assert v.observada(m, 1) == nint(q.incremental_mensal(1, m))


def test_probvaz_sao_as_folhas_do_vazoes(pacote):
    """PROBVAZ.DAT guarda só as folhas do estágio estocástico, em float32,
    iguais em bits às do registro 4 do VAZOES.RVx."""
    v = vazoes(pacote.nome)
    p = probvaz(pacote.nome)
    assert len(p) == v.aberturas[-1]
    np.testing.assert_array_equal(p, v.probabilidades[v.n_estagios - 1 :])
    assert p.dtype == np.float32


def test_probvaz_igual_ao_probvaz_rel(pacote):
    p = probvaz(pacote.nome)
    rel = T.ler_probvaz_rel(pacote.arq("PROBVAZ.REL"))
    mes = mes_estocastico(pacote.nome)
    assert rel.shape[0] == len(p)
    np.testing.assert_allclose(p.astype(np.float64), rel[:, mes - 1], atol=0.5e-4 + 1e-9)
    outros = np.delete(rel, mes - 1, axis=1)
    assert np.all(outros == 1.0)


def test_probvaz_sao_contagens_sobre_50000(pacote):
    """INFERIDO F2-PB-04 (para F8/T10): todas as probabilidades são k/50000 com
    k inteiro, e as contagens somam 50000 (R3383: amostra de 50 mil)."""
    p = probvaz(pacote.nome).astype(np.float64)
    k = np.round(p * 50000)
    assert k.sum() == 50000
    assert np.all((k / 50000).astype(np.float32) == probvaz(pacote.nome))
    # e 50000 é o menor N que torna todas compatíveis com contagens inteiras
    for n in range(1, 50000):
        kk = np.round(p * n)
        if kk.sum() == n and np.all((kk / n).astype(np.float32) == probvaz(pacote.nome)):
            pytest.fail(f"N menor compatível: {n}")
