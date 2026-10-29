"""Postos derivados nos cenários publicados (frentes F11 e F13, lacuna L11;
P-LAT-02, P-LAT-04, P-AGR-07, P-GER-09).

Com a lognormal exata da F11 (P-LN3-09, P-LN3-04), os W de todas as séries
da carga são reconstruídos dos totais do VAZTOTGD.DAT (incremental própria
de cada usina, também das NW, F6-INC-03) e ficam na imagem da matriz do
mês; o W do posto total do lateral (SOBRADINHO, que no GEVAZP.OUT sai da
defasagem linear) é tirado da imagem pelas outras séries, e o do lateral,
da sua coluna.
"""

import functools

import numpy as np
import pytest

import apoio
import apoio_f11 as F
import base
import pacotes
from pulsar import espacial as E
from pulsar import historico
from pulsar.configuracao import LATERAL
from pulsar.oraculos import ler_totais_gerados
from pulsar.totalizacao import incrementais_de_totais
from test_t5_espacial import carga

EXATO = 1e-7


@functools.lru_cache(maxsize=None)
def proprias(nome):
    """Incrementais próprias dos cenários (totais do VAZTOTGD.DAT menos os
    de montante, NW com coluna própria) por (nome, lateral?)."""
    cfg = base.configuracao(nome)
    tot = ler_totais_gerados(apoio.deck(nome).arq("VAZTOTGD.DAT")).valores[:, :len(cfg.completa)]
    inc = incrementais_de_totais(tot, cfg, nw="propria")
    return {(u.nome_str, u.status == LATERAL): inc[:, i] for i, u in enumerate(cfg.completa)}


def _origens(nome) -> set[str]:
    """Usinas com posto lateral (o GEVAZP.OUT delas vem da defasagem)."""
    return {u.nome_str for u in base.configuracao(nome).usinas if u.posto_lateral}


@functools.lru_cache(maxsize=None)
def ruidos_da_carga(nome):
    """(nomes, W) de todas as séries da carga menos as de origem de lateral,
    a partir das incrementais próprias."""
    c, _, _ = carga(nome)
    cond, inc = F.condicionamento(nome), proprias(nome)
    nomes = [n for n in c.nomes if n not in _origens(nome)]
    w = [F.w_da_coluna(nome, *cond[(n, False)], inc[(n, False)]) for n in nomes]
    assert all(x is not None for x in w)
    return nomes, np.stack(w, 1)


def _residuo(nome, nomes, w):
    c, u, _ = carga(nome)
    idx = [c.nomes.index(n) for n in nomes]
    fora = [k for k in range(len(c.nomes)) if k not in idx]
    lam, a = np.linalg.eigh(u)
    nuc = a[:, lam < 1e-10]
    if fora:
        _, _, vt = np.linalg.svd(nuc[fora])
        nuc = nuc @ vt[len(fora):].T
    p = F.pesos(nome)[:, None]
    r = w @ nuc[idx]
    return float(np.sqrt((p * r * r).sum() / (p * w * w).sum()))


def test_nw_e_jusantes_geradas_como_as_demais(pacote):
    """P-GER-09 (INFERIDO, L11): as usinas NW e as jusantes que as recebem,
    com a incremental própria (VAZTOTGD.DAT, NW subtraída na jusante),
    ficam na imagem da matriz do mês junto com as demais (< 1e-7): a NW tem
    modelo, limite (P-LN3-09) e ruído da carga como qualquer série; no
    GEVAZP.OUT ela só é absorvida na jusante depois (F6-INC-02). Controle:
    com a coluna do GEVAZP.OUT na jusante (NW absorvida) o resíduo sobe."""
    nome = pacote.nome
    nomes, w = ruidos_da_carga(nome)
    r = _residuo(nome, nomes, w)
    assert r < EXATO, r
    cfg = base.configuracao(nome)
    por = cfg.por_numero()
    jus = {por[u.jusante].nome_str for u in cfg.usinas if u.status == "NW" and u.jusante in por}
    if not jus:
        pytest.skip("sem usina NW com jusante")
    cond, nint, g = F.condicionamento(nome), apoio.nint_por_nome(nome), apoio.gevazp_out(nome).valores
    w2 = w.copy()
    for k, n in enumerate(nomes):
        if n in jus:
            x = F.w_da_coluna(nome, *cond[(n, False)], g[:, nint[n] - 1])
            w2[:, k] = np.nan if x is None else x
    r2 = _residuo(nome, nomes, w2) if np.isfinite(w2).all() else np.inf
    assert r2 > 100 * r, (r2, r)


@functools.lru_cache(maxsize=None)
def laterais(nome):
    """Por posto lateral: (nome, W_L, W_P, ρ_m, ρ_anual), com W_P o W do
    posto total tirado da imagem pelas outras séries da carga e W_L o da
    coluna do lateral."""
    cfg = base.configuracao(nome)
    c, u, _ = carga(nome)
    nomes, w = ruidos_da_carga(nome)
    idx = [c.nomes.index(n) for n in nomes]
    lam, a = np.linalg.eigh(u)
    b = a[:, lam > 1e-10] * np.sqrt(lam[lam > 1e-10])
    y = np.linalg.lstsq(b[idx], w.T, rcond=None)[0].T
    ss = historico.series_incrementais(base.deck(nome).historico, cfg)
    mes = apoio.mes_estocastico(nome)
    cond, inc = F.condicionamento(nome), proprias(nome)
    por = cfg.por_numero()
    out = []
    for ul in [x for x in cfg.completa if x.status == LATERAL]:
        origem = por[ul.origem_lateral].nome_str
        wo = y @ b[c.nomes.index(origem)]
        wl = F.w_da_coluna(nome, *cond[(ul.nome_str, True)], inc[(ul.nome_str, True)])
        par = [s for s in ss if (s.nome, s.status == LATERAL) in ((origem, False), (ul.nome_str, True))]
        assert len(par) == 2
        cl = E.correlacao_espacial(par)
        i = [k for k, s in enumerate(par) if s.status == LATERAL][0]
        out.append((ul.nome_str, wl, wo, float(cl.mes(mes)[i, 1 - i]), float(cl.anual[i, 1 - i])))
    return out


def _versao_11(nome) -> bool:
    return int(apoio.versao_emulada(nome).split(".")[0]) >= 11


def test_lateral_condicionado_com_a_correlacao_do_mes(pacote):
    """P-LAT-02 e P-LAT-04 (INFERIDO, L11): o W do posto lateral é
    ρ_m W_P + E b1, com W_P o do posto total, ρ_m a correlação histórica do
    mês estocástico entre as duas séries e E = √(1 - ρ_m²) (M18 eq. 4.19 e
    R23954 eq. 2 com a correlação mensal, não a anual que os dois citam):

    - versão 11.0.x (abr/2026 em diante): sem o ruído próprio, W_L = ρ_m W_P
      a menos de 1e-6 em todos os cenários; com a correlação anual a
      diferença fica mais de mil vezes maior;
    - versões 8.1.6 e 10.0.0: b1 = (W_L - ρ_m W_P)/E tem desvio ponderado
      entre 0,85 e 1,15 e correlação com W_P abaixo de 0,2 (um ruído normal
      padrão independente); a correlação anual dá b1 com desvio fora dessa
      faixa nos meses em que ela se afasta da mensal (|ρ_a - ρ_m| > 0,002).
    Divergência com o M18 e o R23954 registrada nas P-LAT-02/04."""
    nome = pacote.nome
    lats = laterais(nome)
    assert lats, "todos os pacotes públicos têm SOBRADINHO_L"
    p = F.pesos(nome)
    for nl, wl, wo, rm, ra in lats:
        dif = np.abs(wl - rm * wo).max()

        def b1(rho):
            x = (wl - rho * wo) / np.sqrt(1 - rho * rho)
            return float(np.sqrt(p @ (x - p @ x) ** 2)), float(np.corrcoef(x, wo)[0, 1])

        if _versao_11(nome):
            assert dif < 1e-6, (nl, dif)
            assert np.abs(wl - ra * wo).max() > 1e3 * dif
        else:
            sd, cr = b1(rm)
            assert 0.85 < sd < 1.15 and abs(cr) < 0.2, (sd, cr)
            if abs(ra - rm) > 0.002:
                assert not 0.85 < b1(ra)[0] < 1.15
        print(f"{nome} {nl}: ρ_m = {rm:.5f}, ρ_anual = {ra:.5f}, máx |W_L - ρ_m W_P| = {dif:.1e}")


# Pacotes das versões 8.1.6 e 10.0.0 cujo b1 é a mesma sequência nó a nó
# (saída de ferramentas/familias_b1.py nos 53 pacotes; o parceiro de cada
# pacote é o de maior K da família, ou o segundo maior para ele mesmo).
FAMILIAS_B1 = (
    ("202201_pmo", "202202_pmo", "202203_pmo", "202204_pmo", "202205_pmo", "202206_pmo", "202207_pmo"),
    ("202208_pmo", "202209_pmo", "202210_pmo", "202211_pmo", "202212_pmo", "202301_pmo"),
    ("202302_pmo", "202303_pmo", "202304_pmo", "202305_pmo", "202306_pmo", "202308_pmo", "202309_pmo",
     "202310_pmo", "202311_pmo", "202312_pmo", "202401_pmo"),
    ("202402_pmo", "202402_rev1", "202402_rev2", "202402_rev3", "202403_pmo", "202404_pmo", "202405_pmo",
     "202406_pmo", "202407_pmo", "202408_pmo", "202409_pmo", "202410_pmo", "202411_pmo", "202412_pmo"),
    ("202501_pmo", "202502_pmo", "202503_pmo", "202504_pmo", "202505_pmo", "202506_pmo", "202507_pmo",
     "202508_pmo", "202509_pmo", "202510_pmo", "202511_pmo", "202512_pmo", "202601_pmo", "202602_pmo",
     "202603_pmo"),
)


def _ruido_proprio(nome):
    """(b1, W_P) do primeiro lateral: b1 = (W_L - ρ_m W_P)/√(1 - ρ_m²)."""
    _, wl, wo, rm, _ = laterais(nome)[0]
    return (wl - rm * wo) / np.sqrt(1 - rm * rm), wo


def test_ruido_proprio_do_lateral_sorteado_no_a_no(pacote):
    """P-LAT-04 (INFERIDO, L11): nas versões 8.1.6 e 10.0.0 o ruído
    próprio b1 que entra no W do lateral não vem do vetor agregado: é uma
    sequência sorteada nó a nó, que não depende de K nem da agregação
    (R23954 §2: o ruído de cada posto lateral é gerado depois do dos
    principais e individualmente). Com o pacote de maior K da mesma família
    entre os de K diferente do seu (outra agregação; famílias de
    ferramentas/familias_b1.py), b1 do nó j
    é o mesmo a 1e-3 em ≥ 97% dos nós comuns (97,2% a 100% nos 53 pacotes;
    os outros, até 7 em 353, sem causa identificada), enquanto o W do posto
    total, que vem da agregação, fica igual a 1e-3 em no máximo 1 nó: um
    centroide do K-means não se repete entre agregações diferentes. O teste
    não diz se o K-means tem uma componente do lateral que não é usada no
    W (P-AGR-07). Na versão 11 não há b1 (P-LAT-04)."""
    nome = pacote.nome
    if _versao_11(nome):
        pytest.skip("versão 11: o lateral não tem ruído próprio (P-LAT-04)")
    fam = next((f for f in FAMILIAS_B1 if nome in f), None)
    assert fam is not None, f"{nome}: pacote das versões 8.1.6/10.0.0 fora das famílias conhecidas"
    k = {n: base.deck(n).dadger.vazoes.aberturas[0] for n in fam if n in pacotes.todos()}
    outros = sorted((n for n in k if k[n] != k[nome]), key=lambda n: -k[n])
    if not outros:
        pytest.skip(f"{nome}: nenhum pacote da família com outro K em decks/")
    par = outros[0]
    b1, wo = _ruido_proprio(nome)
    b2, wo2 = _ruido_proprio(par)
    n = min(len(b1), len(b2))
    iguais = np.abs(b1[:n] - b2[:n]) < 1e-3
    wp = np.abs(wo[:n] - wo2[:n]) < 1e-3
    print(f"{nome} (K = {len(b1)}) x {par} (K = {len(b2)}): b1 igual em {iguais.sum()}/{n} nós, "
          f"W_P em {wp.sum()}/{n}")
    assert iguais.mean() >= 0.97
    assert wp.sum() <= 1
