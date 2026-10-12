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
- **As escolhas do `compare` esperam o usuário.** A lista está em `decisions.md`, "The comparison
  of definitions": o nome, a entrada por caminho, as linhas `-` e `+` com o valor em JSON, o tipo
  na comparação, as listas por posição e a saída 0 com ou sem diferenças. Fecha com a resposta do
  usuário no PR #7.
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
- **O `scripts/space_values.py` num espaço do alvo.** O script rodou num espaço do laboratório em
  2026-10-11 e imprimiu o mesmo JSON que o `values` na mesma conta (`environments.md`, "The project
  space"); no alvo, onde o `Project()` funciona (o usuário, 2026-10-11), não rodou. Não
  lidos lá: o ambiente Tooling padrão que o SDK `sagemaker-studio` acha (o blueprint `Tooling` ou
  `ToolingLite`, ou a conexão IAM), os recursos `userRoleArn`, `securityGroup`, `privateSubnets`,
  `kmsKeyArn` e `s3BucketPath` dele, e a ordem das sub-redes, que no laboratório é a das zonas.
  Fecha com o que o script imprime num espaço do alvo.
- **Nenhum `.zip` de `package-task` rodou num worker.** No laboratório, um `.zip` montado pela
  receita à mão rodou numa task Python em 2026-10-11, depois que a política do endpoint de gateway
  do S3 passou a admitir `mwaa-serverless-code-files-*-<região>-prod`, o bucket da cópia que o
  serviço guarda (`environments.md`). No alvo, a política do endpoint de gateway não foi lida.
  Fecha com um `.zip` do `package-task` numa execução, e com a política lida no alvo.
- **Nenhuma pasta do `package-job` rodou num job, e o pacote não rodou num space.** No laboratório,
  uma pasta gravada num space pelo script do AWS-DataScience, com os mesmos passos do `uv`, rodou
  num job em 2026-10-11, e o `package-job` gravou a mesma pasta num space simulado, com o
  `UV_PYTHON` apontando o 3.13 da imagem (`packaging.md`, "The interpreter `uv` needs"). Não
  medidos num space de verdade: o `uv tool install` do pacote no Python da distribuição, a recusa
  sem o `UV_PYTHON` e a pasta com ele. Fecha com o `package-job` rodado num space do laboratório e
  a pasta dele num job.
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
- **A distribuição.** O pacote é instalado por git, porque o nome está livre no PyPI. Quando houver
  um índice próprio (o CodeArtifact do D14 do AWS-DataScience), o controle de origem do pacote
  bloqueia o upstream para este nome. Fecha com o índice.
