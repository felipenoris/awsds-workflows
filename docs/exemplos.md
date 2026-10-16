Esta página é o roteiro dos exemplos da pasta
[`examples/`](https://github.com/felipenoris/awsds-workflows/tree/main/examples) do repositório, na
ordem em que cada comando roda. Cada exemplo é uma aplicação da CLI de CI/CD do SageMaker Unified
Studio, a `aws-smus-cicd-cli` 1.0.9: uma pasta com o `manifest.yaml`, o workflow em `workflows/`,
na notação da CLI, e o código. A CLI leva a pasta a um projeto, cria o workflow lá e o executa; o
portal é o outro caminho, com o mesmo workflow preenchido pelo `render`. Cada passo diz onde ele
acontece:

- **na máquina que empacota**: um Linux com internet, com o pacote e a CLI instalados e o
  repositório clonado; os comandos rodam na raiz do clone, ou na pasta do exemplo quando o passo
  diz;
- **no espaço**: um terminal de um espaço do projeto no SageMaker Unified Studio, JupyterLab ou
  Code Editor; a pasta `~/shared/` dele é o prefixo `shared/` do projeto no bucket, então um `cp`
  para lá é um envio ao S3;
- **no portal**: a página *Workflows* do projeto no SageMaker Unified Studio.

Os termos estão em [Os conceitos](../awsds_workflows.html#os-conceitos). O que cada exemplo
mostra, task por task, o manifest dele e as leituras inteiras de cada execução estão no
`README.md` da pasta dele; o que cada um leu no laboratório e no ambiente alvo, com as datas,
está em [As notas do laboratório](lab_notes.html#os-exemplos).

| Exemplo | O que ele mostra | O que ele pede além do projeto |
|---|---|---|
| [probe-worker](#probe-worker) | o que o worker tem, numa task Bash inline | nada |
| [demo-python-operator](#demo-python-operator) | uma task Python sobre o `.zip` do `package-task` | o `.zip` em `code/` e a amostra em `inbox/` |
| [demo-bash-operator](#demo-bash-operator) | uma task Bash sobre o mesmo `.zip`, com dois scripts, e a prova de que o worker não alcança a PyPI | o `.zip` em `code/` e a amostra em `inbox/` |
| [demo-devenv-job](#demo-devenv-job) | um job de processamento na imagem padrão do SageMaker, sobre o `.tar.gz` da pasta do projeto preparada | a permissão do projeto, o `.tar.gz` em `src/`, a rede do projeto e a imagem no shell, e a amostra em `inbox/` |
| [redshift-unload](#redshift-unload) | uma task Python que descarrega uma consulta ao Redshift Serverless no S3 | o `.zip` em `code/`, os nomes do Redshift no shell e o acesso do usuário do projeto ao banco |
| [houseprice-etl](#houseprice-etl) | um job do Visual ETL: a task cria ou atualiza o job do Glue e o executa | um Parquet em `entrada/`, as sub-redes no shell e o job criado uma vez com o `job.json` |

## A preparação

1. **Na máquina que empacota**, instale o pacote:

   ```shell
   uv tool install git+https://github.com/felipenoris/awsds-workflows
   ```

2. **Instale a CLI de CI/CD**, na versão que os exemplos seguem:

   ```shell
   uv tool install aws-smus-cicd-cli==1.0.9
   ```

3. **Clone o repositório** e entre na pasta dele, onde rodam os comandos desta página:

   ```shell
   git clone https://github.com/felipenoris/awsds-workflows
   cd awsds-workflows
   ```

4. **Confira o pacote**:

   ```shell
   awsds-workflows --help
   ```

5. **Confira a CLI**, que imprime `aws-smus-cicd-cli 1.0.9`:

   ```shell
   aws-smus-cicd-cli --version
   ```

6. **Leve ao espaço** dois arquivos do clone, pelo botão de upload do JupyterLab:
   `scripts/space_values.py` e `examples/awsds-demo-job/sample.csv`.

7. **No espaço**, grave os valores do projeto:

   ```shell
   python space_values.py > space_values.json
   ```

   Num projeto sem chave KMS própria, o aviso `o ambiente Tooling não tem kmsKeyArn` no stderr é
   normal ([Os valores de dentro de um espaço](../awsds_workflows.html#os-valores-de-dentro-de-um-espaco)).

8. **No espaço**, confira o JSON:

   ```shell
   cat space_values.json
   ```

   Ele traz `ACCOUNT_ID`, `DOMAIN_ID`, `PROJECTS_BUCKET`, `PROJECT_ID`, `PROJECT_ROLE_NAME`,
   `PROJECT_SG`, `REGION`, `SUBNET_AZ1` e `SUBNET_AZ2`, e `PROJECT_KEY_ID` quando o projeto tem
   chave KMS própria.

9. **No espaço**, confira a montagem do `~/shared/`:

   ```shell
   mount | grep -i shared
   ```

   > [!WARNING]
   > **O `mount` tem de mostrar uma linha `s3fs on /mnt/custom-file-systems/s3/shared`**, a
   > montagem que faz do `~/shared/` o bucket do projeto. Sem ela, os passos que gravam em
   > `~/shared/` não valem.

10. **Copie o `space_values.json` para a máquina que empacota**, pelo download do JupyterLab ou
    colando a saída do `cat` num arquivo.

> [!CAUTION]
> **Os ids da conta ficam fora do git.** O `space_values.json` os leva, e o `.gitignore` do
> repositório ignora `space_values*.json`. O que o `render` grava também os leva: vai para `/tmp`,
> nunca para o repositório.

**As variáveis do shell.** O manifest de cada exemplo lê do shell o que marca como `${NOME}`: o
domínio e os dois projetos, em todos, e as variáveis de stage de cada um, o que nenhum projeto
tem. Os dois stages do manifest são dois projetos do mesmo domínio: `dev`, onde a aplicação se
desenvolve, e `test`, onde ela roda como uma esteira a rodaria. Na máquina que empacota, exporte o
domínio e a região, do `space_values.json`:

```shell
export DOMAIN_ID=<DOMAIN_ID> DOMAIN_REGION=<REGION>
```

e os nomes dos dois projetos, os que o portal mostra, não os ids; com um projeto só, o nome dele
nas duas variáveis, porque a CLI lê o manifest inteiro, e a perna `test` se pula:

```shell
export DEV_PROJECT_NAME=<projeto de dev> TEST_PROJECT_NAME=<projeto de teste>
```

> [!WARNING]
> **Uma `${NOME}` do manifest sem valor no shell para a CLI em qualquer comando**, com
> `Variable ${NOME} is not set and has no default value`.

**A credencial.** A CLI entra na conta pelo `boto3`, com a credencial das variáveis `AWS_*` do
shell, e não lê o cache em que o `aws` guarda a credencial de um perfil SSO: exporte-a de um perfil
do `aws` que alcança o domínio, sem imprimi-la:

```shell
eval "$(aws configure export-credentials --profile <perfil> --format env)"
```

Uma credencial vencida para a CLI em `Token has expired and refresh failed`: exporte de novo.

## A aplicação pela CLI de CI/CD

Os mesmos passos para todos os exemplos, na máquina que empacota; cada exemplo abaixo diz o que
vem antes, o que pôr no shell e o que ler. A CLI chama o DataZone, o S3 e o MWAA Serverless, com
rede até as APIs da AWS e a credencial da preparação: um espaço do ambiente alvo não alcança a
PyPI, para instalá-la, nem o MWAA Serverless, que não tem endpoint lá (inferido).

**O manifest** de cada exemplo tem a mesma forma:

- `content.storage`: as pastas que vão ao projeto, lidas do disco ao lado do manifest,
  `workflows/` em todos e `code/`, `src/` ou `glue/` conforme o exemplo;
- `content.workflows`: o workflow e, num exemplo com task Python ou Bash, o `.zip` de `code/`
  como `code`, que a CLI passa ao workflow;
- `stages`: `dev` e `test`, cada um com o nome do projeto, o domínio, as variáveis de stage em
  `environment_variables`, as ações de `bootstrap`, `workflow.create` nos dois e `workflow.run`
  com `trailLogs: true` no `test`, e o destino de cada pasta, `exemplos/<exemplo>/<pasta>` na
  conexão `default.s3_shared`, a pasta `shared/` do projeto, a mesma `~/shared/` de um espaço.

1. **Entre na pasta do exemplo**, onde o `manifest.yaml` está:

   ```shell
   cd examples/<exemplo>
   ```

2. **Confira a aplicação**, sem AWS:

   ```shell
   awsds-workflows lint .
   ```

   Ele lê o manifest, o workflow e os scripts das pastas copiadas contra as regras de
   [O lint](../awsds_workflows.html#o-lint), e imprime `ok` com o número de arquivos lidos, ou
   cada recusa numa linha, `arquivo: regra: motivo`, e termina com 1. Uma recusa aqui pararia o
   `deploy` ou a execução.

3. **Confira o manifest e o acesso aos projetos**:

   ```shell
   aws-smus-cicd-cli describe --manifest manifest.yaml --connect
   ```

   Ele lista os dois stages com o domínio, o projeto e as conexões dele, entre elas
   `default.s3_shared`, com o `s3Uri` da pasta `shared/`, e `default.workflow_serverless`. Um nome
   de projeto errado ou uma credencial vencida param aqui.

4. **Implante no stage `dev`**:

   ```shell
   aws-smus-cicd-cli deploy --manifest manifest.yaml --targets dev --skip-validation --no-events
   ```

   O `deploy` copia as pastas para `shared/exemplos/<exemplo>/` do projeto de dev, sem apagar o
   que já estava lá, e cria o workflow `<exemplo>_<projeto>_<exemplo>`, o nome da aplicação, o do
   projeto e o do workflow unidos por `_`, com cada caractere fora de letras, dígitos e `_`
   trocado por `_`, com as variáveis do projeto preenchidas e as de stage gravadas como
   `{{ params.NOME }}`. Num exemplo com `.zip`, ele o copia para `operatorFiles/` da pasta
   `shared/` do projeto e aponta o workflow para essa cópia. Um `deploy` de novo, com ou sem
   mudança, substitui o workflow inteiro e gasta uma versão dele.

   > [!WARNING]
   > **`--skip-validation` e `--no-events` fazem parte do comando.** A validação que o `deploy`
   > faz antes de agir simula as permissões no IAM sem as chaves de contexto das chamadas reais, e
   > reprova onde uma política as usa, sem escrever nada; o evento que o `deploy` publica no fim
   > não tem quem o trate na CLI 1.0.9, e sem `--no-events` o `deploy` para nele.

   > [!WARNING]
   > **Uma `{env.NOME}` do workflow fora do `environment_variables` do stage derruba o
   > `deploy`** com `Failed to resolve variables`: os exemplos declaram as variáveis de stage nos
   > dois stages, e o shell precisa de todas antes do `deploy` e do `run`.

5. **Execute no stage `dev`**:

   ```shell
   aws-smus-cicd-cli run --manifest manifest.yaml --targets dev --workflow <exemplo>
   ```

   O `--workflow` é o nome do workflow no manifest, o do exemplo. A CLI imprime o nome do
   workflow no projeto, o ARN dele e, em `Run ID`, o id da execução, e passa como parâmetros da
   execução as variáveis de stage lidas do shell nessa hora: um valor novo é um `export` e um
   `run` de novo, sem `deploy`.

   > [!IMPORTANT]
   > **Num exemplo com sensor, a amostra tem de estar em `inbox/` antes do `run`**: o sensor espera
   > 10 minutos, e depois disso a execução termina sem erro e sem rodar o resto.

6. **Leia a execução** pela API, com o ARN e o id que o `run` imprimiu:

   ```shell
   aws mwaa-serverless get-workflow-run --workflow-arn <ARN> --run-id <RUN_ID>
   ```

   O `RunState` termina em `SUCCESS` ou `FAILED`, e `OverrideParameters` traz as variáveis de
   stage que a execução recebeu
   ([Como ler uma execução](../awsds_workflows.html#como-ler-uma-execucao)). O log de cada task
   está na página da execução, no portal, ou no grupo de logs do workflow,
   `/aws/mwaa-serverless/<domínio>-<projeto>/<workflow>`, num stream por tentativa de task:

   ```shell
   aws logs get-log-events --log-group-name <grupo do workflow> --log-stream-name <stream da task>
   ```

   > [!WARNING]
   > **O `monitor` e o `logs` da CLI 1.0.9 leem uma execução errado**: o `monitor` a mostra
   > `INITIALIZING`, com `Start Time: N/A`, depois de terminada, e o `logs` responde
   > `No log events found` com o stream cheio. O `get-workflow-run` e o `get-log-events` são as
   > leituras.

7. **Leve ao stage `test`**, o segundo projeto, com o bundle, o `.zip` que uma esteira guarda:

   ```shell
   aws-smus-cicd-cli bundle --manifest manifest.yaml --targets test
   ```

   ```shell
   aws-smus-cicd-cli deploy --manifest manifest.yaml --targets test \
       --bundle-archive-path artifacts/<exemplo>.zip --skip-validation --no-events
   ```

   O `bundle` grava `artifacts/<exemplo>.zip` com as pastas do manifest lidas do disco, sem o
   manifest; `artifacts/` fica fora do git. O `deploy` do `test` copia as pastas da pasta do
   manifest, com ou sem o bundle, cria o workflow no projeto de teste, com o papel e a rede dele,
   e o executa uma vez, pela ação `workflow.run` com `trailLogs: true`, que espera o fim da
   execução sem transmitir o log. O que o exemplo pede antes, a amostra em `inbox/`, a permissão,
   o `GRANT` ou o job, o projeto de teste pede também. Sem um segundo projeto, pule este passo.

   > [!WARNING]
   > **`wait: true` sem `trailLogs` derruba a CLI 1.0.9** logo depois de iniciar a execução, com
   > um `TypeError`; os manifests usam `trailLogs: true`.

8. **No portal**, o workflow aparece na página *Workflows* do projeto, só para leitura, com a
   definição preenchida em *View code*: ele se edita no git, e a CLI o reimplanta.

## Os passos no portal

O outro caminho, sem a CLI, na página *Workflows* do projeto; cada exemplo abaixo diz o nome, o
`.zip` e a definição dele.

1. **Na máquina que empacota**, preencha o workflow com os valores do projeto:

   ```shell
   awsds-workflows render examples/<exemplo>/workflows/<exemplo>.yaml \
       --values-file space_values.json > /tmp/<exemplo>.yaml
   ```

   O `render` troca cada variável da CLI pela expressão com placeholders, `{proj.id}` por
   `<PROJECT_ID>` e `{env.NOME}` por `<NOME>`, e preenche com o `space_values.json`
   ([Os valores da definição](../awsds_workflows.html#os-valores-da-definicao)). O
   `demo-devenv-job` e o `redshift-unload` levam um segundo `--values-file`, o `extra_values.json`
   da pasta, um arquivo de modelo com os valores que o espaço não dá: um valor igual ao próprio
   nome entre `<` e `>`, como `"REDSHIFT_WORKGROUP": "<REDSHIFT_WORKGROUP>"`, está por preencher,
   e até lá o `render` recusa com `nenhum valor para: REDSHIFT_WORKGROUP`; um valor pode
   referenciar outros placeholders, como o `JOB_IMAGE_URI` do job, que leva a `REGION` do
   `space_values.json`.

   > [!WARNING]
   > **Um `nenhum valor para: ...` do `render`** é um placeholder sem valor no
   > `space_values.json`, ou um arquivo a menos na linha de comando: pare.

2. **Crie um workflow novo e vazio**, com o nome do exemplo.
3. **O `.zip`**, num exemplo que tem um: em *Settings → Storage → Python/Bash Operator Files*,
   envie o arquivo; o campo abaixo passa a mostrar `dev/operatorFiles/<nome>.zip`. Num exemplo
   sem `.zip`, esvazie o campo *Operator files zip S3 location*.

   > [!WARNING]
   > **O envio ou o campo vazio vêm antes do save**: sem isso, o save falha com
   > `Code not found in specified S3 location`.

4. **A definição**: *Actions → Import definition file*, com o YAML preenchido, e salve. Uma versão
   nova do `.zip` pede um envio e um save novos, porque o workflow roda a cópia que o serviço tirou
   no último save ([O `.zip` no workflow](../awsds_workflows.html#o-zip-no-workflow)).

   > [!WARNING]
   > **Uma importação não substitui um workflow já salvo**: apague o antigo antes.

5. **Execute** e abra o log de cada task na execução.

> [!IMPORTANT]
> **Num exemplo com sensor, a amostra tem de estar em `inbox/` antes de executar**: o sensor espera
> 10 minutos, e depois disso a execução termina sem erro e sem rodar o resto.

Os caminhos no bucket são os da CLI, `shared/exemplos/<exemplo>/`: a amostra, o `.tar.gz`, o
script e o Parquet vão para as mesmas pastas de `~/shared/` pelos dois caminhos.

## probe-worker

Uma task Bash inline, sem `.zip` e sem variável: o workflow entra no portal como está, sem o
`render`.

1. **Pela CLI**, na pasta `examples/probe-worker`, o `deploy` e o `run` de
   [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd), sem variável de stage.
2. **Ou no portal**: workflow `probe-worker`, o campo *Operator files zip S3 location* vazio, a
   definição `examples/probe-worker/workflows/probe-worker.yaml` do clone, salve e execute.
3. **Leia** o log de `probe_worker`:
   - `--- disco`, com o `df -h` e o tempo de gravar 1 GiB em `/var/tmp`;
   - `--- CPU e memória`;
   - `--- ferramentas`, onde estão `aws`, `tar`, `unzip` e `gzip`, ou `ausente`;
   - `--- pacotes`, o Python, sete pacotes ou `ausente`, e a lista das distribuições, que a task
     também devolve como XCom.

> [!NOTE]
> **Estado**: rodou no ambiente alvo, pelo portal; pela CLI ainda não
> ([as notas](lab_notes.html#probe-worker)).

## demo-python-operator

Um sensor espera um arquivo em `inbox/`, e a task Python chama `demo_tasks.run`, que imprime com
o que o worker a roda e resume cada CSV da caixa de entrada num JSON em `outbox/<carimbo>/`,
apagando a origem.

1. **Na máquina que empacota**, trave o projeto:

   ```shell
   (cd examples/awsds-demo-job && uv lock)
   ```

2. **Monte o `.zip`** em `code/` do exemplo, de onde o manifest o sobe:

   ```shell
   awsds-workflows package-task examples/awsds-demo-job \
       examples/demo-python-operator/code/demo_tasks.py \
       examples/demo-python-operator/code/demo-python-operator.zip
   ```

   O `package-task` imprime o tamanho e a raiz: `awsds_demo_job`, `demo_tasks.py`, `petl`,
   `six.py` e os `dist-info`; o `boto3` e o PyYAML, que o worker tem, ficam de fora. O `.zip`
   fica fora do git.

3. **No espaço**, ponha a amostra na caixa de entrada:

   ```shell
   mkdir -p ~/shared/exemplos/demo-python-operator/inbox
   cp sample.csv ~/shared/exemplos/demo-python-operator/inbox/
   ```

4. **Pela CLI**, na pasta `examples/demo-python-operator`, o `deploy` e o `run` de
   [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd), sem variável de stage: o
   `deploy` sobe o `.zip` e aponta o workflow para a cópia dele em `operatorFiles/`.
5. **Ou no portal**: o workflow preenchido pelo `render` de [Os passos no portal](#os-passos-no-portal),
   `/tmp/demo-python-operator.yaml`, o `.zip` do clone,
   `examples/demo-python-operator/code/demo-python-operator.zip`, salve e execute.
6. **Leia** o log de `run_project`:

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
   no worker: a linha dele diz qual venceu, e o `sys.path` diz por quê.

7. **No espaço**, confira o hash do resultado:

   ```shell
   sha256sum ~/shared/exemplos/demo-python-operator/outbox/*/sample.result.json
   ```

   Ele tem de ser `1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191`. A task
   apagou a amostra de `inbox/`: outra execução pede outro `cp`.

> [!NOTE]
> **Estado**: rodou no ambiente alvo, pelo portal, com o hash do laboratório; pela CLI, com o
> `.zip` passado por ela, ainda não, e as linhas do `six` e do `sys.path` ainda não foram lidas
> ([as notas](lab_notes.html#demo-python-operator)).

## demo-bash-operator

O mesmo projeto, numa task Bash: `run_command` roda o modo S3 do projeto com `python3 -m` a partir
do `.zip`; `reach_pypi` roda o script `reach_pypi.sh` do `.zip`, que tenta a PyPI; e `probe_bash`,
sem dependência, mostra como o worker roda um script e um módulo do `.zip`.

1. **Na máquina que empacota**, trave o projeto:

   ```shell
   (cd examples/awsds-demo-job && uv lock)
   ```

2. **Monte o `.zip`** em `code/` do exemplo, sem módulo de entrada e com os dois scripts:

   ```shell
   awsds-workflows package-task examples/awsds-demo-job \
       examples/demo-bash-operator/code/demo-bash-operator.zip \
       --include examples/demo-bash-operator/code/probe.sh \
       --include examples/demo-bash-operator/code/reach_pypi.sh
   ```

   A raiz traz `probe.sh` e `reach_pypi.sh`, com o bit de execução, além do projeto, do `petl` e
   do `six.py`. O `.zip` fica fora do git.

3. **No espaço**, ponha a amostra na caixa de entrada:

   ```shell
   mkdir -p ~/shared/exemplos/demo-bash-operator/inbox
   cp sample.csv ~/shared/exemplos/demo-bash-operator/inbox/
   ```

4. **Pela CLI**, na pasta `examples/demo-bash-operator`, o `deploy` e o `run` de
   [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd), sem variável de stage: o
   `deploy` sobe o `.zip` e aponta o workflow para a cópia dele em `operatorFiles/`.
5. **Ou no portal**: o workflow preenchido pelo `render` de [Os passos no portal](#os-passos-no-portal),
   `/tmp/demo-bash-operator.yaml`, o `.zip` do clone,
   `examples/demo-bash-operator/code/demo-bash-operator.zip`, salve e execute.
6. **Leia** os quatro logs.

   > [!IMPORTANT]
   > **A execução termina `FAILED` por causa de `reach_pypi`**, que sai com 1 quando nada
   > respondeu: "sem internet" é o resultado esperado, e as outras três tasks terminam em sucesso.
   > No stage `test`, o `deploy` espera essa execução e a lê como falha, o esperado.

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

7. **No espaço**, confira o hash do resultado, o mesmo da task Python:

   ```shell
   sha256sum ~/shared/exemplos/demo-bash-operator/outbox/*/sample.result.json
   ```

> [!NOTE]
> **Estado**: rodou no ambiente alvo, pelo portal, cada task num worker próprio; pela CLI ainda
> não ([as notas](lab_notes.html#demo-bash-operator)).

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

> [!WARNING]
> **Sem a permissão do projeto, a execução para antes de existir um job.** O operador descreve o
> job antes de criá-lo e põe nele a etiqueta do projeto, e o papel do projeto, como o blueprint o
> cria, não deixa nem uma coisa nem outra: sem a política de
> [A permissão do projeto](../awsds_workflows.html#a-permissao-do-projeto), a execução para em
> `AccessDeniedException` em `sagemaker:DescribeProcessingJob`. Quem aplica a política é a
> infraestrutura, no Terraform do projeto ou à mão.

Antes do primeiro job, além da permissão:

- **A conta do registro da imagem.** A imagem padrão é a SageMaker Distribution 4.5, no registro
  da região, cuja conta um parâmetro público do SSM dá, num espaço:

  ```shell
  aws ssm get-parameter --name /aws/service/sagemaker-distribution/ecr-account-id \
      --query Parameter.Value --output text --cli-connect-timeout 5
  ```

  O URI da imagem leva essa conta e a `REGION` do `space_values.json`:
  `<SMD_REGISTRY_ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/sagemaker-distribution-prod:4.5.2-cpu`.
  Pela CLI, ele é a variável de stage `JOB_IMAGE_URI`, no shell; pelo portal, preencha
  `SMD_REGISTRY_ACCOUNT` em `examples/demo-devenv-job/extra_values.json`, na máquina que empacota,
  e o `render` o monta:

  ```json
  {
    "SMD_REGISTRY_ACCOUNT": "<SMD_REGISTRY_ACCOUNT>",
    "JOB_IMAGE_URI": "<SMD_REGISTRY_ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/sagemaker-distribution-prod:4.5.2-cpu"
  }
  ```

  A `4.5.2-cpu` é a tag mais nova da 4.5 no ECR público (lida em 2026-10-12)
  ([A imagem do job](../awsds_workflows.html#a-imagem-do-job)); o Python dela não entra, porque
  o `.tar.gz` traz o seu.
- **Um projeto com chave KMS própria** acrescenta ao `config` do workflow, antes do `deploy` ou
  do `render`, a chave do volume e a da saída, com o ARN dela numa variável de stage:

  ```yaml
  ProcessingResources:
    ClusterConfig:
      VolumeKmsKeyId: "{env.PROJECT_KEY_ARN}"
  ProcessingOutputConfig:
    KmsKeyId: "{env.PROJECT_KEY_ARN}"
  ```

  declarada nos dois stages do manifest, `PROJECT_KEY_ARN: ${PROJECT_KEY_ARN}`, e exportada no
  shell como `arn:aws:kms:<REGION>:<ACCOUNT_ID>:key/<PROJECT_KEY_ID>`, com os valores do
  `space_values.json`; pelo portal, o `render` a lê como `<PROJECT_KEY_ARN>`, num terceiro
  arquivo de valores.

Os passos:

1. **Na máquina que empacota**, num Linux x86_64, a plataforma do job, trave o projeto:

   ```shell
   (cd examples/awsds-demo-job && uv lock)
   ```

2. **Grave o `.tar.gz`** do projeto em `src/` do exemplo, de onde o manifest o sobe:

   ```shell
   awsds-workflows prepare-offline examples/awsds-demo-job \
       examples/demo-devenv-job/src/awsds-demo-job.tar.gz
   ```

   O `prepare-offline` copia o projeto para uma pasta temporária, sem alterar a do exemplo,
   recria lá a `.venv/` com o CPython 3.12 que o `uv` baixa para dentro dela, o projeto instalado
   como pacote e as dependências de execução, torna relativo cada link, grava o `.tar.gz` com a
   raiz `awsds-demo-job/` e prova, extraindo-o noutra pasta temporária, que o `.venv/bin/python`
   de lá roda sem o `uv`. Ele imprime o tamanho do arquivo e o da pasta extraída, com a versão do
   interpretador, e a raiz:

   ```text
   examples/demo-devenv-job/src/awsds-demo-job.tar.gz: 34111121 bytes, 100119806 extraídos, com o CPython 3.12.13 em Linux x86_64
   raiz: awsds-demo-job/
   ```

   Noutra plataforma ele para antes de qualquer download
   ([A pasta do projeto preparada num `.tar.gz`](../awsds_workflows.html#a-pasta-do-projeto-preparada-num-targz)).
   O `.tar.gz` fica fora do git.

3. **No espaço**, ponha a amostra na caixa de entrada, um arquivo por vez, porque `remove_source`
   apaga o prefixo inteiro:

   ```shell
   mkdir -p ~/shared/exemplos/demo-devenv-job/inbox
   cp sample.csv ~/shared/exemplos/demo-devenv-job/inbox/
   ```

4. **Pela CLI**, na pasta `examples/demo-devenv-job`, exporte as quatro variáveis de stage, a
   rede do projeto, do `space_values.json`, e a imagem:

   ```shell
   export SUBNET_AZ1=<SUBNET_AZ1> SUBNET_AZ2=<SUBNET_AZ2> PROJECT_SG=<PROJECT_SG>
   ```

   ```shell
   export JOB_IMAGE_URI=<SMD_REGISTRY_ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/sagemaker-distribution-prod:4.5.2-cpu
   ```

   e então o `deploy` e o `run` de [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd):
   o `deploy` sobe o `.tar.gz` para `exemplos/demo-devenv-job/src/`, a entrada de código do job, e
   o `run` passa as quatro variáveis à execução, que o `config` do job lê como `{{ params.NOME }}`.
   Uma versão nova do projeto é o `prepare-offline` e o `deploy` de novo.

5. **Ou no portal**, preencha o workflow com os dois arquivos de valores:

   ```shell
   awsds-workflows render examples/demo-devenv-job/workflows/demo-devenv-job.yaml \
       --values-file space_values.json \
       --values-file examples/demo-devenv-job/extra_values.json > /tmp/demo-devenv-job.yaml
   ```

   Com a conta do registro por preencher, o `render` recusa: `nenhum valor para:
   SMD_REGISTRY_ACCOUNT`; sem o segundo arquivo, `nenhum valor para: JOB_IMAGE_URI`.

6. **No espaço**, pelo portal, copie o `.tar.gz`, levado para lá, para a entrada de código:

   ```shell
   mkdir -p ~/shared/exemplos/demo-devenv-job/src
   cp awsds-demo-job.tar.gz ~/shared/exemplos/demo-devenv-job/src/
   ```

   Uma versão nova do projeto é o `prepare-offline` de novo e a cópia por cima do objeto, que a
   execução seguinte já lê. Confira a cópia no S3, com o bucket, o domínio e o projeto do
   `space_values.json`:

   ```shell
   aws s3 ls s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/exemplos/demo-devenv-job/src/
   ```

   > [!WARNING]
   > **O `aws s3 ls` tem de listar o `awsds-demo-job.tar.gz`** com o tamanho que o
   > `prepare-offline` imprimiu, além do marcador de pasta de zero bytes. Se não listar, pare: a
   > cópia não chegou ao S3, de onde o job lê o prefixo inteiro a cada execução.

7. **No portal**: workflow `demo-devenv-job`, o campo *Operator files zip S3 location* vazio, a
   definição `/tmp/demo-devenv-job.yaml`, salve e execute. O formulário do editor não expressa o
   `config` inteiro do job: só a importação o guarda.

8. **Leia** o log de `run_project`, que imprime o `config` do job e espera o fim dele, e o log do
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

9. **No espaço**, confira o hash do resultado, o mesmo dos outros dois `demo-*`:

   ```shell
   sha256sum ~/shared/exemplos/demo-devenv-job/outbox/*/sample.result.json
   ```

> [!NOTE]
> **Estado**: no ambiente alvo, pelo portal, a execução parou na permissão do projeto, antes de
> existir um job; o `.tar.gz` ainda não rodou num job, e pela CLI o exemplo ainda não rodou
> ([as notas](lab_notes.html#demo-devenv-job)).

## redshift-unload

A task chama `redshift_unload.unload`, que manda três comandos numa sessão da Data API do Redshift
Serverless, com as credenciais do worker: `SELECT current_user`, o `UNLOAD` da consulta para o
S3, em Parquet, e `SELECT pg_last_unload_count()`. Antes:

- **Os nomes do Redshift**: `REDSHIFT_WORKGROUP`, o workgroup do Redshift Serverless;
  `REDSHIFT_DATABASE`, o banco em que a sessão entra; e `REDSHIFT_TABLE`, a tabela em três
  partes, `<banco do datashare>.<esquema>.<tabela>`, porque a consulta é
  `SELECT * FROM <REDSHIFT_TABLE>` e, numa sessão da Data API, uma tabela de um datashare leva o
  nome assim. Pela CLI, eles são as variáveis de stage, no shell; pelo portal, estão por preencher
  em `examples/redshift-unload/extra_values.json`, na máquina que empacota. Preenchido:

  ```json
  {
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

  > [!WARNING]
  > **Sem esse `GRANT`, o workflow para em
  > `Permission denied to query database created from datashare`.** Num banco criado
  > `WITH PERMISSIONS`, o usuário também precisa de `USAGE` no esquema e de `SELECT` nas tabelas.
  > A primeira linha do log de cada execução diz quem precisa da permissão.

Os passos:

1. **Na máquina que empacota**, monte o `.zip` em `code/` do exemplo, só com o módulo na raiz:

   ```shell
   python3 -m zipfile -c examples/redshift-unload/code/redshift-unload.zip \
       examples/redshift-unload/code/redshift_unload.py
   ```

   O módulo só usa o `boto3` que o worker traz, então o `.zip` dispensa o `package-task`; ele fica
   fora do git.

2. **Pela CLI**, na pasta `examples/redshift-unload`, exporte os três nomes:

   ```shell
   export REDSHIFT_WORKGROUP=meu-workgroup REDSHIFT_DATABASE=dev \
       REDSHIFT_TABLE=meu_banco.meu_esquema.minha_tabela
   ```

   e então o `deploy` e o `run` de [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd):
   o `deploy` sobe o `.zip` e aponta o workflow para a cópia dele em `operatorFiles/`, e o `run`
   passa os três nomes à execução, que a task lê nos `op_kwargs`. Não há sensor nem job: a task
   roda na hora, e não depende da permissão do projeto para jobs.

3. **Ou no portal**, preencha o workflow com os dois arquivos de valores:

   ```shell
   awsds-workflows render examples/redshift-unload/workflows/redshift-unload.yaml \
       --values-file space_values.json \
       --values-file examples/redshift-unload/extra_values.json > /tmp/redshift-unload.yaml
   ```

   Com um nome do Redshift por preencher, o `render` recusa nomeando-o. Depois, no portal:
   workflow `redshift-unload`, o `.zip` `examples/redshift-unload/code/redshift-unload.zip` do
   clone, a definição `/tmp/redshift-unload.yaml`, salve e execute.

4. **Leia** o log de `unload`: `usuário do banco: IAMR:user-project@<projeto>`,
   `<n> linha(s) descarregada(s) em <s> s sob s3://.../shared/exemplos/redshift-unload/<data-hora>/`
   e `Done. Returned value was: <n>`.

5. **No espaço**, liste os arquivos, numa pasta por execução, com a data e a hora dela:

   ```shell
   ls ~/shared/exemplos/redshift-unload/*/
   ```

   Os `.parquet` e o `manifest`. Com zero linhas, o `UNLOAD` não grava nada, e a contagem diz 0.
   As outras falhas estão na tabela do `README.md` do exemplo.

> [!TIP]
> **Para testar a função antes**, num espaço, copie `redshift_unload.py` para lá e rode o exemplo
> da docstring dele, com um destino de teste.

> [!NOTE]
> **Estado**: rodou no ambiente alvo, pelo portal, depois do `GRANT`; pela CLI ainda não
> ([as notas](lab_notes.html#redshift-unload)).

## houseprice-etl

Uma task `GlueJobOperator` cria o job do Glue `houseprice-etl-<projeto>` com o script do exemplo,
ou o atualiza se ele já existe, e o executa: o job lê um Parquet de `entrada/` e grava os dados em
CSV, sem cabeçalho, acrescentando a `saida/`. O workflow não tem task Python nem Bash, e por isso
não tem `.zip`; o script vai ao projeto em `glue/`, pelo `deploy` ou à mão. O porquê de cada
parâmetro da task está no `README.md` do exemplo.

> [!IMPORTANT]
> **O job se cria uma vez, antes da primeira execução, em cada projeto.** A política do papel do
> projeto só autoriza o `GetJob` sobre um job com a etiqueta do projeto, e um job que ainda não
> existe não tem etiqueta: a primeira execução para em `AccessDeniedException` no `GetJob`, antes
> de tentar o `CreateJob`. O `job.json` do exemplo é a entrada do `CreateJob` que a task faria.

1. **No espaço**, prepare um Parquet: o que um fluxo do Visual ETL do projeto lê, ou a amostra da
   preparação convertida:

   ```shell
   python -c "import pandas; pandas.read_csv('sample.csv').to_parquet('house-price.parquet')"
   ```

   O pandas e o pyarrow vêm com a imagem padrão do espaço (inferido); sem eles, o comando para em
   `ModuleNotFoundError`, e qualquer Parquet serve.

2. **No espaço**, ponha o Parquet em `entrada/house-price.parquet`:

   ```shell
   mkdir -p ~/shared/exemplos/houseprice-etl/entrada
   cp house-price.parquet ~/shared/exemplos/houseprice-etl/entrada/
   ```

3. **Na máquina que empacota**, preencha o modelo do job com os valores do projeto:

   ```shell
   awsds-workflows render examples/houseprice-etl/job.json \
       --values-file space_values.json > /tmp/houseprice-etl.job.json
   ```

   O `render` traduz as variáveis da CLI do arquivo, como num workflow, e preenche as sub-redes
   com o `space_values.json`.

4. **Crie o job uma vez**, num espaço, com o arquivo levado para lá, ou na máquina que empacota,
   com a credencial da preparação:

   ```shell
   aws glue create-job --cli-input-json file://houseprice-etl.job.json
   ```

   O job lê o script em `exemplos/houseprice-etl/glue/` do projeto a cada execução.

5. **Pela CLI**, na pasta `examples/houseprice-etl`, exporte as sub-redes do projeto, do
   `space_values.json`:

   ```shell
   export SUBNET_AZ1=<SUBNET_AZ1> SUBNET_AZ2=<SUBNET_AZ2>
   ```

   e então o `deploy` e o `run` de [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd):
   o `deploy` copia o script para `exemplos/houseprice-etl/glue/`, de onde o job o lê, e o `run`
   passa as sub-redes à execução, que o operador escreve nos nomes das conexões do job.

6. **Ou no portal**, leve ao espaço o `examples/houseprice-etl/glue/etl_houseprice.py` do clone e,
   lá, copie-o para o caminho que o job lê:

   ```shell
   mkdir -p ~/shared/exemplos/houseprice-etl/glue
   cp etl_houseprice.py ~/shared/exemplos/houseprice-etl/glue/
   ```

7. **Na máquina que empacota**, pelo portal, preencha o workflow:

   ```shell
   awsds-workflows render examples/houseprice-etl/workflows/houseprice-etl.yaml \
       --values-file space_values.json > /tmp/houseprice-etl.yaml
   ```

8. **No portal**: workflow `houseprice-etl`, o campo *Operator files zip S3 location* vazio, a
   definição `/tmp/houseprice-etl.yaml`, salve e execute.

9. **Leia** o log de `run_glue_job`: `Checking if job already exists: houseprice-etl-<projeto>`;
   `Updating job: houseprice-etl-<projeto>` e `Updated configurations: {...}`, com os campos que
   diferem, quando o job difere da definição; uma linha
   `Polling for AWS Glue Job houseprice-etl-<projeto> current run state with status RUNNING` a cada
   6 s e, no fim, `Exiting Job jr_... Run State: SUCCEEDED` e
   `AWS Glue Job: houseprice-etl-<projeto> status: SUCCEEDED. Run Id: jr_...`. Com a definição
   sem mudança, uma execução sem as linhas do `Updating job` diz que o job e a definição ficaram
   iguais.

10. **No espaço**, confira a saída. Cada execução acrescenta arquivos `part-*.csv`, sem cabeçalho:

    ```shell
    ls ~/shared/exemplos/houseprice-etl/saida/
    head -3 ~/shared/exemplos/houseprice-etl/saida/part-*.csv
    ```

    Na página *Data processing jobs* do projeto, confira se o job aparece, com as execuções e os
    logs. A API cria o job sem `JobMode`, que o Glue trata como `SCRIPT`, o tipo *Code* da página
    (inferido).

11. **No stage `test`**, o projeto de teste pede o Parquet dos passos 1 e 2 e o job dos passos 3 e
    4, com o `space_values.json` de um espaço dele, antes do `bundle` e do `deploy` de
    [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd), que executa o workflow uma
    vez.

As falhas estão na tabela do `README.md` do exemplo.

> [!NOTE]
> **Estado**: rodou no laboratório pela CLI, nos stages `dev` e `test`: a primeira execução parou
> no `GetJob`, o job se criou uma vez com o `job.json`, e as seguintes terminaram em sucesso, com
> o `UpdateJob` em cada uma até a definição levar o `Command` inteiro; uma execução sem
> `UpdateJob`, e o caminho do portal, ainda não ([as notas](lab_notes.html#houseprice-etl)).

## Limpeza

1. **No portal**, apague os workflows, os importados e os que a CLI criou, em cada projeto.
2. **No espaço**, apague as pastas dos exemplos:

   ```shell
   rm -r ~/shared/exemplos/
   ```

3. **O job do `houseprice-etl`**, em cada projeto, se apaga na página *Data processing jobs* ou,
   num espaço, com:

   ```shell
   aws glue delete-job --job-name houseprice-etl-<PROJECT_ID>
   ```

4. **Na máquina que empacota**, o que os passos gravaram nas pastas dos exemplos fica fora do
   git: os `.zip` em `code/`, o `.tar.gz` em `src/` e os bundles em `artifacts/`.

O grupo de logs de cada workflow e os `.zip` em `dev/operatorFiles/`, do portal, e em
`shared/operatorFiles/`, da CLI, ficam ([Limpeza](../awsds_workflows.html#limpeza)). O `destroy`
da CLI, que apaga o que o manifest implantou, não foi exercitado nos exemplos.
