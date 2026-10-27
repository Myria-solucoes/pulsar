<h1 align="center">Pulsar</h1>

<p align="center">
  Reconstrução aberta do GEVAZP, o gerador de cenários de afluências do CEPEL,<br>
  feita só com fontes públicas.
</p>

<p align="center">
  <a href="LICENSE"><img alt="Licença Apache 2.0" src="https://img.shields.io/badge/licen%C3%A7a-Apache%202.0-8aadf4?style=flat-square"></a>
  <img alt="Python 3.12" src="https://img.shields.io/badge/python-3.12-3f6e8a?style=flat-square&logo=python&logoColor=white">
  <img alt="NumPy" src="https://img.shields.io/badge/NumPy-float64-3f6e8a?style=flat-square&logo=numpy&logoColor=white">
  <a href="PROVENIENCIA.md"><img alt="276 decisões com proveniência" src="https://img.shields.io/badge/proveni%C3%AAncia-276%20decis%C3%B5es-5fae6e?style=flat-square"></a>
  <a href="00-regras.md"><img alt="Só fontes públicas" src="https://img.shields.io/badge/fontes-s%C3%B3%20p%C3%BAblicas-5fae6e?style=flat-square"></a>
  <a href="00-regras.md"><img alt="Sem engenharia reversa" src="https://img.shields.io/badge/engenharia%20reversa-nenhuma-5fae6e?style=flat-square"></a>
  <a href="docs/relatorio-final.md"><img alt="Determinísticos byte a byte" src="https://img.shields.io/badge/determin%C3%ADsticos-byte%20a%20byte-8aadf4?style=flat-square"></a>
  <a href="https://github.com/Myria-solucoes/pulsar/actions/workflows/pages.yml"><img alt="Página" src="https://img.shields.io/github/actions/workflow/status/Myria-solucoes/pulsar/pages.yml?branch=master&label=p%C3%A1gina&style=flat-square"></a>
  <a href="CONTRIBUTING.md"><img alt="Contribuições bem-vindas" src="https://img.shields.io/badge/PRs-bem--vindos-ff9f43?style=flat-square"></a>
</p>

<p align="center">
  <a href="https://pulsar.myria.energy"><b>pulsar.myria.energy</b></a> ·
  <a href="docs/relatorio-final.md">Relatório final</a> ·
  <a href="PROVENIENCIA.md">Proveniência</a> ·
  <a href="CONTRIBUTING.md">Como participar</a>
</p>

---

O Pulsar gera o `VAZOES.RVx` que o DECOMP lê, a partir do mesmo deck que o
ONS publica. Ele usa **somente informação pública ou inferida de dados
públicos**: relatórios do CEPEL, a documentação LIBS, literatura científica
e os pacotes que o ONS publica. Nas partes determinísticas, a meta é
igualdade byte a byte com o arquivo oficial. Nas partes que a documentação
pública deixa em aberto, a meta é equivalência estatística demonstrada.

| | 202609 RV0 | 202609 RV1 | 202610 RV0 |
| --- | :---: | :---: | :---: |
| Blocos determinísticos do `VAZOES.RVx` iguais ao oficial | 100% | 100% | 100% |
| Média dos cenários na faixa das 20 sementes (referência 0,90) | 0,908 | 0,941 | 0,908 |
| Correlação espacial na faixa das 20 sementes (referência 0,90) | 0,909 | 0,912 | 0,894 |

Detalhes, limites e o que ainda está em aberto: [docs/relatorio-final.md](docs/relatorio-final.md).

### Como funciona

```text
deck do ONS ─▶ 1 leitura e configuração ─▶ 2 vazões incrementais ─▶ 3 PAR(p)-A
           ─▶ 4 correlação espacial ─▶ 5 tendência hidrológica
           ─▶ 6 ruídos + K-means ─▶ 7 lognormal e recorrência
           ─▶ 8 totalização e artificiais ─▶ 9 VAZOES.RVx + PROBVAZ.DAT
```

A página do projeto mostra cada etapa com o que ela faz, o resultado contra
o oficial e a fonte pública de cada decisão.

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
