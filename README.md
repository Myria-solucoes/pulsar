# Pulsar

O Pulsar é uma reconstrução aberta do GEVAZP, o gerador de cenários de
afluências do CEPEL, no caminho que alimenta o DECOMP (arquivo `VAZOES.RVx`).
Ele usa **somente informação pública ou inferida de dados públicos**:
relatórios do CEPEL, a documentação LIBS, literatura científica e os pacotes
que o ONS publica.

Página do projeto: <https://pulsar.myria.energy>

O objetivo é chegar o mais perto possível do arquivo oficial. Nas partes
determinísticas, a meta é igualdade byte a byte. Nas partes que a
documentação pública deixa em aberto, a meta é equivalência estatística
demonstrada.

## Leia nesta ordem

| Arquivo | Para quê |
| --- | --- |
| [00-regras.md](00-regras.md) | O que é permitido e proibido. Todo agente lê isto primeiro. |
| [01-fontes.md](01-fontes.md) | Catálogo das fontes públicas e o que cada uma cobre. |
| [02-especificacao-publica.md](02-especificacao-publica.md) | O que a documentação pública diz sobre cada etapa, com citação. |
| [03-oraculos-e-testes.md](03-oraculos-e-testes.md) | Os decks públicos usados como oráculo, a escada de testes e as técnicas de inferência permitidas. |
| [04-lacunas.md](04-lacunas.md) | O que as fontes públicas não especificam e como tratar cada lacuna. |
| [05-plano-e-prompts.md](05-plano-e-prompts.md) | Fases, entregáveis e os prompts prontos para cada agente. |

## Estrutura

```text
src/pulsar/          código
tests/               testes, em degraus T0–T12 (03-oraculos-e-testes.md)
docs/                layouts dos arquivos e relatório final
ferramentas/         scripts de apoio (fontes, relatórios, sementes)
ambiente/            imagem Docker com Python, NumPy e pytest
fontes/              texto das fontes públicas (CEPEL, LIBS, AS 136) e manifesto
decks/               pacotes GEVAZP publicados pelo ONS (não vêm no git)
site/                página pública do projeto
```

## Como começar

1. Construa o ambiente: `docker build -t pulsar-py:dev ambiente/`.
2. Baixe do SINtegre/ONS os pacotes "Arquivos dos modelos de geração de
   cenários de vazões" e descompacte em `decks/ons-pacote-gevazp/<AAAAMM>/`
   (03-oraculos-e-testes.md §1). Os testes que dependem de um deck ausente
   são pulados.

## Uso

```sh
./ambiente/py src/pulsar/cli.py decks/ons-pacote-gevazp/202609 --revisao RV0 \
    --saida saida/VAZOES.RV0 --semente 1    # grava saida/VAZOES.RV0 e saida/PROBVAZ.DAT
./ambiente/py -m pytest tests                # degraus T0–T12
```

Resultados por deck, o que fecha byte a byte e as escolhas com o impacto de
cada uma: [docs/relatorio-final.md](docs/relatorio-final.md).

## Proveniência

Cada decisão de implementação tem uma linha em `PROVENIENCIA.md`, com o tipo
(DOC, INFERIDO ou ESCOLHA) e a fonte ou o teste que a sustenta, e
`tests/test_proveniencia.py` confere essas linhas. Onde a documentação
pública é omissa, o kit aponta a lacuna (`04-lacunas.md`) e o arquivo
público que permite investigá-la.

Se você desconfiar de que alguma instrução depende de conhecimento não
público, abra uma issue e trate o ponto como lacuna.

## Como participar

Leia [CONTRIBUTING.md](CONTRIBUTING.md) e [00-regras.md](00-regras.md). As
quatro regras principais:

- toda implementação tem evidência pública (documento, teste contra arquivo
  publicado ou lacuna registrada);
- o executável oficial do GEVAZP não é usado, nem como caixa-preta;
- sem engenharia reversa do GEVAZP, feita por nós ou por terceiros;
- os decks oficiais publicados pelo ONS podem ser usados como gabarito.

## Licença

O código e a documentação do Pulsar estão sob a
[Licença Apache 2.0](LICENSE). A pasta `fontes/` traz o texto de documentos
públicos de terceiros (CEPEL, StatLib) só como referência: eles continuam
sob os termos dos seus autores e não estão sob a licença do Pulsar. Os decks
do ONS não vêm no repositório.

GEVAZP, DECOMP e NEWAVE são modelos do CEPEL. O Pulsar não é afiliado ao
CEPEL nem ao ONS.
