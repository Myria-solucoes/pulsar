# Layout de `VAZOES.RVx` (árvore de vazões do DECOMP)

Leitor: `pulsar.oraculos.ler_vazoes_decomp`. Testes:
`tests/test_oraculo_vazoes_decomp.py`. Proveniência: F2-VZ-01..12.
Fecha a lacuna L10 nos três arquivos disponíveis (202609 RV0 e RV1, 202610 RV0).

## O que o U19 diz (§5.3.4)

Arquivo de acesso direto em quatro partes: (1) informações gerais; (2)
semanais previstas e cenários mensais gerados; (3) o mesmo considerando
postos artificiais; (4) observadas mensais e semanais. Registros 1 a 10 com
os campos listados em 02-especificacao-publica.md §12; `NREG` = nós da
árvore / número de postos, arredondado para cima; espelho em texto no
`VAZDCP.REL`. Tipos, ordem dos campos dentro de cada registro e
arredondamento não estão escritos.

## Layout confirmado

`RECL = NPOS*4` = 1280 bytes; little-endian; sem marcadores.

| Registros | Tipo | Conteúdo |
| --- | --- | --- |
| 1 | int32 | `nº de usinas`, `NEST`, `aberturas[1..NEST]`, `NPOS`, `nº de usinas NW`, zeros |
| 2 | int32 | códigos das usinas (`nº de usinas + nº NW` valores; as NW no fim) |
| 3 | int32 | semanas previstas, dias excluídos, mês inicial, ano inicial, nº de postos, semanas observadas, código da versão (`110002`, impresso "11.0.2"); bytes 29-40 = `26 31 30 5f 2e 2e 44 24 5f 48 00 00` (não identificados) |
| 4 .. 3+NREGP | float32 | probabilidades dos `NNOS` nós, `NREGP = ceil(NNOS/NPOS)` |
| bloco 5 | int32 por posto | incrementais semanais previstas, `NEST-1` registros |
| bloco 6 | int32 por posto | incrementais mensais geradas, um registro por cenário |
| bloco 7 | int32 por coluna ENA | semanais previstas considerando artificiais, `NEST-1` registros |
| bloco 8 | int32 por coluna ENA | mensais geradas considerando artificiais, um por cenário |
| bloco 9 | int32 por coluna ENA | incrementais mensais observadas: 11 registros, dos 11 meses anteriores ao mês inicial, em ordem cronológica |
| bloco 10 | int32 por coluna ENA | incrementais semanais observadas, uma por semana observada |

`NNOS = Σ_k Π_{l≤k} aberturas[l]`; com aberturas `1 1 1 1 259` são 263 nós.
"Coluna ENA" = posto artificial (`PART` na configuração do `GEVAZP.REL`) se
a usina tiver um, senão o posto.

Contagem de registros nos três arquivos:

| Arquivo | NEST | aberturas | prev. sem. | gerados | obs. mês | obs. sem. | total | tamanho |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 202609 VAZOES.RV0 | 6 | 1 1 1 1 1 259 | 5 | 259 | 11 | 0 | 543 | 695 040 |
| 202609 VAZOES.RV1 | 5 | 1 1 1 1 259 | 4 | 259 | 11 | 1 | 542 | 693 760 |
| 202610 VAZOES.RV0 | 7 | 1 1 1 1 1 1 228 | 6 | 228 | 11 | 0 | 483 | 618 240 |

**Divergências com o U19 §5.3.4.** O manual lista no registro 1 só o total
de postos, o nº de estágios e as aberturas; o arquivo traz também `NPOS` e o
nº de usinas NW. O registro 2 inclui os códigos das usinas NW, que o manual
não menciona. Vale o arquivo (F2-VZ-02, F2-VZ-03).

**Versão.** Só há uma amostra: o código `110002`, que o `VAZDCP.REL` imprime
como "11.0.2" (F2-VZ-04a). A fórmula `maior*10000 + menor*100 + revisão`
usada para gerar o texto é ESCOLHA (F2-VZ-04b), trocável pelo parâmetro
`decodificar_versao`; outras codificações também dão "11.0.2" para 110002.

**Árvores aceitas.** O leitor só aceita aberturas `1 … 1 S` (uma abertura em
cada estágio semanal, um estágio estocástico no fim) e levanta erro nas
demais (F2-VZ-09).

## Evidência

Espelho `VAZDCP.REL` (202609, execução da RV1):

```text
REGISTRO No.:    1
NUM USINAS:   169 NUM ESTAGIOS :     5 ABERTURAS:     1    1    1    1  259    0 ... NPOS:   320 NUM USINAS NW:    2
REGISTRO No.:    3
NSEM PREV:     4 NDIAS :     2 PERIODO INICIAL:  SET/2026 PERIODO FINAL:  OUT/2026 NPOSTOS:   320 NSEM OBS:     1 VERSAO GEVAZP:  11.0.2
REGISTRO No.:    4
  PROBABILIDADE DOS NOS
1.000000 1.000000 1.000000 1.000000 0.003640 0.003680 ...
REGISTRO No.:    5
  VAZAO PREVISTA INCREMENTAL SEMANA            2
      45        0        0        0        0      170       42 ...
```

Binário: registro 1 = `[169, 5, 1, 1, 1, 1, 259, 320, 2, 0, ...]`; registro 5
começa com `[45, 0, 0, 0, 0, 170, 42, ...]`. A coluna é o posto: FUNIL-GRANDE
(código 4, posto 211) tem `46` na coluna 211 e `0` na coluna 4.

`test_todos_os_registros_iguais_ao_vazdcp`: todos os 542 (202609) e 483
(202610) registros batem com o `VAZDCP.REL`, inteiros exatos e
probabilidades a 6 casas.

## Relação com os outros arquivos

- Bloco 6 = `NINT(GEVAZP.OUT)` na coluna do posto; bloco 8 =
  `NINT(vazoesia.out)` na coluna ENA (tudo igual nos dois decks). O posto
  lateral `SOBRADINHO_L` (posto 168) aparece nos blocos 6 e 8 embora não
  esteja na lista de códigos do registro 2.
- Blocos 5, 7 e 10 = colunas "PREVISOES INCREMENTAIS" e "... PARA ENA" da
  primeira página do `GEVAZP.REL` (semanas observadas primeiro).
- Bloco 9 está na convenção ENA: usinas com posto artificial têm a coluna do
  próprio posto zerada e as usinas a jusante de artificiais diferem da
  incremental natural do `QPAST.DAT` (por exemplo SLT.SANTIAGO, 70 contra
  244 em out/2025). Nas usinas sem artificial a montante, bloco 9 =
  `NINT(QPAST incremental)`.
- Registro 4: `1.0` para cada estágio semanal, seguido das folhas, iguais em
  bits ao `PROBVAZ.DAT`.

## Arredondamento

`NINT` (inteiro mais próximo). Nenhum valor de `GEVAZP.OUT` ou
`vazoesia.out` tem fração exatamente `.5`. O `QPAST.DAT` tem 23 (202609) e
10 (202610) valores assim, mas todos no posto artificial 75, onde o
`QPAST.DAT` guarda o total e o `VAZOES.RVx` grava a incremental com
artificiais. A regra de empate não é determinável por estes dados.

## Reconstrução dos registros determinísticos (frente F5, T7)

`pulsar.vazoes_deterministicos.montar_registros` monta, sem ler o
`VAZOES.RVx`, os registros 1–3, o prefixo de probabilidades semanais e os
blocos 5, 7, 9 e 10; todos iguais byte a byte em 202609 RV0, 202609 RV1 e
202610 RV0 (`tests/test_t7_vazoes_deterministicos.py`). Os registros 1–3
também batem em 503 `vazoes.rvN` de 2017–2026 da coleção de decks do ONS
(`tests/test_t7_colecao_ons.py`). O que foi descoberto:

- registro 1: as versões 6.0.0, 7.0.0 e 8.0.0 não gravam NPOS nem o nº de
  NW; de 8.1.6 em diante, sim (P-VZD-08);
- bytes 29–40 do registro 3: a mesma constante em todos os arquivos de 2017
  a 2026 (P-VZD-05); o significado continua desconhecido;
- totais arredondados antes das incrementais; regras com `VAZ(n)` em
  precisão simples; regra do mês inicial em todas as semanas (P-ART-01..05);
- incremental natural sem as NW a montante; ENA com as NW; posto lateral com
  o próprio total; coluna 300 nula (P-INC-01..06);
- bloco 9: 11 meses nos 503 arquivos de 2017 a 2026; a ordem máxima é 11 em
  todos os DADGER do período, então não se sabe se o número é fixo
  (lacuna L17, P-TEND-07).

## Não identificado

- Significado dos bytes 29-40 do registro 3 (constante em 2017–2026).
- Árvores com mais de um estágio estocástico ou com mais de uma abertura
  num estágio semanal: não observadas; o leitor recusa.
- A codificação geral da versão: os 503 arquivos da coleção do ONS têm sete códigos, todos compatíveis com a F2-VZ-04b, mas outras fórmulas também caberiam.
- Se o número de meses observados (11) depende da ordem máxima do PAR(p)
  (11 em todos os decks de 2017 a 2026) ou é fixo (lacuna L17).
