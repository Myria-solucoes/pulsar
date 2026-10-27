"""T10: K-means do AS 136 (P-KM-01..06), ruídos (P-RUI-*) e agregação (P-AGR-*), sem deck."""

import numpy as np
import pytest

import base  # noqa: F401
from pulsar.estocastico import agregacao as AG
from pulsar.estocastico import ruidos as R
from pulsar.estocastico.kmeans import ErroKmeans, kmns


def _otimo_hartigan_wong(a, r) -> int:
    """Pontos que violam o critério de parada do AS 136: nenhuma
    transferência isolada reduz a soma de quadrados dentro dos grupos, isto
    é, para todo L ≠ L1, D(I,L)·NC(L)/(NC(L)+1) ≥ D(I,L1)·NC(L1)/(NC(L1)-1)."""
    a = a.astype(np.float64)
    c = r.centros.astype(np.float64)
    nc = r.contagens
    d = ((a[:, None, :] - c[None]) ** 2).sum(-1)
    an1 = np.where(nc > 1, nc / np.maximum(nc - 1, 1), np.inf)
    an2 = nc / (nc + 1)
    proprio = d[np.arange(len(a)), r.grupo] * an1[r.grupo]
    outros = d * an2[None]
    outros[np.arange(len(a)), r.grupo] = np.inf
    return int((outros.min(1) < proprio * (1 - 1e-6)).sum())


@pytest.mark.parametrize("m,n,k", [(300, 3, 7), (2000, 10, 20), (3000, 30, 45)])
def test_otimo_local_e_centros_medias(m, n, k):
    """P-KM-02: na saída do KMNS os centros são as médias dos grupos
    (rótulo 150) e nenhum ponto melhora com uma transferência isolada."""
    rng = np.random.default_rng(m)
    a = rng.standard_normal((m, n))
    r = kmns(a, a[rng.choice(m, k, replace=False)])
    assert r.ifault == 0
    assert _otimo_hartigan_wong(a, r) == 0
    for g in range(k):
        assert np.allclose(r.centros[g], a[r.grupo == g].mean(0), atol=1e-12)
    assert r.contagens.sum() == m and (r.contagens > 0).all()


@pytest.mark.parametrize("m,n,k", [(2000, 10, 20), (3000, 30, 45)])
def test_distancia_blas_e_sequencial_dao_os_mesmos_grupos(m, n, k):
    """P-KM-01/P-KM-03: o modo "blas" (expansão em float64 e varredura por
    argmin) dá os mesmos grupos e as mesmas iterações do modo "sequencial"
    (somas em J e varredura com R2 corrente, como no Fortran); em float32 (o
    REAL do as136.f) o modo sequencial também chega a um ótimo local."""
    rng = np.random.default_rng(n)
    a = rng.standard_normal((m, n))
    c0 = a[rng.choice(m, k, replace=False)]
    r1 = kmns(a, c0, distancia="blas")
    r2 = kmns(a, c0, distancia="sequencial")
    assert np.array_equal(r1.grupo, r2.grupo) and r1.iteracoes == r2.iteracoes
    a32 = a.astype(np.float32)
    r3 = kmns(a32, a32[rng.choice(m, k, replace=False)], distancia="sequencial")
    assert r3.centros.dtype == np.float32 and _otimo_hartigan_wong(a32, r3) == 0


def test_exemplo_da_nota_tecnica_42():
    """Exemplo de Johnson e Wichern reproduzido na NT 42 (anexo do R13612,
    Tabelas 1–4): A(5,3), B(-1,1), C(1,-2), D(-3,-2), K = 2, partindo dos
    centroides de AB e CD; termina com os grupos A e BCD."""
    a = np.array([[5.0, 3.0], [-1.0, 1.0], [1.0, -2.0], [-3.0, -2.0]])
    r = kmns(a, np.array([[2.0, 2.0], [-1.0, -2.0]]))
    assert list(r.grupo) == [0, 1, 1, 1]
    assert np.allclose(r.centros, [[5.0, 3.0], [-1.0, -1.0]])


def test_ifault():
    """P-KM-05: K ≤ 1 ou K ≥ M é IFAULT 3 (erro); com iterações esgotadas,
    IFAULT 2 e centros finais ainda iguais às médias."""
    rng = np.random.default_rng(3)
    a = rng.standard_normal((50, 2))
    with pytest.raises(ErroKmeans):
        kmns(a, a[:1])
    with pytest.raises(ErroKmeans):
        kmns(a[:5], a[:5])
    a = rng.standard_normal((3000, 20))
    r = kmns(a, a[:60], iteracoes=1)
    assert r.ifault == 2
    for g in range(60):
        assert np.allclose(r.centros[g], a[r.grupo == g].mean(0))


def test_desempate_inicial_pelo_menor_indice():
    """P-KM-06: na alocação inicial (laço 50), empate de distância fica com o
    centro de menor índice (comparações estritas do Fortran)."""
    a = np.array([[0.0], [1.0], [-1.0], [9.0], [11.0]])
    r = kmns(a, np.array([[1.0], [-1.0], [10.0]]), iteracoes=0)
    # o ponto 0 está à distância 1 dos centros 0 e 1: fica com o 0
    assert r.grupo.tolist() == [0, 0, 1, 2, 2]


# --------------------------------------------------------------------------
# Ruídos (L6)


def test_coluna_por_posto_nao_depende_da_configuracao():
    """P-RUI-01/03: a coluna de um posto só depende da semente e do número
    do posto (robustez da versão 11 a entradas, saídas e reordenação)."""
    a = R.amostra_original([6, 1, 211], semente=7, n_objetos=1000)
    b = R.amostra_original([1, 211, 6, 17], semente=7, n_objetos=1000)
    assert np.array_equal(a[:, 0], b[:, 2]) and np.array_equal(a[:, 1], b[:, 0])
    assert np.array_equal(a[:, 2], b[:, 1])
    c = R.amostra_original([6], semente=8, n_objetos=1000)
    assert not np.array_equal(a[:, 0], c[:, 0])
    assert np.array_equal(R.amostra_original([6], 7, 1000), a[:, :1])


def test_amostra_normal_padrao_e_antitetica():
    """P-RUI-03/04: colunas N(0, 1) independentes; na variante antitética a
    segunda metade é a primeira com o sinal trocado (média exatamente 0)."""
    x = R.amostra_original(range(1, 6), 0, 50_000)
    assert np.all(np.abs(x.mean(0)) < 0.03) and np.all(np.abs(x.std(0) - 1) < 0.02)
    assert np.abs(np.corrcoef(x.T) - np.eye(5)).max() < 0.03
    y = R.amostra_original([3, 4], 0, 1000, simetria="antitetica")
    assert np.array_equal(y[500:], -y[:500]) and np.all(y[:500] + y[500:] == 0)
    with pytest.raises(ValueError):
        R.amostra_original([3], 0, 999, simetria="antitetica")
    with pytest.raises(ValueError):
        R.amostra_original([3, 3], 0, 10)


def test_centros_iniciais_sao_objetos_distintos():
    """P-RUI-05: K objetos distintos da amostra, sorteados pela semente."""
    i = R.sorteia_centros(50_000, 259, 5)
    assert len(set(i.tolist())) == 259 and i.min() >= 0 and i.max() < 50_000
    assert np.array_equal(i, R.sorteia_centros(50_000, 259, 5))
    assert not np.array_equal(i, R.sorteia_centros(50_000, 259, 6))


# --------------------------------------------------------------------------
# Agregação e fator de compensação (L7)


def test_fator_de_compensacao_eq_2_2():
    """P-AGR-04/05: FC = (Σ 1/σ_i)/N_UHE (R3383 eq. 2.2) com σ_i pela
    variante; "por_usina" divide cada componente pelo próprio σ_i."""
    rng = np.random.default_rng(0)
    c = rng.standard_normal((6, 3)) * [0.2, 0.3, 0.4]
    p = np.array([0.1, 0.2, 0.3, 0.15, 0.15, 0.1])
    mu = p @ c
    s_pond = np.sqrt(p @ (c - mu) ** 2)
    assert np.allclose(AG.desvios_dos_centroides(c, p, "ponderado"), s_pond)
    assert np.allclose(AG.desvios_dos_centroides(c, p, "simples"), c.std(0))
    assert np.allclose(AG.desvios_dos_centroides(c, p, "amostral"), c.std(0, ddof=1))
    assert np.allclose(AG.desvios_dos_centroides(c, p, "zero"), np.sqrt(p @ c ** 2))
    assert np.allclose(AG.fator_de_compensacao(s_pond, "escalar"), np.mean(1 / s_pond))
    assert np.allclose(AG.fator_de_compensacao(s_pond, "por_usina"), 1 / s_pond)
    with pytest.raises(ValueError):
        AG.fator_de_compensacao(np.array([1.0, 0.0]), "escalar")


def test_agregacao_probabilidades_e_compensacao():
    """M18 eq. 5.9 (P_k = NO_k/N) e R3383 eq. 2.2: os ruídos agregados com o
    FC "ponderado" têm desvio ponderado médio ≈ 1; recompensar com outra
    variante não muda centroides nem contagens."""
    op = AG.OpcoesAgregacao(n_objetos=4000)
    ag = AG.agregar(range(1, 11), 40, semente=3, opcoes=op)
    assert ag.contagens.sum() == 4000 and len(ag.contagens) == 40
    assert np.allclose(ag.probabilidades, ag.contagens / 4000)
    p = ag.probabilidades
    sd = np.sqrt(p @ (ag.ruidos - p @ ag.ruidos) ** 2)
    assert abs(sd.mean() - 1) < 0.02 and float(ag.fator) > 1
    s = AG.compensar(ag, "simples", "escalar")
    assert np.array_equal(s.centroides, ag.centroides) and np.array_equal(s.contagens, ag.contagens)
    assert not np.array_equal(s.fator, ag.fator)
    um = AG.agregar(range(1, 4), 1, semente=3, opcoes=op)
    assert um.contagens.tolist() == [4000] and float(um.fator) == 1.0
