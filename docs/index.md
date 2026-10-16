O `awsds-workflows` prepara o que um workflow de um projeto do SageMaker Unified Studio executa e
preenche a definição do workflow com os valores da sua conta. Um workflow é uma sequência de tasks
que o Amazon MWAA Serverless, o Apache Airflow gerenciado da AWS, roda por você: esperar um arquivo
chegar no S3, rodar um programa Python ou um comando Bash, iniciar um job de processamento do
SageMaker.

- **Para quem é**: quem monta workflows num projeto do SageMaker Unified Studio, como um cientista
  de dados, e a infraestrutura que dá ao projeto a permissão e a rede que eles pedem.
- **O problema que resolve**:
  - nem o worker que roda uma task nem o job de processamento alcançam o PyPI, então o código
    chega pronto, com cada dependência construída para quem vai rodá-lo;
  - o editor de workflows do portal não monta esse código nem preenche os valores da conta na
    definição;
  - o portal reescreve a definição a cada save, e a diferença para a cópia versionada não se lê a
    olho.
- **Como**: as ferramentas rodam numa máquina Linux com internet, onde o `uv` alcança o PyPI. O que
  elas gravam é copiado para o ambiente do SageMaker, que não tem internet: lá nada é instalado, e
  o código chega pronto, com as dependências ao lado.

| Comando | O que grava ou imprime | Onde o resultado vai |
|---|---|---|
| `package-task` | o `.zip` com o código de uma task Python ou Bash e as dependências dele | o worker |
| `package-job` | a pasta de código de um job de processamento, só com o que a imagem do job não tem | um job de processamento |
| `prepare-offline` | o `.tar.gz` da pasta de um projeto preparada com o próprio interpretador | um job de processamento, que o extrai no volume |
| `render` | o arquivo de definição do workflow preenchido com os valores do projeto, as variáveis da CLI de CI/CD traduzidas | a importação no portal |
| `values` | os valores do projeto, lidos da conta | o `render` |
| `compare` | o que difere no conteúdo de duas definições, como a versionada e a que o portal salvou | quem revisa uma mudança feita no portal |

As páginas desta documentação:

- **esta página**, o guia: o procedimento do começo ao fim, para quem vai montar o primeiro
  workflow;
- **`awsds_workflows.examples`**: o roteiro dos exemplos do repositório, comando por comando;
- **`awsds_workflows.lab_notes`**: o que rodou no laboratório e no ambiente alvo, com a data de
  cada leitura, e o que ainda não foi medido; cada seção deste guia resume o estado num aviso que
  aponta para lá;
- **a referência de cada módulo**, no menu: `awsds_workflows.package_task`,
  `awsds_workflows.package_job`, `awsds_workflows.prepare_offline`, `awsds_workflows.render`,
  `awsds_workflows.compare`, `awsds_workflows.errors` e `awsds_workflows.cli`.

| Seção | Para quem | O que traz |
|---|---|---|
| [Início rápido](#inicio-rapido) | todos | uma task Python, do projeto à execução |
| [Os conceitos](#os-conceitos) | todos | os termos desta página |
| [Instalação](#instalacao) | todos | o pacote na máquina que empacota, e o Python que o `uv` usa nela |
| [Os exemplos](#os-exemplos) | todos | os workflows de exemplo da pasta `examples/` do repositório e uma aplicação da CLI de CI/CD com um job do Visual ETL; os passos de cada um estão na página `awsds_workflows.examples` |
| [As peças](#as-pecas) | todos | onde ficam o arquivo de definição do workflow, o código, os logs e as execuções, e o que é o worker |
| [A imagem do job](#a-imagem-do-job) | todos | a imagem padrão do SageMaker ou uma customizada, o que muda, e o arquivo de ambiente |
| [A permissão do projeto](#a-permissao-do-projeto) | infraestrutura | a política que o papel do projeto precisa antes do primeiro job |
| [A rede](#a-rede) | infraestrutura | os endpoints que o worker e o job usam |
| [Regras de autoria](#regras-de-autoria) | cientista de dados | o formato do YAML, o editor, a importação, os erros do save, os templates, o sensor |
| [Uma task de processamento](#uma-task-de-processamento) | cientista de dados | um job na imagem escolhida, a pasta de código com `package-job` e o `.tar.gz` da pasta do projeto com `prepare-offline` |
| [O código de uma task Python ou Bash](#o-codigo-de-uma-task-python-ou-bash) | cientista de dados | o `.zip` com `package-task`, e uma task Python |
| [Uma task Bash](#uma-task-bash) | cientista de dados | o `BashOperator`: o comando, o ambiente do worker e o código que ele chama |
| [Os valores da definição](#os-valores-da-definicao) | todos | os placeholders, o `render`, os valores lidos de dentro de um espaço e o `compare` com a definição que o portal salvou |
| [Como ler uma execução](#como-ler-uma-execucao) | todos | uma leitura por pergunta |
| [Limpeza](#limpeza) | todos | o que fica depois de um workflow |

## Início rápido

Uma task Python no worker, do projeto `uv` à execução. Cada passo diz onde roda; o que cada um
pede está na seção que ele aponta.

1. **Na máquina que empacota**, um Linux com internet e com o `uv`, instale o pacote
   ([Instalação](#instalacao)):

   ```shell
   uv tool install git+https://github.com/felipenoris/awsds-workflows
   ```

2. **Num espaço do projeto**, leia os valores da conta com o script `scripts/space_values.py` do
   repositório, copiado para o espaço, e traga o `space_values.json` para a máquina que empacota
   ([Os valores de dentro de um espaço](#os-valores-de-dentro-de-um-espaco)):

   ```shell
   python space_values.py > space_values.json
   ```

3. **Na máquina que empacota**, monte o `.zip` da task a partir do projeto e do módulo de entrada,
   o arquivo com a função que a task chama ([O `.zip` com `package-task`](#o-zip-com-package-task)):

   ```shell
   awsds-workflows package-task ~/src/meu-projeto ~/src/meu-projeto/tasks.py /tmp/meu-projeto.zip
   ```

4. **Na máquina que empacota**, preencha a definição do workflow, escrita pelas
   [Regras de autoria](#regras-de-autoria) com uma task como a de
   [A task Python na definição](#a-task-python-na-definicao):

   ```shell
   awsds-workflows render meu-workflow.yaml --values-file space_values.json > /tmp/meu-workflow.yaml
   ```

5. **No portal**, na página *Workflows* do projeto:

   - crie um workflow vazio;
   - envie `/tmp/meu-projeto.zip` em *Settings → Storage → Python/Bash Operator Files*;
   - importe `/tmp/meu-workflow.yaml` em *Actions → Import definition file*;
   - salve e execute.

6. **Leia o log da task** na execução ([Como ler uma execução](#como-ler-uma-execucao)).

> [!TIP]
> O exemplo `demo-python-operator` do repositório percorre estes passos com um projeto, um módulo
> de entrada e uma definição prontos:
> [os passos dele](awsds_workflows/examples.html#demo-python-operator).

Depois do primeiro workflow:

- **uma task de processamento** pede antes a permissão do projeto e a escolha da imagem do job
  ([A permissão do projeto](#a-permissao-do-projeto), [A imagem do job](#a-imagem-do-job));
- **uma mudança feita no portal** se lê comparando a definição salva com a versionada
  ([A definição que o portal salvou](#a-definicao-que-o-portal-salvou)).

## Os conceitos

Os termos desta página, na ordem em que um workflow os usa.

**O workflow e a sua definição.** Na página *Workflows* de um projeto, um workflow é descrito por
um arquivo YAML, o arquivo de definição do workflow: as tasks, os parâmetros de cada uma e a ordem
entre elas. O MWAA Serverless o executa: prepara um worker para cada task, roda a task nele e grava
os logs. A definição fica no bucket do projeto, e o portal a reescreve a cada save
([As peças](#as-pecas)).

**As tasks e os operadores.** Cada task da definição é um operador do Airflow, uma classe que sabe
fazer uma coisa, com os parâmetros dela. Três tipos de task entram nos workflows desta página:

| A task | O operador | Onde roda | O código dela |
|---|---|---|---|
| um sensor, que espera um arquivo no S3 | `S3KeySensor` | no worker | nenhum: só os parâmetros |
| uma task Python ou Bash | `PythonOperator`, `BashOperator` | no worker | um `.zip` com o seu código e as dependências, montado pelo `package-task` |
| uma task de processamento | `SageMakerProcessingOperator` | num job de processamento do SageMaker, na imagem que a task nomeia | uma pasta de código no S3, montada pelo `package-job`, ou o `.tar.gz` da pasta do projeto, gravado pelo `prepare-offline` |

**O worker** é a máquina pequena que o MWAA Serverless prepara para cada task, com Python 3.12, o
Airflow e sem internet. Uma task Python ou Bash roda nele. Numa task de processamento, ele roda só
o operador: o trabalho acontece num job de processamento do SageMaker, um contêiner que a AWS
inicia numa instância à parte, com a imagem que a task escolhe, e que no laboratório roda isolado
da rede.

> [!WARNING]
> **Nem o worker nem o job alcançam o PyPI**, então um `pip install` não existe lá. O código e cada
> dependência chegam prontos, construídos para o interpretador e a plataforma de quem vai rodá-los:
> o `.zip` de uma task para o worker, a pasta ou o `.tar.gz` de um job para a imagem do job. As
> ferramentas de empacotamento partem de um projeto gerenciado pelo `uv`, com `pyproject.toml` e
> `uv.lock`.

**A definição versionada e os valores.** A definição guardada no git escreve cada valor da conta,
como o id do projeto e o bucket, como um placeholder: `<PROJECT_ID>`, `<PROJECTS_BUCKET>`. O
`render` troca os placeholders pelos valores do projeto antes da importação no portal, o caminho
inverso devolve os placeholders a uma definição que o portal salvou, e o `compare` mostra o que
ela mudou.

**O laboratório e o ambiente alvo.** O laboratório é a conta de testes em que os passos desta
página foram medidos. O ambiente alvo é o SageMaker Unified Studio em que os workflows vão rodar.
O que rodou em cada um, com as datas, e o que ainda não foi medido estão em
`awsds_workflows.lab_notes`.

## Instalação

Instale o pacote na máquina que empacota: um Linux com internet e com o
[`uv`](https://docs.astral.sh/uv/) no `PATH`. O que ela grava é copiado depois para o ambiente do
SageMaker.

Como o comando `awsds-workflows`:

```shell
uv tool install git+https://github.com/felipenoris/awsds-workflows
```

Ou como dependência de um projeto:

```shell
uv add git+https://github.com/felipenoris/awsds-workflows
```

> [!CAUTION]
> **Instale pelo endereço do repositório ou por uma pasta local, nunca pelo nome.** O nome
> `awsds-workflows` está livre no PyPI (lido em 2026-10-11), e um pacote publicado lá com esse nome
> por outra pessoa seria instalado no lugar deste.

O comando instalado pelo endereço, sem um commit fixo, acompanha a `main` com:

```shell
uv tool upgrade awsds-workflows
```

> [!TIP]
> **O commit instalado** é o `commit_id` do arquivo `direct_url.json`, dentro de
> `$(uv tool dir)/awsds-workflows/`; o `uv tool list` mostra o endereço, e não o commit.

O que o pacote pede:

- **o Python 3.12 ou mais novo**, que o `uv` instala; o pacote é testado no 3.12, no 3.13 e no
  3.14;
- **o `uv`**, que ele chama como programa;
- **as dependências dele**: o `packaging`, que avalia os marcadores do arquivo de ambiente da
  imagem ([A imagem do job](#a-imagem-do-job)), e o PyYAML, que lê as definições que o `compare`
  compara.

> [!NOTE]
> **Estado**: o `uv tool upgrade` foi medido
> ([as notas](awsds_workflows/lab_notes.html#instalacao)).

### O Python que o `uv` usa

O `package-task` e o `package-job` rodam o `uv` na pasta do projeto, e o `uv` escolhe um
interpretador que o projeto aceite:

1. o que o `.python-version` do projeto nomeia;
2. sem esse arquivo, um que satisfaça o `requires-python`;
3. sem nenhum, um que ele baixa, a menos que os downloads de Python estejam desligados.

O `prepare-offline` não usa esse interpretador: ele pede ao `uv` o CPython da versão dada, baixado
para dentro da cópia do projeto, com os downloads ligados nessa chamada
([A pasta do projeto preparada num `.tar.gz`](#a-pasta-do-projeto-preparada-num-targz)).

> [!WARNING]
> **Num espaço, o `uv` pode não achar o Python do job.** Num espaço do laboratório, a imagem
> desliga os downloads (`UV_PYTHON_DOWNLOADS=never`), e o `uv` acha só o Python da distribuição,
> `/opt/conda/bin/python` 3.12. O interpretador do job, `/opt/awsds/venv/bin/python` 3.13, fica
> fora dos caminhos em que o `uv` procura, e um projeto que pede o 3.13 é recusado com
> `No interpreter found for Python 3.13`.

A saída é a variável `UV_PYTHON` do próprio `uv`, que nomeia o interpretador; o pacote a repassa a
cada chamada do `uv`:

```shell
UV_PYTHON=/opt/awsds/venv/bin/python awsds-workflows package-job ~/src/meu-projeto \
    /tmp/meu-projeto-0.2.0 --environment ambiente.txt --python 3.13
```

> [!NOTE]
> **Estado**: medido num espaço simulado; num espaço de verdade, o pacote ainda não rodou
> ([as notas](awsds_workflows/lab_notes.html#o-python-que-o-uv-usa)).

## Os exemplos

A pasta [`examples/`](https://github.com/felipenoris/awsds-workflows/tree/main/examples) do
repositório traz workflows de exemplo, cada um com a definição, o código e um `README.md` que diz
o que ele mostra e o que cada execução leu. Os passos para reproduzi-los, na ordem em que cada
comando roda, estão na página `awsds_workflows.examples`.

| Exemplo | O que ele mostra |
|---|---|
| `probe-worker` | o que o worker tem: disco, CPU, memória, ferramentas e pacotes, numa task Bash inline |
| `demo-python-operator` | uma task Python sobre o `.zip` do `package-task` |
| `demo-bash-operator` | uma task Bash sobre o mesmo projeto, com dois scripts, e a prova de que o worker não alcança a PyPI |
| `demo-devenv-job` | um job de processamento na imagem padrão do SageMaker, sobre o `.tar.gz` da pasta do projeto gravado pelo `prepare-offline` |
| `redshift-unload` | uma task Python que descarrega uma consulta ao Redshift Serverless no S3, com `UNLOAD` |
| `houseprice-etl` | um job do Visual ETL numa aplicação da CLI de CI/CD do SageMaker Unified Studio: uma task `GlueJobOperator` cria ou atualiza o job do Glue e o executa |

- **O projeto dos `demo-*`.** Os três dividem um projeto `uv`, `examples/awsds-demo-job/`: um CSV
  entra, um resumo em JSON sai.
- **Os valores.** Eles vêm do `space_values.json` que o script de
  [Os valores de dentro de um espaço](#os-valores-de-dentro-de-um-espaco) escreve, mais o
  `extra_values.json` da pasta de cada exemplo: um arquivo de modelo com o prefixo do exemplo no
  bucket, `EXAMPLE_PREFIX`, e os valores que o espaço não dá, por preencher no job e no
  `redshift-unload`. O `render` lê os dois, na ordem da linha de comando
  ([Os valores da definição](#os-valores-da-definicao)).
- **Os testes do repositório** renderizam cada definição com o arquivo dela e valores fabricados,
  constroem os dois `.zip`, preparam o `.tar.gz` do job e conferem que o workflow da aplicação do
  `houseprice-etl`, com as variáveis da CLI, é a definição dele.

> [!NOTE]
> **Estado**: os exemplos rodaram no ambiente alvo, menos o `demo-devenv-job`, que parou na
> permissão do projeto, e o `houseprice-etl`, que ainda não rodou num projeto
> ([as notas](awsds_workflows/lab_notes.html#os-exemplos)).

## As peças

Onde cada peça de um workflow fica, para você saber onde procurar o que enviou e o que o serviço
gravou.

| O quê | Onde | Nota |
|---|---|---|
| o arquivo de definição do workflow | `s3://<bucket do projeto>/<domínio>/<projeto>/dev/workflows/<nome>.yaml` | gravado pelo portal a cada save; *View code* o mostra |
| o `.zip` de uma task Python ou Bash | `.../dev/operatorFiles/<arquivo>` | enviado em *Settings → Storage*; um `.zip` é guardado como foi enviado, e o workflow fixa a versão S3 dele |
| a cópia do código que o serviço guarda | `mwaa-serverless-code-files-<conta da AWS>-<região>-prod`, um bucket do serviço | tirada a cada save, fora do bucket do projeto, e cifrada com a chave do projeto; o worker a busca pelo endpoint de gateway do S3 ([A rede](#a-rede)) |
| os logs das tasks | `/aws/mwaa-serverless/<domínio>-<projeto>/<workflow>`, um stream por tentativa de task | por projeto, sem retenção; o grupo existe desde o primeiro save, antes de qualquer execução, e sobrevive ao workflow |
| a saída do contêiner de um job | `/aws/sagemaker/ProcessingJobs`, stream `<job>/algo-1-<n>` | da conta inteira: todo papel de projeto da conta pode lê-la |
| a identidade | o papel do projeto, `datazone_usr_role_<projeto>_<ambiente>`, o papel do IAM com que o projeto age; sessão `AmazonMWAAServerless` no worker e `SageMaker` dentro de um job | |
| a rede | as sub-redes privadas e o grupo de segurança do projeto, injetados pelo portal | sem rota padrão: a AWS é alcançada pelos endpoints de VPC ([A rede](#a-rede)) |
| a chave | a chave KMS do projeto | cifra o workflow, o volume e as saídas do job, e o bucket |

**O worker**, segundo o guia da AWS do MWAA Serverless (lido em 2026-10-11):

| | O worker |
|---|---|
| CPU e memória | 1 vCPU e 3 GiB; dimensione a task por esses números |
| Python e pacotes | Python 3.12, Airflow 3.0.6, o provider da Amazon 9.32.0 e o `boto3` 1.43.1 |
| rede | sem internet e sem proxy |
| custo | 0,088 USD por task-hora, com mínimo de um minuto; uma task ocupa o worker durante toda a sua duração, a espera de um sensor incluída |

> [!IMPORTANT]
> **Cada task tem o seu worker.** Um arquivo que uma task grava no disco não chega à seguinte:
> passe os dados de uma task a outra pelo S3.

> [!NOTE]
> **Estado**: um worker por task foi medido no laboratório, e um arquivo gravado no disco por uma
> task e procurado pela seguinte ainda não. Um worker do ambiente alvo tinha mais CPU e memória
> que o guia diz, numa execução que não diz se o excedente se repete
> ([as notas](awsds_workflows/lab_notes.html#as-pecas)).

## A imagem do job

Um job de processamento roda dentro de uma imagem de contêiner, e a definição da task diz qual. O
pacote não supõe nenhuma: a imagem decide o interpretador que o job chama, a versão do Python e os
pacotes já instalados, e cada um desses fatos entra no `package-job` e na definição. As tasks
Python e Bash não dependem da imagem, porque rodam no worker.

Duas imagens servem:

- **a imagem padrão do SageMaker**, a SageMaker Distribution que a AWS publica;
- **uma imagem customizada**, registrada no SageMaker pela infraestrutura.

A tabela diz de onde vem cada valor em cada caso.

| | A imagem padrão do SageMaker | Uma imagem customizada |
|---|---|---|
| exemplo | a SageMaker Distribution 4.5, a imagem inicial do ambiente alvo | a imagem do laboratório, `awsds-sandbox-dev-env` |
| `JOB_IMAGE_URI`, a imagem na definição | o URI da distribuição na região do projeto, escrito no arquivo de valores | lido da imagem registrada no SageMaker (`values --image-name`) ou escrito no arquivo de valores |
| `JOB_PYTHON`, o interpretador que o job chama | `/opt/conda/bin/python` | o do ambiente da imagem; na do laboratório, `/opt/awsds/venv/bin/python` |
| `--python`, a versão desse interpretador | lida com `/opt/conda/bin/python --version` num espaço que roda a imagem | na do laboratório, 3.13 |
| o arquivo de ambiente, a lista do que a imagem já tem | `uv pip list --format freeze --python /opt/conda/bin/python` num espaço que roda a imagem | o mesmo comando com o interpretador da imagem, ou o `uv export` do projeto que constrói a imagem |

> [!NOTE]
> **Estado**: na SageMaker Distribution 4.5, ainda não foram medidos o URI da imagem para um job
> no ambiente alvo nem o usuário do contêiner de um job; o espaço do ambiente alvo roda a 4.5, e o
> patch dela não foi lido ([as notas](awsds_workflows/lab_notes.html#a-imagem-do-job)).

### O arquivo de ambiente

O arquivo de ambiente diz ao `package-job` o que a imagem já tem, para a pasta de código levar só
o resto.

1. **Num espaço do projeto que roda a imagem do job**, o ambiente interativo do portal (JupyterLab
   ou Code Editor), sem internet, grave o arquivo:

   ```shell
   uv pip list --format freeze --python /opt/conda/bin/python > ambiente.txt
   ```

2. **Copie o `ambiente.txt` para a máquina que empacota.**

> [!WARNING]
> **Use o `uv pip list --format freeze`, e não o `pip freeze`.** O `uv pip list --format freeze`
> escreve só linhas `nome==versão`; o `pip freeze` escreve `nome @ file:///...` para um pacote
> instalado pelo conda, e o `package-job` recusa essa linha: se a ignorasse, o pacote pareceria
> ausente da imagem e entraria na pasta.

> [!IMPORTANT]
> **O arquivo vale para aquela versão da imagem.** Uma imagem nova pede um arquivo novo e uma
> pasta de código nova.

Uma imagem construída de um projeto `uv`, como a do laboratório, dá o arquivo sem um espaço: o
lock do projeto que a constrói, exportado na pasta dele.

```shell
uv export --frozen --no-dev --no-emit-project --no-hashes > ambiente.txt
```

O `package-job` e o `job-constraints` aceitam esse arquivo com o cabeçalho e as anotações `# via`
que o `uv` escreve.

> [!NOTE]
> **Estado**: o arquivo exportado do projeto da imagem do laboratório foi medido
> ([as notas](awsds_workflows/lab_notes.html#a-imagem-do-job)).

## A permissão do projeto

Tudo num workflow roda como o papel do projeto, e a política dele vem do blueprint, o conjunto de
regras com que o SageMaker Unified Studio cria o ambiente do projeto.

> [!WARNING]
> **A política do blueprint não basta para o `SageMakerProcessingOperator`.** Sem a política desta
> seção, nenhum job de processamento chega a existir: a execução para numa recusa do papel do
> projeto.

Os motivos:

- **O operador descreve o nome do job antes de criá-lo**, e o blueprint deixa o papel descrever só
  um job com a etiqueta do próprio projeto. Um nome ainda livre não tem etiqueta, então a primeira
  execução falha com `AccessDeniedException` em `DescribeProcessingJob`, antes de existir um job.
- **Criar um job com etiquetas também é autorizado como `sagemaker:AddTags`**, e o blueprint tira
  toda chave `AmazonDataZone*` do `AddTags` enquanto exige que o job leve a etiqueta
  `AmazonDataZoneProject`. A segunda execução falha com `AccessDeniedException` em
  `sagemaker:AddTags`.

> [!NOTE]
> **Estado**: as duas recusas foram medidas no laboratório; no ambiente alvo, a primeira execução
> parou na primeira delas ([as notas](awsds_workflows/lab_notes.html#a-permissao-do-projeto)).

Para dar a permissão:

1. **Anexe a política abaixo a cada papel de projeto que roda jobs.** O papel nasce com o ambiente
   Tooling do projeto e se chama `datazone_usr_role_<projeto>_<ambiente>`; quem mantém a conta com
   Terraform anexa a política a esse nome depois que o projeto existe.
2. **Troque `<REGION>` e `<ACCOUNT_ID>`** pela região e pela conta do projeto.

A política permite o `DescribeProcessingJob` de um job sem etiqueta de projeto e o `AddTags` só da
etiqueta do próprio projeto, num job sem etiqueta ou com a do chamador; os jobs de outro projeto
ficam fora de alcance.

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

O worker roda nas sub-redes privadas do projeto, sem rota para a internet, e alcança cada serviço
da AWS por um endpoint de VPC, uma porta privada para aquele serviço; um serviço sem endpoint não
responde.

| Quem | Chama | Por onde |
|---|---|---|
| o operador de processamento, como o papel do projeto | `CreateProcessingJob` e `DescribeProcessingJob` | o endpoint de interface `sagemaker.api` |
| o worker, ao gravar o log | `CreateLogStream` | o endpoint `logs` |
| uma task que chama o STS | o STS | o endpoint de interface `sts` |
| o sensor, ao listar o prefixo | o S3 | o endpoint de gateway do S3 |
| o worker de um workflow com código | um `GetObject` da cópia que o serviço guarda em `mwaa-serverless-code-files-<conta da AWS>-<região>-prod`, como o principal de serviço `airflow-serverless.amazonaws.com` | o endpoint de gateway do S3 |
| a plataforma, ao baixar a imagem do job | o registro da imagem | fora da rede do projeto, então um job isolado não precisa de endpoint do ECR |

> [!WARNING]
> **A política do endpoint de gateway do S3 tem de admitir o bucket da cópia do código.** Uma
> política que não admite `mwaa-serverless-code-files-<conta da AWS>-<região>-prod` faz o worker
> falhar antes da primeira task, com `Execution environment preparation failed due to an internal
> server error`, e só um evento de atividade de rede do CloudTrail, com `errorCode`
> `VpceAccessDenied`, nomeia a recusa. Com o bucket admitido, o mesmo workflow roda.

> [!WARNING]
> **A internet não responde.** Uma task que tenta o PyPI falha:
>
> - onde o firewall de DNS da VPC recusa o nome, na resolução, em segundos; o Python do worker lê
>   essa recusa como `[Errno 16] Device or resource busy`, e não como um nome que não existe;
> - onde o nome resolve para um endereço público, na conexão, com
>   `[Errno 101] Network is unreachable`, depois dos timeouts de conexão.

> [!NOTE]
> **Estado**: a tabela e os avisos foram medidos no laboratório. No ambiente alvo, o worker usou o
> S3, a API do SageMaker, o STS e os logs, e o caminho do job, do download da imagem à gravação da
> saída, ainda não foi medido ([as notas](awsds_workflows/lab_notes.html#a-rede)).

## Regras de autoria

O que o laboratório aprendeu escrevendo e importando definições. Leia esta seção antes de escrever
a sua.

**O formato do YAML é o da AWS.** A AWS define o formato do arquivo de definição do workflow para o
MWAA Serverless, que o valida antes de executar. A seção *YAML support* do guia descreve o formato,
com um exemplo e os templates Jinja2, e não publica um esquema:
[MWAA Serverless, YAML support](https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/mwaas-concepts.html#yaml-dag-authoring).
Cada task é um operador do Airflow com os parâmetros dele, nos limites que o serviço impõe. O
conversor de DAGs Python para YAML da AWS,
[`python-to-yaml-dag-converter-mwaa-serverless`](https://github.com/awslabs/python-to-yaml-dag-converter-mwaa-serverless),
escreve DAGs compatíveis com o [dag-factory](https://github.com/astronomer/dag-factory) 1.0, a
biblioteca da Astronomer que monta DAGs do Airflow a partir de YAML e que o worker traz instalada
(lido em 2026-10-11).

**Crie vazio, depois importe.**

1. Na página *Workflows*, crie um workflow vazio.
2. Use *Actions → Import definition file* com a definição preenchida pelo `render`.
3. Salve.

Os formulários do editor não expressam tudo o que uma definição expressa, e a importação guarda
cada campo: a definição salva difere da importada só por `is_paused_upon_creation: false`, pela
ordem das chaves e por textos longos dobrados.

> [!WARNING]
> **Uma importação não substitui um workflow salvo.** Importado no editor de um workflow já salvo,
> o arquivo vira um workflow novo com o mesmo nome, e o save é recusado com
> `ConflictException: Workflow with given name already exists`. Apague antes o workflow antigo
> (lista *Workflows*, *Delete workflow*, e a palavra "confirm") e então salve: o CloudTrail
> registra `DeleteWorkflow` e depois `CreateWorkflow`, o sufixo do ARN muda, e o histórico de
> execuções e de versões recomeça. O grupo de logs leva o nome do workflow e guarda os logs de
> cada execução.

> [!IMPORTANT]
> **A primeira linha do YAML é o layout do editor**, um comentário JSON como
> `# {"wait_for_file":{"x":120,"y":200},...}`, com a posição de cada task no desenho. Mantenha-a,
> e não ponha outro comentário num arquivo que vai ser importado.

### Os erros do save

| O portal diz | O que aconteceu | Saída |
|---|---|---|
| `ValidationException: Code not found in specified S3 location` | o editor preenche o campo *Operator files zip S3 location* num workflow novo, vazio ou importado, mesmo sem task Python ou Bash, e o save o enviou sem nenhum arquivo nesse local | envie o arquivo da task em *Settings → Storage*; num workflow sem código (só comandos Bash inline, ou nenhuma task Python ou Bash), esvazie o campo antes de salvar, e o save não manda o `Code` |
| `ContainerArguments: Container argument is required` | o editor exige argumentos numa task de processamento, embora a API não os exija | separe o comando em programa (`ContainerEntrypoint`) e argumentos (`ContainerArguments`) |
| dois workflows com o mesmo nome | dois saves feitos a 2 s um do outro passaram juntos pela conferência do nome | apague um; fora dessa corrida, o nome é conferido |

### Os templates

Um template é um trecho entre `{{ }}` que o serviço troca por um valor quando a execução é criada,
com a sintaxe Jinja do Airflow. O serviço conhece só `macros`, `ti`/`task_instance`, `params`,
`ds`, `ds_nodash`, `ts` e `ts_nodash`:

- `{{ ts_nodash }}` é a meia-noite do dia numa execução manual, então duas execuções no mesmo dia
  colidem nele;
- `{{ dag_run... }}` derruba a execução antes da primeira task ("'dag_run' is undefined");
- um método de um objeto que uma macro devolveu também derruba ("access to attribute 'strftime' of
  'datetime' object is unsafe");
- as funções de um módulo passam.

> [!TIP]
> **Um carimbo por execução**:
> `{{ macros.time.strftime('%Y%m%dT%H%M%S', macros.time.gmtime()) }}`.

**Parâmetros que o serviço ignora ou limita**: `deferrable`, `trigger_rule`,
`render_template_as_native_obj` e `do_xcom_push` são ignorados, então uma lista renderizada chega
como texto. `retries` vale 1 por padrão e no máximo 3, e `execution_timeout` vai até 3.600 s.

> [!TIP]
> **Escreva `retries: 0` em cada task durante o desenvolvimento**, ou uma falha roda duas vezes.

### O sensor de arquivo

Um sensor é uma task que espera uma condição, conferindo-a de tempos em tempos. O `S3KeySensor`
com `wildcard_match: true`, `poke_interval: 30`, `timeout: 600` e `soft_fail: true` espera até 10
minutos por um arquivo que case com o padrão, conferindo a cada 30 s, e termina a execução sem erro
se nada chegar.

> [!WARNING]
> **Observe `inbox/?*`, e não `inbox/*`.** O `mkdir` de um espaço deixa um marcador de pasta de
> zero bytes, `inbox/`, e `inbox/*` casa com ele. O `?*` pede um caractere depois da barra; o `*`
> só serve quando uma task seguinte apaga o prefixo inteiro.

**Uma caixa de entrada vazia** termina a execução com `SUCCESS`, por causa do `soft_fail`, depois
do timeout. A API lê então o estado do sensor como `NONE`, e não `SKIPPED`, e não lista instância
para as tasks seguintes; só o log da task diz `Skipping task.` A espera cobra os seus 10 minutos
(cerca de 0,015 USD).

## Uma task de processamento

Uma task de processamento inicia um job de processamento do SageMaker: um contêiner com a imagem
escolhida, numa instância à parte, que recebe entradas do S3, roda um comando e devolve as saídas
ao S3. O `config` da task é a chamada `CreateProcessingJob` inteira, em YAML.

> [!IMPORTANT]
> **Escreva o `config` inteiro da task no YAML e importe-o.** O formulário *SageMaker Processing*
> do portal não tem campo para `NetworkConfig`, para as chaves KMS nem para as etiquetas, e um job
> sem eles pode ser recusado pelas regras do ambiente
> ([Uma definição de exemplo](#uma-definicao-de-exemplo)).

**O que o ambiente exige do job.** No laboratório, o limite de permissões dos papéis de projeto, a
política que a infraestrutura põe por cima de cada papel, exige em todo job:

- `NetworkConfig.VpcConfig`: as duas sub-redes privadas e o grupo de segurança do projeto;
- `EnableNetworkIsolation: true`: o contêiner não tem rede nem credenciais da AWS;
- `EnableInterContainerTrafficEncryption: true`, mesmo com uma só instância;
- `ProcessingResources.ClusterConfig.VolumeKmsKeyId`: a chave do projeto;
- um tipo de instância dentro do teto do limite; `ml.t3.medium` é o menor que ele admite.

As regras do próprio projeto acrescentam `Tags: [{Key: AmazonDataZoneProject, Value: <projeto>}]`
e o `KmsKeyId` da saída, a chave do projeto. Outro ambiente pode exigir outra lista; a recusa do
`CreateProcessingJob` no log da task a nomeia.

**As entradas e as saídas ficam em `/opt/ml/processing/`.** O SageMaker baixa cada
`ProcessingInput` para uma pasta de lá antes de o comando começar e envia cada `ProcessingOutput`
ao S3 depois que ele termina, como o papel do projeto.

> [!WARNING]
> **O usuário do contêiner não grava na pasta de saída.** A imagem do laboratório roda como
> `sagemaker-user` (uid 1000), e a plataforma cria cada pasta montada como root com modo 755; uma
> gravação falha com `Permission denied`, e o job termina com `AlgorithmError: , exit code: 1`. O
> `sudo` da imagem funciona dentro de um job, então o comando abre com um `chown`.

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

**O código é mais uma entrada do job**, numa de duas formas: a pasta que o `package-job` grava,
copiada para o S3 do projeto, ou o `.tar.gz` que o `prepare-offline` grava, que o comando do job
extrai no volume.

| | A pasta de código do `package-job` | O `.tar.gz` do `prepare-offline` |
|---|---|---|
| o interpretador | o da imagem, `<JOB_PYTHON>` | o CPython que vai dentro da pasta |
| as dependências | só as que a imagem não tem | todas as do projeto, na `.venv/` da pasta |
| as versões | as da imagem, em tudo o que o projeto compartilha com ela | as do lock do projeto, que não precisa concordar com a imagem |
| no S3 | um prefixo com um objeto por arquivo | um objeto só |
| o que a imagem precisa ter | o interpretador e os pacotes que o projeto compartilha com ela | só o sistema, o `bash`, o `tar`, o `gzip`, o `sudo` e a glibc |
| o comando do job | roda `<JOB_PYTHON>`, com o `PYTHONPATH` na pasta | extrai o `.tar.gz` e roda o `.venv/bin/python` da pasta |

### A pasta de código com `package-job`

O job não tem rede, então as dependências do projeto ou vêm no ambiente da imagem ou viajam na
entrada de código; nada é instalado na execução. O que separa essa entrada do `.zip` de uma task:

- **O interpretador é o da imagem do job**, e não o do worker.
- **A entrada é uma pasta, e não um arquivo.** Um `ProcessingInput` baixa um prefixo do S3, e um
  módulo de extensão (um pacote com código compilado) não é importado de um `.zip` no `sys.path`.
- **A precedência é a do `python3` de uma task Bash, e a inversa da de uma task Python.** O
  `PYTHONPATH` vem antes do `site-packages` da imagem, então um pacote presente nos dois esconderia
  a cópia da imagem. A pasta leva só o que a imagem não tem, e as versões do projeto têm de ser
  iguais às da imagem em tudo o que os dois compartilham.

1. **Prepare o projeto.**
   - Ele tem um `pyproject.toml` e um `uv.lock` em dia.
   - O `requires-python` dele admite o Python da imagem.
   - O código próprio dele é Python puro, e roda como `python -m meu_pacote` (um `__main__.py`).

2. **Gere o arquivo de ambiente da imagem** num espaço que roda a imagem do job e copie-o para a
   máquina que empacota ([O arquivo de ambiente](#o-arquivo-de-ambiente)):

   ```shell
   uv pip list --format freeze --python /opt/conda/bin/python > ambiente.txt
   ```

3. **Confira o projeto contra a imagem e grave a pasta**, com a versão do Python da imagem. A pasta
   de saída ainda não pode existir.

   ```shell
   awsds-workflows package-job ~/src/meu-projeto /tmp/meu-projeto-0.2.0 \
       --environment ambiente.txt --python 3.12
   ```

   Num espaço, o `uv` pode não achar o Python que o projeto pede
   ([O Python que o `uv` usa](#o-python-que-o-uv-usa)).

4. **Se ele apontar uma discordância**, cole no `pyproject.toml` do projeto o bloco que ele
   imprime:

   ```toml
   [tool.uv]
   constraint-dependencies = [
     "boto3==1.43.92",
     ...
   ]
   ```

   O bloco fixa cada pacote que o projeto compartilha com a imagem na versão da imagem, o que
   também põe os testes do projeto nas versões que o job importa.

5. **Trave o projeto de novo** e repita o passo 3:

   ```shell
   uv lock
   ```

   Quando um limite inferior do projeto passa de uma versão da imagem, esse lock falha, e a
   dependência não serve a esta imagem: ela pede outra versão, outro pacote ou outra imagem.

6. **Leia o que ele imprimiu**: a pasta e o tamanho, o que vem da imagem, o que a pasta leva e a
   raiz, que tem só o projeto e os pacotes que a imagem não tem.

7. **Copie a pasta para o S3 do projeto, num prefixo só desta versão.** Uma entrada baixa o prefixo
   inteiro, então uma cópia sobre uma pasta mais velha misturaria duas versões.

   ```shell
   aws s3 cp --recursive /tmp/meu-projeto-0.2.0 \
       s3://<bucket do projeto>/<domínio>/<projeto>/shared/jobs/meu-projeto-0.2.0/
   ```

   Num espaço com o `~/shared/` do projeto, a mesma cópia é:

   ```shell
   mkdir -p ~/shared/jobs
   cp -r /tmp/meu-projeto-0.2.0 ~/shared/jobs/
   ```

   O `shared/` grava no prefixo um marcador de zero bytes por pasta, e o job baixa um prefixo assim
   sem problema.

8. **Nomeie a pasta no `config` do job**, ao lado das exigências do ambiente, e importe a
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

> [!TIP]
> **As versões da imagem como requisitos**, para `uv pip compile -c` ou `uv add -c`, saem do
> `job-constraints`:
>
> ```shell
> awsds-workflows job-constraints --environment ambiente.txt --python 3.12
> ```

**Uma versão nova.** Uma versão nova da imagem muda o alvo: gere o arquivo de ambiente de novo e
grave uma pasta nova. Uma versão nova do código são os passos 3, 7 e 8 com um nome de pasta novo. O
job lê o prefixo a cada execução, sem cópia tirada num save.

As opções do `package-job`:

| Opção | O padrão | O que ela diz |
|---|---|---|
| `--environment ARQUIVO` | nenhum: é obrigatória | o arquivo de ambiente da imagem |
| `--python X.Y` | nenhum: é obrigatória | a versão do interpretador que o job chama |
| `--platform ETIQUETA` | `x86_64-manylinux_2_28` | a etiqueta dos wheels: o padrão é Linux x86_64 com glibc 2.28 ou mais nova, e `ldd --version` num espaço diz a glibc da imagem |

#### Quando o `package-job` recusa

| Ele diz | Significado | O que fazer |
|---|---|---|
| `não há uv.lock em ...` | o projeto nunca foi travado | `uv lock` no projeto |
| `... já existe: nomeie uma pasta nova` | a pasta de saída já está lá | uma pasta nova, ou apague a velha |
| `o lock do projeto e o ambiente da imagem discordam` | um pacote compartilhado noutra versão | os passos 4 e 5 |
| `... não é nome==versão` | o arquivo de ambiente veio do `pip freeze` | gere-o com `uv pip list --format freeze` |
| `não é Python puro` | o projeto tem módulos de extensão | construa o wheel dele na plataforma do alvo |
| `no wheels with a matching platform tag` | uma dependência da pasta não publica wheel para o alvo | outra versão, outro pacote ou outra imagem |
| `No interpreter found for Python <versão>` | o `uv` não acha o Python que o projeto pede e não pode baixá-lo | `UV_PYTHON` com o interpretador do job ([O Python que o `uv` usa](#o-python-que-o-uv-usa)) |

> [!NOTE]
> **Estado**: uma pasta com os mesmos arquivos que o `package-job` grava rodou num job do
> laboratório, mas nenhuma pasta gravada pelo próprio `package-job` rodou num job ainda
> ([as notas](awsds_workflows/lab_notes.html#a-pasta-de-codigo-com-package-job)).

### A pasta do projeto preparada num `.tar.gz`

A pasta do `package-job` vai ao S3 expandida, um objeto por arquivo, e o job baixa o prefixo a
cada execução. Um projeto com a `.venv/` pronta, de muitos arquivos pequenos, pode ir como um
objeto só: o `.tar.gz` da pasta inteira, com o interpretador e as dependências dentro dela, que o
comando do job extrai no volume antes de rodar. O `JOB_PYTHON` da imagem não é chamado
([Uma task de processamento](#uma-task-de-processamento) compara as duas formas). O
`prepare-offline` grava esse arquivo, e o exemplo `demo-devenv-job` o usa
([Os exemplos](#os-exemplos)).

1. **Trave o projeto**, na pasta dele. O `prepare-offline` pede o `uv.lock` e recusa um lock
   desatualizado.

   ```shell
   uv lock
   ```

2. **Grave o `.tar.gz` numa máquina Linux x86_64 com internet**, a plataforma do job:

   ```shell
   awsds-workflows prepare-offline ~/src/meu-projeto /tmp/meu-projeto.tar.gz
   ```

   O CPython é o 3.12; o `--python 3.13` troca a versão, que o `requires-python` do projeto tem de
   admitir. O comando imprime o tamanho do arquivo e o da pasta extraída, a versão do
   interpretador e a raiz:

   ```text
   /tmp/meu-projeto.tar.gz: 34111121 bytes, 100119806 extraídos, com o CPython 3.12.13 em Linux x86_64
   raiz: meu-projeto/
   ```

3. **Copie o objeto para o prefixo da entrada de código**, como
   `shared/exemplos/demo-devenv-job/code/` no exemplo, e nomeie esse prefixo na entrada `code` do
   `config`, como na pasta do `package-job`:

   ```shell
   aws s3 cp /tmp/meu-projeto.tar.gz \
       s3://<bucket do projeto>/<domínio>/<projeto>/shared/meu-job/code/
   ```

   Uma versão nova é copiada por cima, e a execução seguinte já lê a nova.

4. **Escreva o comando do job**: ele dá as duas pastas ao usuário do contêiner, extrai e roda o
   interpretador da pasta, pelo caminho absoluto.

   ```yaml
   ContainerArguments:
     - 'sudo -n chown "$(id -u)" /opt/ml/processing/code /opt/ml/processing/outbox && tar -xzf /opt/ml/processing/code/meu-projeto.tar.gz -C /opt/ml/processing/code && exec /opt/ml/processing/code/meu-projeto/.venv/bin/python -m meu_pacote --input /opt/ml/processing/inbox --output /opt/ml/processing/outbox'
   ```

> [!IMPORTANT]
> **O `VolumeSizeInGB` do job tem de caber o arquivo e a pasta extraída.** O `tar` extrai como o
> usuário do contêiner, que fica dono dos arquivos.

#### O que o `prepare-offline` faz

1. Trabalha numa cópia temporária do projeto, sem a `.venv/`, o `.python/`, o `.git` e os caches,
   e não altera a pasta dele.
2. Na cópia, `uv sync --locked --no-dev --no-editable` recria a `.venv/` com o CPython que o `uv`
   baixa para `.python/`, dentro dela, e com os pacotes copiados do cache do `uv`. O projeto entra
   instalado como pacote, porque uma instalação editável gravaria um `.pth` com o caminho absoluto
   da pasta.
3. Cada link absoluto que o `uv` cria vira relativo ao arquivo real, dentro da pasta.
4. O `.tar.gz` é gravado com os links e os modos, com a raiz do nome da pasta do projeto,
   `meu-projeto/`, e sem o usuário desta máquina.
5. Antes de o arquivo tomar o lugar de um anterior, ele é extraído numa pasta temporária, e o
   `.venv/bin/python` de lá, num ambiente sem o `uv`, lê a versão do pacote do projeto e confirma
   que usa a `.venv/` extraída.

#### Quando o `prepare-offline` recusa

| Ele diz | Significado | O que fazer |
|---|---|---|
| `esta máquina é ..., e a pasta só serve ao job preparada em Linux x86_64` | o `uv` baixa o interpretador e os wheels da máquina em que roda | uma máquina Linux x86_64 |
| `não há uv.lock em ...` | o projeto nunca foi travado | `uv lock` no projeto |
| `uv sync --locked falhou:` | o lock está desatualizado, ou o `uv` não acha nem baixa o CPython pedido | `uv lock`, ou outro `--python` |
| `... nomeie o arquivo com .tar.gz` | o nome do arquivo tem outro sufixo | o sufixo que o `tar -xzf` do job extrai |
| `... aponta para fora da pasta` | um link da `.venv/` ou do `.python/` sai da cópia | leia o link na pasta do projeto |
| `a pasta extraída não roda:` | o projeto não importa fora da pasta de origem | a saída de erro do interpretador, abaixo da recusa |

> [!NOTE]
> **Estado**: o `.tar.gz` foi provado na máquina que empacota, extraído noutra pasta e rodado sem
> `uv` e sem rede; num job, ainda não rodou
> ([as notas](awsds_workflows/lab_notes.html#a-pasta-do-projeto-preparada-num-targz)).

### Uma definição de exemplo

Três tasks: o sensor, o job e a remoção da origem. Os placeholders são preenchidos pelo `render`
([Os valores da definição](#os-valores-da-definicao)). O exemplo `demo-devenv-job` do repositório
é esta definição para um projeto sem chave KMS própria e com a entrada de código no `.tar.gz`
([A pasta do projeto preparada num `.tar.gz`](#a-pasta-do-projeto-preparada-num-targz)), com os
passos ([Os exemplos](#os-exemplos)).

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

> [!IMPORTANT]
> **Quem apaga a origem é o workflow, e não o job**: um contêiner isolado não alcança o S3. Por
> isso a terceira task é um `S3DeleteObjectsOperator` no prefixo da caixa de entrada, depois da
> task de processamento.

> [!WARNING]
> **Um arquivo por vez na caixa de entrada.** A remoção apaga o prefixo inteiro, então um arquivo
> que chega entre o download do job e a remoção é apagado sem ser processado, e só volta pela
> versão anterior que o bucket versionado guarda.

> [!CAUTION]
> **No código do job, imprima contagens e caminhos, nunca dados.** A saída do contêiner vai para
> um grupo de logs da conta inteira, que todo papel de projeto da conta pode ler
> ([As peças](#as-pecas)).

> [!NOTE]
> **Custo e duração**: uma execução levou cerca de 15 minutos e 0,03 USD no laboratório, a maior
> parte com o job baixando a imagem, e a task de processamento ocupa o worker durante o job
> inteiro ([as notas](awsds_workflows/lab_notes.html#uma-definicao-de-exemplo)).

## O código de uma task Python ou Bash

Uma task Python chama uma função sua no worker; uma task Bash roda um comando lá. O código das duas
viaja num `.zip`, o `Code` do workflow, que o `package-task` monta a partir de um projeto `uv`. Os
exemplos `demo-python-operator` e `demo-bash-operator` do repositório são uma task de cada, com os
passos ([Os exemplos](#os-exemplos)).

> [!NOTE]
> **Estado**: uma task Python e uma task Bash rodaram no laboratório, sobre `.zip` montados à mão,
> e no ambiente alvo, sobre `.zip` do `package-task`
> ([as notas](awsds_workflows/lab_notes.html#o-codigo-de-uma-task-python-ou-bash)).

### O que o worker espera

- **Um arquivo ou um `.zip`.** O worker recebe o código como um único `.py`, um único `.sh` ou um
  `.zip` com vários arquivos, de no máximo 250 MB, compactado e descompactado; uma conta guarda até
  75 GB de código.
- **Tudo na raiz do `.zip`**: os seus módulos, os seus pacotes e cada pacote de terceiros. O worker
  extrai o `.zip` em `/usr/local/airflow/dags`, que está no `sys.path`, então um módulo na raiz é
  importado pelo nome.
- **Pacotes de terceiros construídos para o worker**: CPython 3.12 em Linux x86_64. Um pacote
  instalado para a sua máquina ou para a imagem do job não é importado lá.
- **Nenhum pacote que o worker já tem**: o Airflow, o provider da Amazon, o `boto3` e o
  `botocore`, o dag-factory, o PyYAML, o lz4 e a família do AWS Encryption SDK. Numa task Python, o
  pacote pré-instalado vence a cópia do `.zip`. Escreva contra o `boto3` 1.43.1 do worker.
- **Nenhum `__pycache__` ou `.pyc`**: um bytecode de outra plataforma pode não carregar.

> [!CAUTION]
> **Nenhum segredo no `.zip`**: ele é copiado pelo serviço e guardado fora da conta.

### O `.zip` com `package-task`

1. **Prepare o projeto.**
   - Ele tem um `pyproject.toml` e um `uv.lock` em dia: rode `uv lock` no projeto depois de cada
     mudança.
   - O `requires-python` dele admite o Python do worker, 3.12.
   - O código próprio dele é Python puro. Um projeto com módulos de extensão não pode ser
     construído na máquina que empacota para o worker, e o `package-task` o recusa.
   - Para uma task Python, um módulo de entrada, um arquivo pequeno ao lado do pacote e não
     dentro dele, tem a função que a task chama. Uma task Bash não precisa dele
     ([Uma task Bash](#uma-task-bash)).

     ```python
     # tasks.py
     from meu_pacote import pipeline


     def run(bucket: str, inbox: str, outbox: str, **_context):
         return pipeline.process(bucket, inbox, outbox)
     ```

2. **Rode o `package-task`**, com o projeto, o módulo de entrada de uma task Python e o `.zip` a
   gravar:

   ```shell
   awsds-workflows package-task ~/src/meu-projeto ~/src/meu-projeto/tasks.py /tmp/meu-projeto.zip
   ```

   Um `.zip` só de tasks Bash dispensa o módulo de entrada:

   ```shell
   awsds-workflows package-task ~/src/meu-projeto /tmp/meu-projeto.zip
   ```

3. **Leia o que ele imprimiu**: o tamanho do `.zip` e a raiz, que lista o seu pacote, o módulo de
   entrada e os pacotes de terceiros, e nenhum dos do worker (`boto3`, `botocore`, `yaml`, Airflow).
   A última linha é o próximo passo.
4. **Copie o `.zip` para onde o navegador que abre o portal alcança** e envie-o em *Settings →
   Storage → Python/Bash Operator Files* do workflow; depois salve.
5. **Nomeie a função** na task: `python_callable: tasks.run`, que o editor mostra como *File*
   `tasks` e *Function* `run`. Uma task Bash nomeia um comando
   ([Uma task Bash](#uma-task-bash)).
6. **Uma versão nova do código** são os mesmos três movimentos: rodar o `package-task`, enviar e
   salvar. O workflow continua rodando a cópia tirada no último save.

As opções do `package-task`, que vão depois do `.zip`:

| Opção | O padrão | O que ela diz |
|---|---|---|
| `--python X.Y` | `3.12` | a versão do Python do worker |
| `--platform ETIQUETA` | `x86_64-manylinux2014` | a plataforma do worker |
| `--omit PACOTE`, repetida | nenhum | mais um pacote a deixar de fora, além dos que o worker traz |
| `--include ARQUIVO`, repetida | nenhum | mais um arquivo na raiz, como o script ou o binário que uma task Bash chama |

Os padrões são o worker que o guia descreve.

> [!TIP]
> **O serviço pode trocar o interpretador sem aviso.** O log de uma task nomeia o que rodou nos
> caminhos (`.../python3.12/site-packages/...`): quando esse caminho mudar, passe a nova versão.

#### Quando o `package-task` recusa

| Ele diz | Significado | O que fazer |
|---|---|---|
| `The lockfile at uv.lock needs to be updated` | o `pyproject.toml` mudou depois do lock | `uv lock` no projeto |
| `No interpreter found for Python <versão>` | o `uv` não acha o Python que o projeto pede e não pode baixá-lo | `UV_PYTHON` com um interpretador que o projeto aceite ([O Python que o `uv` usa](#o-python-que-o-uv-usa)) |
| `no wheels with a matching platform tag` | uma dependência não publica wheel para o alvo | ela não viaja no `.zip`: outra versão ou outro pacote |
| `não é Python puro` | o projeto tem módulos de extensão | construa o wheel dele na plataforma do alvo |
| `acima do limite de 250000000 bytes do worker` | o `.zip` é grande demais | `--omit` mais pacotes, ou corte dependências |
| `não há arquivo em` | o módulo de entrada ou um `--include` não existe, ou é uma pasta | passe o caminho de um arquivo |
| `já está na raiz do .zip` | um arquivo tem o nome de um pacote da raiz ou de outro arquivo | renomeie o arquivo |
| `unrecognized arguments` | um argumento com `--` ficou entre os caminhos | ponha-o depois do `.zip` |

#### O que o `package-task` faz

Cada passo é uma regra do worker.

1. `uv export --locked --no-dev --no-emit-project --prune <nome> ...` grava o fechamento travado,
   a lista de todas as dependências nas versões do `uv.lock`, como arquivo de requisitos.
   `--locked` recusa um lock desatualizado, e `--prune` tira cada pacote do worker junto com as
   dependências que só ele usa: o `boto3` leva o `s3transfer` e o `jmespath`, e o `urllib3`, de que
   o `requests` também precisa, fica.
2. `uv pip install --target <pasta> --no-deps --only-binary :all: --python-version <X.Y>
   --python-platform <ETIQUETA> --requirements <arquivo>` instala os wheels do alvo para esse
   fechamento, com os hashes do lock. `--only-binary` recusa uma distribuição de código-fonte, que
   seria compilada para a máquina que empacota.
3. `uv build --wheel` constrói o projeto, recusado quando não é Python puro, e a mesma instalação
   põe o pacote dele na raiz.
4. A trava do `uv`, os scripts de `bin/` e o bytecode saem.
5. O módulo de entrada e os arquivos de `--include` são copiados para a raiz com o modo de cada um;
   um nome que já está na raiz é recusado.
6. O `.zip` é gravado pelo Python, com o modo de cada arquivo, o bit de execução incluído; um
   conteúdo acima de 250 MB descompactado é recusado antes de gravar.

> [!NOTE]
> **Estado**: o `.zip` foi medido no laboratório, num projeto com dependências compiladas e com
> pacotes que o worker traz ([as notas](awsds_workflows/lab_notes.html#o-zip-com-package-task)).

> [!TIP]
> **Mantenha o módulo de entrada fino.** O editor mostra o `python_callable` como *File* e
> *Function*, então um módulo na raiz que importa do pacote é o que ele consegue mostrar. Um
> caminho pontuado para dentro do pacote, `pacote.modulo.funcao`, ainda não foi medido.

### O que o `.zip` leva

```
meu-projeto.zip              o CONTEÚDO da pasta de montagem, sem pasta própria
├── tasks.py                 o módulo de entrada: python_callable: tasks.run
├── run.sh                   um arquivo de --include, com o modo dele
├── meu_pacote/              o seu pacote, do wheel dele
├── meu_pacote-0.1.0.dist-info/
├── petl/                    um pacote de terceiros, construído para o worker
├── petl-1.7.29.dist-info/
└── ...
```

### A task Python na definição

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
e também o contexto do Airflow se aceitar `**kwargs`.

### O `.zip` no workflow

**O código é sempre um objeto S3, nunca uma pasta.** O `Code` da API é um `S3Location`: um bucket,
uma chave e uma versão opcional de um único `.py`, `.sh` ou `.zip`. O worker extrai esse objeto,
então um prefixo de arquivos soltos não pode ser nomeado, e um pacote com dependências viaja como
`.zip`. O `Code` é um por workflow: as tasks Python e Bash de um workflow dividem o mesmo `.zip`,
com o módulo de entrada e os arquivos de `--include` juntos.

- **No portal**, *Settings → Storage → Python/Bash Operator Files* envia arquivos, e o *operator
  files S3 location* ao lado é onde eles são guardados (`dev/operatorFiles/` por padrão), e não uma
  origem a ler. O guia diz: um arquivo é guardado como está, vários são compactados num `.zip`, só
  `.py`, `.sh` e `.zip` são aceitos, e o `.zip` fica abaixo de 250 MB.
- **Pela API** (`create-workflow --code`, ou o `awscc` do Terraform a partir da 1.99.0), o objeto
  pode ser qualquer um que quem salva consiga ler, como um `.zip` no `shared/` do projeto. O serviço
  o lê na hora do save, na sessão de quem salva (ainda não medido).

> [!IMPORTANT]
> **Uma versão nova do código pede um envio e um save.** O workflow roda a cópia que o serviço
> tirou no último save, da versão S3 que o `Code` fixa, então trocar o objeto no S3 por fora do
> portal não muda o que roda. Cada save tira uma cópia nova, mesmo um que só muda a descrição do
> workflow.

> [!WARNING]
> **A receita de dependências do guia do portal omite as opções de plataforma**
> (`pip install --target ./package sua-dependencia`): rodada noutra plataforma, ela instala os
> wheels daquela plataforma para todo pacote compilado. Use o `package-task`, ou a receita à mão
> abaixo.

> [!NOTE]
> **Estado**: o envio pelo portal foi medido no laboratório; o `Code` pela API, ainda não
> ([as notas](awsds_workflows/lab_notes.html#o-zip-no-workflow)).

### À mão, sem o pacote

Para um projeto que o `uv` não gerencia, os mesmos passos no shell, a partir da pasta do projeto.

1. **Monte a pasta** com o módulo de entrada e o seu pacote:

   ```shell
   rm -rf build && mkdir build
   cp tasks.py build/
   cp -R src/meu_pacote build/
   ```

2. **Instale as dependências para o worker**, com o `requirements.txt` sem cada pacote que o worker
   já traz:

   ```shell
   uv pip install --target build --python-platform x86_64-manylinux2014 --python-version 3.12 \
       --only-binary :all: --requirements requirements.txt
   ```

3. **Tire a trava do `uv` e o bytecode**:

   ```shell
   rm -f build/.lock
   find build -name __pycache__ -type d -prune -exec rm -rf {} +
   ```

4. **Grave o `.zip` de dentro da pasta**: o `cd build` torna cada caminho relativo à pasta, então o
   `.zip` não tem uma pasta `build/` de topo.

   ```shell
   (cd build && zip -qr ../minha-task.zip . -x '*.pyc')
   ```

5. **Confira a raiz**: a listagem mostra `tasks.py`, e não `build/tasks.py`.

   ```shell
   unzip -l minha-task.zip | head
   ```

## Uma task Bash

Uma task Bash roda um comando do shell no worker: comandos inline, um script, um módulo Python com
`python3 -m` ou um binário. O código que ela chama viaja no `Code` do workflow, que o `package-task`
monta ([O código de uma task Python ou Bash](#o-codigo-de-uma-task-python-ou-bash)). O operador é
o `BashOperator` do Airflow, do pacote `apache-airflow-providers-standard`.

> [!NOTE]
> **Estado**: tasks Bash rodaram no laboratório, inline e sobre um `.zip` montado à mão, e no
> ambiente alvo, sobre um `.zip` do `package-task` com dois scripts de `--include`; um `Code` que é
> um `.py` ou um `.sh` solto e o `env` sem `append_env` ainda não foram medidos
> ([as notas](awsds_workflows/lab_notes.html#uma-task-bash)).

| | Uma task Python | Uma task Bash |
|---|---|---|
| A task nomeia | uma função, `python_callable: <módulo>.<função>` | um comando, `bash_command` |
| Como roda | a função é chamada no processo da task | num subprocesso, `bash -c "<comando>"`, ou `bash` numa cópia do script chamado pelo nome |
| Sucesso | a função volta sem exceção | a saída 0; a saída 99 pula a task, e qualquer outra a falha |
| O código do `.zip` | importado pelo nome, porque `/usr/local/airflow/dags` está no `sys.path` | um módulo, com `python3 -m`, porque o `PYTHONPATH` começa por `/usr/local/airflow/dags`; um script ou um binário, pelo caminho nessa pasta, porque a pasta de trabalho é outra |

### O comando

> [!TIP]
> **`set -euo pipefail`** abre um comando de várias linhas: sem ele, só a saída do último passo
> conta, e um passo que falha no meio passa despercebido.

> [!WARNING]
> **O Jinja renderiza o comando**, inline ou num arquivo `.sh`
> ([Os templates](#os-templates)): um `{#` sem fecho, como o de `${#lista[@]}`, é um erro de
> template, e as chaves duplas só levam as variáveis que o serviço conhece.

> [!WARNING]
> **`env` troca o ambiente inteiro da task**: sem `append_env: true` ao lado, ela perde o `PATH`
> do worker e as variáveis da credencial (lido no código do operador; ainda não medido).

### O ambiente do worker

O que uma task Bash encontra no worker:

- a pasta de trabalho é temporária, `/var/tmp/airflowtmp…`, e não `/usr/local/airflow/dags`, onde
  o `.zip` é extraído. O guia diz que um script roda em `/usr/local/airflow/dags`, mas o script
  chamado pelo nome rodou de uma cópia numa pasta temporária, e o chamado pelo caminho inteiro, na
  pasta de trabalho da task ([O código do `.zip` no comando](#o-codigo-do-zip-no-comando));
- com um `.zip`, o `PYTHONPATH` começa por `/usr/local/airflow/dags`, que aparece duas vezes, e
  segue com os pacotes do worker, `/opt/mwaa-serverless-venv/lib/python3.12/site-packages`;
- os arquivos do `.zip` chegam com o modo que o `.zip` guarda, todos de um usuário do worker (uid e
  gid 997), então um script de `--include` chega executável;
- o `python3` do `PATH` é o do worker, `/opt/mwaa-serverless-venv/bin/python3` 3.12.14, com o
  `boto3` 1.43.1 e os outros pacotes que o worker traz: no ambiente alvo, 164 distribuições, entre
  elas o `redshift-connector` 2.1.8, o `PyAthena` 3.17.1, o `sagemaker_studio` 1.0.27, o
  SQLAlchemy 1.4.54 e o `six` 1.17.0, e nenhum `pyarrow`, `duckdb`, `deltalake`, `pandas` ou
  `numpy`;
- o worker não tem `tar`, `unzip` nem o `aws`, só o `gzip`: um comando que extrai um arquivo ou
  copia do S3 usa o `python3`, com o `zipfile`, o `tarfile` ou o `boto3`;
- o disco da raiz, um `overlay` de 21 GiB, tinha 19 GiB livres e guarda `/usr/local/airflow/dags`
  e o `/var/tmp`, onde gravar 1 GiB levou 3 s; o `/tmp` é um disco à parte, de 9,7 GiB;
- os processos que a task abre recebem a credencial do papel do projeto, sessão
  `AmazonMWAAServerless`, e `AWS_REGION` e `AWS_DEFAULT_REGION` trazem a região;
- as variáveis que o portal injeta no workflow chegam à task: `DataZoneDomainId`,
  `DataZoneDomainRegion`, `DataZoneEndpoint`, `DataZoneEnvironmentId`, `DataZoneProjectId`,
  `DataZoneStage` e `ProjectS3Path`.

> [!NOTE]
> **Estado**: lido no laboratório e no ambiente alvo, em tasks inline e com um `.zip`
> ([as notas](awsds_workflows/lab_notes.html#o-ambiente-do-worker)).

### O `Code` do workflow

O `Code` depende do que a task chama:

| A task chama | O `Code` |
|---|---|
| só comandos inline | nenhum: esvazie *Operator files zip S3 location* em *Settings → Storage* antes de salvar |
| um script `.py` ou `.sh` que usa só os pacotes do worker | o próprio arquivo, sem `.zip`, como o guia descreve; onde o worker o põe ainda não foi medido |
| um projeto uv | `awsds-workflows package-task ~/src/meu-projeto /tmp/meu-projeto.zip`, sem o módulo de entrada |
| um projeto uv e um script ou um binário | o mesmo comando com `--include ~/src/meu-projeto/run.sh`, um por arquivo |
| um binário sem projeto Python | um `.zip` à mão: `zip -j ferramenta.zip minha-ferramenta run.sh` |

### O código do `.zip` no comando

Uma task que roda um pacote do `.zip`:

```yaml
run_project:
  operator: airflow.providers.standard.operators.bash.BashOperator
  dependencies: [wait_for_file]
  bash_command: |
    set -euo pipefail
    cd /usr/local/airflow/dags
    python3 -m meu_pacote --bucket <PROJECTS_BUCKET> --dia {{ ds }}
  retries: 0
```

- **`python3 -m meu_pacote`** pede um `__main__.py` no pacote, e `python3 -m meu_pacote.modulo`
  roda um módulo dele. O `PYTHONPATH` da task começa por `/usr/local/airflow/dags`, então o
  `python3` acha o pacote mesmo sem o `cd` do exemplo.
- **Um script do `.zip`** roda pelo caminho, com `bash` na frente ou, porque o worker mantém o bit
  de execução, sem ele: `bash /usr/local/airflow/dags/run.sh <argumentos>` ou
  `/usr/local/airflow/dags/run.sh <argumentos>`. O `$0` é esse caminho, e a pasta de trabalho é a
  da task.
- **Um `bash_command` que termina em `.sh` ou `.bash`**, como `run.sh`, é para o Airflow o nome de
  um template: o worker passa o arquivo do `.zip` pelo Jinja para uma cópia numa pasta temporária
  e roda `bash` nela. Essa forma não leva argumentos, que fariam o comando deixar de terminar em
  `.sh`; o `$0` dela não aponta para o `.zip`, e as regras do Jinja de [O comando](#o-comando)
  valem para o arquivo.
- **Um binário** é Linux x86_64 e, de preferência, estático, porque a glibc do worker não é
  documentada. O `.zip` guarda o bit de execução, e o worker o mantém ao extrair, então o binário
  roda pelo caminho:

```yaml
run_tool:
  operator: airflow.providers.standard.operators.bash.BashOperator
  bash_command: /usr/local/airflow/dags/minha-ferramenta --dia {{ ds }}
  retries: 0
```

> [!WARNING]
> **Numa task Bash, um pacote do `.zip` vence o do worker com o mesmo nome**, o contrário de uma
> task Python: o `python3` da task importou o `six` 1.16.0 do `.zip` no lugar do 1.17.0 do worker,
> de que o Airflow depende. O `package-task` deixa os pacotes do worker de fora.

> [!NOTE]
> **Estado**: cada forma desta seção rodou no laboratório ou no ambiente alvo
> ([as notas](awsds_workflows/lab_notes.html#o-codigo-do-zip-no-comando)).

## Os valores da definição

Uma definição versionada guarda cada valor da conta como placeholder, `<NOME>`, e o portal precisa
dos valores reais. O `render` preenche os placeholders e imprime o resultado na tela. Uma
definição que o portal salvou faz o caminho inverso com `--placeholders`, e o `compare` a
confronta com a cópia versionada
([A definição que o portal salvou](#a-definicao-que-o-portal-salvou)).

> [!CAUTION]
> **Nada do que o `render` imprime volta para o repositório**: a definição preenchida leva os ids
> da conta. Grave-a fora do clone, como em `/tmp`.

**Os valores vêm de um arquivo JSON, da conta, ou dos dois.** Quando vêm dos dois, os do arquivo
completam e substituem os da conta; `--values-file` se repete, e cada arquivo, na ordem da linha de
comando, completa e substitui o que veio antes dele.

Com um arquivo de valores:

```shell
awsds-workflows render meu-workflow.yaml --values-file valores.json > /tmp/meu-workflow.yaml
```

Com dois arquivos, o segundo sobre o primeiro:

```shell
awsds-workflows render meu-job.yaml --values-file space_values.json \
    --values-file valores-job.json > /tmp/meu-job.yaml
```

Com a leitura da conta e um arquivo por cima dela:

```shell
awsds-workflows render meu-workflow.yaml --profile meu-perfil \
    --subnet-name 'meu-projeto-private-*' --values-file imagem.json > /tmp/meu-workflow.yaml
```

O caminho inverso, numa definição que o portal salvou:

```shell
awsds-workflows render --placeholders salvo.yaml --values-file valores.json
```

Os valores da conta num arquivo, para os comandos acima:

```shell
awsds-workflows values --profile meu-perfil --subnet-name 'meu-projeto-private-*' > valores.json
```

- **A leitura da conta** (`--profile`) usa o `aws` da máquina, num perfil que alcança a conta do
  projeto, e roda só chamadas de leitura: do STS, do IAM, do EC2 e, com `--image-name`, do
  SageMaker. Ela pede `--subnet-name`, o padrão do `Name` das sub-redes privadas do projeto
  (`awsds-sandbox-private-*` no laboratório). Numa conta com mais de um projeto, `--project`
  escolhe o id.
- **Um projeto sem chave KMS própria**, como o do ambiente alvo, não dá `PROJECT_KEY_ID`. Quando o
  papel não tem a etiqueta `KmsKeyId`, ou a tem vazia, a leitura da conta dá os outros valores, e o
  `render` e o `values` avisam na saída de erro, como o script de
  [Os valores de dentro de um espaço](#os-valores-de-dentro-de-um-espaco). Uma definição que nomeia
  `<PROJECT_KEY_ID>` é então recusada pelo `render`.
- **Onde o IAM não responde a partir de um espaço**, como no ambiente alvo, os valores vêm de um
  arquivo. Um script do repositório o escreve de dentro de um espaço do projeto
  ([Os valores de dentro de um espaço](#os-valores-de-dentro-de-um-espaco)), e o `values` de uma
  máquina que alcança a conta também; os valores da imagem entram à mão, num segundo arquivo.
- **Os valores que dependem da imagem**, `JOB_IMAGE_URI` e `JOB_PYTHON`, vêm do arquivo com a imagem
  padrão. Com uma imagem customizada registrada no SageMaker, `--image-name` lê o `JOB_IMAGE_URI`.
- **Um valor pode referenciar outros placeholders**, trocados antes pelos valores deles, um
  nível, e um valor que referencia um placeholder sem valor, ou a si mesmo, é recusado como um
  placeholder sem valor. Com isso um arquivo de modelo monta um valor a partir de outros e marca
  o que está por preencher com o próprio nome, como o `extra_values.json` do job dos exemplos
  ([Os exemplos](#os-exemplos)):

  ```json
  {
    "SMD_REGISTRY_ACCOUNT": "<SMD_REGISTRY_ACCOUNT>",
    "JOB_IMAGE_URI": "<SMD_REGISTRY_ACCOUNT>.dkr.ecr.<REGION>.amazonaws.com/sagemaker-distribution-prod:4.5.2-cpu"
  }
  ```

  Até a conta do registro entrar, o `render` recusa com `nenhum valor para:
  SMD_REGISTRY_ACCOUNT`; depois, o `JOB_IMAGE_URI` sai montado com ela e a `REGION`.
- **Um workflow na notação da CLI de CI/CD**, o `aws-smus-cicd-cli`, guarda os valores do projeto
  como variáveis dela e o que nenhum projeto tem como variáveis de stage, `{env.NOME}`. O `render`
  troca cada uma pela expressão com placeholders antes de preencher, e recusa uma variável fora
  desta tabela; assim o mesmo YAML que a CLI implanta num projeto se importa no portal, preenchido
  com os valores desse projeto, sem a CLI ([Os exemplos](#os-exemplos)).

  | Variável da CLI | O que o `render` lê no lugar dela |
  |---|---|
  | `{proj.id}` | `<PROJECT_ID>` |
  | `{proj.iam_role_arn}` | `arn:aws:iam::<ACCOUNT_ID>:role/<PROJECT_ROLE_NAME>` |
  | `{proj.connection.default.s3_shared.s3Uri}` | `s3://<PROJECTS_BUCKET>/<DOMAIN_ID>/<PROJECT_ID>/shared/` |
  | `{domain.id}` | `<DOMAIN_ID>` |
  | `{domain.region}` | `<REGION>` |
  | `{env.NOME}` | `<NOME>` |

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

### Os valores de dentro de um espaço

O script
[`scripts/space_values.py`](https://github.com/felipenoris/awsds-workflows/blob/main/scripts/space_values.py)
do repositório roda num espaço do projeto e imprime o JSON que o `values` imprime sem
`--image-name`, sem o pacote, sem o `aws` e sem as permissões de IAM e EC2.

1. **Copie o arquivo para o espaço.**
2. **Rode-o num terminal de lá**, com o Python do espaço:

   ```shell
   python space_values.py > space_values.json
   ```

3. **Copie o `space_values.json` para a máquina que empacota.**

O que o script lê e quando ele para:

- **Os valores** vêm do SDK `sagemaker-studio`, que o espaço traz: o `Project()` dá o projeto e o
  domínio, e o ambiente Tooling padrão do projeto dá a conta, a região, o caminho S3 do projeto
  (`s3BucketPath`) e os recursos com que o SDK cria um job (`userRoleArn`, `securityGroup`,
  `privateSubnets` e `kmsKeyArn`). O SDK escolhe o endpoint do DataZone e as credenciais.
- **As sub-redes** saem na ordem do ambiente; o `values` as ordena pela zona, que só o EC2 informa.
- **A chave KMS do projeto**, `kmsKeyArn`, só existe num projeto com chave própria. Sem ela, o JSON
  sai sem `PROJECT_KEY_ID`, com um aviso na saída de erro, e o script termina com 0.
- **Outro valor que o ambiente não dá** termina o script com 1, sem JSON, e a mensagem lista o que
  falta e os recursos que o ambiente tem. Uma recusa do DataZone também termina sem JSON, com o
  rastro do Python na saída de erro.

> [!NOTE]
> **Estado**: o script rodou num espaço do laboratório, com o mesmo JSON que o `values`, e num
> espaço do ambiente alvo, sem a chave KMS
> ([as notas](awsds_workflows/lab_notes.html#os-valores-de-dentro-de-um-espaco)).

### A definição que o portal salvou

O portal grava a definição a cada save, e ela difere da cópia versionada no texto mesmo quando diz
o mesmo: as chaves reordenadas, os textos longos dobrados em várias linhas e as listas em bloco.
Para ver o que uma mudança feita no portal mudou:

1. **Copie a definição salva** para `salvo.yaml`, de *View code* ou do arquivo em `dev/workflows/`
   no bucket do projeto ([As peças](#as-pecas)).
2. **Devolva os placeholders**:

   ```shell
   awsds-workflows render --placeholders salvo.yaml --values-file valores.json > /tmp/salvo.yaml
   ```

3. **Compare** com a cópia versionada:

   ```shell
   awsds-workflows compare meu-workflow.yaml /tmp/salvo.yaml
   ```

   ```
   - meu-job.tasks.run_project.config.ProcessingResources.ClusterConfig.InstanceType: "ml.t3.medium"
   + meu-job.tasks.run_project.config.ProcessingResources.ClusterConfig.InstanceType: "ml.m5.large"
   + meu-job.is_paused_upon_creation: false
   ```

Como o `compare` lê:

- **O `compare` lê as duas definições como YAML** e imprime só as diferenças de conteúdo: os
  comentários, o layout do editor inclusive, a ordem das chaves, as aspas e a forma dos textos e
  das listas não contam. Os valores se comparam com o tipo, então `0` e `"0"` diferem, e as listas
  posição a posição.
- **Cada diferença** sai com o caminho das chaves e o valor em JSON: `-` para o que só a primeira
  definição tem e `+` para o que só a segunda tem; um valor que mudou dá as duas linhas. O comando
  termina com 0 com ou sem diferenças, e com 1 quando um arquivo falta, não é YAML ou não é um
  mapeamento.
- **`is_paused_upon_creation: false`** aparece em toda comparação com uma definição salva: o portal
  o acrescenta a cada save, e o serviço o ignora, com o aviso
  `ignored attributes: is_paused_upon_creation` na resposta de cada `update-workflow`.
- **Uma descrição escrita no portal** entra como a chave `description` do workflow.
- **Um workflow na notação da CLI de CI/CD** se compara com a definição que a CLI implantou e o
  portal guarda: o `compare` troca as variáveis da CLI dos dois lados pela expressão com
  placeholders, como o `render` ([Os valores da definição](#os-valores-da-definicao)), e
  `{{ params.NOME }}`, a forma em que a CLI grava uma variável de stage, por `<NOME>`.

> [!IMPORTANT]
> **Uma mudança que deve ficar entra à mão na cópia versionada**, com os placeholders no lugar dos
> valores da conta.

> [!NOTE]
> **Estado**: o `compare` de definições salvas no laboratório contra os arquivos importados
> imprimiu só o `is_paused_upon_creation` e as mudanças feitas de propósito
> ([as notas](awsds_workflows/lab_notes.html#a-definicao-que-o-portal-salvou)).

## Como ler uma execução

As perguntas que uma execução deixa, e onde está a resposta de cada uma.

| Pergunta | Leitura |
|---|---|
| Como terminou cada task, e quanto tempo ocupou o worker? | `aws mwaa-serverless list-task-instances --workflow-arn <arn> --run-id <id>`; leia o `DurationInSeconds` de uma task, nunca o da execução |
| Por que uma task falhou? | o stream `workflow_id=<workflow>/run_id=<id>/task_id=<task>/attempt=<n>.log` no grupo de logs do workflow |
| Por que o worker parou em `Execution environment preparation failed due to an internal server error`, antes da primeira task? | uma trilha do CloudTrail com eventos de atividade de rede do S3: o `VpceAccessDenied` do `GetObject` da cópia do código nomeia o bucket que o endpoint de gateway recusou ([A rede](#a-rede)) |
| O que o contêiner do job imprimiu, e por que ele falhou? | o stream do job em `/aws/sagemaker/ProcessingJobs`, e o `FailureReason` de `aws sagemaker describe-processing-job` |
| Por qual porta veio uma chamada, e como quem? | o `vpcEndpointId` e o `userIdentity` do `CreateProcessingJob` no CloudTrail |
| O resultado chegou, e com qual chave? | `aws s3api head-object` no resultado |

> [!TIP]
> **O aviso de falha do editor não nomeia a causa**: "Workflow execution failed, please check the
> task execution logs for more details". O log da task nomeia, e numa task de processamento o
> `FailureReason` do job e o stream do contêiner também.

**Uma falha antes da primeira task** ("User template error: ...") é um template que o serviço não
conseguiu renderizar ao criar a execução ([Os templates](#os-templates)).

**O tipo de uma execução** é lido execução por execução: `list-workflow-runs` devolve `RunType`
nulo. Uma task que falhou roda de novo uma vez com o `retries` padrão: leia a duração da task, e
não a da execução.

**O estado da execução atrasa o das tasks**: o `RunState` do `get-workflow-run` pode ler `QUEUED`
depois de o sensor terminar e com o job já sendo criado. Leia o progresso nas tasks, com o
`list-task-instances` ([as notas](awsds_workflows/lab_notes.html#como-ler-uma-execucao)).

## Limpeza

- **Apague um workflow** na página *Workflows*. O grupo de logs dele fica, sem retenção.
- **Esvazie as caixas de entrada** para a próxima execução começar de um estado conhecido; as
  caixas de saída são os resultados.
- **Um job de processamento não pode ser apagado**: ele continua listado.
- **Os `.zip` de código** em `dev/operatorFiles/` ficam com todas as versões, porque o bucket é
  versionado.
- **As pastas de código** em `shared/jobs/` ficam, uma por versão; apague uma só quando nenhuma
  definição a nomeia.
