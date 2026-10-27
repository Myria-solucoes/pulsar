# Gravação de `VAZOES.RVx` e `PROBVAZ.DAT` (frente F7, degrau T9)

Código: `pulsar.empacotamento`. Testes: `tests/test_t9_empacotamento.py`.
Proveniência: F7-VZ-01..12, F7-PB-01..02. Layout lido pela F2 em
[layout-VAZOES.RVx.md](layout-VAZOES.RVx.md) e
[layout-PROBVAZ.DAT.md](layout-PROBVAZ.DAT.md).

## Fluxo

```text
Configuracao (F1) ─┐
& VAZOES (DADGER) ─┤
GEVAZP.OUT ────────┤
vazoesia.out ──────┼─ montar_arvore ─> ArvoreVazoes ─> serializar_vazoes_rvx ─> bytes
PROBVAZ (folhas) ──┤
blocos 5/7/9/10 ───┘   (RegistrosDeterministicos, da F5)

contagens/N ─> probabilidades_de_contagens ─> serializar_probvaz ─> bytes
```

`ArvoreVazoes` é o conteúdo do arquivo já tipado, campo a campo; o
serializador só checa formas e tipos e grava. Nenhum módulo do pacote lê um
`VAZOES.RVx` ou o `VAZDCP.REL` (teste estático e de importação).

## De onde vem cada campo

| Registro | Campo | Origem | Proveniência |
| --- | --- | --- | --- |
| 1 | nº de usinas, nº NW | configuração base, status `NW` | F7-VZ-06 |
| 1 | NEST, aberturas | semanas não observadas + estágio estocástico do `& VAZOES` | F7-VZ-02 |
| 1 | NPOS | parâmetro `npos` | F7-VZ-02b |
| 2 | códigos | `Configuracao.ordem_vazoes_rv()` | F7-VZ-06, P-CFG-16 |
| 3 | semanas previstas, dias excluídos, mês, semanas observadas | `& VAZOES` | F7-VZ-02, F7-VZ-02b, F7-VZ-11 |
| 3 | ano | `& VAZOES` reg. 4; em branco, reg. 6 | F7-VZ-12 |
| 3 | nº de postos | `Deck.n_postos` | F7-VZ-02b |
| 3 | versão | `OpcoesEmpacotamento.versao` (`"11.0.2"`) | F7-VZ-03 |
| 3 | bytes 29-40 | `OpcoesEmpacotamento.cauda_registro3` | F7-VZ-04 |
| 4.. | probabilidades | 1.0 por semana + folhas | F7-VZ-09 |
| 6, 8 | gerados | `NINT` do `GEVAZP.OUT`/`vazoesia.out`, coluna posto / ENA | F7-VZ-05, F7-VZ-07, F7-VZ-08 |
| 5, 7, 9, 10 | determinísticos | F5 (T7); no T9, transplante do `VAZDCP.REL` | F7-VZ-10 |

## Resultado (T9)

| Deck | Revisão | Registros | Palavras iguais |
| --- | --- | --- | --- |
| 202609 | RV1 | 542 | 173 440 / 173 440 |
| 202610 | RV0 | 483 | 154 560 / 154 560 |
| 202609 | RV0 | registros 1-3 | iguais; não há `GEVAZP.OUT` desta revisão no pacote |

O que cada parte da igualdade prova:

- registros 1-4: montados da configuração, do `& VAZOES`, da versão e das
  folhas do `PROBVAZ.DAT`; conteúdo e serialização verificados;
- blocos 6 e 8: a partir do `GEVAZP.OUT`/`vazoesia.out` oficiais
  (arredondamento e colunas verificados);
- blocos 5, 7, 9 e 10: transplantados do `VAZDCP.REL`, o espelho em texto
  do próprio arquivo de destino. Aqui a igualdade prova só a serialização e a
  posição nas colunas, não o conteúdo, que depende do T7 da F5.

`PROBVAZ.DAT` igual byte a byte nos dois pacotes, a partir das contagens
inteiras (`k/50000`).

## Em aberto

- Blocos 5, 7, 9 e 10 ainda vêm de transplante; a igualdade deles depende do
  T7 da F5. A tabela "PREVISOES SEMANAIS" do `GEVAZP.REL` não cobre todas as
  colunas (faltam, por exemplo, o posto lateral 168 e colunas de postos
  artificiais), e o bloco 9 só é reproduzível pelo `VAZDCP.REL`.
- Árvores com mais de um estágio estocástico ou com mais de uma abertura
  num estágio semanal: sem exemplo público; o gravador recusa.
- Significado dos bytes 29-40 do registro 3, fórmula geral da versão, regra
  de empate do arredondamento e colisão de colunas com valores não nulos
  (todas ESCOLHA parametrizável, lacuna L10).
- Campos do `& VAZOES` em branco: semanas e dias excluídos gravam 0 ou são
  recusados (`campo_em_branco`, F7-VZ-11). Na coleção de decks do ONS, 230 DADGER de
  2012-2016 têm as semanas observadas em branco; o 0 gravado não é
  conferível porque os `vazoes.rvN` da época têm outro layout no registro 3.
  O ano inicial em branco usa o reg. 6 (F7-VZ-12), conferido em 250 decks
  DECOMP publicados.
- Os 12 bytes de cauda do registro 3 devem ser reconferidos quando houver
  pacote de outro mês ou outra versão; se mudarem, o padrão de F7-VZ-04
  precisa ser revisto.
- As contagens do teste do `PROBVAZ.DAT` saem do próprio arquivo oficial; o
  teste fixa a precisão (F7-PB-02), não as contagens (papel do T10).
- Se os 11 meses observados dependem da ordem máxima: o gravador grava
  quantos meses receber.
