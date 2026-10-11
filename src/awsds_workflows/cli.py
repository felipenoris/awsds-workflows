"""[public] A linha de comando ``awsds-workflows``.

Cada subcomando roda uma ferramenta do pacote na máquina com internet, e o que ela grava é copiado
depois para o ambiente do SageMaker, que não tem internet.

- ``package-task`` grava o ``.zip`` de uma task Python ou Bash para o worker do MWAA Serverless
  (``awsds_workflows.package_task``).
- ``package-job`` grava a pasta de código de um job de processamento para a imagem do job, cujo
  ambiente chega em ``--environment`` (``awsds_workflows.package_job``).
- ``job-constraints`` imprime as versões do ambiente da imagem como requisitos, para restringir o
  lock do projeto com ``uv add -c`` ou ``uv pip compile -c``.
- ``render`` imprime uma definição com os placeholders preenchidos, ou, com ``--placeholders``, uma
  definição salva com os valores trocados pelos placeholders (``awsds_workflows.render``).
- ``values`` imprime os valores em JSON, o formato de ``--values-file``.

Os valores de ``render`` e ``values`` vêm de ``--values-file``, de ``--profile`` (a leitura da
conta, que pede ``--subnet-name``) ou dos dois, e então os do arquivo completam e substituem os da
conta. Uma recusa imprime o motivo na saída de erro e termina com 1; um erro de uso termina com 2.

Exemplo:

.. code-block:: shell

    awsds-workflows package-task ~/src/meu-projeto ~/src/meu-projeto/tasks.py /tmp/meu-projeto.zip
    awsds-workflows package-job ~/src/meu-projeto /tmp/meu-projeto-0.2.0 \\
        --environment ambiente.txt --python 3.12
    awsds-workflows job-constraints --environment ambiente.txt --python 3.12
    awsds-workflows render meu-workflow.yaml --values-file valores.json > /tmp/meu-workflow.yaml
    awsds-workflows render --placeholders salvo.yaml --values-file valores.json
    awsds-workflows values --profile meu-perfil --subnet-name 'meu-projeto-private-*' > valores.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from awsds_workflows import package_job, package_task, render
from awsds_workflows.errors import RefusalError

__all__ = ["main"]


def main(
    argv: list[str] | None = None,
) -> int:
    """[public] Executa a linha de comando.

    Cada subcomando guarda a sua função em ``handler`` (``set_defaults`` do ``argparse``), e uma
    recusa do pacote vira o motivo na saída de erro.

    Exemplo:

    .. code-block:: python

        main(["package-task", "meu-projeto", "meu-projeto/tasks.py", "meu-projeto.zip"])
        # 0 com o .zip gravado; 1 com o motivo da recusa na saída de erro

    :param argv: os argumentos, sem o nome do programa; ``None`` lê ``sys.argv``.
    :return: o código de saída: 0 quando o comando termina e 1 numa recusa.
    :raises SystemExit: o erro de uso que o ``argparse`` detecta, com o código 2, e ``--help``,
        com o código 0.
    """
    arguments = _build_parser().parse_args(argv)
    try:
        return arguments.handler(arguments)
    except RefusalError as error:
        print(error, file=sys.stderr)
        return 1


def _build_parser() -> argparse.ArgumentParser:
    """[private] O parser da linha de comando, com um subcomando por ferramenta."""
    parser = argparse.ArgumentParser(
        prog="awsds-workflows",
        description="Empacota o código das tasks de um workflow do MWAA Serverless e renderiza "
        "as definições de workflow de um projeto do SageMaker Unified Studio.",
    )
    commands = parser.add_subparsers(dest="command", required=True)
    _add_package_task_parser(commands)
    _add_package_job_parser(commands)
    _add_job_constraints_parser(commands)
    _add_render_parser(commands)
    _add_values_parser(commands)
    return parser


def _add_package_task_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``package-task``."""
    command = commands.add_parser(
        "package-task",
        help="grava o .zip de uma task Python ou Bash para o worker do MWAA Serverless",
    )
    command.add_argument("project", type=Path, help="a pasta do projeto uv, com uv.lock")
    command.add_argument(
        "entry_module",
        type=Path,
        help="o módulo .py que vai para a raiz e que o python_callable nomeia",
    )
    command.add_argument("archive", type=Path, help="o .zip a gravar, numa pasta que já existe")
    command.add_argument(
        "--python",
        default=package_task.WORKER_PYTHON,
        help=f"a versão do CPython do worker (padrão: {package_task.WORKER_PYTHON})",
    )
    command.add_argument(
        "--platform",
        default=package_task.WORKER_PLATFORM,
        help=f"o --python-platform do uv (padrão: {package_task.WORKER_PLATFORM})",
    )
    command.add_argument(
        "--omit",
        action="append",
        default=[],
        metavar="PACOTE",
        help="mais um pacote a deixar de fora, além dos que o worker traz; repita para vários",
    )
    command.set_defaults(handler=_package_task)


def _add_package_job_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``package-job``."""
    command = commands.add_parser(
        "package-job",
        help="grava a pasta de código de um job de processamento para a imagem do job",
    )
    command.add_argument("project", type=Path, help="a pasta do projeto uv, com uv.lock")
    command.add_argument("output", type=Path, help="a pasta a gravar, que ainda não pode existir")
    _add_job_target_arguments(command)
    command.set_defaults(handler=_package_job)


def _add_job_constraints_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``job-constraints``."""
    command = commands.add_parser(
        "job-constraints",
        help="imprime as versões do ambiente da imagem do job como requisitos",
    )
    _add_job_target_arguments(command)
    command.set_defaults(handler=_job_constraints)


def _add_job_target_arguments(
    command: argparse.ArgumentParser,
) -> None:
    """[private] As opções que descrevem a imagem do job, comuns a ``package-job`` e
    ``job-constraints``."""
    command.add_argument(
        "--environment",
        type=Path,
        required=True,
        help="o arquivo nome==versão do ambiente da imagem do job, como o de "
        "uv pip list --format freeze",
    )
    command.add_argument(
        "--python",
        required=True,
        help="a versão do CPython do interpretador que o job chama, como 3.12",
    )
    command.add_argument(
        "--platform",
        default=package_job.JOB_PLATFORM,
        help=f"o --python-platform do uv (padrão: {package_job.JOB_PLATFORM})",
    )


def _add_render_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``render``."""
    command = commands.add_parser(
        "render",
        help="imprime uma definição com os placeholders preenchidos",
    )
    command.add_argument("file", type=Path, help="o arquivo com os placeholders")
    command.add_argument(
        "--placeholders",
        action="store_true",
        help="o caminho inverso: troca cada valor do arquivo pelo seu placeholder",
    )
    _add_value_source_arguments(command)
    command.set_defaults(handler=_render)


def _add_values_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``values``."""
    command = commands.add_parser(
        "values",
        help="imprime os valores em JSON, o formato de --values-file",
    )
    _add_value_source_arguments(command)
    command.set_defaults(handler=_values)


def _add_value_source_arguments(
    command: argparse.ArgumentParser,
) -> None:
    """[private] As opções de onde vêm os valores, comuns a ``render`` e ``values``."""
    command.add_argument(
        "--values-file",
        type=Path,
        help="um JSON de nome de placeholder para valor; completa e substitui os da conta",
    )
    command.add_argument("--profile", help="o perfil do aws com que a conta é lida")
    command.add_argument(
        "--subnet-name",
        help="com --profile, o padrão do Name das sub-redes privadas do projeto, como "
        "'awsds-sandbox-private-*'",
    )
    command.add_argument("--project", help="com --profile, o id do projeto, numa conta com vários")
    command.add_argument(
        "--image-name",
        help="com --profile, a imagem customizada registrada no SageMaker, que dá JOB_IMAGE_URI",
    )


def _package_task(
    arguments: argparse.Namespace,
) -> int:
    """[private] Grava o ``.zip`` e imprime o resumo e o próximo passo."""
    archive = package_task.build_archive(
        arguments.project,
        arguments.entry_module,
        arguments.archive,
        python=arguments.python,
        platform=arguments.platform,
        omit=arguments.omit,
    )
    print(
        f"{archive.path}: {archive.size_bytes} bytes, {archive.unzipped_bytes} descompactados, "
        f"para o CPython {archive.python} em {archive.platform}"
    )
    print(f"raiz: {', '.join(archive.top_level)}")
    module = arguments.entry_module.stem
    print(
        "próximo passo: envie o .zip em Settings -> Storage -> Python/Bash Operator Files do "
        f"workflow, salve, e nomeie a função como python_callable: {module}.<função>"
    )
    return 0


def _package_job(
    arguments: argparse.Namespace,
) -> int:
    """[private] Grava a pasta e imprime o resumo e os próximos passos."""
    folder = package_job.build_folder(
        arguments.project,
        arguments.output,
        environment=arguments.environment,
        python=arguments.python,
        platform=arguments.platform,
    )
    target = f"para o CPython {folder.python} em {folder.platform}"
    from_environment = ", ".join(folder.from_environment) or "-"
    vendored = ", ".join(f"{name}=={version}" for name, version in folder.vendored.items())
    print(f"{folder.path}: {folder.size_bytes} bytes, {target}")
    print(f"da imagem ({len(folder.from_environment)}): {from_environment}")
    print(f"na pasta ({len(folder.vendored)}): {vendored or '-'}")
    print(f"raiz: {', '.join(folder.top_level)}")
    print(
        "próximo passo: copie a pasta para um prefixo só desta versão no S3 do projeto "
        "(aws s3 cp --recursive), nomeie esse prefixo como a entrada de código do job em "
        "/opt/ml/processing/code e defina PYTHONPATH: /opt/ml/processing/code no Environment do job"
    )
    return 0


def _job_constraints(
    arguments: argparse.Namespace,
) -> int:
    """[private] Imprime cada versão do ambiente da imagem como ``nome==versão``."""
    versions = package_job.environment_versions(
        arguments.environment,
        python=arguments.python,
        platform=arguments.platform,
    )
    for name, version in versions.items():
        print(f"{name}=={version}")
    return 0


def _render(
    arguments: argparse.Namespace,
) -> int:
    """[private] Imprime o arquivo preenchido, ou com os placeholders de volta."""
    values = _values_from(arguments)
    if not arguments.file.is_file():
        raise RefusalError(f"o arquivo {arguments.file} não existe")
    text = arguments.file.read_text(encoding="utf-8")
    if arguments.placeholders:
        sys.stdout.write(render.restore_placeholders(text, values))
    else:
        sys.stdout.write(render.fill_placeholders(text, values))
    return 0


def _values(
    arguments: argparse.Namespace,
) -> int:
    """[private] Imprime os valores em JSON, com as chaves em ordem."""
    values = _values_from(arguments)
    print(json.dumps(values, indent=2, sort_keys=True, ensure_ascii=False))
    return 0


def _values_from(
    arguments: argparse.Namespace,
) -> dict[str, str]:
    """[private] Os valores da conta, quando há ``--profile``, completados e substituídos pelos
    do arquivo, quando há ``--values-file``."""
    if arguments.profile is None and arguments.values_file is None:
        raise RefusalError("nomeie de onde vêm os valores: --values-file, --profile ou os dois")

    values: dict[str, str] = {}
    if arguments.profile is not None:
        if arguments.subnet_name is None:
            raise RefusalError("--profile pede --subnet-name, o padrão do Name das sub-redes")
        values = render.read_values(
            arguments.profile,
            subnet_name=arguments.subnet_name,
            project=arguments.project,
            image_name=arguments.image_name,
        )
    if arguments.values_file is not None:
        values.update(render.load_values(arguments.values_file))
    return values
