"""A task Python de ``redshift-unload``: ``redshift_unload.unload``, que descarrega no S3, com
``UNLOAD``, o resultado de uma consulta ao Redshift Serverless.

A definição do workflow chama a função com os ``op_kwargs`` ``select``, ``destination``,
``workgroup`` e ``database``. Os comandos vão pela Data API, com as credenciais do worker, que roda
com o papel do projeto. Um namespace sem papel IAM não aceita ``IAM_ROLE`` no ``UNLOAD``, então o
comando leva no próprio texto as credenciais temporárias do worker. O módulo só importa o ``boto3``
que o worker já traz, e roda igual num espaço do projeto, que tem o mesmo papel.

Exemplo, num espaço do projeto:

.. code-block:: python

    import redshift_unload

    redshift_unload.unload(
        select="SELECT * FROM <banco do datashare>.<esquema>.<tabela>",
        destination="s3://<bucket>/<domínio>/<projeto>/shared/exemplos/redshift-unload/teste/",
        workgroup="<workgroup>",
        database="<banco>",
    )
"""

import re
import time

import boto3
from botocore.client import BaseClient

# Os estados em que um comando da Data API termina sem sucesso.
FAILED_STATUSES = ("FAILED", "ABORTED")
# O intervalo entre duas leituras do estado de um comando.
POLL_SECONDS = 5
# A sessão da Data API continua aberta por esse tempo depois de cada comando que o pede.
SESSION_SECONDS = 60
# O valor de cada cláusula de credencial, que a máscara troca por ***.
CREDENTIAL_CLAUSE = re.compile(r"(ACCESS_KEY_ID|SECRET_ACCESS_KEY|SESSION_TOKEN)\s+'[^']*'")


def unload(
    select: str,
    destination: str,
    workgroup: str,
    database: str,
    **context,
) -> int:
    """Descarrega o resultado de ``select`` em Parquet sob ``destination`` e devolve o número de
    linhas.

    Os comandos rodam numa só sessão da Data API: ``SELECT current_user``, que imprime o usuário
    do banco com que o worker entrou, o ``UNLOAD`` e ``SELECT pg_last_unload_count()``. O
    ``UNLOAD`` grava os arquivos e um manifesto verboso; com zero linhas ele não grava nada, e a
    contagem é o que diz isso. O destino precisa estar vazio, porque o ``UNLOAD`` não sobrescreve
    arquivos.

    :param select: a consulta descarregada. Numa sessão da Data API, uma tabela de um datashare
        leva o nome em três partes, ``<banco do datashare>.<esquema>.<tabela>``.
    :param destination: o prefixo de destino no S3, com ou sem a barra final, na forma
        ``s3://<bucket>/<chave>/``; os arquivos e o manifesto ficam sob ele.
    :param workgroup: o workgroup do Redshift Serverless.
    :param database: o banco em que a sessão entra, como ``dev``.
    :param context: o contexto que o Airflow passa à task; a função não o usa.
    :return: o número de linhas descarregadas.
    :raises RuntimeError: quando um comando termina em ``FAILED`` ou ``ABORTED``.
    """
    client = boto3.client("redshift-data")
    prefix = destination.rstrip("/") + "/"

    # O primeiro comando abre a sessão e diz o usuário do banco, que é quem precisa da permissão
    # de leitura sobre a consulta.
    opening = client.execute_statement(
        WorkgroupName=workgroup,
        Database=database,
        Sql="SELECT current_user",
        SessionKeepAliveSeconds=SESSION_SECONDS,
    )
    session_id = opening["SessionId"]
    user = read_single_value(client, opening["Id"])
    print(f"usuário do banco: {user}")

    # O UNLOAD, na mesma sessão.
    started = time.monotonic()
    statement = client.execute_statement(
        SessionId=session_id,
        Sql=unload_text(select, prefix),
        SessionKeepAliveSeconds=SESSION_SECONDS,
    )
    wait_until_finished(client, statement["Id"])
    seconds = time.monotonic() - started

    # A contagem é a do último UNLOAD da sessão.
    counting = client.execute_statement(
        SessionId=session_id,
        Sql="SELECT pg_last_unload_count()",
    )
    rows = int(read_single_value(client, counting["Id"]))
    print(f"{rows} linha(s) descarregada(s) em {seconds:.1f} s sob {prefix}")
    return rows


def unload_text(
    select: str,
    prefix: str,
) -> str:
    """O comando ``UNLOAD`` de ``select`` para ``prefix``, em Parquet com manifesto verboso e com
    as credenciais do worker.

    A consulta entra como literal, com a contrabarra e a aspa simples dobradas, porque o literal
    do ``UNLOAD`` trata a contrabarra como escape (medido no ambiente alvo em 2026-09-23). O texto
    devolvido carrega segredo: só a Data API o recebe.

    :param select: a consulta descarregada.
    :param prefix: o prefixo de destino no S3, terminado em barra.
    :return: o texto do comando.
    """
    frozen = boto3.Session().get_credentials().get_frozen_credentials()
    escaped = select.replace("\\", "\\\\").replace("'", "''")
    credentials = (
        f"ACCESS_KEY_ID '{frozen.access_key}' SECRET_ACCESS_KEY '{frozen.secret_key}' "
        f"SESSION_TOKEN '{frozen.token}'"
    )
    return f"UNLOAD ('{escaped}')\nTO '{prefix}'\n{credentials}\nFORMAT AS PARQUET MANIFEST VERBOSE"


def wait_until_finished(
    client: BaseClient,
    statement_id: str,
) -> None:
    """Espera o comando ``statement_id`` da Data API terminar.

    :param client: o cliente ``redshift-data`` do ``boto3``.
    :param statement_id: o identificador que ``execute_statement`` devolveu.
    :raises RuntimeError: quando o comando termina em ``FAILED`` ou ``ABORTED``; a mensagem traz o
        erro da Data API, sem o valor das credenciais.
    """
    while True:
        description = client.describe_statement(Id=statement_id)
        status = description["Status"]
        if status == "FINISHED":
            return
        if status in FAILED_STATUSES:
            error = CREDENTIAL_CLAUSE.sub(r"\1 '***'", description.get("Error", ""))
            raise RuntimeError(f"o comando da Data API terminou em {status}: {error}")
        time.sleep(POLL_SECONDS)


def read_single_value(
    client: BaseClient,
    statement_id: str,
) -> str | int:
    """O valor da única célula do resultado do comando ``statement_id``, depois que ele termina.

    :param client: o cliente ``redshift-data`` do ``boto3``.
    :param statement_id: o identificador que ``execute_statement`` devolveu.
    :return: o valor da célula: ``str`` para um texto, ``int`` para um inteiro.
    :raises RuntimeError: quando o comando termina em ``FAILED`` ou ``ABORTED``.
    """
    wait_until_finished(client, statement_id)
    result = client.get_statement_result(Id=statement_id)
    # A Data API devolve cada célula como um dicionário de uma chave só, como {"longValue": 42}.
    cell = result["Records"][0][0]
    return list(cell.values())[0]
