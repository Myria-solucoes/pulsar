# Layout de `VAZTOTGD.DAT` (totais gerados)

Leitor: `pulsar.oraculos.ler_totais_gerados`. Testes:
`tests/test_oraculo_series_arvore.py`. Proveniência: F2-ARV-01..03.

## Layout

Idêntico ao do `GEVAZP.OUT` (ver `layout-GEVAZP.OUT.md`): acesso direto,
`RECL = NPOS*8`, um registro de `NPOS` float64 por cenário do mês
estocástico, coluna `NINT-1`. U19 §5.3.1 ("Arquivo de séries sintéticas de
vazões totais", nome dado no `Arquivos.DAT`: "CENARIOS GERADOS VAZAO TOTAL:
VAZTOTGD.DAT") e §5.3.1.2.

## Confirmação

| Deck | Registros | Colunas não nulas |
| --- | --- | --- |
| 202609 | 259 | 166 de 172 |
| 202610 | 228 | 166 de 172 |

Igual ao `VAZOEST.CSV` a 2 casas em todos os valores dos dois decks.
Exemplo (202609, cenário 1):

```text
VAZOEST.CSV:  1,  211, FUNIL-GRANDE,    1, 249.00, ..., 91.57,   100.90, 0.00, 0.00,
VAZTOTGD.DAT: registro 1, coluna 2 = 100.8977...
```

A média ponderada pelas probabilidades (`PROBVAZ.DAT`) de cada coluna bate
com a linha `GER` de "RESULTADOS PARA VAZOES TOTALIZADAS" do `GEVAZP.REL`
(1 casa), por exemplo FUNIL-GRANDE `110.7`.

## Não identificado

- Nenhum valor negativo; não sabemos se há truncamento em zero ou se é só
  consequência do modelo.
- Árvores com mais de um período estocástico não foram observadas.
