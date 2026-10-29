# Relatório final do Pulsar

Versão inicial: frente F9 (27/10/2026, branch `frente/F9-integracao`, com
F1–F8 integradas). Atualizado pela frente F11 (28/10/2026, branch
`frente/F11-limite-inferior`, a partir do master com a F10): seções 2.1,
2.2, 2.3, 2.4, 3 (transplante), 4, 5, 6.1 e 8, com a lognormal identificada
(docs/limite-inferior.md). Atualizado pela frente F13 (29/10/2026, branch
`frente/F13-rel23954`): fonte nova R23954 (Rel. CEPEL 23954/2016, tempo de
viagem) e o lateral fora do vetor agregado (P-AGR-07, P-LAT-04), que muda a
parte estocástica: seções 1, 2.1, 2.3, 2.4, 5, 6.1 e 8. As seções 6.2–6.5 e 7 são as da F9. Todos os números saem de testes em `tests/` ou de
`ferramentas/`, rodados no ambiente `pulsar-py:dev` (`./ambiente/py`).

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
K-means (50 000 × 154, K = 228 a 259; 155 até a F11, com o lateral no vetor). A execução real da CLI no 202610
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
| 4 probabilidades (1 registro) | 64 / 67 / 72 de 320 | 64 / 67 / 72 de 320 | 93 / 98 / 101 de 320 |
| 5 semanas previstas, natural | 1 600/1 600 | 1 280/1 280 | 1 920/1 920 |
| 6 mês gerado, natural | 45 590 / 45 691 / 45 775 de 82 880 | 45 497 / 45 579 / 45 714 de 82 880 | 39 702 / 39 772 / 39 858 de 72 960 |
| 7 semanas previstas, ENA | 1 600/1 600 | 1 280/1 280 | 1 920/1 920 |
| 8 mês gerado, ENA | 45 549 / 45 647 / 45 737 de 82 880 | 45 347 / 45 432 / 45 556 de 82 880 | 39 621 / 39 692 / 39 780 de 72 960 |
| 9 meses observados (11) | 3 520/3 520 | 3 520/3 520 | 3 520/3 520 |
| 10 semanas observadas | — (0) | 320/320 | — (0) |
| **arquivo** (medianas) | 99 086 / 173 760 (57,0%) | 98 439 / 173 440 (56,8%) | 87 882 / 154 560 (56,9%) |

Leitura: **todos os registros determinísticos são iguais byte a byte nas
três revisões** (cabeçalho, códigos, calendário, as semanas previstas
natural e ENA, os 11 meses observados e as semanas observadas). Nos blocos
gerados, as palavras iguais vêm quase todas das colunas sem dispersão
(postos sem usina, PN, NW absorvidas e incrementais nulas), que são iguais
em 100%; nas 153 colunas com dispersão do bloco 6 só 6,2% (RV0), 6,0% (RV1)
e 4,8% (202610) das palavras coincidiam na semente 1 na F11, por acaso (a
F13 muda as medianas da tabela em menos de 0,1%). No registro
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
`test_transplante_entre_revisoes`).

Com a lognormal da frente F11 (limite inferior M_t da P-LN3-09 e momentos
históricos dos resíduos, P-LN3-04; docs/limite-inferior.md), **o VAZOES.RV0
sai igual ao oficial byte a byte**, inclusive as 82 880 palavras de cada
bloco gerado (6 e 8). O controle RV1 → RV1 devolve o NINT do GEVAZP.OUT em
100% dos valores. É a evidência mais forte de que o condicionamento
(P-GER-03/04), a lognormal (P-LN3-04, P-LN3-09) e a ordem da recorrência
(P-GER-05, no nível do NINT) são os do modelo oficial, obtida numa execução
oficial que não serviu para inferir nenhuma regra.

Na F9, com a lognormal da primeira versão da F8 (M_t = 0, momentos
teóricos), o mesmo transplante dava:

| Bloco do VAZOES.RV0 | Palavras iguais (F9) |
| --- | --- |
| registros 1–3, probabilidades, blocos 5, 7, 9 | 100% |
| 6 (natural gerado) | 78 922 / 82 880 (95,2%); 90,0% nas 153 colunas com dispersão |
| 8 (ENA gerado) | 78 836 / 82 880 (95,1%); 89,9% nas 154 colunas com dispersão |

com erro de ±1 em 85% das palavras diferentes, até 18 m³/s, crescente com
|W|: era o erro de escala da lognormal que a F11 corrigiu.

### 2.3 Degraus T0–T12

Resultado de `./ambiente/py -m pytest tests` na frente F13 (29/10/2026), na
configuração padrão: amostra de 6 pacotes (`tests/pacotes.py`: 202609,
202610, 202201_pmo, 202402_rev2, 202507_pmo, 202605_pmo; T11 e T12 só nos
dois originais), **sem** a coleção de decks do ONS (03 §1.2), com o cache
de `cache/f8/` preenchido por `ferramentas/sementes_f8.py` para os dois
originais (simetria "nenhuma" com e sem o lateral no vetor agregado,
"antitetica" sem ele):

**974 passaram, 107 pulados, 0 falharam, 78 subtestes passaram** (53 min;
na F11, 970 passaram e 104 pulados: a F13 acrescenta o teste sem deck do
ruído individual do lateral e o teste nó a nó do ruído próprio, que passa
nos três pacotes das versões 8.1.6/10.0.0 da amostra e é pulado nos três da
versão 11).
Os pulados: agregações dos quatro pacotes do SINtegre fora do cache (T10,
16), testes que exigem a coleção do ONS (T0, T1, T7), amostras legíveis
escritas só para o 202609, casos sem o objeto testado no pacote (sem NW,
ramo PAR(p)) e controles da regra de M_t que não mudam nenhum M_t naquele
pacote (L8). A versão F9 deste relatório (418 passaram, com a coleção do
ONS e só os dois originais) mediu outra configuração e outro conjunto de
testes.

| Degrau | 202609 | 202610 | 202201_pmo | 202402_rev2 | 202507_pmo | 202605_pmo | sem deck |
| --- | --- | --- | --- | --- | --- | --- | --- |
| F2 (test_oraculo_*, leitores) | 40 ✓ | 38 ✓, 2 pul. | 35 ✓, 5 pul. | 37 ✓, 3 pul. | 38 ✓, 2 pul. | 38 ✓, 2 pul. | — |
| T0 | — | — | — | — | — | — | 13 ✓, 2 pul. |
| T1 | — | — | — | — | — | — | 17 ✓, 1 pul. |
| T2 | 5 ✓ | 5 ✓ | 5 ✓ | 5 ✓ | 5 ✓ | 5 ✓ | — |
| T3 | 11 ✓ | 11 ✓ | 7 ✓, 4 pul. | 11 ✓ | 11 ✓ | 11 ✓ | — |
| T4 | 18 ✓, 1 pul. | 18 ✓, 1 pul. | 17 ✓, 2 pul. | 18 ✓, 1 pul. | 18 ✓, 1 pul. | 18 ✓, 1 pul. | 20 ✓ |
| T5 | 14 ✓ | 14 ✓ | 14 ✓ | 14 ✓ | 14 ✓ | 14 ✓ | 11 ✓ |
| T6 | 6 ✓, 1 pul. | 6 ✓, 1 pul. | 5 ✓, 2 pul. | 6 ✓, 1 pul. | 6 ✓, 1 pul. | 6 ✓, 1 pul. | 4 ✓ |
| T7 | 5 ✓ | 3 ✓ | 2 ✓ | 2 ✓ | 2 ✓ | 2 ✓ | 48 ✓, 2 pul. |
| T8 | 9 ✓ | 9 ✓ | 8 ✓, 1 pul. | 8 ✓, 1 pul. | 9 ✓ | 9 ✓ | 19 ✓ |
| T9 | 4 ✓ | 3 ✓ | 3 ✓ | 3 ✓ | 3 ✓ | 3 ✓ | 12 ✓, 1 pul. |
| T10 | 4 ✓ | 4 ✓ | 4 pul. | 4 pul. | 4 pul. | 4 pul. | 14 ✓ |
| T11 | 21 ✓ | 21 ✓ | — | — | — | — | 14 ✓ |
| T12 | 4 ✓ (2 revisões) | 2 ✓ | — | — | — | — | 8 ✓ |
| L8 (test_oraculo_limite_inferior, test_ajuste_livre_sem_deck) | 15 ✓, 7 pul. | 14 ✓, 8 pul. | 14 ✓, 8 pul. | 13 ✓, 9 pul. | 14 ✓, 8 pul. | 16 ✓, 6 pul. | 4 ✓ |
| L11 (test_oraculo_laterais) | 2 ✓, 1 pul. | 2 ✓, 1 pul. | 2 ✓, 1 pul. | 2 ✓, 1 pul. | 3 ✓ | 2 ✓, 1 pul. | 1 ✓ (T11 sem deck) |
| test_proveniencia | — | — | — | — | — | — | 3 ✓ |

Os dois oráculos da F11 também nos 61 pacotes
(`pytest tests/test_oraculo_limite_inferior.py tests/test_oraculo_laterais.py
--decks todos`, com RuntimeWarning como erro, numa execução única de 1 465
itens, 60 min): **955 passaram, 510
pulados, 0 falharam**; os pulados são controles que não mudam nenhum M_t
no pacote e pacotes sem NW com jusante. T11 com 20 sementes só nos dois
originais; não foi rodado nos 61.

Na F13, `pytest tests/test_oraculo_laterais.py --decks todos` (em seis
lotes, um por família de b1 e um com os pacotes da versão 11): **137
passaram, 46 pulados, 0 falharam**; os pulados são o teste nó a nó nos 8
pacotes da versão 11 (sem ruído próprio) e pacotes sem NW com jusante. O
teste nó a nó passa nos 53 pacotes das versões 8.1.6 e 10.0.0: o b1 é igual a
1e-3 ao do pacote de maior K da família com K diferente do seu em 97,2% a
100% dos nós comuns, e o W do posto total coincide em no máximo 1 nó (famílias de
`ferramentas/familias_b1.py`, gravadas em `FAMILIAS_B1`).

### 2.4 Estatísticas de 03 §5

**Sobre o GEVAZP.OUT** (T11, `tests/test_t11_aceitacao.py`): fração
das 153 colunas (e dos pares, na correlação) em que a estatística oficial
cai na faixa [mín, máx] das 20 sementes (P-ACE-06; um gerador idêntico ao
oficial dá 0,90). "F8" é a primeira versão (M_t = 0, momentos teóricos,
lateral com a correlação anual e ruído próprio no vetor agregado); "F11"
tem a lognormal atual (docs/limite-inferior.md) com o lateral no vetor
agregado; "F13" é a atual, com o lateral fora dele (P-AGR-07):

| Deck | versão | média | desvio | assim. | Q1 | Q2 | Q3 | correl. | árvore |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 202609 RV1 | F8 | 0,922 | 0,909 | 0,857 | 0,890 | 0,870 | 0,909 | 0,908 | 1,000 |
| 202609 RV1 | F11 | 0,929 | 0,929 | 0,851 | 0,916 | 0,903 | 0,935 | 0,915 | 1,000 |
| 202609 RV1 | F13 | 0,935 | 0,916 | 0,877 | 0,903 | 0,909 | 0,909 | 0,921 | 0,833 |
| 202610 RV0 | F8 | 0,909 | 0,851 | 0,805 | 0,883 | 0,890 | 0,792 | 0,893 | 1,000 |
| 202610 RV0 | F11 | 0,916 | 0,877 | 0,844 | 0,890 | 0,896 | 0,870 | 0,896 | 1,000 |
| 202610 RV0 | F13 | 0,916 | 0,909 | 0,851 | 0,896 | 0,909 | 0,877 | 0,885 | 1,000 |

F11 e F13 diferem dentro do ruído de duas frações (~0,05) e se alternam
(`test_momentos_e_lateral_nao_se_separam`): o T11 não decide se o lateral
entra no vetor agregado. Quem decide de onde vem o b1 que entra no W são os
53 pacotes das versões 8.1.6 e 10.0.0 (sorteado nó a nó, não do vetor
agregado; P-LAT-04, seção 8); se o K-means tem uma componente do lateral
que não é usada continua sem oráculo (P-AGR-07, DOC + ESCOLHA). A árvore do 202609 passa a ter 5 das 6 estatísticas na
faixa (o Q3 da soma fica 0,4% abaixo). No `test_primeira_versao_da_f8` a
vantagem no Q3 do 202610 sobre a variante "zero" (M_t = 0) cai de 0,071
para 0,058, no limite do ruído; o limiar do teste passou de 0,06 para 0,05, e o critério
do T10 dos tamanhos de grupo mudou (P-ACE-08, decididos depois de ver os
resultados).

**Sobre o VAZOES.RVx** (T12, F9, P-INT-03; bloco 6 inteiro com as
probabilidades do registro 4), nas três revisões, faixa [mín, máx] e, entre
parênteses, a referência de um gerador idêntico (cada semente contra as
outras 19). Os limiares do teste são os do T11 (≥ 0,87 em média, Q2 e
correlação; a árvore, uma coluna só, em ≥ 5 das 6 estatísticas desde a F11;
mínimo 0,78; média das frações ≥ 0,87); a referência nos quartis passa de
0,90 porque os valores do VAZOES.RVx são inteiros e os empates alargam a
faixa. Linhas F9 com a lognormal da primeira versão, F11 com a atual e o
lateral no vetor agregado, F13 com o lateral fora dele:

| Revisão | versão | média | desvio | assim. | Q1 | Q2 | Q3 | correl. | árvore |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 202609 RV0 | F9 | 0,908 (0,90) | 0,908 (0,90) | 0,856 (0,90) | 0,928 (0,96) | 0,935 (0,96) | 0,961 (0,95) | 0,909 (0,90) | 1,000 |
| 202609 RV0 | F11 | 0,935 (0,90) | 0,922 (0,90) | 0,856 (0,90) | 0,941 (0,96) | 0,954 (0,96) | 0,974 (0,95) | 0,917 (0,90) | 1,000 |
| 202609 RV0 | F13 | 0,922 (0,90) | 0,908 (0,90) | 0,876 (0,90) | 0,961 (0,96) | 0,954 (0,96) | 0,948 (0,94) | 0,919 (0,90) | 0,833 |
| 202609 RV1 | F9 | 0,941 (0,90) | 0,889 (0,90) | 0,843 (0,90) | 0,948 (0,96) | 0,941 (0,96) | 0,967 (0,95) | 0,912 (0,90) | 1,000 |
| 202609 RV1 | F11 | 0,948 (0,90) | 0,908 (0,90) | 0,850 (0,90) | 0,948 (0,96) | 0,954 (0,96) | 0,980 (0,95) | 0,917 (0,90) | 1,000 |
| 202609 RV1 | F13 | 0,928 (0,90) | 0,915 (0,90) | 0,876 (0,90) | 0,967 (0,96) | 0,961 (0,96) | 0,961 (0,95) | 0,920 (0,90) | 0,833 |
| 202610 RV0 | F9 | 0,908 (0,90) | 0,856 (0,90) | 0,804 (0,90) | 0,935 (0,95) | 0,948 (0,95) | 0,869 (0,94) | 0,894 (0,90) | 1,000 |
| 202610 RV0 | F11 | 0,908 (0,90) | 0,876 (0,90) | 0,843 (0,90) | 0,948 (0,95) | 0,961 (0,95) | 0,922 (0,94) | 0,899 (0,90) | 1,000 |
| 202610 RV0 | F13 | 0,928 (0,90) | 0,902 (0,90) | 0,863 (0,90) | 0,967 (0,95) | 0,948 (0,95) | 0,935 (0,94) | 0,886 (0,90) | 1,000 |

Com a faixa P5–P95 (o exemplo de 03 §5) as frações oficiais ficam em
0,71–0,94 (F13; 0,74–0,93 na F11; 0,70–0,91 na F9) e as da referência em 0,81–0,92: o critério de 90% não é
atingível com 20 sementes por essa faixa nem por um gerador idêntico
(P-ACE-06). No bloco 8 (ENA) os números são os do bloco 6 a ±0,02.

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
- a partir do W oficial do RV1: o VAZOES.RV0 inteiro, byte a byte (T12,
  seção 2.2; 90% das palavras geradas antes da F11).

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

- **Forma da distribuição**: com a F11 o Q3 do 202610 sobe de 0,79 para
  0,87 (GEVAZP.OUT) e de 0,87 para 0,92 (VAZOES.RVx), o que indica que boa
  parte da pendência vinha do M_t (L8); na F13, tirar o M_t piora o Q3 do
  202610 em 0,058, no limite do ruído de ~0,05 (P-ACE-08 (b)). A assimetria ainda fica em 0,84–0,86 das
  colunas nas três revisões, abaixo da referência de 0,90 (ganho de
  ~0,04 no 202610, no limite do ruído); com o lateral fora do vetor
  agregado (F13) ela vai a 0,85–0,88, dentro do ruído; o resto pode ser a
  forma dos ruídos agregados (L6, L7), que nenhum arquivo público separa.
- **Bits da geração**: com a F11 o transplante entre revisões fecha byte a
  byte; os float64 da recorrência continuam sem oráculo de bits (L23).
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

As 99 linhas de PROVENIENCIA.md com ESCOLHA (inteira ou parcial; 93 na F9, mais P-LN3-10..13 e P-LAT-04 na F11 e P-ACE-08 na F13), agrupadas
pelo efeito nos três VAZOES.RVx publicados. "Sem efeito" quer dizer que o
caso não ocorre nos decks públicos ou que as alternativas dão o mesmo
arquivo; todas são parâmetros, salvo onde indicado.

### 6.1 Mudam a parte estocástica (blocos 6 e 8, probabilidades)

| Id | Escolha | Impacto medido |
| --- | --- | --- |
| P-RUI-01, P-RUI-03, P-RUI-05, P-GER-01 | PCG64 por posto, ziggurat, centros sorteados sem reposição, semente 0 | Definem a realização: as palavras das colunas com dispersão coincidem em ~5% (acaso); estatísticas equivalentes (seção 2.4). Não inferível (L6) |
| P-RUI-04 | "Ruído simétrico" = amostra aleatória simples | A antitética derruba a fração da média de 0,935 para 0,825 (202609) e de 0,916 para 0,844 (202610) (F11: 0,929 → 0,851 e 0,916 → 0,818; F8: 0,922 → 0,825 e 0,909 → 0,760) |
| P-AGR-04, P-AGR-05 | σ_i ponderado; FC escalar | Variantes mudam o FC < 0,3% e as frações ±0,03; sem o fator o T11 falha (< 0,1) |
| P-AGR-06 | K = 1: média da amostra, sem fator | Sem efeito (K = 259 e 228) |
| P-AGR-07, P-LAT-03, P-LAT-04 | Lateral fora do vetor agregado (DOC pelo R23954 §2 + ESCOLHA; F13), sem ruído próprio no W (versão 11, INFERIDO); principal = posto total | Uma coluna (SOBRADINHO_L): W_L = ρ_m W_P a 1e-6 nos 8 pacotes da versão 11; nos 53 das versões 8.1.6 e 10.0.0 o ruído próprio que entra no W é uma sequência sorteada nó a nó, que não vem do vetor agregado (variante "individual", INFERIDO); pôr o lateral no vetor (como até a F11) ou somar o ruído próprio muda as frações do T11 ≤ 0,05 (ruído) |
| P-LN3-03, P-LN3-07, P-LN3-08, P-LN3-10, P-LN3-11, P-LN3-12, P-LN3-13 | Rota inferida (padrão); M_t = 0, cúbicas e quantis como variantes; empate nos limiares de γ e nos extremos da faixa da cúbica (γ = 2 entra, γ = 4 não), limiar de negativos 0,15 dentro de [0,144; 0,1505), série sem valor ≥ 0 | A regra fecha o teste de núcleo a ~1e-8 nos 61 pacotes; as escolhas restantes não ocorrem nos pacotes; cúbicas e quantis perdem 0,07–0,14 na média das frações do T11 |
| P-LN3-06 | μ_a − Δ < 0: eq. 24 com quadrado (INFERIDO na F11) | 16 dos 61 pacotes têm 1 a 3 séries nesse caso; "normal" fica cem vezes pior no teste de núcleo |
| P-KM-01, P-KM-03, P-KM-04, P-KM-05 | Aritmética BLAS, lotes, ITER = 50, IFAULT | Mesmos grupos e iterações que a aritmética sequencial; convergência em 22–42 iterações; só desempenho (~6×) |
| P-GER-05 | Ordem da soma da recorrência | Ulps; o transplante fecha byte a byte com ela (2.2) |
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

- L6–L7: a assimetria um pouco abaixo da referência (0,84–0,86) e as
  variantes do fator de compensação. L8 e o resíduo do transplante foram
  fechados pela F11 (docs/limite-inferior.md); ficam o empate nos limiares
  da regra e o limiar de negativos dentro de [14,4%; 15,05%).
- L11 (F13): nos 53 pacotes das versões 8.1.6 e 10.0.0 o ruído próprio que
  entra no W do lateral é o mesmo nó a nó entre agregações de K diferentes
  (igual a 1e-3 em 97,2% a 100% dos nós comuns; o W do posto total coincide
  em no máximo 1 nó), então não vem do vetor agregado, como o R23954 §2
  descreve ("gerado individualmente"). O lateral saiu do vetor agregado por
  padrão (DOC pelo R23954 + ESCOLHA): nenhum arquivo mostra se o K-means
  tem uma componente do lateral que não é usada, nem na versão 11 nem nas
  anteriores (T10 e T11 não separam). Ficam também: os poucos nós em que o b1
  difere dentro de uma família; por que a versão 11 tirou o ruído próprio;
  satélites (o R23954 §4 descreve a classificação, mas a fórmula está em
  documentos que não estão em `fontes/`, e não há deck) e mais de um
  lateral.
- L19 e "Alcance das evidências da F3": T2–T5 repousam numa única amostra
  de histórico (1931–2024); faltam pacotes completos antigos (ramo PAR(p)) e
  de outro ano final de histórico.
- L10, L13–L18, L21: casos de layout e de configuração sem deck público.
- 03 §5 item 5: custo no DECOMP não avaliado.
- Desempenho: o K-means (P-KM-03) domina a execução (~2–3 min por deck).
