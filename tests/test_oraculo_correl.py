"""correli.out e correlt.out contra o texto do GEVAZP.REL.

Proveniência: F2-CI-01..10, F2-CT-01..02.
"""

import math

import numpy as np
import pytest

import apoio
from apoio import correli, correlt, correlacoes_rel, estat_geradas_rel, mes_estocastico, nint_por_nome, series_rel

TOL5 = 0.5e-5 + 1e-12  # 5 casas
TOL2 = 0.005 + 1e-9  # 2 casas
TOL1 = 0.05 + 1e-9  # 1 casa


def _tol_e3(r):
    """Meia unidade do 3º algarismo significativo (formato 0.ddd E±ee)."""
    if r == 0:
        return 1e-12
    return 0.5 * 10 ** (math.floor(math.log10(abs(r))) - 2) * 1.0001


def _nint(nome, rel_nome):
    return nint_por_nome(nome)[rel_nome]


# --------------------------------------------------------------------------
# correli


def test_correli_indice_e_lista_historica(pacote):
    c = correli(pacote.nome)
    par = estat_geradas_rel(pacote.nome, "PROCESSO  PAR(P)")
    nomes_rel = list(series_rel(pacote.nome))
    # F2-CI-10: tamanho do bloco = 17 + 3·nl + 2·NH, com NH = len(H) = nº de
    # seções 'SERIE DE VAZOES INCREMENTAIS' do REL (157), e não 2·N (155)
    assert c.tamanho_bloco == 17 + 3 * 11 + 2 * len(nomes_rel)
    assert len(c.lista_historica) == len(nomes_rel)
    # índice = séries com página 'PROCESSO PAR(P)', na mesma ordem
    assert c.indice == tuple(_nint(pacote.nome, n) for n in par)
    # lista H = séries com seção 'SERIE DE VAZOES INCREMENTAIS', na mesma ordem
    assert c.lista_historica == tuple(_nint(pacote.nome, n) for n in nomes_rel)
    # H = índice + séries de incremental nula
    extra = set(c.lista_historica) - set(c.indice)
    for i in extra:
        nome = next(n for n, k in nint_por_nome(pacote.nome).items() if k == i)
        assert not any(v.any() for v in series_rel(pacote.nome)[nome].historico.values())


def test_correli_estatisticas_mensais_e_modelo(pacote):
    c = correli(pacote.nome)
    rel = series_rel(pacote.nome)
    nomes = {k: n for n, k in nint_por_nome(pacote.nome).items()}
    for i in c.indice:
        s, r = c.serie(i), rel[nomes[i]]
        assert np.all(np.abs(s.media - r.media) <= TOL2), nomes[i]
        assert np.all(np.abs(s.desvio - r.desvio) <= TOL2), nomes[i]
        assert np.all(np.abs(s.fac - r.fac) <= TOL5), nomes[i]
        assert np.all(np.abs(s.facp - r.facp) <= TOL5), nomes[i]
        assert list(s.ordens) == r.ordens, nomes[i]
        for m in range(12):
            assert len(s.coeficientes[m]) == len(r.coeficientes[m])
            for x, y in zip(s.coeficientes[m], r.coeficientes[m]):
                assert abs(x - y) <= _tol_e3(y), (nomes[i], m + 1, x, y)


def test_correli_estatistica_anual(pacote):
    """Registro anual: média, desvio (denominador N) e autocorrelação lag 1 das
    médias do ano civil, calculadas a partir do histórico impresso no REL."""
    c = correli(pacote.nome)
    rel = series_rel(pacote.nome)
    nomes = {k: n for n, k in nint_por_nome(pacote.nome).items()}
    for i in c.indice:
        h = rel[nomes[i]].historico
        a = np.array([h[ano].mean() for ano in sorted(h)])
        mu, d = a.mean(), a - a.mean()
        sd = math.sqrt((d * d).mean())
        r1 = (d[1:] * d[:-1]).sum() / (d * d).sum()
        an = c.serie(i).anual
        assert abs(an.media - mu) <= TOL2, nomes[i]
        assert abs(an.desvio - sd) <= TOL2, nomes[i]
        assert abs(an.autocorrelacao_lag1 - r1) <= 2e-4, nomes[i]
        assert abs(an.media - c.serie(i).media.mean()) <= 1e-9 * max(1, abs(an.media))


def test_correli_correlacao_historica(pacote):
    c = correli(pacote.nome)
    rel = correlacoes_rel(pacote.nome, "hist_principais")
    h = c.lista_historica
    perdidas = 0
    for (ni, nj), r in rel.items():
        i, j = _nint(pacote.nome, ni), _nint(pacote.nome, nj)
        b = c.correlacao_historica(i, j)
        if np.isnan(b).all():
            # linhas sobrescritas pela média/desvio gerados: as 2 últimas de H
            assert j in h[len(c.indice):] or h.index(j) >= len(c.indice), (ni, nj)
            perdidas += 1
            continue
        assert np.all(np.abs(b - r) <= TOL5), (ni, nj)
    n_extra = len(h) - len(c.indice)
    assert sum(np.isnan(v).all() for v in c.corr_historica.values()) == n_extra * len(c.indice)
    assert perdidas > 0


def test_correli_correlacao_sintetica(pacote):
    c = correli(pacote.nome)
    rel = correlacoes_rel(pacote.nome, "sint_principais")
    assert len(rel) == len(c.indice) * (len(c.indice) - 1) // 2
    for (ni, nj), r in rel.items():
        b = c.correlacao_sintetica(_nint(pacote.nome, ni), _nint(pacote.nome, nj))
        assert np.all(np.abs(b - r) <= TOL5), (ni, nj)
    for i in c.indice:
        assert np.all(c.correlacao_sintetica(i, i)[:12] == 1.0)


def test_correli_media_e_desvio_gerados(pacote):
    """Linhas HIST e GER de 'PROCESSO PAR(P)' (1 casa)."""
    c = correli(pacote.nome)
    rel = estat_geradas_rel(pacote.nome, "PROCESSO  PAR(P)")
    mes = mes_estocastico(pacote.nome)
    for nome, r in rel.items():
        s = c.serie(_nint(pacote.nome, nome))
        assert np.all(np.abs(s.media - r["media_hist"]) <= TOL1), nome
        assert np.all(np.abs(s.desvio - r["desvio_hist"]) <= TOL1), nome
        assert np.all(np.abs(s.media_gerada - r["media_ger"]) <= TOL1), nome
        assert np.all(np.abs(s.desvio_gerado - r["desvio_ger"]) <= TOL1), nome
        outros = np.delete(s.media_gerada, mes - 1)
        assert not outros.any() and not s.fac_gerada.any()


# --------------------------------------------------------------------------
# correlt


def test_correlt_indice(pacote):
    c = correlt(pacote.nome)
    assert c.indice == tuple(range(1, len(nint_por_nome(pacote.nome)) + 1))
    assert c.lista_historica == c.indice
    # F2-CI-10: no correlt NH = N e o bloco não tem folga: L = 5 + 2·nl + 2·N
    assert c.tamanho_bloco == 5 + 2 * 11 + 2 * len(c.indice)
    assert not any(np.isnan(v).any() for v in c.corr_historica.values())


def test_correlt_estatisticas(pacote):
    """Linhas HIST/GER de 'RESULTADOS PARA VAZOES TOTALIZADAS' (1 casa)."""
    c = correlt(pacote.nome)
    rel = estat_geradas_rel(pacote.nome, "RESULTADOS PARA VAZOES TOTALIZADAS")
    assert len(rel) > 140
    for nome, r in rel.items():
        s = c.serie(_nint(pacote.nome, nome))
        assert np.all(np.abs(s.media - r["media_hist"]) <= TOL1), nome
        assert np.all(np.abs(s.desvio - r["desvio_hist"]) <= TOL1), nome
        assert np.all(np.abs(s.media_gerada - r["media_ger"]) <= TOL1), nome
        assert np.all(np.abs(s.desvio_gerado - r["desvio_ger"]) <= TOL1), nome
    for s in c.series.values():
        assert abs(s.anual.media - s.media.mean()) <= 1e-9 * max(1, abs(s.anual.media))


def test_correlt_correlacoes(pacote):
    c = correlt(pacote.nome)
    for tabela, obter in [("hist_todos", c.correlacao_historica), ("sint_todos", c.correlacao_sintetica)]:
        rel = correlacoes_rel(pacote.nome, tabela)
        # o REL da versão 10.0.0 lista só 153 das 170 séries do correlt (sem
        # JIRAU, BELO MONTE, ...); os pares entre as listadas estão todos lá
        listadas = {n for par in rel for n in par}
        assert listadas <= {u.nome for u in apoio.config(pacote.nome) if u.nint in c.indice}
        assert len(rel) == len(listadas) * (len(listadas) - 1) // 2
        assert len(listadas) == len(c.indice) or len(listadas) >= 0.85 * len(c.indice)
        for (ni, nj), r in rel.items():
            b = obter(_nint(pacote.nome, ni), _nint(pacote.nome, nj))
            assert np.all(np.abs(b - r) <= TOL5), (tabela, ni, nj)


def test_correl_camargos_202609(pacote):
    """Amostra legível: CAMARGOS no 202609."""
    if pacote.nome != "202609":
        pytest.skip("amostra legível escrita para o 202609")
    s = correli(pacote.nome).serie(1)
    assert round(s.media[0], 2) == 242.03 and round(s.desvio[0], 2) == 103.66
    assert round(s.fac[0, 0], 5) == 0.46782  # CORRELOGRAMA, ordem 1, JAN
    assert round(s.facp[1, 7], 5) == -0.34724  # PARCIAL, ordem 2, AGO
    assert s.ordens == (1, 1, 1, 7, 8, 2, 4, 2, 4, 5, 2, 2)
    assert round(s.coeficientes[7][0], 2) == 1.13  # "0.113E+01"
    assert round(s.media_gerada[9], 4) == 56.3444  # QUANTIL.CSV MEDIA GER
    assert round(correli(pacote.nome).correlacao_historica(1, 3)[12], 5) == 0.80351
