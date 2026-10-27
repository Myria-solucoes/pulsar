# Layout de `correli.out` (estatísticas das séries incrementais)

Leitor: `pulsar.oraculos.ler_correli`. Testes: `tests/test_oraculo_correl.py`
e `tests/test_oraculo_relacoes.py`. Proveniência: F2-CI-01..10, F2-REL-01..02.

O U19 §5.2 só diz que é um dos "arquivos não formatados de acesso direto,
contendo informações sobre o processamento do estudo ... utilizados pela
interface gráfica". Todo o layout abaixo é inferido.

## Registro

`RECL = 120` bytes (15 palavras de 8 bytes), little-endian. 6 856 200 bytes =
57 135 registros nos dois decks (o tamanho não depende da árvore).

Formatos de registro encontrados:

| Formato | Bytes |
| --- | --- |
| E (estatística mensal) | 12 float64 (jan..dez) + 24 bytes nulos |
| A (modelo AR de um mês) | int32 `p` + `p` float64 a partir do byte 5 (desalinhado) |
| C (correlação de um par) | int32 `i`, int32 `j`, 13 float64 (12 meses + anual), 8 bytes nulos |
| N (estatística anual) | 5 float64 |

## Cabeçalho

| Registro | Conteúdo |
| --- | --- |
| 1 | int32 `N` = 155 (séries no índice) |
| 2 .. N+1 | int32 `NINT`, int32 registro inicial do bloco (159, 523, 887, ...: passo `L = 364`) |
| N+2 .. 158 | nulos |

O índice tem as usinas que não são PN e cuja incremental não é nula. Ficam
de fora: 2 ITUTINGA e 43 PARANAPANEMA (incremental nula) e as 15 PN
(76, 77, 86, 97, 98, 106, 107, 115-119, 122, 162, 165).

## Bloco de uma série (L = 364 registros)

Posições relativas ao início do bloco, com `N` = 155 e 11 defasagens:

| Posições | Formato | Conteúdo | Ordem |
| --- | --- | --- | --- |
| 1 | E | média mensal histórica | H |
| 2 | E | desvio mensal histórico (denominador N) | H |
| 3-13 | E | correlograma, defasagens 1..11 | H |
| 14-24 | E | correlograma parcial (FACP), defasagens 1..11 | H |
| 25-36 | A | ordem final e `φ_1..φ_p` de cada mês | H |
| 37-193 | C | correlações espaciais históricas com cada série de H (157 linhas) | H |
| 192 | E | média gerada (só o mês estocástico ≠ 0) | índice |
| 193 | E | desvio gerado | índice |
| 194-204 | E | correlograma gerado, defasagens 1..11 (nulo nestes decks) | índice |
| 205-359 | C | correlações espaciais sintéticas com cada série do índice (155) | índice |
| 360 | N | média, desvio e autocorrelação lag 1 das médias do ano civil; 2 campos não identificados | índice |
| 361-364 | — | nulos | — |

**Tamanho do bloco (F2-CI-10).** `L = 17 + 3·nl + 2·NH` = 17 + 33 + 314 =
364: o bloco é alocado para NH = 157 séries nas seções histórica e
sintética, mas as posições são calculadas com N = 155. Daí os 4 registros
nulos no fim (361-364) e a sobreposição de 192-193. O leitor deduz NH do
tamanho do bloco e confere contra as marcas (i, j).

**Duas ordens.** A parte histórica (1-193) do bloco `q` é da série `H[q]`,
com H = lista das 157 séries com seção "SERIE DE VAZOES INCREMENTAIS" no
`GEVAZP.REL` (o índice mais ITUTINGA e PARANAPANEMA). A parte gerada
(192-360) do bloco `q` é da série `índice[q]`, a que o ponteiro do
cabeçalho aponta. Consequências:

- a partir de ITUTINGA o ponteiro do índice não aponta para a parte
  histórica da série (FUNIL-GRANDE, índice 2, tem a parte histórica no
  bloco 3);
- os blocos 156 e 157 só têm parte histórica (de 171 FOZ R. CLARO e 172
  SOBRADINHO_L), e o arquivo termina no registro 193 do bloco 157;
- as linhas históricas 192-193 de cada bloco (pares com 171 e 172) foram
  sobrescritas pela média e pelo desvio gerados. O leitor devolve NaN
  nesses 310 pares; os valores estão no `GEVAZP.REL`.

## Evidência no texto público (202609, CAMARGOS)

| Registro do bloco 1 | Binário | `GEVAZP.REL` |
| --- | --- | --- |
| 1 | 242.0319, 220.0745, ... | `MEDIA AMOSTRAL 242.03 220.07 ...` |
| 2 | 103.6632, ... | `DESVIO PADRAO AMOSTRAL 103.66 ...` |
| 3 | 0.46782, 0.49802, ... | `CORRELOGRAMA DA SERIE / 1 0.46782 0.49802 ...` |
| 15 | -0.07724, ... | `CORRELOGRAMA PARCIAL DA SERIE / 2 -0.07724 ...` |
| 28 | p = 7; 0.75541 0.34416 0.15053 0.21356 0.10830 -0.02572 0.27566 | `4  7  0.755E+00 0.344E+00 0.151E+00 0.214E+00 0.108E+00 -.257E-01 0.276E+00` |
| 39 | (1, 3); 0.80193 ... 0.83759 0.80351 | `CAMARGOS ->FUNIL-GRANDE 0.80193 ... 0.83759 0.80351` |
| 192 | 56.3444 no mês 10 | `PROCESSO PAR(P)`: `GER ... 56.3`; `QUANTIL.CSV`: `56.3444` |
| 206 | (1, 3); 0.51466 no mês 10 | `SINTETICA ... CAMARGOS ->FUNIL-GRANDE ... 0.51466` |
| 360 | 127.1241, 37.0977, 0.35887, 19884.12, 1527040.58 | médias anuais do histórico impresso: 127.124, 37.098 (denominador N), r1 = 0.35887 |

Testes: médias e desvios (2 casas), FAC e FACP (5 casas), ordens (iguais),
coeficientes (3 algarismos), correlações históricas e sintéticas (5 casas)
de todas as séries e pares, nos dois decks.

## Relações úteis (F2-REL)

- Média gerada = `Σ p_s x_s` e desvio gerado = `sqrt(Σ p_s x_s² - μ²)`, com
  `p` = `PROBVAZ.DAT` em float32 e `x` = coluna do `GEVAZP.OUT`; bate a
  1e-10 e 1e-8 (relativo) nas séries não afetadas por NW nem por posto
  lateral.
- As séries NW (68, 145) têm estatística gerada própria, mas coluna nula no
  `GEVAZP.OUT`; a média gerada da NW mais a da jusante é a média ponderada
  da coluna da jusante no `GEVAZP.OUT`.
- O registro anual não usa o primeiro ano de forma especial: média, desvio
  e r1 calculados com todos os anos do histórico.

## Não identificado

- Campos 4 e 5 do registro anual (por exemplo 19884.12 e 1527040.58 para
  CAMARGOS; no `correlt.out` a mesma série tem 1216.69 e 6199.61). Não são
  momentos do histórico nem do gerado; talvez venham dos testes de sequência
  negativa.
- Registros 361-364: sempre nulos (sobra de alocação para 157 séries).
- Correlograma gerado: nulo nos dois decks (só um mês gerado); o formato E
  é suposto.
- Coeficiente `ψ` do PAR(p)-A ("COEFICIENTES DA PARTE A12" no REL) e as
  estatísticas da série `A` não aparecem neste arquivo.
- Como o número de defasagens (11) e a ordem máxima do `DADGER` interagem.
