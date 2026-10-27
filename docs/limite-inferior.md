# Limite inferior da lognormal e postos derivados (frente F11)

Lacunas L8 (limite inferior `M_t` da lognormal de três parâmetros) e L11
(postos laterais e outros derivados), investigadas nos 61 pacotes
completos (03 §1.1 e §1.1b): 59 do SINtegre/ONS (PMOs de jan/2022 a set/2026,
menos jul/2023, e as revisões 1–3 de fev/2024) e os dois originais
(202609 RV1 e 202610 RV0). Só arquivos publicados nos pacotes; nenhum
executável.

## 1. A restrição estrutural usada

No período estocástico o passado é o mesmo em todas as folhas, então cada
coluna do `GEVAZP.OUT` de uma série da matriz de carga é (M18 eq. 4.9a,
4.11–4.15; L-LN3 eq. 18–27)

```text
Z = σ_m (c + a),   a = exp(σ_ξ W + μ_ξ) + Δ,   Δ = M_t/σ_m − c,
```

com `c`, `σ_m` já reproduzidos pelo Pulsar (P-GER-03/04) e `σ_ξ`, `μ_ξ`
função de `Δ` e dos momentos `μ_a`, `σ_a` do ruído (eq. 22–24). E
`W = D b` com `D = A √V A'` (P-ESP-07/09): como a matriz `U` do mês tem
posto N − 1 = 93 para ~150 séries, cada vetor `W` de uma folha tem de estar
na imagem de `U` — ~56 restrições lineares por folha, ~14 500 por pacote,
para uma incógnita `M_t` por série.

Invertendo a lognormal com `M_t` e momentos candidatos, o resíduo
`√(Σ_k p_k |K'W_k|² / Σ_k p_k |W_k|²)` (K = base do núcleo de U, p = PROBVAZ)
mede o quanto eles explicam os cenários publicados (`tests/apoio_f11.py`).
Com a lognormal da primeira versão da F8 (`M_t = 0`, momentos teóricos) o
resíduo ficava em 0,02–0,17 e era impossível em 202411 e 202511 (cenários
negativos de TRES IRMAOS).

## 2. Identificação

Exploração (scripts fora do repositório, refeitos pelos testes abaixo):

1. Ajuste por mínimos quadrados de um `M_t` livre por série (Levenberg–
   Marquardt), depois de `M_t`, escala e deslocamento livres de cada `W`.
   Em 25 pacotes o resíduo foi a ~1,2e-8 (ruído de float64): `M_t` é
   identificado sem ambiguidade (fixar em outro valor sobe o resíduo de
   2e-14 para 1,5e-2 na função objetivo).
2. Os `M_t` ajustados caíam em três fórmulas do histórico do mês: 3 038 em
   `f · mínimo`, com f ∈ {0,15; 0,35; 0,5; 0,6} conforme a assimetria; 520
   em `μ − 3σ`; 119 em metade da cúbica da eq. 25 nas vazões. A escolha
   entre elas fechou com uma variável cada (separação perfeita: `f · mínimo`
   mais de 3σ abaixo da média → `μ − 3σ`).
3. Com a regra, escala e deslocamento livres levavam todos os 61 pacotes a
   ~1e-8; a escala/deslocamento que sobrava era a dos momentos: com a média
   e o desvio **históricos** dos resíduos do mês (P-RES-02) o resíduo vai a
   ~1e-8 sem parâmetro livre nenhum.

## 3. A regra (P-LN3-09..13)

Com `x` as vazões incrementais históricas do mês estocástico (janela da F3),
`μ`, `σ` (denominador N) e `γ` a média, o desvio e a assimetria delas
(P-EST-01..03):

1. se mais de 15% dos valores de `x` são negativos: `M_t = μ − 3σ`;
2. base = menor valor não negativo de `x` (0 se houver vazão 0);
3. com 2 ≤ γ < 4, se `τ = μ − σ/η(γ)` (η da eq. 25) está em (0, base):
   base = τ;
4. `f = 0,15 / 0,35 / 0,5 / 0,6` para γ < 1 / < 2 / < 4 / ≥ 4;
5. `M_t = max(f · base, μ − 3σ)`.

A lognormal usa `μ_a`, `σ_a` históricos dos resíduos (P-LN3-04) e a eq. 24
com `(μ_a − Δ)²` quando `μ_a − Δ < 0` (P-LN3-06, 16 pacotes).

Contagem nos 61 pacotes (8 999 séries × pacote, `ferramentas/limite_inferior.py`):

| Ramo | Séries × pacote |
| --- | ---: |
| f = 0,15 (γ < 1) | 2 522 |
| f = 0,35 (1 ≤ γ < 2) | 3 369 |
| f = 0,5 (2 ≤ γ < 4) | 1 097 |
| f = 0,5 sobre a cúbica | 338 |
| f = 0,6 (γ ≥ 4) | 274 |
| piso μ − 3σ | 1 397 |
| mais de 15% negativos | 2 |

Limiares, cercados pelas séries em que o ramo decide `M_t`:

| Limiar | Maior valor abaixo | Menor valor acima |
| --- | ---: | ---: |
| γ = 1 | 0,999574 | 1,000064 |
| γ = 2 | 1,999788 | 2,000832 |
| γ = 4 | 3,964403 | 4,000973 |
| fração de negativos 0,15 | 0,144444 (13/90) | 0,150538 (14/93) |

O ramo dos negativos aparece só em TRES IRMAOS, dezembro, em 202411 e
202511 (`M_t` = −71,6 e −71,1 m³/s): é ele que explica os cenários
negativos que a F10 registrou. O limiar de 15% é ESCOLHA dentro do
intervalo; o empate exato nos limiares de γ também (nenhum pacote o tem).

## 4. Testes

`tests/test_oraculo_limite_inferior.py`, nos 61 pacotes (`--decks todos`):

- `test_ruidos_publicados_na_imagem_com_a_regra`: resíduo < 1e-7 (máximo
  1,34e-8); `M_t = 0` ≥ 1e-3 ou impossível; momentos teóricos ≥ 100 vezes;
- `test_cada_ramo_da_regra`: 18 controles (k = 2,9/3,1, sem piso, limiares
  ±0,01, frações ±0,01, faixa da cúbica, limiar de negativos); cada um que
  muda algum `M_t` sobe o resíduo mais de 100 vezes. Pacotes em que cada um
  muda algum `M_t`: piso, frações e cúbica 61; limiar 1 27; limiar 2 15–18;
  cúbica com γ ≥ 4 29; limiar 4,01 1; negativos 14% 3; sem limiar de
  negativos 2;
- `test_base_com_negativos_e_errada`, `test_media_do_ruido_abaixo_do_limite_eq_24_com_quadrado`,
  `test_matriz_do_mes_estocastico_exata` (P-ESP-09: só a matriz do mês
  deixa os W na imagem; as outras 12 ficam acima de 1e-3).

`tests/test_t12_ponta_a_ponta.py::test_transplante_entre_revisoes`: o W do
202609 RV1, reaplicado com o condicionamento do RV0, dá o `VAZOES.RV0`
oficial **byte a byte** (antes, 90,0% das palavras geradas).

## 5. Postos derivados (L11)

`tests/test_oraculo_laterais.py`, nos 61 pacotes:

- **NW e jusantes** (`test_nw_e_jusantes_geradas_como_as_demais`): com as
  incrementais próprias tiradas do `VAZTOTGD.DAT`, as usinas NW e as
  jusantes que as recebem ficam na imagem junto com as demais (< 1e-7): a
  NW é gerada como qualquer série da carga, com o mesmo `M_t`, e só depois
  absorvida na jusante no `GEVAZP.OUT` (F6-INC-02).
- **Lateral** (`test_lateral_condicionado_com_a_correlacao_do_mes`): o W de
  SOBRADINHO_L, comparado com o de SOBRADINHO (tirado da imagem pelas
  outras séries), segue `W_L = ρ_m W_P + E b1` com `ρ_m` a correlação do
  **mês** estocástico (P-LAT-02), não a anual do M18 §4.3.3.1, e:
  - versão 11.0.x (8 pacotes, abr–out/2026): **sem** o ruído próprio,
    `W_L = ρ_m W_P` a menos de 1e-6 (P-LAT-04);
  - versões 8.1.6 e 10.0.0 (53 pacotes): `b1` com desvio 0,91–1,09 e sem
    correlação com `W_P`, um normal padrão independente.

  O padrão do Pulsar segue a versão atual (`ruido_lateral="nenhum"`); a
  forma do M18 fica como `"proprio"`. Se `b1` é componente do vetor
  agregado pelo K-means ou um normal à parte não se separa nos dados
  (P-AGR-07).

## 6. Aceitação estatística (03 §5) antes e depois

RESULTADO_T11

## 7. Em aberto

- Os limiares de empate (γ exatamente 1, 2 ou 4) e a fração de negativos
  entre 14,4% e 15,05%: sem pacote que os separe.
- Série sem valor não negativo no mês: base 0 por escolha.
- Por que o lateral perdeu o ruído próprio na versão 11: nenhuma fonte
  pública registra a mudança.
- Observação exploratória, fora dos testes: 202402 e 202403 têm as mesmas
  probabilidades e o mesmo `b1` do lateral, o que sugere a mesma agregação
  (P-INT-01 entre pacotes), mas as coordenadas de `b` nas imagens dos dois
  meses não fecham num único `b` (resíduo relativo 0,9%). Fica para a L7.
- O resíduo de ~1,2e-8 (e não 1e-15) sugere alguma etapa em precisão
  menor que float64 entre `b` e o `GEVAZP.OUT`; não investigado.
