# houseprice-etl: um job do Visual ETL numa aplicação

Um fluxo do Visual ETL é um job do AWS Glue que roda Spark: no ambiente alvo, em 2026-10-14, o save
do editor gravou um job `glueetl` com `JobMode: VISUAL`, Glue 6.0 e dois workers `G.1X`, e os
arquivos do fluxo em `shared/jobs/<job>/`, entre eles o script que o job executa. A CLI de CI/CD
do SageMaker Unified Studio, a `aws-smus-cicd-cli` 1.0.9, leva pastas, workflows e notebooks de um
projeto para outro e não tem tipo de conteúdo para um job do Glue. Este exemplo leva o job numa
aplicação da CLI: o script do job em `glue/` e um workflow cuja task cria o job, ou o atualiza se
ele já existe, e o executa.

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
| `job_name` | `houseprice-etl-{proj.id}` | o nome de um job do Glue é único na conta e na região, então leva o id do projeto |
| `iam_role_arn` | `{proj.iam_role_arn}`, o papel do projeto | com o ARN, o operador não chama o IAM |
| `update_config` | `true` | o operador cria o job quando ele não existe e, quando existe, compara cada campo da definição com o do job e chama `UpdateJob`, com o job inteiro, se algum difere |
| `script_args` | `--SOURCE_PATH`, `--TARGET_PATH` | os caminhos do projeto, sob `exemplos/houseprice-etl/` |
| `create_job_kwargs` | o `Command` inteiro, Glue 6.0, dois `G.1X`, `Timeout` 50, `Connections`, `--custom-logGroup-prefix`, `Tags` | o que o job do editor tinha e o papel do projeto exige |
| `retries` | `0` | uma falha não roda o job duas vezes |

O `Command` vai inteiro em `create_job_kwargs`, com `PythonVersion: "3"`, porque o `GetJob` devolve
o `Command` com esse campo, que o operador não põe no `Command` que monta sozinho: a diferença
chamou `UpdateJob` em toda execução no laboratório, com a definição sem mudança (2026-10-16). Com o
campo na definição, os dois `Command` ficam iguais e a execução sem mudança não chama `UpdateJob`
(inferido do código do operador; a próxima execução mede).

O job da aplicação é separado do job que o editor salvou. O `UpdateJob` do Glue substitui o job
inteiro, e o operador manda só o que a task define: apontado para o job do editor, ele tiraria o
`JobMode: VISUAL` e a configuração do Spark do projeto, o `--conf`, e tentaria remover a tag
`AmazonDataZoneUsername`, que a política do papel do projeto não deixa remover.

A política gerenciada do papel do projeto, `SageMakerStudioProjectUserRolePolicy`, só autoriza o
`glue:CreateJob` com a tag `AmazonDataZoneProject` igual ao projeto de quem chama e com etiquetas
`AmazonDataZone*` e `ProjectUserTag*`: o job leva a tag. O `glue:GetJob`, o `UpdateJob` e o
`StartJobRun` ela autoriza só sobre um job com a tag do projeto, e um job que ainda não existe não
tem tag: a primeira execução num projeto para no `GetJob` com `AccessDenied`, medido no
laboratório em 2026-10-16. Com um `glue:GetJob` a mais no papel do projeto, sobre os jobs sem a
tag cujo nome termina no id do projeto, o `GetJob` responde `EntityNotFoundException`, o
`CreateJob` com a tag passa e o operador cria o job, medido no laboratório no mesmo dia; sem esse
grant, o job se cria uma vez com o `job.json` antes da primeira execução ("Falhas"). As
conexões de rede são as do projeto, `datazone-glue-network-connection-<sub-rede>-<projeto>-dev`,
que o workflow monta com as variáveis de stage `SUBNET_AZ1` e `SUBNET_AZ2`; o job do editor do
ambiente alvo tinha três, uma por sub-rede, e que as do espaço sejam as mesmas é inferido. O
`--custom-logGroup-prefix`, `datazone-<projeto>-dev`, o do job do editor, põe os logs do job num
grupo que o papel do projeto lê (inferido). O `Timeout` de 50 min fica abaixo do limite de 60 min
de uma task, que espera o job terminar e cobra a espera como tempo de task.

O job não leva o `--conf` do job do editor, que liga o catálogo do Glue, o conector do Redshift e
a linhagem: ele lê e grava caminhos do S3 e não precisa deles.

## A aplicação

A pasta é a forma que a CLI 1.0.9 espera: o `manifest.yaml` na raiz, o script em `glue/` e o
workflow em `workflows/`, na notação da CLI. `{proj.id}`, `{proj.iam_role_arn}`,
`{proj.connection.default.s3_shared.s3Uri}` e `{domain.region}` são os valores do projeto do
stage, que a CLI preenche ao criar o workflow. As sub-redes, que a CLI não conhece, são variáveis
de stage, `{env.SUBNET_AZ1}` e `{env.SUBNET_AZ2}`: a CLI as grava na definição como
`{{ params.SUBNET_AZ1 }}` e as preenche em cada execução que inicia com o `environment_variables`
do stage, que o manifest lê do shell, `${SUBNET_AZ1}`, no `deploy` e no `run`. Os dois stages
declaram as duas, porque uma `{env.NOME}` sem declaração derruba o `workflow.create` (laboratório,
2026-10-16); quando os projetos de dev e de teste têm sub-redes diferentes, as variáveis se
exportam de novo antes de cada stage. O domínio e os projetos vêm das variáveis `DOMAIN_ID`,
`DOMAIN_REGION`, `DEV_PROJECT_NAME` e `TEST_PROJECT_NAME`.

Os itens de `content.storage` não têm `connectionName`, então o `bundle` e o `deploy` leem as duas
pastas do disco, ao lado do manifest. O `deploy` de um stage:

1. copia `glue/` e `workflows/` para `shared/exemplos/houseprice-etl/` do projeto do stage, sem
   apagar o que já estava lá;
2. cria o workflow `houseprice_etl_<projeto>_houseprice_etl`, que junta a aplicação, o nome do
   projeto e o workflow com `_`, cada caractere fora de `[A-Za-z0-9_]` trocado por `_`, com as
   variáveis do projeto preenchidas, pela ação `workflow.create` do `bootstrap`, porque a cópia
   dos arquivos sozinha não cria nada;
3. no stage `test`, executa o workflow uma vez, pela ação `workflow.run` com `trailLogs: true`,
   que espera o fim da execução; `wait: true` derruba a CLI 1.0.9 logo depois de iniciá-la.

Cada `deploy` gasta uma versão do workflow, com ou sem mudança na definição. O workflow que a CLI
criou se lê no portal e se edita no git: a CLI o reimplanta.

## Arquivos

| Arquivo | O que é |
|---|---|
| `manifest.yaml` | o manifest da aplicação: as duas pastas, o workflow e os stages `dev` e `test` |
| `workflows/houseprice-etl.yaml` | o workflow, na notação da CLI; o `render` o traduz para importar no portal |
| `glue/etl_houseprice.py` | o script do job |
| `job.json` | a entrada do `CreateJob` que a task faz, na notação da CLI, para criar o job uma vez antes da primeira execução, onde o papel do projeto não tem o `glue:GetJob` sobre jobs sem tag |

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#houseprice-etl):
um Parquet em `entrada/` de cada projeto, o job criado com o `job.json` onde o papel não tem o
grant, o `deploy` e o `run` no projeto de dev, o `bundle` e o `deploy` no de teste, e a leitura
das execuções.

## Falhas

| A task diz | O que fazer |
|---|---|
| `AccessDeniedException` em `GetJob`, na primeira execução num projeto | a política do papel do projeto só autoriza `glue:GetJob` sobre jobs com a tag do projeto, e um job que ainda não existe não tem tag (laboratório, 2026-10-16): crie o job uma vez com o `job.json`, como diz a [página dos passos](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#houseprice-etl), e rode o workflow de novo; ou dê ao papel o `glue:GetJob` sobre os jobs sem tag cujo nome termina no id do projeto, com que o operador cria o job (laboratório, 2026-10-16) |
| `AccessDeniedException` em `CreateJob` | a política exige a tag `AmazonDataZoneProject` com o id do projeto e só aceita etiquetas `AmazonDataZone*` e `ProjectUserTag*`: confira `Tags` |
| `iam:PassRole` não autorizado | `iam_role_arn` precisa ser o papel do projeto |
| um erro sobre uma conexão, no `CreateJob` ou na execução do job | um nome de `Connections` não existe no projeto: copie os de um job do Visual ETL do projeto, com `aws glue get-job --job-name <job do Visual ETL> --query Job.Connections` |
| `Exiting Job jr_... Run State: FAILED` | o job falhou no Glue; o erro está na execução dele, na página *Data processing jobs* |
| `Exiting Job jr_... Run State: TIMEOUT`, ou a task parou por tempo | o job passou dos 50 min do `Timeout`, ou a task passou do limite do workflow, 60 min por padrão |
| `Failed to resolve variables`, no `deploy` | o workflow lê uma `{env.NOME}` que o stage não declara em `environment_variables`, ou a variável não está no shell |

## Conferência

`tests/test_examples.py` confere que o workflow, com as variáveis da CLI traduzidas, preenche com
os valores de um espaço; que o manifest tem o nome da pasta e o workflow dela, copia as duas
pastas para `exemplos/houseprice-etl/` nos dois stages, declara nos dois as variáveis de stage que
o workflow lê, cria o workflow em `dev` e o cria e executa com `trailLogs` em `test`; que o
workflow lê o script onde o manifest o copia; que o `job.json` preenchido é o `CreateJob` que o
operador monta com a task, com o `Command` inteiro; e roda o script sobre dublês do `awsglue` e
do `pyspark`.

Fora da AWS, em 2026-10-14, sem credenciais:

- **O script** rodou duas vezes no PySpark 4.1.1, o Spark do Glue 6.0, com o `getResolvedOptions`
  do `aws-glue-libs`, sobre um Parquet de três linhas: cada execução acrescentou um CSV sem
  cabeçalho com as três linhas.
- **A task** rodou com o Airflow 3.0.6, o `apache-airflow-providers-amazon` 9.32.0 e o `botocore`
  1.43.1 do worker, contra o Glue e o STS do `moto` 5.2.4. A primeira execução chamou `GetJob`,
  `CreateJob`, `StartJobRun` e `GetJobRun`; a segunda, `GetJob`, `GetCallerIdentity`, `GetTags`,
  `GetJob`, `StartJobRun` e `GetJobRun`, sem `UpdateJob`, porque a definição não mudou e o Glue
  simulado devolve o `Command` como foi criado; a terceira, com o `Timeout` trocado para 40,
  chamou também `UpdateJob`, com o job inteiro em `JobUpdate`. Nenhuma chamou o IAM.
- **O manifest** passou na validação da CLI 1.0.9, o resolvedor de variáveis dela escreveu, a
  partir do workflow, a definição preenchida, e o `bundle` empacotou o script e o workflow.

No laboratório, entre dois projetos de uma conta, pela CLI 1.0.9 de um laptop:

- **2026-10-15, `deploy --targets dev --skip-validation --no-events`.** Os dois arquivos
  copiados para `shared/exemplos/houseprice-etl/` do projeto de dev, e o workflow criado, `READY`
  e só manual, com o papel, a rede e a chave do projeto, como um workflow feito no portal. A
  validação que o `deploy` faz antes de agir simula o IAM sem as chaves de contexto das chamadas
  reais e reprova sempre; `--skip-validation` a pula. O evento que o `deploy` publica no fim não
  tem quem o trate na 1.0.9; `--no-events` o pula.
- **2026-10-16, as execuções no projeto de dev.** A primeira parou no `GetJob`, `AccessDenied`
  para o papel do projeto, sem tentar o `CreateJob`. Com o job criado uma vez com o `job.json`,
  a segunda e as seguintes terminaram `SUCCESS`: o job do Glue em 86 s na segunda, o CSV igual à
  entrada, e um CSV a mais em `saida/` a cada execução. O operador chamou `UpdateJob` em toda
  execução, pela diferença do `Command` ("Os parâmetros da task"). A definição que a CLI gravou
  tem `{{ params.SUBNET_AZ1 }}`, a execução leva o valor do stage nos seus parâmetros, e o job
  saiu com os nomes das conexões preenchidos. Um `update_config` vindo de uma variável de stage
  não muda nada: o operador chamou `UpdateJob` com `"false"` e com a variável vazia, porque o
  campo não passa pelo template e um texto vale como verdadeiro; o `true` literal fica.
- **2026-10-16, com o grant do `GetJob`.** Com o papel do projeto de dev autorizado a ler os jobs
  sem tag cujo nome termina no id do projeto e o job apagado, a execução terminou `SUCCESS` em
  139 s: `GetJob` `EntityNotFoundException`, `CreateJob` e `StartJobRun` autorizados, o job criado
  pelo operador com a tag do projeto, as conexões preenchidas e o `PythonVersion: "3"` posto pelo
  serviço; o log diz `Checking if job already exists` e `Creating job`. Antes dela, uma execução
  do workflow de dev numa forma experimental, `update_config: "{{ params.GLUE_UPDATE_CONFIG }}"`,
  a partir do manifest do exemplo, que não declara a variável, falhou no render, antes de qualquer
  task: `DAG template rendering failed: 'dict object' has no attribute 'GLUE_UPDATE_CONFIG'`.
- **2026-10-16, o stage `test`.** O `bundle --targets test` gravou o `.zip` com o workflow igual
  ao do git, as variáveis por preencher, e o `deploy --targets test --bundle-archive-path <zip>`
  criou o workflow no projeto de teste, com o papel e a rede dele, e o executou. Com `wait: true`
  no `workflow.run`, a CLI caiu com um `TypeError` logo depois de iniciar a execução, que terminou
  `SUCCESS` com 545 linhas em `saida/`. Com `trailLogs: true`, a execução terminou `SUCCESS` em
  149 s e a CLI voltou 0 depois de 5,5 min, sem transmitir uma linha de log.
- **As leituras.** O `monitor` e o `logs` da CLI leem errado uma execução; o que a lê é
  `aws mwaa-serverless get-workflow-run`, e os logs da task, `aws logs get-log-events`.
