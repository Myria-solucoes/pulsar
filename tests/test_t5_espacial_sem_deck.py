"""T5 sem deck: Jacobi, tratamento de autovalores e opções da matriz de
carga (P-ESP-05..09)."""

import math

import numpy as np
import pytest

import base  # noqa: F401 (caminhos)
from pulsar import espacial as E
from pulsar.configuracao import EXISTENTE, LATERAL
from pulsar.historico import SerieIncremental


def _serie(numero, valores, status=EXISTENTE, anos=None):
    v = np.asarray(valores, dtype=np.float64)
    anos = anos or tuple(range(2000, 2000 + v.shape[0]))
    return SerieIncremental(numero, f"S{numero}", numero, status, anos, v)


def test_jacobi_2x2_analitico():
    a = np.array([[2.0, 1.0], [1.0, 2.0]])
    esp = E.jacobi(a)
    assert sorted(esp.autovalores) == pytest.approx([1.0, 3.0], abs=1e-15)
    v = esp.autovetores
    assert np.allclose(np.abs(v), np.sqrt(0.5), atol=1e-15)
    assert esp.rotacoes == 1


def test_jacobi_diagonal_sem_rotacao():
    esp = E.jacobi(np.diag([3.0, 1.0, 2.0]))
    assert esp.rotacoes == 0 and esp.varreduras == 0
    assert list(esp.autovalores) == [3.0, 1.0, 2.0]
    assert np.array_equal(esp.autovetores, np.eye(3))


def test_jacobi_contra_lapack_em_matriz_aleatoria():
    rng = np.random.default_rng(7)
    x = rng.standard_normal((40, 25))
    a = x @ x.T / 25  # 40 × 40, posto 25: autovalores nulos e negativos de arredondamento
    a = (a + a.T) / 2
    esp = E.jacobi(a)
    assert np.max(np.abs(np.sort(esp.autovalores) - np.linalg.eigvalsh(a))) < 1e-12
    v = esp.autovetores
    assert np.max(np.abs(v.T @ v - np.eye(40))) < 1e-13
    assert np.max(np.abs((v * esp.autovalores) @ v.T - a)) < 1e-12


def test_jacobi_recusa_assimetrica_e_limita_varreduras():
    with pytest.raises(E.ErroCorrelacao):
        E.jacobi(np.array([[1.0, 0.5], [0.4, 1.0]]))
    a = np.random.default_rng(3).standard_normal((12, 12))
    with pytest.raises(E.ErroCorrelacao):
        E.jacobi(a + a.T, varreduras_maximas=1)


def test_tratamento_dos_autovalores():
    lam = np.array([4.0, 0.0, -1e-15])
    assert list(E.raiz_dos_autovalores(lam)) == [2.0, 0.0, 0.0]
    assert E.raiz_dos_autovalores(lam, "abs")[2] == np.sqrt(1e-15)
    with pytest.raises(E.ErroCorrelacao):
        E.raiz_dos_autovalores(lam, "erro")
    assert list(E.raiz_dos_autovalores(lam[:2], "erro")) == [2.0, 0.0]
    with pytest.raises(ValueError):
        E.raiz_dos_autovalores(lam, "piso")


def test_carga_de_matriz_de_posto_incompleto():
    """D D' = U e D simétrica com mais séries que anos (posto N-1)."""
    rng = np.random.default_rng(11)
    ss = [_serie(k + 1, rng.gamma(2.0, 50.0, size=(6, 12))) for k in range(9)]
    u = E.correlacao_espacial(ss).mes(3)
    for modo in ("zero", "abs"):
        dc = E.matriz_de_carga(u, nao_positivos=modo)
        assert np.max(np.abs(dc.d - dc.d.T)) < 1e-14
        assert np.max(np.abs(dc.d @ dc.d.T - u)) < 1e-12
        assert (dc.espectro.autovalores > 1e-10).sum() == 5


def test_correlacao_trivial():
    """P-ESP-01..04 em série construída: correlação 1 e -1, série nula 0."""
    base_ = np.arange(1.0, 37.0).reshape(3, 12)
    ss = [_serie(1, base_), _serie(2, 2 * base_ + 5), _serie(3, -base_), _serie(4, np.zeros((3, 12)))]
    c = E.correlacao_espacial(ss)
    assert c.matriz.shape == (13, 4, 4)
    for m in range(13):
        assert c.matriz[m, 0, 1] == pytest.approx(1.0, abs=1e-15)
        assert c.matriz[m, 0, 2] == pytest.approx(-1.0, abs=1e-15)
        assert list(c.matriz[m, 3]) == [0.0, 0.0, 0.0, 1.0]
    r = c.restrita([3, 1])
    assert r.numeros == (3, 1) and r.matriz[0, 0, 1] == c.matriz[0, 2, 0]
    with pytest.raises(E.ErroCorrelacao):
        E.correlacao_espacial([_serie(1, base_), _serie(2, base_, anos=(1, 2, 3))])


def test_series_da_carga_e_matriz_do_estudo():
    v = np.arange(1.0, 37.0).reshape(3, 12)
    ss = [_serie(1, v), _serie(2, np.zeros((3, 12))), _serie(3, v[::-1], status=LATERAL)]
    assert [s.numero for s in E.series_da_carga(ss)] == [1]
    assert [s.numero for s in E.series_da_carga(ss, laterais="dentro")] == [1, 3]
    with pytest.raises(ValueError):
        E.series_da_carga(ss, laterais="talvez")
    c = E.correlacao_espacial([ss[0], ss[2]])
    assert np.array_equal(E.matriz_do_estudo(c, 5, 1), c.matriz[4])
    assert np.array_equal(E.matriz_do_estudo(c, 5, 0), c.anual)
    with pytest.raises(E.ErroCorrelacao):
        E.matriz_do_estudo(c, 5, None)
    with pytest.raises(E.ErroCorrelacao):
        E.matriz_do_estudo(c, 5, 2)


def _jacobi_laco_nr(a, n_max=50):
    """Referência em Python puro com os laços do NR §11.1 (S somado em p e
    depois q; laços em j escalares), para conferir a versão vetorizada."""
    n = len(a)
    a = [list(map(float, r)) for r in a]
    v = [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]
    b = [a[i][i] for i in range(n)]
    d = b[:]
    z = [0.0] * n

    def rot(m, i, j, k, l, s, tau):
        g, h = m[i][j], m[k][l]
        m[i][j] = g - s * (h + g * tau)
        m[k][l] = h + s * (g - h * tau)

    for it in range(1, n_max + 1):
        sm = 0.0
        for ip in range(n - 1):
            for iq in range(ip + 1, n):
                sm += abs(a[ip][iq])
        if sm == 0.0:
            return d, v
        tresh = 0.2 * sm / (n * n) if it < 4 else 0.0
        for ip in range(n - 1):
            for iq in range(ip + 1, n):
                g = 100.0 * abs(a[ip][iq])
                if it > 4 and abs(d[ip]) + g == abs(d[ip]) and abs(d[iq]) + g == abs(d[iq]):
                    a[ip][iq] = 0.0
                elif abs(a[ip][iq]) > tresh:
                    h = d[iq] - d[ip]
                    if abs(h) + g == abs(h):
                        t = a[ip][iq] / h
                    else:
                        theta = 0.5 * h / a[ip][iq]
                        t = 1.0 / (abs(theta) + math.sqrt(1.0 + theta * theta))
                        if theta < 0.0:
                            t = -t
                    c = 1.0 / math.sqrt(1.0 + t * t)
                    s = t * c
                    tau = s / (1.0 + c)
                    h = t * a[ip][iq]
                    z[ip] -= h
                    z[iq] += h
                    d[ip] -= h
                    d[iq] += h
                    a[ip][iq] = 0.0
                    for j in range(ip):
                        rot(a, j, ip, j, iq, s, tau)
                    for j in range(ip + 1, iq):
                        rot(a, ip, j, j, iq, s, tau)
                    for j in range(iq + 1, n):
                        rot(a, ip, j, iq, j, s, tau)
                    for j in range(n):
                        rot(v, j, ip, j, iq, s, tau)
        for ip in range(n):
            b[ip] += z[ip]
            d[ip] = b[ip]
            z[ip] = 0.0
    raise AssertionError("sem convergência")


def test_jacobi_vetorizado_igual_ao_laco_do_nr_bit_a_bit():
    """P-ESP-06: mesmos bits da referência com os laços do NR."""
    rng = np.random.default_rng(5)
    x = rng.standard_normal((14, 9))
    a = x @ x.T / 9
    a = np.triu(a) + np.triu(a, 1).T  # simétrica bit a bit
    esp = E.jacobi(a)
    d, v = _jacobi_laco_nr(a.tolist())
    assert np.array_equal(esp.autovalores, np.array(d))
    assert np.array_equal(esp.autovetores, np.array(v))


def test_desvio_nulo_em_serie_nao_nula():
    """P-ESP-03: série identicamente nula vale 0 sempre; mês de desvio nulo
    numa série não nula é erro (padrão) ou 0 com desvio_nulo='zero'."""
    v = np.arange(1.0, 37.0).reshape(3, 12)
    w = v.copy()
    w[:, 4] = 7.0  # maio constante
    ss = [_serie(1, v), _serie(2, w), _serie(3, np.zeros((3, 12)))]
    with pytest.raises(E.ErroCorrelacao):
        E.correlacao_espacial(ss)
    c = E.correlacao_espacial(ss, desvio_nulo="zero")
    assert list(c.mes(5)[1]) == [0.0, 1.0, 0.0]
    assert c.mes(4)[0, 1] == pytest.approx(1.0, abs=1e-15)
    E.correlacao_espacial([ss[0], ss[2]])  # só a série nula: sem erro
    with pytest.raises(ValueError):
        E.correlacao_espacial(ss, desvio_nulo="talvez")


def test_soma_do_produto_parametrizavel():
    """P-ESP-08: 'numpy' e 'sequencial' dão D iguais a poucos ulps."""
    rng = np.random.default_rng(13)
    ss = [_serie(k + 1, rng.gamma(2.0, 50.0, size=(8, 12))) for k in range(6)]
    u = E.correlacao_espacial(ss).anual
    d1 = E.matriz_de_carga(u).d
    d2 = E.matriz_de_carga(u, soma_produto="sequencial").d
    assert np.max(np.abs(d1 - d2)) < 1e-14
    assert np.max(np.abs(d2 @ d2.T - u)) < 1e-13
    with pytest.raises(ValueError):
        E.matriz_de_carga(u, soma_produto="kahan")
