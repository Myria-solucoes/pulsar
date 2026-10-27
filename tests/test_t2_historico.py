"""T2: séries incrementais, janela de anos, médias e desvios mensais e
componente anual, contra o correli.out (float64) e o GEVAZP.REL.

Proveniência: P-HIST-01..03, P-EST-01..02, P-ANU-01..02.
"""

import numpy as np

import apoio
import base
from apoio_parp import ajustes, correli_da_serie, series
from pulsar import historico

TOL2 = 0.005 + 1e-9  # 2 casas do GEVAZP.REL


def test_incrementais_iguais_ao_rel(pacote):
    """P-HIST-01: todas as seções 'SERIE DE VAZOES INCREMENTAIS' do REL
    (inclusive NW, posto lateral e incrementais nulas) são reproduzidas."""
    rel = apoio.series_rel(pacote.nome)
    nossas = {s.nome: s for s in series(pacote.nome)}
    assert list(nossas) == list(rel)  # mesmas séries, mesma ordem
    for nome, r in rel.items():
        s = nossas[nome]
        ref = np.array([r.historico[a] for a in s.anos])
        assert sorted(r.historico) == list(s.anos), nome
        assert np.array_equal(s.valores, ref), nome


def test_janela_de_anos(pacote):
    """P-HIST-02 (lacuna L1): a janela é o período comum da configuração,
    não o fim do VAZOES.DAT."""
    d, c = base.deck(pacote.nome), base.configuracao(pacote.nome)
    anos = historico.janela(c)
    rel = apoio.series_rel(pacote.nome)
    for r in rel.values():
        assert tuple(sorted(r.historico)) == anos
    assert d.historico.ano_final > anos[-1]  # o histórico lido vai além


def test_series_ajustadas_sao_o_indice_do_correli(pacote):
    """P-HIST-03: séries com modelo = não PN e não nulas, na ordem da
    configuração (índice do correli e ordem do vordem.out)."""
    nint = apoio.nint_por_nome(pacote.nome)
    nossas = [nint[s.nome] for s in historico.series_ajustadas(series(pacote.nome))]
    assert tuple(nossas) == apoio.correli(pacote.nome).indice
    nulas = [s.nome for s in series(pacote.nome) if s.nula]
    assert nulas and all(nint[n] not in apoio.correli(pacote.nome).indice for n in nulas)


def test_media_e_desvio_bit_a_bit(pacote):
    """P-EST-01, P-EST-02: float64 iguais ao correli.out em todas as séries."""
    for nome, aj in ajustes(pacote.nome).items():
        s = correli_da_serie(pacote.nome, nome)
        assert np.array_equal(aj.est.media, s.media), nome
        assert np.array_equal(aj.est.desvio, s.desvio), nome


def test_componente_anual_igual_ao_rel(pacote):
    """P-ANU-01, P-ANU-02: 'SERIE DE MEDIA ULTIMOS 12 MESES' (1º ano zerado)
    e sua média e desvio (2 casas). O denominador N-1 é discriminado: com N
    a média de JAN de CAMARGOS seria 126.26, não 127.62."""
    rel = apoio.series_rel(pacote.nome)
    for nome, aj in ajustes(pacote.nome).items():
        assert aj.anual is not None
        r = rel[nome]
        ref = np.array([r.serie_anual[a] for a in aj.serie.anos])
        assert np.all(np.abs(aj.anual.serie - ref) <= TOL2), nome
        assert np.all(np.abs(aj.anual.media - r.media_anual) <= TOL2), nome
        assert np.all(np.abs(aj.anual.desvio - r.desvio_anual) <= TOL2), nome
        assert not np.any(aj.anual.serie[0])
