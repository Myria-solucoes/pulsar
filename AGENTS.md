# Instruções para agentes

Este arquivo vale para qualquer agente de código (Claude Code, Codex e
outros) que trabalhe neste repositório. Ele resume `00-regras.md` e
`CONTRIBUTING.md`; em caso de dúvida, valem esses dois.

## Antes de qualquer coisa

1. Leia `00-regras.md` inteiro. As quatro regras:
   - toda implementação tem evidência pública: documento, teste contra
     arquivo publicado ou lacuna registrada;
   - o executável oficial do GEVAZP não é usado, nem como caixa-preta;
   - sem engenharia reversa do GEVAZP, feita por você ou por terceiros;
   - os decks oficiais publicados pelo ONS (e pela CCEE) podem ser usados.
2. Leia a parte de `01-fontes.md` a `04-lacunas.md` que toca a sua tarefa.
   O que não está especificado é lacuna (`04-lacunas.md`), não algo a
   adivinhar em silêncio.
3. Se encontrar material proibido (seção 2 de `00-regras.md`), pare de ler,
   registre em `PROVENIENCIA.md` o que viu e onde, e avise quem pediu a
   tarefa. Não use o que viu.

## O que nunca fazer

- Executar, abrir, listar ou procurar qualquer executável do GEVAZP, seu
  arquivo de licença ou ferramentas que o rodem.
- Buscar desmontagens, descompilações, rastreamentos ou análises feitas a
  partir do executável, inclusive de terceiros.
- Escrever um valor, constante ou regra "porque sabe que é assim" sem uma
  fonte pública ou um teste contra arquivo publicado. Sem evidência, é
  ESCOLHA, com lacuna e parâmetro.
- Fazer push direto no `master`.

## Proveniência

Toda constante, fórmula, ordem de operação, arredondamento ou detalhe de
layout implementado ganha uma linha em `PROVENIENCIA.md`:

| Tipo | Quando | O que citar |
| --- | --- | --- |
| DOC | está escrito numa fonte pública | sigla da tabela "Siglas das fontes" e seção, equação ou página |
| INFERIDO | foi descoberto comparando com um arquivo publicado | o teste em `tests/` que demonstra |
| ESCOLHA | a documentação é omissa | a lacuna de `04-lacunas.md`; a escolha precisa ser parametrizável |

Quando a documentação e um arquivo público discordarem, vale o arquivo e a
divergência fica registrada. `tests/test_proveniencia.py` confere essas
linhas.

## Ambiente e testes

```sh
docker build -t pulsar-py:dev ambiente/        # uma vez
./ambiente/py -m pytest tests                  # amostra de 6 pacotes (padrão)
./ambiente/py -m pytest tests --decks todos    # todos os pacotes em decks/
./ambiente/py src/pulsar/cli.py decks/ons-pacote-gevazp/202609 --revisao RV0 \
    --saida saida/VAZOES.RV0 --semente 1
```

Rode Python sempre por `./ambiente/py`. Os decks ficam em `decks/`, fora do
git (veja o README e `03-oraculos-e-testes.md` §1), e os testes que dependem
de um deck ausente são pulados. `cache/`, `saida/` e `explora/` também ficam
fora do git.

## Repositório público

Tudo o que for commitado é público. Não inclua caminhos absolutos da sua
máquina, nomes de usuário ou de máquina, nomes de projetos ou ferramentas
internas, identificadores de sessão nem credenciais. Cite dados externos pela
origem pública (por exemplo "pacote GEVAZP do ONS de 2024-02, RV2"), nunca
pelo caminho local.

## Entregas

- Commits pequenos, um por regra descoberta, citando o id da linha de
  proveniência.
- Antes do PR: a suíte passa, inclusive `tests/test_proveniencia.py`, e os
  números novos de resultado entram em `docs/relatorio-final.md`.
- PR com os decks usados e o resultado por deck (`CONTRIBUTING.md`). Ao
  abrir o PR, você declara que nada veio de material proibido e licencia a
  contribuição sob a Licença Apache 2.0.
- `site/index.html` não é atualizado a cada PR; vale o `PROVENIENCIA.md`.
