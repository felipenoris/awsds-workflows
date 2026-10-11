# Referências

Este arquivo lista os sites consultados na pesquisa que levou ao pacote e à documentação em
`docs/index.md`, agrupados por assunto. As páginas da AWS foram lidas para o runbook do
AWS-DataScience, nas datas que o `docs/REFERENCES.md` de lá registra, e são as fontes dos fatos que o
pacote repete.

## Projetos de referência

- O runbook de que o pacote saiu:
  <https://github.com/felipenoris/AWS-DataScience/blob/main/docs/plan/runbooks/serverless-workflows.md>
- As regras do repositório e o molde da documentação e da CI: <https://github.com/felipenoris/serialize-db>

## MWAA Serverless

- O que é o MWAA Serverless:
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/what-is-mwaa-serverless.html>
- Os operadores Python e Bash: o `Code`, os limites, o worker, os pacotes pré-instalados e a pasta
  `/usr/local/airflow/dags` (lido em 2026-10-10 e 2026-10-11):
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/operators-python-bash-detail.html>
- Os operadores suportados, e o histórico do guia que data a chegada dos operadores Python e Bash em
  2026-08-17: <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/operators.html> e
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/doc-history.html>
- Os parâmetros do Airflow suportados, os limites de `retries`, `retry_delay` e
  `execution_timeout` e os ignorados:
  <https://docs.aws.amazon.com/mwaa/latest/mwaa-serverless-userguide/supported-airflow-parameters.html>
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
  receita de dependências sem opção de plataforma (relido em 2026-10-11):
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/serverless-visual-workflows.html>
- A orquestração de workflows no SageMaker Unified Studio:
  <https://docs.aws.amazon.com/sagemaker-unified-studio/latest/userguide/workflow-orchestration.html>
- As entradas e as saídas de um job de processamento, sob `/opt/ml/processing/`:
  <https://docs.aws.amazon.com/sagemaker/latest/dg/byoc-input-and-output.html>

## Ferramentas Python

- O `uv`: <https://docs.astral.sh/uv/>
- O `pdoc`: <https://pdoc.dev/>
- A API JSON do PyPI, consultada em 2026-10-11 para saber se os nomes candidatos estavam livres
  (todos responderam 404): <https://pypi.org/pypi/awsds-workflows/json>
