"""T4: ordens e coeficientes PAR(p)-A, com o tratamento de coeficientes
negativos, contra o correli.out (float64), o GEVAZP.REL e o rastro do
vordem.out.

Proveniência: P-ORD-01..03, P-YW-01, P-LIN-01, P-NEG-01..05, P-PAR-01,
P-VORD-01..03.
"""

import numpy as np

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
            assert confere_3_algarismos(md.psi, r.psi[m]), (nome, m + 1)
            if md.ordem == 0:
                assert md.psi == 0.0 and r.psi[m] == 0.0


def test_modelo_par_a_e_ordem_maxima_do_deck(pacote):
    """P-PAR-01, P-ORD-01: os pacotes trazem MODELO PAR-A = 1, e o REL
    imprime "AJUSTA MODELO ESTOCASTICO PAR-A SIM"; a ordem máxima é 11 no
    DADGER (reg. 11), no GEVAZP.DAT (reg. 15) e no REL."""
    d = base.deck(pacote.nome)
    assert d.dadger.vazoes.modelo_par_a == 1
    assert d.dadger.vazoes.ordem_maxima == 11 and d.gevazp.ordem_maxima == 11
    gerais = rel_texto.dados_gerais(rel_texto.linhas_rel(pacote.arq("GEVAZP.REL")))
    assert gerais["AJUSTA MODELO ESTOCASTICO PAR-A"] == "SIM"
    assert gerais["ORDEM MAXIMA DO MODELO AUTOREGRESSIVO"] == "11"
    aj = next(iter(ajustes(pacote.nome).values()))
    assert aj.opcoes.anual and aj.opcoes.ordem_maxima == 11


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
                assert np.all(np.abs(np.array(nossa.fisicos[m]) - rm.coefs) <= TOL5), c
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
