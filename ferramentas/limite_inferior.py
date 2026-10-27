"""Ramos da regra do limite inferior M_t (P-LN3-09..13) nos pacotes públicos.

Uso: ./ambiente/py ferramentas/limite_inferior.py [-j 12] [pacotes...]

Para cada pacote: resíduo do teste de núcleo com a regra (apoio_f11),
quantas séries usam cada ramo e, para os limiares da assimetria e da fração
de negativos, o maior valor observado abaixo e o menor acima do limiar entre
as séries em que o ramo decide o M_t. Sem pacotes, os 61 (03 §1.1 e §1.1b).
"""

import argparse
import os
import sys
from collections import Counter
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))


def _um(nome):
    import apoio
    import apoio_f11 as F
    from pulsar.estocastico.lognormal import RegraLimite, eta_da_assimetria

    r = RegraLimite()
    m = apoio.mes_estocastico(nome) - 1
    ramos, perto = Counter(), []
    for _, aj, _, _, _ in F.series(nome):
        x = aj.serie.valores[:, m]
        mu, sd, g = float(aj.est.media[m]), float(aj.est.desvio[m]), float(aj.est.assimetria[m])
        piso = mu - r.k_desvios * sd
        fneg = (x < 0).mean()
        perto.append(("negativos", fneg, fneg > r.limiar_negativos))
        if fneg > r.limiar_negativos:
            ramos["μ-3σ (negativos)"] += 1
            continue
        nn = x[x >= 0]
        base = float(nn.min()) if nn.size else 0.0
        cub = mu - sd / eta_da_assimetria(g) if g > 0 else float("nan")
        usa_cub = r.faixa_cubica[0] <= g < r.faixa_cubica[1] and 0 < cub < base
        if usa_cub:
            base = cub
        if r.fracao(g) * base <= piso:
            ramos["μ-3σ (piso)"] += 1
            continue
        ramos[("cúbica" if usa_cub else "fração") + f" {r.fracao(g)}"] += 1
        if base > 0:  # com base 0 a fração não muda o M_t
            perto.append(("assimetria", g, None))
    return nome, F.residuo(nome, F.ruidos(nome)), ramos, perto


def main():
    import pacotes

    ap = argparse.ArgumentParser()
    ap.add_argument("pacotes", nargs="*")
    ap.add_argument("-j", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    a = ap.parse_args()
    nomes = a.pacotes or list(pacotes.todos())
    total, lims = Counter(), {}
    with ProcessPoolExecutor(a.j) as ex:
        for nome, res, ramos, perto in ex.map(_um, nomes):
            total.update(ramos)
            print(f"{nome:12s} resíduo {res:.2e} " + ", ".join(f"{k}: {v}" for k, v in sorted(ramos.items())), flush=True)
            for tipo, v, acima in perto:
                if tipo == "assimetria":
                    for t in (1.0, 2.0, 4.0):
                        lo, hi = lims.get(t, (-1e9, 1e9))
                        lims[t] = (max(lo, v) if v < t else lo, min(hi, v) if v >= t else hi)
                else:
                    lo, hi = lims.get("neg", (-1.0, 2.0))
                    lims["neg"] = (lo if acima else max(lo, v), min(hi, v) if acima else hi)
    print("total:", dict(sorted(total.items())))
    for t, (lo, hi) in lims.items():
        print(f"limiar {t}: maior abaixo {lo:.6f}, menor acima {hi:.6f}")


if __name__ == "__main__":
    main()
