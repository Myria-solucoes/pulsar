"""Tabelas do docs/relatorio-final.md (F9).

Uso: ./ambiente/py ferramentas/relatorio_f9.py

Para cada VAZOES.RVx publicado: palavras iguais por bloco (mínimo, mediana e
máximo nas 20 sementes, cadeia da CLI com as agregações em cache/f8/) e
frações de 03 §5 sobre o bloco 6 (faixas [mín, máx] e P5–P95, oficial e
referência de um gerador idêntico).
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("OPENBLAS_NUM_THREADS", "4")
RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

import numpy as np  # noqa: E402

import apoio_f8  # noqa: E402
import apoio_f9 as F  # noqa: E402
from test_t9_empacotamento import palavras_por_bloco  # noqa: E402


def main():
    for nome, rev in F.revisoes():
        o = F.oficial_bytes(nome, rev)
        cont = {}
        for s in apoio_f8.SEMENTES:
            a, b, _ = F.gerado(nome, rev, s)
            for k, (i, t) in palavras_por_bloco(b, o, a).items():
                cont.setdefault(k, ([], t))[0].append(i)
        print(f"## {nome} {rev}  ({len(o)} bytes, {len(o) // 4} palavras)")
        tot_i = tot_t = 0
        for k, (v, t) in cont.items():
            v = np.array(v)
            tot_i += np.median(v)
            tot_t += t
            print(f"  {k:22s} {t:7d}  mín {v.min():7d}  mediana {int(np.median(v)):7d}  máx {v.max():7d}"
                  f"  ({np.median(v) / t if t else 1:.3f})")
        print(f"  {'total (medianas)':22s} {tot_t:7d}  {int(tot_i)}  ({tot_i / tot_t:.3f})")
        cols = F.colunas(nome, rev)
        print(f"  colunas com dispersão no bloco 6: {len(cols)}")
        for faixa in ("minmax", "p5p95"):
            for rot, f in (("oficial", F.fracoes(nome, rev, faixa=faixa)),
                           ("referência", F.fracoes_referencia(nome, rev, faixa=faixa))):
                print(f"  03§5 {faixa:6s} {rot:10s}", " ".join(f"{k}={x:.3f}" for k, x in f.items()))
        for faixa in ("minmax",):
            f = F.fracoes(nome, rev, "gerada_mensal_ena", faixa)
            print(f"  03§5 bloco 8 {faixa}", " ".join(f"{k}={x:.3f}" for k, x in f.items()))
        print(flush=True)


if __name__ == "__main__":
    main()
