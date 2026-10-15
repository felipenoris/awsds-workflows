# houseprice-etl: um job do Visual ETL numa aplicação

Um fluxo do Visual ETL é um job do AWS Glue que roda Spark: no ambiente alvo, em 2026-10-14, o save
do editor gravou um job `glueetl` com `JobMode: VISUAL`, Glue 6.0 e dois workers `G.1X`, e os
arquivos do fluxo em `shared/jobs/<job>/`, entre eles o script que o job executa. A CLI de CI/CD
do SageMaker Unified Studio, a `aws-smus-cicd-cli` 1.0.9, leva pastas, workflows e notebooks de um
projeto para outro e não tem tipo de conteúdo para um job do Glue. Este exemplo leva o job numa
aplicação da CLI como a AWS a monta: o script do job e um workflow cuja task cria o job, ou o
atualiza se ele já existe, e o executa.

O script é o que o Visual ETL gerou para um fluxo de três nós, uma origem Parquet no S3, um nó de
código que não muda os dados e um destino CSV no S3, com uma mudança: os caminhos de entrada e de
saída, que o script gerado traz escritos, chegam como argumentos do job, `--SOURCE_PATH` e
`--TARGET_PATH`, porque cada projeto tem os seus. O job se edita nesse script, no git; o fluxo do
Visual ETL fica no projeto de dev como rascunho.

| Task | Operador | O que faz |
|---|---|---|
| `run_glue_job` | `GlueJobOperator` | cria ou atualiza o job `houseprice-etl-<projeto>` com o `create_job_kwargs` e o executa com os dois caminhos de `script_args`, esperando o fim dele |

## Os parâmetros da task

| Parâmetro | Valor | Por quê |
|---|---|---|
| `job_name` | `houseprice-etl-<PROJECT_ID>` | o nome de um job do Glue é único na conta e na região, então leva o id do projeto |
| `iam_role_arn` | o papel do projeto | com o ARN, o operador não chama o IAM |
| `update_config` | `true` | o operador cria o job quando ele não existe e, quando existe, compara cada campo da definição com o do job e chama `UpdateJob` se algum difere |
| `script_args` | `--SOURCE_PATH`, `--TARGET_PATH` | os caminhos do projeto |
| `create_job_kwargs` | Glue 6.0, dois `G.1X`, `Timeout` 50, `Connections`, `--custom-logGroup-prefix`, `Tags` | o que o job do editor tinha e o papel do projeto exige |
| `retries` | `0` | uma falha não roda o job duas vezes |

O job da aplicação é separado do job que o editor salvou. O `UpdateJob` do Glue substitui o job
inteiro, e o operador manda só o que a task define: apontado para o job do editor, ele tiraria o
`JobMode: VISUAL` e a configuração do Spark do projeto, o `--conf`, e tentaria remover a tag
`AmazonDataZoneUsername`, que a política do papel do projeto não deixa remover.

A política gerenciada do papel do projeto, `SageMakerStudioProjectUserRolePolicy`, só autoriza o
`glue:CreateJob` com a tag `AmazonDataZoneProject` igual ao projeto de quem chama e com etiquetas
`AmazonDataZone*` e `ProjectUserTag*`: o job leva a tag. As conexões de rede são as do projeto,
`datazone-glue-network-connection-<sub-rede>-<projeto>-dev`, que a definição monta com
`SUBNET_AZ1` e `SUBNET_AZ2` do `space_values.json`; o job do editor do ambiente alvo tinha três,
uma por sub-rede, e que as do espaço sejam as mesmas é inferido. O `--custom-logGroup-prefix`,
`datazone-<projeto>-dev`, o do job do editor, põe os logs do job num grupo que o papel do projeto
lê (inferido). O `Timeout` de 50 min fica abaixo do limite de 60 min de uma task, que espera o job
terminar e cobra a espera como tempo de task.

O job não leva o `--conf` do job do editor, que liga o catálogo do Glue, o conector do Redshift e
a linhagem: ele lê e grava caminhos do S3 e não precisa deles.

## A aplicação

`aplicacao/` é a forma que a CLI 1.0.9 espera: o `manifest.yaml` na raiz, o script em `jobs/` e o
workflow em `workflows/`, com as variáveis da CLI, `{proj.id}`, `{proj.iam_role_arn}`,
`{proj.connection.default.s3_shared.s3Uri}` e `{domain.region}`, no lugar dos placeholders da
definição. A CLI não tem variável para as sub-redes: `<SUBNET_AZ1>` e `<SUBNET_AZ2>` ficam, e o
`render` as preenche uma vez, numa cópia fora deste repositório, porque elas são da conta.

Os itens de `content.storage` não têm `connectionName`, então o `bundle` lê as duas pastas do
disco, ao lado do manifest, e não do projeto de dev. O `deploy` do stage `test`:

1. copia `jobs/` e `workflows/` para `shared/exemplos/houseprice-etl/` do projeto de teste;
2. troca as variáveis do workflow pelos valores desse projeto;
3. cria o workflow `houseprice_etl_<projeto de teste>_houseprice_etl`, que junta a aplicação, o
   nome do projeto e o workflow com `_`, cada caractere fora de `[A-Za-z0-9_]` trocado por `_`,
   e o executa uma vez, a execução que cria o job.

## Arquivos

| Arquivo | O que é |
|---|---|
| `houseprice-etl.yaml` | a definição, com placeholders, para importar no portal |
| `extra_values.json` | o arquivo de valores extras, de modelo: só o prefixo do exemplo |
| `job.json` | a entrada do `CreateJob` que a task faz, com placeholders, para criar o job à mão se a primeira execução não conseguir |
| `aplicacao/manifest.yaml` | o manifest da aplicação, para a CLI de CI/CD |
| `aplicacao/workflows/houseprice-etl.yaml` | a mesma definição, com as variáveis da CLI |
| `aplicacao/jobs/etl_houseprice.py` | o script do job |

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#houseprice-etl):
o script e um Parquet no projeto, a definição e o `job.json` preenchidos, o workflow no portal, as
duas execuções, e a aplicação pela CLI de CI/CD.

## Falhas

| A task diz | O que fazer |
|---|---|
| `AccessDeniedException` em `GetJob`, na primeira execução | a política do papel do projeto só autoriza `glue:GetJob` sobre jobs com a tag do projeto, e um job que ainda não existe não tem tag (incerto): crie o job uma vez com o `job.json`, como diz a [página dos passos](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#houseprice-etl), e rode o workflow de novo |
| `AccessDeniedException` em `CreateJob` | a política exige a tag `AmazonDataZoneProject` com o id do projeto e só aceita etiquetas `AmazonDataZone*` e `ProjectUserTag*`: confira `Tags` |
| `iam:PassRole` não autorizado | `iam_role_arn` precisa ser o papel do projeto |
| um erro sobre uma conexão, no `CreateJob` ou na execução do job | um nome de `Connections` não existe no projeto: copie os de um job do Visual ETL do projeto, com `aws glue get-job --job-name <job do Visual ETL> --query Job.Connections` |
| `Exiting Job jr_... Run State: FAILED` | o job falhou no Glue; o erro está na execução dele, na página *Data processing jobs* |
| `Exiting Job jr_... Run State: TIMEOUT`, ou a task parou por tempo | o job passou dos 50 min do `Timeout`, ou a task passou do limite do workflow, 60 min por padrão |

Se a primeira execução parar no `GetJob`, o resultado vale para qualquer projeto novo: o `deploy`
da CLI também vai precisar do job criado antes da primeira execução do workflow.

## Conferência

`tests/test_examples.py` confere que o workflow da aplicação, com cada variável da CLI trocada pelo
placeholder do mesmo valor, preenche igual à definição; que o `job.json` preenchido é o `CreateJob`
que o operador monta com a task; que o manifest copia o script para o caminho que o workflow passa
ao job; e roda o script sobre dublês do `awsglue` e do `pyspark`.

Fora da AWS, em 2026-10-14, sem credenciais:

- **O script** rodou duas vezes no PySpark 4.1.1, o Spark do Glue 6.0, com o `getResolvedOptions`
  do `aws-glue-libs`, sobre um Parquet de três linhas: cada execução acrescentou um CSV sem
  cabeçalho com as três linhas.
- **A task** rodou com o Airflow 3.0.6, o `apache-airflow-providers-amazon` 9.32.0 e o `botocore`
  1.43.1 do worker, contra o Glue e o STS do `moto` 5.2.4. A primeira execução chamou `GetJob`,
  `CreateJob`, `StartJobRun` e `GetJobRun`; a segunda, `GetJob`, `GetCallerIdentity`, `GetTags`,
  `GetJob`, `StartJobRun` e `GetJobRun`, sem `UpdateJob`, porque a definição não mudou; a
  terceira, com o `Timeout` trocado para 40, chamou também `UpdateJob`, com o job inteiro em
  `JobUpdate`. Nenhuma chamou o IAM. O `job.json` preenchido é a entrada desse `CreateJob`.
- **O manifest** passou na validação da CLI 1.0.9, o resolvedor de variáveis dela escreveu, a
  partir de `aplicacao/workflows/houseprice-etl.yaml`, a definição preenchida, e o `bundle`
  empacotou `jobs/etl_houseprice.py` e `workflows/houseprice-etl.yaml`.

O exemplo ainda não rodou num projeto. A primeira execução responde se o `GetJob` sobre um job que
não existe passa pela política do papel do projeto.
