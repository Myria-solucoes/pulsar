"""T5: correlação espacial mensal e anual das incrementais (contra o
correli.out em float64 e o GEVAZP.REL) e matriz de carga D.

Proveniência: P-ESP-01..10.
"""

import functools

import numpy as np

import apoio
import base
from apoio_parp import series
from pulsar import espacial as E

TOL5 = 0.5e-5 + 1e-12  # 5 casas do GEVAZP.REL


@functools.lru_cache(maxsize=None)
def correlacao(nome):
    """Todas as séries com seção incremental no REL (lista H do correli)."""
    return E.correlacao_espacial(series(nome))


@functools.lru_cache(maxsize=None)
def carga(nome):
    sel = E.series_da_carga(series(nome))
    c = E.correlacao_espacial(sel)
    v = base.deck(nome).dadger.vazoes
    u = E.matriz_do_estudo(c, apoio.mes_estocastico(nome), v.matriz_mensal)
    return c, u, E.matriz_de_carga(u, c.numeros)


def _nint(nome, c):
    nint = apoio.nint_por_nome(nome)
    return [nint[n] for n in c.nomes]


# --------------------------------------------------------------------------
# Matriz de correlação (T5)


def test_correlacao_bit_a_bit_com_o_correli(pacote):
    """P-ESP-01..04: os 12 meses e a anual de todos os pares gravados no
    correli.out (157 × 157, inclusive diagonal e séries de incremental nula)
    são iguais em float64."""
    c = correlacao(pacote.nome)
    ci = apoio.correli(pacote.nome)
    num = _nint(pacote.nome, c)
    assert tuple(num) == ci.lista_historica
    iguais = total = perdidos = 0
    for a, i in enumerate(num):
        for b, j in enumerate(num):
            ref = ci.correlacao_historica(i, j)
            if np.isnan(ref).any():  # linhas sobrescritas (F2-CI-07)
                perdidos += 1
                continue
            total += 1
            iguais += np.array_equal(c.matriz[:, a, b], ref)
    # pares com as k = NH - N últimas de H (sobrescritas, F2-CI-07), fora da
    # diagonal delas: k·NH - k² (2026: k = 2; 2022: k = 1)
    k = len(num) - len(ci.indice)
    assert perdidos == k * len(num) - k * k
    assert iguais == total


def test_correlacao_igual_ao_rel(pacote):
    """Os 12 246 pares da tabela histórica 'POSTOS PRINCIPAIS' do REL (5
    casas), que cobrem também os pares perdidos no correli.out."""
    c = correlacao(pacote.nome)
    pos = {n: k for k, n in enumerate(c.nomes)}
    rel = apoio.correlacoes_rel(pacote.nome, "hist_principais")
    n = len(c.nomes)
    assert len(rel) == n * (n - 1) // 2
    for (ni, nj), r in rel.items():
        assert np.all(np.abs(c.matriz[:, pos[ni], pos[nj]] - r) <= TOL5), (ni, nj)


def test_diagonal_simetria_e_series_nulas(pacote):
    """P-ESP-02/03: diagonal 1 exata, matriz simétrica bit a bit, pares com
    série de incremental nula (ITUTINGA, PARANAPANEMA) valem 0."""
    c = correlacao(pacote.nome)
    nulas = [k for k, s in enumerate(series(pacote.nome)) if s.nula]
    assert nulas  # 2026: ITUTINGA e PARANAPANEMA; 2022: só ITUTINGA
    for m in range(13):
        u = c.matriz[m]
        assert np.array_equal(np.diag(u), np.ones(len(u)))
        assert np.array_equal(u, u.T)
        for k in nulas:
            assert not np.any(np.delete(u[k], k))


def test_media_anual_do_ano_civil(pacote):
    """P-ESP-04: a série anual é a média do ano civil; média e desvio dela
    (denominador N) são os do registro anual do correli.out, a 1e-14
    relativo. O registro anual (F2-CI-08) não usa a mesma ordem de soma: a
    média difere em 1 ulp em algumas séries, mas os bits da correlação anual
    conferem (test_correlacao_bit_a_bit_com_o_correli)."""
    ci = apoio.correli(pacote.nome)
    nint = apoio.nint_por_nome(pacote.nome)
    for s in E.series_da_carga(series(pacote.nome), laterais="dentro"):
        a = E.medias_anuais(s.valores)
        reg = ci.serie(nint[s.nome]).anual
        mu = sum(a.tolist()) / len(a)
        assert np.isclose(mu, reg.media, rtol=1e-14, atol=0), s.nome
        assert np.isclose(np.sqrt(np.mean((a - mu) ** 2)), reg.desvio, rtol=1e-14, atol=0), s.nome


# --------------------------------------------------------------------------
# Séries da matriz de carga (lacuna L4)


def test_series_da_carga(pacote):
    """P-ESP-05: séries com modelo (índice do correli, que é também a lista
    da tabela sintética 'POSTOS PRINCIPAIS' do REL) sem o posto lateral."""
    ci = apoio.correli(pacote.nome)
    dentro = E.series_da_carga(series(pacote.nome), laterais="dentro")
    fora = E.series_da_carga(series(pacote.nome))
    nint = apoio.nint_por_nome(pacote.nome)
    assert tuple(nint[s.nome] for s in dentro) == ci.indice
    sint = apoio.correlacoes_rel(pacote.nome, "sint_principais")
    nomes_sint = {n for par in sint for n in par}
    assert nomes_sint == {s.nome for s in dentro}
    assert [s.nome for s in dentro if s not in fora] == ["SOBRADINHO_L"]


# --------------------------------------------------------------------------
# Matriz de carga


def test_matriz_do_estudo_e_a_do_mes_estocastico(pacote):
    """P-ESP-09: & VAZOES reg. 13 = 1 nos dois decks (REL 'ADOCAO DA MATRIZ
    DE CORRELACAO CRUZADA MENSAL'): U = matriz do mês estocástico."""
    c, u, _ = carga(pacote.nome)
    assert base.deck(pacote.nome).dadger.vazoes.matriz_mensal == 1
    assert np.array_equal(u, c.mes(apoio.mes_estocastico(pacote.nome)))


def test_jacobi_e_o_espectro_de_u(pacote):
    """P-ESP-06: o Jacobi converge; autovalores iguais aos do LAPACK a 1e-12,
    autovetores ortonormais e U = A V A'. Com 154 séries e 94 anos há 93
    autovalores positivos (N-1) e os demais são ruído de arredondamento."""
    c, u, dc = carga(pacote.nome)
    esp = dc.espectro
    n_anos = len(series(pacote.nome)[0].anos)
    assert esp.varreduras < E.VARREDURAS_MAXIMAS
    lam, a = esp.autovalores, esp.autovetores
    assert np.max(np.abs(np.sort(lam) - np.linalg.eigvalsh(u))) < 1e-12
    assert np.max(np.abs(a.T @ a - np.eye(len(u)))) < 1e-12
    assert np.max(np.abs((a * lam) @ a.T - u)) < 1e-12
    positivos = lam > 1e-10
    assert positivos.sum() == n_anos - 1
    assert np.max(np.abs(lam[~positivos])) < 1e-12
    assert np.any(lam < 0)  # os negativos existem e precisam do tratamento P-ESP-07


def test_dd_reproduz_u_nas_direcoes_positivas(pacote):
    """P-ESP-07/08: D simétrica; para cada autovetor a_k com λ_k > 0,
    a_k' D D' a_k = λ_k e D D' a_k = U a_k; nas direções nulas D a_k = 0;
    no todo, D D' = U a 1e-12."""
    c, u, dc = carga(pacote.nome)
    d = dc.d
    lam, a = dc.espectro.autovalores, dc.espectro.autovetores
    assert np.max(np.abs(d - d.T)) < 1e-13
    dd = d @ d.T
    pos = lam > 1e-10
    ap = a[:, pos]
    assert np.max(np.abs(np.einsum("ik,ij,jk->k", ap, dd, ap) - lam[pos])) < 1e-12
    assert np.max(np.abs(dd @ ap - u @ ap)) < 1e-12
    assert np.max(np.abs(d @ a[:, lam <= 0])) < 1e-12
    assert np.max(np.abs(dd - u)) < 1e-12
    assert np.allclose(np.diag(dd), 1.0, rtol=0, atol=1e-12)


# --------------------------------------------------------------------------
# Evidência nos cenários publicados (GEVAZP.OUT)


def _fora_do_nucleo(nome) -> set[str]:
    """Colunas do GEVAZP.OUT que não são a incremental gerada da própria
    série: as usinas NW, as jusantes que recebem a NW e as usinas com posto
    lateral (2026: FOZ DO PRATA, ESTRELA, MONTE CLARO, SALTO, SOBRADINHO)."""
    cfg = base.configuracao(nome)
    por = cfg.por_numero()
    nw = [u for u in cfg.usinas if u.status == "NW"]
    out = {u.nome_str for u in nw}
    out |= {por[u.jusante].nome_str for u in nw if u.jusante in por}
    out |= {u.nome_str for u in cfg.usinas if u.posto_lateral}
    return out


def _residuo_no_nucleo(nome, u, nomes, valores=None, transf=np.log):
    """Menor valor singular do operador q -> L diag(q) K, com L = transf(Z)
    dos cenários (por padrão os do GEVAZP.OUT), centrado e normalizado com as
    probabilidades do PROBVAZ.DAT, e K = base do núcleo de U com peso nulo
    nas colunas que não são a incremental gerada da própria série (as NW, as
    jusantes que recebem a NW e SOBRADINHO, que vem do lateral). Vale 0 se
    cada coluna W_i = (L_i - c_i)/s_i e cada W_k está na imagem de U."""
    nint = apoio.nint_por_nome(nome)
    num = [nint[n] for n in nomes]
    fora = {nint[n] for n in _fora_do_nucleo(nome) if n in nint}
    ei = [k for k, n in enumerate(num) if n in fora]
    ui = [k for k, n in enumerate(num) if n not in fora]
    lam, a = np.linalg.eigh(u)
    nucleo = a[:, lam < 1e-10]
    _, _, vt = np.linalg.svd(nucleo[ei])
    k = (nucleo @ vt[len(ei):].T)[ui]
    if valores is None:
        valores = apoio.gevazp_out(nome).valores
    v = valores[:, [num[i] - 1 for i in ui]]
    p = np.asarray(apoio.probvaz(nome), float)
    w = p / p.sum()
    x = transf(v)
    x = (x - w @ x) * np.sqrt(w)[:, None]
    x = x / np.sqrt((x ** 2).sum(0))
    g = np.einsum("ki,ij->kji", x, k).reshape(-1, len(ui))
    return np.linalg.svd(g, compute_uv=False)[-1]


def test_cenarios_publicados_no_subespaco_do_mes_estocastico(pacote):
    """P-ESP-09 e P-ESP-07: com ln Z (M_t = 0, lacuna L8), os cenários do
    GEVAZP.OUT ficam muito mais perto da imagem da matriz do mês estocástico
    (posto 93) do que da de qualquer outro mês ou da anual (resíduo ~0,02
    contra ≥ 0,19). O resíduo não chega a 0: depende da lognormal (L8)."""
    c, _, _ = carga(pacote.nome)
    m = apoio.mes_estocastico(pacote.nome)
    r = [_residuo_no_nucleo(pacote.nome, c.matriz[k], c.nomes) for k in range(13)]
    alvo = r[m - 1]
    outros = r[:m - 1] + r[m:]
    assert alvo < 0.03
    assert alvo < 0.2 * min(outros)


def test_piso_nos_autovalores_nulos_e_incompativel(pacote):
    """P-ESP-07: um piso ε ≥ 3e-3 nos autovalores nulos (D de posto cheio),
    sozinho e com ruídos normais independentes, já daria no mesmo teste
    resíduo maior que o dos cenários publicados; ε = 0 dá resíduo nulo."""
    c, u, _ = carga(pacote.nome)
    observado = _residuo_no_nucleo(pacote.nome, u, c.nomes)
    lam, a = np.linalg.eigh(u)
    nint = apoio.nint_por_nome(pacote.nome)
    forma = apoio.gevazp_out(pacote.nome).valores.shape
    b = np.random.default_rng(20261027).standard_normal((forma[0], len(u)))
    for eps in (0.0, 3e-3):
        d = (a * np.sqrt(np.where(lam > 1e-10, lam, eps))) @ a.T
        w = b @ d.T
        cen = np.zeros(forma)
        for k, n in enumerate(c.nomes):
            cen[:, nint[n] - 1] = w[:, k]
        r = _residuo_no_nucleo(pacote.nome, u, c.nomes, cen, transf=lambda x: x)
        if eps == 0.0:
            assert r < 1e-10
        else:
            assert r > observado, (r, observado)


# --------------------------------------------------------------------------
# Variantes descartadas (citadas em P-ESP-01)


def test_variantes_da_correlacao(pacote):
    """P-ESP-01: fora da diagonal, só Σ(d_i d_j)/N/(σ_i σ_j) com soma do 1º ao
    último ano acerta todos os bits do correli.out. Variantes: produto das
    padronizadas, divisão única por N σ_i σ_j, divisões sucessivas por σ_i e
    σ_j, soma do último ao primeiro ano."""
    c = correlacao(pacote.nome)
    ci = apoio.correli(pacote.nome)
    ss = [s for s in series(pacote.nome) if not s.nula]
    nint = apoio.nint_por_nome(pacote.nome)
    m = apoio.mes_estocastico(pacote.nome) - 1
    x = np.stack([s.valores[:, m] for s in ss], axis=-1)
    n = x.shape[0]
    mu = E._soma_anos(x) / n
    d = x - mu
    sd = np.sqrt(E._soma_anos(d * d) / n)
    z = d / sd
    s_dir = sum(np.multiply.outer(d[k], d[k]) for k in range(n))
    s_rev = sum(np.multiply.outer(d[k], d[k]) for k in range(n - 1, -1, -1))
    s_pad = sum(np.multiply.outer(z[k], z[k]) for k in range(n))
    den = np.multiply.outer(sd, sd)
    variantes = {
        "escolhida": s_dir / n / den,
        "padronizadas": s_pad / n,
        "n_sigma_sigma": s_dir / (n * den),
        "sigma_i_depois_sigma_j": s_dir / n / sd[:, None] / sd[None, :],
        "reversa": s_rev / n / den,
    }
    num = [nint[s.nome] for s in ss]
    ref = np.array([[ci.correlacao_historica(i, j)[m] for j in num] for i in num])
    fora = ~np.eye(len(num), dtype=bool) & ~np.isnan(ref)
    taxa = {k: np.mean(v[fora] == ref[fora]) for k, v in variantes.items()}
    assert taxa["escolhida"] == 1.0
    # 2026 (mês 10/11): 0,15, 0,65, 0,65 e 0,19; nos outros pacotes as taxas
    # mudam com o mês e o histórico, mas nenhuma variante chega perto de 1.
    for k in ("padronizadas", "n_sigma_sigma", "sigma_i_depois_sigma_j", "reversa"):
        assert taxa[k] < 0.8, (k, taxa[k])
    k0 = [c.nomes.index(s.nome) for s in ss]
    assert np.array_equal(c.matriz[m][np.ix_(k0, k0)][fora], variantes["escolhida"][fora])


def test_vazoes_e_nao_residuos(pacote):
    """P-ESP-01 (M18 §4.3.2 contra L-CORR): a matriz que explica os cenários
    é a correlação das vazões; a correlação dos resíduos históricos do mesmo
    mês (P-RES-01, só os anos com resíduo) fica no nível dos controles."""
    from apoio_parp import residuos

    c, u, _ = carga(pacote.nome)
    m = apoio.mes_estocastico(pacote.nome) - 1
    res = residuos(pacote.nome)
    x = np.stack([res[n].valores[1:, m] for n in c.nomes], axis=-1)  # sem o 1º ano
    d = x - x.mean(0)
    sd = np.sqrt((d * d).mean(0))
    ur = (d.T @ d) / len(d) / np.multiply.outer(sd, sd)
    np.fill_diagonal(ur, 1.0)
    r_vaz = _residuo_no_nucleo(pacote.nome, u, c.nomes)
    r_res = _residuo_no_nucleo(pacote.nome, ur, c.nomes)
    assert r_res > 5 * r_vaz, (r_res, r_vaz)


def test_sobradinho_e_combinacao_do_lateral(pacote):
    """P-ESP-10: no GEVAZP.OUT a coluna de SOBRADINHO é combinação linear
    exata das de SOBRADINHO_L e das usinas a montante (M18 eq. 4.21), por
    isso fica fora do teste de núcleo."""
    nint = apoio.nint_por_nome(pacote.nome)
    cols = [nint[n] - 1 for n in ("SOBRADINHO", "SOBRADINHO_L", "TRES MARIAS", "RETIRO BAIXO", "QUEIMADO")]
    x = apoio.gevazp_out(pacote.nome).valores[:, cols]
    x = np.hstack([x, np.ones((len(x), 1))])
    s = np.linalg.svd(x / np.abs(x).max(0), compute_uv=False)
    assert s[-1] / s[0] < 1e-12 < s[-2] / s[0]
