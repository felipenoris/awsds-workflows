"""A task Python de ``demo-python-operator``: ``demo_tasks.run``, com ``inbox`` e ``outbox`` como
``op_kwargs``, os dois URIs ``s3://`` que a definição monta com a conexão do projeto.

Antes de entregar o trabalho ao modo S3 do projeto, a função imprime com o que o worker a roda: o
interpretador, o ``sys.path``, a credencial e de onde cada pacote sondado foi importado, que é como
uma cópia do ``.zip`` se distingue de uma pré-instalada no worker. O módulo fica na raiz do
``.zip``, ao lado do pacote ``awsds_demo_job`` e das dependências dele.
"""

from __future__ import annotations

import importlib
import sys

# O petl não está no worker e vem do .zip; o six e o PyYAML estão no worker, e o .zip leva o six
# numa versão mais antiga, então o __file__ de cada um diz qual cópia o import achou.
PROBED_PACKAGES = ("petl", "six", "yaml")


def print_environment() -> None:
    """Imprime o interpretador, o ``sys.path``, a credencial e a origem de cada pacote sondado."""
    import boto3

    print(f"python {sys.version.split()[0]} em {sys.executable}")
    print(f"sys.path: {sys.path}")
    print(f"credencial: {boto3.client('sts').get_caller_identity()['Arn']}")
    for name in PROBED_PACKAGES:
        try:
            module = importlib.import_module(name)
        except ImportError as error:
            print(f"import {name}: falhou, {error}")
            continue
        version = getattr(module, "__version__", "-")
        print(f"import {name}: {version} de {getattr(module, '__file__', '-')}")


def run(
    inbox: str,
    outbox: str,
    **context,
) -> int:
    """Resume cada objeto sob ``inbox`` em ``outbox`` e devolve quantos foram processados.

    :param inbox: o URI ``s3://`` da caixa de entrada, em que os arquivos chegam.
    :param outbox: o URI ``s3://`` da caixa de saída, em que os resumos ficam, numa pasta por
        execução.
    :param context: o contexto que o Airflow passa à task; a função não o usa.
    :return: o número de objetos processados.
    :raises RuntimeError: quando não há nada sob a entrada, porque a execução começa depois que
        o sensor viu um arquivo.
    """
    print_environment()

    from awsds_demo_job import s3

    processed = s3.run(inbox, outbox)
    if not processed:
        raise RuntimeError(f"nada sob {inbox}, e o sensor viu um arquivo")
    return processed
