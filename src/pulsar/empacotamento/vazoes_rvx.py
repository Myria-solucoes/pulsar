"""VAZOES.RVx (VAZOES.XXX do U19 §5.3.4): árvore de vazões entregue ao DECOMP.

Layout em docs/layout-VAZOES.RVx.md (F2) e docs/gravacao-VAZOES.RVx.md (F7).
Acesso direto, RECL = NPOS*4 bytes, little-endian, sem marcadores:

1. int32: nº de usinas sem NW, NEST, aberturas[NEST], NPOS, nº de usinas NW
2. int32: códigos das usinas (P-CFG-16: as NW no fim)
3. int32: semanas previstas, dias excluídos, mês inicial, ano inicial, nº de
   postos, semanas observadas, código da versão; 12 bytes de cauda
4. float32: probabilidades dos nós, ceil(NNOS/NPOS) registros
5. semanais previstas (coluna = posto)
6. mensais geradas (coluna = posto)
7. semanais previstas considerando artificiais (coluna ENA)
8. mensais geradas considerando artificiais (coluna ENA)
9. mensais observadas (coluna ENA)
10. semanais observadas (coluna ENA)

Blocos 5 a 10 em int32. O gravador não lê nenhum VAZOES.RVx existente: tudo
vem dos argumentos.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass, field

import numpy as np

from ..configuracao import NEWAVE, Configuracao
from ..entradas.dadger import BlocoVazoes


def nint(x) -> np.ndarray:
    """F7-VZ-07 (ESCOLHA, lacuna L10): inteiro mais próximo com empate para
    longe do zero, a semântica do NINT do Fortran. Os arquivos públicos não
    têm nenhum valor gerado com fração .5 (F2-VZ-08)."""
    x = np.asarray(x, dtype=np.float64)
    if not np.isfinite(x).all():
        raise ValueError("valor não finito (NaN ou infinito) para arredondar")
    # rint arredonda empates para o par; só os empates exatos são corrigidos
    # (evita o erro de floor(x + 0.5) em x = 0.49999999999999994).
    r = np.rint(x)
    empate = np.abs(x - np.trunc(x)) == 0.5
    r = np.where(empate, np.trunc(x) + np.sign(x), r)
    return r.astype(np.int64)


def codificar_versao(versao: str) -> int:
    """F7-VZ-03 (ESCOLHA, lacuna L10): "maior.menor.revisão" ->
    maior*10000 + menor*100 + revisão, a inversa da decodificação F2-VZ-04b.
    Única amostra pública: "11.0.2" <-> 110002."""
    maior, menor, rev = (int(x) for x in versao.split("."))
    if not (0 <= menor < 100 and 0 <= rev < 100):
        raise ValueError(f"versão {versao!r} não cabe na codificação")
    return maior * 10000 + menor * 100 + rev


# F7-VZ-04 (INFERIDO na forma, ESCOLHA no padrão; lacuna L10): bytes 29-40 do
# registro 3, iguais nos três VAZOES.RVx públicos e sem significado
# identificado (docs/layout-VAZOES.RVx.md, "Não identificado").
CAUDA_REGISTRO3_PUBLICA = bytes.fromhex("2631305f2e2e44245f480000")


@dataclass(frozen=True)
class OpcoesEmpacotamento:
    # F7-VZ-03: versão gravada no registro 3 (padrão = a dos pacotes públicos).
    versao: str = "11.0.2"
    codificar_versao: Callable[[str], int] = codificar_versao
    # F7-VZ-04: cauda do registro 3; b"" grava zeros.
    cauda_registro3: bytes = CAUDA_REGISTRO3_PUBLICA
    # F7-VZ-07: arredondamento dos blocos gerados.
    arredondar: Callable[[np.ndarray], np.ndarray] = nint
    # F7-VZ-08 (ESCOLHA, lacuna L10): duas usinas na mesma coluna (posto 300
    # das PARTIF, por exemplo). "ultimo": vale a última na ordem da
    # configuração; "erro": levanta erro se os valores diferirem.
    colisao: str = "ultimo"
    # F7-VZ-11 (ESCOLHA, lacuna L15): semanas não observadas, semanas
    # observadas ou dias excluídos em branco no & VAZOES (reg. 7 e 8).
    # "zero": grava 0 (P-TXT-02); "erro": recusa o deck.
    campo_em_branco: str = "zero"

    def __post_init__(self):
        if self.colisao not in ("ultimo", "erro"):
            raise ValueError(self.colisao)
        if self.campo_em_branco not in ("zero", "erro"):
            raise ValueError(self.campo_em_branco)
        if len(self.cauda_registro3) > 12:
            raise ValueError("cauda do registro 3 tem no máximo 12 bytes")


@dataclass(frozen=True)
class RegistrosDeterministicos:
    """Blocos 5, 7, 9 e 10, já inteiros, na coluna final (entregues pela F5).

    prevista_semanal[s, posto-1], prevista_semanal_ena[s, coluna-1],
    observada_mensal[k, coluna-1] em ordem cronológica,
    observada_semanal[s, coluna-1].
    """

    prevista_semanal: np.ndarray
    prevista_semanal_ena: np.ndarray
    observada_mensal: np.ndarray
    observada_semanal: np.ndarray


@dataclass(frozen=True)
class ArvoreVazoes:
    """Conteúdo do VAZOES.RVx já tipado: o que é gravado, campo a campo."""

    n_usinas: int
    aberturas: tuple[int, ...]
    npos: int
    n_usinas_nw: int
    codigos: tuple[int, ...]
    semanas_previstas: int
    dias_excluidos: int
    mes_inicial: int
    ano_inicial: int
    n_postos: int
    semanas_observadas: int
    versao_codigo: int
    probabilidades: np.ndarray  # float32, um valor por nó
    prevista_semanal: np.ndarray
    gerada_mensal: np.ndarray
    prevista_semanal_ena: np.ndarray
    gerada_mensal_ena: np.ndarray
    observada_mensal: np.ndarray
    observada_semanal: np.ndarray
    cauda_registro3: bytes = field(default=CAUDA_REGISTRO3_PUBLICA, repr=False)

    @property
    def n_estagios(self) -> int:
        return len(self.aberturas)


def _colunas(valores: np.ndarray, colunas: list[int], npos: int, colisao: str, nome: str) -> np.ndarray:
    """Espalha valores[:, i] na coluna colunas[i] (1..npos), na ordem i."""
    out = np.zeros((valores.shape[0], npos), dtype=np.int64)
    escrita = np.zeros(npos, dtype=bool)
    for i, c in enumerate(colunas):
        if not 1 <= c <= npos:
            raise ValueError(f"{nome}: coluna {c} fora de 1..{npos}")
        if colisao == "erro" and escrita[c - 1] and (out[:, c - 1] != valores[:, i]).any():
            raise ValueError(f"{nome}: valores diferentes na coluna {c}")
        out[:, c - 1] = valores[:, i]
        escrita[c - 1] = True
    return out


def montar_arvore(
    configuracao: Configuracao,
    vazoes: BlocoVazoes,
    n_postos: int,
    geradas: np.ndarray,
    geradas_ena: np.ndarray,
    folhas: np.ndarray,
    deterministicos: RegistrosDeterministicos,
    npos: int,
    opcoes: OpcoesEmpacotamento | None = None,
) -> ArvoreVazoes:
    """Monta o conteúdo do VAZOES.RVx.

    geradas, geradas_ena: float64 [cenário, NINT-1] (GEVAZP.OUT e
    vazoesia.out); folhas: float32, probabilidades das folhas (PROBVAZ.DAT);
    n_postos: nº de postos do histórico (Deck.n_postos).
    """
    op = opcoes or OpcoesEmpacotamento()
    det = deterministicos

    # F7-VZ-02: estágios = semanas não observadas (uma abertura cada) + os
    # estágios estocásticos do & VAZOES. Só um estágio estocástico tem layout
    # verificado (F2-VZ-09, F2-ARV-03).
    if len(vazoes.aberturas) != 1:
        raise NotImplementedError(f"aberturas {vazoes.aberturas}: só um estágio estocástico é suportado")
    def campo(nome: str, obrigatorio: bool = False) -> int:
        v = getattr(vazoes, nome)
        if v is not None:
            return v
        if obrigatorio or op.campo_em_branco == "erro":
            raise ValueError(f"& VAZOES: campo {nome} em branco")
        return 0  # F7-VZ-11

    nprev = campo("semanas_nao_observadas")
    nobs = campo("semanas_observadas")
    dias = campo("dias_excluidos")
    # F7-VZ-11: mês inicial (reg. 4) em branco é recusado (sem campo duplicado).
    mes = campo("mes_inicial", True)
    # F7-VZ-12 (P-DADG-12, U19 §4.5): sem o ano no reg. 4, vale o do reg. 6,
    # como em configuracao.montar_configuracao; sem os dois, erro.
    ano = vazoes.ano_inicial or vazoes.ano_inicial_estudo
    if not ano:
        raise ValueError("& VAZOES: campos ano_inicial (reg. 4) e ano_inicial_estudo (reg. 6) em branco")
    ncen = vazoes.aberturas[0]
    aberturas = (1,) * nprev + (ncen,)

    if geradas.shape[0] != ncen or geradas_ena.shape[0] != ncen or len(folhas) != ncen:
        raise ValueError(
            f"{ncen} aberturas, mas {geradas.shape[0]}/{geradas_ena.shape[0]} cenários e {len(folhas)} folhas"
        )
    if det.prevista_semanal.shape[0] != nprev or det.prevista_semanal_ena.shape[0] != nprev:
        raise ValueError(f"esperadas {nprev} semanas previstas")
    if det.observada_semanal.shape[0] != nobs:
        raise ValueError(f"esperadas {nobs} semanas observadas")

    # F7-VZ-05: colunas por NINT na ordem da configuração completa (base +
    # laterais); bloco 6 na coluna do posto, bloco 8 na coluna ENA.
    completa = configuracao.completa
    n = len(completa)
    postos = [u.posto for u in completa]
    ena = [u.posto_artificial or u.posto for u in completa]
    ger = _colunas(op.arredondar(geradas[:, :n]), postos, npos, op.colisao, "gerada")
    ger_ena = _colunas(op.arredondar(geradas_ena[:, :n]), ena, npos, op.colisao, "gerada ENA")

    # F2-VZ-10: probabilidade 1 para cada estágio semanal, depois as folhas.
    prob = np.concatenate([np.ones(nprev, dtype=np.float32), np.asarray(folhas, dtype=np.float32)])

    base = configuracao.usinas
    return ArvoreVazoes(
        n_usinas=sum(u.status != NEWAVE for u in base),
        aberturas=aberturas,
        npos=npos,
        n_usinas_nw=sum(u.status == NEWAVE for u in base),
        codigos=tuple(configuracao.ordem_vazoes_rv()),
        semanas_previstas=nprev,
        dias_excluidos=dias,
        mes_inicial=mes,
        ano_inicial=ano,
        n_postos=n_postos,
        semanas_observadas=nobs,
        versao_codigo=op.codificar_versao(op.versao),
        probabilidades=prob,
        prevista_semanal=det.prevista_semanal,
        gerada_mensal=ger,
        prevista_semanal_ena=det.prevista_semanal_ena,
        gerada_mensal_ena=ger_ena,
        observada_mensal=det.observada_mensal,
        observada_semanal=det.observada_semanal,
        cauda_registro3=op.cauda_registro3,
    )


def _inteiros(nome: str, m: np.ndarray, npos: int) -> np.ndarray:
    m = np.asarray(m)
    if m.ndim != 2 or m.shape[1] != npos:
        raise ValueError(f"{nome}: forma {m.shape}, esperado (n, {npos})")
    if not np.issubdtype(m.dtype, np.integer):
        raise TypeError(f"{nome}: valores devem ser inteiros, não {m.dtype}")
    if (m < -(2**31)).any() or (m >= 2**31).any():
        raise OverflowError(f"{nome}: valor fora de int32")
    return m.astype("<i4")


def serializar_vazoes_rvx(a: ArvoreVazoes) -> bytes:
    """Bytes do VAZOES.RVx na ordem do U19 §5.3.4 (F7-VZ-01)."""
    npos = a.npos
    nest = a.n_estagios

    r1 = np.zeros(npos, dtype="<i4")
    cab = [a.n_usinas, nest, *a.aberturas, npos, a.n_usinas_nw]
    if len(cab) > npos:
        raise ValueError("registro 1 não cabe em NPOS inteiros")
    r1[: len(cab)] = cab

    r2 = np.zeros(npos, dtype="<i4")
    if len(a.codigos) != a.n_usinas + a.n_usinas_nw or len(a.codigos) > npos:
        raise ValueError(f"{len(a.codigos)} códigos para {a.n_usinas}+{a.n_usinas_nw} usinas")
    r2[: len(a.codigos)] = a.codigos

    campos3 = [a.semanas_previstas, a.dias_excluidos, a.mes_inicial, a.ano_inicial,
               a.n_postos, a.semanas_observadas, a.versao_codigo]
    r3 = np.array(campos3, dtype="<i4").tobytes() + a.cauda_registro3
    r3 = r3.ljust(npos * 4, b"\x00")

    prob = np.asarray(a.probabilidades)
    if prob.dtype != np.float32:
        raise TypeError("probabilidades devem ser float32")
    nnos = sum(int(np.prod(a.aberturas[: k + 1])) for k in range(nest))
    if len(prob) != nnos:
        raise ValueError(f"{len(prob)} probabilidades para {nnos} nós")
    nregp = -(-nnos // npos)
    r4 = np.zeros(nregp * npos, dtype="<f4")
    r4[:nnos] = prob

    blocos = [
        ("prevista_semanal", a.prevista_semanal),
        ("gerada_mensal", a.gerada_mensal),
        ("prevista_semanal_ena", a.prevista_semanal_ena),
        ("gerada_mensal_ena", a.gerada_mensal_ena),
        ("observada_mensal", a.observada_mensal),
        ("observada_semanal", a.observada_semanal),
    ]
    partes = [r1.tobytes(), r2.tobytes(), r3, r4.tobytes()]
    partes += [_inteiros(nome, m, npos).tobytes() for nome, m in blocos]
    return b"".join(partes)


def gravar_vazoes_rvx(caminho: str | os.PathLike, arvore: ArvoreVazoes) -> None:
    with open(caminho, "wb") as f:
        f.write(serializar_vazoes_rvx(arvore))
