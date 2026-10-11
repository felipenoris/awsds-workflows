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
- **Nenhum `.zip` de `package-task` rodou num worker.** No laboratório, o worker de um workflow com
  `Code` falha ao preparar o ambiente, e a leitura, não medida, é que a política do endpoint de
  gateway do S3 recusa o bucket do serviço (decisão 7 do Stage 6i do AWS-DataScience, aberta). No
  alvo, a política do endpoint de gateway não foi lida. Fecha com a decisão 7 aplicada e uma
  execução.
- **A precedência no worker.** O guia diz que um pacote pré-instalado vence a cópia do `.zip`
  (verificação viii do Stage 6i do AWS-DataScience, não medida); `WORKER_PROVIDED` poda esses
  pacotes por isso. Fecha com uma task que imprime o `__file__` do `boto3`.
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
