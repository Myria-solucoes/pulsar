"""Gera o config.out de um deck e compara com o público, se existir.

Uso: python3 ferramentas/gerar_config_out.py <deck> <saida> [--dadger NOME]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from pulsar.config_out import TAMANHO_REGISTRO, gerar_config_out  # noqa: E402
from pulsar.configuracao import montar_configuracao  # noqa: E402
from pulsar.entradas import ler_deck  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("deck", type=Path)
    ap.add_argument("saida", type=Path)
    ap.add_argument("--dadger", default=None)
    a = ap.parse_args()
    cfg = montar_configuracao(ler_deck(a.deck, dadger=a.dadger))
    dados = gerar_config_out(cfg)
    a.saida.write_bytes(dados)
    print(f"{a.saida}: {len(dados)} bytes, {len(cfg.usinas)} usinas + {len(cfg.laterais)} laterais")
    publico = a.deck / "config.out"
    if publico.is_file():
        p = publico.read_bytes()
        regs = sorted({i // TAMANHO_REGISTRO for i in range(min(len(p), len(dados))) if p[i] != dados[i]})
        igual = p == dados
        print(f"comparação com {publico}: {'IGUAL' if igual else 'DIFERENTE'}; registros diferentes: {regs[:20]}")
        return 0 if igual else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
