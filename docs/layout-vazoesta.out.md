# Layout de `vazoesta.out` (totais considerando artificiais)

Leitor: `pulsar.oraculos.ler_totais_artificiais`. Testes:
`tests/test_oraculo_series_arvore.py`. Proveniência: F2-ARV-01..04.

## Layout

Idêntico ao do `GEVAZP.OUT`. U19 §5.3.1.2: "Um arquivo de nome fixo igual a
VAZOESTA.OUT, com formato idêntico ao descrito nos itens 4.3.1.1 e 4.3.1.2,
será criado contendo os cenários de vazões calculados considerando os
postos de vazões totais artificiais presentes na configuração."
O nome no pacote é `vazoesta.out` (minúsculas).

## Confirmação

Igual ao `VAZOESTA.CSV` a 2 casas em todos os valores, nos dois decks. Como
no `vazoesia.out`, o CSV rotula as usinas com posto artificial com esse
posto (`BARRA BONITA` aparece como posto 37: `368.80` no cenário 1 de
202609). Colunas não nulas: 163 de 172. Tem valores negativos (mínimo
-197.43 em 202609).

## Observações

- Colunas com todos os valores exatos em float32: `STA CECILIA`,
  `NILO PECANHA`, `BELO MONTE`, `PIMENTAL` (os dois decks).

## Não identificado

- Árvores com mais de um período estocástico.
