"""Acesso somente leitura às coleções parciais de decks do ONS (03 §1.2).

- GEVAZP operacional: ``<ano>/<AAAAMM>_<pmo|revN>/`` com DADGER, HIDR e
  REGRAS.
- DECOMP valor esperado: zips com ``dadger.rvN``, ``hidr.dat`` e
  ``vazoes.rvN``; o registro 2 do ``vazoes.rvN`` traz os códigos das usinas
  na ordem da configuração (U19 §5.3.4).
"""

from __future__ import annotations

import io
import os
import re
import struct
import zipfile
from dataclasses import dataclass
from pathlib import Path

# Diretórios locais das coleções (03 §1.2), por variável de ambiente.
RAIZ_GEVAZP = Path(os.environ.get("PULSAR_COLECAO_GEVAZP", "/nao-configurada"))
RAIZ_DECOMP = Path(os.environ.get("PULSAR_COLECAO_DECOMP", "/nao-configurada"))


def disponivel() -> bool:
    return RAIZ_GEVAZP.is_dir()


@dataclass
class CasoGevazp:
    ano: int
    mes: int
    rev: int
    diretorio: Path
    dadger: Path
    hidr: Path | None
    regras: Path | None

    @property
    def nome(self) -> str:
        return f"{self.ano}{self.mes:02d}_rv{self.rev}"


_PASTA = re.compile(r"^(\d{4})(\d{2})_(pmo|rev(\d+))$")


def casos_gevazp() -> list[CasoGevazp]:
    casos = []
    for ano_dir in sorted(RAIZ_GEVAZP.iterdir()):
        if not ano_dir.is_dir():
            continue
        for d in sorted(ano_dir.iterdir()):
            m = _PASTA.match(d.name)
            if not m:
                continue
            rev = 0 if m.group(3) == "pmo" else int(m.group(4))
            dadgers = sorted(p for p in d.iterdir() if p.name.upper().startswith("DADGER."))
            if not dadgers:
                continue
            hidr = d / "HIDR.DAT"
            regras = d / "REGRAS.DAT"
            casos.append(
                CasoGevazp(
                    ano=int(m.group(1)), mes=int(m.group(2)), rev=rev, diretorio=d,
                    dadger=dadgers[0], hidr=hidr if hidr.is_file() else None,
                    regras=regras if regras.is_file() else None,
                )
            )
    return casos


_ZIP = (
    re.compile(r"__ve_(\d{2})_(\d{4})_r(\d+)\.zip$", re.I),  # 2005–2013: MM_AAAA
    re.compile(r"__ve_(\d{4})(\d{2})_r(\d+)\.zip$", re.I),  # 2014–2019: AAAAMM
    re.compile(r"__DEC_ONS_(\d{2})(\d{4})_RV(\d+)_VE\.zip$", re.I),  # 2020–: MMAAAA
)


def zips_decomp() -> dict[tuple[int, int, int], Path]:
    """(ano, mês, revisão) -> zip do deck DECOMP de valor esperado."""
    saida: dict[tuple[int, int, int], Path] = {}
    if not RAIZ_DECOMP.is_dir():
        return saida
    for ano_dir in sorted(RAIZ_DECOMP.iterdir()):
        for z in sorted(ano_dir.glob("*.zip")):
            for i, rx in enumerate(_ZIP):
                m = rx.search(z.name)
                if m:
                    a, b, r = (int(x) for x in m.groups())
                    ano, mes = (b, a) if i in (0, 2) else (a, b)
                    saida.setdefault((ano, mes, r), z)
                    break
    return saida


def membro(z: zipfile.ZipFile, nome: str) -> bytes | None:
    alvo = nome.lower()
    for n in z.namelist():
        if n.lower().rsplit("/", 1)[-1] == alvo:
            return z.read(n)
    return None


def vazoes_rv_do_zip(caminho: Path) -> bytes | None:
    """Conteúdo do ``vazoes.rvN`` de um deck DECOMP, lido em memória.

    Os zips até 2019 trazem o deck dentro de outro zip (``DEC_ONS_*.zip``,
    ao lado de ``RESULTADOS_*.zip``); abre-se só o primeiro nível interno.
    """
    with zipfile.ZipFile(caminho) as z:
        for n in z.namelist():
            if n.lower().rsplit("/", 1)[-1].startswith("vazoes.rv"):
                return z.read(n)
        for n in z.namelist():
            base = n.rsplit("/", 1)[-1].upper()
            if base.endswith(".ZIP") and not base.startswith("RESULTADOS"):
                with zipfile.ZipFile(io.BytesIO(z.read(n))) as interno:
                    for m in interno.namelist():
                        if m.lower().rsplit("/", 1)[-1].startswith("vazoes.rv"):
                            return interno.read(m)
    return None


def registro1_vazoes_rv(dados: bytes, n_postos: int = 320) -> tuple[int, ...]:
    return struct.unpack_from(f"<{n_postos}i", dados, 0)


def codigos_vazoes_rv(dados: bytes, n_postos: int = 320) -> list[int]:
    """Registro 2 do VAZOES.RVx (U19 §5.3.4): códigos até o primeiro valor
    fora de 1..n_postos. O preenchimento é zero nos arquivos atuais e
    brancos (0x20202020) nos antigos."""
    R = 4 * n_postos
    reg = struct.unpack_from(f"<{n_postos}i", dados, R)
    saida = []
    for c in reg:
        if not 1 <= c <= n_postos:
            break
        saida.append(c)
    return saida
