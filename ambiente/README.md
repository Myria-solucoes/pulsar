# Ambiente do Pulsar

O Python do sistema não tem NumPy (05-plano-e-prompts.md, "Organização").
Este diretório define uma imagem Docker própria, construída do zero a partir
de `python:3.12-slim` com NumPy e pytest, sem reaproveitar imagens de outros
projetos.

```sh
docker build -t pulsar-py:dev ambiente/
./ambiente/py -m pytest tests          # roda os testes
./ambiente/py algum_script.py          # roda um script com a worktree em /pulsar
```

`ambiente/py` monta a worktree em `/pulsar` e define `PYTHONPATH=/pulsar/src`.
Quando as variáveis `PULSAR_COLECAO_GEVAZP` e `PULSAR_COLECAO_DECOMP` apontam
para diretórios locais com as duas coleções de decks do ONS descritas em
03-oraculos-e-testes.md §1.2 (GEVAZP operacional e DECOMP valor esperado),
elas são montadas só para leitura, no mesmo caminho, para os testes da
coleção. Sem elas, esses testes são pulados.
