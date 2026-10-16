# demo-python-operator: uma task Python sobre o `.zip` do `package-task`

Um sensor espera um arquivo em `inbox/`, e uma task Python chama `demo_tasks.run`, que imprime
com o que o worker a roda e entrega o trabalho ao projeto [`awsds-demo-job`](../awsds-demo-job/):
cada objeto da caixa de entrada vira um resumo em JSON em `outbox/<carimbo>/`, e a origem é
apagada.

| Task | Operador | O que faz |
|---|---|---|
| `wait_for_file` | `S3KeySensor` | espera `inbox/?*`, a cada 30 s, por 10 minutos |
| `run_project` | `PythonOperator` | `demo_tasks.run`, com os URIs `inbox` e `outbox` como `op_kwargs` |

## Arquivos

| Arquivo | O que é |
|---|---|
| `demo-python-operator.yaml` | a definição, com placeholders |
| `extra_values.json` | o arquivo de valores extras: o prefixo do exemplo no bucket, `EXAMPLE_PREFIX` |
| `demo_tasks.py` | o módulo de entrada, com a função `run` |
| [`../awsds-demo-job/`](../awsds-demo-job/) | o projeto que o `.zip` leva, com o `petl` e o `six` |

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#demo-python-operator): o `.zip` e a
definição na máquina que empacota, a amostra em `inbox/` num espaço, o workflow no portal e o
hash do resultado.

## O que o log diz

```
python 3.12.14 em /opt/mwaa-serverless-venv/bin/python3
sys.path: [...]
credencial: arn:aws:sts::<conta>:assumed-role/<papel do projeto>/AmazonMWAAServerless
import petl: 1.7.28 de /usr/local/airflow/dags/petl/__init__.py
import six: <versão> de <caminho>
import yaml: 6.0.2 de /opt/mwaa-serverless-venv/lib64/python3.12/site-packages/yaml/__init__.py
sample.csv: 10 linhas -> s3://<bucket>/<domínio>/<projeto>/shared/exemplos/demo-python-operator/outbox/<carimbo>Z/sample.result.json; origem apagada
1 objeto(s) processado(s)
```

- O `petl` vem do `.zip`, em `/usr/local/airflow/dags`, e o PyYAML do worker: numa task
  Python, o pacote pré-instalado vence a cópia do `.zip`.
- O `six` está nos dois, o 1.16.0 no `.zip` e o 1.17.0 no worker. A linha dele diz qual venceu,
  e o `sys.path` diz por quê; nenhum dos dois foi lido numa task Python ainda.
- A credencial é o papel do projeto, na sessão `AmazonMWAAServerless`.

## Lido no ambiente alvo em 2026-10-12

Às 19:16 UTC, a primeira task Python sobre um `.zip` do `package-task`: o worker recebeu a
cópia do código em 0,1 s, imprimiu o Python 3.12.14, a credencial do papel do projeto, o `petl`
1.7.28 do `.zip` e o PyYAML 6.0.2 do worker, gravou `sample.result.json` e apagou a origem, em
2,44 s. O sha256 do resultado, lido num espaço, foi o do laboratório. O `.zip` daquele dia levava
só o `petl`, e o módulo imprimia em inglês; o desta pasta leva também o `six` e imprime o
`sys.path` e a origem do `six`, o que ainda não rodou.
