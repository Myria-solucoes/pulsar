# Como participar do Pulsar

Obrigado pelo interesse. O Pulsar só tem valor se for possível mostrar que
cada decisão veio de fonte pública, então as regras abaixo valem para todas
as contribuições: código, testes, documentação e issues.

## Antes de começar

- Leia `00-regras.md` inteiro. Em resumo:
  - **toda implementação precisa de evidência pública**: um documento
    público, um teste contra um arquivo publicado ou uma lacuna registrada;
  - **o executável oficial do GEVAZP não é usado, nem como caixa-preta**:
    nada de rodá-lo para comparar saídas, nem de usar desmontagem,
    descompilação, rastreamento ou análises de terceiros feitas a partir
    dele;
  - **sem engenharia reversa**: ninguém desmonta, descompila, rastreia,
    depura ou sonda o GEVAZP, nem usa o resultado de quem fez isso. Ler e
    interpretar os arquivos que o ONS publica, comparando com a
    documentação, é permitido e é como o projeto preenche as lacunas;
  - **os decks oficiais publicados pelo ONS (e pela CCEE) podem ser
    usados**, com todas as entradas e saídas que vêm neles.
- Leia `01-fontes.md` a `04-lacunas.md` para saber o que já está
  especificado e o que ainda é lacuna.
- Monte o ambiente seguindo o README (Docker, fontes e decks).

## Toda mudança precisa de proveniência

Toda constante, fórmula, ordem de operação, arredondamento ou detalhe de
layout que você implementar precisa de uma linha em `PROVENIENCIA.md`:

| Tipo | Quando usar | O que citar |
| --- | --- | --- |
| DOC | está escrito numa fonte pública | sigla da fonte (`U19`, `M18`, `L-PAR`…) e seção, equação ou página |
| INFERIDO | você descobriu comparando com um arquivo publicado pelo ONS | o teste em `tests/` que demonstra |
| ESCOLHA | a documentação é omissa | a lacuna de `04-lacunas.md`; a escolha precisa ser parametrizável |

Quando a documentação e um arquivo público discordarem, vale o arquivo
público; registre a divergência na linha.

## Pull requests

- Commits pequenos, um por regra descoberta, citando o id da linha de
  proveniência.
- Rode `./ambiente/py -m pytest tests` antes de abrir o PR, incluindo
  `tests/test_proveniencia.py`.
- Descreva no PR quais decks você usou e o resultado por deck.
- Ao abrir o PR, você declara que nenhuma parte dele veio de material
  proibido por `00-regras.md` e concorda em licenciá-lo sob a Licença
  Apache 2.0.

## Issues

Use issues para relatar diferenças contra um arquivo oficial (diga o deck,
a revisão e o bloco), propor uma fonte pública nova ou apontar uma
instrução que pareça depender de conhecimento não público.
