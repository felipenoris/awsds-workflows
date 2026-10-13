# demo-devenv-job: um job de processamento na imagem padrão

Um sensor espera um arquivo em `inbox/`; `run_project` cria um job de processamento do
SageMaker, que baixa a pasta de código e a caixa de entrada, roda `python -m awsds_demo_job` sem
rede e envia a saída ao S3; e `remove_source` apaga a caixa de entrada, porque um contêiner
isolado não alcança o S3.

| Task | Operador | O que faz |
|---|---|---|
| `wait_for_file` | `S3KeySensor` | espera `inbox/?*`, a cada 30 s, por 10 minutos |
| `run_project` | `SageMakerProcessingOperator` | o `CreateProcessingJob` inteiro, no `config` |
| `remove_source` | `S3DeleteObjectsOperator` | apaga o prefixo `inbox/` |

## Arquivos

| Arquivo | O que é |
|---|---|
| `demo-devenv-job.yaml` | a definição, com placeholders, para um projeto sem chave KMS própria |
| [`../awsds-demo-job/`](../awsds-demo-job/) | o projeto que o job roda, copiado como está para a entrada de código |

O código do job usa só a biblioteca padrão, então a entrada de código é a pasta do projeto, com
`PYTHONPATH=/opt/ml/processing/code/src`; o `petl` e o `six` do projeto servem só às tasks do
worker. Um projeto com dependências que a imagem não tem passa pelo `package-job`
([Uma task de processamento](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#uma-task-de-processamento)).

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#demo-devenv-job), com o que vem antes do
primeiro job: a permissão do projeto, o `valores-job.json` com a imagem e o Python do job e as
linhas da chave KMS de um projeto que tem uma; depois, a pasta do projeto na entrada de código, a
definição com os dois arquivos de valores, o workflow no portal e o log do contêiner.

## O que o log diz

O comando do contêiner abre com `id` e o `ls -ln` das pastas montadas, dá a pasta de saída ao
usuário do contêiner com `sudo -n chown` e então roda o projeto, que imprime
`python 3.12.14 em /opt/conda/bin/python`,
`sample.csv: 10 linhas -> /opt/ml/processing/outbox/sample.result.json` e
`1 arquivo(s) processado(s)`. O resultado vai para `outbox/<carimbo>/sample.result.json`, com o
sha256 dos outros dois `demo-*`. O job imprime contagens e caminhos, nunca dados: o grupo de logs
é da conta inteira.

## Lido no ambiente alvo

Em 2026-10-12, às 18:12 UTC, a primeira execução passou pelo sensor e falhou em 1,5 s com
`AccessDeniedException` em `sagemaker:DescribeProcessingJob`, como papel do projeto, antes de
existir um job: a política de A permissão do projeto ainda não estava aplicada. O caminho do job,
do pull da imagem à gravação da saída, não foi medido lá, e o usuário do contêiner da imagem
padrão também não. No laboratório, em 2026-10-11, com uma imagem customizada e a chave KMS do
projeto, a mesma definição rodou em cerca de 15 minutos e 0,03 USD, 7,5 dos quais baixando a
imagem.
