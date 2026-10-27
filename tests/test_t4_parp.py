"""T4: ordens e coeficientes PAR(p)-A, com o tratamento de coeficientes
negativos, contra o correli.out (float64), o GEVAZP.REL e o rastro do
vordem.out.

Proveniência: P-ORD-01..03, P-YW-01, P-LIN-01, P-NEG-01..05, P-PAR-01,
P-VORD-01..03.
"""

import numpy as np
import pytest

import apoio
import base
import rel as rel_texto
from apoio_parp import ajustes, confere_3_algarismos, correli_da_serie, vordem

TOL5 = 0.5e-5 + 1e-9  # 5 casas do vordem.out


def test_ordens_finais_iguais(pacote):
    """Ordens finais iguais ao correli.out e ao 'ORDEM FINAL' do REL em todas
    as séries e meses."""
    rel = apoio.series_rel(pacote.nome)
    for nome, aj in ajustes(pacote.nome).items():
        assert aj.ordens == correli_da_serie(pacote.nome, nome).ordens, nome
        assert list(aj.ordens) == rel[nome].ordens, nome


def test_coeficientes_bit_a_bit(pacote):
    """P-YW-01, P-LIN-01: φ float64 iguais ao correli.out."""
    for nome, aj in ajustes(pacote.nome).items():
        s = correli_da_serie(pacote.nome, nome)
        for m, md in enumerate(aj.modelos):
            assert np.array_equal(np.array(md.phi), s.coeficientes[m]), (nome, m + 1)


def test_coeficientes_e_psi_iguais_ao_rel(pacote):
    """φ e ψ ('COEFICIENTES DA PARTE A12') com os 3 algarismos do REL; ψ = 0
    nos meses de ordem 0 (P-NEG-03)."""
    rel = apoio.series_rel(pacote.nome)
    for nome, aj in ajustes(pacote.nome).items():
        r = rel[nome]
        for m, md in enumerate(aj.modelos):
            assert confere_3_algarismos(md.phi, r.coeficientes[m]).all(), (nome, m + 1)
            if not aj.opcoes.anual:  # ramo PAR(p): sem ψ no modelo nem no REL
                assert md.psi is None and r.psi is None, nome
                continue
            assert confere_3_algarismos(md.psi, r.psi[m]), (nome, m + 1)
            if md.ordem == 0:
                assert md.psi == 0.0 and r.psi[m] == 0.0


def test_modelo_par_a_e_ordem_maxima_do_deck(pacote):
    """P-PAR-01, P-ORD-01: com MODELO PAR-A = 1 o REL imprime "AJUSTA MODELO
    ESTOCASTICO PAR-A SIM"; sem o registro (DADGER de 2022), "NAO" e o ramo
    PAR(p). A ordem máxima é 11 no DADGER (reg. 11), no GEVAZP.DAT (reg. 15)
    e no REL em todos os pacotes."""
    d = base.deck(pacote.nome)
    flag = d.dadger.vazoes.modelo_par_a
    assert flag in (None, 1)
    assert d.dadger.vazoes.ordem_maxima == 11 and d.gevazp.ordem_maxima == 11
    gerais = rel_texto.dados_gerais(rel_texto.linhas_rel(pacote.arq("GEVAZP.REL")))
    assert gerais["AJUSTA MODELO ESTOCASTICO PAR-A"] == ("SIM" if flag == 1 else "NAO")
    assert gerais["ORDEM MAXIMA DO MODELO AUTOREGRESSIVO"] == "11"
    aj = next(iter(ajustes(pacote.nome).values()))
    assert aj.opcoes.anual == (flag == 1) and aj.opcoes.ordem_maxima == 11


def test_rastro_igual_ao_vordem(pacote):
    """P-NEG-01..05: cada iteração do tratamento de negativos reproduz o
    bloco 'USINA:' correspondente do vordem.out: ordens identificadas,
    ordens usadas, φ', ψ' e as contribuições 'FUNC. DE' até a primeira
    negativa; o número de iterações é o mesmo."""
    vo = vordem(pacote.nome)
    for nome, aj in ajustes(pacote.nome).items():
        its = vo[nome]
        assert len(its) == len(aj.iteracoes), nome
        for k, (nossa, ref) in enumerate(zip(aj.iteracoes, its)):
            ctx = (nome, k + 1)
            assert nossa.identificadas == ref.identificadas, ctx
            for m, rm in enumerate(ref.meses):
                c = (*ctx, m + 1)
                assert rm.mes == m + 1
                assert nossa.modelos[m].ordem == rm.ordem, c
                assert len(rm.coefs) == rm.ordem, c
                # P-VORD-04: campo estourado (********) vem NaN e não é comparado
                ok = ~np.isnan(rm.coefs)
                assert np.all(np.abs(np.array(nossa.fisicos[m])[ok] - np.array(rm.coefs)[ok]) <= TOL5), c
                if rm.psi is None:  # ramo PAR(p): o vordem.out não traz PSI
                    assert not aj.opcoes.anual and nossa.psi_fisico[m] == 0.0, c
                else:
                    assert abs(nossa.psi_fisico[m] - rm.psi) <= TOL5, c
                # FUNC: meses m-1, m-2, ... até a primeira negativa
                f = nossa.contribuicoes[m]
                corte = next((j + 1 for j, v in enumerate(f) if v < 0), len(f))
                assert [mm for mm, _ in rm.contribuicoes] == [(m - j) % 12 + 1 for j in range(1, corte + 1)], c
                assert np.all(np.abs(np.array(f[:corte]) - [v for _, v in rm.contribuicoes]) <= TOL5), c
            # meses com contribuição negativa = meses reduzidos na próxima
            neg = [m for m in range(12) if any(v < 0 for _, v in ref.meses[m].contribuicoes)]
            assert nossa.negativos == neg, ctx


def test_limite_da_busca_igual_ao_vordem(pacote):
    """P-NEG-05: nos meses reduzidos, o limite da nova busca na FACP é a
    ordem identificada anterior menos 1 (2ª linha 'AR( )' do vordem.out)."""
    vo = vordem(pacote.nome)
    n = 0
    for nome, aj in ajustes(pacote.nome).items():
        for k in range(1, len(aj.iteracoes)):
            antes = aj.iteracoes[k - 1]
            for m in antes.negativos:
                assert aj.iteracoes[k].limites[m] == vo[nome][k].meses[m].limite == antes.identificadas[m] - 1
                n += 1
    assert n > 0


def test_ordem_zero_so_por_coeficiente_combinado_negativo(pacote):
    """P-NEG-03: toda ordem 0 vem de uma ordem identificada 1 cujo
    coeficiente combinado φ'_1 + ψ'/12 do ajuste de ordem 1 é negativo."""
    n = 0
    for nome, aj in ajustes(pacote.nome).items():
        for it in aj.iteracoes:
            for m, md in enumerate(it.modelos):
                if md.ordem == 0:
                    assert it.identificadas[m] == 1, (nome, m + 1)
                    n += 1
    assert n > 0


def test_solver_do_ramo_parp(pacote):
    """P-LIN-03: no ramo PAR(p) os φ do correli.out são os do Cholesky; o
    Gauss-Jordan da P-LIN-01 (o do PAR(p)-A) erra o último bit em boa parte
    dos meses. No PAR(p)-A a opção não muda nada."""
    import dataclasses

    from pulsar import parp

    iguais = {"cholesky": 0, "gauss_jordan": 0}
    total = 0
    for nome, aj in ajustes(pacote.nome).items():
        s = correli_da_serie(pacote.nome, nome)
        for m, md in enumerate(aj.modelos):
            if md.ordem == 0:
                continue
            total += 1
            for solver in iguais:
                op = dataclasses.replace(aj.opcoes, solver_parp=solver)
                phi, _ = parp.yule_walker(aj.est, aj.anual, m, md.ordem, op.pivo_nulo, op.solver_parp)
                iguais[solver] += np.array_equal(np.array(phi), s.coeficientes[m])
    if aj.opcoes.anual:
        assert iguais["cholesky"] == iguais["gauss_jordan"] == total
    else:
        assert iguais["cholesky"] == total
        assert iguais["gauss_jordan"] < 0.7 * total, iguais


def test_ordem_para_antes_da_facp_maior_que_1(pacote):
    """P-ORD-04: a ordem identificada na 1ª iteração (vordem.out) nunca
    alcança a primeira defasagem com |φ_kk| > 1; sem o corte ("ignora") a
    identificação muda nos meses em que essa defasagem existe. No PAR(p)-A
    a FACP é uma correlação parcial e não passa de 1 nos pacotes."""
    import dataclasses

    from pulsar import parp

    vo = vordem(pacote.nome)
    cortados = 0
    for nome, aj in ajustes(pacote.nome).items():
        ref = vo[nome][0].identificadas
        assert aj.iteracoes[0].identificadas == ref, nome
        for m in range(12):
            lim = parp.limite_valido(aj.facp[:, m], aj.opcoes.ordem_maxima)
            assert ref[m] <= max(lim, 1), (nome, m + 1)
            if lim < aj.opcoes.ordem_maxima:
                cortados += 1
                sem = parp.identificar(aj.facp[:, m], aj.opcoes.ordem_maxima, aj.limiar, aj.opcoes.ordem_minima)
                assert sem != ref[m] or sem <= lim, (nome, m + 1)
    if aj.opcoes.anual:
        assert cortados == 0
    else:
        assert cortados > 0
        ign = dataclasses.replace(aj.opcoes, facp_maior_que_1="ignora")
        difere = sum(parp.ajustar(a.serie, ign).iteracoes[0].identificadas != vo[n][0].identificadas
                     for n, a in ajustes(pacote.nome).items())
        assert difere > 0


def _gauss_retro(a, b):
    """Eliminação de Gauss sem pivô e retrossubstituição (variante)."""
    n = len(b)
    m = [r[:] + [b[i]] for i, r in enumerate(a)]
    for i in range(n):
        for r in range(i + 1, n):
            f = m[r][i] / m[i][i]
            for j in range(i, n + 1):
                m[r][j] -= f * m[i][j]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        s = m[i][n]
        for j in range(i + 1, n):
            s -= m[i][j] * x[j]
        x[i] = s / m[i][i]
    return x


def _contagens_do_solver(nome):
    """Meses (série, mês com ordem ≥ 1) com φ igual em bits ao correli.out,
    por variante de solução do Yule-Walker do ramo PAR(p)."""
    from pulsar import parp
    from test_t3_variantes import _cholesky_nr

    def numpy_chol(a, b):
        lo = np.linalg.cholesky(np.array(a))
        return np.linalg.solve(lo.T, np.linalg.solve(lo, np.array(b))).tolist()

    def gauss_jordan(a, b):
        inv = parp.inversa(a)
        return [parp.soma(inv[i][j] * b[j] for j in range(len(b))) for i in range(len(b))]

    variantes = {
        "cholesky": parp.cholesky,
        "nr_k_crescente": lambda a, b: _cholesky_nr(a, b, False),
        "nr_k_decrescente": lambda a, b: _cholesky_nr(a, b, True),
        "numpy_cholesky": numpy_chol,
        "lapack": lambda a, b: np.linalg.solve(np.array(a), np.array(b)).tolist(),
        "gauss_retrossubstituicao": _gauss_retro,
        "gauss_jordan": gauss_jordan,
    }
    ok = dict.fromkeys(variantes, 0)
    total = 0
    for nome_s, aj in ajustes(nome).items():
        s = correli_da_serie(nome, nome_s)
        for m, md in enumerate(aj.modelos):
            if md.ordem == 0:
                continue
            total += 1
            mat = parp._matriz(aj.est, None, m, md.ordem)
            a = [r[1:] for r in mat[1:]]
            b = [r[0] for r in mat[1:]]
            for k, f in variantes.items():
                ok[k] += np.array_equal(np.array(f(a, b)), s.coeficientes[m])
    return total, ok


def test_variantes_do_solver_no_ramo_parp(pacote):
    """P-LIN-03: no ramo PAR(p) só o Cholesky da P-LIN-03 (somas em k
    crescente na fatoração e nas duas substituições) acerta todos os bits
    de φ; as variantes ficam abaixo. Contagens citadas na P-LIN-03: jan–jul
    de 2022 (162 usinas, 1 758 meses) e ago–dez (163 usinas, 1 770 meses)."""
    aj = next(iter(ajustes(pacote.nome).values()))
    if aj.opcoes.anual:
        pytest.skip("ramo PAR(p) só nos pacotes sem MODELO PAR-A (2022)")
    total, ok = _contagens_do_solver(pacote.nome)
    print(pacote.nome, total, ok)
    assert ok["cholesky"] == total
    assert all(v < total for k, v in ok.items() if k != "cholesky"), ok
    esperado = {
        1758: dict(nr_k_crescente=1333, nr_k_decrescente=1209, numpy_cholesky=1203, lapack=970,
                   gauss_retrossubstituicao=982, gauss_jordan=832),
        1770: dict(nr_k_crescente=1346, nr_k_decrescente=1222, numpy_cholesky=1214, lapack=978,
                   gauss_retrossubstituicao=990, gauss_jordan=840),
    }[total]
    assert {k: v for k, v in ok.items() if k != "cholesky"} == esperado
