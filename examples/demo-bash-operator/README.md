# demo-bash-operator: uma task Bash sobre o `.zip`, com scripts

Um sensor espera um arquivo em `inbox/`; `run_command` roda o modo S3 do projeto
[`awsds-demo-job`](../awsds-demo-job/) com `python3 -m`, a partir do `.zip`; `reach_pypi` roda
o script `reach_pypi.sh` do `.zip`, que tenta a PyPI e falha, porque o worker não tem internet;
e `probe_bash`, sem dependência, imprime como o worker roda um script e um módulo do `.zip`.

| Task | Operador | O que faz |
|---|---|---|
| `wait_for_file` | `S3KeySensor` | espera `inbox/?*`, a cada 30 s, por 10 minutos |
| `run_command` | `BashOperator` | `cd /usr/local/airflow/dags && python3 -m awsds_demo_job.s3 --bucket ... --inbox ... --outbox ...` |
| `reach_pypi` | `BashOperator` | `reach_pypi.sh`, depois de `run_command`; termina com 1 quando nada respondeu, o esperado, e a execução termina `FAILED` |
| `probe_bash` | `BashOperator` | inline: a pasta de trabalho, o `PYTHONPATH`, os modos dos arquivos extraídos, o `python3 -m` sem `cd`, de onde vêm o `petl` e o `six`, e `probe.sh` pelo caminho inteiro e executado direto |

## Arquivos

| Arquivo | O que é |
|---|---|
| `demo-bash-operator.yaml` | a definição, com placeholders |
| `probe.sh` | o script que `probe_bash` chama: imprime `$0`, os argumentos e a pasta de trabalho |
| `reach_pypi.sh` | a tentativa de alcançar a PyPI com o `urllib` e com o `pip`, com o tempo de cada uma |
| [`../awsds-demo-job/`](../awsds-demo-job/) | o projeto que o `.zip` leva |

Um `.sh` que um `bash_command` nomeia passa pelo Jinja antes de rodar: nenhum dos dois scripts
tem `{{` nem `{#`, e um teste do repositório confere isso.

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#demo-bash-operator): o `.zip` com os dois
scripts e a definição na máquina que empacota, a amostra em `inbox/` num espaço, o workflow no
portal e o hash do resultado.

## O que os logs dizem

- **`run_command`**: `cwd /var/tmp/airflowtmp...`, o `PYTHONPATH`, que começa por
  `/usr/local/airflow/dags`, `python 3.12.14 em /opt/mwaa-serverless-venv/bin/python3`,
  `sample.csv: 10 linhas -> s3://.../outbox/<carimbo>Z/sample.result.json; origem apagada` e
  `1 objeto(s) processado(s)`.
- **`probe_bash`**: os arquivos do `.zip` em `/usr/local/airflow/dags` com os modos do `.zip`,
  os scripts `-rwxr-xr-x`; a linha `usage:` do módulo, sem `cd`;
  `petl 1.7.28 de /usr/local/airflow/dags/petl/__init__.py` e
  `six 1.16.0 de /usr/local/airflow/dags/six.py`, porque numa task Bash o `.zip` vence o worker,
  que tem o `six` 1.17.0; e `probe.sh` com `$0 = /usr/local/airflow/dags/probe.sh`, os
  argumentos e a pasta de trabalho da task, pelas duas formas.
- **`reach_pypi`**: nenhuma variável de proxy, `pypi.org` resolvido,
  `urllib: URLError(OSError(101, 'Network is unreachable'))`, o `pip` 23.2.1 do worker com
  `[Errno 101] Network is unreachable`, e a saída 1. Onde um firewall de DNS recusa o nome, a
  falha vem em segundos, com outro erro.

## Lido no ambiente alvo em 2026-10-12

Das 19:34 às 19:38 UTC, cada task num worker próprio: `probe_bash` terminou em 11,7 s,
`run_command` em 9,2 s, com um resultado de sha256 igual ao da task Python, e `reach_pypi` em
116 s, com `urllib: 43 s` e `pip: 64 s`, os dois em errno 101. Os scripts daquele dia imprimiam
em inglês; os desta pasta imprimem o mesmo em português.
