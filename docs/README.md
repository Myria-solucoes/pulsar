# Oráculos binários decodificados (frente F2)

| Arquivo | Leitor (`pulsar.oraculos`) | Layout | Degrau |
| --- | --- | --- | --- |
| `correli.out` | `ler_correli` | [layout-correli.out.md](layout-correli.out.md) | T2-T4 (média, desvio, FAC, FACP, ordens, φ), T5 (correlação histórica) |
| `correlt.out` | `ler_correlt` | [layout-correlt.out.md](layout-correlt.out.md) | T2-T3 e T5 nas totais; T8 (média/desvio gerados) |
| `QPAST.DAT` | `ler_qpast` | [layout-QPAST.DAT.md](layout-QPAST.DAT.md) | T6 |
| `vazaoanual.out` | `ler_media_anual_anterior` | [layout-vazaoanual.out.md](layout-vazaoanual.out.md) | T4/T6 (`A_{t-1}` do PAR(p)-A) |
| `GEVAZP.OUT` | `ler_incrementais_geradas` | [layout-GEVAZP.OUT.md](layout-GEVAZP.OUT.md) | T8/T9 (transplante), T11 |
| `VAZTOTGD.DAT` | `ler_totais_gerados` | [layout-VAZTOTGD.DAT.md](layout-VAZTOTGD.DAT.md) | T8 |
| `vazoesia.out` | `ler_incrementais_artificiais` | [layout-vazoesia.out.md](layout-vazoesia.out.md) | T8/T9 |
| `vazoesta.out` | `ler_totais_artificiais` | [layout-vazoesta.out.md](layout-vazoesta.out.md) | T8 |
| `PROBVAZ.DAT` | `ler_probvaz` | [layout-PROBVAZ.DAT.md](layout-PROBVAZ.DAT.md) | T9, T10 |
| `VAZOES.RVx` | `ler_vazoes_decomp` | [layout-VAZOES.RVx.md](layout-VAZOES.RVx.md) | T7, T9 |
| `vordem.out` (texto) | `ler_vordem` | [layout-vordem.out.md](layout-vordem.out.md) | T4 (rastro do tratamento de negativos; frente F3) |

Leitores de texto (oráculos dos binários) em `pulsar.oraculos.texto`:
configuração, previsões, tendência, seções por série (inclusive a série
"MEDIA ULTIMOS 12 MESES" e, com `ler_residuos`, a "SERIE DE RUIDOS" e seus
momentos), correlações espaciais e estatísticas geradas do `GEVAZP.REL`; `VAZDCP.REL`;
`PROBVAZ.REL`; `VAZOES*.CSV`.

Testes: `./ambiente/py -m pytest tests` (ver `ambiente/README.md`).

Para escrever um gravador (F7) não use o leitor ao contrário sem ler as
seções "Não identificado" de cada layout: há bytes não explicados no
registro 3 do `VAZOES.RVx` e campos não identificados no `correl*.out`.

Totalização e artificiais (frente F6): `pulsar.totalizacao` calcula e
grava `VAZTOTGD.DAT`, `GEVAZP.OUT`, `vazoesta.out` e `vazoesia.out`; ver
[totalizacao-e-artificiais.md](totalizacao-e-artificiais.md) (T8).

Gravadores (frente F7): `pulsar.empacotamento` grava `VAZOES.RVx` e
`PROBVAZ.DAT` a partir de dados tipados; ver
[gravacao-VAZOES.RVx.md](gravacao-VAZOES.RVx.md) (T9).

Integração (frente F9): `src/pulsar/cli.py` grava `VAZOES.RVx` e
`PROBVAZ.DAT` a partir de um deck; resultados por deck e escolhas em
[relatorio-final.md](relatorio-final.md) (T12).

Revalidação de T0–T10 nos 61 pacotes de 2022–2026 (frente F10): [revalidacao-2022-2026.md](revalidacao-2022-2026.md).
