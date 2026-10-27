"""Relatório de aceitação estatística da F8 (03 §5), usado por
tests/test_t11_aceitacao.py e por ``python tests/aceitacao_f8.py`` (imprime
a tabela por deck e variante)."""

from __future__ import annotations

import functools
import sys

import numpy as np

import apoio
import apoio_f8
import base
from pulsar.estocastico import aceitacao as A

ESTATISTICAS = ("media", "desvio", "assimetria", "q25", "q50", "q75")


def colunas(nome) -> list[int]:
    """Colunas do GEVAZP.OUT com dispersão no oficial (sem PN, NW e nulas)."""
    g = apoio.gevazp_out(nome).valores[:, : len(base.configuracao(nome).completa)]
    return [j for j in range(g.shape[1]) if g[:, j].std() > 0]


def estatisticas(z: np.ndarray, p) -> dict[str, np.ndarray]:
    """Por coluna e para a soma das colunas (a árvore como um todo, última
    posição): média, desvio, assimetria e quartis ponderados."""
    x = np.hstack([z, z.sum(1, keepdims=True)])
    mu, sd = A.media_desvio(x, p)
    q = A.quantis(x, p)
    return dict(media=mu, desvio=sd, assimetria=A.assimetria(x, p), q25=q[0], q50=q[1], q75=q[2])


def correlacoes(z, p) -> np.ndarray:
    c = A.correlacao(z, p)
    return c[np.triu_indices(c.shape[0], 1)]


@functools.lru_cache(maxsize=None)
def oficial(nome):
    z = apoio.gevazp_out(nome).valores[:, colunas(nome)]
    p = apoio.probvaz(nome)
    return estatisticas(z, p), correlacoes(z, p), np.rint(np.asarray(p, float) * 50_000).astype(int)


@functools.lru_cache(maxsize=None)
def sementes(nome, variante="base"):
    cols = colunas(nome)
    est, cor, cont = [], [], []
    for s in apoio_f8.SEMENTES:
        z, p, r = apoio_f8.arvore(nome, s, variante)
        est.append(estatisticas(z[:, cols], p))
        cor.append(correlacoes(z[:, cols], p))
        cont.append(r.agregacao.contagens)
    return ({k: np.array([e[k] for e in est]) for k in ESTATISTICAS}, np.array(cor), cont)


def _fracoes(eo, co, es, cs, faixa) -> dict[str, float]:
    lo, hi = (0.0, 100.0) if faixa == "minmax" else (5.0, 95.0)
    out = {k: float(A.dentro_da_faixa(es[k][:, :-1], eo[k][:-1], lo, hi).mean()) for k in ESTATISTICAS}
    out["correlacao"] = float(A.dentro_da_faixa(cs, co, lo, hi).mean())
    out["arvore"] = float(np.mean([A.dentro_da_faixa(es[k][:, -1], eo[k][-1], lo, hi) for k in ESTATISTICAS]))
    return out


def fracoes(nome, variante="base", faixa="minmax") -> dict[str, float]:
    """Fração de postos (e de pares, na correlação) em que a estatística do
    GEVAZP.OUT oficial cai na faixa das 20 sementes: "minmax" (padrão,
    P-ACE-06: com 20 sementes, [mín, máx] contém uma 21ª amostra da mesma
    distribuição com probabilidade 19/21 ≈ 0,905) ou "p5p95"."""
    eo, co, _ = oficial(nome)
    es, cs, _ = sementes(nome, variante)
    return _fracoes(eo, co, es, cs, faixa)


def fracoes_referencia(nome, variante="base", faixa="minmax") -> dict[str, float]:
    """Mesma fração com cada semente no papel do oficial contra as outras 19
    (média): o que um gerador idêntico ao oficial alcançaria."""
    es, cs, _ = sementes(nome, variante)
    n = len(cs)
    acc = []
    for i in range(n):
        o = [j for j in range(n) if j != i]
        acc.append(_fracoes({k: v[i] for k, v in es.items()}, cs[i], {k: v[o] for k, v in es.items()}, cs[o], faixa))
    return {k: float(np.mean([a[k] for a in acc])) for k in acc[0]}


def relatorio(decks=None, variantes=None):
    for nome in decks or [n for n, _ in base.ESTOCASTICOS]:
        for v in variantes or apoio_f8.VARIANTES:
            for faixa in ("minmax", "p5p95"):
                for rot, f in (("oficial", fracoes(nome, v, faixa)), ("ref", fracoes_referencia(nome, v, faixa))):
                    print(nome, f"{v:19s} {faixa:6s} {rot:7s}", " ".join(f"{k}={x:.3f}" for k, x in f.items()), flush=True)


if __name__ == "__main__":
    relatorio(sys.argv[1:2] or None, sys.argv[2:] or None)


# --------------------------------------------------------------------------
# Testes do M18 cap. 6 (P-ACE-05)

TESTES = ("t_media", "t_desvio", "ks", "cvm")


@functools.lru_cache(maxsize=None)
def teoricos(nome):
    """Por coluna de ``colunas(nome)`` que é a incremental gerada da própria
    série: (σ_m, c, ParametrosLN3) da geração (iguais em todas as sementes:
    dependem só do ajuste e do passado)."""
    _, _, r = apoio_f8.arvore(nome, apoio_f8.SEMENTES[0])
    por = {s.indice: s for s in r.series}
    mes = r.mes - 1
    sig = {a.serie.numero * 10 + (a.serie.status == "PL"): float(a.est.desvio[mes]) for a in apoio_f8.ajustes(nome)}
    out = {}
    for j in colunas(nome):
        s = por.get(j)
        if s is None:
            continue
        u = base.configuracao(nome).completa[j]
        out[j] = (sig[s.numero * 10 + (u.status == "PL")], s.c, s.ln3)
    return out


def rejeicoes(z: np.ndarray, p, nome) -> dict[str, float]:
    """Fração das séries rejeitadas a 5% por teste (M18 §6.2)."""
    k = len(p)
    cols = colunas(nome)
    mu, sd = A.media_desvio(z, p)
    rej = {t: [] for t in TESTES}
    for i, j in enumerate(cols):
        if j not in teoricos(nome):
            continue
        sm, c, ln = teoricos(nome)[j]
        mt = sm * abs(c + ln.mu_a)
        st = sm * ln.sigma_a
        f0 = functools.partial(A.cdf_ln3, sigma_m=sm, c=c, delta=ln.delta, mu_xi=ln.mu_xi, sigma_xi=ln.sigma_xi)
        rej["t_media"].append(A.t_media(mu[i], mt, st, k) > A.T_CRITICO)
        rej["t_desvio"].append(A.desvio_rejeitado(sd[i], st, ln.sigma_xi, k))
        rej["ks"].append(A.ks(z[:, i], p, f0) > A.ks_critico(k))
        rej["cvm"].append(A.cvm(z[:, i], p, f0) > A.CVM_CRITICO)
    return {t: float(np.mean(v)) for t, v in rej.items()}


def mediana_t_media(z, p, nome) -> float:
    """Mediana, nas séries, do t da média (P-ACE-05): mede o desvio da média
    dos ruídos agregados em relação à da população (P-RUI-04)."""
    k = len(p)
    mu, _ = A.media_desvio(z, p)
    t = []
    for i, j in enumerate(colunas(nome)):
        if j in teoricos(nome):
            sm, c, ln = teoricos(nome)[j]
            t.append(A.t_media(mu[i], sm * abs(c + ln.mu_a), sm * ln.sigma_a, k))
    return float(np.median(t))


def oficial_e_sementes(nome, f, variante="base"):
    """f(z, p, nome) no oficial e em cada semente."""
    zo = apoio.gevazp_out(nome).valores[:, colunas(nome)]
    of = f(zo, apoio.probvaz(nome), nome)
    sem = []
    for s in apoio_f8.SEMENTES:
        z, p, _ = apoio_f8.arvore(nome, s, variante)
        sem.append(f(z[:, colunas(nome)], p, nome))
    return of, sem
