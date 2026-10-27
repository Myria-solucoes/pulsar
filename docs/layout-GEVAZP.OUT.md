# Layout de `GEVAZP.OUT` (incrementais geradas)

Leitor: `pulsar.oraculos.ler_incrementais_geradas`. Testes:
`tests/test_oraculo_series_arvore.py`. Proveniência: F2-ARV-01..03.

## Layout

| Item | Valor | Tipo |
| --- | --- | --- |
| Acesso | direto, não formatado, sem marcadores de registro | DOC (U19 §5.3.1.2) |
| RECL | `NPOS*8` = 2560 bytes (`NPOS` = 320) | DOC (U19 §5.3.1.2: `RECL=ZPOS*8`) |
| Registros | um por série gerada (cenário) do período estocástico | DOC + INFERIDO |
| Conteúdo | `NPOS` float64 little-endian | INFERIDO |
| Coluna | `NINT-1`, ordem da tabela "CONFIGURACAO DAS USINAS HIDRELETRICAS" do `GEVAZP.REL`; colunas `NINT > nº de usinas` valem 0 | INFERIDO |

U19 §5.3.1.2 descreve o laço:

```text
DO ISEG = 1, NSEG
   JREC = JREC + 1
   WRITE(IOENGS,REC=JREC) (EG(IPEA,ISEG,ISIS), ISIS = 1, NSIS )
ENDDO
```

"Assim, em cada registro, são gravados os valores gerados para todas as
usinas especificadas no arquivo da configuração (item 4), para uma
determinada série e um determinado período."

## Confirmação nos arquivos reais

| Deck | Tamanho | Registros | Aberturas do estágio mensal (`GEVAZP.REL`, "NUMERO DE SEGMENTOS") |
| --- | --- | --- | --- |
| 202609 (RV1) | 663 040 | 259 | 259 |
| 202610 (RV0) | 583 680 | 228 | 228 |

Só o mês estocástico está gravado (um registro por cenário, nenhum registro
para os meses determinísticos). O `VAZOESI.CSV` mostra os 12 meses do ano por
cenário; os meses anteriores repetem a tendência e o mês seguinte ao
estocástico vale 0. Exemplo (202609, cenário 1, CAMARGOS):

```text
VAZOESI.CSV: 1,    1, CAMARGOS    ,    1,   117.00, ..., 44.90,    51.68,     0.00,     0.00,
GEVAZP.OUT:  registro 1, coluna 0 = 51.676767...
```

Todos os 172 × 259 (202609) e 172 × 228 (202610) valores arredondados a 2
casas são iguais ao CSV (teste `test_igual_ao_csv_em_todos_os_valores`).

## Observações para outras frentes

- Usinas NW (`FOZ DO PRATA`, NINT 68; `ESTRELA`, NINT 145) têm coluna nula; a
  incremental delas aparece somada na usina de jusante (`MONTE CLARO`,
  `SALTO`). Evidência: as médias geradas do `correli.out` (que guardam a
  série antes dessa soma) somam exatamente a média ponderada da coluna de
  jusante (`test_oraculo_relacoes.py::test_nw_somada_na_jusante`).
- Usinas PN e usinas com incremental nula têm coluna nula; `TRAICAO` (PN) é
  exceção, com valores não nulos, todos exatos em float32.
- `SOBRADINHO` (NINT 114) difere da média do `correli.out` por causa do posto
  lateral `SOBRADINHO_L` (NINT 172).

## Observação da frente F6

O conteúdo é a incremental recalculada dos totais do `VAZTOTGD.DAT`
(`total − T(m1) − T(m2) − …`, montantes na ordem da configuração, sem
subtrair as NW), não a incremental que entrou na totalização (F6-INC-01;
[totalizacao-e-artificiais.md](totalizacao-e-artificiais.md)). Os valores
não nulos de `TRAICAO` são o resíduo de arredondamento dessa subtração.

## Não identificado

- Como o arquivo fica quando há mais de um período estocástico (só vimos
  árvores com um mês estocástico). U19 indica `JREC` contínuo entre períodos.
- Regra de empate do arredondamento posterior (ver `layout-VAZOES.RVx.md`).
