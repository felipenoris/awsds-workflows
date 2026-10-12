O `awsds-workflows` prepara o que um workflow de um projeto do SageMaker Unified Studio executa.
Um workflow é uma sequência de tasks que o Amazon MWAA Serverless, o Apache Airflow gerenciado da
AWS, roda por você: esperar um arquivo chegar no S3, rodar um programa Python ou um comando Bash,
iniciar um job de processamento do SageMaker. O portal do SageMaker Unified Studio tem o editor
desses workflows, mas não monta o código que as tasks rodam nem preenche os valores da sua conta na
definição. O pacote faz essas duas coisas, e compara definições, com estas ferramentas:

- `package-task` grava o `.zip` com o código de uma task Python ou Bash e as dependências dele;
- `package-job` grava a pasta de código de um job de processamento, só com o que a imagem do job
  não tem;
- `render` preenche o arquivo de definição do workflow com os valores do projeto, e `values` lê
  esses valores da conta;
- `compare` mostra o que difere no conteúdo de duas definições, como a versionada e a que o
  portal salvou.

As ferramentas rodam numa máquina Linux com internet, onde o `uv` alcança o PyPI. O que elas gravam
é copiado para o ambiente do SageMaker, que não tem internet: lá nada é instalado, e o código chega
pronto, com as dependências ao lado.

Esta página ensina o procedimento do começo ao fim, para quem vai montar o primeiro workflow. Cada
passo foi medido em outubro de 2026 no laboratório, uma conta de testes em `us-west-2` com uma
imagem customizada, `awsds-sandbox-dev-env`, e cada ponto ainda não medido está dito. A referência
de cada módulo do pacote está no menu: `awsds_workflows.package_task`,
`awsds_workflows.package_job`, `awsds_workflows.render`, `awsds_workflows.compare`,
`awsds_workflows.errors` e
`awsds_workflows.cli`.

| Seção | Para quem | O que traz |
|---|---|---|
| [Os conceitos](#os-conceitos) | todos | os termos desta página e a ordem em que um primeiro workflow os usa |
| [Instalação](#instalacao) | todos | o pacote na máquina que empacota, e o Python que o `uv` usa nela |
| [As peças](#as-pecas) | todos | onde ficam o arquivo de definição do workflow, o código, os logs e as execuções |
| [A imagem do job](#a-imagem-do-job) | todos | a imagem padrão do SageMaker ou uma customizada, e o que muda |
| [A permissão do projeto](#a-permissao-do-projeto) | infraestrutura | a política que o papel do projeto precisa antes do primeiro job |
| [A rede](#a-rede) | infraestrutura | os endpoints que o worker e o job usam |
| [Regras de autoria](#regras-de-autoria) | cientista de dados | o formato do YAML, o editor, a importação, os templates, o sensor |
| [Uma task de processamento](#uma-task-de-processamento) | cientista de dados | um job na imagem escolhida, e a pasta de código com `package-job` |
| [O código de uma task Python ou Bash](#o-codigo-de-uma-task-python-ou-bash) | cientista de dados | o `.zip` com `package-task`, e uma task Python |
| [Uma task Bash](#uma-task-bash) | cientista de dados | o `BashOperator`: o comando, o ambiente do worker e o código que ele chama |
| [Os valores da definição](#os-valores-da-definicao) | todos | os placeholders, o `render`, os valores lidos de dentro de um espaço e o `compare` com a definição que o portal salvou |
| [Como ler uma execução](#como-ler-uma-execucao) | todos | uma leitura por pergunta |
| [Limpeza](#limpeza) | todos | o que fica depois de um workflow |

## Os conceitos

Os termos desta página, na ordem em que um workflow os usa.

**O workflow e a sua definição.** Na página *Workflows* de um projeto, um workflow é descrito por
um arquivo YAML, o arquivo de definição do workflow: ele lista as tasks, os parâmetros de cada uma e
a ordem entre elas. Quem o executa é o MWAA Serverless: ele prepara um worker para cada task, roda
a task nele e grava os logs. A definição fica no bucket do projeto, e o portal a reescreve a cada
save ([As peças](#as-pecas)).

**As tasks e os operadores.** Cada task da definição é um operador do Airflow, uma classe que sabe
fazer uma coisa, com os parâmetros dela. Três tipos de task entram nos workflows desta página:

| A task | O operador | Onde roda | O código dela |
|---|---|---|---|
| um sensor, que espera um arquivo no S3 | `S3KeySensor` | no worker | nenhum: só os parâmetros |
| uma task Python ou Bash | `PythonOperator`, `BashOperator` | no worker | um `.zip` com o seu código e as dependências, montado pelo `package-task` |
| uma task de processamento | `SageMakerProcessingOperator` | num job de processamento do SageMaker, na imagem que a task nomeia | uma pasta de código no S3, montada pelo `package-job` |

**O worker** é a máquina pequena que o MWAA Serverless prepara para cada task, com Python 3.12, o
Airflow e sem internet. Uma task Python ou Bash roda nele. Uma task de processamento roda nele só
o operador: o trabalho de verdade acontece num job de processamento do SageMaker, um contêiner
que a AWS inicia numa instância à parte, com a imagem que a task escolhe, e que no laboratório
roda isolado da rede.

**Por que empacotar.** Nem o worker nem o job alcançam o PyPI, então um `pip install` não existe lá.
O código e cada dependência chegam prontos, construídos para o interpretador e a plataforma de quem
vai rodá-los: o `.zip` de uma task para o worker, a pasta de um job para a imagem do job. As duas
ferramentas partem de um projeto gerenciado pelo `uv`, com `pyproject.toml` e `uv.lock`.

**A definição versionada e os valores.** A definição guardada no git escreve cada valor da conta,
como o id do projeto e o bucket, como um placeholder: `<PROJECT_ID>`, `<PROJECTS_BUCKET>`. O
`render` troca os placeholders pelos valores do projeto antes da importação no portal, o caminho
inverso devolve os placeholders a uma definição que o portal salvou, e o `compare` mostra o que
ela mudou.

**O laboratório e o ambiente alvo.** O laboratório é a conta de testes em que cada passo desta
página foi medido, nas datas que a página cita. O ambiente alvo é o SageMaker Unified Studio em que
os workflows vão rodar: lá a primeira task Python rodou em 2026-10-12, e a página diz o que ainda
não foi medido.

**O primeiro workflow**, na ordem das seções: instale o pacote; leia onde cada peça fica e qual é a
imagem do job; peça à infraestrutura a permissão e a rede; escreva a definição pelas regras de
autoria; monte o código da task de processamento ou o `.zip` da task Python ou Bash; preencha os
valores e importe a definição; leia a execução; e, depois de uma mudança feita no portal, compare
a definição salva com a versionada.

## Instalação

Instale o pacote na máquina que empacota: um Linux com internet e com o
[`uv`](https://docs.astral.sh/uv/) no `PATH`. O que ela grava é copiado depois para o ambiente do
SageMaker.

```shell
uv tool install git+https://github.com/felipenoris/awsds-workflows   # o comando awsds-workflows
uv add git+https://github.com/felipenoris/awsds-workflows            # ou como dependência
```

Instale sempre pelo endereço do repositório ou por uma pasta local, nunca pelo nome: o nome
`awsds-workflows` está livre no PyPI (lido em 2026-10-11), e um pacote publicado lá com esse nome
por outra pessoa seria instalado no lugar deste.

O comando instalado pelo endereço, sem um commit fixo, acompanha a `main` com:

```shell
uv tool upgrade awsds-workflows
```

Medido em 2026-10-12 com o `uv` 0.12.13, numa instalação feita de um repositório git local que
depois ganhou um commit na `main`: o `uv tool upgrade` instalou o commit novo. O commit instalado é
o `commit_id` do arquivo `direct_url.json`, dentro de `$(uv tool dir)/awsds-workflows/`; o
`uv tool list` mostra o endereço, e não o commit.

O pacote pede o Python 3.12 ou mais novo, que o `uv` instala, e é testado no 3.12, no 3.13 e no
3.14. Ele chama o `uv` como programa, e as dependências dele são o `packaging`, que avalia os
marcadores do arquivo de ambiente da imagem ([A imagem do job](#a-imagem-do-job)), e o PyYAML,
que lê as definições que o `compare` compara.

### O Python que o `uv` usa

O `package-task` e o `package-job` rodam o `uv` na pasta do projeto, e o `uv` escolhe um
interpretador que o projeto aceite: o que o `.python-version` do projeto nomeia ou, sem esse
arquivo, um que satisfaça o `requires-python`. Quando não acha nenhum, o `uv` baixa um, a menos que
os downloads de Python estejam desligados.

Num espaço do laboratório, a imagem desliga esses downloads (`UV_PYTHON_DOWNLOADS=never`), e o
`uv` acha só o Python da distribuição, `/opt/conda/bin/python` 3.12. O interpretador do job,
`/opt/awsds/venv/bin/python` 3.13, fica fora dos caminhos em que o `uv` procura, e um projeto que
pede o 3.13 é recusado com `No interpreter found for Python 3.13`. A saída é a variável `UV_PYTHON`
do próprio `uv`, que nomeia o interpretador; o pacote a repassa a cada chamada do `uv`:

```shell
UV_PYTHON=/opt/awsds/venv/bin/python awsds-workflows package-job ~/src/meu-projeto \
    /tmp/meu-projeto-0.2.0 --environment ambiente.txt --python 3.13
```

Medido num espaço simulado em 2026-10-11, com o `uv` 0.12.17 da imagem do laboratório, os
downloads desligados, só um CPython 3.12 no `PATH` e um 3.13 fora dele: o `uv tool install`
instalou o pacote no 3.12, sem ler o `.python-version` da pasta em que rodou; sem o `UV_PYTHON`, o
`package-job` e o `package-task` pararam no `uv export --locked` de um projeto que pedia o 3.13;
com ele, gravaram a pasta e o `.zip`. Com os downloads ligados, o `uv` baixou o CPython 3.13.15, e
o `package-job` gravou os mesmos arquivos, diferentes só em metadados da instalação (2026-10-12).
Num espaço de verdade, o pacote ainda não rodou.

## As peças

Onde cada peça de um workflow fica, para você saber onde procurar o que enviou e o que o serviço
gravou.

| O quê | Onde | Nota |
|---|---|---|
| o arquivo de definição do workflow | `s3://<bucket do projeto>/<domínio>/<projeto>/dev/workflows/<nome>.yaml` | gravado pelo portal a cada save; *View code* o mostra |
| o `.zip` de uma task Python ou Bash | `.../dev/operatorFiles/<arquivo>` | enviado em *Settings → Storage*; um `.zip` é guardado como foi enviado, e o workflow fixa a versão S3 dele |
| a cópia do código que o serviço guarda | `mwaa-serverless-code-files-<conta da AWS>-<região>-prod`, um bucket do serviço (lido no CloudTrail em 2026-10-11) | tirada a cada save, fora do bucket do projeto, e cifrada com a chave do projeto; o worker a busca pelo endpoint de gateway do S3 ([A rede](#a-rede)) |
| os logs das tasks | `/aws/mwaa-serverless/<domínio>-<projeto>/<workflow>`, um stream por tentativa de task | por projeto, sem retenção; o grupo existe desde o primeiro save, antes de qualquer execução, e sobrevive ao workflow |
| a saída do contêiner de um job | `/aws/sagemaker/ProcessingJobs`, stream `<job>/algo-1-<n>` | da conta inteira: todo papel de projeto da conta pode lê-la |
| a identidade | o papel do projeto, `datazone_usr_role_<projeto>_<ambiente>`, o papel do IAM com que o projeto age; sessão `AmazonMWAAServerless` no worker e `SageMaker` dentro de um job | |
| a rede | as sub-redes privadas e o grupo de segurança do projeto, injetados pelo portal | sem rota padrão: a AWS é alcançada pelos endpoints de VPC |
| a chave | a chave KMS do projeto | cifra o workflow, o volume e as saídas do job, e o bucket |

**O worker**, segundo o guia da AWS do MWAA Serverless (lido em 2026-10-11), tem 1 vCPU e 3 GiB,
Python 3.12, Airflow 3.0.6, o provider da Amazon 9.32.0 e o `boto3` 1.43.1, e não tem internet nem
proxy. Uma task ocupa o worker durante toda a sua duração, a espera de um sensor incluída, e custa
0,088 USD por task-hora, com mínimo de um minuto.

Cada task tem o seu worker: duas tasks da mesma execução rodaram em sub-redes diferentes, e o log
de cada task abre com `Preparing the execution environment.` (medido no laboratório em
2026-10-11). Por isso um arquivo que uma task grava no disco não chega à seguinte (não medido):
passe os dados de uma task a outra pelo S3.

## A imagem do job

Um job de processamento roda dentro de uma imagem de contêiner, e a definição da task diz qual. O
pacote não supõe nenhuma: a imagem decide o interpretador que o job chama, a versão do Python e os
pacotes já instalados, e cada um desses fatos entra no `package-job` e na definição. As tasks
Python e Bash não dependem da imagem, porque rodam no worker.

Duas imagens servem: a imagem padrão do SageMaker, a SageMaker Distribution que a AWS publica, ou
uma imagem customizada, registrada no SageMaker pela infraestrutura. A tabela diz de onde vem cada
valor em cada caso.

| | A imagem padrão do SageMaker | Uma imagem customizada |
|---|---|---|
| exemplo | a SageMaker Distribution 4.15, a imagem inicial do ambiente alvo | a imagem do laboratório, `awsds-sandbox-dev-env` |
| `JOB_IMAGE_URI`, a imagem na definição | o URI da distribuição na região do projeto, escrito no arquivo de valores | lido da imagem registrada no SageMaker (`values --image-name`) ou escrito no arquivo de valores |
| `JOB_PYTHON`, o interpretador que o job chama | `/opt/conda/bin/python` | o do ambiente da imagem; na do laboratório, `/opt/awsds/venv/bin/python` |
| `--python`, a versão desse interpretador | lida com `/opt/conda/bin/python --version` num espaço que roda a imagem | na do laboratório, 3.13 |
| o arquivo de ambiente, a lista do que a imagem já tem | `uv pip list --format freeze --python /opt/conda/bin/python` num espaço que roda a imagem | o mesmo comando com o interpretador da imagem, ou o `uv export` do projeto que constrói a imagem |

**O arquivo de ambiente** diz ao `package-job` o que a imagem já tem, para a pasta de código levar
só o resto. Gere-o num espaço do projeto que roda a imagem do job, o ambiente interativo do portal
(JupyterLab ou Code Editor), sem internet, e copie-o para a máquina que empacota. Ele vale para
aquela versão da imagem: uma imagem nova pede um arquivo novo e uma pasta de código nova. O
`uv pip list --format freeze` escreve só linhas `nome==versão`; o `pip freeze` escreve
`nome @ file:///...` para um pacote instalado pelo conda, e o `package-job` recusa essa linha: se a
ignorasse, o pacote pareceria ausente da imagem e entraria na pasta.

Uma imagem construída de um projeto `uv`, como a do laboratório, dá o arquivo sem um espaço: o
lock do projeto que a constrói, exportado na pasta dele com
`uv export --frozen --no-dev --no-emit-project --no-hashes`. Com a imagem do laboratório, esse
arquivo, com o cabeçalho e as anotações `# via` que o `uv` escreve, foi aceito pelo `package-job`
e pelo `job-constraints`, que leu 452 versões para o CPython 3.13 em `x86_64-manylinux_2_28`
(medido em 2026-10-12).

**Ainda não medido na SageMaker Distribution 4.15**: o URI da imagem para um job no ambiente alvo,
a versão do Python de `/opt/conda/bin/python` e o usuário do contêiner. A imagem do laboratório
roda como `sagemaker-user` (uid 1000), e o `sudo` dela funciona dentro de um job (medido em
2026-10-11); a distribuição, de que a imagem do laboratório deriva, deve ter o mesmo usuário, e o
primeiro job no ambiente alvo é a medida.

## A permissão do projeto

Tudo num workflow roda como o papel do projeto, e a política dele vem do blueprint, o conjunto de
regras com que o SageMaker Unified Studio cria o ambiente do projeto. Essa política não basta para
o `SageMakerProcessingOperator`, por dois motivos medidos no laboratório em 2026-10-10:

- **O operador descreve o nome do job antes de criá-lo**, e o blueprint deixa o papel descrever só
  um job com a etiqueta do próprio projeto. Um nome ainda livre não tem etiqueta, então a primeira
  execução falha com `AccessDeniedException` em `DescribeProcessingJob`, antes de existir um job.
- **Criar um job com etiquetas também é autorizado como `sagemaker:AddTags`**, e o blueprint tira
  toda chave `AmazonDataZone*` do `AddTags` enquanto exige que o job leve a etiqueta
  `AmazonDataZoneProject`. A segunda execução falha com `AccessDeniedException` em
  `sagemaker:AddTags`.

No ambiente alvo, a primeira execução, em 2026-10-12, falhou do mesmo jeito em
`DescribeProcessingJob`, antes de existir um job.

A política abaixo, anexada a cada papel de projeto que roda jobs, cobre os dois casos. O papel nasce
com o ambiente Tooling do projeto e se chama `datazone_usr_role_<projeto>_<ambiente>`; quem
mantém a conta com Terraform anexa a política a esse nome depois que o projeto existe. Ela permite
o `DescribeProcessingJob` de um job sem etiqueta de projeto e o `AddTags` só da etiqueta do próprio
projeto, num job sem etiqueta ou com a do chamador; os jobs de outro projeto ficam fora de alcance.
`<REGION>` e `<ACCOUNT_ID>` são a região e a conta do projeto.

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
responde. O que o laboratório leu no CloudTrail, nos logs de fluxo e no log do firewall de DNS em
2026-10-11:

- **O operador de processamento** chama `CreateProcessingJob` e `DescribeProcessingJob` pelo
  endpoint de interface `sagemaker.api`, como o papel do projeto.
- **O worker grava o log** por `CreateLogStream`, pelo endpoint `logs`.
- **Uma task que chama o STS** passa pelo endpoint de interface `sts`.
- **O S3** é alcançado pelo endpoint de gateway. O sensor lista o prefixo por ele, e o worker de um
  workflow com código busca por ele a cópia que o serviço guarda em
  `mwaa-serverless-code-files-<conta da AWS>-<região>-prod`, num `GetObject` do principal de
  serviço `airflow-serverless.amazonaws.com`. Uma política do endpoint que não admite esse bucket
  faz o worker falhar antes da primeira task, com `Execution environment preparation failed due to
  an internal server error`, e só um evento de atividade de rede do CloudTrail, com `errorCode`
  `VpceAccessDenied`, nomeia a recusa. Com o bucket admitido, o mesmo workflow rodou.
- **A internet não responde**: uma task que tentou o PyPI falhou em cerca de 2 s, na resolução do
  nome, que o firewall de DNS da VPC do laboratório recusa. O Python do worker lê essa recusa como
  `[Errno 16] Device or resource busy`, e não como um nome que não existe.
- **A imagem do job é baixada pela plataforma**, fora da rede do projeto, então um job isolado não
  precisa de endpoint do ECR.

No ambiente alvo, as leituras feitas a partir de um espaço (2026-09-21 e 2026-09-23) encontraram o
endpoint de gateway do S3 e endpoints de interface para STS, Redshift, Glue, Athena, Secrets
Manager e DataZone; os nomes do KMS e do IAM resolveram para endereços públicos e não responderam.
O nome do SageMaker que elas testaram, `sagemaker.sa-east-1.amazonaws.com`, também não respondeu,
mas a API atende em `api.sagemaker.sa-east-1.amazonaws.com`. Em 2026-10-12, de um espaço do
projeto, o SageMaker respondeu a uma listagem de jobs e o SSM a uma leitura de parâmetro. No mesmo
dia, na primeira execução de um workflow lá, o worker listou a pasta de entrada no S3, chamou a API
do SageMaker, que recusou o pedido por permissão, e gravou o log da task. Numa task Python, o
worker recebeu a cópia do código, chamou o STS e leu, gravou e apagou objetos na pasta do projeto.
O caminho do job, do download da imagem à gravação da saída, ainda não foi medido no ambiente alvo.

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

**Crie vazio, depois importe.** Na página *Workflows*, crie um workflow e use *Actions → Import
definition file* com a definição preenchida pelo `render`. Os formulários do editor não expressam
tudo o que uma definição expressa, e a importação guarda cada campo: a definição salva difere da
importada só por `is_paused_upon_creation: false`, pela ordem das chaves e por textos longos
dobrados.

**Uma importação não substitui um workflow salvo.** Importado no editor de um workflow já salvo, o
arquivo vira um workflow novo com o mesmo nome, e o save é recusado com `ConflictException: Workflow
with given name already exists` (medido no laboratório em 2026-10-11). Apague antes o workflow
antigo (lista *Workflows*, *Delete workflow*, e a palavra "confirm") e então salve: o CloudTrail
registra `DeleteWorkflow` e depois `CreateWorkflow`, o sufixo do ARN muda, e o histórico de
execuções e de versões recomeça. O grupo de logs leva o nome do workflow e guarda os logs de cada
execução.

**Erros do save e a saída de cada um**:

| O portal diz | O que aconteceu | Saída |
|---|---|---|
| `ValidationException: Code not found in specified S3 location` | o editor preenche o campo *Operator files zip S3 location* num workflow novo, vazio ou importado, mesmo sem task Python ou Bash, e o save o enviou sem nenhum arquivo nesse local | envie o arquivo da task em *Settings → Storage*; num workflow sem código (só comandos Bash inline, ou nenhuma task Python ou Bash), esvazie o campo antes de salvar, e o save não manda o `Code` (2026-10-11) |
| `ContainerArguments: Container argument is required` | o editor exige argumentos numa task de processamento, embora a API não os exija | separe o comando em programa (`ContainerEntrypoint`) e argumentos (`ContainerArguments`) |
| dois workflows com o mesmo nome | dois saves feitos a 2 s um do outro passaram juntos pela conferência do nome | apague um; fora dessa corrida, o nome é conferido |

**A primeira linha do YAML é o layout do editor**, um comentário JSON como
`# {"wait_for_file":{"x":120,"y":200},...}`, com a posição de cada task no desenho. Mantenha-a, e
não ponha outro comentário num arquivo que vai ser importado.

**Os templates são renderizados quando a execução é criada.** Um template é um trecho entre
`{{ }}` que o serviço troca por um valor ao criar a execução, com a sintaxe Jinja do Airflow; o
serviço conhece só `macros`, `ti`/`task_instance`, `params`, `ds`, `ds_nodash`, `ts` e `ts_nodash`:

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

**O sensor de arquivo.** Um sensor é uma task que espera uma condição, conferindo-a de tempos em
tempos. O `S3KeySensor` com `wildcard_match: true`, `poke_interval: 30`, `timeout: 600` e
`soft_fail: true` espera até 10 minutos por um arquivo que case com o padrão, conferindo a cada 30
s, e termina a execução sem erro se nada chegar:

- o `mkdir` de um espaço deixa um marcador de pasta de zero bytes, `inbox/`, e `inbox/*` casa com
  ele. Observe `inbox/?*`, que pede um caractere depois da barra, a menos que uma task seguinte
  apague o prefixo inteiro;
- `soft_fail` termina com `SUCCESS` uma execução de caixa de entrada vazia, depois do timeout. A
  API lê então o estado do sensor como `NONE`, e não `SKIPPED`, e não lista instância para as tasks
  seguintes; só o log da task diz `Skipping task.` A espera cobra os seus 10 minutos (cerca de
  0,015 USD).

## Uma task de processamento

Uma task de processamento inicia um job de processamento do SageMaker: um contêiner com a imagem
escolhida, numa instância à parte, que recebe entradas do S3, roda um comando e devolve as saídas
ao S3. O `config` da task é a chamada `CreateProcessingJob` inteira, em YAML.

O formulário *SageMaker Processing* do portal não tem campo para `NetworkConfig`, para as chaves
KMS nem para as etiquetas, e um job sem eles pode ser recusado pelas regras do ambiente. Escreva
o `config` inteiro da task no YAML e importe-o
([Uma definição de exemplo](#uma-definicao-de-exemplo)).

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
ao S3 depois que ele termina, como o papel do projeto. O código é mais uma entrada: a pasta que o
`package-job` grava, copiada para o S3 do projeto.

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
  módulo de extensão (um pacote com código compilado) não é importado de um `.zip` no `sys.path`.
- **A precedência é a inversa da do worker.** O `PYTHONPATH` vem antes do `site-packages` da
  imagem, então um pacote presente nos dois esconderia a cópia da imagem. A pasta leva só o que a
  imagem não tem, e as versões do projeto têm de ser iguais às da imagem em tudo o que os dois
  compartilham.

1. **Prepare o projeto.**
   - Ele tem um `pyproject.toml` e um `uv.lock` em dia.
   - O `requires-python` dele admite o Python da imagem.
   - O código próprio dele é Python puro, e roda como `python -m meu_pacote` (um `__main__.py`).
2. **Gere o arquivo de ambiente da imagem** num espaço que roda a imagem do job e copie-o para a
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
   a etiqueta dos wheels para Linux x86_64 com glibc 2.28 ou mais nova; `ldd --version` num espaço
   diz a glibc da imagem. A imagem do laboratório tem o `onnxruntime` 1.30.0, que não publica wheel
   anterior a `manylinux_2_28` (medido em 2026-10-11), então `manylinux2014` não a descreve. Num
   espaço, o `uv` pode não achar o Python que o projeto pede
   ([O Python que o `uv` usa](#o-python-que-o-uv-usa)).
4. **Se ele apontar uma discordância**, cole o bloco que ele imprime no `pyproject.toml` do projeto,
   rode `uv lock` e repita o passo 3:

   ```toml
   [tool.uv]
   constraint-dependencies = [
     "boto3==1.43.92",
     ...
   ]
   ```

   O bloco fixa cada pacote que o projeto compartilha com a imagem na versão da imagem, o que também
   põe os testes do projeto nas versões que o job importa. Quando um limite inferior do projeto
   passa de uma versão da imagem, esse lock falha, e a dependência não serve a esta imagem: ela
   pede outra versão, outro pacote ou outra imagem.
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

   Num espaço com o `~/shared/` do projeto, a mesma cópia é
   `mkdir -p ~/shared/jobs && cp -r /tmp/meu-projeto-0.2.0 ~/shared/jobs/`. O `shared/` grava no
   prefixo um marcador de zero bytes por pasta, e um job baixou um prefixo assim sem problema
   (2026-10-11).
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
| `No interpreter found for Python <versão>` | o `uv` não acha o Python que o projeto pede e não pode baixá-lo | `UV_PYTHON` com o interpretador do job ([O Python que o `uv` usa](#o-python-que-o-uv-usa)) |

**Medido em 2026-10-11** com a imagem do laboratório, num projeto descartável que dependia de
`petl`, `requests`, `boto3` e `pyyaml`: o lock novo discordou da imagem em `boto3`, `botocore`,
`charset-normalizer`, `idna` e `urllib3`; com o bloco impresso e um novo `uv lock`, 12 pacotes
vieram da imagem e só o `petl` entrou na pasta, de 1,2 MB.

**Medido num job em 2026-10-11**, com a imagem do laboratório, num projeto que dependia do `petl`
(Python puro), do `msgspec` (um módulo de extensão) e do `pyarrow`, que a imagem tem. O lock novo
discordou da imagem no `pyarrow`, 26.0.0 no lock e 24.0.0 na imagem; com o bloco e um novo
`uv lock`, a pasta levou o projeto, o `petl` 1.7.29 e o `msgspec` 0.22.0, em 176 arquivos e
1.735.841 bytes. O job a recebeu como entrada de código, sem rede, e o contêiner imprimiu de onde
importou cada pacote:

```
python 3.13.15 at /opt/awsds/venv/bin/python
petl 1.7.29 from /opt/ml/processing/code/petl
msgspec 0.22.0 from /opt/ml/processing/code/msgspec, extension _core.cpython-313-x86_64-linux-gnu.so
pyarrow 24.0.0 from /opt/awsds/venv/lib/python3.13/site-packages/pyarrow, extension lib.cpython-313-x86_64-linux-gnu.so
```

O pacote Python puro e o módulo de extensão vieram da pasta, e o `pyarrow` do ambiente da imagem;
as saídas, um JSON e uma tabela Parquet, são byte a byte as da execução local. A pasta foi gravada
num espaço por um script com os mesmos passos do `uv`, e nenhuma pasta do `package-job` rodou num
job ainda. Num espaço simulado, o `package-job` gravou os mesmos 176 arquivos, iguais a menos de
três metadados do projeto: o caminho temporário do wheel, a hora da construção e os hashes dos
dois.

**Quem apaga a origem é o workflow, e não o job**: um contêiner isolado não alcança o S3. Por isso
a terceira task da definição de exemplo é um `S3DeleteObjectsOperator` no prefixo da caixa de
entrada, depois da task de processamento.

**Um arquivo por vez na caixa de entrada.** A remoção apaga o prefixo inteiro, então um arquivo que
chega entre o download do job e a remoção é apagado sem ser processado, e só volta pela versão
anterior que o bucket versionado guarda.

**No código do job, imprima contagens e caminhos, nunca dados.** A saída do contêiner vai para um
grupo de logs da conta inteira, que todo papel de projeto da conta pode ler
([As peças](#as-pecas)).

**O custo e a duração de uma execução** (medido no laboratório em 2026-10-11): cerca de 15 minutos e
0,03 USD. O job passou cerca de 7,5 dos seus 8 minutos baixando a imagem do laboratório, de 6,97 GB,
antes de o contêiner começar, e a task de processamento ocupa o worker durante o job inteiro. No
job com dependências, a task ocupou o worker 791 s para um comando de um segundo: cerca de 3
minutos de provisionamento antes do `ProcessingStartTime`, 7 de download da imagem e 2,5 depois do
`ProcessingEndTime` até o job ler `Completed`, o estado que o operador espera. A pasta com as
dependências não mudou o custo da execução, cerca de 0,03 USD.

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

Uma task Python chama uma função sua no worker; uma task Bash roda um comando lá. O código das duas
viaja num `.zip`, o `Code` do workflow, que o `package-task` monta a partir de um projeto `uv`.

**Estado no laboratório**: funciona desde 2026-10-11. Uma task Python e uma task Bash, cada uma com
um `.zip`, leram a amostra, gravaram o resultado e apagaram a origem. Os dois `.zip` foram montados
pela receita [à mão](#a-mao-sem-o-pacote). Antes, o worker falhava ao preparar o ambiente, antes de
qualquer task: a política do endpoint de gateway do S3 recusava o bucket da cópia do código
([A rede](#a-rede)).

**Estado no ambiente alvo**: uma task Python funciona desde 2026-10-12, com um `.zip` do
`package-task` de 261.205 bytes, o projeto do laboratório com o `petl` 1.7.28. O worker, um
CPython 3.12.14, importou o `petl` do `.zip`, em `/usr/local/airflow/dags`, e o PyYAML 6.0.2 dos
pacotes dele, e o resultado saiu igual ao do laboratório, com o mesmo sha256. Uma task Bash ainda
não rodou lá.

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
  pacote pré-instalado vence a cópia do `.zip`: o PyYAML 6.0.2 do worker foi importado no lugar do
  6.0.1 do `.zip` (2026-10-11). Escreva contra o `boto3` 1.43.1 do worker.
- **Nenhum `__pycache__` ou `.pyc`**: um bytecode de outra plataforma pode não carregar.
- **Nenhum segredo**: o `.zip` é copiado pelo serviço e guardado fora da conta.

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
   awsds-workflows package-task ~/src/meu-projeto /tmp/meu-projeto.zip   # só tasks Bash
   ```

   `--python X.Y` e `--platform ETIQUETA` mudam o alvo; os padrões, 3.12 e `x86_64-manylinux2014`,
   são o worker que o guia descreve. O serviço pode trocar o interpretador sem aviso, e o log de uma
   task nomeia o que rodou nos caminhos (`.../python3.12/site-packages/...`): quando esse caminho
   mudar, passe a nova versão. `--omit PACOTE`, repetido, deixa mais pacotes de fora, e
   `--include ARQUIVO`, repetido, põe na raiz um script ou um binário que uma task Bash chama. Os
   argumentos com `--` vão depois do `.zip`.
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

**Quando o `package-task` recusa:**

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

**O que ele faz**, cada passo uma regra do worker:

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
  `.py`, `.sh` e `.zip` são aceitos, e o `.zip` fica abaixo de 250 MB. Medido no laboratório: um
  `.zip` guardado como foi enviado, com a versão S3 fixada e o sha256 igual ao do `.zip` construído.
- **Pela API** (`create-workflow --code`, ou o `awscc` do Terraform a partir da 1.99.0), o objeto
  pode ser qualquer um que quem salva consiga ler, como um `.zip` no `shared/` do projeto. O serviço
  o lê na hora do save, na sessão de quem salva. Não exercitado.

**A receita de dependências do guia do portal omite as opções de plataforma** (`pip install
--target ./package sua-dependencia`): rodada noutra plataforma, ela instala os wheels daquela
plataforma para todo pacote compilado. Use o `package-task`, ou a receita à mão abaixo.

**Uma versão nova do código pede um envio e um save.** O workflow roda a cópia que o serviço tirou
no último save, da versão S3 que o `Code` fixa, então trocar o objeto no S3 por fora do portal não
muda o que roda. Cada save tira uma cópia nova, mesmo um que só muda a descrição do workflow
(medido no laboratório em 2026-10-11).

### À mão, sem o pacote

Para um projeto que o `uv` não gerencia, os mesmos passos no shell:

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

## Uma task Bash

**Estado no laboratório**: funciona desde 2026-10-11. Tasks com comandos inline mostraram o
ambiente do worker, e um workflow com um `.zip` montado à mão rodou um módulo do `.zip` com
`python3 -m` e um script do `.zip` pelo nome. Nenhum `.zip` do `package-task` rodou numa task Bash
ainda.

Uma task Bash roda um comando do shell no worker: comandos inline, um script, um módulo Python com
`python3 -m` ou um binário. O código que ela chama viaja no `Code` do workflow, que o `package-task`
monta ([O código de uma task Python ou Bash](#o-codigo-de-uma-task-python-ou-bash)). O operador é
o `BashOperator` do Airflow, cujo código, no `apache-airflow-providers-standard`, foi lido em
2026-10-11.

| | Uma task Python | Uma task Bash |
|---|---|---|
| A task nomeia | uma função, `python_callable: <módulo>.<função>` | um comando, `bash_command` |
| Como roda | a função é chamada no processo da task | num subprocesso, `bash -c "<comando>"`, ou `bash` numa cópia do script chamado pelo nome |
| Sucesso | a função volta sem exceção | a saída 0; a saída 99 pula a task, e qualquer outra a falha |
| O código do `.zip` | importado pelo nome, porque `/usr/local/airflow/dags` está no `sys.path` | um módulo, com `python3 -m`, porque o `PYTHONPATH` começa por `/usr/local/airflow/dags`; um script ou um binário, pelo caminho nessa pasta, porque a pasta de trabalho é outra |

### O comando

**`set -euo pipefail`** abre um comando de várias linhas: sem ele, só a saída do último passo
conta, e um passo que falha no meio passa despercebido.

**O Jinja** renderiza o comando, inline ou num arquivo `.sh`
([Regras de autoria](#regras-de-autoria)): um `{#` sem fecho, como o de `${#lista[@]}`, é um erro
de template, e as chaves duplas só levam as variáveis que o serviço conhece.

**`env`** troca o ambiente inteiro da task: sem `append_env: true` ao lado, ela perde o `PATH` do
worker e as variáveis da credencial (lido no código do operador, não medido).

### O ambiente do worker

O laboratório leu o ambiente em 2026-10-11, em tasks com comandos inline, num workflow sem `Code` e
num com um `.zip`:

- a pasta de trabalho é temporária, `/var/tmp/airflowtmp…`, e não `/usr/local/airflow/dags`, onde
  o `.zip` é extraído. O guia diz que um script roda em `/usr/local/airflow/dags`, mas o script
  chamado pelo nome rodou de uma cópia numa pasta temporária
  ([O código do `.zip` no comando](#o-codigo-do-zip-no-comando));
- com um `.zip`, o `PYTHONPATH` começa por `/usr/local/airflow/dags`, que aparece duas vezes, e
  segue com os pacotes do worker, `/opt/mwaa-serverless-venv/lib/python3.12/site-packages`;
- o `python3` do `PATH` é o do worker, `/opt/mwaa-serverless-venv/bin/python3` 3.12.14, com o
  `boto3` 1.43.1 e os outros pacotes que o worker traz;
- os processos que a task abre recebem a credencial do papel do projeto, sessão
  `AmazonMWAAServerless`, e `AWS_REGION` e `AWS_DEFAULT_REGION` trazem a região;
- as variáveis que o portal injeta no workflow chegam à task: `DataZoneDomainId`,
  `DataZoneDomainRegion`, `DataZoneEndpoint`, `DataZoneEnvironmentId`, `DataZoneProjectId`,
  `DataZoneStage` e `ProjectS3Path`.

### O `Code` do workflow

O `Code` depende do que a task chama:

| A task chama | O `Code` |
|---|---|
| só comandos inline | nenhum: esvazie *Operator files zip S3 location* em *Settings → Storage* antes de salvar |
| um script `.py` ou `.sh` que usa só os pacotes do worker | o próprio arquivo, sem `.zip`, como o guia descreve; onde o worker o põe não foi medido |
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
  roda um módulo dele; o laboratório rodou um módulo assim, depois do `cd` do exemplo. O
  `PYTHONPATH` da task começa por `/usr/local/airflow/dags`, então o `python3` acharia o pacote
  mesmo sem o `cd` (não medido). Pela mesma ordem, um pacote do `.zip` venceria o do worker com o
  mesmo nome (não medido), o contrário de uma task Python; o `package-task` deixa os do worker de
  fora.
- **Um script do `.zip`** roda como `bash /usr/local/airflow/dags/run.sh <argumentos>` (não
  medido). Um `bash_command` que termina em `.sh` ou `.bash`, como `run.sh`, é para o Airflow o
  nome de um template: o worker passou o arquivo do `.zip` pelo Jinja para uma cópia numa pasta
  temporária e rodou `bash` nela (medido no laboratório em 2026-10-11). Essa forma não leva
  argumentos, que fariam o comando deixar de terminar em `.sh`; o `$0` dela não aponta para o
  `.zip`, e as regras do Jinja de [O comando](#o-comando) valem para o arquivo.
- **Um binário** é Linux x86_64 e, de preferência, estático, porque a glibc do worker não é
  documentada. O `.zip` guarda o bit de execução, mas a extração pelo `zipfile` do Python o
  descarta, e o serviço não diz como extrai: copie o binário para a pasta de trabalho e dê
  `chmod +x` lá.

```yaml
run_tool:
  operator: airflow.providers.standard.operators.bash.BashOperator
  bash_command: |
    set -euo pipefail
    cp /usr/local/airflow/dags/minha-ferramenta .
    chmod +x minha-ferramenta
    ./minha-ferramenta --dia {{ ds }}
  retries: 0
```

## Os valores da definição

Uma definição versionada guarda cada valor da conta como placeholder, `<NOME>`, e o portal precisa
dos valores reais. O `render` preenche os placeholders e imprime o resultado na tela; nada do que
ele imprime volta para o repositório. Uma definição que o portal salvou faz o caminho inverso com
`--placeholders`, e o `compare` a confronta com a cópia versionada
([A definição que o portal salvou](#a-definicao-que-o-portal-salvou)).

**Os valores vêm de um arquivo JSON, da conta, ou dos dois.** Quando vêm dos dois, os do arquivo
completam e substituem os da conta:

```shell
awsds-workflows render meu-workflow.yaml --values-file valores.json > /tmp/meu-workflow.yaml
awsds-workflows render meu-workflow.yaml --profile meu-perfil \
    --subnet-name 'meu-projeto-private-*' --values-file imagem.json > /tmp/meu-workflow.yaml
awsds-workflows render --placeholders salvo.yaml --values-file valores.json
awsds-workflows values --profile meu-perfil --subnet-name 'meu-projeto-private-*' > valores.json
```

- **A leitura da conta** (`--profile`) usa o `aws` da máquina, num perfil que alcança a conta do
  projeto, e roda só chamadas de leitura: do STS, do IAM, do EC2 e, com `--image-name`, do
  SageMaker. Ela pede `--subnet-name`, o padrão do `Name` das sub-redes privadas do projeto
  (`awsds-sandbox-private-*` no laboratório). Numa conta com mais de um projeto, `--project`
  escolhe o id.
- **No ambiente alvo** o IAM não respondeu a partir de um espaço (leituras de 2026-09-21 e
  2026-09-23), então lá os valores vêm de um arquivo. Um script do repositório o
  escreve de dentro de um espaço do projeto
  ([Os valores de dentro de um espaço](#os-valores-de-dentro-de-um-espaco)), e o `values` de uma
  máquina que alcança a conta também; os valores da imagem entram à mão.
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

### Os valores de dentro de um espaço

O script
[`scripts/space_values.py`](https://github.com/felipenoris/awsds-workflows/blob/main/scripts/space_values.py)
do repositório roda num espaço do projeto e imprime o JSON que o `values` imprime sem
`--image-name`, sem o pacote, sem o `aws` e sem as permissões de IAM e EC2. Copie o arquivo para o
espaço e rode, num terminal de lá, com o Python do espaço:

```shell
python space_values.py > valores.json
```

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

Os nomes dos recursos vêm do código do SDK `sagemaker-studio` 1.1.35, igual ao da 1.1.32 nesse
ponto (lidos em 2026-10-11). Num espaço do laboratório, em 2026-10-11, o script imprimiu o mesmo
JSON, byte a byte, que o `values` com `--profile` imprimiu para a mesma conta, as sub-redes na
ordem das zonas inclusive. Num espaço do ambiente alvo, em 2026-10-12, o ambiente Tooling tinha
`userRoleArn`, `securityGroup`, `privateSubnets` e `s3BucketPath`, e não tinha `kmsKeyArn`; sem a
chave, o script imprimiu os outros nove valores.

### A definição que o portal salvou

O portal grava a definição a cada save, e ela difere da cópia versionada no texto mesmo quando diz
o mesmo: as chaves reordenadas, os textos longos dobrados em várias linhas e as listas em bloco.
Para ver o que uma mudança feita no portal mudou, copie a definição salva para `salvo.yaml`, de
*View code* ou do arquivo em `dev/workflows/` no bucket do projeto ([As peças](#as-pecas)),
devolva os placeholders e compare:

```shell
awsds-workflows render --placeholders salvo.yaml --values-file valores.json > /tmp/salvo.yaml
awsds-workflows compare meu-workflow.yaml /tmp/salvo.yaml
```

```
- meu-job.tasks.run_project.config.ProcessingResources.ClusterConfig.InstanceType: "ml.t3.medium"
+ meu-job.tasks.run_project.config.ProcessingResources.ClusterConfig.InstanceType: "ml.m5.large"
+ meu-job.is_paused_upon_creation: false
```

- **O `compare` lê as duas definições como YAML** e imprime só as diferenças de conteúdo: os
  comentários, o layout do editor inclusive, a ordem das chaves, as aspas e a forma dos textos e
  das listas não contam. Os valores se comparam com o tipo, então `0` e `"0"` diferem, e as listas
  posição a posição.
- **Cada diferença** sai com o caminho das chaves e o valor em JSON: `-` para o que só a primeira
  definição tem e `+` para o que só a segunda tem; um valor que mudou dá as duas linhas. O comando
  termina com 0 com ou sem diferenças, e com 1 quando um arquivo falta, não é YAML ou não é um
  mapeamento.
- **`is_paused_upon_creation: false`** aparece em toda comparação com uma definição salva: o portal
  o acrescentou a cada save lido no laboratório, e o serviço o ignora, com o aviso
  `ignored attributes: is_paused_upon_creation` na resposta de cada `update-workflow`
  (2026-09-10).
- **O `compare` de seis definições salvas** contra os arquivos importados imprimiu só essa linha e
  as mudanças feitas de propósito, entre elas uma descrição escrita no portal, que entra como a
  chave `description` do workflow (medido no laboratório em 2026-10-12).
- **Uma mudança que deve ficar** entra à mão na cópia versionada, com os placeholders no lugar dos
  valores da conta.

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

**Uma falha no aviso do editor não nomeia a causa**: "Workflow execution failed, please check the
task execution logs for more details". O log da task nomeia, e numa task de processamento o
`FailureReason` do job e o stream do contêiner também.

**Uma falha antes da primeira task** ("User template error: ...") é um template que o serviço não
conseguiu renderizar ao criar a execução ([Regras de autoria](#regras-de-autoria)).

`list-workflow-runs` devolve `RunType` nulo, então o tipo de uma execução é lido execução por
execução. Uma task que falhou roda de novo uma vez com o `retries` padrão: leia a duração da task,
e não a da execução.

**O estado da execução atrasa o das tasks.** O `RunState` do `get-workflow-run` leu `QUEUED` até as
23:06:16Z, depois de o sensor terminar e com o job já sendo criado (2026-10-11). Leia o progresso
nas tasks, com o `list-task-instances`.

## Limpeza

- **Apague um workflow** na página *Workflows*. O grupo de logs dele fica, sem retenção.
- **Esvazie as caixas de entrada** para a próxima execução começar de um estado conhecido; as
  caixas de saída são os resultados.
- **Um job de processamento não pode ser apagado**: ele continua listado.
- **Os `.zip` de código** em `dev/operatorFiles/` ficam com todas as versões, porque o bucket é
  versionado.
- **As pastas de código** em `shared/jobs/` ficam, uma por versão; apague uma só quando nenhuma
  definição a nomeia.
