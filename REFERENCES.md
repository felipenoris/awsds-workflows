# Referências

Este arquivo lista os sites consultados na pesquisa que levou ao pacote e à documentação em
`docs/index.md`, agrupados por assunto. As páginas da AWS foram lidas para o runbook do
AWS-DataScience, nas datas que o `docs/REFERENCES.md` de lá registra, e são as fontes dos fatos que o
pacote repete.

## Projetos de referência

- O runbook de que o pacote saiu:
  <https://github.com/felipenoris/AWS-DataScience/blob/main/docs/plan/runbooks/serverless-workflows.md>
- As regras do repositório e o molde da documentação e da CI: <https://github.com/felipenoris/serialize-db>
- O PR #110 do AWS-DataScience, fonte das leituras de 2026-10-11 sobre o job com dependências e o
  `uv` num space (lido em 2026-10-11): <https://github.com/felipenoris/AWS-DataScience/pull/110>
- O log da etapa 6i do AWS-DataScience, fonte das leituras de 2026-10-11 sobre a task Bash com um
  `.zip`, o worker de cada task e a cópia do código a cada save (lido em 2026-10-12):
  <https://github.com/felipenoris/AWS-DataScience/blob/main/docs/log/log-stage-06i-sandbox-orchestration.md>
- Os exemplos do AWS-DataScience, com o `compare` das definições que o portal salvou (lido em
  2026-10-12):
  <https://github.com/felipenoris/AWS-DataScience/blob/main/examples/sandbox-orchestration/README.md>

## MWAA Serverless

- O que é o MWAA Serverless:
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/what-is-mwaa-serverless.html>
- Os operadores Python e Bash: o `Code`, os limites, o worker, os pacotes pré-instalados, a pasta
  `/usr/local/airflow/dags` e a frase de que um script do `BashOperator` roda nela (lido em
  2026-10-10 e 2026-10-11):
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/operators-python-bash-detail.html>
- Os operadores suportados, e o histórico do guia que data a chegada dos operadores Python e Bash em
  2026-08-17: <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/operators.html> e
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/doc-history.html>; a versão em
  Markdown da página, com a lista inteira, 199 classes do provedor Amazon por área mais o
  `PythonOperator` e o `BashOperator`, lida em 2026-10-16 para a regra `operador` do `lint`:
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/operators.md>
- Os parâmetros do Airflow suportados, os limites de `retries`, `retry_delay` e
  `execution_timeout` e os ignorados (lida de novo em 2026-10-16, para a regra `limites` do
  `lint`: `retries` de 0 a 3, `retry_delay` de 0 a 300 s, `execution_timeout` até 3.600 s,
  `start_date` "must be in the future"):
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/supported-airflow-parameters.html>
- As cotas do MWAA Serverless na AWS, com os 50 KB de uma definição, as 50 versões por workflow e os
  60 minutos de uma task (lida em 2026-10-16):
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/mwaa-serverless-quotas.html>
- As cotas do MWAA Serverless numa página fora da AWS, com o *Maximum task execution timeout* de 60
  minutos, ajustável (lida em 2026-10-12):
  <https://www.awsfundamentals.com/limits/airflow-serverless>
- A skill *authoring-mwaa-workflow* do *agent toolkit* da AWS, que lista o erro *Operator not found
  in Serverless: not allowlisted* para um operador fora da lista (lida em 2026-10-12):
  <https://tessl.io/registry/skills/github/aws/agent-toolkit-for-aws/authoring-mwaa-workflow>
- A rede do worker:
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/networking.html> e
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/networking-vpc.html>
- O formato da definição: o MWAA Serverless recebe um YAML, valida-o antes de executar e aceita
  Jinja2, sem publicar um esquema; a seção "YAML support" dos conceitos (lido em 2026-10-11):
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/mwaas-concepts.html>
- O conversor de DAGs Python para YAML da AWS, que escreve "dag-factory compatible Dags" e se diz
  compatível com o DagFactory 1.0 (lido em 2026-10-11):
  <https://github.com/awslabs/python-to-yaml-dag-converter-mwaa-serverless>
- O dag-factory, a biblioteca da Astronomer (Apache-2.0, fora do projeto Apache Airflow) que
  constrói DAGs do Airflow a partir de YAML; o worker traz a 1.0.0 (lido em 2026-10-11):
  <https://github.com/astronomer/dag-factory>

## SageMaker Unified Studio e SageMaker

- Os workflows visuais serverless: o editor, o envio dos arquivos dos operadores Python e Bash e a
  receita de dependências sem opção de plataforma (relido em 2026-10-11). As leituras da mesma
  página entre 21:30 e 22:10 UTC daquele dia não acharam o texto dos operadores:
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/serverless-visual-workflows.html>
- O anúncio dos operadores Python e Bash nos workflows do SageMaker Unified Studio, de 2026-09-03
  (lido em 2026-10-11):
  <https://aws.amazon.com/about-aws/whats-new/2026/09/sagemaker-workflows-python-bash/>
- A orquestração de workflows no SageMaker Unified Studio:
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/workflow-orchestration.html>
- As entradas e as saídas de um job de processamento, sob `/opt/ml/processing/`:
  <https://docs.aws.amazon.com/sagemaker/latest/dg/byoc-input-and-output.html>
- O arquivo de metadados de um espaço, `/opt/ml/metadata/resource-metadata.json`, que a página
  descreve só pelo `ProjectS3Path` (lido em 2026-10-11):
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/accessing-metadata.html>
- O SDK `sagemaker-studio`, cujo código 1.1.35 dá o `Project()`, o ambiente Tooling padrão e os
  recursos dele, os nomes dos campos desse arquivo e o endpoint do DataZone; a API JSON do PyPI e as
  rodas 1.1.35 e 1.1.32 (lidas em 2026-10-11). A 1.1.35 foi relida em 2026-10-12 no
  `RemoteExecutionClient`, que cria o job sem chave quando o ambiente não tem `kmsKeyArn` e monta o
  URI da SageMaker Distribution pelo parâmetro público do SSM
  `/aws/service/sagemaker-distribution/ecr-account-id`:
  <https://pypi.org/pypi/sagemaker-studio/json>,
  <https://files.pythonhosted.org/packages/bb/aa/c2c4a60ff70a46b673a0cfb73e38f1552619cc35e5c9e7b939e1f18befdf/sagemaker_studio-1.1.35-py3-none-any.whl>
  e
  <https://files.pythonhosted.org/packages/5c/93/60f4e17498ae65299197ad408986dc265ead855539948f0d7301bb64a46f/sagemaker_studio-1.1.32-py3-none-any.whl>
- A política gerenciada do papel do projeto, `SageMakerStudioProjectUserRolePolicy` v75, com o
  `datazone:GetProject`, o `ListConnections`, o `GetEnvironment`, as listagens de ambientes e de
  blueprints, o `iam:GetRole` e os `ec2:Describe*` (lida em 2026-10-11, e relida em 2026-10-12 sem
  nenhuma ação `sagemaker:` e com o `AllowPassRoleOnProjectRoles`, o `iam:PassRole` do próprio papel
  para o `sagemaker.amazonaws.com`; relida em 2026-10-14 nas ações do Glue: o `CreateJob` só com
  a etiqueta `AmazonDataZoneProject` do chamador e com chaves `AmazonDataZone*` e
  `ProjectUserTag*`, a remoção só de etiquetas `ProjectUserTag*`, o `PassConnection` das conexões
  com a etiqueta do projeto e a leitura de logs só sob o grupo do projeto):
  <https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SageMakerStudioProjectUserRolePolicy.html>
  e a página dela no guia do administrador:
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/adminguide/security-iam-awsmanpol-SageMakerStudioProjectUserRolePolicy.html>
- A política gerenciada de aprendizado de máquina do papel do projeto,
  `SageMakerStudioProjectRoleMachineLearningPolicy` v42: o `CreateProcessingJob` e o
  `DescribeProcessingJob` só com a etiqueta `AmazonDataZoneProject` do chamador e o `AddTags` sem
  as chaves `AmazonDataZone*`, o `ListProcessingJobs` só com a etiqueta
  `EnableSageMakerMLWorkloadsPermissions` do papel, e o ECR e os logs sem condição de projeto (lida
  em 2026-10-12):
  <https://docs.aws.amazon.com/aws-managed-policy/latest/reference/SageMakerStudioProjectRoleMachineLearningPolicy.html>
- O `VolumeKmsKeyId` e o `KmsKeyId` da saída de um job de processamento, opcionais, sem dizer o
  que cifra o volume e a saída sem eles (lidos em 2026-10-12):
  <https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingClusterConfig.html> e
  <https://docs.aws.amazon.com/sagemaker/latest/APIReference/API_ProcessingOutputConfig.html>
- As tags da SageMaker Distribution no ECR público, que vão até a 4.5.2, lidas em 2026-10-12 com o
  token anônimo: <https://public.ecr.aws/token/> e
  <https://public.ecr.aws/v2/sagemaker/sagemaker-distribution/tags/list>
- A política de suporte das imagens do Studio, com o ritmo da SageMaker Distribution: uma versão
  maior a cada seis meses e menores mensais (lida em 2026-10-12, e relida em 2026-10-13 sem uma
  tabela de URIs por região):
  <https://docs.aws.amazon.com/sagemaker/latest/dg/sagemaker-distribution.html>
- Os caminhos de registro das imagens de algoritmos do SageMaker, por região, que não listam a
  SageMaker Distribution, cuja conta vem do parâmetro público do SSM (lida em 2026-10-13):
  <https://docs.aws.amazon.com/sagemaker/latest/dg-ecr-paths/sagemaker-algo-docker-registry-paths.html>
- Os espaços de código de um domínio IAM do SageMaker Unified Studio, cuja escolha de imagem dá o
  exemplo "SageMaker Distribution 2.11" (lida em 2026-10-12):
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/code-spaces-iam.html>
- Os blueprints customizados, que nomeiam os parâmetros `privateSubnets` e `s3BucketArn` e nada do
  arquivo de metadados (lido em 2026-10-11):
  <https://aws.amazon.com/blogs/big-data/tailor-amazon-sagemaker-unified-studio-project-environments-to-your-needs-using-custom-blueprints/>
- O provedor de credenciais do SageMaker Unified Studio no driver JDBC do Athena, com os mesmos
  nomes `DataZoneDomainId`, `DataZoneEnvironmentId`, `DataZoneDomainRegion` e um
  `DataZoneEndpointOverride` (lido em 2026-10-11):
  <https://docs.aws.amazon.com/athena/latest/ug/jdbc-v3-driver-datazone-iamcp.md>
- Os endpoints de interface do DataZone, numa página que não nomeia o serviço nem os nomes DNS
  privados (lida em 2026-10-11):
  <https://docs.aws.amazon.com/datazone/latest/userguide/datazone-vpc.html>
- Os conceitos do CI/CD do SageMaker Unified Studio: o manifest, fonte única da aplicação, os
  stages, um projeto cada, o bundle imutável e o deploy que o leva aos stages seguintes (lido em
  2026-10-14):
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/cicd-key-concepts.html>
- A CLI de CI/CD `aws-smus-cicd-cli` 1.0.9, lida no código do pacote e do repositório
  (`3418ae1`, 2026-10-05) em 2026-10-14: os tipos de conteúdo, sem um para o job do Glue, as
  variáveis `{proj.*}` e `{domain.*}` do workflow, a substituição `${VAR}` do manifest, o nome do
  workflow implantado e a skill `generate-bundle-manifest`, que leva o script de um job em
  `content.storage` e o cria com um `GlueJobOperator`:
  <https://pypi.org/project/aws-smus-cicd-cli/> e
  <https://github.com/aws/CICD-for-SageMakerUnifiedStudio>
- Os jobs de processamento de dados e a página *Data processing jobs*, com um job do Visual ETL ou
  de código (lido em 2026-10-14):
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/smus-creating-jobs.html>
- Um job do Visual ETL: os nós, o modo de permissão `project.spark.compatibility` e o *Save to
  project*, sem dizer onde ficam os arquivos nem que o save cria um job do Glue (lido em
  2026-10-14):
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/getting-started-visual-etl.html>
- O anúncio dos jobs no SageMaker, de 2025-07-15, com um fluxo do Visual ETL salvo como job
  (lido em 2026-10-14):
  <https://aws.amazon.com/blogs/big-data/introducing-jobs-in-amazon-sagemaker>
- As transformações visuais customizadas do Visual ETL, num artigo de 2026-07-26 (lido em
  2026-10-14):
  <https://dev.classmethod.jp/en/articles/20260726-amazon-smus-custom-visual-transform/>

## AWS Glue

- O Glue 6.0, com o Spark 4.1 e o Python 3.13, num anúncio de 2026-08-21 (lido em 2026-10-14):
  <https://aws.amazon.com/about-aws/whats-new/2026/08/aws-glue-6-0-price-reduction-iceberg-v3/>
- A migração para o Glue 6.0, em que o `getResolvedOptions` não aceita mais um prefixo do nome
  do argumento (lido em 2026-10-14):
  <https://docs.aws.amazon.com/glue/latest/dg/migrating-version-60.html>
- Os exemplos de política do Glue, cujo exemplo de etiqueta é de um gatilho e não de um job
  (lido em 2026-10-14):
  <https://docs.aws.amazon.com/glue/latest/dg/security_iam_id-based-policy-examples.html>
- A resposta do suporte da AWS de que o editor visual não aceita parâmetros nos nós de origem e de
  destino do S3 (lida em 2026-10-14):
  <https://repost.aws/questions/QUb7gn8piCTmqTJPQa-SnOmw/how-to-parameterize-aws-glue-studio-job-s3-source-and-s3-target>
- O `getResolvedOptions` do `aws-glue-libs`, lido no código em 2026-10-14 e usado nos testes do
  script do `houseprice-etl` no PySpark 4.1.1:
  <https://raw.githubusercontent.com/awslabs/aws-glue-libs/master/awsglue/utils.py> e
  <https://raw.githubusercontent.com/awslabs/aws-glue-libs/master/awsglue/job.py>

## Apache Airflow

- O `BashOperator` e o `SubprocessHook` do `apache-airflow-providers-standard`, lidos no código dos
  wheels 1.6.0 e 1.20.0 em 2026-10-11: o `template_ext`, o `bash -c`, a pasta temporária, o `env`
  e o `append_env` e os códigos de saída; o 1.6.0 relido em 2026-10-12, no `_is_inline_command`.
  A API JSON do PyPI deu os endereços dos wheels:
  <https://pypi.org/pypi/apache-airflow-providers-standard/1.6.0/json> e
  <https://pypi.org/pypi/apache-airflow-providers-standard/json>
- As constraints do Airflow 3.0.6 para o Python 3.12, que fixam o
  `apache-airflow-providers-standard` 1.6.0 (lido em 2026-10-11), o `python-dateutil` 2.9.0.post0
  e o `six` 1.17.0 (lidos em 2026-10-12), relidas em 2026-10-14 para instalar o Airflow do worker
  num ambiente temporário:
  <https://raw.githubusercontent.com/apache/airflow/constraints-3.0.6/constraints-3.12.txt>
- A dependência do Airflow no `six`, lida na API JSON do PyPI em 2026-10-12: o
  `apache-airflow-core` 3.0.6 pede o `python-dateutil`, e o `python-dateutil` 2.9.0.post0 pede o
  `six`: <https://pypi.org/pypi/apache-airflow-core/3.0.6/json> e
  <https://pypi.org/pypi/python-dateutil/2.9.0.post0/json>
- O `SageMakerProcessingOperator` do `apache-airflow-providers-amazon` 9.37.0, lido no código do
  wheel em 2026-10-12: o nome do job é descrito antes da criação, e só uma `ValidationException`
  conta como job ausente: <https://pypi.org/project/apache-airflow-providers-amazon/9.37.0/>
- O `GlueJobOperator` e o `GlueJobHook` do `apache-airflow-providers-amazon` 9.32.0, o do worker,
  lidos no código do wheel e rodados contra o `moto` em 2026-10-14: o `update_config`, o
  `create_job_kwargs`, o `iam_role_arn`, a consulta do estado a cada 6 s e as linhas do log:
  <https://pypi.org/project/apache-airflow-providers-amazon/9.32.0/>

## Ferramentas Python

- O `uv`: <https://docs.astral.sh/uv/>
- O Terraform 1.16.5 e os providers `hashicorp/aws` 5.100.0 e `hashicorp/time` 0.14.2 e 0.14.0, a
  versão que o lock do Terraform do alvo fixa, baixados com as somas SHA-256 em 2026-10-12 para
  validar as cópias ajustadas do Terraform do ambiente alvo:
  <https://releases.hashicorp.com/terraform/1.16.5/>,
  <https://releases.hashicorp.com/terraform-provider-aws/5.100.0/>,
  <https://releases.hashicorp.com/terraform-provider-time/0.14.2/> e
  <https://releases.hashicorp.com/terraform-provider-time/0.14.0/>
- O botocore 1.43.111, num ambiente temporário em 2026-10-12, que chama a API do SageMaker em
  `https://api.sagemaker.sa-east-1.amazonaws.com`: <https://pypi.org/project/botocore/1.43.111/>
- O `pdoc`: <https://pdoc.dev/>
- O exemplo `dark-mode` do pdoc 16.0.0, lido em 2026-10-12, de onde vêm as cores escuras do
  `theme.css` de `docs/theme/` e o estilo `monokai` do destaque do código:
  <https://raw.githubusercontent.com/mitmproxy/pdoc/v16.0.0/examples/dark-mode/README.md>,
  <https://raw.githubusercontent.com/mitmproxy/pdoc/v16.0.0/examples/dark-mode/theme.css> e
  <https://raw.githubusercontent.com/mitmproxy/pdoc/v16.0.0/examples/dark-mode/syntax-highlighting.css>
- A API JSON do PyPI, consultada em 2026-10-11 para saber se os nomes candidatos estavam livres
  (todos responderam 404): <https://pypi.org/pypi/awsds-workflows/json>
