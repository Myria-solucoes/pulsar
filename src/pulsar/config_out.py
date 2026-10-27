"""Gravação e leitura do ``config.out`` (layout em docs/layout-config-out.md).

Arquivo binário de registros de 160 bytes, little-endian, sem marcadores
de registro (acesso direto). Dois blocos:

1. cabeçalho com o número de usinas da configuração base + um registro por
   usina;
2. cabeçalho com o número de usinas incluindo os postos laterais + um
   registro por usina (as da base, na mesma ordem, e depois os laterais).
"""

from __future__ import annotations

import struct
from collections.abc import Callable
from pathlib import Path

from .configuracao import Configuracao, UsinaConfig

# P-COUT-01..04 (INFERIDO, testes T1 contra 202609/202610 config.out).
TAMANHO_REGISTRO = 160
_REG = struct.Struct("<i12s3id2s7i")  # 66 bytes úteis
assert _REG.size == 66
_ANTES = struct.Struct("<i12s3i")  # bytes 0-27
_DEPOIS = struct.Struct("<2s7i")  # bytes 36-65


def percentual_real8(valor: float) -> bytes:
    """P-COUT-04 (ESCOLHA, lacuna L13): bytes 28-35 = real*8 little-endian."""
    return struct.pack("<d", valor)


def cabecalho_bloco2(cfg: Configuracao) -> tuple[int, ...]:
    """P-COUT-03 (ESCOLHA no 2º inteiro, lacuna L13): (total com laterais,
    total com laterais, nº de postos laterais)."""
    n = len(cfg.completa)
    return (n, n, len(cfg.laterais))


def _registro(u: UsinaConfig, percentual: Callable[[float], bytes]) -> bytes:
    p = percentual(u.percentual_minimo)
    if len(p) != 8:
        raise ValueError("o percentual ocupa 8 bytes (28-35)")
    corpo = (
        _ANTES.pack(u.numero, u.nome[:12].ljust(12, b" "), u.posto, u.jusante, u.bacia)
        + p
        + _DEPOIS.pack(
            u.status.encode("latin-1")[:2].ljust(2, b" "),
            u.ajuste_automatico,
            u.ano_inicial,
            u.ano_final,
            u.tempo_viagem,
            u.posto_lateral,
            u.defasagem,
            u.posto_artificial,
        )
    )
    return corpo.ljust(TAMANHO_REGISTRO, b"\x00")


def _cabecalho(*valores: int) -> bytes:
    return struct.pack(f"<{len(valores)}i", *valores).ljust(TAMANHO_REGISTRO, b"\x00")


def gerar_config_out(
    cfg: Configuracao,
    cabecalho2: Callable[[Configuracao], tuple[int, ...]] = cabecalho_bloco2,
    percentual: Callable[[float], bytes] = percentual_real8,
) -> bytes:
    # P-COUT-02: cabeçalho do bloco 1 = número de usinas da base.
    partes = [_cabecalho(len(cfg.usinas))]
    partes += [_registro(u, percentual) for u in cfg.usinas]
    partes.append(_cabecalho(*cabecalho2(cfg)))
    partes += [_registro(u, percentual) for u in cfg.completa]
    return b"".join(partes)


def gravar_config_out(cfg: Configuracao, caminho: Path) -> None:
    Path(caminho).write_bytes(gerar_config_out(cfg))


def ler_config_out(caminho: Path) -> tuple[list[dict], list[dict]]:
    """Decodifica um config.out em dois blocos de dicionários."""
    dados = Path(caminho).read_bytes()
    R = TAMANHO_REGISTRO
    if len(dados) % R:
        raise ValueError(f"{caminho}: tamanho {len(dados)} não é múltiplo de {R}")
    regs = [dados[i : i + R] for i in range(0, len(dados), R)]
    blocos = []
    i = 0
    while i < len(regs):
        n, = struct.unpack_from("<i", regs[i], 0)  # 1º inteiro do cabeçalho
        bloco = []
        for r in regs[i + 1 : i + 1 + n]:
            c = _REG.unpack_from(r, 0)
            bloco.append(
                dict(
                    numero=c[0], nome=c[1], posto=c[2], jusante=c[3], bacia=c[4],
                    percentual_minimo=c[5], status=c[6].decode("latin-1"),
                    ajuste_automatico=c[7], ano_inicial=c[8], ano_final=c[9],
                    tempo_viagem=c[10], posto_lateral=c[11], defasagem=c[12],
                    posto_artificial=c[13], resto=r[66:],
                )
            )
        blocos.append(bloco)
        i += 1 + n
    if len(blocos) != 2:
        raise ValueError(f"{caminho}: esperava 2 blocos, achou {len(blocos)}")
    return blocos[0], blocos[1]
