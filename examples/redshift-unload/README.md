# redshift-unload: uma task Python que descarrega uma consulta no S3

Uma task Python, sem sensor, chama `redshift_unload.unload`, que roda três comandos numa sessão
da Data API do Redshift Serverless, com as credenciais do worker:

1. `SELECT current_user`, que imprime o usuário do banco com que o worker entrou;
2. o `UNLOAD` da consulta para o S3, em Parquet, com manifesto verboso;
3. `SELECT pg_last_unload_count()`, que dá o número de linhas, o que a task devolve.

Um namespace sem papel IAM não aceita `IAM_ROLE` no `UNLOAD`, então o comando leva no próprio
texto as credenciais temporárias do worker. A função não imprime esse texto, e uma mensagem de
erro passa por uma máscara antes de sair. O módulo só usa o `boto3` que o worker já traz.

| Task | Operador | O que faz |
|---|---|---|
| `unload` | `PythonOperator` | `redshift_unload.unload`, com `select`, `destination`, `workgroup` e `database` como `op_kwargs` |

## Arquivos

| Arquivo | O que é |
|---|---|
| `redshift-unload.yaml` | a definição, com placeholders |
| `redshift_unload.py` | o módulo da task, que vai sozinho no `.zip` |

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#redshift-unload): o `valores-redshift.json`,
o acesso do usuário do projeto ao banco do datashare, o `.zip` com o módulo na raiz, a definição
com os dois arquivos de valores, o workflow no portal e onde ler o resultado.

## Falhas

| A task diz | O que fazer |
|---|---|
| `permission denied` ou `does not exist` sobre a tabela | dê ao usuário do banco impresso no log a leitura da tabela, ou troque a tabela |
| `Permission denied to query database created from datashare` | o usuário do banco não tem acesso ao banco do datashare: o `GRANT` está na [página dos passos](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#redshift-unload) |
| `S3ServiceException` com `Access Denied` | o papel do projeto não grava nesse prefixo, ou não usa a chave KMS do bucket |
| `unload destination on S3 is not empty` | o destino precisa estar vazio; cada execução usa a data e a hora |
| `NoRegionError` ou `Could not connect to the endpoint URL` | o worker não achou a região ou o endpoint `redshift-data` |

## Conferência

`tests/test_examples.py` roda o módulo contra o `Stubber` do `botocore`, que valida os
parâmetros das três chamadas contra o modelo da Data API, e confere o escape da consulta e a
máscara das credenciais numa falha, sem rede e com credenciais fabricadas.

No ambiente alvo, em 2026-10-13, a função rodou no espaço: 101 linhas em 5,5 s, um `.parquet` e
o `manifest`. No workflow, ela parou na permissão do banco do datashare, antes de gravar no S3.
Depois do `GRANT USAGE`, o workflow descarregou as mesmas 101 linhas em 5,5 s, numa task de
23,4 s, às 02:22 UTC. A pasta de destino levou a hora da execução, `20261013T022213`, e não a
meia-noite da data lógica.
