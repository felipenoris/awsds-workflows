# awsds-demo-job: o projeto dos três `demo-*`

Um CSV entra, um resumo em JSON sai: o número de linhas, as colunas, a soma, o mínimo e o máximo
de cada coluna numérica e o sha256 da entrada. Dois pontos de entrada dividem a transformação:

| Comando | Onde roda | A entrada e a saída |
|---|---|---|
| `python -m awsds_demo_job --input PASTA --output PASTA` | num job de processamento, sem rede | pastas locais, que o SageMaker baixa antes e envia depois |
| `python -m awsds_demo_job.s3 --inbox s3://B/PREFIXO/ --outbox s3://B/PREFIXO/` | numa task Python ou Bash, no worker | dois URIs do S3, pelo `boto3` do worker |

O código próprio usa só a biblioteca padrão. As duas dependências, `petl==1.7.28` e
`six==1.16.0`, existem para as tasks mostrarem de onde cada pacote é importado: o `petl` não
está no worker e viaja no `.zip`; o `six` está no worker, no 1.17.0, e viaja no `.zip` numa
versão mais antiga. O job não importa nenhum dos dois.

`sample.csv` tem dez linhas sintéticas. O resumo dele, `sample.result.json`, tem o sha256
`1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191`, o mesmo no laboratório
(2026-10-11) e no ambiente alvo (2026-10-12); o teste do projeto o confere.

## Rodar aqui

```shell
cd examples/awsds-demo-job
uv sync --all-groups
uv run pytest
mkdir -p /tmp/entrada /tmp/saida && cp sample.csv /tmp/entrada/
uv run python -m awsds_demo_job --input /tmp/entrada --output /tmp/saida
sha256sum /tmp/saida/sample.result.json
```

O `uv lock` deixa o `uv.lock` que o `package-task` e o `prepare-offline` pedem; ele fica fora
do git, como a `.venv/`.

## A pasta preparada num `.tar.gz`

O `prepare-offline` do pacote grava a entrada de código do `demo-devenv-job`. Numa máquina Linux
x86_64 com internet, a plataforma do job, ele copia o projeto para uma pasta temporária, recria lá
a `.venv/` com o CPython 3.12 que o `uv` baixa para dentro dela, o projeto instalado como pacote e
as dependências de execução, sem o grupo `dev`, torna relativo cada link, grava o `.tar.gz` com a
raiz `awsds-demo-job/` e prova que a pasta extraída roda sem o `uv`; a pasta do projeto não muda,
e o `uv.lock` tem de existir:

```shell
(cd examples/awsds-demo-job && uv lock)
awsds-workflows prepare-offline examples/awsds-demo-job /tmp/awsds-demo-job.tar.gz
```

A pasta extraída roda de qualquer caminho, sem `uv` e sem rede, com
`awsds-demo-job/.venv/bin/python -m awsds_demo_job`. Em 2026-10-13, o arquivo teve 34.111.121
bytes, 100.119.806 extraídos, com o CPython 3.12.13, e o resumo da amostra saiu com o sha256
acima ([A pasta do projeto preparada num `.tar.gz`](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#a-pasta-do-projeto-preparada-num-targz)).
