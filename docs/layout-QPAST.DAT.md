# Layout de `QPAST.DAT` (tendência hidrológica)

Leitor: `pulsar.oraculos.ler_qpast`. Testes: `tests/test_oraculo_tendencia.py`.
Proveniência: F2-QP-01..05. O U19 não documenta este arquivo (03 §2:
"binário, não").

## Layout inferido

| Item | Valor |
| --- | --- |
| Tamanho | 61 440 bytes nos dois decks = 24 × 320 × 8 |
| Acesso | direto, `RECL = NPOS*8` = 2560 bytes, 24 registros |
| Conteúdo de cada registro | `NPOS` float64, coluna = posto - 1 |
| Registros 1-12 | vazão **incremental** de cada posto, um registro por mês do calendário (1 = janeiro) |
| Registros 13-24 | vazão **total** de cada posto, idem |

Os 12 meses são os 12 anteriores ao mês estocástico: no 202609 (estocástico
= outubro/2026) jan-set são de 2026 e out-dez de 2025; setembro é a média
ponderada das semanas (`44.90` no CAMARGOS). No 202610 (estocástico =
novembro) jan-out são de 2026 e nov-dez de 2025.

Evidência do ano (F2-QP-03): as tabelas de tendência do REL só mostram
`JAN … DEZ`. O ano vem do `VAZOES.DAT` do pacote, que vai até 2026: os
totais do `QPAST.DAT` são iguais ao histórico do ano do estudo nos meses
anteriores ao mês inicial e ao do ano anterior nos meses posteriores
(CAMARGOS, outubro: `QPAST` 34, `VAZOES.DAT` 34 em 2025 e 56 em 2024), em
todos os postos da tabela "VAZOES FORNECIDAS" e nos dois decks. O mês
inicial (setembro em 202609, outubro em 202610) é a média semanal e não está
no histórico. O REL confirma o início da janela: "MES INICIAL DA TENDENCIA
HIDROLOGICA 10" (202609) e "11" (202610), o mês estocástico.

## Evidência no texto público

`GEVAZP.REL` do 202609 (pág. 4):

```text
      VAZOES FORNECIDAS PARA A TENDENCIA HIDROLOGICA
  COD USINA           JAN       FEV  ...     SET       OUT       NOV       DEZ
    1 CAMARGOS        117.00    148.00 ...   44.90     34.00     46.00     69.00
    6 FURNAS          908.00   1522.00 ...  269.60    186.00    376.00    552.00

      VAZOES INCREMENTAIS PARA A TENDENCIA HIDROLOGICA PARA POSTOS PRINCIPAIS
    6 FURNAS          659.00   1152.00 ...  178.03    116.00    266.00    390.00
```

`QPAST.DAT`: registro 1 (janeiro, incremental), coluna 5 (posto 6) =
`659.0`; registro 13 (janeiro, total), coluna 5 = `908.0`; registro 9,
coluna 5 = `178.0333...`.

Teste: todos os postos das duas tabelas (164 em cada deck) batem a 2 casas
nos 12 meses, nas duas grandezas. A coluna `COD` das tabelas é o posto.

## Semântica fora dos postos principais

Há 223 colunas não nulas e as tabelas do REL cobrem 164 postos. Nas colunas
que não estão em "POSTOS PRINCIPAIS" (postos usados pelas regras,
postos artificiais e usinas PN, por exemplo o posto 37 e o 172 de ITAPARICA)
o registro incremental repete o total (`test_qpast_fora_dos_principais_incremental_repete_total`).
Para essas colunas o `QPAST.DAT` não é a incremental com artificiais que
vai para o `VAZOES.RVx` (ver `layout-VAZOES.RVx.md`, registros observados).

## Uso como oráculo (T6)

Use os registros 1-12 nos postos principais para testar a tendência
hidrológica, e os registros 13-24 para os totais (incluindo os postos das
regras). Os valores não arredondados aparecem só no mês da média semanal
(por exemplo `178.03333333333333`), o que testa o calendário (lacuna L5).

## Reconstrução (frente F5, T6)

`pulsar.tendencia.tendencia` reproduz os 61 440 bytes nos dois decks
(`tests/test_t6_tendencia.py`). As 223 colunas não nulas são todos os postos
com valor no `VAZOES.DAT` nos meses passados (inclusive postos sem usina) e
os postos `NPOSNW` calculados pelas regras. Regras:

- totais dos 11 meses passados = `VAZOES.DAT`; mês inicial = média do PREVS
  ponderada pelos dias (zero nos postos sem PREVS) (P-TEND-01..04);
- postos `NPOSNW` pela regra do mês, com `VAZ(n)` lido em precisão simples e
  o resultado em dupla; os outros postos com regra ficam com o valor
  fornecido (P-ART-01, P-ART-02);
- incremental = total - totais a montante, incluídas as NW; PN e demais
  colunas repetem o total (P-TEND-05).

## Não identificado

- Comportamento quando a tendência hidrológica não é adotada.
- Usina NW com usinas a montante (lacuna L18).
