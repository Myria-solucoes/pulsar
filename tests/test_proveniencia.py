"""Revisão do PROVENIENCIA.md (F9, 00-regras §3): cada linha aponta uma
fonte permitida que existe em ``fontes/`` (ou literatura pública) ou um
teste que existe em ``tests/``; ESCOLHA cita uma lacuna de 04-lacunas.md.

Regras verificadas:

- tipo com DOC, INFERIDO ou ESCOLHA;
- todo ``test_*``/``Test*`` citado existe (função, classe ou arquivo de
  ``tests/``) e todo caminho ``tests/``, ``src/``, ``docs/``, ``fontes/`` e
  ``ferramentas/`` citado existe (exato, ou sem a extensão);
- INFERIDO cita ao menos um teste, ou outra linha cujo tipo tem INFERIDO;
- nenhuma linha cita teste implicitamente ("mesmo teste", "mesmos testes");
- DOC cita ao menos uma fonte (sigla da tabela de siglas do PROVENIENCIA.md,
  arquivo de ``fontes/`` ou literatura pública) ou outra linha;
- ESCOLHA cita ao menos uma lacuna ``Ln`` que existe em 04-lacunas.md;
- toda sigla usada (``U19``, ``L-PAR``…) está na tabela de siglas, e o
  arquivo de cada sigla existe.
"""

from __future__ import annotations

import ast
import functools
import re

from base import RAIZ

PROV = RAIZ / "PROVENIENCIA.md"
TIPOS = ("DOC", "INFERIDO", "ESCOLHA")
LINHA = re.compile(r"^\| ([A-Z][A-Za-z0-9]*-[A-Za-z0-9-]+) \| ")
CAMINHO = re.compile(r"\b((?:tests|src|docs|fontes|ferramentas)/[\w./…-]*[\w])")
# Literatura pública (00-regras §1.3) citada sem arquivo em fontes/.
# Só referências bibliográficas nominais; nada de termos genéricos.
LITERATURA = ("Numerical Recipes", "Press et al", "Stedinger (1980)", "O'Neill", "Burges et al", "Charbeneau",
              "Hartigan", "Salas et al", "Box & Jenkins", "Johnson e Wichern")
# "mesmo(s) teste(s)" sem o nome do teste: citação implícita.
IMPLICITO = re.compile(r"(?:^|[;(]\s*)mesmos? testes?\b|mesmos? testes? d[ao] [A-Z]")


@functools.lru_cache(maxsize=None)
def nomes_de_teste() -> frozenset[str]:
    nomes = set()
    for f in (RAIZ / "tests").glob("*.py"):
        nomes.add(f.stem)
        for no in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(no, (ast.FunctionDef, ast.ClassDef)):
                nomes.add(no.name)
    return frozenset(nomes)


@functools.lru_cache(maxsize=None)
def lacunas() -> frozenset[str]:
    texto = (RAIZ / "04-lacunas.md").read_text(encoding="utf-8")
    return frozenset(re.findall(r"^\| (L\d+) \|", texto, re.M))


def linhas() -> list[tuple[str, str, str, str]]:
    """(id, decisão, tipo, fonte) de cada linha da tabela principal."""
    out = []
    principal = PROV.read_text(encoding="utf-8").split("\n## ", 1)[0]
    for t in principal.splitlines():
        m = LINHA.match(t)
        if not m:
            continue
        # o separador é " | "; "\|" dentro de uma célula é barra escapada
        cel = [c.strip() for c in re.split(r"(?<!\\) \| ", t.strip().strip("|"))]
        if len(cel) != 4:
            raise AssertionError(f"{m[1]}: {len(cel)} colunas")
        out.append(tuple(cel))
    return out


@functools.lru_cache(maxsize=None)
def siglas() -> dict[str, str]:
    """Tabela "Siglas das fontes" do PROVENIENCIA.md: sigla -> arquivo."""
    texto = PROV.read_text(encoding="utf-8")
    sec = texto.split("## Siglas das fontes", 1)
    if len(sec) < 2:
        return {}
    out = {}
    for t in sec[1].split("\n## ", 1)[0].splitlines():
        m = re.match(r"^\| ([A-Z][\w -]*?) \| (\S+)", t)
        if m and m[1] != "Sigla":
            out[m[1]] = m[2]
    return out


SIGLA = re.compile(r"(?<![\w-])(L-[A-Z0-9]+|U19|U11|M18|R1416|R3383|R13612|R46994|R27063|R23953|R23954|R3031|NT 42)(?![\w])")


@functools.lru_cache(maxsize=None)
def manifesto() -> frozenset[str]:
    """Caminhos de fontes/MANIFESTO.tsv: as fontes de terceiros não ficam no
    git (fontes/README.md), então valem pelo manifesto."""
    m = RAIZ / "fontes" / "MANIFESTO.tsv"
    linhas_ = m.read_text(encoding="utf-8").splitlines()[1:] if m.exists() else []
    return frozenset(x.split("\t")[0] for x in linhas_ if x)


def _existe(caminho: str) -> bool:
    caminho = caminho.rstrip(".")
    if caminho.startswith("fontes/") and "…" not in caminho:
        sem_ext = caminho.rsplit(".", 1)[0] if "." in caminho.rsplit("/", 1)[-1] else caminho
        if caminho in manifesto() or sem_ext in manifesto():
            return True
    if "…" in caminho:
        pre = caminho.split("…")[0]
        return any(RAIZ.glob(pre + "*"))
    p = RAIZ / caminho
    # caminho exato, ou sem a extensão (``fontes/cepel/Rel-6646_…`` cita o
    # relatório, que existe em .pdf e .txt); prefixo truncado não vale
    return p.exists() or any(p.parent.glob(p.name + ".*"))


def pendencias() -> list[str]:
    out = []
    ids = set()
    todas = linhas()
    todos_ids = {i for i, *_ in todas}
    tipos = {i: tp for i, _, tp, _ in todas}
    sig = siglas()
    for f in sig.values():
        if not _existe(f):
            out.append(f"sigla aponta arquivo inexistente: {f}")
    for i, decisao, tipo, fonte in todas:
        if i in ids:
            out.append(f"{i}: id repetido")
        ids.add(i)
        texto = f"{decisao} {tipo} {fonte}"
        if not any(t in tipo for t in TIPOS):
            out.append(f"{i}: tipo {tipo!r}")
        testes = set(re.findall(r"\b(test_\w+|Test[A-Z]\w+)", texto))
        for t in sorted(testes):
            if t.removesuffix(".py") not in nomes_de_teste():
                out.append(f"{i}: teste inexistente {t}")
        for c in CAMINHO.findall(texto):
            if not _existe(c):
                out.append(f"{i}: caminho inexistente {c}")
        for s in set(SIGLA.findall(texto)):
            if s not in sig:
                out.append(f"{i}: sigla sem arquivo na tabela de siglas: {s}")
        outras = {x for x in re.findall(r"\b([A-Z][A-Za-z0-9]*-[A-Z]+-?\w*)", fonte) if x in todos_ids and x != i}
        inferidas = {x for x in outras if "INFERIDO" in tipos[x]}
        if "INFERIDO" in tipo and not testes and "tests/" not in fonte and not inferidas:
            out.append(f"{i}: INFERIDO sem teste")
        if IMPLICITO.search(fonte):
            out.append(f"{i}: teste citado implicitamente ('mesmo teste')")
        if "DOC" in tipo and not (SIGLA.search(fonte) or "fontes/" in fonte or "Rel-" in fonte
                                  or any(x in fonte for x in LITERATURA) or outras):
            out.append(f"{i}: DOC sem fonte")
        if "ESCOLHA" in tipo:
            citadas = set(re.findall(r"\bL(\d+)\b", texto))
            if not citadas:
                out.append(f"{i}: ESCOLHA sem lacuna")
            for n in citadas:
                if f"L{n}" not in lacunas():
                    out.append(f"{i}: lacuna L{n} inexistente")
    return out


def test_toda_linha_aponta_fonte_ou_teste_existente():
    p = pendencias()
    assert not p, "\n".join(p)


def test_sem_mencao_a_material_proibido():
    """00-regras §2: nenhuma linha cita desmontagem, descompilação ou
    pseudocódigo do executável como fonte."""
    proibidos = re.compile(r"desmont|descompil|pseudoc", re.I)
    achados = [i for i, *cel in linhas() if proibidos.search(" ".join(cel))]
    assert not achados, achados


def test_regras_do_verificador(monkeypatch):
    """O verificador recusa as formas que a auditoria F9 rodada 1 (M1, M2)
    apontou: citação implícita, INFERIDO apoiado em linha que não é
    INFERIDA, literatura genérica e caminho truncado."""
    import sys

    mod = sys.modules[__name__]
    falsas = [
        ("X-A-01", "base", "DOC", "U19 §4.4"),
        ("X-A-02", "implícita", "INFERIDO", "mesmos testes; X-A-03"),
        ("X-A-03", "inferida", "INFERIDO", "tests/test_proveniencia.py::test_regras_do_verificador"),
        ("X-A-04", "só aponta DOC", "INFERIDO", "ver X-A-01"),
        ("X-A-05", "genérica", "DOC", "Box; conhecimento geral"),
        ("X-A-06", "truncado", "DOC", "fontes/cepel/Rel-66"),
        ("X-A-07", "aponta INFERIDA", "INFERIDO", "ver X-A-03"),
    ]
    monkeypatch.setattr(mod, "linhas", lambda: falsas)
    p = "\n".join(pendencias())
    assert "X-A-01" not in p and "X-A-03" not in p and "X-A-07" not in p
    assert "X-A-02: teste citado implicitamente" in p
    assert "X-A-04: INFERIDO sem teste" in p
    assert "X-A-05: DOC sem fonte" in p
    assert "X-A-06: caminho inexistente" in p
