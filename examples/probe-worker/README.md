# probe-worker: o que o worker tem

Uma task Bash inline, sem `Code`, que imprime o disco, a CPU e a memória do worker, as
ferramentas que ele tem e os pacotes Python que ele traz. Rode-a antes de desenhar uma task Python
ou Bash, para saber o que cabe no worker.

| Task | Operador | O que faz |
|---|---|---|
| `probe_worker` | `BashOperator` | os comandos inline abaixo, e `exit 0` |

## Passos

1. **No portal:** crie o workflow `probe-worker`, esvazie *Operator files zip S3 location* em
   *Settings → Storage*, importe `examples/probe-worker/probe-worker.yaml` e salve. A definição
   não tem placeholder, então o arquivo entra como está, sem o `render`.
2. **Execute** e leia o log da task `probe_worker`.

## O que ela imprime

- `--- disco`: o `df -h` de `/`, `/tmp`, `/var/tmp` e `/usr/local/airflow/dags`, e o tempo
  de gravar 1 GiB em `/var/tmp`.
- `--- CPU e memória`: `nproc`, `MemTotal` e `MemAvailable`, e os limites do cgroup que
  existirem.
- `--- ferramentas`: onde estão `aws`, `tar`, `unzip` e `gzip`, ou `ausente`.
- `--- pacotes`: o Python, a versão de `pyarrow`, `duckdb`, `deltalake`, `SQLAlchemy`,
  `redshift-connector`, `pandas` e `numpy`, ou `ausente`, e a lista inteira das distribuições.

A task termina com `exit 0` e tem `retries: 0`, então uma leitura nunca roda duas vezes.

## Lido no ambiente alvo em 2026-10-13

- `/` é um `overlay` de 21G com 19G livres, com `/var/tmp` e `/usr/local/airflow/dags` nele;
  `/tmp` é um dispositivo próprio, de 9,7G; 1 GiB foi gravado em `/var/tmp` em 3 s.
- `nproc` 2, `MemTotal` 4.929.824 kB, `MemAvailable` 3.914.296 kB, e nenhum limite de cgroup
  abaixo do da máquina, contra o 1 vCPU e os 3 GiB do guia.
- `aws`, `tar` e `unzip` ausentes; `gzip` em `/usr/bin/gzip`.
- Python 3.12.14 em `/opt/mwaa-serverless-venv/bin/python3`, e 164 distribuições, cada uma
  listada duas vezes (o `lib` e o `lib64` do venv): o Airflow 3.0.6, o provider da Amazon
  9.32.0, o `boto3` e o `botocore` 1.43.1, o PyYAML 6.0.2, o SQLAlchemy 1.4.54, o
  `redshift-connector` 2.1.8, o PyAthena 3.17.1, o `six` 1.17.0 e o pip 23.2.1; `pyarrow`,
  `duckdb`, `deltalake`, `pandas` e `numpy` ausentes.
- A task terminou em 13,3 s, num worker com um nome de host privado, `ip-10-...`.
