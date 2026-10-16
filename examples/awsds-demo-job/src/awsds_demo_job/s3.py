"""``python -m awsds_demo_job.s3 --inbox s3://B/PREFIXO/ --outbox s3://B/PREFIXO/``: o modo de
uma task no worker.

Cada objeto sob o URI de entrada vira um resumo sob ``<outbox>/<carimbo UTC>/``, e a origem é
apagada só depois que a gravação do resumo voltou. Os dois URIs têm a forma
``s3://<bucket>/<prefixo>/``, a que a CLI de CI/CD monta a partir da conexão do projeto. O módulo
roda com a credencial que recebe: no worker, a do papel do projeto, pelo endpoint de gateway do
S3. O ``boto3`` é importado dentro de ``run``, então o modo do job de processamento não precisa
dele.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Any

from awsds_demo_job import transform


def split_uri(
    uri: str,
) -> tuple[str, str]:
    """O bucket e o prefixo de um URI ``s3://<bucket>/<prefixo>``, o prefixo terminado em barra.

    :param uri: o URI, com ou sem a barra final.
    :return: o bucket e o prefixo com a barra final.
    :raises ValueError: quando o URI não começa por ``s3://`` ou não tem prefixo.
    """
    if not uri.startswith("s3://"):
        raise ValueError(f"não é um URI s3://: {uri}")
    bucket, _separator, prefix = uri[len("s3://") :].partition("/")
    if not bucket or not prefix.strip("/"):
        raise ValueError(f"o URI precisa de bucket e prefixo, s3://<bucket>/<prefixo>/: {uri}")
    if not prefix.endswith("/"):
        prefix = prefix + "/"
    return bucket, prefix


def run(
    inbox: str,
    outbox: str,
    client: Any = None,
) -> int:
    """Resume cada objeto sob ``inbox`` e devolve quantos foram processados.

    :param inbox: o URI ``s3://`` da caixa de entrada, em que os arquivos chegam.
    :param outbox: o URI ``s3://`` da caixa de saída, em que os resumos ficam, numa pasta por
        execução.
    :param client: o cliente ``s3`` do ``boto3``; ``None`` cria um com a credencial do processo.
    :return: o número de objetos processados.
    :raises ValueError: quando um dos URIs não tem a forma ``s3://<bucket>/<prefixo>/``.
    """
    if client is None:
        import boto3

        client = boto3.client("s3")
    bucket, inbox_prefix = split_uri(inbox)
    outbox_bucket, outbox_prefix = split_uri(outbox)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # As chaves sob a entrada, sem o marcador de pasta que um mkdir deixa.
    keys = []
    paginator = client.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=inbox_prefix):
        for entry in page.get("Contents", []):
            if not entry["Key"].endswith("/"):
                keys.append(entry["Key"])

    # O resumo é gravado antes de a origem ser apagada.
    for key in keys:
        name = key.rsplit("/", 1)[-1]
        data = client.get_object(Bucket=bucket, Key=key)["Body"].read()
        summary = transform.summarize(name, data)
        target = f"{outbox_prefix}{stamp}/{transform.result_name(name)}"
        client.put_object(Bucket=outbox_bucket, Key=target, Body=transform.render(summary))
        client.delete_object(Bucket=bucket, Key=key)
        print(f"{name}: {summary['rows']} linhas -> s3://{outbox_bucket}/{target}; origem apagada")
    print(f"{len(keys)} objeto(s) processado(s)")
    return len(keys)


def main(
    argv: list[str] | None = None,
) -> int:
    """Lê os argumentos, roda ``run`` e devolve o código de saída.

    :param argv: os argumentos, sem o nome do programa; ``None`` lê ``sys.argv``.
    :return: 0 com pelo menos um objeto processado, e 1 com a entrada vazia: a execução começa
        depois que o sensor viu um arquivo, então a entrada vazia é uma falha a mostrar.
    """
    parser = argparse.ArgumentParser(prog="awsds_demo_job.s3")
    parser.add_argument("--inbox", required=True, help="o URI s3:// em que os arquivos chegam")
    parser.add_argument("--outbox", required=True, help="o URI s3:// em que os resumos ficam")
    arguments = parser.parse_args(argv)

    print(f"python {sys.version.split()[0]} em {sys.executable}")
    processed = run(arguments.inbox, arguments.outbox)
    if processed:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
