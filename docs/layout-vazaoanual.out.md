# Layout de `vazaoanual.out` (componente anual)

Leitor: `pulsar.oraculos.ler_media_anual_anterior`. Testes:
`tests/test_oraculo_tendencia.py`. Proveniência: F2-VA-01..03. O U19 não
documenta este arquivo.

## Layout inferido

Mesmo formato dos arquivos de séries em árvore (`layout-GEVAZP.OUT.md`):
acesso direto, `RECL = NPOS*8`, um registro de `NPOS` float64 por cenário do
mês estocástico, coluna `NINT-1`. Tamanhos idênticos aos do `GEVAZP.OUT`
(663 040 = 259 × 2560 em 202609; 583 680 = 228 × 2560 em 202610).

## Conteúdo

Para cada usina não PN, o valor é a média das 12 incrementais anteriores ao
mês estocástico, isto é, `A_{t-1}` do PAR(p)-A (L-PARA eq. 31; R1416 eq.
10), com `t` = mês gerado. O valor é o mesmo em todos os cenários (só há um
mês gerado, então `A_{t-1}` só depende da tendência). Nas usinas PN o valor é 0.

Exemplo (202609, CAMARGOS): a tabela de tendência do `GEVAZP.REL`

```text
    1 CAMARGOS   117.00 148.00 135.00 105.00 64.00 56.00 44.00 36.00 44.90 34.00 46.00 69.00
```

tem média 898.90 / 12 = 74.9083, e o `vazaoanual.out` tem
`74.90833333333333` na coluna 0 de todos os registros.

Teste `test_vazaoanual_e_media_dos_12_meses_da_tendencia`: todas as usinas
principais batem com a média da tabela do REL a 0.005.

## Ordem da soma (para F3 e F5)

`test_vazaoanual_bits_soma_em_ordem_de_calendario`: somar os 12 registros
incrementais do `QPAST.DAT` na ordem janeiro → dezembro (não na ordem
cronológica) e dividir por 12 reproduz **todos os bits** de todas as colunas,
nos dois decks (40 663 e 35 796 valores). Variantes testadas e rejeitadas:
ordem cronológica `/12` (38 332/40 663), cronológica reversa, e multiplicar
por `1/12` (27 713/40 663).

O que os dados discriminam é a indexação por calendário e a divisão por 12.
A ordem da soma **dentro** do calendário não: a soma sequencial jan → dez e a
soma por blocos da `np.sum` reproduzem os mesmos bits nos dois decks. F3 e
F5 não devem tratar a soma sequencial como provada (F2-VA-03).

## Não identificado

- Com mais de um mês estocástico, `A_{t-1}` passaria a depender do cenário;
  não há deck assim para confirmar o layout.
- Não sabemos se este arquivo é usado pelo programa ou só gravado.
