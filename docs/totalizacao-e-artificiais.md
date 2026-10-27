# Totalização, postos laterais e postos artificiais (frente F6, T8)

Código: `pulsar.totalizacao`. Testes: `tests/test_t8_totalizacao.py`.
Proveniência: F6-TOT-*, F6-INC-*, F6-DEF-*, F6-ART-*, F6-GRV-01. Lacunas:
L9 (fechada), L20 e L21 (abertas).

## Cadeia (M18 Figura 4.4, passos 2 a 6)

Matrizes `[cenário, usina]`, usinas na ordem da configuração completa (base
+ postos laterais), a mesma das colunas dos arquivos em árvore.

| Passo | Função | Resultado | Arquivo |
| --- | --- | --- | --- |
| 2–3 | `totalizar` | totais: incremental + Σ totais de montante; PN com incremental nula; posto lateral = lateral; SOBRADINHO pela eq. 4.21 | `VAZTOTGD.DAT` |
| 4 | `incrementais_de_totais(nw="absorve")` | total − T(m1) − T(m2) − …; NW nula e não subtraída | `GEVAZP.OUT` |
| 5 | `totais_artificiais` | usinas com posto artificial recebem a regra; as demais repetem o total | `vazoesta.out` |
| 6 | `incrementais_de_totais(nw="propria")` | idem ao passo 4 sobre os artificiais, NW como usina comum | `vazoesia.out` |

`calcular_series` encadeia tudo; `series_dos_totais` parte do passo 4;
`gravar_series` grava os quatro arquivos.

## O que o GEVAZP.OUT é

O `GEVAZP.OUT` não guarda a incremental que entrou na totalização, e sim a
recalculada dos totais (F6-INC-01). Evidência: a partir do `VAZTOTGD.DAT`, a
subtração sequencial `total − T(m1) − T(m2) − …` com os montantes na ordem
da configuração reproduz o arquivo inteiro byte a byte nos dois pacotes, e
as outras ordens não. Consequências:

- `TRAICAO` (PN, incremental nula na cascata) tem no `GEVAZP.OUT` só o
  resíduo de arredondamento de `(T109 + T117) − T109 − T117`;
- a incremental de entrada não é pública (lacuna L20), e por isso a
  totalização a partir do `GEVAZP.OUT` só pode fechar após o arredondamento
  final. Fecha em 100% dos valores após NINT e após 2 casas, e em ~99% bit
  a bit (tabela abaixo).

## Defasagem linear (SOBRADINHO)

`SOBRADINHO` tem `VINCR 169 168 169` (lateral 168, total 169), defasagem 2
(usa) e montantes `TRES MARIAS` e `QUEIMADO` com tempo de viagem de 360 h.
Nos dois pacotes, `total(169) − lateral(168)` é exatamente afim em
`T(156) + T(162)` (resíduo de mínimos quadrados abaixo de 1e-20·Σy², conferido no teste):

| Pacote | Inclinação | β = 1 − incl. | ndmes | Intercepto/β | Janela do PREVS (156 + 158) |
| --- | --- | --- | --- | --- | --- |
| 202609 RV1 | 0,48276 | 15/29 | 31 (out) − 2 | 189,667 | (7·195 + 7·184 + 1·192)/15 |
| 202610 RV0 | 0,37500 | 15/24 | 30 (nov) − 6 | 274,133 | (7·271 + 7·285 + 1·220)/15 = 4112/15 |

Isto é a eq. 4.21 do M18 com `ndias = 360/24`, `ndmes` = dias do estágio
mensal (mês sem os dias excluídos) e `ZT_mont(t−1)` = média dos totais
semanais do PREVS nos 15 dias anteriores ao estágio. A forma bit a bit não
foi achada: a implementada fica a menos de 2 ulp em todos os cenários, igual
em 223/259 e 202/228, empatada no topo com a variante `nd·P/ndmes`
(`ferramentas/enumerar_defasagem.py` enumera 1 348 formas, inclusive a
incremental pela defasagem seguida da cascata e a precisão estendida;
nenhuma fecha tudo). `ndias` não inteiro e janela maior que as semanas do
PREVS são erro explícito (F6-DEF-04); o ndmes pode ser fornecido em
`dados_defasagem(..., dias_estagio=)` (F6-DEF-06).

## Regras dos postos artificiais (lacuna L9)

O avaliador sintático é o da F1 (`pulsar.entradas.regras`). A precisão
(F6-ART-03): cada `VAZ(n)` (natural ou artificial) é lido em float32, as
constantes e as operações são em float64, e o valor gravado é o resultado
float64. Assim as 26 colunas com posto artificial fecham byte a byte; as
variantes vizinhas erram (`test_precisao_das_regras`). Isso explica as
colunas exatas em float32 vistas pela F2: regras que são um `VAZ` sozinho
(`21 = VAZ(123)`), `MIN/MAX` com constante, diferença de dois valores float32.

## Resultados do T8 (`./ambiente/py -m pytest tests/test_t8_totalizacao.py -s`)

A partir do `VAZTOTGD.DAT` oficial: `GEVAZP.OUT`, `vazoesta.out` e
`vazoesia.out` byte a byte nos dois pacotes.

A partir do `GEVAZP.OUT` oficial (ordem `"inversa"`; colunas NW do
`VAZTOTGD.DAT` fora da contagem, F6-TOT-05):

| Arquivo | 202609 bit a bit | 202610 bit a bit | após NINT e 2 casas |
| --- | --- | --- | --- |
| `VAZTOTGD.DAT` | 43 534 / 44 030 | 38 442 / 38 760 | 100% |
| `GEVAZP.OUT` | 44 369 / 44 548 | 39 088 / 39 216 | 100% |
| `vazoesta.out` | 44 100 / 44 548 | 38 934 / 39 216 | 100% |
| `vazoesia.out` | 44 389 / 44 548 | 39 110 / 39 216 | 100% |
| `VAZOES.RVx` (blocos 6 e 8 e arquivo inteiro) | byte a byte | byte a byte | — |

## Não identificado

- Ordem da soma da cascata e incremental de entrada (L20).
- Forma bit a bit da eq. 4.21; janela com `ndias` não inteiro ou maior que
  as semanas do PREVS (hoje erro); montantes com tempos de viagem
  diferentes; fevereiro (L21).
- Variantes por ano do bloco 2 do REGRAS.DAT diferentes de 0 e postos
  repetidos ou números de regra que também são postos naturais (L16;
  opções `posto_repetido` e `numero_repetido`): sem exemplo público.
- Árvores com mais de um estágio estocástico (F2-ARV-03).
