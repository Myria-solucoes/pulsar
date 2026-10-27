"""Baixa as fontes públicas listadas em fontes/MANIFESTO.tsv.

O texto das fontes já está em fontes/; os originais (PDF e HTML) não ficam
no git. Este script baixa os originais que o servidor de origem entregar,
confere o SHA-256 contra o manifesto e regenera o .txt de cada página e PDF
(`pdftotext -layout`, do poppler). O portal de documentação técnica do CEPEL
costuma recusar downloads automáticos; nesse caso o script diz qual relatório
falta, e basta baixá-lo pelo navegador em
https://www.cepel.br/produtos/documentacao-tecnica/ e salvá-lo com o nome
indicado em fontes/cepel/.

Uso: python ferramentas/baixar_fontes.py
"""

from __future__ import annotations

import hashlib
import html
import re
import shutil
import subprocess
import sys
import urllib.request
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
MANIFESTO = RAIZ / "fontes" / "MANIFESTO.tsv"


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def baixar(url: str, destino: Path) -> bool:
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "pulsar-fontes"})
        with urllib.request.urlopen(req, timeout=60) as r:
            destino.write_bytes(r.read())
        return True
    except OSError as e:
        print(f"  falhou: {e}")
        return False


def html_para_txt(src: Path, url: str) -> None:
    t = src.read_text(encoding="utf-8", errors="replace")
    t = re.sub(r"(?is)<(script|style).*?</\1>", "", t)
    t = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>|</tr>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "", t))
    t = re.sub(r"\n\s*\n+", "\n\n", t)
    cab = f"Fonte: {url} (baixado em {date.today():%d/%m/%Y})\n\n"
    src.with_suffix(".txt").write_text(cab + t.strip() + "\n", encoding="utf-8")


def pdf_para_txt(src: Path) -> None:
    if shutil.which("pdftotext"):
        subprocess.run(["pdftotext", "-layout", str(src), str(src.with_suffix(".txt"))], check=True)
    else:
        print("  pdftotext não encontrado; instale o poppler para gerar o .txt")


def main() -> int:
    faltam = []
    for linha in MANIFESTO.read_text(encoding="utf-8").splitlines()[1:]:
        caminho, formato, url, esperado = linha.split("\t")
        base = RAIZ / caminho
        base.parent.mkdir(parents=True, exist_ok=True)
        ext = {"pdf+txt": ".pdf", "pdf": ".pdf", "html+txt": ".html"}.get(formato, "")
        arq = base.with_name(base.name + ext) if ext else base
        print(caminho)
        if not arq.exists():
            if url.endswith("/documentacao-tecnica/") or not baixar(url, arq):
                faltam.append(arq.relative_to(RAIZ))
                continue
        if sha256(arq) != esperado:
            print("  aviso: SHA-256 diferente do manifesto (a origem pode ter mudado)")
        if formato == "html+txt":
            html_para_txt(arq, url)
        elif formato == "pdf+txt":
            pdf_para_txt(arq)
    if faltam:
        print("\nBaixe pelo navegador e salve com estes nomes:")
        for f in faltam:
            print(f"  {f}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
