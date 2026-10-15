Esta página é o roteiro dos exemplos da pasta
[`examples/`](https://github.com/felipenoris/awsds-workflows/tree/main/examples) do repositório, na
ordem em que cada comando roda. Cada passo diz onde ele acontece:

- **na máquina que empacota**: um Linux com internet, com o pacote instalado e o repositório
  clonado; os comandos rodam na raiz do clone;
- **no espaço**: um terminal de um espaço do projeto no SageMaker Unified Studio, JupyterLab ou
  Code Editor; a pasta `~/shared/` dele é o prefixo `shared/` do projeto no bucket, então um `cp`
  para lá é um envio ao S3 (lido no ambiente alvo em 2026-10-12);
- **no portal**: a página *Workflows* do projeto no SageMaker Unified Studio.

Os termos estão em [Os conceitos](../awsds_workflows.html#os-conceitos). O que cada exemplo
mostra, task por task, e as leituras inteiras de cada execução estão no `README.md` da pasta
dele.

| Exemplo | O que ele mostra | O que ele pede além do `space_values.json` |
|---|---|---|
| [probe-worker](#probe-worker) | o que o worker tem, numa task Bash inline | nada: a definição entra como está |
| [demo-python-operator](#demo-python-operator) | uma task Python sobre o `.zip` do `package-task` | o `extra_values.json` da pasta, só com o prefixo |
| [demo-bash-operator](#demo-bash-operator) | uma task Bash sobre o mesmo `.zip`, com dois scripts, e a prova de que o worker não alcança a PyPI | o `extra_values.json` da pasta, só com o prefixo |
| [demo-devenv-job](#demo-devenv-job) | um job de processamento na imagem padrão do SageMaker, sobre o `.tar.gz` da pasta do projeto preparada | a permissão do projeto e, no `extra_values.json` da pasta, a conta do registro da imagem |
| [redshift-unload](#redshift-unload) | uma task Python que descarrega uma consulta ao Redshift Serverless no S3 | os nomes do Redshift no `extra_values.json` da pasta e o acesso do usuário do projeto ao banco |
| [houseprice-etl](#houseprice-etl) | um job do Visual ETL numa aplicação da CLI de CI/CD: a task cria ou atualiza o job do Glue e o executa | o script e um Parquet no projeto, e o `extra_values.json` da pasta, só com o prefixo |

## A preparação

1. **Na máquina que empacota**, instale o pacote e clone o repositório:

   ```shell
   uv tool install git+https://github.com/felipenoris/awsds-workflows
   git clone https://github.com/felipenoris/awsds-workflows
   cd awsds-workflows
   awsds-workflows --help
   ```

   Os comandos desta página rodam nessa pasta. O que o `render` grava leva os ids da conta: vai
   para `/tmp`, nunca para o repositório.

2. **Leve ao espaço** dois arquivos do clone, pelo botão de upload do JupyterLab:
   `scripts/space_values.py` e `examples/awsds-demo-job/sample.csv`.

3. **No espaço**, leia os valores do projeto e confira o `~/shared/`:

   ```shell
   python space_values.py > space_values.json
   cat space_values.json
   mount | grep -i shared
   ```

   O JSON traz `ACCOUNT_ID`, `DOMAIN_ID`, `PROJECTS_BUCKET`, `PROJECT_ID`, `PROJECT_ROLE_NAME`,
   `PROJECT_SG`, `REGION`, `SUBNET_AZ1` e `SUBNET_AZ2`, e `PROJECT_KEY_ID` quando o projeto tem
   chave KMS própria; sem ela, o aviso `o ambiente Tooling não tem kmsKeyArn` no stderr é
   normal ([Os valores de dentro de um espaço](../awsds_workflows.html#os-valores-de-dentro-de-um-espaco)).
   O `mount` tem de mostrar uma linha `s3fs on /mnt/custom-file-systems/s3/shared`, a montagem
   que faz do `~/shared/` o bucket do projeto; sem ela, os passos que gravam em `~/shared/` não
   valem.

4. **Copie o `space_values.json` para a máquina que empacota**, pelo download do JupyterLab ou
   colando a saída do `cat` num arquivo. Ele leva os ids da conta e fica fora do git: o
   `.gitignore` do repositório ignora `space_values*.json`.

5. **O arquivo de valores extras de cada exemplo**, `examples/<exemplo>/extra_values.json` no
   clone, é o segundo arquivo do `render`, depois do `space_values.json`. Ele fixa
   `EXAMPLE_PREFIX`, o prefixo do exemplo no bucket do projeto, `shared/exemplos/<exemplo>`, a
   pasta `~/shared/exemplos/<exemplo>/` de um espaço, onde os passos abaixo gravam; quem o troca
   troca esses caminhos. Um valor igual ao próprio nome entre `<` e `>`, como
   `"REDSHIFT_WORKGROUP": "<REDSHIFT_WORKGROUP>"`, está por preencher, e até lá o `render`
   recusa com `nenhum valor para: REDSHIFT_WORKGROUP`. Um valor pode referenciar outros
   placeholders, como o `JOB_IMAGE_URI` do job, que leva a `REGION` do `space_values.json`
   ([Os valores da definição](../awsds_workflows.html#os-valores-da-definicao)). O
   `probe-worker` não tem o arquivo: a definição dele não tem placeholder.

## Os passos no portal

Os mesmos para todos os exemplos, na página *Workflows* do projeto; cada exemplo abaixo diz o
nome, o `.zip` e a definição dele.

1. **Crie um workflow novo e vazio**, com o nome do exemplo.
2. **O `.zip`**, num exemplo que tem um: em *Settings → Storage → Python/Bash Operator Files*,
   envie o arquivo; o campo abaixo passa a mostrar `dev/operatorFiles/<nome>.zip`. Num exemplo
   sem `.zip`, esvazie o campo *Operator files zip S3 location*. Os dois antes do save: sem isso,
   o save falha com `Code not found in specified S3 location`.
3. **A definição**: *Actions → Import definition file*, com o YAML preenchido, e salve. Uma
   importação não substitui um workflow já salvo: apague o antigo antes. Uma versão nova do `.zip`
   pede um envio e um save novos, porque o workflow roda a cópia que o serviço tirou no último
   save ([O `.zip` no workflow](../awsds_workflows.html#o-zip-no-workflow)).
4. **Execute** e abra o log de cada task na execução. Num exemplo com sensor, a amostra tem de
   estar em `inbox/` antes: o sensor espera 10 minutos, e depois disso a execução termina sem erro
   e sem rodar o resto.

## probe-worker

Uma task Bash inline, sem `.zip` e sem placeholder: a definição entra no portal como está, sem o
`render`.

1. **No portal**: workflow `probe-worker`, o campo *Operator files zip S3 location* vazio, a
   definição `examples/probe-worker/probe-worker.yaml` do clone, salve e execute.
2. **Leia** o log de `probe_worker`: `--- disco`, com o `df -h` e o tempo de gravar 1 GiB em
   `/var/tmp`; `--- CPU e memória`; `--- ferramentas`, onde estão `aws`, `tar`, `unzip` e
   `gzip`, ou `ausente`; e `--- pacotes`, o Python, sete pacotes ou `ausente`, e a lista das
   distribuições, que a task também devolve como XCom. No ambiente alvo, em 2026-10-13: 19G livres
   em `/`, 2 vCPUs e 4,7 GiB, só o `gzip`, o Python 3.12.14 e 164 distribuições, em 13,3 s.

## demo-python-operator

Um sensor espera um arquivo em `inbox/`, e a task Python chama `demo_tasks.run`, que imprime com
o que o worker a roda e resume cada CSV da caixa de entrada num JSON em `outbox/<carimbo>/`,
apagando a origem.

1. **Na máquina que empacota**, o `.zip` e a definição:

   ```shell
   (cd examples/awsds-demo-job && uv lock)
   awsds-workflows package-task examples/awsds-demo-job \
       examples/demo-python-operator/demo_tasks.py /tmp/demo-python-operator.zip
   awsds-workflows render examples/demo-python-operator/demo-python-operator.yaml \
       --values-file space_values.json \
       --values-file examples/demo-python-operator/extra_values.json > /tmp/demo-python-operator.yaml
   ```

   O `package-task` imprime o tamanho, 274 KB em 2026-10-13, e a raiz: `awsds_demo_job`,
   `demo_tasks.py`, `petl`, `six.py` e os `dist-info`; o `boto3` e o PyYAML, que o worker tem,
   ficam de fora. Um `nenhum valor para: ...` do `render` é um placeholder sem valor no
   `space_values.json`, ou um arquivo a menos na linha de comando: pare.

2. **No espaço**, a amostra na caixa de entrada:

   ```shell
   mkdir -p ~/shared/exemplos/demo-python-operator/inbox
   cp sample.csv ~/shared/exemplos/demo-python-operator/inbox/
   ```

3. **No portal**: workflow `demo-python-operator`, o `.zip` `/tmp/demo-python-operator.zip`, a
   definição `/tmp/demo-python-operator.yaml`, salve e execute.

4. **Leia** o log de `run_project`:

   ```
   python 3.12.14 em /opt/mwaa-serverless-venv/bin/python3
   sys.path: [...]
   credencial: arn:aws:sts::<conta>:assumed-role/<papel do projeto>/AmazonMWAAServerless
   import petl: 1.7.28 de /usr/local/airflow/dags/petl/__init__.py
   import six: <versão> de <caminho>
   import yaml: 6.0.2 de /opt/mwaa-serverless-venv/lib64/python3.12/site-packages/yaml/__init__.py
   sample.csv: 10 linhas -> s3://<bucket>/<domínio>/<projeto>/shared/exemplos/demo-python-operator/outbox/<carimbo>Z/sample.result.json; origem apagada
   1 objeto(s) processado(s)
   ```

   e, do Airflow, `Done. Returned value was: 1`. O `petl` vem do `.zip` e o PyYAML do worker,
   que numa task Python vence a cópia do `.zip`. O `six` está nos dois, 1.16.0 no `.zip` e 1.17.0
   no worker: a linha dele diz qual venceu, e o `sys.path` diz por quê; as duas ainda não foram
   lidas.

5. **No espaço**, o hash do resultado, o mesmo do laboratório (2026-10-11) e do ambiente alvo
   (2026-10-12):

   ```shell
   sha256sum ~/shared/exemplos/demo-python-operator/outbox/*/sample.result.json
   ```

   `1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191`. A task apagou a amostra
   de `inbox/`: outra execução pede outro `cp`.

No ambiente alvo, em 2026-10-12 às 19:16 UTC, a task rodou em 2,4 s.

## demo-bash-operator

O mesmo projeto, numa task Bash: `run_command` roda o modo S3 do projeto com `python3 -m` a partir
do `.zip`; `reach_pypi` roda o script `reach_pypi.sh` do `.zip`, que tenta a PyPI; e `probe_bash`,
sem dependência, mostra como o worker roda um script e um módulo do `.zip`.

1. **Na máquina que empacota**, o `.zip`, sem módulo de entrada e com os dois scripts, e a
   definição:

   ```shell
   (cd examples/awsds-demo-job && uv lock)
   awsds-workflows package-task examples/awsds-demo-job /tmp/demo-bash-operator.zip \
       --include examples/demo-bash-operator/probe.sh \
       --include examples/demo-bash-operator/reach_pypi.sh
   awsds-workflows render examples/demo-bash-operator/demo-bash-operator.yaml \
       --values-file space_values.json \
       --values-file examples/demo-bash-operator/extra_values.json > /tmp/demo-bash-operator.yaml
   ```

   A raiz traz `probe.sh` e `reach_pypi.sh`, com o bit de execução, além do projeto, do `petl` e
   do `six.py`.

2. **No espaço**, a amostra na caixa de entrada:

   ```shell
   mkdir -p ~/shared/exemplos/demo-bash-operator/inbox
   cp sample.csv ~/shared/exemplos/demo-bash-operator/inbox/
   ```

3. **No portal**: workflow `demo-bash-operator`, o `.zip` `/tmp/demo-bash-operator.zip`, a
   definição `/tmp/demo-bash-operator.yaml`, salve e execute.

4. **Leia** os quatro logs. A execução termina `FAILED` por causa de `reach_pypi`, que sai com 1
   quando nada respondeu: "sem internet" é o resultado esperado, e as outras três tasks terminam
   em sucesso.

   - `run_command`: `cwd /var/tmp/airflowtmp...` e o `PYTHONPATH`, que começa por
     `/usr/local/airflow/dags`; depois, as linhas da task Python,
     `python 3.12.14 em /opt/mwaa-serverless-venv/bin/python3`,
     `sample.csv: 10 linhas -> s3://.../outbox/<carimbo>Z/sample.result.json; origem apagada` e
     `1 objeto(s) processado(s)`.
   - `probe_bash`: os arquivos do `.zip` em `/usr/local/airflow/dags` com os modos do `.zip`, os
     scripts `-rwxr-xr-x`; a linha `usage:` do módulo, sem `cd`;
     `petl 1.7.28 de /usr/local/airflow/dags/petl/__init__.py` e
     `six 1.16.0 de /usr/local/airflow/dags/six.py`, porque numa task Bash o `.zip` vence o
     worker; e `probe.sh` com `$0 = /usr/local/airflow/dags/probe.sh`, pelas duas formas.
   - `reach_pypi`: `proxy:` vazio, `resolve: pypi.org -> <endereço>`,
     `urllib: URLError(OSError(101, 'Network is unreachable'))`, `urllib: pypi.org não respondeu`,
     o `pip` 23.2.1 do worker com `[Errno 101] Network is unreachable`,
     `pip: o download falhou, saída 1` e `Command exited with return code 1`. Onde um firewall de
     DNS recusa o nome, a falha vem em segundos, com `resolve: pypi.org falhou`.

5. **No espaço**, o hash do resultado, o mesmo da task Python:

   ```shell
   sha256sum ~/shared/exemplos/demo-bash-operator/outbox/*/sample.result.json
   ```

No ambiente alvo, em 2026-10-12, cada task rodou num worker próprio: `probe_bash` em 11,7 s,
`run_command` em 9,2 s e `reach_pypi` em 116 s, 43 s do `urllib` e 64 s do `pip`.

## demo-devenv-job

Um sensor espera um arquivo em `inbox/`; `run_project` cria um job de processamento do
SageMaker, que baixa o `.tar.gz` do projeto e a caixa de entrada, extrai o projeto no volume do
job, roda o `python -m awsds_demo_job` da pasta extraída sem rede e envia a saída ao S3; e
`remove_source` apaga a caixa de entrada, porque um contêiner isolado não alcança o S3. A entrada
de código é um objeto só: o `.tar.gz` da pasta do projeto, gravado pelo `prepare-offline` com o
próprio CPython 3.12 e as dependências dentro dela, que roda de qualquer caminho com
`.venv/bin/python`, sem o interpretador da imagem
([A pasta do projeto preparada num `.tar.gz`](../awsds_workflows.html#a-pasta-do-projeto-preparada-num-targz)).
Um projeto que usa o ambiente da imagem e leva só o que ela não tem passa pelo `package-job`
([A pasta de código com `package-job`](../awsds_workflows.html#a-pasta-de-codigo-com-package-job)).

Antes do primeiro job:

- **A permissão do projeto.** O operador descreve o job antes de criá-lo e põe nele a etiqueta
  do projeto, e o papel do projeto, como o blueprint o cria, não deixa nem uma coisa nem outra:
  sem a política de [A permissão do projeto](../awsds_workflows.html#a-permissao-do-projeto), a
  execução para em `AccessDeniedException` em `sagemaker:DescribeProcessingJob`, como no ambiente
  alvo em 2026-10-12. Quem aplica a política é a infraestrutura, no Terraform do projeto ou à
  mão.
- **A conta do registro da imagem**, em `examples/demo-devenv-job/extra_values.json`. A imagem
  padrão é a SageMaker Distribution 4.5, no registro da região, cuja conta um parâmetro público
  do SSM dá, num espaço:

  ```shell
  aws ssm get-parameter --name /aws/service/sagemaker-distribution/ecr-account-id \
      --query Parameter.Value --output text --cli-connect-timeout 5
  ```

  Na máquina que empacota, preencha `SMD_REGISTRY_ACCOUNT` no arquivo com essa conta; o resto
  já está nele:

  ```json
  {
    "EXAMPLE_PREFIX": "shared/exemplos/demo-devenv-job",
    "SMD_REGISTRY_ACCOUNT": "<SMD_REGISTRY_ACCOUNT>",
    "JOB_IMAGE_URI": "<SMD_REGISTRY_ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/sagemaker-distribution-prod:4.5.2-cpu"
  }
  ```

  O `JOB_IMAGE_URI` sai montado com essa conta e a `REGION` do `space_values.json`. A
  `4.5.2-cpu` é a tag mais nova da 4.5 no ECR público (lida em 2026-10-12)
  ([A imagem do job](../awsds_workflows.html#a-imagem-do-job)); o Python dela não entra, porque
  o `.tar.gz` traz o seu.
- **Um projeto com chave KMS própria** acrescenta ao `config` da definição, antes do `render`, a
  chave do volume e a da saída, com o `PROJECT_KEY_ID` que o `space_values.json` traz:

  ```yaml
  ProcessingResources:
    ClusterConfig:
      VolumeKmsKeyId: arn:aws:kms:<REGION>:<ACCOUNT_ID>:key/<PROJECT_KEY_ID>
  ProcessingOutputConfig:
    KmsKeyId: arn:aws:kms:<REGION>:<ACCOUNT_ID>:key/<PROJECT_KEY_ID>
  ```

1. **Na máquina que empacota**, num Linux x86_64, a plataforma do job, trave o projeto, grave o
   `.tar.gz` dele e renderize a definição com os dois arquivos de valores:

   ```shell
   (cd examples/awsds-demo-job && uv lock)
   awsds-workflows prepare-offline examples/awsds-demo-job /tmp/awsds-demo-job.tar.gz
   awsds-workflows render examples/demo-devenv-job/demo-devenv-job.yaml \
       --values-file space_values.json \
       --values-file examples/demo-devenv-job/extra_values.json > /tmp/demo-devenv-job.yaml
   ```

   O `prepare-offline` copia o projeto para uma pasta temporária, sem alterar a do exemplo,
   recria lá a `.venv/` com o CPython 3.12 que o `uv` baixa para dentro dela, o projeto instalado
   como pacote e as dependências de execução, torna relativo cada link, grava o `.tar.gz` com a
   raiz `awsds-demo-job/` e prova, extraindo-o noutra pasta temporária, que o `.venv/bin/python`
   de lá roda sem o `uv`. Ele imprime o tamanho do arquivo e o da pasta extraída, com a versão do
   interpretador: em 2026-10-13, `34111121 bytes, 100119806 extraídos, com o CPython 3.12.13 em
   Linux x86_64`, em 14 s. Noutra plataforma ele para antes de qualquer download
   ([A pasta do projeto preparada num `.tar.gz`](../awsds_workflows.html#a-pasta-do-projeto-preparada-num-targz)).

   Com a conta do registro por preencher, o `render` recusa: `nenhum valor para:
   SMD_REGISTRY_ACCOUNT`; sem o segundo arquivo, `nenhum valor para: EXAMPLE_PREFIX,
   JOB_IMAGE_URI`.

2. **Leve ao espaço** o `/tmp/awsds-demo-job.tar.gz` e, lá, copie-o para a entrada de código e
   confira no S3, com o bucket, o domínio e o projeto do `space_values.json`:

   ```shell
   mkdir -p ~/shared/exemplos/demo-devenv-job/code
   cp awsds-demo-job.tar.gz ~/shared/exemplos/demo-devenv-job/code/
   aws s3 ls s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/exemplos/demo-devenv-job/code/
   ```

   O `aws s3 ls` tem de listar o `awsds-demo-job.tar.gz` com o tamanho que o `prepare-offline`
   imprimiu, além do marcador de pasta de zero bytes; se não listar, pare: a cópia não chegou ao
   S3, de onde o job lê o prefixo inteiro a cada execução. Uma versão nova do projeto é o
   `prepare-offline` de novo e a cópia por cima do objeto, que a execução seguinte já lê.

3. **No espaço**, a amostra na caixa de entrada, um arquivo por vez, porque `remove_source` apaga
   o prefixo inteiro:

   ```shell
   mkdir -p ~/shared/exemplos/demo-devenv-job/inbox
   cp sample.csv ~/shared/exemplos/demo-devenv-job/inbox/
   ```

4. **No portal**: workflow `demo-devenv-job`, o campo *Operator files zip S3 location* vazio, a
   definição `/tmp/demo-devenv-job.yaml`, salve e execute. O formulário do editor não expressa o
   `config` inteiro do job: só a importação o guarda.

5. **Leia** o log de `run_project`, que imprime o `config` do job e espera o fim dele, e o log do
   contêiner, no grupo `/aws/sagemaker/ProcessingJobs`, no console do CloudWatch ou num espaço:

   ```shell
   aws logs tail /aws/sagemaker/ProcessingJobs --log-stream-name-prefix demo-devenv- --since 2h
   ```

   O contêiner imprime o `id` e o `ls -ln` das pastas montadas, extrai o `.tar.gz` em
   `/opt/ml/processing/code/` e então
   `python 3.12.13 em /opt/ml/processing/code/awsds-demo-job/.venv/bin/python`, com a versão
   que o `uv` baixou ao preparar,
   `sample.csv: 10 linhas -> /opt/ml/processing/outbox/sample.result.json` e
   `1 arquivo(s) processado(s)`; depois, `remove_source` esvazia `inbox/`.

6. **No espaço**, o hash do resultado, o mesmo dos outros dois `demo-*`:

   ```shell
   sha256sum ~/shared/exemplos/demo-devenv-job/outbox/*/sample.result.json
   ```

No ambiente alvo, em 2026-10-12 às 18:12 UTC, a execução passou pelo sensor e parou na
permissão, antes de existir um job, com a pasta do projeto expandida no S3 como entrada de
código: do pull da imagem à gravação da saída, o caminho do job não foi medido lá, nem o usuário
do contêiner da imagem padrão, e o `.tar.gz` ainda não rodou num job. No laboratório, em
2026-10-11, com uma imagem customizada e a chave KMS do projeto, a definição sobre a pasta
expandida rodou em cerca de 15 minutos e 0,03 USD. Na máquina que empacota, em 2026-10-13, o
`.tar.gz` extraído noutra pasta, por um usuário sem privilégio e sem `uv` nem rede, escreveu o
resumo com o mesmo sha256, em 1,3 s de extração para 100 MB.

## redshift-unload

A task chama `redshift_unload.unload`, que manda três comandos numa sessão da Data API do Redshift
Serverless, com as credenciais do worker: `SELECT current_user`, o `UNLOAD` da consulta para o
S3, em Parquet, e `SELECT pg_last_unload_count()`. Antes:

- **Os nomes do Redshift**, por preencher em `examples/redshift-unload/extra_values.json`, na
  máquina que empacota: `REDSHIFT_WORKGROUP`, o workgroup do Redshift Serverless;
  `REDSHIFT_DATABASE`, o banco em que a sessão entra; e `REDSHIFT_TABLE`, a tabela em três
  partes, `<banco do datashare>.<esquema>.<tabela>`, porque a consulta é
  `SELECT * FROM <REDSHIFT_TABLE>` e, numa sessão da Data API, uma tabela de um datashare leva o
  nome assim. Preenchido:

  ```json
  {
    "EXAMPLE_PREFIX": "shared/exemplos/redshift-unload",
    "REDSHIFT_WORKGROUP": "meu-workgroup",
    "REDSHIFT_DATABASE": "dev",
    "REDSHIFT_TABLE": "meu_banco.meu_esquema.minha_tabela"
  }
  ```
- **O acesso do usuário do projeto.** O worker entra no Redshift como o usuário do projeto,
  `IAMR:user-project@<projeto>`, e o espaço como o usuário da pessoa: um teste no espaço não prova
  a permissão do worker. Quem concede dá o acesso ao banco do datashare, conectado a um banco
  local, como o `dev`, sem um `USE <banco do datashare>` antes:

  ```sql
  GRANT USAGE ON DATABASE <banco do datashare> TO "IAMR:user-project@<projeto>";
  ```

  No ambiente alvo, em 2026-10-13, o workflow parou em
  `Permission denied to query database created from datashare` até esse `GRANT`, que bastou
  sozinho, o que indica um banco criado sem `WITH PERMISSIONS` (inferido). Num banco criado
  `WITH PERMISSIONS`, o usuário também precisa de `USAGE` no esquema e de `SELECT` nas tabelas. A
  primeira linha do log de cada execução diz quem precisa da permissão.

1. **Na máquina que empacota**, o `.zip`, só com o módulo na raiz, e a definição:

   ```shell
   python3 -m zipfile -c /tmp/redshift-unload.zip examples/redshift-unload/redshift_unload.py
   awsds-workflows render examples/redshift-unload/redshift-unload.yaml \
       --values-file space_values.json \
       --values-file examples/redshift-unload/extra_values.json > /tmp/redshift-unload.yaml
   ```

   O módulo só usa o `boto3` que o worker traz, então o `.zip` dispensa o `package-task`. Com um
   nome do Redshift por preencher, o `render` recusa nomeando-o.

2. **No portal**: workflow `redshift-unload`, o `.zip` `/tmp/redshift-unload.zip`, a definição
   `/tmp/redshift-unload.yaml`, salve e execute. Não há sensor nem job: a task roda na hora, e não
   depende da permissão do projeto para jobs.

3. **Leia** o log de `unload`: `usuário do banco: IAMR:user-project@<projeto>`,
   `<n> linha(s) descarregada(s) em <s> s sob s3://.../shared/exemplos/redshift-unload/<data-hora>/`
   e `Done. Returned value was: <n>`.

4. **No espaço**, os arquivos, numa pasta por execução, com a data e a hora dela:

   ```shell
   ls ~/shared/exemplos/redshift-unload/*/
   ```

   Os `.parquet` e o `manifest`. Com zero linhas, o `UNLOAD` não grava nada, e a contagem diz 0.
   As outras falhas estão na tabela do `README.md` do exemplo.

Para testar a função antes, num espaço, copie `redshift_unload.py` para lá e rode o exemplo da
docstring dele, com um destino de teste. No ambiente alvo, em 2026-10-13, ela descarregou 101
linhas em 5,5 s no espaço e no workflow, numa task de 23,4 s.

## houseprice-etl

Uma task `GlueJobOperator` cria o job do Glue `houseprice-etl-<projeto>` com o script do exemplo,
ou o atualiza se ele já existe, e o executa: o job lê um Parquet de `entrada/` e grava os dados em
CSV, sem cabeçalho, acrescentando a `saida/`. O workflow não tem task Python nem Bash, e por isso
não tem `.zip`. O script e o workflow também são o conteúdo de uma aplicação da CLI de CI/CD do
SageMaker Unified Studio, a `aws-smus-cicd-cli` 1.0.9, que tem os passos dela em
[A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd). O porquê de cada parâmetro da task
está no `README.md` do exemplo.

1. **Na máquina que empacota**, a definição e o modelo do job:

   ```shell
   awsds-workflows render examples/houseprice-etl/houseprice-etl.yaml \
       --values-file space_values.json \
       --values-file examples/houseprice-etl/extra_values.json > /tmp/houseprice-etl.yaml
   awsds-workflows render examples/houseprice-etl/job.json \
       --values-file space_values.json \
       --values-file examples/houseprice-etl/extra_values.json > /tmp/houseprice-etl.job.json
   ```

   O `job.json` é a entrada do `CreateJob` que a task faz, para o passo 6, se a primeira execução
   não conseguir criar o job.

2. **Leve ao espaço** o `examples/houseprice-etl/aplicacao/jobs/etl_houseprice.py` do clone e,
   lá, copie-o para o caminho que a definição passa ao job:

   ```shell
   mkdir -p ~/shared/exemplos/houseprice-etl/jobs
   cp etl_houseprice.py ~/shared/exemplos/houseprice-etl/jobs/
   ```

3. **No espaço**, um Parquet em `entrada/house-price.parquet`: o que um fluxo do Visual ETL do
   projeto lê, ou a amostra da preparação convertida:

   ```shell
   python -c "import pandas; pandas.read_csv('sample.csv').to_parquet('house-price.parquet')"
   mkdir -p ~/shared/exemplos/houseprice-etl/entrada
   cp house-price.parquet ~/shared/exemplos/houseprice-etl/entrada/
   ```

   O pandas e o pyarrow vêm com a imagem padrão do espaço (inferido); sem eles, o comando para em
   `ModuleNotFoundError`, e qualquer Parquet serve.

4. **No portal**: workflow `houseprice-etl`, o campo *Operator files zip S3 location* vazio, a
   definição `/tmp/houseprice-etl.yaml`, salve e execute.

5. **Leia** o log de `run_glue_job`. Na primeira execução,
   `Checking if job already exists: houseprice-etl-<projeto>`,
   `Creating job: houseprice-etl-<projeto>`, uma linha
   `Polling for AWS Glue Job houseprice-etl-<projeto> current run state with status RUNNING` a cada
   6 s e, no fim, `Exiting Job jr_... Run State: SUCCEEDED` e
   `AWS Glue Job: houseprice-etl-<projeto> status: SUCCEEDED. Run Id: jr_...`. Execute de novo, sem
   mudar nada: a segunda execução encontra o job e não tem a linha `Creating job`. Cada execução
   acrescenta arquivos `part-*.csv`, sem cabeçalho, à saída:

   ```shell
   ls ~/shared/exemplos/houseprice-etl/saida/
   head -3 ~/shared/exemplos/houseprice-etl/saida/part-*.csv
   ```

   Na página *Data processing jobs* do projeto, confira se o job aparece, com as execuções e os
   logs. A API cria o job sem `JobMode`, que o Glue trata como `SCRIPT`, o tipo *Code* da página
   (inferido).

6. **Se a primeira execução parar em `AccessDeniedException` no `GetJob`**, leve ao espaço o
   `/tmp/houseprice-etl.job.json`, crie o job uma vez e execute o workflow de novo:

   ```shell
   aws glue create-job --cli-input-json file://houseprice-etl.job.json
   ```

   As outras falhas estão na tabela do `README.md` do exemplo.

### A aplicação pela CLI de CI/CD

A CLI leva a aplicação do stage `dev` do `manifest.yaml` ao stage `test`, dois projetos do mesmo
domínio. Ela chama o DataZone, o S3 e o MWAA Serverless, e roda na máquina que empacota ou num
runner de CI, com rede até as APIs da AWS e credenciais do domínio: um espaço do ambiente alvo não
alcança a PyPI, para instalá-la, nem o MWAA Serverless, que não tem endpoint lá (inferido). Esta
parte ainda não rodou num projeto.

1. **Na máquina que empacota**, uma cópia da aplicação fora do clone, com as sub-redes
   preenchidas:

   ```shell
   cp -r examples/houseprice-etl/aplicacao /tmp/houseprice-etl
   awsds-workflows render examples/houseprice-etl/aplicacao/workflows/houseprice-etl.yaml \
       --values-file space_values.json > /tmp/houseprice-etl/workflows/houseprice-etl.yaml
   ```

   O `render` preenche só `<SUBNET_AZ1>` e `<SUBNET_AZ2>`, para as quais a CLI não tem variável;
   as variáveis dela, como `{proj.id}`, ficam para o `deploy`. Com as sub-redes da conta, a cópia
   é o começo do repositório da aplicação, que não é este.

2. **Os nomes das conexões.** O manifest e o workflow usam `default.s3_shared` e
   `default.workflow_serverless`, os nomes que a CLI espera, e o projeto pode ter outros: um job
   do Visual ETL usa a conexão `project.spark.compatibility`. Leia os do projeto na página dele
   ou, num espaço, com:

   ```shell
   aws datazone list-connections --domain-identifier <DOMAIN_ID> \
       --project-identifier <PROJECT_ID> --query 'items[].[name,type]' --output text
   ```

   e troque na cópia, no manifest e no workflow, os que forem outros.

3. **Na máquina que empacota**, a CLI, o `bundle` e o `deploy`, na pasta da cópia, com o domínio,
   a região e os nomes dos dois projetos, que o manifest lê do ambiente:

   ```shell
   uv tool install aws-smus-cicd-cli==1.0.9
   cd /tmp/houseprice-etl
   export DOMAIN_ID=<DOMAIN_ID> DOMAIN_REGION=<REGION>
   export DEV_PROJECT_NAME=<projeto de dev> TEST_PROJECT_NAME=<projeto de teste>
   aws-smus-cicd-cli bundle --manifest manifest.yaml --targets dev
   aws-smus-cicd-cli deploy --manifest manifest.yaml --targets test \
       --bundle-archive-path artifacts/houseprice-etl.zip
   ```

   O `bundle` grava `artifacts/houseprice-etl.zip`, com `jobs/etl_houseprice.py` e
   `workflows/houseprice-etl.yaml` lidos do disco. O `deploy` copia as duas pastas para
   `shared/exemplos/houseprice-etl/` do projeto de teste, troca as variáveis do workflow pelos
   valores desse projeto, cria o workflow `houseprice_etl_<projeto de teste>_houseprice_etl` e o
   executa uma vez, imprimindo os logs: essa execução cria o job. O Parquet do passo 3 tem de
   estar em `shared/exemplos/houseprice-etl/entrada/` do projeto de teste antes do `deploy`, e uma
   execução que pare no `GetJob` pede o passo 6 no projeto de teste.

O exemplo ainda não rodou num projeto; o que foi conferido fora da AWS, em 2026-10-14, está no
`README.md` dele.

## Limpeza

No portal, apague os workflows; no espaço, `rm -r ~/shared/exemplos/`. O grupo de logs de cada
workflow e os `.zip` em `dev/operatorFiles/` ficam
([Limpeza](../awsds_workflows.html#limpeza)). O job do `houseprice-etl` se apaga na página
*Data processing jobs* ou, num espaço, com
`aws glue delete-job --job-name houseprice-etl-<PROJECT_ID>`.
