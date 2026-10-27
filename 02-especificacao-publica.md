# Especificação pública

Tudo neste documento está escrito numa fonte pública e vem com a citação.
Ids das fontes: ver [01-fontes.md](01-fontes.md). Quando uma fonte deixa um
ponto em aberto, isso está marcado com **[lacuna Lx]**, que remete a
[04-lacunas.md](04-lacunas.md).

Escopo: o modo DECOMP (`GEVAZP.DAT` registro 2 = 99, U19 §4), modelo PAR(p)-A
quando o `DADGER` traz `MODELO PAR-A` ativo e PAR(p) caso contrário, sem
MS-PAR(p), uma árvore com prefixo determinístico semanal e um período
estocástico mensal. Ficam de fora: modo paralelo, NEWAVE, ventos, ENSO,
estudo prospectivo e similaridade/severidade.

## 1. Fluxo geral

Ordem das etapas (U19 §2.1; M18 Figura 4.4; R1416 cap. 4; L-RUID):

1. Ler dados gerais, configuração das usinas e históricos.
2. Classificar postos (principal, satélite, artificial, nulo) e calcular as
   vazões incrementais históricas.
3. Ajustar, para cada série incremental, um modelo PAR(p) ou PAR(p)-A:
   estatísticas, identificação da ordem, estimação, resíduos.
4. Calcular a correlação espacial e a matriz de carga.
5. Montar a tendência hidrológica dos meses anteriores (histórico
   atualizado + média ponderada das semanas do mês inicial).
6. Gerar uma amostra grande de ruídos normais independentes, agregá-la por
   K-means e corrigir o desvio-padrão.
7. Correlacionar espacialmente os ruídos agregados, transformar pela
   lognormal de três parâmetros e aplicar a recorrência PAR(p)-A.
8. Somar as incrementais pela cascata (vazões totais), calcular os postos
   artificiais pelas regras e as incrementais dos artificiais.
9. Gravar `VAZOES.XXX`, `PROBVAZ.DAT` e os demais arquivos.

## 2. Entradas

| Arquivo | Especificação |
| --- | --- |
| `CASO.DAT`, `ARQUIVOS.DAT`, `GEVAZP.DAT` | U19 §4.1–4.4; campos atuais em U11 |
| `DADGER.XXX` | registros `UH`, `AC` (`NUMPOS`, `NUMJUS`, `NPOSNW`) e o bloco comentado `& VAZOES` (U19 §4.5; nomes de arquivos, ano final do histórico, número de postos, mês/ano inicial, semanas não observadas/observadas, dias excluídos, aberturas por período estocástico, opção de agregação `N`/`S`/`6`, ordem máxima, defasagem linear, correlação anual/mensal, ordenação, representante `0`/`1`, ajuste a todas as UHEs, MS-PAR, prospectivo) |
| `HIDR.DAT` | cadastro do DECOMP (U19 §4.6) |
| `PREVS.XXX` | vazões semanais totais por posto, até seis semanas (U19 §4.7) |
| `VSEMPAST.XXX` | semanas do mês anterior, só com propagação linear (U19 §4.8) |
| `VAZOES.DAT` | histórico mensal, acesso direto não formatado, 320 ou 600 postos por registro mensal (U19 §3.6, §4.9) |
| `POSTOS.DAT` | anos inicial e final de cada posto (U19 §3.7, §4.10) |
| `MODIF.DAT` | `PARTIF` e `VINCR` (U19 §4.11) |
| `REGRAS.DAT` | regras dos postos artificiais: `+ - * /`, `VAZ(n)`, `MAX`, `MIN`, `SE`, comparadores e conectivos (U19 §3.10; gramática atual em U11) |

Regras de configuração escritas nas fontes:

- `NC` remove a UHE; `PN` mantém a identidade com incremental zero (L-POST,
  U11).
- `PARTIF`: incremental nula nos meses estocásticos; nos meses observados e
  semanas usa os valores fornecidos; associada ao posto 300, nula também nos
  observados e semanas (U19 §4.11).
- `NPOSNW` associa o posto artificial da ENA de acoplamento; com posto
  lateral, indica o posto total (U19 §4.5).
- Os postos 34 e 43 podem ser somados para o posto 44 (Ilha Solteira
  Equivalente) (U19 §4.7).
- Anos efetivos do histórico: interseção comum dos postos, limitada pelo
  `POSTOS.DAT` (U11) **[lacuna L1]**.

## 3. Vazões incrementais históricas

`Zinc(i,t) = Ztot(i,t) - Σ_{m ∈ montante imediata de i} Ztot(m,t)`
(L-INC eq. 1; M18 §4.3.3). Postos com tempo de viagem relevante podem usar
vazão lateral (M18 §4.3.3; L-VIAG).

## 4. Estatísticas

Para cada série e mês m, com N anos (L-PAR eq. 8–11; M18 §2):

- média `μ_m = (1/N) Σ Z_im`;
- desvio `σ_m = sqrt((1/N) Σ (Z_im - μ_m)^2)` (denominador N);
- assimetria `γ_m = N/((N-1)(N-2)) Σ ((Z_im - μ_m)/σ_m)^3`;
- autocorrelação periódica de lag k:
  `ρ_k^m = (1/N) Σ_i ((z_i,m - μ_m)/σ_m)((z_i,m-k - μ_m-k)/σ_m-k)`.
  O tratamento do lag que cruza o início do histórico (primeiro ano) não
  está escrito **[lacuna L2]**.

## 5. PAR(p) e PAR(p)-A

Modelo (L-PAR eq. 12; M18 eq. 4.1a):

`(Z_t - μ_m)/σ_m = Σ_{i=1..p_m} φ_i^m (Z_t-i - μ_m-i)/σ_m-i + a_t`

PAR(p)-A (L-PARA eq. 31–32; R1416 eq. 10–11): acrescenta
`ψ^m (A_t-1 - μ^A_m-1)/σ^A_m-1`, com `A_t-1` a média das 12 observações
anteriores a t. Detalhes de como a média e o desvio de `A` tratam o primeiro
ano do histórico não estão escritos **[lacuna L2]**.

**Identificação da ordem** (M18 §4.2.1; L-PAR; R1416 §3.3):

- ordem máxima 11 (L-PAR) ou a do `DADGER`;
- FACP `φ_kk` de cada mês; no PAR(p)-A, é a correlação entre `Z_t` e
  `Z_t-k` condicionada aos lags intermediários e a `A_t-1` (R1416 §3.3,
  eq. 20–21);
- sob a hipótese de ordem `p_m`, `φ_kk` para `k > p_m` é aproximadamente
  Normal com média 0 e variância `1/N` (M18 §4.2.1); o CEPEL usa intervalo
  de confiança de 95% com amostra igual ao número de anos (L-PAR);
- escolhe-se a maior ordem significativa (M18 §4.2.1).

**Estimação** (M18 §4.2.2; L-PAR eq. 14–16; L-PARA eq. 33–37; R1416 eq. 16–19):
Yule-Walker com as autocorrelações amostrais; no PAR(p)-A, sistema de
`p_m + 1` equações com a linha e a coluna da componente anual. M18 e L-PAR
dizem que o sistema é resolvido por Cholesky. Variância do resíduo
`σ_a²(m) = 1 - Σ φ_i^m ρ_i^m` (M18 eq. 4.8).

**Coeficientes negativos** (L-PAR, seção "Tratamento de coeficientes
negativos", texto integral em `fontes/libs/incerteza_hidrologica_modelo-par-p.txt`):
verifica-se o coeficiente de ordem 1 do mês (se for o caso, o modelo vai a
ordem zero); depois o coeficiente "que combina o coeficiente do modelo PAR(p)
e modelo PAR(p)-A"; se negativo, reduz-se a ordem e reestima-se, até que os
parâmetros de todos os meses não produzam contribuição negativa em nenhum
mês futuro. A forma exata da "contribuição em mês futuro" e da combinação com
o coeficiente anual não está escrita **[lacuna L3]**.

**Resíduos históricos** (L-PAR eq. 17): `a_t = (Z_t-μ_m)/σ_m - Σ φ_i^m (Z_t-i-μ_m-i)/σ_m-i`
(mais o termo anual no PAR(p)-A).

## 6. Correlação espacial e matriz de carga

M18 §4.3.2; L-CORR; L-RUID:

- usa-se a correlação espacial **das vazões** (incrementais) em vez da dos
  resíduos (M18 §4.3.2), anual ou mensal conforme o `DADGER` (U19 §4.5
  reg. 13);
- `W_t = D b_t`, com `D = A √V A'` por decomposição espectral pelo método de
  Jacobi (M18 eq. 4.17–4.18 e ref. [16], Numerical Recipes);
- tratamento de autovalores negativos ou nulos da matriz amostral (que
  aparecem quando há mais séries do que anos) não está escrito
  **[lacuna L4]**;
- quais séries entram na matriz (por exemplo, sem séries de variância nula)
  não está escrito **[lacuna L4]**.

## 7. Tendência hidrológica

- A geração do DECOMP é condicionada à tendência hidrológica: os últimos
  valores observados (M18 §4.3; L-COND).
- Meses anteriores ao inicial: histórico atualizado (U19 §4.7).
- Mês inicial: média das semanas do `PREVS` ponderada pelos dias do mês na
  primeira e na última semana (U19 §4.7). O detalhe do calendário (dias de
  cada mês, ano bissexto) não está escrito **[lacuna L5]**.

## 8. Núcleo estocástico (amostragem seletiva)

- Agregação nos vetores de **ruídos normais independentes**, opção `6` do
  `DADGER` (U19 §4.5 reg. 10; R3383 §2.1).
- Representante = **centroide** do grupo, válido só para agregação nos
  ruídos (U19 §4.5 reg. 15; R3383 §2.1).
- Amostra original recomendada de **50 mil objetos** (R3383 cap. 5 e
  conclusões).
- K-means não hierárquico; centros iniciais são objetos do conjunto
  sorteados (M18 §5.1.4); algoritmo de Hartigan & Wong (R3383 ref. [17];
  `fontes/algoritmos/as136.f`).
- Variáveis padronizadas antes da agregação (M18 §5.1.1). Para ruídos que já
  são normais padrão independentes, a distância de Mahalanobis do M18
  §5.1.3 coincide com a euclidiana.
- Probabilidade do grupo `P_k = NO_k / N` (M18 eq. 5.9).
- **Fator de compensação** `FC = (Σ_{i=1..N_UHE} 1/σ_i)/N_UHE`, aplicado aos
  vetores agregados (R3383 eq. 2.2). Como `σ_i` é calculado (ponderado ou
  não pelas probabilidades) não está escrito **[lacuna L7]**.
- Agregação uma vez por período, repetida nos ramos (R3383 Figura 2.5).
- Versão 11: a semente dos ruídos é associada ao número do posto da UHE
  (R3031; U11).
- Gerador pseudoaleatório, semente e forma de sortear os centros iniciais:
  não escritos **[lacuna L6]**.
- Número de grupos = aberturas do período estocástico, dado do `DADGER`
  (U19 §4.5 reg. 9).

## 9. Lognormal de três parâmetros e recorrência

L-LN3 eq. 18–27; M18 §4.3.1:

- limite inferior `M_t` "pode ser igual a zero, ou pode ser um valor
  estimado com base na distribuição" **[lacuna L8]**;
- deslocamento `Δ_t = -M_t/σ_m - μ_m/σ_m - Σ φ (Z_t-i-μ)/σ` (L-LN3 eq. 21);
- `θ = 1 + σ_a²/(μ_a - Δ_t)²`, `σ_ξ² = ln θ`,
  `μ_ξ = ½ ln(σ_a²/(θ² - θ))`, `a_t = e^{ξ_t} + Δ_t`, `ξ_t = σ_ξ b_t + μ_ξ`
  (L-LN3 eq. 22–27; M18 eq. 4.11–4.15);
- `μ_a`, `σ_a` são os momentos dos resíduos históricos (L-LN3);
- ordem: ruído independente → matriz de carga → lognormal (L-RUID);
- recorrência (M18 eq. 4.9a): `Z_t = μ_m + Σ φ_i σ_m (Z_t-i - μ_m-i)/σ_m-i + σ_m a_t`,
  com o termo anual no PAR(p)-A.

## 10. Postos laterais, satélites e defasagem

M18 §4.3.3; L-VIAG; L-TOT:

- ruído do posto lateral condicionado aos principais:
  `W1 = Σ12 Σ22^-1 W2 + E b1`, `EE' = 1 - Σ12 Σ22^-1 Σ12'`, com correlações
  anuais históricas (M18 eq. 4.19–4.20);
- principal: o conjunto é o próprio posto total; satélite: principais
  imediatamente a montante e o principal imediatamente a jusante;
- totais: (i) incremental + totais de montante, ou (ii) lateral + montante
  defasado `ZT(t) = β Σ ZT_mont(t-1) + (1-β) Σ ZT_mont(t) + Z_lat(t)`,
  `β = ndias/ndmes` (M18 eq. 4.21).

## 11. Postos artificiais

M18 §4.3.4 (Figura 4.4); L-ART; U19 §3.10, §4.5, §4.11:

1. gerar incrementais dos principais;
2. totalizar os principais;
3. calcular totais dos satélites;
4. calcular incrementais de todas as usinas (grava `VAZOEST`, `VAZOESI`);
5. calcular totais dos artificiais pelas regras;
6. calcular incrementais considerando os artificiais (grava `VAZOESTA`,
   `VAZOESIA`).

Precisão numérica das regras e arredondamentos intermediários não estão
escritos **[lacuna L9]**.

## 12. Saídas

**Arquivos de séries em árvore** (U19 §5.3.1.2, §5.3.2): acesso direto não
formatado, `RECL = NPOS*8`, um registro por série e período, valores de todas
as usinas na ordem do arquivo de configuração. `VAZOESTA.OUT` e
`VAZOESIA.OUT` têm o mesmo formato com os artificiais.

**`VAZOES.XXX`** (U19 §5.3.4): acesso direto, quatro partes:

| Registro | Conteúdo |
| --- | --- |
| 1 | total de postos considerados; número de estágios; aberturas em cada estágio |
| 2 | códigos das usinas hidráulicas |
| 3 | semanas completas; dias excluídos do estágio seguinte; mês inicial; ano inicial; número de postos; semanas observadas; versão do GEVAZP |
| 4 (NREG registros) | probabilidades dos nós da árvore |
| 5… | incrementais semanais previstas |
| 6… | incrementais mensais geradas |
| 7… | incrementais semanais previstas considerando artificiais |
| 8… | incrementais mensais calculadas considerando artificiais |
| 9 | incrementais mensais observadas |
| 10 | incrementais semanais observadas |

`NREG` = nós da árvore / número de postos, arredondado para cima. O espelho
em texto é `VAZDCP.REL`. Tipos de dado, ordem das usinas em cada registro e
arredondamento não estão escritos; são inferíveis dos arquivos públicos
**[lacuna L10]**.

**`PROBVAZ.DAT`** (U19 §5.4): acesso direto, `RECL = NPOS*4`, probabilidades
dos nós na ordem esquerda→direita e cima→baixo, gravadas pelo laço transcrito
no manual.
