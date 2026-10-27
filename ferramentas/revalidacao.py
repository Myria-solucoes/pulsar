"""Roda os degraus T0–T10 pacote a pacote, em paralelo, e resume por degrau.

Uso (dentro do ambiente):

    ./ambiente/py ferramentas/revalidacao.py [-j 8] [--degraus T0 T6] [pacotes...]
    ./ambiente/py ferramentas/revalidacao.py --resumo   # só refaz a tabela

Cada pacote roda num pytest próprio (``--decks <nome>``), com JUnit XML em
``cache/revalidacao/<nome>.xml``. O resumo lista, por degrau, os pacotes que
fecham e, para os que não fecham, o primeiro teste que falhou e a primeira
linha da mensagem; vai para a saída padrão em Markdown (seção 2 de
docs/revalidacao-2022-2026.md).
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "tests"))
import pacotes  # noqa: E402

SAIDA = RAIZ / "cache" / "revalidacao"

# Arquivos de teste de cada degrau (03 §4); os testes de oráculos entram no
# degrau cujo arquivo público decodificam.
DEGRAUS = {
    "T0": ["test_t0_leitura.py"],
    "T1": ["test_t1_configuracao.py"],
    "T2": ["test_t2_historico.py", "test_oraculo_correl.py"],
    "T3": ["test_t3_correlogramas.py", "test_t3_variantes.py"],
    "T4": ["test_t4_parp.py", "test_t4_residuos.py", "test_t4_variantes.py"],
    "T5": ["test_t5_espacial.py"],
    "T6": ["test_t6_tendencia.py", "test_oraculo_tendencia.py"],
    "T7": ["test_t7_vazoes_deterministicos.py", "test_oraculo_vazoes_decomp.py", "test_oraculo_series_arvore.py",
           "test_oraculo_relacoes.py"],
    "T8": ["test_t8_totalizacao.py"],
    "T9": ["test_t9_empacotamento.py"],
    "T10": ["test_t10_probabilidades.py"],
}
# Testes das coleções de decks do ONS (03 §1.2) não dependem do pacote: ficam fora da varredura.
FILTRO = "not Colecao and not colecao"


SO_CACHE = False


def _rodar(nome: str, arquivos: list[str]) -> int:
    SAIDA.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--decks", nome, "-k", FILTRO,
           f"--junitxml={SAIDA / (nome + '.xml')}", *[str(RAIZ / "tests" / a) for a in arquivos]]
    env = dict(os.environ, OPENBLAS_NUM_THREADS="1", PULSAR_DECKS=nome)
    if SO_CACHE:
        env["PULSAR_SO_CACHE"] = "1"
    r = subprocess.run(cmd, cwd=RAIZ, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return r.returncode


def _casos(nome: str, pulados: bool = False):
    """[(arquivo, teste, falha ou None)] do JUnit do pacote; com
    ``pulados``, só os testes pulados (falha = motivo)."""
    f = SAIDA / f"{nome}.xml"
    if not f.exists():
        return None
    out = []
    for tc in ET.parse(f).iter("testcase"):
        partes = (tc.get("classname") or "").split(".")
        arq = next((x for x in partes if x.startswith("test_")), partes[0]) + ".py"
        falha = None
        for tag in ("failure", "error"):
            e = tc.find(tag)
            if e is not None:
                msg = (e.get("message") or e.text or "").strip().splitlines()
                falha = msg[0][:160] if msg else tag
                break
        sk = tc.find("skipped")
        if (sk is not None and falha is None) != pulados:
            continue
        if pulados:
            falha = (sk.get("message") or "").strip()[:120]
        out.append((arq, tc.get("name"), falha))
    return out


def resumo(nomes: list[str], degraus: list[str]) -> str:
    linhas = ["| Degrau | Fecham | Testes por pacote | Não fecham: primeira divergência |", "| --- | --- | --- | --- |"]
    for dg in degraus:
        arqs = set(DEGRAUS[dg])
        ok, ruins, sem, contagem = [], [], [], set()
        for n in nomes:
            casos = _casos(n)
            casos = [c for c in casos or [] if c[0] in arqs]
            contagem.add(len(casos))
            if not casos:
                sem.append(n)
                continue
            f = next((c for c in casos if c[2]), None)
            (ruins.append((n, f)) if f else ok.append(n))
        txt_ruins = "<br>".join(f"`{n}`: `{f[1]}`: {re.sub(r'[|`]', ' ', f[2])}" for n, f in ruins) or "—"
        fecham = f"{len(ok)}/{len(nomes)}" + (f" (sem resultado: {', '.join(sem)})" if sem else "")
        npul = {n: len([c for c in _casos(n, pulados=True) or [] if c[0] in arqs]) for n in nomes}
        faixa = f"{min(contagem)}–{max(contagem)}" if len(contagem) > 1 else str(next(iter(contagem), 0))
        if any(npul.values()):
            faixa += f" (+ {min(npul.values())}–{max(npul.values())} pulados)"
        linhas.append(f"| {dg} | {fecham} | {faixa} | {txt_ruins} |")
    return "\n".join(linhas)


def pulados(nomes: list[str], degraus: list[str]) -> str:
    """Motivos dos testes pulados por degrau, com os pacotes de cada um."""
    import collections
    linhas = []
    for dg in degraus:
        arqs = set(DEGRAUS[dg])
        mot = collections.defaultdict(set)
        for n in nomes:
            for c in _casos(n, pulados=True) or []:
                if c[0] in arqs:
                    chave = re.sub(r"\d{6}_?\w*[:/]?", "<pacote>", c[2]).strip()
                    mot[(re.sub(r"\[.*", "", c[1]), chave)].add(n)
        for (t, m), ns in sorted(mot.items()):
            linhas.append(f"- {dg} `{t}` ({len(ns)} pacotes): {m}")
    return "\n".join(linhas)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pacotes", nargs="*")
    ap.add_argument("-j", type=int, default=8)
    ap.add_argument("--degraus", nargs="*", default=list(DEGRAUS))
    ap.add_argument("--resumo", action="store_true", help="não roda; só resume os JUnit existentes")
    ap.add_argument("--so-cache", action="store_true", help="T10: pula as agregações fora de cache/f8/")
    a = ap.parse_args()
    global SO_CACHE
    SO_CACHE = a.so_cache
    nomes = a.pacotes or list(pacotes.todos())
    arquivos = [f for dg in a.degraus for f in DEGRAUS[dg]]
    if not a.resumo:
        with ThreadPoolExecutor(a.j) as ex:
            for nome, rc in zip(nomes, ex.map(lambda n: _rodar(n, arquivos), nomes)):
                print(f"{nome}: {'ok' if rc == 0 else f'código {rc}'}", file=sys.stderr, flush=True)
    print(resumo(nomes, a.degraus))
    print()
    print(pulados(nomes, a.degraus))


if __name__ == "__main__":
    main()
