"""Varredura das famílias de b1 do posto lateral (frente F13, P-LAT-04, P-AGR-07).

Uso: ./ambiente/py ferramentas/familias_b1.py [-j 12] [pacotes...]

Para cada pacote das versões 8.1.6 e 10.0.0 em decks/ (por padrão todos),
reconstrói o ruído próprio do lateral, b1 = (W_L - ρ_m W_P)/√(1 - ρ_m²),
como em tests/test_oraculo_laterais.py, e agrupa os pacotes em famílias:
dois pacotes são da mesma família quando o b1 do nó j é o mesmo (a 1e-3) em
mais da metade dos nós comuns. Imprime, por família, os pacotes com K, a
fração de nós iguais ao pacote de maior K da família e os nós em que o W do
posto total coincide (a 1e-3) com o dele. É daqui que saem as
``FAMILIAS_B1`` do teste nó a nó.
"""

import argparse
import os
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

import numpy as np  # noqa: E402

TOL = 1e-3


def _um(nome):
    import apoio
    import test_oraculo_laterais as L

    if int(apoio.versao_emulada(nome).split(".")[0]) >= 11:
        return nome, None, None
    b1, wo = L._ruido_proprio(nome)
    return nome, b1, wo


def main():
    import pacotes

    ap = argparse.ArgumentParser()
    ap.add_argument("pacotes", nargs="*", default=list(pacotes.todos()))
    ap.add_argument("-j", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    a = ap.parse_args()
    with ProcessPoolExecutor(a.j) as ex:
        res = {n: (b, w) for n, b, w in ex.map(_um, a.pacotes) if b is not None}
    familias: list[list[str]] = []
    for n in sorted(res):
        b = res[n][0]
        for f in familias:
            r = res[f[0]][0]
            k = min(len(r), len(b))
            if np.mean(np.abs(r[:k] - b[:k]) < TOL) > 0.5:
                f.append(n)
                break
        else:
            familias.append([n])
    for f in familias:
        f.sort(key=lambda n: len(res[n][0]))
        ref = f[-1]
        rb, rw = res[ref]
        print(f"família de {len(f)} pacotes, referência {ref} (K = {len(rb)})")
        for n in f[:-1]:
            b, w = res[n]
            k = len(b)
            iguais = int((np.abs(b - rb[:k]) < TOL).sum())
            wp = int((np.abs(w - rw[:k]) < TOL).sum())
            print(f"  {n:12s} K = {k:3d}: b1 igual em {iguais}/{k} nós ({iguais / k:.3f}), W_P em {wp}")


if __name__ == "__main__":
    main()
