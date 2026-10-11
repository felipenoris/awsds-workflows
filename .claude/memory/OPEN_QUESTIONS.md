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
- **A rede do alvo para um workflow.** As leituras do serialize-db a partir de um space do alvo
  (2026-09-21 e 2026-09-23) acharam o endpoint de gateway do S3 e endpoints de interface para STS,
  Redshift, Glue, Athena, Secrets Manager e DataZone; SageMaker, KMS, IAM, Lake Formation e S3
  Tables resolveram para endereços públicos e não responderam. No laboratório, o operador de
  processamento chama `CreateProcessingJob` pelo endpoint `sagemaker.api`, e o worker grava o log
  pelo endpoint `logs` (2026-10-11). Se o worker do alvo usar a mesma rede do space, uma task de
  processamento não alcança o `CreateProcessingJob`, e o `logs` não foi testado. Fecha com a
  primeira execução de um workflow no alvo.
- **A SageMaker Distribution 4.15 como imagem do job.** Não medidos: o URI da imagem para um job de
  processamento no alvo (`JOB_IMAGE_URI`), a versão do Python de `/opt/conda/bin/python` (o space
  do alvo leu 3.12.14 em `/opt/conda` em 2026-09-21, antes da 4.15), o usuário do contêiner e o
  `sudo` que o `chown` da pasta de saída usa. Fecha com um space na imagem (`--version`, `id`,
  `ldd --version`) e o primeiro job.
- **O `scripts/space_values.py` num espaço do alvo.** O script não rodou num espaço. Não lidos: o
  arquivo de metadados de um espaço real (o separador de `PrivateSubnets` e de `SecurityGroup`, que
  só aparecem nos dados de teste do SDK `sagemaker-studio`, e a presença de `DataZoneEndpoint`); se
  o `DataZoneEnvironmentId` do espaço é o ambiente Tooling, o que tem o `kmsKeyArn`; o
  `GetEnvironment` com as credenciais do espaço no alvo, que não tem `~/.aws/config`; e o nome
  `datazone.sa-east-1.api.aws`, que o `boto3` chama sem `DataZoneEndpoint`, enquanto o probe do
  alvo resolveu `datazone.sa-east-1.amazonaws.com`. Fecha com o que o script imprime num espaço do
  alvo.
- **Nenhum `.zip` de `package-task` rodou num worker.** No laboratório, um `.zip` montado pela
  receita à mão rodou numa task Python em 2026-10-11, depois que a política do endpoint de gateway
  do S3 passou a admitir `mwaa-serverless-code-files-*-<região>-prod`, o bucket da cópia que o
  serviço guarda (`environments.md`). No alvo, a política do endpoint de gateway não foi lida.
  Fecha com um `.zip` do `package-task` numa execução, e com a política lida no alvo.
- **Uma task Bash sobre um `.zip`.** Só comandos inline rodaram no worker (2026-10-11). Não
  medidos: a pasta de trabalho de um script, que o guia diz ser `/usr/local/airflow/dags`, quando
  um comando inline rodou numa pasta temporária; um `bash_command` terminado em `.sh`, que o
  Airflow lê como template; o bit de execução depois da extração, que o `.zip` do `package-task`
  guarda e o `zipfile` do Python descarta; onde o worker põe um `Code` que é um `.py` ou um `.sh`
  sozinho; se um pacote do `.zip` vence o do worker num `python3 -m` rodado em
  `/usr/local/airflow/dags`; e o `env` sem `append_env`. Fecha com uma task Bash sobre um `.zip` do
  `package-task` com `--include` que imprima cada um.
- **Um `python_callable` pontuado para dentro do pacote** (`pacote.modulo.funcao`) não foi medido;
  a documentação recomenda um módulo de entrada na raiz. Fecha com uma task que o use.
- **O AWS-DataScience passar a usar o pacote.** O runbook e os exemplos de lá chamam os scripts, com
  os placeholders antigos (`SANDBOX_ACCOUNT_ID`, `REGISTRY_ACCOUNT_ID`, `IMAGE_DIGEST`,
  `DEMO_PREFIX`) e as mensagens em inglês nas tabelas de recusa. Fecha com a decisão do usuário e um
  PR naquele repositório.
- **O GitHub Pages do repositório.** O `docs.yml` falha em `actions/configure-pages` até a origem do
  Pages ser "GitHub Actions" (Settings, Pages, Build and deployment). Fecha quando o usuário
  configurar, antes do primeiro push na `main` com o workflow.
- **A distribuição.** O pacote é instalado por git, porque o nome está livre no PyPI. Quando houver
  um índice próprio (o CodeArtifact do D14 do AWS-DataScience), o controle de origem do pacote
  bloqueia o upstream para este nome. Fecha com o índice.
