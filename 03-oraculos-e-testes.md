# Oráculos públicos e escada de testes

Sem o executável, os únicos oráculos são os arquivos que o ONS já publicou.
Por sorte, o pacote GEVAZP do ONS traz não só o `VAZOES.RVx` final, mas
também os intermediários que o modelo grava. Isso permite testar cada
etapa separadamente.

## 1. Decks disponíveis

### 1.1 Pacotes GEVAZP completos (entradas + todas as saídas)

Em `decks/ons-pacote-gevazp/<AAAAMM>/`, pacotes publicados pelo ONS. Os
decks não ficam no git (são do ONS e somam centenas de MB); baixe-os do
SINtegre e descompacte nessa pasta. O `TESARV.OUT` (100 MB) pode ser
omitido.

| Deck | Mês do estudo | Observação |
| --- | --- | --- |
| `202609` | set/2026 | PMO com `DADGER.RV0` e `DADGER.RV1`, `prevs.RV0`/`RV1`, `VAZOES.RV0`/`RV1` |
| `202610` | out/2026 | PMO RV0 |

Para cobrir os doze meses, vários anos e decks antigos (PAR(p) puro,
antes de `MODELO PAR-A`), use mais pacotes completos. Eles vêm do mesmo
lugar (ONS/SINtegre, arquivos `Gevazp_<AAAAMM>_<PMO|REVn>.zip`). Só use pacotes **publicados pelo ONS**: o cabeçalho do
`GEVAZP.REL` traz "PROGRAMA LICENCIADO PARA OPERADOR NACIONAL DO SISTEMA
ELETRICO".

### 1.1b Pacotes completos baixados do SINtegre (27/10/2026)

Em `decks/ons-sintegre/<AAAAMM>_<pmo|revN>/`, 59 pacotes oficiais do produto
SINtegre/ONS "Arquivos dos modelos de geração de cenários de vazões", com
todas as entradas e saídas (menos o `TESARV.OUT`):

- os PMOs de jan/2022 a set/2026, menos o de jul/2023, que não veio no
  download (56 pacotes), cobrindo os doze meses,
  o ramo PAR(p) (decks anteriores a `MODELO PAR-A`) e o ramo PAR(p)-A;
- as revisões RV1 a RV3 de fev/2024 (ano bissexto).

O arquivo `.ok` de cada pasta registra o ZIP de origem e o SHA-256. Esta
pasta é de leitura: não altere os arquivos.

### 1.2 Coleções parciais de decks do ONS (somente leitura)

Coleções montadas a partir dos decks que o ONS publica (PMO e revisões),
apontadas pelas variáveis de ambiente abaixo. Os testes que dependem delas
são pulados quando a variável não está definida.

| Variável | Estrutura esperada | Conteúdo | Uso |
| --- | --- | --- | --- |
| `PULSAR_COLECAO_GEVAZP` | `<ano>/<AAAAMM>_<pmo|revN>/` | `DADGER`, `HIDR.DAT`, `REGRAS.DAT` de 2012 a 2026 | testar leitura e configuração em muitos casos |
| `PULSAR_COLECAO_DECOMP` | `<ano>/*DEC_ONS_*.zip` | decks DECOMP oficiais com `vazoes.rvX` | `VAZOES` final de centenas de casos; não trazem `PREVS` |

Decks NEWAVE publicados pelo ONS também trazem `VAZOES.DAT` e `POSTOS.DAT`
históricos do mês.

## 2. O que cada arquivo público permite testar

| Arquivo do pacote | Etapa que valida | Precisão | Layout documentado? |
| --- | --- | --- | --- |
| `GEVAZP.REL` | estatísticas mensais, correlogramas, FACP, ordens, coeficientes, série e estatísticas dos resíduos, resultados totalizados | texto, decimais impressos | não; é texto legível |
| `vordem.out` | ordens e coeficientes finais por série | texto | não |
| `correlt.out`, `correli.out` | estatísticas das séries totais e incrementais | binário | não (U19 §5.2 só cita a existência) |
| `config.out` | configuração final das usinas | binário | não |
| `QPAST.DAT` | tendência hidrológica | binário | não |
| `GEVAZP.OUT`, `VAZTOTGD.DAT` | séries geradas incrementais e totais, por cenário | float64, `RECL = NPOS*8` | sim, U19 §5.3.1.2 |
| `vazoesia.out`, `vazoesta.out` | idem considerando artificiais | float64 | sim, U19 §5.3.1–5.3.2 |
| `vazaoanual.out` | componente anual | binário | não |
| `PROBVAZ.DAT` | probabilidades dos nós | float32, `RECL = NPOS*4` | sim, U19 §5.4 |
| `VAZOES.RVx`, `VAZDCP.REL` | arquivo final e seu espelho em texto | binário + texto | parcial, U19 §5.3.4 |
| `TCOND.REL`, `TESTES.REL`, `QUANTIL.CSV` | média, desvio e quantis dos cenários; testes de aderência | texto | M18 cap. 6 |
| `VAZOESI.CSV`, `VAZOESIA.CSV`, `VAZOEST.CSV`, `VAZOESTA.CSV` | espelhos em texto das séries geradas | texto | não |

## 3. Técnicas permitidas para inferir o que não está escrito

**Decodificar arquivos binários de dados.** São dados públicos, não o
programa. Técnicas:

- candidatos de tamanho de registro a partir do tamanho do arquivo e de
  `NPOS` (320/600), sabendo que o modelo usa acesso direto;
- varrer o arquivo procurando inteiros pequenos plausíveis (contagens,
  códigos de usina, anos) e float64 em faixas plausíveis;
- casar valores com o texto impresso no `GEVAZP.REL`, `vordem.out` ou nos
  CSV, que mostram os mesmos números com poucas casas;
- confirmar com dois decks diferentes.

**Isolar uma etapa por transplante.** Alimente a sua etapa N com a saída
oficial da etapa N-1 (por exemplo, o `GEVAZP.OUT` oficial no lugar das suas
séries geradas, ou o `QPAST.DAT` oficial no lugar da sua tendência). Assim
um erro numa etapa não contamina o diagnóstico da seguinte.

**Enumerar variantes numéricas.** Quando o arquivo público é float64 e o seu
valor difere só nos últimos bits, teste variantes razoáveis: ordem da soma
(crescente, decrescente, por blocos), denominadores (`N`, `N-1`, número de
pares válidos), `x*x` contra `x**2`, armazenamento intermediário em
float32, momento em que se arredonda. Registre a variante vencedora como
`INFERIDO`.

**Inferir denominadores e contagens.** Probabilidades float32 de grupos de
K-means são razões `contagem/N`. Encontre o menor `N` inteiro que torna
todas as probabilidades públicas compatíveis com contagens inteiras.

**Comparar regras com vários decks.** Uma regra só vale quando fecha em
todos os decks disponíveis. Mantenha um teste por deck.

**Não** é permitido gerar novas saídas oficiais rodando o modelo, nem com
entradas modificadas.

## 4. Escada de testes

Cada degrau tem um teste automatizado em `tests/` e só se avança quando ele
passa em todos os decks completos disponíveis.

| Degrau | Teste | Critério |
| --- | --- | --- |
| T0 | leitura de todas as entradas de todos os decks (incluindo a coleção parcial de decks do ONS) | sem erro; contagens batem com o texto do `GEVAZP.REL` |
| T1 | configuração final reconstruída a partir de `DADGER`, `HIDR`, `MODIF` | igual ao `config.out` público byte a byte |
| T2 | histórico incremental, janela de anos, médias, desvios, assimetria | igual a `correlt.out`/`correli.out` (depois de decodificados) e ao `GEVAZP.REL` |
| T3 | correlogramas e FACP | idem |
| T4 | ordens e coeficientes PAR(p)/PAR(p)-A, inclusive o tratamento de negativos | ordens iguais em todas as séries e meses; coeficientes iguais ao `correli.out`/`vordem.out` |
| T5 | correlação espacial mensal | igual à matriz gravada no pacote, se for encontrada; senão, ao `GEVAZP.REL` |
| T6 | tendência hidrológica | igual ao `QPAST.DAT` |
| T7 | registros determinísticos do `VAZOES.RVx`: cabeçalho, códigos, calendário, semanas previstas (naturais e artificiais), observados | iguais byte a byte, em todas as revisões |
| T8 | totalização, artificiais e incrementais artificiais por transplante: partindo do `GEVAZP.OUT` oficial | `VAZTOTGD.DAT`, `vazoesta.out`, `vazoesia.out` iguais após o arredondamento final; registros mensais do `VAZOES.RVx` iguais |
| T9 | empacotamento: do `GEVAZP.OUT`, `vazoesia.out` e `PROBVAZ.DAT` oficiais até o `VAZOES.RVx` | igual byte a byte |
| T10 | probabilidades | número de grupos e denominador corretos; distribuição dos tamanhos de grupo compatível com a oficial |
| T11 | geração estocástica completa | aceitação estatística (seção 5) |
| T12 | ponta a ponta | registros determinísticos iguais; registros estocásticos dentro da faixa de variação por semente |

T1 a T9 são determinísticos e devem chegar à igualdade exata. T10 a T12
dependem das lacunas L6 a L8 e têm critério estatístico.

## 5. Aceitação estatística da parte estocástica

O próprio CEPEL avalia o gerador variando a semente (R3383 cap. 4;
R13612 §4; R46994). Use o mesmo critério:

1. Rode a sua geração com 20 sementes diferentes para cada deck.
2. Para cada posto e para a árvore como um todo, calcule com as
   probabilidades das folhas: média, desvio-padrão, assimetria, quantis
   25/50/75 (como no `QUANTIL.CSV`), correlações espaciais entre postos e,
   como no `TCOND.REL`, média e desvio condicionados.
3. Calcule as mesmas estatísticas sobre o `VAZOES.RVx` oficial.
4. Aceite quando a estatística oficial cair dentro da faixa das 20 sementes
   (por exemplo entre o 5º e o 95º percentil) em pelo menos 90% dos postos, e
   quando os testes do M18 cap. 6 (momentos condicionados, Kolmogorov-Smirnov,
   Cramér-von Mises) derem o mesmo veredito para o oficial e para a sua
   geração.
5. Reporte também o custo dessa diferença em termos do DECOMP, se houver
   tempo para rodá-lo com as duas árvores.

Documente no relatório final, por deck, quantas palavras do `VAZOES.RVx`
são iguais, quantas diferem e em que blocos.
