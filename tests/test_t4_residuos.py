"""T4 (resíduos): série de ruídos e seus momentos contra o GEVAZP.REL.

Proveniência: P-RES-01..03.
"""

import numpy as np

from apoio_parp import confere_3_algarismos, residuos, residuos_rel

TOL5 = 0.5e-5 + 1e-12


def test_serie_de_ruidos_igual_ao_rel(pacote):
    """P-RES-01: 'SERIE DE RUIDOS' com 3 algarismos, inclusive os zeros do
    1º ano nos meses cuja ordem alcança antes do início."""
    rel = residuos_rel(pacote.nome)
    for nome, r in residuos(pacote.nome).items():
        ref = rel[nome]
        anos = sorted(ref.serie)
        assert len(anos) == r.valores.shape[0], nome
        tab = np.array([ref.serie[a] for a in anos])
        ok = confere_3_algarismos(r.valores, tab)
        assert ok.all(), (nome, np.argwhere(~ok)[:3])
        assert np.array_equal(r.valores[~r.validos], np.zeros((~r.validos).sum()))


def test_momentos_dos_ruidos_iguais_ao_rel(pacote):
    """P-RES-02: média, desvio e assimetria sobre os resíduos existentes.
    As médias exatamente nulas no float64 saem no REL como ~1e-16; só se
    compara a média dos meses em que ela não é zero de arredondamento."""
    rel = residuos_rel(pacote.nome)
    for nome, r in residuos(pacote.nome).items():
        ref = rel[nome]
        assert confere_3_algarismos(r.desvio, ref.desvio).all(), nome
        assert confere_3_algarismos(r.assimetria, ref.assimetria).all(), nome
        grande = np.abs(ref.media) > 1e-10
        assert confere_3_algarismos(r.media[grande], ref.media[grande]).all(), nome
        assert np.all(np.abs(r.media[~grande]) < 1e-10), nome


def test_correlograma_dos_ruidos_igual_ao_rel(pacote):
    """P-RES-03: todos os pares, divisor N."""
    rel = residuos_rel(pacote.nome)
    for nome, r in residuos(pacote.nome).items():
        assert np.all(np.abs(r.fac - rel[nome].fac) <= TOL5), nome
