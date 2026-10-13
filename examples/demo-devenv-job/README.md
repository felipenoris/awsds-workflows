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

## Antes

- **A permissão do projeto.** O papel do projeto, como o blueprint o cria, não descreve um job
  que ainda não existe nem põe etiquetas num job, e o operador faz as duas coisas: a primeira
  execução falha em `DescribeProcessingJob`. A infraestrutura aplica a política de
  [A permissão do projeto](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#a-permissao-do-projeto) antes do primeiro job.
- **A imagem e o Python do job**, em `valores-job.json`. A imagem padrão é a SageMaker
  Distribution, no registro da região, cuja conta o parâmetro público do SSM dá, num espaço:

  ```shell
  aws ssm get-parameter --name /aws/service/sagemaker-distribution/ecr-account-id \
      --query Parameter.Value --output text
  ```

  ```json
  {
    "JOB_IMAGE_URI": "<conta do registro>.dkr.ecr.<região>.amazonaws.com/sagemaker-distribution-prod:4.5.2-cpu",
    "JOB_PYTHON": "/opt/conda/bin/python"
  }
  ```

  A `4.5.2-cpu` é a tag mais nova da 4.5 no ECR público (lida em 2026-10-12), a versão que o
  espaço do ambiente alvo roda, e `/opt/conda/bin/python` é o CPython 3.12.14 dela
  ([A imagem do job](https://felipenoris.github.io/awsds-workflows/awsds_workflows.html#a-imagem-do-job)).
- **Um projeto com chave KMS própria** acrescenta ao `config` a chave do volume e a da saída, com
  o `PROJECT_KEY_ID` que o `space_values.json` dá:

  ```yaml
  ProcessingResources:
    ClusterConfig:
      VolumeKmsKeyId: arn:aws:kms:<REGION>:<ACCOUNT_ID>:key/<PROJECT_KEY_ID>
  ProcessingOutputConfig:
    KmsKeyId: arn:aws:kms:<REGION>:<ACCOUNT_ID>:key/<PROJECT_KEY_ID>
  ```

## Passos

1. **Copie o projeto para a entrada de código**,
   `~/shared/exemplos/demo-devenv-job/awsds-demo-job/`. Na máquina que empacota, sem o `.venv/`,
   o `uv.lock` e os caches:

   ```shell
   tar -C examples --exclude=.venv --exclude=uv.lock --exclude=__pycache__ \
       --exclude=.pytest_cache -czf /tmp/awsds-demo-job.tgz awsds-demo-job
   ```

   e, com o arquivo enviado ao espaço (o botão de upload do JupyterLab):

   ```shell
   mkdir -p ~/shared/exemplos/demo-devenv-job
   tar -xzf awsds-demo-job.tgz -C ~/shared/exemplos/demo-devenv-job/
   ```

   Uma versão nova do código vai para uma pasta nova, porque o job baixa o prefixo inteiro a cada
   execução.
2. **Renderize a definição**, com os dois arquivos de valores:

   ```shell
   awsds-workflows render examples/demo-devenv-job/demo-devenv-job.yaml \
       --values-file space_values.json --values-file valores-job.json > /tmp/demo-devenv-job.yaml
   ```

3. **No portal:** crie o workflow `demo-devenv-job`, esvazie *Operator files zip S3 location*
   em *Settings → Storage*, importe `/tmp/demo-devenv-job.yaml` e salve. O formulário do editor
   não expressa o `config` inteiro: só a importação o guarda.
4. **Ponha a amostra na caixa de entrada**, um arquivo por vez, porque `remove_source` apaga o
   prefixo inteiro:

   ```shell
   mkdir -p ~/shared/exemplos/demo-devenv-job/inbox
   cp sample.csv ~/shared/exemplos/demo-devenv-job/inbox/
   ```

5. **Execute o workflow** e leia o log de `run_project` e o do contêiner, no grupo
   `/aws/sagemaker/ProcessingJobs`.

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
