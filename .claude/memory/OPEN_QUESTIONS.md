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
  `docs/index.md` como runbook. Fecha com a resposta do usuário no PR.
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
- **A imagem padrão do alvo como imagem do job.** O usuário a chamou de SageMaker Distribution 4.15
  (2026-10-11), e as tags públicas da distribuição vão até a 4.5.2, sem 4.15 (lidas em 2026-10-12).
  Num espaço do alvo, em 2026-10-12, `/opt/conda/bin/python` era o CPython 3.12.14, como em
  2026-09-21, o usuário `sagemaker-user` (uid 1000, gid 100) tinha `sudo` sem senha, e o parâmetro
  público do SSM deu a conta do repositório `sagemaker-distribution-prod` da região
  (`environments.md`, "The target"). A primeira definição do alvo usa
  `sagemaker-distribution-prod:4.5.2-cpu`. Não medidos: a versão que o espaço roda, o pull dessa
  imagem por um job, e o usuário e o `sudo` dentro do job, que o `chown` da pasta de saída usa.
  Fecha com a resposta do usuário e o primeiro job.
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
  `UV_PYTHON` apontando o 3.13 da imagem (`packaging.md`, "The interpreter `uv` needs"). Não
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
- **Um `python_callable` pontuado para dentro do pacote** (`pacote.modulo.funcao`) não foi medido;
  a documentação recomenda um módulo de entrada na raiz. Fecha com uma task que o use.
- **A distribuição.** O pacote é instalado por git, porque o nome está livre no PyPI. Quando houver
  um índice próprio (o CodeArtifact do D14 do AWS-DataScience), o controle de origem do pacote
  bloqueia o upstream para este nome. Fecha com o índice.
