# demo-bash-operator: uma task Bash sobre o `.zip`, com scripts

Um sensor espera um arquivo em `inbox/`; `run_command` roda o modo S3 do projeto
[`awsds-demo-job`](../awsds-demo-job/) com `python3 -m`, a partir do `.zip`; `reach_pypi` roda
o script `reach_pypi.sh` do `.zip`, que tenta a PyPI e falha, porque o worker não tem internet;
e `probe_bash`, sem dependência, imprime como o worker roda um script e um módulo do `.zip`.

| Task | Operador | O que faz |
|---|---|---|
| `wait_for_file` | `S3KeySensor` | espera `inbox/?*`, a cada 30 s, por 10 minutos |
| `run_command` | `BashOperator` | `cd /usr/local/airflow/dags && python3 -m awsds_demo_job.s3 --inbox s3://... --outbox s3://...` |
| `reach_pypi` | `BashOperator` | `reach_pypi.sh`, depois de `run_command`; termina com 1 quando nada respondeu, o esperado, e a execução termina `FAILED` |
| `probe_bash` | `BashOperator` | inline: a pasta de trabalho, o `PYTHONPATH`, os modos dos arquivos extraídos, o `python3 -m` sem `cd`, de onde vêm o `petl` e o `six`, e `probe.sh` pelo caminho inteiro e executado direto |

## A aplicação

A pasta é uma aplicação da CLI de CI/CD do SageMaker Unified Studio, a `aws-smus-cicd-cli` 1.0.9:
o `manifest.yaml` na raiz, o workflow em `workflows/`, na notação da CLI, e os scripts em `code/`.
O `package-task`, com `--include` dos dois scripts, grava em `code/` o `.zip` com eles na raiz, o
projeto compartilhado e as dependências dele, `code/demo-bash-operator.zip`, que fica fora do git.
O item de storage `code` do manifest sobe só o `.zip`, e a entrada `code: code/demo-bash-operator.zip`
do workflow diz à CLI qual arquivo passar como `Code` do workflow: ela o acha pelo nome entre os
arquivos copiados, o copia para `operatorFiles/` da pasta `shared/` do projeto e cria o workflow
apontando para essa cópia, lido no código da CLI e ainda não medido. Os URIs de `run_command` e o
do sensor são o `s3Uri` da conexão `default.s3_shared` do projeto mais o literal
`exemplos/demo-bash-operator/`, então o exemplo não tem variável de stage. O stage `test` executa
o workflow uma vez, com `trailLogs: true`, e a execução termina `FAILED` pela task `reach_pypi`,
o esperado. Pelo portal, o `render` traduz as variáveis da CLI e preenche com o
`space_values.json`.

## Arquivos

| Arquivo | O que é |
|---|---|
| `manifest.yaml` | o manifest da aplicação: as pastas `code/` e `workflows/`, o workflow com o `code` e os stages `dev` e `test` |
| `workflows/demo-bash-operator.yaml` | o workflow, na notação da CLI |
| `code/probe.sh` | o script que `probe_bash` chama: imprime `$0`, os argumentos e a pasta de trabalho |
| `code/reach_pypi.sh` | a tentativa de alcançar a PyPI com o `urllib` e com o `pip`, com o tempo de cada uma |
| `code/demo-bash-operator.zip` | o `.zip` que o `package-task` grava, fora do git |
| [`../awsds-demo-job/`](../awsds-demo-job/) | o projeto que o `.zip` leva |

Um `.sh` que um `bash_command` nomeia passa pelo Jinja antes de rodar: nenhum dos dois scripts
tem `{{` nem `{#`, e um teste do repositório confere isso.

## Os passos

Estão na página [Os exemplos, passo a passo](https://felipenoris.github.io/awsds-workflows/awsds_workflows/examples.html#demo-bash-operator): o `.zip` com os dois
scripts em `code/` na máquina que empacota, o `deploy` e o `run` pela CLI, ou o workflow no
portal, a amostra em `inbox/` num espaço e o hash do resultado.

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
