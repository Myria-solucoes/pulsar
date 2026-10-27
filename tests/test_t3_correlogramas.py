"""T3: correlograma, correlação com a componente anual e FACP, contra o
correli.out (float64) e o GEVAZP.REL.

Proveniência: P-EST-04, P-ANU-03, P-FACP-01, P-LIN-01.
"""

import numpy as np

import apoio
from apoio_parp import ajustes, correli_da_serie

TOL5 = 0.5e-5 + 1e-12  # 5 casas do GEVAZP.REL


def test_correlograma_bit_a_bit(pacote):
    """P-EST-04: soma do último ano ao primeiro, sem os pares que cruzam o
    início, divisor N."""
    for nome, aj in ajustes(pacote.nome).items():
        s = correli_da_serie(pacote.nome, nome)
        assert np.array_equal(aj.est.fac[1:], s.fac), nome


def test_correlograma_cruzando_o_inicio_divide_por_n(pacote):
    """Lacuna L2: dividir pelo número de pares erraria na 3ª casa."""
    aj = next(iter(ajustes(pacote.nome).values()))
    s = correli_da_serie(pacote.nome, aj.serie.nome)
    n = aj.est.n_anos
    k, m = 11, 0  # JAN com lag 11: um par a menos
    assert abs(aj.est.fac[k, m] * n / (n - 1) - s.fac[k - 1, m]) > 1e-4


def test_correlacao_com_a_componente_anual_igual_ao_rel(pacote):
    """P-ANU-03: tabela de ordem 0..11 que segue o correlograma no REL."""
    rel = apoio.series_rel(pacote.nome)
    for nome, aj in ajustes(pacote.nome).items():
        ref = rel[nome].fac_componente_anual
        if aj.anual is None:  # ramo PAR(p): o REL não traz a tabela
            assert ref is None, nome
            continue
        assert ref.shape == aj.anual.correlacao.shape, nome
        assert np.all(np.abs(aj.anual.correlacao - ref) <= TOL5), nome


def test_facp_bit_a_bit(pacote):
    """P-FACP-01, P-LIN-01: correlação parcial condicionada aos lags
    intermediários e a A_{t-1}, todas as séries, lags e meses."""
    for nome, aj in ajustes(pacote.nome).items():
        s = correli_da_serie(pacote.nome, nome)
        assert np.array_equal(aj.facp, s.facp), nome


def test_facp_igual_ao_rel(pacote):
    rel = apoio.series_rel(pacote.nome)
    for nome, aj in ajustes(pacote.nome).items():
        assert np.all(np.abs(aj.facp - rel[nome].facp) <= TOL5), nome
