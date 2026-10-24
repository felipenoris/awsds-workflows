# Questões em aberto

Leia antes de planejar uma sessão e antes de dar uma pergunta por aberta. Este documento registra o
que ainda não tem resposta: as pendências do projeto, as decisões que esperam o usuário e as
perguntas que uma leitura ou uma execução vai fechar. Um item sai daqui quando a resposta entra onde
ela fica (a docstring ou o teste do código, `decisions.md` ou outro arquivo desta pasta), e a saída
nomeia esse lugar.

- **As escolhas de desenho da primeira sessão esperam o usuário.** A lista está em `decisions.md`,
  "Design choices of the first session": o arquivo de ambiente do `package-job`, os valores do
  `render` por arquivo, os nomes genéricos dos placeholders, o `--subnet-name` obrigatório com
  `--profile`, o `--omit`, o `job-constraints`, as mensagens em português, a CI só no Ubuntu e o
  `docs/index.md` como runbook; as da pasta de exemplos, de 2026-10-13 e 2026-10-14
  (`decisions.md`, "The examples folder"), as dos exemplos como aplicações, de 2026-10-16
  (`decisions.md`, "The examples as applications"), as três do `lint` não levadas ao usuário,
  que confirmou as cinco do PR #21 em 2026-10-16 (`decisions.md`, "The lint of an application"),
  e as do `lint-plan` e da regra (6), de 2026-10-23 (`decisions.md`, "The Stage 10 rules after
  Stage 18"). Fecha com a resposta do usuário no PR.
- **A rede do alvo para um workflow.** Na primeira execução no alvo, em 2026-10-12, o worker listou
  a pasta de entrada no S3, chamou a API do SageMaker, que recusou o `DescribeProcessingJob` por
  permissão, e gravou o log da task; às 19:16 UTC, numa task Python, o worker recebeu a cópia do
  código, chamou o STS e leu, gravou e apagou objetos na pasta do projeto; às 19:36 UTC, numa task
  Bash, uma tentativa de alcançar o PyPI falhou com `[Errno 101] Network is unreachable`
  (`environments.md`, "The target"). O Terraform do alvo (a versão atual do usuário, lida em
  2026-10-12) declara endpoints de interface com DNS privado para `sagemaker.api`, `logs`, `sts`,
  `ecr.api` e `ecr.dkr`, entre outros, e nenhum para o KMS. As leituras do serialize-db de
  2026-09-21 e 2026-09-23, em que o SageMaker não respondeu, testaram
  `sagemaker.sa-east-1.amazonaws.com`, que não é o nome da API (`api.sagemaker...`). Não medido no
  alvo: o caminho do job, do pull da imagem à gravação da saída. Fecha com o primeiro job no alvo.
- **A imagem padrão do alvo como imagem do job.** O espaço do alvo roda a SageMaker Distribution
  4.5, a versão que o portal mostra (o usuário, 2026-10-13; `decisions.md`, "Where the package
  runs"), e a tag mais nova da 4.5 no ECR público é a 4.5.2 (lida em 2026-10-12). Num espaço do
  alvo, em 2026-10-12, `/opt/conda/bin/python` era o CPython 3.12.14, como em 2026-09-21, o
  usuário `sagemaker-user` (uid 1000, gid 100) tinha `sudo` sem senha, e o parâmetro público do
  SSM deu a conta do repositório `sagemaker-distribution-prod` da região (`environments.md`, "The
  target"). A primeira definição do alvo usa `sagemaker-distribution-prod:4.5.2-cpu`. Não
  medidos: o patch da 4.5 que o espaço roda, de que depende o arquivo de ambiente de um
  `package-job` cujo job usa a 4.5.2, o pull dessa imagem por um job, e o usuário e o `sudo` dentro
  do job, que o `chown` da pasta de saída usa. Fecha com o primeiro job.
- **O papel do projeto no alvo e o operador de processamento.** A política do blueprint
  `SageMakerStudioProjectRoleMachineLearningPolicy` v42, lida em 2026-10-12, só deixa descrever um
  job com a etiqueta `AmazonDataZoneProject` do chamador e tira as chaves `AmazonDataZone*` do
  `AddTags`, as duas recusas que o laboratório mediu em 2026-10-10; o operador do provedor Amazon
  do Airflow (9.37.0) sempre descreve o nome antes de criar o job. No alvo, a primeira execução,
  em 2026-10-12, falhou na primeira recusa, como papel do projeto. O papel nasce do ambiente
  Tooling do projeto, que o Terraform do alvo cria; a política de `docs/index.md` ("A permissão do
  projeto") foi ao usuário como cópias ajustadas desse Terraform, ainda não aplicadas
  (`environments.md`, "The target"). Fecha com a aplicação e uma execução que crie o job.
- **Nenhuma pasta do `package-job` rodou num job, e o pacote não rodou num space.** No laboratório,
  uma pasta gravada num space pelo script do AWS-DataScience, com os mesmos passos do `uv`, rodou
  num job em 2026-10-11, e o `package-job` gravou a mesma pasta num space simulado, com o
  `UV_PYTHON` apontando o 3.13 da imagem (`packaging.md`, "The interpreter `uv` needs"). Desde a
  versão `default-v0.7.0` da imagem, de 2026-10-15, o ambiente do job é 3.12, a versão menor da
  distribuição, e a recusa vale para um projeto que pede outra versão (`environments.md`). Não
  medidos num space de verdade: o `uv tool install` do pacote no Python da distribuição, a recusa
  sem o `UV_PYTHON` e a pasta com ele. Fecha com o `package-job` rodado num space do laboratório e
  a pasta dele num job.
- **Uma task Bash: o `Code` de um arquivo só e o `env`.** Uma task Bash sobre um `.zip` do
  `package-task` com `--include` rodou no ambiente alvo em 2026-10-12 e mediu o resto do que este
  item listava: o script pelo caminho inteiro e a pasta de trabalho dele, o `python3 -m` sem o `cd`,
  o `six` do `.zip` importado no lugar do que o Airflow do worker traz e o bit de execução mantido
  na extração (`environments.md`, "The first Bash task"; `docs/index.md`, "O código do `.zip` no
  comando"). Não medidos: onde o worker põe um `Code` que é um `.py` ou um `.sh` sozinho, e o `env`
  sem `append_env`, lido só no código do operador. Fecha com uma task que use cada um.
- **Por que a cópia do worker vence numa task Python.** O PyYAML 6.0.2 do worker venceu o 6.0.1 de
  um `.zip` numa task Python (laboratório, 2026-10-11), e o `six` 1.16.0 de um `.zip` venceu o do
  worker numa task Bash, cujo `PYTHONPATH` começa por `/usr/local/airflow/dags` (ambiente alvo,
  2026-10-12). Não lido: o `sys.path` do processo de uma task Python. Se ele também começa pela
  pasta do `.zip`, só vence o módulo que o worker importou antes da função da task (o `yaml`, o
  `six` do Airflow), e um pacote do worker que a função importa primeiro sai do `.zip`; a
  docstring de `package_task.WORKER_PROVIDED` e `docs/index.md` ("O que o worker espera") dizem
  que, numa task Python, o pacote pré-instalado vence. Fecha com o exemplo `demo-python-operator`
  do repositório rodado no alvo: o `demo_tasks.py` dele imprime o `sys.path` e a origem do
  `petl`, do `six` e do `yaml` (2026-10-13).
- **Os cinco exemplos que rodaram no ambiente alvo não rodaram pela CLI de CI/CD.** Eles rodaram
  pelo portal em 2026-10-12 e 2026-10-13, antes de virarem aplicações (`decisions.md`, "The examples
  as applications"), com o prefixo da pasta pessoal; os workflows de `examples/*/workflows/` são os
  mesmos na notação da CLI, com o prefixo literal `exemplos/<exemplo>`, e os dois `.zip` saem do
  projeto compartilhado com as raízes dos do alvo (`packaging.md`, "The port verified against the
  original scripts"). Não medidos: cada um pela CLI, pelos passos da página
  `awsds_workflows.examples`, e com eles o `.zip` de uma task Python ou Bash passado pela CLI como
  `code`, uma variável de stage lida no `config` de um job de processamento e nos `op_kwargs` de uma
  task Python, que o Airflow renderiza, e o `demo-devenv-job` com o `src/` e o
  `{env.JOB_IMAGE_URI}`; cada um importado no portal a partir do `render` do workflow da CLI; e o
  `destroy` de um exemplo, que rodou no laboratório sobre outras aplicações em 2026-10-19
  (`cicd-cli.md`, "The CLI in Stage 18's deployment project"). Fecha com essas execuções.
- **O `.tar.gz` da pasta preparada num job.** O `demo-devenv-job` passou a esse formato pela
  palavra do usuário de 2026-10-13 (04:55 UTC; `decisions.md`, "The examples folder"), e o
  `prepare-offline` o grava desde o pedido das 05:15 UTC; provado na máquina que empacota
  (extraído noutra pasta, por um usuário sem privilégio, sem `uv` nem rede, com o sha256 das
  execuções medidas; `packaging.md`) e ainda não num job: o `sudo` e o `tar` da imagem padrão no
  volume, o tempo de download de um objeto de 34 MB contra o do prefixo expandido e o custo por
  arquivo de uma entrada de código expandida não foram medidos. Fecha com uma execução no alvo.
- **O `houseprice-etl` deixou medições por fazer no laboratório.** Pela CLI de CI/CD 1.0.9, entre
  dois projetos de uma conta, em 2026-10-15 e 2026-10-16 (`cicd-cli.md`): o `deploy` criou o
  workflow em cada projeto; a primeira execução parou no `glue:GetJob`, que a política do papel do
  projeto só autoriza sobre um job com a etiqueta do projeto; o job criado uma vez com o `job.json`
  fez as seguintes terminarem `SUCCESS`; o operador chamou `UpdateJob` em toda execução, pelo
  `Command` que o `GetJob` devolve com `PythonVersion`; e o `bundle` e o `deploy` no stage `test`
  rodaram. Não medidos: uma execução sem `UpdateJob`, com o `Command` inteiro em
  `create_job_kwargs`; se o job aparece em *Data processing jobs*, com as execuções e os logs; onde
  ficam os logs com o `--custom-logGroup-prefix` e se o projeto os lê; se as sub-redes das conexões
  de rede do job são as que `space_values.py` imprime, que o laboratório preencheu à mão nas
  variáveis de stage. O usuário escolheu como o job nasce num projeto em que não existe (2026-10-16
  05:50 UTC; `decisions.md`, "The examples as applications"): um `glue:GetJob` sobre os jobs sem
  etiqueta de projeto, aplicado no laboratório no mesmo dia e medido por uma execução que criou o
  job pelo operador (`cicd-cli.md`, "The Glue job in the lab"); no alvo, o statement está no
  pedido de mudança, sem aplicar, e os passos mantêm o `job.json` para um projeto sem o grant.
  Inferido, não medido: uma execução pelo portal de uma definição que referencia um parâmetro que
  ela não declara falha no render como pela CLI. Fecha com as outras execuções.
- **O `lint` promovido e o `lint-plan` numa esteira.** A cópia de um workflow da CLI para outra
  conta é do `scripts/render-workflow.py` do AWS-DataScience (decisão 20 (e) da etapa 10, do
  usuário em 2026-10-22), que corta as chaves com que o operador do Glue cria o job; o job de
  release de lá roda o `lint --promoted` em cada cópia, no commit `3c1708e`, lido de um laptop em
  2026-10-22 sobre o bundle `v0.2.1`: `ok: 1 arquivo(s)`, e uma imagem de outro repositório
  recusada. As regras (6) e (2c) da etapa 10 entraram em 2026-10-23 (`decisions.md`, "The Stage
  10 rules after Stage 18"; `docs/laboratorio.md`, "Regras de autoria"): a cópia renderizada
  com valores fabricados passa na regra (6), e o `lint-plan` leu planos de teste do Terraform
  1.15.8. Não medidos: os dois numa esteira, depois que o AWS-DataScience subir o pin do pacote e
  chamar o `lint-plan` sobre o plano do slice da aplicação no job de release; e o tempo de
  provisionamento e de encerramento de um job de processamento dentro dos 3.600 s da task, que
  decide a margem dos 2.820 s de `MaxRuntimeInSeconds`. Fecha com a primeira execução das pernas
  de promoção e com um job cronometrado.
- **A regra do job de treinamento espera.** A etapa 10 do AWS-DataScience especificou em
  2026-10-22 uma regra para o `config` de um `SageMakerTrainingOperator` (passo 5.1): `VpcConfig`,
  isolamento de rede, criptografia entre contêineres, as duas chaves KMS, o tipo de instância, a
  saída sob `models/<app>/`, os canais no bucket de saídas, `MaxRuntimeInSeconds` e
  `action_if_job_exists: fail`. O usuário a deixou fora do PR de 2026-10-23 (`decisions.md`, "The
  Stage 10 rules after Stage 18"): a cota de treinamento é 0 em Staging e Produção, a task vira
  um segundo workflow depois do aumento, e a imagem de um algoritmo nativo, uma tag no registro
  da AWS sem digest, é uma escolha em aberto do passo. Fecha com o aumento da cota e essa escolha.
- **Um `python_callable` pontuado para dentro do pacote** (`pacote.modulo.funcao`) não foi medido;
  a documentação recomenda um módulo de entrada na raiz. Fecha com uma task que o use.
- **A distribuição.** O pacote é instalado por git, porque o nome está livre no PyPI. Quando houver
  um índice próprio (o CodeArtifact do D14 do AWS-DataScience), o controle de origem do pacote
  bloqueia o upstream para este nome. Fecha com o índice.
