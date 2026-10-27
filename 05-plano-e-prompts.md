# Plano de trabalho e prompts

## Organização

- Linguagem: Python 3 com NumPy. Código em `src/pulsar/`, testes em
  `tests/`, notas de decodificação em `docs/`. Nesta máquina o Python do
  sistema não tem NumPy nem há compilador C; crie um ambiente próprio do
  projeto (por exemplo um container Docker com Python e NumPy) em vez de
  reaproveitar ambientes de outros projetos.
- Um orquestrador e agentes por frente, em ondas de no máximo três agentes
  ao mesmo tempo.
- Toda frente entrega: código, testes do seu degrau passando em todos os
  decks completos, linhas novas em `PROVENIENCIA.md` e um resumo do que
  ficou em aberto.
- Um agente auditor revisa cada entrega antes de integrar (prompt no fim).

| Onda | Frentes | Depende de |
| --- | --- | --- |
| 1 | F1 Entradas e configuração; F2 Decodificação dos arquivos públicos | — |
| 2 | F3 Estatísticas e PAR(p)-A; F5 Tendência e blocos semanais; F7 Empacotamento | F1, F2 |
| 3 | F4 Correlação espacial; F6 Totalização e artificiais | F3 (F4), F2 (F6) |
| 4 | F8 Núcleo estocástico | F3, F4 |
| 5 | F9 Integração, validação estatística e relatório | todas |

## Como cada frente é executada

Cada frente roda numa sessão nova, numa worktree e branch próprias
(`frente/F<n>-<nome>`). O prompt exato e a auditoria de cada execução ficam
registrados pelo projeto; os registros da primeira versão (frentes F1 a F9)
não fazem parte deste repositório público.

## Preâmbulo comum (cole no início de todo prompt)

```text
Você trabalha no repositório do Pulsar: uma reconstrução a
partir de fontes públicas do gerador de cenários GEVAZP (modo DECOMP). Antes de qualquer
coisa, leia por inteiro, nesta ordem: README.md, 00-regras.md,
01-fontes.md, 02-especificacao-publica.md, 03-oraculos-e-testes.md,
04-lacunas.md.

Regras inegociáveis:
- Use só as fontes permitidas em 00-regras.md. Não abra nenhum executável
  do GEVAZP, nada derivado dele (desmontagem, descompilação, análises) nem
  material de acesso restrito.
  Não rode o GEVAZP. Não procure na web por implementações do GEVAZP.
- Toda constante, fórmula, ordem de operação ou regra de layout que você
  implementar precisa de uma linha em PROVENIENCIA.md (DOC, INFERIDO ou
  ESCOLHA), no formato da seção 3 das regras.
- Quando a documentação e um arquivo público discordarem, vale o arquivo
  público; registre a divergência.
- Se encontrar material proibido, pare, registre em PROVENIENCIA.md e avise.

Responda em português. Ao terminar, entregue: o que foi implementado, os
testes e seus resultados por deck, as linhas novas de proveniência e o que
ficou em aberto.
```

## F1 — Entradas e configuração (degraus T0, T1)

```text
<preâmbulo comum>

Sua frente: leitura de todas as entradas do modo DECOMP e reconstrução da
configuração final das usinas.

1. Implemente leitores para CASO.DAT, Arquivos.DAT, GEVAZP.DAT, DADGER.RVx
   (registros UH, AC e o bloco "& VAZOES"), HIDR.DAT, PREVS.RVx, VAZOES.DAT,
   POSTOS.DAT, MODIF.DAT e REGRAS.DAT, seguindo o U19 §3–4 e o U11. Teste
   em todos os decks de decks/ e em pelo menos 30 casos da coleção
   PULSAR_COLECAO_GEVAZP (03 §1.2) de anos diferentes (T0).
2. Reconstrua a configuração final (quais usinas entram, classificação PN,
   NC, NW, PARTIF, VINCR, posto lateral, posto artificial NPOSNW, jusante,
   ordem) a partir de DADGER, HIDR e MODIF (02 §2).
3. Decodifique o config.out dos pacotes completos com as técnicas de 03 §3 e
   documente o layout em docs/layout-config-out.md, com a evidência que
   sustenta cada campo.
4. Faça a sua configuração gravar um config.out e compare byte a byte com o
   público (T1). Cada divergência resolvida vira uma linha INFERIDO.
```

## F2 — Decodificação dos arquivos públicos

```text
<preâmbulo comum>

Sua frente: entender o formato dos arquivos binários de saída e
intermediários dos pacotes em decks/ons-pacote-gevazp/, para que as outras
frentes tenham oráculos. Você não implementa o modelo.

Arquivos: correlt.out, correli.out, QPAST.DAT, vazaoanual.out, VAZOES.RVx,
PROBVAZ.DAT, GEVAZP.OUT, VAZTOTGD.DAT, vazoesia.out, vazoesta.out.

1. Para os que têm layout no U19 (§5.3.1.2, §5.3.4, §5.4), confirme o
   layout nos arquivos reais.
2. Para os demais, use as técnicas de 03 §3: tamanho de registro, varredura
   de inteiros e float64, e casamento com os números impressos em
   GEVAZP.REL, vordem.out, VAZDCP.REL e nos CSV. Use os dois decks.
3. Para cada arquivo, escreva docs/layout-<arquivo>.md com o layout, os
   trechos do texto público que o confirmam e o que ainda não foi
   identificado.
4. Escreva leitores em src/pulsar/oraculos/ que devolvem estruturas
   nomeadas (por exemplo "média mensal da série incremental do posto X"), com
   testes que conferem uma amostra contra o texto do GEVAZP.REL.
```

## F3 — Estatísticas e PAR(p)/PAR(p)-A (degraus T2, T3, T4)

```text
<preâmbulo comum>

Sua frente: do histórico (VAZOES.DAT + configuração da F1) até as ordens e
coeficientes de cada série incremental, nos ramos PAR(p) e PAR(p)-A.

1. Séries incrementais (02 §3) e janela de anos (lacuna L1).
2. Estatísticas mensais, assimetria, correlogramas (02 §4). Compare com os
   oráculos da F2 em float64 (T2, T3). Para diferenças nos últimos bits, use
   a enumeração de variantes de 03 §3.
3. Componente anual e FACP condicional do PAR(p)-A (02 §5; R1416 §3.3).
4. Seleção da ordem (IC de 95% com N anos) e Yule-Walker (02 §5).
5. Tratamento de coeficientes negativos a partir do texto da L-PAR
   (lacuna L3), refinado até as ordens finais baterem com os arquivos
   públicos em todos os decks (T4).
6. Resíduos históricos e seus momentos (02 §5, §9), conferidos com a
   "SERIE DE RUIDOS" e as estatísticas de ruído impressas no GEVAZP.REL.

Peça ao orquestrador pacotes de decks antigos (sem MODELO PAR-A) para
cobrir o ramo PAR(p).
```

## F4 — Correlação espacial e matriz de carga (degrau T5)

```text
<preâmbulo comum>

Sua frente: matriz de correlação espacial mensal das incrementais e matriz
de carga D (02 §6).

1. Calcule a matriz com as séries e a janela da F3. Descubra quais séries
   entram comparando com a matriz gravada nos pacotes (lacuna L4).
2. Implemente a decomposição espectral pelo método de Jacobi (Numerical
   Recipes, citado no M18 [16]) e D = A √V A'. Decida e registre o
   tratamento de autovalores negativos ou nulos.
3. Teste: matriz igual à pública (T5); D·D' reproduz a correlação nas
   direções de autovalor positivo.
```

## F5 — Tendência e blocos semanais (degraus T6, T7)

```text
<preâmbulo comum>

Sua frente: tendência hidrológica (QPAST.DAT) e todos os registros
determinísticos do VAZOES.RVx: cabeçalho, códigos, calendário, semanas
previstas naturais e artificiais, meses e semanas observados.

1. Média ponderada do mês inicial a partir do PREVS (U19 §4.7; lacuna L5).
2. Monte o QPAST.DAT e compare com o público (T6).
3. Monte os registros determinísticos do VAZOES.RVx com as regras de
   incremental (02 §3), PARTIF/posto 300 (02 §2) e regras dos artificiais
   (02 §11). Compare byte a byte em todas as revisões (RV0, RV1, ...) dos
   decks disponíveis (T7). Use VAZDCP.REL para entender cada registro.
```

## F6 — Totalização e postos artificiais (degrau T8)

```text
<preâmbulo comum>

Sua frente: das séries incrementais geradas até totais, artificiais e
incrementais dos artificiais (02 §10–11).

Trabalhe por transplante: parta do GEVAZP.OUT oficial (incrementais geradas)
e produza VAZTOTGD.DAT, vazoesta.out e vazoesia.out; compare com os oficiais
(T8). Implemente o avaliador de REGRAS.DAT pela gramática do U19 §3.10 e
investigue a precisão numérica das regras (lacuna L9). Trate PARTIF, VINCR,
postos laterais com defasagem (M18 eq. 4.21) e NPOSNW.
```

## F7 — Empacotamento (degrau T9)

```text
<preâmbulo comum>

Sua frente: gravar VAZOES.RVx e PROBVAZ.DAT a partir de dados tipados.

Partindo de GEVAZP.OUT, vazoesia.out e PROBVAZ.DAT oficiais, dos registros
determinísticos da F5 e da configuração da F1, produza o VAZOES.RVx e
compare byte a byte com o público (T9). Use U19 §5.3.4 e §5.4 e o layout
documentado pela F2 (lacuna L10). O gravador não pode ler nenhum VAZOES.RVx
existente.
```

## F8 — Núcleo estocástico (degraus T10, T11)

```text
<preâmbulo comum>

Sua frente: geração dos cenários do período estocástico (02 §8–10).

1. Ruídos normais independentes, uma coluna por número de posto, gerador
   bem estabelecido e semente configurável (lacuna L6). Tamanho da amostra
   conforme R3383 e confirmado pela técnica de denominadores de 03 §3 sobre
   o PROBVAZ.DAT público.
2. K-means: AS 136 de fontes/algoritmos/as136.f (port fiel, sem
   "melhorias"), centros iniciais sorteados entre os objetos, K = aberturas
   do DADGER, probabilidade = contagem/N (lacuna L12).
3. Centroide como representante e fator de compensação do R3383 eq. 2.2
   (lacuna L7: implemente as variantes).
4. Correlação espacial com a D da F4, lognormal de três parâmetros com as
   rotas para M_t da lacuna L8, recorrência PAR(p)-A com a tendência da F5.
5. Postos laterais e derivados (lacuna L11).
6. Grave GEVAZP.OUT no layout do U19 e entregue para a F6 e a F7.
7. T10 e T11: aceitação estatística de 03 §5 com 20 sementes, por deck.
   Escolha as variantes de L7 e L8 pelos resultados e registre como ESCOLHA.
```

## F9 — Integração, validação e relatório (degrau T12)

```text
<preâmbulo comum>

Sua frente: juntar F1–F8 num comando único que recebe um diretório de deck e
grava VAZOES.RVx e PROBVAZ.DAT, e produzir o relatório final.

1. CLI: src/pulsar/cli.py <deck> --revisao RVn --saida <arquivo>
   --semente <n>.
2. Para cada deck completo: palavras iguais e diferentes por bloco do
   VAZOES.RVx, resultado de T1–T11 e estatísticas de 03 §5.
3. Relatório em docs/relatorio-final.md: o que ficou igual byte a byte, o
   que é estatisticamente equivalente, o que não é, e a lista de ESCOLHAS
   com o impacto de cada uma.
4. Revise PROVENIENCIA.md inteiro: cada linha precisa apontar para uma
   fonte permitida ou para um teste existente.
```

## Auditor de proveniência (roda em cada entrega)

```text
<preâmbulo comum>

Você é o auditor de proveniência do Pulsar. Revise a entrega <branch ou diff>:

1. Para cada constante numérica, fórmula, ordem de operação, tamanho de
   registro ou regra condicional no código, encontre a linha de
   PROVENIENCIA.md correspondente e confira a fonte ou o teste citado.
   Liste o que não tiver proveniência ou cuja citação não sustente o
   código.
2. Desconfie de detalhes muito específicos sem teste INFERIDO que os
   justifique (constantes mágicas, sementes, limiares). Peça a evidência.
3. Verifique que nenhum arquivo, comentário ou commit cita executável,
   desmontagem, descompilação, pseudocódigo ou material derivado do executável.
4. Rode os testes da entrega e confira os resultados declarados.

Saída: aprovado ou lista de pendências, com arquivo e linha.
```

## Rodada 2 (27/10/2026): pacotes completos do SINtegre

| Onda | Frentes | Depende de |
| --- | --- | --- |
| 6 | F10 Revalidação em todos os pacotes | primeira versão |
| 7 | F11 Limite inferior da lognormal e postos derivados | F10 |

## F10 — Revalidação em todos os pacotes (degraus T0–T10)

```text
<preâmbulo comum>

Sua frente: revalidar e corrigir a parte determinística do Pulsar nos 59
pacotes completos de decks/ons-sintegre/ (03 §1.1b), além dos dois de
decks/ons-pacote-gevazp/.

1. Faça os testes T0 a T10 rodarem sobre todos os pacotes (parametrize por
   pasta; mantenha um modo rápido com uma amostra para o dia a dia).
2. Para cada degrau, liste em docs/revalidacao-2022-2026.md quais pacotes
   fecham e quais não, com a primeira divergência de cada um.
3. Corrija as divergências usando as técnicas de 03 §3, registrando cada
   regra nova como INFERIDO com teste. Atenção especial a: decks sem
   MODELO PAR-A (ramo PAR(p), lacunas L3 e L19), meses de todo o ano,
   fevereiro de ano bissexto e as revisões de fev/2024 (lacuna L5), janela de
   anos do histórico (L1) e configurações diferentes ao longo de 2022–2026
   (lacunas L13 e L14).
4. Não altere a parte estocástica (F8) além do necessário para os testes
   rodarem.
```

## F11 — Limite inferior da lognormal e postos derivados

```text
<preâmbulo comum>

Sua frente: as lacunas L8 (limite inferior M_t da lognormal de três
parâmetros) e L11 (postos laterais e outros postos derivados), usando os 61
pacotes completos (03 §1.1 e §1.1b).

Os GEVAZP.OUT públicos trazem, em float64, os cenários gerados de cada
usina no mês estocástico. Tudo o que entra na geração, exceto os ruídos e
o limite inferior, já é reproduzido pelo Pulsar a partir de dados públicos
(estatísticas, coeficientes, tendência, matriz de carga). Investigue o que
os cenários públicos permitem identificar sobre M_t de cada usina e mês e
sobre a relação entre postos derivados e seus principais. Explore as
restrições estruturais que o modelo documentado (02 §5–§10) impõe aos
cenários. Com M_t identificado em muitas usinas, meses e anos, procure a
regra que o explica em função de quantidades calculáveis do histórico
(momentos, mínimos, assimetria, contagens), com teste contra todos os
pacotes. Se nenhuma regra fechar, registre o melhor ajuste como ESCOLHA.

Atualize a F8 para usar o que for identificado, rode a aceitação
estatística de 03 §5 de novo e compare com a primeira versão.
```
