"""Descoberta do limite inferior M_t (lacuna L8, P-LN3-09): ajuste livre nos
GEVAZP.OUT públicos e classificação dos M_t ajustados.

Uso: ./ambiente/py ferramentas/ajuste_livre_limite.py [-j 12] [pacotes...]

É o caminho da identificação descrita em docs/limite-inferior.md §2, sem
supor a regra:

1. Por pacote, com as séries de tests/apoio_f11.py (colunas do GEVAZP.OUT
   que são a incremental gerada da própria série), ajusta por
   Levenberg–Marquardt um M_t livre por série que deixa os W na imagem da
   matriz do mês (resíduo no núcleo de U), primeiro com a lognormal dos
   momentos teóricos e depois com escala e deslocamento livres de cada W
   (W_i = α_i W_i(M_i) + β_i, com a média de α fixada em 1), o que não
   pressupõe os momentos. Grava cache/f11/ajuste_livre_<pacote>.npz.
2. Nos pacotes em que o ajuste fecha (resíduo relativo < 1e-6), compara cada
   M_t ajustado com quantidades do histórico do mês: a razão M_t / menor
   vazão não negativa por faixa de assimetria, μ − 3σ e a cúbica da eq. 25;
   deriva dos próprios M_t ajustados os limiares de assimetria entre as
   frações (corte de menor erro), o corte entre fração e μ − 3σ e a fração
   de negativos dos casos μ − 3σ que esse corte não explica. Só as fórmulas
   candidatas (fração do mínimo, μ − kσ com k = 3, cúbica) são dadas; os
   números saem dos dados.

A validação da regra resultante está em tests/test_oraculo_limite_inferior.py;
esta ferramenta só refaz a descoberta a partir dos pacotes públicos.
"""

from __future__ import annotations

import argparse
import math
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

import numpy as np

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

FECHA = 1e-6  # resíduo relativo abaixo do qual o ajuste livre é exato


# --------------------------------------------------------------------------
# Núcleo do ajuste (sem deck)


def w_de(z, mt, c, sig, mu_a, sd_a):
    """W de uma série com limite ``mt`` (lognormal da P-LN3-01, eq. 24 com
    quadrado); NaN se não há lognormal ou se algum cenário fica abaixo."""
    from pulsar.estocastico.lognormal import ErroLognormal, parametros

    if not (z > mt).all():
        return np.full(z.shape, np.nan)
    try:
        p = parametros(c, sig, mu_a, sd_a, "inferida", limite_vazao=float(mt))
    except ErroLognormal:
        return np.full(z.shape, np.nan)
    return p.inversa(z / sig - c)


class Ajuste:
    """Resíduo Σ_k p_k |K'(α ⊙ W_k(M) + β)|² e o seu ajuste.

    ``z`` [cenários, séries], ``cond`` = (c, σ_m, μ_a, σ_a) por série,
    ``k`` base do núcleo [séries, q], ``p`` probabilidades."""

    def __init__(self, z, cond, k, p):
        self.z, self.cond, self.k = np.asarray(z, float), list(cond), np.asarray(k, float)
        p = np.asarray(p, float)
        self.p = p / p.sum()
        self.zmin = self.z.min(0)
        self.sig = np.array([c[1] for c in self.cond])

    def w(self, m):
        return np.stack([w_de(self.z[:, i], m[i], *self.cond[i]) for i in range(len(self.cond))], 1)

    def f(self, m, al=1.0, be=0.0):
        w = self.w(m) * al + be
        r = w @ self.k
        return float((self.p[:, None] * r * r).sum()), w

    def residuo(self, m, al=1.0, be=0.0) -> float:
        """√(F / Σ p |W|²), relativo."""
        f, w = self.f(m, al, be)
        return math.sqrt(f / float((self.p[:, None] * w * w).sum()))

    def dw(self, m):
        h = 1e-6 * (np.abs(self.zmin - m) + 1e-3)
        return (self.w(m + h) - self.w(m - h)) / (2 * h)

    def _passo(self, x, f, r_de, jac, limitar, it):
        lam = 1e-3
        for _ in range(it):
            j, r = jac(x)
            jj, jr = j.T @ j, j.T @ r
            ok = False
            for _ in range(30):
                xn = limitar(x, x - np.linalg.lstsq(jj + lam * np.diag(np.diag(jj) + 1e-12), jr, rcond=None)[0])
                fn = r_de(xn)
                if np.isfinite(fn) and fn < f:
                    ok = True
                    break
                lam *= 10
            if not ok:
                break
            rel = (f - fn) / f
            x, f, lam = xn, fn, max(lam / 10, 1e-14)
            if rel < 1e-13:
                break
        return x, f

    def ajustar_m(self, m0, it=500):
        """M_t por série com a lognormal dos momentos dados (α = 1, β = 0)."""
        n = len(self.cond)
        sp = np.sqrt(self.p)[:, None, None]

        def r_de(m):
            return self.f(m)[0]

        def jac(m):
            _, w = self.f(m)
            j = (sp * self.dw(m)[:, :, None] * self.k[None]).transpose(0, 2, 1).reshape(-1, n)
            return j, (np.sqrt(self.p)[:, None] * (w @ self.k)).ravel()

        return self._passo(np.asarray(m0, float), r_de(m0), r_de, jac, self._limitar_m, it)

    def _limitar_m(self, x, xn):
        n = len(self.cond)
        xn = xn.copy()
        xn[:n] = np.minimum(xn[:n], x[:n] + 0.9 * (self.zmin - x[:n]))  # abaixo do menor cenário
        return xn

    def ajustar_livre(self, m0, it=300):
        """(M_t, α, β) por série; a média de α é fixada em 1 (o resíduo não
        depende da escala global de W). Devolve (M, α, β), F."""
        n = len(self.cond)
        sp = np.sqrt(self.p)[:, None, None]
        g = np.zeros((1, 3 * n))
        g[0, n:2 * n] = 10.0 / n

        def r_vec(x):
            m, al, be = x[:n], x[n:2 * n], x[2 * n:]
            _, w = self.f(m, al, be)
            r = (np.sqrt(self.p)[:, None] * (w @ self.k)).ravel()
            return np.concatenate([r, [10.0 * (al.mean() - 1.0)]])

        def r_de(x):
            r = r_vec(x)
            return float(r @ r)

        def jac(x):
            m, al = x[:n], x[n:2 * n]
            w0 = self.w(m)
            blocos = [(sp * (self.dw(m) * al)[:, :, None] * self.k[None]),
                      (sp * w0[:, :, None] * self.k[None]),
                      (sp * np.ones_like(w0)[:, :, None] * self.k[None])]
            j = np.hstack([b.transpose(0, 2, 1).reshape(-1, n) for b in blocos])
            return np.vstack([j, g]), r_vec(x)

        x0 = np.concatenate([np.asarray(m0, float), np.ones(n), np.zeros(n)])
        x, f = self._passo(x0, r_de(x0), r_de, jac, self._limitar_m, it)
        return (x[:n], x[n:2 * n], x[2 * n:]), f


# --------------------------------------------------------------------------
# Por pacote


def ajustar_pacote(nome, destino=None):
    """Ajuste livre do pacote (passo 1); grava e devolve o npz."""
    import apoio
    import apoio_f11 as F
    from pulsar.estocastico import geracao as G

    destino = Path(destino or RAIZ / "cache" / "f11")
    destino.mkdir(parents=True, exist_ok=True)
    arq = destino / f"ajuste_livre_{nome}.npz"
    if arq.exists():
        return arq
    m = apoio.mes_estocastico(nome) - 1
    ss = F.series(nome)
    cond = [(c, sig, *G.momentos_do_ruido(aj, m, "teoricos")) for _, aj, c, sig, _ in ss]
    a = Ajuste(np.stack([z for *_, z in ss], 1), cond, F.nucleo(nome), F.pesos(nome))
    m0 = np.minimum(0.0, a.zmin - 0.1 * a.sig)
    mt, _ = a.ajustar_m(m0)
    (ml, al, be), _ = a.ajustar_livre(mt)
    x = [aj.serie.valores[:, m] for _, aj, _, _, _ in ss]
    np.savez(arq, nomes=np.array([n for n, *_ in ss]), M=ml, al=al, be=be, Mteo=mt,
             r0=a.residuo(m0), rteo=a.residuo(mt), rlivre=a.residuo(ml, al, be),
             media=np.array([aj.est.media[m] for _, aj, *_ in ss]),
             desvio=np.array([aj.est.desvio[m] for _, aj, *_ in ss]),
             gama=np.array([aj.est.assimetria[m] for _, aj, *_ in ss]),
             hist=np.stack(x, 1))
    return arq


# --------------------------------------------------------------------------
# Classificação (passo 2)


def _eta(g):
    q = math.sqrt(g * g + 4)
    return math.cbrt((g + q) / 2) + math.cbrt((g - q) / 2)


def corte(abaixo, acima):
    """Limiar t que deixa o menor número de valores de ``abaixo`` em ≥ t e de
    ``acima`` em < t (ponto médio entre valores vizinhos); devolve (t, erros)."""
    v = np.sort(np.concatenate([np.asarray(abaixo, float), np.asarray(acima, float)]))
    cand = np.unique((v[1:] + v[:-1]) / 2)
    a, b = np.sort(abaixo), np.sort(acima)
    err = (len(a) - np.searchsorted(a, cand, "left")) + np.searchsorted(b, cand, "left")
    i = int(np.argmin(err))
    return float(cand[i]), int(err[i])


def classificar(arquivos, tol=1e-4):
    """Lê os npz e imprime: razões M/menor não negativo mais frequentes por
    faixa de assimetria, candidatos μ − 3σ e metade da cúbica, e a melhor
    variável de separação para os casos que não são fração."""
    linhas = []
    for f in arquivos:
        z = np.load(f)
        if float(z["rlivre"]) >= FECHA:
            continue
        for i in range(len(z["M"])):
            x = z["hist"][:, i]
            nn = x[x >= 0]
            mu, sd, g = float(z["media"][i]), float(z["desvio"][i]), float(z["gama"][i])
            linhas.append(dict(M=float(z["M"][i]), base=float(nn.min()) if nn.size else 0.0, mu=mu, sd=sd, g=g,
                               neg=float((x < 0).mean()),
                               tau=mu - sd / _eta(g) if g > 0 else float("nan")))
    print(f"séries × pacote com ajuste exato: {len(linhas)}")
    pos = [r for r in linhas if r["base"] > 0]
    razoes = Counter(round(r["M"] / r["base"], 3) for r in pos)
    fracoes = [v for v, c in razoes.most_common() if c >= 0.01 * len(pos)]
    print("razões M / menor não negativo com ≥ 1% das séries:", {v: razoes[v] for v in fracoes})
    for f in sorted(fracoes):
        gs = [r["g"] for r in pos if abs(r["M"] / r["base"] - f) < 5e-4]
        print(f"  fração {f}: {len(gs)} séries, assimetria de {min(gs):.4f} a {max(gs):.4f}")
    perto = lambda a, b: abs(a - b) < tol * max(1.0, abs(a))  # noqa: E731
    cont = Counter()
    resto = []
    for r in linhas:
        if any(perto(r["M"], f * r["base"]) for f in fracoes):
            r["tipo"] = "fração"
        elif perto(r["M"], r["mu"] - 3 * r["sd"]):
            r["tipo"] = "μ − 3σ"
        elif not math.isnan(r["tau"]) and any(perto(r["M"], f * r["tau"]) for f in fracoes):
            r["tipo"] = "fração da cúbica"
        else:
            r["tipo"] = "outro"
            resto.append(r)
        cont[r["tipo"]] += 1
    print("fórmulas:", dict(cont))
    # Limiares de γ entre frações consecutivas, derivados das séries
    # classificadas (corte de menor erro), não fixados.
    lim = sorted(fracoes)
    grupos = [[r["g"] for r in pos if r["tipo"] == "fração" and abs(r["M"] / r["base"] - f) < 5e-4] for f in lim]
    limiares = []
    for f0, f1, g0, g1 in zip(lim, lim[1:], grupos, grupos[1:]):
        t, err = corte(g0, g1)
        limiares.append(t)
        print(f"  limiar de γ entre {f0} e {f1}: {t:.6f} ({err} séries do lado errado)")

    def fracao(g):
        return lim[sum(g >= t for t in limiares)]

    # Separação fração x μ − 3σ por (f(γ)·base − μ)/σ, com os limiares acima.
    for r in linhas:
        r["kmin"] = (fracao(r["g"]) * r["base"] - r["mu"]) / r["sd"] if r["sd"] > 0 else float("nan")
    m3 = [r for r in linhas if r["tipo"] == "μ − 3σ"]
    fr = [r for r in linhas if r["tipo"] == "fração"]
    s_k, err = corte([r["kmin"] for r in m3], [r["kmin"] for r in fr])
    print(f"(f·base − μ)/σ: corte em {s_k:.4f} ({err} séries do lado errado); "
          f"maior nos 'μ − 3σ' abaixo do corte {max(r['kmin'] for r in m3 if r['kmin'] < s_k):.4f}, "
          f"menor nos 'fração' {min(r['kmin'] for r in fr):.4f}")
    # Os 'μ − 3σ' que o corte não explica: comparar a fração de negativos.
    fora = [r for r in m3 if r["kmin"] >= s_k]
    if fora:
        print(f"'μ − 3σ' acima do corte: {len(fora)}, frações de negativos "
              f"{sorted(round(r['neg'], 4) for r in fora)}; maior fração de negativos nos 'fração': "
              f"{max(r['neg'] for r in fr):.4f}")
    neg = sorted((r["neg"], r["tipo"]) for r in linhas if r["neg"] > 0)
    print("maiores frações de negativos e o tipo:", neg[-4:])
    print(f"sem fórmula: {len(resto)}")


def main():
    import pacotes

    ap = argparse.ArgumentParser()
    ap.add_argument("pacotes", nargs="*")
    ap.add_argument("-j", type=int, default=max(1, (os.cpu_count() or 2) // 4))
    a = ap.parse_args()
    nomes = a.pacotes or list(pacotes.todos())
    with ProcessPoolExecutor(a.j) as ex:
        arqs = list(ex.map(ajustar_pacote, nomes))
    for n, f in zip(nomes, arqs, strict=True):
        z = np.load(f)
        print(f"{n:12s} M_t = 0: {float(z['r0']):.2e}  M_t livre (momentos teóricos): {float(z['rteo']):.2e}  "
              f"livre com escala e deslocamento: {float(z['rlivre']):.2e}", flush=True)
    classificar(arqs)


if __name__ == "__main__":
    main()
