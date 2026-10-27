"""T4 sem deck: o exemplo do M18 §6.3 para as contribuições em meses
futuros e o ramo PAR(p) (sem componente anual), que nenhum pacote completo
disponível exercita.

Proveniência: P-NEG-04 (DOC), P-PAR-01, P-FACP-02, P-ORD-01, lacuna L19.
"""

from types import SimpleNamespace

import numpy as np
import pytest

from pulsar import parp
from pulsar.historico import SerieIncremental

JAN, FEV, MAR, ABR, MAI, JUN, JUL, AGO, SET, OUT, NOV, DEZ = range(12)


def test_contribuicoes_reproduzem_o_exemplo_do_m18():
    """M18 §6.3: A_FEV = 0,641 A_JAN - 0,336 A_DEZ + 0,624 A_NOV - 0,421 A_OUT
    - 1,09 A_SET + 1,83 A_AGO, com A_JAN = 0,934 A_DEZ, A_DEZ = 0,971 A_NOV,
    A_NOV = 0,816 A_OUT e A_OUT = 0,470 A_SET - 0,151 A_AGO + 0,581 A_JUL.
    As contribuições de DEZ, NOV, OUT e SET em FEV são 0,2627, 0,8791,
    0,2963 e -0,9507; as de AGO e JUL, depois de substituir OUT, 1,7853 e
    0,1722 (o exemplo usa variáveis padronizadas, então φ' = φ)."""
    coefs = {
        FEV: (0.641, -0.336, 0.624, -0.421, -1.09, 1.83),
        JAN: (0.934,),
        DEZ: (0.971,),
        NOV: (0.816,),
        OUT: (0.470, -0.151, 0.581),
    }
    modelos = [parp.ModeloMes(len(coefs.get(m, ())), coefs.get(m, ()), None) for m in range(12)]
    fisicos = [coefs.get(m, ()) for m in range(12)]
    f = parp.contribuicoes(modelos, fisicos, [0.0] * 12)[FEV]
    assert np.allclose(f[:5], [0.641, 0.2627, 0.8791, 0.2963, -0.9507], atol=5e-5)
    # AGO depois de substituir também SET (que no exemplo não tem modelo)
    assert f[5] == pytest.approx(1.7853, abs=5e-5)


def test_contribuicoes_com_termo_anual_somam_psi_sobre_12():
    """P-NEG-02: no PAR(p)-A o termo anual entra como ψ'/12 em cada um dos 12
    lags (aqui ordem 1 e ψ' = 1,2: contribuição de DEZ em JAN = φ' + 0,1)."""
    modelos = [parp.ModeloMes(1, (0.5,), 0.3)] + [parp.ModeloMes(0, (), 0.0)] * 11
    fisicos = [(0.5,)] + [()] * 11
    psi = [1.2] + [0.0] * 11
    assert parp.contribuicoes(modelos, fisicos, psi)[JAN] == [pytest.approx(0.6)]


def _serie_sintetica(n_anos=60, semente=7):
    """PAR(1) periódico positivo, só para exercitar o código."""
    rng = np.random.default_rng(semente)
    media = 100 + 80 * np.sin(np.arange(12) * np.pi / 6)
    z = np.zeros(n_anos * 12)
    x = 0.0
    for t in range(z.size):
        x = 0.7 * x + rng.normal()
        z[t] = round(max(media[t % 12] * (1 + 0.25 * x), 1.0))
    return SerieIncremental(1, "SINTETICA", 1, "", tuple(range(1931, 1931 + n_anos)), z.reshape(n_anos, 12))


@pytest.mark.parametrize("forma", ["yw", "parcial"])
def test_ramo_parp_sem_componente_anual(forma):
    s = _serie_sintetica()
    aj = parp.ajustar(s, parp.OpcoesPAR(anual=False, facp_parp=forma))
    assert aj.anual is None
    assert all(md.psi is None for md in aj.modelos)
    assert all(0 <= p <= 11 for p in aj.ordens)
    assert not aj.iteracoes[-1].negativos
    if forma == "yw":
        # P-FACP-02: a FACP é o último coeficiente do Yule-Walker de ordem k
        for k in (1, 3, 7):
            for m in (0, 5):
                assert aj.facp[k - 1, m] == parp.yule_walker(aj.est, None, m, k)[0][-1]
    r = parp.residuos(aj)
    assert np.all(np.isfinite(r.desvio))


def test_ordem_maxima_limita_a_identificacao():
    s = _serie_sintetica()
    aj = parp.ajustar(s, parp.OpcoesPAR(anual=False, ordem_maxima=2))
    assert max(aj.iteracoes[0].identificadas) <= 2


def test_opcoes_do_deck():
    """P-PAR-01, P-ORD-01: sem MODELO PAR-A (DADGER até 2022) o ramo é o
    PAR(p); sem ordem máxima (DADGER até 2016), 11."""
    def deck(par_a, ordem):
        return SimpleNamespace(dadger=SimpleNamespace(vazoes=SimpleNamespace(modelo_par_a=par_a, ordem_maxima=ordem)))

    assert parp.opcoes_do_deck(deck(1, 11)) == parp.OpcoesPAR(anual=True, ordem_maxima=11)
    assert parp.opcoes_do_deck(deck(None, 6)) == parp.OpcoesPAR(anual=False, ordem_maxima=6)
    assert parp.opcoes_do_deck(deck(0, None)) == parp.OpcoesPAR(anual=False, ordem_maxima=11)


def test_incremental_nula_nao_e_ajustada():
    s = SerieIncremental(2, "NULA", 2, "", (2000, 2001, 2002), np.zeros((3, 12)))
    with pytest.raises(parp.ErroAjuste):
        parp.ajustar(s)


def test_inversa_gauss_jordan():
    a = [[1.0, 0.3, 0.2], [0.3, 1.0, 0.4], [0.2, 0.4, 1.0]]
    assert np.allclose(np.array(parp.inversa(a)) @ np.array(a), np.eye(3), atol=1e-14)


# --------------------------------------------------------------------------
# Parâmetros das ESCOLHAs (auditoria F3, rodada 1, B2/N1/N2/N3)


def _deck_op(par_a=1, ordem_dadger=11, ordem_gevazp=11):
    return SimpleNamespace(
        dadger=SimpleNamespace(vazoes=SimpleNamespace(modelo_par_a=par_a, ordem_maxima=ordem_dadger)),
        gevazp=SimpleNamespace(ordem_maxima=ordem_gevazp),
    )


def test_ordem_maxima_precedencia_e_zero():
    """P-ORD-01: DADGER reg. 11 x GEVAZP.DAT reg. 15 e o 0 explícito."""
    assert parp.opcoes_do_deck(_deck_op(1, 6, 9)).ordem_maxima == 6
    assert parp.opcoes_do_deck(_deck_op(1, 6, 9), fonte_ordem_maxima="gevazp").ordem_maxima == 9
    assert parp.opcoes_do_deck(_deck_op(1, None, 9)).ordem_maxima == 9
    assert parp.opcoes_do_deck(_deck_op(1, None, None)).ordem_maxima == 11
    assert parp.opcoes_do_deck(_deck_op(1, 0, 9)).ordem_maxima == 0
    assert parp.opcoes_do_deck(_deck_op(1, 0, 9), ordem_maxima_zero="ausente").ordem_maxima == 9


def test_modelo_par_a_fora_de_0_e_1():
    """P-PAR-01: valor ≠ 0/1 vira PAR(p) ou erro, por parâmetro."""
    assert parp.opcoes_do_deck(_deck_op(2)).anual is False
    with pytest.raises(parp.ErroAjuste):
        parp.opcoes_do_deck(_deck_op(2), par_a_outros="erro")


def test_selecao_sem_registro_16():
    """P-HIST-03: reg. 16 ≠ 1 aplica a mesma regra ou recusa."""
    from pulsar.entradas.texto import ErroLeitura
    from pulsar.historico import series_ajustadas

    s = [_serie_sintetica(), SerieIncremental(2, "NULA", 2, "", (2000, 2001, 2002), np.zeros((3, 12)))]
    assert [x.nome for x in series_ajustadas(s, None)] == ["SINTETICA"]
    assert [x.nome for x in series_ajustadas(s, 1, "erro")] == ["SINTETICA"]
    with pytest.raises(ErroLeitura):
        series_ajustadas(s, 0, "erro")


def test_assimetria_parametrizavel():
    """P-EST-03: as quatro combinações dão o mesmo valor a menos de bits."""
    z = _serie_sintetica().valores
    base = parp.estatisticas(z).assimetria
    for soma_ in ("direta", "reversa"):
        for cubo in ("potencia", "produto"):
            op = parp.OpcoesPAR(soma_assimetria=soma_, cubo_assimetria=cubo)
            assert np.allclose(parp.estatisticas(z, opcoes=op).assimetria, base, rtol=1e-12)


def test_desvio_nulo_erro_ou_ordem_zero():
    """P-EST-06: mês constante numa série não nula."""
    s = _serie_sintetica()
    z = s.valores.copy()
    z[:, ABR] = 50.0
    s0 = SerieIncremental(1, "CONSTANTE", 1, "", s.anos, z)
    with pytest.raises(parp.ErroAjuste):
        parp.ajustar(s0, parp.OpcoesPAR(anual=False))
    for anual in (False, True):
        aj = parp.ajustar(s0, parp.OpcoesPAR(anual=anual, desvio_nulo="ordem_zero"))
        assert aj.ordens[ABR] == 0
        assert np.isnan(aj.est.assimetria[ABR])
        r = parp.residuos(aj)
        assert np.all(r.valores[:, ABR] == 0.0)


def test_componente_anual_de_desvio_nulo():
    """P-EST-06 com σ^A_m = 0: série cuja soma do ano civil é constante (DEZ
    fecha a soma), logo A no mês de JAN (média de jan..dez anteriores) não
    varia. "erro" interrompe; "ordem_zero" zera as correlações com A no mês,
    dá ψ = ψ' = 0 e não força a ordem do mês. Com soma anual constante os 12
    meses de um ano são linearmente dependentes, por isso o teste usa 6
    defasagens (a FACP de lag 11 de DEZ seria degenerada)."""
    rng = np.random.default_rng(3)
    n = 40
    base = np.array([300, 280, 260, 200, 150, 120, 100, 90, 95, 120, 180, 250], float)
    z = base + rng.integers(-40, 41, (n, 12)).astype(float)
    z[:, DEZ] = base.sum() - z[:, :DEZ].sum(axis=1)
    s = SerieIncremental(1, "ANUAL CONSTANTE", 1, "", tuple(range(1931, 1931 + n)), z)
    op = dict(anual=True, defasagens=6, ordem_maxima=6)
    with pytest.raises(parp.ErroAjuste, match="componente anual"):
        parp.ajustar(s, parp.OpcoesPAR(**op))
    aj = parp.ajustar(s, parp.OpcoesPAR(**op, desvio_nulo="ordem_zero"))
    assert aj.anual.desvio[JAN] == 0.0
    assert not np.any(aj.anual.correlacao[:, JAN])
    assert aj.modelos[JAN].psi == 0.0 and aj.iteracoes[-1].psi_fisico[JAN] == 0.0
    assert aj.modelos[JAN].ordem == aj.iteracoes[-1].identificadas[JAN]  # ordem mantida
    assert min(aj.est.desvio) > 0  # a série em si não tem desvio nulo


def test_residuos_curtos_sao_erro():
    """P-EST-07: com N = 3 e um mês cuja ordem alcança antes do início, só há
    2 resíduos no mês e a assimetria não existe. O ajuste vem de uma série
    longa e só a série dos resíduos é trocada por 3 anos."""
    from dataclasses import replace

    s = _serie_sintetica()
    aj = parp.ajustar(s, parp.OpcoesPAR(anual=False))
    aj.serie = replace(s, anos=s.anos[:3], valores=s.valores[:3])
    aj.iteracoes[-1].modelos[JAN] = parp.ModeloMes(1, (0.5,), None)
    with pytest.raises(parp.ErroAjuste):
        parp.residuos(aj)


def test_pivo_nulo_erro_ou_lapack():
    """P-LIN-02."""
    a = [[0.0, 1.0], [1.0, 0.0]]
    with pytest.raises(parp.ErroAjuste):
        parp.inversa(a)
    assert np.allclose(parp.inversa(a, "lapack"), [[0.0, 1.0], [1.0, 0.0]])


def test_soma_dos_residuos_parametrizavel():
    """P-RES-04: as duas ordens dão os mesmos momentos a menos de bits."""
    aj = parp.ajustar(_serie_sintetica(), parp.OpcoesPAR(anual=True))
    r1 = parp.residuos(aj)
    aj.opcoes = parp.OpcoesPAR(anual=True, soma_residuos="reversa")
    r2 = parp.residuos(aj)
    for campo in ("media", "desvio", "assimetria", "fac"):
        assert np.allclose(getattr(r1, campo), getattr(r2, campo), rtol=1e-9, atol=1e-15)


def test_historico_curto_e_erro():
    """P-EST-07."""
    with pytest.raises(parp.ErroAjuste):
        parp.estatisticas(np.ones((2, 12)))
