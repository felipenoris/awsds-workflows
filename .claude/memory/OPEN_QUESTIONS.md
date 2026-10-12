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
- **O `scripts/space_values.py` num espaço do alvo.** No laboratório, em 2026-10-11, o script
  imprimiu o mesmo JSON que o `values` na mesma conta. Num espaço do alvo, em 2026-10-12, achou o
  ambiente Tooling com `userRoleArn`, `securityGroup`, `privateSubnets` e `s3BucketPath`, sem
  `kmsKeyArn`, e parou; desde então o JSON sai sem `PROJECT_KEY_ID` (`environments.md`, "The
  project space"). Não lidos lá: os valores e a ordem das sub-redes, que no laboratório é a das
  zonas. Fecha com o JSON que o script imprime num espaço do alvo.
- **O papel do projeto no alvo e o operador de processamento.** A política do blueprint
  `SageMakerStudioProjectRoleMachineLearningPolicy` v42, lida em 2026-10-12, só deixa descrever um
  job com a etiqueta `AmazonDataZoneProject` do chamador e tira as chaves `AmazonDataZone*` do
  `AddTags`, as duas recusas que o laboratório mediu em 2026-10-10; o operador do provedor Amazon
  do Airflow (9.37.0) sempre descreve o nome antes de criar o job. Não lidos no alvo: as políticas
  do papel do projeto e se a política de `docs/index.md` ("A permissão do projeto") pode ser
  anexada lá. Fecha com a primeira execução do operador no alvo.
- **Nenhum `.zip` de `package-task` rodou num worker.** No laboratório, `.zip` montados à mão
  rodaram numa task Python e numa task Bash em 2026-10-11, depois que a política do endpoint de
  gateway do S3 passou a admitir `mwaa-serverless-code-files-*-<região>-prod`, o bucket da cópia
  que o serviço guarda (`environments.md`). No alvo, a política do endpoint de gateway não foi lida.
  Fecha com um `.zip` do `package-task` numa execução, e com a política lida no alvo.
- **Nenhuma pasta do `package-job` rodou num job, e o pacote não rodou num space.** No laboratório,
  uma pasta gravada num space pelo script do AWS-DataScience, com os mesmos passos do `uv`, rodou
  num job em 2026-10-11, e o `package-job` gravou a mesma pasta num space simulado, com o
  `UV_PYTHON` apontando o 3.13 da imagem (`packaging.md`, "The interpreter `uv` needs"). Não
  medidos num space de verdade: o `uv tool install` do pacote no Python da distribuição, a recusa
  sem o `UV_PYTHON` e a pasta com ele. Fecha com o `package-job` rodado num space do laboratório e
  a pasta dele num job.
- **Uma task Bash sobre um `.zip`.** Um `.zip` montado à mão rodou numa task Bash em 2026-10-11:
  um módulo com `python3 -m`, depois de um `cd /usr/local/airflow/dags`, e um script chamado pelo
  nome, que o worker renderizou numa cópia temporária (`environments.md`; `docs/index.md`, "O
  código do `.zip` no comando"). Não medidos: um script chamado pelo caminho inteiro e a pasta
  de trabalho dele; o `python3 -m` sem o `cd`, que o `PYTHONPATH` lido sugere; se um pacote do
  `.zip` vence o do worker com o mesmo nome; o bit de execução depois da extração, que o `.zip` do
  `package-task` guarda e o `zipfile` do Python descarta; onde o worker põe um `Code` que é um
  `.py` ou um `.sh` sozinho; e o `env` sem `append_env`. Fecha com uma task Bash sobre um `.zip`
  do `package-task` com `--include` que imprima cada um.
- **Um `python_callable` pontuado para dentro do pacote** (`pacote.modulo.funcao`) não foi medido;
  a documentação recomenda um módulo de entrada na raiz. Fecha com uma task que o use.
- **A distribuição.** O pacote é instalado por git, porque o nome está livre no PyPI. Quando houver
  um índice próprio (o CodeArtifact do D14 do AWS-DataScience), o controle de origem do pacote
  bloqueia o upstream para este nome. Fecha com o índice.
