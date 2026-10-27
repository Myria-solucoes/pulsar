# Layout do `config.out`

Arquivo binário gravado pelo GEVAZP no modo DECOMP. O U19 não descreve o
seu layout (03 §2: "binário, layout não documentado"). Tudo abaixo foi
decodificado dos `config.out` públicos dos pacotes `decks/ons-pacote-gevazp/202609`
(execução RV1) e `202610` (RV0), com as técnicas de 03 §3, e conferido com
o texto do `GEVAZP.REL` do mesmo pacote. Implementação:
`src/pulsar/config_out.py`. Testes: `tests/test_t1_configuracao.py`.

Os dois arquivos públicos são idênticos (55 200 bytes, mesmo conteúdo),
porque as duas configurações coincidem. A evidência vem, portanto, de uma
única configuração; os pontos que ela não distingue estão listados no fim.

## Visão geral

| Item | Valor | Evidência |
| --- | --- | --- |
| Tamanho do registro | 160 bytes | 55 200 = 345 × 160; o padrão nome/ano se repete a cada 0xA0 bytes (`CAMARGOS` em 0xA4, `ITUTINGA` em 0x144). |
| Marcadores de registro | nenhum | Os registros começam exatamente em múltiplos de 160; não há inteiros de comprimento antes/depois (acesso direto, como os demais binários do U19 §5.3). |
| Ordem dos bytes | little-endian | `ab 00 00 00` = 171 no início; anos `8b 07` = 1931, `e8 07` = 2024. |
| Alinhamento | nenhum (campos empacotados) | O status ocupa 2 bytes (36–37) e os inteiros seguintes começam em 38, 42, 46… (não múltiplos de 4). |
| Blocos | 2 | Registro 0 = 171, seguido de 171 usinas; registro 172 = 172, seguido de 172 usinas. |

345 registros = 1 cabeçalho + 171 usinas + 1 cabeçalho + 172 usinas.

## Cabeçalhos

| Bloco | Bytes 0–3 | Bytes 4–7 | Bytes 8–11 | Resto | Evidência |
| --- | --- | --- | --- | --- | --- |
| 1 | nº de usinas da configuração base (171) | 0 | 0 | zeros | 171 = nº de registros `UH` do DADGER; 171 registros seguem. |
| 2 | nº de usinas com os postos laterais (172) | 172 | 1 | zeros | 172 registros seguem; REL: "TOTAL DE USINAS : 172" e "TOTAL DE USINAS COM POSTO DE VAZAO LATERAL : 1". |

O segundo inteiro do cabeçalho 2 (172) é ambíguo: pode ser a repetição do
total ou a soma base + laterais (171 + 1), que coincidem aqui.

## Registro de usina (bytes 0–65; bytes 66–159 sempre zero)

A ordem dos campos é exatamente a dos 14 campos do arquivo de configuração
do U19 §3.4.1. Esse paralelo é a base da interpretação dos campos que são
zero em todos os registros.

| Bytes | Tipo | Campo (U19 §3.4.1) | Origem na reconstrução | Evidência |
| --- | --- | --- | --- | --- |
| 0–3 | int32 | 1. número da usina | registro `UH` | 1, 2, 4, 6… igual à coluna NUM do REL e aos `UH`; no posto lateral, o número do posto lateral (168). |
| 4–15 | A12 | 2. nome | HIDR (bytes 0–11 do registro da usina) | Idêntico ao nome do HIDR, com brancos; lateral `SOBRADINHO_L`. |
| 16–19 | int32 | 3. posto | HIDR, `AC NUMPOS`, `VINCR` | FUNIL-GRANDE 211 (HIDR); HENRY BORDEN 300 (`AC 119 NUMPOS 300`); SOBRADINHO 169 apesar de `AC 169 NUMPOS 168` (o `VINCR 169 168 169` põe o posto total). |
| 20–23 | int32 | 4. usina de jusante | HIDR, `AC NUMJUS`, cadeia até usina presente | I. SOLTEIRA 45 (`AC 34 NUMJUS 45`); MAUA 61 (HIDR 57→58, 58 fora da configuração, 58→61); ITAIPU 0. |
| 24–27 | int32 | 5. região/bacia | REE do registro `UH` | ITAIPU 5 (`UH 66 5`), CAMARGOS 10; REL imprime `BACIA_005`, `BACIA_010`. |
| 28–35 | real*8 (hipótese) | 6. percentual do mínimo histórico | sempre 0 | Zero em todos os registros. O tamanho de 8 bytes é o espaço entre o campo 5 e o status; o tipo não é verificável. |
| 36–37 | A2 | 7. status | `NW` (col. 72 do `UH`), `PN` (`PARTIF`), `PL` (posto lateral), brancos | 96 e 260 `NW`; as 15 usinas `PARTIF` do MODIF.DAT `PN`; SOBRADINHO_L `PL`; demais `"  "`. Igual à coluna STAT do REL. |
| 38–41 | int32 | 8. ajuste automático da ordem | sempre 0 | Zero; REL coluna AJ = 0. |
| 42–45 | int32 | 9. ano inicial do histórico | POSTOS.DAT / GEVAZP.DAT reg. 16 | 1931 em todos; REL I.HIST. |
| 46–49 | int32 | 10. ano final do histórico | POSTOS.DAT / DADGER `& VAZOES` reg. 2 | 2024 em todos; REL F.HIST. |
| 50–53 | int32 | 11. tempo de viagem até a jusante (h) | registro `VI` do DADGER | TRES MARIAS e QUEIMADO 360 (`VI 156 360`, `VI 162 360`); REL coluna TVj. A coluna TVt do REL (RETIRO BAIXO 360) **não** é gravada. |
| 54–57 | int32 | 12. posto de vazão lateral | `VINCR` do MODIF.DAT (campo 3) | SOBRADINHO 168; REL coluna PL. |
| 58–61 | int32 | 13. defasagem linear | DADGER `& VAZOES` reg. 12 | 2 em todos (`USA PROPAGACAO LINEAR => 2`); REL coluna DEFL. |
| 62–65 | int32 | 14. posto artificial | `AC NPOSNW` | BARRA BONITA 37, SEGREDO 75, PIMENTAL 302 (bytes 62–63 = 0x012E); SOBRADINHO 0 apesar de `AC 169 NPOSNW 169`. REL coluna PART. |
| 66–159 | — | — | zeros | Zero em todos os 343 registros de usina. A coluna FATOR do REL (0.00) não aparece em nenhum byte não nulo. |

## Blocos 1 e 2

- O bloco 2 repete byte a byte os 171 registros do bloco 1, na mesma ordem,
  e acrescenta um registro por posto lateral no fim (`SOBRADINHO_L`).
- Ordem das usinas: crescente pelo número, porque o DADGER traz
  `ORDENACAO AUTOMATICA => 0001` (U19 §4.5 reg. 14). As usinas `NW` ficam
  na posição do seu número (96 entre 95 e 97). No `VAZOES.RVx` elas vão
  para o fim do registro 2 (ver `Configuracao.ordem_vazoes_rv`).
- Registro do posto lateral: número = posto = posto lateral (168), jusante
  0, bacia = REE da usina de origem (3), status `PL`, anos do POSTOS.DAT
  para o posto lateral, tempo de viagem 0, posto lateral 0, defasagem igual
  à da configuração, posto artificial 0. Nome = nome da usina sem brancos à
  direita + `_L`.

## O que os dados públicos disponíveis não distinguem

| Ponto | Alternativas | Escolha atual (parâmetro) | Lacuna |
| --- | --- | --- | --- |
| 2º inteiro do cabeçalho 2 | repetição do total; outra contagem igual a 172 | total (`gerar_config_out(cabecalho2=...)`, P-COUT-03) | L13 |
| Tipo dos bytes 28–35 | real*8; dois inteiros; real*4 + preenchimento | real*8 com 0.0 (`gerar_config_out(percentual=...)`, P-COUT-04) | L13 |
| Nome do lateral com nome de 11–12 letras | cortar o `_L`; cortar o nome | `(nome + "_L")[:12]` (`OpcoesConfiguracao.nome_lateral`, P-CFG-12) | L13 |
| Anos por usina | POSTOS.DAT do posto; GEVAZP.DAT reg. 16 e ano final do DADGER; interseção | interseção (`OpcoesConfiguracao.anos`, P-CFG-08) | L1 |
| Usina `NW` que também é `PARTIF` | `NW`; `PN` | `NW` (`OpcoesConfiguracao.prioridade_status`, P-CFG-06) | L14 |
| Mais de um posto lateral | ordem das usinas de origem; ordem do posto lateral | origem (`OpcoesConfiguracao.ordem_laterais`, P-CFG-11) | L14 |

Para fechar esses pontos é preciso um pacote completo com outra
configuração (por exemplo, sem ordenação automática, com dois `VINCR` ou com
histórico de anos diferentes por posto).
