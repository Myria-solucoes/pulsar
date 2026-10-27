"""Preenche em paralelo o cache das agregações da F8 (cache/f8/).

Uso: ./ambiente/py ferramentas/sementes_f8.py [-j 14] [--simetria nenhuma antitetica]
     [--ruido-lateral nenhum proprio] [decks...]

Cada agregação (50 mil objetos, K-means com K = aberturas) leva cerca de
2 min num núcleo; os testes T10/T11 (tests/test_t1[01]_*.py) leem o cache e
só calculam o que faltar.
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


def _uma(args):
    import apoio_f8

    nome, semente, simetria, lateral = args
    a = apoio_f8.agregacao(nome, semente, simetria, lateral)
    return nome, semente, simetria, lateral, a.iteracoes, a.ifault


def main():
    import base
    import apoio_f8

    ap = argparse.ArgumentParser()
    ap.add_argument("decks", nargs="*", default=[n for n, _ in base.COMPLETOS])
    ap.add_argument("-j", type=int, default=max(1, (os.cpu_count() or 2) // 2))
    ap.add_argument("--simetria", nargs="*", default=["nenhuma"])
    ap.add_argument("--sementes", type=int, default=len(apoio_f8.SEMENTES))
    ap.add_argument("--ruido-lateral", nargs="*", default=["nenhum"],
                    help="nenhum (padrão, P-LAT-04) e/ou proprio (vetor agregado com o lateral, variante f8)")
    a = ap.parse_args()
    tarefas = [(d, s, sm, lt) for lt in a.ruido_lateral for sm in a.simetria for d in a.decks
               for s in apoio_f8.SEMENTES[: a.sementes]]
    with ProcessPoolExecutor(a.j) as ex:
        for r in ex.map(_uma, tarefas):
            print(*r, flush=True)


if __name__ == "__main__":
    main()
