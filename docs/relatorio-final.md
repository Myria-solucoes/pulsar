# Relatório final do Pulsar (frente F9)

Data: 27/10/2026. Branch `frente/F9-integracao`, a partir do master com
F1–F8 integradas. Todos os números deste relatório saem de testes em
`tests/` ou de `ferramentas/relatorio_f9.py`, rodados no ambiente
`pulsar-py:dev` (`./ambiente/py`).

## 1. O comando único

```sh
./ambiente/py src/pulsar/cli.py decks/ons-pacote-gevazp/202609 \
    --revisao RV0 --saida saida/VAZOES.RV0 --semente 1
# RV0: 259 cenários do mês 10, semente 1, 28 iterações do K-means, 130 s
# gravados saida/VAZOES.RV0 e saida/PROBVAZ.DAT
```

| Opção | Efeito | Proveniência |
| --- | --- | --- |
| `<deck>` | diretório com `CASO.DAT` | P-DECK-04 |
| `--revisao RVn` | lista do DECOMP `RVn` do diretório (sem ela, `DADGER.RVn`); sem a opção, a lista do `ARQUIVOS.DAT` | P-CLI-01 |
| `--saida` | VAZOES.RVx; o `PROBVAZ.DAT` vai para o mesmo diretório; padrão: o nome do registro 2 da lista do DECOMP (`vazoes.rv0`) em maiúsculas, como nos pacotes (`VAZOES.RV0`) | P-CLI-02 |
| `--semente` | semente dos ruídos (padrão 0) | P-GER-01 |
| `--intermediarios <dir>` | grava também GEVAZP.OUT, VAZTOTGD.DAT, vazoesta.out, vazoesia.out | P-GER-06 |
| `--simetria`, `--desvio-fc`, `--rota-limite`, `--momentos` | variantes das lacunas L6, L7 e L8 | P-CLI-03 |

A cadeia é a de 02 §1: leitura e configuração (F1), histórico e PAR(p)-A
(F3), matriz de carga (F4), tendência e registros determinísticos (F5),
amostra de 50 mil ruídos, K-means e lognormal (F8), totalização e
artificiais (F6), gravação (F7). Uma execução leva ~2–3 min, quase todos no
K-means (50 000 × 155, K = 228 a 259). A execução real da CLI no 202610
(semente 1) grava o mesmo arquivo, byte a byte, que a cadeia com a
agregação em cache usada nos testes (`test_cli_completa_sem_cache`).

## 2. Resultado por deck

Três `VAZOES.RVx` publicados nos dois pacotes completos: 202609 RV0,
202609 RV1 e 202610 RV0. Só o 202609 RV1 e o 202610 RV0 têm as saídas
intermediárias (GEVAZP.OUT etc.) no pacote; o 202609 RV0 é uma execução
oficial independente, com o mesmo histórico e outro PREVS (5 semanas
previstas, nenhuma observada), coberta pela primeira vez na F9.

### 2.1 Palavras iguais por bloco do VAZOES.RVx

Palavras de 4 bytes, gerado pela cadeia da CLI contra o oficial; nos
blocos estocásticos, mínimo / mediana / máximo nas 20 sementes
(`ferramentas/relatorio_f9.py`, `test_palavras_por_bloco`).

| Bloco | 202609 RV0 | 202609 RV1 | 202610 RV0 |
| --- | --- | --- | --- |
| registro 1 (cabeçalho) | 320/320 | 320/320 | 320/320 |
| registro 2 (códigos) | 320/320 | 320/320 | 320/320 |
| registro 3 (calendário, versão) | 320/320 | 320/320 | 320/320 |
| 4 probabilidades (1 registro) | 63 / 67 / 72 de 320 | 63 / 67 / 72 de 320 | 93 / 98 / 103 de 320 |
| 5 semanas previstas, natural | 1 600/1 600 | 1 280/1 280 | 1 920/1 920 |
| 6 mês gerado, natural | 45 573 / 45 669 / 45 764 de 82 880 | 45 460 / 45 563 / 45 637 de 82 880 | 39 677 / 39 748 / 39 811 de 72 960 |
| 7 semanas previstas, ENA | 1 600/1 600 | 1 280/1 280 | 1 920/1 920 |
| 8 mês gerado, ENA | 45 530 / 45 637 / 45 736 de 82 880 | 45 298 / 45 429 / 45 493 de 82 880 | 39 596 / 39 656 / 39 750 de 72 960 |
| 9 meses observados (11) | 3 520/3 520 | 3 520/3 520 | 3 520/3 520 |
| 10 semanas observadas | — (0) | 320/320 | — (0) |
| **arquivo** (medianas) | 99 053 / 173 760 (57,0%) | 98 420 / 173 440 (56,7%) | 87 822 / 154 560 (56,8%) |

Leitura: **todos os registros determinísticos são iguais byte a byte nas
três revisões** (cabeçalho, códigos, calendário, as semanas previstas
natural e ENA, os 11 meses observados e as semanas observadas). Nos blocos
gerados, as palavras iguais vêm quase todas das colunas sem dispersão
(postos sem usina, PN, NW absorvidas e incrementais nulas), que são iguais
em 100%; nas 153 colunas com dispersão do bloco 6 só 6,3% (RV0), 6,0% (RV1)
e 4,8% (202610) das palavras coincidem na semente 1, por acaso. No registro
de probabilidades, as iguais são as dos estágios semanais (1,0), os zeros
de preenchimento e as folhas que caem na mesma contagem.

### 2.2 Transplante entre revisões (202609 RV1 → RV0)

As 259 probabilidades das folhas do VAZOES.RV0 e do VAZOES.RV1 oficiais do
202609 são **iguais bit a bit**, e os cenários das duas revisões têm
correlação mediana 0,9994 por posto: nesse único par publicado, a
agregação oficial não depende da revisão (P-INT-01), como no Pulsar; a
generalização a outros pares fica na lacuna L6. Isso permite isolar a
parte determinística da geração (03 §3): o ruído W oficial do RV1,
reconstruído do GEVAZP.OUT pela inversa da lognormal e da recorrência do
Pulsar, foi reaplicado com o condicionamento do RV0 (tendência do
PREVS.RV0), totalizado, com os artificiais, e gravado (P-INT-02,
`test_transplante_entre_revisoes`):

| Bloco do VAZOES.RV0 | Palavras iguais |
| --- | --- |
| registros 1–3, probabilidades, blocos 5, 7, 9 | 100% |
| 6 (natural gerado) | 78 922 / 82 880 (95,2%); 90,0% nas 153 colunas com dispersão |
| 8 (ENA gerado) | 78 836 / 82 880 (95,1%); 89,9% nas 154 colunas com dispersão |

O teste afirma ≥ 89% nas colunas com dispersão dos dois blocos. As palavras
diferentes diferem de ±1 em 85% dos casos, no máximo 18 m³/s (pior coluna:
JIRAU, posto 285, 11% de palavras iguais); a diferença média é −0,002 m³/s
(sem viés). A fração de palavras diferentes cresce com |W|, de 6,3%
(|W| < 0,5) a 21,9% (|W| ≥ 2), também afirmado no teste. A leitura disso
como erro de escala na 4ª–5ª casa dos parâmetros da lognormal, compatível
com o TCOND.REL (P-LN3-04: "DESPAD TEO" igual na 4ª casa em 97% das
séries), é interpretação, não testada diretamente. O controle
RV1 → RV1 devolve o NINT do GEVAZP.OUT em 100% dos valores. É a evidência
mais forte de que o condicionamento (P-GER-03/04), M_t = 0 (P-LN3-03) e os
momentos teóricos (P-LN3-04) são os do modelo oficial, obtida numa execução
oficial que não serviu para inferir nenhuma regra.

### 2.3 Degraus T0–T12

Resultado de `./ambiente/py -m pytest tests` (suíte inteira, com a coleção
de decks do ONS montada e o cache de `cache/f8/` preenchido por
`ferramentas/sementes_f8.py`, simetrias "nenhuma" e "antitetica"):

**418 passaram, 2 pulados, 0 falharam, 1 501 subtestes passaram** (17 min, depois da rodada 1 da auditoria). Os dois pulados são amostras legíveis escritas só para o 202609 (`test_oraculo_correl.py:174`, `test_oraculo_tendencia.py:40`). T0 e T1 são `unittest` com subtestes por deck (os dois pacotes e a coleção de decks do ONS), por isso aparecem na coluna "sem deck". Os testes "sem deck" usam casos sintéticos.

| Degrau | Teste | 202609 | 202610 | Sem deck / ambos | Critério e resultado |
| --- | --- | --- | --- | --- | --- |
| F2 | test_oraculo_* | 38 ✓, 2 pulados | 36 ✓ | — | leitores dos binários iguais aos espelhos em texto |
| T0 | test_t0_leitura | — | — | 15 ✓ | todas as entradas dos pacotes e dos 734 casos da coleção do ONS lidas; contagens iguais ao GEVAZP.REL |
| T1 | test_t1_configuracao, test_t1_ac_datado | — | — | 18 ✓ | `config.out` byte a byte; ordem do registro 2 igual em 503 VAZOES da coleção do ONS |
| T2 | test_t2_historico | 5 ✓ | 5 ✓ | — | incrementais, janela, média e desvio bit a bit |
| T3 | test_t3_* | 11 ✓ | 11 ✓ | — | correlograma e FACP bit a bit (20 460 valores) |
| T4 | test_t4_* | 16 ✓ | 16 ✓ | 18 ✓ | ordens iguais em todas as iterações do vordem.out; φ bit a bit |
| T5 | test_t5_* | 13 ✓ | 13 ✓ | 11 ✓ | matriz espacial bit a bit; carga D·D' = U |
| T6 | test_t6_tendencia | 6 ✓ | 6 ✓ | 4 ✓ | QPAST.DAT byte a byte |
| T7 | test_t7_* | 17 ✓ | 9 ✓ | 8 ✓ | blocos determinísticos byte a byte nas 3 revisões |
| T8 | test_t8_totalizacao | 11 ✓ | 11 ✓ | 7 ✓ | do VAZTOTGD: GEVAZP.OUT, vazoesta/ia byte a byte; do GEVAZP.OUT: iguais após NINT |
| T9 | test_t9_empacotamento | 4 ✓ | 3 ✓ | 13 ✓ | VAZOES.RVx e PROBVAZ.DAT byte a byte por transplante |
| T10 | test_t10_* | 4 ✓ | 4 ✓ | 14 ✓ | K e N = 50 000; tamanhos de grupo na faixa das sementes |
| T11 | test_t11_* | 21 ✓ | 21 ✓ | 12 ✓ | aceitação estatística sobre o GEVAZP.OUT (seção 2.4) |
| T12 | test_t12_ponta_a_ponta | 4 ✓ (2 revisões) | 2 ✓ | 8 ✓ | determinísticos byte a byte, transplante RV1→RV0, 03 §5 no VAZOES.RVx, CLI real = cadeia em cache |
| — | test_proveniencia | — | — | 3 ✓ | seção 7 |

### 2.4 Estatísticas de 03 §5

**Sobre o GEVAZP.OUT** (T11, F8, `tests/test_t11_aceitacao.py`): fração
das 153 colunas (e dos pares, na correlação) em que a estatística oficial
cai na faixa [mín, máx] das 20 sementes (P-ACE-06; um gerador idêntico ao
oficial dá 0,90):

| Deck | média | desvio | assim. | Q1 | Q2 | Q3 | correl. | árvore |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 202609 RV1 | 0,922 | 0,909 | 0,857 | 0,890 | 0,870 | 0,909 | 0,908 | 1,000 |
| 202610 RV0 | 0,909 | 0,851 | 0,805 | 0,883 | 0,890 | 0,792 | 0,893 | 1,000 |

**Sobre o VAZOES.RVx** (T12, F9, P-INT-03; bloco 6 inteiro com as
probabilidades do registro 4), nas três revisões, faixa [mín, máx] e, entre
parênteses, a referência de um gerador idêntico (cada semente contra as
outras 19). Os limiares do teste são os do T11 (≥ 0,87 em média, Q2,
correlação e árvore; mínimo 0,78; média das frações ≥ 0,87); a referência
nos quartis passa de 0,90 porque os valores do VAZOES.RVx são inteiros e os
empates alargam a faixa:

| Revisão | média | desvio | assim. | Q1 | Q2 | Q3 | correl. | árvore |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 202609 RV0 | 0,908 (0,90) | 0,908 (0,90) | 0,856 (0,90) | 0,928 (0,96) | 0,935 (0,96) | 0,961 (0,95) | 0,909 (0,90) | 1,000 |
| 202609 RV1 | 0,941 (0,90) | 0,889 (0,90) | 0,843 (0,90) | 0,948 (0,96) | 0,941 (0,96) | 0,967 (0,95) | 0,912 (0,90) | 1,000 |
| 202610 RV0 | 0,908 (0,90) | 0,856 (0,90) | 0,804 (0,90) | 0,935 (0,95) | 0,948 (0,95) | 0,869 (0,94) | 0,894 (0,90) | 1,000 |

Com a faixa P5–P95 (o exemplo de 03 §5) as frações oficiais ficam em
0,70–0,91 e as da referência em 0,81–0,92: o critério de 90% não é
atingível com 20 sementes por essa faixa nem por um gerador idêntico
(P-ACE-06). No bloco 8 (ENA) os números são os do bloco 6 a ±0,015.

**Testes do M18 cap. 6** (P-ACE-05, `test_vereditos_do_m18_cap6`): a
fração de séries rejeitadas a 5% é < 6% no oficial e em todas as sementes,
nos quatro testes (t da média, desvio, KS, Cramér–von Mises): o veredito é
o mesmo.

## 3. O que ficou igual byte a byte

Nos dois pacotes (e, onde se aplica, nas três revisões):

- `config.out` (T1);
- histórico incremental, médias, desvios, correlogramas, FACP, ordens e
  coeficientes φ/ψ do PAR(p)-A contra o `correli.out` e o `vordem.out`,
  bit a bit em float64 (T2–T4; amostra única, ver "Alcance das evidências
  da F3" no PROVENIENCIA.md);
- matriz de correlação espacial histórica, 316 407 valores float64 (T5);
- `QPAST.DAT` (T6) e `vazaoanual.out`;
- registros 1–3 e blocos determinísticos do VAZOES.RVx: semanas previstas
  natural e ENA, 11 meses observados e semanas observadas, nas três
  revisões (T7, T12), inclusive no 202609 RV0, que não tem saídas
  intermediárias no pacote;
- a partir do `VAZTOTGD.DAT` oficial: `GEVAZP.OUT`, `vazoesta.out` e
  `vazoesia.out` (T8);
- a partir do `GEVAZP.OUT`, do `vazoesia.out` e do `PROBVAZ.DAT` oficiais:
  o `VAZOES.RVx` inteiro e o `PROBVAZ.DAT` (T8, T9);
- a partir do `GEVAZP.OUT` oficial (totalização refeita): os quatro
  arquivos iguais depois do arredondamento final e o VAZOES.RVx inteiro
  (T8; bit a bit em ~99% dos float64, lacuna L20);
- a partir do W oficial do RV1: 100% dos registros determinísticos e 90%
  das palavras geradas do VAZOES.RV0 (T12, seção 2.2).

## 4. O que é estatisticamente equivalente

A parte estocástica: blocos 6 e 8 do VAZOES.RVx, as probabilidades das
folhas (registro 4 e `PROBVAZ.DAT`) e os arquivos intermediários gerados.
Nenhum arquivo público traz os ruídos, a semente nem os centros iniciais
(L6), então essa parte não pode coincidir byte a byte. O que foi
demonstrado:

- número de grupos (K = aberturas) e denominador 50 000 iguais aos
  oficiais; mínimo, máximo e desvio dos tamanhos de grupo oficiais dentro
  da faixa das 20 sementes (T10);
- média, Q2, correlação espacial e a árvore como um todo dentro da faixa
  das 20 sementes em ≥ 0,87 das colunas nos dois pacotes (T11) e ≥ 0,89 nas
  três revisões pelo VAZOES.RVx (T12), no nível de um gerador idêntico
  (0,90);
- mesmos vereditos nos testes do M18 cap. 6;
- mesma agregação para revisões com as mesmas usinas e o mesmo K (P-INT-01),
  como no oficial.

## 5. O que não é equivalente (ou não foi demonstrado)

- **Forma da distribuição no 202610**: a assimetria oficial fica na faixa
  das sementes em 0,80–0,81 das colunas e o Q3 em 0,79–0,87, abaixo da
  referência de 0,90. No GEVAZP.OUT a assimetria oficial está acima da
  faixa em ~30% dos postos (observação exploratória registrada na L7). No
  202609 (RV0 e RV1) a assimetria fica em 0,84–0,86, também um pouco abaixo.
  Causa provável: forma dos ruídos agregados (fator de compensação, L7, ou
  "ruído simétrico", L6), que nenhum arquivo público separa.
- **Bits da geração**: o transplante entre revisões deixa 10% das palavras
  geradas das colunas com dispersão a ±1–18 m³/s (Jirau é o pior caso, 11%
  de palavras iguais), com erro que cresce com |W|, provavelmente de escala
  na 4ª–5ª casa dos parâmetros da lognormal (interpretação); a forma
  numérica exata da recorrência e dos momentos teóricos continua aberta
  (L23).
- **Totalização a partir da incremental gerada**: a ordem da soma da
  cascata não é pública (L20); a partir do GEVAZP.OUT ~1% dos float64
  diferem em 1 ulp, sem efeito depois do arredondamento.
- **Defasagem de SOBRADINHO**: total a ≤ 2 ulp do oficial, 223/259 e
  202/228 bit a bit (L21), sem efeito no VAZOES.RVx.
- **Custo no DECOMP** (03 §5 item 5): não avaliado; o DECOMP não foi rodado
  com as duas árvores.
- **Casos sem deck público**: ramo PAR(p) puro (decks até 2022), matriz
  anual, árvores com mais de um período estocástico, VSEMPAST, satélites,
  mais de um posto lateral, fevereiro como mês estocástico: implementados
  como escolha parametrizada ou recusados com erro explícito (seção 6).

## 6. ESCOLHAS e impacto

As 93 linhas de PROVENIENCIA.md com ESCOLHA (inteira ou parcial), agrupadas
pelo efeito nos três VAZOES.RVx publicados. "Sem efeito" quer dizer que o
caso não ocorre nos decks públicos ou que as alternativas dão o mesmo
arquivo; todas são parâmetros, salvo onde indicado.

### 6.1 Mudam a parte estocástica (blocos 6 e 8, probabilidades)

| Id | Escolha | Impacto medido |
| --- | --- | --- |
| P-RUI-01, P-RUI-03, P-RUI-05, P-GER-01 | PCG64 por posto, ziggurat, centros sorteados sem reposição, semente 0 | Definem a realização: as palavras das colunas com dispersão coincidem em ~5% (acaso); estatísticas equivalentes (seção 2.4). Não inferível (L6) |
| P-RUI-04 | "Ruído simétrico" = amostra aleatória simples | A antitética derruba a fração da média de 0,922 para 0,825 (202609) e de 0,909 para 0,760 (202610) |
| P-AGR-04, P-AGR-05 | σ_i ponderado; FC escalar | Variantes mudam o FC < 0,3% e as frações ±0,03; sem o fator o T11 falha (< 0,1) |
| P-AGR-06 | K = 1: média da amostra, sem fator | Sem efeito (K = 259 e 228) |
| P-AGR-07, P-LAT-03 | Ruído próprio do lateral no vetor agregado; principal = posto total | Uma coluna (SOBRADINHO_L); inclinação W_L × W_total 0,9965/0,9995 contra ρ anual 0,9985 |
| P-LN3-03, P-LN3-07, P-LN3-08 | M_t = 0; cúbicas e quantis como variantes | As variantes perdem 0,06–0,15 na média das frações e ≥ 0,1 na assimetria e no Q3; M_t = 0 sustentado pelo transplante (2.2) |
| P-LN3-06 | Média condicional negativa: eq. 24 com quadrado | 2 séries do 202610 (TRES IRMAOS, SAO MANOEL); "normal" daria média negativa, contra cenários oficiais todos positivos |
| P-KM-01, P-KM-03, P-KM-04, P-KM-05 | Aritmética BLAS, lotes, ITER = 50, IFAULT | Mesmos grupos e iterações que a aritmética sequencial; convergência em 22–42 iterações; só desempenho (~6×) |
| P-GER-05 | Ordem da soma da recorrência | Ulps; abaixo do erro de ±1 do transplante |
| P-ESP-07, P-ESP-08, P-ESP-06 (guarda) | √max(λ,0); produto do NumPy; matriz não simétrica recusada | D muda ≤ 5e-8 e < 1e-14; a guarda nunca dispara |

### 6.2 Layout que fecha byte a byte com o valor dos pacotes

| Id | Escolha | Impacto |
| --- | --- | --- |
| F7-VZ-03, P-VZD-04, F2-VZ-04b | Versão 11.0.2 e fórmula `maior*10000+menor*100+rev` | Necessária para o registro 3 igual; outra versão muda 1 palavra |
| F7-VZ-04 | Bytes 29–40 do registro 3 copiados dos pacotes | Sem eles, 3 palavras do registro 3 diferem |
| P-VZD-08 | Registro 1 curto antes de 8.1.6 | Sem efeito com a versão emulada |
| F7-VZ-07, P-ART-03 (empate negativo) | NINT com empate para longe do zero | Nenhum valor público com fração ,5 |
| F7-VZ-08, P-INC-06 | Colunas em colisão (posto 300) | As colunas em colisão são nulas; mesmo arquivo nas duas opções |
| P-COUT-03, P-COUT-04, P-CFG-12 | Significado de campos sempre iguais no `config.out` | Só o `config.out` (T1); sem efeito no VAZOES |

### 6.3 Ordem de operações sem efeito no arquivo final

| Id | Escolha | Impacto |
| --- | --- | --- |
| P-EST-03, P-RES-04 | Ordem das somas da assimetria e dos momentos dos resíduos | Ulps; só no relatório, não no modelo |
| F6-TOT-03 | Soma da cascata na ordem da configuração | Igual depois do NINT; ~1% dos float64 a 1 ulp |
| F6-DEF-05, F6-DEF-06 | Forma da defasagem; calendário gregoriano | ≤ 2 ulp no total de SOBRADINHO; nenhum mês estocástico em fevereiro |
| P-REG-04, P-REG-03 | Regras em float64, precedência usual | A leitura em float32 (F6-ART-03, P-ART-02) é que fecha os bits; nenhuma regra pública depende da precedência |

### 6.4 Casos que não ocorrem nos decks públicos (sem efeito nos três arquivos)

| Lacuna | Ids |
| --- | --- |
| L1 (janela de anos) | P-CFG-08 |
| L5 (calendário) | P-TEND-02 |
| L13–L14 (configuração) | P-DADG-05, P-DADG-12, P-DADG-13, P-DECK-02, P-CFG-06, P-CFG-11 |
| L15 (formato de entrada, nomes) | P-TXT-01, P-TXT-02, P-DADG-11, P-DECK-05..07, P-PREVS-02, P-MODIF-02, P-REG-06, P-REG-08, P-ART-06, F7-VZ-11, P-CLI-01 (recaída), P-CLI-02 |
| L16 (semântica das regras) | P-REG-05, P-REG-07, P-ART-07, F6-ART-05..07 |
| L17 (meses observados) | P-TEND-07 (11 nos 503 decks da coleção do ONS) |
| L18 (montagem determinística) | P-TEND-05 e P-INC-04 (NW com montante), P-TEND-08 |
| L19 (ramo PAR(p) e casos degenerados) | P-HIST-03, P-EST-06, P-FACP-02, P-LIN-02, P-PAR-01, P-ORD-01, P-ESP-03, P-ESP-09 (anual) |
| L4 | P-ESP-05 (lateral dentro ou fora da carga; nenhum arquivo separa) |
| L21 | F6-DEF-04 (`NotImplementedError`) |
| L23 | P-GER-02 (`NotImplementedError` para outras árvores) |

### 6.5 Interface e critério de validação

| Id | Escolha | Impacto |
| --- | --- | --- |
| F7-VZ-10, F6-TOT-05 | Interfaces entre frentes e do transplante | Nenhum no arquivo |
| P-CLI-03 | Opções da CLI com os padrões das escolhas | Nenhum |
| P-ACE-02, P-ACE-04..07, P-INT-03 (L24) | Estatísticas ponderadas, faixa [mín, máx], colunas | Definem o veredito: com P5–P95 todas as frações caem ~0,1, também para um gerador idêntico |

## 7. Revisão do PROVENIENCIA.md

Feita linha a linha e automatizada em `tests/test_proveniencia.py`, que
falha se alguma linha:

- não tiver tipo DOC, INFERIDO ou ESCOLHA;
- citar um teste (`test_*`, `Test*`) ou um caminho (`tests/`, `src/`,
  `docs/`, `fontes/`, `ferramentas/`) que não existe (o caminho vale exato
  ou sem a extensão, nunca como prefixo truncado);
- for INFERIDO sem teste (ou sem outra linha cujo tipo tenha INFERIDO);
- citar teste implicitamente ("mesmo teste", "mesmos testes");
- for DOC sem fonte (sigla, arquivo de `fontes/` ou referência
  bibliográfica nominal);
- for ESCOLHA sem lacuna existente em 04-lacunas.md;
- usar uma sigla de fonte fora da nova tabela "Siglas das fontes";
- citar material proibido (00-regras §2).

Correções feitas: tabela de siglas (as siglas `L-PAR`, `L-LN3` etc. eram
usadas desde o 02 sem mapa para os arquivos de `fontes/libs/`); testes
citados explicitamente onde a linha dizia "mesmo teste" (F2-ARV-03,
F2-QP-02, F2-VA-02, F2-VZ-03, F2-VZ-05, F2-VZ-06, P-VZD-02, P-VZD-03,
P-GER-04; as quatro últimas na rodada 1 da auditoria) ou não citava teste (P-BIN-01,
F2-TXT-01); caminho completo do `as136.f` (P-KM-05, P-KM-06); fonte DOC na
P-GER-07; lacuna nas ESCOLHAS que não citavam nenhuma (P-VZD-04, P-KM-05,
P-AGR-06, P-LN3-06, P-LN3-07, P-GER-02, P-GER-05, P-ACE-02, P-ACE-04..07),
com duas lacunas novas (L23 geração além dos decks e sem oráculo de bits;
L24 critério da aceitação). Nenhum material proibido foi encontrado.

## 8. O que fica em aberto

- L6–L8 e L23: a forma da distribuição no 202610 (assimetria e Q3) e o
  resíduo de ±1 do transplante; um pacote completo de outro mês ajudaria a
  separar as variantes de L7.
- L19 e "Alcance das evidências da F3": T2–T5 repousam numa única amostra
  de histórico (1931–2024); faltam pacotes completos antigos (ramo PAR(p)) e
  de outro ano final de histórico.
- L10, L13–L18, L21: casos de layout e de configuração sem deck público.
- 03 §5 item 5: custo no DECOMP não avaliado.
- Desempenho: o K-means (P-KM-03) domina a execução (~2–3 min por deck).
