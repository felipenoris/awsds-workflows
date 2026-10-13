"""``python -m awsds_demo_job.s3 --bucket B --inbox PREFIXO --outbox PREFIXO``: o modo de uma
task no worker.

Cada objeto sob o prefixo de entrada vira um resumo sob ``<outbox>/<carimbo UTC>/``, e a origem é
apagada só depois que a gravação do resumo voltou. O módulo roda com a credencial que recebe: no
worker, a do papel do projeto, pelo endpoint de gateway do S3. O ``boto3`` é importado dentro de
``run``, então o modo do job de processamento não precisa dele.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from typing import Any

from awsds_demo_job import transform


def with_slash(
    prefix: str,
) -> str:
    """O prefixo terminado em barra.

    :param prefix: um prefixo de chaves do S3, com ou sem a barra final.
    :return: o prefixo com a barra final.
    """
    if prefix.endswith("/"):
        return prefix
    return prefix + "/"


def run(
    bucket: str,
    inbox: str,
    outbox: str,
    client: Any = None,
) -> int:
    """Resume cada objeto sob ``inbox`` e devolve quantos foram processados.

    :param bucket: o bucket do projeto.
    :param inbox: o prefixo em que os arquivos chegam.
    :param outbox: o prefixo em que os resumos ficam, numa pasta por execução.
    :param client: o cliente ``s3`` do ``boto3``; ``None`` cria um com a credencial do processo.
    :return: o número de objetos processados.
    """
    if client is None:
        import boto3

        client = boto3.client("s3")
    inbox = with_slash(inbox)
    outbox = with_slash(outbox)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")

    # As chaves sob a entrada, sem o marcador de pasta que um mkdir deixa.
    keys = []
    for page in client.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix=inbox):
        for entry in page.get("Contents", []):
            if not entry["Key"].endswith("/"):
                keys.append(entry["Key"])

    # O resumo é gravado antes de a origem ser apagada.
    for key in keys:
        name = key.rsplit("/", 1)[-1]
        data = client.get_object(Bucket=bucket, Key=key)["Body"].read()
        summary = transform.summarize(name, data)
        target = f"{outbox}{stamp}/{transform.result_name(name)}"
        client.put_object(Bucket=bucket, Key=target, Body=transform.render(summary))
        client.delete_object(Bucket=bucket, Key=key)
        print(f"{name}: {summary['rows']} linhas -> s3://{bucket}/{target}; origem apagada")
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
    parser.add_argument("--bucket", required=True, help="o bucket do projeto")
    parser.add_argument("--inbox", required=True, help="o prefixo em que os arquivos chegam")
    parser.add_argument("--outbox", required=True, help="o prefixo em que os resumos ficam")
    arguments = parser.parse_args(argv)

    print(f"python {sys.version.split()[0]} em {sys.executable}")
    processed = run(arguments.bucket, arguments.inbox, arguments.outbox)
    if processed:
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
