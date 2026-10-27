# Layout de `correlt.out` (estatísticas das séries totais)

Leitor: `pulsar.oraculos.ler_correlt`. Testes: `tests/test_oraculo_correl.py`
e `tests/test_oraculo_relacoes.py`. Proveniência: F2-CT-01..02, F2-CI-10, F2-REL-01.

Mesmos formatos de registro do `correli.out` (`layout-correli.out.md`):
`RECL = 120` bytes; 7 678 200 bytes = 63 985 registros nos dois decks.

## Cabeçalho

Registro 1: int32 `N` = 172 (todas as usinas da configuração, na ordem
NINT). Registros 2..173: pares (NINT, registro inicial), com início em 174 e
passo `L = 371`. O último bloco termina exatamente no fim do arquivo.

## Bloco (L = 371)

| Posições | Formato | Conteúdo |
| --- | --- | --- |
| 1 | E | média mensal histórica da vazão total |
| 2 | E | desvio mensal histórico |
| 3-13 | E | correlograma, defasagens 1..11 |
| 14-185 | C | correlações espaciais históricas com as 172 séries |
| 186 | E | média gerada |
| 187 | E | desvio gerado |
| 188-198 | E | correlograma gerado (nulo) |
| 199-370 | C | correlações espaciais sintéticas com as 172 séries |
| 371 | N | média, desvio, r1 das médias anuais; 2 campos não identificados |

Não há FACP nem modelo AR (as totais não são modeladas). Aqui a lista
histórica é igual ao índice, então não há deslocamento nem linhas perdidas.

Fórmula geral do tamanho do bloco (F2-CI-10), válida para os dois arquivos: com `nl` = 11
defasagens, `N` séries no índice e `NH` na lista histórica,
`L = 17 + 3·nl + 2·NH` (correli) e `L = 5 + 2·nl + 2·NH` (correlt).

## Evidência no texto público

- "RESULTADOS PARA VAZOES TOTALIZADAS" (155 páginas): linhas `HIST` e `GER`
  de média e desvio, 1 casa; FUNIL-GRANDE `HIST 570.5 510.3 ...`,
  `GER ... 110.7` = registros 1 e 186 do bloco 3.
- "CORRELACAO ESPACIAL HISTORICA ... (TODOS POSTOS)": `CAMARGOS ->ITUTINGA
  1.00000 ...` (vazões totais iguais), `CAMARGOS ->FUNIL-GRANDE 0.92640 ...`.
- "CORRELACAO ESPACIAL SINTETICA ... (TODOS POSTOS)" para as sintéticas.

Testes: todos os 14 706 pares das duas tabelas (5 casas), médias e desvios
das 155 séries com página, nos dois decks. A média e o desvio gerados das
172 séries batem com `VAZTOTGD.DAT` ponderado pelo `PROBVAZ.DAT` (1e-10).

## Não identificado

- Campos 4 e 5 do registro anual.
- Correlograma gerado (nulo).
- Por que só 155 das 172 séries totais têm página no REL (as PN e as de
  incremental nula ficam de fora do relatório, mas estão no binário).
