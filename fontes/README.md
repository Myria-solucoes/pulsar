# Fontes públicas

Esta pasta guarda o texto das fontes públicas citadas no `PROVENIENCIA.md` e
na especificação, para que qualquer pessoa possa conferir cada citação.

**Estes arquivos são de terceiros e não estão sob a Licença Apache 2.0 do
Pulsar.** Os direitos são dos autores: CEPEL (relatórios técnicos e
documentação LIBS) e Royal Statistical Society (AS 136). Estão aqui só como
referência, com a origem de cada um.

| Pasta | O que é |
| --- | --- |
| `cepel/` | texto (`pdftotext -layout`) dos relatórios técnicos do CEPEL sobre o GEVAZP |
| `libs/` | texto das páginas da documentação LIBS do CEPEL, `https://see.cepel.br/manual/libs/latest/`, com a URL no topo |
| `algoritmos/` | AS 136 de Hartigan & Wong (1979), da StatLib |

Os PDFs e as páginas HTML originais não ficam no git. `MANIFESTO.tsv` lista
cada fonte com a origem e o SHA-256 do original que usamos, e
`python ferramentas/baixar_fontes.py` baixa o que a origem permitir e confere
o SHA-256. O portal de documentação técnica do CEPEL
(https://www.cepel.br/produtos/documentacao-tecnica/) costuma recusar
downloads automáticos; nesse caso, baixe o PDF pelo navegador.

O catálogo comentado, com o que cada fonte cobre, está em `01-fontes.md`.
