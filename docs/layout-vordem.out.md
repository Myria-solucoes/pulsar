# Layout de `vordem.out` (rastro do tratamento de coeficientes negativos)

Leitor: `pulsar.oraculos.ler_vordem`. Testes: `tests/test_t4_parp.py`
(`test_rastro_igual_ao_vordem`, `test_limite_da_busca_igual_ao_vordem`).
Proveniência: P-VORD-01..03 e P-NEG-01..05.

O U19 não descreve o arquivo. É texto, gravado no pacote ao lado do
`GEVAZP.REL`. Todo o significado abaixo foi inferido dos pacotes públicos
de 2026 (202609, 202610), que estão no ramo PAR(p)-A.

## Estrutura

Para cada série com modelo (as 155 do índice do `correli.out`) e mais as
duas de incremental nula (ITUTINGA e PARANAPANEMA, um bloco só, tudo zero),
na ordem da configuração, um bloco por iteração:

```text
USINA: CAMARGOS     ->  8  3  7  8  8  2 10  2  4  5  2  2     ordens identificadas
MES: JAN -> AR( 8)                                             ordem usada
MES: JAN -> AR(11)                                             limite da busca
COEFS:      0.77205     -0.04030 ...                           φ'_1..φ'_p
PSI:  0.03363                                                  ψ'
    FUNC. DE DEZ :  0.77485                                    contribuições
    FUNC. DE NOV :  0.37005
    ...
(linha com um espaço)
MES: FEV -> ...
```

| Campo | Significado | Evidência |
| --- | --- | --- |
| ordens identificadas | maior lag com FACP significativa até o limite; mínimo 1 | ordem inicial de CAMARGOS (8 3 7 8 8 2 10 2 4 5 2 2) = maior lag com \|FACP\| > 1,96/√94 na FACP do REL; JAGUARA FEV: nenhum lag significativo e a ordem é 1 |
| ordem usada | igual à identificada, salvo ordem 1 com coeficiente combinado negativo, que vira 0 | JAGUARA FEV: cabeçalho 1, `AR( 0)`, `COEFS:` vazio, `PSI: 0.00000`; o `correli.out` grava 0 |
| limite da busca | 11 na 1ª iteração; nos meses reduzidos, a ordem identificada anterior menos 1; nos demais, a ordem identificada se ≥ 2 (senão não muda) | CAMARGOS: JAN 8 → limite 7 → ordem 1 |
| `COEFS:` | φ'_i = φ_i·σ_m/σ_{m-i} (unidades de vazão) | CAMARGOS MAI: 0,804·37,58/56,99 = 0,53025 |
| `PSI:` | ψ' = ψ·σ_m/σ^A_m, σ^A do mês de t | CAMARGOS MAI: -0,375·37,58/32,17 = -0,43781 |
| `FUNC. DE <mês>` | coeficiente de Z_{t-j} depois de substituir Z_{t-1}..Z_{t-j+1} pelos modelos dos seus meses (M18 §6.3), com o termo anual somado como ψ'/12 em cada um dos 12 lags; impresso para j = 1..max(p,1) e interrompido na primeira negativa | CAMARGOS MAI 2ª iteração: 0,53025 - 0,43781/12 = 0,49376; DE MAR: 0,05362 - 0,03648 + 0,49376·(0,54985 - 1,12355/12) = 0,24240 |

O último bloco de cada usina é o modelo final: as ordens usadas são as do
`correli.out` e do "ORDEM FINAL" do `GEVAZP.REL`. Um mês entra na iteração
seguinte com ordem reduzida exatamente quando alguma linha `FUNC.` dele é
negativa.

Precisão: 5 casas decimais em `COEFS`, `PSI` e `FUNC`.

## Não identificado

- Por que o limite impresso dos meses de ordem 1 que não foram reduzidos
  continua 11. Não afeta o resultado: o limite só é usado quando o mês é
  reduzido, e então vale a ordem identificada menos 1.
- O arquivo não traz as contribuições além do lag p, nem as do termo anual
  além dos 12 meses; o teste mostra que só os lags 1..p decidem.
