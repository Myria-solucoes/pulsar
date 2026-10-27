"""REGRAS.DAT: regras de cálculo dos postos artificiais (U19 §3.10).

Leitura dos dois blocos e análise sintática das expressões. A avaliação
numérica fica em ``avaliar``; a precisão e os arredondamentos do modelo
oficial são a lacuna L9 e pertencem à frente de artificiais.
"""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .texto import ErroLeitura, col, inteiro, ler_linhas

# ------------------------------------------------------------------ AST


@dataclass(frozen=True)
class Num:
    valor: float


@dataclass(frozen=True)
class Vaz:
    posto: int


@dataclass(frozen=True)
class Bin:
    op: str  # + - * / > >= < <= = <> E OU
    a: object
    b: object


@dataclass(frozen=True)
class Neg:
    a: object


@dataclass(frozen=True)
class Func:
    nome: str  # MAX MIN SE
    args: tuple


def postos_referenciados(no) -> set[int]:
    if isinstance(no, Vaz):
        return {no.posto}
    if isinstance(no, Bin):
        return postos_referenciados(no.a) | postos_referenciados(no.b)
    if isinstance(no, Neg):
        return postos_referenciados(no.a)
    if isinstance(no, Func):
        s: set[int] = set()
        for a in no.args:
            s |= postos_referenciados(a)
        return s
    return set()


# --------------------------------------------------------------- análise

# P-REG-02: símbolos alternativos do U19 §3.10: ~ é >=, @ é <=, ! é <>,
# & é E, | é OU. VAZ, MAX, MIN, SE, E, OU sem diferenciar maiúsculas.
_TOKEN = re.compile(
    r"\s*(?:(?P<num>\d+(?:\.\d*)?|\.\d+)|(?P<nome>[A-Za-z]+)|(?P<op><>|<=|>=|[-+*/();<>=~@!&|]))"
)
_ALIAS = {"~": ">=", "@": "<=", "!": "<>", "&": "E", "|": "OU"}


def _tokens(texto: str) -> list[str]:
    pos = 0
    saida: list[str] = []
    texto = texto.rstrip()
    while pos < len(texto):
        m = _TOKEN.match(texto, pos)
        if not m or m.end() == pos:
            raise ErroLeitura(f"regra inválida perto de {texto[pos:]!r}: {texto!r}")
        pos = m.end()
        if m.group("num") is not None:
            saida.append(m.group("num"))
        elif m.group("nome") is not None:
            saida.append(m.group("nome").upper())
        else:
            op = m.group("op")
            saida.append(_ALIAS.get(op, op))
    return saida


class _Parser:
    """Precedência (P-REG-03, ESCOLHA): OU < E < comparação < + - < * / < sinal."""

    def __init__(self, texto: str):
        self.texto = texto
        self.t = _tokens(texto)
        self.i = 0

    def erro(self, msg: str):
        raise ErroLeitura(f"{msg} em {self.texto!r}")

    def ver(self) -> str | None:
        return self.t[self.i] if self.i < len(self.t) else None

    def pegar(self, esperado: str | None = None) -> str:
        tok = self.ver()
        if tok is None or (esperado is not None and tok != esperado):
            self.erro(f"esperava {esperado or 'símbolo'}, achou {tok}")
        self.i += 1
        return tok

    def tudo(self):
        no = self.ou()
        if self.ver() is not None:
            self.erro(f"sobra {self.t[self.i:]}")
        return no

    def ou(self):
        no = self.e()
        while self.ver() == "OU":
            self.pegar()
            no = Bin("OU", no, self.e())
        return no

    def e(self):
        no = self.comp()
        while self.ver() == "E":
            self.pegar()
            no = Bin("E", no, self.comp())
        return no

    def comp(self):
        no = self.soma()
        while self.ver() in (">", ">=", "<", "<=", "=", "<>"):
            op = self.pegar()
            no = Bin(op, no, self.soma())
        return no

    def soma(self):
        no = self.prod()
        while self.ver() in ("+", "-"):
            op = self.pegar()
            no = Bin(op, no, self.prod())
        return no

    def prod(self):
        no = self.unario()
        while self.ver() in ("*", "/"):
            op = self.pegar()
            no = Bin(op, no, self.unario())
        return no

    def unario(self):
        if self.ver() in ("-", "+"):
            op = self.pegar()
            a = self.unario()
            return Neg(a) if op == "-" else a
        return self.primario()

    def primario(self):
        tok = self.ver()
        if tok is None:
            self.erro("fim inesperado")
        if tok == "(":
            self.pegar()
            no = self.ou()
            self.pegar(")")
            return no
        if tok[0].isdigit() or tok[0] == ".":
            self.pegar()
            return Num(float(tok))
        if tok == "VAZ":
            self.pegar()
            self.pegar("(")
            n = self.pegar()
            if not n.isdigit():
                self.erro("VAZ sem número de posto")
            self.pegar(")")
            return Vaz(int(n))
        if tok in ("MAX", "MIN", "SE"):
            self.pegar()
            self.pegar("(")
            args = [self.ou()]
            while self.ver() == ";":
                self.pegar()
                args.append(self.ou())
            self.pegar(")")
            esperado = 3 if tok == "SE" else 2
            if len(args) != esperado:
                self.erro(f"{tok} com {len(args)} argumentos")
            return Func(tok, tuple(args))
        self.erro(f"símbolo inesperado {tok}")


def analisar(texto: str):
    return _Parser(texto).tudo()


def _identidade(x: float) -> float:
    return x


def avaliar(no, vaz, arredondar: Callable[[float], float] | None = None) -> float:
    """Avalia a regra; ``vaz(posto)`` devolve a vazão do posto.

    P-REG-04 (ESCOLHA, lacuna L9): aritmética em precisão dupla, sem
    arredondamento intermediário (``arredondar=None``); comparações devolvem
    1.0/0.0. ``arredondar`` é aplicado a cada valor lido e a cada resultado
    intermediário (por exemplo ``lambda x: float(numpy.float32(x))`` para
    simular precisão simples).
    """
    r = arredondar or _identidade

    def ev(n) -> float:
        if isinstance(n, Num):
            return r(n.valor)
        if isinstance(n, Vaz):
            return r(float(vaz(n.posto)))
        if isinstance(n, Neg):
            return -ev(n.a)
        if isinstance(n, Func):
            if n.nome == "SE":
                return ev(n.args[1]) if ev(n.args[0]) else ev(n.args[2])
            a, b = (ev(x) for x in n.args)
            return max(a, b) if n.nome == "MAX" else min(a, b)
        a = ev(n.a)
        if n.op == "E":
            return float(bool(a) and bool(ev(n.b)))
        if n.op == "OU":
            return float(bool(a) or bool(ev(n.b)))
        b = ev(n.b)
        match n.op:
            case "+":
                return r(a + b)
            case "-":
                return r(a - b)
            case "*":
                return r(a * b)
            case "/":
                return r(a / b)
            case ">":
                return float(a > b)
            case ">=":
                return float(a >= b)
            case "<":
                return float(a < b)
            case "<=":
                return float(a <= b)
            case "=":
                return float(a == b)
            case "<>":
                return float(a != b)
        raise ValueError(n.op)

    return ev(no)


# --------------------------------------------------------------- arquivo


@dataclass
class Regra:
    posto: int
    mes: int  # 0 = todos os meses
    variante: int  # 0 = sem variação anual
    texto: str
    expressao: object
    linha: int


@dataclass
class Regras:
    regras: list[Regra]
    variantes_por_ano: dict[int, list[int]] = field(default_factory=dict)

    def postos(self) -> set[int]:
        return {r.posto for r in self.regras}

    def regra(
        self,
        posto: int,
        mes: int,
        ano_estudo: int = 1,
        prioridade: str = "mes",
        ano_alem_do_bloco2: str = "zero",
    ) -> Regra:
        """Regra do posto para o mês (1–12) e o ano do estudo (base 1).

        P-REG-05 (ESCOLHA, lacuna L16): com ``prioridade="mes"`` a regra do
        mês tem prioridade sobre a de mês 0; com ``"zero"``, o contrário.
        P-REG-07 (ESCOLHA, lacuna L16): ano do estudo além das variantes do
        bloco 2 usa a variante 0 (``"zero"``) ou a última informada
        (``"ultima"``).
        """
        if prioridade not in ("mes", "zero") or ano_alem_do_bloco2 not in ("zero", "ultima"):
            raise ValueError((prioridade, ano_alem_do_bloco2))
        variante = 0
        if posto in self.variantes_por_ano:
            v = self.variantes_por_ano[posto]
            if ano_estudo - 1 < len(v):
                variante = v[ano_estudo - 1]
            elif ano_alem_do_bloco2 == "ultima" and v:
                variante = v[-1]
        cands = [r for r in self.regras if r.posto == posto and r.variante == variante]
        for alvo in ((mes, 0) if prioridade == "mes" else (0, mes)):
            for r in cands:
                if r.mes == alvo:
                    return r
        raise KeyError((posto, mes, ano_estudo))


def ler_regras(caminho: Path, exigir_fim: bool = True) -> Regras:
    """U19 §3.10.

    Bloco 1 (após 2 comentários): posto I4 col. 2–5, mês I2 col. 10–11,
    variante I1 col. 17, regra A600 col. 22–621; termina com 9999.
    Bloco 2 (opcional, após 3 comentários): posto I4 col. 2–5 e uma variante
    I1 por ano nas colunas 12, 19, 26, …; termina com 9999.
    """
    linhas = ler_linhas(caminho)
    regras: list[Regra] = []
    # P-REG-06 (INFERIDO): os REGRAS.DAT públicos de 201701 a 201912 usam
    # um layout anterior, sem variante: mês I2 col. 11–12 e regra a partir
    # da col. 16, com o mesmo comprimento A600 do layout atual (ESCOLHA,
    # lacuna L15).
    # O layout é reconhecido pela linha-máscara (2º comentário): no atual o
    # campo do mês começa na coluna 10, que traz "X"; no antigo, a 10 é branca.
    mascara = linhas[1] if len(linhas) > 1 else ""
    atual = col(mascara, 10, 10) == "X"
    c_mes = (10, 11) if atual else (11, 12)
    c_regra = 22 if atual else 16
    i = 2
    fim1 = False
    while i < len(linhas):
        linha = linhas[i]
        i += 1
        if not linha.strip():
            continue
        posto = inteiro(linha, 2, 5)
        if posto == 9999:
            fim1 = True
            break
        texto = col(linha, c_regra, c_regra + 599).strip()
        try:
            expr = analisar(texto)
        except ErroLeitura as e:
            raise ErroLeitura(f"{caminho}:{i}: {e}") from None
        variante = inteiro(linha, 17, 17) if atual else 0
        regras.append(Regra(posto=posto, mes=inteiro(linha, *c_mes), variante=variante, texto=texto, expressao=expr, linha=i))
    # P-REG-08 (ESCOLHA, lacuna L15): bloco sem 9999 é erro quando
    # ``exigir_fim``; senão, o bloco vai até o fim do arquivo. Linhas em
    # branco são puladas nos dois blocos.
    if not fim1 and exigir_fim:
        raise ErroLeitura(f"{caminho}: bloco 1 sem 9999")
    variantes: dict[int, list[int]] = {}
    resto = [l for l in linhas[i:]]
    if any(l.strip() for l in resto):
        # P-REG-01: o bloco 2 começa depois de 3 comentários (U19 §3.10).
        fim2 = False
        for linha in resto[3:]:
            if not linha.strip():
                continue
            posto = inteiro(linha, 2, 5)
            if posto == 9999:
                fim2 = True
                break
            colunas = list(range(12, len(linha) + 1, 7))
            while colunas and not col(linha, colunas[-1], colunas[-1]).strip():
                colunas.pop()
            variantes[posto] = [inteiro(linha, c, c) for c in colunas]
        if not fim2 and exigir_fim:
            raise ErroLeitura(f"{caminho}: bloco 2 sem 9999")
    return Regras(regras=regras, variantes_por_ano=variantes)
