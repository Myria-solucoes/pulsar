"""Enumera formas numéricas da eq. 4.21 do M18 para SOBRADINHO (F6-DEF-05).

Para cada forma, conta os cenários em que o total calculado é igual bit a
bit ao VAZTOTGD.DAT oficial, nos pacotes completos. Uso:

    ./ambiente/py ferramentas/enumerar_defasagem.py

Termos: lateral (coluna do posto 168), T_i = totais de TRES MARIAS e
QUEIMADO no mês, SW_i = soma da janela (F6-DEF-03), β = 15/ndmes
(F6-DEF-02). As formas variam o termo do mês anterior (β·P, SW/ndmes,
P·β, ndias·P/ndmes), o do mês corrente ((1−β)·T ou (ndmes−ndias)·T/ndmes),
o agrupamento (por montante, separado ou somado) e todas as árvores de soma;
também a incremental pela defasagem seguida da cascata e a forma direta em
precisão estendida.
"""

from __future__ import annotations

import itertools
import sys
from pathlib import Path

import numpy as np

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))
sys.path.insert(0, str(RAIZ / "tests"))

from base import COMPLETOS, DECKS, configuracao, deck  # noqa: E402
from pulsar import oraculos as O  # noqa: E402
from pulsar.totalizacao import dados_defasagem  # noqa: E402


def dados(nome):
    cfg = configuracao(nome)
    tot = O.ler_totais_gerados(DECKS / nome / "VAZTOTGD.DAT").valores
    idx = {u.numero: i for i, u in enumerate(cfg.completa)}
    mont = dados_defasagem(deck(nome), cfg)[169]
    t = [tot[:, idx[m.usina]] for m in mont]
    return tot[:, idx[169]], tot[:, idx[168]], t, [m.soma_janela for m in mont], mont[0].ndias, mont[0].dias_estagio


def arvores(itens):
    if len(itens) == 1:
        yield itens[0]
        return
    n = len(itens)
    for k in range(1, n):
        for esq in itertools.combinations(range(n), k):
            if 0 not in esq:
                continue  # a soma é comutativa: evita repetir o espelho
            a = [itens[i] for i in esq]
            b = [itens[i] for i in range(n) if i not in esq]
            for (na, va) in arvores(a):
                for (nb, vb) in arvores(b):
                    yield f"({na}+{nb})", va + vb


def formas(lat, t, sw, nd, ndm):
    b = nd / ndm
    p = [s / nd for s in sw]
    anterior = {
        "b*P": lambda i: b * p[i],
        "SW/ndm": lambda i: sw[i] / ndm,
        "P*b": lambda i: p[i] * b,
        "nd*P/ndm": lambda i: nd * p[i] / ndm,
    }
    corrente = {
        "(1-b)*T": lambda i: (1 - b) * t[i],
        "((ndm-nd)/ndm)*T": lambda i: ((ndm - nd) / ndm) * t[i],
        "(ndm-nd)*T/ndm": lambda i: (ndm - nd) * t[i] / ndm,
    }
    for (na, fa), (nc, fc) in itertools.product(anterior.items(), corrente.items()):
        sep = [("lat", lat)] + [(f"A{i}", fa(i)) for i in range(len(t))] + [(f"C{i}", fc(i)) for i in range(len(t))]
        por = [("lat", lat)] + [(f"(A{i}+C{i})", fa(i) + fc(i)) for i in range(len(t))]
        por2 = [("lat", lat)] + [(f"(C{i}+A{i})", fc(i) + fa(i)) for i in range(len(t))]
        for grupo, itens in (("separado", sep), ("por montante A+C", por), ("por montante C+A", por2)):
            for nome, valor in arvores(itens):
                yield f"{na} | {nc} | {grupo} | {nome}", valor
    # Incremental pela defasagem, lat + β·(P − T), seguida da cascata comum
    # (incremental + totais de montante), em todas as árvores de soma.
    ps, ts = sum(p), t[0] + t[1]
    for ni, x in {
        "lat+b*(P-T)": lat + b * (ps - ts),
        "lat+(b*P-b*T)": lat + (b * ps - b * ts),
        "(lat+b*P)-b*T": (lat + b * ps) - b * ts,
        "(lat-b*T)+b*P": (lat - b * ts) + b * ps,
        "lat+SW/ndm-nd*T/ndm": lat + sum(sw) / ndm - nd * ts / ndm,
    }.items():
        for nome, valor in arvores([("x", x)] + [(f"T{i}", t[i]) for i in range(len(t))]):
            yield f"incremental {ni} + cascata | {nome}", valor
    # Precisão estendida (long double, 80 bits no x86-64) com arredondamento
    # final para float64, na forma direta.
    L = np.longdouble
    bl = L(nd) / L(ndm)
    ext = (L(lat) + bl * (L(sw[0]) + L(sw[1])) / L(nd) + (1 - bl) * (L(t[0]) + L(t[1]))).astype(np.float64)
    yield "precisão estendida | lat + β·P + (1−β)·T", ext


def main():
    placar: dict[str, list[int]] = {}
    totais = {}
    for nome, _ in COMPLETOS:
        y, lat, t, sw, nd, ndm = dados(nome)
        totais[nome] = len(y)
        for forma, valor in formas(lat, t, sw, nd, ndm):
            placar.setdefault(forma, []).append(int((valor == y).sum()))
    melhores = sorted(placar.items(), key=lambda kv: -sum(kv[1]))
    print(f"{len(placar)} formas; cenários por deck: {totais}")
    print("alguma forma fecha todos os cenários dos dois decks?", any(v == list(totais.values()) for v in placar.values()))
    for forma, v in melhores[:10]:
        print(v, forma)


if __name__ == "__main__":
    main()
