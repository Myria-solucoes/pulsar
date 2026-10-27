"""Arquivos binários de acesso direto: HIDR.DAT, POSTOS.DAT e VAZOES.DAT.

U19 §3.6, §3.7, §4.6, §4.9 e §4.10 dizem que são arquivos não formatados de
acesso direto, mas não dão o layout de cada registro. Os layouts abaixo
foram inferidos dos arquivos públicos (ver PROVENIENCIA.md, P-BIN-*).
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

from .texto import ErroLeitura, ler_bytes

# --------------------------------------------------------------------- HIDR


@dataclass
class UsinaHidr:
    codigo: int
    nome: str  # 12 caracteres, sem os brancos à direita
    nome_bruto: bytes
    posto: int
    jusante: int


@dataclass
class Hidr:
    tamanho_registro: int
    usinas: dict[int, UsinaHidr]

    def __getitem__(self, codigo: int) -> UsinaHidr:
        return self.usinas[codigo]


def ler_hidr(caminho: Path, n_registros: int = 320) -> Hidr:
    """Cadastro do DECOMP; registro k = usina de código k (U19 §4.6).

    P-BIN-01: tamanho do registro = tamanho do arquivo / 320.
    P-BIN-02: nome A12 no byte 0, posto int32 no byte 12, jusante int32 no
    byte 32 (little-endian).
    """
    dados = ler_bytes(caminho)
    if len(dados) % n_registros:
        raise ErroLeitura(f"{caminho}: tamanho {len(dados)} não é múltiplo de {n_registros}")
    R = len(dados) // n_registros
    usinas: dict[int, UsinaHidr] = {}
    for k in range(n_registros):
        r = dados[k * R : (k + 1) * R]
        nome_bruto = r[0:12]
        posto, = struct.unpack_from("<i", r, 12)
        jusante, = struct.unpack_from("<i", r, 32)
        usinas[k + 1] = UsinaHidr(
            codigo=k + 1,
            nome=nome_bruto.decode("latin-1").rstrip(),
            nome_bruto=nome_bruto,
            posto=posto,
            jusante=jusante,
        )
    return Hidr(tamanho_registro=R, usinas=usinas)


# ------------------------------------------------------------------- POSTOS


@dataclass
class Posto:
    numero: int
    nome: str
    ano_inicial: int
    ano_final: int


def ler_postos(caminho: Path, n_postos: int = 320) -> dict[int, Posto]:
    """POSTOS.DAT, um registro por posto (U19 §3.7).

    P-BIN-03: registro de 20 bytes: nome A12, ano inicial int32, ano final
    int32.
    """
    dados = ler_bytes(caminho)
    R = 20
    if len(dados) != n_postos * R:
        raise ErroLeitura(f"{caminho}: esperado {n_postos * R} bytes, achou {len(dados)}")
    postos: dict[int, Posto] = {}
    for k in range(n_postos):
        nome = dados[k * R : k * R + 12].decode("latin-1").rstrip()
        ini, fim = struct.unpack_from("<2i", dados, k * R + 12)
        postos[k + 1] = Posto(numero=k + 1, nome=nome, ano_inicial=ini, ano_final=fim)
    return postos


# ------------------------------------------------------------------ VAZOES


@dataclass
class HistoricoVazoes:
    """Histórico mensal de vazões naturais totais (U19 §3.6)."""

    ano_inicial: int
    n_postos: int
    valores: tuple[int, ...]  # mês-major: (mes_absoluto * n_postos + posto-1)

    @property
    def n_meses(self) -> int:
        return len(self.valores) // self.n_postos

    @property
    def ano_final(self) -> int:
        return self.ano_inicial + (self.n_meses - 1) // 12

    def vazao(self, posto: int, ano: int, mes: int) -> int:
        m = (ano - self.ano_inicial) * 12 + (mes - 1)
        if not (0 <= m < self.n_meses) or not (1 <= posto <= self.n_postos):
            raise IndexError((posto, ano, mes))
        return self.valores[m * self.n_postos + posto - 1]

    def serie(self, posto: int) -> list[int]:
        return [self.valores[m * self.n_postos + posto - 1] for m in range(self.n_meses)]


def ler_vazoes_dat(caminho: Path, ano_inicial: int, n_postos: int = 320) -> HistoricoVazoes:
    """VAZOES.DAT: um registro por mês com ``n_postos`` vazões (U19 §3.6).

    P-BIN-04: cada vazão é int32 little-endian; o primeiro registro é janeiro
    do ano inicial do histórico (GEVAZP.DAT registro 16).
    """
    dados = ler_bytes(caminho)
    R = 4 * n_postos
    if len(dados) % R:
        raise ErroLeitura(f"{caminho}: tamanho {len(dados)} não é múltiplo de {R}")
    n = len(dados) // 4
    return HistoricoVazoes(ano_inicial=ano_inicial, n_postos=n_postos, valores=struct.unpack(f"<{n}i", dados))
