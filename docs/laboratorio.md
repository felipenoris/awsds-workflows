Estas notas guardam o que o guia resume nos avisos de estado: o que rodou no laboratório, no
ambiente alvo e na máquina que empacota, com a data de cada leitura, e o que ainda não foi medido.
Cada seção tem o nome da seção do guia a que se refere e abre com um link para ela.

## Os ambientes

| Ambiente | O que é | O que rodou lá |
|---|---|---|
| o laboratório | uma conta de testes em `us-west-2`, com uma imagem customizada, `awsds-sandbox-dev-env`, e as outras contas da mesma organização | os passos do guia, nas datas de cada seção abaixo, o `houseprice-etl` pela CLI de CI/CD, de um laptop, em 2026-10-15 e 2026-10-16, e outras aplicações pela CLI num projeto de outra conta, em 2026-10-19 |
| o ambiente alvo | o SageMaker Unified Studio em que os workflows vão rodar | os exemplos, em 2026-10-12 e 2026-10-13, e leituras feitas de um espaço desde 2026-09-21 |
| a máquina que empacota | o Linux com internet em que o pacote roda | o `.tar.gz` do `prepare-offline`, extraído e rodado noutra pasta, em 2026-10-13; o `bundle` da CLI de CI/CD e os planos do Terraform do `lint-plan`, em 2026-10-23 |

## O que ainda não foi medido

- o pacote num espaço de verdade ([O Python que o `uv` usa](#o-python-que-o-uv-usa));
- um arquivo que uma task grava no disco e a seguinte procura ([As peças](#as-pecas));
- na SageMaker Distribution 4.5, o URI da imagem para um job no ambiente alvo, o usuário do
  contêiner de um job e o patch da versão ([A imagem do job](#a-imagem-do-job));
- no ambiente alvo, o caminho do job, do download da imagem à gravação da saída
  ([A rede](#a-rede));
- uma pasta gravada pelo próprio `package-job` num job
  ([A pasta de código com `package-job`](#a-pasta-de-codigo-com-package-job));
- o `.tar.gz` do `prepare-offline` num job, e o custo por arquivo de uma entrada de código
  expandida ([A pasta do projeto preparada num `.tar.gz`](#a-pasta-do-projeto-preparada-num-targz));
- um `python_callable` com um caminho pontuado para dentro do pacote, `pacote.modulo.funcao`
  ([O `.zip` com `package-task`](#o-zip-com-package-task));
- o `Code` de um workflow salvo pela API ([O `.zip` no workflow](#o-zip-no-workflow));
- um `Code` que é um `.py` ou um `.sh` solto, e onde o worker o põe; e o `env` de uma task Bash sem
  `append_env` ([Uma task Bash](#uma-task-bash));
- numa task Python do worker, de onde vem o `six` e o que o `sys.path` mostra
  ([demo-python-operator](#demo-python-operator));
- os cinco exemplos além do `houseprice-etl` pela CLI de CI/CD, e com eles o `.zip` de uma task
  Python ou Bash passado pela CLI e uma variável de stage lida no `config` de um job e nos
  `op_kwargs` de uma task Python; e o `destroy` de um exemplo
  ([A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd));
- uma execução do `houseprice-etl` sem `UpdateJob`, com o `Command` inteiro na definição, e o
  caminho do portal com o workflow traduzido pelo `render` ([houseprice-etl](#houseprice-etl));
- o `lint` no modo promovido e o `lint-plan` numa esteira, e o tempo de provisionamento de um job
  dentro do teto da task ([Regras de autoria](#regras-de-autoria)).

## Instalação

No guia: [Instalação](../awsds_workflows.html#instalacao).

- **Laboratório, 2026-10-12.** Com o `uv` 0.12.13, numa instalação feita de um repositório git
  local que depois ganhou um commit na `main`, o `uv tool upgrade` instalou o commit novo.

### O Python que o `uv` usa

No guia: [O Python que o `uv` usa](../awsds_workflows.html#o-python-que-o-uv-usa).

- **Espaço simulado, 2026-10-11.** Com o `uv` 0.12.17 da imagem do laboratório, os downloads
  desligados, só um CPython 3.12 no `PATH` e um 3.13 fora dele:
  - o `uv tool install` instalou o pacote no 3.12, sem ler o `.python-version` da pasta em que
    rodou;
  - sem o `UV_PYTHON`, o `package-job` e o `package-task` pararam no `uv export --locked` de um
    projeto que pedia o 3.13;
  - com ele, gravaram a pasta e o `.zip`.
- **Espaço simulado, 2026-10-12.** Com os downloads ligados, o `uv` baixou o CPython 3.13.15, e o
  `package-job` gravou os mesmos arquivos, diferentes só em metadados da instalação.
- **Imagem do laboratório, 2026-10-15.** O ambiente do job passou a 3.12
  ([A imagem do job](#a-imagem-do-job)); as leituras acima são do 3.13.
- **Ainda não medido**: num espaço de verdade, o pacote ainda não rodou.

## As peças

No guia: [As peças](../awsds_workflows.html#as-pecas).

- **Laboratório, 2026-10-11.** O bucket da cópia do código que o serviço guarda,
  `mwaa-serverless-code-files-<conta da AWS>-<região>-prod`, foi lido no CloudTrail.
- **Laboratório, 2026-10-11.** Cada task tem o seu worker: duas tasks da mesma execução rodaram em
  sub-redes diferentes, e o log de cada task abre com `Preparing the execution environment.`
- **Ambiente alvo, 2026-10-13.** Um worker tinha mais que o guia da AWS diz: 2 CPUs e 4,7 GiB de
  memória, sem limite de cgroup, numa execução. Uma leitura não diz se o excedente se repete, e o
  guia dimensiona a task pelo guia da AWS.
- **Ainda não medido**: que um arquivo gravado no disco por uma task não chegue à seguinte.

## A imagem do job

No guia: [A imagem do job](../awsds_workflows.html#a-imagem-do-job).

- **Laboratório, 2026-10-12.** O lock do projeto que constrói a imagem do laboratório, exportado com
  `uv export --frozen --no-dev --no-emit-project --no-hashes`, com o cabeçalho e as anotações
  `# via` que o `uv` escreve, foi aceito pelo `package-job` e pelo `job-constraints`, que leu 452
  versões para o CPython 3.13 em `x86_64-manylinux_2_28`.
- **Laboratório, 2026-10-11.** A imagem do laboratório roda como `sagemaker-user` (uid 1000), e o
  `sudo` dela funciona dentro de um job.
- **Ambiente alvo, 2026-10-12.** Num espaço, `/opt/conda/bin/python` era o CPython 3.12.14 e o
  usuário era `sagemaker-user` (uid 1000), com `sudo` sem senha.
- **Ambiente alvo, 2026-10-13.** O espaço roda a SageMaker Distribution 4.5, a versão que o portal
  mostra; o patch dela não foi lido.
- **ECR público, 2026-10-12.** A tag mais nova da 4.5 é a `4.5.2-cpu`.
- **Imagem do laboratório, 2026-10-15.** O ambiente da casa, `/opt/awsds/venv`, é CPython 3.12
  desde a versão `default-v0.7.0` da imagem, a versão menor do Python da distribuição; até a
  `default-v0.6.0`, era 3.13, o das leituras acima. A versão registrada no laboratório desde
  2026-10-16 é a `default-v0.8.0`. Lido na receita da imagem, não num espaço.
- **Ainda não medido na SageMaker Distribution 4.5**: o URI da imagem para um job no ambiente alvo
  e o usuário do contêiner de um job. A distribuição, de cuja 4.5.2 a imagem do laboratório deriva,
  deve ter o mesmo usuário num job, e o primeiro job no ambiente alvo é a medida.

## A permissão do projeto

No guia: [A permissão do projeto](../awsds_workflows.html#a-permissao-do-projeto).

- **Laboratório, 2026-10-10.** As duas recusas do guia foram medidas: a primeira execução falhou com
  `AccessDeniedException` em `DescribeProcessingJob`, antes de existir um job, e a segunda, com
  `AccessDeniedException` em `sagemaker:AddTags`.
- **Ambiente alvo, 2026-10-12.** A primeira execução falhou do mesmo jeito em
  `DescribeProcessingJob`, antes de existir um job.

## A rede

No guia: [A rede](../awsds_workflows.html#a-rede).

- **Laboratório, 2026-10-11.** A tabela e os avisos do guia vêm do CloudTrail, dos logs de fluxo e
  do log do firewall de DNS desse dia. Uma task que tentou o PyPI falhou em cerca de 2 s, na
  resolução do nome, que o firewall de DNS da VPC do laboratório recusa. Com o bucket da cópia do
  código admitido na política do endpoint de gateway do S3, o mesmo workflow rodou.
- **Ambiente alvo, 2026-09-21 e 2026-09-23.** As leituras feitas a partir de um espaço encontraram
  o endpoint de gateway do S3 e endpoints de interface para STS, Redshift, Glue, Athena, Secrets
  Manager e DataZone; os nomes do KMS e do IAM resolveram para endereços públicos e não
  responderam. O nome do SageMaker que elas testaram, `sagemaker.sa-east-1.amazonaws.com`, também
  não respondeu, mas a API atende em `api.sagemaker.sa-east-1.amazonaws.com`.
- **Ambiente alvo, 2026-10-12.** De um espaço do projeto, o SageMaker respondeu a uma listagem de
  jobs e o SSM a uma leitura de parâmetro. Na primeira execução de um workflow lá, o worker listou
  a pasta de entrada no S3, chamou a API do SageMaker, que recusou o pedido por permissão, e gravou
  o log da task. Numa task Python, o worker recebeu a cópia do código, chamou o STS e leu, gravou e
  apagou objetos na pasta do projeto.
- **Ambiente alvo, 2026-10-12.** Numa task Bash, um script que tentou o PyPI não achou variável de
  proxy, resolveu `pypi.org` para um endereço público e falhou com
  `[Errno 101] Network is unreachable` depois de 43 s no urllib, com 10 s de timeout por conexão, e
  de 64 s no pip; no laboratório, a mesma tentativa falhou em cerca de 2 s.
- **Ainda não medido**: no ambiente alvo, o caminho do job, do download da imagem à gravação da
  saída.

## Regras de autoria

No guia: [Regras de autoria](../awsds_workflows.html#regras-de-autoria).

- **Laboratório, 2026-10-11.** Importado no editor de um workflow já salvo, o arquivo virou um
  workflow novo com o mesmo nome, e o save foi recusado com
  `ConflictException: Workflow with given name already exists`.
- **Laboratório, 2026-10-11.** Num workflow sem código, com o campo *Operator files zip S3
  location* esvaziado antes de salvar, o save não mandou o `Code`.
- **Páginas do serviço, 2026-10-16.** Os limites que o `lint` confere: `retries` de 0 a 3,
  `retry_delay` até 300 s e `execution_timeout` até 3.600 s, da página dos parâmetros que o
  serviço valida; a cota de 50 KB por definição, da página de cotas; e os operadores do provedor
  Amazon mais o `PythonOperator` e o `BashOperator`, da página dos operadores.
- **Laboratório, 2026-10-22.** O modo promovido rodou de um laptop, fora de uma esteira, sobre a
  cópia renderizada por conta de uma aplicação com um job do Glue e um job de processamento:
  `ok: 1 arquivo(s)`; com a imagem num repositório que não o de `--image-repository`, recusou
  pela regra `imagem`, com código 1.
- **Máquina que empacota, 2026-10-23.** A mesma aplicação, renderizada com valores fabricados
  pelo script que faz a cópia por conta, passou no modo promovido com a recusa das chaves de
  criação do job do Glue, `ok: 1 arquivo(s)`; com `create_job_kwargs` e `script_location` de
  volta na task, foi recusada pela regra `glue`, com código 1.
- **Máquina que empacota, 2026-10-23.** Com o Terraform 1.15.8 e o provedor `hashicorp/aws`
  6.60.0, sem credencial, o JSON de `terraform show -json` sobre o plano salvo tem
  `format_version` `1.2`; cada `aws_glue_job` está em `resource_changes`, com o endereço, como
  `aws_glue_job.this[0]` ou `module.child.aws_glue_job.late`, e o `command` é uma lista de um
  bloco; um `script_location` calculado no `apply` falta em `change.after` e está em
  `change.after_unknown`; um recurso que o plano apaga tem `after` nulo, e um sem mudança está
  lá com a ação `no-op`, os dois lidos num `terraform_data`; um plano sem recurso não tem
  `resource_changes`. O `lint-plan` leu um plano com o job do Terraform de uma aplicação, o
  script sob a pasta `glue/` da versão: `ok: 1 job(s) do Glue: aws_glue_job.this[0]`; num plano
  com um módulo do PyPI, dois arquivos fora do prefixo e um script calculado no `apply`,
  imprimiu as quatro recusas e terminou com 1.
- **Ainda não medido**: o `lint` no modo promovido e o `lint-plan` numa esteira, sobre a cópia
  renderizada e o plano de uma conta; e o tempo de provisionamento e de encerramento de um job
  de processamento dentro dos 3.600 s da task, que decide a margem dos 2.820 s de
  `MaxRuntimeInSeconds`.

## Uma task de processamento

No guia: [Uma task de processamento](../awsds_workflows.html#uma-task-de-processamento).

### A pasta de código com `package-job`

No guia:
[A pasta de código com `package-job`](../awsds_workflows.html#a-pasta-de-codigo-com-package-job).

- **Laboratório, 2026-10-11.** A imagem do laboratório tem o `onnxruntime` 1.30.0, que não publica
  wheel anterior a `manylinux_2_28`, então `manylinux2014` não a descreve; por isso o padrão do
  `--platform` é `x86_64-manylinux_2_28`.
- **Laboratório, 2026-10-11.** Com a imagem do laboratório, num projeto descartável que dependia de
  `petl`, `requests`, `boto3` e `pyyaml`, o lock novo discordou da imagem em `boto3`, `botocore`,
  `charset-normalizer`, `idna` e `urllib3`; com o bloco impresso e um novo `uv lock`, 12 pacotes
  vieram da imagem e só o `petl` entrou na pasta, de 1,2 MB.
- **Laboratório, 2026-10-11, num job.** Com a imagem do laboratório, num projeto que dependia do
  `petl` (Python puro), do `msgspec` (um módulo de extensão) e do `pyarrow`, que a imagem tem, o
  lock novo discordou da imagem no `pyarrow`, 26.0.0 no lock e 24.0.0 na imagem. Com o bloco e um
  novo `uv lock`, a pasta levou o projeto, o `petl` 1.7.29 e o `msgspec` 0.22.0, em 176 arquivos e
  1.735.841 bytes. O job a recebeu como entrada de código, sem rede, e o contêiner imprimiu de onde
  importou cada pacote:

  ```
  python 3.13.15 at /opt/awsds/venv/bin/python
  petl 1.7.29 from /opt/ml/processing/code/petl
  msgspec 0.22.0 from /opt/ml/processing/code/msgspec, extension _core.cpython-313-x86_64-linux-gnu.so
  pyarrow 24.0.0 from /opt/awsds/venv/lib/python3.13/site-packages/pyarrow, extension lib.cpython-313-x86_64-linux-gnu.so
  ```

  O pacote Python puro e o módulo de extensão vieram da pasta, e o `pyarrow` do ambiente da imagem;
  as saídas, um JSON e uma tabela Parquet, são byte a byte as da execução local. A pasta foi
  gravada num espaço por um script com os mesmos passos do `uv`.
- **Espaço simulado.** O `package-job` gravou os mesmos 176 arquivos, iguais a menos de três
  metadados do projeto: o caminho temporário do wheel, a hora da construção e os hashes dos dois.
- **Laboratório, 2026-10-11.** O `shared/` de um espaço grava no prefixo um marcador de zero bytes
  por pasta, e um job baixou um prefixo assim sem problema.
- **Ainda não medido**: nenhuma pasta do `package-job` rodou num job ainda.

### A pasta do projeto preparada num `.tar.gz`

No guia:
[A pasta do projeto preparada num `.tar.gz`](../awsds_workflows.html#a-pasta-do-projeto-preparada-num-targz).

- **Máquina que empacota, 2026-10-13** (uv 0.11.32). Sobre o projeto dos exemplos,
  `examples/awsds-demo-job/`, o `prepare-offline` levou de 11 a 14 s em duas execuções, baixando
  o CPython 3.12.13, e gravou 34.111.121 bytes, 100.119.806 extraídos, 98.862.413 deles o
  interpretador e 1.233.013 a `.venv/`, em 4.970 membros com 1.053 links, nenhum absoluto; a
  extração noutra pasta levou 1,3 s.
- **Máquina que empacota, 2026-10-13.** Extraída noutra pasta, com a de origem renomeada, por um
  usuário sem privilégio e num ambiente sem `uv`, sem `HOME` e sem rede, a pasta rodou
  `python -m awsds_demo_job` sobre a amostra e escreveu o resumo com o sha256 das execuções
  medidas. O teste `network` do repositório repete essa prova.
- **Ainda não medido**: nenhum `.tar.gz` rodou num job ainda, e o custo por arquivo de uma entrada
  de código expandida não foi medido.

### Uma definição de exemplo

No guia: [Uma definição de exemplo](../awsds_workflows.html#uma-definicao-de-exemplo).

- **Laboratório, 2026-10-11.** Uma execução levou cerca de 15 minutos e 0,03 USD. O job passou
  cerca de 7,5 dos seus 8 minutos baixando a imagem do laboratório, de 6,97 GB, antes de o
  contêiner começar, e a task de processamento ocupou o worker durante o job inteiro.
- **Laboratório, 2026-10-11, o job com dependências.** A task ocupou o worker 791 s para um comando
  de um segundo: cerca de 3 minutos de provisionamento antes do `ProcessingStartTime`, 7 de
  download da imagem e 2,5 depois do `ProcessingEndTime` até o job ler `Completed`, o estado que o
  operador espera. A pasta com as dependências não mudou o custo da execução, cerca de 0,03 USD.

## O código de uma task Python ou Bash

No guia:
[O código de uma task Python ou Bash](../awsds_workflows.html#o-codigo-de-uma-task-python-ou-bash).

- **Laboratório, desde 2026-10-11.** Uma task Python e uma task Bash, cada uma com um `.zip`,
  leram a amostra, gravaram o resultado e apagaram a origem. Os dois `.zip` foram montados pela
  receita [à mão](../awsds_workflows.html#a-mao-sem-o-pacote). Antes, o worker falhava ao preparar
  o ambiente, antes de qualquer task: a política do endpoint de gateway do S3 recusava o bucket da
  cópia do código ([A rede](#a-rede)).
- **Ambiente alvo, desde 2026-10-12.** Uma task Python rodou com um `.zip` do `package-task` de
  261.205 bytes, o projeto do laboratório com o `petl` 1.7.28. O worker, um CPython 3.12.14,
  importou o `petl` do `.zip`, em `/usr/local/airflow/dags`, e o PyYAML 6.0.2 dos pacotes dele, e
  o resultado saiu igual ao do laboratório, com o mesmo sha256. Uma task Bash rodou no mesmo dia,
  com um `.zip` do `package-task` que leva também dois scripts de `--include`
  ([Uma task Bash](#uma-task-bash)). Os dois estão na pasta de exemplos do repositório
  ([Os exemplos](#os-exemplos)).

### O que o worker espera

No guia: [O que o worker espera](../awsds_workflows.html#o-que-o-worker-espera).

- **Laboratório, 2026-10-11.** Numa task Python, o PyYAML 6.0.2 do worker foi importado no lugar
  do 6.0.1 do `.zip`.
- **Ambiente alvo, 2026-10-13.** Todos os pacotes que o guia manda deixar fora do `.zip` estavam
  no worker.

### O `.zip` com `package-task`

No guia: [O `.zip` com `package-task`](../awsds_workflows.html#o-zip-com-package-task).

- **Laboratório, 2026-10-11.** Num projeto descartável que dependia de `petl`, `requests`, `boto3`
  e `pyyaml`, o `.zip` teve cerca de 0,9 MB, com o projeto, `tasks.py`, o `petl` e o `requests`
  com `certifi`, `charset_normalizer`, `idna` e `urllib3`; sem `boto3`, `botocore`, `s3transfer`,
  `jmespath` ou `yaml`. Os módulos compilados do `charset_normalizer` saíram com a etiqueta
  `cp312-cp312-manylinux2014_x86_64`, e `cpython-313` com `--python 3.13`.
- **Ainda não medido**: um `python_callable` com um caminho pontuado para dentro do pacote,
  `pacote.modulo.funcao`.

### O `.zip` no workflow

No guia: [O `.zip` no workflow](../awsds_workflows.html#o-zip-no-workflow).

- **Laboratório.** Um `.zip` enviado pelo portal foi guardado como foi enviado, com a versão S3
  fixada e o sha256 igual ao do `.zip` construído.
- **Laboratório, 2026-10-11.** Cada save tirou uma cópia nova do código, mesmo um que só mudou a
  descrição do workflow.
- **Ainda não exercitado**: o `Code` pela API (`create-workflow --code`, ou o `awscc` do Terraform
  a partir da 1.99.0).

## Uma task Bash

No guia: [Uma task Bash](../awsds_workflows.html#uma-task-bash).

- **Laboratório, desde 2026-10-11.** Tasks com comandos inline mostraram o ambiente do worker, e
  um workflow com um `.zip` montado à mão rodou um módulo do `.zip` com `python3 -m` e um script do
  `.zip` pelo nome.
- **Ambiente alvo, desde 2026-10-12.** Uma task Bash rodou com um `.zip` do `package-task`: o
  projeto do laboratório com o `petl` 1.7.28 e o `six` 1.16.0, e dois scripts de `--include`. Um
  módulo do `.zip` rodou com `python3 -m`, com e sem o `cd`; um script rodou pelo nome, pelo
  caminho inteiro e executado direto; e o resultado saiu igual ao do laboratório, com o mesmo
  sha256. A task que tentou o PyPI falhou, como esperado, porque o ambiente alvo não tem internet
  ([A rede](#a-rede)).
- **Código do operador, lido em 2026-10-11.** O código do `BashOperator`, no
  `apache-airflow-providers-standard`, foi lido nesse dia; o aviso do guia sobre o `env` vem dele.
- **Ainda não medido**: o `env` sem `append_env: true`, que pelo código do operador tira da task
  o `PATH` do worker e as variáveis da credencial; e onde o worker põe um `Code` que é um `.py`
  ou um `.sh` solto.

### O ambiente do worker

No guia: [O ambiente do worker](../awsds_workflows.html#o-ambiente-do-worker).

- **Laboratório, 2026-10-11.** O ambiente foi lido em tasks com comandos inline, num workflow sem
  `Code` e num com um `.zip`.
- **Ambiente alvo, 2026-10-12.** A mesma pasta de trabalho, o mesmo `PYTHONPATH` e o mesmo
  `python3` foram lidos numa task com um `.zip` do `package-task`; os arquivos do `.zip` chegaram
  com o modo que o `.zip` guarda, todos do uid e gid 997, e um script de `--include` chegou
  executável.
- **Ambiente alvo, 2026-10-13.** O disco, as ferramentas e os pacotes foram lidos numa task
  inline: 164 distribuições, nenhum `tar`, `unzip` ou `aws`, só o `gzip`, e o disco da raiz, um
  `overlay` de 21 GiB, com 19 GiB livres, onde gravar 1 GiB em `/var/tmp` levou 3 s, e o `/tmp`
  num disco à parte, de 9,7 GiB.

### O código do `.zip` no comando

No guia: [O código do `.zip` no comando](../awsds_workflows.html#o-codigo-do-zip-no-comando).

- **Laboratório, 2026-10-11.** Um módulo do `.zip` rodou com `python3 -m`, depois do `cd` do
  exemplo. Um `bash_command` que termina em `.sh` passou o arquivo do `.zip` pelo Jinja para uma
  cópia numa pasta temporária e rodou `bash` nela.
- **Ambiente alvo, 2026-10-12.** Um módulo do `.zip` rodou sem o `cd`. Um script do `.zip` rodou
  pelo caminho, com o `$0` igual a esse caminho e a pasta de trabalho da task, e executado direto,
  sem `bash` na frente, porque o worker manteve o bit de execução ao extrair. O `bash_command` que
  termina em `.sh` rodou como no laboratório.
- **Ambiente alvo, lido em 2026-10-13.** Na task Bash de 2026-10-12, o `python3` importou o
  `six` 1.16.0 do `.zip` no lugar do 1.17.0 do worker.

## Os valores da definição

No guia: [Os valores da definição](../awsds_workflows.html#os-valores-da-definicao).

- **Ambiente alvo, 2026-09-21 e 2026-09-23.** O IAM não respondeu a partir de um espaço, então lá
  os valores vêm de um arquivo.
- **Ambiente alvo, 2026-10-12.** O projeto não tinha chave KMS própria, e por isso não deu
  `PROJECT_KEY_ID`.

### Os valores de dentro de um espaço

No guia:
[Os valores de dentro de um espaço](../awsds_workflows.html#os-valores-de-dentro-de-um-espaco).

- **SDK, lido em 2026-10-11.** Os nomes dos recursos que o script lê vêm do código do SDK
  `sagemaker-studio` 1.1.35, igual ao da 1.1.32 nesse ponto.
- **Laboratório, 2026-10-11.** Num espaço, o script imprimiu o mesmo JSON, byte a byte, que o
  `values` com `--profile` imprimiu para a mesma conta, as sub-redes na ordem das zonas inclusive.
- **Ambiente alvo, 2026-10-12.** Num espaço, o ambiente Tooling tinha `userRoleArn`,
  `securityGroup`, `privateSubnets` e `s3BucketPath`, e não tinha `kmsKeyArn`; sem a chave, o
  script imprimiu os outros nove valores.

### A definição que o portal salvou

No guia:
[A definição que o portal salvou](../awsds_workflows.html#a-definicao-que-o-portal-salvou).

- **Laboratório, 2026-09-10.** O serviço ignorou o `is_paused_upon_creation`, com o aviso
  `ignored attributes: is_paused_upon_creation` na resposta de cada `update-workflow`; o portal o
  acrescentou a cada save lido no laboratório.
- **Laboratório, 2026-10-12.** O `compare` de seis definições salvas contra os arquivos importados
  imprimiu só a linha do `is_paused_upon_creation` e as mudanças feitas de propósito, entre elas
  uma descrição escrita no portal, que entrou como a chave `description` do workflow.

## Como ler uma execução

No guia: [Como ler uma execução](../awsds_workflows.html#como-ler-uma-execucao).

- **Laboratório, 2026-10-11.** O `RunState` do `get-workflow-run` leu `QUEUED` até as 23:06:16Z,
  depois de o sensor terminar e com o job já sendo criado.

## Os exemplos

No guia: [Os exemplos](../awsds_workflows.html#os-exemplos); os passos estão em
[Os exemplos, passo a passo](examples.html).

O `houseprice-etl` rodou no laboratório pela CLI de CI/CD, nos stages `dev` e `test`, em
2026-10-15 e 2026-10-16. Os outros rodaram no ambiente alvo em 2026-10-12 e 2026-10-13, pelo
portal, antes de virarem aplicações, e o `demo-devenv-job` parou lá na permissão do projeto;
nenhum dos cinco rodou pela CLI ainda. O `README.md` de cada exemplo traz as leituras inteiras de
cada execução.

### A preparação

Nos passos: [A preparação](examples.html#a-preparacao).

- **Ambiente alvo, 2026-10-12.** A pasta `~/shared/` de um espaço é o prefixo `shared/` do projeto
  no bucket, então um `cp` para lá é um envio ao S3.
- **Laboratório, 2026-10-15.** A CLI de CI/CD, pelo `boto3`, não leu o cache em que o `aws` guarda
  a credencial de um perfil SSO: com o token SSO vencido, o `aws` ainda respondia, e a CLI parou
  em `Token has expired and refresh failed`; a credencial exportada do perfil com
  `aws configure export-credentials --format env` resolveu.

### A aplicação pela CLI de CI/CD

Nos passos: [A aplicação pela CLI de CI/CD](examples.html#a-aplicacao-pela-cli-de-cicd). Medido
com o `houseprice-etl`, entre dois projetos de uma conta, pela CLI 1.0.9 de um laptop, salvo
onde o item diz outra aplicação.

- **Laboratório, 2026-10-15.** O `deploy --targets dev --skip-validation --no-events` copiou os
  dois arquivos para `shared/exemplos/houseprice-etl/` do projeto de dev e criou o workflow,
  `READY` e só manual, com o papel, a rede e a chave do projeto, como um workflow feito no
  portal; a definição gravada no S3 é a resolvida. Sem `--skip-validation`, o `deploy` abortou na
  validação prévia, exit 1, sem escrever nada: a simulação do IAM sem as chaves de contexto das
  chamadas reais leu como negadas permissões que as chamadas reais têm. Sem `--no-events`, o
  `deploy` para no evento do fim, que não tem quem o trate na 1.0.9.
- **Laboratório, 2026-10-15.** No portal, o workflow da CLI apareceu na lista, só manual, com a
  definição só para leitura.
- **Laboratório, 2026-10-16.** O `run` passou as variáveis de stage como parâmetros da execução,
  o `OverrideParameters` do `get-workflow-run`; a definição gravada tem `{{ params.SUBNET_AZ1 }}`,
  e o operador do Glue escreveu os valores nos nomes das conexões do job. Uma `{env.NOME}` fora
  do `environment_variables` do stage derrubou o `workflow.create` com
  `Failed to resolve variables`.
- **Laboratório, 2026-10-16.** O `bundle --targets test` gravou `artifacts/houseprice-etl.zip`,
  1.648 bytes, com o script e o workflow iguais aos do git, as variáveis por resolver, sem o
  manifest. O `deploy --targets test --bundle-archive-path` leu as duas pastas do disco, ao lado
  do manifest, criou o workflow no projeto de teste, com o papel e a rede dele, e o executou.
  Com `wait: true` no `workflow.run`, a CLI caiu com um `TypeError` logo depois de iniciar a
  execução, que terminou `SUCCESS`; com `trailLogs: true`, a execução terminou `SUCCESS` em 149 s
  e a CLI voltou 0 depois de 5,5 min, sem transmitir uma linha de log. A saída 1 com uma
  execução em falha foi lida no código, não medida.
- **Laboratório, 2026-10-16.** Cada `deploy` gastou uma versão do workflow, com a definição
  mudada ou não: duas versões para dois `deploy` no projeto de teste, três para três no de dev.
- **Laboratório, 2026-10-16.** O `monitor` mostrou uma execução terminada como `INITIALIZING`,
  com `Start Time: N/A`, e o `logs`, com o ARN do workflow, respondeu `No log events found` com
  40 eventos no stream da execução: o `get-workflow-run` e o `get-log-events` são as leituras.
- **Laboratório, 2026-10-19**, num projeto de outra conta, com outra aplicação. Um bundle
  guardado, passado com `--bundle-archive-path` a um `deploy` rodado num checkout sem o `.zip`
  do `code`, não foi lido: o `deploy` copiou os arquivos da pasta do manifest e parou com
  `No operator code found in S3`, exit 1. Extraído numa pasta vazia, com o manifest ao lado, o
  mesmo `deploy` sem `--bundle-archive-path` copiou os sete arquivos e criou o workflow.
- **Laboratório, 2026-10-19**, no mesmo projeto. Uma segunda aplicação, com as pastas noutro
  prefixo, não mudou nenhum arquivo nem o workflow da primeira. Uma terceira, com o nome de
  workflow e o `dag_id` da primeira, imprimiu `Reading workflow from S3` com a chave do YAML da
  primeira, `shared/<primeira>/workflows/<workflow>.yaml`, gravou a versão resolvida por cima
  dele e criou o workflow com a definição da primeira; o `.zip` dela, de outro nome, foi o
  próprio. A busca varre a pasta `shared/` inteira porque a CLI lê o destino de cada item por um
  atributo que o manifest não tem, `target_directory` no lugar de `targetDirectory`, e o
  primeiro arquivo listado vence.
- **Laboratório, 2026-10-19**, no mesmo projeto. O `destroy --targets` sem `--force` imprimiu
  o plano e perguntou; o plano de uma aplicação com um `GlueJobOperator` listou o job do Glue
  que a definição nomeia. Com `--force`, o `destroy` da segunda apagou o workflow e os objetos
  dos dois prefixos do manifest, `deleted=3`, e deixou o `.zip` em `operatorFiles/` e o grupo
  de logs. Cada `deploy` grava uma cópia nova do `.zip` em `operatorFiles/`, e nenhuma é
  apagada.
- **Máquina que empacota, 2026-10-23.** O `bundle` com o `include` `code/*.zip` imprimiu
  `Warning: Pattern not found: code/*.zip` e `Bundled 0 files for 'code'`, saiu com 0, e o
  bundle levou só o workflow; com o `include` `code/demo-python-operator.zip`, levou o `.zip`.
  O `deploy` expande o glob, pelo código da CLI.
- **Ainda não medido**: os outros cinco exemplos pela CLI; com eles, o `.zip` de uma task Python
  ou Bash passado pela CLI como `Code`, e uma variável de stage lida no `config` de um job de
  processamento e nos `op_kwargs` de uma task Python, que o código do Airflow renderiza; e o
  `destroy` de um exemplo.

### probe-worker

Nos passos: [probe-worker](examples.html#probe-worker).

- **Ambiente alvo, 2026-10-13.** 19G livres em `/`, 2 vCPUs e 4,7 GiB, só o `gzip`, o Python
  3.12.14 e 164 distribuições, em 13,3 s.

### demo-python-operator

Nos passos: [demo-python-operator](examples.html#demo-python-operator).

- **Laboratório, 2026-10-11, e ambiente alvo, 2026-10-12.** O hash do resultado foi o mesmo,
  `1b2bc4d73bc49bca1a23a6d0971c1365362e785826a33adfcebec7925a248191`.
- **Ambiente alvo, 2026-10-12.** A task rodou em 2,4 s, às 19:16 UTC.
- **Máquina que empacota, 2026-10-13.** O `package-task` imprimiu 274 KB.
- **Ainda não lidas**: a linha do `six`, 1.16.0 no `.zip` e 1.17.0 no worker, que diz qual venceu
  numa task Python, e o `sys.path`, que diz por quê.

### demo-bash-operator

Nos passos: [demo-bash-operator](examples.html#demo-bash-operator).

- **Ambiente alvo, 2026-10-12.** Cada task rodou num worker próprio: `probe_bash` em 11,7 s,
  `run_command` em 9,2 s e `reach_pypi` em 116 s, 43 s do `urllib` e 64 s do `pip`.

### demo-devenv-job

Nos passos: [demo-devenv-job](examples.html#demo-devenv-job).

- **Ambiente alvo, 2026-10-12.** A execução das 18:12 UTC passou pelo sensor e parou na
  permissão, com `AccessDeniedException` em `sagemaker:DescribeProcessingJob`, antes de existir
  um job, com a pasta do projeto expandida no S3 como entrada de código.
- **Laboratório, 2026-10-11.** Com uma imagem customizada e a chave KMS do projeto, a definição
  sobre a pasta expandida rodou em cerca de 15 minutos e 0,03 USD.
- **Máquina que empacota, 2026-10-13.** O `prepare-offline` imprimiu
  `34111121 bytes, 100119806 extraídos, com o CPython 3.12.13 em Linux x86_64`, em 14 s. O
  `.tar.gz` extraído noutra pasta, por um usuário sem privilégio e sem `uv` nem rede, escreveu o
  resumo com o mesmo sha256, em 1,3 s de extração para 100 MB.
- **Ainda não medido no ambiente alvo**: do pull da imagem à gravação da saída, o caminho do job;
  o usuário do contêiner da imagem padrão; e o `.tar.gz` num job.

### redshift-unload

Nos passos: [redshift-unload](examples.html#redshift-unload).

- **Ambiente alvo, 2026-10-13.** O workflow parou em
  `Permission denied to query database created from datashare` até o `GRANT USAGE ON DATABASE`
  dos passos, que bastou sozinho, o que indica um banco criado sem `WITH PERMISSIONS` (inferido).
- **Ambiente alvo, 2026-10-13.** A função descarregou 101 linhas em 5,5 s no espaço e no workflow,
  numa task de 23,4 s.

### houseprice-etl

Nos passos: [houseprice-etl](examples.html#houseprice-etl).

- **Fora da AWS, 2026-10-14**, sem credenciais. O script rodou no PySpark 4.1.1, o Spark do Glue
  6.0; a task rodou contra o Glue e o STS do `moto`; e o manifest passou na validação da CLI de
  CI/CD 1.0.9 e no `bundle`. As versões e as chamadas de cada execução estão no `README.md` do
  exemplo.
- **Laboratório, 2026-10-15 e 2026-10-16.** O `deploy`, o `run`, o `bundle` e o `deploy` no
  stage `test` estão em [A aplicação pela CLI de CI/CD](#a-aplicacao-pela-cli-de-cicd).
- **Laboratório, 2026-10-16.** A primeira execução no projeto de dev parou no `GetJob`,
  `AccessDenied` para o papel do projeto, sem tentar o `CreateJob`: a política gerenciada do
  papel, `SageMakerStudioProjectUserRolePolicy`, autoriza `glue:GetJob`, `UpdateJob`,
  `StartJobRun` e `GetJobRun` só sobre um job com a etiqueta `AmazonDataZoneProject` do projeto,
  e um job que não existe não tem etiqueta. Com o job criado uma vez com o `job.json`, a segunda
  e as seguintes terminaram `SUCCESS`: o job do Glue em 86 s na segunda, o CSV igual à entrada,
  e um CSV a mais em `saida/` a cada execução.
- **Laboratório, 2026-10-16, com o grant do `GetJob`.** Com a política do papel do projeto de dev
  autorizando o `glue:GetJob` sobre os jobs sem etiqueta de projeto cujo nome termina no id do
  projeto, aplicada às 14:54 UTC, e o job apagado, a execução das 15:22 UTC terminou `SUCCESS` em
  139 s: o `GetJob` respondeu `EntityNotFoundException`, o `CreateJob` com a etiqueta passou só
  com a política gerenciada, e o operador criou o job com o papel do projeto, o script em `glue/`,
  as conexões preenchidas, o `PythonVersion: "3"` posto pelo serviço e a etiqueta do projeto; o
  log da task diz `Checking if job already exists` e depois `Creating job`. O controle negativo,
  por simulação sobre o papel de dev: o `GetJob` sobre o job do projeto de teste, sobre um nome
  livre terminado no id desse projeto e sobre um nome com outro sufixo continua negado.
- **Laboratório, 2026-10-16.** Uma execução cuja definição referencia um parâmetro que o manifest
  não declara falha no render, antes de qualquer task e de qualquer chamada ao Glue: o workflow
  de dev numa forma experimental, `update_config: "{{ params.GLUE_UPDATE_CONFIG }}"`, executado
  pelo manifest do exemplo, que não declara a variável, terminou com `DAG template rendering
  failed: 'dict object' has no attribute 'GLUE_UPDATE_CONFIG'`; o parâmetro não é preenchido
  vazio. Pelo portal, que não passa parâmetros à execução, falharia do mesmo jeito (inferido). A
  regra `manifest` do `lint` recusa um `{env.NOME}` que um stage não declara.
- **Laboratório, 2026-10-16.** O operador chamou `UpdateJob` em toda execução, com a definição
  sem mudança, porque o `GetJob` devolve o `Command` com `PythonVersion: "3"` e o `Command` que o
  operador monta não o tem; a definição do exemplo leva o `Command` inteiro desde então. Um
  `update_config` vindo de uma variável de stage não mudou nada: o operador chamou `UpdateJob`
  com `"false"` e com a variável vazia, porque o campo não passa pelo template e um texto vale
  como verdadeiro.
- **Laboratório, 2026-10-16.** No projeto de teste, com o job criado uma vez da mesma forma, a
  execução do `deploy` terminou `SUCCESS`, o job do Glue em 124 s e 545 linhas em `saida/`, as
  da entrada do laboratório; a execução repetida com `trailLogs` terminou em 149 s.
- **Ainda não medido**: uma execução sem `UpdateJob`, com o `Command` inteiro; o workflow
  importado no portal a partir do `render` do YAML da CLI.
