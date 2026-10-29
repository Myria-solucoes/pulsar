# Fontes públicas

Todas são públicas e foram baixadas em 26/10/2026. O texto de cada uma está
em `fontes/`; os originais (PDF, HTML) ficam fora do git, com a origem e o
SHA-256 em `fontes/MANIFESTO.tsv` (ver `fontes/README.md`). Esses arquivos
são de terceiros e não estão sob a licença do Pulsar. Os relatórios do CEPEL estão no portal
`https://www.cepel.br/produtos/documentacao-tecnica/`. Cada PDF ganha um
`.txt` gerado com `pdftotext -layout`; fórmulas saem melhor na imagem do PDF.

## Relatórios do CEPEL (`fontes/cepel/`)

| Id | Arquivo | Conteúdo útil |
| --- | --- | --- |
| **M18** | `Rel-13955_2018_Manual-de-Metodologia` | Manual de Metodologia do GEVAZP. Cap. 4: modelo PAR(p), identificação pela FACP (§4.2.1), estimação por Yule-Walker com Cholesky (§4.2.2), geração (§4.3), lognormal de 3 parâmetros (§4.3.1), correlação espacial por decomposição espectral pelo método de Jacobi (§4.3.2), postos laterais e tempo de viagem (§4.3.3), postos artificiais (§4.3.4, fluxograma). Cap. 5: agregação por K-means (definições, distância, representante, probabilidade). Cap. 6: testes de aderência. Referências (Numerical Recipes é a [16]). |
| **U19** | `Rel-6646_2019_Manual-do-Usuario` | Manual do Usuário. §2.1 fluxograma; §3 entradas do modo autônomo; §3.10 gramática do `REGRAS.DAT`; §4 modo DECOMP (`DADGER` bloco `& VAZOES`, `PREVS`, `VSEMPAST`, `VAZOES.DAT`, `POSTOS.DAT`, `MODIF.DAT` com `PARTIF`/`VINCR`); §5.3.1–5.3.2 layout dos arquivos de séries geradas (`RECL = NPOS*8`, um registro por série e período); §5.3.4 layout do `VAZOES.XXX`; §5.4 layout e laço de gravação do `PROBVAZ.DAT`; §7 capacidades; §9 histórico de versões. |
| **R3383** | `Rel-3383_2019_Centroide` | Agregação nos vetores de ruídos normais independentes, centroide como representante, fator de compensação do desvio-padrão (eq. 2.2, legível na imagem da pág. 9), amostra original de 50 mil objetos recomendada, uma agregação por período repetida nos ramos (Figura 2.5), cita Hartigan & Wong [17]. |
| **R1416** | `Rel-1416_2020_PARp-A` | Modelo PAR(p)-A: equações (10)–(19), FACP condicional à componente anual (§3.3), cadeia de geração (cap. 4: ruídos normais → K-means → correlação espacial → lognormal → PAR(p)-A → soma na cascata). |
| R13612 | `Rel-13612_2018_Representante` | Alternativas de representante na agregação (centroide x mais próximo). |
| R46994 | `Rel-46994_2009_Arvore` | Árvore de cenários do médio prazo, sensibilidade à semente. |
| R27063 | `Rel-27063_2016_v54` | Versão 5.4: postos laterais, artificiais, AR(0), tendência por posto. |
| R23953 | `Rel-23953_2016_Compilador` | Mudança de compilador e reprodutibilidade de resultados entre versões. |
| **R23954** | `Rel-23954_2016_Tempo-de-viagem` | "Geração de Cenários de Afluência para Usinas com Tempo de Viagem" (01/12/2016), versão 5.5.1. §1 vazão lateral x incremental e histórico do posto 168/169; §2 PAR(p) ajustado ao histórico lateral qualquer que seja a classificação, ruído do lateral gerado depois do dos principais e individualmente, eq. (2)–(3) (= M18 eq. 4.19–4.20, legíveis na imagem da pág. 7), seleção dos principais (a) principal, (b) satélite; §3 as duas alternativas de vazão total, eq. (4) (= M18 eq. 4.21) e nota 3 (períodos t e t−1 de mesma duração); §4 funcionalidades da 5.5.1 (tendência por posto no `VAZOES.XXX`, usina satélite por alta correlação na mesma bacia, alternativas por usina, ENA de acoplamento a partir das incrementais do `VAZOES.XXX`); §5 avaliação estatística de SOBRADINHO (168 e 169). |

O R23954 constava do índice do portal com o endereço
`https://cepel.br/wp-content/uploads/2022/03/Rel-23954_2016.pdf`, que saiu do
ar depois da reforma do site (em 29/10/2026, quando a cópia foi baixada, o endereço redireciona para
`www.cepel.br` e responde 403; antes, 404). A cópia usada é a pública do
Internet Archive,
`https://web.archive.org/web/20251126020804id_/https://cepel.br/wp-content/uploads/2022/03/Rel-23954_2016.pdf`
(SHA-256 `cd2e4033…9f9a`, em `fontes/MANIFESTO.tsv`), e o índice arquivado
que a lista é
`https://web.archive.org/web/20260713093716/https://www.cepel.br/produtos/documentacao-tecnica/`
(linha "01/12/2016, 23954/2016"). O relatório descreve a versão 5.5.1; os
pacotes de 2022–2026 são das versões 9_L, 10.0.0, 11 e 11.0.2, e onde eles
discordam do texto vale o pacote. As equações (1)–(4) e o Anexo A são
imagens no PDF e saem vazias ou truncadas no `.txt`.

## Documentação web LIBS (`fontes/libs/`)

`Libs_manual.pdf` é o PDF completo da documentação. As páginas avulsas
(`.html` e `.txt` com a URL de origem no topo) são:

| Página | Conteúdo útil |
| --- | --- |
| `incerteza_hidrologica_modelo-par-p` | eq. (2)–(11) estatísticas com denominador N, assimetria `N/((N-1)(N-2))`, correlograma; eq. (12)–(17) PAR(p); IC de 95% com amostra igual ao número de anos; Cholesky; tratamento de coeficientes negativos (prosa) |
| `incerteza_hidrologica_modelo-par-p-a` | eq. (31)–(37) PAR(p)-A e o sistema aumentado |
| `incerteza_hidrologica_distribuicao-lognormal-3-parametros` | eq. (18)–(27) |
| `incerteza_hidrologica_correlacao-espacial` | eq. (28)–(30), Jacobi |
| `incerteza_hidrologica_geracao-ruidos-multivariados` | ordem: ruído independente → matriz de carga → lognormal |
| `incerteza_hidrologica_calculo-vazoes-incrementais` | eq. (1) |
| `incerteza_hidrologica_classificacao-postos` | principal, satélite, artificial, nulo |
| `incerteza_hidrologica_geracao-usinas-afetadas-tempo-viagem` | vazão lateral, eq. (55)–(56) |
| `incerteza_hidrologica_geracao-series-sinteticas-vazao-total` | duas alternativas de totalização, eq. (53)–(54) |
| `incerteza_hidrologica_geracao-cenarios-postos-artificiais` | ordem de cálculo dos artificiais |
| `incerteza_hidrologica_geracao-series-sinteticas-condicionadas`, `..._tendencia-hidrologica` | tendência hidrológica |
| `incerteza_hidrologica_modelo-ms-par-p-enso` | MS-PAR(p) (fora do escopo PMO atual) |
| `geracao_cenarios_*` | definições, métodos (K-means, centroide x mais próximo), árvore |
| `modelos_computacionais_modelo_gevazp` | visão geral e referências |

## Algoritmos de referência (`fontes/algoritmos/`)

| Arquivo | O que é |
| --- | --- |
| `as136.f` | Algoritmo AS 136 (Hartigan & Wong, *Applied Statistics* 28(1):100–108, 1979), código Fortran publicado na StatLib (`http://lib.stat.cmu.edu/apstat/136`). É a referência [17] do R3383. |

Referências públicas que não estão copiadas aqui por direitos autorais, mas
podem ser consultadas:

- Press, Flannery, Teukolsky, Vetterling, *Numerical Recipes in Fortran 77*,
  2ª ed., 1992 — rotina `jacobi` (citada por M18 [16] para a decomposição
  espectral) e geradores de números aleatórios.
- Charbeneau (1978) e Burges et al. (1975) — lognormal de três parâmetros.
- Maceira & Bezerra (1997), PMAPS — modelo de vazões do GEVAZP.
- Salas et al. (1980), *Applied Modeling of Hydrologic Time Series*.

## Manual do Usuário da versão 11 e relatório DSE-3031/2025

| Id | Documento | Conteúdo útil |
| --- | --- | --- |
| **U11** | Manual do Usuário GEVAZP 11.0.2 (CEPEL, 22/04/2026), distribuído na pasta "documentos" do pacote do modelo, segundo a página LIBS do GEVAZP | O que mudou entre 2019 e a versão 11: bloco `& VAZOES` atual, campos novos do `GEVAZP.DAT`, 13º registro da lista de arquivos, gramática completa das regras. |
| **R3031** | Relatório CEPEL DSE-3031/2025, robustez do GEVAZP à entrada de novas usinas (`https://www.cepel.br/wp-content/uploads/2026/01/2025-12-26_RP_DSE_3031_2025_ONS_GEVAZP_PME_012_GEVAZP_robusto_entrada_novas_usinas.pdf`) | A versão 11 associa a semente dos ruídos ao número do posto da usina. |

Os dois estão em `fontes/MANIFESTO.tsv`; o texto deles ainda não está em
`fontes/`. Onde o Pulsar usa um ponto que só esses
documentos descrevem, a linha de proveniência também cita o arquivo público
dos pacotes que confirma o ponto.

## Decks (`decks/`)

Ver [03-oraculos-e-testes.md](03-oraculos-e-testes.md).
