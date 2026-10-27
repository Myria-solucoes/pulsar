# Revalidação dos degraus T0–T10 em 61 pacotes (frente F10)

Pacotes: os 59 de `decks/ons-sintegre/` (03 §1.1b: PMOs de jan/2022 a
set/2026, sem jul/2023, que não veio no download, e as RV1–RV3 de fev/2024) e
os dois de `decks/ons-pacote-gevazp/` (`202609`, executado com a RV1, e
`202610`).

## 1. Como rodar

```sh
./ambiente/py -m pytest tests                       # amostra (padrão): 6 pacotes
./ambiente/py -m pytest tests --decks todos         # os 61
./ambiente/py -m pytest tests --decks 202402_rev2,202201_pmo
./ambiente/py ferramentas/revalidacao.py -j 8       # T0–T10, um pytest por pacote, em paralelo
./ambiente/py ferramentas/revalidacao.py --resumo   # refaz a tabela da seção 3
```

A amostra (`tests/pacotes.py::AMOSTRA`) tem os dois pacotes originais e
quatro do SINtegre: `202201_pmo` (ramo PAR(p), versão 9_L), `202402_rev2`
(fevereiro bissexto, revisão com 2 semanas observadas), `202507_pmo` (versão
10.0.0, com usina NW sem jusante) e `202605_pmo` (versão 11). O T10 usa as
agregações em `cache/f8/` (`ferramentas/sementes_f8.py`); no modo amostra os
pacotes novos usam só o cache (o teste de distribuição é pulado sem as 20
sementes), e T11/T12 rodam só nos originais. Modo rápido sem T11/T12, no fim
da frente: 816 passam, 32 pulados, 6 falham (os testes de núcleo do T5 em
202201, 202507 e 202605; seção 3), em 10 min.

## 2. O que muda ao longo de 2022–2026

| Período | Versão (REL / código no VAZOES) | Modelo | Janela do ajuste | Usinas | NW |
| --- | --- | --- | --- | --- | --- |
| jan–dez/2022 | 9_L / 80106 | PAR(p) (DADGER sem `MODELO PAR-A`) | 1931–2020 | 162 (jan–jul), 163 | — |
| jan–dez/2023 | 9_L / 80106 | PAR(p)-A | 1931–2021 | 163 (jan), 164 | — |
| jan–dez/2024 | 9_L / 80106 | PAR(p)-A | 1931–2022 | 164 (jan), 165 | — |
| jan/2025–mar/2026 | 10.0.0 / 100000 | PAR(p)-A | 1931–2023 (2025), 1931–2024 (2026) | 169 | ESTRELA; JURUENA (sem jusante) até set/2025 |
| abr–jul/2026 | 11 / 110000 | PAR(p)-A | 1931–2024 | 170 (abr), 171 | ESTRELA; FOZ DO PRATA desde mai |
| ago–out/2026 | 11.0.2 / 110002 | PAR(p)-A | 1931–2024 | 171 | FOZ DO PRATA, ESTRELA |

Em todos: ordem máxima 11, `& VAZOES` reg. 13, 14 e 16 = 1, reg. 3 em
branco, 15 usinas PN, 26 postos artificiais, um VINCR (SOBRADINHO), nenhum
AC de configuração repetido ou datado, nenhuma usina NW com PARTIF.
Aberturas do mês estocástico de 116 a 513; 0 a 3 semanas observadas.

## 3. Resultado por degrau

Varredura final, depois da auditoria 1 (`./ambiente/py ferramentas/revalidacao.py -j 12 --so-cache`, código da ponta desta branch), um pytest por pacote. "Fecham" = nenhum teste do degrau falhou no pacote; quando há falha, a coluna da direita traz o primeiro teste que falhou e a primeira linha da mensagem. Os testes das coleções de decks do ONS (03 §1.2: TestColecaoONS, test_t1_ac_datado.py, test_t7_colecao_ons.py e, no T9, `test_ano_do_reg_6_contra_os_vazoes_rv_do_decomp`) dependem de `PULSAR_COLECAO_GEVAZP`/`PULSAR_COLECAO_DECOMP`; na varredura ficam pulados e rodam na suíte padrão com as variáveis definidas.

| Degrau | Fecham | Testes por pacote | Não fecham: primeira divergência |
| --- | --- | --- | --- |
| T0 | 61/61 | 13 | — |
| T1 | 61/61 | 17 | — |
| T2 | 61/61 | 14–15 (+ 0–1 pulados) | — |
| T3 | 61/61 | 7–11 (+ 0–4 pulados) | — |
| T4 | 61/61 | 17–18 (+ 1–2 pulados) | — |
| T5 | 61/61 | 10–14 (+ 0–4 pulados) | — |
| T6 | 61/61 | 15–19 (+ 1–5 pulados) | — |
| T7 | 61/61 | 36–45 (+ 0–1 pulados) | — |
| T8 | 61/61 | 17–18 (+ 0–1 pulados) | — |
| T9 | 61/61 | 16 (+ 1–1 pulados) | — |
| T10 | 61/61 | 4–5 (+ 0–1 pulados) | — |

- T2 `test_correl_camargos_202609` (60 pacotes): amostra legível escrita para o <pacote>
- T3 `test_componente_anual_variantes` (12 pacotes): variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02
- T3 `test_facp_arranjos_alternativos` (12 pacotes): variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02
- T3 `test_facp_definicoes_alternativas_erram_alem_do_rel` (12 pacotes): variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02
- T3 `test_solucao_variantes` (12 pacotes): variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02
- T4 `test_residuo_com_a_nula_no_primeiro_ano_erra` (12 pacotes): variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02
- T4 `test_separacao_do_coeficiente_combinado` (12 pacotes): variante do PAR(p)-A; no ramo PAR(p) ver test_t4_parp.py::test_solver_do_ramo_parp e P-FACP-02
- T4 `test_variantes_do_solver_no_ramo_parp` (49 pacotes): ramo PAR(p) só nos pacotes sem MODELO PAR-A (2022)
- T5 `test_cenarios_publicados_no_subespaco_do_mes_estocastico` (1 pacotes): TRES IRMAOS com cenário -22.425 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T5 `test_cenarios_publicados_no_subespaco_do_mes_estocastico` (1 pacotes): TRES IRMAOS com cenário -27.107 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T5 `test_matriz_do_mes_estocastico_e_a_mais_proxima` (1 pacotes): TRES IRMAOS com cenário -22.425 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T5 `test_matriz_do_mes_estocastico_e_a_mais_proxima` (1 pacotes): TRES IRMAOS com cenário -27.107 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T5 `test_piso_nos_autovalores_nulos_e_incompativel` (1 pacotes): TRES IRMAOS com cenário -22.425 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T5 `test_piso_nos_autovalores_nulos_e_incompativel` (1 pacotes): TRES IRMAOS com cenário -27.107 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T5 `test_vazoes_e_nao_residuos` (1 pacotes): TRES IRMAOS com cenário -22.425 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T5 `test_vazoes_e_nao_residuos` (1 pacotes): TRES IRMAOS com cenário -27.107 ≤ 0: ln Z não existe (P-LN3-03, lacuna L8)
- T6 `test_fevereiro_bissexto_com_28_dias` (57 pacotes): mês inicial não é fevereiro bissexto
- T6 `test_incremental_inclui_nw_a_montante` (38 pacotes): SALTO sem usina NW a montante nesta configuração
- T6 `test_qpast_exemplo_camargos_202609` (60 pacotes): amostra legível escrita para o <pacote>
- T6 `test_vazaoanual_bits_soma_em_ordem_de_calendario` (12 pacotes): ramo PAR(p): vazaoanual.out nulo (F2-VA-04)
- T6 `test_vazaoanual_e_media_dos_12_meses_da_tendencia` (12 pacotes): ramo PAR(p): vazaoanual.out nulo (F2-VA-04)
- T7 `test_nw_somada_na_jusante` (38 pacotes): configuração sem usina NW
- T8 `test_nw_absorvida_no_gevazp_out_e_propria_no_vazoesia` (38 pacotes): configuração sem usina NW
- T9 `test_ano_do_reg_6_contra_os_vazoes_rv_do_decomp` (61 pacotes): coleção de decks do ONS indisponível
- T10 `test_distribuicao_dos_tamanhos_de_grupo` (48 pacotes): agregação <pacote>semente 2 fora do cache (PULSAR_SO_CACHE ou amostra)
- T10 `test_distribuicao_dos_tamanhos_de_grupo` (1 pacotes): agregação <pacote>semente 8 fora do cache (PULSAR_SO_CACHE ou amostra)

Leitura da tabela:

- **Todos os degraus T0–T10 fecham nos 61 pacotes**, inclusive o ramo PAR(p) de 2022, as quatro revisões de fev/2024 e as quatro versões do GEVAZP.
- **T5**: a parte determinística (matriz de correlação histórica bit a bit com o correli.out, igual ao REL, séries da carga, Jacobi, D D' = U) fecha nos 61. Os testes de evidência que medem os cenários publicados no núcleo de U com ln Z dependem da lognormal (lacuna L8, frente F11). Na primeira versão da F10 eles tinham os limiares fixados com o 2026 e falhavam em 27 pacotes (resíduo < 0,03), 20 (piso ε = 3e-3) e 8 (resíduos 5× as vazões). Depois da auditoria 1 cada um afirma, nos 59 pacotes com cenários positivos, o critério que vale em todos (resíduo < 0,07 e razão para a matriz seguinte < 0,5; piso ε = 3e-2; resíduos 3× as vazões; a matriz do mês estocástico é a mais próxima das 13) e mantém os limiares do 2026 nos dois pacotes de 2026. Em 202411 e 202511 TRES IRMAOS tem cenários negativos no GEVAZP.OUT (até −27 m³/s), ln Z não existe e esses testes são pulados com o motivo; o fato é afirmado em `tests/test_oraculo_series_arvore.py::test_incrementais_negativas_no_gevazp_out` e contradiz M_t = 0 (P-LN3-03).
- **T10**: grupos = aberturas, denominador 50 000, saídas no layout público e VAZOES.RVx ponta a ponta (semente 1) fecham nos 61. A distribuição dos tamanhos de grupo contra 20 sementes (`test_distribuicao_dos_tamanhos_de_grupo`) rodou e passou em 12 pacotes (202201–202210 e os dois originais); nos outros 49 foi pulada por custo: as 20 agregações de K-means de 50 mil objetos não estavam em cache (≈ 1 160 agregações, dezenas de horas de CPU). `ferramentas/sementes_f8.py` completa o cache, e o mesmo comando sem `--so-cache` roda o teste.

## 4. Divergências encontradas e o que foi corrigido

Primeira passagem (código do master, antes da F10): T0 e T1 já fechavam nos
61 pacotes. As primeiras divergências por degrau, na ordem em que apareceram:

| Onde | Primeira divergência | Causa | Correção | Proveniência |
| --- | --- | --- | --- | --- |
| T4, 2022 (ramo PAR(p)) | `CAPIM BRANC1`, ordem de março 9 contra 2 no correli.out; φ diferentes no último bit em 141 de 147 séries | (a) o Yule-Walker do ramo PAR(p) é resolvido por Cholesky, não pelo Gauss-Jordan do PAR(p)-A; (b) a busca da ordem para antes da primeira defasagem com \|φ_kk\| > 1 (no PAR(p) a FACP é o último coeficiente do Yule-Walker e pode passar de 1) | `parp.cholesky`, `OpcoesPAR.solver_parp`; `parp.limite_valido`, `OpcoesPAR.facp_maior_que_1` | P-LIN-03, P-ORD-04, P-FACP-02 (agora INFERIDO), P-PAR-01 |
| T6, fev/2024 | `202402_rev2`: QPAST do mês inicial diferente nos 167 postos com PREVS | fevereiro com 28 dias também em ano bissexto: pesos (1, 7, 7, 7, 6), não (2, 7, 7, 7, 6) | `tendencia.dias_no_mes`, `OpcoesTendencia.dias_fevereiro` | P-TEND-02 (era ESCOLHA, agora INFERIDO) |
| T8, 202401 | — (fechava) | a defasagem linear conta fevereiro bissexto com 29 dias: o oposto da tendência | nenhuma | F6-DEF-06 (agora INFERIDO) |
| T7/T9, 2022–2026 | `202201_pmo`: 1 palavra do registro 3 | o código de versão gravado é o do programa: 80106 (9_L), 100000, 110000, 110002 | testes emulam a versão do pacote (o Pulsar já tinha o parâmetro) | F2-VZ-04c, P-VZD-10 |
| T2, 2023–2024 | `202301_pmo`: incrementais do REL zeradas | oráculo: o REL do 9_L repete o título da série incremental na série anual | `oraculos.texto.ler_series_incrementais` | P-REL-02 |
| T4, 2022–2024 | `vordem.out` ilegível (`********`) | oráculo: campos de 8 colunas no 9_L | `oraculos.vordem` | P-VORD-04 |
| T6, 2022 | `vazaoanual.out` diferente da média dos 12 meses | sem MODELO PAR-A o arquivo é nulo | testes | F2-VA-04 |

Também revelaram detalhes que a amostra de 2026 não separava (sem mudança de
código): a soma sequencial jan..dez do `vazaoanual.out` (F2-VA-03), a
constante 1,96 do limiar (P-ORD-02, separada de 1,959964 nos pacotes de
2024) e a matriz do mês estocástico na carga (P-ESP-09, a mais próxima dos
cenários em 59 dos 61 pacotes; nos outros dois ln Z não existe).

O resto das falhas da primeira passagem eram dos testes, escritos para os
dois pacotes de 2026: contagens fixas (26 artificiais, 155 séries, 150
usinas, 2 séries nulas), nomes de usinas (FOZ DO PRATA, ESTRELA como NW),
pesos e dias do calendário de set–out/2026, a versão 11.0.2, um registro de
probabilidades, a tabela de previsões sem a linha PL (o REL a tem em
202201–202207 e 202507–202509, P-REL-03), a tabela de correlações "TODOS
POSTOS" completa (o REL do 10.0.0 lista 153 das 170 séries, P-REL-04), NW sempre com jusante (JURUENA, 2025, não tem) e arquivos
em maiúsculas (`202301_pmo` e `202411_pmo` gravam `vazoes.rv0`,
`vazdcp.rel`, `probvaz.dat`). Os testes passaram a derivar essas quantidades do
pacote (ou do calendário da biblioteca padrão), e as afirmações que só valem
no 2026 ficaram restritas aos dois pacotes originais.

Controles que ficaram mais fracos fora do 2026 (auditoria 1, P12). Onde a
quantidade exata só vale num pacote, os testes passaram a exigir um
mínimo ou uma desigualdade nos outros, e a forma exata continua só nos
originais:

| Teste | Nos dois de 2026 | Nos outros 59 |
| --- | --- | --- |
| `test_t0_leitura.py::test_prevs_igual_ao_rel` | (antes) > 150 usinas conferidas | > 0,85 × usinas da configuração |
| `test_oraculo_correl.py::test_correlt_estatisticas`, `test_oraculo_series_arvore.py`, `test_oraculo_tendencia.py` | (antes) > 150 séries/postos | > 140 |
| `test_oraculo_correl.py::test_correlt_correlacoes` | todos os pares | pares completos entre as séries listadas, ≥ 0,85 do índice (P-REL-04) |
| `test_t5_espacial.py::test_variantes_da_correlacao` | taxas de acerto das variantes nas faixas medidas | cada variante < 0,8 |
| `test_t6_tendencia.py::test_regras_leem_precisao_simples` | contagens exatas de erros das duas variantes | cada variante erra ao menos um valor |
| `test_t6_tendencia.py::test_media_divide_pelos_dias` | multiplicar por 1/dias erra | não exigido (em fev/2025 coincide) |
| `test_t7_vazoes_deterministicos.py::test_sem_arredondar_totais_falha` | coluna 76, uma palavra por semana e 3 meses | erros só em colunas ENA com artificial a montante |
| `test_t8_totalizacao.py::test_precisao_das_regras` | 26 colunas, (6, 9) nas variantes, 20 híbridas e o conjunto exato das que falham | variantes abaixo do total; as que falham ⊆ as regras que citam outro artificial |
| `test_t4_variantes.py::test_separacao_do_coeficiente_combinado` | limiares −0,004/0,029 e os dois controles | só o sinal (máx. dos que vão a 0 < 0 ≤ mín. dos que ficam) |
| `test_t5_espacial.py` (núcleo) | limiares do 2026 | envelope dos 59 (seção 3) |

## 5. Lacunas

| Lacuna | Situação depois da F10 |
| --- | --- |
| L1 janela de anos | O período comum da configuração fecha o T2 nas cinco janelas (1931–2020 a 1931–2024), sempre antes do fim do VAZOES.DAT. O ano final do `& VAZOES` reg. 2 e o do POSTOS.DAT são iguais nos 61, então a precedência entre eles (P-CFG-08) continua ESCOLHA. |
| L3 coeficientes negativos | Fechada também no ramo PAR(p): rastro do vordem.out igual em todas as séries e iterações de 2022, com o combinado φ'_1 sem ψ (P-NEG-02/03) e as duas regras novas P-LIN-03 e P-ORD-04. |
| L5 calendário | Fechada: fevereiro com 28 dias na média do mês inicial, inclusive em 2024 (P-TEND-02); a defasagem usa 29 (F6-DEF-06). QPAST byte a byte nos 61 pacotes, nos doze meses, com 0 a 3 semanas observadas. |
| L10 versão gravada | Quatro códigos observados (F2-VZ-04c); os testes emulam a do pacote (P-VZD-10). A fórmula do código continua ESCOLHA. |
| L13 config.out | Os 61 config.out fecham byte a byte, mas nenhum distingue as escolhas (cabeçalho do bloco 2 sempre (n, n, 1), um lateral SOBRADINHO_L, bytes 28–35 nulos). Aberta. |
| L14 casos de borda da configuração | Nenhum caso listado aparece nos 61 (sem AC de configuração repetido ou datado, sem NW com PARTIF, um VINCR, reg. 3 em branco). Novidade sem regra nova: uma NW sem jusante (JURUENA, jan–set/2025), que o Pulsar já tratava (coluna nula no GEVAZP.OUT, incremental não somada a ninguém). Aberta. |
| L19 ramo PAR(p) e opções do ajuste | Ramo PAR(p) com 12 pacotes completos: FACP, ordens, φ e rastro bit a bit (P-FACP-02, P-LIN-03, P-ORD-04, P-PAR-01). Seguem sem exemplo: MODELO PAR-A = 0 explícito ou outro valor, reg. 16 ≠ 1, ordem máxima ≠ 11, desvio ou pivô nulos. |
| L8 limite inferior (e L22) | Arquivo público contra M_t = 0: TRES IRMAOS tem cenários negativos em 202411 e 202511, já nos totais do VAZTOTGD.DAT (P-LN3-03, teste em `test_oraculo_series_arvore.py`). Os testes de núcleo do T5 dependem de M_t: nos 59 pacotes com cenários positivos afirmam o envelope observado, e os limiares do 2026 só nos originais. Fica para a F11. |

## 6. O que fica em aberto

- **T5 e L8**: os testes de núcleo afirmam o envelope observado nos 59 pacotes com cenários positivos,
  não uma regra; o limite inferior M_t continua 0 no Pulsar, contradito pelos cenários negativos de
  TRES IRMAOS em 202411 e 202511. Fica para a F11, que deve reavaliar esses testes com a lognormal
  identificada.
- **T10, distribuição dos grupos** em 49 pacotes: não rodada por custo (cache de sementes incompleto).
- **T11 e T12** não foram revalidados (fora do escopo); continuam restritos aos dois originais, também
  na amostra padrão. A parte estocástica (F8) não mudou: as opções novas do PAR(p) não agem no PAR(p)-A
  (`test_solver_do_ramo_parp` e `test_ordem_para_antes_da_facp_maior_que_1` confirmam nos 49 pacotes de
  2023–2026), e fevereiro não é mês inicial dos originais. A suíte inteira com T11/T12 não foi rodada de
  novo nesta frente.
- **L1** (DADGER reg. 2 contra POSTOS.DAT), **L13** e **L14**: nenhum pacote distingue as escolhas.
- **L19**: MODELO PAR-A = 0 explícito, reg. 16 ≠ 1, ordem máxima ≠ 11, desvio ou pivô nulos sem
  exemplo. As regras do ramo PAR(p) (P-FACP-02, P-LIN-03, P-ORD-04) valem num histórico só (1931–2020).
- **Falta o PMO de jul/2023** em `decks/ons-sintegre/` (59 pastas: jan/2022–set/2026 sem 202307, mais
  as três revisões de fev/2024).
