"""Ruídos W reconstruídos dos cenários publicados (frente F11, lacunas L8 e L11).

Com o passado único do período estocástico, cada coluna do GEVAZP.OUT de uma
série da matriz de carga é Z = σ_m (c + a), a = e^{σ_ξ W + μ_ξ} + Δ
(M18 eq. 4.9a, 4.11–4.15; P-GER-04, P-LN3-01). Invertendo com M_t e os
momentos do ruído candidatos, W de cada cenário tem de estar na imagem da
matriz U do mês estocástico (W = D b, posto N-1 = 93, P-ESP-07/09): o
resíduo no núcleo de U mede o quanto os candidatos explicam os cenários.
"""

from __future__ import annotations

import functools
import math

import numpy as np

import apoio
import base
from apoio_f8 import ajustes
from pulsar.estocastico import geracao as G
from pulsar.estocastico.lognormal import ErroLognormal, RegraLimite, parametros
from pulsar.tendencia import tendencia
from test_t5_espacial import _fora_do_nucleo, carga


@functools.lru_cache(maxsize=None)
def condicionamento(nome):
    """Por (nome da série, lateral?): (ajuste, c, σ_m) no mês estocástico."""
    d, cfg = base.deck(nome), base.configuracao(nome)
    tend = tendencia(d, cfg)
    mes = apoio.mes_estocastico(nome)
    out = {}
    for aj in ajustes(nome):
        zp, a = G.passado_da_serie(tend, aj.serie.posto, mes)
        out[(aj.serie.nome, aj.serie.status == "PL")] = (
            aj, G.termo_condicional(aj, mes - 1, zp, a), float(aj.est.desvio[mes - 1]))
    return out


def w_da_coluna(nome, aj, c, sig, z, mt=None, momentos="historicos", sem_lognormal="quadrado"):
    """W de uma série a partir dos seus cenários ``z`` (None se algum fica
    abaixo do limite ``mt``; por padrão o da regra P-LN3-09)."""
    m = apoio.mes_estocastico(nome) - 1
    mt = G.limite_do_mes(aj, m) if mt is None else mt
    if not (z > mt).all():
        return None
    mu, sd = G.momentos_do_ruido(aj, m, momentos)
    try:
        p = parametros(c, sig, mu, sd, "inferida", limite_vazao=float(mt), sem_lognormal=sem_lognormal)
    except ErroLognormal:
        return None
    return p.inversa(z / sig - c)


@functools.lru_cache(maxsize=None)
def series(nome):
    """Séries da carga cuja coluna do GEVAZP.OUT é a incremental gerada da
    própria série (sem as da P-ESP-10), com (ajuste, c, σ_m, Z publicados)."""
    c, _, _ = carga(nome)
    cond = condicionamento(nome)
    nint = apoio.nint_por_nome(nome)
    g = apoio.gevazp_out(nome).valores
    fora = _fora_do_nucleo(nome)
    return [(n, *cond[(n, False)], g[:, nint[n] - 1].copy()) for n in c.nomes if n not in fora]


@functools.lru_cache(maxsize=None)
def nucleo(nome):
    """Base ortonormal do núcleo de U restrita às séries de ``series``
    (peso nulo nas colunas da P-ESP-10), como em test_t5_espacial."""
    c, u, _ = carga(nome)
    fora = _fora_do_nucleo(nome)
    ei = [k for k, n in enumerate(c.nomes) if n in fora]
    ui = [k for k, n in enumerate(c.nomes) if n not in fora]
    lam, a = np.linalg.eigh(u)
    nuc = a[:, lam < 1e-10]
    if ei:
        _, _, vt = np.linalg.svd(nuc[ei])
        nuc = nuc @ vt[len(ei):].T
    return nuc[ui]


@functools.lru_cache(maxsize=None)
def pesos(nome):
    p = np.asarray(apoio.probvaz(nome), float)
    return p / p.sum()


def limites(nome, regra: RegraLimite | None = None, rota: str = "inferida") -> np.ndarray:
    """M_t de cada série de ``series`` (rota "inferida" ou "zero")."""
    m = apoio.mes_estocastico(nome) - 1
    if rota == "zero":
        return np.zeros(len(series(nome)))
    return np.array([G.limite_do_mes(aj, m, regra) for _, aj, _, _, _ in series(nome)])


def ruidos(nome, lim=None, momentos: str = "historicos", sem_lognormal: str = "quadrado"):
    """W [cenário, série] dos cenários publicados com os limites ``lim`` (por
    padrão a regra P-LN3-09); None se algum cenário fica abaixo do limite."""
    lim = limites(nome) if lim is None else lim
    cols = []
    for (_, aj, c, sig, z), mt in zip(series(nome), lim, strict=True):
        w = w_da_coluna(nome, aj, c, sig, z, mt, momentos, sem_lognormal)
        if w is None:
            return None
        cols.append(w)
    return np.stack(cols, 1)


def residuo(nome, w) -> float:
    """√(Σ_k p_k |K' W_k|² / Σ_k p_k |W_k|²): 0 se todo W_k está na imagem de U."""
    if w is None:
        return math.inf
    p = pesos(nome)[:, None]
    r = w @ nucleo(nome)
    x = math.sqrt(float((p * r * r).sum() / (p * w * w).sum()))
    return x if math.isfinite(x) else math.inf  # limite infinito: W indefinido
