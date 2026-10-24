"""[public] A linha de comando ``awsds-workflows``.

Cada subcomando roda uma ferramenta do pacote na máquina com internet, e o que ela grava é copiado
depois para o ambiente do SageMaker, que não tem internet.

- ``package-task`` grava o ``.zip`` de uma task Python ou Bash para o worker do MWAA Serverless
  (``awsds_workflows.package_task``); o módulo de entrada é opcional, e ``--include`` põe na raiz
  um script ou um binário.
- ``package-job`` grava a pasta de código de um job de processamento para a imagem do job, cujo
  ambiente chega em ``--environment`` (``awsds_workflows.package_job``).
- ``prepare-offline`` grava o ``.tar.gz`` da pasta de um projeto preparada com o próprio
  interpretador, a entrada de código de um job que a extrai no volume
  (``awsds_workflows.prepare_offline``).
- ``job-constraints`` imprime as versões do ambiente da imagem como requisitos, para restringir o
  lock do projeto com ``uv add -c`` ou ``uv pip compile -c``.
- ``render`` imprime uma definição com os placeholders preenchidos, ou, com ``--placeholders``, uma
  definição salva com os valores trocados pelos placeholders (``awsds_workflows.render``).
- ``values`` imprime os valores em JSON, o formato de ``--values-file``.
- ``compare`` imprime as diferenças de conteúdo entre duas definições de workflow, como a cópia
  versionada e a que o portal salvou com os placeholders de volta (``awsds_workflows.compare``).
- ``lint`` confere uma aplicação da CLI de CI/CD, a pasta com o ``manifest.yaml``, ou uma
  definição de workflow sozinha, contra as regras do serviço e da esteira
  (``awsds_workflows.lint``): sem opção, na notação da CLI, como os arquivos do repositório; com
  ``--promoted``, uma cópia renderizada por conta, que pede ``--prefix``, o prefixo da versão no
  bucket. ``--instance-type`` e ``--image-repository`` restringem o job de processamento.
- ``lint-plan`` confere os jobs do Glue do plano do Terraform que os cria numa conta sem projeto,
  o JSON de ``terraform show -json`` sobre o plano salvo, antes do ``apply``: o script e os
  arquivos de cada job sob um ``--prefix``, e nenhum módulo pelo nome do PyPI
  (``awsds_workflows.lint``).

Os valores de ``render`` e ``values`` vêm de ``--values-file``, repetido para vários arquivos, de
``--profile`` (a leitura da conta, que pede ``--subnet-name``) ou dos dois: cada arquivo, na ordem
da linha de comando, completa e substitui o que veio antes dele, a leitura da conta e os arquivos
anteriores. Quando a leitura da conta não dá ``PROJECT_KEY_ID``, porque o papel do projeto não tem
a etiqueta ``KmsKeyId``, e nenhum arquivo também, o comando avisa na saída de erro e segue. Uma
recusa imprime o motivo na saída de erro e termina com 1; um erro de uso termina com 2.
O ``compare`` termina com 0 com ou sem diferenças; o ``lint`` imprime cada recusa numa linha e
termina com 1, ou imprime ``ok`` com o número de arquivos lidos e termina com 0, e o ``lint-plan``
faz o mesmo com os jobs do Glue lidos no lugar dos arquivos.

Exemplo:

.. code-block:: shell

    awsds-workflows package-task ~/src/meu-projeto ~/src/meu-projeto/tasks.py /tmp/meu-projeto.zip
    awsds-workflows package-task ~/src/meu-projeto /tmp/meu-projeto.zip \\
        --include ~/src/meu-projeto/run.sh
    awsds-workflows package-job ~/src/meu-projeto /tmp/meu-projeto-0.2.0 \\
        --environment ambiente.txt --python 3.12
    awsds-workflows prepare-offline ~/src/meu-projeto /tmp/meu-projeto.tar.gz
    awsds-workflows job-constraints --environment ambiente.txt --python 3.12
    awsds-workflows render meu-workflow.yaml --values-file valores.json > /tmp/meu-workflow.yaml
    awsds-workflows render meu-job.yaml --values-file space_values.json \\
        --values-file valores-job.json > /tmp/meu-job.yaml
    awsds-workflows render --placeholders salvo.yaml --values-file valores.json
    awsds-workflows values --profile meu-perfil --subnet-name 'meu-projeto-private-*' > valores.json
    awsds-workflows compare meu-workflow.yaml /tmp/salvo.yaml
    awsds-workflows lint examples/demo-devenv-job
    awsds-workflows lint /tmp/meu-workflow.yaml --promoted \\
        --prefix s3://meu-bucket/applications/meu-workflow/v1.0.0/ --instance-type ml.m5.xlarge
    awsds-workflows lint-plan /tmp/plano.json \\
        --prefix s3://meu-bucket/applications/meu-workflow/v1.0.0/glue/
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from awsds_workflows import compare, lint, package_job, package_task, prepare_offline, render
from awsds_workflows.errors import RefusalError

__all__ = ["main"]

# O aviso, na saída de erro, de uma leitura da conta sem a chave KMS do projeto.
_NO_KEY_WARNING = (
    "o papel do projeto não tem a etiqueta KmsKeyId, a chave KMS do projeto: os valores saem sem "
    "PROJECT_KEY_ID"
)


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
    _add_prepare_offline_parser(commands)
    _add_job_constraints_parser(commands)
    _add_render_parser(commands)
    _add_values_parser(commands)
    _add_compare_parser(commands)
    _add_lint_parser(commands)
    _add_lint_plan_parser(commands)
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
        nargs="?",
        help="o módulo .py que vai para a raiz e que o python_callable de uma task Python nomeia; "
        "um .zip só de tasks Bash o dispensa",
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
    command.add_argument(
        "--include",
        action="append",
        default=[],
        type=Path,
        metavar="ARQUIVO",
        help="mais um arquivo a pôr na raiz do .zip, como o script ou o binário de uma task Bash; "
        "repita para vários",
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


def _add_prepare_offline_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``prepare-offline``."""
    command = commands.add_parser(
        "prepare-offline",
        help="grava o .tar.gz da pasta de um projeto preparada com o próprio Python, a entrada de "
        "código de um job que a extrai no volume",
    )
    command.add_argument(
        "project", type=Path, help="a pasta do projeto uv, com uv.lock; ela não é alterada"
    )
    command.add_argument("archive", type=Path, help="o .tar.gz a gravar, numa pasta que já existe")
    command.add_argument(
        "--python",
        default=prepare_offline.DEFAULT_PYTHON,
        help=f"a versão do CPython que vai na pasta (padrão: {prepare_offline.DEFAULT_PYTHON})",
    )
    command.set_defaults(handler=_prepare_offline)


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
    command.add_argument(
        "file", type=Path, help="o arquivo com os placeholders, ou na notação da CLI de CI/CD"
    )
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


def _add_compare_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``compare``."""
    command = commands.add_parser(
        "compare",
        help="imprime as diferenças de conteúdo entre duas definições de workflow em YAML",
    )
    command.add_argument("first", type=Path, help="a primeira definição, como a cópia versionada")
    command.add_argument(
        "second",
        type=Path,
        help="a segunda definição, como a que o portal salvou, com os placeholders de volta",
    )
    command.set_defaults(handler=_compare)


def _add_lint_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``lint``."""
    command = commands.add_parser(
        "lint",
        help="confere uma aplicação da CLI de CI/CD, ou uma definição de workflow, contra as "
        "regras do MWAA Serverless e da esteira",
    )
    command.add_argument(
        "path",
        type=Path,
        help="a pasta da aplicação, com o manifest.yaml, ou o arquivo de uma definição",
    )
    command.add_argument(
        "--promoted",
        action="store_true",
        help="o modo promovido: o arquivo é uma cópia renderizada por conta, sem variável da CLI "
        "nem placeholder, com a imagem por digest e a chave do volume; pede --prefix",
    )
    command.add_argument(
        "--prefix",
        action="append",
        default=[],
        metavar="S3_PREFIX",
        help="um prefixo S3 sob o qual a entrada de código do job e o script do Glue têm de "
        "estar, na notação do arquivo; repetível; só para um arquivo, porque numa aplicação os "
        "prefixos vêm do manifest",
    )
    command.add_argument(
        "--instance-type",
        action="append",
        default=[],
        metavar="TYPE",
        help="um tipo de instância que um job de processamento pode pedir; repetível",
    )
    command.add_argument(
        "--image-repository",
        metavar="REPOSITORY",
        help="o repositório ECR que um ImageUri literal tem de nomear",
    )
    command.set_defaults(handler=_lint)


def _add_lint_plan_parser(
    commands: argparse._SubParsersAction,
) -> None:
    """[private] O subcomando ``lint-plan``."""
    command = commands.add_parser(
        "lint-plan",
        help="confere os jobs do Glue de um plano do Terraform, o JSON de terraform show -json, "
        "antes do apply",
    )
    command.add_argument(
        "plan",
        type=Path,
        help="o JSON de terraform show -json sobre o plano salvo",
    )
    command.add_argument(
        "--prefix",
        action="append",
        required=True,
        metavar="S3_PREFIX",
        help="um prefixo S3 sob o qual o script e os arquivos de cada job têm de estar, como a "
        "pasta glue/ da versão no bucket; repetível",
    )
    command.set_defaults(handler=_lint_plan)


def _add_value_source_arguments(
    command: argparse.ArgumentParser,
) -> None:
    """[private] As opções de onde vêm os valores, comuns a ``render`` e ``values``."""
    command.add_argument(
        "--values-file",
        action="append",
        default=[],
        type=Path,
        metavar="ARQUIVO",
        help="um JSON de nome de placeholder para valor; completa e substitui os da conta e os "
        "dos arquivos anteriores; repita para vários",
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
        include=arguments.include,
    )
    print(
        f"{archive.path}: {archive.size_bytes} bytes, {archive.unzipped_bytes} descompactados, "
        f"para o CPython {archive.python} em {archive.platform}"
    )
    print(f"raiz: {', '.join(archive.top_level)}")

    # O próximo passo nomeia o python_callable de uma task Python, ou o caminho que o bash_command
    # de uma task Bash usa, já que a pasta de trabalho dela é temporária.
    upload = "envie o .zip em Settings -> Storage -> Python/Bash Operator Files do workflow, salve"
    if arguments.entry_module is None:
        print(
            f"próximo passo: {upload}, e chame o código no bash_command pelo caminho "
            "/usr/local/airflow/dags, onde o worker extrai o .zip"
        )
        return 0
    module = arguments.entry_module.stem
    print(f"próximo passo: {upload}, e nomeie a função como python_callable: {module}.<função>")
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


def _prepare_offline(
    arguments: argparse.Namespace,
) -> int:
    """[private] Grava o ``.tar.gz`` e imprime o resumo e o próximo passo."""
    archive = prepare_offline.prepare_archive(
        arguments.project,
        arguments.archive,
        python=arguments.python,
    )
    print(
        f"{archive.path}: {archive.size_bytes} bytes, {archive.extracted_bytes} extraídos, com o "
        f"CPython {archive.python} em Linux x86_64"
    )
    print(f"raiz: {archive.root}/")
    print(
        "próximo passo: copie o arquivo para o prefixo da entrada de código do job no S3 do "
        "projeto, e no comando do job extraia-o com tar -xzf em /opt/ml/processing/code e chame "
        f"/opt/ml/processing/code/{archive.root}/.venv/bin/python"
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
    de cada ``--values-file``, na ordem da linha de comando, com um aviso na saída de erro quando
    a leitura da conta termina sem ``PROJECT_KEY_ID``."""
    if arguments.profile is None and not arguments.values_file:
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
    # Cada arquivo completa e substitui o que veio antes dele.
    for values_file in arguments.values_file:
        values.update(render.load_values(values_file))

    # O aviso vem depois dos arquivos, que podem dar a chave que o papel não tem.
    if arguments.profile is not None and "PROJECT_KEY_ID" not in values:
        print(_NO_KEY_WARNING, file=sys.stderr)
    return values


def _compare(
    arguments: argparse.Namespace,
) -> int:
    """[private] Imprime as linhas das diferenças, ou que as definições têm o mesmo conteúdo."""
    differences = compare.compare_definitions(arguments.first, arguments.second)
    if not differences:
        print("as definições têm o mesmo conteúdo")
        return 0
    for line in differences:
        print(line)
    return 0


def _lint(
    arguments: argparse.Namespace,
) -> int:
    """[private] Imprime cada recusa numa linha e termina com 1, ou ``ok`` com o número de
    arquivos lidos e 0; uma pasta é uma aplicação, um arquivo é uma definição."""
    if arguments.path.is_dir():
        if arguments.promoted:
            raise RefusalError("--promoted lê uma cópia renderizada: passe o arquivo, não a pasta")
        if arguments.prefix:
            raise RefusalError(
                "--prefix vale para um arquivo; numa aplicação, os prefixos vêm do manifest"
            )
        report = lint.lint_application(
            arguments.path,
            instance_types=arguments.instance_type,
            image_repository=arguments.image_repository,
        )
        files = report.files
        findings = report.findings
    else:
        if arguments.promoted and not arguments.prefix:
            raise RefusalError("--promoted pede --prefix, o prefixo da versão promovida no bucket")
        files = [arguments.path]
        findings = lint.lint_definition(
            arguments.path,
            promoted=arguments.promoted,
            prefixes=arguments.prefix,
            instance_types=arguments.instance_type,
            image_repository=arguments.image_repository,
        )

    for finding in findings:
        print(finding)
    if findings:
        return 1
    print(f"ok: {len(files)} arquivo(s)")
    return 0


def _lint_plan(
    arguments: argparse.Namespace,
) -> int:
    """[private] Imprime cada recusa numa linha e termina com 1, ou ``ok`` com os jobs do Glue
    lidos e 0; um plano sem job do Glue passa com ``-`` no lugar dos jobs."""
    report = lint.lint_plan(arguments.plan, prefixes=arguments.prefix)
    for finding in report.findings:
        print(finding)
    if report.findings:
        return 1
    jobs = ", ".join(report.jobs) or "-"
    print(f"ok: {len(report.jobs)} job(s) do Glue: {jobs}")
    return 0
