# Os exemplos de workflow

Workflows de exemplo, um por pasta, cada um uma aplicação da CLI de CI/CD do SageMaker Unified
Studio, a `aws-smus-cicd-cli` 1.0.9: o `manifest.yaml`, o workflow em `workflows/`, na notação da
CLI, o código e um `README.md` que diz o que o exemplo mostra, task por task, e o que cada
execução leu; a última coluna da tabela diz onde cada um rodou. Os passos para reproduzi-los, na
ordem em que cada comando roda, estão na página
[Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html)
da documentação. A CLI leva a pasta a um projeto, cria o workflow lá, com os valores desse
projeto, e o executa; pelo portal, o `render` do pacote traduz as variáveis da CLI e preenche o
workflow com o `space_values.json` que `scripts/space_values.py` escreve num espaço do projeto e,
onde um valor não vem do espaço, com o `extra_values.json` da pasta, um arquivo de modelo com os
valores por preencher.

| Exemplo | O que ele mostra | O que vai ao projeto | Onde rodou |
|---|---|---|---|
| [`probe-worker`](probe-worker/) | o que o worker tem: disco, CPU, memória, ferramentas e pacotes, numa task Bash inline | `workflows/` | no ambiente alvo, pelo portal, em 2026-10-13 |
| [`demo-python-operator`](demo-python-operator/) | uma task Python sobre o `.zip` do `package-task`: um CSV entra, um resumo sai no S3 | `workflows/` e o `.zip` em `code/`, o `Code` do workflow | no ambiente alvo, pelo portal, em 2026-10-12 |
| [`demo-bash-operator`](demo-bash-operator/) | uma task Bash sobre o mesmo projeto, com dois scripts, e a prova de que o worker não alcança a PyPI | `workflows/` e o `.zip` em `code/`, o `Code` do workflow | no ambiente alvo, pelo portal, em 2026-10-12 |
| [`demo-devenv-job`](demo-devenv-job/) | um job de processamento na imagem padrão do SageMaker, sem rede, sobre o `.tar.gz` do mesmo projeto preparado com o próprio Python | `workflows/` e o `.tar.gz` em `src/`, a entrada de código do job | parou na permissão do projeto no ambiente alvo, pelo portal, em 2026-10-12 |
| [`redshift-unload`](redshift-unload/) | uma task Python que descarrega uma consulta ao Redshift Serverless no S3, com `UNLOAD` | `workflows/` e o `.zip` do módulo em `code/`, o `Code` do workflow | no ambiente alvo, pelo portal, em 2026-10-13 |
| [`houseprice-etl`](houseprice-etl/) | um job do Visual ETL: uma task `GlueJobOperator` cria ou atualiza o job do Glue e o executa | `workflows/` e o script do job em `glue/`, de onde o job o lê | no laboratório, pela CLI, nos stages `dev` e `test`, em 2026-10-15 e 2026-10-16 |

Os três `demo-*` dividem o projeto `uv` [`awsds-demo-job/`](awsds-demo-job/): um CSV entra, um
resumo em JSON sai, no worker ou dentro do job; o `package-task` do pacote grava, da pasta dele,
o `.zip` das tasks, e o `prepare-offline` o `.tar.gz` que o job recebe. Cada exemplo usa só o
prefixo `exemplos/<exemplo>/` da pasta `shared/` do projeto no bucket, a pasta
`~/shared/exemplos/<exemplo>/` de um espaço, onde o `deploy` copia as pastas do manifest: a caixa
de entrada `inbox/`, a caixa de saída `outbox/` e, no `demo-devenv-job`, a entrada de código
`src/`, com o `.tar.gz`; no `houseprice-etl`, o script do job em `glue/`, o Parquet em `entrada/`
e o CSV em `saida/`. O que o `package-task` e o `prepare-offline` gravam em `code/` e em `src/`,
e o bundle da CLI em `artifacts/`, fica fora do git.

## Os testes

`uv run pytest tests/test_examples.py` confere os workflows (cada um renderiza com valores
fabricados, com as variáveis da CLI traduzidas, é YAML válido, pede só os valores do espaço e os
do `extra_values.json` da pasta, recusa o `render` enquanto um valor por preencher está como veio
e guarda os arquivos sob `exemplos/<exemplo>/` da pasta `shared/`), os manifests (o nome da pasta
e o workflow dela, as pastas que o workflow lê copiadas para `exemplos/<exemplo>/` nos dois
stages, as variáveis de stage do workflow declaradas nos dois, o `.zip` de `code/` como `code` do
workflow onde há task Python ou Bash, o `workflow.create` em `dev` e o `workflow.run` com
`trailLogs` em `test`), roda a task Python e o módulo de `UNLOAD` sobre dublês do `boto3` e, com
`-m network`, constrói os dois `.zip`, lê as raízes deles, prepara o `.tar.gz` do job e o roda
extraído noutra pasta, sem `uv` e sem rede. No `houseprice-etl`, ele confere que o `job.json`
preenchido é o `CreateJob` da task e roda o script sobre dublês do `awsglue` e do `pyspark`. O
projeto compartilhado tem os próprios testes, que o `uv run pytest` da raiz também roda.
