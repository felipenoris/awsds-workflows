# demo-devenv-job: um job de processamento na imagem padrão

Um sensor espera um arquivo em `inbox/`; `run_project` cria um job de processamento do
SageMaker, que baixa o `.tar.gz` do projeto e a caixa de entrada, extrai o projeto no volume,
roda o `python -m awsds_demo_job` da pasta extraída sem rede e envia a saída ao S3; e
`remove_source` apaga a caixa de entrada, porque um contêiner isolado não alcança o S3.

| Task | Operador | O que faz |
|---|---|---|
| `wait_for_file` | `S3KeySensor` | espera `inbox/?*`, a cada 30 s, por 10 minutos |
| `run_project` | `SageMakerProcessingOperator` | o `CreateProcessingJob` inteiro, no `config` |
| `remove_source` | `S3DeleteObjectsOperator` | apaga o prefixo `inbox/` |

## Arquivos

| Arquivo | O que é |
|---|---|
| `demo-devenv-job.yaml` | a definição, com placeholders, para um projeto sem chave KMS própria |
| `extra_values.json` | o arquivo de valores extras, de modelo: o prefixo do exemplo, a conta do registro da imagem por preencher e o URI da imagem padrão montado com ela |
| [`../awsds-demo-job/`](../awsds-demo-job/) | o projeto que o job roda; o `prepare-offline` do pacote grava, da pasta dele, o `.tar.gz` da entrada de código, com o próprio CPython 3.12 e as dependências |

A entrada de código é um objeto só, `code/awsds-demo-job.tar.gz`: a pasta do projeto preparada,
que roda de qualquer caminho com `.venv/bin/python`, sem o interpretador da imagem; o comando do
job a extrai em `/opt/ml/processing/code/` antes de rodar
([A pasta do projeto preparada num `.tar.gz`](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#a-pasta-do-projeto-preparada-num-targz)).
Um projeto que usa o ambiente da imagem e leva só o que ela não tem passa pelo `package-job`
([A pasta de código com `package-job`](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#a-pasta-de-codigo-com-package-job)).

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#demo-devenv-job), com o que vem antes do
primeiro job: a permissão do projeto, a conta do registro da imagem no `extra_values.json` e as
linhas da chave KMS de um projeto que tem uma; depois, o `.tar.gz` do projeto, gravado pelo
`prepare-offline`, na entrada de código, a definição com os dois arquivos de valores, o workflow
no portal e o log do contêiner.

## O que o log diz

O comando do contêiner abre com `id` e o `ls -ln` das pastas montadas, dá a entrada de código e
a pasta de saída ao usuário do contêiner com `sudo -n chown`, extrai o `.tar.gz` e então roda o
projeto, que imprime
`python 3.12.13 em /opt/ml/processing/code/awsds-demo-job/.venv/bin/python`, com a versão que o
`uv` baixou ao preparar,
`sample.csv: 10 linhas -> /opt/ml/processing/outbox/sample.result.json` e
`1 arquivo(s) processado(s)`. O resultado vai para `outbox/<carimbo>/sample.result.json`, com o
sha256 dos outros dois `demo-*`. O job imprime contagens e caminhos, nunca dados: o grupo de logs
é da conta inteira.

## Lido no ambiente alvo

Em 2026-10-12, às 18:12 UTC, a primeira execução, com a pasta do projeto expandida no S3 como
entrada de código, passou pelo sensor e falhou em 1,5 s com `AccessDeniedException` em
`sagemaker:DescribeProcessingJob`, como papel do projeto, antes de existir um job: a política de
A permissão do projeto ainda não estava aplicada. O caminho do job, do pull da imagem à gravação
da saída, não foi medido lá, nem o usuário do contêiner da imagem padrão, e o `.tar.gz` ainda não
rodou num job. No laboratório, em 2026-10-11, com uma imagem customizada e a chave KMS do
projeto, a definição sobre a pasta expandida rodou em cerca de 15 minutos e 0,03 USD, 7,5 dos
quais baixando a imagem. Na máquina que empacota, em 2026-10-13, o `.tar.gz` extraído noutra
pasta, por um usuário sem privilégio e sem `uv` nem rede, escreveu o resumo com o mesmo sha256.
