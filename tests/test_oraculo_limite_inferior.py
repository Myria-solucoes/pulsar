"""Limite inferior M_t da lognormal e momentos do ruído nos cenários
publicados (frente F11, lacuna L8; P-LN3-04, P-LN3-06, P-LN3-09..13).

Teste de núcleo (apoio_f11): os W reconstruídos do GEVAZP.OUT com o M_t da
regra P-LN3-09 e os momentos históricos dos resíduos ficam na imagem da
matriz do mês estocástico a ~1e-8 (ruído numérico) em todos os pacotes; cada
ramo da regra é afirmado pelo controle que o troca: sempre que a troca
muda o M_t de alguma série, o resíduo sobe mais de cem vezes.
"""

from dataclasses import replace

import numpy as np
import pytest

import apoio
import apoio_f11 as F
from pulsar.estocastico import geracao as G
from pulsar.estocastico.lognormal import RegraLimite, parametros
from test_t5_espacial import carga

EXATO = 1e-7  # observado ≤ 1,4e-8 nos 61 pacotes
SEPARA = 100.0  # controle: resíduo ≥ cem vezes o da regra (piso numérico ~1,2e-8)

R = RegraLimite()
CONTROLES = {
    # piso μ - kσ (P-LN3-12)
    "k=2,9": replace(R, k_desvios=2.9),
    "k=3,1": replace(R, k_desvios=3.1),
    "sem piso": replace(R, k_desvios=float("inf")),
    # limiares da assimetria (P-LN3-10)
    "limiar 0,99": replace(R, limiares=(0.99, 2.0, 4.0)),
    "limiar 1,01": replace(R, limiares=(1.01, 2.0, 4.0)),
    "limiar 1,99": replace(R, limiares=(1.0, 1.99, 4.0)),
    "limiar 2,01": replace(R, limiares=(1.0, 2.01, 4.0)),
    "limiar 3,99": replace(R, limiares=(1.0, 2.0, 3.99)),
    "limiar 4,01": replace(R, limiares=(1.0, 2.0, 4.01)),
    # frações (P-LN3-10)
    "fração 0,14": replace(R, fracoes=(0.14, 0.35, 0.5, 0.6)),
    "fração 0,34": replace(R, fracoes=(0.15, 0.34, 0.5, 0.6)),
    "fração 0,49": replace(R, fracoes=(0.15, 0.35, 0.49, 0.6)),
    "fração 0,61": replace(R, fracoes=(0.15, 0.35, 0.5, 0.61)),
    # cúbica (P-LN3-11)
    "sem cúbica": replace(R, faixa_cubica=(np.inf, np.inf)),
    "cúbica desde γ = 1": replace(R, faixa_cubica=(1.0, 4.0)),
    "cúbica também com γ ≥ 4": replace(R, faixa_cubica=(2.0, np.inf)),
    # fração de negativos (P-LN3-12)
    "negativos 14%": replace(R, limiar_negativos=0.14),
    "sem limiar de negativos": replace(R, limiar_negativos=1.0),
}


def _muda(a, b) -> bool:
    return bool((np.abs(a - b) > 1e-9 * np.maximum(1.0, np.abs(a))).any())


def test_ruidos_publicados_na_imagem_com_a_regra(pacote):
    """P-LN3-09 e P-LN3-04 (INFERIDO): com M_t da regra e os momentos
    históricos dos resíduos (P-RES-02), nenhum cenário publicado fica abaixo
    do limite e os W reconstruídos estão na imagem da matriz do mês
    estocástico a menos de 1e-7 (relativo), sem parâmetro livre. Controles:
    M_t = 0 (a rota da F8) dá resíduo ≥ 1e-3, ou é impossível (cenários
    negativos de TRES IRMAOS em 202411 e 202511); os momentos teóricos
    (μ_a = 0, σ_a² = 1 - Σφρ - ψρ_A) dão resíduo cem vezes maior sempre
    que diferem dos históricos."""
    nome = pacote.nome
    r = F.residuo(nome, F.ruidos(nome))
    assert r < EXATO, r
    r0 = F.residuo(nome, F.ruidos(nome, F.limites(nome, rota="zero")))
    assert r0 > 1e-3, r0
    m = apoio.mes_estocastico(nome) - 1
    dif = max(abs(G.momentos_do_ruido(aj, m, "teoricos")[1] - G.momentos_do_ruido(aj, m, "historicos")[1])
              for _, aj, _, _, _ in F.series(nome))
    rt = F.residuo(nome, F.ruidos(nome, momentos="teoricos"))
    if dif > 1e-6:
        assert rt > SEPARA * r, (rt, r)
    print(f"{nome}: regra {r:.2e}, M=0 {r0:.2e}, teóricos {rt:.2e}")


@pytest.mark.parametrize("controle", list(CONTROLES))
def test_cada_ramo_da_regra(pacote, controle):
    """P-LN3-10..12 (INFERIDO): trocar um ramo da regra (piso μ - 3σ,
    limiares 1, 2 e 4 da assimetria, frações 0,15/0,35/0,5/0,6, faixa da
    cúbica, fração de 15% de negativos) muda o M_t de alguma série ou não;
    se muda, o resíduo de núcleo fica cem vezes maior que o da regra.
    Quantos pacotes cada controle separa: docs/limite-inferior.md."""
    nome = pacote.nome
    base_lim = F.limites(nome)
    lim = F.limites(nome, CONTROLES[controle])
    if not _muda(base_lim, lim):
        pytest.skip(f"{controle}: nenhuma série muda de M_t em {nome}")
    r = F.residuo(nome, F.ruidos(nome))
    rc = F.residuo(nome, F.ruidos(nome, lim))
    assert rc > SEPARA * r, (controle, rc, r)


def test_base_com_negativos_e_errada(pacote):
    """P-LN3-13 (INFERIDO): a base da fração é o menor valor não negativo do
    mês; com o menor valor (negativo) o M_t muda nas séries com vazão
    incremental negativa no histórico e o resíduo sobe cem vezes."""
    nome = pacote.nome
    m = apoio.mes_estocastico(nome) - 1
    lim = F.limites(nome)
    alt = lim.copy()
    for k, (_, aj, _, _, _) in enumerate(F.series(nome)):
        x = aj.serie.valores[:, m]
        if x.min() < 0 and (x < 0).mean() <= R.limiar_negativos:
            est = aj.est
            alt[k] = max(R.fracao(float(est.assimetria[m])) * x.min(), est.media[m] - 3 * est.desvio[m])
    if not _muda(lim, alt):
        pytest.skip("nenhuma série com mínimo negativo acima do piso")
    assert F.residuo(nome, F.ruidos(nome, alt)) > SEPARA * F.residuo(nome, F.ruidos(nome))


def test_media_do_ruido_abaixo_do_limite_eq_24_com_quadrado(pacote):
    """P-LN3-06 (INFERIDO): com M_t da regra e os momentos históricos,
    μ_a - Δ_t < 0 em algumas séries (média do ruído abaixo do limite); o
    teste de núcleo fecha com a eq. 24 como escrita, com (μ_a - Δ_t)², e
    a variante "normal" (a_t = μ_a + σ_a W) fica cem vezes pior."""
    nome = pacote.nome
    m = apoio.mes_estocastico(nome) - 1
    neg = 0
    for (_, aj, c, sig, _), mt in zip(F.series(nome), F.limites(nome), strict=True):
        mu, sd = G.momentos_do_ruido(aj, m, "historicos")
        neg += mu - (mt / sig - c) < 0
    if not neg:
        pytest.skip("nenhuma série com μ_a - Δ_t < 0")
    r = F.residuo(nome, F.ruidos(nome))
    assert F.residuo(nome, F.ruidos(nome, sem_lognormal="normal")) > SEPARA * r
    print(f"{nome}: {neg} séries com μ_a - Δ_t < 0")


def test_matriz_do_mes_estocastico_exata(pacote):
    """P-ESP-09 (INFERIDO, reforço da F11): com os W exatos, só a matriz do
    mês estocástico deixa os cenários na imagem (resíduo < 1e-7); as outras
    11 mensais e a anual ficam acima de 1e-3."""
    nome = pacote.nome
    c, _, _ = carga(nome)
    w = F.ruidos(nome)
    mes = apoio.mes_estocastico(nome)
    nomes = [n for n, *_ in F.series(nome)]
    idx = [c.nomes.index(n) for n in nomes]
    fora = [k for k in range(len(c.nomes)) if k not in idx]
    p = F.pesos(nome)[:, None]
    res = []
    for k in range(13):
        lam, a = np.linalg.eigh(c.matriz[k])
        nuc = a[:, lam < 1e-10]
        if fora:
            _, _, vt = np.linalg.svd(nuc[fora])
            nuc = nuc @ vt[len(fora):].T
        r = w @ nuc[idx]
        res.append(float(np.sqrt((p * r * r).sum() / (p * w * w).sum())))
    assert res[mes - 1] < EXATO
    assert min(res[:mes - 1] + res[mes:]) > 1e-3, res


def test_limite_abaixo_dos_cenarios_e_das_formas_sem_deck():
    """P-LN3-09: o limite inferido entra na lognormal como M_t em Z
    (Δ = M/σ_m - c, P-LN3-05) e os cenários ficam acima dele."""
    p = parametros(3.0, 10.0, 0.02, 0.8, "inferida", limite_vazao=12.0)
    assert p.delta == pytest.approx(12.0 / 10.0 - 3.0)
    w = np.linspace(-6, 6, 101)
    assert (10.0 * (3.0 + p.ruido(w)) > 12.0).all()
    assert np.allclose(p.inversa(p.ruido(w)), w, atol=1e-12)
