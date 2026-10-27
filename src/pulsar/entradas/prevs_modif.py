"""PREVS.RVx (U19 §4.7) e MODIF.DAT (U19 §4.11)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .texto import ErroLeitura, col, inteiro, ler_linhas

# ---------------------------------------------------------------- PREVS


@dataclass
class Previsao:
    serie: int
    posto: int
    semanas: list[int]


def ler_prevs(caminho: Path, n_semanas: int | None = None) -> dict[int, Previsao]:
    """Vazões semanais totais por posto.

    U19 §4.7: série I3 (col. 4–6), posto I3 (col. 9–11) e até seis I9
    (col. 13–21, 23–31, …, 63–71).
    P-PREVS-01: os campos são lidos com a largura estendida à esquerda até o
    separador (série col. 1–6, posto col. 7–11, semanas col. 12+10k a
    21+10k), o que dá o mesmo resultado em todo arquivo que respeita o
    manual e aceita o layout I6,I5,6I10 dos decks públicos.
    P-PREVS-02: lê ``n_semanas`` campos quando informado (DADGER reg. 7);
    senão, até o último campo não vazio.
    """
    saida: dict[int, Previsao] = {}
    for n, linha in enumerate(ler_linhas(caminho), start=1):
        if not linha.strip():
            continue
        serie = inteiro(linha, 1, 6)
        posto = inteiro(linha, 7, 11)
        campos = [inteiro(linha, 12 + 10 * k, 21 + 10 * k, padrao=None) for k in range(6)]
        if n_semanas is not None:
            if any(c is None for c in campos[:n_semanas]):
                raise ErroLeitura(f"{caminho}:{n}: menos de {n_semanas} semanas")
            semanas = [int(c) for c in campos[:n_semanas]]
        else:
            while campos and campos[-1] is None:
                campos.pop()
            semanas = [0 if c is None else c for c in campos]
        if posto in saida:
            raise ErroLeitura(f"{caminho}:{n}: posto {posto} repetido")
        saida[posto] = Previsao(serie=serie, posto=posto, semanas=semanas)
    return saida


# ---------------------------------------------------------------- MODIF


@dataclass
class Modif:
    palavra: str  # PARTIF ou VINCR, em maiúsculas
    usina: int
    campo3: int  # PARTIF: posto (informativo); VINCR: posto lateral
    campo4: int  # PARTIF: jusante (informativo); VINCR: posto total
    linha: int


def ler_modif(caminho: Path, exigir_fim: bool = True) -> list[Modif]:
    """P-MODIF-01, U19 §4.11: dois registros de comentário; palavra-chave A6 (col. 2–7),
    usina I3 (col. 9–11), dois valores I3 (col. 13–15 e 16–19); ``9999``
    encerra. Palavra-chave em maiúsculas ou minúsculas.

    P-MODIF-02 (ESCOLHA, lacuna L15): arquivo sem ``9999`` é erro quando
    ``exigir_fim``; senão, lê até o fim do arquivo.
    """
    saida: list[Modif] = []
    linhas = ler_linhas(caminho)
    for n, linha in enumerate(linhas[2:], start=3):
        if col(linha, 2, 5).strip() == "9999" or linha.strip() == "9999":
            break
        if not linha.strip():
            continue
        palavra = col(linha, 2, 7).strip().upper()
        if palavra not in ("PARTIF", "VINCR"):
            raise ErroLeitura(f"{caminho}:{n}: palavra-chave desconhecida {palavra!r}")
        saida.append(
            Modif(
                palavra=palavra,
                usina=inteiro(linha, 9, 11),
                campo3=inteiro(linha, 13, 15),
                campo4=inteiro(linha, 16, 19),
                linha=n,
            )
        )
    else:
        if exigir_fim:
            raise ErroLeitura(f"{caminho}: sem o registro 9999 final")
    return saida
