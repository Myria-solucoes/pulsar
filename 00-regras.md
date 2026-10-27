# Regras do Pulsar

Este projeto só vale se for possível demonstrar que nenhuma decisão de
implementação veio do executável do GEVAZP. As regras abaixo valem para
toda contribuição, de pessoas ou de agentes.

## Em resumo

1. **Toda implementação tem evidência pública.** Cada constante, fórmula,
   ordem de operação, arredondamento ou detalhe de layout aponta, em
   `PROVENIENCIA.md`, um documento público, um teste contra um arquivo
   publicado ou uma lacuna da documentação (seção 3).
2. **O binário oficial não é usado, nem como caixa-preta.** Ninguém executa,
   abre ou analisa o executável do GEVAZP, nem gera saídas novas com ele
   para comparar, mesmo sem olhar o código (seção 2).
3. **Sem engenharia reversa.** Ninguém desmonta, descompila, rastreia,
   depura ou sonda o GEVAZP ou qualquer parte dele, nem usa o resultado de
   quem fez isso. O que o projeto faz é ler os arquivos que o ONS publica e
   compará-los com a documentação pública; é assim que as lacunas são
   preenchidas, e cada conclusão vira um teste.
4. **Os decks oficiais publicados podem ser usados.** Os pacotes e decks
   que o ONS ou a CCEE publicam, com todas as entradas e saídas que vêm
   neles, são públicos e servem de gabarito (seção 1, item 4).

## 1. Fontes permitidas

1. Tudo dentro deste repositório: `fontes/`, `decks/` e os documentos de
   instrução.
2. Documentação pública do CEPEL na web: `https://see.cepel.br/manual/libs/latest/`
   e o portal de documentação técnica `https://www.cepel.br/produtos/documentacao-tecnica/`.
3. Literatura científica pública: artigos, teses, livros (por exemplo
   Numerical Recipes, Box & Jenkins, Salas et al., Hartigan & Wong).
4. Decks e resultados que o ONS ou a CCEE publicam (pacotes GEVAZP, decks
   DECOMP e NEWAVE), inclusive os arquivos de saída e intermediários que
   vêm dentro deles.
5. Conhecimento geral de estatística, análise numérica e engenharia de
   software.

## 2. Fontes proibidas

Não abra, não leia, não busque e não execute:

- qualquer executável do GEVAZP (Linux ou Windows, qualquer versão), nem o
  arquivo de licença;
- qualquer desmontagem, descompilação, pseudocódigo, rastreamento de
  memória ou tabela extraída de um executável do GEVAZP;
- qualquer projeto, pasta ou análise que tenha sido feita a partir do
  executável, mesmo que seja de terceiros;
- qualquer serviço ou ferramenta que rode o executável;
- material de acesso restrito a participantes de fóruns ou comissões do
  setor;
- repositórios, notas ou mensagens que descrevam "como o binário faz".

Também é proibido usar o executável como caixa-preta: rodá-lo com
entradas escolhidas para observar as saídas, mesmo sem olhar o código, ou
usar saídas que outra pessoa gerou assim. Os únicos resultados oficiais
permitidos são os que o ONS ou a CCEE já publicaram.

Se, por qualquer motivo, você encontrar um material proibido, pare de ler,
registre o ocorrido em `PROVENIENCIA.md` (o que viu, onde, quando) e avise o
orquestrador. Não use o que viu.

## 3. Registro de proveniência

Toda constante, fórmula, ordem de operação, regra de arredondamento ou
decisão de layout implementada precisa ter uma linha em `PROVENIENCIA.md`,
num destes formatos:

```text
<id> | <o que foi decidido> | DOC: <arquivo de fontes/> §<seção>/eq.<n>/pág.<p>
<id> | <o que foi decidido> | INFERIDO: teste <id do teste> contra <deck>/<arquivo público>
<id> | <o que foi decidido> | ESCOLHA: <justificativa>; lacuna <id de 04-lacunas.md>
```

`DOC` é para o que está escrito numa fonte pública. `INFERIDO` é para o que
foi descoberto comparando com um arquivo público, e o teste precisa estar em
`tests/`. `ESCOLHA` é para decisões tomadas onde a documentação é omissa;
elas devem ser parametrizáveis.

Revisões de código rejeitam qualquer detalhe sem linha de proveniência.

## 4. Como trabalhar

- Prefira o relatório do CEPEL a qualquer resumo dele.
- Quando a documentação diz uma coisa e o arquivo público mostra outra,
  vale o arquivo público. Registre a divergência.
- Não otimize antes de o teste de igualdade passar.
- Commits pequenos, um por regra descoberta, citando a linha de proveniência.
