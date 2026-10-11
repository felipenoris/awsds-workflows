O pacote prepara o que um workflow serverless de um projeto do SageMaker Unified Studio executa: o
código de uma task Python ou Bash do MWAA Serverless, a pasta de código de um job de processamento
do SageMaker e a definição do workflow com os valores do projeto. As ferramentas rodam numa máquina
Linux com internet, onde o `uv` alcança o PyPI. O que elas gravam é copiado para o ambiente do
SageMaker, que não tem internet, e nada é instalado onde o código roda.

Esta página é o procedimento. Cada passo foi medido em outubro de 2026 no laboratório, uma conta
de testes em `us-west-2` com uma imagem customizada, `awsds-sandbox-dev-env`. A referência de
cada módulo está no menu: `awsds_workflows.package_task`, `awsds_workflows.package_job`,
`awsds_workflows.render`, `awsds_workflows.errors` e `awsds_workflows.cli`.

| Seção | Para quem | O que traz |
|---|---|---|
| [Instalação](#instalacao) | todos | o pacote na máquina que empacota |
| [As peças](#as-pecas) | todos | onde ficam a definição, o código, os logs e as execuções |
| [A imagem do job](#a-imagem-do-job) | todos | a imagem padrão do SageMaker ou uma customizada, e o que muda |
| [A permissão do projeto](#a-permissao-do-projeto) | infraestrutura | a política que o papel do projeto precisa antes do primeiro job |
| [A rede](#a-rede) | infraestrutura | os endpoints que o worker e o job usam |
| [Regras de autoria](#regras-de-autoria) | cientista de dados | o editor, a importação, os templates, o sensor |
| [Uma task de processamento](#uma-task-de-processamento) | cientista de dados | um job na imagem escolhida, e a pasta de código com `package-job` |
| [O código de uma task Python ou Bash](#o-codigo-de-uma-task-python-ou-bash) | cientista de dados | o `.zip` com `package-task` |
| [Os valores da definição](#os-valores-da-definicao) | todos | os placeholders e o `render` |
| [Como ler uma execução](#como-ler-uma-execucao) | todos | uma leitura por pergunta |
| [Limpeza](#limpeza) | todos | o que fica depois de um workflow |

## Instalação

A máquina que empacota é Linux, com internet e com o `uv`. O pacote é instalado pelo endereço do
repositório ou por uma pasta local, nunca pelo nome: o nome `awsds-workflows` está livre no PyPI
(lido em 2026-10-11), e um pacote publicado lá com ele por outra pessoa seria instalado no lugar
deste.

```shell
uv tool install git+https://github.com/felipenoris/awsds-workflows   # o comando awsds-workflows
uv add git+https://github.com/felipenoris/awsds-workflows            # ou como dependência
```

O pacote pede o Python 3.13 ou mais novo e chama o `uv` como programa. A única dependência é o
`packaging`, que avalia os marcadores do ambiente da imagem.

## As peças

| O quê | Onde | Nota |
|---|---|---|
| a definição | `s3://<bucket do projeto>/<domínio>/<projeto>/dev/workflows/<nome>.yaml` | gravada pelo portal a cada save; *View code* a mostra |
| o `.zip` de uma task Python ou Bash | `.../dev/operatorFiles/<arquivo>` | enviado em *Settings → Storage*; um `.zip` é guardado como foi enviado, e o workflow fixa a versão S3 dele |
| a cópia do código que o serviço guarda | armazenamento do serviço | tirada a cada save e cifrada com a chave do projeto; não é gravada no bucket do projeto, e o bucket dela não foi lido (2026-10-11) |
| os logs das tasks | `/aws/mwaa-serverless/<domínio>-<projeto>/<workflow>`, um stream por tentativa de task | por projeto, sem retenção; o grupo sobrevive ao workflow |
| a saída do contêiner de um job | `/aws/sagemaker/ProcessingJobs`, stream `<job>/algo-1-<n>` | da conta inteira: todo papel de projeto da conta pode lê-la |
| a identidade | o papel do projeto, `datazone_usr_role_<projeto>_<ambiente>`, sessão `AmazonMWAAServerless` no worker e `SageMaker` dentro de um job | |
| a rede | as sub-redes privadas e o grupo de segurança do projeto, injetados pelo portal | sem rota padrão: a AWS é alcançada pelos endpoints de VPC |
| a chave | a chave KMS do projeto | a cifra do workflow, o volume e as saídas do job, o bucket |

**O worker** tem 1 vCPU e 3 GiB, Python 3.12, Airflow 3.0.6, o provider da Amazon 9.32.0 e o
`boto3` 1.43.1 (o guia, lido em 2026-10-11). Ele não tem internet nem proxy. Uma task ocupa o
worker durante toda a sua duração, espera de sensor incluída, e custa 0,088 USD por task-hora, com
mínimo de um minuto.

## A imagem do job

Um job de processamento roda numa imagem que o próprio job nomeia, e o pacote não supõe qual. A
imagem decide o interpretador, a versão do Python e o ambiente de pacotes, e cada um entra no
`package-job` e na definição. O worker das tasks Python e Bash não depende dela.

| | A imagem padrão do SageMaker | Uma imagem customizada |
|---|---|---|
| exemplo | a SageMaker Distribution 4.15, a imagem inicial do alvo | a imagem do laboratório, `awsds-sandbox-dev-env` |
| `JOB_IMAGE_URI` | o URI da distribuição na região do projeto, no arquivo de valores | lido da imagem registrada no SageMaker (`values --image-name`) ou no arquivo de valores |
| `JOB_PYTHON`, o interpretador que o job chama | `/opt/conda/bin/python` | o do ambiente da imagem; na do laboratório, `/opt/awsds/venv/bin/python` |
| `--python` | a versão desse interpretador, lida com `/opt/conda/bin/python --version` num space com a imagem | na do laboratório, 3.13 |
| o arquivo de ambiente | `uv pip list --format freeze --python /opt/conda/bin/python` num space com a imagem | o mesmo comando com o interpretador da imagem, ou o `uv export` do projeto que constrói a imagem |

O arquivo de ambiente é gerado num space que roda a imagem do job, sem internet, e copiado para a
máquina que empacota. Ele vale para aquela versão da imagem: uma imagem nova pede um arquivo novo
e uma pasta de código nova. O `uv pip list --format freeze` escreve só linhas `nome==versão`; o
`pip freeze` escreve `nome @ file:///...` para um pacote instalado pelo conda, e o `package-job`
recusa essa linha, porque ignorada ela faria o pacote parecer ausente da imagem e entrar na pasta.

Ainda não medido na SageMaker Distribution 4.15: o URI da imagem para um job no alvo, a versão do
Python de `/opt/conda/bin/python` e o usuário do contêiner. A imagem do laboratório roda como
`sagemaker-user` (uid 1000), e o `sudo` dela funciona dentro de um job (medido em 2026-10-11); a
distribuição, de que a imagem do laboratório deriva, deve ter o mesmo usuário, e o primeiro job no
alvo é a medida.

## A permissão do projeto

O papel de um projeto não roda o `SageMakerProcessingOperator` só com as políticas do blueprint,
por dois motivos medidos no laboratório em 2026-10-10:

- **O operador descreve o nome do job antes de criá-lo**, e o blueprint deixa o papel descrever só
  um job com a etiqueta do próprio projeto. Um nome ainda livre não tem etiqueta, então a primeira
  execução falha com `AccessDeniedException` em `DescribeProcessingJob` antes de existir um job.
- **Uma criação com etiquetas também é autorizada como `sagemaker:AddTags`**, e o blueprint tira
  toda chave `AmazonDataZone*` do `AddTags` enquanto exige que o job leve `AmazonDataZoneProject`.
  A segunda execução falha com `AccessDeniedException` em `sagemaker:AddTags`.

A política abaixo, anexada a cada papel de projeto que roda jobs, cobre os dois. Ela permite o
`DescribeProcessingJob` de um job sem etiqueta de projeto e o `AddTags` só da etiqueta do próprio
projeto, num job sem etiqueta ou com a do chamador; os jobs de outro projeto ficam fora de alcance.

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DescribeAProcessingJobNoProjectHolds",
      "Effect": "Allow",
      "Action": "sagemaker:DescribeProcessingJob",
      "Resource": "arn:aws:sagemaker:<REGION>:<ACCOUNT_ID>:processing-job/*",
      "Condition": {"Null": {"aws:ResourceTag/AmazonDataZoneProject": "true"}}
    },
    {
      "Sid": "TagAProcessingJobWithTheCallersProject",
      "Effect": "Allow",
      "Action": "sagemaker:AddTags",
      "Resource": "arn:aws:sagemaker:<REGION>:<ACCOUNT_ID>:processing-job/*",
      "Condition": {
        "StringEquals": {
          "aws:RequestTag/AmazonDataZoneProject": "${aws:PrincipalTag/AmazonDataZoneProject}"
        },
        "StringEqualsIfExists": {
          "aws:ResourceTag/AmazonDataZoneProject": "${aws:PrincipalTag/AmazonDataZoneProject}"
        },
        "ForAllValues:StringEquals": {"aws:TagKeys": ["AmazonDataZoneProject"]}
      }
    }
  ]
}
```

## A rede

O worker roda nas sub-redes privadas do projeto e alcança a AWS só pelos endpoints de VPC. O que o
laboratório leu no CloudTrail e nos logs de fluxo em 2026-10-11:

- **O operador de processamento** chama `CreateProcessingJob` e `DescribeProcessingJob` pelo
  endpoint de interface `sagemaker.api`, como o papel do projeto.
- **O worker grava o log** por `CreateLogStream`, pelo endpoint `logs`.
- **O S3** é alcançado pelo endpoint de gateway: o sensor lista o prefixo, e o worker de uma task
  com `.zip` busca a cópia do código num bucket do serviço, que a política do endpoint precisa
  admitir.
- **A imagem do job é baixada pela plataforma**, fora da rede do projeto, então um job isolado não
  precisa de endpoint do ECR.

No ambiente alvo, as leituras do serialize-db a partir de um space (2026-09-21 e 2026-09-23)
encontraram o endpoint de gateway do S3 e endpoints de interface para STS, Redshift, Glue, Athena,
Secrets Manager e DataZone; os nomes do SageMaker, do KMS e do IAM resolveram para endereços
públicos e não responderam. Se o worker do alvo usar a mesma rede, uma task de processamento não
alcança o `CreateProcessingJob`; a primeira execução no alvo é a medida.

## Regras de autoria

**Crie vazio, depois importe.** Na página *Workflows*, crie um workflow e use *Actions → Import
definition file* com a definição preenchida pelo `render`. Os formulários do editor não expressam
tudo o que uma definição expressa, e a importação guarda cada campo: a definição salva difere da
importada só por `is_paused_upon_creation: false`, pela ordem das chaves e por textos longos
dobrados.

**Uma importação substitui o workflow.** Cada importação medida aparece no CloudTrail como
`DeleteWorkflow` seguido de `CreateWorkflow`: o sufixo do ARN muda, e o histórico de execuções e de
versões recomeça. O grupo de logs leva o nome do workflow e guarda os logs de cada execução.

**Erros do save e a saída de cada um**:

| O portal diz | O que aconteceu | Saída |
|---|---|---|
| `ValidationException: Code not found in specified S3 location` | o save mandou um local de código em `dev/operatorFiles/` sem arquivo lá | envie qualquer `.py` em *Settings → Storage*, ou importe num workflow novo e vazio |
| `ContainerArguments: Container argument is required` | o editor, e não a API, exige argumentos numa task de processamento | separe o comando em programa (`ContainerEntrypoint`) e argumentos |
| dois workflows com o mesmo nome | dois saves passaram juntos pela conferência do nome, a 2 s um do outro | apague um; fora disso, o nome é conferido |

**A primeira linha do YAML é o layout do editor**, um comentário JSON como
`# {"wait_for_file":{"x":120,"y":200},...}`. Mantenha-a, e não ponha outro comentário num arquivo
que vai ser importado.

**Os templates são renderizados quando a execução é criada**, só com `macros`,
`ti`/`task_instance`, `params`, `ds`, `ds_nodash`, `ts` e `ts_nodash`:

- `{{ ts_nodash }}` é a meia-noite do dia numa execução manual, então duas execuções no mesmo dia
  colidem nele;
- `{{ dag_run... }}` derruba a execução antes da primeira task ("'dag_run' is undefined");
- um método de um objeto que uma macro devolveu também derruba ("access to attribute 'strftime' of
  'datetime' object is unsafe");
- as funções de um módulo passam. Um carimbo por execução:
  `{{ macros.time.strftime('%Y%m%dT%H%M%S', macros.time.gmtime()) }}`.

**Parâmetros que o serviço ignora ou limita**: `deferrable`, `trigger_rule`,
`render_template_as_native_obj` e `do_xcom_push` são ignorados, então uma lista renderizada chega
como texto. `retries` vale 1 por padrão e no máximo 3: escreva `retries: 0` em cada task durante o
desenvolvimento, ou uma falha roda duas vezes. `execution_timeout` vai até 3.600 s.

**O sensor de arquivo.** `S3KeySensor` com `wildcard_match: true`, `poke_interval: 30`,
`timeout: 600` e `soft_fail: true`:

- o `mkdir` de um space deixa um marcador de pasta de zero bytes, `inbox/`, e `inbox/*` casa com
  ele. Observe `inbox/?*`, que pede um caractere depois da barra, a menos que uma task seguinte
  apague o prefixo inteiro;
- `soft_fail` termina com `SUCCESS` uma execução de caixa de entrada vazia, depois do timeout. A
  API lê então o estado do sensor como `NONE`, e não `SKIPPED`, e não lista instância para as tasks
  seguintes; só o log da task diz `Skipping task.` A espera cobra os seus 10 minutos (cerca de
  0,015 USD).

## Uma task de processamento

O formulário *SageMaker Processing* do portal não tem campo para `NetworkConfig`, para as chaves
KMS nem para as etiquetas, e um job sem eles pode ser recusado pelas regras do ambiente. Escreva o
`config` inteiro da task no YAML e importe-o.

**O que o ambiente exige do job.** No laboratório, o limite de permissões dos papéis de projeto
exige em todo job:

- `NetworkConfig.VpcConfig`: as duas sub-redes privadas e o grupo de segurança do projeto;
- `EnableNetworkIsolation: true`: o contêiner não tem rede nem credenciais da AWS;
- `EnableInterContainerTrafficEncryption: true`, mesmo com uma só instância;
- `ProcessingResources.ClusterConfig.VolumeKmsKeyId`: a chave do projeto;
- um tipo de instância dentro do teto do limite; `ml.t3.medium` é o menor que ele admite.

As regras do próprio projeto acrescentam `Tags: [{Key: AmazonDataZoneProject, Value: <projeto>}]`
e o `KmsKeyId` da saída, a chave do projeto. Outro ambiente pode exigir outra lista; a recusa do
`CreateProcessingJob` no log da task a nomeia.

**As entradas e as saídas ficam em `/opt/ml/processing/`.** O SageMaker baixa cada
`ProcessingInput` antes do comando começar e envia cada `ProcessingOutput` depois que ele termina,
como o papel do projeto. O código é mais uma entrada: a pasta que o `package-job` grava, copiada
para o S3 do projeto.

**O usuário do contêiner não grava na pasta de saída.** A imagem do laboratório roda como
`sagemaker-user` (uid 1000), e a plataforma cria cada pasta montada como root com modo 755; uma
gravação falha com `Permission denied`, e o job termina com `AlgorithmError: , exit code: 1`. O
`sudo` da imagem funciona dentro de um job, então o comando abre com um `chown`:

```yaml
ContainerEntrypoint: [/bin/bash, -c]
ContainerArguments:
  - 'sudo -n chown "$(id -u)" /opt/ml/processing/outbox && exec <JOB_PYTHON> -m meu_pacote --input /opt/ml/processing/inbox --output /opt/ml/processing/outbox'
Environment:
  PYTHONPATH: /opt/ml/processing/code
```

- o `exec` entrega ao job o código de saída do interpretador;
- o interpretador é nomeado pelo caminho absoluto, `<JOB_PYTHON>`, porque um `ContainerEntrypoint`
  substitui o ponto de entrada e o `PATH` da imagem.

### A pasta de código com `package-job`

O job não tem rede, então as dependências do projeto ou vêm no ambiente da imagem ou viajam na
entrada de código; nada é instalado na execução. Três coisas separam essa entrada do `.zip` de uma
task:

- **O interpretador é o da imagem do job**, e não o do worker.
- **A entrada é uma pasta, e não um arquivo.** Um `ProcessingInput` baixa um prefixo do S3, e um
  módulo de extensão não é importado de um `.zip` no `sys.path`.
- **A precedência é a inversa da do worker.** O `PYTHONPATH` vem antes do `site-packages` da
  imagem, então um pacote presente nos dois esconderia a cópia da imagem. A pasta leva só o que a
  imagem não tem, e as versões do projeto têm de ser iguais às da imagem em tudo o que os dois
  compartilham.

1. **Prepare o projeto.**
   - Ele tem um `pyproject.toml` e um `uv.lock` em dia.
   - O `requires-python` dele admite o Python da imagem.
   - O código próprio dele é Python puro, e roda como `python -m meu_pacote` (um `__main__.py`).
2. **Gere o arquivo de ambiente da imagem** num space que roda a imagem do job e copie-o para a
   máquina que empacota ([A imagem do job](#a-imagem-do-job)):

   ```shell
   uv pip list --format freeze --python /opt/conda/bin/python > ambiente.txt
   ```

3. **Confira o projeto contra a imagem e grave a pasta**, com a versão do Python da imagem:

   ```shell
   awsds-workflows package-job ~/src/meu-projeto /tmp/meu-projeto-0.2.0 \
       --environment ambiente.txt --python 3.12
   ```

   A pasta de saída ainda não pode existir. `--platform` vale `x86_64-manylinux_2_28` por padrão,
   que pede glibc 2.28 ou mais nova na imagem; `ldd --version` num space diz a glibc. A imagem da
   casa tem o `onnxruntime` 1.30.0, que não publica wheel anterior a `manylinux_2_28` (medido em
   2026-10-11), então `manylinux2014` não a descreve.
4. **Se ele apontar uma discordância**, cole o bloco que ele imprime no `pyproject.toml` do projeto,
   rode `uv lock` e repita o passo 3:

   ```toml
   [tool.uv]
   constraint-dependencies = [
     "boto3==1.43.92",
     ...
   ]
   ```

   O bloco fixa cada pacote que o projeto compartilha com a imagem na versão da imagem. Quando um
   limite inferior do projeto passa de uma versão da imagem, esse lock falha, e a dependência não
   serve a esta imagem: ela pede outra versão, outro pacote ou outra imagem.
   `awsds-workflows job-constraints --environment ambiente.txt --python 3.12` imprime cada versão
   da imagem como requisito, para `uv pip compile -c` ou `uv add -c`.
5. **Leia o que ele imprimiu**: a pasta e o tamanho, o que vem da imagem, o que a pasta leva e a
   raiz, que tem só o projeto e os pacotes que a imagem não tem.
6. **Copie a pasta para o S3 do projeto, num prefixo só desta versão.** Uma entrada baixa o prefixo
   inteiro, então uma cópia sobre uma pasta mais velha misturaria duas versões:

   ```shell
   aws s3 cp --recursive /tmp/meu-projeto-0.2.0 \
       s3://<bucket do projeto>/<domínio>/<projeto>/shared/jobs/meu-projeto-0.2.0/
   ```

7. **Nomeie a pasta no `config` do job**, ao lado das exigências do ambiente, e importe a
   definição:

   ```yaml
   ProcessingInputs:
     - InputName: code
       S3Input:
         S3Uri: s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/jobs/meu-projeto-0.2.0/
         LocalPath: /opt/ml/processing/code
         S3DataType: S3Prefix
         S3InputMode: File
         S3DataDistributionType: FullyReplicated
   ```

8. **Uma versão nova da imagem muda o alvo**: gere o arquivo de ambiente de novo e grave uma pasta
   nova. Uma versão nova do código são os passos 3, 6 e 7 com um nome de pasta novo. O job lê o
   prefixo a cada execução, sem cópia tirada num save.

**Quando o `package-job` recusa:**

| Ele diz | Significado | O que fazer |
|---|---|---|
| `não há uv.lock em ...` | o projeto nunca foi travado | `uv lock` no projeto |
| `... já existe: nomeie uma pasta nova` | a pasta de saída já está lá | uma pasta nova, ou apague a velha |
| `o lock do projeto e o ambiente da imagem discordam` | um pacote compartilhado noutra versão | o passo 4 |
| `... não é nome==versão` | o arquivo de ambiente veio do `pip freeze` | gere-o com `uv pip list --format freeze` |
| `não é Python puro` | o projeto tem módulos de extensão | construa o wheel dele na plataforma do alvo |
| `no wheels with a matching platform tag` | uma dependência da pasta não publica wheel para o alvo | outra versão, outro pacote ou outra imagem |

**Medido em 2026-10-11** com a imagem do laboratório, num projeto descartável que dependia de
`petl`, `requests`, `boto3` e `pyyaml`: o lock novo discordou da imagem em `boto3`, `botocore`,
`charset-normalizer`, `idna` e `urllib3`; com o bloco impresso e um novo `uv lock`, 12 pacotes
vieram da imagem e só o `petl` entrou na pasta, de 1,2 MB.

**O workflow apaga a origem, e não o job**: um contêiner isolado não alcança o S3. A terceira task
é um `S3DeleteObjectsOperator` no prefixo da caixa de entrada, depois da task de processamento.

**Imprima contagens e caminhos, nunca dados.** A saída do contêiner vai para um grupo de logs da
conta inteira ([As peças](#as-pecas)).

**O custo e a duração de uma execução** (medido no laboratório em 2026-10-11): cerca de 15 minutos e
0,03 USD. O job passou cerca de 7,5 dos seus 8 minutos baixando a imagem do laboratório, de 6,97 GB,
antes de o contêiner começar, e a task de processamento ocupa o worker durante o job inteiro.

### Uma definição de exemplo

Três tasks: o sensor, o job e a remoção da origem. Os placeholders são preenchidos pelo `render`
([Os valores da definição](#os-valores-da-definicao)).

```yaml
# {"wait_for_file":{"x":120,"y":200},"run_project":{"x":420,"y":200},"remove_source":{"x":720,"y":200}}
meu-job:
  dag_id: meu-job
  tasks:
    wait_for_file:
      operator: airflow.providers.amazon.aws.sensors.s3.S3KeySensor
      bucket_key: s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/meu-job/inbox/*
      wildcard_match: true
      poke_interval: 30
      timeout: 600
      soft_fail: true
      retries: 0
    run_project:
      operator: airflow.providers.amazon.aws.operators.sagemaker.SageMakerProcessingOperator
      dependencies: [wait_for_file]
      retries: 0
      config:
        ProcessingJobName: "meu-job-{{ macros.time.strftime('%Y%m%dT%H%M%S', macros.time.gmtime()) }}"
        RoleArn: arn:aws:iam::<ACCOUNT_ID>:role/<PROJECT_ROLE_NAME>
        AppSpecification:
          ImageUri: <JOB_IMAGE_URI>
          ContainerEntrypoint: [/bin/bash, -c]
          ContainerArguments:
            - 'sudo -n chown "$(id -u)" /opt/ml/processing/outbox && exec <JOB_PYTHON> -m meu_pacote --input /opt/ml/processing/inbox --output /opt/ml/processing/outbox'
        Environment:
          PYTHONPATH: /opt/ml/processing/code
        ProcessingResources:
          ClusterConfig:
            InstanceCount: 1
            InstanceType: ml.t3.medium
            VolumeSizeInGB: 10
            VolumeKmsKeyId: arn:aws:kms:<REGION>:<ACCOUNT_ID>:key/<PROJECT_KEY_ID>
        NetworkConfig:
          EnableNetworkIsolation: true
          EnableInterContainerTrafficEncryption: true
          VpcConfig:
            Subnets: [<SUBNET_AZ1>, <SUBNET_AZ2>]
            SecurityGroupIds: [<PROJECT_SG>]
        ProcessingInputs:
          - InputName: code
            S3Input:
              S3Uri: s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/jobs/meu-projeto-0.2.0/
              LocalPath: /opt/ml/processing/code
              S3DataType: S3Prefix
              S3InputMode: File
              S3DataDistributionType: FullyReplicated
          - InputName: inbox
            S3Input:
              S3Uri: s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/meu-job/inbox/
              LocalPath: /opt/ml/processing/inbox
              S3DataType: S3Prefix
              S3InputMode: File
              S3DataDistributionType: FullyReplicated
        ProcessingOutputConfig:
          Outputs:
            - OutputName: outbox
              S3Output:
                S3Uri: "s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/meu-job/outbox/{{ macros.time.strftime('%Y%m%dT%H%M%S', macros.time.gmtime()) }}/"
                LocalPath: /opt/ml/processing/outbox
                S3UploadMode: EndOfJob
          KmsKeyId: arn:aws:kms:<REGION>:<ACCOUNT_ID>:key/<PROJECT_KEY_ID>
        StoppingCondition:
          MaxRuntimeInSeconds: 1800
        Tags:
          - Key: AmazonDataZoneProject
            Value: <PROJECT_ID>
    remove_source:
      operator: airflow.providers.amazon.aws.operators.s3.S3DeleteObjectsOperator
      dependencies: [run_project]
      bucket: <PROJECTS_BUCKET>
      prefix: <DOMAIN_ID>/<PROJECT_ID>/shared/meu-job/inbox/
      retries: 0
```

## O código de uma task Python ou Bash

**Estado no laboratório**: bloqueado. O worker de um workflow com `.zip` de código falhou ao
preparar o ambiente, antes de qualquer task, com `Execution environment preparation failed due to an
internal server error` (2026-10-11). Tudo abaixo foi construído e conferido localmente; nada disso
rodou num worker.

### O que o worker espera

- **Um arquivo ou um `.zip`.** Um `.py`, um `.sh` ou um `.zip` com vários arquivos; no máximo
  250 MB, descompactado também, e 75 GB de código por conta.
- **Tudo na raiz do `.zip`**: os seus módulos, os seus pacotes e cada pacote de terceiros. O worker
  extrai o `.zip` em `/usr/local/airflow/dags`, que está no `sys.path`, então um módulo na raiz é
  importado pelo nome.
- **Pacotes de terceiros construídos para o worker**: CPython 3.12 em Linux x86_64. Um pacote
  instalado para a sua máquina ou para a imagem do job não é importado lá.
- **Nenhum pacote que o worker já tem.** O guia diz que o pacote pré-instalado vence a cópia do
  `.zip` (não medido): o Airflow, o provider da Amazon, o `boto3` e o `botocore`, o dag-factory, o
  PyYAML, o lz4 e a família do AWS Encryption SDK. Escreva contra o `boto3` 1.43.1 do worker.
- **Nenhum `__pycache__` ou `.pyc`**: um bytecode de outra plataforma pode não carregar.
- **Nenhum segredo**: o `.zip` é copiado pelo serviço e guardado fora da conta.

### O `.zip` com `package-task`

1. **Prepare o projeto.**
   - Ele tem um `pyproject.toml` e um `uv.lock` em dia: rode `uv lock` no projeto depois de cada
     mudança.
   - O `requires-python` dele admite o Python do worker, 3.12.
   - O código próprio dele é Python puro. Um projeto com módulos de extensão não pode ser
     construído na máquina que empacota para o worker, e o `package-task` o recusa.
   - Um módulo de entrada, um arquivo pequeno ao lado do pacote e não dentro dele, tem a função que
     a task chama:

     ```python
     # tasks.py
     from meu_pacote import pipeline


     def run(bucket: str, inbox: str, outbox: str, **_context):
         return pipeline.process(bucket, inbox, outbox)
     ```

2. **Rode o `package-task`**, com o projeto, o módulo de entrada e o `.zip` a gravar:

   ```shell
   awsds-workflows package-task ~/src/meu-projeto ~/src/meu-projeto/tasks.py /tmp/meu-projeto.zip
   ```

   `--python X.Y` e `--platform ETIQUETA` mudam o alvo; os padrões, 3.12 e `x86_64-manylinux2014`,
   são o worker que o guia descreve. O serviço pode trocar o interpretador sem aviso, e o log de uma
   task nomeia o que rodou nos caminhos (`.../python3.12/site-packages/...`): quando esse caminho
   mudar, passe a nova versão. `--omit PACOTE`, repetido, deixa mais pacotes de fora.
3. **Leia o que ele imprimiu**: o tamanho do `.zip` e a raiz, que lista o seu pacote, o módulo de
   entrada e os pacotes de terceiros, e nenhum dos do worker (`boto3`, `botocore`, `yaml`, Airflow).
   A última linha é o próximo passo.
4. **Copie o `.zip` para onde o navegador que abre o portal alcança** e envie-o em *Settings →
   Storage → Python/Bash Operator Files* do workflow; depois salve.
5. **Nomeie a função** na task: `python_callable: tasks.run`, que o editor mostra como *File*
   `tasks` e *Function* `run`. Uma task Bash roda `python3 -m meu_pacote ...` a partir de
   `/usr/local/airflow/dags`, onde o `.zip` é extraído.
6. **Uma versão nova do código** são os mesmos três movimentos: rodar o `package-task`, enviar e
   salvar. O workflow continua rodando a cópia tirada no último save.

**Quando o `package-task` recusa:**

| Ele diz | Significado | O que fazer |
|---|---|---|
| `The lockfile at uv.lock needs to be updated` | o `pyproject.toml` mudou depois do lock | `uv lock` no projeto |
| `no wheels with a matching platform tag` | uma dependência não publica wheel para o alvo | ela não viaja no `.zip`: outra versão ou outro pacote |
| `não é Python puro` | o projeto tem módulos de extensão | construa o wheel dele na plataforma do alvo |
| `acima do limite de 250000000 bytes do worker` | o `.zip` é grande demais | `--omit` mais pacotes, ou corte dependências |

**O que ele faz**, cada passo uma regra do worker:

1. `uv export --locked --no-dev --no-emit-project --prune <nome> ...` grava o fechamento travado
   como arquivo de requisitos. `--locked` recusa um lock desatualizado, e `--prune` tira cada
   pacote do worker junto com as dependências que só ele usa: o `boto3` leva o `s3transfer` e o
   `jmespath`, e o `urllib3`, de que o `requests` também precisa, fica.
2. `uv pip install --target <pasta> --no-deps --only-binary :all: --python-version <X.Y>
   --python-platform <ETIQUETA> --requirements <arquivo>` instala os wheels do alvo para esse
   fechamento, com os hashes do lock. `--only-binary` recusa uma distribuição de código-fonte, que
   seria compilada para a máquina que empacota.
3. `uv build --wheel` constrói o projeto, recusado quando não é Python puro, e a mesma instalação
   põe o pacote dele na raiz.
4. O módulo de entrada é copiado para a raiz.
5. A trava do `uv`, os scripts de `bin/` e o bytecode saem, e o `.zip` é gravado pelo Python; um
   conteúdo acima de 250 MB descompactado é recusado antes de gravar.

**Medido em 2026-10-11** num projeto descartável que dependia de `petl`, `requests`, `boto3` e
`pyyaml`: cerca de 0,9 MB, com o projeto, `tasks.py`, o `petl` e o `requests` com `certifi`,
`charset_normalizer`, `idna` e `urllib3`; sem `boto3`, `botocore`, `s3transfer`, `jmespath` ou
`yaml`; os módulos compilados do `charset_normalizer` com a etiqueta
`cp312-cp312-manylinux2014_x86_64`, e `cpython-313` com `--python 3.13`.

**Mantenha o módulo de entrada fino.** O editor mostra o `python_callable` como *File* e
*Function*, então um módulo na raiz que importa do pacote é o que ele consegue mostrar. Um caminho
pontuado para dentro do pacote, `pacote.modulo.funcao`, não foi medido.

### O que o `.zip` leva

```
meu-projeto.zip              o CONTEÚDO da pasta de montagem, sem pasta própria
├── tasks.py                 o módulo de entrada: python_callable: tasks.run
├── meu_pacote/              o seu pacote, do wheel dele
├── meu_pacote-0.1.0.dist-info/
├── petl/                    um pacote de terceiros, construído para o worker
├── petl-1.7.29.dist-info/
└── ...
```

### A task na definição

```yaml
run_project:
  operator: airflow.providers.standard.operators.python.PythonOperator
  dependencies: [wait_for_file]
  python_callable: tasks.run
  op_kwargs:
    bucket: <PROJECTS_BUCKET>
    inbox: <DOMAIN_ID>/<PROJECT_ID>/shared/minha-task/inbox/
    outbox: <DOMAIN_ID>/<PROJECT_ID>/shared/minha-task/outbox/
  retries: 0
```

O `python_callable` é `<módulo>.<função>`. A função recebe o `op_kwargs` como argumentos nomeados,
e também o contexto do Airflow se aceitar `**kwargs`. Uma task Bash nomeia um `bash_command`; um
script do `.zip` roda com `/usr/local/airflow/dags` como pasta de trabalho.

### O `.zip` no workflow

**O código é sempre um objeto S3, nunca uma pasta.** O `Code` da API é um `S3Location`: um bucket,
uma chave e uma versão opcional de um único `.py`, `.sh` ou `.zip`. O worker extrai esse objeto,
então um prefixo de arquivos soltos não pode ser nomeado, e um pacote com dependências viaja como
`.zip`.

- **No portal**, *Settings → Storage → Python/Bash Operator Files* envia arquivos, e o *operator
  files S3 location* ao lado é onde eles são guardados (`dev/operatorFiles/` por padrão), e não uma
  origem a ler. O guia: um arquivo é guardado como está, vários são compactados num `.zip`, só
  `.py`, `.sh` e `.zip` são aceitos, e o `.zip` fica abaixo de 250 MB. Medido no laboratório: um
  `.zip` guardado como foi enviado, com a versão S3 fixada e o sha256 igual ao do `.zip` construído.
- **Pela API** (`create-workflow --code`, ou o `awscc` do Terraform a partir da 1.99.0), o objeto
  pode ser qualquer um que quem salva consiga ler, como um `.zip` no `shared/` do projeto. O serviço
  o lê na hora do save, na sessão de quem salva. Não exercitado.

**A receita de dependências do guia do portal omite as opções de plataforma** (`pip install
--target ./package sua-dependencia`): rodada noutra plataforma, ela instala os wheels daquela
plataforma para todo pacote compilado. Use o `package-task`, ou a receita à mão abaixo.

**Uma versão nova do código pede um save novo.** O workflow roda a cópia tirada no último save,
então trocar o objeto no S3 não muda nada até o workflow ser salvo ou importado de novo.

### À mão, sem o pacote

Para um projeto que o uv não gerencia:

```shell
rm -rf build && mkdir build
cp tasks.py build/
cp -R src/meu_pacote build/
uv pip install --target build --python-platform x86_64-manylinux2014 --python-version 3.12 \
    --only-binary :all: --requirements requirements.txt
rm -f build/.lock
find build -name __pycache__ -type d -prune -exec rm -rf {} +
(cd build && zip -qr ../minha-task.zip . -x '*.pyc')
```

- Deixe fora do `requirements.txt` cada pacote que o worker já traz.
- O `cd build` torna cada caminho relativo à pasta, então o `.zip` não tem uma pasta `build/` de
  topo; `unzip -l minha-task.zip | head` lista `tasks.py`, e não `build/tasks.py`.

## Os valores da definição

Uma definição versionada guarda cada valor da conta como placeholder, `<NOME>`, e o portal precisa
dos valores reais. O `render` preenche os placeholders e imprime o resultado na tela; nada do que
ele imprime volta para o repositório. Uma definição que o portal salvou faz o caminho inverso com
`--placeholders`, e a cópia versionada então se compara com o arquivo importado.

**Os valores vêm de um arquivo JSON, da conta, ou dos dois.** Quando vêm dos dois, os do arquivo
completam e substituem os da conta:

```shell
awsds-workflows render meu-workflow.yaml --values-file valores.json > /tmp/meu-workflow.yaml
awsds-workflows render meu-workflow.yaml --profile meu-perfil \
    --subnet-name 'meu-projeto-private-*' --values-file imagem.json > /tmp/meu-workflow.yaml
awsds-workflows render --placeholders salvo.yaml --values-file valores.json
awsds-workflows values --profile meu-perfil --subnet-name 'meu-projeto-private-*' > valores.json
```

- **A leitura da conta** (`--profile`) roda só chamadas de leitura do STS, do IAM, do EC2 e, com
  `--image-name`, do SageMaker, e pede `--subnet-name`, o padrão do `Name` das sub-redes privadas do
  projeto (`awsds-sandbox-private-*` no laboratório). Numa conta com mais de um projeto, `--project`
  escolhe o id.
- **No ambiente alvo** o IAM e o SageMaker não responderam a partir de um space (leituras do
  serialize-db de 2026-09-21 e 2026-09-23), então lá os valores vêm de um arquivo. O `values` de
  uma máquina que alcança a conta escreve um arquivo inicial; os valores da imagem entram à mão.
- **Os valores que dependem da imagem**, `JOB_IMAGE_URI` e `JOB_PYTHON`, vêm do arquivo com a imagem
  padrão. Com uma imagem customizada registrada no SageMaker, `--image-name` lê o `JOB_IMAGE_URI`.

| Placeholder | O valor | De onde |
|---|---|---|
| `REGION` | a região do projeto | o perfil |
| `ACCOUNT_ID` | a conta do projeto | a credencial |
| `PROJECT_ROLE_NAME` | `datazone_usr_role_<projeto>_<ambiente>` | o papel do projeto |
| `PROJECT_ID`, `DOMAIN_ID`, `PROJECTS_BUCKET`, `PROJECT_KEY_ID` | o projeto, o domínio, o bucket do projeto e a chave KMS | as etiquetas que o SageMaker Unified Studio põe no papel |
| `PROJECT_SG` | o grupo de segurança do projeto, `datazone-<projeto>-<escopo>` | o EC2, na VPC da etiqueta `VpcId` do papel |
| `SUBNET_AZ1`, `SUBNET_AZ2` | as sub-redes privadas, em ordem de zona | o EC2, pelo `--subnet-name` |
| `JOB_IMAGE_URI` | a imagem do job | `--image-name` com uma imagem customizada; o arquivo com a padrão |
| `JOB_PYTHON` | o interpretador que o job chama | o arquivo |

Um nome fora desta tabela entra pelo arquivo de valores: o `render` preenche qualquer placeholder
que tenha valor e recusa o que não tem, listando todos os que faltam.

## Como ler uma execução

| Pergunta | Leitura |
|---|---|
| Como terminou cada task, e quanto tempo ocupou o worker? | `aws mwaa-serverless list-task-instances --workflow-arn <arn> --run-id <id>`; leia o `DurationInSeconds` de uma task, nunca o da execução |
| Por que uma task falhou? | o stream `workflow_id=<workflow>/run_id=<id>/task_id=<task>/attempt=<n>.log` no grupo de logs do workflow |
| O que o contêiner do job imprimiu, e por que ele falhou? | o stream do job em `/aws/sagemaker/ProcessingJobs`, e o `FailureReason` de `aws sagemaker describe-processing-job` |
| Por qual porta veio uma chamada, e como quem? | o `vpcEndpointId` e o `userIdentity` do `CreateProcessingJob` no CloudTrail |
| O resultado chegou, e com qual chave? | `aws s3api head-object` no resultado |

**Uma falha no aviso do editor não nomeia a causa**: "Workflow execution failed, please check the
task execution logs for more details". O log da task nomeia, e numa task de processamento o
`FailureReason` do job e o stream do contêiner também.

**Uma falha antes da primeira task** ("User template error: ...") é um template que o serviço não
conseguiu renderizar ao criar a execução ([Regras de autoria](#regras-de-autoria)).

`list-workflow-runs` devolve `RunType` nulo, então o tipo de uma execução é lido execução por
execução. Uma task que falhou roda de novo uma vez com o `retries` padrão: leia a duração da task,
e não a da execução.

## Limpeza

- **Apague um workflow** na página *Workflows*. O grupo de logs dele fica, sem retenção.
- **Esvazie as caixas de entrada** para a próxima execução começar de um estado conhecido; as
  caixas de saída são os resultados.
- **Um job de processamento não pode ser apagado**: ele continua listado.
- **Os `.zip` de código** em `dev/operatorFiles/` ficam com todas as versões, porque o bucket é
  versionado.
