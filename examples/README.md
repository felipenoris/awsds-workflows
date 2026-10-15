# Os exemplos de workflow

Workflows de exemplo, um por pasta, cada uma com a definição, o código e um `README.md` que diz o
que o exemplo mostra, task por task, e o que cada execução leu; a última coluna da tabela diz o
que cada um leu no ambiente alvo. Os passos para reproduzi-los, na ordem em que cada comando
roda, estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html)
da documentação. Cada definição guarda só placeholders: os valores da conta entram pelo
`space_values.json` que `scripts/space_values.py` escreve num espaço do projeto, e os que um
exemplo pede além deles vêm do `extra_values.json` da pasta dele, um arquivo de modelo com o
prefixo do exemplo no bucket e, no job e no `redshift-unload`, os valores por preencher.

| Exemplo | O que ele mostra | O `Code` do workflow | No ambiente alvo |
|---|---|---|---|
| [`probe-worker`](probe-worker/) | o que o worker tem: disco, CPU, memória, ferramentas e pacotes, numa task Bash inline | nenhum | rodou em 2026-10-13 |
| [`demo-python-operator`](demo-python-operator/) | uma task Python sobre o `.zip` do `package-task`: um CSV entra, um resumo sai no S3 | `demo-python-operator.zip` | rodou em 2026-10-12 |
| [`demo-bash-operator`](demo-bash-operator/) | uma task Bash sobre o mesmo projeto, com dois scripts, e a prova de que o worker não alcança a PyPI | `demo-bash-operator.zip` | rodou em 2026-10-12 |
| [`demo-devenv-job`](demo-devenv-job/) | um job de processamento na imagem padrão do SageMaker, sem rede, sobre o `.tar.gz` do mesmo projeto preparado com o próprio Python | nenhum: o código é uma entrada do job | parou na permissão do projeto em 2026-10-12 |
| [`redshift-unload`](redshift-unload/) | uma task Python que descarrega uma consulta ao Redshift Serverless no S3, com `UNLOAD` | `redshift-unload.zip` | rodou em 2026-10-13 |
| [`houseprice-etl`](houseprice-etl/) | um job do Visual ETL numa aplicação da CLI de CI/CD: uma task `GlueJobOperator` cria ou atualiza o job do Glue e o executa | nenhum: o script do job vai para o S3, de onde o job o lê | ainda não rodou |

Os três `demo-*` dividem o projeto `uv` [`awsds-demo-job/`](awsds-demo-job/): um CSV entra, um
resumo em JSON sai, no worker ou dentro do job; o `prepare-offline` do pacote grava, da pasta
dele, o `.tar.gz` que o job recebe. Cada exemplo usa só o prefixo `<EXAMPLE_PREFIX>` do projeto no
bucket, que o `extra_values.json` dele fixa em `shared/exemplos/<exemplo>`, a pasta
`~/shared/exemplos/<exemplo>/` de um espaço: a caixa de entrada `inbox/`, a caixa de saída
`outbox/` e, no `demo-devenv-job`, a entrada de código `code/`, com o `.tar.gz`; no
`houseprice-etl`, o script do job em `jobs/`, o Parquet em `entrada/` e o CSV em `saida/`.

## Os testes

`uv run pytest tests/test_examples.py` confere as definições (cada uma renderiza com valores
fabricados, é YAML válido, pede só os valores do espaço e os do `extra_values.json` dela, recusa
o `render` enquanto um valor por preencher está como veio e guarda os arquivos sob
`<EXAMPLE_PREFIX>`), roda a task Python e o módulo de `UNLOAD` sobre dublês do
`boto3` e, com `-m network`, constrói os dois `.zip`, lê as raízes deles, prepara o `.tar.gz` do
job e o roda extraído noutra pasta, sem `uv` e sem rede. No `houseprice-etl`, ele confere que o
workflow da aplicação, com as variáveis da CLI trocadas pelos placeholders, preenche igual à
definição, que o `job.json` é o `CreateJob` da task, que o manifest copia o script para onde o
workflow o lê, e roda o script sobre dublês do `awsglue` e do `pyspark`. O projeto compartilhado
tem os próprios testes, que o `uv run pytest` da raiz também roda.
