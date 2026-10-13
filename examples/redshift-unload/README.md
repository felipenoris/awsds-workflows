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

## Os valores

Além do `space_values.json`, três valores do Redshift, em `valores-redshift.json`:

```json
{
  "REDSHIFT_WORKGROUP": "<o workgroup do Redshift Serverless>",
  "REDSHIFT_DATABASE": "<o banco em que a sessão entra>",
  "REDSHIFT_TABLE": "<banco do datashare>.<esquema>.<tabela>"
}
```

A consulta é `SELECT * FROM <REDSHIFT_TABLE>`; numa sessão da Data API, uma tabela de um datashare
leva o nome em três partes. O destino é `shared/exemplos/redshift-unload/<data-hora>/`, uma pasta
por execução, porque o `UNLOAD` não grava num destino que já tem arquivos.

## Passos

1. **Monte o `.zip`**, só com o módulo na raiz:

   ```shell
   python3 -m zipfile -c /tmp/redshift-unload.zip examples/redshift-unload/redshift_unload.py
   ```

2. **Renderize a definição**, com os dois arquivos de valores:

   ```shell
   awsds-workflows render examples/redshift-unload/redshift-unload.yaml \
       --values-file space_values.json --values-file valores-redshift.json > /tmp/redshift-unload.yaml
   ```

3. **No portal:** crie o workflow `redshift-unload`, envie `/tmp/redshift-unload.zip` em
   *Settings → Storage → Python/Bash Operator Files*, importe `/tmp/redshift-unload.yaml` e salve.
4. **Execute o workflow.** A task não cria job, então não depende da permissão do projeto para
   jobs.

Para testar antes num espaço do projeto, que tem o mesmo papel, copie `redshift_unload.py` para
lá e rode o exemplo da docstring do módulo, com um destino de teste.

## Onde ler o resultado

- **O log da task:** a linha `usuário do banco: ...` e a linha
  `<n> linha(s) descarregada(s) em <s> s sob s3://...`.
- **Os arquivos:** `~/shared/exemplos/redshift-unload/<data-hora>/`, com os `.parquet` e o
  `manifest`. Com zero linhas, o `UNLOAD` não grava nada, e a contagem diz 0.

## Falhas

| A task diz | O que fazer |
|---|---|
| `permission denied` ou `does not exist` sobre a tabela | dê ao usuário do banco impresso no log a leitura da tabela, ou troque a tabela |
| `Permission denied to query database created from datashare` | o usuário do banco não tem acesso ao banco do datashare; veja "A permissão do usuário do projeto" |
| `S3ServiceException` com `Access Denied` | o papel do projeto não grava nesse prefixo, ou não usa a chave KMS do bucket |
| `unload destination on S3 is not empty` | o destino precisa estar vazio; cada execução usa a data e a hora |
| `NoRegionError` ou `Could not connect to the endpoint URL` | o worker não achou a região ou o endpoint `redshift-data` |

## A permissão do usuário do projeto

O espaço e o worker entram no Redshift com usuários diferentes. No ambiente alvo, em 2026-10-13,
o espaço entrou com o usuário da pessoa, `IAMR:user-<id da pessoa>@<projeto>`, e o worker com o
do projeto, `IAMR:user-project@<projeto>`. O teste no espaço não prova, então, a permissão do
worker: lá o `UNLOAD` passou, e no workflow parou em `Permission denied to query database created
from datashare`. A primeira linha do log de cada execução diz quem precisa da permissão.

Quem tem o direito de conceder dá o acesso ao usuário do projeto, conectado a um banco local, como
o `dev`, sem um `USE <banco do datashare>` antes:

```sql
GRANT USAGE ON DATABASE <banco do datashare> TO "IAMR:user-project@<projeto>";
```

No ambiente alvo, em 2026-10-13, o usuário da pessoa rodou esse `GRANT`, e ele bastou, o que
indica que o banco não foi criado `WITH PERMISSIONS` (inferido): nesse caso, o `USAGE` dá ao
usuário todas as permissões em todos os objetos do banco, a escrita inclusive. Num banco criado
`WITH PERMISSIONS`, o `USAGE` não basta, e o usuário também precisa das permissões dos objetos:

```sql
GRANT USAGE ON SCHEMA <banco do datashare>.<esquema> TO "IAMR:user-project@<projeto>";
GRANT SELECT ON ALL TABLES IN SCHEMA <banco do datashare>.<esquema>
    TO "IAMR:user-project@<projeto>";
```

O pedido mais simples é o mesmo acesso do usuário da pessoa, que o administrador lê com
`SHOW GRANTS FOR "<usuário da pessoa>" FROM DATABASE <banco do datashare>`.

## Conferência

`tests/test_examples.py` roda o módulo contra o `Stubber` do `botocore`, que valida os
parâmetros das três chamadas contra o modelo da Data API, e confere o escape da consulta e a
máscara das credenciais numa falha, sem rede e com credenciais fabricadas.

No ambiente alvo, em 2026-10-13, a função rodou no espaço: 101 linhas em 5,5 s, um `.parquet` e
o `manifest`. No workflow, ela parou na permissão do banco do datashare, antes de gravar no S3.
Depois do `GRANT USAGE`, o workflow descarregou as mesmas 101 linhas em 5,5 s, numa task de
23,4 s, às 02:22 UTC. A pasta de destino levou a hora da execução, `20261013T022213`, e não a
meia-noite da data lógica.
