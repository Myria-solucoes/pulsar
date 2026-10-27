# Layout de `vazoesia.out` (incrementais considerando artificiais)

Leitor: `pulsar.oraculos.ler_incrementais_artificiais`. Testes:
`tests/test_oraculo_series_arvore.py`. Proveniência: F2-ARV-01..04.

## Layout

Idêntico ao do `GEVAZP.OUT` (acesso direto, `RECL = NPOS*8`, um registro de
float64 por cenário, coluna `NINT-1`). U19 §5.3.2: "Um arquivo de nome fixo
igual a VAZOESIA.OUT, com formato idêntico ao descrito nos itens 4.3.1.1 e
4.3.1.2, será criado contendo os cenários de vazões incrementais calculados
considerando os postos de vazões artificiais presentes na configuração."

Divergência menor com o U19: o nome no pacote é `vazoesia.out` (minúsculas).

## Confirmação

Igual ao `VAZOESIA.CSV` a 2 casas em todos os valores, nos dois decks.

A coluna continua indexada por NINT, mas o CSV rotula as 26 usinas que têm
posto artificial (coluna `PART` da configuração) com esse posto, e é nessa
coluna que o `VAZOES.RVx` grava o valor (ver `layout-VAZOES.RVx.md`):

```text
GEVAZP.REL:  29  37 BARRA BONITA  237  38  1931 2024  0 0 0 0 2  37  0.00  BACIA_010
VAZOESIA.CSV: 1,   37, BARRA BONITA,    1, 0.00, ..., 0.00,   249.18, 0.00, 0.00,
```

Diferente do `GEVAZP.OUT`, este arquivo tem valores negativos (mínimo
-197.43 em 202609, -288.70 em 202610).

## Observações

- Nas colunas de `NILO PECANHA`, `P. PASSOS`, `BELO MONTE` e `PIMENTAL` todos
  os valores são exatamente representáveis em float32, nos dois decks. Isso
  sugere aritmética em precisão simples nas regras dos artificiais
  (lacuna L9), mas não prova.

Resolvido pela frente F6 (F6-ART-03): as regras leem cada `VAZ(n)` em
precisão simples e operam em precisão dupla; ver
[totalizacao-e-artificiais.md](totalizacao-e-artificiais.md).

## Não identificado

- Árvores com mais de um período estocástico.
