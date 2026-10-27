"""Poder de discriminação das variantes escolhidas (03 §3, "Enumerar
variantes numéricas"): cada alternativa que PROVENIENCIA.md diz ter
descartado é recalculada aqui e não reproduz os bits do correli.out (ou erra
além da precisão do GEVAZP.REL), enquanto a variante escolhida reproduz.

Proveniência: P-EST-02, P-EST-04, P-ANU-01, P-ANU-03, P-FACP-01, P-LIN-01.
"""

import math

import numpy as np

from apoio_parp import ajustes, correli_da_serie
from pulsar import parp

N_SERIES = 25  # amostra (as primeiras séries da configuração) nos testes mais lentos


def _amostra(nome, n=N_SERIES):
    return list(ajustes(nome).values())[:n]


def _frac(iguais):
    assert iguais
    return sum(iguais) / len(iguais)


def _seq(v):
    return parp.soma(v)


def _rev(v):
    return parp.soma(list(v)[::-1])


def _pares8(a):
    """Soma por pares com 8 acumuladores (blocos de até 128)."""
    a = list(a)
    n = len(a)
    if n < 8:
        return _seq(a)
    if n <= 128:
        r = a[:8]
        i = 8
        while i < n - n % 8:
            for j in range(8):
                r[j] += a[i + j]
            i += 8
        s = ((r[0] + r[1]) + (r[2] + r[3])) + ((r[4] + r[5]) + (r[6] + r[7]))
        for x in a[i:]:
            s += x
        return s
    h = n // 2 - (n // 2) % 8
    return _pares8(a[:h]) + _pares8(a[h:])


def _kahan(a):
    s = c = 0.0
    for x in a:
        y = x - c
        t = s + y
        c = (t - s) - y
        s = t
    return s


# --------------------------------------------------------------------------
# P-EST-02: desvio


def test_desvio_variantes(pacote):
    ok = {k: [] for k in ("escolhida", "reversa", "pares8", "kahan", "z2-mu2")}
    for aj in ajustes(pacote.nome).values():
        s = correli_da_serie(pacote.nome, aj.serie.nome)
        z = aj.serie.valores
        for m in range(12):
            c = z[:, m].tolist()
            n, mu = len(c), aj.est.media[m]
            d = [(v - mu) * (v - mu) for v in c]
            ok["escolhida"].append(math.sqrt(_seq(d) / n) == s.desvio[m])
            ok["reversa"].append(math.sqrt(_rev(d) / n) == s.desvio[m])
            ok["pares8"].append(math.sqrt(_pares8(d) / n) == s.desvio[m])
            ok["kahan"].append(math.sqrt(_kahan(d) / n) == s.desvio[m])
            ok["z2-mu2"].append(math.sqrt(_seq(v * v for v in c) / n - mu * mu) == s.desvio[m])
    assert _frac(ok.pop("escolhida")) == 1.0
    for k, v in ok.items():
        assert _frac(v) < 0.6, k


# --------------------------------------------------------------------------
# P-EST-04: correlograma


def test_correlograma_variantes(pacote):
    """Soma direta; e, com a soma reversa escolhida, padronizar antes de
    multiplicar, /(N·σσ) e /N/σ/σ."""
    ok = {k: [] for k in ("escolhida", "direta", "padroniza", "N*ss", "/s/s")}
    for aj in _amostra(pacote.nome):
        s = correli_da_serie(pacote.nome, aj.serie.nome)
        x = aj.serie.valores.reshape(-1).tolist()
        mu, sd, n = aj.est.media, aj.est.desvio, aj.est.n_anos
        for k in range(1, 12):
            for m in range(12):
                mk = (m - k) % 12
                ts = [12 * i + m for i in range(n) if 12 * i + m - k >= 0]
                p = [(x[t] - mu[m]) * (x[t - k] - mu[mk]) for t in ts]
                pz = [((x[t] - mu[m]) / sd[m]) * ((x[t - k] - mu[mk]) / sd[mk]) for t in ts]
                alvo = s.fac[k - 1, m]
                ok["escolhida"].append(_rev(p) / n / (sd[m] * sd[mk]) == alvo)
                ok["direta"].append(_seq(p) / n / (sd[m] * sd[mk]) == alvo)
                ok["padroniza"].append(_rev(pz) / n == alvo)
                ok["N*ss"].append(_rev(p) / (n * sd[m] * sd[mk]) == alvo)
                ok["/s/s"].append(_rev(p) / n / sd[m] / sd[mk] == alvo)
    assert _frac(ok.pop("escolhida")) == 1.0
    for k, v in ok.items():
        assert _frac(v) < 0.9, k


# --------------------------------------------------------------------------
# P-ANU-01 e P-ANU-03: componente anual, sondada pela FACP de lag 1


def _facp_lag1(aj, a, forma_corr):
    """FACP de lag 1 = (ρ1 - a0 a1)/(√(1-a0²)√(1-a1²)) com a série anual
    ``a`` (achatada) e a correlação Z×A na ``forma_corr``."""
    est, n = aj.est, aj.est.n_anos
    x = aj.serie.valores.reshape(-1).tolist()
    a2 = np.array(a).reshape(n, 12)
    mua = [_seq(a2[1:, m].tolist()) / (n - 1) for m in range(12)]
    sda = [math.sqrt(_seq([(v - mua[m]) * (v - mua[m]) for v in a2[1:, m].tolist()]) / (n - 1)) for m in range(12)]

    def corr(k, m):
        mk = (m - k) % 12
        ts = [12 * i + m for i in range(n - 1, 0, -1)]
        if forma_corr == "covariancia":
            p = [(a[t] - mua[m]) * (x[t - k] - est.media[mk]) for t in ts]
            return _seq(p) / n / (sda[m] * est.desvio[mk])
        p = [((a[t] - mua[m]) / sda[m]) * ((x[t - k] - est.media[mk]) / est.desvio[mk]) for t in ts]
        return _seq(p) / n if forma_corr == "padronizada" else _seq(p[::-1]) / n  # "padronizada_direta"

    out = []
    for m in range(12):
        a0, a1, r1 = corr(0, m), corr(1, m), est.fac[1, m]
        out.append((r1 - a0 * a1) / (math.sqrt(1 - a0 * a0) * math.sqrt(1 - a1 * a1)))
    return out


def _serie_a(aj, forma):
    x = aj.serie.valores.reshape(-1).tolist()
    a = [0.0] * len(x)
    for t in range(12, len(x)):
        j = x[t - 12:t]
        a[t] = {"escolhida": _seq(j) / 12, "vezes_1/12": _seq(j) * (1 / 12), "termo_a_termo": _seq(v / 12 for v in j)}[forma]
    return a


def test_componente_anual_variantes(pacote):
    """P-ANU-01: Σ·(1/12) e Σ(z/12); P-ANU-03: forma de covariância e forma
    padronizada com soma do 2º ao último ano (a escolhida soma do último ao
    2º)."""
    ok = {k: [] for k in ("escolhida", "vezes_1/12", "termo_a_termo", "covariancia", "padronizada_direta")}
    for aj in _amostra(pacote.nome):
        alvo = correli_da_serie(pacote.nome, aj.serie.nome).facp[0]
        for k in ok:
            forma_a = k if k in ("escolhida", "vezes_1/12", "termo_a_termo") else "escolhida"
            forma_c = k if k in ("covariancia", "padronizada_direta") else "padronizada"
            ok[k] += list(np.array(_facp_lag1(aj, _serie_a(aj, forma_a), forma_c)) == alvo)
    assert _frac(ok.pop("escolhida")) == 1.0
    for k, v in ok.items():
        assert _frac(v) < 0.9, k


# --------------------------------------------------------------------------
# P-FACP-01: FACP


def test_facp_definicoes_alternativas_erram_alem_do_rel(pacote):
    """φ_kk do Yule-Walker aumentado e correlação parcial sem A erram mais de
    0,1 em alguma série (o REL imprime 5 casas)."""
    for aj in _amostra(pacote.nome, 5):
        alvo = correli_da_serie(pacote.nome, aj.serie.nome).facp
        yw = np.array([[parp.yule_walker(aj.est, aj.anual, m, k)[0][-1] for m in range(12)] for k in range(1, 12)])
        sem_a = parp.facp(aj.est, None, 11, "parcial")
        assert np.abs(yw - alvo).max() > 0.1, aj.serie.nome
        assert np.abs(sem_a - alvo).max() > 0.1, aj.serie.nome


def test_facp_arranjos_alternativos(pacote):
    """Σ12 (Σ22⁻¹ Σ21) e sqrt(Σ̄11·Σ̄22), nos lags k ≥ 2."""
    ok = {k: [] for k in ("escolhida", "S12(invS21)", "sqrt(produto)")}
    prod = parp._produto
    for aj in _amostra(pacote.nome, 10):
        alvo = correli_da_serie(pacote.nome, aj.serie.nome).facp
        for k in range(2, 12):
            for m in range(12):
                s = parp._matriz(aj.est, aj.anual, m, k)
                o1 = [0, k]
                o2 = [i for i in range(len(s)) if i not in o1]
                s11 = [[s[i][j] for j in o1] for i in o1]
                s12 = [[s[i][j] for j in o2] for i in o1]
                s21 = [[s[i][j] for j in o1] for i in o2]
                inv = parp.inversa([[s[i][j] for j in o2] for i in o2])
                for nome, p in (("escolhida", prod(prod(s12, inv), s21)), ("S12(invS21)", prod(s12, prod(inv, s21)))):
                    b = [[s11[i][j] - p[i][j] for j in range(2)] for i in range(2)]
                    ok[nome].append(b[0][1] / (math.sqrt(b[0][0]) * math.sqrt(b[1][1])) == alvo[k - 1, m])
                    if nome == "escolhida":
                        ok["sqrt(produto)"].append(b[0][1] / math.sqrt(b[0][0] * b[1][1]) == alvo[k - 1, m])
    assert _frac(ok.pop("escolhida")) == 1.0
    for k, v in ok.items():
        assert _frac(v) < 0.9, k


# --------------------------------------------------------------------------
# P-LIN-01: solução dos sistemas


def _gauss_jordan(a, pivo_total=False, multiplica=False):
    """Variantes do Gauss-Jordan: pivô total (como o gaussj do Numerical
    Recipes) e multiplicação pelo inverso do pivô."""
    n = len(a)
    a = [r[:] for r in a]
    ipiv, indxr, indxc = [0] * n, [0] * n, [0] * n
    for i in range(n):
        irow = icol = i
        if pivo_total:
            big = 0.0
            for j in range(n):
                if ipiv[j] != 1:
                    for k in range(n):
                        if ipiv[k] == 0 and abs(a[j][k]) >= big:
                            big, irow, icol = abs(a[j][k]), j, k
        ipiv[icol] += 1
        if irow != icol:
            a[irow], a[icol] = a[icol], a[irow]
        indxr[i], indxc[i] = irow, icol
        piv = a[icol][icol]
        a[icol][icol] = 1.0
        a[icol] = [v * (1.0 / piv) for v in a[icol]] if multiplica else [v / piv for v in a[icol]]
        for r in range(n):
            if r != icol:
                f = a[r][icol]
                a[r][icol] = 0.0
                a[r] = [a[r][j] - a[icol][j] * f for j in range(n)]
    for l in range(n - 1, -1, -1):
        if indxr[l] != indxc[l]:
            for row in a:
                row[indxr[l]], row[indxc[l]] = row[indxc[l]], row[indxr[l]]
    return a


def _cholesky_nr(a, b, k_decrescente):
    """choldc + cholsl do Numerical Recipes."""
    n = len(a)
    a = [r[:] for r in a]
    p = [0.0] * n
    for i in range(n):
        for j in range(i, n):
            s = a[i][j]
            for k in (range(i - 1, -1, -1) if k_decrescente else range(i)):
                s -= a[i][k] * a[j][k]
            if i == j:
                p[i] = math.sqrt(s)
            else:
                a[j][i] = s / p[i]
    x = [0.0] * n
    for i in range(n):
        s = b[i]
        for k in (range(i - 1, -1, -1) if k_decrescente else range(i)):
            s -= a[i][k] * x[k]
        x[i] = s / p[i]
    for i in range(n - 1, -1, -1):
        s = x[i]
        for k in (range(i + 1, n) if k_decrescente else range(n - 1, i, -1)):
            s -= a[k][i] * x[k]
        x[i] = s / p[i]
    return x


def test_solucao_variantes(pacote):
    """Todas as séries: só o Gauss-Jordan sem pivô, dividindo pelo pivô, com
    A⁻¹b em soma direta reproduz todos os bits de φ; o Cholesky do
    Numerical Recipes (k crescente ou decrescente), o LAPACK e o Cholesky do
    NumPy ficam abaixo de 30%."""
    ok = {k: [] for k in ("escolhida", "gj_pivo_total", "gj_multiplica", "inv_b_reversa",
                          "chol_nr_desc", "chol_nr_asc", "lapack", "chol_numpy")}
    for aj in ajustes(pacote.nome).values():
        s = correli_da_serie(pacote.nome, aj.serie.nome)
        for m, md in enumerate(aj.modelos):
            p = md.ordem
            if p == 0:
                continue
            mat = parp._matriz(aj.est, aj.anual, m, p)
            M = [r[1:] for r in mat[1:]]
            b = [r[0] for r in mat[1:]]
            alvo = s.coeficientes[m]

            def igual(x):
                return np.array_equal(np.array(x[:p]), alvo)

            def aplica(inv, rev=False):
                return [_rev([r[j] * b[j] for j in range(len(b))]) if rev else _seq(r[j] * b[j] for j in range(len(b)))
                        for r in inv]

            ok["escolhida"].append(igual(aplica(parp.inversa(M))))
            ok["gj_pivo_total"].append(igual(aplica(_gauss_jordan(M, pivo_total=True))))
            ok["gj_multiplica"].append(igual(aplica(_gauss_jordan(M, multiplica=True))))
            ok["inv_b_reversa"].append(igual(aplica(parp.inversa(M), rev=True)))
            ok["chol_nr_desc"].append(igual(_cholesky_nr(M, b, True)))
            ok["chol_nr_asc"].append(igual(_cholesky_nr(M, b, False)))
            ok["lapack"].append(igual(list(np.linalg.solve(np.array(M), np.array(b)))))
            L = np.linalg.cholesky(np.array(M))
            ok["chol_numpy"].append(igual(list(np.linalg.solve(L.T, np.linalg.solve(L, np.array(b))))))
    assert _frac(ok.pop("escolhida")) == 1.0
    for k in ("gj_pivo_total", "gj_multiplica", "inv_b_reversa"):
        assert _frac(ok[k]) < 0.95, k
    for k in ("chol_nr_desc", "chol_nr_asc", "lapack", "chol_numpy"):
        assert _frac(ok[k]) < 0.30, k
