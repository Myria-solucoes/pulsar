# Layout de `PROBVAZ.DAT` (probabilidades dos nós)

Leitor: `pulsar.oraculos.ler_probvaz`. Testes:
`tests/test_oraculo_vazoes_decomp.py` (`test_probvaz_*`). Proveniência:
F2-PB-01..04.

## O que o U19 diz (§5.4)

```text
OPEN ( UNIT = IOPROB, ACCESS = 'DIRECT', FORM = 'UNFORMATTED',
       RECL = NPOS*4, STATUS = 'UNKNOWN', FILE = 'PROBVAZ.DAT' )
NREGP = NNOT/NPOS
IF (MOD(NNOT,NPOS).GT.0) NREGP = NREGP + 1
...
WRITE(IOPROB,REC=IREG)(PROBLEX(I),I=I1,I2)
```

"onde NNOT é o número de nós existente na árvore. O vetor PROBLEX contém as
probabilidades dos nós já na ordem correta, isto é, da esquerda para direita
e de cima para baixo."

## Confirmação

| Deck | Tamanho | Registros | Valores não nulos |
| --- | --- | --- | --- |
| 202609 (RV1) | 1280 | 1 | 259 |
| 202610 (RV0) | 1280 | 1 | 228 |

- `RECL = NPOS*4` = 1280 bytes confirmado; valores float32 little-endian;
  o resto do registro é zero.
- **Divergência com o U19**: `NNOT` aqui é o número de folhas do estágio
  estocástico (259, 228), e não o total de nós da árvore (263 e 234, que
  incluem os estágios semanais). Os nós semanais (probabilidade 1) só
  aparecem no registro 4 do `VAZOES.RVx`, cujas folhas são iguais em bits às
  do `PROBVAZ.DAT`.
- `PROBVAZ.REL` mostra as mesmas probabilidades com 4 casas, na coluna do
  mês estocástico (os outros meses valem `1.0000`):

```text
 CENARIO,     1,  ...,       9,      10,      11,      12,
     1,  1.0000,  ...,  1.0000,  0.0036,  1.0000,  1.0000,
```

  e o binário tem `0.00364` no primeiro valor.

## Para a F8 (T10)

Todas as probabilidades são `k/50000` com `k` inteiro e `Σk = 50000`, e
50000 é o menor `N` compatível (`test_probvaz_sao_contagens_sobre_50000`),
o que bate com a amostra de 50 mil objetos recomendada em R3383.

## Não identificado

- Ordem e conteúdo com mais de um estágio estocástico.
