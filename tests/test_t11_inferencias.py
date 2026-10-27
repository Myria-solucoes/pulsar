"""T11: o que os arquivos públicos dizem do núcleo estocástico, sem gerar.

- TCOND.REL: média e desvio teóricos condicionados (P-GER-04, P-LN3-04);
- TESTES.REL: tamanho da amostra (P-RUI-02);
- GEVAZP.OUT: rotas alternativas do limite inferior contra a regra da F11
  pelo teste de núcleo (P-LN3-03; a regra e o lateral estão em
  test_oraculo_limite_inferior.py e test_oraculo_laterais.py);
- QUANTIL.CSV: definição dos quartis ponderados (P-ACE-03).
"""

import functools
import re

import numpy as np

import apoio
import base
from apoio_f8 import ajustes
from pulsar.estocastico import aceitacao as A
from pulsar.estocastico.geracao import momentos_do_ruido, passado_da_serie, termo_condicional
from pulsar.estocastico.lognormal import limite_por_quantis, parametros
from pulsar.oraculos import ler_totais_gerados
from pulsar.tendencia import tendencia


@functools.lru_cache(maxsize=None)
def tcond(nome):
    out = {}
    with open(apoio.deck(nome).arq("TCOND.REL"), encoding="latin-1") as f:
        for linha in f:
            c = [x.strip() for x in linha.split(",")]
            if len(c) >= 9 and c[0] == "1":
                out[c[2]] = tuple(map(float, c[3:9]))
    return out


@functools.lru_cache(maxsize=None)
def modelo(nome):
    """Por série com modelo: (ajuste, termo c, σ_m, (μ_a, σ_a) teóricos)."""
    d, cfg = base.deck(nome), base.configuracao(nome)
    tend = tendencia(d, cfg)
    mes = apoio.mes_estocastico(nome)
    out = {}
    for aj in ajustes(nome):
        zp, a = passado_da_serie(tend, aj.serie.posto, mes)
        c = termo_condicional(aj, mes - 1, zp, a)
        out[aj.serie.nome] = (aj, c, float(aj.est.desvio[mes - 1]), momentos_do_ruido(aj, mes - 1, "teoricos"))
    return out


TOL4 = 0.5e-4 * (1 + 1e-9)  # 4 casas do TCOND.REL


def test_media_teorica_condicionada(pacote):
    """P-GER-03/04 (INFERIDO): "MEDIA TEO" do TCOND.REL = σ_m c, com c montado
    com o passado do QPAST da F5 e A_{t-1} = soma jan..dez / 12, em todas
    as 155 séries com modelo, na 4ª casa."""
    t, mod = tcond(pacote.nome), modelo(pacote.nome)
    assert len(t) == len(mod) == 155
    err = np.array([abs(t[n][0] - s * c) for n, (_, c, s, _) in mod.items()])
    assert (err <= TOL4 * 4).all(), err.max()
    assert (err <= TOL4).mean() > 0.97


def test_desvio_teorico_e_dos_momentos_teoricos(pacote):
    """P-LN3-04 (INFERIDO + DOC M18 eq. 6.11): "DESPAD TEO" = σ_m √(1 - Σ φ ρ
    - ψ ρ_A) na 4ª casa; com o desvio dos resíduos históricos (P-RES-02)
    a maioria das séries não fecha."""
    t, mod = tcond(pacote.nome), modelo(pacote.nome)
    mes = apoio.mes_estocastico(pacote.nome) - 1
    teo = np.array([abs(t[n][3] - s * sa) for n, (_, _, s, (_, sa)) in mod.items()])
    hist = np.array([abs(t[n][3] - s * momentos_do_ruido(aj, mes, "historicos")[1])
                     for n, (aj, _, s, _) in mod.items()])
    assert (teo <= TOL4 * 4).all() and (teo <= TOL4).mean() > 0.97
    assert (hist <= TOL4).mean() < 0.5


def test_tamanho_da_amostra_no_testes_rel(pacote):
    """P-RUI-02 (INFERIDO): o TESTES.REL imprime "N. SEGMENTOS GERADOS P/
    CLUSTER : 50000" em todas as usinas; o PROBVAZ.DAT tem uma folha por
    abertura do período estocástico."""
    with open(apoio.deck(pacote.nome).arq("TESTES.REL"), encoding="latin-1") as f:
        n = re.findall(r"N\. SEGMENTOS GERADOS P/ CLUSTER\s*:\s*(\d+)", f.read())
    assert len(n) == 155 and set(n) == {"50000"}
    k = base.deck(pacote.nome).dadger.vazoes.aberturas
    assert len(apoio.probvaz(pacote.nome)) == k[0]


def test_t_valores_do_tcond(pacote):
    """P-ACE-05 (INFERIDO): o T-VALOR da média no TCOND.REL é |μ_ger - μ_teo|
    / (σ_teo/√K), K = folhas (erro ≤ 0,002 com os valores impressos); o do
    desvio fica perto da M18 eq. 6.17b com η² = θ - 1 (mediana < 0,02)."""
    t, mod = tcond(pacote.nome), modelo(pacote.nome)
    k = len(apoio.probvaz(pacote.nome))
    e1, e2 = [], []
    for n, (_, c, s, (mu_a, sa)) in mod.items():
        mt, mg, tm, st, sg, ts = t[n]
        e1.append(abs(A.t_media(mg, mt, st, k) - tm))
        e2.append(abs(A.t_desvio(sg, st, 1 + sa * sa / (mu_a + c) ** 2, k) - ts))
    assert max(e1) < 0.002
    assert np.median(e2) < 0.02


# --------------------------------------------------------------------------
# Limite inferior (lacuna L8): rotas alternativas contra a regra da F11


def _z_oficial(nome, nomes):
    nint = apoio.nint_por_nome(nome)
    g = apoio.gevazp_out(nome).valores
    return np.stack([g[:, nint[n] - 1] for n in nomes], 1)


def test_rotas_alternativas_do_limite(pacote):
    """P-LN3-03 (lacuna L8): no teste de núcleo da F11 (apoio_f11), a regra
    P-LN3-09 deixa os W reconstruídos do GEVAZP.OUT na imagem da matriz do
    mês a ~1e-8; as rotas da primeira versão da F8, M_t = 0 e as cúbicas da
    eq. 25 (assimetria dos resíduos ou das vazões, Δ = μ_a - σ_a/η) e o
    estimador por quantis (Stedinger, 1980), põem o limite acima de algum
    cenário publicado ou deixam resíduo mais de cem vezes maior. Todas com
    os momentos históricos (P-LN3-04)."""
    import apoio_f11 as F
    from pulsar import parp

    nome = pacote.nome
    mes = apoio.mes_estocastico(nome) - 1
    r = F.residuo(nome, F.ruidos(nome))
    assert r < 1e-7
    for rota in ("zero", "cubica_residuos", "cubica_vazoes", "quantis"):
        lim = []
        for _, aj, c, s, _ in F.series(nome):
            mu, sd = momentos_do_ruido(aj, mes, "historicos")
            if rota == "quantis":
                p = parametros(c, s, mu, sd, rota, limite_vazao=limite_por_quantis(aj.serie.valores[:, mes]))
            else:
                g = aj.est.assimetria[mes] if rota == "cubica_vazoes" else parp.residuos(aj).assimetria[mes]
                p = parametros(c, s, mu, sd, rota, gama=g)
            lim.append(s * (c + p.delta))  # limite de Z: σ_m (c + Δ)
        rr = F.residuo(nome, F.ruidos(nome, np.array(lim)))
        assert rr > 100 * r, (rota, rr, r)


def test_lateral_condicionado_com_correlacao_anual(pacote):
    """P-LAT-02 (INFERIDO + DOC M18 eq. 4.19): W de SOBRADINHO_L, tirado do
    GEVAZP.OUT pela lognormal (M = 0, momentos teóricos), regredido em W de
    SOBRADINHO reconstruído pelas outras 153 séries (W = A √V y), tem
    inclinação perto da correlação anual (|Δ| < 0,005) e não da mensal, e
    desvio residual mais perto de √(1-ρ²_anual) que de √(1-ρ²_mensal)."""
    from pulsar import espacial as E
    from pulsar import historico
    from pulsar.totalizacao import incrementais_de_totais

    nome = pacote.nome
    d, cfg = base.deck(nome), base.configuracao(nome)
    mes = apoio.mes_estocastico(nome)
    ss = historico.series_incrementais(d.historico, cfg)
    carga = E.series_da_carga(ss)
    c = E.correlacao_espacial(carga)
    lam, a = np.linalg.eigh(c.mes(mes))
    pos = lam > 1e-10
    tot = ler_totais_gerados(apoio.deck(nome).arq("VAZTOTGD.DAT")).valores[:, :len(cfg.completa)]
    inc = incrementais_de_totais(tot, cfg, nw="propria")  # NW com a própria incremental
    col = {u.nome_str: i for i, u in enumerate(cfg.completa)}
    mod = modelo(nome)

    def w_de(n):
        aj, cc, s, (mu_a, sa) = mod[n]
        p = parametros(cc, s, mu_a, sa)
        return (np.log(inc[:, col[n]] / s - cc - p.delta) - p.mu_xi) / p.sigma_xi

    conh = [n for n in c.nomes if n != "SOBRADINHO"]
    idx = [c.nomes.index(n) for n in conh]
    w = np.stack([w_de(n) for n in conh], 1)
    m = a[:, pos][idx] * np.sqrt(lam[pos])
    y = np.linalg.lstsq(m, w.T, rcond=None)[0].T
    js = c.nomes.index("SOBRADINHO")
    x = y @ (a[js, pos] * np.sqrt(lam[pos]))
    wl = w_de("SOBRADINHO_L")
    p = A.pesos(apoio.probvaz(nome))
    p = p / p.sum()
    x, wl = x - p @ x, wl - p @ wl
    beta = (p @ (x * wl)) / (p @ (x * x))
    res = np.sqrt(p @ (wl - beta * x) ** 2)
    cl = E.correlacao_espacial([s for s in ss if s.nome in ("SOBRADINHO_L", "SOBRADINHO")])
    i, j = cl.nomes.index("SOBRADINHO_L"), cl.nomes.index("SOBRADINHO")
    ra, rm = cl.anual[i, j], cl.mes(mes)[i, j]
    assert abs(beta - ra) < 0.005 < abs(beta - rm)
    assert abs(res - np.sqrt(1 - ra * ra)) < abs(res - np.sqrt(1 - rm * rm))


# --------------------------------------------------------------------------
# Quartis do QUANTIL.CSV


def test_quartis_ponderados_do_quantil_csv(pacote):
    """P-ACE-03 (INFERIDO): os quartis do QUANTIL.CSV (totais do VAZTOTGD.DAT)
    são, em todas as usinas com dispersão, o maior valor cuja probabilidade
    acumulada (float32 somada em float64) é menor que q; média e desvio são
    os ponderados da P-ACE-01 (F2-REL-01)."""
    nome = pacote.nome
    cfg = base.configuracao(nome)
    col = {u.nome_str: i for i, u in enumerate(cfg.completa)}
    tot = ler_totais_gerados(apoio.deck(nome).arq("VAZTOTGD.DAT")).valores
    p = apoio.probvaz(nome)
    n = iguais = 0
    with open(apoio.deck(nome).arq("QUANTIL.CSV"), encoding="latin-1") as f:
        for linha in f:
            c = linha.split(",")
            if len(c) < 11 or not c[0].strip().isdigit() or c[2].strip() not in col:
                continue
            x = tot[:, col[c[2].strip()]]
            if x.std() == 0:
                continue
            n += 1
            q = A.quantis(x, p)
            mu, sd = A.media_desvio(x[:, None], p)
            ok = np.abs(q - [float(c[k]) for k in (7, 8, 9)]) <= 0.5e-4 + 1e-9
            ok &= abs(mu[0] - float(c[4])) <= 0.5e-4 + 1e-9 and abs(sd[0] - float(c[5])) <= 0.5e-4 + 1e-9
            iguais += ok.all()
    assert n == 166 and iguais == n


def test_media_condicional_negativa_eq_24_com_quadrado(pacote):
    """P-LN3-06 (INFERIDO): só o 202610 tem séries com média condicional
    negativa (c < 0): TRES IRMAOS e SAO MANOEL ("MEDIA TEO" −14,6884 e
    −1,2050 no TCOND.REL). No GEVAZP.OUT todos os cenários delas são
    positivos, o que exclui a variante "normal" (média σ_m c < 0) e a "erro"
    (o deck foi gerado). Com a eq. 24 aplicada com (μ_a - Δ)², a média da
    lognormal é σ_m |c|; a média gerada fica dentro do IC de 95% dela
    (t = 0,55 e 0,69, M18 eq. 6.15) e o W reconstruído tem desvio ponderado
    0,90 e 1,01."""
    mod = modelo(pacote.nome)
    neg = sorted(n for n, (_, c, _, _) in mod.items() if c < 0)
    assert neg == (["SAO MANOEL", "TRES IRMAOS"] if pacote.nome == "202610" else [])
    p = A.pesos(apoio.probvaz(pacote.nome))
    k = len(p)
    pn = p / p.sum()
    for n in neg:
        aj, c, s, (mu_a, sa) = mod[n]
        assert tcond(pacote.nome)[n][0] < 0
        z = _z_oficial(pacote.nome, [n])[:, 0]
        assert (z > 0).all()
        mu, _ = A.media_desvio(z[:, None], p)
        assert A.t_media(mu[0], s * abs(c + mu_a), s * sa, k) < A.T_CRITICO
        ln = parametros(c, s, mu_a, sa)  # padrão "quadrado"
        w = (np.log(z / s - c - ln.delta) - ln.mu_xi) / ln.sigma_xi
        sd = np.sqrt(pn @ (w - pn @ w) ** 2)
        assert 0.85 < sd < 1.15, (n, sd)
